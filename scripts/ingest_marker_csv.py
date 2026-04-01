import csv
import os
import sqlite3

from utils import fuzzy_resolve


def _species_id_from_name(species: str) -> int | None:
    """
    Converts a species name to an internal species id.

    Args:
        species (str): Species name from the marker CSV.

    Returns:
        int | None: Species id if recognized, otherwise None.
    """
    if species.strip().lower() == "human":
        return 1
    if species.strip().lower() == "mouse":
        return 2
    return None


def ingest_marker_csv(
    conn: sqlite3.Connection,
    csv_path: str,
    lbl_to_id: dict,
    id_to_lbl: dict,
    choices: list,
    default_source: str = "custom-source",
) -> int:
    """
    Ingests a user-provided marker CSV into the internal SQLite database.

    Args:
        conn (sqlite3.Connection): SQLite connection.
        csv_path (str): Path to the marker CSV.
        lbl_to_id (dict): Ontology label-to-id map.
        id_to_lbl (dict): Ontology id-to-label map.
        choices (list): Ontology label choices.
        default_source (str, optional): Source name to use when CSV rows omit it.

    Returns:
        int: Number of inserted marker rows.

    Raises:
        FileNotFoundError: If the CSV file does not exist.
        ValueError: If required columns are missing.
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Marker CSV not found at {csv_path}")

    cursor = conn.cursor()

    with open(csv_path, encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {"species", "cell_type", "tissue", "marker_gene"}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise ValueError(f"Marker CSV must include columns: {sorted(required)}")

        cursor.execute("DELETE FROM cell_markers WHERE source = ?", (default_source,))
        cursor.execute("DELETE FROM gene_aliases WHERE source = ?", (default_source,))

        data_to_insert = []
        aliases_to_insert = set()
        tissues_seen = set()
        mapping_cache = {}

        for row in reader:
            species = row.get("species", "")
            species_id = _species_id_from_name(species)
            if species_id is None:
                continue

            raw_cell_type = row.get("cell_type", "Unknown")
            tissue = row.get("tissue", "Unknown")
            marker_gene = row.get("marker_gene", "Unknown")
            source = row.get("source", default_source) or default_source
            gene_aliases = row.get("gene_aliases", "")

            if raw_cell_type not in mapping_cache:
                mapping_cache[raw_cell_type] = fuzzy_resolve(raw_cell_type, lbl_to_id, id_to_lbl, choices)
            canonical_cell_type = mapping_cache[raw_cell_type]

            data_to_insert.append((canonical_cell_type, tissue, marker_gene, species_id, source))
            tissues_seen.add(tissue)

            if gene_aliases and gene_aliases != "nan":
                for alias in gene_aliases.split("|"):
                    alias = alias.strip()
                    if alias and alias.lower() != marker_gene.lower():
                        aliases_to_insert.add((species_id, marker_gene, alias, source))

        cursor.executemany(
            "INSERT INTO cell_markers (cell_type, tissue, marker_gene, species_id, source) VALUES (?, ?, ?, ?, ?)",
            data_to_insert,
        )

        cursor.executemany(
            "INSERT OR IGNORE INTO tissues (name, canonical_tissue) VALUES (?, ?)",
            [(t, t) for t in tissues_seen if t != "nan"],
        )

        if aliases_to_insert:
            cursor.executemany(
                "INSERT OR IGNORE INTO gene_aliases (species_id, canonical_symbol, alias, source) VALUES (?, ?, ?, ?)",
                list(aliases_to_insert),
            )

    return len(data_to_insert)
