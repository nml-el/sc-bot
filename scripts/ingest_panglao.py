import csv
import os
import sqlite3

from utils import fuzzy_resolve


def ingest_panglao(conn: sqlite3.Connection, lbl_to_id: dict, id_to_lbl: dict, choices: list) -> int:
    """
    Reads PanglaoDB TSV data, resolves cell types, and inserts records into the database.

    Args:
        conn (sqlite3.Connection): The SQLite database connection.
        lbl_to_id (dict): Mapping from ontology label to node ID.
        id_to_lbl (dict): Mapping from node ID to ontology label.
        choices (list): List of possible ontology labels.

    Returns:
        int: The number of records inserted.
    """
    cursor = conn.cursor()
    source_name = "PanglaoDB"

    # Delete existing PanglaoDB rows
    cursor.execute("DELETE FROM cell_markers WHERE source = ?", (source_name,))

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tsv_filename = os.path.join(base_dir, "data", "raw", "PanglaoDB_markers_27_Mar_2020.tsv")
    data_to_insert = []
    mapping_cache = {}

    print("Parsing PanglaoDB and normalizing cell types...")
    try:
        file = open(tsv_filename, encoding="utf-8")
    except FileNotFoundError:
        raise FileNotFoundError(f"PanglaoDB TSV not found at {tsv_filename}. Run from project root or check data/raw/.")

    with file:
        tsv_reader = csv.DictReader(file, delimiter="\t")

        for row in tsv_reader:
            raw_cell_type = row.get("cell type", "Unknown")
            tissue = row.get("organ", "Unknown")
            marker_gene = row.get("official gene symbol", "Unknown")
            species_str = row.get("species", "Unknown")

            if raw_cell_type not in mapping_cache:
                canonical_lbl = fuzzy_resolve(raw_cell_type, lbl_to_id, id_to_lbl, choices)
                mapping_cache[raw_cell_type] = canonical_lbl

            canonical_cell_type = mapping_cache[raw_cell_type]

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

    # Populate tissues table
    cursor.execute("SELECT DISTINCT tissue FROM cell_markers WHERE source = ?", (source_name,))
    tissues = cursor.fetchall()
    tissues_to_insert = [(t[0], t[0]) for t in tissues if t[0] != "nan"]

    cursor.executemany("INSERT OR IGNORE INTO tissues (name, canonical_tissue) VALUES (?, ?)", tissues_to_insert)

    print(f"Successfully inserted {len(data_to_insert)} records from '{tsv_filename}'.")
    return len(data_to_insert)
