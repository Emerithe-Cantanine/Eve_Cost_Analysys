import yaml
import sqlite3
from loadConfig import load_config
from get_static_data_folder import get_folder_name
folderName = get_folder_name()

global config
config = load_config()
db_path = config["dbPath"]


def convert_tuple_to_list(_tuples):
    _list = list()
    for _tuple in _tuples:
        _list.append(list(_tuple))
    
    return _list

def run_query(db_path, query):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(query)
    results = cursor.fetchall()
    conn.commit()
    conn.close()

    return results

def run_query_parameterized(db_path, query, parameters): #parameters has to be a dictionary (tuple)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(query, parameters)
    results = cursor.fetchall()
    conn.commit()
    conn.close()

    return results

# this is tested and works
def import_blueprints(db_path):
    run_query(db_path, "delete from BlueprintActivityMaterialRequirements")
    run_query(db_path, "delete from BlueprintActivityProductionAmounts")
    run_query(db_path, "delete from BlueprintActivityTimes")
    run_query(db_path, "delete from MaxProductionLimits")
    with open(f'{folderName}\\blueprints.yaml', 'r') as file:
        db_path = config["dbPath"]
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        data = yaml.safe_load(file)
        for d in data:
            for meta in list(data[d].keys()):
                if meta == "maxProductionLimit":
                    mpl = data[d]["maxProductionLimit"]
                    run_query(db_path, f'''
                              insert into MaxProductionLimits (typeID, maxProductionLimit)
                              values ({d}, {mpl})
                              ''')
                if meta == "activities":
                    for activity in list(data[d]["activities"].keys()):
                        if activity == "manufacturing":
                            activityID = 1
                            for something in data[d]["activities"]["manufacturing"].keys():
                                if something == "materials":
                                    for material in list(data[d]["activities"]["manufacturing"]["materials"]):
                                        materialTypeID = material["typeID"]
                                        quantity = material["quantity"]
                                        run_query(db_path, f'''
                                                insert into BlueprintActivityMaterialRequirements (typeID, activityID, materialTypeID, quantity)
                                                values ({d}, {activityID}, {materialTypeID}, {quantity})
                                                ''')
                                if something == "products":
                                    for product in list(data[d]["activities"]["manufacturing"]["products"]):
                                        productTypeID = product["typeID"]
                                        quantity = product["quantity"]
                                        run_query(db_path, f'''
                                                insert into BlueprintActivityProductionAmounts (typeID, activityID, productTypeID, quantity)
                                                values ({d}, {activityID}, {productTypeID}, {quantity})
                                                ''')
                                if something == "time":
                                    time = data[d]["activities"]["manufacturing"]["time"]
                                    run_query(db_path, f'''
                                                insert into BlueprintActivityTimes (typeID, activityID, time)
                                                values ({d}, {activityID}, {time})
                                                ''')
                        elif activity == "reaction":
                            activityID = 11
                            for something in data[d]["activities"]["reaction"].keys():
                                if something == "materials":
                                    for material in list(data[d]["activities"]["reaction"]["materials"]):
                                        materialTypeID = material["typeID"]
                                        quantity = material["quantity"]
                                        run_query(db_path, f'''
                                                insert into BlueprintActivityMaterialRequirements (typeID, activityID, materialTypeID, quantity)
                                                values ({d}, {activityID}, {materialTypeID}, {quantity})
                                                ''')
                                if something == "products":
                                    for product in list(data[d]["activities"]["reaction"]["products"]):
                                        productTypeID = product["typeID"]
                                        quantity = product["quantity"]
                                        run_query(db_path, f'''
                                                insert into BlueprintActivityProductionAmounts (typeID, activityID, productTypeID, quantity)
                                                values ({d}, {activityID}, {productTypeID}, {quantity})
                                                ''')
                                if something == "time":
                                    time = data[d]["activities"]["reaction"]["time"]
                                    run_query(db_path, f'''
                                                insert into BlueprintActivityTimes (typeID, activityID, time)
                                                values ({d}, {activityID}, {time})
                                                ''')

def import_types(db_path):
    run_query(db_path, "delete from Items")
    with open(f'{folderName}\\types.yaml', 'r', encoding='utf-8') as file:
        db_path = config["dbPath"]
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        typeName = ""
        typeID = groupID = volume = marketGroupID = portionSize = capacity = -1
        
        data = yaml.safe_load(file)
        for d in data:
            if d < 18: continue
            typeID = d
            for meta in list(data[d].keys()):
                if meta == "name":
                    typeName = data[d]["name"]["en"]
                    if " SKIN" in typeName: # the space in front of SKIN only works for english and dutch
                        break
                    if "Spawner" in typeName:
                        break
                elif meta == "groupID":
                    groupID = data[d]["groupID"]
                elif meta == "volume":
                    volume = data[d]["volume"]
                elif meta == "marketGroupID":
                    marketGroupID = data[d]["marketGroupID"]
                elif meta == "portionSize":
                    portionSize = data[d]["portionSize"]
                elif meta == "capacity":
                    capacity = data[d]["capacity"]
            
            parameters = (typeID, groupID, typeName, volume, capacity, portionSize, marketGroupID)
            run_query_parameterized(db_path, f'''
                        insert into Items (typeID, groupID, typeName, volume, capacity, portionSize, marketGroupID)
                        values (?, ?, ?, ?, ?, ?, ?)
                        ''', parameters)

def import_template():
    with open(f'{folderName}\\blueprints.yaml', 'r') as file:
        db_path = config["dbPath"]
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        data = yaml.safe_load(file)
        for d in data:
            #blank = data[d]["other stuff"]
            print(d)

import_blueprints(db_path)
import_types(db_path)