---
title: "Close Inbound Shipment"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/close_inbound_shipment.htm"
source: "/content/close_inbound_shipment.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inbound"
  - "Receiving"
  - "Close Inbound Shipment"
sections:
  - "Automatic creation of directed putaway"
  - "Host notifications"
  - "Receiving discrepancies"
  - "Host notification overrides by client"
  - "Inbound quality issues"
  - "Configure close inbound shipments"
  - "Close Inbound Shipment fields"
images: []
source_sha1: 260b0a9e4c8ed1c1dc623e3c8a7e1dd75c5d74b1
---
# Close Inbound Shipment

An inbound shipment is a group of planned inbound orders that are transported to the warehouse together or received together. When transport equipment is used, an inbound shipment typically represents the entire contents of the transport equipment; however, transport equipment can contain one or more inbound shipments.

You can configure the actions that take place when an inbound shipment is closed, when an RF operator closes transport equipment, and when receiving discrepancies occur.

You can also specify whether and when notifications confirming the receipt of inventory are sent to the host.

## Automatic creation of directed putaway

A typical receiving process involves identifying inventory to a receiving staging location. At that point, inventory that is not required for a distribution or for cross docking can be directed to a storage location.

You can configure the application to create directed work automatically to store staged inbound inventory when an RF operator closes the transport equipment on which the inventory arrived. The directed work is added to the work queue.

Use the following steps to set up automatic creation of directed putaway:

1.  Configure processing for closing an inbound shipment.
    
    -   Enable the application to create putaway work automatically by setting the **RF Close Auto Create Putaway Work** field to Yes.
    -   To obtain a Putaway Failures on Transport Equipment Close report listing the LPNs for which the application could not find a suitable storage location, set the **Print Report When Auto Create Putaway Fails** field to Yes. The report prints automatically.
    -   To obtain an Over, Short, and Damaged (OSD) report when received quantities do not match expected quantities, set the **Print Report When Transport Equipment is Closed with Discrepancies** field to Yes. The report prints automatically.
        
    
    See [Configure close inbound shipments](#Configure_close_inbound_shipments).
    
2.  To send an Event Management alert listing the LPNs for which the application could not find a suitable storage location, set the **Auto Create Putaway Fails on Transport Equipment Close** field to Yes. See [Event Management integration](../../integration/event-management.md).

## Host notifications

Host notification is a receipt confirmation transaction from the application to the host. A receipt confirmation identifies the inventory and quantities that have been put away to locations from which the inventory can be allocated. A receipt confirmation is used to inform the host that the inventory is available for allocation to fulfill orders.

A receipt confirmation does not record inventory that was identified and directed to a processing location or other location from which the inventory cannot be allocated. For example, if damaged inventory was identified and moved to a damage location, that inventory is not recorded on the receipt confirmation to the host. A receipt confirmation is also not sent until all holds have been removed from the inventory.

When you configure closing inbound shipments for a non-3PL environment, you can select whether and when a receipt confirmation is sent to the host.

For a 3PL environment, you can specify for each client whether and when the receipt confirmation is sent to the host. For example, some clients may want to be notified when all of the inventory for a planned inbound order has been put away; other clients may want to be notified that inventory is available as soon as an LPN is put away. See [Host notification overrides by client](#Host_notification_overrides_by_client).

**IMPORTANT**: For a 3PL environment, if you want to select one of the host notification levels as the warehouse default, then you must configure that level for each client that does not have another notification level selected.

After a receipt confirmation is sent, you can view the receipt confirmation date when you view the details of an inbound shipment.

## Receiving discrepancies

A receiving discrepancy occurs when there are differences between the expected inventory and the received inventory. Received inventory is inventory that is received to a location, such as receiving staging location, in the warehouse.

The following situations result in receiving discrepancies:

-   **Quantity Overages**: You received more inventory than you expected. For example, the planned inbound order listed 4 cases, but you received 10 cases. The application continuously updates the overage quantity from receiving through the closing of the inbound shipment.
-   **Quantity Shortages**: You received less inventory than you expected. For example, the planned inbound order listed 4 cases, but you only received 2 cases. The application records the shortage only after the inbound shipment is closed. Any inventory that remains in the receiving location (not put away) after the inbound shipment is closed will also be recorded as a shortage.
-   **Damaged Inventory**: You received inventory with a damaged inventory status. You specify the inventory statues that the application considers for the damaged category. The application continuously updates the damaged quantity from receiving through the closing of the inbound shipment.
-   **Inventory attribute differences**: You received inventory with different characteristics than expected. These discrepancies are indicated as quantity discrepancies, not as attribute discrepancies. For example, if the planned inbound order listed 20 eaches of lot A, but you received 20 eaches of lot B, then the application records a quantity overage for lot B. The application records the discrepancy as each LPN is received.

Receiving discrepancies are displayed on the Receiving Issues page in the Receiving module, and on the Overage, Short and Damage (OSD) report.

If Event Management is integrated with Warehouse Management, and you want receiving supervisors to be notified automatically when an unauthorized user attempts to close an inbound shipment with discrepancies, then enable the **User Unable To Close Transport Equipment with Discrepancies** Event Management event.

## Host notification overrides by client

For a 3PL environment, you can select one of the following levels to determine when the notification is sent to the host:

**IMPORTANT**: If you want to select one of the following host notification levels as the warehouse default, then you must configure that level for each client that does not have another notification level selected.

-   **Receipt Confirmation at Inbound Shipment Level**: A receipt confirmation is sent to the host when all of the inventory for an inbound shipment has been identified, is free of holds, and has been deposited to a location from which it can be allocated for orders.
-   **Receipt Confirmation at Inbound Order Level**: A receipt confirmation is sent to the host when all of the inventory for a planned inbound order has been identified, is free of holds, and has been deposited to a location from which it can be allocated for orders.
-   **Receipt Confirmation at LPN Level**: A receipt confirmation is sent to the host when an LPN has been identified, is free of holds, and has been deposited to a location from which it can be allocated for orders.
-   **No Receipt Confirmation Sent**: A receipt confirmation is not sent to the host upon receipt of the client's inventory.

If you select receipt confirmation at the inbound order level or LPN level, then if over receiving is allowed, the receipt confirmation is sent when all of the expected inventory for the planned inbound order or LPN is available for allocation. Then, if additional inventory is received and becomes available for allocation, an additional receipt confirmation is sent to confirm the receipt of that inventory.

## Inbound quality issues

To help you monitor the level of quality that you receive from suppliers and carriers delivering product to your facility, the application enables you to document any quality issues that you encounter as you receive inventory into the warehouse.

For example, you can document the amount of damaged product that a supplier delivers, or whenever a particular carrier arrives late.

A default set of supplier and carrier issue types is provided, but you can add other issues that you want available for selection when a quality issue is reported.

## Configure close inbound shipments

1.  Select **Configuration > Inbound > Receiving > Close Inbound Shipment**.
2.  Enter information in the [Close Inbound Shipment fields](#Close_Inbound_Shipment_fields).
3.  To select user roles that are authorized to close an inbound shipment when quantity discrepancies exist:
    1.  Click **Roles**.
    2.  In the **Available** column, select the check box next to the roles to authorize.
    3.  Click **Apply**.
4.  For a 3PL environment, to define by client when a notification confirming the receipt of inventory is sent to the host application:
    1.  Under **HOST NOTIFICATIONS**, click **Client** **Host Notifications**.
    2.  Perform one of the following tasks:
        -   To add a client override, click **Add**.
        -   To modify a client override, in the grid, click the client.
        -   To copy a client override, in the grid, select the check box next to the client, and then click **Copy**.
    3.  Enter the information in the following fields:
        
        **IMPORTANT**: If you want to select one of the host notification levels as the warehouse default, then you must configure that level for each client that does not have another notification level selected.
        
        | Field | Description |
        | --- | --- |
        | Client | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. |
        | Host Notification Level | Level at which received inventory and quantity information is sent to the host:<br>-   • **Receipt Confirmation at Inbound Shipment Level**: A receipt confirmation is sent to the host when all of the inventory for an inbound shipment has been identified, is free of holds, and has been deposited to a location from which it can be allocated for orders.
        <br>-   • **Receipt Confirmation at Inbound Order Level**: A receipt confirmation is sent to the host when all of the inventory for a planned inbound order has been identified, is free of holds, and has been deposited to a location from which it can be allocated for orders.
        <br>-   • **Receipt Confirmation at LPN Level**: A receipt confirmation is sent to the host when an LPN has been identified, is free of holds, and has been deposited to a location from which it can be allocated for orders.
        <br>-   • **No Receipt Confirmation Sent**: A receipt confirmation is not sent to the host upon receipt of the client's inventory. |
        
    4.  Click **Apply**.
5.  To define the inventory statuses that the application will track as damaged and include in the Over, Short and Damaged Receiving report:
    1.  Under **OVER, SHORT, DAMAGED REPORT**, click **Over, Short, Damaged Report**.
    2.  To add an inventory status:
        1.  Click **Add New**.
        2.  In the **Status Code**, **Description**, and **Short Description** fields, enter the values.
        3.  Click **Save**.
    3.  In the **Available** column, select the check box next to the statuses to include in the report.
    4.  Click **Apply**.
6.  To define inbound quality issues that are available for selection when a supplier or carrier issue is reported:
    1.  Under **INBOUND QUALITY ISSUES**, perform one of the following tasks:
        -   To define supplier issues, click **Supplier Issues**.
        -   To define carrier issues, click **Carrier Issues**.
    2.  To add a quality issue:
        1.  Click **Add**.
        2.  In the **Supplier Issue** or **Carrier Issue**, **Description**, and **Short Description** fields, enter the values.
        3.  Click **Apply**.
    3.  To modify the descriptions for a quality issue:
        1.  In the grid, click a description and change it.
        2.  Click **Apply**.
    4.  To translate a quality issue:
        1.  Perform one of the following tasks:
            -   To translate specific rows, in the grid, select the check box of the rows, and then above the grid, click **Translation**.
            -   To translate all rows, above the grid, click **Translation**.
        2.  From the **Destination Locale** drop-down list, select the locale.
        3.  In the grid, select a translated description or short description, and then enter the new value.
        4.  Click **Save**.
7.  Click **Save**.

## Close Inbound Shipment fields

 
| Field | Description |
| --- | --- |
| Automatic Close | If Yes, the application automatically closes an inbound shipment when the received quantity matches its expected quantity. If the transport equipment contains more than one shipment, then the application only closes the completed shipment. If the inbound shipment is the only shipment on the transport equipment, or if all other inbound shipments on the transport equipment are closed, then the transport equipment is also closed.<br > **Note**: If this field is set to Yes and there are discrepancies found during receiving, then an authorized operator must manually close the transport equipment. Authorized user roles are defined in the Close Inbound Shipment configurations.<br > If No, the operator must manually close the inbound shipments and the transport equipment in the application after receiving is complete. |
| RF Close Confirmation | If Yes, then when the application attempts to automatically close an inbound shipment and its transport equipment after all of the expected inventory is received (**Automatic Close** is set to Yes), the operator is prompted to confirm whether there is additional inventory to receive. If the operator selects No, then the transport equipment and inbound shipment are closed. If the operator selects Yes, the operator can then receive additional inventory if over receiving is allowed and the operator is allowed to over receive.<br > **Note**: If transport equipment contains multiple shipments and the operator answers Yes to the prompt for the first shipment and No to the prompt for the second shipment, then the application will still close all of the shipments and the transport equipment, even though there is additional inventory to receive.<br > If No, the application automatically closes the inbound shipment when the received quantity matches the expected inventory quantity, without prompting the operator to confirm whether there is additional inventory to receive. |
| RF Close Auto Create Putaway Work | If Yes, when an RF operator closes transport equipment, the application creates directed work to move staged inventory to an appropriate storage location. If set to Yes, this process applies to all of the LPNs that were identified from the transport equipment and that are currently in a receiving staging location. This process does not apply to inventory required for a distribution or for cross docking.<br > If the application fails to create work for an LPN, for example, because a suitable storage location cannot be found, the LPN is listed on the Putaway Failures on Transportation Equipment Close report.<br > If No, the application does not attempt to create work automatically for the staged inventory when an RF operator closes the transport equipment. |
| Create Putaway Work During Auto Receiving | If Yes, when a shipment is auto-received and the transport equipment is closed, the application creates directed work to move the staged inventory to an appropriate storage location. If set to Yes, this process applies to all of the LPNs that were identified from the transport equipment and that are currently in a receiving staging location. This process does not apply to inventory required for a distribution or for cross docking.<br > If the application fails to create work for an LPN, for example, because a suitable storage location cannot be found, the LPN is listed on the Putaway Failures on Transportation Equipment Close report.<br > If No, the application does not attempt to create work automatically for the staged inventory when an RF operator closes the transport equipment after auto receiving. If set to No, manual (undirected) putaway is required to move the inventory from staging to storage. |
| Load Close Error | If Yes, then an error message is displayed when the operator attempts to close transport equipment that contains a shipment that is not complete. For example, assume an operator attempts to close transport equipment, and identified inventory from a shipment on the equipment exists that has not yet been deposited to a physical location in the warehouse. If the expected quantity is 100, and the operator identifies 80 and deposits 80, and then identifies 20, but does not deposit them, the error message would be displayed if the operator attempted to close the transport equipment.<br > If No, the operator does not receive an error message when closing transport equipment that contains identified inventory that has not yet been deposited to a physical location in the warehouse. |
| Print Report When Auto Create Putaway Fails | If Yes, then if the application fails to create directed work to store staged inventory when configured to do so, a report is printed automatically. The report, called Putaway Failures on Transportation Equipment Close, lists the LPNs for which directed work was not created. The application may fail to create directed work, for example, if a suitable storage location could not be found for the inventory. Select Yes if you want the report to be printed automatically when this occurs. This field is only available if the **RF Close Auto Create Putaway Work** field is set to Yes.<br > If No, the report is not printed automatically when the application fails to create directed putaway work when configured to do so. |
| Host Notification of Received Inventory | If Yes, receipt confirmation of planned inbound order quantities is sent to the host all at once when the associated inbound shipment is closed. If you select Yes, then if an inbound shipment is closed and then re-opened, the transactions could be duplicated when it is subsequently closed again.<br > If No, the application sends receipt confirmation of planned inbound order quantities to the host based on the selection defined in the **Host Notification Level** field or, for a 3PL environment, the **Client Host Notifications** field. |
| Defer Inbound Shipment Complete | If Yes, then when the Inbound Shipment Complete transaction is logged, the application defers sending the transaction to the host. The transaction is instead saved to a deferred executions database table until it is purged. The Inbound Shipment Complete transaction is logged based on the LOG-MST-RCPT-CMP background workflow. For example, if the workflow is enabled and configured with the Receiving Operations exit point, then the transaction is logged when the operator closes the inbound shipment's transport equipment after receiving the inventory.<br > If No, then the application immediately sends the logged Inbound Shipment Complete transaction to the host. |
| Host Notification Level | Value that determines when a notification confirming the receipt of inventory is sent to the host application:<br>-   • **Receipt Confirmation Based on Host Transaction Rules**: Sends receipt confirmation at the LPN level when inventory is moved to an area. This occurs if area movement transactions are configured to notify the host of inventory movements. See [Movement Transaction](../../integration/host/movement-transaction.md).
<br>-   • **Receipt Confirmation at Inbound Shipment Level**: A receipt confirmation is sent to the host when all of the inventory for an inbound shipment has been identified, is free of holds, and has been deposited to a location from which it can be allocated for orders.
<br>-   • **Receipt Confirmation at Inbound Order Level**: A receipt confirmation is sent to the host when all of the inventory for a planned inbound order has been identified, is free of holds, and has been deposited to a location from which it can be allocated for orders.
<br>-   • **Receipt Confirmation at LPN Level**: A receipt confirmation is sent to the host when an LPN has been identified, is free of holds, and has been deposited to a location from which it can be allocated for orders.
<br>-   • **No Receipt Confirmation Sent**: A receipt confirmation is not sent to the host upon receipt of the inventory.
<br > If you select receipt confirmation at the inbound order level or LPN level, then if over receiving is allowed, the receipt confirmation is sent when all of the expected inventory for the planned inbound order or LPN is available for allocation. Then, if additional inventory is received and becomes available for allocation, an additional receipt confirmation is sent to confirm the receipt of that inventory.<br > This field is only available in a non-3PL environment when the **Host Notification of Received Inventory** field is set to No. |
| Print Report When Transport Equipment is Closed with Discrepancies | If Yes, the application prints an Over, Short, and Damaged (OSD) report automatically when an operator closes transport equipment with discrepancies. A discrepancy occurs when the expected quantity does not match the received quantity. If the application is configured to notify the operator of discrepancies, it will also notify the operator that the report has printed.<br > If No, an OSD report is not printed automatically when an RF operator closes transport equipment with discrepancies. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
