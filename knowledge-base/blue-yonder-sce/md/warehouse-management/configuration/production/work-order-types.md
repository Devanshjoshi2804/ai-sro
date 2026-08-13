---
title: "Work Order Types"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/work_order_types.htm"
source: "/content/work_order_types.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Production"
  - "Work Order Types"
sections:
  - "Add or modify a work order type"
  - "Delete a work order type"
  - "Work Order Type fields"
images: []
source_sha1: 6ff89bd824eb0c14b9ffa9b42b8b6441b298c5a8
---
# Work Order Types

A work order type is a category into which work orders are grouped based on similar processing characteristics. You use work order types to distinguish between work orders that might require different workflows and processes. Currently, two work order types are distributed with the application, but additional work order types can be defined. The following categories are the standard work order types:

-   **Assembly**: Work orders in which component items are assembled into a finished good at a production line or production station. For an assembly type work order, the application allocates the component items based on the work order details, and then the components are assembled into top-level items. The top-level items are then identified and received into the warehouse or cross-docked to fulfill another order.
-   **Disassembly**: Work orders in which finished goods are disassembled at a production line or production station. For a disassembly type work order, the application allocates a quantity of a top-level item based on the work order, and then the items are disassembled into component items. The component items are then identified and received into the warehouse or cross-docked to fulfill another order or work order.

A work order type must be defined for a work order to determine whether the work order is for assembling a finished good from component items or disassembling a finished good into component items.

## Add or modify a work order type

1.  Select **Configuration > Outbound > Production > Work Order Types**.
2.  Perform one of the following tasks:
    -   To add a work order type, click **Add.**
    -   To modify an work order type, in the grid, click the work order type.
3.  Enter information in the [Work Order Type fields](#Work_Order_Type_fields).
4.  Click **Save**.

## Delete a work order type

You cannot delete a work order type that is associated with a work order.

1.  Select **Configuration > Outbound > Production > Work Order Types**.
2.  In the grid, select the check box next to the work order type to delete.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Work Order Type fields

 
| Field | Description |
| --- | --- |
| Work Order Type | Unique identifier for the work order type. A work order type is a category into which work orders are grouped based on similar processing characteristics. |
| Production Area | Area in your facility in which the production line is located. This production area is used as a default area for work orders of this type. If a production area is not assigned to a work order, the application uses the default production area specified for the work order type. |
| Disassembly | If Yes, work orders of this type are used for the disassembly of top-level items. Select Yes if work orders of this type are processed by picking top-level items, which are then delivered to a production line and disassembled into component items to be identified.<br > If No, work orders of this type are used for assembling picked component items into top-level items to be identified. |
| Description | Description that further defines the work order type. |
| Production Line | Identifier for a production line in the selected production area. The production line is used as a default for work orders of this type. If a production line is not assigned to a work order, the application uses the default production line specified for the work order type. |
| Bulk Picking | If Yes, work orders created using this work order type are eligible for bulk pick processing. Bulk pick processing allocates matching inventory for multiple work order lines together into larger unit of measure (UOM) picks so as to reduce the number of smaller UOM picks required to satisfy the orders. Select Yes if work orders created using this work order type should be considered by the application when allocating inventory using bulk picking.<br > If No, work orders created using this work order type are not considered for bulk picking. Instead, the required inventory for the work order is allocated and picked separately.<br > The **Bulk Picking** field is only displayed if bulk picking is enabled for the warehouse. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
