---
title: "Procedures for orders"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/procedures_for_orders.htm"
source: "/content/procedures_for_orders.htm"
toc_path:
  - "Warehouse Management"
  - "Outbound Planner"
  - "Outbound"
  - "Procedures for orders"
sections:
  - "Add or modify an order"
  - "Add or modify an order line"
  - "Add or modify a distribution for an outbound order line"
  - "Cancel an order or order line"
  - "Copy an existing order"
  - "Delete an order or order line"
  - "Change the carrier of an order"
  - "Change the warehouse for an order"
  - "Manage notes for an order"
  - "View outbound orders"
  - "View detailed order information"
  - "Order field listings"
  - "Required Order fields"
  - "General Order fields"
  - "Processing Order fields"
  - "Customs Order fields"
  - "Order Lines field listings"
  - "Required Order Lines fields"
  - "Carrier Order Lines fields"
  - "General Order Lines fields"
  - "Allocation Order Lines fields"
  - "Processing Order Lines fields"
  - "Packaging Order Lines fields"
  - "Export Order Lines fields"
  - "Distribution Order Lines fields"
  - "Customs Order Lines fields"
  - "Order detail fields"
  - "Order Lines detail fields"
  - "Order Activity fields"
images: []
source_sha1: 6d4d074fffa367d928c72b9689fa682c1f66db90
---
# Procedures for orders

You can perform the following procedures on orders.

## Add or modify an order

1.  Perform one of the following tasks:
    -   To add an order, select **Outbound Planner > Outbound > Orders**, and then from the **Actions** drop-down list, select **Add Order**.
        
        **Note**: You can only add outbound orders using the Outbound Planner module.
        
    -   To modify an order:
        1.  Perform one of the following tasks:
            -   [View outbound orders](#View_outbound_orders).
            -   View a grid that displays a link for the order.
        2.  In the grid, click the order. The order details are displayed.
        3.  From the **Actions** drop-down list, select **Modify Order**.
2.  Enter information in the [Order field listings](#Order_field_listings).
3.  To add or modify order notes, see [Manage notes for an order](#Manage_notes_for_an_order).

1.  Click **Save**. A confirmation message is displayed asking if you want to add order lines.
2.  Perform one of the following tasks:
    -   To add an order line:
        1.  Click **Yes**.
        2.  Click **Add**.
        3.  Enter information in the [Order Lines field listings](#Order_line_field_listings).
        4.  Click **Save**.
    -   To save the order without adding lines, click **No**.

## Add or modify an order line

1.  Perform one of the following tasks:
    -   [View outbound orders](#View_outbound_orders).
    -   View a grid that displays a link for the order.
2.  In the grid, click the order. The order details are displayed.
3.  Select **Order Lines**.
4.  In the grid, perform one of the following tasks:
    -   To add an order line, from the **Actions** drop-down list, select **Add Order Line**.
    -   To modify an order line, select the check box next to the order line, and then from the **Actions** drop-down list, select **Modify Order Line**.
5.  Enter information in the [Order Lines field listings](#Order_line_field_listings).
6.  To define the criteria that is used to allocate inventory for the order line:
    
    **Note**: For more information, see [Allocation Rules](../../configuration/outbound/allocation/allocation-rules.md).
    
    1.  Under **Criteria Definition**, click **Expression**.
    2.  Select a column (attribute) to use, such as **Lot Number**.
    3.  Select the qualifier to use, such as "=".
    4.  Enter the attribute to use, such as **LOT1234** (based on the qualifier, the lot number that must be allocated for the order line).
    5.  To add additional rows of criteria:
        1.  Select the mathematical argument used to evaluate multiple rows of criteria.
            -   **Or**: Must match either group of the defined criteria.
            -   **And**: Must match both groups of the defined criteria.
            -   **(**: Opening argument used to group criteria together.
            -   **)**: Closing argument used to group criteria together.
                
                **Note**: Other operators that represent a combination of these arguments, such as ")And(" are also available. The operator determines how the application evaluates the criteria. For example, if you have two criteria lines connected with the operator "And", that means the inventory must match both attributes to meet the criteria. If the two lines are connected with the operator "Or", the inventory only has to match one of the field values to meet the criteria.
                
        2.  Click **Expression**, and define its criteria.
7.  Click **Save**.

## Add or modify a distribution for an outbound order line

When you add or modify a distribution for an outbound order line, you are required to specify the expected inbound order line that will be used to fulfill the required outbound quantity on the line.

You can also [add or modify a distribution from an inbound order line](../../receiving/inbound-shipments/procedures-for-inbound-shipments.md).

1.  Perform one of the following tasks:
    -   [View outbound orders](#View_outbound_orders).
    -   View a grid that displays a link for the order.
2.  In the grid, click the order. The order details are displayed.
3.  Select **Order Lines**.
4.  In the grid, select the check box next to the order line for which to create a distribution.
5.  From the **Actions** drop-down list, select **Modify Order Line**.

**Note**: You can also create a distribution when you add a new order line. See [Add or modify an order line](#Add_or_modify_an_order_line).

7.  Under **DISTRIBUTION**, enter information in the [Distribution Order Lines fields](#Distribution_order_line_fields).
8.  Click **Save**.

## Cancel an order or order line

You cannot cancel an order for which picking has begun; however, individual order lines within an order can still be cancelled as long as picking for the line has not started. See [Order and order line cancellation](../outbound-planning-concepts.md).

1.  [View outbound orders](#View_outbound_orders).
2.  To cancel an order:
    1.  In the grid, select the check box next to each order to cancel.
        
        **Note**: If you are viewing the orders in a wave, you must first click an order to display its details before it can be cancelled.
        
    2.  From the **Actions** drop-down list, select **Cancel Order**.
    3.  Click **OK**.
3.  To cancel an order line:
    1.  In the grid, click an order. The order details are displayed.
    2.  Select **Order Lines**.
    3.  In the grid, select the check box next to each order line to cancel.
    4.  From the **Actions** drop-down list, select **Cancel Order Line**.
    5.  Click **OK**.

## Copy an existing order

You can only copy an existing order from the Orders grid view; some grid views require the entry of search criteria prior to displaying data on the page.

1.  Select **Outbound Planner > Outbound > Orders**.
2.  In the grid, select the row for the order to copy.
3.  From the **Actions** drop-down list, select **Copy Order**.
4.  Enter information in the following fields:
    

 
| Field | Description |
| --- | --- |
| Order Number | Unique number that identifies an order. An order is a request for a supply of material or product. |
| Client | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client ID distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. Only displayed in a 3PL environment. |

8.  Click **OK**.

## Delete an order or order line

**Note**: Deleting an order or order line permanently removes the record from the application. You cannot recover a deleted order or order line, and there is no history of it existing in the application.

1.  [View outbound orders](#View_outbound_orders).
2.  To delete an order:
    1.  In the grid, select the check box next to the each order to delete.
        
        **Note**: If you are viewing the orders in a wave, you must first click an order to display its details before it can be deleted.
        
    2.  From the **Actions** drop-down list, select **Delete Order**.
    3.  Click **OK**.
3.  To delete an order line:
    1.  In the grid, click an order. The order details are displayed.
    2.  Select **Order Lines**.
    3.  In the grid, select the check box next to each order line to delete.
    4.  From the **Actions** drop-down list, select **Delete Order Line**.
    5.  Click **OK**.

## Change the carrier of an order

You can change the carrier of an order only if the application is configured to allow a carrier change in the outbound order settings, and if the **Change Carrier** field on the order is set to Yes.

1.  [View outbound orders](#View_outbound_orders).
    
    **Note**: To change the carrier of multiple orders at the same time, use the Order tab on the Outbound page.
    
2.  In the grid, select the check box next to each order for which to change the carrier; or click an order to display the order details.
3.  From the **Actions** drop-down list, select **Change Carrier**. The Change Carrier window is displayed.
4.  Enter information in the following fields:
    
     
    | Field | Description |
    | --- | --- |
    | Carrier | Identifier for a carrier that delivers inbound inventory to the warehouse or outbound shipments to a customer. This is the identifier that will be displayed to users on the application windows and reports. In the application, a carrier can be associated with a customer, order, inbound shipment, outbound shipment, load, and service levels (such as Ground, Next Day, and Saturday Delivery). |
    | Service Level | Identifier for the service and transit time provided by the carrier that transports an order or shipment to the customer. For example, for a parcel carrier it may be used to indicate services such as express, second-day air, or standard delivery. |
    
5.  Click **OK**.

## Change the warehouse for an order

You can only change the warehouse for an order if the order is not planned into a shipment. Changing the warehouse for an order means that the order is fulfilled by the new warehouse. See [Multi-warehouse](../../configuration/warehouse/warehouses/multi-warehouse.md).

1.  Select **Outbound Planner > Outbound > Orders**.
2.  In the grid, select the check box for the order.
3.  From the **Actions** drop-down list, select **Change Warehouse**. The Change Warehouse window is displayed.
4.  From the **New Warehouse** drop-down list, select the warehouse to which you want to send the order.
5.  Click **OK**.

## Manage notes for an order

1.  Perform one of the following tasks:
    -   [View outbound orders](#View_outbound_orders).
    -   View a grid that displays a link for the order.
2.  In the grid, click the order. The order details are displayed.
3.  From the **Actions** drop down list, select **Modify Order**.

1.  To add or modify order notes:
    1.  Under **NOTES**, perform one of the following tasks:
        -   To add an order note, click **Add**.
        -   To modify an order note, in the grid, click the note line number.
    2.  Enter information in the following fields:
        
        | Field | Description |
        | --- | --- |
        | Note Type | A note type is a template that is used to define a set of attributes that are applied to order notes created using the note type. Notes provide additional information, instructions, or special requirements for the entity, such as an order, that the note is describing. You can configure the note types that are available for selection. See [Outbound Note Types](../../configuration/outbound/order-processing/outbound-note-types.md). |
        | Note Line Number | Identification number assigned to the note. |
        | Text | Supporting text for the note used to better inform the user or operator about the order or order line. |
        
    3.  Click **OK**.
2.  To delete an order note, under **NOTES**, select the check box next to the note line number, click **Delete**, and then click **OK**.

## View outbound orders

You can access the display of outbound orders from the Outbound Planner, Shipping, and Picking modules. Some grid views require the entry of search criteria prior to displaying data on the page.

Perform one of the following tasks:

-   Select **Outbound Planner > Outbound > Orders**.
-   Select **Outbound Planner > Outbound > Shipments**, and then in the grid, click a shipment, and then select **Orders**.
-   Select **Shipping > Loads**, and then in the grid, click a load, and then select **Orders**.
-   Select **Picking > Waves and Picks > Waves**, and then in the grid, click a wave, and then select **Orders**.

## View detailed order information

1.  Perform one of the following tasks:
    -   [View outbound orders](#View_outbound_orders).
    -   View a grid that displays a link for the order.
2.  In the grid, click the order. The order details are displayed.
3.  View information in the [Order detail fields](#Order_detail_fields).
4.  Select **Order Lines** and view information in the [Order Lines detail fields](#Order_lines_detail_fields).
5.  Select **Order Activity** and view information in the [Order Activity fields](#Order_Activity_fields).
6.  Select **Picks** and view information in the [Picks detail fields](../../shared-functions/waves-and-picks/procedures-for-picks-and-work-assignments.md).
7.  Select **LPN** and view information in the [LPN detail field listings](../../shared-functions/inventory/procedures-for-lpns.md).
8.  Select **Shorts** and view information in the [Shorts detail fields](procedures-for-shorts-and-replenishments.md).
9.  Select **Pending Replens** and view information in the [Pending Replenishment detail fields](procedures-for-shorts-and-replenishments.md).

**Note**: Demand replenishments created as a result of pre-inventory allocation (PIA) processing are not displayed on the **Pending Replens** tab, because they are created as pick work and not replenishment work. You can view demand replenishments on the Picking and Outbound Planner Dashboards.

11.  Select **Customs** and view information in the [Customs Order fields](#Customs_Order_fields).
12.  Select **Cross Dock** and view information in the [Cross Dock detail fields](procedures-for-shorts-and-replenishments.md).

## Order field listings

### Required Order fields

 
| Field | Description |
| --- | --- |
| Order Number | Unique number that identifies an order. An order is a request for a supply of material or product. |
| Order Type | Name of an order type. An order type is a category that is used to group orders based on the warehouse processing necessary to fulfill the order. For example, customer orders and distribution orders require different processing by the application, and so an order type can be assigned to categorize each order separately. The application uses order types, for example, to identify orders that are eligible for bulk picking, or to direct orders to specific destination locations. |
| Client | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. |
| Ship To Customer/Address | Name and address for the customer to whom the order must be shipped. |
| Route To Customer/Address | Name and address of the distributor or organization to which the outbound order is sent initially. The route-to customer is responsible for ensuring that the shipment reaches the ship-to customer. The route-to customer and ship-to customer are the same if the order does not require an initial stop. |
| Bill To Customer/Address | Name and address of the customer to whom billing information is sent. |

### General Order fields

 
| Field | Description |
| --- | --- |
| Customer PO Number | Number that identifies the customer's purchase order. |
| Customer PO Type | Type of purchase order sent from the customer to acquire inventory. |
| Customer PO Date | Date on which the customer's purchase order was created. |
| Customer Service Representative | Name of the service representative at a company. |
| Customer Service Email | Address at which the individual or organization associated with customer service receives electronic mail. For example: [\[email protected\]](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/cdn-cgi/l/email-protection). |
| Customer Service Phone | Phone number, including area or country code, for the individual or organization to which customer service calls should be directed. |
| Destination Number | Aisle or shelf number, based on customer's planogram, to which the order should be directed. |
| RMA Number | Returned materials authorization (RMA) is the number assigned to the authorization for returning an outbound order. |
| Customer Payment Terms | Method by which payments are made. The available terms differ depending on whether the order has a specified **COD Indicator Type** and if **Bill Consignee** is set to Yes. |
| Delivery Contact | Name or identifier of the person to be contacted upon delivery of an order. |
| Host Appointment Number | Appointment number associated with the outbound order. Some consignees provide this number when appointments are made. |
| Business Group | Identifier of the business group associated with the outbound order. Business groups are used to classify orders into groups having a common feature. |
| Department Number | Identifier for a department within the customer's facility. A department can be specified for a customer type, customer, order, order line, distribution, and item. It can be used to group information for the purpose of sorting and searching data, consolidating distribution inventory in customer-specific storage locations, and to help customers direct inventory to the proper department when it arrives at their facility. |

### Processing Order fields

 
| Field | Description |
| --- | --- |
| Create Shipment By | Method by which the customer wants their orders to be grouped into shipments. The method determines how the application builds orders into shipments.<br>-   • **Bill-To Customer**: All of the order lines in a shipment must be for the same bill-to customer. The bill-to customer is the address name of the location to which billing information is sent.
<br>-   • **Outbound Order Number**: All of the order lines in a shipment must be for the same order. A shipment consists of a single order.
<br>-   • **Route-To Customer**: All of the order lines in a shipment must be for the same route-to customer. The route-to customer is the address name of the location to which the shipment is sent (such as a distribution hub), before being directed to the ship-to customer.
<br>-   • **Ship-To Customer**: All of the order lines in a shipment must be for the same ship-to customer. The ship-to customer is the address name of the final destination of the shipment.
<br > **Note**: If additional values were configured for your application, those values will also be available for selection. |
| COD Payment Terms | Method (such as currency, check, or money order) by which collect on delivery (COD) payments must be made. Valid values are user-defined. |
| COD Indicator Type | Value that indicates the type of collect on delivery (COD), if any, that will be required for the order.<br>-   • **Electronic**: COD is collected using an electronic form of payment.
<br>-   • **None**: The carrier does not require that you specify the type of COD.
<br>-   • **Regular**: COD is collected as a check or cash. |
| Service Type | For international shipments, defines the type of service that is used by the carrier.<br>-   • **Airport to Airport**: The facility drops off the package at the airport. Then, the carrier transports the package to the airport in the destination country. Finally, the customer (or broker) picks up the package at the destination airport.
<br>-   • **Airport to Door**: The facility drops off the package at the airport where the carrier takes over and transports the package to the actual ship-to address in the destination country.
<br>-   • **Door to Airport**: The carrier picks up the package from the facility and then transports the package to the airport in the destination country. Then, the customer (or broker) picks up the package at the destination airport.
<br>-   • **Door to Door**: The carrier picks up the package from the facility and then transports the package to the actual ship-to address in the destination country. |
| Order Freight Rate | Freight amount for this order. |
| Freight Allowance | Amount that the buyer determines is allocated by the vendor for moving freight. |
| Delivery Number | Alphanumeric identifier that is used to process and load orders together that are destined to the same ship-to customer on a route. Delivery numbers are assigned to orders on a stop to group multiple orders together that need to be delivered to the same destination. For example, delivery numbers can be used when a customer stop on a load contains orders for multiple ship-to locations. Typically, the inventory is first routed through an intermediate location (route-to customer) in the same geographic region, and then routed to the individual ship-to customers. See [Delivery sequence loading](../outbound-planning-concepts.md). |
| Delivery Sequence | Number that indicates the sequence in which the order must be processed in relation to other orders with the same delivery number. A delivery sequence is assigned to the orders within one or more delivery number groups on a stop so they are loaded in a specific sequence. For example, if a stop includes 4 orders, you can assign a sequential number to each one, and the operator is directed to load the orders based on the sequence.<br > The order in which the application enforces loading (ascending or descending) is defined by the **Delivery Sequence Loading Order** field. See [Delivery sequence loading](../outbound-planning-concepts.md). |
| Planned Slot Sequence | Slot sequence value assigned to the order and downloaded from the host. It is used to plan corresponding work assignment picks into a slot on a master handling unit. For more information and setup tasks, see the [Order sequence processing](../../configuration/outbound/picking/work-assignments/order-sequence-processing.md) configurations. |
| Rush Flag | If Yes, then the outbound order is a "rush" or urgent order. This attribute does not affect the priority of work in the work queue, but is used for reporting and wave planning purposes.<br > If No, then the order is not an urgent order. |
| Bill Consignee | If Yes, then the delivery charges for the shipment are billed to the consignee.<br > If No, then the consignee is not billed for delivery charges. |
| Signature Required | If Yes, then you require the shipper to obtain a signature at delivery.<br > If No, then you do not want a recipient to sign for the package, and you are releasing the shipper from obtaining a signature (shipper release). |
| Bill Freight | If Yes, then the freight costs for a collect on delivery (COD) shipment are paid by the recipient. The freight charges are added to the COD amount.<br > If No, then the freight charges are not paid by the recipient; the shipper pays. |
| Release Remaining Lines | Used for cross docking purposes.<br > If Yes, then the pick work for the order or work order lines that are not marked for cross docking are released as usual.<br > If No, then the pick work created for order or work order lines that are not marked for cross docking is held until the inventory that is marked for cross docking is received and allocated. |
| Change Carrier | If Yes, then the carrier can be assigned when the order is built into a shipment, when the shipment is allocated, or when the shipment is prepared for shipping.<br > **Note**: Before a carrier change can happen, the **Carriers** field in the outbound order settings must be set to Yes. Additionally, the **Carriers** field in the outbound staging configuration must be set to Yes to change a carrier for a staged shipment.<br > If No, then you must define the carrier on the order line and the carrier cannot be changed. |

### Customs Order fields

 
| Field | Description |
| --- | --- |
| Customs Status Notes | Description of the customs status from a duty management application indicating the reason that outbound order processing failed and what needs to be changed in the duty management application for the order to be processed successfully. |
| Customs Duty Customer | Customer that is responsible for paying the customs duties. Duties are charged to the tax approval number (**Customs Tax Type**) associated with the customer's address record. If you do not select either a customs or excise duty customer, then the duties are charged to the tax approval number associated with the warehouse site address record. |
| Customs Broker Customer | Broker customer to which this outbound order is shipped. Only available when shipping to an international location. |
| Excise Duty Customer | Customer that is responsible for paying the excise duties. Duties are charged to the tax approval number (**Customs Tax Type**) associated with the customer's address record. If you do not select either a customs or excise duty customer, then the duties are charged to the tax approval number associated with the warehouse site address record. |
| Customs Order Type | Type of customs order that is used by a duty management application to calculate duties owed for an outbound order. A customs order type is used to categorize orders that have the same source site type (customs, customs and excise, or non-bonded), destination site type, and destination country type (United Kingdom, member of European Union, or neither). The application defaults the customs order type based on the address and country attributes (customs site type and customs country type) of the sites to and from which the order is shipping. |
| Customs Order Status | Status indicating the result of a duty management application's processing of the order.<br>-   • **Success**: The outbound order was processed successfully and the application order processing can continue.
<br>-   • **Failure**: Order processing failed in the duty management application, and errors must be corrected before the application order processing can continue.
<br>-   • **No selection (blank)**: The duty management application processing of the order has not taken place. |
| Customs Clearance | For international shipments, if Yes, indicates that parcels will be sent directly to customs for clearance.<br > If No, then customs clearance is not required. |
| Customs Additional Information | Note text from a duty management application that describes what needs to be changed in the application for the order to be processed successfully. |
| Duty Payment Account | Customs account to which the duty payment should be charged. |
| Duty Payment Type | Value that identifies the payer of the duty charges (typically either the shipper, recipient, or a third-party). |

## Order Lines field listings

### Required Order Lines fields

 
| Field | Description |
| --- | --- |
| Order Line | Unique number that identifies the order line. The number corresponds to the line's position on the order. The first order line is automatically assigned a line number of 0001. Additional order lines are then automatically numbered sequentially, beginning with 0002. |
| Order Sub-Line | Identifying number assigned to an outbound order sub-line. By default, the first line of each order line has a sub-line number of 0000, and it identifies the finished product. The remaining sub-lines are numbered sequentially, beginning with 0001, and they identify the component items required to complete the order line. |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Ordered Quantity | Quantity of the item that the customer ordered. |
| Item Client | Name of the client who stores this item in the facility. This field is only displayed in a 3PL environment. |
| Allocation Profile | Default level of quality at which the customer is willing to accept inventory. An allocation profile is a prioritized list of inventory statuses that identifies which statuses can be shipped. It can be applied to both date-controlled and non-date-controlled items. |

### Carrier Order Lines fields

 
| Field | Description |
| --- | --- |
| Carrier | Identifier for a carrier that delivers inbound inventory to the warehouse or outbound shipments to a customer. This is the identifier that will be displayed to users on the application windows and reports. In the application, a carrier can be associated with a customer, order, inbound shipment, outbound shipment, load, and service levels (such as Ground, Next Day, and Saturday Delivery). |
| Service Level | Identifier for the service and transit time provided by the carrier that transports an order or shipment to the customer. For example, for a parcel carrier it may be used to indicate services such as express, second-day air, or standard delivery. |
| Carrier Group | Code that identifies a group of carriers, one of whom is expected to transport an outbound order or a shipment to the customer. If the **Change Carrier** field is set to No for an order, then this is the required carrier group. |
| Freight Code | Code that is used in shipping paperwork to determine who takes financial responsibility for the shipment.<br>-   • **FOB Destination**: Seller takes responsibility for the goods while in transit.
<br>-   • **FOB Source**: Buyer takes responsibility for the goods while in transit. |
| Saturday Delivery | If Yes, then the carrier delivers shipments on Saturday, if required.<br > If No, then the carrier does not deliver on Saturday. |
| Payment Terms | Method (such as pre-paid or third party) by which delivery charges are to be paid. Valid values are either the carrier-specific payment terms retrieved from the integrated Parcel instance, or the generic payment terms defined in the application. **Payment Terms** is optional, and the value is typically sent from the host. |

### General Order Lines fields

 
| Field | Description |
| --- | --- |
| Project Number | Project number assigned to the order. The project number is sent to the host application and used for reporting purposes. |
| Customer Item Number | Identifier for a customer-specific item configuration. The customer item can be configured with specific packaging and date-tracking attributes that the customer requires for the item. When the customer orders the item, the application allocates matching inventory based on the customer's requirements. The customer item identifier may be different from the identifier defined for the item in the application, and can be included in reports and shipping documents. |
| Account Number | Account number, such as a general ledger account number, assigned to the outbound order. Account numbers are used in host transactions and for reporting purposes. |
| Sales Order Line | Customer's order line number. This value may differ from the outbound order line number if your host assigns its own order numbers, or if it consolidates customer orders into warehouse orders. |
| Sales Order Number | Customer's order number. This value may differ from the outbound order number if your host assigns its own order numbers, or if it consolidates customer orders into warehouse orders. |
| Host Ordered Quantity | Quantity required by the host application for this order line. |
| Department Number | Identifier for a department within the customer's facility. A department can be specified for a customer type, customer, order, order line, distribution, and item. It can be used to group information for the purpose of sorting and searching data, consolidating distribution inventory in customer-specific storage locations, and to help customers direct inventory to the proper department when it arrives at their facility. |
| Early Ship Date | First day of the outbound shipment range. The shipment range identifies a series of dates on which an outbound order line must be shipped. The application uses both delivery and ship dates to consolidate order lines into shipments, depending on the values defined for order consolidation. |
| Late Ship Date | Last day of the outbound shipment range. To define a single shipment date, enter the first day of the shipment range. The application uses both delivery and ship dates to consolidate order lines into shipments, depending on the values defined for order consolidation. |
| Early Delivery<br > Date | First day of the delivery range. The delivery range identifies a series of expected delivery dates for the outbound order line. The application uses both delivery and ship dates to consolidate order lines into outbound shipments, depending on the values defined for order consolidation. |
| Late Delivery Date | Last day of the delivery range. To define a single delivery date, enter the first day of the delivery range. The application uses both delivery and ship dates to consolidate outbound order lines into outbound shipments, depending on the values defined for order consolidation. |
| Manufacturer | Name of the organization that manufactures the inventory supplied to a customer. The manufacturer is required when the application is configured to produce UCC128 (Uniform Commercial Code) identifiers for shipment labeling. |

### Allocation Order Lines fields

 
| Field | Description |
| --- | --- |
| Rule Name | Name of the allocation rule. An allocation rule is a processing command that specifies the inventory attribute values that are acceptable to fulfill an order line, work order detail, work order line, or bill of materials (BOM) detail. |
| Description | Description that further defines the allocation rule. |

### Processing Order Lines fields

 
| Field | Description |
| --- | --- |
| Reservation Priority | Number used to determine which outbound orders receive inventory when there is not enough inventory in the warehouse to satisfy all orders for an item. This option applies only when the order reservation process is used. Reservation priority ranges from 1 to 9 with 1 being the highest priority. In situations where there is not enough inventory to satisfy all order lines and the order reservation process is running, order lines with the highest priority receives the inventory. |
| Over Allocation Code | Code that identifies how over allocation is performed.<br>-   • **Percentage**: The application is permitted to allocate a certain percentage more, as defined in the **Over Allocation Amount** field, of the original quantity of component items required for the order line.
<br>-   • **Quantity**: The application is permitted to allocate a certain quantity more, as defined in the **Over Allocation Amount** field, of the original quantity of component items required for the order line.
<br > Over allocation is the process of allocating more than the indicated amount of inventory to satisfy an order or work order. Over allocation is beneficial in situations where it is easier to pick an entire case or pallet instead of breaking a case to complete a pick. |
| Over Allocation Amount | Total amount of inventory that can be allocated over the requested quantity when the allocation code is Quantity, or percentage of inventory that can be allocated when the allocation code is Percentage. If the over-allocation code is Percentage, then the over-allocation amount should be a value from 1 to 100 that indicates the percentage of the order quantity that can be over-allocated. If the over-allocation code is Quantity, then the over-allocation amount should be a value that represents the number that can be over-allocated. |
| Pick Group 1-4 | Code used to identify outbound orders to group together for automatic allocation. The application selects orders with the same pick group value to automatically allocate as a group. Pick Group 2, Pick Group 3, and Pick Group 4 are optional values that are used in customized processes. |
| Partial | If Yes, then the outbound order line can be shipped with less than the required amount of inventory.<br > If No, then the order line must be shipped complete. If there is not enough inventory, and you are using the reservation process, the application does not allow you to build the order line into a shipment. |
| Back Order | If Yes, then the outbound order line that was shipped incomplete is back ordered. The application maintains the incomplete order in the list of unallocated orders. The order line can then be built into a new shipment and reallocated when the inventory is available.<br > If No, then incomplete orders are removed from the application. |
| Non Allocatable Line | If Yes, then the inventory identified on the outbound order line is not considered part of the standard inventory in a facility. Typically, non-allocatable order lines identify inventory that is shipped with an order, but is not inventory that is received, allocated, or picked. Examples of non-allocatable items include warranty cards, installation instructions, or service plans.<br > **Note**: Non allocatable lines are not visible during packing, and the ability to pack non allocatable lines at a station is not supported.<br > If No, then the inventory on the order line is allocatable and is considered part of the standard inventory in a facility. |
| Minimum Shelf Life | Minimum number of hours away from expiration that a date-tracked item must be considered for allocation. For example, if this value is 10, then the application only allocates inventory that has at least 10 hours to reach its expiration date. Only available if the item specified on the order line is date-tracked. |
| Absolute Order Inventory Window | Amount of time in relation to the inventory’s received date or expiration date during which inventory is considered the same age for allocation when one of the FEFO/FIFO/LEFO/LIFO or absolute FEFO/FIFO/LEFO/LIFO inventory rotation methods is required. During allocation, the application uses the assigned date window based on a pre-defined order of precedence. See [Allocation Inventory Selection](../../configuration/outbound/allocation/allocation-inventory-selection.md). |
| Absolute Order Inventory Window Unit | Unit of time for the outbound date window. The valid values are **Days**, **Hours**, and **Minutes**. The outbound date window configuration must be enabled for this value to take effect. |
| Processing Priority | Number that identifies the priority at which outbound order lines are allocated. Order lines with the highest priority are allocated first in a shipment. Processing priority numbers range from 1 to 9 with 1 being the highest priority. If this field is left blank, the application will set the processing priority to 5 by default. |
| Married Code | Code that ties together this outbound order line with another order line. You can use this value to ensure that inventory for order lines are allocated together as a set or a complete group of inventory. If the **Partial** check box is selected for any of the order lines, then all order lines that share the same married code are allocated in the same quantity (if they were the same quantity) or in a proportional quantity (if their quantity was different). For example, if order line 001 had a quantity of 10, and order line 002 had a quantity of 5, and if only 8 can be allocated for 001, then only 4 are allocated for 002. If the **Partial** check box is deselected, and one of the order lines is short, then none of the order lines with same married code are built into a shipment. This option is only available when order reservation is used. |
| Inventory Rotation Method | Value that represents the order in which the allocation process selects available inventory for allocation. Select an inventory rotation method if you want the application to search for inventory based on date processing or location.<br>-   • **FEFO-ORDER-BY and FEFO-ORDER-BY-ABSOLUTE**: First-expiration, first-out. The first inventory to expire will be selected first.
<br>-   • **FIFO-ORDER-BY and FIFO-ORDER-BY-ABSOLUTE**: First-in, first-out. The oldest inventory will be selected first.
<br>-   • **LEFO-ORDER-BY and LEFO-ORDER-BY-ABSOLUTE**: Last-expiration, first-out. The last inventory to expire will be selected first.
<br>-   • **LIFO-ORDER-BY and LIFO-ORDER-BY-ABSOLUTE**: Last-in, first-out. The newest inventory will be selected first.
<br>-   • **LOCATION-ORDER-BY**: Locations are ordered within a pick zone (maintaining the allocation search path order) by the location attributes specified for the **Location Sort** field in inventory selection settings.
<br>-   •
    
    **No selection (blank)**: The application uses the inventory rotation method of the highest defined level of precedence. For information on precedence, see [Inventory rotation allocation processing](../../configuration/outbound/allocation/inventory-rotation-allocation.md).
    
    <br>
    
    **Note**: Inventory rotation methods defined at a lower precedence (except the default method) are automatically copied to the order line or work order line when the line is created. For example, if an order line is created for a date-tracked item with a rotation method defined, the rotation method is copied from the item to the order line, and then the application uses the order line rotation method during allocation.
    
    <br > If no inventory rotation method is defined at any level, then the application uses the allocation search path sequence and allocates the first available inventory it finds that matches all of the required attributes.
<br > When using inventory rotation methods that are not absolute, the application searches for inventory by allocation search path in sequence until it finds a pick zone that contains the inventory, and then allocates inventory that is closest to the preferred processing date. Therefore, the application stops searching at the first pick zone in which matching inventory is found.<br > When using absolute inventory rotation methods, the application searches either all of the allocation search paths for inventory that is closest to the preferred processing date or, if absolute groups are defined, each absolute group in sequence until it finds matching inventory and then allocates inventory that is closest to the preferred processing date from the pick zones within the absolute group. Therefore, the absolute method allows for more a comprehensive search to find the inventory. |
| Round Pick Quantity | If Yes, then the pick quantity can be rounded up to the next unit of measure. For example, if you select Yes, then picks for less than a pallet are rounded up to a full pallet. This functionality is beneficial in situations where it is easier to pick an entire case or pallet instead of breaking a case or pallet to complete a pick.<br > If No, then the pick quantity cannot be rounded up to the next unit of measure. |
| Cross Dock | If Yes, then the order line must be fulfilled with cross docked inventory. When the inventory specified on this outbound order line is identified, it is moved directly from receiving (or production) to a cross dock location or a specified staging location to satisfy the outbound order. If set to Yes, a cross dock record is created during allocation; lines marked for planned cross docking are not considered short.<br > When an outbound order line is created or downloaded from a host without a value for cross dock, this field on the outbound order line inherits the value from the Cross Dock Order Lines field for the customer, if it is set to Yes or No. If the customer value is set to Inherit from customer type, then the outbound order line inherits the value from the Cross Dock Order Lines field for the customer type.<br > If No, then the outbound order line can be fulfilled either by inventory from storage location or cross dock inventory (when opportunistic cross dock is enabled). If set to No and there is insufficient inventory during allocation, the order line is marked as short. |
| Process by Freshness | If Yes, then the item identified on the order line requires freshness date processing. Freshness date processing can be requested for date-tracked items to ensure that future shipments of a product to a specific customer are always delivered with product that is fresher than earlier shipments of that same product.<br > If No, then the item does not require freshness date processing. |
| Allocation Search Path Group | Name associated with allocation search paths for the purpose of grouping them for use during order allocation. If a search path group is specified on the order line, the application uses only the search paths that have a matching group name to find inventory for that order. This process reduces processing time by limiting the number of search paths the application uses during order allocation.<br > An allocation search path group can be assigned to a customer type, order line, allocation search path, and replenishment search path. |
| Wave Set | Optional shipment attribute that identifies a group of shipments that you want to include in a particular wave. A wave is a method of combining orders or shipments into logical sets (such as all shipments that are scheduled to ship tomorrow on a particular carrier) to achieve efficient picking for release and fulfillment. |

### Packaging Order Lines fields

 
| Field | Description |
| --- | --- |
| Footprint Details | Name that identifies a footprint, which describes the packaging dimensions and units of measure for the item with which it is associated. |
| Units Per Pallet | Default number of units (pieces) per pallet to be supplied for the order line. If left blank, there is no specific quantity needed on a pallet, and the application can allocate any quantity on a pallet while still allocating the total quantity needed for the order line. For example, if this field is blank, and if the warehouse stocks an item with 80 units on a pallet and 100 units on a pallet, then the application can allocate either pallet quantity according to other allocation rules. However, if 100 is the value in **Units Per Pallet**, the application allocates from the location with pallet of 100 so the customer gets the specified pallet quantity. |
| Units Per Case | Default number of units (pieces) per case to be supplied for the order line or work order line. If left blank, there is no specific quantity needed in a case, and the application can allocate any quantity in a case while still allocating the total quantity needed for the order line. For example, if this field is blank, and if the warehouse stocks an item with 80 units in a case and 100 units in a case, then the application can allocate either case quantity according to other allocation rules. However, if 100 is the value in **Units Per Case**, the application allocates from the location with cases of 100 so the customer gets the specified case quantity. |
| Units Per Pack | Default number of units (pieces) per inner pack to be supplied for the order line or work order line. If left blank, there is no specific quantity needed in a pack, and the application can allocate any quantity in a pack while still allocating the total quantity needed for the order line. For example, if this field is blank, and if the warehouse stocks an item with 8 units in a pack and 10 units in a pack, then the application can allocate either pack quantity according to other allocation rules. However, if 10 is the value in **Units Per Pack**, the application allocates from the location with packs of 10 so the customer gets the specified inner pack quantity. |
| Standard Case | If Yes, then case quantities for the order line are only allocated in the case UOM defined for the item's default footprint. For example, assume that ITEM-A comes in three footprints: FP1, FP2, and FP3. FP1 has 10 eaches per case, FP2 has 15 eaches per case, and FP3 has 20 eaches per case. If FP2 is the default footprint, then when an order line for ITEM-A has **Standard Case** set to Yes, the application attempts to fulfill case quantities with the FP2 case UOM (15 eaches per case).<br > **Note**: If a specific footprint or units per case is specified on the order line, that value takes precedence over the **Standard Case** setting.<br > If No, then case quantities for the order line can be fulfilled in the case UOM defined for any of the item's footprints, if inventory is not available in the case UOM for the default footprint. |
| Case Splitting | If Yes, then you allow the allocation of less than full case quantities to fulfill the order line when necessary.<br > If No, then you require the allocation of full case quantities to satisfy the order line. As a result, the application does not allocate less than full case quantities for the order line, nor does it enable detail level picking. |
| Handling Unit Type | Name of the handling unit type required for allocating the order line. A handling unit type represents a group of handling units that have the same characteristics, such as size and weight, as well as whether they are serialized, temporary, or considered a container.<br > When a handling unit type is specified on an order line, the application attempts to allocate the inventory on that handling unit type. If inventory on the requested handling unit type cannot be found, the application searches for the inventory on one of the other handling unit types assigned to the same handling unit group (if applicable) as the one that was requested. If inventory is available on one of those handling unit types, the allocation takes place. However, prior to shipping, the inventory must be transferred to the handling unit type that was requested on the order line.<br > If inventory does not exist on the requested handling unit type or on one of the alternate handling unit types in the handling unit group, then allocation fails, and the application creates a short allocation. |
| LPN Attribute | If Yes, the attribute is required by default for a pallet LPN of inventory that uses the footprint. An LPN attribute is a configurable attribute; therefore, the list of available LPN attributes may vary depending on what is configured and enabled for your warehouse. LPN attributes that are enabled are displayed during inventory identification, inventory attribute change operations, and picking (if specified on an order line).<br > If No, the attribute is not required by default for the pallet LPN. |

### Export Order Lines fields

 
| Field | Description |
| --- | --- |
| SED Required | If Yes, then the item must be printed on the Shipper's Export Declaration (SED). The SED is a document that is required by the U.S. Department of Commerce for exports of certain controlled items, shipments to certain countries, and shipments anywhere that exceed certain dollar amounts. This document is used to monitor shipments of controlled goods.<br > If No, then the item on the order line is not required to be printed on the SED. |
| SED Export Type | Value that indicates the item's export classification. Required if the **SED Required** field is set to Yes.<br>-   • **Domestic Exports**: The item was produced or re-manufactured in the United States.
<br>-   • **Foreign Exports**: The item was produced outside of the United States.
<br>-   • **Foreign Military Sales**: The item is being shipped to a foreign government for foreign military use. |
| Certificate of Origin Number | Number that uniquely identifies the certificate of origin. A certificate of origin authenticates the country of origin of the merchandise being shipped, and may be required because of established treaty arrangements, varying duty rates, and preferential duty treatment dependent on the shipment's origin. |
| Certificate of Origin Type | Classification of the item's certificate of origin.<br>-   • **US**: The certificate of origin is a United States certificate of origin.
<br>-   • **NAFTA**: The certificate of origin is a North American Free Trade Agreement (NAFTA) certificate of origin. The NAFTA certificate of origin is used by Canada, Mexico, and the United States, including Puerto Rico, to determine if goods imported into their countries receive reduced or eliminated duty as specified by the NAFTA. A certificate of origin authenticates the country of origin of the merchandise being shipped, and may be required because of established treaty arrangements, varying duty rates, and preferential duty treatment dependent on the shipment's origin. |
| NAFTA Blanket Begin Date | Date and time that the NAFTA blanket certificate of origin takes effect for the item. The blanket period is used when a certificate of origin covers multiple shipments of identical goods that are imported into a NAFTA country for a specified period of time, up to one year (the blanket period). The importation of a good for which preferential treatment is claimed based on this certificate of origin must occur during the blanket period. Required when NAFTA is selected from the **Certificate of Origin Type** drop-down list. |
| NAFTA Blanket End Date | Date and time that the NAFTA blanket certificate of origin expires for the item. The blanket period is used when a certificate of origin covers multiple shipments of identical goods that are imported into a NAFTA country for a specified period of time, up to one year (the blanket period). The importation of a good for which preferential treatment is claimed based on this certificate of origin must occur during the blanket period. Required when NAFTA is selected from the **Certificate of Origin Type** drop-down list. |
| NAFTA Producer | If Yes, then you produced the item defined on the order line.<br > If No, then you did not produce the item. |
| NAFTA Preference Criteria | Value, defined by the NAFTA, that indicates the preferential tariff treatment that applies to this item. Required when NAFTA is selected from the **Certificate of Origin Type** drop-down list. |
| Export License Number | Number that uniquely identifies your export license for this item. An export license is a document issued by the government of the shipper's export country, which permits the license holder to export specific goods to certain destinations. |
| Export License Expiration Date | Date and time that the export license expires. An export license is a document issued by the government of the shipper's export country, which permits the license holder to export specific goods to certain destinations. |
| Export License Exception | Value that indicates the reason an export license is not required to export this item. |
| Export Commodity Control Number | Standard alpha-numeric code, defined by the Commerce Control List, that classifies and identifies the item for export control purposes. |
| Marks and Numbers | Identifying symbols or numbers that the shipper has placed on this item. Marks and numbers can include package identifiers and X of Y package counts for a shipment, and are printed on the U.S. certificate of origin to identify packages in a shipment. |
| Import License Expiration Date | Date and time that the import license expires. An import license is a document provided by the destination country to the importer that permits the license holder to import specific items to a specific destination. An import license can make it easier for a shipment to pass through customs in the destination country. |
| Import License Number | Number that uniquely identifies an import license. An import license is a document provided by the destination country to the importer that permits the license holder to import specific items to a specific destination. An import license can make it easier for a shipment to pass through customs in the destination country. |

### Distribution Order Lines fields

 
| Field | Description |
| --- | --- |
| Distribution | Unique code that is used to identify a distribution. The distribution identifier can be application-generated or user-specified. A distribution is a pre-allocation of a warehouse planned inbound order to a store. |
| Source Distribution Identifier | Unique identifier of the distribution that was generated at the source warehouse. This is used for reference purposes if the distribution was created in another warehouse. |
| Source Warehouse ID | Source warehouse identifier for the facility that created the distribution for merge and transit. This is used for reference purposes if the distribution was created in another warehouse. |
| Source Warehouse Host External ID | Address name of the source warehouse that created the distribution for merge-in-transit. This is used for reference purposes if the distribution was created in another warehouse. |
| Promotion Code | User-defined code that identifies the specific promotion for which the distribution is being created or modified. The **Promotion Code** can be used to search for and select distributions assigned to the promotion. |
| Allow Allocate From Storage For Shorts | If Yes, then inventory can be be allocated from storage to fill any shortages the distribution may have. When inventory is allocated from storage, a new order line is created and associated with the original distribution identifier so that they are allocated together and planned on the same outbound shipment.<br > If No, then inventory from storage cannot be used to fulfill a distribution shortage. |
| Original Distribution Identifier | Unique code that is used to identify the distribution to which the order line was originally assigned. This identifier is used by the application to track new order lines that are created in the event there was a shortage which resulted in an allocation from storage. |
| Auto Generated | If Yes, then the order line associated with the distribution was automatically created by the application.<br > If No, then the order line was not automatically created. |
| Allow Over Distribution | If Yes, then the customer's distribution created from this order line accepts over distributed inventory. If the planned inbound order line tied to the distribution receives a quantity that is over the original distribution amount and is configured to over distribute excess inventory, this field must be set to Yes for the distribution to receive an overage quantity.<br > If No, then the customer's distribution created from this order line does not accept over distributed inventory. |
| Distribution Type | Name of the distribution type assigned to the distribution. The distribution type specifies the manner in which the application assigns distribution inventory to customers. See [Distribution Types](../../configuration/outbound/distribution/distribution-types.md). |
| Planned Inbound Order Number | Identifier for an inbound order that is associated with a specific supplier. Only inventory from this inbound order can be used for the distribution. |
| Supplier Number | Identifier for a supplier. A supplier can be an individual, organization, or another warehouse within your own organization from which you repeatedly receive inventory or handling units. Only inventory from this supplier can be used for the distribution. |
| Inbound Shipment ID | Unique identifier used for inventory tracking for an inbound shipment of inventory. An inbound shipment is a group of orders that are transported to the warehouse together or received together. When inventory arrives at the warehouse on a piece of transport equipment, an inbound shipment represents the contents of the transport equipment; however, one or more inbound shipments can be associated with a piece of transport equipment. |
| Planned Inbound Order Line | Number that identifies an order line. The number corresponds to the line’s position on the order. If specified, only inventory from this planned inbound order line can be used for the distribution. |
| Planned Inbound Order Subline | Number that identifies an order sub-line. The number corresponds to the sub-line's position on the order. If specified, only inventory from this planned inbound order sub-line can be used for the distribution. |

### Customs Order Lines fields

 
| Field | Description |
| --- | --- |
| Under Bond | If Yes, then bonded inventory is required to satisfy this order line. Bonded inventory is inventory for which customs duties and excise duties are required and have not yet been paid.<br > If No, then this order line does not require bonded inventory. |
| Rotation | Unique identifier that the application generates and automatically assigns to bonded inventory during receipt of that inventory into a bonded warehouse. The rotation ID is tracked with the inventory as long as the inventory is in the warehouse. |
| Excise Duty Stamp | If Yes, then inventory for the order line requires a duty stamp. A duty stamp is a form of tax levied on certain excise items.<br > If No, then the order line inventory does not require a duty stamp. |

## Order detail fields

 
| Field | Description |
| --- | --- |
| Order | Unique number that identifies an order. An order is a request for a supply of material or product. |
| Order Lines | Number of order lines on the order. |
| Order Type | Name of an order type. An order type is a category that is used to group orders based on the warehouse processing necessary to fulfill the order. For example, customer orders and distribution orders require different processing by the application, and so an order type can be assigned to categorize each order separately. The application uses order types, for example, to identify orders that are eligible for bulk picking, or to direct orders to specific destination locations. |
| Ship-To Address | Address name for the customer to whom the order must be shipped. |
| Allocated | Percentage of inventory that has been allocated. Additionally, an X of Y value displays the number of eaches that are allocated out of the total number of expected eaches; for example, (50 of 100). The values for this field represent the amount of allocated inventory for the displayed entity (order, shipment, load, or wave). |
| Picked | Percentage of inventory that has been picked. Additionally, an X of Y value displays the number of eaches that are picked out of the total number of expected eaches; for example, (50 of 100). The values for this field represent the amount of picked inventory for the displayed entity (order, shipment, stop, load, or wave). |
| Loaded | Percentage of inventory that has been loaded. Additionally, an X of Y value displays the number of eaches that are loaded out of the total number of expected eaches; for example, (50 of 100). The values for this field represent the amount of loaded inventory for the displayed entity (order, shipment, stop, load, or wave). |
| Carrier | Identifier for a carrier that delivers inbound inventory to the warehouse or outbound shipments to a customer. This is the identifier that will be displayed to users on the application windows and reports. In the application, a carrier can be associated with a customer, order, inbound shipment, outbound shipment, load, and service levels (such as Ground, Next Day, and Saturday Delivery). |
| Load | Unique identifier for a load. A load is one or more shipments grouped together into one or more stops that are shipped on a single piece of transport equipment. |
| Shipment | Unique identifier for an outbound shipment. A shipment is a group of orders or order lines that are allocated together and shipped to the same location. |
| Destination | Staging location to which picked inventory for the shipment is sent. |
| Wave Name | Value that is assigned to the group of pick-type work requests (picks, replenishments, and cross docks) that are created when the wave is planned. The wave name distinguishes one group of pick-type work requests from another, which enables you to track the requests through the application. For example, if you allocate inventory for a single shipment, then all of the picks, replenishments, and cross docks generated for the shipment have the same wave name. |
| Order Reference | Master sales order number generated by the external order management system and provided to the customer for order tracking. This value is only available if the application is integrated with an external order management system through Intelligent Fulfillment. |
| Delivery Number | Alphanumeric identifier assigned to the order that groups multiple orders together that need to be delivered to the same destination. See [Delivery sequence loading](../outbound-planning-concepts.md). |
| Delivery Sequence | Delivery sequence assigned to the outbound order that indicates the sequence in which the order must be processed in relation to other orders with the same delivery number. See [Delivery sequence loading](../outbound-planning-concepts.md). |

## Order Lines detail fields

 
| Field | Description |
| --- | --- |
| Order Line | Unique number that identifies the order line. The number corresponds to the line's position on the order. The first order line is automatically assigned a line number of 0001. Additional order lines are then automatically numbered sequentially, beginning with 0002. |
| Order Sub-Line | Identifying number assigned to an outbound order sub-line. By default, the first line of each order line has a sub-line number of 0000, and it identifies the finished product. The remaining sub-lines are numbered sequentially, beginning with 0001, and they identify the component items required to complete the order line. |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Ordered Quantity | Quantity of the item that the customer ordered. |
| Allocated | Percentage of inventory that has been allocated. Additionally, an X of Y value displays the number of eaches that are allocated out of the total number of expected eaches; for example, (50 of 100). The values for this field represent the amount of allocated inventory for the displayed entity (order, shipment, load, or wave). |
| Picked | Percentage of inventory that has been picked. Additionally, an X of Y value displays the number of eaches that are picked out of the total number of expected eaches; for example, (50 of 100). The values for this field represent the amount of picked inventory for the displayed entity (order, shipment, stop, load, or wave). |
| Loaded | Percentage of inventory that has been loaded. Additionally, an X of Y value displays the number of eaches that are loaded out of the total number of expected eaches; for example, (50 of 100). The values for this field represent the amount of loaded inventory for the displayed entity (order, shipment, stop, load, or wave). |
| Cancelled | A check mark in this field indicates that the order line has been cancelled. |
| Late Ship Date | Last day of the outbound shipment range. To define a single shipment date, enter the first day of the shipment range. The application uses both delivery and ship dates to consolidate order lines into shipments, depending on the values defined for order consolidation. |
| Carrier | Identifier for a carrier that delivers inbound inventory to the warehouse or outbound shipments to a customer. This is the identifier that will be displayed to users on the application windows and reports. In the application, a carrier can be associated with a customer, order, inbound shipment, outbound shipment, load, and service levels (such as Ground, Next Day, and Saturday Delivery). |
| Service Level | Identifier for the service and transit time provided by the carrier that transports an order or shipment to the customer. For example, for a parcel carrier it may be used to indicate services such as express, second-day air, or standard delivery. |
| Block Slot | A check mark in this field indicates that the corresponding slot (on a master handling unit) for the order line is used to block a slot to prevent it from being planned with another order line. Order lines that block a slot are part of a sequenced order downloaded by the host. Blocking a slot maintains the sequence of picks to slots on the handling unit when an order does not require the same items required by the other orders planned on the work assignment. No shipment line is created for a blocked order line. Also, the application does not respect any quantity or order line attributes while processing, with the exception of the item and item family set it to which it belongs.<br > **Note**: This field is a display-only attribute that is visible in grid views for existing order lines that were downloaded from the host. It is neither displayed nor editable when you manually add or modify an order line in the application. |
| Pending to TM | Indicates whether the order line's details will be sent to Transportation Manager (TM) the next time the SEND-TMS-ORDER-LINE-MEASURES job runs. A check mark is displayed if Warehouse Management has not yet sent the order line information to TM, but is scheduled to send it when the job runs again. Jobs are maintained in the Console, under Jobs.<br > Order lines details for new downloaded orders are only sent if the **Send Order Line Details** field is set to Yes in the Transportation Manager integration configuration. |

## Order Activity fields

 
| Field | Description |
| --- | --- |
| Transaction Date | Date and time at which the transaction activity was performed. |
| Activity | Identifier for the transaction activity that was performed by a user or operator. For example, when an operator performs a case pick, "Case Pick" is the displayed activity; or if a user updates an order, the displayed activity is "Outbound Order Changed." |
| Order Line | Unique number that identifies the order line. The number corresponds to the line's position on the order. The first order line is automatically assigned a line number of 0001. Additional order lines are then automatically numbered sequentially, beginning with 0002. |
| Shipment | Unique identifier for an outbound shipment. A shipment is a group of orders or order lines that are allocated together and shipped to the same location. |
| Shipment Line | Unique name or code that identifies a shipment line. A shipment line is the section of a shipment that provides detailed information about an individual item being shipped. |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Wave | Value that is assigned to the group of pick-type work requests (picks, replenishments, and cross docks) that are created when the wave is planned. The wave name distinguishes one group of pick-type work requests from another, which enables you to track the requests through the application. For example, if you allocate inventory for a single shipment, then all of the picks, replenishments, and cross docks generated for the shipment have the same wave name. |
| Order Type | Name of an order type. An order type is a category that is used to group orders based on the warehouse processing necessary to fulfill the order. For example, customer orders and distribution orders require different processing by the application, and so an order type can be assigned to categorize each order separately. The application uses order types, for example, to identify orders that are eligible for bulk picking, or to direct orders to specific destination locations. |
| Ordered Quantity | Quantity of the item that the customer ordered. |
| Pick Quantity | Quantity (in terms of material handling or stock keeping units) of the item that should be picked based on the order, work order, or replenishment. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2023 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
