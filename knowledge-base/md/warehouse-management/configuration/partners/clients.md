---
title: "Clients"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/clients.htm"
source: "/content/clients.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Partners"
  - "Clients"
sections:
  - "Client-specific configurations"
  - "Add or modify a client"
  - "Add or modify a client group"
  - "Delete a client or client group"
  - "Client fields"
  - "Address fields"
  - "Edit Address fields"
  - "General fields"
  - "Receiving Contact fields"
  - "Shipping Contact fields"
images:
  - "/content/resources/images/image632381.png"
source_sha1: 3a9a7f60ba068f22d97f24025641629a1855b089
---
# Clients

A client is a company for which your warehouse provides logistics-related services, such as receiving, storing, and shipping inventory.

As a 3PL provider, you may have one or more clients, each of which may have one or more customers. Every client that you want to track in the warehouse must be defined and enabled in the application.

The application supports the following 3PL processes:

-   Tracking inventory by client at all times
-   Associating received inventory with a client during inventory identification
-   Client-specific inventory reporting
-   Client-specific order allocation and shipping
-   Defining multiple clients and item clients on outbound orders, work orders, bills of materials, and planned inbound orders
-   Communication with multiple host applications

Optionally, you can assign clients to client groups. A client group is a method of grouping clients that have the same warehousing requirements. It is useful to define client groups for the purpose of searching and reporting, and for use in client-specific configurations.

## Client-specific configurations

The application supports the following client-specific configurations, which can be configured by client:

-   **Campus reporting**: Associating a client with one or more warehouses, including a translated warehouse.
-   **Client ownership**: Associating a client with planned inbound orders, outbound orders, shipments, items, customers, and suppliers.
-   **Configurable workflows**: Associating a client with different inbound and outbound workflows.
-   **Cycle counting**: Generating cycle counts and ABC counts by client, along with other count attributes, giving the 3PL provider flexible count scheduling capability.
-   **Inventory adjustment thresholds**: Specifying the inventory adjustment thresholds by client and client group to indicate the limits at and above which inventory adjustments require approval by a designated supervisor (user or role).
-   **Inventory/item configurations**: Associating an item with a client to track and manage inventory.
-   **Multi-building support**: Consolidating outbound orders across buildings for multiple client shipments.
-   **Multi-client host interface**: Communicating with client-specific host applications, as well as multiple formats for the same transaction, allowing clients to send data in their preferred format.
-   **Order processing**: Specifying a client’s item on an outbound order and releasing outbound orders on a client basis.
-   **Over-receipt**: Specifying over-receiving thresholds by client, and defining how the over-receipt should be calculated, such as by percentage, unit quantity, or cost value.
-   **Reason codes**: Specifying different sets of reason codes by client for inventory adjustments, order updates, and other processes that users perform.
-   **Receiving**: Specifying a client and item client during product identification. Multiple item clients can be designated on a single inbound order with or without advance shipment notification (ASN) detail information.
-   **Replenishments**: Selecting pick zones based on the associated client during replenishment stock allocation.
-   **Reports**: Displaying report data by client for inbound orders, outbound orders, shipments, and items.
-   **Security**: Limited access to data, so that a client can access their own data, but not data belonging to other clients.
-   **Shipping paperwork**: Printing client-specific external documents, such as bills of lading, packing slips, and shipping labels.
-   **Storage**: Configuring storage locations for one or more clients and defining the maximum number of LPNs of a client’s items that can be stored in any one aisle.
-   **User configurations**: Associating clients and client groups with users to limit the user to the information and activities associated with a specific client or group of clients.
-   **User-defined inventory attributes**: Configurable inventory attributes can be enabled for visibility in a 3PL environment.
-   **User interface**: Configurable status bar to display the client.
-   **Variable configurations**: Maintaining different variable configurations (such as for a field, button, window, or page) based on client or client group.
-   **Work management**: Controlling how the workforce is deployed to handle warehouse tasks across a multi-client warehouse implementation.
-   **Work order processing**: Specifying one or more clients or item clients on the BOM for both finished goods and component items or on the work order.

## Add or modify a client

1.  Select **Configuration > Partners > Clients**.
2.  Above the grid, select **Clients**.
3.  Perform one of the following tasks:
    -   To add a client, click **Add**.
    -   To modify a client, in the grid, click the client.
4.  Enter the information in the [Client fields](#Client_fields).

1.  To maintain the address information:

**Note**: To change the address of a copied entity without updating the original entity, you must use the lookup feature to add or copy an address before editing and selecting it.

1.  In the **Address** field, click ![Lookup](../../../../images/resources/images/image632381.png) . The Address Lookup window is displayed.
2.  Perform one of the following tasks:
    -   To add a new address, click **Add**.
    -   To modify an address, in the grid, click the address.
    
    **IMPORTANT**: Any modification to an address is reflected in historical data. For example, if you modify an address assigned to a customer, then the ship-to address on orders previously sent to that customer reflects the new address. Therefore, if you want to maintain the integrity of the existing data, create a new address or copy and edit the address, and then associate that address with the entity so that from that point on the new address is used and the historical data is not affected.
    
    -   To copy an address, in the grid, select the check box next to the address, and then click **Copy**.
3.  Enter information in the [Address fields](#Address_fields), and then click **Save**.
4.  To define additional address and contact information for receiving or shipping operations:
    1.  Click **Edit**.
    2.  Enter information in the [Edit Address fields](#Edit_address_fields).
    3.  Click **Save**.

1.  To add the client to a client group:
    1.  Click **Client Groups**.
    2.  In the **Available** column, select the check box next to the client groups that apply.
    3.  Click **Apply**.
2.  Click **Save**.

## Add or modify a client group

1.  Select **Configuration > Partners > Clients**.
2.  Select **Groups**. The grid displays the existing client groups.
3.  Perform one of the following tasks:
    -   To add a group, click **Add**.
    -   To modify a group, in the grid, click the group.
4.  In the **Name** and **Description** fields, enter the values for the client group.
5.  In the **Available Clients** column, select the check box next to the clients that belong in the group.
6.  Click **Save**.

## Delete a client or client group

1.  Select **Configuration > Partners > Clients**. The Clients page is displayed.
2.  Perform one of the following tasks:
    -   To delete a client, select **Clients**. The grid displays the existing clients.
    -   To delete a client group, select **Groups**. The grid displays the existing client groups.
3.  In the grid, select the check box next to the client or group to delete.
4.  Click **Delete**. A confirmation message is displayed.
5.  Click **OK**.

## Client fields

 
| Field | Description |
| --- | --- |
| Name | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. |
| Address | Address information. An address name represents the location and contact information of an entity (such as a carrier, client, customer, or supplier). The information fields support the entry of an address name, first and last name, address lines, a city, a state or province, a postal code, and a country. |
| Lot Format | Identifier for a lot format. If you specify a lot format for the client, then whenever a lot is entered for the client's inventory, the application validates the lot using the pattern and validation command specified for the lot format. Also, if a production or expiration date is embedded in the lot number, the application retrieves the date using the date parsing command specified in the lot format. If a lot format is specified for the item that is being received, then the item lot format is used instead of the client lot format. |
| Enabled | If Yes, the client is available for use and is visible in the current warehouse.<br > If No, the client is not available for use or selection in the current warehouse. You can configure a client without enabling it; however, to view the client in the current warehouse, you must set the **Enabled** field to Yes. |
| Auto Populated Supplier Lot Number | If Yes, then for the client's supplier-lot-tracked items, the supplier lot number is automatically populated during inventory identification. For example, when supplier lot tracked inventory is received into the warehouse for the client, the supplier lot number is populated from the ASN, the inbound order line, or item configuration.<br > If No, the supplier lot number is not automatically populated during identification of the client's inventory. |
| Allow Supplier Lot Change | If Yes, then for the client's supplier-lot-tracked items, the operator can change the supplier lot during inventory identification. For example, when supplier-lot-tracked inventory is received into the warehouse for the client, an operator can update the supplier lot number.<br > If No, an operator is not allowed to change the supplier lot number on the client's inventory during identification. |
| Prevent Packing | If Yes, an operator is not allowed to start packing until all of the inventory for a shipment has been deposited to the pack location. This setting only takes effect for pack locations that are reserved by shipment. That is, the pack location belongs to a movement zone that has a resource type of Derived and an attribute of Shipment ID. See [Processing Location Reservation](../inventory/movement/processing-location-reservation.md).<br > Select Yes if you want the application to prevent the operator from starting to pack a shipment before all of the inventory for the shipment has arrived at the pack location, not including inventory that is not destined for a pack location. If set to Yes, the pack initiation page displays a status for each location in the workstation's processing zone that is reserved by shipment. The status indicates whether packing can begin, and the grid provides visibility to the picking containers in the location.<br > If No, the application allows the operator to start packing even if all of the inventory for a shipment has not arrived. |
| Capture Serialized Inventory | If Yes, then when packing serialized items, the packer is required to enter (or scan) each item and then the serial number for that item. The packer is not allowed to enter multiple serial numbers or a range of serial numbers for an item quantity greater than 1.<br > If No, the packer is allowed to scan an item and then, for an item quantity greater than 1, enter multiple serial numbers or a range of serial numbers. |
| Translated Warehouse | Name of a warehouse to and from which host transactions should take place for this client. Use of a translated warehouse is optional, and only applies in a multi-warehouse environment.<br > You specify a translated warehouse, for example, if your host requires communications to take place to and from a single warehouse for the client. See [Translated warehouse](../warehouse/warehouses.md). |
| Date Window | Amount of time in relation to the inventory’s received date or expiration date during which inventory is considered the same age for allocation when one of the FEFO/FIFO/LEFO/LIFO or absolute FEFO/FIFO/LEFO/LIFO inventory rotation methods is required. |
| Inventory Rotation Method | Value that represents the order in which the allocation process selects available inventory for allocation. Select an inventory rotation method if you want the application to search for inventory based on date processing or location.<br>-   • **FEFO-ORDER-BY and FEFO-ORDER-BY-ABSOLUTE**: First-expiration, first-out. The first inventory to expire will be selected first.
<br>-   • **FIFO-ORDER-BY and FIFO-ORDER-BY-ABSOLUTE**: First-in, first-out. The oldest inventory will be selected first.
<br>-   • **LEFO-ORDER-BY and LEFO-ORDER-BY-ABSOLUTE**: Last-expiration, first-out. The last inventory to expire will be selected first.
<br>-   • **LIFO-ORDER-BY and LIFO-ORDER-BY-ABSOLUTE**: Last-in, first-out. The newest inventory will be selected first.
<br>-   • **LOCATION-ORDER-BY**: Locations are ordered within a pick zone (maintaining the allocation search path order) by the location attributes specified for the **Location Sort** field in inventory selection settings.
<br>-   •
    
    **No selection (blank)**: The application uses the inventory rotation method of the highest defined level of precedence. For information on precedence, see [Inventory rotation allocation processing](../outbound/allocation/inventory-rotation-allocation.md).
    
    <br>
    
    **Note**: Inventory rotation methods defined at a lower precedence (except the default method) are automatically copied to the order line or work order line when the line is created. For example, if an order line is created for a date-tracked item with a rotation method defined, the rotation method is copied from the item to the order line, and then the application uses the order line rotation method during allocation.
    
    <br > If no inventory rotation method is defined at any level, then the application uses the allocation search path sequence and allocates the first available inventory it finds that matches all of the required attributes.
<br > When using inventory rotation methods that are not absolute, the application searches for inventory by allocation search path in sequence until it finds a pick zone that contains the inventory, and then allocates inventory that is closest to the preferred processing date. Therefore, the application stops searching at the first pick zone in which matching inventory is found.<br > When using absolute inventory rotation methods, the application searches either all of the allocation search paths for inventory that is closest to the preferred processing date or, if absolute groups are defined, each absolute group in sequence until it finds matching inventory and then allocates inventory that is closest to the preferred processing date from the pick zones within the absolute group. Therefore, the absolute method allows for more a comprehensive search to find the inventory. |
| Delivery Sequence Loading Order | Determines whether inventory should be loaded in ascending or descending order of the delivery numbers and delivery sequence defined for the orders in a stop. For example, assume a stop includes four orders, two with a delivery number of A1 and two with a delivery number of B1. Also assume that the orders for both A1 and B1 have a delivery sequence of 1 and 2. If this field is set to Descending, then the orders are loaded in the following sequence: B1 2, B1 1, A1 2, A1 1. See [Delivery sequence loading](../../outbound-planner/outbound-planning-concepts.md).<br > **Note**: The delivery sequence loading order defined for a shipment overrides the client value, which overrides the warehouse value. However, if there is no selection (blank) in the Delivery Sequence Loading Order field on a shipment, the value is inherited from the outbound loading settings or, in a 3PL environment, the client configuration.<br>-   • **Ascending**: Operators are directed to load orders from the lowest to the highest value of the delivery number and delivery sequence defined on the orders (for example, 0 to 9 or A to Z).
<br>-   • **Descending**: Operators are directed to load orders from the highest to the lowest value of the delivery number and delivery sequence defined on the orders (for example, 9 to 0 or Z to A).
<br>-   • **Disabled**: The application does not enforce sequence loading, and orders can be loaded in any sequence.
<br > **Note**: To ensure proper loading, all shipments within a stop should have the same delivery sequence loading order. |
| Minimum Extreme Tolerance (%) | Percentage of catch quantity below an item's defined minimum catch quantity that is deemed to be within tolerance. The application calculates catch quantity limits based on an item's configuration, but this value overrides the minimum tolerance and allows you to accept a lower value that would otherwise not be acceptable. For example, if an item's minimum catch quantity is 100, but the extreme minimum tolerance for a warehouse is 15 (15%), then whenever the warehouse captures catch quantity for the item, the application accepts a minimum value of 85.<br > **Note**: In a 3PL environment, the client configuration for this field overrides the warehouse level configuration. |
| Maximum Extreme Tolerance (%) | Percentage of catch quantity above an item's defined maximum catch quantity that is deemed to be within tolerance. The application calculates catch quantity limits based on an item's configuration, but this value overrides the maximum tolerance and allows you to accept a higher value that would otherwise not be acceptable. For example, if an item's maximum catch quantity is 100, but the extreme maximum tolerance for a warehouse is 15 (15%), then whenever the warehouse captures catch quantity for the item, the application accepts a maximum value of 115.<br > **Note**: In a 3PL environment, the client configuration for this field overrides the warehouse level configuration. |
| Suppress Out of Tolerance Prompt | If Yes, the application does not prompt the operator to recapture the catch quantity when the catch quantity of inventory is beyond its normal tolerance limits and within the extreme tolerance limits for the client. The application accepts the entered catch quantity for the inventory. For example, if an item's maximum catch quantity is 100, but the extreme maximum tolerance for the warehouse is 15 (15%), then whenever the application captures catch quantity for the item and warehouse within a value of 115, the application does not prompt the RF operator to recapture the catch quantity.<br > If No, the application prompts the operator to recapture the catch quantity when the catch quantity of inventory is beyond its normal tolerance limits and within the extreme tolerance limits for the client.<br > If the captured catch quantity is beyond the minimum or maximum extreme tolerance limit, the application does not allow the operator to proceed further and prompts the operator to recapture the catch quantity irrespective of the value of **Suppress Out of Tolerance Prompt**.<br > **Note**: In a 3PL environment, the client configuration for this field overrides the warehouse level configuration. |
| Require Sub-LPN Capture | If Yes, the operator is required to capture the catch quantity of each sub-LPN during shipping (while picking or before loading). If you set this field to Yes, the point at which the operator captures the sub-LPN catch quantity depends on whether delayed capture is enabled (**Delay Capture Until Loading** field).<br > **Note**: If a work assignment is picked to a sub-LPN, the individual case information (including catch quantity) is no longer retained. Therefore, the application does not prompt for sub-LPN capture if a work assignment is picked to a sub-LPN, even if this field is set to Yes. See [Work assignments picked to sub-LPNs](../outbound/picking/work-assignments.md).<br > If No, the operator is not required to capture the catch quantity of each sub-LPN during shipping; however, LPN catch quantity may still be required.<br > **Note**: In a 3PL environment, the client configuration for this field overrides the warehouse level configuration. |
| Delay Capture Until Loading | If Yes, the application does not prompt the operator to capture catch quantity at picking. Instead, the application requires the operator to capture catch quantity before loading. The application does not allow an operator to load inventory if the catch quantity is required but has not been captured. If you set this field to Yes, an operator can capture the catch quantity for an LPN or sub-LPN using directed or undirected work, depending on the following configurations:<br>-   • If the **Require Sub-LPN Capture** field is Yes, and if catch-tracked inventory is deposited to a location type with the **Create Sub-LPN Catch Work on Deposit** field set to Yes, then the application creates directed work for the capture. If the inventory is not deposited to a location type enabled for creating directed capture work, then an operator must capture catch quantity using the undirected RF menu option.
<br>-   • If the **Require Sub-LPN Capture** field is No, then the option to create directed capture work upon deposit is disabled, and an operator must capture the capture catch quantity using the undirected RF menu option before loading.
<br > If No, the application prompts the operator to capture the catch quantity of inventory when picking a full or partial pallet.<br > **Note**: In a 3PL environment, the client configuration for this field overrides the warehouse level configuration. |
| Allow Cancel Capture | If Yes, then when prompted to capture the catch quantity of inventory either during picking or before loading, the operator can cancel the capture request. If an operator cancels the catch quantity capture for an LPN or for a sub-LPN on an LPN, then the application will not prompt for a capture of the LPN again.<br > If No, then the operator is required to capture the catch quantity of inventory when prompted by the application; the operator cannot cancel the prompt.<br > **Note**: In a 3PL environment, the client configuration for this field overrides the warehouse level configuration. |
| Require Out of Tolerance Approval | If Yes, the application requires an approval, such as from a supervisor, for inventory that is outside of its normal tolerance but within the defined extreme tolerance limits. Inventory that is outside its normal tolerance but within the extreme limits is displayed with the **Tolerance** tag and must be approved (or adjusted) before it can be loaded and shipped. The application calculates catch quantity limits based on an item's configuration, and the values specified in **Minimum Extreme Tolerance (%)** or **Maximum Extreme Tolerance (%)**. For example, if the minimum tolerance limit is 100, the minimum extreme tolerance limit is 85, and the captured catch quantity is 90, the application tags inventory as out of tolerance and prompts for a supervisor approval.<br > If No, the application does not require an approval to ship inventory even if the catch quantity is outside the normal tolerance limits but within the configured extreme tolerance limits.<br > **Note**: In a 3PL environment, the client configuration for this field overrides the warehouse level configuration. |
| Full Validation Of Inbound Transactions | If Yes, then for the client, the system fully validates each inbound transaction in its entirety, regardless of whether the transaction includes errors. When full validation is enabled, if the system processes a transaction with one or more errors, it records each error until the entire transaction is validated.<br > If No, then when an error is encountered during inbound transaction processing for the client, the system stops validating the transaction. When full validation is disabled, a transaction may need to be processed multiple times if there are multiple errors.<br>
**Notes**:

<br>

-   • Full validation is only performed on certain inbound transactions that impact the ability to ship and receive inventory.
<br>-   • Full validation can eliminate the need to process a transaction multiple times if there are multiple errors since all of the errors can be immediately identified. However, full validation may increase processing time.
<br>-   • The **Full Validation Of Inbound Transactions** field value set at the client level overrides the field value set at the warehouse level.
<br>

 |

## Address fields

 
| Field | Description |
| --- | --- |
| Address Name | Identifier for address information. The address name typically identifies the individual or organization with which an address is associated. You can enter an existing address, or look up and select, add, or edit an address. |
| Client ID | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. |
| Locale ID | Unique identifier for the locale. A locale defines a set of culture-specific components, such as language, time and date formats, currency formats, and a measurement unit system. |
| Address Line 1 | Line one for the address. This is the physical address information (such as house, building or PO box numbers, street names, or suite or floor numbers). |
| Address Line 2 | Line two for the address. |
| City | City for the address. |
| Postal Code | Postal code associated with the ship-to address of the shipment. |
| Country | Country for the ship-to customer specified on the order. |
| State/Province | State or province for the address. |
| Time Zone | Time zone for the address. |

## Edit Address fields

### General fields

 
| Field | Description |
| --- | --- |
| First Name | First name of the individual. For a carrier, client, or customer, this is the person to whom correspondence should be directed. |
| Last Name | Last name of the individual. For a carrier, client, or customer, this is the person to whom correspondence should be directed. |
| Host External ID | Alternate identifier for the route-to address information. This identifier is typically sent from the host, and it is used to reconcile address information with the information contained in the host application. |
| Address Line 1 | Line one for the address. This is the physical address information (such as house, building or PO box numbers, street names, or suite or floor numbers). |
| Address Line 2 | Line two for the address. |
| Address Line 3 | Line three for the address. |
| City | City for the address. |
| State/Province | State or province for the address. |
| Postal Code | Postal code for the address. |
| Country Name | Name or code name of the country. |
| Honorific | Title, such as Mr., Mrs., or Dr., of the individual. For a carrier, client, or customer, this is the person to whom correspondence should be directed. |
| Address District | Postal district for the address. This information is typically used outside of the United States. |
| Residential Address | Indicates that the address information represents a residence. |
| Temporary | Indicates whether the address is temporary. |
| Pool Point | Indicates whether load consolidation and distribution is performed at the address. Available only when Transportation Manager is installed. |
| Pool Rating Service Name | Identifier of the rating service that is used for the pool point. Available only when Transportation Manager is installed and the **Pool Point** check box is selected. |
| P.O. Box Address | Indicates whether the address is a post office box. If deselected, indicates that the address is not a post office box but is a physical address. |
| Region | Geographical region within the country for the address. |
| Latitude | Line of latitude for the address's location. Enter the latitude in decimal format (for example, 40.269 or -75.317). |
| Longitude | Line of longitude for the address's location. Enter the longitude in decimal format (for example, 40.269 or-75.317). |
| Time Zone | Time zone for the address. |

### Receiving Contact fields

 
| Field | Description |
| --- | --- |
| Receiving Phone | Telephone number for the address corresponding to its receiving operations and inbound freight. |
| Receiving Fax | Fax number for this address corresponding to its receiving operations and inbound freight. |
| Receiving Web Address | URL for the internet site of the individual or organization associated with the address corresponding to its receiving operations and inbound freight. |
| Receiving Email | Address at which the individual or organization associated with this address receives email corresponding to its receiving operations and inbound freight. Example: [\[email protected\]](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/cdn-cgi/l/email-protection). |
| Receiving Contact Name | Name of the person who may be contacted with questions or concerns regarding receiving operations and inbound freight. |
| Receiving Contact Title | Title of the person who may be contacted with questions or concerns regarding receiving operations and inbound freight. |
| Receiving Contact Phone | Phone number of the person who may be contacted with questions or concerns regarding receiving operations and inbound freight. |
| Receiving Attention Name | Name that should be used in the correspondence sent to this address regarding receiving operations and inbound freight. |
| Receiving Attention Phone | Phone number of the person for whom correspondence is sent to this address regarding receiving operations and inbound freight. |

### Shipping Contact fields

 
| Field | Description |
| --- | --- |
| Shipping Phone | Telephone number for the address corresponding to its shipping operations and outbound freight. |
| Shipping Fax | Fax number for this address corresponding to its shipping operations and outbound freight. |
| Shipping Web Address | URL for the internet site for this address corresponding to its shipping operations and outbound freight. |
| Shipping Email | Address at which the individual or organization associated with this address receives email corresponding to its shipping operations and outbound freight. Example: [\[email protected\]](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/cdn-cgi/l/email-protection). |
| Shipping Contact Name | Name of the person who may be contacted with questions or concerns regarding shipping operations and outbound freight. |
| Shipping Contact Title | Title of the person who may be contacted with questions or concerns regarding shipping operations and outbound freight. |
| Shipping Contact Phone | Phone number of the person who may be contacted with questions or concerns regarding shipping operations and outbound freight. |
| Shipping Attention Name | Name that should be used in the correspondence sent to the address regarding shipping operations and outbound freight. |
| Shipping Attention Phone | Phone number of the person for whom correspondence is sent to the address regarding shipping operations and outbound freight. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
