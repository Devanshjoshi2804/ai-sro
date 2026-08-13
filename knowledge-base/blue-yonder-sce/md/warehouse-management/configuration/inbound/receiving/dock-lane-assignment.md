---
title: "Dock Lane Assignment"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/dock_lane_assignment_inbound.htm"
source: "/content/dock_lane_assignment_inbound.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inbound"
  - "Receiving"
  - "Dock Lane Assignment"
sections:
  - "Associate staging lanes and aisles with receiving dock doors"
images: []
source_sha1: 9ae91ee7dd888822e061bfe1b012fecdf7735d5b
---
# Dock Lane Assignment - Inbound

The inbound dock lane assignment configuration defines associations between aisles and dock doors and between staging lanes and dock doors. The application uses these associations to allocate a staging lane based on the aisle in which the inventory will be stored and the expected dock door of the inbound shipment.

Manually choosing the best dock door for inbound transport equipment can be difficult. In most cases, the operator is unaware of where the majority of the inventory on the inbound shipment should be put away after it is unloaded. The application optimizes receiving by pre-determining the optimal dock door to which transport equipment should be directed so that the travel time during putaway is minimal. This feature is especially useful for facilities that separate their inventory into different zones within the facility and have a large number of receiving dock doors.

**Note**: Inbound dock lane assignment is a part of the optimal door assignment process. See [Inbound Optimal Door Assignment](inbound-optimal-door-assignment.md).

The goal of dock lane assignments is to create associations that provide the shortest or fastest travel distances to the necessary putaway locations. When aisles are selected to receive inventory, your associations are used to locate a staging lane and optimal dock door. There can be multiple associations between dock doors, staging lanes, and aisles.

You can define an association between a dock door and a staging lane, and between a staging lane or dock door and an aisle. If you create multiple associations from a single entity (such as associating a dock door with multiple staging locations, or a staging location with multiple aisles), you can assign a priority to the association. The priority determines the sequence in which the application attempts to use the associations.

## Associate staging lanes and aisles with receiving dock doors

1.  Select **Configuration > Inbound > Receiving > Dock Lane Assignment**.
2.  From the building drop-down list (in the upper right corner of the page), select the building to which the settings apply.
3.  Perform one of the following tasks:
    -   To assign dock doors or aisles to a staging lane, select **Lanes**, and then in the row for the staging lane, click the number of associated doors or aisles.
    -   To assign staging lanes to a dock door, select **Doors**, and then in the row for the dock door, click the number of associated lanes.
    -   To assign staging lanes to an aisle, select **Aisles**, and then in the row for the aisle, click the number of associated lanes.
4.  In the **Available** column, select the check box next to the staging lanes, aisles, or dock doors that you want to add to the association.
5.  In the **Priority** column for each assigned staging lane, aisle, or dock door, enter a priority for the association.
    
    **Note**: The application uses the priority to determine the order in which to select an optimal dock door or allocate a staging lane. Typically, the priority you set for an association is based on proximity. That is, aisles and staging lanes closer to a specific dock door may have a higher priority association, with 1 being the highest priority, than aisles and lanes farther away from the same door.
    
6.  Click **Save**.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
