---
title: "Inbound shipments"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/inbound_shipments_concept.htm"
source: "/content/inbound_shipments_concept.htm"
toc_path:
  - "Warehouse Management"
  - "Receiving"
  - "Receiving concepts"
  - "Inbound shipments"
sections:
  - "Inbound shipments and transport equipment"
  - "Inbound shipment use scenarios"
  - "Receive transport equipment that arrives with conflicting paperwork"
  - "Receive inventory from unexpected transport equipment"
  - "Add unexpected inventory to an inbound shipment"
  - "Receive inventory without transport equipment"
  - "Receiving transport equipment status"
images: []
source_sha1: ab28b7a7dd0c6e5d5763478bc13257ac92b84c3c
---
# Inbound shipments

An inbound shipment is a group of orders that are transported to the warehouse together or received together. When inventory arrives at the warehouse on transport equipment, an inbound shipment represents the contents of the transport equipment; however, multiple inbound shipments can be associated with a piece of transport equipment. When an inbound shipment arrives without transport equipment, the inbound shipment is used to collect receiving information for a group of orders.

An inbound shipment includes the expected inventory and groups receiving information, such as inventory received and order fulfillment, for reconciliation by the host. An inbound shipment also provides the overall status of receiving activities for the group of orders and provides information about the transport equipment, if used, and its status. If an inbound shipment is not associated with transport equipment, you must assign the inbound shipment to a staging lane before receiving can begin.

Inbound shipments are typically sent from a host application; however, in the absence of downloads or to meet last minute needs, you can use the Inbound shipments page to create a new inbound shipment.

Inbound shipments are not required to receive inventory into the warehouse; however, they can be used to accommodate both planned and unplanned inventory.

## Inbound shipments and transport equipment

Transport equipment delivers inventory to your facility. Receiving transport equipment can be associated with an inbound shipment that identifies the inventory that is expected on the transport equipment. This association enhances your ability to manage the activity in your yard by letting you track the movements, location, and status of the transport equipment delivering inventory to your facility, as well as providing insight into the transport equipment's contents.

Receiving transport equipment is not required for you to receive incoming inventory; however, if used, the inbound shipment details associated with the transport equipment, which are typically sent from a host system, are available during the receiving process. As you move through the receiving process, the status of the transport equipment or inbound shipment changes accordingly.

If a piece of transport equipment arrives unexpectedly, or arrives without shipment information, receiving activities can still take place without the application being updated with transport equipment information. Instead, you can initiate receiving in one of the following ways:

-   Against an existing planned inbound order or advance shipment notification (ASN)
-   Against an existing inbound order
-   Without documentation, if allowed

If an inbound shipment is not associated with transport equipment, you must assign the inbound shipment to a staging lane before receiving can begin.

## Inbound shipment use scenarios

The following scenarios provide examples of inbound shipment use.

### Receive transport equipment that arrives with conflicting paperwork

The application enables you to reconcile and receive transport equipment that arrives at your facility with paperwork that conflicts with the original paperwork.

For example, if transport equipment arrives with a different number of inbound orders than is expected, you can modify an inbound shipment by adding or removing order or order lines so that the actual inbound shipment matches the expected inbound shipment. Once the records are reconciled, you can then check in the transport equipment and begin receiving.

### Receive inventory from unexpected transport equipment

The application enables you to manually create transport equipment and inbound shipments in order to receive inventory from unexpected transport equipment that may arrive at your facility.

For example, Trailer B arrives with inventory that you want to receive but were not expecting. You can use the application to manually create the following items:

-   Transport equipment
-   An inbound shipment
-   Inbound orders that describe the inventory that you want to receive

You can begin receiving from the transport equipment, the inbound shipment, or the order lines. Alternatively, if allowed, you can receive the inventory without documentation.

### Add unexpected inventory to an inbound shipment

Depending on how your warehouse operates, you may choose to modify an inbound shipment to account for unexpected inventory that arrives at the warehouse. You can modify the inbound shipment at any time before you close the shipment or the associated transport equipment to reflect the actual inventory that you want to receive.

For example, if your vendor informs you that an item was added to an inbound shipment due to unexpected space on the transport equipment, you can modify the shipment and related order to include a new order line to accommodate the unexpected inventory. Then, when the transport equipment arrives with the extra item, you are prepared for receiving.

Alternatively, you can receive unexpected inventory without adding it to an inbound shipment or order.

### Receive inventory without transport equipment

You can receive inventory from an inbound shipment in the following situations:

-   When inventory does not arrive on transport equipment. For example, it may have been deposited to a receiving staging location from a manufacturing location.
-   When the transport equipment departs prior to receiving the inventory. In this case, the inventory associated with the inbound shipment is unloaded to a receiving staging location from which it is received.

## Receiving transport equipment status

The receiving transport equipment status is assigned by the application, and it is used to identify the status of transport equipment in relation to the receiving processes. The application updates the status as the equipment is checked into a dock or yard location and as it moves within the yard.

The following receiving transport equipment statuses are used:

-   **Expected**: Transport equipment information is created or downloaded.
-   **Checked In**: Transport equipment is checked in to a yard location.
-   **Open For Receiving**: Transport equipment is checked in or moved to a dock door location.
-   **Receiving**: Unloading from the transport equipment has been started or the equipment is moved from a yard location back to a dock door location after receiving had already been started.
-   **Suspended**: Transport equipment is moved from a dock door location to a yard location after receiving had been started but not completed.
    
    **Note**: If receiving work exists in the work queue for suspended transport equipment, the receiving work is also set to Suspended. RF operators will not be directed to perform the receiving work until the transport equipment is moved back to a dock door location.
    
-   **Closed**: Receiving from the transport equipment is completed or the inventory on the equipment has been unloaded to a staging lane. The equipment is ready to be dispatched or ready to be turned around and used for shipping. Additionally, equipment may be temporarily closed to move it to a different door.
-   **Open For Shipping**: Transport equipment at a dock door was closed and turned around to be used as shipping transport equipment.
-   **Dispatched**: Transport equipment is closed and dispatched from the yard.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
