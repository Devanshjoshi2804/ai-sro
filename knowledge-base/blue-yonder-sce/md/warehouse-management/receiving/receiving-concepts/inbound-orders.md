---
title: "Inbound orders"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/inbound_orders.htm"
source: "/content/inbound_orders.htm"
toc_path:
  - "Warehouse Management"
  - "Receiving"
  - "Receiving concepts"
  - "Inbound orders"
sections:
  - "Inbound order types"
  - "Inbound order status"
  - "Inbound order use scenarios"
  - "Push logistics"
  - "Vendor managed inventory"
  - "Consistent consumption into outbound customer orders"
  - "Bulk buying savings agreements from suppliers"
  - "Back orders"
  - "Materials with unlimited shelf life"
images: []
source_sha1: b80b2d490781732e1bac347427286066644fc76e
---
# Inbound orders

An inbound order is an unplanned order (sometimes called a blanket order) that contains item and quantity information for inbound inventory, but no information about how or when the inventory will be received into the facility. You can use unplanned inbound orders to support the following common practices:

-   Ordering more inventory than is deliverable on one inbound shipment
-   Ordering more than is available or required at any given time from a supplier
-   Ordering more inventory than can fit on one piece of transport equipment

An inbound order has the following characteristics:

-   Eliminates the need to define individual order lines when you add a planned inbound order to an inbound shipment; it can be used to identify inventory that you receive into the warehouse frequently.
-   Is a template that can be used over and over again; the same inbound order can be used as the basis for multiple planned inbound orders.
-   You can associate predefined inbound order information with multiple inbound shipments. The shipments may arrive on the same or different dates.

Inbound orders are typically downloaded from a host system; however, you can create an inbound order if you want a single source from which to track multiple related planned inbound orders over time. You can modify an inbound order, for example, to change its status to either suspend receiving or to close the order to prevent future receipts against it.

## Inbound order types

An inbound order type is a user-configurable category that is applied to an inbound or planned inbound order to represent its purpose and define its processing characteristics.

When creating an order, you can apply one of the following standard order types:

-   **Customer Return**: Indicates that the inbound order is for a blanket return, such as in a recall of shipped inventory.
-   **Production**: Indicates that the inbound order is an internal work order.
-   **Purchase Order**: Indicates that the inbound order is for an external receipt of ordered inventory.

You can configure an inbound warehouse workflow (application-directed operation) to be performed on inventory associated with an inbound order when it is received, based on the order type.

For example, if you want operators to do a quality check on all inventory associated with a customer return, then you can create an inbound warehouse workflow based on the Customer Return order type. Then, when inventory associated with a customer return is identified, operators are instructed to perform a quality check as defined in the workflow. See [Inbound Workflows](../../configuration/work/warehouse-workflows/inbound-workflows.md).

## Inbound order status

The status of an inbound order can be used to prevent receiving from taking place against the inbound order lines. The inbound order status is a user setting; it is not changed or updated by any application action or process.

When you create an inbound order, the following statuses are available for selection:

-   **Open**: This status indicates that receiving against the inbound order is allowed.
-   **Suspended**: This status is typically used to indicate that the order is being researched due to the following conditions:
    
    **Note**: Depending on the receiving identification configuration defined for the warehouse, users may or may not be allowed to receive against a suspended inbound order.
    
    -   Quality problems identified with previously received inventory
    -   Temporary problems with the carrier
    -   Temporary problems with the inbound order
    -   Temporary problems in the receiving process for an item

When research is complete, a user can reset the status to Open.

-   **Closed**: This status is typically used to indicate that the inbound order is no longer active, and that it can be archived for historical purposes.
    
    **Note**: Depending on the receiving identification configuration defined for the warehouse, users may or may not be allowed to receive against a closed inbound order.
    

## Inbound order use scenarios

### Push logistics

Push logistics operations are inventory-based logistics applications characterized by regularly scheduled flows of product and high inventory levels. An internal manufacturing operation can use push logistics to distribute regularly scheduled inventory to a distribution center (DC).

When the DC does not use inbound orders, such as purchase orders, it must create or obtain individual planned inbound orders for each regular shipment of inventory that it receives from the manufacturing operation.

When the DC uses inbound orders, it can generate a single inbound order to account for the inventory that it expects to receive from the manufacturing operation within a specified time period. The DC can then use this inbound order to automatically generate the individual planned inbound orders required to receive the inventory. In addition, it can track its total receiving progress at any time throughout the receiving process.

### Vendor managed inventory

A vendor managed inventory operation is one in which the manufacturer is responsible for maintaining the distributor’s inventory levels.

When a vendor managed inventory operation does not use inbound orders, such as purchase orders, the distributor must create or obtain planned inbound orders for each shipment from the manufacturer as it arrives. Without visibility into how much of the approved inventory level has been received with each shipment, the distributor can be at risk for over receiving.

When a vendor managed inventory operations uses inbound orders, the manufacturer can generate an inbound order for all of the inventory that the distributor should expect to receive within a specific time period. The distributor can use this inbound order to automatically generate the individual planned inbound orders required to receive the inventory, and to ensure that they do not over receive against approved inventory levels.

### Consistent consumption into outbound customer orders

Some facilities ship the same amount of certain items each month to satisfy customer orders, and can therefore accurately forecast the amount of inventory that they will need to receive in order to complete these outbound shipments.

When such facilities do not use inbound orders, such as purchase orders, then they must create or obtain planned inbound orders for each shipment that arrives at their facility. There is limited immediate visibility into how much of the monthly inventory has been received with each inbound shipment.

When such facilities use inbound orders, they can create a single inbound order that requests the expected quantity of certain items each month, and then use that inbound order to automatically create planned inbound orders required to receive those items. The facilities can also track their total receiving progress during the month by examining the identified and expected quantities of the items that they receive.

### Bulk buying savings agreements from suppliers

A bulk buying savings agreement is one in which a manufacturer can purchase products from suppliers in large quantities at a lower price per item, or unit price, than is available for smaller quantities. For example, a manufacturer may order 10,000 plastic bags for use in packaging their hardware. Because the manufacturer does not want to store the entire quantity at one time, they create a purchase order for the full amount, and then arrange to receive shipments on a monthly basis.

When a manufacturer does not use inbound order, such as purchase orders, for bulk purchases, then they must create or obtain individual planned inbound orders for each shipment of the bulk items that arrive. If they have ordered more product than fits on a single piece of transport equipment, then they must create individual planned inbound orders for each inbound shipment associated with an inbound equipment.

When a manufacturer uses inbound orders for bulk purchases, they can use the inbound order to automatically generate the individual planned inbound orders for the bulk items as they arrive, regardless of how many pieces of transport equipment they are receiving or how many shipments are received in a given time period. In addition, the manufacturer can track how much of the purchased item has been received at any point in time, helping them to understand how close their bulk order is to fulfillment.

### Back orders

Backordered items are items that are committed on sales orders, but are not in stock. A facility ordering inventory to fulfill back ordered requests may order more inventory than fits on a single shipment or than can be shipped in a single time period.

When the facility managing the back order does not use inbound orders, such as purchase orders, they must create or obtain planned inbound orders for each inbound shipment of the backordered inventory, and then separately tally the total quantity received against the backordered amount.

When the facility managing the back order uses inbound orders, they can use the inbound order to generate multiple planned inbound orders for the inbound shipments. In addition, they can easily determine how much of the backordered inventory has been received versus how much is expected at any point in time.

### Materials with unlimited shelf life

Materials with an unlimited shelf life are those items that are incorporated into a manufacturing process and can be stored indefinitely, such as the nuts or bolts required to assemble a specific item. Some facilities prefer to order large quantities of product with an unlimited shelf life, and then store the product that they do not immediately need.

When such facilities do not use inbound orders, such as purchase orders, then they must create or obtain planned inbound orders for each inbound shipment of these materials that arrives, regardless of how many pieces of transport equipment it requires to transport them to the facility.

When such facilities use inbound orders, then they can use the inbound order to automatically create as many individual planned inbound orders as is required to receive the requested materials. In addition, these facilities can track how much of the original order has been received with each shipment.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
