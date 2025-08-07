import sqlite3

def get_material_requirements(type_id, activity_id, db_path=r"../../CostAnalysis.db"):
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
    cursor.execute(query, (type_id, activity_id))

    # Fetch all results
    results = cursor.fetchall()

    # Close connection
    conn.close()

    # Display or return results
    if results:
        return results
        print(f"Material requirements for typeID {type_id} and activityID {activity_id}:")
        for material_id, total_qty in results:
            print(f"  materialTypeID: {material_id}, total quantity: {total_qty}")
    else:
        return None
        print(f"No material requirements found for typeID {type_id} and activityID {activity_id}.")

# Example usage:
if __name__ == "__main__":
    type_id = 81922      # Replace with the desired typeID
    activity_id = 1      # Replace with the desired activityID (e.g., 1 = manufacturing)
    get_material_requirements(type_id, activity_id)
