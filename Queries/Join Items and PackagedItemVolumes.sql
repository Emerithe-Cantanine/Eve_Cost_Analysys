SELECT Items.*,
       PackagedItemVolumes.volume
  FROM Items
       JOIN
       PackagedItemVolumes ON Items.typeID = PackagedItemVolumes.typeID;
