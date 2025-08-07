import sqlite3
import os
import json
import re

# Paths
db_path = r"../../CostAnalysis.db"
folder_path = r"../../All Region API calls"

# Target table schema fields
table_name = "MarketOrdersAll"

# Function to extract all JSON arrays from a file
def extract_json_arrays(text):
    json_arrays = []
    matches = re.finditer(r'\[\s*{.*?}\s*\]', text, re.DOTALL)
    for match in matches:
        try:
            arr = json.loads(match.group())
            if isinstance(arr, list):
                json_arrays.append(arr)
        except json.JSONDecodeError:
            continue
    return json_arrays

# Connect to SQLite
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    print("Connected to database.")

    # Ensure table exists
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            typeID INTEGER,
            volume INTEGER,
            solarSystemID INTEGER,
            range TEXT,
            price REAL,
            orderID INTEGER PRIMARY KEY,
            stationID INTEGER,
            dateIssued TEXT,
            buy_true_sell_false INTEGER,
            duration INTEGER
        )
    """)

    # Loop through files
    for i in range(10000001, 10000071):
        filename = os.path.join(folder_path, f"{i}.txt")
        if not os.path.exists(filename):
            print(f"File not found: {filename}")
            continue

        print(f"Processing {filename}...")
        with open(filename, 'r', encoding='utf-8') as file:
            content = file.read()

        json_arrays = extract_json_arrays(content)

        for order_array in json_arrays:
            for order in order_array:
                try:
                    cursor.execute(f"""
                        INSERT OR REPLACE INTO {table_name} (
                            typeID, volume, solarSystemID, range, price,
                            orderID, stationID, dateIssued, buy_true_sell_false, duration
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        order["type_id"],
                        order["volume_remain"],
                        order["system_id"],
                        order["range"],
                        order["price"],
                        order["order_id"],
                        order["location_id"],
                        order["issued"],
                        int(order["is_buy_order"]),
                        order["duration"]
                    ))
                except Exception as e:
                    print(f"Skipping order due to error: {e}")

    conn.commit()
    print("All market orders imported successfully.")

except sqlite3.Error as e:
    print("SQLite error:", e)

finally:
    if conn:
        conn.close()
        print("Database connection closed.")
