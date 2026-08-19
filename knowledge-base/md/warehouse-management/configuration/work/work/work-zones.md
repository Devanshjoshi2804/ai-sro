---
title: "Work Zones"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/work_zones.htm"
source: "/content/work_zones.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Work"
  - "Work"
  - "Work Zones"
sections:
  - "Work zone priorities"
  - "Zone consolidation"
  - "Add or modify a work zone"
  - "Consolidate zones"
  - "Work Zone fields"
images: []
source_sha1: 840058931dc767dd98398dc4bf492fe883843f1b
---
# Work Zones

A work zone is a designated area within a work area, and is typically defined as a group of locations that are in the same general vicinity. For example, an entire narrow-aisle area can be considered a single work area, and each aisle can be set up as a separate work zone.

Work zones are configured for the following purposes:

-   To limit travel by defining the work request priorities that keep operators within a work zone whenever possible
-   To reduce congestion in a work zone by limiting the equipment that can be offered directed work in the zone

**Note**: You need to create work areas before you create work zones. See [Work Areas](work-areas.md).

## Work zone priorities

The application uses work zone priorities along with other considerations to determine which piece of directed work to present to an operator. When an operator signs on to directed work, the application considers the following factors:

-   Permission settings for the operator and the equipment
-   Priority of the work in the work queue
-   Proximity of the work in the warehouse

**Note**: Work zone priorities are designed to make sure that operators are working efficiently, but they do not override operator and equipment authorizations. That is, operators are not directed to perform work that they or their equipment are not authorized to perform.

While the application checks for the best work to give the operator, the application compares the priority of pending work inside of the operator's current work zone with the priority of work in other work zones. If work outside of the operator's current work zone is more important, the application gives the operator that work. The work that is presented to the operator is based, in part, on the following priorities defined for the work zone:

-   **Delta priority**: If work in another work zone is of a higher priority than work in the current work zone, and the difference exceeds the delta priority, the operator is presented the work in the other work zone. Effective priority is the current priority of a work request in the work queue.
-   **Absolute priority**: If the priority of work in another work zone exceeds the absolute priority, then the operator is presented the work in the other work zone.

**IMPORTANT**: With priority, the lower the number, the higher the priority. For example, 1 is the highest priority; 10 is a higher priority than 20.

See [Work management priorities](work-operations.md).

## Zone consolidation

You can use the Consolidate action, available from any zone configuration grid, to consolidate zones that share a common configuration into a single (original) zone. You can consolidate the following types of zones: count zones, movement zones, pick zones, storage zones, and work zones. See [Consolidate zones](#Consolidate_zones).

When you select a zone and use the Consolidate action, the application presents a list of zones that have a configuration that matches the selected (original) zone. You can then select one or more of the matching zones to consolidate to the original zone.

During consolidation, the application performs the following tasks:

-   Updates all the configurations and references for the zones that are being consolidated to now use the original zone. For example, if PickZone2 and PickZone3 are consolidated into PickZone1, then the locations assigned to PickZone2 and PickZone3 are reassigned to PickZone1.
-   Removes the consolidated zones and retains the original zone.
-   Displays a progress bar that shows the processing status of the consolidation.
-   When consolidation is complete, displays the list of any remaining consolidation candidates that match the original zone. This allows you to continue consolidating to the original zone.

The same process is available for location types using the location type configuration. See [Location type consolidation](../../warehouse/locations/location-types.md).

## Add or modify a work zone

1.  Select **Configuration > Work > Work > Work Zones**.
2.  Perform one of the following tasks:
    -   To add a work zone, from the **Actions** drop-down list, select **Add**.
    -   To modify a work zone, in the grid, click the work zone.
    -   To copy a work zone, in the grid, select the check box next to the work zone, and then from the **Actions** drop-down list, select **Copy**.
3.  Enter information in the [Work Zone fields](#Work_Zone_fields).
4.  Click **Layout** or **Next**.
5.  To draw the work zone on the warehouse map for the selected building:
    1.  Click **View**, and then select the check box for each option that you want to display on the warehouse map.
    2.  Click **Draw**, and then move and size the shape on the page.
6.  Click **Finish**.
    
    **Note**: To assign locations to a work zone, see the information on modifying multiple locations in [Location configuration process](../../warehouse/locations.md).
    

## Consolidate zones

You use the following procedure to consolidate zones that have the same configurations into a single (original) zone. See [Zone consolidation](#Zone_consolidation).

**Note**: Zones cannot be consolidated if outstanding work references the selected zone.

1.  Perform one of the following tasks:
    -   For count zones, select **Configuration > Inventory > Counting > Count Zones.**
    -   For movement zones, select **Configuration > Inventory > Movement > Movement Zones.**
    -   For pick zones, select **Configuration > Outbound > Allocation > Pick Zones.**
    -   For storage zones, select **Configuration > Inbound > Storage > Storage Zones.**
    -   For work zones, select **Configuration > Work > Work > Work Zones.**
2.  In the grid, select the zone to which duplicate zones will be consolidated. This becomes the original zone that remains after the duplicate zones have been removed. This is also the zone to which references and configurations are reassigned.
3.  From the **Actions** drop-down list, select **Consolidate**. A list of zones that have the same configuration as the original zone are displayed.
4.  In the grid, select the check box next to the zones to consolidate. The selected zones will be removed after consolidation takes place.
5.  Click **Save**. The selected zones are removed, and the Consolidation page displays the remaining zones, if any, that match the original zone.

## Work Zone fields

 
| Field | Description |
| --- | --- |
| Work Zone | Name or number that identifies a work zone. A work zone is a logical division of warehouse space made on the basis of physical layout and access by different types of warehouse equipment. A work zone exists inside a work area. |
| Description | Text that further describes the zone. |
| Out of Service | If Yes, the work zone is not available. The application does not offer to operators directed work that must be performed in a work zone that is out of service.<br > If No, the work zone is available for operators to perform directed work. |
| Work Area | For the purpose of work management, area of the warehouse in which similar types of operations are performed. For example, narrow-aisle storage and floor storage can be configured as different work areas if each supports different types of operations and different types of equipment. |
| Building | Building in which the work zone resides. |
| Zone Travel Sequence | Numeric value, ranging from low to high, that identifies the travel sequence from one work zone to another, regardless of work area boundaries. Movement from one work zone to another is accomplished through the use of travel sequence assignments. |
| Absolute Priority | Number that defines the priority at which the application moves an operator out of a work zone to perform work in another work zone. If a work request with a priority higher than the absolute priority exists in another work zone, the operator is presented work in the other work zone. |
| Delta Priority | Number that the application uses to determine when to move an operator out of a work zone to perform work in another work zone. The delta priority is the difference between the highest priority work in the current work zone and the highest priority work in another work zone that must exist before the operator is presented work to perform in the other work zone. |
| Equipment Limit | Maximum number of logged-in equipment allowed in the work zone at one time. The application will not issue more work in a work zone if the equipment currently executing work requests in that work zone exceeds this number.<br > Leave this field blank if there is no limit to the equipment allowed to access the work zone. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
