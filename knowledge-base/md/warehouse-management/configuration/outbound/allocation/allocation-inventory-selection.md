---
title: "Allocation Inventory Selection"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/allocation_inventory_selection.htm"
source: "/content/allocation_inventory_selection.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Outbound"
  - "Allocation"
  - "Allocation Inventory Selection"
sections:
  - "Configure allocation inventory selection settings"
  - "Allocation Inventory Selection fields"
images: []
source_sha1: f0806db46a25356ae5d658159c50d51547fc37bd
---
# Allocation Inventory Selection

Inventory selection is the process by which the application selects inventory to fill a shipment line.

Inventory selection settings control the following processes:

-   Whether allocation is prevented in locations that contain both restricted and unrestricted lots
-   When picks for identical inventory can be combined for consolidated picking
-   The order in which inventory in a location is sorted prior to selection
-   Date processing attributes that control how date-tracked inventory is selected for allocation, including how the application selects from inventory with the same date
-   Whether to include movement zones during allocation when searching for inventory for an absolute date rotation method. See [Movement zones for absolute inventory rotation allocation](inventory-rotation-allocation.md).

**Note**: By default, the application sorts inventory for allocation in the following order:

1.  By location (sequenced in the order in which the locations are found)
    
2.  By date (only for date-tracked inventory)
    
3.  By mixed-item LPNs (only for non date-tracked inventory, mixed LPNs are prioritized over single-item LPNs)
    
4.  By units per pallet (only for non date-tracked inventory, pallets with more units are prioritized)
    
5.  By LPN quantity (LPNs with greater quantity are prioritized)
    

## Configure allocation inventory selection settings

1.  Select **Configuration > Outbound > Allocation > Allocation Inventory Selection**.
2.  Enter information in the [Allocation Inventory Selection fields](#Allocation_Inventory_Selection_fields).
3.  To define the pick zones in which the application should not allocate from a location that contains both restricted and unrestricted lots:
    
    **Note**: For more information, see [Item lot restrictions](../../inventory/items/items.md).
    
    1.  Under **GENERAL**, click **Prevent Allocation for Mixed Lot Statuses**.
    2.  In the **Available** column, select the pick zones in which the application should not allocate from a location that contains both restricted and unrestricted lots.
    3.  Click **Apply**.
4.  To select the criteria that must match for individual picks to be grouped together for allocation:
    
    **Note**: Based on the criteria that you select, the application combines the quantities on multiple identical order lines and then allocates the consolidated pick quantity. For example, if set to Shipment, the application combines the quantities from multiple identical order lines for the same shipment.
    
    1.  Under **EVALUATE INVENTORY DURING ALLOCATION**, click **Consolidated Picking**.
    2.  In the **Available** column, select the criteria to use.
        
        **Note**: In the grid, press and hold **Shift** to select consecutive values or press and hold **Ctrl** to select nonconsecutive values.
        
    3.  Click **Apply**.
5.  To specify the order in which LPNs of inventory are sorted within a location based on one or more attributes: 
    
    **Note**: **Inventory in Location Sort** is applied after allocation to ensure the consumption of proper inventory during picking.
    
    1.  Under **EVALUATE INVENTORY DURING ALLOCATION**, click **Inventory in Location Sort**.
    2.  To select criteria from displayed entities:
        1.  If the advanced query is displayed, click **Simple**.
        2.  If the available entities are not displayed, click **Show Available**.
        3.  In the **Available** grid, select the entities that you want to use as criteria.
        4.  Click **Add selected**. The entities are added to the **Selected** grid.
        5.  To remove criteria, in the **Selected** grid, select the criteria to remove, and click **Remove selected**.
        6.  To reorder the criteria, in the **Selected** grid, click a row, and then click the up or down arrow to move the selected criteria. The application applies the criteria in sequential order according to how it is displayed in the grid.
    3.  To enter criteria using database entities, click **Advanced**, and then enter the column and field name, using a period to separate the column and field. Multiple column and field entries must be separated by a comma and space.
        
        You can use operators like IS NULL or IS NOT NULL to build an advanced query. For example, <column name>.<field name > IS NOT NULL, <column name>.< field name>.
        
        **Note**: If you need assistance configuring criteria using database entities, contact your Blue Yonder project team.
        
    4.  Click **Apply**.
6.  To define the precedence that determines which outbound date window is used based on the level at which they are defined, under **DATE PROCESSING**, in the **Date Window Precedence** table, drag an entity to the sequence in which you want it to be used.
    
    **Notes**:
    
    -   A date window can be specified at each of the levels listed in the table under Date Window Precedence (for example, for a specific order line, customer item, and item). The sequence determines the order in which the application looks for a date window to apply during allocation. For example, if sequence 1 is Order Line but a date window was not defined for the order line, the application looks to the next entity in the sequence, such as Customer Item.
    -   The date window precedence applies to both allocation and replenishments. However, the replenishment configuration in the sequence is only used if the application is processing a replenishment; the allocation configuration in the sequence is only used if the application is allocating inventory for an order or work order.
    
7.  To define a location sort of inventory:
    
    **Note**: If inventory that meets the order criteria exists in multiple locations, the location sort determines the sequence in which to sort that inventory for selection. The default value is to sort by quantity, but this can be overridden for any inventory rotation method.
    
    1.  Under **DATE PROCESSING**, click **Location Sort**.
    2.  Perform one of the following tasks:
        -   To define a location sort of inventory that has the same date, under **SECONDARY SORT**, click the inventory rotation method to define.
        -   To define a location sort of inventory using location attributes, under **NON-DATE SORT**, click **Location Order By**.
    3.  If inventory with the best date based on the inventory rotation method must be used to fulfill the order line, then set the **Inventory Must Match Inventory Rotation Method** field to Yes. See [Inventory must match inventory rotation method](inventory-rotation-allocation.md).
    
    **Note**: The **Inventory Must Match Inventory Rotation Method** field is only available for absolute inventory rotation methods (FIFO ABS, FEFO ABS, LIFO ABS, LEFO ABS).
    
    5.  If inventory with the next best date based on the inventory rotation method can be used to fulfill the order line and the **Inventory Must Match Inventory Rotation Method** field is set to Yes, then set the **Continue to Allocate Inventory Beyond Best Date** field to Yes. See [Continue to Allocate Inventory Beyond Best Date](inventory-rotation-allocation.md).
        
        **Note**: If this field is set to Yes and an order line does not allow case splitting, the application's behavior when encountering a partial case of best-date inventory is determined by the **Ignore Partial Cases for Strict Absolute Date Allocation** field. If the **Ignore Partial Cases for Strict Absolute Date Allocation** field is set to Yes, then the application allocates any full cases with the same date as the partial case, skips the partial case, and continues to allocate the next best-date inventory. If the **Ignore Partial Cases for Strict Absolute Date Allocation** field is set to No, then the application allocates any full cases with the same date as the partial case, but the remaining quantity for the order line is shorted.
        
    6.  To select criteria from displayed entities:
        1.  If the advanced query is displayed, click **Simple**.
        2.  If the available entities are not displayed, click **Show Available**.
        3.  In the **Available** grid, select the entities that you want to use as criteria.
        4.  Click **Add selected**. The entities are added to the **Selected** grid.
        5.  To remove criteria, in the **Selected** grid, select the criteria to remove, and click **Remove selected**.
        6.  To reorder the criteria, in the **Selected** grid, click a row, and then click the up or down arrow to move the selected criteria. The application applies the criteria in sequential order according to how it is displayed in the grid.
    7.  To enter criteria using database entities, click **Advanced**, and then enter the column and field name, using a period to separate the column and field. Multiple column and field entries must be separated by a comma and space.
        
        You can use operators like IS NULL or IS NOT NULL to build an advanced query. For example, <column name>.<field name > IS NOT NULL, <column name>.< field name>.
        
        **Note**: If you need assistance configuring criteria using database entities, contact your Blue Yonder project team.
        
    8.  Click **Apply**.
8.  To select the movement zones to search when an absolute inventory rotation method is specified (such as on the order line or for an item):
    
    **Note**: See [Movement zones for absolute inventory rotation allocation](inventory-rotation-allocation.md).
    
    1.  Under **DATE PROCESSING**, click **Non Allocation Search Path Zones for Absolute**.
    2.  In the **Available** column, select the movement zones that apply.
        
        **Note**: For a 3PL environment, you select movement zones for each client.
        
    3.  Click **Apply**.
9.  Click **Save**.

## Allocation Inventory Selection fields

 
| Field | Description |
| --- | --- |
| Force Full Case | If Yes, the pick quantity for pallet picks must be a multiple of the specified units per case defined on the order line. If set to Yes, and if the order line is configured to allow split cases (the **Case Splitting** field is set to Yes), then only pallets that contain quantities matching the specified units per case are considered for allocation. Select Yes if you want the application to ignore the split case option on the order line when allocating full pallet picks to ensure that only full cases are picked.<br > If No, the pick quantity for pallet picks does not have to be a multiple of the specified units per case defined on the order line. |
| Default Rotation Method | Inventory rotation method that is applied by default during allocation if an inventory rotation method was not specified for any other entity in the application's fixed order of precedence. The application uses the inventory rotation method based on the following order of precedence: order line or work order line, customer item, item, customer (ship to), customer type, client, and default rotation method. See [Inventory rotation methods](inventory-rotation-allocation.md). |
| Enable Outbound Date Window | If Yes, the application uses the outbound date window, if specified. If selected, then when allocating FEFO/FIFO/LEFO/LIFO order lines, the application can allocate inventory with expiration or receiving dates that fall within a configured window of time, even if inventory that is closer to or matches the exact expiration or receiving date for FEFO/FIFO/LEFO/LIFO order allocation is available. The window of time is defined by the value for **Outbound Date Window**.<br > If No, the application does not consider an outbound date window, defined at any level, when performing inventory allocation for order lines to which a FEFO/FIFO/LEFO/LIFO inventory rotation method has been assigned. |
| Outbound Date Window | Amount of time in relation to the inventory’s received date or expiration date during which inventory is considered the same age for allocation when one of the FEFO/FIFO/LEFO/LIFO or absolute FEFO/FIFO/LEFO/LIFO inventory rotation methods is required. The available time units include minutes (m), hours (h), or days (d). For example, an entry of "5h" defines the window (5) and unit (hours). During allocation, the application uses the assigned date window based on a pre-defined order of precedence. See [Allocation Inventory Selection](#). |
| Ignore Partial Cases for Strict Absolute Date Allocation | If Yes, then when the application uses an absolute inventory rotation method to allocate inventory for an order line that does not allow case splitting, partial case quantities are ignored and the application continues to allocate full cases of the next best-date inventory.<br > If No, then when the application finds a partial case quantity during allocation of an order line that does not allow case splitting, after allocating any full cases of best-date inventory, the remaining quantity on the order line is shorted.<br > **Note**: This field is only applicable when the **Inventory Must Match Inventory Rotation Method** and **Continue to Allocate Inventory Beyond Best Date** fields are both set to Yes in the location sort settings for the absolute inventory rotation method.<br > For example, assume an order line requires 5 cases of inventory that must be allocated using the absolute FEFO rotation method, and the order line does not allow case splitting. Also assume that there are 3 full cases of best-date inventory, 1 partial case of best-date inventory, and 2 full cases of next best-date inventory. If this field is set to Yes, then after allocating the 3 full cases of best-date inventory, the application ignores the partial case quantity and continues to allocate the 3 cases of next best-date inventory to fulfill the order line. If this field is set to No, then after allocating the 3 full cases of best-date inventory, the application shorts the remaining quantity (2 cases) because the partial case quantity cannot be allocated or bypassed. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
