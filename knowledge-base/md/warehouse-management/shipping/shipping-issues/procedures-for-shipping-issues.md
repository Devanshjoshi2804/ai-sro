---
title: "Procedures for shipping issues"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/procedures_for_shipping_issues.htm"
source: "/content/procedures_for_shipping_issues.htm"
toc_path:
  - "Warehouse Management"
  - "Shipping"
  - "Shipping Issues"
  - "Procedures for shipping issues"
sections:
  - "Manage short loads and items"
  - "Manage inventory that is not shippable"
  - "View problem inventory"
  - "View audited inventory"
  - "Short Inventory fields"
  - "Not Shippable Inventory fields"
  - "Problem Inventory fields"
  - "Basic Audit fields"
  - "Audit Attributes fields"
  - "Audit Dates fields"
  - "Audit Shipping fields"
  - "Audit Serialized fields"
images:
  - "/content/resources/images/image429922.png"
  - "/content/resources/images/image429922.png"
source_sha1: b44a7782222493b688c5d2bbe82f54a0cd7f389b
---
# Procedures for shipping issues

The following procedures can be performed on the issues identified on the Shipping Issues page.

## Manage short loads and items

For a description of the issue, see [Shipping issue: Short](../shipping-issues.md).

1.  Select **Shipping > Shipping Issues > Short**.
2.  Perform one of the following tasks:
    -   To view short inventory by load:
        1.  Select **Loads**. The display shows a list of loads that contain at least one order that is not completely fulfilled.
        2.  Click ![Expand](../../../../images/resources/images/image429922.png). The display shows shipment and item information for the short load.
    -   To view short inventory by item, select **Items**. The display shows a list of items for which the ordered quantity cannot be fulfilled.
3.  In the grid, click a shipment number or item to view additional information for the short inventory.
4.  View the information in the [Short Inventory fields](#Short_Inventory_fields).
5.  Perform one or more of the following tasks:
    -   To view inventory in the warehouse, select **On Hand**. The display shows the item quantity that is in storage, and the picking zone in which the inventory is stored.
    -   To view inventory in receiving pending putaway, select **To Store**. The display shows the item quantity that is in a receiving staging lane awaiting storage, and the pick zone in which the inventory will be stored.
    -   To view expected inventory, select **Expected**. The display shows the quantity that is expected to arrive on an inbound shipment, including the date and time the inbound shipment is expected at the warehouse.
6.  To ship an order short:
    1.  In the **Short Shipment Lines** grid, select the check box next to the line you want to ship short.
        
        **Note**: An order can only be shipped short if the **Partial** field is set to Yes on the order line with unfulfilled inventory.
        
    2.  Click **Ship Short**. The application cancels any outstanding replenishments for the short order line.
    3.  If a message is displayed stating the shipment has been unassigned from the stop, click **OK**.
        
        **Note**: A shipment is unassigned from a stop if the shipment line you ship short is the only line on the shipment and has no fulfilled quantity.
        
7.  To reallocate the short inventory:
    1.  In the **Short Shipment Lines** grid, select the check box next to the order you want to reallocate.
    2.  Click **Reallocate**. The application searches for available inventory to fulfill the short order line.

## Manage inventory that is not shippable

For a description of the issue, see [Shipping issue: Not shippable inventory](../shipping-issues.md).

1.  Select **Shipping > Shipping Issues > Not Shippable Inventory**.
2.  To view the details for an LPN, in the grid, click ![Expand](../../../../images/resources/images/image429922.png).
3.  View information in the [Not Shippable Inventory fields](#Not_Shippable_Inventory_fields).
4.  To approve the catch quantity:
    1.  Select the check box next to the LPN.
    2.  From the **Actions** drop-down list, select **Approve Catch Qty**. The catch quantity of the LPN is approved, and the inventory is available for shipping.
5.  To unpick inventory that is not shippable:
    1.  Select the check box next to the LPN.
    2.  From the **Actions** drop-down list, select **Unpick/Return**. The Unpick/Return window is displayed.
    3.  Enter information in the [Unpick and Return fields](../../shared-functions/inventory/procedures-for-lpns.md).
    4.  Click **Save**.
6.  To release a hold from an LPN:
    1.  Select the check box next to the LPN.
    2.  From the **Actions** drop-down list, select **Release Hold**. The Release Hold page is displayed.
    3.  Select the hold to release, and click **Apply**. The Release Hold window is displayed.
    4.  Enter information in the following fields:
        
        | Field | Description |
        | --- | --- |
        | Change Inventory Status | Status to which the released inventory is changed. This field is displayed only if the **Inventory Status** field on the hold configuration is set to Yes. |
        | Change Only Certain Statuses | Indicates that the status for certain released inventory is to be changed based on its current status. If selected, then for each inventory status, in the **To Inventory Status** column, select the status to apply to the inventory. For example, you may only want to update the status for inventory that has a Hold status, while keeping the remaining released inventory in its current status. This field is displayed only if the **Inventory Status** field on the hold configuration is set to Yes. |
        | Reason | Value that indicates why the hold is being released. A reason is required whenever a hold is released. |
        
7.  Click **OK**. A confirmation message is displayed.
    
    **Note**: If the application was unable to release the hold, then a list of the LPNs is displayed with the reason the hold could not be released.
    

## View problem inventory

For a description of the issue, see [Shipping issue: Problem inventory](../shipping-issues.md).

Problem inventory refers to inventory that has been adjusted off of a shipment and moved to a problem location. The inventory is unpicked and no longer associated with a shipment. This occurs, for example, when an order is cancelled after a shipment has been staged or inventory was damaged during picking.

1.  Select **Shipping > Shipping Issues > Problem Inventory**.
2.  View information in the [Problem Inventory fields](#Problem_Inventory_fields).

## View audited inventory

For a description of the issue, see [Shipping issue: RF outbound audit](../shipping-issues.md).

1.  Select **Shipping > Shipping Issues > RF Outbound Audit**.
2.  To view information for audits with discrepancies, click **Discrepancies**.
3.  To view information for pending and completed audits, click **Pending/Completed**.
4.  To view detailed information for a specific audit record, in the grid, click the identifier for the inventory and perform one or more of the following tasks:
    -   Click **Basic** and view the [Basic Audit fields](#Basic_Audit_fields).
    -   Click **Attributes** and view the [Audit Attributes fields](#Audit_attributes_fields).
    -   Click **Dates** and view the [Audit Dates fields](#Audit_Dates_fields).
    -   Click **Shipping** and view the [Audit Shipping fields](#Audit_Shipping_fields).
    -   Click **Serialized** and view the [Audit Serialized fields](#Audit_serialized_fields).

## Short Inventory fields

 
| Field | Description |
| --- | --- |
| Departure | Date and time that the transport equipment associated with a load is scheduled to depart from the warehouse. |
| Load | Unique identifier for a load. A load is one or more shipments grouped together into one or more stops that are shipped on a single piece of transport equipment. |
| Location | Unique name for a location within the facility that is used to receive, store, process, or ship inventory. |
| Transport | Alphanumeric identifier used to identify a piece of transport equipment associated with an outbound load or inbound shipment. Identifier for the carrier with which the transport equipment number is associated. |
| Shipment | Unique identifier for an outbound shipment. A shipment is a group of orders or order lines that are allocated together and shipped to the same location. |
| Outbound Order | Unique identifier for an outbound order. An order is a request for a supply of material or product. |
| Customer | Name used to identify a business to whom you ship inventory. Each customer has a profile that is used to define how their inventory is handled, how their orders are processed, and how their inventory is shipped. |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Short | Quantity of an item that is short of the quantity required for the order line. For example, a value of "10 of 200" means that a quantity of 200 is required to fulfill the order line, and a quantity of 10 is as yet unfulfilled; therefore, the order line is 10 short of the required quantity of 200. |
| Loads Short | Quantity of loads that are short due to an unfulfilled demand of the displayed item. |
| Orders Short | Quantity of orders that are short due to an unfulfilled demand of the displayed item. |
| Manifests Short | Quantity of parcel manifests that are short due to an unfulfilled demand of the displayed item. |
| On Hand | Quantity of the displayed item that is currently in storage. |
| To Store | Quantity of the displayed item that is in a receiving staging lane and awaiting storage. |
| Expected | Quantity of the displayed item that is expected to arrive at the warehouse on an inbound shipment. |
| Allow Shipping Short | Indicates whether the order line with unfulfilled inventory is allowed to be shipped short. If the order line can be shipped short, a check mark is displayed in this column. This is determined by the **Partial** field on the order line. |
| Short Reason | Reason that the ordered quantity cannot be fulfilled. |
| Realloc Attempts | Number of times that the application has attempted to fulfill the short quantity through reallocation. |

## Not Shippable Inventory fields

 
| Field | Description |
| --- | --- |
| LPN | Unique identifier for inventory. Typically, an LPN refers to a pallet; however, it can refer to inventory received at less than pallet quantity. The LPN is the license plate by which the inventory is tracked in the facility. |
| Departure | Date and time that the transport equipment associated with a load is scheduled to depart from the warehouse. |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Description | Text that further describes the item. |
| Client | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. |
| Location | Unique name for a location within the facility that is used to receive, store, process, or ship inventory. |
| Reason | Reason that the item cannot be shipped. For example, a hold that prevents shipping may be assigned to the item. |
| Issue On | Identifier and description of the item that is not shippable. |
| Load | Unique identifier for a load. A load is one or more shipments grouped together into one or more stops that are shipped on a single piece of transport equipment. |
| Shipment | Unique identifier for an outbound shipment. A shipment is a group of orders or order lines that are allocated together and shipped to the same location. |
| Order | Unique number that identifies an order. An order is a request for a supply of material or product. |
| Manifest | Internal tracking number assigned and used by the application to uniquely identify a manifest. A manifest list identifies all parcels that are shipped together on the same piece of transport equipment by the parcel carrier. This identifier is blank until the manifest is closed. |
| Route to Address | Name and address of the distributor or organization to which the shipment is initially sent. The route-to address and ship-to address are the same if the shipment does not require an initial stop. |

## Problem Inventory fields

 
| Field | Description |
| --- | --- |
| Duration | Amount of time, in minutes, that the displayed inventory has been in a problem location. A problem location is not typically associated with a pick zone because the problem inventory needs to be evaluated to determine its disposition. For example, if it is not damaged, it could be returned to storage; if it is damaged, it may need to be directed to a processing or scrap location. |
| Location | Unique name for a location within the facility that is used to receive, store, process, or ship inventory. |
| LPN | Unique identifier for inventory. Typically, an LPN refers to a pallet; however, it can refer to inventory received at less than pallet quantity. The LPN is the license plate by which the inventory is tracked in the facility. |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Quantity | Quantity of the item that resides in a problem location. |
| Inventory Status | Value that defines the quality or disposition of the inventory. |
| Hold | Unique identifier for the hold definition. Hold numbers are applied to inventory identifiers to indicate that the inventory is on hold as described in the hold definition. Hold numbers can either be user defined or application generated when hold definitions are created. |

## Basic Audit fields

 
| Field | Description |
| --- | --- |
| Audit Started | Scheduled date and time on which the audit is to be (or was) completed, and the type of audit that is to be (or was) performed. |
| LPN | Unique identifier for inventory. Typically, an LPN refers to a pallet; however, it can refer to inventory received at less than pallet quantity. The LPN is the license plate by which the inventory is tracked in the facility. |
| Slot | Identifier for the slot on a handling unit in which the audited inventory is located. |
| Carton Number | Unique identifier for a carton. Identifies the carton that contains the inventory under audit. |
| Carton Position | Position of the audited carton on the destination picking equipment (such as a cart). |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Client | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. |
| Expected Quantity | Quantity of inventory that is expected by the application for the LPN under audit. |
| Actual Quantity | Quantity of inventory that was recorded by the operator during the audit. |

## Audit Attributes fields

 
| Field | Description |
| --- | --- |
| LPN | Unique identifier for inventory. Typically, an LPN refers to a pallet; however, it can refer to inventory received at less than pallet quantity. The LPN is the license plate by which the inventory is tracked in the facility. |
| Item | Identifier for an item. An item is any specific product that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). This is the identifier for the inventory under audit. |
| Client | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. |
| Lot | Identifier assigned to a quantity of an item during the manufacturing process for the purpose of tracking an attribute of that item, such as an expiration date. Lots differentiate distinct groups of inventory with the same item number. Items that may require a lot number include pharmaceuticals, fabrics, food, and other products with limited shelf life. Lots are user defined and are not necessarily unique since the same lot number can be applied to different items. However, lot and item combinations must be unique. |
| Origin Code | Identifier assigned to an item to identify the item's country of origin. It is typically used for export paperwork. Origin codes are user defined. |
| Revision Level | Identifier that is assigned to an item number to differentiate revisions of the same item number. |
| Supplier | Identifier for a supplier. A supplier can be an individual, organization, or another warehouse within your own organization from which you repeatedly receive inventory or handling units. |
| Supplier Lot | Identifier that is an attribute of an item or item and lot combination and is assigned by the item's supplier. A supplier lot number used to uniquely identify and track the inventory to which it is assigned. The supplier lot number is a different attribute than the lot number, which is a manufacturer or production lot number. |
| Handling Unit | Unique identifier for a handling unit that is tracked as an individual as well as collectively by handling unit type. You may want to track valuable handling units, such as CHEP pallets, as individuals. All transport equipment handling units are tracked as individuals. Handling units tracked as individuals can be further identified with a serial number. |

## Audit Dates fields

 
| Field | Description |
| --- | --- |
| LPN | Unique identifier for inventory. Typically, an LPN refers to a pallet; however, it can refer to inventory received at less than pallet quantity. The LPN is the license plate by which the inventory is tracked in the facility. |
| Item | Identifier for an item. An item is any specific product that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). This is the identifier for the inventory under audit. |
| Client | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. |
| Aging profile | Name of the aging profile representing the aging process assigned to this item. An inventory aging profile is a configuration that defines a series of inventory statuses, each of which is associated with an age, such as 2 hours, 10 days, or 4 weeks. You assign an aging profile to a date-tracked item when you want the application to automatically update the inventory status of inventory for the item as it ages in the warehouse. |
| FIFO | Date used by the application for processing inventory when the first in, first out (FIFO) inventory rotation method is used. FIFO ensures that the oldest inventory is selected first. |
| Manufactured Date | Date on which the inventory identified on this LPN was manufactured. The date is stored in the database and displayed in the web client in the original captured time zone, not converted to a different time zone, such as a user preferred time zone. This date is the basis for date calculations (such as for aging and shelf life) that the application performs for date-tracked items. For example, this date can be used for first in, first out (FIFO) order processing. |
| Expire | Date on which the inventory will expire. The expiration date is determined by aging profile or shelf life assigned to the item configuration. The date is stored in the database and displayed in the web client in the original captured time zone, not converted to a different time zone, such as a user preferred time zone. |
| Received | Date on which the inventory was received into the warehouse. |

## Audit Shipping fields

 
| Field | Description |
| --- | --- |
| LPN | Unique identifier for inventory. Typically, an LPN refers to a pallet; however, it can refer to inventory received at less than pallet quantity. The LPN is the license plate by which the inventory is tracked in the facility. |
| Item | Identifier for an item. An item is any specific product that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). This is the identifier for the inventory under audit. |
| Client | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. |
| Pick Date | Date on which the inventory for the LPN was picked. |
| User | User who performed the transaction activity. |
| Order | Unique number that identifies an order. An order is a request for a supply of material or product. |
| Order Line | Unique number that identifies the order line. The number corresponds to the line's position on the order. The first order line is automatically assigned a line number of 0001. Additional order lines are then automatically numbered sequentially, beginning with 0002. |
| Work Assignment | Unique identifier that the application assigns to a work assignment when the assignment is created. A work assignment is a list of individual picks that an operator can perform in one picking tour, moving from one pick location to another until the assignment is complete. |
| Load | Unique identifier for a load. A load is one or more shipments grouped together into one or more stops that are shipped on a single piece of transport equipment. |
| Stop | Unique identifier for a stop. A stop is a collection of one or more outbound shipments making up a delivery to a single customer. |
| Distribution | Unique code that is used to identify a distribution. The distribution identifier can be application-generated or user-specified. A distribution is a pre-allocation of a warehouse planned inbound order to a store. |
| Address | Address information. An address name represents the location and contact information of an entity (such as a carrier, client, customer, or supplier). The information fields support the entry of an address name, first and last name, address lines, a city, a state or province, a postal code, and a country. |

## Audit Serialized fields

 
| Field | Description |
| --- | --- |
| LPN | Unique identifier for inventory. Typically, an LPN refers to a pallet; however, it can refer to inventory received at less than pallet quantity. The LPN is the license plate by which the inventory is tracked in the facility. |
| Item | Identifier for an item. An item is any specific product that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). This is the identifier for the inventory under audit. |
| Client | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. |
| Serial Number | Unique identifier that is used to identify a piece of inventory in the warehouse. The identifier may contain numbers, letters, and check digits as required by the serial number type, and may be captured for an LPN, sub-LPN or detail LPN of inventory. The point at which the serial number is captured is determined by the serialization type assigned to the item. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
