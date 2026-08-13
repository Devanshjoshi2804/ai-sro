---
title: "Buildings"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/buildings.htm"
source: "/content/buildings.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Warehouse"
  - "Buildings"
sections:
  - "Add or modify a building"
  - "Delete a building"
  - "Building fields"
  - "Address fields"
  - "Edit Address fields"
  - "General fields"
  - "Receiving Contact fields"
  - "Shipping Contact fields"
images:
  - "/content/resources/images/image632381.png"
source_sha1: cd5e9382c0bb502758ae44381ba68cb9eaf19e32
---
# Buildings

A building is a warehouse entity that supports one or more defined areas, zones, and locations. At least one building must be defined for each defined warehouse. Inventory and location information can be reported by building.

After you define buildings, you can define the order in which the application searches selected buildings for the following purposes:

-   To find locations for storing received inventory. See [Storage building sequence](../inbound/storage/storage-building-sequence.md).
-   To find locations for allocating inventory to fulfill orders. See [Allocation building sequence](../outbound/allocation/allocation-building-sequence.md).

## Add or modify a building

1.  Select **Configuration > Warehouse > Buildings**.
2.  Select **Grid View**.
    
    **Note**: You can also add or modify a building using the **Map View**.
    
3.  Perform one of the following tasks:
    -   To add a building, click **Add.**
    -   To modify a building, in the grid, click the building name.
    -   To copy a building, in the grid, select the check box next to the building name, and then click **Copy**.
        
        **Note**: The copy function is only available in the **Grid View**.
        
4.  Enter information in the [Building fields](#Building_fields).

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

1.  To filter the map display, click **View**, and then select the entities to display.
    
2.  To add an image, select one from the list or click **Upload Image** to add a new one.
3.  To define the building boundaries for the warehouse:
    
    **Note**: Previously created buildings associated with the selected warehouse image are also displayed.
    
    1.  Click **Draw**. The boundary is automatically displayed on the warehouse map.
    2.  Size and drag the building box on the map.
4.  Click **Save**.

## Delete a building

You cannot delete a building if there is any entity, such as an area, assigned to the building. You must first delete the assigned entities, and then you can delete the building.

1.  Select **Configuration > Warehouse > Buildings**.
2.  Select **Grid View**.
3.  In the grid, select the check box next to the building to delete.
4.  Click **Delete**. A confirmation message is displayed.
5.  Click **OK**.

## Building fields

 
| Field | Description |
| --- | --- |
| Building Name | Unique identifier for a building. A building is a warehouse entity consisting of one or more areas. Inventory and location information can be reported by building. |
| Building Address | Address information. The information fields support the entry of an address name, address lines, a city, a state or province, a postal code, and a country. |

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
