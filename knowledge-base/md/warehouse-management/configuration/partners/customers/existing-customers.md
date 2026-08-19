---
title: "Existing Customers"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/existing_customers.htm"
source: "/content/existing_customers.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Partners"
  - "Customers"
  - "Existing Customers"
sections:
  - "Shelf-life processing"
  - "Freshness date processing"
  - "Customer distribution processing"
  - "Add or modify a customer"
  - "Delete a customer"
  - "Customer fields"
  - "Address fields"
  - "Edit Address fields"
  - "General fields"
  - "Receiving Contact fields"
  - "Shipping Contact fields"
  - "Customer Item fields"
  - "Customer Shipping fields"
  - "Distribution Settings fields"
  - "Rule fields"
images:
  - "/content/resources/images/image632381.png"
  - "/content/resources/images/image430894.png"
source_sha1: 3a5211113a53cd4e621de770a95997760422c9dc
---
# Existing Customers

A customer is a business to whom you ship inventory. Each customer has a profile that is used to define how their inventory is handled, how their orders are processed, and how their inventory is shipped. The profile includes the following information:

-   Address information
-   Order handling requirements for partial orders, split cases, and consolidation
-   Outbound handling requirements for inventory, date-controlled inventory, packaging, cartonization, transportation, and carriers
-   Item configurations that define the order processing requirements for specific items
-   Distribution processing requirements that define the type of store, delivery addresses, staging locations, and storage rules for distribution orders

The attributes that are defined for a customer are defaulted into the respective fields on an order and order line if the values on the order line are not already populated when it is created. If any customer information on the order and order line is still missing after being populated by the customer values, the application uses the values specified for the customer type to populate the missing information.

You must define a customer profile for every customer for whom you plan to ship inventory.

## Shelf-life processing

Shelf-life processing supports the ability to fill orders for date-tracked items with inventory that is at least a specified number of days away from its expiration date. If a shelf life is defined for an item, the application assigns a default expiration date at the time of receipt (based on manufactured date and the shelf life), but it will not automatically change the status of inventory as it ages. Generally, you would specify a shelf life for an item if you want to retain the status assigned to inventory at the time it is received, even if it ages beyond that status. When a value for shelf-life is defined, allocation limits the list of available pickable inventory to that which exceeds the minimum shelf-life.

In addition to assigning a shelf life to date-tracked items, you can define a value for the minimum shelf life allowed for an order line, a customer, and customer type. If a value is not provided on the order line, the application uses the value defined for the customer, and finally the customer type.

The value for minimum shelf life is evaluated at the time of allocation. Therefore, it is important to take into consideration the amount of time in advance of shipping at which allocation occurs. For example, a customer may order items that take approximately six days to reach a retail location. To ensure that the product can be sold for at least four days, the customer may request that only inventory that has at least 10 days (240 hours) to reach its expiration date be allocated to fill their orders.

## Freshness date processing

Freshness date processing can be implemented with date-tracked items to ensure that future shipments of an item to a specific customer are always delivered with inventory that is fresher than earlier shipments of that same item.

An item's freshness date is considered to be the oldest expiration date associated with the most recent shipment of the item.

Freshness date processing can be specified for a customer and customer type. In addition, you can view the oldest expiration date for each date-tracked item that is shipped to a customer.

When freshness date processing is specified on an order for a specific item, then the application captures the oldest expiration date for that inventory when it is shipped, and allocates only inventory with later expiration dates to satisfy future orders.

## Customer distribution processing

A distribution is a pre-allocation of a planned inbound order to a single customer. Multiple distributions can be associated with a planned inbound order to distribute the expected inventory to multiple customers. See [Distribution](../../outbound/distribution.md).

The customer to whom distribution inventory is shipped typically represents a store, such as a chain store or department store. After these customers are created, you can define the scheduled times (routes) at which inventory is picked up for delivery to the customer. If routes are defined, then when you allocate distribution inventory for a customer, the application automatically creates the loads and stops for the resulting shipments. See [Outbound Routes](../../outbound/distribution/outbound-routes.md).

When you define a customer for the purpose of distribution processing, you must configure the following components:

-   **Ship staging locations**: Shipment staging locations in which picked distribution inventory is staged prior to being shipped to the customer.
-   **Customer-preferred storage locations**: Locations to which unallocated inventory is consolidated and stored until the distribution quantity is allocated. As inventory is moved into preferred storage locations that are configured for manual consolidation, an operator can manually consolidate sub-LPN and detail-LPN inventory onto pallets. For example, in a location configured for sub-LPNs, users can manually build cases into a pallet and then manually transfer the pallet a location configured for LPNs. Then when the distribution is allocated, the operator can be directed to transfer an entire load to the customer's ship staging location instead of having to do multiple case or each transfers. These storage locations can be used by one or more customers. Distribution inventory that is placed in a storage location can be shipped at different times and on different transport equipment, it does not have to be planned to one shipment as is the case with distribution locations.
    
    When you configure storage locations for distribution inventory, you define the rules and criteria that determine which inventory is directed to the locations. For example, you can configure that only inventory for a specific customer, customer category or group, or processing priority is deposited to a particular location.
    

## Add or modify a customer

1.  Select **Configuration > Partners > Customers > Existing Customers.**
2.  Perform one of the following tasks:
    -   To add a customer, click **Add.**
    -   To modify a customer, in the grid, click the customer.
    -   To copy a customer, in the grid, select the check box next to the customer, and then click **Copy**.
3.  Enter information in the [Customer fields](#Customer_fields), and then click **Save**.

1.  To maintain the address information:

**Note**: To change the address of a copied entity without updating the original entity, you must use the lookup feature to add or copy an address before editing and selecting it.

1.  In the **Address** field, click ![Lookup](../../../../../images/resources/images/image632381.png) . The Address Lookup window is displayed.
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

1.  To add or modify special item configurations:
    1.  Under **CUSTOMER ITEMS**, click **Items**.
    2.  Perform one of the following tasks:
        -   To add an item, click **Add**.
        -   To modify an item, in the grid, click the item.
        -   To copy an item, in the grid, select the check box next to the item, and then click **Copy**.
    3.  Enter information in the [Customer Item fields](#Customer_Item_fields).
    4.  Click **Save**, and then click ![Previous page](../../../../../images/resources/images/image430894.png).
2.  To define shipping preferences for a customer:
    1.  Under **OUTBOUND HANDLING,** click **Shipping**.
    2.  Enter information in the [Customer Shipping fields](#Customer_Shipping_fields).
    3.  To configure handling units for a customer:
        1.  Under **HANDLING UNIT TYPES**, click **Handling Units**. The grid displays the handling units types that are enabled for the customer.
        2.  To add a handling unit type:
            1.  Click **Add**.
            2.  From the **Handling Unit Type** drop-down list, select a handling unit type.
            3.  Select the UOM that the customer requires to be shipped on the selected handling unit type.
            4.  Click **Apply**.
        3.  To delete a handling unit type:
            1.  In the grid, select the check box next to the handling unit type.
            2.  Click **Delete**. A confirmation message is displayed.
            3.  Click **OK** and then click **Apply**.
    4.  To select the repack classes for a customer:
        1.  Under **CARTONIZATION**, click **Repack Classes**.
        2.  In the **Available** column, select the check box for the repack classes to assign.
            
            **Note**: Repack classes are defined in the outbound picking cartonization configuration. See [Configure pick cartonization](../../outbound/picking/pick-cartonization.md).
            
        3.  Click **Save**.
    5.  If carriers are enabled, then to enter carrier account information:
        1.  Under **CARRIERS**, click **Carrier Accounts**.
        2.  In the **Available** column, select the carriers with whom the customer has accounts.
        3.  In the **Selected** column, enter the account number for each selected carrier.
        4.  Click **Apply**.
3.  If the customer is a store location used for distribution orders, under **DISTRIBUTION**, define the distribution settings:
    
    **Note**: To configure other attributes of distribution processing, see [Distribution](../../outbound/distribution.md).
    
    1.  To add or delete a customer category or customer group:
        1.  Under the field, click **Maintain**.
        2.  To add a row, click **Add**, enter the values, and then click **Save**.
        3.  To delete a row, in the grid, select the check box next to the row to delete, click **Delete**, and then click **OK**.
    2.  Under **DISTRIBUTION**, click **Distribution Settings**. The Distribution Settings page is displayed.
        
        **Note**: In a multi-warehouse environment, distribution settings are warehouse specific; they only apply to the current warehouse.
        
    3.  Enter information in the [Distribution Settings fields](#Distribution_Settings_fields).
    4.  To select and sort the customer's ship staging locations for outbound distribution inventory:
        1.  Click **Shipment Staging Locations**.
        2.  In the **Available** column, select the staging locations that apply.
        3.  To change the sequence in which the locations are used, in the **Selected** column, drag the location to the position you want.
        4.  Click **Apply**.
    5.  To select the locations in which unallocated distribution inventory is stored:
        1.  Click **Distribute to Storage Rules**.
        2.  Perform one of the following tasks:
            -   To add a storage rule, click **Add**.
            -   To modify a storage rule, in the grid, click the location.
            -   To copy a storage rule, in the grid, select the check box next to the sequence, and then click **Copy**.
        3.  Enter information in the [Rule fields](#Rule_fields).
        4.  Define the criteria used to determine which inventory is directed to the location for storage:
            1.  Under **CRITERIA**, perform one of the following tasks:
                -   To add criteria, click **Add**.
                -   To modify criteria, in the grid, click the attribute.
            2.  In the **Attribute** field, enter the attribute for which you want to define criteria.
            3.  In the **Value** field, enter the value for the attribute that inventory must match to be directed to the location.
            4.  Click **Apply**. The Rule page is displayed.
        5.  Click **Apply**. The Distribute to Storage Rules page is displayed.
        6.  To change the sequence in which the storage locations are used, in the grid, drag a location to the position you want.
        7.  Click **Apply**. The Distribution Settings page is displayed.
        8.  Click **Apply**. The customer page is displayed.
4.  Click **Save**.

## Delete a customer

1.  Select **Configuration > Partners > Customers > Existing Customers.**
2.  In the grid, select the check box next to the customer to delete.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Customer fields

 
| Field | Description |
| --- | --- |
| Customer | Name used to identify a business to whom you ship inventory. Each customer has a profile that is used to define how their inventory is handled, how their orders are processed, and how their inventory is shipped.<br > The attributes that are defined for a customer are defaulted into the respective fields on an order and order line if those values are not already populated at the time the order or order line is created. If any customer information on the order and order line is still missing after being populated by the customer values, the application uses the values specified for the customer type to populate the missing information. |
| Customer Address | Name of the customer's address information. An address name represents the location and contact information of an entity (such as a carrier, client, customer, or supplier). The information fields support the entry of an address name, first and last name, address lines, a city, a state or province, a postal code, and a country.<br > Address information is used, for example, to provide the warehouse ship-from address and the customer's ship-to address on an order. |
| Customer Type | Name for a group of customers that share the same attributes defined by the customer type, such as for order processing, packaging, and shipping. It is used to provide attribute information that populates customer-related fields on an order line that were not populated either when the order line was created or by the values inherited from the customer profile. It is also used to group customers for reporting purposes. |
| Client | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. |
| Department | Identifier for a department within the customer's facility. A department can be specified for a customer type, customer, order, order line, distribution, and item. It can be used to group information for the purpose of sorting and searching data, consolidating distribution inventory in customer-specific storage locations, and to help customers direct inventory to the proper department when it arrives at their facility. |
| ASN System | Name of the customer's host application, as defined in Integrator, to which Warehouse Management sends electronic transmissions, such as advance shipment notifications (ASNs) to the customer. In a multi-warehouse environment, the ASN system can represent the host in another warehouse to which shipment information is transmitted electronically. |
| Manufacturer | Name of the organization that manufactures the inventory supplied to a customer. The manufacturer is required when the application is configured to produce UCC128 (Uniform Commercial Code) identifiers for shipment labeling. |
| Partial Orders | If Yes, the customer allows order lines to be shipped with less than the required amount of inventory. Select Yes if the customer wants to receive at least part of an order when the entire order cannot be fulfilled.<br > If No, the order line must be shipped complete. If there is not enough inventory, and you are using the reservation process, the application does not allow you to plan the order line into a shipment. |
| Back Orders | If Yes, then if an order line has been shipped incomplete, the application notifies the host of what was shipped, back orders or saves the order line for the quantity that was not shipped, and maintains the incomplete order. Select Yes if you want to ship a partial order, but keep the order open and retain the order line until it is completely fulfilled.<br > If No, then if an order line has been shipped incomplete, the application notifies the host of what was shipped and completes the order. Select No if you want to ship a partial order and complete the order line even though it has not been completely fulfilled. |
| Case Splitting | If Yes, the customer allows the allocation of less than full case quantities to fulfill the order line when necessary.<br > If No, the customer requires the allocation of full case quantities to satisfy the order line. The order line cannot be fulfilled with partial case quantities. |
| Create Shipment By | Method by which the customer wants their orders to be grouped into shipments. The method determines how the application builds orders into shipments.<br>-   • **Bill-To Customer**: All of the order lines in a shipment must be for the same bill-to customer. The bill-to customer is the address name of the location to which billing information is sent.
<br>-   • **Outbound Order Number**: All of the order lines in a shipment must be for the same order. A shipment consists of a single order.
<br>-   • **Route-To Customer**: All of the order lines in a shipment must be for the same route-to customer. The route-to customer is the address name of the location to which the shipment is sent (such as a distribution hub), before being directed to the ship-to customer.
<br>-   • **Ship-To Customer**: All of the order lines in a shipment must be for the same ship-to customer. The ship-to customer is the address name of the final destination of the shipment.
<br > **Note**: If additional values were configured for your application, those values will also be available for selection. |
| Cross Dock Order Lines | Value that determines how the **Cross Dock** field on an outbound order line is set when an outbound order is added manually or downloaded from a host without a defined cross dock value for the order lines.<br>-   • **Inherit from customer type**: The **Cross Dock** field on the outbound order line inherits the value from the **Cross Dock Order Lines** field for the customer type. For example, if this field is set to Inherit from customer type, and the **Cross Dock Order Lines** field for the customer type is set to Yes, then the **Cross Dock** field on the order line is set to Yes (if it was undefined when the order was downloaded from a host or added manually).
<br>-   • **Yes**: The **Cross Dock** field on the order line is set to Yes.
<br>-   • **No**: The **Cross Doc**k field on the order line is set to No.
<br > Changing the value of this field affects only future order lines that are downloaded from a host, not the existing order lines for the customer. You can override this configuration at the order line level before allocating the inventory. |
| Pallet Building | Rule that determines the attributes that must be the same for inventory to be consolidated on the same pallet during pallet build operations. Pallet building is a process in which cases or repack cartons are consolidated after picking to create a new pallet. For example, if the rule is based on the shipment, then when an operator attempts to build a pallet, the application verifies that each case on the pallet is part of the same shipment. Alternatively, if the rule is based on staging lane, then inventory from different shipments can be added to the same pallet as long as the destination staging location is the same.<br > The options that are available are defined in shipping staging configuration. |
| Work Sequencing Release Type | Value that determines how locked pick work (for the purpose of outbound work sequencing) will be unlocked so an operator can perform the work. This field is used in controlling the sequence in which picked inventory is delivered to ship staging. For example, if the sequence is by stop, then pick work for stop 1 is unlocked first. After it has been picked and deposited to ship staging, pick work for stop 2 is unlocked, and so on. This field is enabled only when **Enable Outbound Work Sequencing** is set to Yes. See [Outbound work sequencing](../../outbound/shipping/outbound-staging.md).<br > The following options are available for selection:<br>-   •
    
    **Item Family**: Work is unlocked based on the work release sequence (from lowest number to highest) defined for each item family required for the load.
    
    <br>
    
    **Note**: Since this value ignores stop sequence, if it is selected for a load that is being fluid loaded (skips staging), then the **Ignore Stop Sequence** field on the load should be set to Yes to ensure loading is not dictated by stop sequence.
    
    <br>
<br>-   • **Manual**: Worked is unlocked based on the manual work release sequence assigned to each piece of pick work, with the lowest sequence released first. At any time, the system will start or resume unlocking work only when there is a manual work release sequence assigned to each piece of work for a load with the manual release type. If pick work with this release type is cancelled, a configuration determines whether the manual sequence is retained for the reallocated pick.
<br>-   • **None**: Work is excluded from outbound work sequencing and is not locked in the work queue.
<br>-   • **Stop**: Work is unlocked based on the stop's loading sequence (defined on the load) in order from lowest to highest. For example, stop 1, 2, 3, and so on.
<br>-   • **Stop/Item Family**: Work is unlocked based on the work release sequence defined for each item family within a stop, and then based on the stop's loading sequence (defined on the load) in order from lowest to highest. The work for the first item family on the first stop is unlocked, and after it has been staged, the work for the next item family on the first stop is unlocked, and so on. After the first stop is staged, the first item family for the next sequential stop is unlocked, and so on.
<br > **Note**: You can define a work release type for a load, customer, and warehouse. If a work sequencing release type is not defined for a load when a stop with shipments is added to the load, the application uses the value defined for the customer. If no release type is defined for the load and customer, the application uses the warehouse value. If there are multiple customers on the load, then the application uses the value for the customer associated with the first shipment picked for the load. The work release type cannot be updated from host transactions. |
| Customer Category | Name that describes the kind of customer that represents a store to which distributions are shipped. It may be useful to assign stores to a category, such as chain store, retail store, department store, or boutique. This field is only used for display and reporting purposes. |
| Customer Group | Name that describes the category of customer that represents a store to which distributions are shipped. It may be useful to assign stores to a group, for example, by area of country: Atlantic, Southeast, or Midwest. This field is only used for display and reporting purposes. |

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

## Customer Item fields

 
| Field | Description |
| --- | --- |
| Item | Identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). Before the application can effectively store, track, and manipulate inventory, you must assign an item identifier and define the attributes of each item you want to track. When defining an item, you specify information such as how the item is packaged and handled, along with details that define how it should be received, stored, allocated, shipped, counted, and valued (cost information). |
| Manufacturer | Name of the organization that manufactures the inventory supplied to a customer. The manufacturer is required when the application is configured to produce UCC128 (Uniform Commercial Code) identifiers for shipment labeling. |
| Department | Identifier for a department within the customer's facility. A department can be specified for a customer type, customer, order, order line, distribution, and item. It can be used to group information for the purpose of sorting and searching data, consolidating distribution inventory in customer-specific storage locations, and to help customers direct inventory to the proper department when it arrives at their facility. |
| Units per Case | Default number of items per packaging type. For example, for the Each/Case packaging type, it is the quantity of pieces or eaches of the item that is typically received in a single case. If a pallet of the item is received with a different quantity in the cases, the receiver can change the Each/Case value for that specific pallet. |
| Units per Pallet | Default number of items per packaging type. For example, for the Case/Pallet packaging type, it is the quantity of cases of the item that is typically received on a single pallet. If a pallet of the item is received with a different number of cases stacked on it, the receiver can change the Case/Pallet value for that specific pallet. |
| Pallet rounding threshold % for over shipment | Number representing the percentage of a pallet at and over which the application will round up the ordered quantity to a full pallet. For example, if a pallet quantity is 100 units, and the threshold is set to 80%, then if the customer orders 90 units of the item, the application will allocate a full pallet to satisfy the order. The pallet rounding threshold defined for the customer item takes precedence over the pallet rounding threshold defined for the item family. |
| Units Per Pack | Default number of items per packaging type. For example, for the Each/Inner Pack packaging type, it is the quantity of pieces or eaches of the item that is typically received in a single inner pack. If a pallet of the item is received with a different quantity in the inner packs, the receiver can change the Each/Inner Pack value for that specific pallet. |
| Customer Item | Identifier for a customer-specific item configuration. The customer item can be configured with specific packaging and date-tracking attributes that the customer requires for the item. When the customer orders the item, the application allocates matching inventory based on the customer's requirements. The customer item identifier may be different from the identifier defined for the item in the application, and can be included in reports and shipping documents. |
| Is this item date controlled | If Yes, the item is tracked by its manufactured date, expiration date, or both. If you select Yes, the date tracking fields become available for configuration.<br > If No, the item is not tracked by its manufactured or expiration date. |
| Inventory Rotation Method | Value that represents the order in which the allocation process selects available inventory for allocation. Select an inventory rotation method if you want the application to search for inventory based on date processing or location.<br>-   • **FEFO-ORDER-BY and FEFO-ORDER-BY-ABSOLUTE**: First-expiration, first-out. The first inventory to expire will be selected first.
<br>-   • **FIFO-ORDER-BY and FIFO-ORDER-BY-ABSOLUTE**: First-in, first-out. The oldest inventory will be selected first.
<br>-   • **LEFO-ORDER-BY and LEFO-ORDER-BY-ABSOLUTE**: Last-expiration, first-out. The last inventory to expire will be selected first.
<br>-   • **LIFO-ORDER-BY and LIFO-ORDER-BY-ABSOLUTE**: Last-in, first-out. The newest inventory will be selected first.
<br>-   • **LOCATION-ORDER-BY**: Locations are ordered within a pick zone (maintaining the allocation search path order) by the location attributes specified for the **Location Sort** field in inventory selection settings.
<br>-   •
    
    **No selection (blank)**: The application uses the inventory rotation method of the highest defined level of precedence. For information on precedence, see [Inventory rotation allocation processing](../../outbound/allocation/inventory-rotation-allocation.md).
    
    <br>
    
    **Note**: Inventory rotation methods defined at a lower precedence (except the default method) are automatically copied to the order line or work order line when the line is created. For example, if an order line is created for a date-tracked item with a rotation method defined, the rotation method is copied from the item to the order line, and then the application uses the order line rotation method during allocation.
    
    <br > If no inventory rotation method is defined at any level, then the application uses the allocation search path sequence and allocates the first available inventory it finds that matches all of the required attributes.
<br > When using inventory rotation methods that are not absolute, the application searches for inventory by allocation search path in sequence until it finds a pick zone that contains the inventory, and then allocates inventory that is closest to the preferred processing date. Therefore, the application stops searching at the first pick zone in which matching inventory is found.<br > When using absolute inventory rotation methods, the application searches either all of the allocation search paths for inventory that is closest to the preferred processing date or, if absolute groups are defined, each absolute group in sequence until it finds matching inventory and then allocates inventory that is closest to the preferred processing date from the pick zones within the absolute group. Therefore, the absolute method allows for more a comprehensive search to find the inventory. |
| Outbound Date Window | Amount of time in relation to the inventory’s received date or expiration date during which inventory is considered the same age for allocation when one of the FEFO/FIFO/LEFO/LIFO or absolute FEFO/FIFO/LEFO/LIFO inventory rotation methods is required. The available time units include minutes (m), hours (h), or days (d). For example, an entry of "5h" defines the window (5) and unit (hours). During allocation, the application uses the assigned date window based on a pre-defined order of precedence. See [Allocation Inventory Selection](../../outbound/allocation/allocation-inventory-selection.md). |
| Shelf Life | Minimum amount of time prior to the inventory's expiration date that must exist for date-controlled inventory to be considered for allocation. For example, a customer may order items that take approximately 6 days to reach a retail location. To ensure that the product can be sold for at least 4 days, the customer may request that only inventory that has at least 10 days (240 hours) to reach its expiration date be allocated to fill their orders.<br > Only available if the customer orders date-controlled inventory. |
| Freshness Date | Freshness date processing ensures that future shipments of a date-controlled item to a customer (for whom this attribute is enabled) always contain inventory that is fresher than earlier shipments of that same item.<br>-   • **Freshness Date Processing**: Indicates that the customer requires freshness date processing.
<br>-   • **No Freshness Date Processing**: Indicates that the customer does not require freshness date processing.
<br>-   • **Inherited Value**: Indicates that the value for this field will be provided on the order line by the customer type to which the customer belongs. This option is only available for a customer configuration; not for a customer type configuration.
<br > Only available if the customer orders date-controlled inventory. |

## Customer Shipping fields

 
| Field | Description |
| --- | --- |
| Allocation Search Path Group | Name associated with allocation search paths for the purpose of grouping them for use during order allocation. If a search path group is specified on the order line, the application uses only the search paths that have a matching group name to find inventory for that order. This process reduces processing time by limiting the number of search paths the application uses during order allocation.<br > An allocation search path group can be assigned to a customer type, order line, allocation search path, and replenishment search path. |
| Inventory Rotation Method | Value that represents the order in which the allocation process selects available inventory for allocation. Select an inventory rotation method if you want the application to search for inventory based on date processing or location.<br>-   • **FEFO-ORDER-BY and FEFO-ORDER-BY-ABSOLUTE**: First-expiration, first-out. The first inventory to expire will be selected first.
<br>-   • **FIFO-ORDER-BY and FIFO-ORDER-BY-ABSOLUTE**: First-in, first-out. The oldest inventory will be selected first.
<br>-   • **LEFO-ORDER-BY and LEFO-ORDER-BY-ABSOLUTE**: Last-expiration, first-out. The last inventory to expire will be selected first.
<br>-   • **LIFO-ORDER-BY and LIFO-ORDER-BY-ABSOLUTE**: Last-in, first-out. The newest inventory will be selected first.
<br>-   • **LOCATION-ORDER-BY**: Locations are ordered within a pick zone (maintaining the allocation search path order) by the location attributes specified for the **Location Sort** field in inventory selection settings.
<br>-   •
    
    **No selection (blank)**: The application uses the inventory rotation method of the highest defined level of precedence. For information on precedence, see [Inventory rotation allocation processing](../../outbound/allocation/inventory-rotation-allocation.md).
    
    <br>
    
    **Note**: Inventory rotation methods defined at a lower precedence (except the default method) are automatically copied to the order line or work order line when the line is created. For example, if an order line is created for a date-tracked item with a rotation method defined, the rotation method is copied from the item to the order line, and then the application uses the order line rotation method during allocation.
    
    <br > If no inventory rotation method is defined at any level, then the application uses the allocation search path sequence and allocates the first available inventory it finds that matches all of the required attributes.
<br > When using inventory rotation methods that are not absolute, the application searches for inventory by allocation search path in sequence until it finds a pick zone that contains the inventory, and then allocates inventory that is closest to the preferred processing date. Therefore, the application stops searching at the first pick zone in which matching inventory is found.<br > When using absolute inventory rotation methods, the application searches either all of the allocation search paths for inventory that is closest to the preferred processing date or, if absolute groups are defined, each absolute group in sequence until it finds matching inventory and then allocates inventory that is closest to the preferred processing date from the pick zones within the absolute group. Therefore, the absolute method allows for more a comprehensive search to find the inventory. |
| Allocation Profile | Identifier for the levels of quality at which the customer is willing to accept inventory. The allocation profile is a prioritized list of inventory statuses that defines which statuses can be shipped. It is applied to both date-controlled and non-date-controlled inventory. If you select **Inherited Value**, the value defined for the customer type is used. |
| Reservation Priority | Value that determines which orders receive inventory when there is not enough inventory in the warehouse to satisfy all orders for an item. This value applies only when the pick reservation process is used. |
| Bulk Picking | If Yes, the customer is enabled for bulk pick processing. Bulk pick processing allocates matching inventory for multiple order or work order lines together into larger unit of measure (UOM) picks so as to reduce the number of smaller UOM picks required to satisfy the orders. Select Yes if you want orders for this customer, by default, to be eligible for bulk pick processing at the time of allocation.<br > If No, orders for this customer are not eligible for bulk pick processing, even if the application is enabled to perform it. |
| Date-Controlled Items | If Yes, the customer orders date-controlled items. If the customer orders date-controlled items, then you can specify the customer's preferences for outbound date window and freshness date processing.<br > If No, the customer does not order date-controlled items, and so preferences for outbound date window and freshness date do not need to be configured. |
| Shelf Life | Minimum amount of time prior to the inventory's expiration date that must exist for date-controlled inventory to be considered for allocation. For example, a customer may order items that take approximately 6 days to reach a retail location. To ensure that the product can be sold for at least 4 days, the customer may request that only inventory that has at least 10 days (240 hours) to reach its expiration date be allocated to fill their orders.<br > Only available if the customer orders date-controlled inventory. |
| Freshness Date | Freshness date processing ensures that future shipments of a date-controlled item to a customer (for whom this attribute is enabled) always contain inventory that is fresher than earlier shipments of that same item.<br>-   • **Freshness Date Processing**: Indicates that the customer requires freshness date processing.
<br>-   • **No Freshness Date Processing**: Indicates that the customer does not require freshness date processing.
<br>-   • **Inherited Value**: Indicates that the value for this field will be provided on the order line by the customer type to which the customer belongs. This option is only available for a customer configuration; not for a customer type configuration.
<br > Only available if the customer orders date-controlled inventory. |
| Outbound Date Window | Amount of time in relation to the inventory’s received date or expiration date during which inventory is considered the same age for allocation when one of the FEFO/FIFO/LEFO/LIFO or absolute FEFO/FIFO/LEFO/LIFO inventory rotation methods is required. The available time units include minutes (m), hours (h), or days (d). For example, an entry of "5h" defines the window (5) and unit (hours). During allocation, the application uses the assigned date window based on a pre-defined order of precedence. See [Allocation Inventory Selection](../../outbound/allocation/allocation-inventory-selection.md). |
| Single Item Pallet | Reserved for future use. |
| Standard Case | If Yes, then the customer requires case quantities for an order line to be allocated in the case UOM defined for the item's default footprint. For example, assume that ITEM-A comes in three footprints: FP1, FP2, and FP3. FP1 has 10 eaches per case; FP2 has 15 eaches per case; and FP3 has 20 eaches per case. If FP2 is the default footprint, then when an order line for ITEM-A has **Standard Case** set to Yes, the application attempts to fulfill case quantities with the FP2 case UOM (15 eaches per case).<br > **Note**: If a specific footprint or units per case is specified on the order line, that value takes precedence over the **Standard Case** setting.<br > If No, then the customer allows case quantities for an order line to be fulfilled in the case UOM defined for any of the item's footprints, if inventory is not available in the case UOM for the default footprint. |
| Shipping Label | If Yes, the customer uses a custom label format. Select Yes to enable the field in which you can enter the shipping label format that the customer uses.<br > If No, then you do not need to specify a customer-specific label format. |
| What format does this customer use? | Name of the shipping label format, defined in the application, that the customer prefers. |
| Wrap | LPN-level packaging attribute for inventory. LPN packaging attributes are user-defined fields that are used to indicate requirements such as pallet wrapping, use of a slip sheet, and the application of labels on all four sides of a pallet of inventory. |
| Double Wrap | LPN-level packaging attribute for inventory. LPN packaging attributes are user-defined fields that are used to indicate requirements such as pallet wrapping, use of a slip sheet, and the application of labels on all four sides of a pallet of inventory. |
| Label 4 Sides | LPN-level packaging attribute for inventory. LPN packaging attributes are user-defined fields that are used to indicate requirements such as pallet wrapping, use of a slip sheet, and the application of labels on all four sides of a pallet of inventory. |
| Slip Sheet | LPN-level packaging attribute for inventory. LPN packaging attributes are user-defined fields that are used to indicate requirements such as pallet wrapping, use of a slip sheet, and the application of labels on all four sides of a pallet of inventory. |
| TMS Planning | If Yes, outbound orders must be planned into shipments and loads by a transportation management system.<br > If No, outbound orders can be planned into shipments using Warehouse Management. |
| Change Carrier | If Yes, then orders can be created with or without defining a carrier, and the carrier can be changed or added later during shipment planning, allocation, or processing. Select Yes if you want to specify carrier accounts for the customer. |
| Carrier Group | Code that identifies a group of carriers, one of which is expected to transport an order or a shipment to the customer. This is the required carrier group unless the order is configured to allow a carrier to be assigned after the order is created. |

## Distribution Settings fields

 
| Field | Description |
| --- | --- |
| Route-To Customer | Name of the customer to whom shipments are initially delivered. Select a route-to customer if shipments are delivered to an intermediate stop before being directed to their final destination. |
| Bill-To Customer | Name of the customer to whom billing information is sent. |
| Processing Priority | Number that indicates the order in which you want distributions to be applied to this customer as compared to other customers. The application selects and processes customers with the highest priority first. Priorities range from 1 to 9 with 1 being the highest priority. The value for **Processing Priority** may be overridden on an individual distribution created for the customer. |

## Rule fields

 
| Field | Description |
| --- | --- |
| Movement Zone | Movement zone in which the location for storing unallocated distribution inventory for the customer is located. |
| Location | Location to which the customer's unallocated distribution inventory should be directed until it can be planned into a shipment. A location can be shared by one or more customers. |
| LPN Levels | LPN levels that must be moved to the customer's storage location when identified as part of a distribution.<br > For example, if you select LPN, then when a pallet is received for a distribution, it must be moved to the customer's storage location. Moving an LPN to the customer's storage location allows operators to combine it with other inventory to be shipped to the same customer. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
