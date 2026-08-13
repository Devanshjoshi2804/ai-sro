---
title: "Reasons"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/reasons.htm"
source: "/content/reasons.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Advanced"
  - "Reasons"
sections:
  - "Reason groups"
  - "Add or modify a reason"
  - "Delete a reason"
images: []
source_sha1: 0bb171fc7dfb5657e400be0675706eeae54152a3
---
# Reasons

A reason is a value that is assigned to an action to further explain the reason for the action. For example, when a user removes a hold from inventory or performs an inventory attribute change, the user can provide a reason for the action. Some processes are configured to require users to enter a reason before they are allowed to complete the action.

In a 3PL environment, you can assign reasons to specific clients so that users can select only the reason codes associated with the client for the selected record. For example, only the reason codes associated with CLIENT01 are available for selection when adjusting that client's inventory.

## Reason groups

A reason group is a list of reasons that is intended for a common process or operation. For example, the reasons for approving an inventory adjustment are included in the Adjustment Approval reason group. When a user approves an inventory adjustment, the user can select a reason from the displayed list.

The following table lists the standard reason groups and the process during which the reasons for the group are available for selection.

 
| Reason Group | Process |
| --- | --- |
| Adjustment Approval | Approving or rejecting an inventory adjustment |
| Client Ownership Change | Transferring inventory from one client to another |
| Counting | Performing an inventory adjustment during a cycle count |
| Inventory Adjustments | Performing an inventory quantity adjustment |
| Inventory Attribute Adjustment | Performing an inventory attribute adjustment |
| Inventory Hold | Adding a hold to or removing a hold from inventory |
| Inventory Status Change | Changing the status of inventory |
| Outbound Order Update | Changing an attribute of an outbound order |
| Packing Errors | Indicating a problem while processing picked inventory to a shipping container |
| Pallet Position Override Reasons | Overriding the pallet position to which the operator was directed to deposit inventory |
| Production Line Schedule | Changing the schedule for a production line |
| Receive Without Order | Receiving without documentation, such as an inbound order |
| Return Action | Processing inventory that was returned to the warehouse from a customer |
| Return Condition | Processing inventory that was returned to the warehouse from a customer |
| Return Reason | Processing inventory that was returned to the warehouse from a customer |
| Ship Stage Override Reason | Overriding the staging location to which the operator was directed to deposit inventory |
| Undeliverable | Recording undelivered inventory that had been sent out on delivery transport equipment but was brought back to the warehouse |
| Work Order Stop | Stopping a work order that is in progress on a production line |

## Add or modify a reason

1.  Select **Configuration > Advanced > Reasons**.
2.  From the reason group drop-down list, select a reason group.
3.  Perform one of the following tasks:
    -   To add a reason, click **Add**.
    -   To modify a reason, in the grid, click the reason.
    -   To copy a reason, in the grid, select the check box next to the reason, and then click **Copy**.
4.  Enter information in the following fields:
    
     
    | Field | Description |
    | --- | --- |
    | Reason Code | Code that is appended to application transactions to further explain the reason for the hold. Only available when the **System Generated** check box is deselected. |
    | System Generated | Select this check box if you want the application to create a reason code. The code is displayed in the **Reason Code** field after you click **Save**. |
    | Reason Description | Text that describes the reason code and is displayed on the application windows and in reports. |
    
5.  To specify the clients that use the reason:
    1.  Click **Clients**.
    2.  In the **Available** column, select the check box next to the clients that use the reason.
    3.  Click **Apply**.
6.  If customs functionality is enabled, enter information in the following fields:
    
     
    | Field | Description |
    | --- | --- |
    | Customs Order Type | Type of customs order that is used by a duty management application to calculate duties owed for an order. You associate a customs order type with the reason code that is used to identify an inventory adjustment that adds bonded inventory to the warehouse. A customs order type is used to categorize orders that have the same source site type (customs, customs and excise, or non-bonded), destination site type, and destination country type (United Kingdom, member of European Union, or neither). Only available when customs functionality is enabled. |
    | Customs Planned Inbound Order Type | Planned inbound order type that is on the customs paperwork for the transport equipment. You associate a customs planned inbound order type with the reason code that is used to identify an inventory adjustment that deletes bonded inventory from the warehouse. Only available when customs functionality is enabled.<br>-   • **From EU States**: The planned inbound order originated from another country in the European Union (EU), and the current warehouse is in the EU.
    <br>-   • **From Importation**: The planned inbound order originated from a country outside the EU, and the current warehouse is within the EU.
    <br>-   • **Other Sources**: The planned inbound order originated from a source not identified by other receipt types; for example, from an adjustment or production line.
    <br>-   • **Other UK Warehouses**: The planned inbound order originated from another warehouse in the United Kingdom.
    <br>-   • **Gains in Store**: The planned inbound order is for an adjustment in the quantity of existing inventory. |
    
7.  Click **Save**.

## Delete a reason

1.  Select **Configuration > Advanced > Reasons**.
2.  From the reason group drop-down list, select a reason group.
3.  In the grid, select the check box next to the reason.
4.  Click **Delete**. A confirmation message is displayed.
5.  Click **OK**.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
