---
title: "Order Sequence Processing"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/order_sequence_processing.htm"
source: "/content/order_sequence_processing.htm"
toc_path:
  - "Warehouse Management"
  - "Picking"
  - "Order Sequence Processing"
sections:
  - "View order sequence processing for a handling unit"
  - "Change cut-off time for a work assignment"
  - "Cut handling units"
  - "Change close time for a work assignment"
  - "Close handling units"
  - "Print slot labels"
  - "Print handling unit labels"
  - "Print summary report"
  - "Auto-ship a handling unit"
  - "Order Sequence Processing fields"
  - "Work Assignment LPN fields"
images: []
source_sha1: ffdc03d4219829b24eff3ad9ef9a036b29babd77
---
# Order Sequence Processing

The Order Sequence Processing page displays the progress of picking work assignments for sequenced orders. These work assignments are picked to slotted or non-slotted master handling units. Slotted handling units contain multiple slots with one order per slot. An LPN is assigned to each master handling unit.

You can view the master handling units that are pending, in progress, and completed. The display does not show work assignments for shipments that have been checked out (dispatched).

**Note**: For more information and setup tasks, see the [Order sequence processing](../configuration/outbound/picking/work-assignments/order-sequence-processing.md) configurations.

For a selected LPN that is pending or in progress, you can perform the following tasks:

-   Change the cut-off time for the master handling unit. The cut-off time determines the point at which the application prevents additional picks from being planned to the work assignment for the master handling unit.
-   Cut handling units. You use this action to prevent the application from planning any more picks to the work assignment for the master handling unit.
-   Change the close time for the master handling unit.
-   Close a master handling unit. You use this action to complete the master handling unit. When the handling unit is closed, the application allows the operator to complete the current pick (for a non-slotted handling unit) or the picks for the current slot (for a slotted handling unit). Any remaining picks are re-planned to slots on another master handling unit as long as there is still time before the close time to complete the picks for shipping. If there is not enough time to complete the picks, the picks are cancelled.
    
    **Note**: Picks for a slot are always handled together. If picking for a slot has started, the application does not close the handling unit until the remaining picks for the same slot are all picked. If any pick for a slot needs to be cancelled because of insufficient time, then all picks for the same slot are cancelled.
    
-   Print labels for the slots on a master handling unit.
-   Print labels for a master handling unit.
-   Print a summary report of the inventory picked to slots on a master handling unit.
-   Automatically ship a handling unit. You use this action to systematically load, close, ship, and check out a shipment (represented by a master handling unit) that has been staged. This action is available if the carrier associated with the shipment has been configured to allow automatic shipping.

## View order sequence processing for a handling unit

You can view the status of picks for sequenced orders by LPN and LPN details. An LPN represents a work assignment master handling unit. LPN details show the status of picks to each of the slots on the master handling unit.

1.  Select **Picking > Order Sequence Processing**.
2.  View the information in the [Order Sequence Processing fields](#Order_Sequence_Processing_fields).
3.  In the grid, click the LPN to view.
4.  View the information in the [Work Assignment LPN fields](#Work_Assignment_LPN_fields).
5.  To view the details for a slot, in the grid, expand the slot information.
    
    **Note**: You can view details for a slot if any column in the grid displays a value of "Many".
    

## Change cut-off time for a work assignment

The cut-off time is the date and time on which no more picks will be planned to the work assignment for the master handling unit. Select a cut-off time that allows you to complete remaining picks in time for shipping.

1.  Select **Picking > Order Sequence Processing**.
2.  In the grid, select the check box next to the LPN for the master handling unit.
3.  From the **Actions** drop-down list, select **Change Cut Off Time**.
4.  Enter the cut-off date and time.
5.  Click **Save**. The new cut-off time is displayed for the LPN.

## Cut handling units

You cut a master handling unit to prevent the application from planning any more picks to the work assignment for the master handling unit.

1.  Select **Picking > Order Sequence Processing**.
2.  In the grid, select the check box next to the LPN for the master handling unit.
3.  From the **Actions** drop-down list, select **Cut Handling Units**.
4.  Click **Save**. The cut-off time displayed for the LPN is updated to the current date and time.

## Change close time for a work assignment

The close time is the date and time on which the application automatically closes the master handling unit.

1.  Select **Picking > Order Sequence Processing**.
2.  In the grid, select the check box next to the LPN for the master handling unit.
3.  From the **Actions** drop-down list, select **Change Close Time**.
4.  Enter the close date and time.
5.  Click **Save**. The new close time is displayed for the LPN.

## Close handling units

You close a master handling unit to immediately complete the work assignment for the master handling unit. When a handling unit is closed, the following actions take place:

-   The application allows the operator to complete the current pick (for a non-slotted handling unit) or the picks for the current slot (for a slotted handling unit). This is used to maintain the integrity and sequence of the slot before closing the handling unit.
-   The application cuts remaining picks from the work assignment and automatically plans them to a new work assignment.
-   If any pick for a slot cannot be completed in time for the ship date, all the picks for the slot are cancelled.
    
    **Note**: Picks for a slot are always handled together. If picking for a slot has started, the application does not close the handling unit until remaining picks for the same slot are all picked. If any pick for a slot needs to be cancelled because of insufficient time, then all picks for the same slot are cancelled.
    

Perform the following tasks to close handling units:

1.  Start **Picking > Order Sequence Processing**.
2.  In the grid, select the check box next to the handling unit to close, or click the LPN.
3.  From the **Actions** drop-down list, select **Close Handling Units**. A confirmation message is displayed.
4.  Click **Yes**. Any remaining picks for the handling unit that were not completed are re-planned to a new work assignment. You can view the new work assignment on the Order Sequence Processing page.
5.  To view the details of the new or completed work assignment:
    1.  In the grid, click the LPN.
    2.  View the information in the [Work Assignment LPN fields](#Work_Assignment_LPN_fields).

## Print slot labels

You can print labels for the slots on a master handling unit for a work assignment. Labels can be printed after work has been released. Each label contains the following information: item, item description, item family set sequence, planned order sequence, slot on the master handling unit, and order.

1.  Select **Picking > Order Sequence Processing**.
2.  In the grid, select the LPN for the master handling unit.
3.  From the **Actions** drop-down list, select **Print Slot Labels**. A confirmation message is displayed.
4.  Click **OK**.

## Print handling unit labels

You can print a master handling unit label report for a master handling unit for a work assignment. The document can be printed to a report or label after picks have been released. The report contains the work assignment barcode, planned order sequence numbers, slots, and slot label information.

1.  Select **Picking > Order Sequence Processing**.
2.  In the grid, select the LPN for the master handling unit.
3.  From the **Actions** drop-down list, select **Print Handling Unit Labels**. A confirmation message is displayed.
4.  Click **OK**.

## Print summary report

You can print a Master Handling Unit Summary report for a work assignment that is complete (closed). The report provides the work assignment barcode, master LPN, item family set sequence, handling unit type, close date, total quantity picked, and the following detail information for each slot: planned order sequence, item, slot, and quantity.

1.  Select **Picking > Order Sequence Processing**.
2.  In the grid, select the LPN for the master handling unit.
3.  From the **Actions** drop-down list, select **Print Summary Report**. A confirmation message is displayed.
4.  Click **OK**.

## Auto-ship a handling unit

You can automatically ship a handling unit that contains sequenced orders if the handling unit meets the following criteria:

-   All of the inventory for the shipment has been staged, is related to the same work assignment, and is on the same LPN (master handling unit).
-   The shipment is not already closed.
-   There are no in-process item family set sequences for the same item family set (not on this shipment) that should be shipped first. This is important to ensure that shipments are dispatched in sequential order.

Perform the following tasks to set up the automatic shipment of a handling unit:

1.  Select **Picking > Order Sequence Processing**.
2.  In the grid, select the check box next to the LPN for the master handling unit.
3.  From the **Actions** drop-down list, select **Auto-Ship Handling Unit**. A confirmation message is displayed.
4.  Click **Yes**.

## Order Sequence Processing fields

 
| Field | Description |
| --- | --- |
| LPN | Identifier for the master handling unit to which inventory has been picked for sequenced orders. |
| Status | Status of the LPN that represents a master handling unit that contains inventory picked for sequenced orders.<br>-   • **Pending**: Picking for the slot on the master handling unit has not started.
<br>-   • **Picking In Process**: Picking for the slot on the master handling unit has begun.
<br>-   • **Complete**: Picking for the slot on the master handling unit is complete. |
| Pick Progress | Percentage of the picks that have been completed for the work assignment. An X of Y value displays the number of picks that have been completed out of the total number of expected picks; for example, 2 of 4. |
| Unallocated Slots | Number of slots on the master handling unit for which picks have not been allocated. |
| User | User associated with last activity performed on the master handling unit. |
| Cut-Off Time | Date and time that no more picks will be planned to the work assignment for the master handling unit. |
| Expected Complete Time | Date and time that pick work for the master handling unit is expected to be completed based on the close time that was defined for the work assignment. |
| Shipment | Unique identifier for an outbound shipment. A shipment is a group of orders or order lines that are allocated together and shipped to the same location. |
| Order | Unique number that identifies an order. An order is a request for a supply of material or product. |
| Order Line | Unique number that identifies the order line. The number corresponds to the line's position on the order. The first order line is automatically assigned a line number of 0001. Additional order lines are then automatically numbered sequentially, beginning with 0002. |
| Planned Slot Sequence | Slot sequence value assigned to the order and downloaded from the host. It is used to plan corresponding work assignment picks into a slot on a master handling unit. For more information and setup tasks, see the [Order sequence processing](../configuration/outbound/picking/work-assignments/order-sequence-processing.md) configurations. |
| Shipment Status | Status that represents the processing state of the shipment.<br>-   • **Ready**: The shipment has been created or planned and is ready for allocation. Shipments can be created automatically by host download, or manually.
<br>-   • **In-Process**: Inventory for the shipment has been allocated.
<br>-   • **Staged**: The shipment has been staged manually or automatically. A shipment is staged when all inventory for the shipment has been picked and deposited in the ship staging location and is ready to be loaded onto the transport equipment.
<br>-   • **Loading**: At least one pallet, case, or piece of inventory has been deposited onto the transport equipment.
<br>-   • **Loaded**: All inventory for the shipment has been loaded onto the transport equipment.
<br>-   • **Complete**: The transport equipment containing the shipment has been closed and dispatched from the facility.
<br>-   • **Transfer**: Inventory for the shipment is being moved to a different ship staging location.
<br>-   • **Cancelled**: The shipment has been cancelled with a shipped quantity of zero. |
| Carrier | Identifier for a carrier that delivers inbound inventory to the warehouse or outbound shipments to a customer. This is the identifier that will be displayed to users on the application windows and reports. In the application, a carrier can be associated with a customer, order, inbound shipment, outbound shipment, load, and service levels (such as Ground, Next Day, and Saturday Delivery). |
| Work Assignment Complete Date | Date and time that the pick work for the master handling unit was completed. |
| Item Family Set Name | Name of the item family set. An item family set is a group of item families that you want to be able to assign to the same work assignment rule for picking sequenced orders to a master handling unit. |
| Item Family Set Sequence | Sequence number that is used to control the release of work assignments for the same item family set. For example, if there are three work assignments planned for the same item family set, the application increases the sequence by one for each work assignment that is generated. The application prevents the last two work assignments from being started until the first one is completed. |

## Work Assignment LPN fields

 
| Field | Description |
| --- | --- |
| Status | Status of the LPN that represents a master handling unit that contains inventory picked for sequenced orders.<br>-   • **Pending**: Picking for the slot on the master handling unit has not started.
<br>-   • **Picking In Process**: Picking for the slot on the master handling unit has begun.
<br>-   • **Complete**: Picking for the slot on the master handling unit is complete. |
| Handling Unit Type | Handling unit type assigned to the LPN. A handling unit type is a category that classifies a group of handling units (for example, pallets or totes) that share the same characteristics such as size and weight, as well as whether they are serialized, temporary, or considered a container. |
| User | User associated with last activity performed on the master handling unit. |
| Closed Time | Date and time that the application will automatically close the master handling unit. |
| Cut-Off Time | Date and time that no more picks will be planned to the work assignment for the master handling unit. |
| Slot | Identifier for the slot on the handling unit. |
| Status | Status of the picks allocated to the slot on the master handling unit. |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Order Quantity | Quantity of the item that is required for the order that is associated with the slot. |
| Picked Quantity | Quantity that has been picked for the slot on the master handling unit. |
| LPN | Identifier for the master handling unit to which inventory has been picked for sequenced orders. |
| Item Family | Identifier used to group similar items together. Typically, all of the items within a family have the same material handling characteristics. |
| Shipment | Identifier for the shipment associated with the order assigned to the slot on the master handling unit. When sequenced orders are downloaded, the application automatically creates a shipment for each order. When the master handling unit LPN is completed, the application splits the order lines on the master handling unit from their original orders and consolidates them into a single shipment. |
| Planned Slot Sequence | Slot sequence value assigned to the order and downloaded from the host. It is used to plan corresponding work assignment picks into a slot on a master handling unit. For more information and setup tasks, see the [Order sequence processing](../configuration/outbound/picking/work-assignments/order-sequence-processing.md) configurations. |
| Order | Unique number that identifies an order. An order is a request for a supply of material or product. |
| Order Line | Unique number that identifies the order line. The number corresponds to the line's position on the order. The first order line is automatically assigned a line number of 0001. Additional order lines are then automatically numbered sequentially, beginning with 0002. |
| Shipment Status | Status that represents the processing state of the shipment.<br>-   • **Ready**: The shipment has been created or planned and is ready for allocation. Shipments can be created automatically by host download, or manually.
<br>-   • **In-Process**: Inventory for the shipment has been allocated.
<br>-   • **Staged**: The shipment has been staged manually or automatically. A shipment is staged when all inventory for the shipment has been picked and deposited in the ship staging location and is ready to be loaded onto the transport equipment.
<br>-   • **Loading**: At least one pallet, case, or piece of inventory has been deposited onto the transport equipment.
<br>-   • **Loaded**: All inventory for the shipment has been loaded onto the transport equipment.
<br>-   • **Complete**: The transport equipment containing the shipment has been closed and dispatched from the facility.
<br>-   • **Transfer**: Inventory for the shipment is being moved to a different ship staging location.
<br>-   • **Cancelled**: The shipment has been cancelled with a shipped quantity of zero. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
