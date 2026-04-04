import json
import os
import sqlite3
import urllib.request
from typing import Tuple

from rapidfuzz import fuzz, process


def download_uberon(dest: str) -> None:
    """
    Downloads the UBERON ontology JSON if it does not already exist.
    """
    if os.path.exists(dest):
        print("UBERON ontology data already exists.")
        return

    url = "http://purl.obolibrary.org/obo/uberon/uberon-full.json"

    print(f"Downloading UBERON ontology from {url}...")
    os.makedirs(os.path.dirname(dest), exist_ok=True)

    try:
        urllib.request.urlretrieve(url, dest)
        print("Download complete.")
    except Exception as e:
        if os.path.exists(dest):
            os.remove(dest)
        raise RuntimeError(f"Failed to download UBERON ontology data: {e}")


def create_schema(cursor: sqlite3.Cursor) -> None:
    """
    Drops existing tables and recreates the schema for species, cell_markers,
    tissues, and ontology tables. Populates the species table.

    Args:
        cursor (sqlite3.Cursor): The SQLite database cursor.
    """
    # Drop existing tables
    cursor.execute("DROP TABLE IF EXISTS cell_markers")
    cursor.execute("DROP TABLE IF EXISTS species")
    cursor.execute("DROP TABLE IF EXISTS tissues")
    cursor.execute("DROP TABLE IF EXISTS ontology_nodes")
    cursor.execute("DROP TABLE IF EXISTS ontology_synonyms")
    cursor.execute("DROP TABLE IF EXISTS ontology_edges")
    cursor.execute("DROP TABLE IF EXISTS gene_aliases")
    cursor.execute("DROP TABLE IF EXISTS app_metadata")

    # Create species table
    cursor.execute("""
        CREATE TABLE species (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            taxa_id INTEGER NOT NULL UNIQUE,
            abbreviation TEXT NOT NULL UNIQUE
        )
    """)

    # Populate species table
    cursor.execute("INSERT OR IGNORE INTO species (id, name, taxa_id, abbreviation) VALUES (1, 'Human', 9606, 'Hs')")
    cursor.execute("INSERT OR IGNORE INTO species (id, name, taxa_id, abbreviation) VALUES (2, 'Mouse', 10090, 'Mm')")

    # Create cell_markers table
    cursor.execute("""
        CREATE TABLE cell_markers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cell_type TEXT NOT NULL,
            tissue TEXT NOT NULL,
            marker_gene TEXT NOT NULL,
            species_id INTEGER NOT NULL,
            source TEXT NOT NULL,
            FOREIGN KEY(species_id) REFERENCES species(id)
        )
    """)

    # Create tissues table
    cursor.execute("""
        CREATE TABLE tissues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            canonical_tissue TEXT
        )
    """)

    # Create gene_aliases table
    cursor.execute("""
        CREATE TABLE gene_aliases (
            species_id INTEGER NOT NULL,
            source TEXT NOT NULL,
            canonical_symbol TEXT NOT NULL,
            alias TEXT NOT NULL,
            UNIQUE(canonical_symbol, alias COLLATE NOCASE, species_id, source),
            FOREIGN KEY(species_id) REFERENCES species(id)
        )
    """)

    # Create ontology tables
    cursor.execute("""
        CREATE TABLE ontology_nodes (
            id TEXT PRIMARY KEY,
            label TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE ontology_synonyms (
            node_id TEXT NOT NULL,
            synonym TEXT NOT NULL,
            FOREIGN KEY(node_id) REFERENCES ontology_nodes(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE ontology_edges (
            sub_id TEXT NOT NULL,
            obj_id TEXT NOT NULL,
            pred TEXT NOT NULL,
            FOREIGN KEY(sub_id) REFERENCES ontology_nodes(id),
            FOREIGN KEY(obj_id) REFERENCES ontology_nodes(id)
        )
    """)


def load_ontology(cursor: sqlite3.Cursor, skip_db_write: bool = False) -> Tuple[dict, dict, list]:
    """
    Reads the UBERON ontology from JSON and populates mapping dictionaries.
    Optionally inserts the ontology into the database.

    Args:
        cursor (sqlite3.Cursor): The SQLite database cursor.
        skip_db_write (bool): If True, skips database insertion. Defaults to False.

    Returns:
        tuple[dict, dict, list]: A tuple containing lbl_to_id, id_to_lbl, and choices.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    json_path = os.path.join(base_dir, "data", "raw", "uberon-full.json")

    download_uberon(json_path)

    print("Loading UBERON ontology...")
    with open(json_path, "r", encoding="utf-8") as f:
        ontology_data = json.load(f)

    graph = ontology_data.get("graphs", [])[0]

    lbl_to_id = {}
    id_to_lbl = {}

    nodes_to_insert = []
    synonyms_to_insert = []

    for n in graph.get("nodes", []):
        nid = n.get("id")
        lbl = n.get("lbl")
        if not nid or not lbl:
            continue

        nodes_to_insert.append((nid, lbl))
        lbl_to_id[lbl.lower()] = nid
        id_to_lbl[nid] = lbl

        meta = n.get("meta", {})
        for s in meta.get("synonyms", []):
            s_val = s.get("val")
            if s_val:
                synonyms_to_insert.append((nid, s_val))
                lbl_to_id[s_val.lower()] = nid

    edges_to_insert = []
    for e in graph.get("edges", []):
        sub = e.get("sub")
        obj = e.get("obj")
        pred = e.get("pred")
        if sub and obj and pred:
            edges_to_insert.append((sub, obj, pred))

    if not skip_db_write:
        print(
            f"Inserting {len(nodes_to_insert)} nodes, {len(synonyms_to_insert)} synonyms, {len(edges_to_insert)} edges..."
        )
        cursor.executemany("INSERT OR IGNORE INTO ontology_nodes (id, label) VALUES (?, ?)", nodes_to_insert)
        cursor.executemany("INSERT INTO ontology_synonyms (node_id, synonym) VALUES (?, ?)", synonyms_to_insert)
        cursor.executemany("INSERT INTO ontology_edges (sub_id, obj_id, pred) VALUES (?, ?, ?)", edges_to_insert)

    choices = list(lbl_to_id.keys())
    return lbl_to_id, id_to_lbl, choices


def get_gene_alias_weight(cursor: sqlite3.Cursor, canonical_symbol: str, species_id: int | None = None) -> int:
    """
    Returns a weight boost for custom marker genes.

    Args:
        cursor (sqlite3.Cursor): SQLite cursor.
        canonical_symbol (str): Canonical gene symbol.
        species_id (int | None, optional): Species filter.

    Returns:
        int: Weight boost for custom-sourced aliases.
    """
    query = "SELECT COUNT(*) FROM gene_aliases WHERE canonical_symbol COLLATE NOCASE = ? AND source = 'custom-source'"
    params = [canonical_symbol]
    if species_id is not None:
        query += " AND species_id = ?"
        params.append(species_id)

    cursor.execute(query, tuple(params))
    return int(cursor.fetchone()[0])


def normalize_cell_name(name: str) -> str:
    """
    Normalizes a cell type name by lowercasing and stripping trailing words.

    Args:
        name (str): The raw cell type name.

    Returns:
        str: The normalized cell type name.
    """
    t = name.lower()
    if t.endswith(" cells"):
        t = t[:-6]
    elif t.endswith(" cell"):
        t = t[:-5]
    elif t.endswith("s") and not t.endswith("ss"):
        t = t[:-1]
    return t


def fuzzy_resolve(raw_name: str, lbl_to_id: dict, id_to_lbl: dict, choices: list) -> str:
    """
    Resolves a raw cell type name to a canonical ontology label using exact and fuzzy matching.

    Args:
        raw_name (str): The raw cell type name.
        lbl_to_id (dict): Mapping from label to node ID.
        id_to_lbl (dict): Mapping from node ID to label.
        choices (list): List of possible labels for fuzzy matching.

    Returns:
        str: The canonical label if matched, else the original raw name.
    """
    norm = normalize_cell_name(raw_name)

    # Exact matches
    if f"{norm} cell" in lbl_to_id:
        match_key = f"{norm} cell"
    elif norm in lbl_to_id:
        match_key = norm
    elif raw_name.lower() in lbl_to_id:
        match_key = raw_name.lower()
    else:
        # Fuzzy match
        fuzzy_matches = process.extract(norm, choices, scorer=fuzz.token_sort_ratio, limit=1)
        if fuzzy_matches and fuzzy_matches[0][1] >= 85:
            match_key = fuzzy_matches[0][0]
        else:
            return raw_name

    return id_to_lbl[lbl_to_id[match_key]]
