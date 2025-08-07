import sqlite3
from Aggregate_Blueprint_Materials import get_material_requirements

def find_items_with_blueprints_and_call_materials(db_path):
    # Connect to the SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Query to select rows where blueprintID is not NULL
    query = '''
    SELECT typeID, blueprintID FROM Items
    WHERE blueprintID IS NOT NULL;
    '''

    cursor.execute(query)
    results = cursor.fetchall()

    # Call get_material_requirements for each entry
    for type_id, blueprint_id in results:
        print(f"Getting materials for typeID {type_id} using blueprintID {blueprint_id}")
        materials = get_material_requirements(blueprint_id, activity_id=1, db_path=r"../../CostAnalysis.db")
        print(materials)  # You can change this to log to a file or structure as needed

    conn.close()

# Example usage
if __name__ == "__main__":
    find_items_with_blueprints_and_call_materials(r"../../CostAnalysis.db")
