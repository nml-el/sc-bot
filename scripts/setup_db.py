import argparse
import os
import sqlite3
import sys

# Add both src/ and scripts/ to Python path for imports to work regardless of where run
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ingest_cellmarker2 import ingest_cellmarker2
from ingest_panglao import ingest_panglao
from utils import create_schema, load_ontology
from sc_bot.config import DB_PATH


def main() -> int:
    """
    Main entrypoint for orchestrating the database setup.
    Parses arguments to determine whether to initialize the database schema, load
    the ontology, and selectively ingest data sources like PanglaoDB or CellMarker2.
    """
    parser = argparse.ArgumentParser(description="Setup SQLite database and ingest data sources.")
    parser.add_argument("--panglao", action="store_true", help="Ingest PanglaoDB data")
    parser.add_argument("--cellmarker2", action="store_true", help="Ingest CellMarker2 data")
    parser.add_argument("--keep-schema", action="store_true", help="Refresh source data without dropping the schema")

    args = parser.parse_args()

    # If no specific flags are set, run both by default
    if not args.panglao and not args.cellmarker2:
        args.panglao = True
        args.cellmarker2 = True

    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        if not args.keep_schema:
            print("Creating schema...")
            create_schema(cursor)

        lbl_to_id, id_to_lbl, choices = load_ontology(cursor, skip_db_write=args.keep_schema)

        if args.panglao:
            ingest_panglao(conn, lbl_to_id, id_to_lbl, choices)

        if args.cellmarker2:
            ingest_cellmarker2(conn, lbl_to_id, id_to_lbl, choices)

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


if __name__ == "__main__":
    sys.exit(main())
