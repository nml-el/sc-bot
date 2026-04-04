import os
from pathlib import Path
import sys
import uuid

from dotenv import load_dotenv

from sc_bot.agent import create_ai_agent
from sc_bot.config import DB_PATH, MARKER_CSV_PATH, DEFAULT_MARKER_SOURCE
from sc_bot.db_metadata import get_app_version, get_database_version
from sc_bot.logger import setup_session_logger
from sc_bot.tui import ScBotApp


def _scripts_dir() -> Path:
    """
    Returns the absolute path to the repository's `scripts` directory.

    Args:
        None

    Returns:
        Path: Absolute path to the scripts directory.

    Raises:
        None
    """
    return Path(__file__).resolve().parents[2] / "scripts"


def _ensure_scripts_dir_on_path() -> None:
    """
    Adds the repository's `scripts` directory to `sys.path` if needed.

    Args:
        None

    Returns:
        None

    Raises:
        None
    """
    scripts_dir = str(_scripts_dir())
    if scripts_dir not in sys.path:
        sys.path.append(scripts_dir)


def _rebuild_database() -> bool:
    """
    Rebuilds the local marker database using the standard setup workflow.

    Args:
        None

    Returns:
        bool: `True` if the rebuild succeeds, otherwise `False`.

    Raises:
        None
    """
    _ensure_scripts_dir_on_path()
    from setup_db import setup_database

    return setup_database() == 0


def _ensure_database_is_current() -> bool:
    """
    Ensures the local database exists and matches the installed sc-bot version.

    Args:
        None

    Returns:
        bool: `True` if the database is ready for use, otherwise `False`.

    Raises:
        None
    """
    app_version = get_app_version()

    try:
        database_version = get_database_version(DB_PATH)
    except Exception as exc:
        print(f"Warning: could not read database version metadata ({exc}). Rebuilding local database...")
        database_version = None

    if DB_PATH.exists() and database_version == app_version:
        return True

    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}. Building the local database for sc-bot {app_version}...")
    elif database_version is None:
        print("Database version metadata is missing. Rebuilding the local database...")
    else:
        print(
            f"Database version {database_version} does not match installed sc-bot {app_version}. "
            "Rebuilding the local database..."
        )

    if not _rebuild_database():
        print("Error: automatic database rebuild failed.")
        print("Please run 'uv run python scripts/setup_db.py' to initialize the database.")
        return False

    return DB_PATH.exists()


def _maybe_import_marker_csv() -> None:
    """
    Refreshes the user marker CSV if it exists and the main database is available.

    Args:
        None

    Returns:
        None

    Raises:
        None
    """
    if not DB_PATH.exists() or not MARKER_CSV_PATH.exists():
        return

    import sqlite3

    _ensure_scripts_dir_on_path()
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
    """
    Starts the interactive sc-bot TUI after validating local prerequisites.

    Args:
        None

    Returns:
        None

    Raises:
        None
    """
    # Load environment variables (e.g., GOOGLE_API_KEY)
    load_dotenv()

    if not _ensure_database_is_current():
        return

    _maybe_import_marker_csv()

    if not os.environ.get("GOOGLE_API_KEY"):
        print("Error: GOOGLE_API_KEY not found in .env file or environment variables.")
        print("Please copy .env.example to .env and set GOOGLE_API_KEY=your_key_here")
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
