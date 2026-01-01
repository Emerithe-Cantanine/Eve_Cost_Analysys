import sqlite3
import requests
import time
import csv
import os

# Constants
DB_PATH = r"../../CostAnalysis.db"
CSV_OUTPUT = "OrderHistory.csv"
REGION_ID_START = 10000001
REGION_ID_END = 10000069
ESI_TEMPLATE = "https://esi.evetech.net/latest/markets/{regionID}/history/?datasource=tranquility&type_id={typeID}"
HEADERS = {"User-Agent": "EVE Cost Analysis Tool by Emerithe Cantanine"}

def run_query(db_path, query):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(query)
    results = cursor.fetchall()
    conn.commit()
    conn.close()

    return results

# Step 1: Get typeIDs with valid activityID
def get_valid_type_ids(db_path):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT typeID FROM Recipes WHERE activityID IS NOT NULL AND activityID IS NOT 8")#8=t2 bpo
        return [row[0] for row in cursor.fetchall()]

# Step 2: Fetch and write data to CSV
def fetch_and_write_to_csv(type_ids, csv_path):
    fieldnames = ["regionID", "typeID", "average", "date", "highest", "lowest", "order_count", "volume"]
    calls = 0

    # Create or overwrite the CSV file
    with open(csv_path, mode="w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        regions = run_query(DB_PATH, "select RegionID from Regions")
        for region_id in regions:
            if region_id[0] == 10000024 or region_id == 10000026: continue
            print(region_id[0])
            for type_id in type_ids:
                url = ESI_TEMPLATE.format(regionID=region_id[0], typeID=type_id)
                try:
                    response = requests.get(url, headers=HEADERS)
                    if response.status_code == 200:
                        data = response.json()
                        for entry in data:
                            row = {
                                "regionID": region_id[0],
                                "typeID": type_id,
                                "average": entry.get("average"),
                                "date": entry.get("date"),
                                "highest": entry.get("highest"),
                                "lowest": entry.get("lowest"),
                                "order_count": entry.get("order_count"),
                                "volume": entry.get("volume")
                            }
                            writer.writerow(row)
                        #print(f"Stored {len(data)} entries for region {region_id}, type {type_id}")
                        calls += 1
                        
                        if calls % 250 == 0:
                            print("250 calls made")
                            calls = 0

                        if calls >= 1000:
                            print("1000 calls made")
                            calls = 0
                    else:
                        print(f"Failed for region {region_id[0]}, type {type_id}: HTTP {response.status_code}")
                except Exception as e:
                    print(f"Error for region {region_id[0]}, type {type_id}: {e}")
                time.sleep(1.0)  # Respect ESI rate limits

if __name__ == "__main__":
    type_ids = get_valid_type_ids(DB_PATH)
    print(f"Found {len(type_ids)} valid typeIDs.")
    fetch_and_write_to_csv(type_ids, CSV_OUTPUT)
    print(f"All data saved to {CSV_OUTPUT}")
