---
title: "Dock Lane Assignment"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/dock_lane_assignment.htm"
source: "/content/dock_lane_assignment.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Outbound"
  - "Shipping "
  - "Dock Lane Assignment"
sections:
  - "Aisle and door associations"
  - "Lane and door associations"
  - "Priority"
  - "Example"
  - "Dock lane assignment setup"
  - "Associate staging lanes and aisles with shipping dock doors"
images: []
source_sha1: cd3a41ac49833db68cf5e31aab3b09f48ddc58d9
---
# Dock Lane Assignment - Outbound

The dock lane assignment configuration defines associations between aisles and dock doors and between staging lanes and dock doors. The application uses these associations to allocate a staging lane during pick release based on the aisle from which the inventory was picked and the expected dock door.

### Aisle and door associations

Manually choosing the best dock door for outbound transport equipment can be difficult. In most cases, the operator is unaware of where the majority of the picks are coming from. To minimize dock appointment durations, the application selects an expected dock door based on the aisle-door associations that you set up. Before the shipping transport equipment arrives, UOM picks that are marked for immediate release are directed to an assigned staging location, which is the highest priority available location associated with the chosen dock door.

**Note**: Only inventory available for allocation will be considered when selecting a staging lane. Shortages or cross dock inventory will not be considered.

### Lane and door associations

The dock lane assignment configuration defines prioritized associations between staging lanes and specific dock doors, typically based on proximity. During pick release, the application attempts to allocate a staging lane from the lanes assigned to the expected dock door or dock set for the load. If the application cannot allocate an assigned staging lane because there are none available, then depending on how you configure the application, one of the following events take place:

-   The application allocates an available staging lane that is not assigned to the expected door but is in the same movement zone.
-   The application does not allocate a staging lane and the picks are not released.

The **Allocate Only Assigned Lanes** field determines whether the application allocates a staging lane from only the lanes assigned to the expected dock door or dock set. See [Configure outbound staging](outbound-staging.md).

### Priority

The application uses the priority of an association to determine the order in which to select a door (based on the aisle of picked inventory) or allocate a staging lane (based on the expected door for the shipment's transport equipment). Typically, priority is based on proximity; that is, aisles and staging lanes closer to a specific dock door may have a higher priority association than aisles and lanes farther away from the same door. With priority, 1 is the highest, followed by 2, and so on.

There may be situations in which you want to prevent the application from allocating certain staging lanes for a specific purpose. You can set the **Exclude Lane Priority** field to 99, and then update the staging lane priority to 99 in the dock lane assignment configuration. When picks are released for a load and the application attempts to allocate a staging lane, the staging lane with priority 99 is excluded from allocation. See [Configure outbound staging](outbound-staging.md).

### Example

For this example, consider the following information and dock lane assignments: 

-   The staging lanes are in the same movement zone.
-   The Ignore Lane Priority field is set to 99.
-   The majority of picks for a load must be completed in AISLE11.

  
| Dock Door | Associated Aisles (Priority) | Associated Staging Lane (Priority) |
| --- | --- | --- |
| SDOOR01 | AISLE11 (1) | SSTG01 (1) |
| AISLE12 (2) | SSTG02 (2) |
| AISLE13 (3) | SSTG03 (99) |
| SDOOR02 | AISLE14 (1) | SSTG04 (1) |
| AISLE15 (2) | SSTG05 (2) |
| AISLE11 (3) | SSTG06 (3) |

The following assumptions can be made with this information: 

-   Based on the pick locations, the application recommends SDOOR01 as the optimal door, even though AISLE11 is also associated to SDOOR2. This is because the priority of the association between AISLE11 and SDOOR1 is higher (1) than the priority of SDOOR2 (3).
-   If the expected door for the load is SDOOR1, then when the picks are released, the application attempts to allocate a staging lane from the assigned lanes SSTG01 to SSTG03. If SSTG01 is available, it is allocated first because it has the highest priority.
-   SSTG03 is never allocated, because the priority of its association to SDOOR01 is 99, which is the priority value the application is configured to ignore.
-   If SSTG01 and SSTG02 are full, and the **Allocate Only Assigned Lanes** is set to Yes, then application does not allocate a staging location for the shipments during pick release, and the picks are not released.
-   If SSTG01 and SSTG02 are full, and the **Allocate Only Assigned Lanes** is set to No, then application searches for other available staging lanes in the same movement zone. If SSTG04 is available, it is allocated first because it has the highest priority association, and the picks are released.

## Dock lane assignment setup

You must perform the following steps to configure the application for dock lane assignment:

1.  Define the dock door locations, aisles, and staging lanes used for shipping. See [Location configuration process](../../warehouse/locations.md).
2.  Determine whether to allocate a staging lane from only the lanes assigned to the expected dock door or dock set, and if applicable, define a priority the application excludes when allocating a lane. See [Configure outbound staging](outbound-staging.md).
3.  Define the dock door, staging location, and aisle associations. The goal is to create associations that will offer the shortest or fastest travel distances from the pick locations. When inventory is allocated, your associations are used to locate a staging lane and optimal dock door. There can be multiple associations between dock doors, staging lanes, and aisles.

## Associate staging lanes and aisles with shipping dock doors

1.  Select **Configuration > Outbound > Shipping > Dock Lane Assignment**.
2.  From the building drop-down list (in the upper right corner of the page), select the building to which the settings apply.
3.  Perform one of the following tasks:
    -   To assign staging lanes or aisles to a dock door, select **Doors**, and then in the row for the dock door, click the number of associated lanes (to assign lanes) or associated aisles (to assign aisles).
    -   To assign shipping dock doors to a staging lane, select **Lanes**, and then in the row for the staging lane, click the number of associated doors.
    -   To assign shipping dock doors to an aisle, select **Aisles**, and then in the row for the aisle, click the number of associated aisles.
4.  In the **Available** staging lane column, select the check box next to the staging lanes, aisles, or dock doors that you want to add to the association.
5.  In the **Priority** column for each assigned staging lane, aisle, or dock door, enter a priority for the association.
    
    **Note**: The application uses the priority to determine the order in which to select an optimal dock door (based on the aisle of picked inventory) or allocate a staging lane (based on the expected door for the shipment's transport equipment). Typically, priority is based on proximity; that is, aisles and staging lanes closer to a specific dock door may have a higher priority association, with 1 being the highest priority, than aisles and lanes farther away from the same door.
    
6.  Click **Save**.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
