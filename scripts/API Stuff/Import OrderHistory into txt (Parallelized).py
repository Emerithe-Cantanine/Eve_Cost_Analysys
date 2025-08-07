import sqlite3
import requests
import time
import csv
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# Constants
DB_PATH = r"../../CostAnalysis.db"
CSV_OUTPUT = "OrderHistory.csv"
REGION_ID_START = 10000008
REGION_ID_END = 10000070
ESI_TEMPLATE = "https://esi.evetech.net/latest/markets/{regionID}/history/?datasource=tranquility&type_id={typeID}"
HEADERS = {"User-Agent": "EVE Cost Analysis Tool by YourName"}
MAX_THREADS = 70  # ESI safe limit is ~5 requests/second

# CSV field names
FIELDNAMES = ["regionID", "typeID", "average", "date", "highest", "lowest", "order_count", "volume"]

# Thread-safe write lock
write_lock = threading.Lock()

# Step 1: Get typeIDs with valid activityID
def get_valid_type_ids(db_path):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT typeID FROM Items WHERE activityID IS NOT NULL")
        return [row[0] for row in cursor.fetchall()]

# Step 2: Fetch and write data for one region
def process_region(region_id, type_ids, csv_path):
    count = 0
    rows = []
    for type_id in type_ids:
        url = ESI_TEMPLATE.format(regionID=region_id, typeID=type_id)
        try:
            response = requests.get(url, headers=HEADERS)
            if response.status_code == 200:
                data = response.json()
                for entry in data:
                    row = {
                        "regionID": region_id,
                        "typeID": type_id,
                        "average": entry.get("average"),
                        "date": entry.get("date"),
                        "highest": entry.get("highest"),
                        "lowest": entry.get("lowest"),
                        "order_count": entry.get("order_count"),
                        "volume": entry.get("volume")
                    }
                    rows.append(row)
            else:
                print(f"[{region_id}] HTTP {response.status_code} for type {type_id}")
        except Exception as e:
            print(f"[{region_id}] Error for type {type_id}: {e}")
        time.sleep(0.2)  # Respect rate limit per thread

    if rows:
        with write_lock:
            with open(csv_path, mode="a", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)
                writer.writerows(rows)
        #print(f"[{region_id}] Wrote {len(rows)} rows")
        if count >= 1000:
            count = 0
            print("1000 calls")

# Step 3: Run everything in parallel
def fetch_market_data_parallel(type_ids, csv_path):
    # Create/overwrite the file and write header once
    with open(csv_path, mode="w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)
        writer.writeheader()

    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        futures = []
        for region_id in range(REGION_ID_START, REGION_ID_END + 1):
            futures.append(executor.submit(process_region, region_id, type_ids, csv_path))

        for future in as_completed(futures):
            future.result()  # Raise exceptions if any

if __name__ == "__main__":
    type_ids = get_valid_type_ids(DB_PATH)
    print(f"Found {len(type_ids)} valid typeIDs.")
    fetch_market_data_parallel(type_ids, CSV_OUTPUT)
    print(f"All data saved to {CSV_OUTPUT}")
