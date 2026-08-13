---
title: "Dock Access Groups"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/dock_access_groups.htm"
source: "/content/dock_access_groups.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Warehouse"
  - "Locations"
  - "Dock Access Groups"
sections:
  - "Add or modify a dock access group"
  - "Delete a dock access group"
images: []
source_sha1: 3e3a8b9fc8db9619771f99ada99603fe8ab7d29d
---
# Dock Access Groups

A dock access group is an attribute that can be assigned to transport equipment types and dock door locations. The application uses the dock access group to sort and display door locations based on the transport equipment type. During check in and when moving equipment to a door location, if the dock access group assigned to an available door location is also assigned to the type of transport equipment being checked in, then the door location is displayed first in the list of available locations (before the mismatched doors). The remaining available doors that have either no or a different dock access group are listed (with the Access Mismatch tag) after the matching doors. Mismatched doors are not restricted; you can check in or move transport equipment to any optimal or available door location that is displayed.

For example, assume side load transport equipment must be parked parallel to the warehouse, and rear load equipment is parked perpendicular to the warehouse. You can create two dock access groups (Side Load and Rear Load) and then assign each access group to the relevant equipment type, and to the door locations that accommodate each type. When side load equipment is checked in, the locations that share the same dock access group are displayed first, followed by the mismatched locations (either no or a different dock access group).

Each dock door location can be assigned a single dock access group, but a single transport equipment type can be assigned multiple dock access groups. See [Transport Equipment Type](../../equipment/equipment/transport-equipment-type.md).

**Notes**:

-   Dock access groups may be considered when the application assigns picks for a shipment to a staging lane. For example, assume an outbound shipment is assigned to a load that is assigned to transport equipment. During staging lane assignment, the application considers the type of transport equipment assigned to the load, and then selects the best staging lane that is also associated to a dock door with a dock access group that matches the equipment type. If there are no matching doors, the application selects the best staging lane regardless of dock access.
-   Dock access groups work in conjunction with optimal door assignments. If you have optimal door assignment configured, during check in and transport equipment moves, optimal dock doors are listed before available door doors. Within each separate group of door locations, doors with a matching dock access group are listed first, followed by the doors with either no or a different dock access group.

## Add or modify a dock access group

1.  Select **Configuration > Warehouse > Locations > Dock Access Groups**.
2.  To add a dock access group:
    1.  Click **Add**.
    2.  In the **Dock Access Group**, **Description**, and **Short Description** fields, enter the information.
    3.  Click **Save**.
3.  To modify the description of a dock access group:
    1.  In the grid, click the description to modify, and then enter the information.
    2.  Click **Save**.
4.  To change the sort sequence:
    
    **Note**: The sort sequence determines the order in which the location access groups are listed, such as for selection from a drop-down list.
    
    1.  In the grid, select a row and drag it to the position you want. The application automatically updates the sort sequence.
    2.  Click **Save**.
5.  To translate the description of dock access groups:
    1.  Perform one of the following tasks:
        -   To translate specific rows, in the grid, select the check box of the rows, and then above the grid, click **Translation**.
        -   To translate all rows, above the grid, click **Translation**.
    2.  From the **Destination Locale** drop-down list, select the locale.
    3.  In the grid, select a translated description or short description, and then enter the new value.
    4.  Click **Save**.

## Delete a dock access group

1.  Select **Configuration > Warehouse > Locations > Dock Access Groups**.
2.  In the grid, select the check box next to the dock access group to delete.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
