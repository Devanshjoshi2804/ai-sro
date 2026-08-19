---
title: "Narrow aisle inventory replenishment configuration points"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/narrow_aisle_inventory_replenishment_configuration_points.htm"
source: "/content/narrow_aisle_inventory_replenishment_configuration_points.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inventory"
  - "Replenishments"
  - "Narrow aisle inventory replenishment configuration points"
sections: []
images: []
source_sha1: c0a278453d234fe8ca251dc2905a89eb9b5720b7
---
# Narrow aisle inventory replenishment configuration points

You can configure replenishment to allocate inventory out of a narrow aisle; for example, to a P&D location so that an operator using other equipment can move the replenishment to its destination. You can also configure the allocation of inventory at a larger unit of measure (UOM) than what is required for the replenishment. For example, if inventory required for a replenishment resides in a location that is only accessible by specialized equipment (such as narrow-aisle handling equipment), the application can allocate a pallet from a location in the zone, direct it to a location designated for splitting inventory off the pallet, and then from that location, allocate replenishment picks at a lower UOM level, such as cases. After the case picks are performed, the pallet LPN with the remaining inventory can be returned to storage.

The following tasks describe the configuration points that can be used to set up replenishment allocation from narrow aisle storage:

1.  Configure the inventory movement and storage strategies for narrow aisle storage. See [Narrow aisle inventory movement and storage configuration points](../../inbound/storage/storage-zones.md).
2.  Configure the movement zone that contains the narrow aisle storage locations. See [Movement Zones](../movement/movement-zones.md).
    
    If you want the application to allocate inventory out of the zone at a larger UOM than what is required for a replenishment pick, then for the storage aisle movement zone, set the **Allocate Maximum UOM** field to Yes.
    
3.  Configure a movement zone that contains P&D or splitting locations for replenishment inventory that must be split off from pallet LPNs. Configure a next move for the hop to generate directed work for moving inventory out of the zone immediately after inventory moves into the zone. Assign the replenishment split (RPLSPLT) work operation to the hop if you want the application to direct the user to enter the quantities to split and put the remaining inventory away.
4.  Configure a movement path from the narrow aisle storage to the zone to keep filled. If a P&D or splitting location is required, then add a hop to the movement zone that directs inventory to the zone where the picked inventory will be deposited. The hop can be a P&D or a special zone designated for splitting LPNs. See [Movement Paths](../movement/movement-paths.md).
5.  Configure a pick method for the replenishment search path. This is typically the Replenishment Split Pick method used to create directed work using the Replenishment Split work operation. This operation is used to indicate that the operator should be directed to split the inventory, return remaining inventory to storage, and move the requested inventory to its destination. Configure the pick method with release rules that define the action and operation associated with the directed work for the replenishments generated from the defined pick zone. See [Pick Methods](../../outbound/picking/pick-methods.md).
6.  Configure a replenishment search path for the narrow aisle pick zone. Assign the replenishment split pick method to the path. See [Replenishment Search Paths](replenishment-search-paths.md).
7.  Configure a replenishment path from the narrow aisle pallet zone to the pick movement zone to keep filled. If needed, include a hop zone in the path the defines the zone where the replenishment inventory is split off from the pallet LPN.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
