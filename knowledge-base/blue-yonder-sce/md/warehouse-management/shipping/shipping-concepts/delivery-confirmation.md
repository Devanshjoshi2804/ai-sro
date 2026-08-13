---
title: "Delivery confirmation"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/delivery_confirmation.htm"
source: "/content/delivery_confirmation.htm"
toc_path:
  - "Warehouse Management"
  - "Shipping"
  - "Shipping concepts"
  - "Delivery confirmation"
sections:
  - "Undelivered inventory"
  - "Unexpected delivery receipts"
  - "Delivery transport equipment status"
  - "Business process decisions for delivery confirmation"
  - "Delivery confirmation configuration tasks"
images: []
source_sha1: 298a7dfffd31777e9323bf85a4c97eb12fcdd96b
---
# Delivery confirmation

Delivery confirmation is the process of accounting for undelivered inventory and unexpected delivery receipts on returned delivery transport equipment.

In situations in which you retain ownership of inventory that is shipped on delivery transport equipment, you can process returned delivery transport equipment to account for undelivered inventory and unexpected delivery receipts.

For example, delivery transport equipment is loaded with orders to deliver a washer and dryer to house #1, a freezer to house #2, a 42" television to house #3, a refrigerator to house #4, and 50 computers to a business. During the delivery of the washer and dryer, the customer accepts delivery of the washer but refuses delivery of the dryer. During the delivery of the television, the customer sends back the 37" television that was delivered to them the previous week. During the delivery of the refrigerator, the old refrigerator is removed to the delivery transport equipment for disposal. During the delivery of the computers, the business accepts delivery of 49 computers, but sends a damaged computer back with the driver.

Transactions for successful deliveries are sent to the host application after the returned delivery transport equipment is processed. Inventory that was not delivered is returned to the warehouse and made available for future orders. In addition, any unexpected delivery receipts, such as a television and old refrigerator, are received into the warehouse and processed.

Delivery confirmation takes place after orders are planned into waves, inventory is allocated, picked for the shipments and then loaded onto the delivery transport equipment, the delivery transport equipment is closed and dispatched, inventory is delivered to customer stops, and the delivery transport equipment returns to the facility.

## Undelivered inventory

Undelivered inventory is inventory that was sent out on delivery transport equipment, but was not delivered and is still on the delivery transport equipment when it returns to the warehouse. Since all information about inventory that went out on delivery transport equipment is stored in the application, when that inventory is not delivered, you only need to specify a few additional attributes to indicate that the inventory was not delivered.

Information about the undelivered inventory is saved to let you generate queries and reports about this type of inventory. For example, information about undelivered inventory is saved with an operation code of Undelivered Inventory (UNDLVINV).

The application provides the following reasons to support undelivered inventory:

-   Customer Refused Delivery
-   Customer Was not Home
-   Incorrect Item
-   Item Damaged

**Note**: You can add your own reasons in Code Maintenance-Supervisor using a Column value of "undlv\_reacod".

## Unexpected delivery receipts

An unexpected delivery receipt is an item that was not shipped on the delivery transport equipment, but which is on the delivery transport equipment when it returns to the warehouse. Examples of such unexpected inventory are a haul away (the customer exchanged an old appliance for a new appliance) or something the customer returned that was delivered on a different outbound shipment. No information is stored in the application about unexpected delivery receipts, therefore you must provide the needed information. This process is similar to receiving new inventory from suppliers into the facility.

## Delivery transport equipment status

Delivery transport equipment passes through the following shipping transport equipment statuses:

-   **Expected**: The transport equipment has been created or downloaded from the host application, and is expected to arrive at the facility, but has not yet been checked in.
-   **Checked in**: The transport equipment has been checked into or moved to your yard and is parked in a yard location waiting to be moved to a shipping dock door so that loading of the shipments for delivery can begin.
-   **Open for shipping**: The transport equipment has been checked into or moved to a shipping dock door. At this time, an operator may begin loading the transport equipment, but loading has not yet begun.
-   **Loading**: The transport equipment is currently being loaded.
-   **Suspended**: The transport equipment has been moved from a dock door location to a yard location after loading was started but before loading was completed. When transport equipment has a Suspended status, loading work is held. To resume loading, the transport equipment must be moved back to a shipping dock door location.
-   **Loaded**: The transport equipment has been completely loaded.
-   **Closed**: The stops have been completed and the transport equipment is ready to be dispatched for delivery.
-   **On delivery**: The transport equipment has been dispatched and is currently out on a delivery. This transport equipment status is unique to the delivery transport equipment.
-   **Returned from delivery**: The transport equipment has returned from the delivery attempt and has been checked in to the yard or a dock door. The transport equipment status is unique to the delivery transport equipment.
-   **Unloading**: The transport equipment has returned from its delivery, any undelivered inventory and unexpected delivery receipts on the transport equipment have been specified, unexpected delivery receipts have been identified or put away, and the unloading process has been started. This transport equipment status is unique to the delivery transport equipment.
-   **Delivery complete**: The transport equipment has returned from its delivery and it is empty. It is empty because either all of the deliveries were made and no unexpected items were received or all of the undelivered inventory and unexpected delivery receipts have been removed from the transport equipment. This transport equipment status is unique to the delivery transport equipment.
-   **Dispatched**: The transport equipment has returned from its delivery, has been processed for undelivered inventory and unexpected delivery receipts, and has either permanently left the facility or been turned around for another delivery run. The host transactions have been sent.

## Business process decisions for delivery confirmation

Before using delivery confirmation in your facility, you need to make the following business process decisions:

-   Decide how to add undelivered inventory and unexpected delivery receipts; for example, you can require that the driver note this information on the shipping documentation.
-   Decide how to label unexpected delivery receipts; for example, you can use pre-printed LPN labels or a custom LPN label.
-   Decide how to identify and put away unexpected delivery receipts. For example, you can perform both functions at a workstation, perform both functions using RF devices and undirected RF Identify and RF Receive, or perform one function at a workstation and the other function using RF devices.
-   If you are using RF Identify or RF Receive, decide how to notify the RF operators that unexpected delivery receipts are ready to be identified or put away when there is no undelivered inventory; for example, you can verbally notify them, or use the Message page to send a message to the RF devices.

## Delivery confirmation configuration tasks

You must perform the following tasks to configure the application for delivery confirmation.

1.  Define any additional undelivered inventory reasons in Code Maintenance-Supervisor using a Column value of "undlv\_reacod".
2.  Set up the application for handling unexpected delivery receipts:
    1.  Define items for unexpected delivery receipts, such as OLDREF, OLDFRZR, and OLDTV. These items can be as specific or as general as needed for properly applying putaway rules and workflow processing. For example, you can create two items: COMPDONATE to be used to identify newer haul-away computers and COMPOLD to be used to identify older haul-away computers.
    2.  If desired, configure processing and storage zones and locations for unexpected delivery receipts. For example, you can configure a Recycle Computers zone with locations for storing COMPDONATE items and a Scrap zone with locations for storing COMPOLD items.
    3.  Configure putaway rules for unexpected delivery receipts. For example, you can configure the application so that all newer haul-away computers, identified as COMPDONATE, are put away to the Recycle Computers zone from which the computers can be allocated to an order for shipping to a school or library. You can also configure the application so that all older haul-away computers, identified as COMPOLD, are put away to the Scrap zone for appropriate disposal.
    4.  If desired, configure workflows to be applied to unexpected delivery receipts. For example, you can configure the application so that a workflow to prepare computers for donation to a school or library is applied to all newer haul-away computers, identified as COMPDONATE, before they are put away to the Recycle Computers zone.
3.  If you are using directed work to unload returned delivery transport equipment, then define which users are authorized to perform directed transport equipment unloading.
4.  Create delivery transport equipment by selecting the Shipping transport equipment type, and setting the **Delivery** field to Yes.
    
    **IMPORTANT**: Shipping transport equipment must be defined as delivery transport equipment before it is checked in (while the transport equipment's status is Expected).
    

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
