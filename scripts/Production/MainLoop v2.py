import sqlite3
import pickle
import multiprocessing
from loadConfig import load_config
from Reports import createFile, appendFile, newLine, createDirectory

global config
config = load_config()

global reservedOrders
reservedOrders = [] # [["OrderID", "VolumeAvailable", "VolumeUsed"]]

def printConfig():
    global config 
    config = load_config()
    for key, value in config.items():
        print(f"{key}: {value}")
    return config

# might not have to use the PurchaseOrders table at all. Going to experiment with using a global list to store
# the orderIDs and the quantity that's used from the order. This way, when calculating cost to buy
# it'll be doing the pretend to buy step. Also it'll be easier to check if an order can piggyback
# on another order that was already made for the same material.
# rolling back orders should be easier to do as well.
def storeReservedOrder(orderID, volume, volumeUsed):
    global reservedOrders
    reservedOrders.append([orderID, volume, volumeUsed])

def retrieveReservedOrder(orderID):
    global reservedOrders
    for order in reservedOrders:
        if order[0] == orderID:
            return order
    return None

def removeReservedOrder(orderID, volumeUsed):
    global reservedOrders
    x = 0
    for order in reservedOrders:
        if order[0] == orderID and order[2] == volumeUsed:
            reservedOrders.pop(x)
            return
        x += 1

def loadRecipeBlobFromDB(db_path, typeID):
    result = run_query(db_path, f"select recipeBlob from Recipes where typeID = {typeID}")[0][0]
    recipeList = pickle.loads(result)
    return recipeList

def run_multiple_query(db_path, query):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.executescript(query)
    results = cursor.fetchall()
    conn.commit()
    conn.close()

    return results

def run_query(db_path, query):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(query)
    results = cursor.fetchall()
    conn.commit()
    conn.close()

    return results

# step 1 and 2
def get_typeID_regionID_volumehigh(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    query = '''
    select a.typeID, b.regionID, b.volume_high
    from Items a, EstimatedRegionalHighSellAmount b
    where a.typeID = b.typeID and b.volume_high > 0 and b.regionID < 10000070 --and a.typeID > 11125
    order by a.typeID;
    '''
    # note to self: remember to remove the a.typeID = 16665 when testing is done.
    # and a.typeID = 16665 # Testing is done =)
    cursor.execute(query)
    results = cursor.fetchall()
    conn.close()
    return results

def find_manufacturing_systems(db_path, regionID):
    # This assumes the user wants to find the system with the cheapest cost index
    # closest to their prefered trade hub.
    preferedTradeHub = config["preferedTradeHub"]

    # if no prefered trade hub, then default to the closest trade hub to the order history.
    if preferedTradeHub == "None":
        preferedTradeHub = run_query(db_path, 
                        f"select nearestTradeHubName from Distances where regionID = {regionID}")[0][0]
        
    if config["buildAnywhereCheapest"] == False:
        return {"highsecManuSystem": config["highsecManuSystem"],
                "lowsecManuSystem": config["lowsecManuSystem"],
                "tradeHub": preferedTradeHub}

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

def find_item_sell_prices(db_path, components, systems): #, jobRuns):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    global reservedOrders

    tradeHub = systems["tradeHub"]
    solarSystemID = run_query(db_path, 
        f"select solarSystemID from solarSystems where solarSystemName = '{tradeHub}'")[0][0]
    for x in range(0, len(components)):
        if components[x][6] is not None:
            find_item_sell_prices(db_path, components[x][6], systems) #, jobRuns)
        
        query = f'''
        select price, volume, orderID
        from MarketOrdersAll
        where typeID = {components[x][0]} and buy_true_sell_false = 0
        order by
            CASE
                WHEN solarSystemID = {solarSystemID} THEN 1 
            END DESC, price
            
        ''' # limit 1 <-- this was taken out in case the first order didn't have enough.
        # modified the query, so now it asks for all orders outside the system, in case the system runs out.

        cursor.execute(query)
        amountAvailable = 0; total = 0; amountNeeded = components[x][5] # * jobRuns
        totalPrice = 0
        components[x][7] = list()   # remove this later when I rerun the GenerateRecipes script.
        
        while total < amountNeeded:             # if the total available from orders is less than what's needed
            difference = amountNeeded - total   # how much more is needed
            result = cursor.fetchone()          # get price and volume
            if result is None:                  # if there's no orders left in the station
                break;
            if(result[1] >= difference):        # if the order has more available than is needed
                totalPrice += difference * result[0]    # difference * order price
                total += difference                     # fill up total with the difference needed
                components[x][7].append([result[2], difference, result[0]])      # save the orderID, amount & price for later.
                storeReservedOrder(result[2], result[1], difference)
                break
            elif(result[1] < difference):       # if the order has less available than what is needed
                totalPrice += result[1] * result[0]     # order amount * order price
                total += result[1]                      # add order amount to total
                components[x][7].append([result[2], result[1], result[0]])      # save orderID, amount & price for later.
                storeReservedOrder(result[2], result[1], total)
                continue
                
        # x += 1 # I guess this is here to prevent infinite loops?? I forget why I added it.

        # price = totalPrice / total # this makes it price per unit
        components[x][8] = totalPrice # price

    conn.close()

# This is a stat that's needed to find out how much system cost index needs to be multiplied by.
def calculate_estimatedItemValue(db_path, components): #, multiplier):
    EIV = 0
    
    for x in range(0, len(components)):
        adjustedPrice = run_query(db_path, 
                        f"select adjustedPrice from AdjustedCostIndexes where typeID = {components[x][0]}"
                        )[0][0]
        EIV += components[x][5] * adjustedPrice

    return EIV

# EIV = estimatedItemValue
# SCI = systemCostIndex
# SCC = sccSurcharge
# Facility = facilityTax
def calculate_EIV_SCI_SCC_Facility(db_path, buildTypeID, components, systems):
    # this part just knocks it out for all sub items.
    for x in range(0, len(components)):
        if components[x][6] is not None:
            components[x][10] = calculate_EIV_SCI_SCC_Facility(db_path, components[x][0], components[x][6], systems)

    # Calculates EIV for all items in this layer of the recipe
    EIV = calculate_estimatedItemValue(db_path, components) #, jobRuns)

    total = 0
    sci = 0.0
    scc = config["sccSurcharge"]
    facilityTax = config["facilityTax"]
    activityID = run_query(db_path, f"select activityID from Items where typeID = {buildTypeID}")[0][0]
    if(activityID == 1):
        # ssid = solarSystemID
        ssid = run_query(db_path, f"select solarSystemID from SolarSystems where solarSystemName = '{systems['highsecManuSystem']}'")[0][0]
        sci = run_query(db_path, f"select manufacturing from SystemCostIndexes where solarSystemID = {ssid}")[0][0]
    elif(activityID == 11):
        ssid = run_query(db_path, f"select solarSystemID from SolarSystems where solarSystemName = '{systems['lowsecManuSystem']}'")[0][0]
        sci = run_query(db_path, f"select reaction from SystemCostIndexes where solarSystemID = {ssid}")[0][0]
    
    total += sci * EIV
    total += scc * EIV
    total += facilityTax * EIV

    return total

# buildTypeID is the item up one layer whose components this function is calculating the cost of
def find_item_build_cost(db_path, taxes, components, systems): #, jobRuns):
    # tradeHub = systems["tradeHub"]
    # solarSystemID = run_query(db_path, 
    #     f"select solarSystemID from solarSystems where solarSystemName = '{tradeHub}'")[0][0]
    # resourceCost = 0
    ignoreCalculateReactions = config["ignoreReactionsForNormalItems"]
    buildCost = taxes

    # I realized that EIV and SCI are kinda independent of the rest of the manufacturing costs.

    for x in range(0, len(components)):
        cost = 0
        if components[x][6] is not None: # if there are subcomponents
            # this will break things for finding out if reactions are profitable, but whatever.
            if ignoreCalculateReactions and components[x][3] == 11:
                components[x][9] = components[x][8]
            else:
                components[x][9] = find_item_build_cost(db_path, components[x][10], components[x][6], systems)
        else:
            components[x][9] = components[x][8] # this isn't elegant, but it doesn't break anything down the line

        # if buildCost < buying the materials off the market
        if components[x][9] < components[x][8]:
            buildCost += components[x][9]       # Building it is cheaper
            # remove the orders to buy this item
            for y in range(0, len(components[x][7])):
                orderID = components[x][7][y][0]; quant = components[x][7][y][1]
                removeReservedOrder(orderID, quant)
            components[x][7].clear()

        else:   # Buying it off the market is cheaper
            buildCost += components[x][8]       # components[x][8] already has the total price for quant * price
    
    return buildCost



    # for x in range(0, len(components)):
    #     cost = 0
    #     if components[x][6] is not None:
    #         build_or_buy = find_item_build_cost(db_path, components[x][10], components[x][6], systems) #, jobRuns)
    #         if build_or_buy:    # if the item is cheaper to build than to buy
    #             buildCost += build_or_buy
    #         else:               # if the item is more expensive to build than to buy
    #             return 0    # zero means the item is too expensive to build
    #         sellCost = components[x][8]
    #         if(buildCost >= sellCost):
    #             return 0    # zero means the item is too expensive to build
    #         components[x][9] = buildCost
    #     else:   # if there are no sub components
    #         for order in components[x][7]:  # order is orderID, quantity/volumeNeeded, and price
    #             cost += components[x][8] * order[1] # cost * quantity
        

        # components[x][8] = resourceCost
        # components[x][8] is build cost. Build cost is calculated from running THIS entire function.
        # It is resourceCost, but for the item whose subcomponents this function is running the numbers for.
        # So build cost gets returned. Then the item's[9] slot that called this function gets BC returned to it.
    # return resourceCost # build cost
    # The math ain't mathin on this.

def find_mainItem_sellPrice(db_path, typeID, systems):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    tradeHub = systems["tradeHub"]
    solarSystemID = run_query(db_path, 
        f"select solarSystemID from solarSystems where solarSystemName = '{tradeHub}'")[0][0]
    
    query = f'''
        select price
        from MarketOrdersAll
        where typeID = {typeID} and solarSystemID = {solarSystemID} and buy_true_sell_false = 0
        order by price ASC
        limit 1;
        '''

    cursor.execute(query)
    result = cursor.fetchone()

    # I decided to not use this. The market orders would be screwed up if I changed the trade hub at the end.
    # if result is None:  # try jita
    #     systems["tradeHub"] = "Jita"
    #     query = f'''
    #     select price from MarketOrdersAll
    #     where typeID = {typeID} and solarSystemID = 30000142 and buy_true_sell_false = 0
    #     order by price ASC limit 1;
    #     '''
    #     cursor.execute(query)
    #     result = cursor.fetchone()

    if result is None:
        return 0    # give up
        
    conn.close()
    return result[0]
    

def multiply_recipe_by_jobRuns(components, jobRuns):
    for x in range(0, len(components)):
        components[x][5] *= jobRuns
        subComponentsJobRuns = round(components[x][5] / components[x][4])

        if components[x][6] is not None:
            multiply_recipe_by_jobRuns(components[x][6], subComponentsJobRuns)

def recalculate_excessMaterials_by_jobRuns(excess, jobRuns):
    for x in range(0, len(excess)):
        excess[x][3] *= jobRuns
        excess[x][3] %= excess[x][2]
        # print()

def build_or_buy(recipe):
    buildPrice = recipe[9]
    sellPrice = recipe[8]
    if buildPrice < sellPrice:   # if the build price is less than the sell price (or the price to buy the materials)
        if recipe[6] is not None:
            for x in range(0, len(recipe[6])):
                y = build_or_buy(recipe[x][6])
                if y == "build": 
                    sell = ""
                elif y == "sell": 
                    build = ""
        return "build"
    else:
        return "sell"
    


# ingredients[x] =    [
#                     0 ingredient[0],   # typeID
#                     1 stuff[0],         # typeName
#                     2 stuff[1],         # blueprintID
#                     3 stuff[2],         # activityID
#                     4 stuff[3],         # portionSize
#                     5 ingredient[1],    # quantity
#                     6 "subComponents",
#                     7 "market Orders",
#                     8 "sell price",
#                     9 "build price"
#                     10 "taxes"
#                     ]

def compute_profitability(db_path, typeID, regionID, regionName, volumehigh):
    global config
    recipe = loadRecipeBlobFromDB(db_path, typeID)
    portionSize = recipe[4]
    # if(typeID == 583):
    #     print()

    jobRuns = round(volumehigh/portionSize)
    if(volumehigh == 0 or jobRuns == 0):
        return -1
    
    recipe[5] = recipe[4] * jobRuns # quantity to make = portionSize * jobRuns
    # I should add a config setting to disallow jobRuns that produce excess materials
    recalculate_excessMaterials_by_jobRuns(recipe[7], jobRuns)
    multiply_recipe_by_jobRuns(recipe[6], jobRuns)
    
    systems = find_manufacturing_systems(db_path, regionID)
    find_item_sell_prices(db_path, recipe[6], systems) #, jobRuns)
    recipe[10] = calculate_EIV_SCI_SCC_Facility(db_path, recipe[0], recipe[6], systems)
    recipe[9] = find_item_build_cost(db_path, recipe[10], recipe[6], systems) #, jobRuns) # this might need work
    recipe[8] = find_mainItem_sellPrice(db_path, recipe[0], systems)
    recipe[8] *= recipe[5] # factor in quantity
    recipe[8] -= recipe[8] * config["sellTax"]  # factor in taxes

    profit = round(recipe[8] - recipe[9])  # sell price minus build price
    if profit < 1000:   # if it is not profitable to produce and sell at market
        return 0
    
    generate_report(db_path, recipe, systems, regionID, jobRuns)
    return recipe[8] - recipe[9]

# def save_report_to_db(db_path, reportList, recipe):
#     conn = sqlite3.connect(db_path)
#     cursor = conn.cursor()

#     filePath = "something"
#     fileName = "something"

#     binary_data = convert_to_binary_data(filePath)
#     query = f"insert into Reports (fileName, binary_data) values (?, ?)"
#     cursor.execute(query, (fileName, binary_data,))
#     conn.commit()
#     conn.close

def layer_report(db_path, components, systems, indention):
    reportText = str()
    for component in components:
        if(component[9] < component[8]):
            reportText += f"{indention} Build {component[1]} x {component[5]} in "
            if(component[3] == 1):
                reportText += f"{systems["highsecManuSystem"]}"
            elif(component[3] == 11):
                reportText += f"{systems["lowsecManuSystem"]}"
            reportText += "\n"

            reportText += f"{indention} The sub components are:"
            reportText += "\n"
            reportText += layer_report(db_path, component[6], systems, indention + "  ")
        else:
            for order in component[7]:
                
                reportText += f"{indention} Buy {component[1]} x {order[1]:,} for {round(order[1] * order[2]):,} @ at {order[2]}/unit "
                marketOrder = run_query(db_path, 
                f"select typeID, price, stationID from MarketOrdersAll where orderID = {order[0]}")[0]
                stationName = run_query(db_path, f"select stationName from Stations where stationID = {marketOrder[2]}")[0][0]
                reportText += f"{stationName}"
                reportText += "\n"
    return reportText

def generate_report(db_path, recipe, systems, regionID, jobRuns):
    itemName = recipe[1]
    netProfit = round(recipe[8] - recipe[9])
    regionName = run_query(db_path, f"select regionName from Regions where regionID = {regionID}")[0][0]

    # createDirectory(f"./reports/{itemName}")
    # file = createFile(f"./reports/{itemName}/{regionName} - {itemName} - {netProfit}")
    
    reportText = ""

    reportText += f"Build {itemName} x {recipe[5]:,}."
    reportText += "\n"
    reportText += f"That is {jobRuns:,} runs of {recipe[4]:,} units each."
    reportText += "\n"
    reportText += f"Expected profit is: {netProfit:,} isk."
    reportText += "\n"
    # I should list taxes and all the other bullshit too.
    reportText += "\n"
    # appendFile(file, f"You'll need to buy this stuff, if you don't have it already:")
    # newLine(file)

    # for order in reservedOrders:
    #     quantity = order[2]
    #     marketOrder = run_query(db_path, 
    #     f"select typeID, price, stationID from MarketOrdersAll where orderID = {order[0]}")[0]
    #     __itemName = run_query(db_path, f"select typeName from Items where typeID = {marketOrder[0]}")[0][0]

    #     stationName = run_query(db_path, f"select stationName from Stations where stationID = {marketOrder[2]}")[0][0]
    #     appendFile(file, f"{stationName}: {__itemName} x {quantity} @ {marketOrder[1]}")
    #     newLine(file)
    
    reportText += "\n"
    reportText += f"This is a breakdown of everthing you will need to buy and build:"
    reportText += "\n"
    reportText += layer_report(db_path, recipe[6], systems, "  ")
    reportText += "\n"

    highsecDistance = run_query(db_path, 
    f"select distance{systems["tradeHub"]} from Distances where solarSystemName = '{systems["highsecManuSystem"]}'")[0][0]
    reportText += f"{systems["highsecManuSystem"]} (Highsec) is {highsecDistance} jumps from {systems["tradeHub"]}"

    reportText += "\n"

    lowsecDistance = run_query(db_path, 
    f"select distance{systems["tradeHub"]} from Distances where solarSystemName = '{systems["lowsecManuSystem"]}'")[0][0]
    reportText += f"{systems["lowsecManuSystem"]} (Lowsec) is {lowsecDistance} jumps from {systems["tradeHub"]}"

    reportText += "\n"

    if recipe[4] == 1:
        reportText += f"{recipe[1]} sells in {systems["tradeHub"]} for around {round(recipe[8]/jobRuns)} per unit"

    if recipe[4] > 1:
        reportText += f"{recipe[1]} sells in {systems["tradeHub"]} for around {round(recipe[8]/jobRuns)} per {recipe[4]} units"

    reportText += "\n"

    reportText += f"Expected income is {round(recipe[8])} - {round(recipe[9])} = {round(recipe[8] - recipe[9])}"

    run_query(db_path, f'''
              insert into Reports (typeID, typeName, regionName, netProfit, reportData)
              values ({recipe[0]}, "{recipe[1]}", "{regionName}", {netProfit}, "{reportText}")
              ''')

    # work on this some other time.
    # save_report_to_db(db_path, file, recipe)
    

    # y = build_or_buy(recipe)

    # I just realized that sell and build for top level items are 8 and 9 respectively
    # for sub components, they are 7 and 8 respectively.

    # Done
    # next I need to determine throughout the entire recipe, what to build and what to buy.
    # If I need to build, I need to purge the "buy orders" from the reservedOrders list for that item,
    # but not necessarily its sub components (unless they too are cheaper to build than to buy)

    # Done
    # Obviously I should check the top level item first.
    # This is almost done. It just needs a few more pieces to make it complete.

    # Then I need to figure out how to parse the static data because I can't use the data from fuzzworks anymore
    
    


######################################################################################
######################################################################################
######################################################################################
######################################################################################
######################################################################################

def mainloop():
    printConfig()
    global config
    db_path = config["dbPath"]
    
    items = get_typeID_regionID_volumehigh(db_path) # Step 1 & 2
    onlyUsePreferedRegions = config["onlyUsePreferedRegions"]
    preferedRegions = config["preferedRegionsToFindLeads"]

    for typeID, regionID, volumehigh in items:
        reservedOrders.clear()
        if(volumehigh == 0): # It never will be. The query prevents it. Keeping it here just in case.
            continue

        itemName = run_query(db_path, f"select typeName from Items where typeID = {typeID}")[0][0]
        # need to get the returned string out of the wrapping.
        regionName = run_query(db_path, f"select regionName from Regions where regionID = {regionID}")[0][0]
        
        # I can't see myself making stuff for all 25 regions, so this option limits the regions searched
        if onlyUsePreferedRegions:
            prefered = False
            for preferedRegion in preferedRegions:
                if preferedRegion == regionName:
                    prefered = True
                    break
            if not prefered:
                continue
        
        # Another idea I had was to condense the entire recipe chain into a single list, but that idea
        # feels like it would break down when some items needed to be bought versus being built. I don't know,
        # I imagine some compromise could be figured out. Maybe a condensed list for stuff to build and
        # a condensed list for stuff to buy. I should try to avoid feature creep too and maybe just go with
        # the simplest design, since it's almost certainly just going to be me using it.
        profitability = compute_profitability(db_path, typeID, regionID, regionName, volumehigh)

mainloop()

######################################################################################
######################################################################################
######################################################################################
######################################################################################
######################################################################################