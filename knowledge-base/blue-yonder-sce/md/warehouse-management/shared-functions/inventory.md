---
title: "Inventory"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/inventory.htm"
source: "/content/inventory.htm"
toc_path:
  - "Warehouse Management"
  - "Shared functions"
  - "Inventory"
sections:
  - "Inventory movement"
  - "Inventory adjustments overview"
  - "Inventory status change"
  - "Client ownership transfer"
  - "Management of bonded inventory"
  - "Shipped LPN reuse"
images: []
source_sha1: 9c5db46c24fd757610672098f3e47924e74bda04
---
# Inventory

The Inventory page is accessible from the following modules: **Inventory**, **Outbound Planner**, **Picking**, **Production**, **Receiving**, or **Shipping**.

This page provides visibility to inventory at the warehouse and LPNs that have been shipped. When you first access the Inventory page and select a tab, you must enter search criteria to retrieve data.

**IMPORTANT**: It is highly recommended that you limit the number of search criteria used in a single query on the Inventory page. Additional criteria increase the query's complexity, which could negatively affect application performance. If a search that uses multiple criteria is required for a regular business workflow, consider creating a custom report or Page Builder page to retrieve the data. See [Reports - Administration](../../administration/system-administrator/reports-labels/reports.md) and [Page Builder](../../administration/extensions/page-builder.md).

The Inventory page consists of the following tabs:

-   **On-Site**: Displays the locations, items, and LPNs in the warehouse (designated as four-wall). You can deselect the Show Four-Wall Inventory Only check box to include inventory and locations that are not four-wall, and therefore may not actually be on-site. For example, if the check box is deselected, the On-Site tab displays inventory associated with ASNs that have not yet been received.

**Note**: The subtabs display the number of records that were returned based on the search criteria.

-   **Locations**: Displays information for the locations that match the search criteria. For example, if you search for not pickable locations using the quick filter, the application displays all of the locations that have the **Pickable** field set to No. You can also search for an item-specific attribute, such as hazardous items, to view the locations that contain hazardous inventory. You can perform actions on locations and also view detailed location information. See [Procedures for locations](inventory/procedures-for-locations.md).
-   **Items**: Displays information for all of the items in the warehouse. For example, if you search for hazardous inventory, the Items subtab lists all of the items that are considered hazardous. You can perform actions on items and also view detailed item information. See [Procedures for items](inventory/procedures-for-items.md).
    
    **Note**: The Items subtab displays the total quantity of an item in the warehouse regardless of the search criteria. For example, if you search for an item with a specific inventory status, such as held inventory, the quantity displayed is the total warehouse quantity and not only the held quantity.
    
-   **LPNs**: Displays information for the LPNs that match the search criteria. For example, if you search for hazardous inventory, the LPNs tab lists all of the LPNs that contain an item that is considered hazardous. You can perform actions on LPNs and also view detailed LPN information. See [Procedures for LPNs](inventory/procedures-for-lpns.md).

-   **Shipped**: Displays the LPNs that have been shipped from the warehouse. You cannot perform actions on shipped LPNs. However, if you click an item in the grid to display its details, you can perform actions on the item. Actions performed on an item that was accessed from the Shipped grid do not impact shipped inventory.

You use the Shipped tab to view historical data for the LPNs that have been shipped. The application supports reusing LPN identifiers after they are shipped, so this tab can display multiple records for a single LPN, depending on how many times it was shipped and reintroduced into the application. See [Shipped LPN reuse](#Shipped_LPN_reuse) and [View shipped inventory](inventory/procedures-for-lpns.md).

## Inventory movement

You use move inventory to transfer inventory from one location to another. You can choose to move inventory immediately or create a move work request in the work queue. Work that has been released to the work queue can be performed by an RF operator. A move work request creates a replenishment work in the work queue. You can also choose to move the inventory at an LPN or sub-LPN level.

The source and destination areas must be configured in the inventory move configuration to move the inventory.

-   When you move the inventory immediately, the following conditions apply:
    -   When you move a full LPN or sub-LPNs from the location, you must provide the destination location and the move reason.
    -   When you move a partial LPN (less than the quantity of an LPN or sub-LPN), you must modify the Destination LPN value, and specify the destination location and move reason.
    
    **Note**: The areas to and from which inventory moves can be performed and the zones in which operators are allowed to move a partial quantity is determined based on the inventory moves configuration. See [Inventory Move Settings](../configuration/inventory/inventory-moves/inventory-move-settings.md).
    
-   When you create a move request in the work queue, the following condition apply:
    -   When you move a full LPN from the location, you must specify the destination location value.
    -   When you move a partial LPN (less than the quantity of an LPN or sub-LPN) with the **Round Up** field set to Yes, the inventory count is updated to the next highest unit of measure for the LPN defined in the item footprint configuration. This creates a replenishment work in the work queue.
    
    For example, if the **Round Up** option is enabled, a pallet quantity is five cases, and you select to move three cases, then the application creates an inventory move work from the location for a full pallet (five cases). If this option is disabled, the inventory move from the location is done for three cases.
    
    **Note**: For **Round Up**, the areas to and from which inventory moves can be performed is determined based on the warehouse storage location configuration. The source location must be configured as pickable and the destination location must be configured for replenishments. See [Storage Locations](../configuration/warehouse/locations/storage-locations.md).
    

**Note**: You need to modify the Destination LPN value only if you move a partial LPN, in order to deposit the partial quantity to another LPN in the destination location.

## Inventory adjustments overview

Inventory adjustments are performed to modify the quantity of inventory in a storage location. For example, if you found inventory that had not been identified, you can perform an inventory adjustment to add the inventory to the proper storage location.

In addition, you can use inventory adjustments to modify inventory quantities. For example, if a pallet is received and put away at 12 cases per pallet and later it is determined that the pallet contained only 10 cases, you can perform an inventory adjustment to modify the quantity that is actually stored in the storage location.

An inventory adjustment is made when there is a noted discrepancy in physical inventory. The effect of an inventory adjustment is to bring book values (logical counts) into agreement with physical counts.

The following manual inventory adjustments can be made:

-   Adding inventory to a storage location, such as when inventory is found that has not been identified.
-   Removing inventory from the storage location, such as when inventory is lost.
-   Modifying inventory quantities within a storage location, such as when inventory is damaged.

You can perform adjustments at an LPN, sub-LPN, or detail-LPN level.

When you adjust inventory, the application places the storage location in error. You can choose to keep the storage locations in error to prevent any inventory activity from taking place in the location. If you choose to keep the location in error, then after the adjustments are made and you want to use the location again, you must reset the location status. Inventory adjustment transactions are sent (played) to the host automatically, if configured to do so; otherwise, you must do so manually.

Some manual inventory adjustments require approval by an authorized user, such as a supervisor. When a user performs an inventory adjustment that is equal to or exceeds a cost or unit adjustment threshold defined for the user, user's role, warehouse or (in a 3PL environment) for a client or client group, the adjusted location is locked, and the adjustment is not processed until it has been approved.

You use Inventory Adjustment Approval to view inventory adjustments that require approval and either approve or reject each adjustment. For details on Adjustment approvals, see [Adjustments](../inventory/adjustments.md).

## Inventory status change

You can change an inventory status when an item is identified and received into your facility, and thereafter, as needed. However, you cannot change the status of inventory in the following situations:

-   Inventory is reserved for an order. To change the status of inventory that is reserved, you must first cancel the reservation or the pick work for that inventory.
-   Inventory is pending or waiting to be put away in a location.
-   The status change violates the inventory aging profile assigned to the inventory.
-   The role to which you are assigned is not authorized to perform it. The settings to restrict inventory status changes are defined in the Inventory Status Settings configuration. The inventory status change operation is possible only if the user's role is authorized to perform it.

If you are using aging profiles for date-tracked items, you can still manually change the inventory statuses, but only to a status that is later in the aging progression. The exception to this is when a backwards change coordinates with the application-calculated status. For example, if you manually changed an inventory status from First Quality to Second Quality, you can manually go back to First Quality if the inventory's age is within the window defined for the First Quality status.

You can also choose multiple LPNs and change the inventory status.

## Client ownership transfer

Client ownership transfer enables you to change one or more of the following inventory attributes:

-   Item
-   Client
-   Footprint

You can transfer inventory from one client to another client, from one item to another item, and from one footprint to another footprint. When you transfer inventory, you enter a reason and comment for why the transfer was made. If the transfer is successful, the application logs two daily transactions: one to record the deletion of the original inventory and one to record the creation of the new or transferred inventory.

**Notes**:

-   You cannot perform a client ownership transfer for inventory that is serialized, allocated, picked, pending a move, associated with a distribution, or in a location with an active cycle count in progress.
-   You cannot perform the client transfer operation if doing so would violate mixing restrictions that are configured for the location.

## Management of bonded inventory

Bonded inventory requires strict control and tracking during all movements, transactions, LPN transfers, adjustments, cycle counts, inventory reconciliation, client transfers, and security.

The application supports the management of bonded inventory through the following activities:

-   Movements and transactions using standard and customs inventory attributes.
-   Transfers by tracking the rotation number as part of the movement process. If part of an LPN or a case is transferred to another LPN, the rotation number stays with the items that are transferred to the new LPN. For example, if you have a case of an item that is bonded and you move part of that case to another LPN or case, then the rotation number that was assigned to it when it was received is associated with the new inventory detail record that is created.
-   Adjustments and cycle counts by tracking the rotation number in the process.
-   Inventory reconciliation by tracking the consignment and rotation number for inventory.
-   Client transfers (the transfer of customs inventory from one client to another) by assigning a new rotation number to the inventory and notifying the duty management application when the transfer is made.
-   Security by supporting the creation of a user role that determines which users are allowed to perform the functions needed to support bonded inventory and the interaction with the duty management application; for example, to change the consignment status from Pending to Complete.

## Shipped LPN reuse

The application supports the ability to reuse LPNs that have been shipped (such as when an LPN is returned to the warehouse, with or without inventory). When an LPN is shipped from the warehouse, the application creates a historical record for that specific instance, which includes related inventory and shipping attributes. A single LPN can be associated with many historical records.

For example, assume a warehouse ships inventory on pallets (each associated with a permanent LPN) and also receives returned inventory using the same LPNs. When inventory is returned to the warehouse, the application accepts the LPN (along with any new inventory attributes, if applicable) while still maintaining history of the previous instances the LPN was shipped. The LPN can then be shipped and reused again as needed by your operational requirements.

You can view shipped LPN information using the Shipped tab on the Inventory page, and you can generate reports that contain shipped LPN information. Historical records of shipped LPNs can be archived and purged to remove them from the production instance of the application using the same archive and purge job for dispatched transport equipment.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
