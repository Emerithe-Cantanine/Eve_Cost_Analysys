import sqlite3

# Full path to the database file
db_path = r"../../CostAnalysis - Market Orders.db"

try:
    # Connect to the SQLite database
    conn = sqlite3.connect(db_path)
    print("Connection successful!")

    # Create a cursor object to interact with the database
    cursor = conn.cursor()

    # Example query (you can replace this with your own)
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("Tables in database:", tables)

    # Always close the connection when done
    conn.close()
    print("Connection closed.")

except sqlite3.Error as e:
    print("SQLite error:", e)
