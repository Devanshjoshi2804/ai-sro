---
title: "Processing Locations"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/processing_locations.htm"
source: "/content/processing_locations.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Warehouse"
  - "Locations"
  - "Processing Locations"
sections:
  - "Add processing areas and locations"
  - "Modify multiple processing locations"
  - "Modify a processing location"
  - "Delete a processing location"
  - "Dimension fields"
  - "Location fields"
images:
  - "/content/resources/images/image429922.png"
source_sha1: e83e0ac17ee2db8162b6fbfb2f6b761e274c51db
---
# Processing Locations

A processing location is used for special handling or manipulation of inventory as it is moved through the facility. For example, you may have the following types of processing locations:

-   Pack station locations to which inventory is deposited to be packed into outbound containers for shipping
-   Audit station locations to which outbound containers are deposited for an operator to verify that the inventory physically picked to the container matches what the application shows for the container
-   Consolidation locations to which cases of inventory are deposited to be combined with other cases on a pallet for shipping
-   Distribution locations to which inventory for distributions is consolidated prior to shipping
-   Inbound pallet build locations to which received inventory is consolidated prior to putaway, distribution, replacement picks, or cross dock

## Add processing areas and locations

You must complete each step in the configuration before moving to the next step. Once you complete a step you can go back to a previous step by clicking **Back** or by clicking a step in the progress bar.

1.  Select **Configuration > Warehouse > Locations > Processing Locations**.
2.  From the **Actions** drop-down list, select **Add.**

1.  To add a new area:
    1.  Click **Add a New Area**.
    2.  Enter a name, description, and building.
    3.  To define the boundaries of the area on the floor plan:
        1.  Click **Draw**. A boundary box appears on the floor plan.
        2.  To move the boundary box, click and drag the center to a new position.
        3.  To adjust the size of the boundary box, click and drag the edges to new positions.
            
    4.  Click **Save**.
2.  In the grid, select the check box next to the area, and then click **Next**.
3.  In the **Starting Location** field, enter an identifier for the first location in the range of locations to create.
4.  In the **Ending Location** field, enter an identifier for the last location in the range.
    
    **Note**: Starting and ending location identifiers can include numbers and letters, but the entries must have the same naming format and length. For example, if the starting location is 01, the ending location can be any two-digit number (01-99); if you wanted the ending location to be 100, the starting location must be 001 (or any three-digit number). Alternatively, if the starting location is A01, the ending location must be constructed of a single letter followed by a two-digit number, for example, A30.
    

1.  From the **Select the function of these processing locations** drop-down list, select the location type. The attributes defined for the location type are applied to the new processing locations.
2.  Click **Add Locations**.

1.  Under **Verify Locations**, verify or edit the locations that were added:
    
    **Note**: A conflict indicates that a location with the same name already exists. You must resolve conflicts before continuing to the next step in the process.
    
    -   To view a list of the locations within a range, click ![Expand](../../../../../images/resources/images/image429922.png).
    -   To delete a range of locations, in the grid, select the check box next to the range, and then click **Delete**.
    -   To delete a single location, in the grid, expand the location range, select the check box next to the location, and then click **Delete**.
2.  Click **Next**.

1.  Define location size and capacity:
    
    **Note**: Size and capacity must be specified for every location, but can be specified for multiple locations at the same time.
    
    1.  Under **Select Locations**, select a location or range of locations.
        
        **Note**: In the grid, press and hold **Shift** to select consecutive values or press and hold **Ctrl** to select nonconsecutive values.
        
    2.  Under **Define Dimensions**, enter information in the [Dimension fields](#Dimension_fields).
    3.  Click **Apply**.

1.  Click **Next**.

1.  Review the list of locations:
    1.  To make changes, click **Back** to return to a previous page.
    2.  If no changes are required, click **Finish**.

## Modify multiple processing locations

You can configure or change one or more attributes for multiple locations all at the same time.

1.  Select **Configuration > Warehouse > Locations > Processing Locations**.

1.  In the grid, select the check box next to the locations to update.
2.  From the **Actions** drop-down list, select **Update Location Attributes**.
3.  In the **Attributes** column, select the attribute value to apply. The current value is displayed in the **Current Values** column for each selected location. You can select a value for multiple attributes.
    
    **Note**: If you do not want an attribute value to be changed, leave the attribute field blank. For information about an attribute, see [Location fields](#Location_fields).
    
4.  To clear the value of an attribute for all of the selected locations:
    
    **Note**: The option to clear all values is not available for Yes/No values.
    
    1.  In the **Attributes** column, select the attribute.
    2.  Select the **Clear all values in this field** check box. Doing so renders the attribute value blank for all of the selected locations.
5.  Click **Save**. A message is displayed indicating the number of locations that were updated or failed to update.
6.  Click **OK**.

## Modify a processing location

1.  Select **Configuration > Warehouse > Locations > Processing Locations**.

1.  In the grid, click the location name.
2.  Enter information in the [Location fields](#Location_fields).
3.  Click **Save**.

## Delete a processing location

1.  Select **Configuration > Warehouse > Locations > Processing Locations**.

1.  In the grid, select the check box next to the location to delete.
2.  Click **Delete**. A confirmation message is displayed.
3.  Click **OK**.

## Dimension fields

 
| Field | Description |
| --- | --- |
| Select how you track capacity in these locations | The application calculates capacity to determine when a location is full or to initiate other processes that are based on location capacity thresholds, such as count near zero counts, and replenishments.<br>-   • **Pallets**: Expresses capacity in the number of pallets or LPNs that the location can hold. When **Pallets** is selected, the **How many pallets are allowed in each location** field is also available. For example, if the maximum capacity specified for a location is 2, then the application allows 2 pallets or LPNs into the location before changing its status to full. However, depending on the location's pallet stack restriction, the capacity may be adjusted based on the item being stored.
<br>-   • **Volume**: Expresses capacity by volume (length x width x height) of space available in the location. When **Volume** is selected, the **Enter the maximum volume** field is also available. For example, to determine volume for a location in a floor storage area, you can determine the maximum height that inventory can be stacked in the location, and then multiply that number by the width and length of the location. This value is typically used for floor storage areas or for pickfaces when items are not assigned to the specific locations. However, depending on the location's pallet stack restriction, the capacity may be adjusted based on the item being stored.
<br>-   • **Length**: Expresses capacity in the total length of all of the cases in the location as if the cases were placed end-to-end. When **Length** is selected, the **Default Maximum Capacity** field is also available. It is typically used for case flow rack areas. Therefore, if the maximum capacity specified for a location in the area is 250, it will be considered full when the length of all the cases in the location adds up to 250.
<br>-   • **Eaches**: Expresses capacity as the quantity of pieces (stocking units of measure) of inventory that fit in the location. When **Eaches** is selected, the **How many eaches are allowed in each location** field is also available. Typically, a product is assigned to a specific location in the area. For example, a bin location that is assigned or reserved for 7-inch screws can be defined to hold 500 of these screws.
<br>-   • **Unlimited**: The locations have no capacity restrictions. This value is generally used for temporary storage locations such as a damaged or pickup and deposit location.
<br>-   • **Case Dimension**: Expresses capacity by the dimension of a case of inventory. When location capacity is set to **Case Dimension**, the **How many cases can case dimension location hold** field is also available for you to define the maximum capacity. The location can support a case of any size, as long as it fits within the location dimensions. In addition, you can limit the number of cases stored in the location by specifying a value for maximum capacity. The application calculates available space based on the assumption that cases are stored side by side.
<br>-   •
    
    **Transport Equipment**: Expresses capacity in the number of pieces of transport equipment that the location can hold. When **Transport Equipment** is selected, the **Enter the maximum equipment capacity allowed in each location** field is also available.
    
    <br>
    
    **Note**: Transport Equipment is only available as a selection for yard locations.
    
    <br> |
| How many pallets can these locations hold | Maximum number of pallets of inventory that can be stored in the location when pallet stack height is not applicable. If you use stacking restrictions, the application may recalculate this value and adjust a location's maximum capacity based on the pallet stacking restriction you selected. |
| How do you want to limit the stacking height of your pallets in these locations | Value that determines how pallets are stacked in the location and if the location's maximum capacity is recalculated based on the stack method or pallet stack height defined for the item stored in the location.<br>-   • **No Stacking Restrictions**: The application does not adjust the maximum capacity of the location based on the stack method or pallet stack height defined for the item being stored.
<br>-   • **Pallet Stack Height**: The application may adjust the location's maximum capacity to a lower value based on the stack height defined for the item footprint being stored in the location. For example, assume a location can store 3 pallets on the floor level and has a default maximum capacity of 9 pallets. If the footprint for an item being stored there has a stack height of 2, the default maximum capacity is adjusted to 6 pallets. However, if the item's stack height is 4, the application does not adjust the capacity to 12 because it is higher than the location's original maximum capacity.
<br>-   • **Interlock Stack Method**: The application may adjust the location's maximum capacity to a lower value based on the stack method defined for the item footprint being stored in the location. For example, assume a location can store 3 pallets on the floor level and has a default maximum capacity of 9 pallets. If the footprint for an item being stored has a stack method requiring the second level to have 1 less pallet than the first level and the third level to have 2 less pallets than the first level, then the application adjusts the maximum capacity from 9 pallets to 6 and displays the stack method to the operator. However, the application does not adjust a location's maximum capacity to a value greater than the original maximum capacity for the location. |
| Enter the maximum volume | Maximum volume of inventory that you can store in the location when pallet stack height is not applicable. If you selected a pallet stacking restriction, the application may recalculate this value and adjust the location's capacity based on the pallet stacking restriction and the inventory stored in the location. |
| How many eaches are allowed in each location | Maximum number of eaches (pieces) of inventory that can be stored in the location. This value is used to define capacity based on individual stocking units of an item. |
| Default Maximum Capacity | Length of the location that can be used for inventory. Locations in which capacity is determined by length are typically case flow rack locations. The length is used to determine the number of cases that can fit in the location when the cases are placed end to end. |
| Enter Dimensions | Enter the length, width, and height for the location. To change a measurement unit, click the unit next to the field, and select a different unit. |

## Location fields

 
| Field | Description |
| --- | --- |
| Area | Identifier for an area. Areas are used for grouping and sorting locations in the warehouse. For example, an area named STAGING can be used to group ship staging locations; an area named CASEPICK can be used to group case pickface locations. |
| Aisle | Identifier for a passageway in the facility where operators and equipment move between racks or blocks of locations, typically to put away or pick inventory. You typically define aisles and then, in the process of defining storage locations, you can assign locations to the aisle in which they are located (a single location can be assigned to only one aisle). |
| Bay | Identifier used in a location numbering scheme to group locations typically by the type of racking that is present (such as flow racks, floor locations, or shelving), the number of pick levels, and the size or appearance of the racking. |
| Level | Identifier used in a location naming scheme to identify the level in a multilevel rack or storage aisle. |
| Position | Identifier used in a location naming scheme to identify a location's position within a bay. |
| Dock Set | Name of the dock set to which the dock door belongs. A dock set is a group of one or more dock doors in the same area. A dock door can belong to only one dock set. |
| Location Type | Category that is used to group and configure locations that are used for similar purposes, regardless of their proximity to one another. Location type attributes define how the application tracks and processes inventory or transport equipment in the location. |
| Voice Check Digit | Number used to represent the location in facilities that use voice terminals. When the voice terminal operator is required to confirm a location, the operator can speak the voice check digit to identify the location to the application.<br > By default, the three check digit fields for a location are titled **First (Primary)**, **Middle**, and **Last**. The value in the first (primary) field is the number that operators must speak to confirm the location during voice operations. However, if the **Check Digit Rotation** field is set to Yes in the voice picking configuration, the voice device prompts the operator for one of the three check digit values to use for a picking assignment.<br > For example, when an operator begins a picking assignment, the voice device might speak "Middle," meaning the operator must use the middle check digit value to confirm each pick and deposit location for the assignment. The application randomly selects a check digit for each assignment.<br > You can change the description that is spoken to voice operators for each check digit field using the Voice Check Digit Schemes configuration. See [Configure voice picking](../../outbound/picking/voice-picking.md).<br > If check digit rotation is disabled, then the middle and last check digits are not needed.<br > **Note**: Check digit rotation is only used during picking operations. During other voice operations that require check digit confirmation, such as replenishments, putaway, or distribution, the application always prompts for the first (primary) check digit. |
| Verification Code | Code that identifies a physical location in a warehouse, and that can be used to ensure that operators are traveling to and scanning a particular physical location. For facilities that use verification codes and location codes to identify locations, you can require that RF operators scan the verification code to confirm that they have arrived at a particular physical location. If scanning the verification code is required, and the operator scans the location code instead, then a message is displayed indicating that the verification code must be entered. The operator cannot continue until the verification code is scanned. If the verification code is not unique, the operator is also required to scan the location code. |
| ABC Code | Code that determines how often the item is counted in a single count period. Select an ABC code if the application is configured to generate cycle counts by item automatically. The frequency assigned to each ABC code is defined in inventory counting settings. You typically select a code based on the value of the item; for example, assign the A code to expensive items that you want to closely monitor, and the C code to items to do not need to be counted as often. |
| Velocity Category | Identifies the speed at which inventory stored in a location moves in and out of the warehouse. Velocity is used to optimize warehouse space and inventory handling by placing fast moving items in the best locations for quick picking, and slower moving items in the less accessible storage locations. The application accomplishes this by attempting to match the velocity of an item with the velocity of a location when finding a location for storing an item. |
| Top-Off Replenishment Percentage | Level of inventory to which the application attempts to replenish a location. This value represents a percentage of maximum capacity for the location. For example, if you set the percentage to 90, the application replenishes the location to 90% of its capacity. |
| Replenishment Percentage | Percentage of a pickface location's maximum capacity that is eligible to be filled by an emergency or demand replenishment. For example, assume the value of this field is 60% and the location has a capacity of 200. If inventory is being moved to this destination location to satisfy a demand or emergency replenishment, then the maximum that can be allocated is 120 (60% of 200).<br > In order for replenishments to a destination location to be successful, the location must have available capacity, or the location must be in a movement zone configured with the **Fill to Capacity** field set to Yes. |
| Dock Access | Dock access group assigned to the location. A dock access group is an attribute that can be assigned to transport equipment types and dock door locations. The application uses the dock access group to sort and display locations during check in and when moving equipment to a door location based on the transport equipment type. If the dock access group assigned to an available door location is also assigned to the type of transport equipment being checked in or moved, then the door location is displayed first in the list of available locations (before the mismatched doors). See [Dock Access Groups](dock-access-groups.md). |
| Backfill Location | Name for the backfill location associated with the master location. A backfill location is a warehouse location that can be accessed from two separate physical aisles with different coordinates. The back of the location in one aisle is used to deposit or replenish inventory to the location, and the front of the location in the second aisle is used for picking inventory from or counting inventory in the location. The backfill location is not used in warehouse processing and is not stored in the master location database table. Instead, the backfill location name serves as an alternate identifier when an operator confirms a backfill location during a deposit or replenishment. Additionally, you can search and filter data using the backfill location name. See [Backfill locations](location-types.md). |
| Backfill Verification Code | Code that identifies a backfill location in a warehouse, and that can be used to ensure that operators are traveling to and scanning the back of a particular location. A backfill location is a warehouse location that can be accessed from two separate physical aisles with different coordinates. The back of the location in one aisle is used to deposit or replenish inventory to the location, and the front of the location in the second aisle is used for picking inventory from or counting inventory in the location.<br > For facilities that use verification codes and location codes to identify locations, you can require that RF operators scan the backfill verification code to confirm that they have arrived at the back of a physical location (instead of the location pickface in an adjacent aisle). Operators are required to scan the back of a backfill location when depositing or replenishing inventory. If scanning the backfill verification code is required and the operator scans the location code or the front of the location instead, then a message is displayed indicating that the backfill verification code must be scanned. If the backfill verification code is not unique, then the operator is also required to scan the location code. |
| Backfill Voice Check Digit | Number used to represent the back of a location in facilities that use voice terminals and backfill locations. A backfill location is a warehouse location that can be accessed from two separate physical aisles with different coordinates. The back of the location in one aisle is used to deposit or replenish inventory to the location, and the front of the location in the second aisle is used for picking inventory from or counting inventory in the location. When the voice terminal operator is required to confirm the back of a location, such as during a replenishment, the operator can speak the backfill voice check digit to identify the back of the location to the application.<br > By default, the three backfill check digit fields for a location are titled First (Primary), Middle, and Last. The value in the first (primary) field is the number that operators must speak to confirm the back of the location during voice operations. The Middle and Last backfill check digits are not used because check digit rotation is only used in picking operations, and backfill locations are used strictly for deposits. |
| Location Length | Length of the location. To change a measurement unit, click the unit next to the field, and select a different unit. |
| Location Width | Width of the location. To change a measurement unit, click the unit next to the field, and select a different unit. |
| Location Height | Height of the location. To change a measurement unit, click the unit next to the field, and select a different unit. |
| Location Volume | Maximum cubic volume of a location, calculated by the application as a function of location length x location width x location height, if those values are entered. |
| Maximum Weight Validation | If Yes, the application prevents the deposit of inventory that would cause the total weight on the location to exceed the value defined by the **Maximum Weight** field.<br > If No, the application does not perform weight validation for the location. |
| Maximum Weight | Maximum amount of weight that can be stored in the location. The application uses this value in determining the best location for inventory and does not release work or direct inventory to a location that does not have the capacity to hold the inventory. For example, the application validates the weight restriction (along with dimension and capacity restrictions) before releasing work when the defined movement path includes hops (such as P&D locations) for the inventory. To change a measurement unit, click the unit next to the field, and select a different unit.<br > The **Maximum Weight** field is only available if the **Maximum Weight Validation** field on the location is set to Yes. |
| Location Capacity Code | Value that identifies how the application calculates the capacity for the location. This value is used in conjunction with the value for **Maximum Capacity**, which specifies an amount.<br>-   • **Case Dimension**: Expresses capacity by cases. During storage and replenishment, the application ensures that the available space in the assigned location is large enough to accommodate the case dimensions. In addition, you can limit the number of cases or sub-LPNs stored in the location by specifying a value for **Maximum Capacity**.
<br>-   • **Each**: Expresses capacity as the quantity of pieces (stocking units of measure) of inventory that fit in the location.
<br>-   • **Length**: Expresses capacity by the length of the location. Capacity by length is typically used for case flow rack locations. The application determines the number of cases that can fit within the length of location when the cases are placed end to end.
<br>-   • **Pallet**: Expresses capacity in the number of pallets or LPNs that the location can hold.
<br>-   • **Volume**: Expresses capacity in the volume (length x width x height) of space available in the location.
<br > For examples, see [Location capacity](../locations.md). |
| Maximum Capacity | Maximum capacity of the location based on the location capacity code. For example, if **Location Capacity Code** is set to Pallet, then the value for **Maximum Capacity** represents the maximum number of pallets that can reside in the location.<br > The application uses this value to determine the best location for inventory and does not release work or direct inventory to a location that does not have the capacity to hold the inventory. For example, the application validates the capacity restriction (along with dimension and weight restrictions) before releasing work when the defined movement path includes hops (such as P&D locations) for the inventory.<br > When pallet stack height is applied, which varies depending on the item footprint stored in the location, capacity is calculated according to pallet volume (full pallet length x full pallet width x full pallet height).<br > **Note**: The **Maximum Capacity** is only considered for application-initiated inventory moves (application allocates location). The application does not validate user-initiated inventory moves (application does not allocate location) against this value. Application-initiated inventory moves are also validated against the location's pallet stack height and weight capacity, if enabled. |
| How many pieces of transport equipment can this location hold | Maximum number of pieces of transport equipment of inventory that can be stored in the location. This field is only available for yard locations. |
| Stacking Height | Value that determines how pallets are stacked in the location and if the location's maximum capacity is recalculated based on the stack method or pallet stack height defined for the item stored in the location.<br>-   • **No Stacking Restrictions**: The application does not adjust the maximum capacity of the location based on the stack method or pallet stack height defined for the item being stored.
<br>-   • **Pallet Stack Height**: Pallets in this location are stacked based on the item footprint's pallet stack height value. The application may adjust the location's maximum capacity to a lower value based on the stack height defined for the item footprint being stored in the location. For example, assume a location can store 3 pallets on the floor level and has a maximum capacity of 9 pallets. If the footprint for an item being stored there has a stack height of 2, the maximum capacity is adjusted to 6 pallets. However, if the item's stack height was 4, the application would not adjust the default capacity to 12 because it is higher than the location's original maximum capacity.
<br>-   • **Interlock Stack Method**: Pallets in this location are stacked based on the item footprint's stack method value. The application may adjust the location's maximum capacity to a lower value based on the stack method defined for the item footprint being stored in the location. For example, assume a location can store 3 pallets on the floor level and has a maximum capacity of 9 pallets. If the footprint for an item being stored has a stack method requiring the second level to have 1 less pallet than the first level and the third level to have 2 less pallets than the first level, then the application would adjust the maximum capacity from 9 pallets to 6 and would display the stack method to the operator. However, the application does not adjust a location's maximum capacity to a value greater than the original maximum capacity for the location. |
| Picking Zone | Name of a picking zone. A picking zone represents a group of locations that share the same attributes for picking, such as the LPN level at which picks can be allocated, the cartonization group to which it belongs, and whether the location supports pick stealing, starter pallets, and pre-inventory allocation. The allocation search path searches picking zones when attempting to allocate inventory in the warehouse. Picks resulting from allocation reference the picking zone as the source. A location can belong to only one picking zone. |
| Storage Zone | A storage zone represents a group of locations that have the same attributes (consolidation, item mixing, date control, and others) for storing inventory. |
| Movement Zone | Name of a movement zone. A movement zone represents a group of locations to and from which inventory can be moved. For example, storage locations to which inventory can be deposited and processing locations to which inventory is moved for packing are the types of locations that must be assigned to a movement zone for the application to select those locations for putaway or deposit.<br > Source, hop, and destination locations must be assigned to a movement zone so that a movement path can be defined to use each of those locations. |
| Work Zone | Name or number that identifies a work zone. A work zone is a logical division of warehouse space made on the basis of physical layout and access by different types of warehouse equipment. A work zone exists inside a work area. |
| Count Zone | Name of a count zone. A count zone is a method of grouping locations for an inventory count. You may want to group locations into a count zone based on the type of counts that take place (RF or paper-based) and how counts are generated (manually or automatically). |
| Location Access | Name that can be assigned to locations and to pieces of warehouse equipment. In work management, the application offers directed work to operators based on whether their equipment access group matches the access group assigned to the location in which the directed work takes place. The application does not offer directed work to an operator if their equipment does not have an access group that matches that of the location in which the work needs to be performed. See [Location Access Groups](../../equipment/equipment/location-access-groups.md). |
| Escalation Type | Specifies the value by which the application escalates directed pick work.<br>-   • **Maximum Pallets**: The application escalates directed pick work from the selected location when the pallet quantity in the location exceeds the defined amount.
<br>-   • **Threshold Percent**: The application escalates directed pick work from the selected location when the pallet quantity percentage in the location exceeds the defined percent.
<br>-   • **Blank (no selection)**: Escalation of directed pick work is not determined by the location.
<br > You define the amount or percent in the **Escalation Threshold** field. |
| Escalation Threshold | Value by which the application escalates work in the location. When the amount of pallets in the location exceeds this threshold, the application increases the priority of existing pick work in the location. This value is only effective when an escalation type is selected in the **Escalation Type** field.<br > The escalation increment and time are determined by the work operation. See [Escalation based on a location](../../work/work/work-operations.md). |
| Travel Sequence | Numeric value, ranging from low to high, that represents the optimal travel sequence in which an operator is directed from one location to the next when performing directed work. |
| Count Sequence | Number that is used to sequence counting activities within the facility. When requesting counts for a range of locations, the application can use this value to determine the order in which to count the locations within the range. |
| Slotting Sequence | Number that is used by Slotting to determine the order in which this location is considered for slotting. A slotting sequence number is a common location attribute on which to base an attribute rule for a location set. Attribute rules direct Slotting in how to slot locations. An attribute rule that combines the slotting sequence number with an increasing sort order directs Slotting to use the slotting sequence number value for each location within a location set. Then, based on those values, Slotting arranges the locations so that the location with the lowest sequence number is slotted first. |
| Storage Sequence | Numeric value that represents the sequence in which the application considers the location for putaway in relation to other locations with storage sequences in the same storage zone. The application evaluates the sequence in order from lowest number to highest. If a storage sequence is not defined, the application uses the travel sequence.<br > **Note**: For outbound inventory (such as during picking), the application uses travel sequence to direct an operator from one location to the next. |
| Allocate to Empty Sequence | Value that identifies the sequence in which inventory in the location is allocated when compared to other locations in the same zone. When a pick zone is configured with the **Allocate to Empty** field set to Yes, the application allocates from one location in the zone until it is empty before allocating from another location.<br > The **Allocate to Empty Sequence** determines the order in which the application considers locations in a zone for allocation; the lower the sequence value, the higher the location's allocation priority. The sequence is set automatically by the application or manually by a user, depending on the pick zone configuration.<br > For example, assume ITEM01 is stored in LOC-A and LOC-B, and that LOC-A and LOC-B have allocate to empty sequences of 100 and 200, respectively. When the application allocates ITEM01, the inventory in LOC-A is allocated first until the location is empty, and then the application allocates ITEM01 from LOC-B.<br > The allocate to empty process is intended to be used in pick zones that have single-item locations, not pickface locations. See [Allocate to empty process](../../outbound/allocation/pick-zones.md).<br > **Note**: If two or more locations have identical allocate to empty sequence numbers, the application evaluates the allocate to empty dates and uses the location that had its allocate to empty sequence set first as the primary allocation source. |
| Allocate to Empty Date | Date on which inventory in the location was first allocated in a pick zone with the **Allocate to Empty** field set to Yes. |
| Replenishment | If Yes and if replenishment processing is enabled, the application evaluates this location for replenishment opportunities.<br > If No, the application does not evaluate the location for replenishment. |
| Storable | If Yes, the location is used to store inventory, and the application evaluates the location for the purpose of directing additional inventory to the location.<br > If No, the location can still be used to store inventory, but the application does not direct additional inventory to the location. |
| Pickable | If Yes, the application evaluates the inventory in the location during order allocation processing to determine if it can be used for order fulfillment.<br > If No, the application does not include the location in order allocation processing. |
| Summarize Existing Picks | If Yes, then when verifying inventory for existing picks before allocating new pick requests, the application logically combines existing eligible outstanding picks for the same item into one summarized pick for this location. Eligible picks are at the sub-load and detail level, have the same required attributes, and use simple allocation rules or no allocation rules. This allows for faster allocation of remaining inventory in the location and does not affect the picking process.<br > If No, then when verifying inventory for existing picks before allocating new pick requests, the application does not summarize existing picks for this location. Picks are allocated separately, which may result in longer processing times.<br > For example, assume there are 500 existing eligible picks for a location and 5 new requests for the same item. If this field is set to Yes, then to verify the available inventory in the location before allocating the new requests, the application reprocesses and reserves the total quantity of the existing picks as one summarized pick to be allocated at the same time. Therefore, the application processes 6 pick requests during allocation, one for the 500 existing picks and five more for the new requests. If this field is set to No, then the application reprocesses and reserves inventory for the 500 existing picks separately. Therefore, the application processes 505 pick requests during allocation. Regardless of how this field is configured, the picks are completed separately. |
| Count Back | If Yes, the location is enabled for count back. Count back is a pick verification task that applies when the operator is picking less than a full pallet from a location. If the item, location, UOM, and the operator (user) are enabled for count back, then the application requires the operator to capture the quantity of inventory that is left in addition to the quantity of inventory being picked. If the remaining quantity does not match the application-expected quantity, a count is generated. If the operator is authorized to do the count, the application prompts the operator to complete it; otherwise, a supervisor must resolve the discrepancy using an audit count.<br > If No, count back picking verification is not enabled or required for the location. |
| Permanently Assigned | If Yes, then the location is permanently assigned to an item even after assignments made using location preference rules are deleted or the location is emptied. If the preference rule assignment is deleted, then the location is reserved for future use with no specific item. Also, if set to Yes, and if the **Assignment** field is also set to Yes, replenishment processing does not use the location for future item assignments to the location.<br > If No, then the location is not permanently assigned to an item. If this field is set to No and a replenishment item configuration exists and the location is already assigned to an item, the assignment remains selected. However, if this field is set to No and a replenishment item configuration does not exist, the application clears the assignment when the location is emptied so that a different item than previously assigned can be stored in the location. |
| Assignment | If Yes, and the location is a storage location, the location is reserved for an item as defined by a location preference rule. The application does not direct operators to store any other item in the location. A location to which an item has been assigned cannot be deleted until the item location assignment is removed. If the location is not a storage location, selecting Yes indicates that the location is reserved for a specific purpose, such as to reserve it (if it were a staging lane) for a specific carrier.<br > If Slotting is installed and enabled, location assignments are created by the slotting plan. When the slotting plan is executed, some locations may not be slotted, resulting in the location assignments being removed and setting this field to No.<br > If No, then there is no item assigned to the location. |
| Assigned Item | Item that is assigned to the location. One or more items can be assigned to a location through storage location preference rules. When an item is assigned to a location, the application does not direct any other item to the location even if the location becomes empty. If multiple items have been assigned, then only the first item is displayed in the **Assigned Item** field. |
| Billing | If Yes, the location is evaluated for inventory that belongs to a client that is enabled for third-party billing. If this field is set to Yes, then on a scheduled basis, the application captures the details of the client's inventory in the location and generates a client billing transaction. Billing transactions are sent to the External Billing application. The **Billing** field is only available if an External Billing System is integrated with Warehouse Management. See [General Integration](../../integration/general-integration.md).<br > If No, the location is not included in billing storage transactions. |
| Report Printer | Name of the printer that will be used to print reports from this location. Only printers that have been configured to print reports are available for selection. You can assign a printer to a location so that when printing takes place at the location as a result of a workflow action, paperwork is directed to the assigned printer by default. |
| Label Printer | Name of the printer that will be used to print labels from this location. Only label printers that have been set up and configured to work with the application are available for selection. You can assign a printer to a location so that when printing takes place at the location as a result of a workflow action, paperwork is directed to the assigned printer by default. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
