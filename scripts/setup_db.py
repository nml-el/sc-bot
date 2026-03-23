import csv
import json
import sqlite3
import sys
import os
from rapidfuzz import process, fuzz

# Add the src directory to sys.path to allow importing config
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from sc_bot.config import DB_PATH


def normalize_panglao(panglao_type: str) -> str:
    t = panglao_type.lower()
    if t.endswith(" cells"):
        t = t[:-6]
    elif t.endswith(" cell"):
        t = t[:-5]
    elif t.endswith("s") and not t.endswith("ss"):
        t = t[:-1]
    return t


def setup_database() -> None:
    """
    Sets up the SQLite database and populates it with data from PanglaoDB TSV file,
    normalized against the UBERON/CL ontology.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Drop existing tables
    cursor.execute("DROP TABLE IF EXISTS cell_markers")
    cursor.execute("DROP TABLE IF EXISTS species")
    cursor.execute("DROP TABLE IF EXISTS ontology_nodes")
    cursor.execute("DROP TABLE IF EXISTS ontology_synonyms")
    cursor.execute("DROP TABLE IF EXISTS ontology_edges")

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

    # 1. Load Ontology
    print("Loading UBERON ontology...")
    with open("data/raw/uberon-full.json", "r", encoding="utf-8") as f:
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

    print(
        f"Inserting {len(nodes_to_insert)} nodes, {len(synonyms_to_insert)} synonyms, {len(edges_to_insert)} edges..."
    )
    cursor.executemany("INSERT OR IGNORE INTO ontology_nodes (id, label) VALUES (?, ?)", nodes_to_insert)
    cursor.executemany("INSERT INTO ontology_synonyms (node_id, synonym) VALUES (?, ?)", synonyms_to_insert)
    cursor.executemany("INSERT INTO ontology_edges (sub_id, obj_id, pred) VALUES (?, ?, ?)", edges_to_insert)
    conn.commit()

    choices = list(lbl_to_id.keys())

    # 2. Ingest PanglaoDB
    tsv_filename = "data/raw/PanglaoDB_markers_27_Mar_2020.tsv"
    source_name = "PanglaoDB"
    data_to_insert = []

    # Cache for panglao -> canonical mapping so we don't run fuzzy match for every row
    panglao_mapping_cache = {}

    print("Parsing PanglaoDB and normalizing cell types...")
    try:
        with open(tsv_filename, encoding="utf-8") as file:
            tsv_reader = csv.DictReader(file, delimiter="\t")

            for row in tsv_reader:
                raw_cell_type = row.get("cell type", "Unknown")
                tissue = row.get("organ", "Unknown")
                marker_gene = row.get("official gene symbol", "Unknown")
                species_str = row.get("species", "Unknown")

                # Normalize Cell Type
                if raw_cell_type not in panglao_mapping_cache:
                    norm = normalize_panglao(raw_cell_type)
                    match = None
                    if f"{norm} cell" in lbl_to_id:
                        match = f"{norm} cell"
                    elif norm in lbl_to_id:
                        match = norm
                    elif raw_cell_type.lower() in lbl_to_id:
                        match = raw_cell_type.lower()
                    else:
                        fuzzy_matches = process.extract(norm, choices, scorer=fuzz.token_sort_ratio, limit=1)
                        if fuzzy_matches and fuzzy_matches[0][1] >= 85:
                            match = fuzzy_matches[0][0]

                    if match:
                        canonical_lbl = id_to_lbl[lbl_to_id[match]]
                        panglao_mapping_cache[raw_cell_type] = canonical_lbl
                    else:
                        panglao_mapping_cache[raw_cell_type] = raw_cell_type

                canonical_cell_type = panglao_mapping_cache[raw_cell_type]

                # Handle species splitting (e.g., "Mm Hs")
                abbreviations = species_str.split()
                for abbr in abbreviations:
                    if abbr == "Hs":
                        species_id = 1
                    elif abbr == "Mm":
                        species_id = 2
                    else:
                        continue  # Skip unknown species

                    data_to_insert.append((canonical_cell_type, tissue, marker_gene, species_id, source_name))

        cursor.executemany(
            """
            INSERT INTO cell_markers (cell_type, tissue, marker_gene, species_id, source)
            VALUES (?, ?, ?, ?, ?)
        """,
            data_to_insert,
        )

        conn.commit()
        print(f"Successfully inserted {len(data_to_insert)} records from '{tsv_filename}' into the database.")

    except FileNotFoundError:
        print(f"Error: Could not find the file '{tsv_filename}'. Make sure it is in the same directory.")
    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        conn.close()


if __name__ == "__main__":
    setup_database()
