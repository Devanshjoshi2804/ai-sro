---
title: "Items Not Assigned To A Location"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/items_not_assigned_to_a_location.htm"
source: "/content/items_not_assigned_to_a_location.htm"
toc_path:
  - "Warehouse Management"
  - "Inventory"
  - "Items Not Assigned To A Location"
sections:
  - "View items not assigned to a location"
  - "Items Not Assigned To A Location fields"
images: []
source_sha1: 4dc80cdc17b40f0fbd35f255e18ade4ed14cdfb9
---
# Items Not Assigned To A Location

Items are assigned to locations for storage or replenishments using the location preference or replenishment preference rules. Any item that is not defined in a preference rule as having an assigned location, regardless of whether inventory exists in the warehouse, is displayed on the Items Not Assigned To A Location page. See [Location Preference Rules](../configuration/inbound/storage/location-preference-rules.md) and [Configure replenishment settings](../configuration/inventory/replenishments/replenishment-settings.md).

## View items not assigned to a location

You can view the items in the warehouse that are not assigned to a location.

1.  Select **Inventory > Items Not Assigned To A Location**.
2.  View the information in the [Items Not Assigned To A Location fields](#Items_Not_Assigned_to_a_Location_fields).

## Items Not Assigned To A Location fields

 
| Field | Description |
| --- | --- |
| Item Number | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Item Family | Identifier used to group similar items together. Typically, all of the items within a family have the same material handling characteristics. |
| LPN Level | Value that determines the minimum LPN level at which the item is identified during the receiving process and tracked in the application, such as LPN, sub-LPN, or detail LPN. |
| Lot Tracking | Indicates whether the item is lot tracked (**Lot Tracking** field set to Yes in the item configuration). A lot is a batch (quantity) of an item uniquely identified by a lot number during the manufacturing process for the purpose of tracking that batch of inventory. |
| Velocity | Identifies the speed at which inventory stored in a location moves in and out of the warehouse. Velocity is used to optimize warehouse space and inventory handling by placing fast moving items in the best locations for quick picking, and slower moving items in the less accessible storage locations. The application accomplishes this by attempting to match the velocity of the item with the velocity of the location when finding a location for storing the item. |
| Date Controlled | Indicates whether date tracking is enabled for the item (**Date Code** field in the item configuration is not blank). |
| Date Last Modified | Date and time indicating when the item was last modified. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
