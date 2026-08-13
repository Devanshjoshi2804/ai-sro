---
title: "Planned inbound orders"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/planned_inbound_orders.htm"
source: "/content/planned_inbound_orders.htm"
toc_path:
  - "Warehouse Management"
  - "Receiving"
  - "Receiving concepts"
  - "Planned inbound orders"
sections:
  - "Planned inbound order use scenarios"
  - "Track progress of an expected inbound order"
  - "Receive additional or unexpected inventory"
  - "Receive unexpected transport equipment"
  - "Receive an unexpected inbound shipment"
  - "How planned inbound order lines are updated during receiving"
  - "Examples: Planned inbound order line updates"
  - "Receive 1"
  - "Receive 2"
  - "Receive 3"
images: []
source_sha1: ce875b8a75022b4246ebfc0b85b6c4d2f5e64b63
---
# Planned inbound orders

A planned inbound order is an authorization to receive specific inventory and quantities from a supplier. It is used, but not required, to receive inventory into the warehouse. Planned inbound orders can be associated with an inbound shipment, which can be associated with inbound transport equipment. Planned inbound orders can include one or more order lines that contain the following information:

-   Items to be received in a single shipment
-   Quantity of the items to be received

**Note**: If you do not associate a planned inbound order with an inbound shipment, then during receiving, the application automatically generates an inbound shipment for the order and closes that shipment automatically when the inbound order is complete.

Planned inbound orders are typically sent from a host application as part of an inbound shipment; however, in the absence of downloads or to meet last minute needs, you can use the Inbound Shipments page to add a new order to an existing inbound shipment.

**IMPORTANT**: When defining the inventory attributes for a planned inbound order line, remember that a date, such as manufactured date, represents a detail that can be very difficult to fill because the application would only match inbound inventory that has the same manufactured date.

If a planned inbound order contains advanced shipment notification (ASN) information, it also displays the individual license plate numbers (LPNs) that will be sent on the transport equipment.

## Planned inbound order use scenarios

The following scenarios provide examples of inbound order use.

### Track progress of an expected inbound order

You can use planned inbound orders to track the receiving progress of expected inventory. Understanding how much inventory is expected, received, and stored can help you better manage your receiving operations for the receipt of that inventory.

You can track the progress of inbound shipments on the Inbound Shipments page. From this page you can access inbound order and order line details that display the quantities expected, received, and stored.

### Receive additional or unexpected inventory

When receiving additional or unexpected inventory, you can create a new planned inbound order that describes the inventory, and then optionally associate that order with an inbound shipment.

For example, assume that a warehouse expects a shipment of 100 televisions from Supplier A and 50 laptop computers from Supplier B, and has prepared to receive this inventory by downloading information for an inbound shipment for that inventory. When the transport equipment arrives, the receiving operator discovers that it also contains an order of 75 keyboards from Supplier C. To reconcile this order, the receiving clerk can view the inbound shipment, which also contains the orders from Supplier A and B, from the Inbound Shipments page and add a new order and order line for the 75 keyboards.

### Receive unexpected transport equipment

When unexpected transport equipment, such as a trailer, containing inventory that you want to receive arrives at your facility, and you want to use a planned inbound order to receive the inventory, you can do so by performing the following tasks:

-   Create the transport equipment in the application.
-   Create planned inbound orders and associated orders lines for the inventory to receive.
-   Optionally, associate the new order with an inbound shipment. If you do not specify an inbound shipment, the application generates an one automatically during the receiving process.
-   Check in the transport equipment and begin receiving from a dock door, or unload the inbound shipment and begin receiving from a staging location.

### Receive an unexpected inbound shipment

If an inbound shipment arrives, regardless of whether it is on transport equipment, you can use information from the shipment's packing slip to create a planned inbound order prior to or during receiving. This process allows the received inventory to be tracked against an existing inbound order in Warehouse Management or the host application.

## How planned inbound order lines are updated during receiving

During receiving, the application attempts to match actual received quantities with expected quantities listed on the order lines for planned inbound orders. You can use the Outbound Planner module to view planned inbound order lines and the details of the inventory that was actually received against each line.

Planned inbound order line quantities are updated when inventory is received against a line, filling the line’s expected quantity. Each line is associated with a line number, such as 001 or 002, and a sequence number. The sequence number for expected inventory is 0 (zero). When inventory is received against a planned inbound order, another row is added to the order information that has the same line number, but a different sequence number (such as 1) to indicate it is a received quantity. You may have multiple sequence number rows associated with a single planned inbound order line if multiple LPNs of inventory, with differing attributes, were received against a single line. The sequence number record shows line information for the inventory that was applied to the planned inbound order line’s expected quantity. If sequence number records share the same inventory attribute values, they are grouped into one sequence number.

When the application identifies incoming inventory to receive against a planned inbound order line, the attributes of the incoming inventory must match those on the line in order for the application to process the planned inbound order. For example, if the order line has an item with an origin code value of US, the application would only receive inventory against that line if its origin code was also US. However, if a planned inbound order line has an item with an attribute value that is null (blank) or ---- (four dashes), the application will receive inventory against the order line regardless of the incoming attribute value. The application will still look to match other defined attributes on the planned inbound order line, but any attribute having a value that is null or ---- can be filled with inventory having any value for that same attribute.

**IMPORTANT**: If you are using a date field such as manufactured date as an inventory attribute, it is important to remember that date fields can contain a high level of detail which can cause problems in filling the order. For example, if the item on the planned inbound order line has a manufactured date that includes month/day/hours/minutes, the application would only match inventory that has the same manufactured date, down to the exact minute. Date attribute configurations should be monitored in order to prevent situations of matching dates that contain a high level of detail.

## Examples: Planned inbound order line updates

The following examples use a planned inbound order line for a quantity of 100 of ITEM01 and show how incoming inventory is matched and received against the line. Since the planned inbound order line is an expected quantity and does not represent an applied quantity, its sequence number is 0.

### Receive 1

The first LPN identified matches the origin code attribute and is received against the planned inbound order line, as shown in the following table. Additionally, because the expected order line has the value of ---- as the lot number attribute, the application accepts inventory from any lot, in this case from LOT5. The following table is an example of a quantity of 50 of ITEM01 being received against the line and being assigned the sequence number of 1.

**Note**: If the LPN had been identified with an origin code of CHINA instead of US, the inventory would not have been received against line 0001 because the attributes do not match.

       
|   | Line number | Sequence number | Item | Expected quantity | Received quantity | Origin code | Lot number |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Expected | 0001 | 0 | ITEM01 | 100 | 0 | US | \---- |
| Actual | **0001** | **1** | **ITEM01** | **0** | **50** | **US** | **LOT5** |

### Receive 2

The application then receives an additional quantity of 40 with the expected origin code of US, but this time coming from LOT7. This inventory transaction against the planned inbound order line is given a sequence number record of 2 because it is the second quantity received against the line, and since the attributes differ from sequence number 1, the application creates a new record for the inventory.

       
|   | Line number | Sequence number | Item | Expected quantity | Received quantity | Origin code | Lot number |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Expected | 0001 | 0 | A | 100 | 0 | US |   |
| Actual | 0001 | 1 | A | 0 | 50 | US | LOT5 |
| Actual | **0001** | **2** | **A** | **0** | **40** | **US** | **LOT7** |

### Receive 3

When the application receives its final quantity for the planned inbound order line, the inventory happens to match the origin code and lot number values from sequence number 1. In this case, no new sequence record is created, but the additional quantity of 10 is added to sequence number 1, changing its quantity to 60, and fulfilling the total expected quantity of 100.

       
|   | Line number | Sequence number | Item | Expected quantity | Received quantity | Origin code | Lot number |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Expected | 0001 | 0 | A | 100 | 0 | US |   |
| Actual | **0001** | **1** | **A** | **0** | **60** | **US** | **LOT5** |
| Actual | 0001 | 2 | A | 0 | 40 | US | LOT7 |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
