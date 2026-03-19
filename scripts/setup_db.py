import sqlite3


def setup_database() -> None:
    # 1. Connect to SQLite database (this creates the file if it doesn't exist)
    db_filename = "cell_data.db"
    conn = sqlite3.connect(db_filename)

    # Create a cursor object to execute SQL commands
    cursor = conn.cursor()

    # 2. Create the table
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

    # Clear existing data if script is run multiple times
    cursor.execute("DELETE FROM cell_markers")

    # 3. Define the dummy data
    data_to_insert = [
        ("T cell", "Immune Cell", "CD3E", "Human", "PanglaoDB"),
        ("B cell", "Immune Cell", "CD19", "Human", "PanglaoDB"),
        ("Neuron", "Brain", "SYP", "Mouse", "CellMarker"),
        ("Hepatocyte", "Liver", "ALB", "Human", "Human Cell Atlas"),
        ("Cardiomyocyte", "Heart", "TNNT2", "Mouse", "PanglaoDB"),
    ]

    # 4. Insert the data into the table
    cursor.executemany(
        """
        INSERT INTO cell_markers (cell_type, tissue, marker_gene, species, source)
        VALUES (?, ?, ?, ?, ?)
    """,
        data_to_insert,
    )

    # Save (commit) the changes
    conn.commit()
    print(f"Successfully created '{db_filename}' and inserted {len(data_to_insert)} rows.")

    # 5. Verify by querying the data back
    print("\n--- Reading Data from SQLite ---")
    cursor.execute("SELECT * FROM cell_markers")
    rows = cursor.fetchall()

    for row in rows:
        print(row)

    # 6. Close the connection
    conn.close()


if __name__ == "__main__":
    setup_database()
