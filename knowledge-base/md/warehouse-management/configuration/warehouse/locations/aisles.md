---
title: "Aisles"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/aisles.htm"
source: "/content/aisles.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Warehouse"
  - "Locations"
  - "Aisles"
sections:
  - "Add an aisle"
  - "Delete an aisle"
images: []
source_sha1: 817c72347624b4c68c4de6c03f3dd0b3a703b888
---
# Aisles

An aisle is a passageway in the facility where operators and equipment move between racks or blocks of locations, typically to put away or pick inventory. You typically define aisles and then, in the process of defining storage locations, you can assign locations to the aisle in which they are located (a single location can be assigned to only one aisle).

Aisle assignments are used in the following processes:

-   **Directed putaway**: This process directs inventory to an appropriate storage location based on the configuration of a search path. A search path defines the attributes of inventory that should be directed to a particular storage zone. When defining a search path, you can specify the maximum number of LPNs that can be stored in an aisle within the zone. By limiting the inventory in an aisle, you can ensure better distribution of inventory based on a single item, item family, or client, and reduce the possibility of a large receipt flooding critical forward pickface aisles.
-   **Aisle, dock door and staging lane associations**: These associations are used to direct inbound shipments to the dock door closest to the inventory's putaway locations. They are also used to direct outbound inventory to a staging lane based on the location of the aisle from which the inventory was picked and the dock door at which it will be loaded onto transport equipment. If you configure the association of aisles with staging lanes and staging lanes with dock doors, then the application can direct outbound inventory to the appropriate staging lane, and recommend the optimal dock doors to the user responsible for moving inbound and outbound transport equipment. Choosing an optimal dock door and staging lane can help minimize travel distances and shorten appointment times.

## Add an aisle

You can add one or more aisles by entering a starting and ending identifier. The application then assigns identifiers sequentially to the aisles within the range.

1.  Select **Configuration > Warehouse > Locations > Aisles**.
2.  Click **Add**.
3.  In the **Starting Aisle** field, enter the identifier for the first aisle in the range.
    
    **Note**: An aisle identifier can include numbers and letters. The ending aisle must have the same format and length as the starting aisle. For example, if the starting aisle is 01, the ending aisle can be any two-digit number greater than 01, such as 02-99; if you want the ending aisle to be 100, the starting aisle must be 001 (or any three-digit number less than 100). Alternatively, if the starting aisle is A01, the ending aisle must be a single letter followed by a two-digit number, such as A30. To create a single aisle, enter the same identifier for the starting and ending aisle.
    
4.  In the **Ending Aisle** field, enter the identifier for the last aisle in the range.
5.  Click **Add Aisles**. The new aisles are displayed under Verify Aisles.
6.  To delete a duplicate aisle:
    
    **Note**: Before you can save the new aisles, you must delete any aisle that has the same identifier as an existing aisle.
    
    1.  Under **Verify Aisles**, in the grid, select the check box next to the aisle to delete.
    2.  Click **Delete**. A confirmation message is displayed.
    3.  Click **OK**.
7.  Click **Save**.

## Delete an aisle

You cannot delete an aisle that is currently assigned to a location.

When you delete an aisle that is part of a dock door and staging lane assignment (dock lane assignment), the assignment is also deleted.

1.  Select **Configuration > Warehouse > Locations > Aisles**.
2.  In the grid, select the check box next to the aisle to delete.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
