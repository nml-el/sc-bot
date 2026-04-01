import csv
import gzip
import os
import shutil
import sqlite3
import urllib.request

from utils import fuzzy_resolve


def download_panglaodb(dest: str) -> None:
    """
    Downloads and extracts the PanglaoDB TSV dataset if it does not already exist.
    """
    if os.path.exists(dest):
        print("PanglaoDB data already exists.")
        return

    url = "https://panglaodb.se/markers/PanglaoDB_markers_27_Mar_2020.tsv.gz"
    gz_dest = dest + ".gz"

    print(f"Downloading PanglaoDB data from {url}...")
    os.makedirs(os.path.dirname(dest), exist_ok=True)

    try:
        urllib.request.urlretrieve(url, gz_dest)
        print("Extracting PanglaoDB data...")
        with gzip.open(gz_dest, "rb") as f_in:
            with open(dest, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        os.remove(gz_dest)
        print("Download and extraction complete.")
    except Exception as e:
        if os.path.exists(gz_dest):
            os.remove(gz_dest)
        raise RuntimeError(f"Failed to download/extract PanglaoDB data: {e}")


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

    download_panglaodb(tsv_filename)

    data_to_insert = []
    aliases_to_insert = set()
    mapping_cache = {}

    print("Parsing PanglaoDB and normalizing cell types...")

    with open(tsv_filename, encoding="utf-8") as file:
        tsv_reader = csv.DictReader(file, delimiter="\t")

        for row in tsv_reader:
            raw_cell_type = row.get("cell type", "Unknown")
            tissue = row.get("organ", "Unknown")
            marker_gene = row.get("official gene symbol", "Unknown")
            nicknames = row.get("nicknames", "")
            species_str = row.get("species", "Unknown")

            if raw_cell_type not in mapping_cache:
                canonical_lbl = fuzzy_resolve(raw_cell_type, lbl_to_id, id_to_lbl, choices)
                mapping_cache[raw_cell_type] = canonical_lbl

            canonical_cell_type = mapping_cache[raw_cell_type]

            if marker_gene != "nan" and nicknames and nicknames != "nan":
                aliases = [alias.strip() for alias in nicknames.split("|") if alias.strip()]
                for alias in aliases:
                    if alias.lower() != marker_gene.lower():
                        for abbr in species_str.split():
                            if abbr == "Hs":
                                alias_species_id = 1
                            elif abbr == "Mm":
                                alias_species_id = 2
                            else:
                                continue
                            aliases_to_insert.add((alias_species_id, source_name, marker_gene, alias))

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

    if aliases_to_insert:
        cursor.executemany(
            "INSERT OR IGNORE INTO gene_aliases (species_id, source, canonical_symbol, alias) VALUES (?, ?, ?, ?)",
            list(aliases_to_insert),
        )

    print(f"Successfully inserted {len(data_to_insert)} records from '{tsv_filename}'.")
    return len(data_to_insert)
