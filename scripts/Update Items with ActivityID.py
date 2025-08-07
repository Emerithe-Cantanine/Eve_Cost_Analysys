import sqlite3

# Path to your SQLite database
db_path = r"F:\Eve Cost Analysis\CostAnalysis.db"

def update_items_with_activity_ids(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Fetch all typeIDs from Items
        cursor.execute("SELECT typeID FROM Items")
        item_ids = cursor.fetchall()

        for (type_id,) in item_ids:
            # Find matching productTypeID in BlueprintActivityProductionAmounts
            cursor.execute("""
                SELECT activityID FROM BlueprintActivityProductionAmounts
                WHERE productTypeID = ?
            """, (type_id,))
            result = cursor.fetchone()

            # If a match is found, update Items.activityID
            if result:
                activity_id = result[0]
                cursor.execute("""
                    UPDATE Items
                    SET activityID = ?
                    WHERE typeID = ?
                """, (activity_id, type_id))

        conn.commit()
        print("Items table updated successfully.")

    except Exception as e:
        print("Error:", e)
    finally:
        conn.close()

update_items_with_activity_ids(db_path)
