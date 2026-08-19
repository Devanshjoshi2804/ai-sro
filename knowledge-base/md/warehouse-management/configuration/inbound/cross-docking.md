---
title: "Cross Docking"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/cross_docking.htm"
source: "/content/cross_docking.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inbound"
  - "Cross Docking"
sections:
  - "Pick replacement processing"
  - "Work types for pick replacement processing"
  - "ASN distribution cross docks"
  - "Setup"
  - "Cross docking setup"
  - "Configure cross docking"
  - "Cross Docking fields"
  - "Release Rules fields"
  - "Destination Release Rules fields"
images:
  - "/content/resources/images/image430894.png"
  - "/content/resources/images/image430894.png"
source_sha1: c6285f416cb1399e6a1206839c83999d2e6edb21
---
# Cross Docking

Cross docking is the process of moving inventory directly from receiving to shipping to satisfy an outbound order line. This process bypasses the intermediate step of storage.

You can configure cross docking to deliver inventory to either of the following locations:

-   Ship staging location for the order (direct cross docking). This location is specified during order allocation.
-   Location in a cross dock zone, where the application generates pick work to move it to ship staging (indirect cross docking). Cross dock zones are defined during the configuration of cross docking.

If configured, the application automatically creates cross docks for distributions that are downloaded as part of an advanced shipment notification (ASN). See [ASN distribution cross docks](#ASN_distribution_cross_docks).

You can also configure the process of pick replacement. This process replaces the source location (typically in a storage zone) of an outstanding pick or replenishment with a location in a receiving zone (such as a receiving dock door or production zone) that has been enabled for this process. For example, with pick replacement functionality enabled, received inventory can be used to satisfy a pick and moved directly from receiving to the customer order's destination location (typically ship staging).

After cross docking is enabled and configured, if an order line is not marked for planned cross docking, the application may still use opportunistic cross docking to fulfill the order line. Opportunistic cross docking occurs when inventory is received and moved directly to ship staging (or other cross dock location) to satisfy a short order line. However, order lines marked for planned cross docking can only be fulfilled with cross docked inventory, and the lines are not considered short. See [Cross docking process](../../outbound-planner/outbound-planning-concepts.md).

## Pick replacement processing

Pick replacement is the process by which the application automatically changes the source location (typically in a storage zone) of an outstanding pick or replenishment with a location in a receiving zone (such as a receiving dock door or production location) that has been enabled for pick replacement. For example, with pick replacement enabled, received inventory can be used to satisfy a pick and moved directly from receiving to the customer order's destination location.

You must perform the following tasks to configure pick replacement processing:

1.  Configure cross docking. See [Configure cross docking](#Configure_cross_docking).
    1.  Enable cross docking.
    2.  Enable pick replacement processing by setting the **Fill Picks with Received Inventory** field to Yes.
    3.  Select from the **LPN Levels** field which levels you allow inventory in a receiving location to be used to fulfill a pick.
    4.  Select the from the **Status** field which pick statuses can be replaced. You use this setting to prevent the source location of picks that is a certain status, such as Released, from being changed.
    5.  Select the types of directed work for which pick replacement processing is enabled. For example, if you specify top-off replenishments, then when a top-off replenishment is allocated, the application evaluates whether the pick can be fulfilled with inventory from a receiving location instead of from storage. You can specify types of picks (such as bulk picks and kit picks), types of replenishments (such as manual, top-off, and triggered), and inventory transfers.
    6.  Select the items for which pick replacement is enabled. While pick replacement processing saves travel time, you must also consider whether this is good practice with date-tracked inventory. If enabled for date-tracked items, the process can result in fulfilling picks with newer inventory than that which may exist in storage.
    7.  Select whether replacement picks can be fulfilled with inventory that is on a handling unit different from the one requested on the order line. This is an optional setting that is configured by setting the **Pick Inventory from Other Handling Units** field. If set to Yes, then the replacement pick is allocated successfully if it is on a handling unit that is in the same allocation handling unit group as the handling unit specified on the order line. While allocation is successful, the inventory must be moved to the requested handling unit type prior to shipping. Select Yes, if you would rather allocate the inventory and move it to a different handling unit, than fail to allocate the pick at all. Select No if you only want to perform replacement picks that are on the requested handling unit type.
2.  Configure pick zones. Select the pick zones in which you allow the source location of picks to be changed to a receiving location. To enable this process for a pick zone, in the pick zone configuration, set the **Replace Picks** field to Yes. See [Pick Zones](../outbound/allocation/pick-zones.md).

## Work types for pick replacement processing

The following types of directed work may be enabled for pick replacement processing:

-   **Pick**: Work type used to pick inventory to fill an order.
-   **Kit**: Work type used to pick component items to fill a work order.
-   **Bulk Pick**: Work type used to perform bulk picks.
-   **Manual Replenishment**: Replenishment work type initiated by an operator for a specific location.
-   **Top-off Replenishment**: Replenishment work type generated automatically when an item in a zone or a location has dropped below a user-defined level.
-   **Triggered Replenishment**: Replenishment work type generated automatically at timed intervals.
-   **Emergency Replenishment**: Replenishment work type generated automatically when there is insufficient inventory in a pick zone to satisfy a shipment line.
-   **Replenishment**: Work type used to fill a pickface location with inventory from a storage location.
-   **Stage Transfer**: Pick work generated to transfer inventory typically from a cross docking location to a staging lane.

## ASN distribution cross docks

Some facilities download and process advanced shipments notifications (ASNs) that include distribution information, and then fulfill the distribution by using direct cross dock functionality. For example, when an ASN distribution is downloaded, the application creates the planned inbound order, and then creates the outbound orders and shipments that are required to fulfill the distribution. The shipments are then allocated (short) to create cross dock requests for the inbound inventory. When the inventory is received, the application allocates inventory for the cross docks, and then the inventory can be ship staged.

You can configure the application to pre-process ASN distribution cross docks, which means the inventory is considered allocated and picked prior to its arrival. When the ASN inventory arrives at the warehouse and is scanned, the inventory is received and then can be immediately deposited to a staging location for the distribution (depending on the movement path). The application pre-processes ASN distribution cross docks only for fully distributed LPNs. If an LPN contains inventory that is destined for storage, pre-processing is not executed.

If pre-processing is not enabled, then the application processes the distribution cross dock picks (allocation and auto-picking) when the ASN inventory is received.

The application processes all of the cross dock allocation requests for a single distributed LPN at once. For example, if there are 10 sub-LPNs on a distributed LPN, each for a single cross dock, instead of attempting to allocate each cross dock separately (10 different times), the application processes the allocation for all 10 sub-LPNs at the same time.

### Setup

You must perform the following tasks before the application can process ASN distribution cross docks:

1.  Configure advanced shipment notification receiving attributes. See [Configure inbound identification](receiving/inbound-identification.md).
2.  Configure distributions. See [Distribution setup](../outbound/distribution.md).
3.  Create an auto allocation method with the **Include Unplanned Orders** field set to Yes and with criteria that matches the orders to auto allocate. See [Automatic Allocation](../outbound/allocation/automatic-allocation.md).
4.  Enable and configure cross docking. See [Cross docking setup](#Cross_docking_setup).
    
    **Note**: You can enable pre-processing for ASN distribution cross docks in the cross dock configuration. Pre-processing takes place only if an auto allocation method is configured and when the allocation event occurs (download or scheduled).
    

## Cross docking setup

You must perform the following tasks to set up automated cross docking:

1.  Enable and configure cross docking. This task requires the configuration of the cross docking settings and defining the following zones and their associations:
    
    -   **Cross Docking Zones**: A cross docking zone defines the locations to which inventory can be moved from receiving and deposited prior to being directed to a ship staging location for an outbound order. Standard product provides the XDCK zone and the XDCK01 location in that zone, but you can create additional zones and locations as needed.
    -   **Zone Movement Associations**: A zone movement association defines the movement path that is used to direct inventory from a source zone (such returns staging, the receiving dock, or inbound order staging) to a cross docking zone, and finally to a destination zone (such as ship staging). When cross docked inventory is available, the application uses these path associations to direct inventory to its next location.
        
        Zone movement associations for direct cross docking define the logical cross docking zones to which inventory is systematically moved from a source (receiving) zone. Zone movement associations for indirect cross docking define the zones to which inventory is physically moved from a source zone.
        
    
    -   **Release Rules**: Release rules define the actions that the application takes to release work for cross docking. For cross docking, the application typically uses pick work to move inventory directly from receiving to a ship staging location to satisfy an order. Release rules determine the action that takes place to release work to pick (move) inventory. For example, a release rule is used to create directed work to pick inventory out of a source location to a cross dock or ship staging location. For each release rule you define the following attributes:
        -   LPN level to which the release rule applies; for example, LPNs, sub-LPNs, or detail LPNs.
        -   Action that takes place when the release command is executed; for example, to create directed work
        -   Type of work (such as move or pick) that is created by a release command that creates work. In addition, you can optionally define the priority in which the work should be created, if you want it to be different from the standard base priority.
        -   Destination rule, which is a specific release rule that is used based on a pick's destination movement zone.
            
    
    See [Configure cross docking](#Configure_cross_docking).
    
2.  Configure pick replacement processing. When you configure cross docking, you can also configure the application to automatically replace the source location of a pick with a location in receiving that contains inventory required for the pick. To configure pick replacement processing, you select the following attributes:
    -   LPN levels that can be fulfilled with replacement picks. For example, you may allow full LPN picks but not sub-LPN picks.
    -   Pick statuses in which picks can be fulfilled with replacement picks. For example, you may allow pending picks to be replaced but not picks that have already been released for picking.
    -   Types of directed pick work (such as kit, bulk, and replenishment picks) that can be fulfilled with replacement picks.
    -   Items that are eligible to be fulfilled with replacement picks. For example, to preserve inventory rotation methods, date-tracked items should not be selected for pick replacement.
    -   Pick zones in which pick replacement processing is enabled. See [Pick Zones](../outbound/allocation/pick-zones.md).
        

## Configure cross docking

1.  Start **Configuration > Inbound > Cross Docking.**
2.  To enable automated cross dock processing, select **ENABLED**.
3.  Enter information in the [Cross Docking fields](#Cross_Docking_fields).
4.  To configure the release rules for creating work to move cross docked inventory:
    1.  Under **DIRECT CROSS DOCKING SETTINGS**, click **Release Rules**. The Release Rules page is displayed.
    2.  Click the LPN level for which you want to define release rules.
    3.  Enter the information in the [Release Rules fields](#Release_Rule_fields).
    4.  To define the attributes that must match for individual pieces of work to be grouped into a single task, click **Work Groupings**, select the check box for the attributes that must match, and click **Save**.
        
        **Note**: The work groupings can limit the performance of the action you specified for the release rule by grouping individual pieces of work into one piece of work. For example, if you select PRODUCE WORK ASSIGNMENT as the action for the release rule, and then select Operation Code and Cartonization Group as the work groupings, the application will only produce on one work assignment for all picks that are of the same type of operation and that have the same cartonization group.
        
    5.  To add or modify a destination rule:
        
        **Note**: A destination rule is a separate release rule that is used instead of the normal release rule when the pick's destination movement zone is that which you specify in the destination rule.
        
        1.  Under **DIRECT CROSS DOCKING SETTINGS**, click **Destination Rules**.
        2.  Perform one of the following tasks:
            -   To add a new destination rule, click **Add**.
            -   To modify an existing destination rule, in the grid, select the rule.
        3.  Enter information in the [Destination Release Rules fields](#Destination_Release_Rule_fields).
        4.  To define the attributes that must match for individual pieces of work to be grouped into a single task when the destination rule is used, click **Work Groupings**, select the check box for the attributes that must match, and click **Save**.
        5.  Click **Save**.
    6.  Click ![Previous page](../../../../images/resources/images/image430894.png) until the Cross Docking page is displayed.
5.  To configure the logical movement of inventory that is directly cross docked between zones:
    1.  Under **DIRECT CROSS DOCKING SETTINGS**, click **Zone Movement Associations**.
        
        **Note**: Zone movement associations for direct cross docking define the logical cross docking zones to which inventory is systematically moved from a source (receiving) zone. Inventory is not physically moved to the direct cross docking zone, but the zone can be configured as the source for a movement path.
        
    2.  To define associations, draw a line from a box in one column to a box in the next column.
        
        **Note**: To draw a line, click a box, and drag your pointer. Alternatively, you can hold **Ctrl**, click the two boxes, and then click **Assign**.
        
    3.  To remove an association, click a line, and then click **Clear**.
    4.  Click **Apply**.
6.  To select the locations to which indirectly cross docked inventory can be deposited before being moved to ship staging:
    1.  Under **INDIRECT CROSS DOCKING SETTINGS**, click **Cross Docking Zones**.
        
        **Note**: Indirect cross docking occurs when the final destination of the inventory is not defined at the time of allocation, or if the destination location is unavailable. The inventory is physically moved to an intermediate location in a cross docking zone until the final destination is defined and the location is available.
        
    2.  Perform one of the following tasks:
        -   To add a zone, click **Add**.
        -   To modify a zone, in the grid, click the zone.
    3.  In **Zone Name**, **Description**, and **Building** fields, enter the values.
    4.  Click **Layout** or **Next**.
    5.  To draw the zone on the floor plan, click **Draw**, and then size and drag the box the map.
    6.  To display areas or other zones on the floor plan, click **View**, and then select the check box next to the selections you want.
    7.  Click **Locations** or **Next**.
    8.  In the **Available Locations** column, select the locations that belong to the cross dock zone. You must select at least one location.
    9.  Click **Finish**, and then click ![Previous page](../../../../images/resources/images/image430894.png) to return to the Cross Docking page.
7.  To configure the movement of inventory that is indirectly cross docked between zones:
    1.  Under **INDIRECT CROSS DOCKING SETTINGS**, click **Zone Movement Associations**.
        
        **Note**: Zone associations define the zones to which inventory can be moved from receiving to cross docking, and from a cross docking zone to ship staging.
        
    2.  To define associations, draw a line from a box in one column to a box in the next column.
        
        **Note**: To draw a line, click a box, and drag your pointer. Alternatively, you can hold **Ctrl**, click the two boxes, and then click **Assign**.
        
    3.  To remove an association, click a line, and then click **Clear**.
    4.  Click **Apply**.
8.  To select the types of directed pick work that can be fulfilled with inventory in a receiving zone:
    
    **Note**: To configure pick replacement processing, the **Fill Picks with Cross Dock Inventory** field must be set to **Yes**.
    
    1.  Under **REPLACE PICKS**, click **Work Types**.
    2.  In the **Available Work Types** column, select the work types that apply.
    3.  Click **Save**.
9.  To select the items for which replacement picks can be created:
    1.  Under **REPLACE PICKS**, click **Items**.
    2.  In the **Available Items** column, select the items that apply.
    3.  Click **Save**.
10.  Click **Save**.

## Cross Docking fields

 
| Field | Description |
| --- | --- |
| Split LPN | If Yes, received LPNs can be split into less than full pallet quantities to fulfill cross docking requirements. Any remaining inventory is directed to a storage location.<br > If No, the application does not attempt to fulfill outstanding picks with a partial quantity of a received LPN. Select No if you want do not want operators to remove cases from a full pallet for the purpose of fulfilling a cross dock request with a less than full pallet quantity. |
| Display Location Failure | If Yes, a message is displayed to the operator when the application cannot find an acceptable cross dock or ship staging location for the inventory picked up from a receiving location.<br > If No, no message is displayed to the operator when a suitable deposit location is not found for cross dock inventory. |
| Cross Dock Priority | Indicates whether work order lines or outbound order lines are given priority when they both require the same cross docked inventory.<br>-   • **Work Orders**: When inbound inventory is available to fulfill cross dock opportunities, the application allocates the appropriate quantity to work order lines first (starting with the highest processing priority). If there is excess inventory, or if no work order lines need cross docked inventory, the application allocates the available inventory to outbound order lines with cross dock requests (starting with the highest processing priority).
<br>-   • **Outbound Orders**: When inbound inventory is available to fulfill cross dock opportunities, the application allocates the appropriate quantity to outbound order lines first (starting with the highest processing priority). If there is excess inventory, or if no outbound order lines need cross docked inventory, the application allocates the available inventory to work order lines with cross dock requests (starting with the highest processing priority).
<br>-   • **No selection (blank)**: When inbound inventory is available to fulfill a cross dock request, the application allocates the appropriate quantity to any outbound order lines and work order lines (starting with the highest processing priority across all order lines).
<br > **Note**: This configuration has no effect on pick stealing, which is the process that replaces the source location of an outstanding pick with the receiving location to which inbound inventory has been identified. Pick stealing does not happen until inventory is already allocated. Therefore, there is no need to prioritize since there is no short. |
| Direct Move Zone | Movement zone to which inventory for a direct cross dock is systematically moved to by default when it is received. Direct cross docking occurs when the final destination of the inventory is defined at the time of allocation. Direct cross docking entails moving the inventory directly from receiving to its final destination (such as ship staging) without an intermediate stop. The default direct move zone is used when there are no other direct zone associations configured for the source zone (zone in which the inventory is received). Inventory is not physically moved to the direct cross docking zone, but the zone can be configured as the source for a movement path. |
| Indirect Move Zone | Default movement zone to which the application directs inventory for an indirect cross dock when it is received. Indirect cross docking occurs when the final destination of the inventory is not defined at the time of allocation, or if the destination location is unavailable. Indirect cross docking entails physically moving the inventory to an intermediate location until the final destination is defined and the location is available. The default indirect move zone is used when there are no other indirect zone associations configured for the source zone (zone in which the inventory is received). |
| Pre-Process ASN Distribution Cross Docks | If Yes, then when an ASN that includes distribution information is allocated (on download or when scheduled), the application processes the resulting cross docks immediately so that the inventory is considered allocated and picked prior to its arrival. When the ASN inventory arrives at the warehouse and is scanned, the inventory is received and then can be immediately deposited to the destination location for the shipment (typically, ship staging). The application pre-processes ASN distribution cross docks only for fully distributed LPNs. If an LPN contains inventory that is destined for storage, pre-processing is not executed.<br > **Note**: If this field is set to Yes, the application does not reserve locations during pre-processing pick release, regardless of the cross dock pick method configuration.<br > If No, then the application processes the distribution cross dock picks (allocation and picking) when the ASN inventory is received.<br > **Note**: Additional setup is required before the system can process ASN distribution cross docks. See [ASN distribution cross docks](#ASN_distribution_cross_docks). |
| Fill Picks with Received Inventory | If Yes, then when the application finds inventory in a receiving zone (such as a dock door or production location) that can be used to fulfill an outbound order, it directs the user to pick that inventory for the order. This process replaces the source location (typically in storage) of an outstanding pick or replenishment with a location in a receiving zone. If enabled, this process takes place after distribution inventory, finished goods for which shipments are waiting, and cross docking processes are complete.<br > If No, the application does not attempt to automatically change the source location of a pick to a location in a receiving zone. |
| LPN Levels | LPN level at which inventory in a receiving zone can be used to fulfill a pick. Select either LPN, Sub-LPN, or both. If neither check box is selected, pick replacements will not take place. |
| Pick Inventory from Other Handling Units | If Yes, then the application allocates the inventory required to fulfill the pick if it is on the handling unit requested on the order line or if is available on one of the other handling unit types in the same handling unit group as the type requested on the order line. If inventory on an alternate handling unit type is allocated, that inventory must be transferred to the requested handling unit type prior to shipping.<br > If No, the application does not allocate inventory for a replacement pick if the inventory is not on the specific handling unit type requested on the order line. |
| Status | Pick work statuses that are eligible for pick replacement. When pick work is in a selected status, the application attempts to fulfill the pick with inventory from a receiving location, if possible. Select all the statuses that you want to enable for pick replacement.<br>-   • **Pending**: Pick work inventory is reserved for allocation until automatically released by the application.
<br>-   • **On Hold**: Pick work inventory is reserved for allocation until manually released by a user.
<br>-   • **Released**: Pick work inventory is released to the work queue. |

## Release Rules fields

 
| Field | Description |
| --- | --- |
| Action | Action that the application performs to release the pick:<br>-   • **CREATE DIRECTED WORK**: Creates a directed work request for the pick, which is added to the work queue so that an RF operator can perform it.
<br>-   • **CREATE WORK**: Releases the pick as undirected work.
<br>-   • **CREATE WORK FOR PM PRE MANIFEST PACKAGE**: Creates a work queue entry for a case pick or kit pick, and manifests the parcel package.
<br>-   • **PROCESS PM PRE MANIFEST PACKAGE**: Creates a work queue entry for a case pick or kit pick, manifests the parcel package, and prints a manifest label with pick information and parcel package information.
<br>-   •
    
    **CREATE LABEL FILE FOR PM PREMANIFEST PACKAGE**: Manifests the parcel package and prints a manifest label with pick information and parcel package information.
    
    <br>
<br>-   • **PRODUCE SHIPMENT LABEL**: Prints a pick label that includes the information for the pick work. |
| Operation | Work operation that identifies the type of work that is created, such as piece pick, case pick, kit pick, list pick, pallet pick, or replenishment pick. |
| Priority | Priority at which work initially enters the work queue. It is the priority at which a work request is created. Priority is used, for example, to assign a higher priority to pallet and case replenishment work to fill pick locations than to pallet or case pick work to fulfill orders.<br>-   • **Use base priority**: The value for the operation's base priority at the time of allocation is used when work is created. The base priority is the current priority that is defined for the operation.
<br>-   • **Override base priority**: The operation's base priority is overridden at the time of allocation for the selected zone with the number specified in the **Value** field. For example, you may consider your case replenishments coming out of your flow racks more important than your case replenishments coming out of your floor zone.
<br>-   • **Increase priority from base priority**: The operation's base priority is increased at the time of allocation by the number specified in the **Value** field.
<br>-   • **Decrease priority from base priority**: The operation's base priority is decreased at the time of allocation by the number specified in the **Value** field. |
| Value | Value that is applied against the base priority of the operation. Depending on what is selected for **Priority**, the value either replaces the base priority, or it is added to or subtracted from the base priority to result in a new priority. |

## Destination Release Rules fields

 
| Field | Description |
| --- | --- |
| Destination | Movement zone that contains the final destination location for inventory that was picked or moved. For example, for inventory picked for an outbound order, this could be a zone that contains ship staging locations. |
| Action | Action that the application performs to release the pick:<br>-   • **CREATE DIRECTED WORK**: Creates a directed work request for the pick, which is added to the work queue so that an RF operator can perform it.
<br>-   • **CREATE WORK**: Releases the pick as undirected work.
<br>-   • **CREATE WORK FOR PM PRE MANIFEST PACKAGE**: Creates a work queue entry for a case pick or kit pick, and manifests the parcel package.
<br>-   • **PROCESS PM PRE MANIFEST PACKAGE**: Creates a work queue entry for a case pick or kit pick, manifests the parcel package, and prints a manifest label with pick information and parcel package information.
<br>-   •
    
    **CREATE LABEL FILE FOR PM PREMANIFEST PACKAGE**: Manifests the parcel package and prints a manifest label with pick information and parcel package information.
    
    <br>
<br>-   • **PRODUCE SHIPMENT LABEL**: Prints a pick label that includes the information for the pick work. |
| Operation | Work operation that identifies the type of work that is created, such as piece pick, case pick, kit pick, list pick, pallet pick, or replenishment pick. |
| Priority | Priority at which work initially enters the work queue. It is the priority at which a work request is created. Priority is used, for example, to assign a higher priority to pallet and case replenishment work to fill pick locations than to pallet or case pick work to fulfill orders.<br>-   • **Use base priority**: The value for the operation's base priority at the time of allocation is used when work is created. The base priority is the current priority that is defined for the operation.
<br>-   • **Override base priority**: The operation's base priority is overridden at the time of allocation for the selected zone with the number specified in the **Value** field. For example, you may consider your case replenishments coming out of your flow racks more important than your case replenishments coming out of your floor zone.
<br>-   • **Increase priority from base priority**: The operation's base priority is increased at the time of allocation by the number specified in the **Value** field.
<br>-   • **Decrease priority from base priority**: The operation's base priority is decreased at the time of allocation by the number specified in the **Value** field. |
| Value | Value that is applied against the base priority of the operation. Depending on what is selected for **Priority**, the value either replaces the base priority, or it is added to or subtracted from the base priority to result in a new priority. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
