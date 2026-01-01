import sqlite3
import csv
import os

# Define paths
db_path = "../../CostAnalysis.db"
csv_path = "./marketHistory.csv"

# Connect to the SQLite database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("DELETE FROM OrderHistory")

# Prepare the INSERT SQL statement
insert_sql = """
    INSERT INTO OrderHistory (
        typeID, average, date, highest, lowest, order_count, volume, regionID
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
"""

# Read the CSV and insert rows into the table
with open(csv_path, newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    rows = [
        (
            int(row['typeID']),
            float(row[' average']),
            row[' date'],
            float(row[' highest']),
            float(row[' lowest']),
            int(row[' order_count']),
            int(row[' volume']),
            int(row[' region'])
        )
        for row in reader
    ]

    cursor.executemany(insert_sql, rows)

# Commit and close
conn.commit()
conn.close()

print("OrderHistory.csv has been successfully imported into the database.")
