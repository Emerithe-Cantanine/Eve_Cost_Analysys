import sqlite3

# typeID = blueprintID
def get_material_requirements(blueprintID, activityID, db_path="../../CostAnalysis.db"):
    # Connect to the SQLite database
    conn = sqlite3.connect(r"../../CostAnalysis.db")
    cursor = conn.cursor()

    # Prepare and execute the SQL query
    query = '''
        SELECT materialTypeID, SUM(quantity) as total_quantity
        FROM BlueprintActivityMaterialRequirements
        WHERE typeID = ? AND activityID = ?
        GROUP BY materialTypeID
    '''
    cursor.execute(query, (blueprintID, activityID))

    # Fetch all results
    results = cursor.fetchall()

    # Close connection
    conn.close()

    # Display or return results
    if results:
        return results
        print(f"Material requirements for typeID {blueprintID} and activityID {activityID}:")
        for material_id, total_qty in results:
            print(f"  materialTypeID: {material_id}, total quantity: {total_qty}")
    else:
        return None
        print(f"No material requirements found for typeID {blueprintID} and activityID {activityID}.")

# Example usage:
if __name__ == "__main__":
    blueprintID = 81922      # Replace with the desired typeID
    activityID = 1      # Replace with the desired activityID (e.g., 1 = manufacturing)
    get_material_requirements(blueprintID, activityID)
