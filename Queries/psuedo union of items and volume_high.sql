select a.typeID, a.blueprintID, a.activityID, b.typeID, b.regionID, b.volume_high
from Items a, EstimatedRegionalHighSellAmount b
where a.typeID = b.typeID
order by a.typeID;