import csv
import sqlite3
import sys
import os

# Add the root directory to sys.path to allow importing config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_PATH


def setup_database() -> None:
    """
    Sets up the SQLite database and populates it with data from PanglaoDB TSV file.

    Returns:
        None

    Errors:
        sqlite3.Error: If there's an issue connecting or writing to the database.
        FileNotFoundError: If the TSV file cannot be found.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cell_markers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cell_type TEXT NOT NULL,
            tissue TEXT NOT NULL,
            marker_gene TEXT NOT NULL,
            species TEXT NOT NULL,
            source TEXT NOT NULL
        )
    """)

    # Clear existing data so it's idempotent
    cursor.execute("DELETE FROM cell_markers")

    tsv_filename = "data/raw/PanglaoDB_markers_27_Mar_2020.tsv"
    source_name = "PanglaoDB"
    data_to_insert = []

    try:
        with open(tsv_filename, encoding="utf-8") as file:
            tsv_reader = csv.DictReader(file, delimiter="\t")

            for row in tsv_reader:
                cell_type = row.get("cell type", "Unknown")
                tissue = row.get("organ", "Unknown")
                marker_gene = row.get("official gene symbol", "Unknown")
                species = row.get("species", "Unknown")

                data_to_insert.append((cell_type, tissue, marker_gene, species, source_name))

        cursor.executemany(
            """
            INSERT INTO cell_markers (cell_type, tissue, marker_gene, species, source)
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
