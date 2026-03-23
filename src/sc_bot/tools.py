import sqlite3
from functools import lru_cache
from langchain_core.tools import tool
from rapidfuzz import process, fuzz

from sc_bot.config import DB_PATH


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
def get_markers_by_cell_type(cell_types: list[str], species: str = "Human") -> list[dict[str, str]]:
    """
    Retrieves a list of marker genes for the specified cell type(s) and species.
    It automatically resolves natural language queries (like "T cells" or "T-lymphocyte") to the correct canonical ontology cell types.
    If multiple cell types are provided, it returns only the marker genes that are COMMON (intersection) across all provided cell types.

    Args:
        cell_types (list[str]): A list of cell type names to query (e.g., ['T cell'] or ['T cell', 'B cell']).
        species (str, optional): The species to query. Valid options are "Human" or "Mouse". Defaults to "Human".

    Returns:
        list[dict[str, str]]: A list of dictionaries containing marker gene details (marker_gene).

    Example:
        Input: get_markers_by_cell_type(["T cell", "B cell"], "Human")
        Output: [{"marker_gene": "CXCR4"}, {"marker_gene": "CD52"}]
    """
    if not cell_types:
        return []

    conn = get_connection()
    cursor = conn.cursor()

    # Resolve and deduplicate cell types automatically
    resolved_types = list(set(resolve_cell_type(ct) for ct in cell_types))

    # Create placeholders for the IN clause
    placeholders = ",".join("?" for _ in resolved_types)
    num_types = len(resolved_types)

    # We use grouping to find genes that appear in ALL specified cell types for the given species
    query = f"""
        SELECT m.marker_gene
        FROM cell_markers m
        JOIN species s ON m.species_id = s.id
        WHERE m.cell_type COLLATE NOCASE IN ({placeholders})
          AND s.name COLLATE NOCASE = ?
        GROUP BY m.marker_gene 
        HAVING COUNT(DISTINCT m.cell_type COLLATE NOCASE) = ?
    """

    # The parameters are the list of cell types, plus the species, plus the count at the end for the HAVING clause
    params = tuple(resolved_types) + (species, num_types)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [{"marker_gene": row[0]} for row in rows]


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

    Example:
        Input: get_cell_types_by_marker(["CD3E", "CD8A"], "Human")
        Output: [{"cell_type": "T cell"}]
    """
    if not marker_genes:
        return []

    conn = get_connection()
    cursor = conn.cursor()

    placeholders = ",".join("?" for _ in marker_genes)
    num_genes = len(marker_genes)

    query = f"""
        SELECT m.cell_type
        FROM cell_markers m
        JOIN species s ON m.species_id = s.id
        WHERE m.marker_gene COLLATE NOCASE IN ({placeholders})
          AND s.name COLLATE NOCASE = ?
        GROUP BY m.cell_type 
        HAVING COUNT(DISTINCT m.marker_gene COLLATE NOCASE) = ?
    """

    params = tuple(marker_genes) + (species, num_genes)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [{"cell_type": row[0]} for row in rows]
