import sqlite3
from langchain_core.tools import tool

DB_FILENAME = "data/sc_markers.db"


def get_connection() -> sqlite3.Connection:
    """
    Returns a connection to the SQLite database.

    Returns:
        sqlite3.Connection: A connection object to the database.
    """
    return sqlite3.connect(DB_FILENAME)


@tool
def get_all_cell_types() -> list[str]:
    """
    Returns a list of all unique cell types available in the database. Use this to check for valid cell types.

    Returns:
        list[str]: A list containing all unique cell types.

    Example:
        Input: get_all_cell_types()
        Output: ["T cell", "B cell", "Neuron"]
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT cell_type FROM cell_markers")
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]


@tool
def get_markers_by_cell_type(cell_type: str) -> list[dict[str, str]]:
    """
    Retrieves a list of marker genes for a specific cell type.

    Args:
        cell_type (str): The name of the cell type to query (e.g., 'T cell', 'Neuron').

    Returns:
        list[dict[str, str]]: A list of dictionaries containing marker gene details (marker_gene, tissue, species, source).

    Example:
        Input: get_markers_by_cell_type("T cell")
        Output: [{"marker_gene": "CD3E", "tissue": "Blood", "species": "Human", "source": "PBMC"}]
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
    Retrieves a list of cell types associated with a specific marker gene.

    Args:
        marker_gene (str): The name of the marker gene to query (e.g., 'CD3E', 'CD19').

    Returns:
        list[dict[str, str]]: A list of dictionaries containing cell type details (cell_type, tissue, species, source).

    Example:
        Input: get_cell_types_by_marker("CD3E")
        Output: [{"cell_type": "T cell", "tissue": "Blood", "species": "Human", "source": "PBMC"}]
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
