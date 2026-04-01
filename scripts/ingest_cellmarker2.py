import os
import sqlite3
import urllib.request
from urllib.error import URLError

import pandas as pd
from rapidfuzz import fuzz, process

from utils import fuzzy_resolve


def download_cellmarker2(dest: str) -> None:
    """
    Downloads the CellMarker 2.0 Excel dataset if it does not already exist.
    """
    url = "http://117.50.127.228/CellMarker/CellMarker_download_files/file/Cell_marker_All.xlsx"
    if not os.path.exists(dest):
        print(f"Downloading CellMarker2 data from {url}...")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        try:
            urllib.request.urlretrieve(url, dest)
            print("Download complete.")
        except URLError as e:
            raise RuntimeError(f"Failed to download CellMarker2 data from {url}: {e}")
    else:
        print("CellMarker2 data already exists.")


def ingest_cellmarker2(conn: sqlite3.Connection, lbl_to_id: dict, id_to_lbl: dict, choices: list) -> int:
    """
    Reads CellMarker2 Excel data, resolves cell types, and inserts records into the database.

    Args:
        conn (sqlite3.Connection): The SQLite database connection.
        lbl_to_id (dict): Mapping from ontology label to node ID.
        id_to_lbl (dict): Mapping from node ID to ontology label.
        choices (list): List of possible ontology labels.

    Returns:
        int: The number of records inserted.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    excel_path = os.path.join(base_dir, "data", "raw", "Cell_marker_All.xlsx")

    download_cellmarker2(excel_path)

    cursor = conn.cursor()
    source_name = "CellMarker2"
    cursor.execute("DELETE FROM gene_aliases WHERE source = ?", (source_name,))

    print("Parsing CellMarker2 and normalizing cell types...")
    df = pd.read_excel(excel_path, usecols=["species", "cancer_type", "tissue_type", "cell_name", "marker", "Symbol"])

    # Filter for Normal and specific species
    df = df[df["cancer_type"] == "Normal"]
    df = df[df["species"].isin(["Human", "Mouse"])]

    # Deduplicate
    df = df.drop_duplicates(subset=["species", "tissue_type", "cell_name", "marker", "Symbol"])

    cursor.execute("DELETE FROM cell_markers WHERE source = ?", (source_name,))

    data_to_insert = []
    aliases_to_insert = set()
    mapping_cache = {}

    for _, row in df.iterrows():
        raw_cell_type = str(row["cell_name"])
        tissue = str(row["tissue_type"])
        alias_gene = str(row["marker"])
        marker_gene = str(row["Symbol"])
        species_str = str(row["species"])

        if raw_cell_type not in mapping_cache:
            canonical_lbl = fuzzy_resolve(raw_cell_type, lbl_to_id, id_to_lbl, choices)
            mapping_cache[raw_cell_type] = canonical_lbl

        canonical_cell_type = mapping_cache[raw_cell_type]

        if species_str == "Human":
            species_id = 1
        elif species_str == "Mouse":
            species_id = 2
        else:
            print(f"Warning: Unknown species '{species_str}' found in CellMarker2. Skipping row.")
            continue

        if alias_gene != "nan" and marker_gene != "nan" and alias_gene.lower() != marker_gene.lower():
            aliases_to_insert.add((species_id, source_name, marker_gene, alias_gene))

        data_to_insert.append((canonical_cell_type, tissue, marker_gene, species_id, source_name))

    cursor.executemany(
        """
        INSERT INTO cell_markers (cell_type, tissue, marker_gene, species_id, source)
        VALUES (?, ?, ?, ?, ?)
    """,
        data_to_insert,
    )

    # Populate tissues table mapping
    cursor.execute("SELECT DISTINCT canonical_tissue FROM tissues WHERE canonical_tissue IS NOT NULL")
    canonical_tissues = [r[0] for r in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT tissue FROM cell_markers WHERE source = ?", (source_name,))
    cm2_tissues = [r[0] for r in cursor.fetchall()]

    tissues_to_insert = []
    for t in cm2_tissues:
        if t == "nan":
            continue

        m = process.extractOne(t, canonical_tissues, scorer=fuzz.token_sort_ratio)
        canonical = m[0] if m and m[1] >= 90 else None
        tissues_to_insert.append((t, canonical))

    cursor.executemany("INSERT OR IGNORE INTO tissues (name, canonical_tissue) VALUES (?, ?)", tissues_to_insert)

    if aliases_to_insert:
        cursor.executemany(
            "INSERT OR IGNORE INTO gene_aliases (species_id, source, canonical_symbol, alias) VALUES (?, ?, ?, ?)",
            list(aliases_to_insert),
        )

    print(f"Successfully inserted {len(data_to_insert)} records from CellMarker2.")
    return len(data_to_insert)
