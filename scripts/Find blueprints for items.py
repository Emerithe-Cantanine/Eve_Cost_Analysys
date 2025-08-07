import sqlite3

# Connect to the SQLite database
conn = sqlite3.connect('F:\Eve Cost Analysis\CostAnalysis.db')
cursor = conn.cursor()

# Select all typeIDs from Items
cursor.execute("SELECT typeID FROM Items")
item_type_ids = cursor.fetchall()

# Loop through each typeID
for (type_id,) in item_type_ids:
    # Check for match in BlueprintActivityProductionAmounts
    cursor.execute("""
        SELECT typeID, quantity
        FROM BlueprintActivityProductionAmounts
        WHERE productTypeID = ?
    """, (type_id,))
    match = cursor.fetchone()

    if match:
        blueprint_id, portion_size = match
        # Update Items table
        cursor.execute("""
            UPDATE Items
            SET blueprintID = ?, portionSize = ?
            WHERE typeID = ?
        """, (blueprint_id, portion_size, type_id))

# Commit changes and close the connection
conn.commit()
conn.close()

print("Items table updated successfully.")
