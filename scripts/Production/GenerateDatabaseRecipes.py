import sqlite3
import time
import pickle
from Aggregate_Blueprint_Materials import get_material_requirements
from loadConfig import load_config
# from SetItemLayers import mainloop

global config
config = load_config()

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

def getItems(db_path, typeID = 178):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # production
    # query = "select typeID, blueprintID, activityID, layer from Recipes"

    # testing
    query = f"select typeID, typeName, blueprintID, activityID, portionSize from Recipes where typeID >= {typeID}"
    cursor.execute(query)
    results = cursor.fetchall()

    # convert the tuples in result to lists in _list
    _list = convert_tuple_to_list(results)
    for item in _list:
        item.append("quantity")
        item.append("subComponents")
    conn.close()
    return _list

def findRecursiveIngredient(item, ingredients):
    for ingredient in ingredients:
        if item[0] == ingredient[0]:
            return True
        
    return False

def findNonExistingIngredients(db_path, ingredients):
    for ingredient in ingredients:
        if ingredient[0] == 3924:
            print()
        result = run_query(db_path, f"select typeID from Items where typeID = {ingredient[0]}")
        if len(result) == 0:
            print(f"typeID: {ingredient[0]} does not exist.")
            return True

def generateRecipe(db_path, item):
    layer = run_query(db_path, f"select layer from Recipes where typeID = {item[0]}")
    if(layer == -1):
        print(f"stopped by: {item[1]}, {item[0]}")
        return
    blueprintID = item[2]
    activityID = item[3]
    ingredients_tuple = get_material_requirements(blueprintID, activityID, db_path)
    if ingredients_tuple is None:
        print(f"stopped by: {item[1]}, {item[0]}")
        return None
    ingredients = convert_tuple_to_list(ingredients_tuple)
    if findRecursiveIngredient(item, ingredients):
        print(f"stopped by: {item[1]}, {item[0]}")
        return None
    if findNonExistingIngredients(db_path, ingredients):
        print(f"stopped by: {item[1]}, {item[0]}")
        return None

    x = 0
    for ingredient in ingredients:
        stuff = run_query(db_path, 
        f"select typeName, blueprintID, activityID, portionSize from Items where typeID = {ingredient[0]}")[0]

        ingredients[x] = [ingredient[0],    # typeID
                          stuff[0],         # typeName
                          stuff[1],         # blueprintID
                          stuff[2],         # activityID
                          stuff[3],         # portionSize
                          ingredient[1],    # quantity
                          # adding an element for volume would be a good idea too, but I don't need it right now and it's feature creep territory.
                          "subComponents",  # subComponents (duh)
                          list(),
                          "sell price",
                          "build price",
                          "taxes"
                          ]
        
        # this might not be needed
        layer = run_query(db_path, f"select layer from Items where typeID = {ingredient[0]}")[0][0]
        if(layer == 0):
            ingredients[x][6] = None
            x += 1
            continue
        
        subcomponent_tuple = run_query(db_path, 
        f"select typeID, typeName, blueprintID, activityID, portionSize from Recipes where typeID = {ingredient[0]}")[0]

        subcomponent = list(subcomponent_tuple)
        subcomponent.append(ingredient[1])
        subcomponent.append("subComponents")

        recipe = generateRecipe(db_path, subcomponent)
        subcomponent[6] = recipe
        ingredients[x][6] = recipe
        x += 1

        
        
    #recipe = [blueprintID, activityID, ingredients]
    return ingredients

def generateRecipes():
    
    global config
    db_path = config["dbPath"]
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # These 2 queries and the mainloop() function basically refreshes the Recipes table with updated recipes.
    run_query(db_path, "DELETE FROM Recipes")
    run_query(db_path, '''
                Insert Into Recipes (typeID, typeName, blueprintID, activityID, portionSize, layer)
                select typeID, typeName, blueprintID, activityID, portionSize, layer
                from Items
                where blueprintID is not NULL;
              ''')
    
    # mainloop()

    items = getItems(db_path) #, 34317)

    for item in items:
        if(item[1] == ''):
            continue
        recipe = generateRecipe(db_path, item)
        if recipe is None:
            continue
        item[6] = recipe

        # the last element of each 'excess' list-element shows how much is used by production
        # instead of how much is produced as waste. Originally it showed how much was produced as extra, but then
        # I remembered that there would likely be multiple runs of each recipe. It would be easier on the calculations
        # to show how much is used each run, then multiply that by the number of runs and modulo that
        # by the portionsize.
        excess = findProductionExcess(recipe)
        if excess:
            excess = sortExcess(excess)
        item.append(excess) # Yea, I'm just bolting it onto the recipes.
        # I'm also aware that many, many recipes will have an empty list bolted on. I'm doing it for consistency.
        if item[7] is None:
            item[7] = "This is for excess"

        # this will be useful to already have when the recipe costs get calculated
        item.append("sell price")
        item.append("build price")
        item.append("taxes")

        # adding an element for volume would probably be a good idea too, but I don't need it right now and it's feature creep territory.
        
        result = pickle.dumps(item) # recipe)
        query = "update Recipes set recipeBlob = ? where typeID = ?"
        cursor.execute(query, (result, item[0],))
        conn.commit()

        # This shows how to get the recipe out of the database and back into list form.
        # result = run_query(db_path, f"select recipeBlob from Recipes where typeID = {item[0]}")[0][0]
        # list = pickle.loads(result)
        # print()

def findMatchingTypeID(uniqueItems, typeID):
    if uniqueItems:
        x = 1
        for item in uniqueItems:
            if item[0] == typeID:
                return x    # any number higher than zero is true. So x has to start at 1.
            x += 1
    return False

def sortExcess(excessItems):
    # sum the excess materials that have the same typeID and remove the duplicates
    uniqueItems = list()
    for item in excessItems:
        match = findMatchingTypeID(uniqueItems, item[0])
        if(match == False): # no match
            uniqueItems.append(item)
        else:   # match found
            uniqueItems[match - 1][3] += item[3]

    # remove the materials whose excess equals the amount needed for production (thus no actual excess)
    for item in uniqueItems:
        if(item[2] == item[3]):
            uniqueItems.remove(item)

    # compute how much will actually be excess.
    # Nevermind. It's explained in GenerateRecipes() why I'm not doing it like this anymore.
    # x = 0
    # for item in uniqueItems:
    #     uniqueItems[x][3] = uniqueItems[x][2] - uniqueItems[x][3]
    #     x += 1

    return uniqueItems


def findProductionExcess(recipe):
    excessItems = list()
    for item in recipe:
        if(item[4] > 1): # if portionSize is greater than 1
            excessItems.append([item[0], item[1], item[4], item[5]])    #typeID, typeName, portionSize, quantity
        if(item[6] is not None):
            excess = findProductionExcess(item[6])
            if excess:
                for xs in excess:
                    excessItems.append(xs)
    
    return excessItems;

start = time.time()
generateRecipes()
end = time.time()
print(f"Time taken: {end - start} seconds")
# This took like 36 minutes to run