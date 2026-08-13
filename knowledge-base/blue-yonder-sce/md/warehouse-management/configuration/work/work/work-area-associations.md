---
title: "Work Area Associations"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/work_area_associations.htm"
source: "/content/work_area_associations.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Work"
  - "Work"
  - "Work Area Associations"
sections:
  - "Priority tolerance"
  - "Example: Work area associations"
  - "Setup"
  - "Add or modify a work area association"
  - "Delete a work area association"
images: []
source_sha1: 273d0d18b3b337ade571c8bcb4327eb3f104e5a7
---
# Work Area Associations

A work area association is a configuration that defines the sequence in which the application searches selected work areas to find directed work. With work area associations, the application considers the association between work areas (typically based on proximity) over work priority, while still following the absolute and delta priorities defined for the home and current work areas. Work area associations limit the work areas to which an operator is directed in order to reduce the amount of travel from the completion of one work task to the start of the next.

You can define a move sequence for a work area association to determine the order in which the application considers the work areas, regardless of the priority of the work in the areas. With move sequence and priority, a lower number indicates a higher sequence and priority, with 1 being the highest. For example, assume a work area association between WA1 and WA2 has a sequence of 1, and an association between WA1 and WA3 has a sequence of 2. If work exists in WA2 with a priority of 15 and work in WA3 has a priority of 10, then the application directs the operator to WA2, even though WA3 has higher priority work. This is because the move sequence from WA1 to WA2 is higher (lower number) than the association between WA1 and WA3.

Work area associations are enabled at the warehouse level and also for warehouse equipment types. For example, you can enable work area associations for hand trucks but disable them for fork trucks. If a hand truck operator completes work in an area configured with a work area association, then the application considers existing work in the associated work area as well as the operator's current work area. Based on the delta priority of the current work area and the priority tolerance, the application either directs the operator to the associated work area or finds work from the current work area.

**Note**: Work area associations must be reciprocated for the application to direct an operator from a move area back to the current work area, unless it is the operator's home work area. For example, assume a work area association exists between WA1 (current work area) and WA2 (move work area). If an operator is directed from WA1 to WA2 to perform work, then another association must exist between WA2 (current work area) and WA1 (move work area) for the application to direct the operator back to WA1. However, if the operator specified WA1 as the home work area during the login process, then the application can direct the operator to WA1 without an association.

### Priority tolerance

The application calculates priority tolerance to determine whether an operator is presented work in the current area or directed to the first sequential work area. Priority tolerance is defined as the highest priority work in the current work area minus the defined delta priority of the current work area. If the priority of the work in the first sequential work area is higher than the priority tolerance of the current work area, then the application directs the operator out of the current work area. However, if the priority of work in the first sequential work area is not higher than the priority tolerance of the current area, then the application will not direct the operator to another associated work area with a lower move sequence, even if the work priority is higher than the tolerance.

For example, assume the current work area (CWA) has an association with work area 1 (WA1) with a move sequence of 1, and an association with work area 2 (WA2) with a move sequence of 2. If the current work area (CWA) has a delta priority of 15, and the highest priority work in the area is 40, then the priority tolerance is 25 (40 - 15 = 25). If work with a priority of 20 exists in WA1, then the application directs the operator to WA1, because it has the highest move sequence (1) and the work priority (20) is higher than the priority tolerance (25) of CWA.

However, if the work in WA1 has a priority of 30, and there is work in WA2 with a priority of 20, then the operator is directed to perform the work in CWA with a priority of 40, even though WA1 and WA2 have higher priority work. The operator is not directed to WA1 because the work has a lower priority (30) than the priority tolerance (25). The operator is not directed to WA2 because the area has a lower move sequence (2) than WA1 (1).

### Example: Work area associations

The following table is an example configuration of work area associations.

  
| Current Work Area | Move Work Area | Move Sequence |
| --- | --- | --- |
| WA1 | WA2 | 1 |
| WA1 | WA3 | 2 |
| WA3 | WA2 | 1 |
| WA3 | WA4 | 1 |

The following scenarios explain how the application presents directed work to an operator based on the work area associations. For these examples, assume the delta priority of work area WA1 and WA3 is 15.

#### Scenario 1

-   **Assumption**: The priority of work in WA1 is 40, WA2 is 30, and WA3 is 10; the priority tolerance of WA1 is 25 (40 - 15)
-   **Result**: Work in WA3 falls within the priority tolerance (10 is a higher priority than 25), but since the move sequence from WA1 to WA3 is higher than the other work areas, the work in WA3 is not presented to the operator. The work in WA2 does not fall within the priority tolerance (30 is lower priority than 25), so the work in WA2 is also not presented to the operator. Instead, the application directs the operator to the work with priority 40 in WA1.

#### Scenario 2

-   **Assumption**: The priority of work in WA1 is 40, WA2 is 24, and WA3 is 10; the priority tolerance of WA1 is 25 (40 - 15)
-   **Result**: Work in WA3 falls within the priority tolerance (10 is a higher priority than 25), but since work exists in WA2, which has a higher move sequence, the work in WA3 is not presented to the operator. The work in WA2 falls within the priority tolerance (24 is a higher priority than 25), and WA 2 is the first move sequence from WA1, so the application directs the operator to the work with priority 24 in WA2.

#### Scenario 3

-   **Assumption**: The priority of work in WA1 is 40, WA2 has no work, and WA3 is 10; the priority tolerance of WA1 is 25 (40 - 15)
-   **Result**: Work in WA3 is within the priority tolerance (10 is a higher priority than 25), but since it has a move sequence of 2, and work exists in the current work area WA1, the application directs the operator to the work with priority 40 work in WA1.

#### Scenario 4

-   **Assumption**: The priority of work in WA3 is 40, and the priority of work in WA2 and WA4 is 10; the priority tolerance of WA3 is 25 (40 - 15); Warehouse Labor Management is integrated with Warehouse Management, directed work by proximity is enabled, and the work location in WA4 has closer proximity to WA3 than the work in WA2.
-   **Result**: Work in WA2 and WA4 falls within priority tolerance (10 is a higher priority than 25). Since the work aisle in WA4 is physically closer to the operator's current aisle in WA3, the application directs the operator to W4 instead of WA2. If two work area associations have the same move sequence, then the higher priority work is presented since there is no move sequence to differentiate the areas.

**Notes**: 

-   If the current work area has no associated work areas, then the application can send the operator to any work area based on delta priority and absolute priority. However, if the current work area has associations, but no work is available in those areas, then the application will not send the operator to another work area outside of the associated areas (even if higher priority work exists).
-   If a work task is assigned to a specific operator, that work takes priority over the logic for work area associations. That is, the application will ignore the work area associations and present the assigned task to the operator.
-   If the operator or warehouse equipment is not authorized to perform the work, or if the work would exceed the warehouse equipment limit, then it is not presented to the operator.

### Setup

You must perform the following tasks to use work area associations:

1.  Enable work area associations for the warehouse. See [Configure work RF settings](work-rf-settings.md).
2.  Enable work area associations for warehouse equipment types. See [Add or modify a warehouse equipment type](../../equipment/equipment/warehouse-equipment-type.md).
3.  Configure work area associations. See [Add or modify a work area association](#Add_or_modify_a_work_area_association).
4.  If Warehouse Labor Management is integrated, enable directed work by proximity. See [Directed work by proximity](work-operations.md).

## Add or modify a work area association

1.  Select **Configuration > Work > Work > Work Area Associations**.
2.  Perform one of the following tasks:
    -   To add a work area association, click **Add**.
    -   To modify a work area association, in the grid, click the current work area.
3.  Enter information in the following fields:
    

 
| Field | Description |
| --- | --- |
| Current Work Area | Name of the work area in which an operator is currently working. The application uses the current work area to determine which work areas the operator can be directed to based on the defined associations. For example, if WA1 is the **Current Work Area**, then when an operator completes work in the area, the application considers the operator's home work area (if specified during the login process), the current work area (WA1), and any move work areas defined in an association with WA1. |
| Move Work Area | Name of the work area in which the application looks for work based on the current work area, and to which an operator can be directed from the current work area. The application considers all move work areas, and their respective move sequences, defined for the current work area to find the next directed work task to present to the operator. For example, if WA1 is the **Current Work Area** and WA2 is the **Move Work Area**, then when an operator completes work in WA1, the application considers the operator's home work area (if specified during the login process), the current work area (WA1), and the associated move work area (WA2). |
| Move Sequence | Sequence number that determines the order in which the application considers the work areas associated with the Current Work Area, regardless of the priority of the work in the areas. With move sequence, a lower number indicates a higher sequence, with 1 being the highest. For example, assume a work area association between WA1 and WA2 has a sequence of 1, and an association between WA1 and WA3 has a sequence of 2. If work exists in WA2 with a priority of 15 and work in WA3 has a priority of 10, then the application directs the operator to WA2, even though WA3 has higher priority work. |

5.  Click **Save**.

## Delete a work area association

1.  Select **Configuration > Work > Work > Work Area Associations**.
2.  In the grid, select the check box next to the association to delete.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
