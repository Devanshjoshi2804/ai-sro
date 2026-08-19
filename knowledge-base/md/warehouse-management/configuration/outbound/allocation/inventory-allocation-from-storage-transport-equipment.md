---
title: "Inventory allocation from storage transport equipment"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/inventory_allocation_from_storage_transport_equipment.htm"
source: "/content/inventory_allocation_from_storage_transport_equipment.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Outbound"
  - "Allocation"
  - "Inventory allocation from storage transport equipment"
sections:
  - "Inventory allocation from storage transport equipment setup"
images: []
source_sha1: 15f0e81faccd59ba6de5df4ac18607902299c12a
---
# Inventory allocation from storage transport equipment

You can configure the application to allocate inventory directly from storage transport equipment for outbound order picks and replenishments. Additionally, you can schedule and perform cycle counts and audit counts on storage transport equipment that is at a dock door. This is helpful for customers who perform store fulfillments that require large quantities of the same item. The inventory can be allocated from the storage transport equipment, which can be moved to a dock door when the inventory needs to be picked, instead of having to move inventory to a storage location within the warehouse before it can be picked. This provides more efficiency in fulfilling large orders of the same item while conserving storage capacity within the warehouse.

## Inventory allocation from storage transport equipment setup

The application can allocate inventory from storage transport equipment like any other storage location in a pick zone. The transport equipment can be in a yard location or at a dock door. However, before allocated picks can be released and performed, the transport equipment must be at a dock door with safety checks completed as required. To allocate inventory from the storage transport equipment, perform the following tasks:

1.  Add the storage transport equipment as a pick zone. See [Add or modify a pick zone](pick-zones.md).
2.  Add a storage transport equipment pick method. See [Add or modify a pick method](../picking/pick-methods.md).
3.  In the allocation search path or replenishment search path, include the equipment as the pick zone and select the storage equipment pick method that will be used to release picks for inventory from the pick zone. See [Configure allocation search paths for order picks](allocation-search-paths.md) or [Configure replenishment search paths](../../inventory/replenishments/replenishment-search-paths.md).

**Note**: A new work operation, Storage Equipment Pick, is distributed with a release rule that prevents allocated picks on storage transport equipment from being released until the equipment is at a dock door. It is recommended that you do not modify the release rule for this work operation.

In order to be considered for allocation, inventory on the transport equipment must be homogeneous to prevent unnecessary searching and unloading of inventory from the equipment. This means that the transport equipment contains either a single LPN of one distinct item, or multiple LPNs of inventory, with each LPN containing a distinct item. For example, the transport equipment can contain one LPN of ITEM1, one LPN of ITEM2, and one LPN of ITEM3, but not one LPN of both ITEM1 and ITEM2. If tracked by lot, revision, or origin code, then all the inventory on a single LPN must contain the same lot, revision and origin code to be considered homogeneous.

**Note**: You cannot move the equipment from the dock door once the picks are released or the once a count is started.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
