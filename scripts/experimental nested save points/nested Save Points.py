import sqlite3

def apply_nested_price_updates(db_path, order_id, nested_levels):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if order exists
        cursor.execute("SELECT price FROM MarketOrdersAll WHERE orderID = ?", (order_id,))
        row = cursor.fetchone()
        if row is None:
            print(f"No order found with orderID = {order_id}")
            return

        print(f"Original price: {row[0]}")

        # Begin transaction
        cursor.execute("BEGIN")

        # Dynamically create nested savepoints
        for i in range(nested_levels):
            savepoint_name = f"sp_{i}"
            cursor.execute(f"SAVEPOINT {savepoint_name}")
            cursor.execute(
                "UPDATE MarketOrdersAll SET price = price + 1 WHERE orderID = ?", (order_id,)
            )
            print(f"Savepoint {savepoint_name}: price incremented by 1")

        # Release all savepoints
        for i in reversed(range(nested_levels)):
            savepoint_name = f"sp_{i}"
            cursor.execute(f"RELEASE SAVEPOINT {savepoint_name}")

        conn.commit()

        # Show updated price
        cursor.execute("SELECT price FROM MarketOrdersAll WHERE orderID = ?", (order_id,))
        updated_price = cursor.fetchone()[0]
        print(f"Final updated price: {updated_price}")

    except Exception as e:
        print("An error occurred:", e)
        conn.rollback()

    finally:
        conn.close()


# Example usage
apply_nested_price_updates("F:\Eve Cost Analysis\CostAnalysis.db", order_id=911190994, nested_levels=5)
