import requests
import sqlite3

# SQLite DB file
db_path = r"../../CostAnalysis.db"

# ESI API endpoint
url = "https://esi.evetech.net/latest/industry/systems/?datasource=tranquility"

# Map ESI activity names to DB column names
activity_map = {
    "manufacturing": "manufacturing",
    "researching_material_efficiency": "me",
    "researching_time_efficiency": "te",
    "copying": "copying",
    "invention": "invention",
    "reaction": "reaction"
}

try:
    # Fetch data from the API
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()

    # Connect to SQLite
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create the table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS SystemCostIndexes (
            manufacturing REAL,
            me REAL,
            te REAL,
            copying REAL,
            invention REAL,
            reaction REAL,
            solarSystemID INTEGER PRIMARY KEY
        )
    """)

    # Clear existing data
    cursor.execute("DELETE FROM SystemCostIndexes")

    # Insert data
    for system in data:
        cost_indices = {activity: 0.0 for activity in activity_map.values()}
        solar_system_id = system["solar_system_id"]

        for entry in system["cost_indices"]:
            activity = entry["activity"]
            if activity in activity_map:
                db_column = activity_map[activity]
                cost_indices[db_column] = entry["cost_index"]

        query = """
            INSERT INTO SystemCostIndexes (
                manufacturing, me, te, copying, invention, reaction, solarSystemID
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        values = (
            cost_indices["manufacturing"],
            cost_indices["me"],
            cost_indices["te"],
            cost_indices["copying"],
            cost_indices["invention"],
            cost_indices["reaction"],
            solar_system_id
        )

        cursor.execute(query, values)

    conn.commit()
    print("Data successfully inserted into SystemCostIndexes in CostAnalysis.db.")

except requests.RequestException as e:
    print(f"API request failed: {e}")
except sqlite3.Error as e:
    print(f"SQLite error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
finally:
    if 'cursor' in locals():
        cursor.close()
    if 'conn' in locals():
        conn.close()
