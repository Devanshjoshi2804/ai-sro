---
title: "Item Velocity"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/item_velocity.htm"
source: "/content/item_velocity.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Advanced"
  - "Item Velocity"
sections:
  - "Add or modify an item velocity"
  - "Delete an item velocity"
  - "Item Velocity fields"
images: []
source_sha1: dc53e8e723281b7b240b2d4c55c03cef36d58921
---
# Item Velocity

An item velocity is the rate at which an item UOM is ordered, picked, shipped, or moved. Item velocity attributes are based on an actual, historical, or projected rate. Velocity is used to optimize warehouse space and inventory handling by placing fast moving items in the best locations for quick picking, and slower moving items in the less accessible storage locations. The application accomplishes this by attempting to match the velocity of the item with the velocity of the location when finding a location for storing the item.

The Item Velocity page displays the quantities tracked for an item based on item velocity policy settings. See the information on item velocity processing behavior in the _Supply Chain Execution Help_.

**IMPORTANT**: Item velocity policies are available when Slotting is installed and enabled in Warehouse Management.

## Add or modify an item velocity

1.  Select **Configuration > Advanced > Item Velocity**.
2.  Perform one of the following tasks:
    -   To add a new item velocity, from the **Actions** drop-down list, select **Add**.
    -   To copy an item velocity, in the grid select the check box on the row of the item velocity, and then from the **Actions** drop-down list, select **Copy**.
    -   To modify an item velocity, in the grid select the check box on the row of the item velocity, and then from the **Actions** drop-down list, select **Edit**.
3.  Enter information in the [Item Velocity fields](#Item_Velocity_fields).
4.  Click **Save**.

## Delete an item velocity

1.  Select **Configuration > Advanced > Item Velocity.**
2.  In the grid, select the check box next on the row of the item velocity.
3.  From **Actions** drop-down list, select **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Item Velocity fields

 
| Field | Description |
| --- | --- |
| Client ID | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. |
| Item # | Identifier for the item. |
| Outbound Order Number | Unique identifier for an outbound order. An order is a request for a supply of material or product. |
| Plan Date | Shipment date for the outbound order. |
| Unit of Measure | Identifier for the packaging level (such as each, inner pack, case, layer, or pallet) at which an item can be received, stocked, tracked, and reported. Units of measure are used in item footprint configurations. |
| Velocity Type | A slotting attribute that is used as criteria in a slotting plan to select items to be slotted. Velocity types are maintained on the Velocity Type page. The following velocity types are distributed with the application:<br>-   • **FORECAST ORDER QTY**: Forecast of the outbound order quantity by UOM.
<br>-   • **ORDER QTY**: Total quantity of an item for an order by UOM.
<br>-   • **PICK HITS**: Number of visits to locations for picking by UOM.
<br>-   • **PICK QTY**: Picking quantity by UOM.
<br>-   • **VELZON RECALC**: Number of picks by item, client, outbound order type, and inventory status. |
| Inventory Status | Value that represents the quality or disposition of the inventory allocated for the picks, such as **A** for Available.<br > **IMPORTANT**: You must use an existing **Inventory Status** value defined on the Inventory Statuses page. |
| Operation Type | Reserved for future use. |
| Quantity | Number of items that changed (for example, number of items that were ordered, picked, or shipped) as a result of the velocity type and item velocity policy settings. See the information on item velocity processing behavior in the _Supply Chain Execution Help_. |
| Velocity ID | Unique identifier for an item velocity. |
| Warehouse Id | Unique identifier for this site, such as WMD1. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
