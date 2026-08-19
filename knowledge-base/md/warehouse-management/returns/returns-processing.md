---
title: "Returns Processing"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/returns_processing.htm"
source: "/content/returns_processing.htm"
toc_path:
  - "Warehouse Management"
  - "Returns"
  - "Returns Processing"
sections:
  - "Options available during returns processing"
  - "Serial number capture during return processing"
  - "Process a return order"
  - "Complete an LPN"
  - "Return Processing fields"
  - "Inventory Information fields"
  - "Return fields"
images: []
source_sha1: f12198449a1e9bf5f10a3b25028fdf505afa55e0
---
# Returns Processing

Returns processing allows an operator to receive returned inventory back into the warehouse, and then direct the inventory to an appropriate storage or processing location.

Returns processing involves the following steps:

1.  Returned inventory typically arrives in a package or carton from a third-party carrier. Cartons are unloaded to a labeled pallet (LPN), and then moved to a returns processing location.
2.  At the returns location, the operator scans the LPN that contains the inventory to be processed.
3.  The operator processes the return orders, one at a time, for each of the cartons or packages on the LPN.
    -   For expected returns, the operator uses the return order associated with the carton or package.
    -   For unexpected returns, the operator creates a new return order.
        -   If the original customer order (identifying the inventory that was shipped) can be found, the new return order is created from the information in the original order.
        -   If the original order has been purged along with the customer on that order, the operator can create a new return order and add the customer. When the return order is purged (at a later date) then the customer is also purged if it is not associated with any other order.
4.  For each return order, the operator performs the following tasks:
    1.  Identifies each item by entering or scanning the item identifier. The user processes inventory in a unit quantity of 1, regardless of whether there are multiples of the same item. For example, if three identical items are returned, the user must scan each item separately.
    2.  Records the action that the customer requested for each item, such as whether to provide an exchange, replacement, or refund.
    3.  Records the condition of each item to indicate, for example, that the item is damaged or expired.
    4.  Processes the item. The application directs the operator to deposit the item. If pallet building is used, the operator is directed to deposit the item to a pallet position or to create a new LPN.
    5.  After all of the items on the return order are processed, the operator closes the return order. Closing a return starts the putaway process for the returned inventory and sends return information to the host. No additional inventory can be identified for the return.
5.  When a new return LPN is scanned, the application confirms that the previous LPN is empty. If the previous LPN is empty, the application deletes it.

## Options available during returns processing

When performing returns operations, the following options are available:

-   **Clear Form**: When starting a return, you can clear the information that you entered into the available fields to search for a return.
-   **Close Later**: When viewing item information for an order, you can choose to skip processing an item and retain the information so that it can be processed later.
-   **Complete LPN**: When starting a return, you can indicate that the LPN to which returned inventory has been processed is full. If configured to do so, this action generates work to transfer the completed LPN to its next destination.
-   **Create New**: When starting a return, you can create a new return order for processing an unexpected return. An unexpected return is inventory that arrives at the warehouse without documentation. If you can find the original customer order, the new return order can be based on the information in the original order.
-   **Edit Order Information**: When viewing items, you can view the customer and client information associated with the return order and edit the information in the return order fields.
-   **LPN Full**: When processing returns, you can indicate that the LPN to which the returned inventory is being processed is full. If configured to do so, this action generates work to transfer the completed LPN to its next destination.
-   **Search Orders**: When starting a return, you can search for return orders or original orders by entering filter criteria, and view the items associated with each order. When you find an order that you want to process, you can select and process the order.

## Serial number capture during return processing

Serial number capture takes place during returns processing for items that are configured for serialization at the Detail LPN level.

When a serial-tracked item is processed, the operator is required to enter a serial number for each of the serial number types assigned to the item.

The serial number must match the length and format required by the serial number type, and must not be a duplicate of an existing serial number for the same type.

## Process a return order

You can process an existing return order. Depending on how returns processing has been configured, you may also be allowed to create an unexpected return based on an original order, create an unexpected return without an original order, or add unexpected items to an existing return order.

1.  Select **Returns > Return Processing**. A prompt is displayed requesting the return arrival LPN.
2.  Perform one of the following tasks:
    -   In the **Return Arrival LPN** field, enter the LPN that contains the items to be processed, and then click **Process**. The Return Processing page is displayed for the return arrival LPN.
    -   Click **Cancel**, and then find a return arrival LPN:
        1.  Select **Return Arrival LPNs** and locate an LPN to process. Record the LPN for use in the next step.
        2.  Select **Return Processing** and then on the Return Processing page, click **Select LPN.**
        3.  In the **Return Arrival LPN** field, enter the LPN that contains the items to be processed.
3.  Perform one of the following tasks:
    -   In the **Process Return Order** field, enter the return order, and then click **Start Return**. The order information is displayed.
    -   To find an order:
        1.  Enter criteria in the [Return Processing fields](#Return_Processing_fields).
        2.  Click **Search Orders**. The return or original orders that match your criteria are displayed.
        3.  In the grid, select the order to process, and then click **Select and Process**.
        4.  To create a returns order from an original order:
            1.  In the **Carrier** field, enter the carrier that delivered the return to the warehouse.
            2.  In the **Shipment Reference** field, enter an identifier (such as a shipment tracking number) associated with the returned inventory.
            3.  Click **OK**. The order information is displayed.
    -   To create a new return order:
        1.  Enter criteria in the [Return Processing fields](#Return_Processing_fields).
        2.  Click **Create New**. The order information is displayed.
4.  To edit the order information:
    1.  In the left column, click **Edit Order Information**.
    2.  Enter information in the [Return Processing fields](#Return_Processing_fields).
    3.  Click **Save**.
5.  To associate a comment with the order, select an item, and then in **Comment** field, enter the comment.
6.  Perform one of the following tasks:
    -   In the grid, select an item, and then click **Process**.
    -   Above the grid, enter search criteria, and then select an item. If the item is not included on the return order, click **Yes** to process the unexpected item.
    
    The item page is displayed.
    
7.  Enter information in the [Inventory Information fields](#Inventory_Information_fields). Fields are only displayed for the attributes by which the item is tracked.
    
    **Note**: For serial-tracked items, you must enter a serial number for each of the serial types that are displayed.
    
8.  Enter information in the [Return fields](#Return_fields).
9.  Click **Process Item**. The deposit location is displayed. If pallet building is required, a deposit location, LPN, and pallet position are also displayed.
10.  If required, in the **Destination LPN** field, enter the LPN and deposit the item. For pallet building, the LPN and pallet position are displayed.
11.  Perform one of the following tasks:
     -   To indicate that the LPN is full, click **LPN Full**.
     -   To confirm the deposit, click **Sort Item**. If a message indicates that the pallet is full, click **OK**.
         
         **Note**: If configured to do so, the application creates work to transfer a full pallet to its next destination.
         
12.  Perform one of the following tasks:
     -   To close the return arrival LPN:
         1.  Click **Close Return**. A confirmation message is displayed.
         2.  To indicate that the return arrival LPN is empty, select **Yes**; otherwise, select **No**.
         3.  To start processing a new return arrival LPN, in the **Return Arrival LPN** field, enter the LPN.
         4.  Click **Process**. If the LPN was marked empty, it is deleted from the application and can be used again.
     -   To stop processing the items on the return arrival LPN, click **Close Later**.

## Complete an LPN

When starting a return, you can indicate that the LPN to which returned inventory has been processed is full.

1.  Select **Returns > Return Processing**. A prompt is displayed requesting the return arrival LPN.
2.  Perform one of the following tasks:
    -   In the **Return Arrival LPN** field, enter the LPN that contains the items to be processed, and then click **Process**. The Return Processing page is displayed for the return arrival LPN.
    -   Click **Cancel**.
3.  Click **Complete LPN**. The LPN Full window is displayed.
4.  In the **Enter the Pallet to complete** field, enter the LPN, and then click **OK**. If configured to do so, this action generates work to transfer the completed LPN to its next destination.

## Return Processing fields

 
| Field | Description |
| --- | --- |
| Return Order | Unique identifier for a return order. A return order describes the source (customer) of inventory that is returned to the warehouse along with the inventory details. A return order is typically downloaded from the host, but can be created by the returns operator if your configuration allows it. |
| Customer | Identifier of the customer to whom the return inventory was originally shipped. |
| Client | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. |
| Address | Address information. An address name represents the location and contact information of an entity (such as a carrier, client, customer, or supplier). The information fields support the entry of an address name, first and last name, address lines, a city, a state or province, a postal code, and a country. |
| Original Order | Identifier for the order that was used to identify and ship the inventory to a customer. Information from an original order can be used to create a return order if required and allowed. |
| Original Shipment Carrier | Carrier that delivered the original order to the customer. |
| Original Shipment Reference | Reference number (such as a parcel tracking number of bill of lading) for the outbound shipment used to deliver the original order to the customer. |
| Return Carrier | Carrier that delivered the return inventory to the warehouse. |
| Return Shipment Reference | Reference number (such as a parcel tracking number or bill of lading) for the inbound shipment used to deliver the return inventory from the customer to the warehouse. |
| Return Date | Date on which the returned inventory arrived at the warehouse. |

## Inventory Information fields

 
| Field | Description |
| --- | --- |
| Lot | Identifier assigned to a quantity of an item during the manufacturing process for the purpose of tracking an attribute of that item, such as an expiration date. Lots differentiate distinct groups of inventory with the same item number. Items that may require a lot number include pharmaceuticals, fabrics, food, and other products with limited shelf life. Lots are user defined and are not necessarily unique since the same lot number can be applied to different items. However, lot and item combinations must be unique. |
| Origin Code | Identifier assigned to an item to identify the item's country of origin. It is typically used for export paperwork. Origin codes are user defined. |
| Revision Level | Identifier that is assigned to an item number to differentiate revisions of the same item number. |
| Supplier Lot | Identifier that is an attribute of an item or item and lot combination and is assigned by the item's supplier. A supplier lot number used to uniquely identify and track the inventory to which it is assigned. The supplier lot number is a different attribute than the lot number, which is a manufacturer or production lot number. |
| Expiration Date | Date on which the inventory will expire. The expiration date is determined by the aging profile or shelf life assigned to the item configuration. The date is stored in the database and displayed in the web client in the original captured time zone, not converted to a different time zone, such as a user preferred time zone. |
| Manufactured Date | Date on which the inventory identified on this LPN was manufactured. The date is stored in the database and displayed in the web client in the original captured time zone, not converted to a different time zone, such as a user preferred time zone. This date is the basis for date calculations (such as for aging and shelf life) that the application performs for date-tracked items. For example, this date can be used for first in, first out (FIFO) order processing. |
| Serial Number | Unique identifier that is used to identify a piece of inventory in the warehouse. The identifier may contain numbers, letters, and check digits as required by the serial number type, and may be captured for an LPN, sub-LPN or detail LPN of inventory. The point at which the serial number is captured is determined by the serialization type assigned to the item. |

## Return fields

 
| Field | Description |
| --- | --- |
| Reason | Value that describes why the item was returned to the warehouse from the customer. The values available for selection are based on what has been configured for the client or warehouse. |
| Condition | Value that describes the state of the item, especially with regard to its appearance, quality, or working order. The values available for selection are based on what has been configured for the client or warehouse. |
| Action | Value that describes the action to be performed as a result of the item being returned. The action is typically in compliance with the customer request associated with the return order. The values available for selection are based on what has been configured for the client or warehouse. |
| Status | Inventory status that is assigned to the returned item. An inventory status may be displayed by default, based on the item attributes; however, the status can be changed. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
