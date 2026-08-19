---
title: "Connect"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/connect.htm"
source: "/content/connect.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Integration"
  - "Connect"
sections:
  - "Connect GS1 messages"
  - "Configure Connect integration"
images:
  - "/content/resources/images/back_wmconfig.png"
source_sha1: 502875541b6bbfe8158e96fae70f3a99442073ec
---
# Connect

Connect supports the use of GS1 industry standard data format to promote agile and responsive communications across numerous applications from the planning and execution line of Blue Yonder products (and external systems). Integration with Connect ensures that information from one application is communicated to another, as needed, to enable seamless management of transfer orders, the customer order lifecycle, and inventory updates across multiple business processes and roles in the enterprise. This promotes intelligent distribution decision making that reduces costs and improves customer service through superior product availability and faster throughput.

Connect communicates with Warehouse Management (WM) through an adapter (the canonical system of Integrator) that transforms GS1 messages to the standard inbound WM integration transactions, and standard WM outbound transactions to GS1 messages. The Connect message broker monitors an Enterprise Service Bus (ESB), which is a communication thoroughfare between interacting systems, for messages relevant to WM. The message broker consumes the message and can then send it to Integrator (the adapter for WM) to send to WM. Messages received through the ESB can originate from a host system, a Blue Yonder product, or any other interacting system that communicates in the standard GS1 format.

For example, assume that a facility communicates between systems using an ESB, and that two of the systems are WM and Transportation Manager (TM) or other external transportation management system. When information needs to be communicated to TM, WM sends a message to the canonical Integrator system (the adapter that transforms the message to GS1), and the GS1 message is sent to Connect. The Connect message broker presents that message to the ESB, and it can then be received by the TM adapter for translation to the proper data format before being sent to TM. The communication flow is the same regardless of whether the transportation management system to which WM is sending data is a Blue Yonder product; you can define the receiving systems for each message in the Connect configuration.

## Connect GS1 messages

You can define and enable the systems to which messages are sent when the following tasks are executed: 

**Note**: For more information about the integration transactions, see the _Warehouse Management Integration Transactions Overview_.

-   **Acknowledge message**: The Application Receipt Acknowledgment GS1 message is sent whenever Warehouse Management receives a GS1 message from a canonical system. The message is sent through the GS1\_ACK\_NACK\_TO\_CANONICAL integration transaction to the sending system of the original message, and indicates whether or not the inbound message was successfully processed.
-   **Appointment updated or deleted**: The Transport Pickup Dropoff Confirmation GS1 message is sent whenever an appointment is updated (such as changing the date, time, and dock slot) or deleted. If the appointment is updated, the message is sent through the APPT\_UPDATE\_TO\_CANONICAL integration transaction. If the appointment is deleted, the message is sent through the APPT\_DELETE\_TO\_CANONICAL integration transaction.
-   **Inbound shipment complete**: The Receiving Advice GS1 message is sent through the MASTER\_RCPT\_COMPL\_TO\_CANONICAL integration transaction whenever an inbound shipment is completed.
    
-   **Return order closed**: The Receiving Advice GS1 message is sent through the RECEIVE\_RETURN\_TO\_CANONICAL integration transaction whenever a return order is closed.
-   **Unexpected inventory received**: The Receiving Advice GS1 message is sent through the BLIND\_RECEIPT\_TO\_CANONICAL integration transaction whenever unexpected inventory is received.
-   **Load shipped**: The Despatch Advice GS1 message is sent through the CARRIER\_MOVE\_TO\_CANONICAL integration transaction whenever an outbound load is shipped. The message is sent for full truckload (FTL) and less than truckload (LTL) loads, and for outbound loads shipped by a parcel application (integrated through Parcel Handler).
-   **Order updated or deleted**: The Order GS1 message is sent whenever an outbound order is updated, deleted, or cancelled in Warehouse Management. If an order is updated, the message is sent through the ORDER\_UPDATE\_TO\_CANONICAL integration transaction. If an order is deleted or cancelled, the message is sent through the ORDER\_DELETE\_TO\_CANONICAL integration transaction.
    
-   **Outbound shipment updated**: The Warehousing Outbound Notification GS1 message is sent through the SHIP\_STATUS\_TO\_CANONICAL integration transaction whenever the status of an allocated outbound shipment changes. After you define and enable the receivers for this message, you must also enable the specific shipment statuses so that information is sent to the receivers when the shipment reaches each enabled status. For example, you can enable statuses for when picks are cancelled and when picks are complete (staged) so that information is sent to the defined planning system when a shipment's status is updated to Cancelled (PICK\_CANCEL) or Staged (PICK\_COMPLETE).
-   **Outbound shipment allocated**: The Warehousing Outbound Notification GS1 message is sent through the SHIP\_STATUS\_TO\_CANONICAL integration transaction whenever an outbound shipment's status is changed from Ready to In Progress (when the shipment is allocated).

## Configure Connect integration

When you configure the Connect integration, you specify the following types of information:

-   Receiving systems to which messages from Connect are sent.
-   How values defined in Warehouse Management map to their corresponding GS1 values.
-   Whether messages are sent when a shipment status is updated to Cancelled or Completed.

1.  Select **Configuration > Integration > Connect**.
2.  To enable integration, in the **Enable Connect** field, select **Enabled**.
3.  If 3PL is disabled, then in the **Enterprise** field, enter the default enterprise value that is used to populate all client values in outbound GS1 messages.
4.  To determine if the Bill-To Address and the Ship-To Address on an order are included in the Despatch Advice GS1 message, select one of the following values from the **Include Address in Despatch Advice** field:
    
    -   **Never**: The addresses are never included in the message.
    -   **Manifest Only**: The addresses are only included for manifested parcel shipments.
    -   **Always**: The addresses are always included in the message.
5.  In the **APPOINTMENTS**, **RECEIVING**ADVICE**, **RETURNS**, and **RECEIVERS sections, add the receiving systems to which a message is sent when a task is executed:
    
    **Note**: For more information on the processing tasks and associated GS1 messages that are sent, see [Connect GS1 messages](#Connect_GS1_messages).
    
    1.  In the grid for the processing task, click **Add**.
    2.  In the **Receiver** field, enter the receiving system.
    3.  To enable the receiver for messages, set the **Enabled** field to Yes.
    4.  Click **Save**.
6.  Under **Receivers**, enable or disable the following shipment statuses to indicate whether a message is sent to the enabled receivers of the **Outbound Shipment Updated** processing task when a shipment reaches the status:
    -   **Pick Cancel**: If enabled, a message is sent when a shipment status is updated to Cancelled.
    -   **Pick Complete**: If enabled, a message is sent when a shipment status is updated to Completed.
7.  To map Warehouse Management configuration values to standard GS1 values: 
    
    **Note**: Mapping consists of defining WM configuration values and their corresponding GS1 values. Connect sends the GS1 value in outgoing messages to other systems, and sends the WM value in inbound messages. You can map values for the following configurations: dock sets, return conditions, return reasons, inventory statuses, freight codes, order change reasons, order priorities, and service conditions.
    
    1.  In the **DOCK SET**, **RETURNS**, **INVENTORY**, and **RECEIVERS** sections, click the **Mapping** button for the configuration.
    2.  Click **Add**.
    3.  Enter information in the following fields:
        
         
        | Field | Description |
        | --- | --- |
        | WM Value | Warehouse Management configuration value that corresponds to the GS1 value. For example, if you are mapping dock sets, enter a dock set value as defined in WM, and then enter the corresponding GS1 dock set value in the **GS1 Value** field. |
        | GS1 Value | GS1 code value that corresponds to the Warehouse Management value. For example, if you are mapping dock sets, enter a standard GS1 dock set, and then enter the corresponding WM dock set in the **WM Value** field. |
        | WM Default | If Yes, then when multiple Warehouse Management configuration values correspond to the same **GS1 Value**, the defined **WM Value** is used by default. Connect sends the GS1 value in outgoing messages to other systems, and sends the default WM value in inbound messages. |
        | GS1 Default | If Yes, then when multiple GS1 values correspond to the same **WM Value**, the defined **GS1 Value** is used by default. Connect sends the default GS1 value in outgoing messages to other systems, and sends the WM value in inbound messages. |
        
    4.  Click **Save**, and then click **![Previous page](../../../../images/resources/images/back_wmconfig.png).**
8.  Click **Save**.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
