---
title: "Handling Units"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/handling_units.htm"
source: "/content/handling_units.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inventory"
  - "LPN Handling"
  - "Handling Units"
sections:
  - "Add or modify a handling unit"
  - "Handling Unit fields"
images: []
source_sha1: c9fa1d22ed8824391022522427e739263bdd791f
---
# Handling Units

A handling unit defines the unique identifier and attributes of handling units that are tracked as individuals. Each handling unit that belongs to a handling unit type that is configured as serialized must be defined as an individual handling unit.

## Add or modify a handling unit

1.  Select **Configuration > Inventory > LPN Handling > Handling Units**.
2.  Perform one of the following tasks:
    -   To add a handling unit, click **Add**.
    -   To modify a handling unit, in the grid, click the handling unit.
    -   To copy a handling unit, in the grid, select the check box next to the handling unit, and then click **Copy**.
3.  Enter information in the [Handling Unit fields](#Handling_Unit_fields).
4.  To define features for transport equipment handling units:
    
    **Note**: The **Handling Unit Category** for the handling unit type must be set to Transport Equipment in order to define features.
    
    1.  Under **TRANSPORT EQUIPMENT** select **Features**.
    2.  In the **Available** column, select the features to use.
    3.  In the **Minimum** field, enter the first value in the range of acceptable values.
    4.  In the **Maximum** field, enter the last value in the range of acceptable values.
    5.  Click **Apply**.
5.  Click **Save**.

## Handling Unit fields

 
| Field | Description |
| --- | --- |
| Handling Unit | Unique identifier for a handling unit that is tracked as an individual as well as collectively by handling unit type. You may want to track valuable handling units, such as CHEP pallets, as individuals. All transport equipment handling units are tracked as individuals. Handling units tracked as individuals can be further identified with a serial number. |
| Handling Unit Status | Current condition of the handling unit, such as active or inactive. This value is only used for reporting purposes. |
| Manufacturer ID | Name of the company that produced the individual handling unit. |
| Warranty Date | Date and time that the warranty of the individual handling unit expires. Enter a date or click the calendar to select a date from the display. |
| Client | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. |
| Handling Unit Type | Unique identifier for a serialized handling unit type. A handling unit type represents a group of handling units that have the same characteristics, such as size and weight, as well as whether they are temporary or considered a container. The application tracks the on-hand quantity of handling units by type and, for serialized handling units, by handling unit identifier. |
| Serial Number | Alphanumeric value that can represent the serial number associated with an individual handling unit. |
| Model | Alphanumeric model number for the individual handling unit. Manufacturers use model numbers to differentiate similar products. |
| Purchase Date | Date and time that the individual handling unit was purchased. Enter a date or click the calendar to select a date from the display. |
| Location | Location in the warehouse in which the handling unit is stored. |
| Parent Handling Unit LPN | Unique identifier for another handling unit on or in which this (child) handling unit resides. The two handling units are tracked together; the location of the child handling unit is the same as that of the parent. You cannot specify another child handling unit as a parent handling unit; however, multiple (child) handling units can be associated with a parent. Only available when the handling unit type category is set to Inventory. |
| Transport Equipment Number | Alphanumeric identifier for transport equipment. Transport equipment numbers are not unique, can exist multiple times, and can be associated with various carriers. |
| Carrier | Identifier for the carrier associated with the transport equipment number. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
