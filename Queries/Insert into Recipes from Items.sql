Insert Into Recipes (typeID, typeName, blueprintID, activityID, portionSize, layer)
select typeID, typeName, blueprintID, activityID, portionSize, layer
from Items
where blueprintID is not NULL;