---
title: "Procedures for items"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/procedures_for_items.htm"
source: "/content/procedures_for_items.htm"
toc_path:
  - "Warehouse Management"
  - "Shared functions"
  - "Inventory"
  - "Procedures for items"
sections:
  - "Apply a hold to inventory"
  - "Release a hold from inventory"
  - "Generate or cancel a cycle count for an item"
  - "Generate or cancel a replenishment for an item"
  - "Maintain an item"
  - "Inventory mass update"
  - "View items"
  - "View detailed item information"
  - "Item fields"
  - "Item Summary fields"
  - "Item Footprint fields"
  - "Item Footprint UOM fields"
  - "Inventory fields"
  - "Processing fields"
  - "Inventory Attributes fields"
images: []
source_sha1: 9b64ca14584465220692165b0f0e783acbcf595d
---
# Procedures for items

You can perform these procedures using the Inventory page, which is accessible from the following modules: **Inventory**, **Outbound Planner**, **Picking**, **Production**, **Receiving**, or **Shipping**.

## Apply a hold to inventory

You can apply one or more holds to the same inventory. When you apply a hold to an item, all of the inventory for that item is held, regardless of the LPN on which the inventory is located. When you apply a hold to inventory on a specific LPN, only the inventory on that LPN is held.

You can also apply a hold to an item or inventory in a location by viewing the detailed information for a location or item (on the Summary tab). See [View detailed LPN information](procedures-for-lpns.md) and [View detailed item information](#View_detailed_item_information).

1.  Perform one of the following tasks:
    -   View the Inventory page, select **On-Site**, and then perform one of the following tasks:
        
        1.  Select one of the following modules: **Inventory**, **Outbound Planner**, **Picking**, **Production**, **Receiving**, or **Shipping**.
        2.  Select **Inventory**.
        
        -   To apply a hold to an item, select **Items**, and then in the grid, select the check box next to the item.
        -   To apply a hold to inventory on a specific LPN, select **LPNs**, and then in the grid, select the check box next to the LPN.
        -   To apply a hold to inventory in a specific location:
            1.  Select **Locations**.
            2.  In the grid, click the location. The location details are displayed.
            3.  Perform one of the following tasks:
                -   To apply a hold to an item in the location, select **Items**, and then in the grid, select the check box next to the item.
                -   To apply a hold to an LPN in the location, select **LPNs**, and then in the grid, select the check box next to the LPN.
    -   View a grid with a link for a location, click the location, and then select one of the following: **Items** or **LPNs**.
    -   View a grid with a link for an item, and then click the item.
2.  From the **Actions** drop-down list, select **Apply Hold**. The Apply Hold page is displayed with a list of existing hold definitions.
3.  To add a hold definition:
    1.  Click **Add Hold**.
    2.  Enter information in the [Holds fields](../../inventory/holds/procedures-for-holds.md).
    3.  If the **Apply to Inbound Inventory** field is set to Yes, then define the criteria for the inventory to which the hold will be automatically applied at the time of receipt:
        1.  Under **INBOUND PROCESSING**, click **Inventory Criteria**.
        2.  Enter information in the [Inbound Hold Criteria fields](../../inventory/holds/procedures-for-holds.md).
        3.  Click **Apply**.
    4.  Click **Save**.
4.  In the grid, select the hold to apply, and then click **Apply**. The Apply Hold window is displayed.
5.  Enter information in the following fields:
    
     
    | Field | Description |
    | --- | --- |
    | Change Inventory Status | Status to which the held inventory is changed. This field is only displayed if the **Inventory Status** field on the hold configuration is set to Yes. |
    | Change Only Certain Statuses | Indicates that the status for certain held inventory is to be changed based on its current status. If selected, then for each inventory status, in the **To Inventory Status** column, select the status to apply to the inventory. For example, you may only want to update the status for inventory that has an Available status, while keeping the remaining held inventory in its current status. This field is only displayed if the **Inventory Status** field on the hold configuration is set to Yes. |
    | Reason | Value that indicates why the hold is being applied. A reason is required whenever a hold is applied to inventory. |
    
6.  Click **OK**. A confirmation message is displayed.

**Note**: If the application was unable to apply the hold, then a list of the LPNs is displayed with the reason the hold could not be applied.

8.  Click **OK**.

## Release a hold from inventory

You can release a hold to remove the hold from the inventory.

1.  Perform one of the following tasks:
    -   View the Inventory page, select **On-Site**, and then perform one of the following tasks:
        
        1.  Select one of the following modules: **Inventory**, **Outbound Planner**, **Picking**, **Production**, **Receiving**, or **Shipping**.
        2.  Select **Inventory**.
        
        -   To release a hold from an item, select **Items**, and then in the grid, select the check box next to the item.
        -   To release a hold from inventory on a specific LPN, select **LPNs**, and then in the grid, select the check box next to the LPN.
        -   To release a hold from inventory in a specific location:
            1.  Select **Locations**.
            2.  In the grid, click the location. The location details are displayed.
            3.  Perform one of the following tasks:
                -   To release a hold to an item in the location, select **Items**, and then in the grid, select the check box next to the item.
                -   To release a hold to an LPN in the location, select **LPNs**, and then in the grid, select the check box next to the LPN.
    -   Select **Inventory > Holds**, and then perform the following tasks:
        1.  Select **Active Holds**.
        2.  Click a hold, and then select **LPNs**.
        3.  In the grid, select the check box next to the LPN, or click the LPN.
        
        **Note**: To release all inventory under an active hold, instead of selecting **LPNs**, select **Summary** and then from the **Actions** drop-down list, select **Release All Inventory**. The Release Hold page is displayed.
        
    -   View a grid with a link for a location, click the location, and then select one of the following: **Items** or **LPNs**.
    -   View a grid with a link for an item, and then click the item.
2.  From the **Actions** drop-down list, select **Release Hold**. The Release Hold page is displayed.
3.  Select the hold to release, and click **Apply**. The Release Hold window displays.
4.  Enter information in the following fields:
    
     
    | Field | Description |
    | --- | --- |
    | Change Inventory Status | Status to which the held inventory is changed. This field is only displayed if the **Inventory Status** field on the hold configuration is set to Yes. |
    | Change Only Certain Statuses | Indicates that the status for certain held inventory is to be changed based on its current status. If selected, then for each inventory status, in the **To Inventory Status** column, select the status to apply to the inventory. For example, you may only want to update the status for inventory that has an Available status, while keeping the remaining held inventory in its current status. This field is only displayed if the **Inventory Status** field on the hold configuration is set to Yes. |
    | Reason | Value that indicates why the hold is being applied. A reason is required whenever a hold is applied to inventory. |
    
5.  Click **OK**. A confirmation message is displayed.
6.  Click **OK**.

## Generate or cancel a cycle count for an item

When you request a count, the application generates a cycle count for the item. When you cancel a cycle count, the pending count work is cancelled. You can generate multiple cycle counts for an item.

1.  Perform one of the following tasks:
    -   [View items](#View_items), and then in the grid, click the item. The item details are displayed.
    -   View a grid with a link for an item, and then click the item.
2.  To request a count of the item:
    1.  From the **Actions** drop-down list, select **Generate Cycle Count**. A confirmation message is displayed.
    2.  Click **OK**. The **Pending Count** tag is displayed for the item.
3.  To cancel a count request:
    1.  From the **Actions** drop-down list, select **Cancel Cycle Count**. A confirmation message is displayed.
    2.  Click **OK**. The **Pending Count** tag is removed for the item.

## Generate or cancel a replenishment for an item

When you request a replenishment for an item, the application searches for the inventory in the storage locations for replenishment, based on the movement zone set up in Replenishment configuration.

The item must be configured for replenishment in Replenishment configuration to generate a replenishment. You must enable top-off replenishments in Top-off Replenishments configuration. In Replenishment configuration, the **Maximum Locations for Item** field must be greater than zero. You can generate multiple replenishments based on the available inventory in the storage locations.

Item replenishment can fail when there is no sufficient inventory available in the storage location for top-off, if the search path is not defined, if release rules for top-off replenishment is not defined, or if the item is not configured for top-off replenishment.

Cancelling a replenishment from the top-off location also cancels replenishment request for the items in that location. If you have multiple replenishments, and when you cancel a replenishment for an item, all the replenishments for the items are canceled.

**Note**: You can generate replenishment only if a top-off replenishment location is available.

1.  View the Inventory page.
    
    1.  Select one of the following modules: **Inventory**, **Outbound Planner**, **Picking**, **Production**, **Receiving**, or **Shipping**.
    2.  Select **Inventory**.
    
2.  Select **On-Site**, and then select **Items**.
3.  In the grid, select the check box next to the item.
4.  To generate a replenishment for the item:
    1.  From the **Actions** drop-down list, select **Generate Replenishment**. A confirmation message is displayed.
    2.  Click **OK**. The **Pending Replenishment** tag is displayed for the location.
5.  To cancel a replenishment request:
    1.  From the **Actions** drop-down list, select **Cancel Replenishment**. A confirmation message is displayed.
    2.  Click **OK**. The **Pending Replenishment** tag is removed for the location.

## Maintain an item

1.  Perform one of the following tasks:
    -   [View items](#View_items), and then in the grid, click the item. The item details are displayed.
    -   View a grid with a link for an item, and then click the item.
2.  From the **Actions** drop-down list, select **Maintain Item**. The Edit Item page is displayed. The Edit Item page displays the **Available** fields by default. Click **All** to view all the fields in the item configuration.
3.  Enter information in the [Item fields](#Item_fields).
4.  To define footprint configurations for the item:
    1.  Under **FOOTPRINT**, click **Footprint Configuration**.
    2.  Perform one of the following tasks:
        -   To add a footprint for the item, click **Add**.
        -   To modify a footprint, in the grid, click the footprint.
        -   To copy a footprint, in the grid, select the check box next to the item, and then click **Copy**.
    3.  Enter information in the [Item Footprint fields](#Item_footprint_fields).
    4.  To define units of measure (UOMs):
        1.  Under **UNITS OF MEASURE**, click **Setup**.
        2.  Perform one of the following tasks:
            -   To add a UOM, click **Add**.
            -   To modify a UOM, in the grid, click the UOM.
            -   To copy a UOM, in the grid, select the check box next to the UOM, and then click **Copy**.
        3.  Enter information in the [Item Footprint UOM fields](#Item_footprint_uom_fields).
        4.  Click **Apply**.
    5.  Click **Apply**.
5.  To define how the application handles inventory for the item in the warehouse:
    1.  Under **HANDLING**, click **Inventory**.
    2.  Enter information in the [Inventory fields](#Inventory_fields).
    3.  Click **Apply**.
6.  To define how the application processes inventory for the item during receiving and shipping:
    1.  Under **HANDLING**, click **Processing**.
    2.  Enter information in the [Processing fields](#Processing_fields).
    3.  To assign repack classes to the item:
        1.  Click **Repack Classes**.
        2.  In the **Available Repack Classes** column, select the check box next to the repack classes to assign.
        3.  Click **Apply**.
    4.  Click **Apply**.
7.  Click **Save**.

## Inventory mass update

You use inventory mass update to modify inventory attributes of multiple LPNs at the same time.

You enter the selection criteria to find the inventory that you want to change, and then enter new values for selected attributes. If you change the manufacturing or expiration date of existing inventory associated with an aging profile, the application recalculates the dates and updates the inventory status. If you change the footprint of existing inventory, the application recalculates the current quantity, volume, and length values for the locations where the inventory resides.

1.  View the Inventory page.
    
    1.  Select one of the following modules: **Inventory**, **Outbound Planner**, **Picking**, **Production**, **Receiving**, or **Shipping**.
    2.  Select **Inventory**.
    
2.  Select **On-Site**, and then select the **Locations**, **Items**, or **LPNs** tab.
3.  From the **Actions** drop-down list, select **Inventory Mass Update**. The Inventory Mass Update page is displayed with all the LPNs.
4.  In the filter, enter search criteria to select the inventory to change.

**IMPORTANT**: Attribute updates are applied to all of the displayed inventory.

6.  Click **Update Attributes**. The Update Attributes window is displayed.
7.  From the **Reason** drop-down list, select the reason for modifying the inventory.
8.  To add more information, in the **Comment** field, enter the information.
9.  Enter information in the [Inventory Attributes fields](#Inventory_Attributes_fields).
10.  Click **Save**. A confirmation message is displayed.
11.  Click **Yes**.
12.  Click **Done**.

## View items

Perform one of the following tasks:

-   View the Inventory page, select **On-Site**, and then select **Items**.
    
    1.  Select one of the following modules: **Inventory**, **Outbound Planner**, **Picking**, **Production**, **Receiving**, or **Shipping**.
    2.  Select **Inventory**.
    
-   To view items in a specific location, [view locations](procedures-for-locations.md), click the location, and then select **Items**.

## View detailed item information

1.  Perform one of the following tasks:
    -   [View items](#View_items), and then in the grid, click the item. The item details are displayed.
    -   View a grid with a link for an item, and then click the item.
2.  Select **Summary** and view information in the [Item Summary fields](#Item_summary_fields).
3.  Select **Footprint** and view information in the [Item Footprint fields](#Item_footprint_fields).
4.  Select **LPNs** and view information in the [LPN detail field listings](procedures-for-lpns.md).
5.  Select **History** and view information in the following areas:
    -   **Last Activity**: Displays the last non-counting activity performed on the item and other supporting information. For example, if an LPN of the item was unpicked from an order, this area displays the user that performed the activity, the date and time at which it was performed, the specific LPN that was unpicked, and the location from which (and to which) the LPN was moved.
    -   **Count Activity**: Displays recent count activity information for the item such as the user that performed the count, the date and time at which it was performed, and the count activity (such as a detail cycle count).

## Item fields

 
| Field | Description |
| --- | --- |
| Item | Identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). Before the application can effectively store, track, and manipulate inventory, you must assign an item identifier and define the attributes of each item you want to track. When defining an item, you specify information such as how the item is packaged and handled, along with details that define how it should be received, stored, allocated, shipped, counted, and valued (cost information). |
| Client | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. |
| Description | Text that further describes the item. |
| Short Description | Brief description of the item. The short description is displayed when space is limited and the normal description cannot be displayed, such as on an RF device. |
| Item Family | Identifier used to group similar items together. Typically, all of the items within a family have the same material handling characteristics. |
| Item Hierarchy | Level of attributes associated with the facility's item hierarchy to which the item belongs. Item hierarchy levels are user-defined values that are used to associate an item with a set of attributes by which the item can be identified, stored, allocated, and shipped. |
| Receive Status | Value that defines the quality or disposition of inventory. When defined for an item, it represents the status assigned to inventory by default during receiving. |
| LPN Level | Value that determines the minimum LPN level at which the item is identified during the receiving process and tracked in the application.<br>-   • **LPN (Pallet)**: An identification label is required for the pallet. When inventory for this item is received, the operator is required to identify the pallet (or partial pallet).
<br>-   • **Sub-LPN (Case)**: An identification label is required for each case on a pallet.
<br>-   • **Detail LPN (Box)**: An identification label is required for each piece in a case.
<br > The typical LPN level for an item is LPN (Pallet). You usually only select an LPN level of Sub-LPN (Case) or Detail (Box) when every case or piece of the item is individually labeled with a unique serial number, and strict monitoring of every case or piece of inventory is required. |
| Business Unit | Name of the business unit to which the item belongs. A business unit is an entity used to group areas and items for which a subset of operations exist within a specific building of a warehouse. See [Business Units](../../configuration/warehouse/business-units.md). |
| Image | Media tool that displays the image that is associated with the entity. If an image has not been associated with the entity, a default image is displayed. You can view an enlarged version of the image and, depending on the settings, you can add, change, or remove the associated image file. |
| Stocking UOM | Smallest unit of measure (UOM) in which the item is stored. This value must match the smallest UOM defined on the item footprints. The bar chart quantities that are displayed in the application to show the progress of a warehouse process such as allocation, picking, or loading are based on the **Stocking UOM** for the item. |
| Display UOM | Unit of measure in which you want quantities of this item to be displayed, by default, in display quantity fields. The display quantity fields, such as **Display Pick Quantity** and **Display Cross Dock Quantity**, are included as columns in certain grid views in the application. The fields are used to show total quantity for an operation (based on this UOM); any remainder is displayed in the next lower UOM. For example, if the **Display UOM** is Case and there are 10 eaches in a case, then for a quantity of 49, the Display Quantity and UOM columns would show 4 Cases and the Remainder Quantity and UOM columns would show 9 Eaches. If the **Display UOM** is Eaches, then the Display Quantity and UOM columns would show 49 Eaches, and the Remainder Quantity and UOM columns would be blank. The **Display UOM** is also used in RF footprint display screens.<br > **Note**: The **Display UOM** configuration does not affect bar chart quantities that are used to display the progress of a warehouse process such as allocation, picking, or loading. Additionally, this configuration does not affect the **Pick Quantity** field value, which is displayed in the UOM required for the pick. |
| Nesting Class Code | Code that indicates this item can be nested inside of other items that have the same nesting class code during cartonization. |
| Weight Class | Value (such as Heavy, Medium, or Light) that represents the relative weight of the item. |
| Unit Cost | Cost of a single stocking unit of the item. The application uses unit cost during processing, for example, to evaluate whether cost thresholds have been exceeded for automatic inventory adjustments, inventory adjustment approvals, playing inventory adjustments to the host, over receiving, inventory count discrepancies, and generating a count near zero count when a pick is cancelled. Costs are also displayed in reports, for example, to show the cost of counted inventory in a Count Activity report or count variances in a Count Audit Worksheet report. |
| Currency | Identifier for the currency in which the monetary value is saved. |
| Display Item | Alternate item that has been selected to be used in place of the master item whenever the item is displayed, such as in fields, grids, or reports. The display item or any other alternate item can be entered in place of the master item during any process that requires the item to be entered. |
| Item Type | User-defined code that you can use to group similar items. This value is not used in warehouse processing, but can be displayed in shipped history reports. |
| Department | Identifier for a department within the customer's facility. A department can be specified for a customer type, customer, order, order line, distribution, and item. It can be used to group information for the purpose of sorting and searching data, consolidating distribution inventory in customer-specific storage locations, and to help customers direct inventory to the proper department when it arrives at their facility. |
| Color | User-defined value for the color of the item. Enter a value if you want to track, report on, or search for inventory based on this attribute. For example, this value can be displayed in inventory and item reports, and can be used to find matching inventory for the purpose of applying a hold or performing an inventory status change operation. |
| Style | User-defined value for the style of the item. Enter a value if you want to track, report on, or search for inventory based on this attribute. For example, this value can be displayed in inventory and item reports, and can be used to find matching inventory for the purpose of applying a hold or performing an inventory status change operation. |
| Size | User-defined value for the size of the item. Enter a value if you want to track, report on, or search for inventory based on this attribute. For example, this value can be displayed in inventory and item reports, and can be used to find matching inventory for the purpose of applying a hold or performing an inventory status change operation. |
| Fit | User-defined value for the fit of the item. Enter a value if you want to track, report on, or search for inventory based on this attribute. For example, this value can be displayed in inventory and item reports, and can be used to find matching inventory for the purpose of applying a hold or performing an inventory status change operation. |
| WIP Supply Item | If Yes, then the item is used in work order processing as a component in a top-level item; however, it is not allocated, picked, or delivered to a production staging location, line, or station. Instead, a supply item is typically stored in or near the production area (such as in a non-inventory tracked work-in-process supply locations) and is used by multiple production lines and top-level items. Cellophane and other wrapping materials are examples of supply items. Supply items are charged to a work order, either by specifying them in a bill of material (BOM) used to create the work order, or by specifying them when the work order is closed.<br > If No, the item is not a supply item. |
| Host Notification | If Yes, the application sends host transactions for this item. Select Yes for items that are received, stored, and shipped from your facility.<br > If No, then receiving information about any inventory received for this item is maintained, but no transaction is sent to the host, and no ABC cycle counts can be generated. Select No, for example, for an item that represents the warehouse materials used for packaging or maintenance of the facility. |
| Conveyable | If Yes, then the item can be moved through the warehouse on a conveyor. You can use the **Conveyable** attribute as a filter and in various configurations to direct inbound and outbound inventory as required by your warehouse operations. For example, you can configure movement path criteria for storage search paths that directs cases of a conveyable item to a conveyor hop location and pallets of the same item directly to a storage location, bypassing the conveyor hop.<br > If No, then the item is not considered to be conveyable. Select No if you want to exclude this item from processing that applies to conveyable items.<br > **Note**: This attribute by itself does not allow or prevent an item at any LPN level from traveling on a conveyor. Indicating an item is conveyable does not impact processing unless the attribute is used as criteria in configurations such as a storage search path or work assignment rules |
| Item Class | Item class to which the item belongs. An item class is a category that can be used to group items for processing typically based on matching characteristics, such as hazardous or flammable material. You can assign an item class to an item even if inventory for the item exists in the warehouse. See [Item Classes](../../configuration/inventory/items/item-classes.md).<br > **IMPORTANT**: Warehouse Management designation of hazardous materials related to this functionality in no way implies compliance with federal or international regulations pertaining to the storage, processing, and transport of such materials. |

## Item Summary fields

 
| Field | Description |
| --- | --- |
| Description | Text that further describes the item. |
| Client | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. |
| Item Family | Identifier used to group similar items together. Typically, all of the items within a family have the same material handling characteristics. |
| Receive Status | Value that defines the quality or disposition of inventory. When defined for an item, it represents the status assigned to inventory by default during receiving. |
| Date Controlled | Indicates whether date tracking is enabled for the item (**Date Code** field in the item configuration is not blank). The date by which the item is tracked is displayed; for example, the manufactured or expiration date. |
| LPN Level | Value that determines the minimum LPN level at which the item is identified during the receiving process and tracked in the application.<br>-   • **LPN (Pallet)**: An identification label is required for the pallet. When inventory for this item is received, the operator is required to identify the pallet (or partial pallet).
<br>-   • **Sub-LPN (Case)**: An identification label is required for each case on a pallet.
<br>-   • **Detail LPN (Box)**: An identification label is required for each piece in a case. |
| Lot Tracked | Indicates whether the item is lot tracked (**Lot Tracking** field set to Yes in the item configuration). A lot is a batch (quantity) of an item uniquely identified by a lot number during the manufacturing process for the purpose of tracking that batch of inventory. |
| Origin Tracked | Indicates whether the item is tracked by its origin (**Origin Code** field set to Yes in the item configuration). The origin code is typically an identifier for the country or area of the world in which the item was manufactured. |
| Revision Tracked | Indicates whether the item is revision tracked (**Revision** field set to Yes in the item configuration). A revision may be used to identify a specific manufactured version of the item, so that when the item is modified or improved, the manufacturer may assign a new version number to reflect the change. |
| Serialization | Indicates whether the item is serialized. A check mark is displayed in this field if the item is serialized. |
| Catch Tracked | Indicates that the item is tracked by catch unit measurements (**Catch Code** field in the item configuration is not blank). Catch unit measurements are variable weights or sizes of inventory that may exist within the same material handling (stock keeping) unit. A check mark is displayed in this field if the item is catch tracked. |
| Consignment Tracked | Indicates that the item is tracked as a consigned inventory. A check mark is displayed in this field if the item is consignment tracked. |
| Item Type | User-defined code that you can use to group similar items. This value is not used in warehouse processing, but can be displayed in shipped history reports. |
| Velocity | Identifies the speed at which inventory stored in a location moves in and out of the warehouse. Velocity is used to optimize warehouse space and inventory handling by placing fast moving items in the best locations for quick picking, and slower moving items in the less accessible storage locations. The application accomplishes this by attempting to match the velocity of the item with the velocity of the location when finding a location for storing the item. |
| Current Quantity in Each | Quantity of the item in Eaches in the following categories:<br>-   • **Current**: Quantity that is currently within the warehouse.
<br>-   • **Committed**: Quantity that is currently committed to a warehouse process, such as picking for an order, an inventory move, or a replenishment.
<br>-   • **Pending In**: Quantity that is pending for an inventory activity. For an item, the pending quantity equals the committed quantity.
<br>-   • **Forecast**: Expected quantity of the item to be received against inbound order lines. |
| Unit Cost | Cost of a single stocking unit of the item. The application uses unit cost during processing, for example, to evaluate whether cost thresholds have been exceeded for automatic inventory adjustments, inventory adjustment approvals, playing inventory adjustments to the host, over receiving, inventory count discrepancies, and generating a count near zero count when a pick is cancelled. Costs are also displayed in reports, for example, to show the cost of counted inventory in a Count Activity report or count variances in a Count Audit Worksheet report. |
| Currency | Identifier for the currency in which the monetary value is saved. |
| ABC Classification | Code that determines how often the item is counted in a single count period. The frequency assigned to each ABC code is defined in inventory counting settings. |

## Item Footprint fields

 
| Field | Description |
| --- | --- |
| Footprint | Name that identifies a footprint, which describes the packaging dimensions and units of measure for the item with which it is associated. |
| Footprint Description | Description that further identifies the footprint. |
| Default Item Footprint | If Yes, the footprint is displayed by default when the item is displayed. One and only one footprint must be defined as the default footprint.<br > If No, this is not the default footprint. |
| Default Handling Unit | Handling unit type that is applied by default (if handling unit tracking is enabled in the warehouse) when a pallet LPN of inventory for the item footprint is received. A handling unit type is group of platforms or containers (such as a pallets or totes) that share the same characteristics such as size and weight as well as whether they are serialized, temporary, and considered a container. The application tracks the on-hand quantity of handling units by type and, for serialized assets, by handling unit LPN. |
| Purge Unused Footprint | If Yes, the footprint is automatically purged from the application when no more inventory with the footprint exists. Select Yes for a footprint that is rarely used, such as one that represents an unusual packaging configuration. This field is automatically set to Yes for a new footprint that is created on a device during receiving.<br > If No, the footprint is not automatically purged when there is no more inventory associated with the footprint. |
| Pallet Stack Height | Maximum number of pallets that can be stacked on top of one another in a location. This value applies when the item footprint is stored in locations configured with a pallet stack height restriction; it does not apply to stacking pallets in transport equipment configured for storage. A value of 0 permits stacking pallets as high as the location capacity allows. |
| Stack Method | Name of the stack method used for stacking pallets in a location. This stack method is used when the pallet level UOM for the item footprint is stored in locations configured with a pallet stack restriction. |
| Cases Per Tier | Number of cases that are typically placed on each tier of a pallet-equivalent UOM for the item footprint. When defining a footprint for which you do not have a layer UOM, you must specify the number of cases that are typically placed on each tier or level of a pallet of inventory. For example, if cases of an item are typically received on pallets that are stacked with 6 cases per level and 3 levels high, totaling 18 cases, the cases per tier would be defined as 6. The application compares the LPN height to the location height to determine if an LPN can fit in a location. |
| Level Units | Number of level units (width) that a pallet-equivalent UOM of this item occupies when deposited to a location associated with a level type. The value you enter here must be considered in relation to other elements of level type configuration, such as the total level units defined for a level type, and how many pallets of this size can be stored on the level. For example, if a level can fit 5 pallets of this size and the level has 10 total level units, then the level unit value for this footprint is 2.<br > If this footprint represents the smallest pallet for the item, the number of level units should be equal to the number of level units in a single location associated with a level type and used to store the item. See [Level units](../../configuration/warehouse/locations/level-types.md). |
| Nesting Length | Additional length of a single unit of an item when it is stacked inside or on top of other items in the same nesting class. This optional attribute is used by cartonization to fit more inventory into smaller or fewer cartons, thus saving on shipping expenses. |
| Nesting Width | Additional width of a single unit of an item when it is stacked inside or on top of other items in the same nesting class. This optional attribute is used by cartonization to fit more inventory into smaller or fewer cartons, thus saving on shipping expenses. |
| Nesting Height | Additional height of a single unit of an item when it is stacked inside or on top of other items in the same nesting class. This optional attribute is used by cartonization to fit more inventory into smaller or fewer cartons, thus saving on shipping expenses. |
| Wrap | LPN-level packaging attribute for inventory. LPN packaging attributes are user-defined fields that are used to indicate requirements such as pallet wrapping, use of a slip sheet, and the application of labels on all four sides of a pallet of inventory. |
| Double Wrap | LPN-level packaging attribute for inventory. LPN packaging attributes are user-defined fields that are used to indicate requirements such as pallet wrapping, use of a slip sheet, and the application of labels on all four sides of a pallet of inventory. |
| Label 4 Sides | LPN-level packaging attribute for inventory. LPN packaging attributes are user-defined fields that are used to indicate requirements such as pallet wrapping, use of a slip sheet, and the application of labels on all four sides of a pallet of inventory. |
| Slip Sheet | LPN-level packaging attribute for inventory. LPN packaging attributes are user-defined fields that are used to indicate requirements such as pallet wrapping, use of a slip sheet, and the application of labels on all four sides of a pallet of inventory. |

## Item Footprint UOM fields

 
| Field | Description |
| --- | --- |
| Unit of Measure | Identifier for the packaging level (such as each, inner pack, case, layer, or pallet) at which an item can be received, stocked, tracked, and reported. Units of measure are used in item footprint configurations. |
| Unit Quantity | Number of individual units of the item contained in the unit of measure (UOM). The application automatically updates this value based on the values for UOM Quantity and next UOM. For example, if the configuration has Pallet, Case, and Each UOMs, and there are 10 eaches per Case and 10 cases per Pallet, then the unit quantity for Pallet is 100. |
| System Equivalent UOM | Inventory level at which the application tracks the UOM. The application supports inventory tracking (using license plate numbers) at the following levels: LPN (pallet-equivalent UOM), sub-LPN (case-equivalent UOM), and detail-LPN (unit or each UOM). The case and pallet equivalent settings are required for every footprint. The application automatically defines the smallest UOM on the footprint as the detail-LPN level.<br>-   • **None**: The UOM is not an inner pack, case, or pallet equivalent unit of measure. Select None, for example, if the UOM represents a single unit (each) or a layer.
<br>-   • **PACK EQUIVALENT**: The UOM represents an inner pack. An inner pack is a less-than-case quantity that consists of multiple units (eaches) packaged together. The footprint configuration defines the number of units per pack. It is used, for example, to qualify a quantity on an order or work order by number of units per pack instead of by footprint.
<br>-   • **CASE EQUIVALENT**: The UOM represents a sub-LPN level of inventory.
<br>-   • **LAYER EQUIVALENT**: The UOM represents a single tier (layer) on a pallet of inventory. A layer typically consists of a number of cases. This system equivalent UOM is only used for reporting pick activity when Warehouse Labor Management is integrated with the application.
<br>-   • **PALLET EQUIVALENT**: The UOM represents an LPN level of inventory. Select this option for the largest UOM in the footprint. |
| Receive | If Yes, the unit of measure (UOM) is the default UOM in which the inventory is received, added, or modified during inventory identification. This default UOM can be overridden, if necessary, during inventory identification. For example, if the item is typically received in full pallets but occasionally arrives at the receiving dock as less than a full pallet, the operator can choose a different UOM defined for the footprint to identify the quantity received.<br > If No, this is not the default UOM in which the item is identified. |
| Length | Length of the item footprint UOM. To change a measurement unit, click the unit next to the field, and select a different unit. |
| Width | Width of the item footprint UOM. To change a measurement unit, click the unit next to the field, and select a different unit. |
| Height | Height of the item footprint UOM. To change a measurement unit, click the unit next to the field, and select a different unit. |
| Gross Weight | Weight of the item footprint UOM that includes its packaging. To change a measurement unit, click the unit next to the field, and select a different unit. |
| Net Weight | Weight of the item footprint UOM, excluding the weight of its packaging. To change a measurement unit, click the unit next to the field, and select a different unit. |
| Cartonization | If Yes, indicates that the unit of measure can be cartonized (picked to a carton). Cartonization is an allocation process that determines which picks can be packed together in cartons for shipment, and which size carton should be used. Select Yes if you want to be able to allocate the item in this UOM for picking to a carton. Cartonization is typically enabled for each or piece UOMs that are small enough to fit into the picking and shipping cartons that your facility uses.<br > If No, the UOM will not be considered a candidate for cartonization. Select No, for example, for pallet UOMs and for case UOMs that are too large for a carton. |
| Carton Distribution | If Yes, the UOM must be placed in a carton if it is part of a distribution order. A distribution is a pre-allocation of a warehouse receipt to a single store; it connects a planned inbound order to an outbound order. The application evaluates this attribute during the distribution process; so that for a distribution order, you can require a UOM (even if it is not normally cartonized) to be packed into a shipping carton prior to being combined with other distribution inventory at a distribution deposit location. If inventory for which carton distribution is required is picked to a carton, the application does not direct the operator to pack it into another carton during the distribution process, since it has already been cartonized into the most efficient shipping carton.<br > If No, the application does not attempt to cartonize the UOM when it is part of a distribution order. |
| Bulk Picking | If Yes, indicates that the unit of measure can be aggregated for bulk picking. Bulk pick processing allocates matching inventory for multiple outbound order or work order lines together into larger UOM picks so as to reduce the number of smaller UOM picks required to satisfy the orders. For example, if Case is enabled as the bulk picking UOM on the default item footprint, then during bulk pick processing the application can combine order lines for case quantities of the item into larger bulk picking UOM quantities, such as pallets. The larger bulk picking UOM that is eligible to be the physical pick resulting from combining smaller UOM quantities is defined in Units of Measure. If you select Yes, the when eligible order or work order lines for the item are allocated using bulk pick processing, the application combines order lines for this UOM quantity in order to allocate the inventory at a higher, bulk picking UOM.<br > If No, the application does not combine order lines for the UOM quantity; and instead the order lines are allocated separately. Only available for the default item footprint, and only if bulk picking is enabled for the warehouse. |
| Threshold Percentage | Minimum percentage value of the UOM capacity that a partial UOM must contain to qualify as a threshold pick. Threshold picking is a pick process that is used to satisfy an order for a less than full platform quantity. For example, if a full pallet consists of 10 cases, and an order line requires 9 cases, the operator can be directed to pick a full pallet and then remove the unneeded case, rather than being directed to pick 9 cases separately.<br > Valid values are from 1.000 to 100.000. The smallest UOM must have a value of 100.000. Specify a threshold percentage for the pallet level UOM, if your facility uses threshold picking. |

## Inventory fields

 
| Field | Description |
| --- | --- |
| Lot Tracking | If Yes, users are required to enter a lot number when the item is received or identified. A lot is a batch (quantity) of an item uniquely identified by a lot number during the manufacturing process for the purpose of tracking that batch of inventory. Lots are commonly used with pharmaceuticals, fabrics, paints, dyes, food, and products with limited shelf life. Select Yes if you want the application to track the inventory by this attribute and consider it during order processing (if the attribute is requested on an order line), picking (if validation of the attribute is required), putaway (if mixing this attribute in a location is restricted), counting (if confirmation of the attribute is required), and consolidation of inventory on an LPN (if mixing the attribute is allowed).<br > If No, the item is not tracked by this attribute. |
| Lot Format | Format required for lot numbers that use the format. If a lot format is specified for the item, then whenever a lot number is entered for the item, the application validates the lot number against the required format. Also, if the lot format is configured with a production or expiration date, then during inventory identification, the application extracts the date from the format to populate the manufacture or expiration date fields. The format of the extracted date is defined by the **Raw Lot Format** field that is available when adding a new lot format. |
| Origin Code | If Yes, users are required to enter an origin code when the item is received or identified. The origin code is typically an identifier for the country or area of the world in which the item was manufactured. Select Yes if you want the application to track the inventory by this attribute and consider it during order processing (if the attribute is requested on an order line), picking (if validation of the attribute is required), putaway (if mixing this attribute in a location is restricted), counting (if confirmation of the attribute is required), and consolidation of inventory on an LPN (if mixing the attribute is allowed).<br > If No, the item is not tracked by this attribute. |
| Revision | If Yes, users are required to enter a revision when the item is received or identified. A revision may be used to identify a specific manufactured version of the item, so that when the item is modified or improved, the manufacturer may assign a new version number to reflect the change. Revisions are used in industries such as electronics, computer software, and publishing. Select Yes if you want the application to track the inventory by this attribute and consider it during order processing (if the attribute is requested on an order line), picking (if validation of the attribute is required), putaway (if mixing this attribute in a location is restricted), counting (if confirmation of the attribute is required), and consolidation of inventory on an LPN (if mixing the attribute is allowed).<br > If No, the item is not tracked by this attribute. |
| Supplier Lot Tracking | If Yes, indicates that users will be required to enter a supplier lot number when the item is received. In addition, the application will track supplier lot numbers on inventory for the item. A supplier lot number is assigned by the item's supplier and is used to uniquely identify and track the inventory to which it is assigned. The supplier lot number is different from the lot number, which is a manufacturer-assigned or production-assigned lot number. Select Yes if you want the application to track the inventory by this attribute and consider it during order processing (if the attribute is requested on an order line), picking (if validation of the attribute is required), putaway (if mixing this attribute in a location is restricted), counting (if confirmation of the attribute is required), and consolidation of inventory on an LPN (if mixing the attribute is allowed).<br > If No, the item is not tracked by this attribute. |
| Shipping Restriction by Lot | If Yes, then lots of this item can be set to a restricted status. Select Yes if you want to restrict certain lots of this item from being shipped, except in cases where the order type or work order is configured to allow inventory from a restricted lot status. An item lot might be restricted to indicate, for example, a safety issue within a specific lot (such as with food products) or that the inventory requires testing or validation before it can be shipped to an end customer. If you select Yes, any lot automatically created by the application for this item is restricted by default.<br > **Note**: If an item has a hold applied to it, the hold takes precedence over the lot status in terms of whether the item can be shipped.<br > If No, there are no shipping restrictions for this item by lot and you cannot specify a lot status. If you select No, any lot automatically created by the application for this item will be unrestricted, and the **Lot Status** field for the item lot is disabled. |
| Date Code | Value that determines whether date tracking is enabled for the item and, if it is, the date by which it is tracked. The date code cannot be changed if inventory for the item exists in the warehouse. Date code control primarily benefits facilities in which inventory's manufactured date, age, freshness date, shelf life, and incubation period is essential for delivering a quality product. You can store, select, and ship date-tracked inventory based on its date-related item attributes and customer requirements.<br>-   • **Manufactured Date**: The item is tracked by its manufactured date.
<br>-   • **Expiration Date**: The item is tracked by its expiration date.
<br>-   • **Both**: The item is tracked by both its manufactured and expiration date.
<br>-   • **No selection (blank)**: Date tracking is not enabled for the item. |
| Aging Profile | Name of the aging profile representing the aging process assigned to this item. An inventory aging profile is a configuration that defines a series of inventory statuses, each of which is associated with an age, such as 2 hours, 10 days, or 4 weeks. You assign an aging profile to a date-tracked item when you want the application to automatically update the inventory status of inventory for the item as it ages in the warehouse.<br > Included in the aging profile is the option to define an expired status. The application uses the age of the expired status to calculate the expiration date of an item that is tracked by its expiration date. When an item is tracked by both its manufactured date and expiration date, then you must assign either an aging profile or a shelf life to the item. |
| Shelf Life | Amount of time (from manufactured date) that it takes for the item to expire. If a shelf life is defined for an item, the application assigns a default expiration date at the time of receipt (based on the shelf life), but it will not automatically change the status of inventory as it ages. Generally, you would specify a shelf life for an item if you want to retain the status assigned to inventory at the time it is received, even if it ages beyond that status.<br > When an item is tracked by both its manufactured date and expiration date, then you must assign either an aging profile or a shelf life to the item. If an aging profile is assigned, the application automatically updates the status of the inventory as it ages. If a shelf life is assigned, the application does not update the status as inventory ages, even after it expires. |
| Time to Warn For Expiration | Number of seconds prior to a date-tracked item's expiration date that a warning message is displayed (during RF product identification) indicating that the inventory is about to expire. For example, if you specify 86,400, then a warning message is displayed if the inventory is identified within 1 day (24 hours) of its expiration date. |
| Date Window Type | Value that is used to evaluate whether multiple dates of an item can be stored in a single storage location and if so, the type of date that is evaluated. If you define a date window, then during automatic storage location selection, the date window is used to ensure that inventory is not deposited into a location where the age difference between the oldest and newest inventory is larger than the window defined for the item.<br>-   • **FIFO**: Indicates that the value in the Date Window field is based on the first-in, first-out dates of the inventory.
<br>-   • **Expiration Date**: (Only available if the value for Date Code is Expiration Date or Both.) Indicates that the value in the Date Window field is based on the expiration dates of the inventory.
<br>-   • **Manufactured Date**: (Only available if the value for Date Code is Manufactured Date or Both.) Indicates that the value in the Date Window field is based on the manufactured dates of the inventory.
<br>-   • **No selection (blank)**: All ages of the item can be mixed in a storage location.
<br > The amount of time for a date window is defined in the **Date Window** field, and the unit of time (minutes, hours, or days) is defined in the associated Time field. |
| Date Window | Value that identifies the maximum acceptable age difference between the oldest and newest inventory for an item in a storage location, based on the selected **Date Window Type**. The unit of time (minutes, hours, or days) for the window is specified in the **Date Window** field. |
| Date Window Time Unit | Unit of time associated with the value in the **Date Window** field. |
| Outbound Date Window | Amount of time in relation to the inventory’s received date or expiration date during which inventory is considered the same age for allocation when one of the FEFO/FIFO/LEFO/LIFO or absolute FEFO/FIFO/LEFO/LIFO inventory rotation methods is required. The available time units include minutes (m), hours (h), or days (d). For example, an entry of "5h" defines the window (5) and unit (hours). During allocation, the application uses the assigned date window based on a pre-defined order of precedence. See [Allocation Inventory Selection](../../configuration/outbound/allocation/allocation-inventory-selection.md). |
| Inventory Rotation Method | Value that represents the order in which the allocation process selects available inventory for allocation. Select an inventory rotation method if you want the application to search for inventory based on date processing or location.<br>-   • **FEFO-ORDER-BY and FEFO-ORDER-BY-ABSOLUTE**: First-expiration, first-out. The first inventory to expire will be selected first.
<br>-   • **FIFO-ORDER-BY and FIFO-ORDER-BY-ABSOLUTE**: First-in, first-out. The oldest inventory will be selected first.
<br>-   • **LEFO-ORDER-BY and LEFO-ORDER-BY-ABSOLUTE**: Last-expiration, first-out. The last inventory to expire will be selected first.
<br>-   • **LIFO-ORDER-BY and LIFO-ORDER-BY-ABSOLUTE**: Last-in, first-out. The newest inventory will be selected first.
<br>-   • **LOCATION-ORDER-BY**: Locations are ordered within a pick zone (maintaining the allocation search path order) by the location attributes specified for the **Location Sort** field in inventory selection settings.
<br>-   •
    
    **No selection (blank)**: The application uses the inventory rotation method of the highest defined level of precedence. For information on precedence, see [Inventory rotation allocation processing](../../configuration/outbound/allocation/inventory-rotation-allocation.md).
    
    <br>
    
    **Note**: Inventory rotation methods defined at a lower precedence (except the default method) are automatically copied to the order line or work order line when the line is created. For example, if an order line is created for a date-tracked item with a rotation method defined, the rotation method is copied from the item to the order line, and then the application uses the order line rotation method during allocation.
    
    <br > If no inventory rotation method is defined at any level, then the application uses the allocation search path sequence and allocates the first available inventory it finds that matches all of the required attributes.
<br > When using inventory rotation methods that are not absolute, the application searches for inventory by allocation search path in sequence until it finds a pick zone that contains the inventory, and then allocates inventory that is closest to the preferred processing date. Therefore, the application stops searching at the first pick zone in which matching inventory is found.<br > When using absolute inventory rotation methods, the application searches either all of the allocation search paths for inventory that is closest to the preferred processing date or, if absolute groups are defined, each absolute group in sequence until it finds matching inventory and then allocates inventory that is closest to the preferred processing date from the pick zones within the absolute group. Therefore, the absolute method allows for more a comprehensive search to find the inventory. |
| Velocity | Identifies the speed at which inventory stored in a location moves in and out of the warehouse. Velocity is used to optimize warehouse space and inventory handling by placing fast moving items in the best locations for quick picking, and slower moving items in the less accessible storage locations. The application accomplishes this by attempting to match the velocity of the item with the velocity of the location when finding a location for storing the item. |
| Recalculate Velocity | If Yes, item is enabled for item velocity recalculation. If item velocity recalculation is enabled for the warehouse, the application automatically updates the velocity for the item as needed, based on the item's actual pick velocity as compared to the pick velocity of other items for which Recalculate Velocity is selected. For example, if enabled, the application changes the velocity for an item from Fast Moving to Slow Moving when the item's pick velocity falls within the range defined for the Slow Moving velocity.<br > If No, the application does not recalculate or change the item's velocity based on actual pick velocity. |
| Count Back | If Yes, the item is enabled for count back. Count back is a picking verification task that applies when the operator is picking less than a full pallet from a location. If the item, location, UOM, and the operator (user), are enabled for count back, then the application requires the operator to capture the quantity of inventory that is left in addition to the quantity of inventory being picked. If the remaining quantity does not match the application-expected quantity, a count is generated. If the operator is authorized to do the count, the application prompts the operator to complete it; otherwise, a supervisor must resolve the discrepancy using an audit count.<br > If No, count back picking verification is not enabled or required for the item. |
| Supports Inventory Adjustment | If Yes, then inventory adjustments are allowed to be performed for the item. Also, when a variance occurs during a count, the count can be completed, and an inventory adjustment recorded if necessary.<br > If No, then inventory adjustments are not allowed to be performed for the item. If a user attempts to adjust inventory for the item, the application displays a message indicating that an adjustment is not allowed. However, during an RF inventory adjustment made as a result of a count discrepancy, missing inventory is moved (logically) to the lost location defined for the area. See [Lost location for count discrepancies](../../configuration/inventory/counting/count-settings.md). |
| Count Near Zero | If Yes, the application directs an RF operator to perform a cycle count immediately following a pick or inventory transfer if the item's inventory level drops below the **Count Near Zero Amount** threshold. The picking operator, if authorized for the count near zero operation, is prompted to perform the count. If the picking operator is not authorized, then another operator performs the count. Select Yes if you want to ensure that the inventory level is accurate when it falls below a certain amount.<br > Count near zero functionality can be enabled by item and by count zone. Therefore, a count near zero can be generated for a location, even if the item in the location is not enabled for it, as long as the location is in a count zone enabled for count near zero. If you enable count near zero for an item and leave the **Count Near Zero Amount** blank (null), then the application defers to the count zone setting. For example, if the Count Near Zero field for an item is Yes and the amount is left blank (null), but the count zone in which the item is stored has the Count Near Zero field set to No, then a count is not generated.<br > Alternatively, if both the item and count zone are enabled for count near zero and have differing thresholds, the value defined for the item takes precedence. For example, assume an item's threshold is 20 units and a count zone's threshold is 25 units. After a pick is complete, if the remaining quantity in the location is 22, then a count is not generated because the quantity did not fall below the item's threshold.<br > If No, then the item is not enabled for count near zero. However, a count near zero can be generated for the location in which the item is stored if the count zone is enabled for count near zero, and the inventory falls below the count zone threshold. |
| Count Near Zero Amount | Unit quantity of the item that represents the inventory level threshold at which an RF operator is prompted to perform a cycle count immediately following a pick or an inventory transfer. For example, if the value is 20, then when the inventory level falls below 20 following a pick, the count is generated. If you set this field to zero (0), then a count is generated when the location is empty (remaining unit quantity is 0). |
| Count Threshold Cost | Monetary value threshold for an inventory count discrepancy. If the monetary value of an inventory count discrepancy is less than or equal to this value, a secondary count will not be generated. This value is used to prevent generating a secondary count for minor discrepancies. For example, if this value is 100, and a count discrepancy of 50 occurs, then a secondary count is not generated (if one was configured to occur for the count type). The count threshold cost defined for an item overrides the count threshold cost defined for a warehouse. When determining a value for threshold, take into consideration the value specified in the **Unit Cost** field for the item. |
| Count Threshold Unit | Unit quantity threshold for an inventory count discrepancy. If an inventory count reveals a discrepancy that is less than or equal to this value, a secondary (audit) count is not automatically generated. This value is used to prevent generating a secondary count for minor discrepancies. For example, if this value is 100, and a count discrepancy of 50 occurs, then a secondary count is not generated (if one was configured to occur for the count type that was performed). The count threshold unit for an item overrides the count threshold unit defined for the warehouse. |
| ABC Code | Code that determines how often the item is counted in a single count period. Select an ABC code if the application is configured to generate cycle counts by item automatically. The frequency assigned to each ABC code is defined in inventory counting settings. You typically select a code based on the value of the item; for example, assign the A code to expensive items that you want to closely monitor, and the C code to items to do not need to be counted as often. |
| Re-Order Point | Amount of inventory that specifies when this item should be reordered. When inventory levels within the warehouse reach this point, the item should be reordered at the specified reorder quantity. Re-Order Quantity and Re-Order Point can be used in custom reports or custom processes to inform the host when the item needs to be re-ordered and in what quantity. |
| Re-Order Quantity | Amount of inventory to reorder when the inventory levels within the warehouse reach the reorder point. Re-order Quantity and Re-order Point can be used in custom reports or custom processes to inform the host when the item needs to be re-ordered and in what quantity. |
| Serialization Level | LPN level at which you require serial numbers for the item or item/client combination to be captured. Do not select an LPN level if the item does not require serial number tracking.<br>-   • **LPN (Pallet)**: Highest UOM defined for the item footprint.
<br>-   • **Sub-LPN (Case)**: UOM defined as the Case UOM in the item footprint.
<br>-   • **Detail LPN (Box)**: Smallest UOM defined for the item footprint. |
| Serialization Type | Method that determines when serial numbers are captured for the item (or item and client combination). Do not select a serialization type if the item does not require serial number tracking. You cannot change this value when inventory exists for an item.<br>-   • **Cradle to Grave**: Serial numbers are captured during receiving and anytime the inventory quantity is changed, and they are validated during every partial move or transfer. Serial numbers are also captured during manual pick confirmation.
<br>-   • **Outbound Capture Only**: Serial numbers are captured during outbound processes, after picking and after packing. |
| Delay Outbound Serial Capture Until Packing | If Yes, then if inventory is directed to a pack station after picking, the application prompts the operator to capture serial numbers during pack station processing instead of during picking. If Yes is selected, and inventory is not directed to a pack station after picking, then the application prompts the operator to capture serial numbers during picking.<br > If No, then the application prompts the operator to capture serial numbers during picking. |
| Serial Number Type | Identifier for a specific kind of serial number. A serial number type defines the order in which the operator is prompted to enter serial numbers when multiple types are required for an item, whether serial numbers of this type are reported to the host, and the number mask that is used to verify that a valid serial number has been entered. |
| Sub-LPN Configuration | User-defined code that the application can use to verify serial numbers at the case level. A sub-LPN configuration code is located in a specified position within a serial number. It enables the application to determine whether a valid serial number has been scanned. |
| Sub-LPN Configuration Position | Position within a serial number at which the sub-LPN configuration code begins. For example, if you want the code to begin at the eighth position within a serial number, the configuration position would be 8. |
| Detail Configuration | User-defined code that the application can use to verify serial numbers at the detail level. A configuration code is located in a specified position within a serial number. It enables the application to determine whether a valid serial number has been scanned. |
| Detail Configuration Position | Position within a serial number at which the detail configuration code begins. For example, if you want the code to begin at the eighth position within a serial number, the configuration position would be 8. |
| Catch Code | Code that the application uses to determine if and when it should capture catch unit measurements for the item during processing. Catch unit measurements are variable weights or sizes of inventory that may exist within the same material handling (stock keeping) unit. For example, cases of frozen turkeys may vary in weight, and so in addition to the quantity of cases you can capture the weight of each case. Select a catch code only if the item is tracked by a catch unit type, such as weight or length. You cannot change the catch code while inventory for this item exists in the warehouse.<br > **Note**: If the Delay Capture Until Loading field is set to Yes for the warehouse (inventory settings) and client (in a 3PL environment), then the application does not prompt operators to capture catch quantity during picking. Instead, the application requires that operators capture catch quantity before the inventory is loaded on transport equipment. However, the application still prompts for a catch quantity during other processes as required by the catch code, such as during receiving or a cycle count.<br>-   • **Catch from Cradle to Grave**: Catch unit measurements are captured during each warehouse process from the time the item is received to the time it is shipped. If you select this option, then the application requires that catch unit measurements are captured during receiving and shipping (picking), as well as during inventory processes such as movements, adjustments, and counts. When you capture from cradle to grave, the most recently captured catch quantity value is displayed on inventory pages in the application.
<br>-   • **Catch on Receiving and Shipping**: Catch unit measurements are captured when the item is received and when it is shipped (picked). If you select this option, then the application requires that catch quantity is captured during receiving and shipping, but not when the item is involved in other inventory processes in the warehouse such as inventory adjustments and counts. When you capture only during receiving and shipping, the catch quantity value displayed on inventory pages in the application is 0 (zero). This is because the value is sent to the host when the item is received, and the catch quantity is no longer needed in the application until the item is picked.
<br>-   • **Catch on Shipping**: Catch unit measurements are only captured when the item is shipped (picked). If you select this option, then catch measurement units are not captured during receiving or during other inventory management processes. However, operators are required to capture a catch value when the item is picked for an outbound order or work order. |
| Catch Unit Type | Unit of measure, such as feet, gallons or pounds, to use when capturing catch weight measurements. This value may not be changed while inventory exists for this item. Only available if a catch code is selected for the item. |
| Average Catch | If Yes, indicates that you want to enable average catch quantity capture for the item. Average catch quantity capture allows the operator to specify a total gross quantity per planned inbound order line. The application determines the average catch quantity by dividing the total gross quantity by the number of units on the planned inbound order line. This is done instead of capturing a specific catch quantity for each unit. For example, if the gross quantity for an inbound order line for 20 cases of meat is 200 pounds, then the average catch quantity for each case of meat is 10 pounds (200 / 20 = 10).<br > If No, the application requires the operator to enter a catch quantity for each LPN. |
| Catch Unit Weight | Weight of one catch unit of the item. Enter a catch unit weight when weight is not the item's catch unit type, but you want to capture the weight of the catch unit type. For example, if you track carpet by the roll with a catch unit type of yards, but the host application also needs the weight for shipping purposes, you can enter the weight of one yard of the carpet in the Catch Unit Weight field. This allows the host to calculate the weight of entire roll of carpet. Only available if a catch code is selected for the item. |
| Minimum Catch Quantity | Minimum catch quantity per stocking unit of measure. Enter a value that represents the lowest acceptable catch quantity that you accept for a unit of the item. During inventory identification, if the operator enters a lower catch quantity when capturing the actual catch quantity measurement, the application displays a message stating that the quantity is unacceptable and not allowed. This is helpful in alerting the operator to either an inaccurate entry or unacceptable inventory. Only available if a catch code is selected for the item. |
| Maximum Catch Quantity | Maximum catch quantity per stocking unit of measure. Enter a value that represents the highest acceptable catch quantity that you accept for a unit of the item. During inventory identification, if the operator enters a higher catch quantity when capturing the actual catch quantity measurement, the application displays a message stating that the quantity is unacceptable and not allowed. This is helpful in alerting the operator to either an inaccurate entry or unacceptable inventory. Only available if a catch code is selected for the item. |
| Catch Unit Cost | Cost of one catch unit, as specified by the **Catch Unit Type** field, of the item; for example, cost per pound or cost per linear foot. Catch quantity cost information is used in inventory reports. |

## Processing fields

 
| Field | Description |
| --- | --- |
| Receivable | If Yes, users can receive inventory for this item. Select Yes only if the necessary information for this item has been entered in the application.<br > If No, and the NON-RCV service is configured and enabled, then the first time that an operator attempts to identify inventory for this item, an error message is displayed, and the inventory cannot be received until item attributes are verified and updated in the application, if necessary, and this field is set to Yes. Typically, the **Receivable** field is set to No when new item information is sent to Warehouse Management from a host that is not able to supply all of the information that is needed to store and ship the item. Many host applications do not maintain a footprint code or dimensional information for items, so the host sends the new item information to Warehouse Management, but leaves the unknown information blank and this field set to No. |
| Pick Replacement | If Yes, then the item is eligible for pick replacement. Pick replacement is the process by which the application automatically changes the source location (typically in a storage zone) of an outstanding pick or replenishment with a location in a receiving zone (such as a receiving dock door or production location) that has been enabled for pick replacement. For example, with pick replacement enabled, received inventory can be used to satisfy a pick and moved directly from receiving to the customer order's destination location. Additional configuration is needed for pick replacement to happen. Click the Help icon to see more information on pick replacement processing in the online help.<br > **Note**: While pick replacement processing saves travel time, you must also consider whether this is good practice with date-tracked inventory. If enabled for date-tracked items, the process can result in fulfilling picks with newer inventory than that which may exist in storage.<br > If No, then the item is not eligible for pick replacement. |
| Allow Opportunistic Cross Docking | If Yes, then the item can be used for opportunistic cross docking. Opportunistic cross docking occurs when inventory is received and moved directly to ship staging (or other cross dock location) to satisfy a short order line. A short is created when an order line that is not marked for planned cross docking is allocated and there is insufficient inventory.<br > If No, then the application prevents opportunistic cross docking of the item to fulfill short order lines.<br > **Note**: This field does not affect planned cross docking (when the order line is marked for cross docking) or pick replacement. |
| Pick to Box | If Yes, the item picked at a certain LPN level, such as eaches, needs to be picked to a box before being added to a picking carton. If selected, then during cartonization, the footprint of the box will be considered instead of the footprint of the item. Therefore, if Yes, you should define a repack class for the item that is same as the repack class defined for the small box.<br > If No, the item does not need to be picked to a box before cartonization. |
| Threshold Pick Variance | Variance percentage over or under the required pick quantity. If an operator picks a quantity greater than or less than that which is required for the pick, and the quantity exceeds the Threshold Pick Variance, then a message is displayed to the operator that requires the operator to acknowledge the pick is over or under the allowed variance. A value of zero means a message will always be displayed when a pick does not match the required pick quantity; a value of 100 means that the message will never be displayed. |
| Reservation Unit Of Measure | When order reservation, which is a process that reserves inventory for orders prior to the actual allocation, is used at a facility, the reservation unit of measure indicates the minimum quantity of this item that can be reserved during a reservation. For example, if the reservation unit of measure is cases, and the units per case for this item is four, then this item will be reserved for orders in increments of four. |
| Commodity Code | Code that identifies a commodity. Commodities are categories created to group inventory that has the same qualities and specifications, regardless of their source. For example, wheat is a commodity. Commodity codes are standardized to provide carriers with a standard by which to determine pricing and to simplify the shipment process. The Commodity Code is usually printed on the bill of lading (BOL). If the commodity is printed on the BOL, all products of the same commodity are totaled. |
| Freight Class | Standardized code, ranging from 50 to 500, that classifies the kind of freight being carried. Freight class is used as the product basis in the over-the-road industry. The higher the freight class, the more carriers will charge to transport it. Factors such as value, density, and hazardous nature determine the freight class. |
| STCC | Standard Transportation Commodity Code (STCC) is a coding system used in the rail industry for freight classification. Moving from left to right, each additional digit of an STCC tells more information about the commodity being transported. STCCs are the rail equivalent of freight classes, which are used by TL and LTL carriers. |
| Parcel | If Yes, the item can be shipped using a parcel or small package carrier such as UPS or RPS.<br > If No, the item cannot be shipped using a parcel or small package carrier. |
| Hazardous Material | If Yes, the item should be treated as hazardous. This field does not impact processing unless the attribute is used as criteria in configurations such as a storage search path or work assignment rules. If the **Hazardous Material** field for an item is set to Yes, the Hazardous tag is also applied (on application pages) to LPNs, order, and shipments that contain the item. The hazardous material designation can be used in conjunction with item classes. See [Item Classes](../../configuration/inventory/items/item-classes.md).<br > **IMPORTANT**: Warehouse Management designation of hazardous materials related to this functionality in no way implies compliance with federal or international regulations pertaining to the storage, processing, and transport of such materials.<br > If No, the item is not considered to be hazardous. |
| Insurance Required | If Yes, insurance is required for this item. When insured items are cartonized with uninsured items, only those items in the carton configured to require insurance (this field set to Yes) will be insured. Insurance will use the item's unit cost to calculate the amount of insurance. Insurance is not included in rate shopping when the application shops for the best rate for the package.<br > If No, the item will not be insured. |
| Customs Item Type | Category that defines the type of customs tracking that is required for the item. Only displayed if Customs functionality is enabled.<br>-   • **Customs**: Customs duties need to be paid for the item. Available if the address for the warehouse is designated as a Customs site type.
<br>-   • **Excise**: Excise duties need to be paid for the item; customs duties may also be required. Available if the address for the warehouse is designated as a Customs and Excise site type.
<br>-   • **No selection (blank)**: Inventory for the item is not bonded. |
| Customs VAT Code | Code for the value added tax (VAT) for the item. A customs VAT is charged on goods and some services that are imported from countries outside the European Unit (EU) and brought into the United Kingdom (UK) from other EU countries. It is also charged on most goods and services that VAT-registered businesses provide in the UK.<br>-   • **Standard**: The standard customs VAT rate is charged for this item.
<br>-   • **Zero**: No customs VAT is charged for this item. |
| Customs Commodity Code | Commodity code that is used by a duty management application to determine the type of duty to be paid for this item. The code must match a commodity code that is defined in the duty management application; Warehouse Management does not validate this code. |
| Default Country | Country in which the item was manufactured. This value is displayed by default on the planned inbound order line for the item, but can be changed during receiving. Only available if the value for **Customs Item Type** is either **Customs** or **Excise**. |
| Duty Stamp Tracked | If Yes, the item requires a duty stamp. Select Yes if the value for **Customs Item Type** is **Excise** and the item contains over 30% alcohol by volume in containers that are 35 cubic liters or larger.<br > If No, the item does not require a duty stamp.<br > Only available if the value for **Customs Item Type** on the order is **Excise**. |
| Customs Cost | Monetary amount that is paid to customs for the item. The amount is paid in the currency defined in the currency field. Only available if the **Customs Item Type** is either Customs or Excise. |

## Inventory Attributes fields

 
| Field | Description |
| --- | --- |
| LPN | Unique identifier for inventory. Typically, an LPN refers to a pallet; however, it can refer to inventory received at less than pallet quantity. The LPN is the license plate by which the inventory is tracked in the facility. |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Lot | Identifier assigned to a quantity of an item during the manufacturing process for the purpose of tracking an attribute of that item, such as an expiration date. Lots differentiate distinct groups of inventory with the same item number. Items that may require a lot number include pharmaceuticals, fabrics, food, and other products with limited shelf life. Lots are user defined and are not necessarily unique since the same lot number can be applied to different items. However, lot and item combinations must be unique. |
| Origin Code | Identifier assigned to an item to identify the item's country of origin. It is typically used for export paperwork. Origin codes are user defined. |
| Revision Level | Identifier that is assigned to an item number to differentiate revisions of the same item number. |
| Supplier | Identifier for a supplier. A supplier can be an individual, organization, or another warehouse within your own organization from which you repeatedly receive inventory or handling units. |
| Supplier Lot | Identifier that is an attribute of an item or item and lot combination and is assigned by the item's supplier. A supplier lot number used to uniquely identify and track the inventory to which it is assigned. The supplier lot number is a different attribute than the lot number, which is a manufacturer or production lot number. |
| Consignment Change Point | Value that determines when ownership of consigned inventory is transferred from the supplier to the warehouse. The consignment values defined for the supplier item override those defined for the supplier, which override those defined for the warehouse.<br>-   • **Consignment Days**: Ownership is transferred after the specified number of consignment days (defined in the **Consignment Days** field) have passed.
<br>-   • **Putaway**: Ownership is transferred when the putaway work for the inventory is complete.
<br>-   • **Receipt**: Ownership is transferred when the inventory is received by the warehouse.
<br>-   • **Transport Equipment Close**: Ownership is transferred when the outbound transport equipment on which the consigned inventory is loaded is closed.
<br>-   • **Transport Equipment Dispatch**: Ownership is transferred when the outbound transport equipment on which the consigned inventory is loaded is dispatched. |
| Consignment Days | Number of days after receiving consigned inventory that the ownership is transferred from the supplier to the warehouse. If **Consignment Days** is selected as the change point, then this value represents the number of days after receipt during which the supplier has ownership of the consigned inventory. A schedule-based job is configured to run daily to determine when the specified number of consignment days has passed, at which point ownership is transferred to the warehouse.<br > **Note**: The application sets the consignment end date for inventory on an ASN shipment based on when the inventory was received and put away to storage. For non-ASN shipments, the application sets the consignment end date based on when the inventory was identified. For example, if the Consignment Days value is 30, then when an ASN shipment is received, the consignment change point is 30 days from when the inventory is put away to storage; when a non-ASN shipment is received, the change point is 30 days from when the inventory is identified. |
| Remaining Consignment Days | Number of days remaining to transfer the ownership from the supplier to the warehouse, calculated based on the current date and the consignment end date. If **Consignment Days** is selected as the **Consignment Change Point**, then this value represents the number of days after receipt during which the supplier retains ownership of the consigned inventory. Only available if the change point is Consignment Days. |
| Consignment End Date | The date at which the ownership of the inventory is transferred from the supplier to the warehouse. Only available if the change point is Consignment Days. |
| Handling Unit | Unique identifier for a handling unit that is tracked as an individual as well as collectively by handling unit type. You may want to track valuable handling units, such as CHEP pallets, as individuals. All transport equipment handling units are tracked as individuals. Handling units tracked as individuals can be further identified with a serial number. |
| Rotation | Unique identifier that the application generates and automatically assigns to bonded inventory during receipt of that inventory into a bonded warehouse. The rotation ID is tracked with the inventory as long as the inventory is in the warehouse. |
| Under Bond | If Yes, then the inventory is bonded. Bonded inventory is inventory for which customs duties and excise duties are required and have not yet been paid.<br > If No, then the inventory is not bonded. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
