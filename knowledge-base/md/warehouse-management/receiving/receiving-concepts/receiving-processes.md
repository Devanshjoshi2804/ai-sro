---
title: "Receiving processes"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/receiving_processes.htm"
source: "/content/receiving_processes.htm"
toc_path:
  - "Warehouse Management"
  - "Receiving"
  - "Receiving concepts"
  - "Receiving processes"
sections:
  - "Directed receiving work"
  - "Catch quantity inventory receiving"
  - "Lot-tracked inventory receiving"
  - "Handling unit receiving"
  - "Date code controlled inventory receiving"
  - "How received quantities are displayed for planned inbound order lines"
  - "Examples: How received quantities are displayed for planned inbound order lines"
  - "Example 1"
  - "Example 2"
  - "Example 3"
  - "Bonded inventory receiving process"
  - "Returns processing"
  - "Receipt reversal"
images: []
source_sha1: 935a7125c2b232a3c41fd14a8f73a34ffe30e85a
---
# Receiving processes

Receiving is the process of identifying inventory into your warehouse so that it can be tracked, processed, and stored. The following are examples of how inventory may arrive and be received at your warehouse:

-   With or without transport equipment
-   As expected (documented by an existing inbound order or planned inbound order) or unexpected (no inbound order)
-   Received from transport equipment at the dock door
-   Unloaded from transport equipment and received from a staging location
-   Received as a result of an internal (work) order from a production line or other processing location

The following tasks can be performed to receive inventory into the warehouse:

1.  **Download inbound orders for the expected inventory**.
    
    See [Inbound orders](inbound-orders.md).
    
2.  **Download or create an inbound shipment and planned inbound orders for the expected inventory**.
    
    See [Planned inbound orders](planned-inbound-orders.md) and [Inbound shipments](inbound-shipments.md).
    
    **Note**: If your facility allows receiving inventory into the warehouse without any prior documentation, you can receive inventory without an existing inbound shipment or inbound order.
    
3.  **Check in transport equipment or assign an inbound shipment to a staging lane**.
    
    If an inbound shipment is associated with transport equipment, you must check in the transport equipment to notify the application that it has arrived at the warehouse and to assign it to a location. Transport equipment can be parked in a yard location, or if you are ready to begin receiving, at a dock door. See [Check in transport equipment](../../shared-functions/transport-equipment/procedures-for-transport-equipment.md).
    
    If an inbound shipment is not associated with transport equipment, you must assign the inbound shipment to a staging lane before receiving can begin. A shipment may not be associated with transport equipment in the application, for example, if the equipment information was not included on a downloaded ASN. Alternatively, some facilities do not track the activities of transport equipment and must receive inbound shipments from a staging lane. See [Assign an inbound shipment to a staging lane](../inbound-shipments/procedures-for-inbound-shipments.md).
    
    If automated directed receiving has been enabled, then when transport equipment is checked in or when an inbound shipment is assigned to staging, directed work is automatically created and released to an appropriate RF operator to receive the inventory. See [Automated directed receiving](../../configuration/inbound/receiving.md).
    
4.  **Assign an operator to receiving transport equipment or an inbound shipment**.
    
    You can assign one or more operators to transport equipment or an inbound shipment so that the associated directed work is offered to those operators exclusively.
    
5.  **Move receiving transport equipment from a yard location to a dock door location**.
    
    Transport equipment must be moved to a dock door location before receiving can begin. During the move request, if configured to do so, the application can provide a list of optimal dock doors for receiving (based on the inbound inventory) so that putaway time for that inventory is minimized. See [Inbound Optimal Door Assignment](../../configuration/inbound/receiving/inbound-optimal-door-assignment.md).
    
6.  **Unload the inbound shipment**.
    
    You can unload an inbound shipment from transport equipment that is parked at a dock door location so that the transport equipment can be dispatched without having to wait for receiving to be complete. The inbound shipment retains the transport equipment information for tracking until its inventory is received and stored. See [Unload an inbound shipment](../../shared-functions/staging/procedures-for-staging.md). If you unload an inbound shipment, you can then move that shipment to a different staging location, if desired.
    
7.  **Receive the incoming inventory**.
    
    Receiving incoming inventory involves assigning inventory identifiers, indicating the quantity and inventory status, and applying applicable attribute values such as lot number and manufactured date. If available, inbound shipment or order information is used to populate the attribute values.
    
8.  **Receive empty handling units**.
    
    If your application is configured for inventory handling unit tracking, you can identify any empty handling units on the transport equipment and receive them into the warehouse.
    
9.  **Store the incoming inventory**.
    
    Received inventory must be moved out of the receiving location. Some inventory may be put away directly to a storage location; however, inventory that is needed to fulfill an outbound order may be moved to a cross dock location where it can be combined with an outbound shipment. If you perform storage without the use of RF devices, you can print a work sheet for storing the inventory. See [Put away received inventory](../inbound-shipments/procedures-for-inbound-shipments.md).
    
10.  **Record quality issues for inbound inventory**.
     
     To help you monitor the level of quality that you receive from suppliers and carriers delivering inventory to your facility, the application enables you to document quality issues that you encounter during receiving. For example, you can record that a supplier sent a quantity of damaged inventory, or that a carrier was late to arrive with an inbound shipment.
     
11.  **View and resolve receiving issues**.
     
     Receiving issues represent the disposition of inventory or unexpected receiving activity that can prevent the successful progression of receiving inventory into the warehouse. See [Receiving Issues](../receiving-issues.md).
     
12.  **Complete receiving**.
     
     When you have received all of the inventory associated with an inbound shipment or transport equipment, you can complete receiving, which enables you to close the following items:
     
     -   Transport equipment
     -   Inbound shipment

If you attempt to close an inbound shipment when the transport equipment has additional inbound shipments, then the application prompts you to confirm if you want to complete all of the inbound shipments on the equipment.

If you complete and close inbound shipments that have not been received, then the application displays a list of the receiving discrepancies, and inventory information is sent to the host. If you are not authorized to close inbound shipments with discrepancies, then the inbound shipments remain in their current status, and inventory information is not sent to the host until all inbound shipments on the transport equipment are received. Alternatively, if you close a single inbound shipment that was received, then the inventory information is sent to the host immediately.

When you complete receiving, the application removes existing receiving work and pre-identification inventory details created from an ASN from the application.

**Note**: It is recommended that all received inventory be stored before the transport equipment or inbound shipment is closed. If inventory is received, but not stored, it is noted as a discrepancy during the completion process.

## Directed receiving work

Directed receiving work is work that is associated with a piece of receiving transport equipment, and that can be performed by an operator using an RF or voice device. The application can be configured to automatically create and add directed receiving work to the work que when inbound transport equipment is checked in or moved to a dock door for unloading.

When an operator in directed mode has acknowledged a piece of receiving work, that operator remains assigned to the receiving work as long as the operator continues to identify and stage LPNs from the transport equipment. However, if the operator acknowledges a different piece of work, such as storing the inventory after receiving, the operator is unassigned from the receiving work. When an operator is unassigned from receiving work, the following scenarios are possible:

-   A different operator (authorized for receiving work) can acknowledge and continue the receiving work. This is especially useful if the original operator must travel a long distance to store the received LPN. Instead of the receiving work stopping while the original operator is performing the storage, the receiving work can be continued by a different eligible operator.
-   When the original operator has deposited the received LPN in a storage location, there may be a better piece of work in the vicinity of the storage location rather than traveling back to the dock to continue receiving. This reduces empty-handed travel and ensures that any higher priority work can be assigned to the operator.

Even though only one operator can be assigned to a piece of directed receiving work, additional operators can be manually instructed to help. The additional operators receive inventory off of the transport equipment using the RF receiving functions.

## Catch quantity inventory receiving

A catch quantity is a quantity that is represented in catch unit measurements, which are variable weights or sizes of inventory that may exist within the same material handling (stock keeping) unit. Catch quantities are especially important for the meat and dairy industry, where item weights can vary from piece to piece. The value of these items is based on the total weight of goods, rather than the logistic unit of measure, such as eaches or cases. For example, if a stock keeping unit is a case of meat, then the catch unit could be the weight, in pounds, associated with each case, since the weight can vary from case to case.

Depending on the value of the **Catch Code** field for an item, catch quantity can be captured during the receiving and shipping (picking) processes only; during receiving, processing and shipping; or only when the item is shipped (picked). However, when picking less than a full LPN, catch quantity capture is required regardless of the item's catch code. If the catch quantity is captured when an item is received, then the application also reports the quantity to the host. When an item's catch quantity is configured to be captured from cradle to grave, the application tracks the amount of catch quantity received and maintains it as long as the inventory is in the warehouse. When the item is configured to be captured during receiving and shipping only, then the captured catch quantity is removed from the application after the quantity is reported to the host.

## Lot-tracked inventory receiving

If lot tracking is configured for an item, the application manages inventory according to the following process:

1.  During receiving, the operator enters a lot number.
2.  If the lot number is associated with a lot format, the application determines whether the lot number is valid. If it is not, the operator must enter a valid lot number to continue.
3.  For date-tracked inventory, the following actions take place:
    -   If the lot number exists and has a manufactured or expiration date defined, the application uses the existing manufactured and expiration date for the lot.
    -   If the lot number is new and is associated with a lot format configured for date parsing, then the manufactured and expiration dates are parsed from the lot number.
    -   If the lot number is new but is not associated with a lot format, the operator must enter or confirm the manufactured or expiration dates during identification.
4.  If the lot number does not exist, the application creates and stores the item and lot combination. The item and lot combination is used to confirm future receipts. During picking, operators are required to confirm the lot number when they perform a pick.
5.  If the lot-tracked item is not date controlled, or if it is date controlled but no aging profile is assigned, the application populates the inventory status based on the inventory status that has been defined (in the following order of precedence) for the lot, the planned inbound order line, the supplier item, the supplier, or the item.

## Handling unit receiving

If your application is configured for Inventory handling unit tracking, then you can receive handling units from receiving transport equipment. You can receive empty non-serialized handling units using a process in the Receiving module that is separate from inventory receiving. See [Receive empty handling units](../inbound-shipments/procedures-for-inbound-shipments.md).

If you receive inventory on a handling unit, the application prompts for handling unit information during the normal receiving process; a separate process is not required.

**Note**: You can receive serialized handling units during receiving, or you can receive empty serialized handling units using an RF or mobile device.

Non-serialized handling units are tracked by the total quantity of a specific handling unit type. Alternatively, while serialized handling units are associated with a handling unit type, they are tracked at the individual level and can be uniquely identified.

When you receive non-serialized empty handling units, the application updates the quantity of the associated handling unit type; the handling unit type must exist in the application before receiving handling units of that type. When you receive serialized handling units, the application adds the unique handling unit LPN and any associated attributes.

You can view a summary of received empty and non-empty serialized and non-serialized handling units using the Received Inbound Shipment Handling Units Summary report. Alternatively, you can view the empty serialized and non-serialized handling units that were received against a specific inbound shipment. See [View received empty handling units](../inbound-shipments/procedures-for-inbound-shipments.md).

## Date code controlled inventory receiving

During receiving of date-tracked items, the application requires a value for the manufactured date, expiration date, or both, depending on the item's date code. The application assigns a date to inventory based on the following date codes:

-   **Manufactured Date**: If the manufactured date is not supplied by the lot or planned inbound order line, the application displays the current date and time for the manufactured date.
-   **Expiration Date**: If the expiration date is not supplied by the lot, planned inbound order line, aging profile, or shelf life, the application displays the current date and time for the expiration date.
-   **Both**: If the manufactured date is not supplied by the lot or planned inbound order line, the application displays the current date and time for the manufactured date. The expiration date is supplied by either the lot, planned inbound order line, aging profile, or shelf life.

**Note**: To retain data consistency with physical labels, manufactured dates and expiration dates are not converted to a different time zone when displayed in the web client or stored in the database, but retain their original captured time zone. For example, if a user views inventory that was received in a different time zone, the expiration date and manufactured date are displayed in the original time zone.

The operator can accept the default calculated expiration date or override it by manually entering a different date that is later than the manufactured date. If the item is associated with an aging profile, the application updates the inventory status based on the associated aging profile after the background inventory aging process runs.

**IMPORTANT**: After inventory has been received, its manufactured and expiration dates cannot be overridden.

See [Aging Profiles](../../configuration/inventory/inventory-status/aging-profiles.md).

## How received quantities are displayed for planned inbound order lines

The application displays the quantities received against a planned inbound order line in summary (by order line) and detail views (by sequence number for each order line). The summary view shows the quantity received, and the detail view shows the quantities based on item attributes that differ for inventory received against the same order line. You can view receiving progress on the Inbound Shipments dashboard and by accessing the details for each planned inbound order.

During receiving, the application attempts to match actual received quantities with expected quantities for planned inbound order lines. The attributes must match those on the planned inbound order line in order for the application to process the inventory against the order line. For example, if the order line requires an origin code of US (United States), the application only processes matching inventory with an origin code of US against the order line.

However, if a order line has an attribute value that is blank or "----", the application processes inventory against the order line regardless of the incoming attribute value. The application still requires a match for the other defined attributes on the order line, but any attribute having a value that is blank or "----" can be filled with inventory having any value for that attribute.

For example, if the origin code attribute is blank, then inventory having an origin code of US could be received against an order line, and inventory having an origin code of CAN (Canada) could be received against the same order line. The application records each quantity separately, by sequence number (such as 1, 2, and so on) for the order line.

## Examples: How received quantities are displayed for planned inbound order lines

The following examples show how the application uses sequence numbers to display the receipt of inventory against a planned inbound order line. The following examples use an expected quantity of 100 for ITEM01. In all cases, the expected quantity is represented by sequence number 0.

### Example 1

The following table shows that the first LPN matches what is required by the order line. Because the expected order line has the value of "----" for the lot number attribute, the application accepts inventory with a lot number of LOT5. The actual received quantity of 50 of ITEM01 is assigned the sequence number of 1.

**Note**: If the LPN had been identified with an origin code of CHINA instead of US, the inventory could not be received against line 0001 because the attributes do not match.

       
|   | **Order Line** | **Sequence Number** | **Item** | **Expected Quantity** | **Received Quantity** | **Origin Code** | **Lot** |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Expected | 0001 | 0 | ITEM01 | 100 | 0 | US | \---- |
| **Actual** | **0001** | **1** | **ITEM01** | **0** | **50** | **US** | **LOT5** |

### Example 2

The following table shows that an additional quantity of 40 is received against the same order line with a lot number of LOT7. Because this inventory matches what is required by the order line, but differs from the inventory previously received, it is assigned a sequence number of 2.

       
|   | **Order Line** | **Sequence Number** | **Item** | **Expected Quantity** | **Received Quantity** | **Origin Code** | **Lot** |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Expected | 0001 | 0 | ITEM01 | 100 | 0 | US | \---- |
| Actual | 0001 | 1 | ITEM01 | 0 | 50 | US | LOT5 |
| **Actual** | **0001** | **2** | **ITEM01** | **0** | **40** | **US** | **LOT7** |

### Example 3

The following table shows that an additional quantity of 10 is received against the same order line with a lot number of LOT5. Because this inventory matches the inventory for sequence 1, it is added to that line. The line quantity for sequence 1 is updated to 60. This fulfills the total expected quantity (100) of the order line.

       
|   | **Order Line** | **Sequence Number** | **Item** | **Expected Quantity** | **Received Quantity** | **Origin Code** | **Lot** |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Expected | 0001 | 0 | ITEM01 | 100 | 0 | US | \---- |
| **Actual** | **0001** | **1** | **ITEM01** | **0** | **60** | **US** | **LOT5** |
| Actual | 0001 | 2 | ITEM01 | 0 | 40 | US | LOT7 |

## Bonded inventory receiving process

The following is the process by which a planned inbound order for bonded inventory is processed in a bonded warehouse:

1.  During the identification of bonded inventory, a customs consignment is assigned to the planned inbound order. A customs consignment can be created prior to receiving using Customs Consignment Maintenance; or, if your application allows it, it can be created during receiving. All bonded inventory received into the warehouse must be associated with a specific consignment identified by a consignment ID.
    
    If an inbound shipment contains both bonded inventory and non-bonded or duty paid inventory, the receiving operator is not prompted for a customs consignment ID when receiving non-bonded or duty paid inventory. When the bonded inventory is received, the operator is prompted to enter or verify the customs consignment.
    
2.  A rotation number is assigned to all bonded inventory for the same planned inbound order line received on the same date. The rotation number is a unique, application-generated identifier that the application tracks as an attribute of the inventory.
3.  If an item is defined as an excise item and requires a duty stamp, then during receiving the user specifies whether duty stamps were applied.
4.  When a planned inbound order is closed, the customs consignment is automatically completed and sent to the duty management application for processing. If a future Customs hold has been configured, the inventory is placed on hold. Additionally, it is prevented from being put away until successful processing of the consignment by the duty management application unless Warehouse Management has been configured to allow putaway in spite of the consignment's processing status.
5.  When the duty management application completes the processing of the planned inbound order, it notifies Warehouse Management that processing is complete by changing the status of the consignment to Duty Processed, allowing putaway of the inventory and, if a Customs hold was applied, removing the hold automatically. If errors occurred during processing, the consignment must be corrected and reset to Complete so that it can be resent to duty management.
6.  Warehouse Management directs the putaway of received inventory using storage configuration rules.

### Returns processing

During returns processing, a rotation number is required to be entered for bonded inventory. If inventory for an item is shipped out under bond and it is returned to the warehouse under bond, then during receiving its rotation number remains the same as the original rotation ID that was assigned to it. Returns also require the creation of a customs consignment.

### Receipt reversal

If a customs consignment for bonded inventory has already been processed through a duty management application, then the planned inbound order for that inventory cannot be reversed. Instead, you must perform an inventory adjustment to remove the inventory from the warehouse. It would then need to be identified (received again) to be brought back into the warehouse.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
