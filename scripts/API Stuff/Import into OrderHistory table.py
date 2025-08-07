import sqlite3
import requests
import time

# Constants
DB_PATH = r"../../CostAnalysis.db"
REGION_ID_START = 10000001
REGION_ID_END = 10000070
ESI_TEMPLATE = "https://esi.evetech.net/latest/markets/{regionID}/history/?datasource=tranquility&type_id={typeID}"
HEADERS = {"User-Agent": "EVE Cost Analysis Tool by Emerithe Cantanine"}

# Step 1: Get typeIDs with valid activityID
def get_valid_type_ids(db_path):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT typeID FROM Items WHERE activityID IS NOT NULL AND activityID IS NOT 8")#8=t2 bpo
        return [row[0] for row in cursor.fetchall()]

# Step 2: Insert one row of market history into OrderHistory
def insert_order_history(conn, region_id, type_id, entry):
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO OrderHistory (regionID, typeID, average, date, highest, lowest, order_count, volume)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        region_id,
        type_id,
        entry.get("average"),
        entry.get("date"),
        entry.get("highest"),
        entry.get("lowest"),
        entry.get("order_count"),
        entry.get("volume")
    ))
    conn.commit()

# Step 3: Fetch and store data
def fetch_and_store_history(type_ids, db_path):
    with sqlite3.connect(db_path) as conn:
        for region_id in range(REGION_ID_START, REGION_ID_END + 1):
            for type_id in type_ids:
                url = ESI_TEMPLATE.format(regionID=region_id, typeID=type_id)
                try:
                    response = requests.get(url, headers=HEADERS)
                    if response.status_code == 200:
                        data = response.json()
                        for entry in data:
                            insert_order_history(conn, region_id, type_id, entry)
                        print(f"Stored {len(data)} entries for region {region_id}, type {type_id}")
                    else:
                        print(f"Failed for region {region_id}, type {type_id}: HTTP {response.status_code}")
                except Exception as e:
                    print(f"Error for region {region_id}, type {type_id}: {e}")
                time.sleep(0.2)  # ESI rate limiting

if __name__ == "__main__":
    type_ids = get_valid_type_ids(DB_PATH)
    print(f"Found {len(type_ids)} valid typeIDs.")
    fetch_and_store_history(type_ids, DB_PATH)
