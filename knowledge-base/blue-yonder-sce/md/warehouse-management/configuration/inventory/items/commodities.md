---
title: "Commodities"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/commodities.htm"
source: "/content/commodities.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inventory"
  - "Items"
  - "Commodities"
sections:
  - "Freight class"
  - "STCC code"
  - "Add or modify a commodity"
  - "Delete a commodity"
images: []
source_sha1: 98f44f130e5fc4ad5c50d7b4b3bc45ba44c90f4a
---
# Commodities

A commodity is a category created to group items that have the same qualities and specifications, regardless of their source. Commodity codes provide carriers with a standard by which to determine pricing and to simplify the shipment process.

A commodity code can be assigned to an item configuration for use in transportation planning.

## Freight class

An NMFC freight class is a standardized number ranging from 50 to 500 that identifies a commodity group. The higher the number, the more carriers will charge to transport the commodity. The NMFC freight class is the over-the-road industry equivalent of standard transportation commodity code (STCC), which is used by the rail industry.

The application provides many of the commodity freight classes standardized by the National Motor Freight Traffic Association. The National Motor Freight Classification (NMFC) system is a commodity classification system that is used by truckload and less than truckload carriers. Commodities are evaluated according to certain characteristics such as density, stowability, handling, and liability, and then grouped into 1 of 18 unique categories called freight classes. A shipment's freight class is needed in order to calculate freight charges for rating purposes.

A freight class can be assigned to an item configuration for the purpose of transportation planning.

## STCC code

Standard Transportation Commodity Code (STCC) is a comprehensive commodity classification system that is used in the rail industry. The STCC is needed in order to calculate charges for rating purposes.

Commodities are evaluated according to their characteristics, grouped into 1 of 48 unique categories, and assigned a standardized five- to seven-digit numeric code. Moving from left to right, each additional digit of an STCC tells more information about the commodity being transported. The code determines what carriers will charge to transport the commodity.

The codes are maintained by the STCC Technical Committee of the Association of American Railroads (AAR). STCC is the rail equivalent of a freight class.

An STCC code can be assigned to an item configuration for the purpose of transportation planning.

## Add or modify a commodity

Commodities should only be updated to reflect changes made to the standards.

1.  Select **Configuration > Inventory > Items > Commodities**.
2.  Perform one of the following tasks:
    -   To add a commodity, click **Add.**
    -   To modify a commodity, in the grid, click the commodity.
    -   To copy a commodity, in the grid, select the check box next to the commodity, and then click **Copy**.
3.  In the **Commodity Code** and **Description** fields, enter the values.
4.  If the commodity is shipped by truckload or less than truckload carriers, from the **Freight Class** drop-down list, select the freight class that applies.
5.  If the commodity is shipped by rail, in the **STCC Code** field, enter the STCC code that applies.
6.  Click **Save**.

## Delete a commodity

You cannot delete a commodity that is assigned to an item. Commodities should only be updated to reflect changes made to the standards.

1.  Select **Configuration > Inventory > Items > Commodities**.
2.  In the grid, select the check box of the commodity to delete.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
