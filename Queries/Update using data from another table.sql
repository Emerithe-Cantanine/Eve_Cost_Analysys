update Distances as d
set regionID = ss.regionID
from SolarSystems as ss
where d.solarSystemID = ss.solarSystemID;