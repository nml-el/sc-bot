import os
import sqlite3
import urllib.request

import pandas as pd

from utils import fuzzy_resolve


def download_celltypist(dest: str) -> None:
    """
    Downloads the CellTypist Pan-Immune Excel dataset if it does not already exist.

    Args:
        dest (str): Local destination path for the downloaded Excel file.

    Returns:
        None

    Raises:
        RuntimeError: If the dataset cannot be downloaded.
    """
    url = (
        "https://raw.githubusercontent.com/Teichlab/celltypist_wiki/main/atlases/"
        "Pan_Immune_CellTypist/v2/tables/Basic_celltype_information.xlsx"
    )
    if os.path.exists(dest):
        print("CellTypist data already exists.")
        return

    print(f"Downloading CellTypist data from {url}...")
    os.makedirs(os.path.dirname(dest), exist_ok=True)

    try:
        urllib.request.urlretrieve(url, dest)
        print("Download complete.")
    except Exception as exc:
        if os.path.exists(dest):
            os.remove(dest)
        raise RuntimeError(f"Failed to download CellTypist data from {url}: {exc}") from exc


def ingest_celltypist(conn: sqlite3.Connection, lbl_to_id: dict, id_to_lbl: dict, choices: list) -> int:
    """
    Reads CellTypist Pan-Immune Excel data and inserts curated positive marker records into the database.

    Args:
        conn (sqlite3.Connection): The SQLite database connection.
        lbl_to_id (dict): Mapping from ontology label to node ID.
        id_to_lbl (dict): Mapping from node ID to ontology label.
        choices (list): List of possible ontology labels.

    Returns:
        int: The number of unique marker records inserted.

    Raises:
        RuntimeError: If the CellTypist dataset cannot be downloaded.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    excel_path = os.path.join(base_dir, "data", "raw", "Basic_celltype_information.xlsx")

    download_celltypist(excel_path)

    cursor = conn.cursor()
    source_name = "CellTypist"
    species_id = 1
    tissue = "Immune system"

    cursor.execute("DELETE FROM gene_aliases WHERE source = ?", (source_name,))
    cursor.execute("DELETE FROM cell_markers WHERE source = ?", (source_name,))

    print("Parsing CellTypist and normalizing cell types...")
    df = pd.read_excel(excel_path, usecols=["Low-hierarchy cell types", "Curated markers"])
    df = df.drop_duplicates(subset=["Low-hierarchy cell types", "Curated markers"])

    data_to_insert: set[tuple[str, str, str, int, str]] = set()
    mapping_cache = {}

    for _, row in df.iterrows():
        raw_cell_type = str(row["Low-hierarchy cell types"])
        marker_block = str(row["Curated markers"])

        if raw_cell_type not in mapping_cache:
            canonical_lbl = fuzzy_resolve(raw_cell_type, lbl_to_id, id_to_lbl, choices)
            mapping_cache[raw_cell_type] = canonical_lbl

        canonical_cell_type = mapping_cache[raw_cell_type]

        for raw_gene in marker_block.split(","):
            marker_gene = raw_gene.strip()
            if not marker_gene or marker_gene.lower() == "nan":
                continue

            data_to_insert.add((canonical_cell_type, tissue, marker_gene, species_id, source_name))

    cursor.executemany(
        """
        INSERT INTO cell_markers (cell_type, tissue, marker_gene, species_id, source)
        VALUES (?, ?, ?, ?, ?)
        """,
        sorted(data_to_insert),
    )

    cursor.execute("INSERT OR IGNORE INTO tissues (name, canonical_tissue) VALUES (?, ?)", (tissue, tissue))

    print(f"Successfully inserted {len(data_to_insert)} records from CellTypist.")
    return len(data_to_insert)
