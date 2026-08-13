---
title: "Address"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/admin/address.htm"
source: "/content/admin/address.htm"
toc_path:
  - "Administration"
  - "System Administrator"
  - "Configuration"
  - "System"
  - "Address"
sections:
  - "Add or modify an address"
  - "Delete an address"
  - "Address fields"
images: []
source_sha1: af90abe9229d038578b195d71d3cc0c060a1c6bc
---
# Address

An address is a set of contact information that can be assigned to an entity, such as a customer, user, warehouse, carrier, or in a 3PL environment, a client. An address may include a postal address, URL address, email address, telephone number, fax number, attention name, contact information, and an indication of whether the information is for a temporary address or represents a residence. In addition, you can define contact information for the receiving and shipping departments at the address.

Once you assign an address to one or more entities, if you update the address information it is automatically updated for all of the entities to which the address is assigned. The update also changes the historical data associated with the address. For example, if the ship-to address for a customer is modified, then the ship-to address on orders previously sent to that customer is changed to the new address.

**IMPORTANT**: If you want to update address information, but you do not want historical data to be changed, then you must create a new address and associate the new address with the entity. From that point on, the new address is used and the historical data is not affected.

You use the Address page to maintain address information. Alternatively, you can define addresses when you define clients, customers, and users.

## Add or modify an address

1.  Select **System Administrator > Configuration > ** **System > Address**.
2.  Perform one of the following tasks:
    -   To add a new address, from the **Actions** drop-down list, select **Add**.
    -   To copy an address, in the grid select the check box next to the address, and then from the **Actions** drop-down list, select **Copy**.
    -   To modify an address, in the grid select the check box next to the address, and then from the **Actions** drop-down list, select **Edit**.
3.  Enter information in the [Address fields](#Address_fields).
4.  Click **Save**. A confirmation message is displayed.
5.  Click **OK**.

## Delete an address

1.  Select **System Administrator > Configuration > ** **System > Address**.
2.  In the grid, select the check box next to the address.
3.  From the **Actions** drop-down list, select **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Address fields

 
| Field | Description |
| --- | --- |
| Address Name | Identifier for address information. The address name typically identifies the individual or organization with which an address is associated. |
| Client ID | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. |
| Address Type | Indicates the type of entity to which the address pertains, such as a client, customer, or user. The application uses this information to limit address lookups as appropriate. |
| Address Line 1 | Line one for the address. This is the physical address information (such as house, building or PO box numbers, street names, or suite or floor numbers). |
| Address Line 3 | Line three for the address. |
| Address State | State for the address. |
| Country Name | Name or code name of the country. |
| Last Name | Last name of the individual. For a carrier, client, or customer, this is the person to whom correspondence should be directed. |
| Honorific | Title, such as Mr., Mrs., or Dr., of the individual. For a carrier, client, or customer, this is the person to whom correspondence should be directed. |
| Residential Address | Indicates that the address information represents a residence. |
| PO Box Address | Indicates whether the address is a post office box. If deselected, indicates that the address is not a post office box but is a physical address. |
| Pool Rating Service Name | Identifier of the rating service that is used for the pool point. Available only when Transportation Manager is installed and the **Pool Point** check box is selected. |
| Latitude | Line of latitude for the address's location. Enter the latitude in decimal format (for example, 40.269 or -75.317). |
| Receiving Attention Name | Name that should be used in the correspondence sent to this address regarding receiving operations and inbound freight. |
| Receiving Attention Phone | Phone number of the person for whom correspondence is sent to this address regarding receiving operations and inbound freight. |
| Site Type | Customs site type assigned to the address of the warehouse from which the outbound order is shipped. The site type indicates whether the warehouse is bonded, and if it is bonded, the type of bonded warehouse.<br>-   • **Customs**: The address is a bonded warehouse that contains inventory for which customs duties must be paid. Customs duties are assessed against goods (other than alcoholic beverages and tobacco products) that have been imported from the European Union (EU).
<br>-   • **Customs and Excise**: The address is a bonded warehouse that contains inventory for which both customs and excise duties must be paid. Excise duties are assessed against goods such as alcoholic beverages and tobacco products.
<br>-   • **No selection (blank)**: The address is not a bonded warehouse and only duty paid items can be received.
<br > Only available if the customs functionality is enabled. |
| Receiving Fax | Fax number for this address corresponding to its receiving operations and inbound freight. |
| GLN | Global Location Number. An alphanumeric code, assigned by the European Article Numbering Uniform Code Council (EAN/UCC), that is used to identify a legal entity (such as a supplier or customer), a physical entity (such as a warehouse, loading dock, or delivery point), or a functional entity (such as an accounting department or returns department). The GLN is a 13-digit code that contains an EAN/UCC company prefix, a location reference, and a check digit.<br > Only available if the customs functionality is enabled. |
| Shipping Attention Name | Name that should be used in the correspondence sent to the address regarding shipping operations and outbound freight. |
| Shipping Contact Name | Name of the person who may be contacted with questions or concerns regarding shipping operations and outbound freight. |
| Shipping Contact Title | Title of the person who may be contacted with questions or concerns regarding shipping operations and outbound freight. |
| Shipping Fax Number | Fax number for this address corresponding to its shipping operations and outbound freight. |
| Pager Number | The pager number of person who may be contacted with questions or concerns regarding receiving operations and inbound freight. |
| Web Address | URL for the internet site of the individual or organization associated with the address. |
| Host External ID | Alternate identifier for the address information. This identifier is typically sent from the host, and it is used to reconcile address information with the information contained in the host application. |
| Address ID | A system-generated value that identifies an individual or organization and an address. |
| Locale Id | Identifier for a locale. A locale defines the attributes for a language that affect how information is displayed in the application. |
| Address Line 2 | Line two for the address. |
| Address City | City for the address. |
| Postal Code | Postal code for the address. |
| Region | Geographical region within the country for the address. |
| First Name | First name of the individual. For a carrier, client, or customer, this is the person to whom correspondence should be directed. |
| Address District | Postal district for the address. This information is typically used outside of the United States. |
| Pool Point | Indicates whether load consolidation and distribution is performed at the address. Available only when Transportation Manager is installed. |
| Temporary | Indicates whether the address is temporary. |
| Time Zone | Time zone for the address. |
| Longitude | Line of longitude for the address's location. Enter the longitude in decimal format (for example, 40.269 or-75.317). |
| Receiving Contact Name | Name of the person who may be contacted with questions or concerns regarding receiving operations and inbound freight. |
| Receiving Contact Title | Title of the person who may be contacted with questions or concerns regarding receiving operations and inbound freight. |
| Transaction Type | Tax approval number. This number is obtained from the internal revenue service for the United Kingdom, and is required for a bonded warehouse if the value for the **Site Type** field is **Customs and Excise**.<br > Only available if the customs functionality is enabled. |
| Email Address | Address at which the individual or organization associated with the address receives electronic mail. For example: [\[email protected\]](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/admin/cdn-cgi/l/email-protection) |
| Receiving Phone Number | Telephone number for the address corresponding to its receiving operations and inbound freight. |
| Group Name | Identifier used by Blue Yonder product teams to indicate the product group that was responsible for loading data (in a particular row of a table). For example, standard group names include dcs\_data, mcs\_data, sal\_data, and so on. This field is display only. |
| Shipping Attention Phone | Phone number of the person for whom correspondence is sent to the address regarding shipping operations and outbound freight. |
| Shipping Contact Phone | Phone number of the person who may be contacted with questions or concerns regarding shipping operations and outbound freight. |
| Shipping Email Address | Address at which the individual or organization associated with this address receives email corresponding to its shipping operations and outbound freight. Example: [\[email protected\]](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/admin/cdn-cgi/l/email-protection). |
| Shipping Phone | Telephone number for the address corresponding to its shipping operations and outbound freight. |
| Shipping Web Address | URL for the internet site for this address corresponding to its shipping operations and outbound freight. |
| User Display | User first and last names for display with USR type addresses. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
