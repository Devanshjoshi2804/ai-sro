---
title: "Units of Measure"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/units_of_measure.htm"
source: "/content/units_of_measure.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inventory"
  - "Units of Measure"
sections:
  - "Add or modify a UOM"
  - "Delete a UOM"
  - "Configure the display sequence for units of measure"
  - "Units of Measure fields"
images: []
source_sha1: ec73a45016ed7444f667f672465f4840fff1d1a9
---
# Units of Measure

A unit of measure (UOM) refers to the packaging unit in which an item is received, added, counted, or modified. UOMs are used in item footprint configurations to show the quantity of an item represented by a UOM level, such as a pallet or case.

You must add and enable each UOM that you want to use in your facility. Multiple warehouses on the same instance have visibility to all UOM configurations, but a UOM can only be used in the warehouses for which it is enabled.

When you define a UOM, you can specify the following allocation options:

-   Immediately release items using this UOM during shipment or work order allocation processes. When a UOM is marked for immediate release in the shipment or work order allocation process, then all inventory belonging to that UOM will be immediately released for picking as soon as the inventory is allocated. If a UOM is not marked for immediate release, then all inventory belonging to that UOM is placed into a held status. Work is not generated for the UOM until the picks are manually released using Pick Release Operations.
    
    **Note**: During allocation, a user can clear the default selections.
    
-   Enable the UOM to be allocated as a bulk pick. During bulk pick processing, the application combines smaller UOM quantities into larger quantity picks; the larger quantity picks are called bulk picks.

## Add or modify a UOM

1.  Select **Configuration > Inventory > Units of Measure**.
2.  Perform one of the following tasks:
    -   To add a new UOM, click **Add**.
    -   To modify a UOM, in the grid, click the unit of measure.
    -   To copy a UOM, in the grid, select the check box next to the UOM, and then click **Copy**.
3.  Enter information in the [Units of Measure fields](#Units_of_Measure_fields).
4.  To reorder the list, in the grid, select the unit of measure to move, and then drag it to the new location in the grid.
5.  Click **Save**.

## Delete a UOM

1.  Select **Configuration > Inventory > Units of Measure**.
2.  In the grid, select the check box next to the UOM to delete.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Configure the display sequence for units of measure

You can change the sequence in which UOMs are displayed in a UOM or Unit of Measure drop-down list. Multiple UOMs can have the same sequence number, which is useful for placing UOMs that are enabled for different warehouses in sequential order.

1.  Select **Configuration > Inventory > Units of Measure**.
2.  In the grid, in **Display Sequence**, center the order in which you want the UOM to be displayed in a drop-down list.

## Units of Measure fields

 
| Field | Description |
| --- | --- |
| Units of Measure | Select the check box for each UOM in which bulk picks can be allocated. For example, if you select the check box for the Pallet UOM, then any eligible smaller UOMs (such as Case or Each UOMs) can be combined and allocated in Pallet UOM quantities. |
| Description | Description of the UOM. This is the value that is displayed in Unit of Measure and UOM fields in application windows. You can define multiple UOMs with same description for use in different warehouses: however, the identifier for each UOM must be unique. |
| Short Description | Short description of the UOM that is displayed in RF screens. You can define multiple UOMs with same short description for use in different warehouses; however, the identifier for each UOM must be unique. |
| Enable Unit of Measure in Warehouse | If Enabled, the UOM is available for use in the current warehouse. |
| Bulk Picking | If Yes, indicates that the unit of measure can be aggregated for bulk picking. Bulk pick processing allocates matching inventory for multiple outbound order or work order lines together into larger UOM picks so as to reduce the number of smaller UOM picks required to satisfy the orders. For example, if Case is enabled as the bulk picking UOM on the default item footprint, then during bulk pick processing the application can combine order lines for case quantities of the item into larger bulk picking UOM quantities, such as pallets. The larger bulk picking UOM that is eligible to be the physical pick resulting from combining smaller UOM quantities is defined in Units of Measure. If you select Yes, the when eligible order or work order lines for the item are allocated using bulk pick processing, the application combines order lines for this UOM quantity in order to allocate the inventory at a higher, bulk picking UOM.<br > If No, the application does not combine order lines for the UOM quantity; and instead the order lines are allocated separately. Only available for the default item footprint, and only if bulk picking is enabled for the warehouse. |
| Immediate Release - Shipping Allocation | If Yes, the selected UOM is marked, by default, for immediate release during shipment allocation. Select Yes to avoid requiring the user to select this UOM during every shipment allocation session. During allocation, if the UOM is selected by default, the user can deselect it.<br > If No, the selected UOM is not set for immediate release during shipment allocation. |
| Immediate Release - Work Order Allocation | If Yes, indicates that the selected UOM is marked, by default, for immediate release during work order allocation. Select Yes to avoid requiring the user to select this UOM during every work order allocation session. During allocation, if the UOM is selected by default, the user can deselect it. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
