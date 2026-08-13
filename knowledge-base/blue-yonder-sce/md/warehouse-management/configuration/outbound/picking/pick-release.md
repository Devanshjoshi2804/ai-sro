---
title: "Pick Release"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/pick_release.htm"
source: "/content/pick_release.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Outbound"
  - "Picking "
  - "Pick Release"
sections:
  - "Resource locations"
  - "Staging location reservation by resource code"
  - "Setup"
  - "Configure pick release attributes"
  - "Pick Release fields"
images:
  - "/content/resources/images/image942307.png"
source_sha1: 24e82501e365e7f759c18b3553817e31dec706c6
---
# Pick Release

Pick release is the process of allocating the locations in the movement path for picked inventory to its final destination, and releasing those picks so that operators can perform the work.

Pick release can be executed manually or set up for automatic processing based on specific pick release configurations.

During pick release, the application considers a group of picks in a wave, determines which picks are for work assignments and which are single picks, builds the work assignments, and then attempts to reserve locations for the entire group of picks (if the pick method is configured to reserve locations in a movement path). If there are one or more locations with capacity for the group, the picks are released; if there is not enough capacity for the group, the picks are not released.

**Note**: If a pick method is configured to reserve all locations, then during the location reservation phase of pick release, the application searches for staging lanes based on the release group defined on the pick method and by matching resource codes, if enabled. See [Location reservation](../../inventory/movement/movement-paths.md) and [Staging location reservation by resource code](#Staging_location_reservation_by_resource_code).

When you configure pick release you specify the following settings:

-   Restrictions that limit the amount of pick work that is released at one time
-   Pick consolidation that determines whether pick work is consolidated (to reduce the number of picks, if possible) and how pick work is grouped for release at the same time
-   Release specifications that are used to enable automatic pick release and related actions, to specify the days on which picks are performed, and to allocate locations in the movement path for the picked inventory
-   Whether the application groups picks for release and staging lane reservation
-   If staging lane reservation by resource code is enabled, a utilization percentage that determines the percentage of a lane's capacity that a group of picks must reach before it can be staged in the location

## Resource locations

A resource location is a location in a movement path that is reserved for picked inventory at the time the inventory is allocated. The movement path for picked inventory consists of movement zones that include processing locations (such as for overpack, consolidation, and staging). If there is no location available in a given movement zone that already has the same resource code (such as item family) as that required for picked inventory, the application allocates an empty location in the zone.

The application searches for a valid location using the location attributes and sequence specified for resource location sequences. Location attributes can include, for example, ABC code, maximum capacity, work zone, or travel sequence. If multiple attributes are selected, the application sorts the valid locations according to the order in which the attributes are listed in the grid. For example, if attributes are listed as Maximum Capacity and then Travel Sequence, then locations are sorted first by capacity and then by travel sequence. If resource location sequences are left blank, then the list of valid locations is not sorted prior to the application reserving a location for the picked inventory.

## Staging location reservation by resource code

You can configure the application to reserve staging lane locations by grouping picks within a wave based on the resource variable assigned to the destination movement zone of each pick. The application searches for staging capacity based on the entire group of picks and will only release the picks if one or more staging lanes have the capacity to completely stage the group. When you configure the application to reserve staging lanes by resource code, the resource variable defined on the destination movement zone of the picks determines which value is used to group picks for release and location reservation. For example, if the resource variable for zone MOVE1 is Load, then during pick release, the application reserves staging lanes in zone MOVE1 for each separate load within a wave.

The staging lane utilization determines the percentage of a lane's capacity that a group of picks must reach before it can be staged in the location. The utilization percentage is only used when ship staging lane reservation by resource code is enabled. The application may reserve more than one lane if a single lane does not have capacity for an entire group of picks.

**Note**: The location capacity code is used to determine if a group of picks satisfies the utilization percentage, not the number of picks included in the group. For example, if the capacity code is Pallet and a work assignment includes 10 sub-LPN picks that can fit on 1 pallet, the application uses the count of 1 pallet to determine capacity utilization. Additionally, if the capacity code is Pallet, then any handling unit type used for the picks is considered a pallet for capacity calculations.

When a dock set or dock door is defined on an appointment, the application determines the priority of the lanes associated with the dock set or door in the following sequence:

**Note**: If a destination zone and destination lane are defined during wave planning or allocation, the application does not evaluate any other staging lanes associated with the dock set or door. Additionally, if an appointment does not have a dock set or door, or if there is no appointment associated with the group of picks, then priority is not evaluated and location sort rules are used instead. For the application to process ship staging lane reservation by resource code properly, it is recommended that you do not define a destination zone or lane during wave planning or allocation, and that picks are associated with an appointment that specifies a dock set or door.

1.  A staging lane with inventory that matches the grouped picks (utilization is ignored) based on the resource variable assigned to the destination movement zone
2.  Highest priority lane associated to the appointment dock set or door for which the grouped picks satisfy the utilization percentage
    
    **Note**: If multiple lanes are required and the utilization percentage is not met for all of the lanes needed in a dock set, the application can reserve lanes across multiple dock sets as long as the lane is in the same movement zone as the original dock set and is assigned a priority.
    
3.  Highest priority lane associated to the appointment dock set or door but for which the picks do not satisfy the utilization percentage
4.  Location sort rules, such as travel sequence, defined in the outbound staging configurations. Location sort rules are also used to break priority ties between lanes identified earlier in the reservation sequence.

**Note**: If a lane is associated to multiple doors in a set, then the application uses the average priority of all lane-to-door associations defined in the dock lane assignment configuration. For example, if the dock set defined on an appointment has 3 doors, and a lane is assigned to each door in the set with priorities of 1, 2, and 3, then the lane priority is 2 for the dock set \[(1 + 2 + 3 = 6) / 3 = 2\]. If another lane is associated to the same doors with the priorities of 1, 1, and 2, then that lane would be evaluated first since its average priority is higher than 2.

If the application cannot find one or more lanes with capacity in which to stage the entire group of picks for the resource code, then the picks are not released.

### Setup

You must perform the following tasks to set up and configure staging lane reservation by resource code: 

1.  Associate each shipping dock door with each staging lane until each door is associated with every staging lane. Typically, the lane closest in proximity to the dock door has the highest priority (1), and that priority decreases as the lanes increase in distance from the door. However, other factors may dictate how you set priority, such as smaller lanes closer to the door being assigned a lower priority to ensure larger lanes farther away are used first. See [Associate staging lanes and aisles with shipping dock doors](../shipping/dock-lane-assignment.md).
    
    **Note**: If you configure low capacity lanes with a high priority, the application will fill smaller staging lanes first, resulting in a higher number of lanes reserved for a single group of picks.
    
2.  For ship staging lane reservation by resource code, it is recommended to configure the application to not release groups of picks based on shipment or scheduled batch (**Release Grouping** = No Grouping). This allows for any pick that is successfully allocated to be released, regardless of short inventory. If you release by shipment or scheduled batch, not only will shorts prevent the entire shipment or batch from being released, but staging lanes in the movement zone must have the capacity for both the release grouping and the group of picks (grouped based on the movement zone's resource variable). For example, if the release grouping is set to Shipment and the resource variable is Load, then if there is not enough capacity for an entire load, the picks are not released, even if the lanes have capacity for one or more shipments on the load. See [Configure pick release attributes](#Configure_pick_release_attributes).
3.  Configure all work assignment pick methods (that you want to be staged together) to reserve all locations at the time of pick release (**Reserve During Pick Release** = All). See [Add or modify a pick method](pick-methods.md).
    
    **IMPORTANT**: Do not change the setting of this field if there are work assignments that are already allocated or released. If you are upgrading an existing system in which you cannot ensure there are no work assignments allocate or released for a pick method, then it is recommended that you create new pick methods with the **Reserve During Pick Release** field set to All, and then update the existing allocation search path rules with the new pick methods. Operators can then complete existing work assignments with ship staging reservation taking place during deposit, and the application allocates new work assignments using the new pick methods on the allocation search paths.
    
4.  Set the **Ship Staging Lane Reservation by Resource Code** field to Yes and define the **Staging Lane Utilization** in the pick release configurations. See [Configure pick release attributes](#Configure_pick_release_attributes).
    
    **Note**: The **Resource Variable** on a movement zone determines the resource code used to reserve locations. For example, if the resource variable for zone MOVE1 is Load, then during pick release, the application reserves staging lanes in zone MOVE1 for each separate load within a wave.
    

## Configure pick release attributes

1.  Select **Configuration > Outbound > Picking > Pick Release**.
2.  Enter information in the [Pick Release fields](#Pick_Release_fields).
3.  To specify the dates on which the pick day is reversed:
    
    **Note**: An exception reverses the pick day selection. For example, if Monday is selected as a pick day, an exception for a date that falls on a Monday indicates picking is not performed on that date. If Monday is not selected as a pick day, an exception for a date that falls on a Monday indicates picking is performed on that date. The application does not allow you to configure exceptions until changes to pick days are saved.
    
    1.  If Pick Days have been edited, click **Save**.
    2.  Under **RELEASE SPECIFICATIONS**, click **Exceptions**.
    3.  To add an exception, on the calendar, select the dates on which the pick day configuration is reversed. The selected dates are highlighted in red.
    4.  To remove an exception, on the calendar, click the exception.
    5.  Click ![Close](../../../../../images/resources/images/image942307.png).
4.  To define the criteria that determines the order in which the application assigns an available resource location:
    
    **Note**: A resource location is a processing location in a movement zone to which the pick will be directed. The resource location sequence determines how the application sorts resource locations before selecting one. The sequence is based on location attributes (such as travel sequence) and the arrangement (sequence) of those attributes in the grid.
    
    1.  Click **Resource Location Sequence**.
    2.  In the **Available** grid, select the check box next to the attributes to use.
    3.  In the **Selected** grid, click and drag the selected attribute to the preferred position.
    4.  Click **Apply**.
5.  Click **Save**.

## Pick Release fields

 
| Field | Description |
| --- | --- |
| Maximum Stops | Maximum number of stops that are released at one time for a given outbound load when picks are allocated to a Held status. For example, if you set this value to 2, then the picks for 2 stops for a held load are released. No more picks are released for the load until picking for one of the stops is complete. If this value is blank or zero, the application will not release any picks automatically for a shipments in the Held status; they would have to be released manually. |
| Limit by Availability | If Yes, the application checks the locations in the movement path (such as a packing or consolidation location) before releasing the picks to ensure that another process did not already reserve the location that is needed. This is useful when more than one process in the application handles the release of picks; that is, when you are using more than one Pick Release Manager.<br > If No, the application does not check the availability of the locations in the movement path. |
| Maximum Batches | Maximum number of batches that the pick release command should process ahead in the queue of outstanding batches. A batch is a collection of picks that are allocated at the same time (not necessarily released at the same time). More batches are released after the number of current batches falls below this value. This value must be less than or equal to 250. |
| Maximum Pallets for Small Shipping Lane | Maximum number of pallets allowed at a shipment staging lane for it to be considered a small staging lane. If you define a value, then the pick release process requires that a small shipping lane is only used when it can contain at least 50% of the pallets required by the shipment. This prevents many small lanes from being occupied by one large shipment, and keeps them available for smaller shipments.<br > For example, if you want to define small shipping lanes as those that have a capacity for 4 pallets, then set this value to 4. For this configuration, if a shipment requires 8 or fewer pallets, then shipping lanes that have a maximum capacity of 4 pallets would be candidates for use. However, if a shipment requires 10 pallets or more, then those shipping lanes would not be candidates for use because one of them cannot hold 50% of the shipment. |
| Consolidation | If Yes, the application attempts to consolidate, into a single pick, any pending picks that have the same schedule batch, shipment line, LPN level, origin, lot, revision level, source location, destination location, and UCC. If selected, then during pick release, picks for the sub-LPN and detail LPN that share these properties are combined into one pick.<br > If No, matching picks are not be combined automatically and must be picked separately. |
| Release Grouping | Value that determines the grouping by which picks are released after the group is entirely allocated. When releasing picks, the application waits until all allocations in the selected structure (Shipment or Schedule Batch) are complete and then releases the picks for that group.<br>-   • **Release By Shipment**: Picks for a shipment or work order are released when all picks for the shipment or work order are allocated. If one or more order lines is short, the remaining picks are not released.
<br>-   • **Release By Scheduled Batch**: Picks for a scheduled batch are released when all picks for the scheduled batch are allocated. If one or more order lines is short, the remaining picks are not released.
<br>-   • **No Grouping**: Picks are not grouped. If one or more order lines is short, the remaining picks are released. |
| Case Picking Footprint Code Enforcement | If Yes, then when performing a case (sub-LPN) pick, an operator is not required to select a case with the same footprint as the one that was allocated. If this field is set to Yes, then for case picks, the application allows a different case footprint for the same item to be picked.<br > The configuration only applies to case (sub-LPN) picks for orders, not to replenishment picks. If the configuration is enabled, the application performs the following operations:<br>-   • Consolidates pick work for the same item with different footprint codes on the same shipment line, as long as the picks are sourced from the same location. For a work assignment, picks are consolidated first and then assigned to the same work assignment. So the picks on the work assignment already consider any footprint.
<br>-   • Allows the operator to pick a footprint code different from that specified for the pick.
<br>-   • If the quantity in the selected case is not enough to fulfill the pick quantity, the remaining quantity is allocated as an each pick.
<br > If No, then when performing a case pick, the operator is required to select a case with the same footprint as the one that was allocated. |
| Ship Staging Lane Reservation by Resource Code | If Yes, then during pick release, the application reserves staging lane locations by grouping picks within a wave based on the resource variable assigned to the destination movement zone. The application searches for staging capacity based on the entire group of picks and will only release the picks if one or more staging lanes have the capacity to completely stage the group. When you configure the application to reserve ship staging lanes by resource code, the resource variable defined on the destination movement zone of the picks determines which value is used to group picks for location reservation. For example, if the resource variable for zone MOVE1 is Load, then during pick release, the application reserves staging lanes in zone MOVE1 for each separate load within a wave. See [Staging lane reservation by resource code](#Staging_location_reservation_by_resource_code).<br > **Note**: If this field is set to Yes, it is recommended that the **Reserve During Pick Release** field is set to All for any pick methods you want to be able to stage together. For example, work assignments and full pallet picks may need to be staged together but require different pick methods, so each method should be configured to reserve all locations.<br > If No, then during pick release, the application does not reserve ship staging lanes based on the capacity needed for the entire group of picks. If you set this field to No and configure the application to reserve all locations during pick release, then this could result in some picks in a resource code group being staged while other picks in the same group remain unreleased because there was not enough staging capacity. |
| Staging Lane Utilization Percentage | Determines the percentage of a lane's capacity that a group of picks must reach before it can be staged in the location. The utilization percentage is only used when **Ship Staging Lane Reservation by Resource Code** field is set to Yes. The location capacity code is used to determine if a group of picks satisfies the utilization percentage, not the number of picks included in the group. For example, if the capacity code is Pallet and a work assignment includes 10 sub-LPN picks that can fit on 1 pallet, the application uses the count of 1 pallet to determine capacity utilization. Additionally, if the capacity code is Pallet, then any handling unit type used for the picks is considered a pallet for capacity calculations.<br > **Note**: Set the utilization percentage higher if staging lane space is limited so a high percentage of a location's capacity is required to be filled. Set the utilization percentage lower if you want to keep resource code groups within the appointment's assigned dock set or grouped closely together. If you do not enter a utilization percentage value, the application considers the value to be 0%, and the utilization percentage is not used during location reservation by resource code. |
| Automatic Release | If Yes, the pick release manager is enabled to release batches of picks after allocation.<br > If No, the picks must be released manually. |
| Pick Days | Days of the week that you allow picks to be released. This configuration prevents pick release from taking place on days that picks are not performed; for example, on weekends.<br > You use the **Exceptions** field to select the dates on which exceptions to the pick days occur. For example, you can select as an exception a holiday that falls on a day of the week that is set as a pick day. An exception reverses the pick day configuration. |
| Post Release | If Yes, the application processes the command specified in the **Command** field after the release of each schedule batch or combination code (as defined by the **Timing** field). For example, if the application is integrated with Warehouse Labor Management planning functionality, and you are sending pick information immediately, then your Blue Yonder project team may set the command to "register picks released" and the execution point to "After Combination Code Release."<br > When the Post Release field is set to Yes, the **Command** and **Timing** fields become available for configuration.<br > **IMPORTANT**: To avoid unexpected results, consult your Blue Yonder project team before changing the command.<br > If No, the application does not process a post-release command. |
| Command | Server command that is executed after pick release. A post-release command can be configured to perform special processing after the release of each schedule batch or combination code. For example, if this instance of Warehouse Management is integrated with Warehouse Labor Management planning functionality and you are sending pick information immediately, then your project team may set the command to "Register Picks Released" and the execution timing to "After Combination Code Release".<br > Register Picks Released is the only valid command distributed with Warehouse Management and should only be selected when the instance is integrated with Warehouse Labor Management planning functionality and you are sending pick information immediately.<br > Contact your Blue Yonder project team before changing this value.<br > Only available when the **Command** field is set to Yes. |
| Timing | The point at which the application executes the post release command.<br>-   • **After Combination Code Release**: The command is executed after picks that have the same combination code are released. The command is initiated only once for each combination code. A combination code indicates that separate identical picks (such as for separate order lines) have been combined into one single pick, so that the user does not have to perform separate picks from the same location.
<br>-   • **After Scheduled Batch Release**: The command is executed after the picks associated with a scheduled batch are released. Since batches of picks may be released over time, the post release command may be executed multiple times.
<br > Only available when the **Command** field is set to Yes. |
| Log File | Name of the log file, such as PckRelMgr.Sts, that you want to be created in the LESDIR log directory, and to which status (.sts) files will be added during each pick release cycle.<br > A log status file contains detailed information about each pick release allocation attempt. Log files are often useful for debugging, but generating these files can slow down performance; therefore, it is recommended that you provide a log file name only if you are having problems with pick release processing and want to use the log files to troubleshoot the issues. If you do not want to generate log files, then do not provide a value in this field. |
| Threshold Pick Operation | Work operation that identifies the type of directed work that is created for a threshold pick. See [Work Operations](../../work/work/work-operations.md). |
| Reload Locations for Each Pick | If Yes, the application reloads the available staging locations during each pick release session in a schedule batch, so that the application can select the best staging location for the pick. Select Yes if you have dock door and staging lane associations defined, and you want to use these preferred locations for the following situations:<br>-   • You have picks that are not associated with a load at the time of pick release; for example, the picks are for less than truckload (LTL), parcel, or unplanned truckload (TL) transport modes.
<br>-   • Staging locations are assigned at the shipment, stop, order, or another level other than by carrier or by load ID.
<br > Selecting Yes requires additional processing to take place and may slow down the pick release process.<br > If No, then during pick release, the application loads available staging locations only once per destination (staging) zone and uses the cached list during further pick release processing. Select No if you have not defined staging and dock door associations, or if these associations are defined but staging locations are only assigned by carrier or by load ID. |
| Resource Location Pallet Volume | Value that represents the cubic volume of a full pallet. The application uses this default value when determining a resource location to use in a processing area (such as overpack, consolidation, or staging). For example, a value of 120960 cubic inches represents the volume of a full pallet that measures 42 x 48 x 60 inches. To change a measurement unit, click the unit next to the field, and select a different unit. |
| Empty Pallet Weight | Value that represents the weight of an empty standard pallet. To change a measurement unit, click the unit next to the field, and select a different unit. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
