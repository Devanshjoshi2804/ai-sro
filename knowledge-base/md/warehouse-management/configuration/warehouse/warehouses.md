---
title: "Warehouses"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/warehouses.htm"
source: "/content/warehouses.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Warehouse"
  - "Warehouses"
sections:
  - "Translated warehouse"
  - "Add or modify a warehouse"
  - "View warehouse statistics"
  - "Warehouse fields"
  - "Address fields"
  - "Edit Address fields"
  - "General fields"
  - "Receiving Contact fields"
  - "Shipping Contact fields"
images:
  - "/content/resources/images/image632381.png"
source_sha1: 0ff4ec85085b206d8c1964fe8b0ad147f07df1f2
---
# Warehouses

A warehouse is a single physical facility under the domain of Warehouse Management, considered to be a unique repository for goods. Within a warehouse you can set up locations, items, and rules for moving inventory. You can maintain multiple warehouses in a single installed instance of Warehouse Management.

In a multi-warehouse environment, you can maintain multiple warehouses and limit user access to specific warehouses. You can also set up campus reporting, which directs all transactions to and from the host application through a different warehouse, so that the host is not aware of any other warehouses in the multi-warehouse environment. In a 3PL multi-warehouse environment, you can limit client access and the management of client inventory to one or more warehouses.

## Translated warehouse

A translated warehouse is a warehouse, in a multi-warehouse environment, that is visible to the host through inbound and outbound transactions.

You can define whether a warehouse is visible to the host as a translated warehouse. Use of a translated warehouse is optional, and only applies in a multi-warehouse environment.

You specify a translated warehouse, for example, if your host requires communications to take place to and from a single warehouse, instead of from multiple warehouses. It is also useful if the host downloads outbound orders, shipments, and inbound orders that are meant to be fulfilled by more than one warehouse.

If a translated warehouse is specified, then all transactions from the warehouse to the host that specify a warehouse contain the name of the translated warehouse. As a result, they appear to originate from the translated warehouse instead of the warehouse in which the activities occurred.

All inbound orders, outbound orders, and shipments for warehouses are downloaded from the host to the translated warehouse. They can then be redirected to the warehouse that should fulfill the processing.

A client can be associated with one or more warehouses, including the translated warehouse. Warehouses are configured in the web client.

See [Multi-warehouse](warehouses/multi-warehouse.md).

## Add or modify a warehouse

1.  Select **Configuration > Warehouse > Warehouse**. The Warehouse page displays the name and address of the current warehouse, and a list of the solutions that have been enabled for integration. See [Integration](../integration.md).
2.  Perform one of the following tasks:
    -   To edit an existing warehouse, click **Edit Warehouse**.
    -   To add a new warehouse, click **Create a new warehouse**.
3.  Enter information in the [Warehouse fields](#Warehouse_fields).

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

1.  Click **Save**.

## View warehouse statistics

1.  Select **Configuration > Warehouse > Warehouse**. The Warehouse page displays the name and address of the current warehouse and a list of the solutions that have been enabled for integration. See [Integration](../integration.md).
2.  Select **Statistics**. The Statistics tab displays the components that can be configured in each category. The quantity of each component is also displayed.
3.  To view a page you can use to add, modify, or delete a component, click the quantity value.

## Warehouse fields

 
| Field | Description |
| --- | --- |
| Warehouse Name | Unique identifier for this site, such as WMD1. |
| Description | Description of the warehouse. This is the display name of the warehouse. |
| Address Name | Identifier for address information. The address name typically identifies the individual or organization with which an address is associated. You can enter an existing address, or look up and select, add, or edit an address. |
| Address | Postal address of the warehouse. The information fields support the entry of an address name, address lines, a city, a state or province, a postal code, and a country. |
| Translated Warehouse | Name of a different warehouse to and from which host transactions should take place for this warehouse. Use of a translated warehouse is optional, and only applies in a multi-warehouse environment.<br > You specify a translated warehouse, for example, if your host requires communications to take place to and from a single warehouse, instead of multiple warehouses. It is also useful if the host downloads outbound orders, shipments, and inbound orders that are meant to be fulfilled by more than one warehouse. See [Translated warehouse](#Translated_warehouse). |
| Default Hold Prefix | Code that is added to the beginning of hold numbers that are created and applied to inventory in the warehouse. The default hold prefix is site specific, and its purpose is to differentiate holds placed on inventory at one site from holds placed on inventory at another site. This value is used when a hold prefix is not provided when the hold is created. See [Holds](../../inventory/holds.md). |
| Default Country | Country that is assigned to international parcel packages shipped from the warehouse if a country was not already specified for the package. This value is used to identify the parcel package's place of origin, and is typically used for export paperwork. |
| Count Threshold Unit | Unit quantity of an inventory count discrepancy that is allowed without generating a secondary count. If an inventory count reveals a discrepancy that is less than or equal to this value, a secondary (audit) count will not be generated. This value is used to prevent generating a secondary count for minor discrepancies. For example, if this value is 100, and a count discrepancy of 50 occurs, then a secondary count is not generated if one was configured to occur. The count threshold number at the item level overrides the number defined at the warehouse level. |
| Auto Send Cost Threshold | Monetary value threshold for inventory adjustments that can be sent to the host immediately and automatically. Inventory adjustments that are less than or equal to this value are sent to the host immediately without being stored in the application to be sent at a later time. Set a threshold if you want to avoid having to process small inventory adjustments manually.<br > Inventory adjustments that are greater than this value are not sent to the host automatically. Instead, they are stored until an authorized user sends them to the host. If you leave this field blank or enter a value of 0 (zero), then all inventory adjustments are stored until an authorized user sends them to the host. |
| Count Threshold Cost | Monetary value threshold for an inventory count discrepancy that is allowed without generating a secondary count. If the monetary value of an inventory count discrepancy is less than or equal to this value, a secondary count will not be generated. This value is used to prevent generating a secondary count for minor discrepancies. For example, if this value is 10 USD, and a count discrepancy of 5 USD occurs, then a secondary count is not generated if one was configured to occur. The count threshold cost at the item level overrides the value defined at the warehouse level. |
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

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
