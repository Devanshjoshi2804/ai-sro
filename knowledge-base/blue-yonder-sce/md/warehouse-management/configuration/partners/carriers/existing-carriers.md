---
title: "Existing Carriers"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/existing_carriers.htm"
source: "/content/existing_carriers.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Partners"
  - "Carriers"
  - "Existing Carriers"
sections:
  - "Add or modify a carrier"
  - "Delete a carrier"
  - "Carrier fields"
  - "Address fields"
  - "Edit Address fields"
  - "General fields"
  - "Receiving Contact fields"
  - "Shipping Contact fields"
  - "Service Level fields"
images:
  - "/content/resources/images/image632381.png"
  - "/content/resources/images/image942438.png"
source_sha1: 19fd99750b029a6de2b2c0c9a79272d0d80e46d7
---
# Existing Carriers

A carrier is an individual or company that transports product from a designated origin to a designated destination. The application uses carrier information during receiving, order processing, and shipping operations. For example, a carrier is associated with inbound shipments and outbound loads; a customer configuration can identify a preferred carrier group for their orders; a carrier can be assigned to an order line; and a carrier can be associated with service levels that define how the carrier handles and delivers inventory.

You create a carrier record for each of the carriers that are used to transport your inbound and outbound orders. When you define a carrier, you specify the following attributes:

-   Carrier code, name, address, and account number.
-   Standard Carrier Alpha Code (SCAC) for the carrier. SCAC is a standardized coding system adopted by the transportation industry in which a carrier is assigned an alphabetic code.
-   Carrier service level (including transport mode) and shipping cartonization thresholds that limit the contents of a shipping container by value, weight, and volume.
-   If Warehouse Management is integrated with a parcel application through Parcel Handler, settings for automatically closing a parcel shipment. See [Set up automatic close of parcel shipments](../../outbound/shipping/parcel.md).

Typically, you create carriers during the installation process, and they remain constant thereafter. However, you can add, modify, and delete carriers to meet changing transportation requirements and business needs.

## Add or modify a carrier

1.  Select **Configuration > Partners > Carriers > Existing Carriers**.
2.  Perform one of the following tasks:
    -   To add a new carrier, click **Add**.
    -   To modify a carrier, in the grid, click the carrier.
    -   To copy a carrier, select the check box next to the carrier, and then click **Copy**.
3.  Enter information in the [Carrier fields](#Carrier_fields).

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

1.  To define service levels for a carrier:
    1.  Under **CARRIER SERVICES**, click **Service Levels**.
    2.  Perform one of the following tasks:
        -   To add a service level, click **Add**.
        -   To modify a service level, in the grid, click the service level.
        -   To copy a service level, in the grid, select the check box next to the service level, and then click **Copy**.
        -   To delete a service level, in the grid, select the check box next to the service level, and then click **Delete**.
    3.  Enter information in the [Service Levels fields](#Service_Level_fields).
    4.  Click **Apply**.
    5.  Click ![Previous page](../../../../../images/resources/images/image942438.png).
2.  Click **Save**.

## Delete a carrier

1.  Select **Configuration > Partners > Carriers > Existing Carriers**.
2.  In the grid, select the check box next to the carrier to delete.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Carrier fields

 
| Field | Description |
| --- | --- |
| Carrier | Identifier for a carrier that delivers inbound inventory to the warehouse or outbound shipments to a customer. This is the identifier that will be displayed to users on the application windows and reports. In the application, a carrier can be associated with a customer, order, inbound shipment, outbound shipment, load, and service levels (such as Ground, Next Day, and Saturday Delivery). |
| Carrier Name | Full name or description of the carrier. |
| Carrier Address | Carrier's address information. An address name represents the location and contact information of an entity (such as a carrier, client, customer, or supplier). The information fields support the entry of an address name, first and last name, address lines, a city, a state or province, a postal code, and a country.<br > Address information is used, for example, to provide the billing address for the carrier. |
| SCAC | Standard Carrier Alpha Code (SCAC) for the carrier. SCAC is a standardized coding system adopted by the transportation industry in which a carrier is assigned an alphabetic code. The SCAC can be used in the industry as an alternate identifier for the carrier code and service level combination. |
| Account | Unique number that identifies the account that you have established with this carrier. |
| Automatically Close Shipments | If Yes, Warehouse Management automatically moves a parcel shipment from Staged to Load Complete after the length of time specified in the **Wait Time** field when all of the shipment's parcels have been manifested and are in the manifest status specified in the **Manifest Status** field. When a shipment moves from Staged to Load Complete, host transactions are sent. This process is dependent upon the Automatically Close Parcel Shipments job, which can be configured on the Jobs page in the Console.<br > If No, Warehouse Management will not use the settings under SHIPMENT CLOSE to automatically close parcel shipments.<br > Only displayed when Warehouse Management is integrated with a parcel application through Parcel Handler. |
| Wait Time | Length of time (in minutes) that Warehouse Management will wait after a shipment for this carrier is staged before automatically closing the shipment. This value only takes effect when **Automatically Close Shipments** is set to Yes, and all parcels for the staged shipment are manifested and have the manifest status specified in the **Manifest Status** field.<br > Only displayed when Warehouse Management is integrated with a parcel application through Parcel Handler. |
| Manifest Status | Manifest status of a shipment's staged parcels that causes Warehouse Management to automatically close the associated shipment after the designated wait time. Typically, Released or Closed is the selected value. This value only takes effect if **Automatically Close Shipments** is set to Yes, and when all of the parcels in a shipment are in the selected status.<br > Only displayed when Warehouse Management is integrated with a parcel application through Parcel Handler. |

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

## Service Level fields

 
| Field | Description |
| --- | --- |
| Service Level | Identifier for the service and transit time provided by the carrier that transports an order or shipment to the customer. For example, for a parcel carrier it may be used to indicate services such as express, second-day air, or standard delivery. |
| Transport Mode | Type of carrier, such as TL (truckload), LTL (less than truckload), or small package (parcel), that defines how freight is transported from one location to another. The attributes defined for a transport mode are applied to carriers to which the transport mode is assigned. See [Transport Modes](transport-modes.md). |
| Allow Ship Staging Override | If Yes, indicates that ship staging override is enabled for the carrier at this service level. Ship staging override lets an operator choose a different ship staging location instead of the displayed location when depositing inventory. However, to work, ship staging location overrides must also be enabled for both the original and the new ship staging zones.<br > If No, the operator is not allowed to override the application-directed ship staging location for this carrier and service level. |
| Saturday Delivery | If Yes, the carrier deliver shipments on Saturday at this service level, if requested to do so on a shipment, or on an order line before it is planned into a shipment. Selecting Yes for Saturday Delivery only indicates that Saturday delivery is an available option when maintaining order lines or shipments. It does not automatically enable Saturday delivery for all shipments associated with this carrier service (carrier and service level).<br > If No, the carrier does not perform Saturday deliveries at this service level. |
| Force Single Package Parcels | If Yes, indicates that the parcel application creates a separate shipment for each manifested package for the carrier service level. Selecting Yes to enable single package shipments disables multiple package shipments in the parcel application. The result is that each manifested package ships separately regardless of the status of any related package.<br > If No, a shipment can consists of multiple packages.<br > For example, if No is selected, and there are three packages on a shipment in Warehouse Management, they manifest and ship together using multiple package shipments as 1 of 3, 2 of 3, and 3 of 3. If Yes, is selected, then the parcel application creates a separate shipment for each of the three manifested packages and ships each of them as 1 of 1. |
| Allow Bundling | If Yes, the carrier permits manifesting a group of bundled parcels as one parcel (bundled parcel load) at this service level.<br > If No, the carrier does not support bundled parcels; each parcel is processed individually. |
| International Delivery | If Yes, the carrier provides international service at this service level.<br > If No, the carrier does not provide international service at this service level. |
| Maximum Weight | Value that represents the total maximum weight of inventory allowed to be packed into a shipping container for the carrier service level during shipping cartonization. The weight of the inventory is derived from the gross weight specified for the item footprint UOM. For this threshold value to take effect, shipping cartonization must be enabled. |
| Maximum Volume | Value that represents the total maximum cubic volume of inventory allowed to be packed into a shipping container for the carrier service level during shipping cartonization. The volume of the inventory is derived from the dimensions specified for the item footprint UOM. For this threshold value to take effect, shipping cartonization must be enabled. |
| Maximum Value | Value that represents the total maximum monetary value of inventory allowed to be packed into a shipping container for the carrier service level during shipping cartonization. The value of the inventory is derived from the unit price on the order line, if specified; otherwise, it is derived from the unit cost specified for the item. For this threshold value to take effect, shipping cartonization must be enabled. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
