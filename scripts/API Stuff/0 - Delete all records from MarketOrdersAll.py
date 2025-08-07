import sqlite3

# Path to your SQLite database file
db_path = '../../CostAnalysis.db'

# Connect to the database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Delete all records from MarketOrdersAll
try:
    cursor.execute("DELETE FROM MarketOrdersAll;")
    conn.commit()
    print("All data from MarketOrdersAll has been deleted.")
except sqlite3.Error as e:
    print(f"An error occurred: {e}")
finally:
    # Close the connection
    conn.close()
