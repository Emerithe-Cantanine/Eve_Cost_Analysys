import sqlite3
from datetime import datetime

def get_avg_highest_price(db_path, type_id, region_id, num_rows=14):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Query the 14 most recent rows for the given typeID
    cursor.execute("""
        SELECT date, highest, volume
        FROM OrderHistory
        WHERE typeID = ? AND regionID = ?
        ORDER BY date DESC
        LIMIT ?
    """, (type_id, region_id, num_rows))
    
    rows = cursor.fetchall()
    conn.close()

    if not rows: # or len(rows) < num_rows:
        print(f"No row found for typeID {type_id} in region {region_id}.")
        # print(f"Not enough rows found for typeID {type_id} in region {region_id}. Found {len(rows)} rows.")
        return None

    # Compute weighted average price (highest * volume, sum, then divide by row count)
    total_weighted = sum(highest * volume for (_, highest, volume) in rows)
    avg_highest_price = total_weighted / num_rows

    # Compute average volume
    avg_volume = sum(volume for (_, _, volume) in rows) / num_rows

    # Get date range
    dates = [datetime.fromisoformat(date) for (date, _, _) in rows]
    date_range = (min(dates).date(), max(dates).date())

    return {
        "avg_highest_price": avg_highest_price,
        "avg_volume": avg_volume,
        "date_range": date_range
    }


# Example usage:
if __name__ == "__main__":
    db_path = "../../CostAnalysis.db"
    type_id = 203  # Example: Tritanium
    region_id = 10000002 # jita
    result = get_avg_highest_price(db_path, type_id, region_id)
    
    if result:
        print(f"Average Highest Price: {result['avg_highest_price']:.2f}")
        print(f"Average Volume: {result['avg_volume']:.2f}")
        print(f"Date Range: {result['date_range'][0]} to {result['date_range'][1]}")
