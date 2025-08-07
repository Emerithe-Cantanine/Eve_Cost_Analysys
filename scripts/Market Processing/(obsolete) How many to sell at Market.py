import sqlite3
from datetime import datetime

# Path to your database
DB_PATH = "../../CostAnalysis.db"

# Trade hub system IDs and region IDs
TRADE_HUB_SYSTEMS = {30000142, 30002053, 30002187, 30002510, 30002659}
TRADE_HUB_REGIONS = {10000002, 10000042, 10000043, 10000030, 10000032}

def estimate_sell_split(avg, low, high, total_volume):
    """
    Estimate the fraction of trades at the high vs. low price using a 2-price model.
    """
    if high == low:
        return {
            "fraction_high": 0.0,
            "volume_high": 0,
            "volume_low": total_volume,
            "note": "All trades occurred at the same price."
        }

    x = (avg - low) / (high - low)  # fraction at high
    x = max(0.0, min(1.0, x))       # clamp between 0 and 1

    volume_high = total_volume * x
    volume_low = total_volume - volume_high

    return {
        "fraction_high": x,
        "volume_high": round(volume_high),
        "volume_low": round(volume_low),
        "note": f"Approx {x*100:.2f}% of trades at the high price."
    }

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get all solar systems not in a trade hub region or system
    cursor.execute("""
        SELECT solarSystemID, solarSystemName, regionID 
        FROM SolarSystems
        WHERE regionID NOT IN ({})
          AND solarSystemID NOT IN ({});
    """.format(
        ",".join(str(r) for r in TRADE_HUB_REGIONS),
        ",".join(str(s) for s in TRADE_HUB_SYSTEMS)
    ))
    systems = cursor.fetchall()

    results = []

    for solarSystemID, solarSystemName, regionID in systems:
        # Step 2: Compute estimate_sell_split for most recent 14 rows in OrderHistory for this system
        cursor.execute("""
            SELECT date, highest, volume
            FROM OrderHistory
            WHERE regionID = ?
            ORDER BY date DESC
            LIMIT 14;
        """, (regionID,))
        history_rows = cursor.fetchall()

        sell_estimate = estimate_sell_split(history_rows)

        if sell_estimate is None:
            continue

        # Step 3: Find system's lowest sell price for each typeID in MarketOrdersAll
        cursor.execute("""
            SELECT typeID, MIN(price)
            FROM MarketOrdersAll
            WHERE solarSystemID = ? AND buy_true_sell_false = 0
            GROUP BY typeID;
        """, (solarSystemID,))
        lowest_prices = cursor.fetchall()

        for typeID, lowest_price in lowest_prices:
            # Step 4: Ignore rows whose 'highest' < system sell price
            cursor.execute("""
                SELECT highest
                FROM OrderHistory
                WHERE typeID = ? AND regionID = ?
                ORDER BY date DESC
                LIMIT 14;
            """, (typeID, regionID))
            highs = [row[0] for row in cursor.fetchall() if row[0] >= lowest_price]

            if not highs:
                continue

            # Step 5: Find the average of the remaining rows
            avg_remaining = sum(highs) / len(highs)

            results.append({
                "systemID": solarSystemID,
                "systemName": solarSystemName,
                "regionID": regionID,
                "typeID": typeID,
                "sell_estimate": sell_estimate,
                "lowest_sell_price": lowest_price,
                "average_remaining_highs": avg_remaining
            })

    conn.close()

    # Print results
    for r in results:
        print(f"System {r['systemName']} ({r['systemID']}), Type {r['typeID']}:")
        print(f"  Sell estimate: {r['sell_estimate']:.2f}")
        print(f"  Lowest sell price: {r['lowest_sell_price']:.2f}")
        print(f"  Avg remaining highs: {r['average_remaining_highs']:.2f}")
        print()

if __name__ == "__main__":
    main()
