import sqlite3
from collections import defaultdict

from loadConfig import load_config
from FindNumJumpsAnywhere_IDs import find_jumps_between_system_ids

def update_jumps_from_home():
    config = load_config()
    hek = "Hek"
    
    with sqlite3.connect(config["dbPath"]) as conn:
        cursor = conn.cursor()

        # Find the systemID of Jita
        cursor.execute("SELECT solarSystemID FROM SolarSystems WHERE solarSystemName = ?", (hek,))
        result = cursor.fetchone()
        if not result:
            raise ValueError(f"Trade hub '{hek}' not found in SolarSystems table.")
        hekID = result[0]

        # Get all unique solarSystemIDs from MarketOrdersAll
        cursor.execute("SELECT DISTINCT solarSystemID FROM MarketOrdersAll")
        unique_system_ids = [row[0] for row in cursor.fetchall()]

        # Cache for systemID to jumps
        system_jumps = {}

        for system_id in unique_system_ids:
            if system_id is None:
                continue
            try:
                jumps = find_jumps_between_system_ids(config["dbPath"], hekID, system_id, 0.45) #highsec
                if jumps is None:
                    jumps = find_jumps_between_system_ids(config["dbPath"], hekID, system_id, -2.0)
            except Exception as e:
                print(f"Error finding jumps between {hekID} and {system_id}: {e}")
                jumps = -1  # Use -1 to indicate error/unreachable

            system_jumps[system_id] = jumps
            #print(jumps)

        # Update all records with the appropriate distanceHek
        for system_id, jumps in system_jumps.items():
            cursor.execute("UPDATE MarketOrdersAll SET distanceHek = ? WHERE solarSystemID = ?", (jumps, system_id))

        conn.commit()
        print("Update complete.")

if __name__ == "__main__":
    update_jumps_from_home()
