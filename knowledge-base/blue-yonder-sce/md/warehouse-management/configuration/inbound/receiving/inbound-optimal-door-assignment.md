---
title: "Inbound Optimal Door Assignment"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/inbound_optimal_door_assignment.htm"
source: "/content/inbound_optimal_door_assignment.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inbound"
  - "Receiving"
  - "Inbound Optimal Door Assignment"
sections:
  - "Optimal door assignment setup"
  - "Configure optimal door assignment settings and rules"
  - "Rule fields"
images: []
source_sha1: ceea69332fc35c7d79e587364bf2cb9ebeea7873
---
# Inbound Optimal Door Assignment

Optimal door assignment is the process by which the application recommends the best dock door for inbound transport equipment based on the putaway locations required for the inbound inventory. The optimal dock door is one that is associated with the staging lane and aisle in which expected inventory will be stored so that travel distance is minimized.

When optimal dock doors are presented, an operator can choose a different dock door at any point in the check-in or move process. If the application does not provide an optimal dock door, the operator must select a dock door. If the primary door is unavailable, the application may provide another dock door that is between the two locations with the most putaway assignments.

The following process determines the optimal dock door:

1.  The application evaluates the inbound shipment information to determine whether the inventory matches any of the rules defined for the optimal door assignment for the building.
2.  If a rule is found, the application evaluates storage search paths to find a storage zone for the inventory.
3.  If a storage zone is found, the application evaluates the dock lane assignments to find the dock door and staging lane associations for the aisle in which the inventory will be stored. See [Dock Lane Assignment](dock-lane-assignment.md).
4.  When a user checks in the transport equipment or initiates a move to a dock door, the application displays the recommended optimal dock doors, if any.

## Optimal door assignment setup

You must perform the following steps to configure the application to recommend an optimal dock door for receiving:

1.  Define the dock door locations, aisles, and staging lanes used for receiving. See [Location configuration process](../../warehouse/locations.md).
2.  Define the storage search paths and location preference rules for inventory. For example, a storage zone called FREEZER can be configured for inventory that belongs to the item family called Frozen. If inventory for this item family is received, the application attempts to find a location in the FREEZER storage zone where it can be put away. See [Storage Search Paths](../storage/storage-search-paths.md) and [Location Preference Rules](../storage/location-preference-rules.md).
3.  Configure optimal door assignment settings and rules for each building:
    1.  Select the building to which the configuration applies.
    2.  Select the types of storage locations (partially full or empty) to use and whether default search paths are used. Default search paths have no inventory criteria defined; these typically are used for storing inventory that either does not match the criteria on other search paths or for which no available locations were found in matching search paths.
    3.  Add the rules that define the criteria and thresholds by which the application evaluates expected inventory. For example, a rule can be defined for an item family with a threshold of 50%. If an inbound shipment matches the rule, then the application provides a dock door associated with a staging lane associated with the aisle to which the item family must be put away. If none of the inbound inventory matches any of the rules, then the application does not suggest a dock door.
4.  Define the dock door, staging lane, and aisle associations. See [Dock Lane Assignment](dock-lane-assignment.md).
    

## Configure optimal door assignment settings and rules

1.  Select **Configuration > Inbound > Receiving > Inbound Optimal Door Assignment**.
2.  From the building drop-down list (in the upper right corner of the page), select the building to which the settings apply.
3.  Under **GENERAL**, enter information in the following fields: 
    

 
| Field | Description |
| --- | --- |
| Location Status | Fill status of locations that determines how storage zones are prioritized for the expected inventory.<br>-   • **Partially Full**: Priority is given to storage zones that have the most locations that already contain the expected inventory. Select this option, for example, to combine inbound inventory into as few locations as possible.
<br>-   • **Empty**: Priority is given to storage zones that have the most empty storage locations. Select this option, for example, to distribute inventory across multiple locations for an item so that multiple users can access it. |
| Use Default Search Paths | If Yes, the application uses search paths that match the expected inventory as well as default search paths. A default search path is a search path that is configured with no inventory criteria. These paths are typically assigned the lowest priority of the search path rules and used for storing inventory that either does not match any of the criteria on the other search paths or for which no available storage locations were found in the zones in which it is usually stored. Select Yes if you want the application to recommend an optimal dock door even if it is optimal to a generic storage location.<br > If No, the application only uses those search paths that have criteria matching the expected inventory. If a storage zone cannot be found, the application does not provide an optimal dock door. Select No if you do not want the application to recommend an optimal dock door based on a generic storage location. |

5.  Define the rules by which the application evaluates expected inventory: 
    1.  Under **RULES**, perform one of the following tasks:
        -   To add a rule, click **Add**.
        -   To modify a rule, in the grid, click the criteria.
        -   To copy a rule, in the grid, select the check box next to the rule, and then click **Copy**.
    2.  Enter information in the [Rule fields](#Rule_fields).
    3.  Click **Apply**.
6.  To change the sequence of the rules, in the rules grid, drag a rule to the preferred position in the list.
7.  To delete a rule:
    1.  In the rules grid, select the check box next to the rule to delete, and then click **Delete**. A confirmation message is displayed.
    2.  Click **OK**.
8.  Click **Save**.
9.  [Associate staging lanes and aisles with receiving dock doors](dock-lane-assignment.md).

## Rule fields

 
| Field | Description |
| --- | --- |
| Item Family Group | Name used to group similar item families together. Typically, all of the item families within a group have the same material handling characteristics. Item family groups can be used for sorting and reporting purposes, and as criteria, for example, for storage paths and work assignment rules. |
| Item Family | Identifier used to group similar items together. Typically, all of the items within a family have the same material handling characteristics. |
| Item | Identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). Before the application can effectively store, track, and manipulate inventory, you must assign an item identifier and define the attributes of each item you want to track. When defining an item, you specify information such as how the item is packaged and handled, along with details that define how it should be received, stored, allocated, shipped, counted, and valued (cost information). |
| Item Client | Name of the client who stores this item in the facility. This field is only displayed in a 3PL environment. |
| Threshold | Percentage of inventory on the transport equipment that must meet the criteria for this rule. For example, if you specify 50%, then the application determines whether 50% of the inventory on the transport equipment matches the criteria defined for the rule. If it does match, the application uses the storage zone for this inventory to find an optimal dock door. If it does not match, the application determines whether the inventory matches the next sequential rule. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
