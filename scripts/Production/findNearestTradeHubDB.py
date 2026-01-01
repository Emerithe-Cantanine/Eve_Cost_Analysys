import sqlite3
from loadConfig import load_config

def run_query(db_path, query):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(query)
    results = cursor.fetchall()
    conn.commit()
    conn.close()

    return results

def find_nearest_tradeHub_based_on_region(db_path, regionID):

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    query = f'''
    SELECT  Distances.distanceAmarr, Distances.distanceJita, Distances.distanceHek, Distances.distanceDodixie,
            Distances.solarSystemName
    FROM    Distances
            where regionID = {regionID};
            '''
    cursor.execute(query)
    solarSystems = cursor.fetchall()
    conn.close()

    amarr = jita = hek = dodixie = 0

    for systems in solarSystems:
        amarr += systems[0]
        jita += systems[1]
        hek += systems[2]
        dodixie += systems[3]

    hubs = [amarr, jita, hek, dodixie]
    hubs.sort()

    if hubs[0] == amarr:
        run_query(db_path, f"update Distances set nearestTradeHubName = 'Amarr' where regionID = {regionID}")
        return "Amarr"
    elif hubs[0] == jita:
        run_query(db_path, f"update Distances set nearestTradeHubName = 'Jita' where regionID = {regionID}")
        return "Jita"
    elif hubs[0] == hek:
        run_query(db_path, f"update Distances set nearestTradeHubName = 'Hek' where regionID = {regionID}")
        return "Hek"
    elif hubs[0] == dodixie:
        run_query(db_path, f"update Distances set nearestTradeHubName = 'Dodixie' where regionID = {regionID}")
        return "Dodixie"
    
config = load_config()
db_path = config["dbPath"]
solarSystemIDsAndRegionIDs = run_query(db_path, "select solarSystemID, regionID from Distances")

for solarSystemID, regionID in solarSystemIDsAndRegionIDs:
    find_nearest_tradeHub_based_on_region(db_path, regionID)