import sqlite3
from collections import defaultdict

from loadConfig import load_config
from FindNumJumpsAnywhere_IDs import find_jumps_between_system_ids

def update_jumps_from_home():
    config = load_config()
    home_system_name = config["highsecManuSystem"]
    
    with sqlite3.connect(config["dbPath"]) as conn:
        cursor = conn.cursor()

        # Find the systemID of the home system
        cursor.execute("SELECT solarSystemID FROM SolarSystems WHERE solarSystemName = ?", (home_system_name,))
        result = cursor.fetchone()
        if not result:
            raise ValueError(f"Home system '{home_system_name}' not found in SolarSystems table.")
        home_system_id = result[0]

        # Get all unique solarSystemIDs from MarketOrdersAll
        cursor.execute("SELECT DISTINCT solarSystemID FROM Distances")
        unique_system_ids = [row[0] for row in cursor.fetchall()]

        # Cache for systemID to jumps
        system_jumps = {}
        contiguous_highsec = {}

        for system_id in unique_system_ids:
            if system_id is None:
                continue
            try:
                jumps = find_jumps_between_system_ids(config["dbPath"], home_system_id, system_id, 0.45) #highsec
                if jumps is not None:
                    contiguous_highsec[system_id] = 1
                if jumps is None:
                    jumps = find_jumps_between_system_ids(config["dbPath"], home_system_id, system_id, -2.0)
                    contiguous_highsec[system_id] = 0
            except Exception as e:
                print(f"Error finding jumps between {home_system_id} and {system_id}: {e}")
                jumps = -1  # Use -1 to indicate error/unreachable

            system_jumps[system_id] = jumps
            #print(jumps)

        # Update all records with the appropriate distanceHome
        for system_id, jumps in system_jumps.items():
            cursor.execute("UPDATE Distances SET distanceHome = ? WHERE solarSystemID = ?", (jumps, system_id))

        for system_id, highsec in contiguous_highsec.items():
            cursor.execute("UPDATE Distances SET contiguousHighsec = ? WHERE solarSystemID = ?", (highsec, system_id))
        conn.commit()
        print("Update complete.")

if __name__ == "__main__":
    update_jumps_from_home()
