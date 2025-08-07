import sqlite3

def create_savepoint(cursor, savepoint_name, order_id):
    cursor.execute(f"SAVEPOINT {savepoint_name}")
    cursor.execute(
        "UPDATE MarketOrdersAll SET price = price + 1 WHERE orderID = ?", (order_id,)
    )
    print(f"{savepoint_name}: price incremented by 1")

def rollback_to_savepoint(cursor, savepoint_name):
    cursor.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
    cursor.execute(f"RELEASE SAVEPOINT {savepoint_name}")
    print(f"{savepoint_name}: rolled back")

def release_savepoint(cursor, savepoint_name):
    cursor.execute(f"RELEASE SAVEPOINT {savepoint_name}")
    print(f"{savepoint_name}: released")


def apply_nested_price_updates_with_rollback(db_path, order_id, nested_levels, rollback_levels):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Confirm the order exists
        cursor.execute("SELECT price FROM MarketOrdersAll WHERE orderID = ?", (order_id,))
        row = cursor.fetchone()
        if row is None:
            print(f"No order found with orderID = {order_id}")
            return

        print(f"Original price: {row[0]}")

        cursor.execute("BEGIN")
        savepoints = []

        # Create nested savepoints
        for i in range(nested_levels):
            sp_name = f"sp_{i}"
            create_savepoint(cursor, sp_name, order_id)
            savepoints.append(sp_name)

        # Rollback the last `rollback_levels` savepoints
        for i in range(nested_levels - 1, nested_levels - rollback_levels - 1, -1):
            rollback_to_savepoint(cursor, savepoints[i])

        # Release the remaining savepoints
        for i in range(nested_levels - rollback_levels):
            release_savepoint(cursor, savepoints[i])

        conn.commit()

        # Display final price
        cursor.execute("SELECT price FROM MarketOrdersAll WHERE orderID = ?", (order_id,))
        updated_price = cursor.fetchone()[0]
        print(f"Final updated price: {updated_price}")

    except Exception as e:
        print("An error occurred:", e)
        conn.rollback()
    finally:
        conn.close()


# Example usage
apply_nested_price_updates_with_rollback(
    db_path="CostAnalysis",
    order_id=911190994,
    nested_levels=5,
    rollback_levels=2
)
