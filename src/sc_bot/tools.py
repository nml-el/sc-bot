import sqlite3
from functools import lru_cache
from typing import Any

from langchain_core.tools import tool
from rapidfuzz import process, fuzz

from sc_bot.config import DB_PATH
from sc_bot.enrichr import Enrichr

ENRICHR_HUMAN_LIBRARIES = [
    "CellMarker_2024",
    "CellMarker_Augmented_2021",
    "PanglaoDB_Augmented_2021",
    "Azimuth_Cell_Types_2021",
    "Azimuth_2023",
    "Tabula_Sapiens",
    "Human_Gene_Atlas",
    "Descartes_Cell_Types_and_Tissue_2021",
]

ENRICHR_MOUSE_LIBRARIES = [
    "Tabula_Muris",
    "Mouse_Gene_Atlas",
    "PanglaoDB_Augmented_2021",
]


def get_connection() -> sqlite3.Connection:
    """
    Returns a connection to the SQLite database.

    Returns:
        sqlite3.Connection: A connection object to the database.
    """
    return sqlite3.connect(DB_PATH)


@lru_cache(maxsize=128)
def resolve_cell_type(query: str) -> str:
    """
    Resolves a natural language cell type query to a canonical cell type
    available in the database using exact matching, fuzzy matching, and ontology lineage.
    """
    conn = get_connection()
    cursor = conn.cursor()

    query_clean = query.strip()

    # 1. Exact match in cell_markers?
    cursor.execute("SELECT DISTINCT cell_type FROM cell_markers WHERE cell_type COLLATE NOCASE = ?", (query_clean,))
    row = cursor.fetchone()
    if row:
        conn.close()
        return row[0]

    # 2. Fuzzy match against known cell_markers first
    cursor.execute("SELECT DISTINCT cell_type FROM cell_markers")
    db_types = [r[0] for r in cursor.fetchall()]

    match = process.extractOne(query_clean, db_types, scorer=fuzz.token_sort_ratio)
    if match and match[1] >= 85:
        conn.close()
        return match[0]

    # 3. Fuzzy match against ontology to find a node ID
    cursor.execute("""
        SELECT id, label FROM ontology_nodes
        UNION ALL
        SELECT node_id, synonym FROM ontology_synonyms
    """)
    rows = cursor.fetchall()

    ontology_strings = {}
    for nid, text in rows:
        if text:
            ontology_strings[text.lower()] = nid

    match_ont = process.extractOne(query_clean.lower(), ontology_strings.keys(), scorer=fuzz.token_sort_ratio)

    if not match_ont or match_ont[1] < 75:
        conn.close()
        return query_clean

    matched_text = match_ont[0]
    matched_id = ontology_strings[matched_text]

    db_types_set = set(db_types)

    queue = [matched_id]
    visited = set()

    while queue:
        curr = queue.pop(0)
        if curr in visited:
            continue
        visited.add(curr)

        # get label for current node
        cursor.execute("SELECT label FROM ontology_nodes WHERE id = ?", (curr,))
        lbl_row = cursor.fetchone()
        if lbl_row:
            lbl = lbl_row[0]
            if lbl in db_types_set:
                conn.close()
                return lbl

        # add parents dynamically
        cursor.execute("SELECT obj_id FROM ontology_edges WHERE sub_id = ? AND pred = 'is_a'", (curr,))
        queue.extend([row[0] for row in cursor.fetchall()])

    conn.close()
    # If no ancestor found, fallback to original query
    return query_clean


@lru_cache(maxsize=128)
def resolve_tissue(query: str) -> tuple[str, ...]:
    """
    Resolves a natural language tissue query to a list of raw tissue names.
    If the tissue maps to a canonical tissue, all raw names under that canonical
    are returned. Otherwise, returns the best matched raw name.
    """
    conn = get_connection()
    cursor = conn.cursor()
    query_clean = query.strip()

    cursor.execute("SELECT name, canonical_tissue FROM tissues")
    tissues = cursor.fetchall()
    conn.close()

    names = [r[0] for r in tissues]
    match = process.extractOne(query_clean, names, scorer=fuzz.token_sort_ratio)

    if not match or match[1] < 75:
        return tuple()

    best_name = match[0]
    best_canonical = next((r[1] for r in tissues if r[0] == best_name), None)

    if best_canonical:
        # Return all names sharing this canonical tissue
        return tuple(r[0] for r in tissues if r[1] == best_canonical)
    else:
        # No canonical, return just the matched raw name
        return (best_name,)


@tool
def get_all_cell_types() -> list[str]:
    """
    Returns a list of all unique cell types available in the database. Use this to check for valid cell types.

    Returns:
        list[str]: A list containing all unique cell types.

    Example:
        Input: get_all_cell_types()
        Output: ["T cell", "B cell", "GABAergic neuron"]
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT cell_type FROM cell_markers ORDER BY cell_type")
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]


@tool
def get_tissues_for_cell_type(cell_type: str, species: str = "Human") -> list[str]:
    """
    Returns the list of canonical tissue categories that have data for this cell type.
    Used by the agent to suggest tissue refinements to the user.
    """
    conn = get_connection()
    cursor = conn.cursor()
    resolved_type = resolve_cell_type(cell_type)

    query = """
        SELECT DISTINCT t.canonical_tissue
        FROM cell_markers m
        JOIN species s ON m.species_id = s.id
        -- INNER JOIN relies on the tissues table being fully populated during ingestion
        JOIN tissues t ON m.tissue = t.name
        WHERE m.cell_type COLLATE NOCASE = ? 
          AND s.name COLLATE NOCASE = ?
          AND t.canonical_tissue IS NOT NULL
        ORDER BY t.canonical_tissue
    """
    cursor.execute(query, (resolved_type, species))
    rows = cursor.fetchall()
    conn.close()

    return [row[0] for row in rows]


@tool
def get_markers_by_cell_type(
    cell_types: list[str], species: str = "Human", tissue: str | None = None
) -> list[dict[str, str | int]]:
    """
    Retrieves a list of marker genes for the specified cell type(s) and species.
    It automatically resolves natural language queries (like "T cells") to the canonical ontology cell types.
    Optionally accepts a tissue filter to restrict results.
    Each returned marker includes 'tissue_count' and 'source_count' scores for ranking.

    Args:
        cell_types (list[str]): A list of cell type names to query (e.g., ['T cell'] or ['T cell', 'B cell']).
        species (str, optional): The species to query. Valid options are "Human" or "Mouse". Defaults to "Human".
        tissue (str | None, optional): A tissue name to filter by. Defaults to None.

    Returns:
        list[dict[str, str | int]]: A list of dictionaries containing 'marker_gene', 'tissue_count', and 'source_count'.
    """
    if not cell_types:
        return []

    conn = get_connection()
    cursor = conn.cursor()

    resolved_types = list(set(resolve_cell_type(ct) for ct in cell_types))
    ct_placeholders = ",".join("?" for _ in resolved_types)
    num_types = len(resolved_types)

    params = list(resolved_types)
    params.append(species)

    tissue_clause = ""
    if tissue:
        resolved_tissues = list(resolve_tissue(tissue))
        if resolved_tissues:
            t_placeholders = ",".join("?" for _ in resolved_tissues)
            tissue_clause = f"AND m.tissue IN ({t_placeholders})"
            params.extend(resolved_tissues)

    params.append(num_types)

    query = f"""
        SELECT m.marker_gene, 
               COUNT(DISTINCT m.tissue) as tissue_count,
               COUNT(DISTINCT m.source) as source_count
        FROM cell_markers m
        JOIN species s ON m.species_id = s.id
        WHERE m.cell_type COLLATE NOCASE IN ({ct_placeholders})
          AND s.name COLLATE NOCASE = ?
          AND m.marker_gene != 'nan'
          {tissue_clause}
        GROUP BY m.marker_gene 
        HAVING COUNT(DISTINCT m.cell_type COLLATE NOCASE) = ?
        ORDER BY source_count DESC, tissue_count DESC
    """

    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    conn.close()

    return [{"marker_gene": row[0], "tissue_count": row[1], "source_count": row[2]} for row in rows]


@tool
def get_cell_types_by_marker(marker_genes: list[str], species: str = "Human") -> list[dict[str, str]]:
    """
    Retrieves a list of cell types associated with the specified marker gene(s) and species.
    If multiple genes are provided, it returns only the cell types that express ALL of the provided genes.

    Args:
        marker_genes (list[str]): A list of marker gene names to query (e.g., ['CD3E'] or ['CD3E', 'CD8A']).
        species (str, optional): The species to query. Valid options are "Human" or "Mouse". Defaults to "Human".

    Returns:
        list[dict[str, str]]: A list of dictionaries containing cell type details (cell_type).
    """
    if not marker_genes:
        return []

    conn = get_connection()
    cursor = conn.cursor()

    # Deduplicate and normalize marker genes case-insensitively
    unique_genes = list({g.upper(): g for g in marker_genes}.values())
    placeholders = ",".join("?" for _ in unique_genes)
    num_genes = len(unique_genes)

    query = f"""
        SELECT m.cell_type
        FROM cell_markers m
        JOIN species s ON m.species_id = s.id
        WHERE m.marker_gene COLLATE NOCASE IN ({placeholders})
          AND s.name COLLATE NOCASE = ?
          AND m.marker_gene != 'nan'
        GROUP BY m.cell_type 
        HAVING COUNT(DISTINCT m.marker_gene COLLATE NOCASE) = ?
    """

    params = tuple(unique_genes) + (species, num_genes)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [{"cell_type": row[0]} for row in rows]


@tool
def query_enrichr(genes: list[str], species: str = "Human") -> list[dict[str, Any]]:
    """
    Submits a list of marker genes to the external Enrichr API to infer plausible cell types.
    This searches across multiple large external databases and returns the top 25 consensus matches.
    Use this when the user provides a list of genes and wants to know what cell type they represent.

    Args:
        genes (list[str]): A list of gene symbols (e.g., ["CD3D", "CD3E", "CD8A"]).
        species (str, optional): The species context. Valid options are "Human" or "Mouse". Defaults to "Human".

    Returns:
        list[dict]: Top 25 matching cell types, sorted by adjusted p-value.
        Each dictionary contains:
        - term_name (str): The inferred cell type name.
        - adjusted_p_value (float): Statistical significance of the match.
        - combined_score (float): Enrichr combined score (higher is better).
        - overlapping_genes (list[str]): The subset of input genes that matched this cell type.
        - gene_sets (list[str]): The libraries where this match was found.

    Example:
        Input: query_enrichr(["CD3D", "CD3E"], "Human")
        Output: [{"term_name": "T Cell", "adjusted_p_value": 0.001, "combined_score": 150.5, "overlapping_genes": ["CD3D", "CD3E"], "gene_sets": ["Azimuth_2023"]}]
    """
    if not genes:
        return []

    libraries = ENRICHR_HUMAN_LIBRARIES if species.lower() == "human" else ENRICHR_MOUSE_LIBRARIES

    try:
        enrichr = Enrichr(gene_list=genes)
    except ValueError:
        return []

    results_df = enrichr.get_cell_type_enrichment(gene_sets=libraries, max_workers=5)

    if results_df.empty:
        return []

    aggregated = []
    for term, group in results_df.groupby("term name"):
        # Take the best p-value and combined score for this term across libraries
        best_row = group.loc[group["adjusted p-value"].idxmin()]

        # Union the overlapping genes across all libraries that found this term
        all_genes = set()
        for genes_list in group["overlapping genes"]:
            all_genes.update(genes_list)

        aggregated.append(
            {
                "term_name": term,
                "adjusted_p_value": best_row["adjusted p-value"],
                "combined_score": best_row["combined score"],
                "overlapping_genes": list(all_genes),
                "gene_sets": group["gene_set"].tolist(),
            }
        )

    # Sort by adjusted p-value ascending, then combined score descending
    aggregated.sort(key=lambda x: (x["adjusted_p_value"], -x["combined_score"]))

    # Return top 25 consensus results
    return aggregated[:25]
