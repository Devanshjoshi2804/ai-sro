---
title: "Order Line Mass Update"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/order_line_mass_update.htm"
source: "/content/order_line_mass_update.htm"
toc_path:
  - "Warehouse Management"
  - "Shared functions"
  - "Order Line Mass Update"
sections:
  - "Perform order line mass update"
  - "Order Line Mass Update fields"
images: []
source_sha1: b542ea47c336ceb90ae3a901b0e7af597546ab38
---
# Order Line Mass Update

The Order Line Mass Update page is accessible from the following modules: **Outbound Planner**, **Picking**, or **Shipping**.

A mass order update is a manual update made to one or more order lines that are associated with a shipment. You can update order lines, for example, to change the inventory rotation method for allocation, or you may want to change the packaging footprint code for multiple orders.

**Note**: Order lines that do not have a shipment cannot be mass updated.

The grid on the Order Line Mass Update page displays the following color codes to indicate whether an order can be updated based on the order’s status and the order mass update restrictions:

-   **Red**: Order line is restricted from being updated.
-   **Yellow**: Order line can be updated with a warning and user confirmation.
-   **Green**: Order line is allowed to be updated.

For more information on configuring the restrictions for mass order line updates, see [Configure order processing settings](../configuration/outbound/order-processing/outbound-order-settings.md).

## Perform order line mass update

You can query for orders that you want to change, and then for multiple selected orders, update the attribute values in one process instead of having to change the attribute for each individual order line.

While performing order line mass update, you can mark order lines for cross docking at any time before the order is allocated. You can mark existing order lines for cross docking, and you can remove cross docking from order lines before the order lines are processed.

After a mass update is processed, the results to determine whether the action was successful are displayed. If an updated value is not applicable to one or more order lines, a failure message is displayed. For example, an order line cannot be updated with a footprint that is not applicable to the item in the order line.

1.  View the Order Line Mass Update page.
    
    1.  Select one of the following modules: **Outbound Planner**, **Picking**, or **Shipping**.
    2.  Select **Order Line Mass Update**.
    
2.  In the filter, enter the search criteria to select the order lines to update.
    
    **Note**: To view order lines that contain a single item, select the **Single Item Orders** check box.
    
3.  Click **Update Order Lines**. The Update Order Lines window is displayed.
4.  To manage additional fields that are available for mass update:
    1.  Click **Manage**. The Mass Update Attributes Maintenance window is displayed.
    2.  To add fields for mass update, in the **Available** column, select the check box next to each field.
    3.  To remove fields from mass update, in the **Available** column, deselect the check box next to each field.
    4.  Click **Save**.
5.  On the Update Order Lines window, select the check box next to each attribute you want to update, and then enter information in the applicable [Order Line Mass Update fields](#Order_line_mass_update_fields).
    
    **Note**: The order lines to modify are displayed based on the attributes selected. If you select the check box next to an attribute, but do not provide a new value, the existing values for that attribute across the selected order lines to update will be cleared.
    
6.  Click **Save**.

## Order Line Mass Update fields

 
| Field | Description |
| --- | --- |
| Inventory Rotation Method | Value that represents the order in which the allocation process selects available inventory for allocation. Select an inventory rotation method if you want the application to search for inventory based on date processing or location.<br>-   • **FEFO-ORDER-BY and FEFO-ORDER-BY-ABSOLUTE**: First-expiration, first-out. The first inventory to expire will be selected first.
<br>-   • **FIFO-ORDER-BY and FIFO-ORDER-BY-ABSOLUTE**: First-in, first-out. The oldest inventory will be selected first.
<br>-   • **LEFO-ORDER-BY and LEFO-ORDER-BY-ABSOLUTE**: Last-expiration, first-out. The last inventory to expire will be selected first.
<br>-   • **LIFO-ORDER-BY and LIFO-ORDER-BY-ABSOLUTE**: Last-in, first-out. The newest inventory will be selected first.
<br>-   • **LOCATION-ORDER-BY**: Locations are ordered within a pick zone (maintaining the allocation search path order) by the location attributes specified for the **Location Sort** field in inventory selection settings.
<br>-   •
    
    **No selection (blank)**: The application uses the inventory rotation method of the highest defined level of precedence. For information on precedence, see [Inventory rotation allocation processing](../configuration/outbound/allocation/inventory-rotation-allocation.md).
    
    <br>
    
    **Note**: Inventory rotation methods defined at a lower precedence (except the default method) are automatically copied to the order line or work order line when the line is created. For example, if an order line is created for a date-tracked item with a rotation method defined, the rotation method is copied from the item to the order line, and then the application uses the order line rotation method during allocation.
    
    <br > If no inventory rotation method is defined at any level, then the application uses the allocation search path sequence and allocates the first available inventory it finds that matches all of the required attributes.
<br > When using inventory rotation methods that are not absolute, the application searches for inventory by allocation search path in sequence until it finds a pick zone that contains the inventory, and then allocates inventory that is closest to the preferred processing date. Therefore, the application stops searching at the first pick zone in which matching inventory is found.<br > When using absolute inventory rotation methods, the application searches either all of the allocation search paths for inventory that is closest to the preferred processing date or, if absolute groups are defined, each absolute group in sequence until it finds matching inventory and then allocates inventory that is closest to the preferred processing date from the pick zones within the absolute group. Therefore, the absolute method allows for more a comprehensive search to find the inventory. |
| Allocation Search Path Group | Name associated with allocation search paths for the purpose of grouping them for use during order allocation. If a search path group is specified on the order line, the application uses only the search paths that have a matching group name to find inventory for that order. This process reduces processing time by limiting the number of search paths the application uses during order allocation.<br > An allocation search path group can be assigned to a customer type, order line, allocation search path, and replenishment search path. |
| Footprint | Name that identifies a footprint, which describes the packaging dimensions and units of measure for the item with which it is associated. |
| Rule Name | Name of the allocation rule. An allocation rule is a processing command that specifies the inventory attribute values that are acceptable to fulfill an order line, work order detail, work order line, or bill of materials (BOM) detail. |
| Cross Dock | If Yes, then when the inventory specified on this outbound order or work order line is identified, it is moved directly from receiving to a cross dock location or a specified staging location to satisfy an outbound order or work order. If you select Yes, inventory for this order line must be cross-docked; the application will not allocate the inventory from storage.<br > If No, then the order or work order line does not use cross docked inventory. Select No if you want inventory for this order line to be allocated from storage. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
