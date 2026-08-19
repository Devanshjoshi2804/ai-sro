---
title: "Non Serialized Handling Unit Adjustment Operations"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/non_serialized_handling_unit_adjustments.htm"
source: "/content/non_serialized_handling_unit_adjustments.htm"
toc_path:
  - "Warehouse Management"
  - "Inventory"
  - "Non Serialized Handling Unit Adjustment Operations"
sections:
  - "Add or modify a non-serialized handling unit type on-hand quantity"
  - "Delete a non-serialized handling unit type on-hand quantity"
  - "Non Serialized Handling Unit Adjustment Operations fields"
images: []
source_sha1: 60dbe37fff9ef13f6fa921991adf8ffaa759a133
---
# Non Serialized Handling Unit Adjustment Operations

You use the Non Serialized Handling Unit Adjustment Operations page to maintain the quantities of non-serialized handling unit types. The application tracks the on-hand quantity of non-serialized handling units by handling unit type (unlike serialized handling units, which are tracked individually by a handling unit identifier). See [Handling Unit Types](../configuration/inventory/lpn-handling/handling-unit-types.md).

## Add or modify a non-serialized handling unit type on-hand quantity

1.  Select **Inventory > Non Serialized Handling Unit Adjustment Operations**.
2.  Perform one of the following tasks:
    -   To add a new on-hand quantity, from the **Actions** drop-down list, select **Add**.
    -   To copy an on-hand quantity, in the grid select the check box on the row of the handling unit type, and then from the **Actions** drop-down list, select **Copy**.
    -   To modify an on-hand quantity, in the grid select the check box on the row of the handling unit type, and then from the **Actions** drop-down list, select **Edit**.
3.  Enter information in the [Non Serialized Handling Unit Adjustment Operations fields](#Non_Serialized_Handling_Unit_Adjustment_Operations_fields).
4.  Click **Save**. A confirmation message is displayed.
5.  Click **OK**.

## Delete a non-serialized handling unit type on-hand quantity

1.  Select **Inventory > Non Serialized Handling Unit Adjustment Operations.**
2.  In the grid, select the check box on the row of the handling unit type on-hand quantity.
3.  From **Actions** drop-down list, select **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Non Serialized Handling Unit Adjustment Operations fields

 
| Field | Description |
| --- | --- |
| Handling Unit Type | Category that classifies a group of handling units (for example, pallets, totes, transport equipment, or vehicles) that share the same characteristics such as size and weight, as well as whether they are serialized, temporary, or considered a container. The application tracks the on-hand quantity of handling units by type and, for serialized handling units, by handling unit identifier. |
| Handling Unit Status | Current condition of the handling unit, such as active or inactive. This value is only used for reporting purposes. |
| Address ID | Identifier for the address information where the handling unit quantity is currently located. The address identifier is a system-generated value that identifies an individual or organization and an address. |
| Client ID | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. |
| Source Address ID | Identifier for the address information where the handling unit type on-hand quantity was first created. The source address ID is a system-generated value that identifies an individual or organization and an address. |
| On-Hand Qty | Quantity of the handling unit type that is currently in storage. |
| Inserted Date | Date and time at which the handling unit type on-hand quantity was created. |
| Inserted User | User who created the handling unit type on-hand quantity. |
| Last Updated Date | Date and time at which the handling unit type on-hand quantity was last updated. |
| Last Updated User | User who most recently updated the handling unit type on-hand quantity. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
