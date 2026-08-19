---
title: "History"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/history.htm"
source: "/content/history.htm"
toc_path:
  - "Warehouse Management"
  - "Shared functions"
  - "History"
sections:
  - "View historical transactions"
  - "Inventory History fields"
  - "Attributes History fields"
  - "Order History fields"
  - "Adjustment History fields"
  - "Handling Unit History fields"
images: []
source_sha1: 32c3ccd41312eb4100c14a6ce53d2091661d0194
---
# History

The History page is accessible from the following modules: **Inventory**, **Picking**, **Production**, **Receiving**, **Shipping**, or **Yard**.

This page provides a detailed view into the activities performed in the warehouse. When you first access the page, you enter the date range and time duration for which to search completed transactions. You can also filter the transactions by more specific criteria; some examples include an LPN, a location, an order, or the activity or operation that was performed.

The History page includes the following tabs:

-   **Inventory**: Displays transaction information related to general inventory information, such as the item, UOM, LPN, and location, among others.
-   **Attributes**: Displays transaction information related to inventory attributes, such as the footprint, lot, and origin, among others. If enabled, this tab also displays user-defined inventory attributes.
-   **Order**: Displays transaction information related to order information, such as the order or shipment number, carrier, and transport equipment identifier, among others.
-   **Adjustments**: Displays transaction information related to inventory adjustments, such as a status change and the reason for the change, among others.
-   **Handling Unit**: Displays transaction information related to warehouse handling units, such as the handling unit type and status, among others.

## View historical transactions

1.  View the History page.
    
    1.  Select one of the following modules: **Inventory**, **Picking**, **Production**, **Receiving**, **Shipping**, or **Yard**.
    2.  Select **History**.
    
2.  In the **Search** fields, enter the date and time by which to limit the displayed transactions. By default, transactions that occurred in the last hour are displayed.
3.  Click **Go**.
4.  To view transaction details related to inventory information, select **Inventory** and view the information in the [Inventory History fields](#Inventory_history_fields).
5.  To view transaction details related to inventory attributes, select **Attributes** and view the information in the [Attributes History fields](#Attributes_history_fields).
6.  To view transaction details related to order and shipment information, select **Order** and view the information in the [Order History fields](#Order_history_fields).
7.  To view transaction details related to inventory adjustments, select **Adjustment** and view the information in the [Adjustment History fields](#Adjustment_fields).
8.  To view transaction details related to handling units, select **Handling Unit** and view the information in the [Handling Unit History fields](#Handling_Unit_history_fields).

## Inventory History fields

 
| Field | Description |
| --- | --- |
| Transaction Date | Date and time at which the transaction activity was performed. |
| User | User who performed the transaction activity. |
| Activity | Identifier for the transaction activity that was performed by a user or operator. For example, when an operator performs a case pick, "Case Pick" is the displayed activity; or if a user updates an order, the displayed activity is "Outbound Order Changed." |
| Operation | Work operation that identifies the type of directed work that was created. |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Quantity | Quantity (in eaches) of an item that was involved in the transaction activity, such as the number of eaches that was picked or adjusted. |
| Move UOM | Identifier for the packaging level at which an item was moved in the transaction, such as the UOM in which inventory was received or picked. Units of measure (such as each, inner pack, case, layer, or pallet) are used in item footprint configurations. For example, assume an operator picks 1 pallet that contains 50 eaches. In the transaction for the pick, the **Quantity** field displays the number of eaches that were picked (50), and the **UOM** field displays the pick UOM (PA). |
| LPN | Unique identifier for inventory. Typically, an LPN refers to a pallet; however, it can refer to inventory received at less than pallet quantity. The LPN is the license plate by which the inventory is tracked in the facility. |
| Destination LPN | Unique identifier for the pallet to which inventory was moved, such as for an adjustment. The LPN is the license plate by which the inventory is tracked in the facility. |
| Sub-LPN | Unique identifier for a case of inventory. |
| Destination Sub-LPN | Unique identifier for the case to which inventory was moved, such as for an adjustment. The sub-LPN is the license plate by which a case of inventory is tracked in the facility. |
| Detail LPN | Unique identifier for inventory at the unit or each unit of measure. |
| Destination Detail LPN | Unique identifier for inventory at the unit or each UOM; the destination detail LPN is relevant for identification through an adjustment. |
| Source Location | Location where the work originated, such as the location from which inventory is picked, at which a count is performed, or from which transport equipment is moved. |
| Destination Location | Unique identifier for the location where the work was completed, such as the location to which inventory was delivered or to which transport equipment was moved. |
| Source Area | Area in which the transaction activity began, such as the area from which inventory was moved. |
| Destination Area | Area in which the transaction activity ended, such as the area to which inventory was moved. |
| Client | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. |
| Warehouse | Unique identifier for the site at which the transaction activity was performed. |
| Move Reference | Identifier for the movement of the transaction. This reference is used internally to display the type of inventory movements. |
| Exception | Value that describes the reason for the exception. Exceptions occur when there is a discrepancy in the amount of actual residual inventory and the expected residual quantity at the end of the deposit process and the distribution audit fails.<br>-   • **Extra Inventory Remaining**: There is inventory remaining after the distribution assignment is completed.
<br>-   • **Insufficient Inventory Remaining**: The quantity of inventory remaining does not match what the application expects to be remaining.
<br>-   • **Expected Inventory, None Remaining**: The application expects there to be additional inventory and there is none remaining.
<br>-   • **No Expected Inventory, Inventory Remaining**: The application does not expect any additional inventory and there is some remaining. |
| Distribution Exception ID | Identifier for the location to which the operator is directed to deposit unexpected residual inventory. |
| Expected Quantity | Quantity of residual inventory that was expected by the application for the distribution audit. |
| Reported Quantity | Quantity of residual inventory that was entered by an operator during the distribution audit. This quantity does not match the application's expected quantity, which caused the distribution exception to occur. |
| Device | Unique identifier for a piece of equipment, such as a radio frequency terminal or voice device, with which the user performed the transition activity. |
| Daily Transaction ID | Unique identifier for the daily transactions (general activity and work activities) performed within the warehouse. |
| Archive Date | Date and time when the transaction was archived. |
| Archive Source | Name of the instance used as the source where the transaction data will be archived. This is typically the production (working) instance. This value would be different than the production working instance if you have multiple source application that will be archived to the same archive environment. There is a possibility of data with duplicate warehouse IDs. |
| Transaction Detail ID | Unique identifier of the record in the transaction detail table. |
| Transaction Detail Table | Table name where the transaction detail is stored. |

## Attributes History fields

**Note**: If enabled, the user defined inventory attributes (UDIA) are displayed in this tab.

 
| Field | Description |
| --- | --- |
| Transaction Date | Date and time at which the transaction activity was performed. |
| User | User who performed the transaction activity. |
| Activity | Identifier for the transaction activity that was performed by a user or operator. For example, when an operator performs a case pick, "Case Pick" is the displayed activity; or if a user updates an order, the displayed activity is "Outbound Order Changed." |
| Operation | Work operation that identifies the type of directed work that was created. |
| Footprint | Name that identifies a footprint, which describes the packaging dimensions and units of measure for the item with which it is associated. |
| Lot | Identifier assigned to a quantity of an item during the manufacturing process for the purpose of tracking an attribute of that item, such as an expiration date. Lots differentiate distinct groups of inventory with the same item number. Items that may require a lot number include pharmaceuticals, fabrics, food, and other products with limited shelf life. Lots are user defined and are not necessarily unique since the same lot number can be applied to different items. However, lot and item combinations must be unique. |
| Supplier Lot | Identifier that is an attribute of an item or item and lot combination and is assigned by the item's supplier. A supplier lot number used to uniquely identify and track the inventory to which it is assigned. The supplier lot number is a different attribute than the lot number, which is a manufacturer or production lot number. |
| Origin | Identifier assigned to an item to identify the item's country of origin. It is typically used for export paperwork. Origin codes are user defined. |
| Revision Level | Identifier that is assigned to an item number to differentiate revisions of the same item number. |
| Catch Quantity | Actual measured quantity of the inventory to receive. Catch quantity is typically obtained at receipt and may be verified prior to shipment. |
| Catch Unit Type | Unit of measure, such as feet, gallons or pounds, used when capturing catch weight measurements. |

## Order History fields

 
| Field | Description |
| --- | --- |
| Transaction Date | Date and time at which the transaction activity was performed. |
| User | User who performed the transaction activity. |
| Activity | Identifier for the transaction activity that was performed by a user or operator. For example, when an operator performs a case pick, "Case Pick" is the displayed activity; or if a user updates an order, the displayed activity is "Outbound Order Changed." |
| Operation | Work operation that identifies the type of directed work that was created. |
| Order | Unique number that identifies an order. An order is a request for a supply of material or product. |
| Supplier | Identifier for a supplier. A supplier can be an individual, organization, or another warehouse within your own organization from which you repeatedly receive inventory or handling units. |
| Carrier | Identifier for a carrier that delivers inbound inventory to the warehouse or outbound shipments to a customer. This is the identifier that will be displayed to users on the application windows and reports. In the application, a carrier can be associated with a customer, order, inbound shipment, outbound shipment, load, and service levels (such as Ground, Next Day, and Saturday Delivery). |
| To Carrier | New carrier to which the shipment was assigned. |
| Service Level | Identifier for the service and transit time provided by the carrier that transports an order or shipment to the customer. For example, for a parcel carrier it may be used to indicate services such as express, second-day air, or standard delivery. |
| To Service Level | Identifier for the service and transit time provided by the carrier that transports an order or shipment to the customer. For example, for a parcel carrier it may be used to indicate services such as express, second-day air, or standard delivery. This is the new service level that was assigned to the shipment. |
| Transport Equipment | Alphanumeric identifier for transport equipment. Transport equipment numbers are not unique, can exist multiple times, and can be associated with various carriers. |
| To Transport Equipment | Alphanumeric identifier used to identify a piece of transport equipment associated with an outbound load or inbound shipment. This is the new transport equipment to which a shipment or load was assigned. |
| Shipment | Unique identifier for an outbound shipment. A shipment is a group of orders or order lines that are allocated together and shipped to the same location. |
| Tracking Number | Unique identifier used by a parcel carrier to track a parcel throughout the delivery process. |

## Adjustment History fields

 
| Field | Description |
| --- | --- |
| Transaction Date | Date and time at which the transaction activity was performed. |
| User | User who performed the transaction activity. |
| Activity | Identifier for the transaction activity that was performed by a user or operator. For example, when an operator performs a case pick, "Case Pick" is the displayed activity; or if a user updates an order, the displayed activity is "Outbound Order Changed." |
| Operation | Work operation that identifies the type of directed work that was created. |
| From Inventory Status | Status of inventory before the transaction activity was performed. |
| To Inventory Status | Status of inventory after the transaction activity was performed. |
| From Aging Profile | Identifier of the aging profile before the transaction activity was performed. |
| To Aging Profile | Identifier of the aging profile after the transaction activity was performed. |
| Variable | Unique identifier that represents a piece of source text in the message catalog. Each MLS ID is associated with a description (the text that is displayed in the application in place of the MLS ID), and other attributes that determine where it is used. MLS IDs are used to support translations and customizations. |
| From Value | Value of the **Variable** field before the transaction activity was performed. |
| To Value | Value of the **Variable** field after the transaction activity was performed. |
| Adjustment Reference One | Identifier for the host account to which the inventory adjustment was performed. This information was included when the inventory adjustment transaction was sent to the host. |
| Adjustment Reference Two | Identifier for the host account to which the inventory adjustment was performed. This information was included when the inventory adjustment transaction was sent to the host. |
| Reason | A reason that indicates why the inventory adjustment was performed. |
| Comment for Change | Text that further describes the change. |

## Handling Unit History fields

 
| Field | Description |
| --- | --- |
| Transaction Date | Date and time at which the transaction activity was performed. |
| User | User who performed the transaction activity. |
| Activity | Identifier for the transaction activity that was performed by a user or operator. For example, when an operator performs a case pick, "Case Pick" is the displayed activity; or if a user updates an order, the displayed activity is "Outbound Order Changed." |
| Operation | Work operation that identifies the type of directed work that was created. |
| Handling Unit Types | Category that classifies a group of handling units (for example, pallets, totes, transport equipment, or vehicles) that share the same characteristics such as size and weight, as well as whether they are serialized, temporary, or considered a container. The application tracks the on-hand quantity of handling units by type and, for serialized handling units, by handling unit identifier. |
| Handling Unit | Unique identifier for a handling unit that is tracked as an individual as well as collectively by handling unit type. You may want to track valuable handling units, such as CHEP pallets, as individuals. All transport equipment handling units are tracked as individuals. Handling units tracked as individuals can be further identified with a serial number. |
| Handling Unit Status | Current condition of the handling unit, such as active or inactive. This value is only used for reporting purposes. |
| Wrap | LPN-level packaging attribute for inventory. LPN packaging attributes are user-defined fields that are used to indicate requirements such as pallet wrapping, use of a slip sheet, and the application of labels on all four sides of a pallet of inventory. |
| Double Wrap | LPN-level packaging attribute for inventory. LPN packaging attributes are user-defined fields that are used to indicate requirements such as pallet wrapping, use of a slip sheet, and the application of labels on all four sides of a pallet of inventory. |
| Label 4 Sides | LPN-level packaging attribute for inventory. LPN packaging attributes are user-defined fields that are used to indicate requirements such as pallet wrapping, use of a slip sheet, and the application of labels on all four sides of a pallet of inventory. |
| Slip Sheet | LPN-level packaging attribute for inventory. LPN packaging attributes are user-defined fields that are used to indicate requirements such as pallet wrapping, use of a slip sheet, and the application of labels on all four sides of a pallet of inventory. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
