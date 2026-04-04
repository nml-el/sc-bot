"""Helpers for tracking the local database version."""

from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path
import sqlite3
import tomllib

APP_METADATA_TABLE = "app_metadata"
APP_VERSION_KEY = "app_version"


def get_app_version() -> str:
    """
    Returns the current application version for sc-bot.

    Args:
        None.

    Returns:
        str: The current semantic version string.

    Raises:
        RuntimeError: If the version cannot be determined from installed metadata or `pyproject.toml`.
    """
    pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
    try:
        with pyproject_path.open("rb") as pyproject_file:
            project_data = tomllib.load(pyproject_file)
    except FileNotFoundError:
        project_data = None

    version_value = None if project_data is None else project_data.get("project", {}).get("version")
    if isinstance(version_value, str) and version_value:
        return version_value

    try:
        return package_version("sc-bot")
    except PackageNotFoundError as exc:
        raise RuntimeError("Could not determine the sc-bot version.") from exc


def ensure_metadata_table(cursor: sqlite3.Cursor) -> None:
    """
    Ensures the metadata table exists for storing application-level database metadata.

    Args:
        cursor (sqlite3.Cursor): The SQLite cursor used to manage schema state.

    Returns:
        None

    Raises:
        sqlite3.Error: If SQLite cannot create the metadata table.
    """
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS app_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )


def set_database_version(cursor: sqlite3.Cursor, app_version: str) -> None:
    """
    Stores the application version used to build the local marker database.

    Args:
        cursor (sqlite3.Cursor): The SQLite cursor used to write metadata.
        app_version (str): The current sc-bot version string.

    Returns:
        None

    Raises:
        sqlite3.Error: If SQLite cannot write the version metadata.
    """
    ensure_metadata_table(cursor)
    cursor.execute(
        f"INSERT OR REPLACE INTO {APP_METADATA_TABLE} (key, value) VALUES (?, ?)",
        (APP_VERSION_KEY, app_version),
    )


def get_database_version(db_path: Path) -> str | None:
    """
    Returns the sc-bot version that last built the local marker database.

    Args:
        db_path (Path): The path to the SQLite marker database.

    Returns:
        str | None: The recorded app version, or `None` if no version metadata is available.

    Raises:
        sqlite3.Error: If SQLite cannot open the database.
    """
    if not db_path.exists():
        return None

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (APP_METADATA_TABLE,),
        )
        if cursor.fetchone() is None:
            return None

        cursor.execute(
            f"SELECT value FROM {APP_METADATA_TABLE} WHERE key = ?",
            (APP_VERSION_KEY,),
        )
        row = cursor.fetchone()
        return None if row is None else str(row[0])
    finally:
        conn.close()
