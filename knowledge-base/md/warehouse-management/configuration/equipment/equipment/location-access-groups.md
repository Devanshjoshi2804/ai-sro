---
title: "Location Access Groups"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/location_access_groups.htm"
source: "/content/location_access_groups.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Equipment"
  - "Equipment"
  - "Location Access Groups"
sections:
  - "Add or modify a location access group"
  - "Delete a location access group"
images: []
source_sha1: 318c18618bf52f97b61276f4b15b0536c5219256
---
# Location Access Groups

A location access group is a code that can be assigned to warehouse equipment and locations. It is used to prevent an RF operator from being offered directed work in locations that are incompatible with the operator's equipment. The application permits access to a location when the location access group assigned to the location matches the location access group assigned to the equipment. Each location is assigned a single location access group, but equipment can be assigned multiple location access groups.

For example, within your facility, a fork truck may be assigned a location access group called Low Locations. This means that an operator performing directed work with the fork truck is only offered work in locations that have the same location access group. However, if a handheld terminal is assigned the High Locations and Low Locations access groups, it can be used to perform work in locations that are assigned either of those access groups.

## Add or modify a location access group

1.  Select **Configuration > Equipment > Equipment > Location Access Groups**.
2.  To add a location access group:
    1.  Click **Add**.
    2.  In the **Location Access Group**, **Description**, and **Short Description** fields, enter the information.
    3.  Click **Save**.
3.  To modify the description of a location access group:
    1.  In the grid, click the description to modify, and then enter the information.
    2.  Click **Save**.
4.  To change the sort sequence:
    
    **Note**: The sort sequence determines the order in which the location access groups are listed, such as for selection from a drop-down list.
    
    1.  In the grid, select a row and drag it to the position you want. The application automatically updates the sort sequence.
    2.  Click **Save**.
5.  To translate the description of location access groups:
    1.  Perform one of the following tasks:
        -   To translate specific rows, in the grid, select the check box of the rows, and then above the grid, click **Translation**.
        -   To translate all rows, above the grid, click **Translation**.
    2.  From the **Destination Locale** drop-down list, select the locale.
    3.  In the grid, select a translated description or short description, and then enter the new value.
    4.  Click **Save**.

## Delete a location access group

You cannot delete a location access group that is currently assigned to equipment or to a location.

1.  Select **Configuration > Equipment > Equipment > Location Access Groups**.
2.  In the grid, select the check box next to the location access group to delete.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
