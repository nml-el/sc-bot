import argparse
import os
import sqlite3
import sys

# Add both src/ and scripts/ to Python path for imports to work regardless of where run
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ingest_cellmarker2 import ingest_cellmarker2
from ingest_marker_csv import ingest_marker_csv
from ingest_panglao import ingest_panglao
from sc_bot.db_metadata import get_app_version, set_database_version
from utils import create_schema, load_ontology
from sc_bot.config import DB_PATH


def setup_database(
    panglao: bool = True,
    cellmarker2: bool = True,
    marker_csv: str | None = None,
    marker_source: str = "custom-source",
    keep_schema: bool = False,
) -> int:
    """
    Builds or refreshes the local SQLite marker database.

    Args:
        panglao (bool, optional): Whether to ingest PanglaoDB data. Defaults to True.
        cellmarker2 (bool, optional): Whether to ingest CellMarker2 data. Defaults to True.
        marker_csv (str | None, optional): Path to a personal marker CSV to ingest. Defaults to None.
        marker_source (str, optional): Source label for CSV rows without a source value. Defaults to "custom-source".
        keep_schema (bool, optional): Whether to preserve the existing schema while refreshing data. Defaults to False.

    Returns:
        int: `0` on success, `1` on failure.

    Raises:
        None
    """
    if not panglao and not cellmarker2:
        panglao = True
        cellmarker2 = True

    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        if not keep_schema:
            print("Creating schema...")
            create_schema(cursor)

        lbl_to_id, id_to_lbl, choices = load_ontology(cursor, skip_db_write=keep_schema)

        if panglao:
            ingest_panglao(conn, lbl_to_id, id_to_lbl, choices)

        if cellmarker2:
            ingest_cellmarker2(conn, lbl_to_id, id_to_lbl, choices)

        if marker_csv:
            if os.path.exists(marker_csv):
                ingest_marker_csv(conn, marker_csv, lbl_to_id, id_to_lbl, choices, default_source=marker_source)
            else:
                print(f"Skipping marker CSV import; file not found at {marker_csv}")

        set_database_version(cursor, get_app_version())
        conn.commit()
        print("Database setup complete.")
        return 0
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error setting up database: {e}")
        return 1
    finally:
        if conn:
            conn.close()


def main() -> int:
    """
    Main entrypoint for orchestrating the database setup.
    Parses arguments to determine whether to initialize the database schema, load
    the ontology, and selectively ingest data sources like PanglaoDB or CellMarker2.

    Args:
        None

    Returns:
        int: Process exit code.

    Raises:
        None
    """
    parser = argparse.ArgumentParser(description="Setup SQLite database and ingest data sources.")
    parser.add_argument("--panglao", action="store_true", help="Ingest PanglaoDB data")
    parser.add_argument("--cellmarker2", action="store_true", help="Ingest CellMarker2 data")
    parser.add_argument("--marker-csv", type=str, default=None, help="Ingest a personal marker CSV file")
    parser.add_argument(
        "--marker-source", type=str, default="custom-source", help="Source label for the personal marker CSV"
    )
    parser.add_argument("--keep-schema", action="store_true", help="Refresh source data without dropping the schema")

    args = parser.parse_args()
    return setup_database(
        panglao=args.panglao,
        cellmarker2=args.cellmarker2,
        marker_csv=args.marker_csv,
        marker_source=args.marker_source,
        keep_schema=args.keep_schema,
    )


if __name__ == "__main__":
    sys.exit(main())
