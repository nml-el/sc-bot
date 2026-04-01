import os
import uuid
from dotenv import load_dotenv

from sc_bot.agent import create_ai_agent
from sc_bot.config import DB_PATH, MARKER_CSV_PATH, DEFAULT_MARKER_SOURCE
from sc_bot.logger import setup_session_logger
from sc_bot.tui import ScBotApp


def _maybe_import_marker_csv() -> None:
    """
    Refreshes the user marker CSV if it exists and the main database is available.

    Returns:
        None
    """
    if not DB_PATH.exists() or not MARKER_CSV_PATH.exists():
        return

    import sqlite3
    import sys

    sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
    from ingest_marker_csv import ingest_marker_csv
    from utils import load_ontology

    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        lbl_to_id, id_to_lbl, choices = load_ontology(cursor, skip_db_write=True)
        ingest_marker_csv(
            conn, str(MARKER_CSV_PATH), lbl_to_id, id_to_lbl, choices, default_source=DEFAULT_MARKER_SOURCE
        )
        conn.commit()
        print(f"Loaded personal marker CSV from {MARKER_CSV_PATH}")
    finally:
        conn.close()


def main() -> None:
    # Load environment variables (e.g., GEMINI_API_KEY)
    load_dotenv()

    _maybe_import_marker_csv()

    if not DB_PATH.exists():
        print(f"Error: Database not found at {DB_PATH}")
        print("Please run 'uv run python scripts/setup_db.py' to initialize the database.")
        return

    if not os.environ.get("GEMINI_API_KEY"):
        print("Error: GEMINI_API_KEY not found in .env file or environment variables.")
        print("Please add your key to a .env file: GEMINI_API_KEY=your_key_here")
        return

    session_id = uuid.uuid4().hex
    logger = setup_session_logger(session_id)
    logger.info("Session started (TUI Mode).")

    try:
        agent = create_ai_agent()
        app = ScBotApp(agent=agent, logger=logger)
        app.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"A fatal error occurred. Check logs at session_{session_id}.log")


if __name__ == "__main__":
    main()
