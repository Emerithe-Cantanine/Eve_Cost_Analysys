import requests
import time
import sqlite3

DB_NAME = r"../../CostAnalysis.db"
TABLE_NAME = "MarketOrdersAll"
BASE_URL = "https://esi.evetech.net/latest/markets/{}/orders/?datasource=tranquility&order_type=all&page={}"
REGION_START = 10000001
REGION_END = 10000070
SLEEP_TIME = 0.2

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            orderID INTEGER PRIMARY KEY,
            typeID INTEGER,
            volume INTEGER,
            solarSystemID INTEGER,
            range TEXT,
            price REAL,
            stationID INTEGER,
            dateIssued TEXT,
            buy_true_sell_false INTEGER,
            duration INTEGER
        )
    """)
    conn.commit()
    return conn

def insert_orders(conn, orders):
    cursor = conn.cursor()
    for order in orders:
        try:
            cursor.execute(f"""
                INSERT OR IGNORE INTO {TABLE_NAME} (
                    orderID, typeID, volume, solarSystemID, range, price,
                    stationID, dateIssued, buy_true_sell_false, duration
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order.get("order_id"),
                order.get("type_id"),
                order.get("volume_remain"),
                order.get("system_id"),
                order.get("range"),
                order.get("price"),
                order.get("location_id"),
                order.get("issued"),
                int(order.get("is_buy_order")),
                order.get("duration")
            ))
        except Exception as e:
            print(f"Error inserting order {order.get('order_id')}: {e}")
    conn.commit()

def fetch_region_data(conn, region_id):
    page = 1
    while True:
        url = BASE_URL.format(region_id, page)
        response = requests.get(url)
        print(f"Region {region_id}, Page {page} - Status {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            insert_orders(conn, data)
            page += 1
            time.sleep(SLEEP_TIME)
        elif response.status_code == 404 and "Requested page does not exist!" in response.text:
            print(f"Region {region_id} complete at page {page - 1}.")
            break
        else:
            print(f"Unexpected response for region {region_id} page {page}: {response.status_code}")
            break

def main():
    conn = init_db()
    try:
        for region_id in range(REGION_START, REGION_END + 1):
            if region_id == 24 or region_id == 26: continue
            print(f"Fetching data for region {region_id}...")
            fetch_region_data(conn, region_id)
    finally:
        conn.close()
        print("Database connection closed.")

if __name__ == "__main__":
    main()
