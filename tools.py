import sqlite3
from langchain_core.tools import tool

from config import DB_PATH


def get_connection() -> sqlite3.Connection:
    """
    Returns a connection to the SQLite database.

    Returns:
        sqlite3.Connection: A connection object to the database.
    """
    return sqlite3.connect(DB_PATH)


@tool
def get_all_cell_types() -> list[str]:
    """
    Returns a list of all unique cell types available in the database. Use this to check for valid cell types.

    Returns:
        list[str]: A list containing all unique cell types.

    Example:
        Input: get_all_cell_types()
        Output: ["T cells", "B cells", "Neurons"]
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT cell_type FROM cell_markers")
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]


@tool
def get_markers_by_cell_type(cell_types: list[str]) -> list[dict[str, str]]:
    """
    Retrieves a list of marker genes for the specified cell type(s).
    If multiple cell types are provided, it returns only the marker genes that are COMMON (intersection) across all provided cell types.

    Args:
        cell_types (list[str]): A list of cell type names to query (e.g., ['T cells'] or ['T cells', 'B cells']).

    Returns:
        list[dict[str, str]]: A list of dictionaries containing marker gene details (marker_gene).

    Example:
        Input: get_markers_by_cell_type(["T cells", "B cells"])
        Output: [{"marker_gene": "CXCR4"}, {"marker_gene": "CD52"}]
    """
    if not cell_types:
        return []

    conn = get_connection()
    cursor = conn.cursor()

    # Create placeholders for the IN clause
    placeholders = ",".join("?" for _ in cell_types)
    num_types = len(cell_types)

    # We use grouping to find genes that appear in ALL specified cell types
    query = f"""
        SELECT marker_gene
        FROM cell_markers 
        WHERE cell_type COLLATE NOCASE IN ({placeholders})
        GROUP BY marker_gene 
        HAVING COUNT(DISTINCT cell_type COLLATE NOCASE) = ?
    """

    # The parameters are the list of cell types, plus the count at the end for the HAVING clause
    params = tuple(cell_types) + (num_types,)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    # Since we are doing an intersection grouping, returning tissue/source metadata doesn't make strict sense
    # because a gene might have different metadata in different cell types. We return just the genes.
    return [{"marker_gene": row[0]} for row in rows]


@tool
def get_cell_types_by_marker(marker_genes: list[str]) -> list[dict[str, str]]:
    """
    Retrieves a list of cell types associated with the specified marker gene(s).
    If multiple genes are provided, it returns only the cell types that express ALL of the provided genes.

    Args:
        marker_genes (list[str]): A list of marker gene names to query (e.g., ['CD3E'] or ['CD3E', 'CD8A']).

    Returns:
        list[dict[str, str]]: A list of dictionaries containing cell type details (cell_type).

    Example:
        Input: get_cell_types_by_marker(["CD3E", "CD8A"])
        Output: [{"cell_type": "T cells"}]
    """
    if not marker_genes:
        return []

    conn = get_connection()
    cursor = conn.cursor()

    placeholders = ",".join("?" for _ in marker_genes)
    num_genes = len(marker_genes)

    query = f"""
        SELECT cell_type
        FROM cell_markers 
        WHERE marker_gene COLLATE NOCASE IN ({placeholders})
        GROUP BY cell_type 
        HAVING COUNT(DISTINCT marker_gene COLLATE NOCASE) = ?
    """

    params = tuple(marker_genes) + (num_genes,)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [{"cell_type": row[0]} for row in rows]
