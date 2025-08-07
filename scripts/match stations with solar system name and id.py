import sqlite3
import re

def extract_solar_system_name(station_name):
    # Match up to the first Roman numeral followed by either ' -' or ' ('
    match = re.match(r'^(.*?)(?=\s+[IVXLCDM]+\s+(?:-|\())', station_name)
    if match:
        return match.group(1).strip()
    return None

def update_station_system_info():
    conn = sqlite3.connect("F:\Eve Cost Analysis\CostAnalysis.db")
    cursor = conn.cursor()

    # Fetch all station IDs and names
    cursor.execute("SELECT stationID, stationName FROM Stations")
    stations = cursor.fetchall()

    for stationID, stationName in stations:
        solar_system_name = extract_solar_system_name(stationName)
        if not solar_system_name:
            continue

        # Search for matching solarSystemName in SolarSystems table
        cursor.execute("""
            SELECT solarSystemID, solarSystemName
            FROM SolarSystems
            WHERE solarSystemName = ?
        """, (solar_system_name,))
        result = cursor.fetchone()

        if result:
            solarSystemID, solarSystemName = result

            # Update the Stations table
            cursor.execute("""
                UPDATE Stations
                SET solarSystemName = ?, solarSystemID = ?
                WHERE stationID = ?
            """, (solarSystemName, solarSystemID, stationID))

    conn.commit()
    conn.close()
    print("Stations table updated with solar system info.")

if __name__ == "__main__":
    update_station_system_info()
