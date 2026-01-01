import sqlite3

def get_items():
    db_path = "../../CostAnalysis.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    query = '''
    SELECT typeID, blueprintID, activityID, layer
    from Items
    where blueprintID is not null;
    '''

    cursor.execute(query)
    result = cursor.fetchall()
    conn.close()
    return result

def get_item(typeID):
    db_path = "../../CostAnalysis.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    query = '''
    select typeID, blueprintID, activityID, layer
    from Items
    where typeID = ?
    '''

    cursor.execute(query, (typeID,))
    result = cursor.fetchall()
    conn.close()
    return result
    
def get_blueprint_materials(blueprintID, activityID):
    db_path = "../../CostAnalysis.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    #quantity isn't needed, but I might reuse this function somewhere else
    query = '''
    select materialTypeID, quantity 
    from BlueprintActivityMaterialRequirements
    where typeID = ? and activityID = ?
    '''

    cursor.execute(query, (blueprintID, activityID,))
    result = cursor.fetchall()
    conn.close()
    return result

def find_layers(blueprintID, activityID):
    current_count = 0 # the current node count
    new_count = 0   # the new number from lower nodes.
    materials = get_blueprint_materials(blueprintID, activityID)
    for materialTypeID, quantity in materials:
        item = get_item(materialTypeID)
        if(not item):
            continue
        if(item[0][1] == blueprintID):
            return - 1
        if(item[0][1] is None):   # if the item has no blueprint and is thus a layer-0 item
            continue
        new_count = find_layers(item[0][1], item[0][2]) #tuples are apparently treated like 2D arrays
        if(new_count > current_count):
            current_count = new_count
    
    current_count += 1
    return current_count

def set_layer(blueprintID, layer_count):
    db_path = "../../CostAnalysis.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    query = '''
    update Items
    set layer = ?
    where blueprintID = ?
    '''

    cursor.execute(query, (layer_count, blueprintID,))
    conn.commit()
    conn.close()
    return cursor.rowcount

def mainloop():
    items = get_items()

    for typeID, blueprintID, activityID, layer in items:
        count = find_layers(blueprintID, activityID)
        set_layer(blueprintID, count)

mainloop()