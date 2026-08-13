---
title: "Inbound Shipments"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/inbound_shipments_config.htm"
source: "/content/inbound_shipments_config.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inbound"
  - "Receiving"
  - "Inbound Shipments"
sections:
  - "Inbound order types"
  - "Configure inbound shipments"
  - "Inbound Order Type fields"
images: []
source_sha1: 527d3149154c153d466c31c7dfc7982995895ef3
---
# Inbound Shipments - Configuration

An inbound shipment is a group of planned inbound orders that are either transported to the warehouse together or received together. When inventory arrives at the warehouse on transport equipment, an inbound shipment represents the contents of the transport equipment. One or more inbound shipments can be associated with transport equipment.

When inventory does not arrive on transport equipment, the inbound shipment is used to collect receiving information for a group of planned inbound orders. Inventory may be received without transport equipment, for example, when it arrives from a manufacturing operation or is deposited to a staging location from transport equipment that has left the yard.

You configure inbound shipments with the following attributes:

-   Whether RF operators can create and check in an inbound shipment (with or without transport equipment)
-   Inbound order types used to group inbound orders for searching, reporting, and processing purposes
-   Number of days in advance to plan labor for processing an inbound shipment. Warehouse operations require labor estimates for planned inbound orders to be available for planning labor for receiving. The application calculates estimates based on ASNs and planned inbound orders, and provides visibility to the estimates during receiving dock and appointment scheduling operations. The application also adjusts the estimates in response to adjustments to ASNs and receiving actuals. Labor planning is only available if Warehouse Labor Management is integrated with Warehouse Management. Labor planning is useful in the following types of scenarios:
    -   When your receiving dock supervisor wants to fill an empty slot in the appointment schedule, the labor estimates can assist in matching the slot duration with the inbound shipments waiting to be unloaded.
    -   When the arrival of a high priority inbound shipment requires reordering of the schedule. The labor estimates can assist in optimizing the new schedule.

## Inbound order types

An inbound order type is a user-defined category that is applied to an order to represent its purpose and define its processing characteristics.

Inbound order types are used to group inbound orders into categories for the following purposes:

-   Reporting
-   Determining what actions should be taken when inventory associated with a particular order type is received
-   Initiating a workflow when inventory associated with a particular order type is received. For example, if you want operators to perform a quality check on all inventory associated with customer returns, you can create an inbound workflow that is applied to inventory associated with the Customer Return order type. When inventory associated with a Customer Return order is identified, operators are instructed to perform a quality check as defined in the workflow.
-   Searching for orders. For example, you can create a Purchase Orders inbound order type, apply it when creating unplanned inbound orders, and then search for this order type to find all unplanned inbound orders.

## Configure inbound shipments

1.  Select **Configuration > Inbound > Receiving > Inbound Shipments**.
2.  Enter information in the following fields:
    
     
    | Field | Description |
    | --- | --- |
    | Checking in Equipment | If Yes, an operator is allowed to check in an inbound shipment when performing RF identification or receiving functions.<br > If No, an RF operator can only process inventory against an inbound shipment that has already been checked in. |
    | RF Create Inbound Shipment | If Yes, an operator can create an inbound shipment prior to performing RF identification or receiving functions.<br > If No, an operator can only process inbound inventory against existing inbound shipments. |
    
3.  To define the order types that are used to group inbound orders:
    1.  Under **INBOUND ORDERS**, click **Order Type**.
    2.  Perform one of the following tasks:
        -   To add an order type, click **Add**.
        -   To modify an order type, in the grid, click the order type.
    3.  Enter information in the [Inbound Order Type fields](#Inbound_Order_Type_fields).
    4.  Click **Apply**. The Inbound Order Types page is displayed.
    5.  To delete an inbound order type:
        1.  In the grid, select the check box next to the order type to delete, and then click **Delete**. A confirmation message is displayed.
        2.  Click **OK**.
    6.  Click **Apply**.
4.  Click **Save**.

## Inbound Order Type fields

 
| Field | Description |
| --- | --- |
| Order Type | Inbound order type that represents a category used to group inbound orders that have the same purpose and processing characteristics, such as unplanned inbound orders, warehouse transfers, or customer returns. |
| Description | Meaningful description that further describes the inbound order type. The description is used to identify the order type in reports and as a selection within drop-down fields. |
| Use Standard Putaway | If Yes, the application directs the putaway of inventory for the inbound order to standard assigned locations first, even if the application is configured to skip assigned locations for items that are configured with a first-in-first-out (FIFO) date window. (The configuration to skip assigned locations for inventory with a FIFO date window is used to prevent placing newer inventory into assigned locations when older inventory exists in unassigned locations.) Selecting Yes allows all inventory, including inventory with a FIFO date window, to be directed to assigned locations first, which reduces the number of replenishments required for pick locations.<br > If No, the application respects the configuration to skip assigned locations for inventory that has a FIFO date window, but it still directs other inventory (items that are not configured with a FIFO date window) to assigned locations first. |
| Delivery Inbound Order Type | If Yes, the order type is associated with delivery confirmation processing to receive haul-away items through that process. During the delivery confirmation process, when transport equipment returns to the warehouse, if any unexpected inventory exists on the transport equipment that was not originally sent out on the transport equipment, you must receive it using this order type. Unexpected inventory could be, for example, an old appliance that was hauled away after a new appliance was delivered. When adding unexpected delivery orders, the application creates an inbound order of this type for each unexpected item that was added to the returned delivery transport equipment. This gives you the needed information against which to identify and put away the unexpected item.<br > If No, the order type is not associated with delivery confirmation processing. |
| Return Inbound Order Type | If Yes, the order type is for inbound orders for inventory that has been or will be returned to the warehouse. For inbound orders of this type, during receiving, the operator is prompted to select a reason for the return. In addition, unexpected (blind) receiving is automatically enabled for this type of inbound order, regardless of the configuration for blind receiving. The reason is that the application creates the inbound order for returns processing without information on the items or quantities being returned.<br > If No, inbound orders with this order type are not used for returned inventory. |
| GS1 Inbound Order Type | GS1 inbound order type that corresponds to the Warehouse Management inbound order type. If integrated with Warehouse Management, Connect sends this GS1 inbound order type value in outgoing messages to other systems, and sends the WM inbound order type value in inbound messages. |
| WM Default | If Yes, then when multiple Warehouse Management inbound order types correspond to the **GS1 Inbound Order Type** value, this WM order type is used by default. If integrated with Warehouse Management, Connect sends the GS1 order type value in outgoing messages to other systems, and sends the default WM inbound order type value in inbound messages. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
