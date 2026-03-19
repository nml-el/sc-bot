import sqlite3
from langchain_core.tools import tool

DB_FILENAME = "cell_data.db"


def get_connection() -> sqlite3.Connection:
    """Returns a connection to the SQLite database."""
    return sqlite3.connect(DB_FILENAME)


@tool
def get_all_cell_types() -> list[str]:
    """Returns a list of all unique cell types available in the database. Use this to check for valid cell types."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT cell_type FROM cell_markers")
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]


@tool
def get_markers_by_cell_type(cell_type: str) -> list[dict[str, str]]:
    """
    Args:
        cell_type (str): The name of the cell type to query (e.g., 'T cell', 'Neuron').

    Returns:
        A list of marker genes for a specific cell type. Each entry includes the marker_gene, tissue, species, and source.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT marker_gene, tissue, species, source FROM cell_markers WHERE cell_type COLLATE NOCASE = ?", (cell_type,)
    )
    rows = cursor.fetchall()
    conn.close()

    return [{"marker_gene": row[0], "tissue": row[1], "species": row[2], "source": row[3]} for row in rows]


@tool
def get_cell_types_by_marker(marker_gene: str) -> list[dict[str, str]]:
    """
    Returns a list of cell types associated with a specific marker gene.
    Each entry includes the cell_type, tissue, species, and source.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT cell_type, tissue, species, source FROM cell_markers WHERE marker_gene COLLATE NOCASE = ?",
        (marker_gene,),
    )
    rows = cursor.fetchall()
    conn.close()

    return [{"cell_type": row[0], "tissue": row[1], "species": row[2], "source": row[3]} for row in rows]
