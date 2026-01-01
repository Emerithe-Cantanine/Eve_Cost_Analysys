SELECT  Distances.solarSystemID, Distances.solarSystemName, Distances.contiguousHighsec,
            Distances.distanceAmarr,
            SystemCostIndexes.manufacturing, 
            SolarSystems.security
    FROM    Distances
    JOIN    SystemCostIndexes ON Distances.solarSystemID = SystemCostIndexes.solarSystemID
    JOIN    SolarSystems ON SystemCostIndexes.solarSystemID = solarSystems.solarSystemID
    WHERE   security >= 0.45
    ORDER BY manufacturing ASC, distanceAmarr ASC, security DESC;