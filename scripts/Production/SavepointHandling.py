import sqlite3
import uuid

def pretend_buy_materials(conn, type_id, amount_needed):
    cursor = conn.cursor()
    savepoints = []
    remaining = amount_needed

    # Find cheapest sell orders
    cursor.execute("""
        SELECT orderID, volume, price
        FROM MarketOrdersAll
        WHERE typeID = ? AND buy_true_sell_false = 0
        ORDER BY price ASC
    """, (type_id,))
    
    rows = cursor.fetchall()

    for orderID, volume, price in rows:
        if remaining <= 0:
            break

        used_amount = min(remaining, volume)
        savepoint_name = f"sp_{uuid.uuid4().hex[:8]}"
        savepoints.append(savepoint_name)

        # Create savepoint
        cursor.execute(f"SAVEPOINT {savepoint_name}")

        # Update order's volume (simulate buying)
        cursor.execute("""
            UPDATE MarketOrdersAll
            SET volume = volume - ?
            WHERE orderID = ?
        """, (used_amount, orderID))

        remaining -= used_amount

    if remaining > 0:
        print(f"Warning: Could not fulfill entire order. Short by {remaining} units.")

    return savepoints

def rollback_savepoints(conn, savepoints):
    cursor = conn.cursor()
    # Rollback in reverse order
    for sp_name in reversed(savepoints):
        cursor.execute(f"ROLLBACK TO {sp_name}")
        cursor.execute(f"RELEASE {sp_name}")
