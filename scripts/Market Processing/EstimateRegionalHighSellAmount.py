import sqlite3
from collections import defaultdict

def estimate_sell_split(avg, low, high, total_volume):
    if high == low:
        return {
            "fraction_high": 0.0,
            "volume_high": 0,
            "volume_low": total_volume,
        }

    x = (avg - low) / (high - low)
    x = max(0.0, min(1.0, x))

    volume_high = total_volume * x
    volume_low = total_volume - volume_high

    return {
        "fraction_high": x,
        "volume_high": volume_high,
        "volume_low": volume_low,
    }

def main(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Fetch all regionIDs from Regions table
    cursor.execute("SELECT regionID FROM Regions")
    regions = [row[0] for row in cursor.fetchall()]

    for region_id in regions:
        print(region_id)
        # Get all unique typeIDs in OrderHistory for this region
        cursor.execute("""
            SELECT DISTINCT typeID 
            FROM OrderHistory 
            WHERE regionID = ?
        """, (region_id,))
        type_ids = [row[0] for row in cursor.fetchall()]

        count = 0
        for type_id in type_ids:
            count += 1
            if(count > 1000):
                print(1000)
                count = 0
            # Get the 14 most recent rows by date
            cursor.execute("""
                SELECT average, lowest, highest, volume 
                FROM OrderHistory 
                WHERE regionID = ? AND typeID = ?
                ORDER BY date DESC
                LIMIT 14
            """, (region_id, type_id))
            rows = cursor.fetchall()

            if len(rows) < 1:
                continue

            total_fraction = 0.0
            total_volume_high = 0
            total_volume_low = 0
            valid_count = 0

            for avg, low, high, vol in rows:
                result = estimate_sell_split(avg, low, high, vol)
                total_fraction += result["fraction_high"]
                total_volume_high += result["volume_high"]
                total_volume_low += result["volume_low"]
                valid_count += 1

            if valid_count == 0:
                continue

            avg_fraction = total_fraction / valid_count
            avg_volume_high = round(total_volume_high / valid_count)
            avg_volume_low = round(total_volume_low / valid_count)

            # Insert into EstimatedRegionalHighSellAmount
            cursor.execute("""
                INSERT INTO EstimatedRegionalHighSellAmount (
                    typeID, regionID, fraction_high, volume_high, volume_low
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                type_id,
                region_id,
                avg_fraction,
                avg_volume_high,
                avg_volume_low
            ))

    conn.commit()
    conn.close()

if __name__ == "__main__":
    main("../../CostAnalysis.db")
