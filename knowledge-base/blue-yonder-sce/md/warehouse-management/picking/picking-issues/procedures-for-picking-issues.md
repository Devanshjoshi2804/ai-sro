---
title: "Procedures for picking issues"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/procedures_for_picking_issues.htm"
source: "/content/procedures_for_picking_issues.htm"
toc_path:
  - "Warehouse Management"
  - "Picking"
  - "Picking Issues"
  - "Procedures for picking issues"
sections:
  - "View and manage inventory that is not pickable"
  - "View cancelled picks"
  - "View unallocated orders"
  - "View picked UOM discrepancies"
  - "Not Pickable fields"
  - "Cancelled Picks fields"
  - "Orders Not Allocated fields"
  - "Picked UOM Discrepancy fields"
images:
  - "/content/resources/images/image1083390.png"
source_sha1: 1f3790872778be3c14b3688a8132bdf17ff30631
---
# Procedures for picking issues

The following procedures can be performed on the issues identified on the Picking Issues page.

## View and manage inventory that is not pickable

For a description of the issue, see [Picking issue: Not pickable](../picking-issues.md).

1.  Perform one of the following tasks:
    -   Select **Picking > Picking Issues > Not Pickable**.
    -   Select **Inventory > Inventory Issues > Not Pickable**.
2.  View the information in the [Not Pickable fields](#Not_Pickable_fields_-_Picking_issues).
3.  To view location details, in the grid, click the current location. See [View detailed location information](../../shared-functions/inventory/procedures-for-locations.md).
4.  To change the configuration of a search path, in the **Zone not in Search Path** column, click **Resolve in Configuration**. See [Configure allocation search paths for order picks](../../configuration/outbound/allocation/allocation-search-paths.md).
5.  To reset a location that is out of service, in the **Location Out of Service** column, click **Resolve in Location**. See [Set or reset a location out of service](../../shared-functions/inventory/procedures-for-locations.md).
6.  To enable a location for picking, in the **Location not Pickable** column, click **Resolve in Location**. See [Modify a storage location](../../configuration/warehouse/locations/storage-locations.md).
7.  To assign a location to a pick zone, in the **No Pick Zone** column, click **Resolve in Configuration**. See [Modify a storage location](../../configuration/warehouse/locations/storage-locations.md).
8.  To resolve the issue of a non-pickable UOM, in the **UOM Not Pickable** column, click **Resolve in Configuration**. See [Configure allocation search paths for order picks](../../configuration/outbound/allocation/allocation-search-paths.md).

## View cancelled picks

For a description of the issue, see [Picking issue: Cancelled picks](../picking-issues.md).

1.  Select **Picking > Picking Issues > Cancelled Picks**.
2.  In the date field, select the date or date range by which to limit the cancelled picks that are displayed.
3.  Click **Go**.
    
    **Note**: The summary row displayed at the top of the grid shows the total number of cancelled picks, routes, customers, items, and pick quantities currently being displayed.
    
4.  To view all cancelled picks regardless of date, click **Clear** to remove the date filter, and click ![Refresh](../../../../images/resources/images/image1083390.png).
5.  View the information in the [Cancelled Picks fields](#Cancelled_Picks_fields).

## View unallocated orders

For a description of the issue, see [Picking issue: Unallocated orders](../picking-issues.md).

This page displays the orders that are planned into a wave, but are not allocated yet.

1.  Select **Picking > Picking Issues > Orders Not Allocated**.
2.  In the date field, select the dates to limit your search results to transactions that occurred within the selected time frame.
3.  Click **Go**.
    
    **Note**: The Departure column is filtered based on the selected date range.
    
4.  To view all unallocated orders regardless of date, click **Clear** to remove the date filter.
5.  View the information in the [Orders Not Allocated fields](#Orders_Not_Allocated_fields).

## View picked UOM discrepancies

For a description of the issue, see [Picking issue: UOM discrepancies](../picking-issues.md).

1.  Select **Picking > Picking Issues > Picked UOM Discrepancy**.
2.  In the date field, select the date or date range by which to limit the picked UOM discrepancies that are displayed.
3.  Click **Go**.
4.  To view all discrepancies regardless of date, click **Clear** to remove the date filter.
5.  View the information in the [Picked UOM Discrepancy fields](#Picked_UOM_Discrepancy_fields).

## Not Pickable fields

 
| Field | Description |
| --- | --- |
| Current Location | Location in which the inventory currently resides. |
| Pick Zone | Name of a pick zone. A pick zone represents a group of locations that share the same attributes for picking, such as the LPN level at which picks can be allocated, the cartonization group to which it belongs, and whether the location supports replacement picks and pre-inventory allocation. The search path searches pick zones when attempting to find inventory for allocation. |
| Zone not in Search Path | The **Resolve in Configuration** text in this column indicates that the pick zone is not assigned to an allocation search path rule. This issue prevents the application from allocating inventory from locations assigned to the pick zone. |
| Location Out of Service | The **Resolve in Location** text in this column indicates that the location is either disabled or in an error status, both of which prevent inventory activities such as allocation, picking, and putaway from taking place in the location. |
| Location not Pickable | The **Resolve in Location** text in this column indicates that the storage location is not configured to be a pickable location (the **Pickable** field is set to No). |
| No Pick Zone Assigned | The **Resolve in Configuration** text in this column indicates that the location is not associated with a pick zone. If the location is not associated with a pick zone, it is not included in an allocation search path and the application will not find the location when attempting fulfill an order. |
| UOM Not Pickable | The **Resolve in Configuration** text in this column indicates that the location is associated with a pick zone on an allocation search path rule, but the rule does not support picking inventory in the unit of measure (UOM) that the order requires. |

## Cancelled Picks fields

 
| Field | Description |
| --- | --- |
| Cancelled | Date and time when the pick was cancelled. |
| Cancel Action | Text that describes the cancel code. Typically, the description identifies the reason for the picking cancellation or the actions that occur after the cancellation. For example, a cancel code of CANCEL-NO-REALLOC can be used to indicate that the application does not reallocate inventory for the cancelled pick work. |
| User | User who cancelled the pick. |
| Customer | Name used to identify the business to whom the order with the cancelled pick is to be shipped. |
| Pick Location | Location from which the inventory should be picked to complete the order. |
| Item | Identifier for the item included in the cancelled pick. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Load | Unique identifier for a load. A load is one or more shipments grouped together into one or more stops that are shipped on a single piece of transport equipment. |
| Shipment | Unique identifier for an outbound shipment. A shipment is a group of orders or order lines that are allocated together and shipped to the same location. |
| Order | Unique number that identifies an order. An order is a request for a supply of material or product. |
| Pick Quantity | Quantity (in terms of material handling or stock keeping units) of the item that should be picked based on the order, work order, or replenishment. |
| Pick Status | Current status of the pick.<br>-   • **Pending**: Pick work inventory is reserved for allocation until automatically released by the application.
<br>-   • **Hold**: Pick work inventory is reserved for allocation until manually released by a user.
<br>-   • **Released**: Pick work is released to the work queue.
<br>-   • **Complete**: Pick work is complete.
<br>-   • **Un-Assigned**: Pick work is unassigned from a work assignment.
<br>-   • **Ready For List**: Pick work has been released and the pick is qualified for a work assignment. A background process builds these picks into either a handling unit-based or regular work assignment.
<br>-   • **Error**: Pre-manifesting the package for the pick work failed. The application allows packages to be pre-manifested; that is, manifested to hold. These packages are typically manifested during allocation (before the inventory is picked) and usually so that a label can be printed in advance for the package. You can view the specific error code and description on the Waves and Picks page. See [Waves and Picks](../../shared-functions/waves-and-picks.md). |
| Work ID | Unique application-assigned identifier for a piece of work in the work queue. |
| Pick Type | Type of pick that was cancelled. |
| Route | Name of the route on which the order with the cancelled pick is to be shipped. A route is a static schedule that defines the start and end times that inventory for one or more customers will be picked up from a warehouse for delivery to one or more stops. |

## Orders Not Allocated fields

 
| Field | Description |
| --- | --- |
| Departure | Date and time that the transport equipment associated with a load is scheduled to depart from the warehouse. |
| Load | Unique identifier for a load. A load is one or more shipments grouped together into one or more stops that are shipped on a single piece of transport equipment. Along with the unique identifier, the number of stops on the load are also displayed. |
| Transport | Alphanumeric identifier used to identify a piece of transport equipment associated with an outbound load or inbound shipment. Identifier for the carrier with which the transport equipment number is associated. |
| Order | Number of orders on the load that could not be allocated. An order is a request for a supply of material or product. |
| Order Line | Number of order lines that could not be allocated. |
| Shipment | Number of shipments and shipment lines that could not be allocated. A shipment is a group of orders or order lines that are allocated together and shipped to the same location. |
| Customer | Number of customers that placed orders on the load for which inventory could not be fully allocated. Each customer has a profile that is used to define how their inventory is handled, how their orders are processed, and how their inventory is shipped. |

## Picked UOM Discrepancy fields

 
| Field | Description |
| --- | --- |
| Date | Date on which the inventory was picked. |
| User | User who picked the inventory. |
| Work Reference | Unique application-assigned identifier for a piece of work in the work queue. |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Expected Pick Quantity | Quantity of the item that was specified by the work reference. |
| Expected UOM | Unit of measure for the pick that was specified by the work reference. |
| Actual Pick Quantity | Actual quantity of the item that was picked for the work reference. |
| Actual UOM | Actual unit of measure in which the item was picked for the work reference. |
| Footprint Code | Name that identifies a footprint, which describes the packaging dimensions and units of measure for the item with which it is associated. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
