import os
import re
import sqlite3
import urllib.request

import pandas as pd

from utils import fuzzy_resolve

_HUMAN_ORF_PATTERN = re.compile(r"^([A-Z]\d+)orf(\d+)$", re.IGNORECASE)


def download_sctype(dest: str) -> None:
    """
    Downloads the ScType Excel dataset if it does not already exist.

    Args:
        dest (str): Local destination path for the downloaded Excel file.

    Returns:
        None

    Raises:
        RuntimeError: If the dataset cannot be downloaded.
    """
    url = "https://raw.githubusercontent.com/IanevskiAleksandr/sc-type/master/ScTypeDB_full.xlsx"
    if os.path.exists(dest):
        print("ScType data already exists.")
        return

    print(f"Downloading ScType data from {url}...")
    os.makedirs(os.path.dirname(dest), exist_ok=True)

    try:
        urllib.request.urlretrieve(url, dest)
        print("Download complete.")
    except Exception as exc:
        if os.path.exists(dest):
            os.remove(dest)
        raise RuntimeError(f"Failed to download ScType data from {url}: {exc}") from exc


def _normalize_sctype_gene_symbol(gene_symbol: str) -> str:
    """
    Normalizes ScType gene symbols into the human-oriented casing used by sc-bot.

    Args:
        gene_symbol (str): Raw gene symbol from the ScType spreadsheet.

    Returns:
        str: Normalized gene symbol, or an empty string if the value should be skipped.

    Raises:
        None
    """
    gene_clean = gene_symbol.strip()
    if not gene_clean or gene_clean.lower() == "nan":
        return ""

    orf_match = _HUMAN_ORF_PATTERN.fullmatch(gene_clean)
    if orf_match:
        return f"{orf_match.group(1).upper()}orf{orf_match.group(2)}"

    if any(char.islower() for char in gene_clean):
        return gene_clean.upper()

    return gene_clean


def ingest_sctype(conn: sqlite3.Connection, lbl_to_id: dict, id_to_lbl: dict, choices: list) -> int:
    """
    Reads ScType Excel data, resolves cell types, and inserts positive marker records into the database.

    Args:
        conn (sqlite3.Connection): The SQLite database connection.
        lbl_to_id (dict): Mapping from ontology label to node ID.
        id_to_lbl (dict): Mapping from node ID to ontology label.
        choices (list): List of possible ontology labels.

    Returns:
        int: The number of unique marker records inserted.

    Raises:
        RuntimeError: If the ScType dataset cannot be downloaded.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    excel_path = os.path.join(base_dir, "data", "raw", "ScTypeDB_full.xlsx")

    download_sctype(excel_path)

    cursor = conn.cursor()
    source_name = "ScType"
    species_id = 1

    cursor.execute("DELETE FROM gene_aliases WHERE source = ?", (source_name,))
    cursor.execute("DELETE FROM cell_markers WHERE source = ?", (source_name,))

    print("Parsing ScType and normalizing cell types...")
    df = pd.read_excel(excel_path, usecols=["tissueType", "cellName", "geneSymbolmore1"])
    df = df.drop_duplicates(subset=["tissueType", "cellName", "geneSymbolmore1"])

    data_to_insert: set[tuple[str, str, str, int, str]] = set()
    tissues_seen = set()
    mapping_cache = {}

    for _, row in df.iterrows():
        raw_cell_type = str(row["cellName"])
        tissue = str(row["tissueType"])
        marker_block = str(row["geneSymbolmore1"])

        if raw_cell_type not in mapping_cache:
            canonical_lbl = fuzzy_resolve(raw_cell_type, lbl_to_id, id_to_lbl, choices)
            mapping_cache[raw_cell_type] = canonical_lbl

        canonical_cell_type = mapping_cache[raw_cell_type]

        for raw_gene in marker_block.split(","):
            marker_gene = _normalize_sctype_gene_symbol(raw_gene)
            if not marker_gene:
                continue

            data_to_insert.add((canonical_cell_type, tissue, marker_gene, species_id, source_name))
            tissues_seen.add(tissue)

    cursor.executemany(
        """
        INSERT INTO cell_markers (cell_type, tissue, marker_gene, species_id, source)
        VALUES (?, ?, ?, ?, ?)
        """,
        sorted(data_to_insert),
    )

    cursor.executemany(
        "INSERT OR IGNORE INTO tissues (name, canonical_tissue) VALUES (?, ?)",
        sorted((tissue, tissue) for tissue in tissues_seen if tissue != "nan"),
    )

    print(f"Successfully inserted {len(data_to_insert)} records from ScType.")
    return len(data_to_insert)
