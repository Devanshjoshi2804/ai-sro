---
title: "Suppliers"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/suppliers.htm"
source: "/content/suppliers.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Partners"
  - "Suppliers"
sections:
  - "Trusted suppliers"
  - "Supplier item overrides"
  - "Packaging attributes"
  - "Receiving defaults"
  - "Supplier item footprint overrides"
  - "Consignment"
  - "Consignment tracking"
  - "Add or modify a supplier"
  - "Delete a supplier"
  - "Supplier fields"
  - "Address fields"
  - "Edit Address fields"
  - "General fields"
  - "Receiving Contact fields"
  - "Shipping Contact fields"
  - "Supplier Item fields"
  - "Override Footprint fields"
images:
  - "/content/resources/images/image632381.png"
  - "/content/resources/images/image942438.png"
source_sha1: e094f070bfcf094c11324d35bffdbedc332f68c4
---
# Suppliers

A supplier is a vendor that provides your warehouse with the inventory needed to stock, allocate, pick, and ship items for orders you receive from your customers. The supplier is responsible for supplying items to your warehouse. You configure supplier attributes to define how the application processes items received from different suppliers.

## Trusted suppliers

A trusted supplier is one that is configured with the **Trusted** field set to Yes. This is done to expedite the receiving process. When inventory arrives from a trusted supplier, the receiving operator is not prompted to validate the advanced shipment notification (ASN) information, and instead moves directly to putaway.

The Trusted attribute is typically assigned to suppliers from whom you receive ASN information that is consistently accurate with regard to the inventory information that it supplies.

The application can download (and operators can receive from) ASNs from trusted suppliers that have LPNs with inventory for multiple planned inbound orders. However, the application does not accept ASNs that contain LPNs with inventory for multiple planned inbound orders from non-trusted suppliers.

**Note**: The application does not support receiving mixed-order LPNs from trusted suppliers if the inventory is for distribution or cross docking.

When inventory for a single inbound order arrives from a non-trusted supplier, the receiving operator is prompted to validate the ASN information and, if necessary, update the information. You can view updates to ASN information, along with details related to other activities performed in the warehouse, on the History page.

The Trusted attribute is not typically assigned to suppliers that have a history of discrepancies between the ASN information that is sent and the inventory that actually arrives. It is also not typically assigned to new suppliers until experience shows that their ASN information is consistently accurate and their inventory is consistently in good condition.

## Supplier item overrides

A supplier item is a configuration that defines how certain items (from the supplier) should be handled upon receipt into the warehouse. It defines inventory attribute values that are applied by default during receiving. The attribute values defined for the supplier item override those defined for the supplier, other suppliers, or the item.

The following scenarios present examples of how supplier items are used:

-   The handling unit type set for the supplier is CHEP. However, you typically receive an item called SOAP with a handling unit type of EURO. You can add SOAP as a supplier item and assign to it the proper handling unit type.
-   The receive status set for the supplier is Available. However, you often notice quality issues with an item called PAINT when it arrives from the supplier. You can define a supplier item for PAINT with a receive status of Inspect. This enables you to receive PAINT with a default value of Inspect, and other items with a default value of Available.

## Packaging attributes

Packaging attributes are user-defined inventory attribute that can be applied to an LPN of inventory. If one or more packaging attributes have been enabled for your warehouse, you can configure the attribute as a receiving default for a supplier, supplier item override, or supplier item footprint override. The operator can change the default value, if necessary, to match the inventory that actually arrives. The attribute becomes part of the inventory's detail record in the warehouse.

## Receiving defaults

The receiving defaults defined for a supplier are inventory attribute values (such as for receive status, serial number type, lot format, and handling unit type) that are applied by default to inventory when it is received from the supplier.

Receiving defaults are overridden by supplier item overrides and by supplier item footprint overrides. If no receiving defaults or overrides are defined, then the defaults defined for the item are applied.

## Supplier item footprint overrides

A supplier item footprint is an item to which you can assign a default footprint that is different from how the item is received from other suppliers.

You can use a supplier item footprint override, for example, when you receive an item from a supplier that requires a packaging configuration different from the item footprint that the rest of your suppliers use for that item. For example, suppliers A, B, and C send you SOAP with the default footprint code of T2H2, but supplier D sends you SOAP with a footprint code of T4H4. So, for supplier D, you can specify T4H4 to be the default footprint code for SOAP, so that when you receive SOAP from supplier D that footprint code is applied by default.

## Consignment

A consignment is inventory for which the supplier retains ownership after it has been received into the warehouse. In the application, consignment is an attribute of consigned inventory.

If consignment tracking is enabled for inventory, ownership of the inventory remains with the supplier until a certain point during warehouse processing at which time ownership is transferred to the warehouse.

You configure consignment during the process of adding or modifying a supplier. You can enable consignment tracking for all items received from the supplier, or only the ones that you select. You define the consignment change point at which ownership is transferred to the warehouse. The consignment values defined for a supplier item override those defined for a supplier, which override those defined for the warehouse.

## Consignment tracking

For each supplier you can indicate whether consignment tracking is enabled and, if it is, whether it is enabled for all or only specific items that you designate. Consignment tracking indicates that the supplier has retained ownership of the inventory delivered to the facility.

You can choose one of the following options to configure the point at which transfer of ownership from the supplier to the warehouse takes place:

-   Immediately upon receipt of the inventory
-   When inventory is put away to a storage location
-   When the shipping transport equipment on which the inventory is loaded is closed or dispatched
-   At a specified number of days after receipt

**Note**: The application sets the consignment end date for inventory on an ASN shipment based on when the inventory was received and put away to storage. For non-ASN shipments, the application sets the consignment end date based on when the inventory was identified. For example, if the Consignment Days value is 30, then when an ASN shipment is received, the consignment change point is 30 days from when the inventory is put away to storage; when a non-ASN shipment is received, the change point is 30 days from when the inventory is identified.

Transfer of ownership can be configured for a warehouse, supplier or supplier item. The application uses the most specific value if transfer of ownership is configured at multiple levels. A background command (job) is executed on a daily basis to find inventory that has exceeded its consignment days, which triggers the ownership change. When appropriate, an integration transaction notifies the host that the transfer of ownership has occurred.

The application also enables you to perform the following tasks:

-   Specify a particular supplier's item on an order, work order or work order setup.
-   Require operators to confirm the supplier during picking of consigned items.
-   View supplier and consignment state on inventory, order, bill of material (BOM), work order and daily transaction reports.

## Add or modify a supplier

1.  Select **Configuration > Partners > Suppliers**.
2.  Perform one of the following tasks:
    -   To add a supplier, click **Add New**.
    -   To modify a supplier, in the grid, click the supplier.
    -   To copy a supplier, select the check box next to the supplier, and then click **Copy**.
3.  Enter information in the [Supplier fields](#Supplier_fields).
    
    **Note**: LPN attributes (such as **Wrap** and **Double Wrap**) are user-defined fields. Therefore, the name and number of fields that are displayed in the **LPN ATTRIBUTES** section will vary depending on what is configured for your warehouse.
    

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

1.  To assign a supplier item override:
    1.  Click **Set Items**. The Supplier Items page is displayed.
    2.  Perform one of the following tasks:
        -   To add an item, click **Add**.
        -   To modify an item, in the grid, click the item.
        -   To copy an item, select the check box next to the item, and then click **Copy**.
    3.  Enter information in the [Supplier Item fields](#Supplier_Item_fields).
    4.  To override an item footprint:
        
        **Note**: The ITEM FOOTPRINTS grid displays the footprints assigned to the item. You can override some attributes of the item footprint to match the item configuration you typically receive from the supplier.
        
        1.  Under **ITEM FOOTPRINTS**, in the grid, click the footprint to override.
        2.  Enter information in the [Override Footprint fields](#Override_Footprint_fields).
        3.  Click **Apply**.
2.  Click **Apply** and then click ![Previous page](../../../../images/resources/images/image942438.png).
3.  To specify items for consignment tracking or exclusion:
    1.  Click **Consignments**. The Supplier Consignments page is displayed.
        
        **Note**: The **Consignments** button is only available if consignment tracking is enabled and the value for the **Track Consignments** field is **Track Only for Items Listed Below** or **Track for All Items Except Those Listed Below**.
        
    2.  In the **Available** column, select the check box next to the items you want to select.
    3.  Click **Apply**.
4.  Click **Save**.

## Delete a supplier

You cannot delete a supplier that is associated with inventory or receipts in the warehouse.

1.  Select **Configuration > Partners > Suppliers > Existing Suppliers.**
2.  Select the check box next to the supplier to delete.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Supplier fields

 
| Field | Description |
| --- | --- |
| Supplier | Identifier for a supplier. A supplier can be an individual, organization, or another warehouse within your own organization from which you repeatedly receive inventory or handling units. |
| Trusted | If Yes, the supplier is trusted. This means that during receiving the operator is not prompted to verify the ASN information for the inventory and moves directly to putaway. The trusted attribute is typically assigned to suppliers from whom ASN information is traditionally accurate. See [Trusted suppliers](#Trusted_suppliers).<br > If No, then during receiving, the operator is prompted to verify and, if necessary, update the ASN information for the inventory before putting it away. For historical purposes, the application tracks ASN updates for non-trusted suppliers. |
| Auto Receive Trusted ASNs | If Yes, then when receiving an ASN shipment from a trusted supplier, the user has the option to perform auto receiving. Auto receiving is a process in which the application immediately receives all of the LPNs on an inbound shipment and systematically moves them to a receiving staging lane. The physical move of the LPNs can take place before, during, or after auto-receive processing. An inbound shipment is eligible for auto receiving if it is associated with a detailed ASN (with LPN information), and the supplier on every planned inbound order is trusted and enabled for auto receiving. If any of the suppliers on the inbound shipment are not trusted or not enabled for auto receiving, then the application initiates LPN receiving, which requires the operator to scan each LPN on the inbound shipment.<br > For example, assume an inbound shipment associated with an ASN arrives at the warehouse. When the operator scans the shipment to receive, the application confirms whether all of the inbound orders are from trusted suppliers that are enabled for auto receiving. If so, the operator is prompted with the option to perform auto receiving; when auto-receive processing is done, the operator can complete the inbound shipment.<br > See [ASN auto receiving from trusted suppliers](../../receiving/receiving-concepts.md).<br > **Note**: This field must be set to Yes in the Inbound Identification configurations and for each trusted supplier from which you want to auto receive.<br > If No, then auto receiving is disabled. If set to No in the Inbound Identification configurations, operators are required to scan each LPN on all inbound shipments, regardless of whether the supplier is trusted or enabled for auto receiving. |
| Client | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. |
| Barcode Template | Identifier for a bar code template. A bar code template is used to parse data from supplier-provided inventory barcodes for tracking purposes. A bar code template contains one or more bar code applications and can be associated with one or more suppliers. A bar code application defines the data structure (application ID, field name, length, date format, and decimal value) that the application uses to extract data from a supplier's bar code.<br > Bar code templates are used to simplify the receiving process to ensure inventory attributes are accurate when received from the supplier. Based on an agreed upon bar code format between you and your supplier, certain inventory attributes are contained in bar codes placed on the shipping container. During receiving, when the bar code is scanned (or entered), this information populates the fields on the receiving screens and updates any existing information that is inaccurate. |
| Serial Number Type | Identifier for a specific kind of serial number that is applied by default to inventory received from the supplier. A serial number type defines the order in which the operator is prompted to enter serial numbers when multiple types are required for an item, whether serial numbers of this type are reported to the host, and the number mask that is used to verify that a valid serial number has been entered. |
| Supplier Address | Name of the supplier's address information. An address name represents the location and contact information of an entity (such as a carrier, client, customer, or supplier). The information fields support the entry of an address name, first and last name, address lines, a city, a state or province, a postal code, and a country. |
| Receive Status | Value that defines the quality or disposition of inventory. When defined for an item, it represents the status assigned to inventory by default during receiving. |
| Lot Format | Defines the default lot format for lot numbers received from the supplier. If a lot format is specified for an item, then whenever a lot number is entered for the item, the application validates the lot number against the required format. Also, if the lot format is configured with a production or expiration date, then during inventory identification, the application extracts the date from the format to populate the manufacture or expiration date fields. The format of the extracted date is defined by the **Raw Lot Format** field that is available when adding a new lot format. |
| Wrap | LPN-level packaging attribute for inventory. LPN packaging attributes are user-defined fields that are used to indicate requirements such as pallet wrapping, use of a slip sheet, and the application of labels on all four sides of a pallet of inventory. |
| Double Wrap | LPN-level packaging attribute for inventory. LPN packaging attributes are user-defined fields that are used to indicate requirements such as pallet wrapping, use of a slip sheet, and the application of labels on all four sides of a pallet of inventory. |
| Label 4 Sides | LPN-level packaging attribute for inventory. LPN packaging attributes are user-defined fields that are used to indicate requirements such as pallet wrapping, use of a slip sheet, and the application of labels on all four sides of a pallet of inventory. |
| Slip Sheet | LPN-level packaging attribute for inventory. LPN packaging attributes are user-defined fields that are used to indicate requirements such as pallet wrapping, use of a slip sheet, and the application of labels on all four sides of a pallet of inventory. |
| Handling Unit Type | Default handling unit type that is applied to inventory received from the supplier. A handling unit type classifies a group of handling units (for example, pallets, totes, pieces of equipment, or vehicles) that share the same characteristics such as size and weight, as well as whether they are serialized, temporary, or considered a container. The application tracks the on-hand quantity of handling units by type and, for serialized handling units, by handling unit LPN. |
| Enable Consignment Tracking | If Yes, items from this supplier are tracked for consignment. Consigned inventory is inventory for which the supplier retains ownership until the designated point (such as when it is put away or shipped) at which time ownership is transferred to the warehouse. See [Consignment tracking](#Consignment_tracking).<br > If No, the supplier does not retain ownership of inventory in the warehouse. |
| Track Consignments | Description that indicates how items received from the supplier are tracked for consignment.<br>-   • **Track for All Items**: Indicates that all items are tracked for consignment.
<br>-   • **Track Only for Items Listed Below**: Indicates that only the items listed in the Supplier Consignments to Track grid are tracked for consignment.
<br>-   • **Track for All Items Except Those Listed Below**: Indicates that all items except those listed in the Supplier Consignments to Exclude grid are tracked for consignment. |
| Consignment Change Point | Value that determines when ownership of consigned inventory is transferred from the supplier to the warehouse. The consignment values defined for the supplier item override those defined for the supplier, which override those defined for the warehouse.<br>-   • **Consignment Days**: Ownership is transferred after the specified number of consignment days (defined in the **Consignment Days** field) have passed.
<br>-   • **Putaway**: Ownership is transferred when the putaway work for the inventory is complete.
<br>-   • **Receipt**: Ownership is transferred when the inventory is received by the warehouse.
<br>-   • **Transport Equipment Close**: Ownership is transferred when the outbound transport equipment on which the consigned inventory is loaded is closed.
<br>-   • **Transport Equipment Dispatch**: Ownership is transferred when the outbound transport equipment on which the consigned inventory is loaded is dispatched. |
| Consignment Days | Number of days after receiving consigned inventory that the ownership is transferred from the supplier to the warehouse. If **Consignment Days** is selected as the **Consignment Change Point**, then this value represents the number of days after receipt during which the supplier retains ownership of the consigned inventory. A schedule-based job is configured to run daily to determine when the specified number of consignment days has passed, at which point ownership is transferred to the warehouse. Only available if **Consignment Change Point** is **Consignment Days**.<br > **Note**: The application sets the consignment end date for inventory on an ASN shipment based on when the inventory was received and put away to storage. For non-ASN shipments, the application sets the consignment end date based on when the inventory was identified. For example, if the Consignment Days value is 30, then when an ASN shipment is received, the consignment change point is 30 days from when the inventory is put away to storage; when a non-ASN shipment is received, the change point is 30 days from when the inventory is identified. |
| Customs Site Type | Customs site type assigned to the address of the warehouse from which the outbound order is shipped. The site type indicates whether the warehouse is bonded, and if it is bonded, the type of bonded warehouse.<br>-   • **Customs**: The address is a bonded warehouse that contains inventory for which customs duties must be paid. Customs duties are assessed against goods (other than alcoholic beverages and tobacco products) that have been imported from the European Union (EU).
<br>-   • **Customs and Excise**: The address is a bonded warehouse that contains inventory for which both customs and excise duties must be paid. Excise duties are assessed against goods such as alcoholic beverages and tobacco products.
<br>-   • **No selection (blank)**: The address is not a bonded warehouse and only duty paid items can be received.
<br > Only available if the customs functionality is enabled. |
| Global Location Number | Alphanumeric code, assigned by the European Article Numbering Uniform Code Council (EAN/UCC), that is used to identify a legal entity (such as a supplier or customer), a physical entity (such as a warehouse, loading dock, or delivery point), or a functional entity (such as an accounting department or returns department). The GLN is a 13-digit code that contains an EAN/UCC company prefix, a location reference, and a check digit.<br > Only available if the customs functionality is enabled. |
| Customs Tax Site | Tax approval number. This number is obtained from the internal revenue service for the United Kingdom, and is required for a bonded warehouse if the value for the **Customs Site Type** field is **Customs** and **Excise**.<br > Only available if the customs functionality is enabled. |

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

## Supplier Item fields

 
| Field | Description |
| --- | --- |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Receive Status | Value that defines the quality or disposition of inventory. When defined for an item, it represents the status assigned to inventory by default during receiving. |
| Handling Unit Type | Default handling unit type that is applied to inventory received from the supplier. A handling unit type classifies a group of handling units (for example, pallets, totes, pieces of equipment, or vehicles) that share the same characteristics such as size and weight, as well as whether they are serialized, temporary, or considered a container. The application tracks the on-hand quantity of handling units by type and, for serialized handling units, by handling unit LPN. |
| Consignment Change Point | Value that determines when ownership of consigned inventory is transferred from the supplier to the warehouse. The consignment values defined for the supplier item override those defined for the supplier, which override those defined for the warehouse.<br>-   • **Consignment Days**: Ownership is transferred after the specified number of consignment days (defined in the **Consignment Days** field) have passed.
<br>-   • **Putaway**: Ownership is transferred when the putaway work for the inventory is complete.
<br>-   • **Receipt**: Ownership is transferred when the inventory is received by the warehouse.
<br>-   • **Transport Equipment Close**: Ownership is transferred when the outbound transport equipment on which the consigned inventory is loaded is closed.
<br>-   • **Transport Equipment Dispatch**: Ownership is transferred when the outbound transport equipment on which the consigned inventory is loaded is dispatched. |
| Consignment Days | Number of days after receiving consigned inventory that the ownership is transferred from the supplier to the warehouse. If **Consignment Days** is selected as the **Consignment Change Point**, then this value represents the number of days after receipt during which the supplier retains ownership of the consigned inventory. A schedule-based job is configured to run daily to determine when the specified number of consignment days has passed, at which point ownership is transferred to the warehouse. Only available if **Consignment Change Point** is **Consignment Days**.<br > **Note**: The application sets the consignment end date for inventory on an ASN shipment based on when the inventory was received and put away to storage. For non-ASN shipments, the application sets the consignment end date based on when the inventory was identified. For example, if the Consignment Days value is 30, then when an ASN shipment is received, the consignment change point is 30 days from when the inventory is put away to storage; when a non-ASN shipment is received, the change point is 30 days from when the inventory is identified. |
| Re-Order Point | Amount of inventory that specifies when this item should be reordered. When inventory levels within the warehouse reach this point, the item should be reordered at the specified reorder quantity. Re-Order Quantity and Re-Order Point can be used in custom reports or custom processes to inform the host when the item needs to be re-ordered and in what quantity. |
| Re-Order Quantity | Amount of inventory to reorder when the inventory levels within the warehouse reach the reorder point. Re-order Quantity and Re-order Point can be used in custom reports or custom processes to inform the host when the item needs to be re-ordered and in what quantity. |
| Wrap | LPN-level packaging attribute for inventory. LPN packaging attributes are user-defined fields that are used to indicate requirements such as pallet wrapping, use of a slip sheet, and the application of labels on all four sides of a pallet of inventory. |
| Double Wrap | LPN-level packaging attribute for inventory. LPN packaging attributes are user-defined fields that are used to indicate requirements such as pallet wrapping, use of a slip sheet, and the application of labels on all four sides of a pallet of inventory. |
| Label 4 Sides | LPN-level packaging attribute for inventory. LPN packaging attributes are user-defined fields that are used to indicate requirements such as pallet wrapping, use of a slip sheet, and the application of labels on all four sides of a pallet of inventory. |
| Slip Sheet | LPN-level packaging attribute for inventory. LPN packaging attributes are user-defined fields that are used to indicate requirements such as pallet wrapping, use of a slip sheet, and the application of labels on all four sides of a pallet of inventory. |

## Override Footprint fields

 
| Field | Description |
| --- | --- |
| Do you want to override Footprint for this Supplier | If Yes, the attributes that you select in the Override Footprint window apply to the footprint for the selected item when it is received from the supplier.<br > If No, the item footprint is not changed for the selected item when it is received from the supplier. |
| Do you want to make this Footprint the default footprint for this Supplier | If Yes, the footprint is displayed by default when the item is received from the supplier. One and only one footprint must be defined as the default footprint.<br > If No, the footprint is not the default footprint for the selected item from the supplier. |
| Handling Unit Type | Default handling unit type that is applied to the item when it is received from the supplier. A handling unit type classifies a group of handling units (for example, pallets or totes) that share the same characteristics such as size and weight, as well as whether they are serialized, temporary, or considered a container. The application tracks the on-hand quantity of handling units by type and, for serialized handling units, by handling unit LPN. |
| Wrap | If Yes, this LPN-level packaging attribute is required for the footprint configuration. LPN packaging attributes are user-defined fields that are used to indicate requirements such as pallet wrapping, use of a slip sheet, and the application of labels on all four sides of a pallet of inventory. Select Yes to enable the use of this LPN packaging attribute.<br > If No, this LPN packaging attribute is not required for the footprint configuration, and must not be applied.<br > If Inherited Value, the packaging attribute value defined for the item applies to the footprint configuration. |
| Label 4 Sides | If Yes, this LPN-level packaging attribute is required for the footprint configuration. LPN packaging attributes are user-defined fields that are used to indicate requirements such as pallet wrapping, use of a slip sheet, and the application of labels on all four sides of a pallet of inventory. Select Yes to enable the use of this LPN packaging attribute.<br > If No, this LPN packaging attribute is not required for the footprint configuration, and must not be applied.<br > If Inherited Value, the packaging attribute value defined for the item applies to the footprint configuration. |
| Double Wrap | If Yes, this LPN-level packaging attribute is required for the footprint configuration. LPN packaging attributes are user-defined fields that are used to indicate requirements such as pallet wrapping, use of a slip sheet, and the application of labels on all four sides of a pallet of inventory. Select Yes to enable the use of this LPN packaging attribute.<br > If No, this LPN packaging attribute is not required for the footprint configuration, and must not be applied.<br > If Inherited Value, the packaging attribute value defined for the item applies to the footprint configuration. |
| Slip Sheet | If Yes, this LPN-level packaging attribute is required for the footprint configuration. LPN packaging attributes are user-defined fields that are used to indicate requirements such as pallet wrapping, use of a slip sheet, and the application of labels on all four sides of a pallet of inventory. Select Yes to enable the use of this LPN packaging attribute.<br > If No, this LPN packaging attribute is not required for the footprint configuration, and must not be applied.<br > If Inherited Value, the packaging attribute value defined for the item applies to the footprint configuration. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
