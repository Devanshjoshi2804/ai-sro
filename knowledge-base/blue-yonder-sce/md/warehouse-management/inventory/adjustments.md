---
title: "Adjustments"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/adjustments.htm"
source: "/content/adjustments.htm"
toc_path:
  - "Warehouse Management"
  - "Inventory"
  - "Adjustments"
sections:
  - "Approve or reject a pending inventory adjustment"
  - "Send or delete inventory adjustment transactions"
  - "View inventory adjustments pending to host"
  - "Approvals fields"
  - "Transaction fields"
images: []
source_sha1: 620ba0f5607da655907ef81b21c1e3d84caa4c9c
---
# Adjustments

You use the Adjustments page to view the following information:

-   **Approvals**: Inventory adjustments that have been performed by a user, but require approval for the application to process the adjustment. When viewing approvals, you can approve or reject a pending inventory adjustment. The adjustments that require approval are displayed by location and LPN, item, client (in 3PL), adjusted quantity and cost. The adjustment approvals are displayed only for the clients assigned to the user. When approving or rejecting an adjustment, you can request a cycle count for the location in which the inventory was adjusted.
-   **Transaction**: Inventory adjustment transactions that have been generated (approved) but not sent to a host. When viewing transactions, you can send an approved adjustment to another host system or delete a pending transaction. Transactions displayed on this tab may be grouped together if the **Play Adjustment To Host** field (inventory adjustment settings configuration) is set to Send when complete.
-   **Pending to Host**: Inventory adjustments performed by a user that have been approved (if required) but not yet sent to the host. This display shows the details of the adjustment that was performed. When an adjustment transaction is sent to the host, either automatically or manually (using the Transactions tab), it is removed from the Pending to Host tab. Transactions on this tab are always displayed individually.

## Approve or reject a pending inventory adjustment

When a user performs an inventory adjustment that is equal to or exceeds the cost or unit thresholds defined for the user, the user’s role, warehouse, or (for a 3PL environment) client or client group, the adjustment is not processed until it has been approved or rejected. The adjusted location remains in the Locked status until an authorized user approves or rejects the adjustment.

**Note**: In a 3PL environment, you can reject multiple adjustments only for the same client.

1.  Select **Inventory > Adjustments**.
2.  Select **Approvals**. For details on field descriptions, see [Approvals fields](#Approvals_fields).
3.  In the grid, select the check box next to the adjustments.
4.  To approve adjustments, click **Approve**. The Approve Adjustments window is displayed.
5.  To reject adjustments, click **Reject**. The Reject Adjustments window is displayed.
6.  From the **Reason** drop-down list, select a reason for approving or rejecting the adjustment.
7.  In the **Comment** field, enter a description to approve or reject the adjustment.

**Note**: You can generate cycle counts when you approve or reject adjustments. The cycle count is completed only if the adjustment is successful.

9.  To generate a cycle count for the locations, select the **Generate Cycle Count** check box.
10.  Click **OK**. A confirmation message with the results of the adjustment approval or rejection is displayed.

After you approve adjustments, the approved adjustments display on the Transactions tab where you can send them to a host or delete a pending transaction.

## Send or delete inventory adjustment transactions

You can send transactions for completed adjustments to a host. This is typically required when your application is not configured to send the adjustment transactions to the host automatically.

1.  Select **Inventory > Adjustments**.
2.  Select **Transaction**. View the information in the [Transaction fields](#Transaction_fields).
3.  In the grid, select the check box next to the approved adjustment transactions.
4.  Perform one of the following tasks:
    -   To send the selected transactions, click **Send**.
    -   To delete the selected transactions, click **Delete**.

A confirmation message is displayed.

6.  Click **OK**.

## View inventory adjustments pending to host

The Pending to Host tab displays the approved adjustments that have not yet been sent to the host. The date represents the date on which the adjustment was approved. When a transaction is sent to the host, it is no longer viewable on the Pending to Host tab.

**Note**: Pending adjustments (those requiring approval) are displayed on the **Approvals** tab of the Adjustments page.

1.  Select **Inventory > Adjustments**.
2.  Select **Pending to Host**. The details of all the approved but unsent adjustments are displayed.
3.  View the information in the [Transaction fields](#Transaction_fields).

## Approvals fields

 
| Field | Description |
| --- | --- |
| Date | Date and time during which the inventory was adjusted. |
| User | Last name and first name of the person who performed the adjustment. |
| Location | Location where the inventory was adjusted. |
| LPN | Unique identifier for inventory. Typically, an LPN refers to a pallet; however, it can refer to inventory received at less than pallet quantity. The LPN is the license plate by which the inventory is tracked in the facility.<br > If item is tracked at LPN level, then LPN is displayed. If tracked at sub LPN level, then sub LPN is displayed. If tracked at detailed LPN level, then detail LPN is displayed. |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Original | Quantity of the item existing in the location before the adjustment was performed. |
| New | Quantity of the item in the location after the adjustment was performed. During adjustment, if items are added to the inventory, the original quantity displayed is zero. If items are modified or removed from the inventory, the original quantity displayed is the quantity existing in the location prior to the adjustment. |
| Reason | A reason that indicates why the inventory adjustment was performed. |
| Reference | Optional internal alphanumeric reference number assigned to a piece of transport equipment when it is checked in to the warehouse. If you specify a reference number, then it is a required entry when performing a yard audit, and is used by the application to validate the equipment being audited. |
| Generate cycle count | Specifies whether the application generates a cycle count for the location after the inventory adjustment approval is processed. |

## Transaction fields

 
| Field | Description |
| --- | --- |
| Date | Date and time at which the inventory adjustment was approved. |
| Approve User | Last name and first name of the person who approved the adjustment. |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Adj Quantity | Quantity of item in the location that is adjusted. |
| Cost | The cost of inventory that is adjusted. |
| Display Quantity | The adjusted quantity displayed in terms of Display UOM, if configured for the item.<br > If Display UOM is not configured, the adjusted quantity is displayed in terms of Stocking UOM. |
| Reason | A reason that indicates why the inventory adjustment was performed. |
| Reference | Optional internal alphanumeric reference number assigned to a piece of transport equipment when it is checked in to the warehouse. If you specify a reference number, then it is a required entry when performing a yard audit, and is used by the application to validate the equipment being audited. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
