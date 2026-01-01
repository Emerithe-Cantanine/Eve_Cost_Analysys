import sqlite3
import pickle
from Aggregate_Blueprint_Materials import get_material_requirements
from loadConfig import load_config
from Reports import createFile, appendFile, newLine, createDirectory

global config
config = load_config()

global itemReport

global orderNum
orderNum = 0

global savepointOrders
savepointOrders = list()

def printConfig():
    global config 
    config = load_config()
    print
    for key, value in config.items():
        print(f"{key}: {value}")
    return config

# step 1
def get_typeIDs_blueprintIDs_and_activityIDs_from_Items_table(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    query = '''
    SELECT typeID, blueprintID, activityID FROM Items 
    WHERE blueprintID IS NOT NULL;
    '''

    cursor.execute(query)
    results = cursor.fetchall()
    conn.close()
    return results

# step 2
def get_volume_high_from_EstimatedRegionalHighSellAmount_table(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    query = '''
    SELECT regionID, typeID, volume_high from EstimatedRegionalHighSellAmount
    WHERE volume_high > 0;
    '''

    cursor.execute(query)
    results = cursor.fetchall()
    conn.close()
    return results

# step 1 and 2
def get_typeID_blueprintID_activityID_regionID_volumehigh(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    query = '''
    select a.typeID, a.blueprintID, a.activityID, b.typeID, b.regionID, b.volume_high
    from Items a, EstimatedRegionalHighSellAmount b
    where a.typeID = b.typeID and b.volume_high > 0
    order by a.typeID;
    '''

    cursor.execute(query)
    results = cursor.fetchall()
    conn.close()
    return results

# It just queries the database for portion size and returns it. It doesn't adjust anything.
def adjust_volumehigh_for_portionSize(db_path, typeID):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    query = f'''
    select portionSize
    from Items
    where Items.typeID = {typeID};
    '''

    cursor.execute(query)
    result = cursor.fetchone()[0]
    conn.close()

    return result

def get_itemName(db_path, typeID):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    query = '''
    SELECT typeName FROM Items 
    WHERE typeID = ?;
    '''

    cursor.execute(query, (typeID,))
    results = cursor.fetchone()
    conn.close()
    return results[0]

def get_regionName(db_path, regionID):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    query = '''
    SELECT RegionName FROM Regions
    WHERE RegionID = ?;
    '''

    cursor.execute(query, (regionID,))
    results = cursor.fetchone()
    conn.close()
    return results[0]

def get_solarSystemID_from_solarSystemName(db_path, solarSystemName):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    query = f'''
    select solarSystemID
    from SolarSystems
    where solarSystemName = '{solarSystemName}';
    '''

    cursor.execute(query)
    solarSystemID = cursor.fetchone()[0]
    conn.close()

    return solarSystemID

def get_typeID_layer_from_Items(db_path, typeID):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    query = f'''
    select layer
    from Items
    where typeID = {typeID};
    '''

    cursor.execute(query)
    layer = cursor.fetchone()[0]
    return layer

# Finds the components of a top level item (typeID) all the way down to its lowest sub-component
def find_components(db_path, typeID):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    query = '''
    SELECT typeID, blueprintID, activityID, layer, typeName FROM Items 
    WHERE typeID = ?;
    '''

    cursor.execute(query, (typeID,))
    item = cursor.fetchall()
    conn.close()

    itemTypeID = item[0][0]
    itemBlueprintID = item[0][1]
    itemActivityID = item[0][2]
    layer = item[0][3]
    typeName = item[0][4]

    if itemBlueprintID is None:
        return
    materials = get_material_requirements(itemBlueprintID, itemActivityID, db_path)

    if materials is None:
        return
    
    components = list()

    for material in materials:
        materialTypeID = material[0]
        materialQuantity = material[1]
        subComponents = find_components(db_path, materialTypeID)

        components.append(materialTypeID)   # 0
        components.append(materialQuantity) # 1
        components.append(subComponents)    # 2
        components.append("sell price")      # 3
        components.append("build price")    # 4
    
    return components

# I should probably just add this as a column to the Distances table instead of recalculating it every time.
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
        return "Jita"
    elif hubs[0] == hek:
        return "Hek"
    elif hubs[0] == dodixie:
        return "Dodixie"

def find_manufacturing_systems(db_path, regionID):
    if config["buildAnywhereCheapest"] == False:
        return {"highsecManuSystem": config["highsecManuSystem"], "lowsecManuSystem": config["lowsecManuSystem"]}
    
    # This assumes the user wants to find the system with the cheapest cost index
    # closest to their prefered trade hub.
    preferedTradeHub = config["preferedTradeHub"]

    # if no prefered trade hub, then default to the closest trade hub to the order history.
    if preferedTradeHub == "None":
        preferedTradeHub = find_nearest_tradeHub_based_on_region(db_path, regionID)

    # This setting tells the program to find the cheapest system within x number of jumps from the trade hub.
    # This probably won't be practical for lowsec, so I'll just have it find the nearest one beyond x jumps.
    # I decided to get rid of this option because it would be annoying to implement.
    # I left it in the config file in case I change my mind in the future.
    # buildAnywhereHubDistance = config["buildAnywhereHubDistance"]

    # This setting allows the user to decide if they want to allow manufacturing, not just reactions, in lowsec.
    manufacturingInHighsecOnly = config["manufacturingInHighsecOnly"]
    security = ""
    if manufacturingInHighsecOnly:
        security = "security >= 0.45"
    else:
        security = "security > -1"

    blackListedSystems = config["blackListedSystems"]

    if blackListedSystems:
        for solarSystem in blackListedSystems:
            security += f" AND solarSystems.solarSystemName IS NOT '{solarSystem}'"

    # This modifies the sql query to prioritize index, distance, and security in any order.
    priorityOrderForManuSystems = config["priorityOrderForManuSystems"]
    orderBy = ""
    i = 0
    for priority in priorityOrderForManuSystems:
        if priority == "index":
            orderBy += "manufacturing ASC"
        elif priority == "distance":
            orderBy += f"distance{preferedTradeHub} ASC"
        elif priority == "security":
            orderBy += "security DESC"
        i += 1
        if i <= 2:
            orderBy += ", "

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # since I don't know sql very well, this took about 45 minutes to figure out. That includes dicking around.
    # this query does a join on 3 tables and tells me the prefered system to manufacture items in.
    query = f'''
    SELECT  Distances.solarSystemID, Distances.solarSystemName, Distances.contiguousHighsec,
            Distances.distance{preferedTradeHub},
            SystemCostIndexes.manufacturing, 
            SolarSystems.security
    FROM    Distances
    JOIN    SystemCostIndexes ON Distances.solarSystemID = SystemCostIndexes.solarSystemID
    JOIN    SolarSystems ON SystemCostIndexes.solarSystemID = solarSystems.solarSystemID
    WHERE   {security}
    ORDER BY {orderBy}
    LIMIT   1;
            '''
    
    cursor.execute(query)
    manuSystem = cursor.fetchone()[1] # solarSystemName. [0] is solarSystemID
    
    security = "security <= 0.45"

    if blackListedSystems:
        for solarSystem in blackListedSystems:
            security += f" AND solarSystems.solarSystemName IS NOT '{solarSystem}'"

    # This modifies the sql query to prioritize index, distance, and security in any order.
    priorityOrderForReacSystems = config["priorityOrderForReacSystems"]
    orderBy = ""
    i = 0
    for priority in priorityOrderForReacSystems:
        if priority == "index":
            orderBy += "manufacturing ASC"
        elif priority == "distance":
            orderBy += f"distance{preferedTradeHub} ASC"
        elif priority == "security":
            orderBy += "security DESC"
        i += 1
        if i <= 2:
            orderBy += ", "

    # this query does a join on 3 tables and tells me the prefered system to do reactions in.
    query = f'''
    SELECT  Distances.solarSystemID, Distances.solarSystemName, Distances.contiguousHighsec,
            Distances.distance{preferedTradeHub},
            SystemCostIndexes.reaction, 
            SolarSystems.security
    FROM    Distances
    JOIN    SystemCostIndexes ON Distances.solarSystemID = SystemCostIndexes.solarSystemID
    JOIN    SolarSystems ON SystemCostIndexes.solarSystemID = solarSystems.solarSystemID
    WHERE   {security}
    ORDER BY {orderBy}
    LIMIT   1;
            '''
    
    cursor.execute(query)
    reacSystem = cursor.fetchone()[1] # solarSystemName. [0] is solarSystemID
    conn.close()

    return {"highsecManuSystem": manuSystem, "lowsecManuSystem": reacSystem, "tradeHub": preferedTradeHub}

# components is a list where 1 item is represented by 5 elements.
# In order, those elements are: typeID, quantity, a list of sub-components, its sell price, and its build price.
# systems is a dictionary that contains, in order: highsec manu system, lowsec reaction/manu system, tradehub.
# multiplier is the number of jobs to produce the top level item
def find_item_sell_prices(db_path, components, systems, multiplier):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    tradeHub = systems["tradeHub"]
    solarSystemID = get_solarSystemID_from_solarSystemName(db_path, tradeHub)

    for x in range(0, len(components), 5):
        if components[x+2] is not None:
            find_item_sell_prices(db_path, components[x+2], systems, multiplier)
        
        query = f'''
        select price
        from MarketOrdersAll
        where typeID = {components[x]} and solarSystemID = {solarSystemID} and buy_true_sell_false = 0
        order by price ASC
        limit 1;
        '''

        cursor.execute(query)
        result = cursor.fetchone()[0]
        components[x+3] = result
    conn.close()

def run_query(db_path, query):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(query)
    results = cursor.fetchall()
    conn.commit()
    conn.close()

    return results


# def start_transaction(db_path):
#     conn = sqlite3.connect(db_path)
#     cursor = conn.cursor()

#     query = "BEGIN TRANSACTION;"

#     cursor.execute(query)
#     conn.commit()
#     conn.close()

# def rollback_transaction(db_path):
#     conn = sqlite3.connect(db_path)
#     cursor = conn.cursor()

#     query = "ROLLBACK;"

#     cursor.execute(query)
#     conn.commit()
#     conn.close()

# def start_savepoint(db_path, savepointName):
#     global orderSavepointNumber
#     global savepointOrders
#     conn = sqlite3.connect(db_path)
#     cursor = conn.cursor()

#     savepointName = f"{savepointName}_{orderSavepointNumber}"
#     query = f"SAVEPOINT {savepointName};"
#     orderSavepointNumber += 1
#     savepointOrders.append(savepointName)

#     cursor.execute(query)
#     conn.commit()
#     conn.close()

#     return savepointName

# def rollback_savepoint(db_path, savepointName):
#     global orderSavepointNumber
#     conn = sqlite3.connect(db_path)
#     cursor = conn.cursor()

#     run_query(db_path, "delete from Items where typeID = 88853;")

#     query = f"ROLLBACK TO {savepointName};"

#     split = savepointName.split('_')
#     length = len(split)
#     orderSavepointNumber = int(savepointName.split('_')[length - 1])

#     cursor.execute(query)
#     conn.commit()
#     conn.close()

# I can't get savepoints to work. I'll have to do something else to replicate their feature.
# def savepoint_test(db_path):
#     conn = sqlite3.connect(db_path)
#     cursor = conn.cursor()

#     # run_query(db_path, "begin transaction;")
#     run_query(db_path, "savepoint s1;")
#     run_query(db_path, "delete from Items where typeID = 88568;")
#     run_query(db_path, "savepoint s2;")
#     run_query(db_path, "delete from Items where typeID = 88377;")
#     run_query(db_path, "rollback to s2;")
#     run_query(db_path, "rollback;")
    
#     conn.commit()
#     conn.close()

def update_savepointOrders(typeID, volumeUsed):
    global orderNum
    savepointOrders.append(orderNum)
    savepointOrders.append(typeID)
    savepointOrders.append(volumeUsed)

# components is a list where 1 item is represented by 5 elements.
# In order, those elements are: typeID, quantity, a list of sub-components, its sell price, and its build price.
def copy_market_order(db_path, typeID, solarSystemID, volumeNeeded):
    global orderNum
    global savepointOrders
    cost = 0
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Another function handles this part
    # query = f'''
    # select typeID, volumeRemaining
    # from PurchaseOrders
    # where typeID = {typeID} and solarSystemID = {solarSystemID} and volumeRemaining > 0;
    # '''

    # get all sell orders of an item in a specific trade hub. Ignore this query. The new one is below it.
    query = f'''
    select typeID, volume, volumeRemaining, solarSystemID, orderID, stationID, buy_true_sell_false,
    contiguousHighsec, tradeHub, distanceAmarr, distanceJita, distanceHek, distanceDodixie
    from MarketOrdersAll
    where solarSystemID = {solarSystemID} and typeID = {typeID} and buy_true_sell_false = 0;
    '''

    query = f'''
    select *
    from MarketOrdersAll
    where solarSystemID = {solarSystemID} and typeID = {typeID} and buy_true_sell_false = 0
    order by price asc;
    '''
    
    cursor.execute(query)
    results = cursor.fetchall()

    # for each order, add it to the PurchaseOrders table. Then figure out if another order is needed or if enough has been purchased.
    for result in results:
        query = f'''
        insert into PurchaseOrders
        values ({result[0]}, {result[1]}, {result[2]}, {result[3]}, '{result[4]}', {result[5]}, 
        {result[6]}, {result[7]}, '{result[8]}', '{result[9]}', {result[10]}, {result[11]}, 
        '{result[12]}', '{result[13]}', {result[14]}, {result[15]}, {result[16]}, {result[17]}, {orderNum});
        '''

        price = result[5]

        # old, but keeping it in case it comes in handy for some reason.
        # '''
        # set typeID = {result[0]}, volume = {result[1]}, volumeRemaining = {result[2]}, solarSystemID = {result[3]}, orderID = {result[4]}, 
        # stationID = {result[5]},  buy_true_sell_false = {result[6]}, contiguousHighsec = {result[7]}, tradeHub = {result[8]},
        # distanceAmarr = {result[9]}, distanceJita = {result[10]}, distanceHek = {result[11]}, distanceDodixie = {result[12]},
        # orderNum = {orderNum}
        # '''
        
        cursor.execute(query)
        conn.commit()

        orderNum += 1

        #subtract volume Remaining in the order from the volume that is needed
        # volumeNeeded -= result[2]   

        #find out how much volume is remaining after the item has been bought. If more is needed than the order can fulfill, then
        #set volumeRemaining to 0.
        volumeRemaining = result[2]
        volumeRemaining -= volumeNeeded
        if(volumeRemaining < 0):    # if there's not enough in the order to satisfy resource needs
            cost += result[2] * price
            volumeRemaining = 0
            savepoint = update_savepointOrders(typeID, result[2]) # Once things cemented, may want change to result[1].
        else:   # if there IS enough
            cost += volumeNeeded * price
            savepoint = update_savepointOrders(typeID, volumeNeeded)

        #update the table with how much is left, if anything.
        query = f'''
        update PurchaseOrders
        set volumeRemaining = {volumeRemaining}
        where orderID = {result[6]};
        '''

        cursor.execute(query)
        conn.commit()

        if volumeRemaining > 0:
            break

    conn.close()
    return cost

def get_remaining_from_PurchaseOrders(db_path, typeID):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    query = f'''
    select volumeRemaining from PurchaseOrders
    where typeID = {typeID} and volumeRemaining > 0;
    '''

    cursor.execute(query)
    results = cursor.fetchone()
    conn.close()

    if results is None:
        return None
    else:
        return results[0]

# components is a list where 1 item is represented by 5 elements.
# In order, those elements are: typeID, quantity, a list of sub-components, its sell price, and its build price.
# multiplier is the number of jobs to produce the top level item
def pretend_purchase_resources(db_path, component, tradeHub, multiplier):
    global orderNum
    typeID = component[0]
    quantityNeeded = component[1] * multiplier
    tradeHubOnly = config["buyFromTradeHubsOnly"]
    cost = 0

    query = f"select solarSystemID from SolarSystems where solarSystemName = '{tradeHub}';"
    solarSystemID = run_query(db_path, query)[0][0]
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    remaining = get_remaining_from_PurchaseOrders(db_path, typeID)

    # get the price of the resource
    resourceCost = run_query(db_path, f'''
                            select price
                            from PurchaseOrders 
                            where typeID = {typeID} and volumeRemaining > 0;
                            ''')

    if remaining is not None:
        num = remaining - quantityNeeded
        if num >= 0:    # If we don't need to buy more from another order
            cost += resourceCost * quantityNeeded

            run_query(db_path, f'''
                      update PurchaseOrders 
                      set volumeRemaining = {num} 
                      where typeID = {typeID} and volumeRemaining > 0;
                      ''')
            update_savepointOrders(typeID, num)
            # cost += num * price
        else:   # if we DO need to buy more from another order
            quantityNeeded -= remaining    # subtract how much was left in the order from how much is needed
            cost += resourceCost * remaining    # we're buying everything remaining b/c it's not enough.
            
            run_query(db_path, f'''
                      update PurchaseOrders 
                      set volumeRemaining = 0
                      where typeID = {typeID} and volumeRemaining > 0;
                      ''')
            update_savepointOrders(typeID, remaining)
            cost += copy_market_order(db_path, typeID, solarSystemID, remaining)
    else:   # if there aren't any residual items left in previous market orders
            cost += copy_market_order(db_path, typeID, solarSystemID, quantityNeeded) # does the same as *this* function

    # if tradeHubOnly:
    #     print()
    # else:
    #     print()

    conn.close()
    return cost

# This is a stat that's needed to find out how much system cost index needs to be multiplied by.
def calculate_estimatedItemValue(db_path, components, multiplier):
    EIV = 0
    
    for x in range(0, len(components), 5):
        adjustedPrice = run_query(db_path, 
                                  f"select adjustedPrice from AdjustedCostIndexes where typeID = {components[x]}"
                                  )[0][0]
        EIV += components[x+1] * multiplier * adjustedPrice

    return EIV

# components is a list where 1 item is represented by 5 elements.
# In order, those elements are: typeID, quantity, a list of sub-components, its sell price, and its build price.
# systems is a dictionary that contains, in order: highsec manu system, lowsec reaction/manu system, tradehub.
# multiplier is the number of jobs to produce the top level item
def find_item_build_cost(db_path, components, systems, multiplier):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    tradeHub = systems["tradeHub"]
    solarSystemID = get_solarSystemID_from_solarSystemName(db_path, tradeHub)
    resourceCost = 0

    for x in range(0, len(components), 5):
        component = [components[x], components[x+1], components[x+2], components[x+3], components[x+4]]
        if components[x+2] is not None:
            find_item_build_cost(db_path, components[x+2], systems, multiplier)
        else:   # if the component has no sub components and is thus a layer 0 item like tritanium.
            components[x+4] = "layer 0" # not sure if this is how I want to set the flag for this
            continue
        # something isn't working. Come back to it on Sunday.
        if components[x+2] is None:
            resourceCost = pretend_purchase_resources(db_path, component, tradeHub, multiplier)
        else:
            subComponents = components[x+2]
            for y in range(0, len(subComponents), 5):
                if(subComponents[y+4] == "layer 0"):
                    resourceCost += subComponents[y+3]  # can only buy
                    break
                if(subComponents[y+3] < subComponents[y+4]):
                    resourceCost += subComponents[y+3]  # cheaper to buy
                else:
                    resourceCost += subComponents[y+4]  # cheaper to build
        sci = 0.0
        EIV = calculate_estimatedItemValue(db_path, components, multiplier)
        activityID = run_query(db_path, f"select activityID from Items where typeID = {component[x]}")[0][0]
        if(activityID == 1):
            # ssid = solarSystemID
            # sci = systemCostIndex
            # EIV = estimatedItemValue
            ssid = run_query(db_path, f"select solarSystemID from SolarSystems where solarSystemName = '{systems['highsecManuSystem']}'")[0][0]
            sci = run_query(db_path, f"select manufacturing from SystemCostIndexes where solarSystemID = {ssid}")[0][0]
            resourceCost += sci * EIV
        elif(activityID == 11):
            ssid = run_query(db_path, f"select solarSystemID from SolarSystems where solarSystemName = '{systems['lowsecManuSystem']}'")[0][0]
            sci = run_query(db_path, f"select reaction from SystemCostIndexes where solarSystemID = {ssid}")[0][0]
            resourceCost += sci * EIV

        components[x+4] = resourceCost
        
        # write a new function for calculating adjustedCost.
        # Look at this forum post as a sort of guide: https://forums.eveonline.com/t/estimated-item-value-calculation/241319
        # adjustedCost = run_query(db_path, f"select adjustedPrice from AdjustedPriceIndex where typeID = {component[x]}")
        
    conn.close()

# The report needs to know the trade hub (or wherever) where the item is supposed to be sold.
def create_sub_report(db_path, components, volumehigh, file):
    for x in range(0, len(components), 5):
        typeName = run_query(db_path, f"select typeName from Items where typeID = {components[x]}")[0][0]
        appendFile(file, f"{typeName} x {components[x+1] * volumehigh}. ")
        #if it's cheaper to buy it than to build it
        if(components[x+4] == "layer 0" or components[x+3] < components[x+4]):
            query = f'''
                    select volume, volumeRemaining, solarSystemID, price, stationID
                    from PurchaseOrders
                    where typeID = {components[x]}
                    order by volumeRemaining asc
                    '''
            marketData = run_query(db_path, query)
            for market in marketData:
                volume = market[0]

                solarSystemName = run_query(db_path,
                        f"select solarSystemName from SolarSystems where solarSystemID = {marketData[2]}")[0][0]
                price = marketData[3]
                stationName = run_query(db_path,
                        f"select stationName from Stations where stationID = {marketData[4]}")[0][0]
                appendFile(file, "Buy this component ")

def create_report(db_path, components, volumehigh, file, expectedProfit, tradeHub):
    typeName = run_query(db_path, f"select typeName from Items where typeID = {components[0]}")[0][0]
    appendFile(file, f"{typeName} x {volumehigh}")
    newLine(file)
    appendFile(file, "Components:")
    newLine(file)

    for x in range(0, len(components), 5):
        create_sub_report(db_path, components[x+2], volumehigh, file)

# step 3
# Each function instance only computes 1 item at a time
def compute_profitability(db_path, typeID, blueprintID, activityID, regionID, volumehigh):
    global config
    portionSize = adjust_volumehigh_for_portionSize(db_path, typeID)
    # https://stackoverflow.com/questions/2272149/round-to-5-or-other-number-in-python
    volumehigh = portionSize * round(volumehigh/portionSize)
    if(volumehigh == 0):
        return -1
    # results = get_material_requirements(blueprintID, activityID, db_path)
    # I forget why I needed to know item production sub-component levels/tiers, but it's in the database now.

    # Now I need to run through all the materials
        # I need to find out if it has sub components - done
        # How much it costs to make and how much it costs to buy on the market (based on config settings)
            # When determining cost to buy, need to use transactions (w/e) to pretend to buy resources.
            # Also need to factor in hauling costs (depending on config settings)
        # Determine which is cheaper
    
    components = find_components(db_path, typeID)
    components = [typeID, volumehigh, components, "sell price", "build price"]
    systems = find_manufacturing_systems(db_path, regionID)
    find_item_sell_prices(db_path, components, systems, volumehigh)
    # start_transaction(db_path)
    find_item_build_cost(db_path, components, systems, volumehigh)
    # rollback_transaction(db_path)   # this comes at the end
    
    # factor portionsize into the item price.
    k = run_query(db_path, f"select portionSize from Items where typeID = {components[0]}")[0][0]
    k *= components[3]

    totalSellPrice = components[3] * k * volumehigh
    taxes = config["sellTax"] * totalSellPrice
    buildCost = components[4]
    totalExpectedProfit = totalSellPrice - taxes - buildCost

    if(totalExpectedProfit <= 1000000):
        return -1
    
    #Create the report
    itemName = run_query(db_path, f"select typeName from items where typeID = {typeID}")[0][0]
    regionName = run_query(db_path, f"select regionName from Regions where regionID = {regionID}")[0][0]
    createDirectory(f"./reports/{itemName}")
    file = createFile(f"./reports/{itemName}/{regionName}")
    create_report(db_path, components, volumehigh, file, totalExpectedProfit, systems["tradeHub"])
    file.close()
    
    # something else that will probably become an issue later. I don't think portion size is factored in
    # when a subcomponent's build cost is being figured out.
    
    # This appears to work.
    # Need to make the report next that breaks down where to buy stuff and the various costs/prices/whatever.
    # if type(components[0]) is list:
    #     print("a list")
    # else:
    #     print("not a list")

        
def find_item_final_sell_price(db_path, typeID, regionID):
    run_query(db_path, "select ")

######################################################################################
######################################################################################
######################################################################################
######################################################################################
######################################################################################

def mainloop():
    printConfig()
    global config
    db_path = config["dbPath"]

    # results = run_query(db_path, "select typeID, layer from Recipes")

    run_query(db_path, "delete from PurchaseOrders;") # empty the PurchaseOrders table.

    # savepoint_test(db_path)

#    items = get_typeIDs_blueprintIDs_and_activityIDs_from_Items_table(db_path)
#    volume_high = get_volume_high_from_EstimatedRegionalHighSellAmount_table(db_path)
    items = get_typeID_blueprintID_activityID_regionID_volumehigh(db_path) # Step 1 & 2

    for typeID, blueprintID, activityID, typeID2, regionID, volumehigh in items:
        if(volumehigh == 0): # It never will be. The query prevents it. Keeping it here just in case.
            continue
        # materials = get_material_requirements(blueprintID, activityID, db_path)
        itemName = get_itemName(db_path, typeID)
        # need to get the returned string out of the wrapping.
        regionName = get_regionName(db_path, regionID)
        # appendFile(file, f"Creating {itemName} x {volumehigh} for region {regionName}")
        # newLine(file)
        profitability = compute_profitability(db_path, typeID, blueprintID, activityID, regionID, volumehigh)
        print()


mainloop()

######################################################################################
######################################################################################
######################################################################################
######################################################################################
######################################################################################
