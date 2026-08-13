---
title: "Inbound Identification"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/inbound_identification.htm"
source: "/content/inbound_identification.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inbound"
  - "Receiving"
  - "Inbound Identification"
sections:
  - "Receiving, shipping, and processing resource codes"
  - "Resource types"
  - "Configure inbound identification"
  - "Inbound Identification fields"
images: []
source_sha1: e3163685111fda2059c983118d62cc62b5f844c6
---
# Inbound Identification

Identification is the first step in the receiving process. During identification, users assign an identifier (LPN) to incoming inventory, indicate a quantity and status for the inventory, and assign any applicable inventory attributes (such as a lot). Inventory is identified from transport equipment or inbound shipments. Inventory identification also takes place when a user identifies inventory during an inventory adjustment. Once inventory is identified, it can be put away.

You can configure the rules the application uses to identify and receive inventory into your warehouse, including what the user has to validate, what is displayed to operators on their device, how the application reserves staging locations, and how the application searches transport equipment for inventory needed to fill short orders.

## Receiving, shipping, and processing resource codes

Receiving resource codes for a location are set when a location is assigned for inbound inventory; this occurs during putaway after inventory has been identified. For example, if the resource variable is set to be the LPN against which the inventory is received, then after the inventory is received and directed to a location, that location's receiving resource code is set to the LPN. Only inventory received for that specific LPN is allowed to be placed in the location until the location is emptied.

Shipping resource codes for a location are set during inventory allocation when the ship staging location is assigned for the outbound inventory. For example, if the resource variable is set to be the carrier, then when a shipment is assigned to a location, the location is set to the carrier associated with the outbound inventory. Thereafter, only inventory scheduled to be shipped by that specific carrier is allowed to be placed in the location.

Processing resource codes for a location are set when the location is assigned for deposit. The deposit process involves placing picked or cross-docked inventory for multiple orders into separate locations. For example, if the resource variable is set to be the item family, then the resource code is set to the item family to which the inventory belongs.

You can configure location types to automatically clear the resource codes for shipping and processing locations. However, for warehouses that want processing or ship staging locations reserved even after the location is emptied (such as for the same customer or for inventory in a specific item family) the location type can be configured to not clear the location, meaning the resource code is retained.

## Resource types

A resource type is a method by which a deposit location in a staging or processing movement zone is reserved for specific inventory. The application uses the resource type to obtain a resource code for a location, which identifies the inventory allowed in the location. The following resource types are available for use in location reservation processing:

-   **Command**: The resource code is generated based on the results of running the command specified as the resource variable. The command must be defined in the application and must accept a work reference; the published value from the command is used as the resource code. For example, if inventory is moving through the zone, the application runs the specified command and uses the result as the resource code.
-   **Derived**: The resource code is derived from a column name (field) on the pick work, shipment, shipment header, outbound order, and outbound order header tables. The resource code can be assigned to a location when inventory is allocated or when it is being moved from one zone in the movement path to the next, depending on the configuration for the outbound pick method. After a location is assigned a code, only inventory that has the same value (such as a specific carrier) is deposited to the location until the the location is emptied of all inventory and is released either manually or automatically. If you select a derived resource type, you select one or more resource variables from a list that includes column names (fields) from the aforementioned tables. For example, if you select Derived as the resource type and you select Carrier as the resource variable, the application will set the location's resource code to the carrier that is responsible for shipping the inventory.
-   **Unrestricted**: The resource code specifies that any inventory can be mixed in the location until the location capacity is reached. The application does not match the resource code value to an inventory attribute value in order to assign inventory to the location; all inventory can be routed to a location with an unrestricted resource code.
-   **Generate**: The resource code value is an application-generated value based on the control number that you select as the resource variable.
-   **Location Assigned**: The resource code specifies the location within a zone to which all inventory is directed regardless of the location's capacity. For example, if inventory is moving through a zone where staging takes place, the resource variable you specify is the location within the zone where you want the inventory placed. For received items, the assigned resource variable for the zone is the location where inbound inventory is placed. For picked inventory, the resource code is set upon allocation, and the location is also assigned to the pick move for inventory moving through the zone for distribution or shipment. The outbound inventory moving through the zone would be directed to the specified location.

## Configure inbound identification

1.  Select **Configuration > Inbound > Receiving > Inbound Identification**.
2.  Enter information in the [Inbound Identification fields](#Inbound_identification_fields).
3.  For a 3PL environment, to select the clients that require a single expiration date for all inventory with the same item lot:
    1.  Under **VALIDATION**, click **Enforce Expiration Date of Item Lot**.
    2.  In the grid, select the check box next to the clients that apply.
    3.  Click **Apply**.
4.  To select the attributes an operator must confirm during sorted case receiving:
    1.  Under **CASE SORTING**, click **Case Sorting Sequence**.
    2.  To select criteria from displayed entities:
        1.  If the advanced query is displayed, click **Simple**.
        2.  If the available entities are not displayed, click **Show Available**.
        3.  In the **Available** grid, select the entities that you want to use as criteria.
        4.  Click **Add selected**. The entities are added to the **Selected** grid.
        5.  To remove criteria, in the **Selected** grid, select the criteria to remove, and click **Remove selected**.
        6.  To reorder the criteria, in the **Selected** grid, click a row, and then click the up or down arrow to move the selected criteria. The application applies the criteria in sequential order according to how it is displayed in the grid.
    3.  To enter criteria using database entities, click **Advanced**, and then enter the column and field name, using a period to separate the column and field. Multiple column and field entries must be separated by a comma and space.
        
        You can use operators like IS NULL or IS NOT NULL to build an advanced query. For example, <column name>.<field name > IS NOT NULL, <column name>.< field name>.
        
    4.  Click **Apply**.
5.  To configure the resource type that the application uses to reserve inventory in movement zones that consist of receiving staging locations:
    1.  Under **RECEIVING STAGING LANE ASSIGNMENT**, click **Location Reservation**.
    2.  In the grid, click the movement zone to configure.
    3.  To reserve locations using the returned value of a server command:
        1.  From the **Resource Type** drop-down list, select **Command**.
        2.  In the **Reserve by Command** field, enter the command.
    4.  To reserve locations using a value derived from an attribute associated with the inventory:
        1.  From the **Resource Type** drop-down list, select **Derived**.
        2.  To select the attributes by which to reserve locations:
            1.  Click **Derived Resource Variables**.
            2.  In the **Available Attributes** column, select the check box next to the attributes that must match for inventory to be allowed in the locations.
            3.  Click **Apply**.
        3.  To assign attribute values to locations:
            1.  Click **Assign Values to Locations**.
            2.  In the grid next to the location, click the attribute column, and enter a value.
            3.  Click **Apply**.
    5.  To reserve locations using a control number:
        1.  From the **Resource Type** drop-down list, select **Generate**.
        2.  From the **Control Number Description** drop-down list, select a control number.
    6.  To reserve a single location to which all inventory should be directed when moved into this zone.
        1.  From the **Resource Type** drop-down list, select **Location Assigned**.
        2.  In the **Reserve By Location** field, enter the location.
    7.  To allow all inventory to be deposited in any location in the zone (no restrictions), from the **Resource Type** drop-down list, select **Unrestricted**.
    8.  Click **Apply**.
6.  For a 3PL environment, to select the clients for which the application will record a history of LPN attributes when inventory is received:
    
    **Note**: The inventory history is a snapshot of the LPN and its attributes at the time it was received; the original record is not updated if changes are made after receiving. This information can be used for various quality, auditing, or recall purposes to determine what inventory was received, when it was received, and with what attributes it was received.
    
    1.  Click **Receive With Order**.
    2.  In the **Available** column, select the clients for which the application will track receiving history at the LPN level.
    3.  Click **Apply**.
7.  To limit the transport equipment that the application evaluates when searching for inventory needed to fill short orders:
    1.  Under **HOT ITEMS NEEDED IN SHIPPING**, click **Restrictions**.
    2.  Click **Add**.
    3.  Enter information in the following fields:
        
        | Field | Description |
        | --- | --- |
        | Attribute | Category for the criteria that you want the application to use. For example, to evaluate only transport equipment that contains inventory from a specific supplier, select **Supplier**. |
        | Value | Specific criteria that you want the application to use. The values that are available for selection depend on what is selected in the **Attribute** field. |
        
    4.  Click **Save**.
    5.  Click **Apply**.
8.  Click **Save**.

## Inbound Identification fields

 
| Field | Description |
| --- | --- |
| Unexpected Items | If Yes, users can receive an item that is not listed on a planned inbound order, as long as it is already defined in your warehouse. If this field is set to Yes, and the **Planned Inbound Order Required** field is also set to Yes, then during receiving, RF operators still need to specify the planned inbound order or shipment from which to receive.<br > If No, users can only receive an item if it is listed on a planned inbound order. |
| Receivable Inbound Order Statuses | Inbound order statuses against which inventory can be received. An inbound order (not planned) is a blanket order that contains item and quantity information for inbound inventory, but not information about how or when the inventory will be received into the facility. By default, users can receive against inbound orders with a status of Open. You can also select either or both of the following statuses to receive against.<br > **IMPORTANT**: It is recommended that you do not allow receiving against inbound orders that are closed or suspended.<br>-   • **Closed**: This status indicates that the inbound order has been closed to any further receiving.
<br>-   • **Suspended**: This status indicates that receiving against the inbound order has been temporarily stopped until the status is reset to Open. This status is typically used when problems are identified with previously received inventory, the carrier, or the receiving process for the item. |
| Inventory Status | If Yes, users are allowed to identify inventory in a status that is different from what is expected (listed on the planned inbound order line). If this field is set to Yes, and the **Unexpected Items** field is set to No, then the application will still allow an item with an unexpected inventory status to be identified.<br > If No, users are not allowed to identify inventory in a status that is different from what is expected (listed on the planned inbound order line). |
| Maximum Identical LPNs | Maximum number of identical LPNs (full pallets only) that a user is allowed to identify at one time. Allowing a user to identify multiple pallets of the same item at one time reduces the amount of data entry required. The user is prompted to provide a different LPN for each pallet, but only has to enter the attribute values once for the set of identical LPNs received. |
| RF LPN Confirmation | If Yes, when an operator creates new inventory, a prompt is displayed asking the operator if new inventory should be created. Select Yes if you want to notify operators that new inventory is going to be created, so that they have an opportunity to cancel the process if they entered an quantity in error.<br > If No, when an operator creates new inventory, the inventory is created without prompting operator for confirmation; the "Create Inventory?" message is not displayed. Select No if you want to save time by eliminating the prompt. |
| Enforce Expiration Date of Item Lot | If Yes, the application prevents users from changing the expiration date of an existing item lot whenever inventory is added, ordered, or changed. Inventory can be added to the application through receiving, ASN downloads, work orders, and quantity adjustments. Inventory can be requested through planned inbound orders and changed through inventory attribute adjustments. If this field is set to Yes, then during all of these processes, the application prevents users from changing the expiration date of an existing item lot. For example, if red paint Lot123 has an expiration date of January 1, 2018, then users are not allowed to add quantities of red paint Lot123 with a different expiration date. However, an item lot can still be modified, including its expiration date. You use the Item Lot page available in the Inventory module to configure item lots. See [Item Lots](../../../inventory/item-lots.md).<br > If No, the application allows users to change the expiration date of an existing item lot when adding, ordering, and changing inventory, as well as by using the Item Lot page. |
| Print Label After Identify | If Yes, the application prints a label automatically after the user identifies an LPN.<br > If No, the LPN labels are not automatically printed. |
| Planned Inbound Order Required | If Yes, operators are required to enter the planned inbound order from which to receive inventory when an inbound shipment contains multiple planned inbound orders. If an invalid planned inbound order is entered, the operator is not allowed to proceed with receiving.<br > If No, then operators are not required to enter a planned inbound order. When each item is scanned, the application searches for the item on existing planned inbound order lines and receives against the first line that contains the scanned inventory. When the first line is full, the application receives against the next planned inbound order line for the same item, until all lines for the item are fulfilled.<br>
**Notes**:

<br>

-   • If this field is set to No and the **Unexpected Items** field is set to Yes, then during receiving, if the application does not find a planned inbound order containing the item, the application creates a new order line under the last planned inbound order that was received. The new line would include the actual received quantity and have an expected quantity of zero. If an unexpected item is the first inventory received, the order line is added to the first planned inbound order line received from the inbound shipment.
<br>-   • If this field is set to No, and the **Unexpected Items** field is set to No, then during receiving, if the application does not find a planned inbound order line containing the item, the application displays a message and prevents the operator from receiving the item.
<br>

 |
| Receiving New Case Quantity | If Yes, operators can create new item footprints using an RF device while receiving, receiving without an order, or performing an inventory adjustment. This functionality allows operators to receive or adjust inventory with a case quantity (units per case) that is different from that which already is defined on existing footprints for the item. For example, if the only footprint for an item specifies there are 10 units in each case of inventory, but an operator scans a case of the item that has 15 units, then the operator can create a new footprint (specifying 15 units per case) in order to process the inventory.<br > If No, RF operators cannot create new item footprints, and therefore cannot receive inventory unless the units per case value is already defined on a footprint for the item being processed. |
| ASN Receiving | If Yes, operators are required to scan the expiration and manufactured dates when performing advanced shipment notification (ASN) receiving of date-controlled, single-item LPNs. If dates already exist, they are displayed on the Receive Date Control screen and the operator can either accept or change them. Select Yes, if you want the operator to capture the actual dates, which may differ from the dates passed down from the ASN.<br > If No, operators are not prompted to scan the dates. Instead, operators must perform a visual check to verify the expiration and manufactured dates when performing ASN receiving. |
| Items Tracked by Sub-LPN | If Yes, during ASN receiving of an item that is tracked by sub-LPN (case), the operator is required to scan each case individually. For example, assume an ASN for a pallet of case-tracked inventory is downloaded by the application. When the inventory arrives at the warehouse, an operator must scan each individual sub-LPN on the pallet; the entire LPN cannot be received at once. Each case that is scanned is moved to the operator's device and can be put away individually or processed for distribution, cross-docking, or pallet building. Select Yes if you want to confirm and track the receipt and processing of each individual case of sub-LPN tracked inventory received against an ASN.<br > If No, when an operator scans an LPN or sub-LPN from a pallet of case-tracked inventory during ASN receiving, the entire LPN (all cases) is processed by the application and can be put away as a single pallet.<br>

**Notes**:

<br>

-   • This configuration applies to ASNs received from both trusted and non-trusted suppliers.
<br>-   • If an item tracked by sub-LPN is also serialized, the operator must always scan each individual case, and confirm the serial number, regardless of this configuration.
<br>-   • Receiving detail-tracked (eaches) items by scanning the detail LPN is not supported.
<br>

 |
| Auto Receive Trusted ASNs | If Yes, then when receiving an ASN shipment from a trusted supplier, the user has the option to perform auto receiving. Auto receiving is a process in which the application immediately receives all of the LPNs on an inbound shipment and systematically moves them to a receiving staging lane. The physical move of the LPNs can take place before, during, or after auto-receive processing. An inbound shipment is eligible for auto receiving if it is associated with a detailed ASN (with LPN information), and the supplier on every planned inbound order is trusted and enabled for auto receiving. If any of the suppliers on the inbound shipment are not trusted or not enabled for auto receiving, then the application initiates LPN receiving, which requires the operator to scan each LPN on the inbound shipment.<br > For example, assume an inbound shipment associated with an ASN arrives at the warehouse. When the operator scans the shipment to receive, the application confirms whether all of the inbound orders are from trusted suppliers that are enabled for auto receiving. If so, the operator is prompted with the option to perform auto receiving; when auto-receive processing is done, the operator can complete the inbound shipment.<br > See [ASN auto receiving from trusted suppliers](../../../receiving/receiving-concepts.md).<br > **Note**: This field must be set to Yes in the Inbound Identification configurations and for each trusted supplier from which you want to auto receive.<br > If No, then auto receiving is disabled. If set to No in the Inbound Identification configurations, operators are required to scan each LPN on all inbound shipments, regardless of whether the supplier is trusted or enabled for auto receiving. |
| Case Sorting RF Screen | Name of the RF screen that is used when the operator has entered a non-existent case during the sorted case receiving process. Typically, operators can create inventory on this screen, based on information that is entered or bar codes that are scanned. |
| Mixed Items on LPN | If Yes, a prompt is not displayed when a user identifies inventory to an LPN that has already been used during identification and for which receiving has not been completed. The LPN, for example, has not been staged or put away. Select Yes if you do not want to alert a user, during receiving, that an LPN is already in progress.<br > If No, a prompt is displayed when a user identifies inventory to an existing LPN in progress. The prompt gives the user the following options:<br>-   • **Del**: Clear the last item scanned from the LPN in progress (Yes or No).
<br>-   • **Add**: Add the new inventory to the LPN in progress (Yes or No).
<br > If the inventory is not added to the LPN, the user must enter a new LPN for the inventory. |
| RF Repeat Handling Unit | If Yes, during inventory identification, if the operator has already entered a handling unit type or LPN attributes for an item, the operator is not prompted to confirm those details for additional quantities of the same item. If the values are defaulted, the operator can override the defaults, and is not prompted to identify the handling unit type or LPN attributes again until a new inbound shipment or different item is identified.<br > If No, during inventory identification or receiving, operators are prompted to confirm the handling unit type and LPN attributes for each LPN, including additional quantities of the same item. |
| RF Repeat Item | If Yes, during inventory identification, the item details entered when identifying an LPN are used as default values when identifying additional LPNs. However, if the operator chooses to perform a putaway (store identified inventory), then the default values are cleared. I fthe values are defaulted, the operator is still prompted to enter an LPN and item quantity, and can also change the auto-populated details if required.<br > If No, during inventory identification, item details are no populated by default form the previous LPN that was identified. Operators must enter item details for each LPN, regardless if they are repetitive values. |
| Auto Fill Attributes | If Yes, then when inventory is identified, attributes from the planned inbound order line are automatically displayed in the receiving fields on the user's device (RF or web client). For example, when an RF operator scans an item to receive, the application selects the first planned inbound order line (with capacity to receive) that matches the item, and then populates the attributes from the line to the receiving fields. The application continues to auto fill the attributes until the received quantity on the order line is equal to the expected quantity. If there is additional quantity of the same item to receive, the application searches for the next inbound order line that matches the item and auto fills the values based on the line attributes. If no additional order lines require the inventory and it is over-received, the receiving fields remain blank and the operator must manually enter the attribute values.<br>

**Notes**:

<br>

-   • The application does not auto fill values from order lines created from unexpected inventory, or sequenced lines that do not have attributes specified at the time of creation.
<br>-   • Auto filled attribute values may not always reflect the exact attributes of the inventory being received, and therefore, the operator is allowed to change the attributes.
<br>

<br > If No, then when inventory is identified, the application does not auto fill any receiving field values, and the user must enter them instead.<br>

**Notes**:

<br>

-   • If **Auto Fill Attributes** is set to Yes and customs is enabled, the consignment ID is auto filled but disabled. If No, the consignment ID is blank and editable, but the value entered must match the consignment ID for the order.
<br>-   • If a user is ASN receiving from a non-trusted supplier and the **Auto Fill Attributes** field is set to No, the receiving values are still populated from the ASN (instead of the order line) and must be verified by the operator. If **Auto Fill Attributes** is set to Yes in the same scenario, the attributes are populated from the order line instead of the ASN, and the operator must still verify the values.
<br>

 |
| Global Trade Item Number (GTIN) | If Yes, during inventory identification at a workstation, RF identify, RF receiving, and RF inventory adjustment functions, if a global trade item number (GTIN) is scanned as the item identifier, the UOM field is populated automatically with the UOM defined for the GTIN. However, the operator can override the populated information.<br > If No, operators have to manually select the correct UOM during identify, receiving, or inventory adjustments when a GTIN is scanned.<br > A GTIN is a type of alternate item number. See [Alternate items](../../inventory/items/items.md). |
| Default Receiving Location | Staging location to be used by default when receiving without transport equipment. A receiving location is required, for example, when inventory for an inbound shipment is unloaded from transport equipment and the equipment is dispatched prior to the inventory being received; or when inventory is received without an order (blind receiving). The receiving location is used to track the inbound shipment to a physical location in the warehouse. It provides a starting location for directed receiving work and for calculating putaway of the received inventory. The default value is displayed to the user during the receiving process whenever a receiving location is required; however, a user can override the default value. If a default receiving location is not configured, users are prompted to provide a location when they perform receiving activities that require a receiving location. |
| Receive Without Order | If Yes, then whenever inventory is received without an order, the application creates a history record to track the LPN attributes at the time the inventory was received. The information recorded by the application is a snapshot of the inventory, meaning that the original record is never updated, even if attribute changes are made to the inventory post-receiving. This information can be used for various quality, auditing, or recall purposes to determine what inventory was received, when it was received, and with what attributes it was received.<br > If No, the application does not create a history record for inventory received without an order. |
| Receive With Order | If Yes, then whenever inventory is received with an order, the application creates a history record to track the LPN attributes at the time the inventory was received. The information recorded by the application is a snapshot of the inventory, meaning that the original record is never updated, even if attribute changes are made to the inventory post-receiving. For example, if an LPN was received and a tracking record was created by the application, and if that same LPN was later reverse-received, then the original record would not be updated, but rather the application creates a new line for the record with a negative quantity. This information can be used for various quality, auditing, or recall purposes to determine what inventory was received, when it was received, and with what attributes it was received.<br > **Note**: This field is only available in a non-3PL environment. In a 3PL environment, you must define the clients for which inventory history is tracked when receiving with an order.<br > If No, the application does not create a history record for inventory received with an order. |
| Equipment with Hot Items | Select the type of transport equipment that the application should search when attempting to find inventory to fulfill an outbound order that was allocated short. The needed inventory is referred to as "hot items."<br > If you select Receiving Equipment and Storage Equipment, the application searches receiving transport equipment first before searching storage transport equipment. |
| Validate SSCC LPN | If Yes, the application validates the serial shipping container code (SSCC) LPN assigned to a pallet to ensure that the LPN complies with the GS1 system of standards for SSCC pallet identification.<br > If this field is set to Yes, the **SSCC Validation Skip Prefix** field becomes available so that you can also specify a prefix that, if found in an SSCC identifier, excludes that identifier from compliance validation. If an LPN is excluded from compliance validation, the application still validates that number to ensure that it meets the minimum and maximum values for length based on the values defined in the LPN **Minimum Length** and **Maximum Length** fields.<br > If enabled, SSCC pallet validation takes place during inventory identification, inventory adjustments, partial LPN transfers, deposits to a new LPN, pallet relabelling, pallet building, picking work assignments, and during loading or fluid loading of carton picks. SSCC validation does not take place during carton picking, when creating a permanent LPN, or if handling unit tracking is enabled.<br > If No, the application does not validate SSCC LPNs when they are created. |
| SSCC Validation Skip Prefix | Prefix found in the LPNs that you do not want to be validated for compliance. The LPNs that are created with this prefix will still be validated for length based on the values defined in the **LPNs Min Length** and **LPNs Max Length** fields.<br > Only available if the **Validate SSCC LPN** field is set to Yes. |
| Defer Inventory Receipts | If Yes, then when inventory is received, the application defers sending the Inventory Receipts transaction to the host. The transaction is instead saved to a deferred execution database table until it is purged. For example, some facilities may defer inventory receipt transactions when inventory is received from expected receipts to a movement zone.<br > If No, then the Inventory Receipts transaction is immediately sent to the host after inventory is received. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
