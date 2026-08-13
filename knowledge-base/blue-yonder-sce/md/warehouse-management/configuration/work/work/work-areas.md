---
title: "Work Areas"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/work_areas.htm"
source: "/content/work_areas.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Work"
  - "Work"
  - "Work Areas"
sections:
  - "Work area priorities"
  - "Add or modify a work area"
  - "Delete a work area"
  - "Work Areas fields"
images: []
source_sha1: adf42317f2163fcf5240f0c000cb4df7bb6350f7
---
# Work Areas

For work management purposes, the warehouse is divided into work areas. A work area represents an area of the warehouse where similar types of operations are performed and is used to direct operators to their work. For example, dock and pallet storage can be set up as different work areas with each work area supporting different operations and allowing different equipment.

When operators log onto the RF and enter their home work area, they will be directed to work in that work area. When work with a higher priority exists outside their home work area, they will be directed to that work area. Once that work is complete, they will be directed back to their home work area. Home work areas can change from day to day. For example, one day an operator's home work area could be DOCK, and the next day it could be PRODUCTION.

However, if work area associations are enabled, then the work area to which an operator is directed is dependent on the defined associations as well as priority. A work area association is a configuration that defines the sequence in which the system searches selected work areas to find directed work. With work area associations, the system considers the association between work areas (typically based on proximity) over work priority, while still following the absolute and delta priorities defined for the home and current work areas. See [Work Area Associations](work-area-associations.md).

**Note**: Work zones are sections in a work area. A work area can include one work zone or many work zones. For example, a dock work area may include two work zones (one for receiving and another for shipping), or a pallet storage work area spread across 10 aisles can include 10 work zones (one work zone for each aisle). See [Work Zones](work-zones.md).

## Work area priorities

The application uses work area priorities along with other considerations to determine which piece of directed work to present to an operator. When an operator signs on to directed work, the application considers the following factors:

-   Permission settings for the operator and the equipment
-   Priority of the work in the work queue
-   Proximity of the work in the warehouse

**Note**: Work area priorities are designed to make sure that operators are working efficiently, but they do not override operator and equipment authorizations. That is, operators are not directed to perform work that they or their equipment are not authorized to perform.

While the application checks for the best work to give the operator, the application compares the priority of pending work inside of the operator's current work area with the priority of work in other work areas. If work outside of the operator's current work area is more important, the application gives the operator that work. The work that is presented to the operator is based, in part, on the following priorities defined for the work area:

-   **Delta priority**: If work in another work area is of a higher priority than work in the current work area, and the difference exceeds the delta priority, the operator is presented the work in the other work area. Effective priority is the current priority of a work request in the work queue.
-   **Absolute priority**: If the priority of work in another work area exceeds the absolute priority, then the operator is presented the work in the other work area.
-   **Home work area absolute priority**: If work in the operator's home work area is greater than the home work area absolute priority, and the operator is currently in another work area, the operator is presented the work in the operator's home work area.

**IMPORTANT**: With priority, the lower the number, the higher the priority. For example, 1 is the highest priority; 10 is a higher priority than 20.

See [Work management priorities](work-operations.md).

If work area associations are enabled, then the work area to which an operator is directed is dependent on the defined associations as well as priority. A work area association is a configuration that defines the sequence in which the system searches selected work areas to find directed work. With work area associations, the system considers the association between work areas (typically based on proximity) over work priority, while still following the absolute and delta priorities defined for the home and current work areas. See [Work Area Associations](work-area-associations.md).

## Add or modify a work area

1.  Select **Configuration > Work > Work > Work Areas**.
2.  Perform one of the following tasks:
    -   To add a work area, click **Add**.
    -   To modify a work area, in the grid, click the work area.
    -   To copy a work area, in the grid, select the check box next to the work area, and then click **Copy**.
3.  Enter information in the [Work Areas fields](#Work_Areas_fields).
4.  Click **Save**.

## Delete a work area

You cannot delete a work area if it contains one or more work zones.

1.  Select **Configuration > Work > Work > Work Areas**.
2.  In the grid, select the check box next to the work area to delete.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Work Areas fields

 
| Field | Description |
| --- | --- |
| Work Area | For the purpose of work management, area of the warehouse in which similar types of operations are performed. For example, narrow-aisle storage and floor storage can be configured as different work areas if each supports different types of operations and different types of equipment. |
| Description | Text that further describes the work area. |
| Voice Code | Code used to represent the piece of equipment in facilities that use voice terminals. When the voice terminal operator is prompted for the equipment, the operator can speak the voice code to identify the equipment to the application. |
| Home Work Area Absolute Priority | Number that defines the priority at which the application moves an operator back to their home work area (if signed on) when they are servicing a request in another work area. If a work request with a priority higher than the home work area absolute priority exists in the operator's home work area while the operator is in another work area, the operator is directed to the home work area to perform the work. |
| Absolute Priority | Number that defines the priority at which the application moves an operator out of a work area to perform work in another work area. If a work request with a priority higher than the absolute priority exists in another work area, the operator is presented work in the other work area. |
| Delta Priority | Number that the application uses to determine when to move an operator out of a work area to perform work in another work area. The delta priority is the difference between the highest priority work in the current work area and the highest priority work in another work area that must exist before the operator is presented work to perform in the other work area. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
