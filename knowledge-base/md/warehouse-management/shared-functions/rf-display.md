---
title: "RF Display"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/rf_display.htm"
source: "/content/rf_display.htm"
toc_path:
  - "Warehouse Management"
  - "Shared functions"
  - "RF Display"
sections:
  - "View RF devices"
  - "RF Display fields"
images: []
source_sha1: 90cb0c774ba6bdabc1d34907d95db8705fc61c69
---
# RF Display

The RF Display page is accessible from the following modules: **Inventory**, **Outbound Planner**, **Picking**, **Production**, **Receiving**, **Shipping**, or **Yard**. You can use this page to view a list of RF and mobile devices that are currently logged in to the application.

## View RF devices

1.  View the RF Display page.
    
    1.  Select one of the following modules: **Inventory**, **Outbound Planner**, **Picking**, **Production**, **Receiving**, **Shipping**, or **Yard**.
    2.  Select **RF Display**.
    
2.  View the [RF Display fields](#RF_Display_fields).

## RF Display fields

 
| Field | Description |
| --- | --- |
| Warehouse ID | Unique ID associated with the warehouse. |
| Device Code | Unique identifier for a piece of equipment such as a radio frequency (RF) or mobile device that has access to or communicates with the application. The device code is the display name for the device and represents a logical location during warehouse operations. For example, during picking, an inventory display shows the device code as the location of the inventory until the inventory is deposited. |
| Last User ID | Operator that is currently logged in to the RF or mobile device. |
| Current Work Area | Work area in which the RF or mobile device is currently in use. |
| Current Work Zone ID | Work zone in which the RF or mobile device is currently in use. |
| Current Location | Location in which the RF or mobile device is currently in use. |
| Home Work Area | Home work area selected by the operator. The home work area is used for work management purposes to reduce travel by primarily (depending on priorities) offering the operator directed work that originates in their home work area. |
| Equipment | Identifier for the equipment or material handling unit used in warehouse operations. |
| RFT Mode | Work mode currently selected by the user.<br>-   • **D**: Directed work acknowledged through RF directed work.
<br>-   • **U**: Undirected work performed through a selected RF menu option. |
| Activity Date | Indicates the last login activity date on the RF or mobile device. |
| Last Modified Date | Date and time at which an operation was last performed. |
| Building ID Filter | Building in which the work request is issued for directed work operations. Only displayed if directed work filters are enabled. |
| Last Modified By | Username of the last person who performed an operation using the RF or mobile device. |
| Aisle ID Filter | Aisle in which the work request is issued for directed work operations. Only displayed if directed work filters are enabled. |
| Work Zone ID Filter | Work zone in which the work request is issued for directed work operations. Only displayed if directed work filters are enabled. |
| Home Work Area Absolute Priority | Number that defines the priority at which the application moves an operator back to their home work area (if signed on) when they are servicing a request in another work area. If a work request with a priority higher than the home work area absolute priority exists in the operator's home work area while the operator is in another work area, the operator is directed to the home work area to perform the work. |
| LPN Equipment Limit | Maximum number of LPNs that can reside on a piece of equipment before an operator is prompted to deposit them. A value of "0" indicates an unlimited number of LPNs. It also represents the number of directed pick work assignments that a voice operator can select to perform at the same time. See [Warehouse equipment LPN limits](../configuration/equipment/equipment/warehouse-equipment-type.md). |
| Resource ID | A combination of the device code and warehouse ID. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
