---
title: "Procedures for locations"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/procedures_for_locations.htm"
source: "/content/procedures_for_locations.htm"
toc_path:
  - "Warehouse Management"
  - "Shared functions"
  - "Inventory"
  - "Procedures for locations"
sections:
  - "Apply a hold to inventory"
  - "Release a hold from inventory"
  - "Add inventory to a location or LPN"
  - "Set or reset a location error status"
  - "Set or reset a location out of service"
  - "Generate or cancel a replenishment for a location"
  - "Generate or cancel a cycle count for a location"
  - "Maintain a location"
  - "View locations"
  - "View detailed location information"
  - "Inventory mass update"
  - "Location fields"
  - "Location Summary fields"
  - "Location Items fields"
  - "Location Minimum Handling Unit fields"
  - "Location History fields"
  - "Inventory Attributes fields"
  - "Add Inventory fields"
images: []
source_sha1: 3f3dcc916c861c9899c4817ff43e286d7e2cbd0e
---
# Procedures for locations

You can perform these procedures using the Inventory page, which is accessible from the following modules: **Inventory**, **Outbound Planner**, **Picking**, **Production**, **Receiving**, or **Shipping**.

## Apply a hold to inventory

You can apply one or more holds to the same inventory. When you apply a hold to an item, all of the inventory for that item is held, regardless of the LPN on which the inventory is located. When you apply a hold to inventory on a specific LPN, only the inventory on that LPN is held.

You can also apply a hold to an item or inventory in a location by viewing the detailed information for a location or item (on the Summary tab). See [View detailed LPN information](procedures-for-lpns.md) and [View detailed item information](procedures-for-items.md).

1.  Perform one of the following tasks:
    -   View the Inventory page, select **On-Site**, and then perform one of the following tasks:
        
        1.  Select one of the following modules: **Inventory**, **Outbound Planner**, **Picking**, **Production**, **Receiving**, or **Shipping**.
        2.  Select **Inventory**.
        
        -   To apply a hold to an item, select **Items**, and then in the grid, select the check box next to the item.
        -   To apply a hold to inventory on a specific LPN, select **LPNs**, and then in the grid, select the check box next to the LPN.
        -   To apply a hold to inventory in a specific location:
            1.  Select **Locations**.
            2.  In the grid, click the location. The location details are displayed.
            3.  Perform one of the following tasks:
                -   To apply a hold to an item in the location, select **Items**, and then in the grid, select the check box next to the item.
                -   To apply a hold to an LPN in the location, select **LPNs**, and then in the grid, select the check box next to the LPN.
    -   View a grid with a link for a location, click the location, and then select one of the following: **Items** or **LPNs**.
    -   View a grid with a link for an item, and then click the item.
2.  From the **Actions** drop-down list, select **Apply Hold**. The Apply Hold page is displayed with a list of existing hold definitions.
3.  To add a hold definition:
    1.  Click **Add Hold**.
    2.  Enter information in the [Holds fields](../../inventory/holds/procedures-for-holds.md).
    3.  If the **Apply to Inbound Inventory** field is set to Yes, then define the criteria for the inventory to which the hold will be automatically applied at the time of receipt:
        1.  Under **INBOUND PROCESSING**, click **Inventory Criteria**.
        2.  Enter information in the [Inbound Hold Criteria fields](../../inventory/holds/procedures-for-holds.md).
        3.  Click **Apply**.
    4.  Click **Save**.
4.  In the grid, select the hold to apply, and then click **Apply**. The Apply Hold window is displayed.
5.  Enter information in the following fields:
    
     
    | Field | Description |
    | --- | --- |
    | Change Inventory Status | Status to which the held inventory is changed. This field is only displayed if the **Inventory Status** field on the hold configuration is set to Yes. |
    | Change Only Certain Statuses | Indicates that the status for certain held inventory is to be changed based on its current status. If selected, then for each inventory status, in the **To Inventory Status** column, select the status to apply to the inventory. For example, you may only want to update the status for inventory that has an Available status, while keeping the remaining held inventory in its current status. This field is only displayed if the **Inventory Status** field on the hold configuration is set to Yes. |
    | Reason | Value that indicates why the hold is being applied. A reason is required whenever a hold is applied to inventory. |
    
6.  Click **OK**. A confirmation message is displayed.

**Note**: If the application was unable to apply the hold, then a list of the LPNs is displayed with the reason the hold could not be applied.

8.  Click **OK**.

## Release a hold from inventory

You can release a hold to remove the hold from the inventory.

1.  Perform one of the following tasks:
    -   View the Inventory page, select **On-Site**, and then perform one of the following tasks:
        
        1.  Select one of the following modules: **Inventory**, **Outbound Planner**, **Picking**, **Production**, **Receiving**, or **Shipping**.
        2.  Select **Inventory**.
        
        -   To release a hold from an item, select **Items**, and then in the grid, select the check box next to the item.
        -   To release a hold from inventory on a specific LPN, select **LPNs**, and then in the grid, select the check box next to the LPN.
        -   To release a hold from inventory in a specific location:
            1.  Select **Locations**.
            2.  In the grid, click the location. The location details are displayed.
            3.  Perform one of the following tasks:
                -   To release a hold to an item in the location, select **Items**, and then in the grid, select the check box next to the item.
                -   To release a hold to an LPN in the location, select **LPNs**, and then in the grid, select the check box next to the LPN.
    -   Select **Inventory > Holds**, and then perform the following tasks:
        1.  Select **Active Holds**.
        2.  Click a hold, and then select **LPNs**.
        3.  In the grid, select the check box next to the LPN, or click the LPN.
        
        **Note**: To release all inventory under an active hold, instead of selecting **LPNs**, select **Summary** and then from the **Actions** drop-down list, select **Release All Inventory**. The Release Hold page is displayed.
        
    -   View a grid with a link for a location, click the location, and then select one of the following: **Items** or **LPNs**.
    -   View a grid with a link for an item, and then click the item.
2.  From the **Actions** drop-down list, select **Release Hold**. The Release Hold page is displayed.
3.  Select the hold to release, and click **Apply**. The Release Hold window displays.
4.  Enter information in the following fields:
    
     
    | Field | Description |
    | --- | --- |
    | Change Inventory Status | Status to which the held inventory is changed. This field is only displayed if the **Inventory Status** field on the hold configuration is set to Yes. |
    | Change Only Certain Statuses | Indicates that the status for certain held inventory is to be changed based on its current status. If selected, then for each inventory status, in the **To Inventory Status** column, select the status to apply to the inventory. For example, you may only want to update the status for inventory that has an Available status, while keeping the remaining held inventory in its current status. This field is only displayed if the **Inventory Status** field on the hold configuration is set to Yes. |
    | Reason | Value that indicates why the hold is being applied. A reason is required whenever a hold is applied to inventory. |
    
5.  Click **OK**. A confirmation message is displayed.
6.  Click **OK**.

## Add inventory to a location or LPN

You can add inventory to a storage location or LPN, such as when inventory is found that has not been identified. When you add the inventory, you can define all the inventory attributes.

1.  Perform one of the following tasks:
    -   [View locations](#View_locations).
    -   [View LPNs](procedures-for-lpns.md).
2.  In the grid, select the check box next to the location or LPN, or click the LPN.
3.  From the **Actions** drop-down list, select **Add Inventory**. The Add Inventory window is displayed.
4.  Enter information in the [Add Inventory fields](#Add_inventory_fields).
5.  Click **Next**.

**Note**: If serial number or catch quantity capturing is not required for the item, and if the item is tracked at the LPN level and you are receiving a quantity of 1, then the application processes the inventory. If you did not enter an LPN, an identifier is automatically generated.

7.  If the Number Capture window is displayed, perform the following tasks:
    1.  Under **Quantity**, perform one of the following tasks:
        -   To automatically generate the identifiers, click **Generate LPNs**.
        -   To enter a range of identifiers, click **Enter a range**, then enter a starting and ending value, and then press **Tab**.
        -   To enter individual identifiers, in the text box, enter the first identifier and then press **Enter**. Repeat this process until you have entered the required number of identifiers.
    2.  If the inventory is serialized and requires serial number capturing, then under **Serial Numbers**, enter a serial number for each LPN that requires it.
    
    **Note**: To enter a range of serial numbers, click **Enter Range**, then enter the range of numbers to apply to the inventory, and then press **Tab**.
    
    4.  If the inventory is catch tracked and requires a catch quantity, under **Catch Quantity**, enter a value for each LPN that requires it.
    5.  Click **Finish**.

## Set or reset a location error status

You can manually change the location status to error for any inventory issues and reset the location status once corrective actions have been taken. The application automatically sets the location status to error if an adjustment is being performed on a location. Resetting a location from error status sets the locations status to its previous state.

An error status places a hold on inventory activity in a location. The location is no longer available for storage, or for reserving the inventory in the location for orders. Any inventory activity for the location that was defined prior to setting the location in error can be completed, but no new activity is created. When the error status is removed (reset), activities can resume. You can set or reset error location for multiple locations on the Inventory page or a single location in the Location view.

1.  Perform one of the following tasks:
    -   [View locations](#View_locations).
    -   View a grid with a link for a location.
2.  In the grid, click the location or select the row for a location or multiple locations.
3.  To set a location to an error status:
    1.  From the **Actions** drop-down list, select **Error Location**. A confirmation message is displayed.
    
    **Note**: This action is disabled in the Location view when the location cannot be set to error status.
    
    3.  Click **Yes**. If the operation to set a location to error fails, the details of the failed operation is displayed.
4.  To remove the error status from a location:
    1.  From the **Actions** drop-down list, select **Reset Location**. A confirmation message is displayed.
    2.  Click **Yes**. If the operation to reset an error location fails, the details of the failed operation is displayed.

## Set or reset a location out of service

You can set a location to out of service to prevent the application from using the location or reporting inventory in the location. When the location is reset, the location becomes available for use and reporting.

1.  Perform one of the following tasks:
    -   [View locations](#View_locations).
    -   View a grid with a link for a location.
2.  In the grid, click the location to modify. The location details are displayed.
3.  To disable the location:
    1.  From the **Actions** drop-down list, select **Set Out of Service**.
    2.  Enter a reason for setting the location out of service.
    3.  Click **OK**. The location is set out of service and the **Out of Service** tag is displayed for the location.
4.  To enable the location for use:
    1.  From the **Actions** drop-down list, select **Set in Service**. A confirmation message is displayed.
    2.  Click **Yes**. The location is enabled and the **Out of Service** tag is removed from the location.

## Generate or cancel a replenishment for a location

When you request a replenishment for a location, the application allocates the inventory and creates replenishment picks to fill the location with inventory based on the top-off replenishment percentage defined for the storage location.

When you cancel a replenishment request, the pending pick work is cancelled. If you have multiple replenishments, then when you cancel a replenishment for the location, all the replenishments for the location are canceled. Cancelling a replenishment from the top-off location also cancels replenishment requests for the items in that location.

**Note**: You can generate replenishment only if a top-off replenishment location is available.

1.  View the Inventory page.
    
    1.  Select one of the following modules: **Inventory**, **Outbound Planner**, **Picking**, **Production**, **Receiving**, or **Shipping**.
    2.  Select **Inventory**.
    
2.  Select **On-Site**, and then select **Locations**.
    
    **Note**: To view all locations with a pending replenishment, from the **Quick Filters** drop-down list, select **Pending Replenishment**.
    
3.  In the grid, select the check box next to the location.
4.  To generate a replenishment for the location:
    1.  From the **Actions** drop-down list, select **Generate Replenishment**. A confirmation message is displayed.
    2.  Click **OK**. The **Pending Replenishment** tag is displayed for the location.
5.  To cancel a replenishment request:
    1.  From the **Actions** drop-down list, select **Cancel Replenishment**. A confirmation message is displayed.
    2.  Click **OK**. The **Pending Replenishment** tag is removed for the location.

## Generate or cancel a cycle count for a location

When you request a count, the application generates a cycle count for the location. When you cancel a cycle count, the pending count work is cancelled.

1.  Perform one of the following tasks:
    -   [View locations](#View_locations).
    -   View a grid with a link for a location.
2.  In the grid, click the location to modify. The location details are displayed.
3.  To request a count of the location:
    1.  From the **Actions** drop-down list, select **Generate Cycle Count**. A confirmation message is displayed.
    2.  Click **OK**. The **Pending Count** tag is displayed for the location.
4.  To cancel a count request:
    1.  From the **Actions** drop-down list, select **Cancel Cycle Count**. A confirmation message is displayed.
    2.  Click **OK**. The **Pending Count** tag is removed for the location.

## Maintain a location

1.  Perform one of the following tasks:
    -   [View locations](#View_locations).
    -   View a grid with a location link.
2.  In the grid, click the location to modify. The location details are displayed.
3.  From the **Actions** drop-down list, select **Maintain Location**.
4.  Click the **Enable Location** button to enable or disable the location.
5.  Enter information in the [Location fields](#Location_fields).
6.  To define the minimum number of handling units that you want to store in a location:
    
    **Note**: The minimum value can only be defined for a handling unit that is configured as Serialized.
    
    1.  Under **ATTRIBUTES**, click **Location Handling Unit Capacity**.
    2.  Perform one of the following tasks:
        -   To add a handling unit, click **Add**.
        -   To modify a handling unit, in the grid, click the handling unit type.
        -   To copy a handling unit, in the grid, select the check box next to the handling unit type, and then click **Copy**.
    3.  Enter information in the [Location Minimum Handling Unit fields](#Location_Minimum_Handling_Unit_fields).
    4.  Click **Apply**.
7.  Click **Save**.

## View locations

Perform one of the following tasks:

-   View the Inventory page, select **On-Site**, and then select **Locations**.

1.  Select one of the following modules: **Inventory**, **Outbound Planner**, **Picking**, **Production**, **Receiving**, or **Shipping**.
2.  Select **Inventory**.

-   To view dock door and yard locations, View the Door Activity page.
    
    1.  Select one of the following modules: **Receiving**, **Shipping**, or **Yard**.
        
    2.  Select **Door Activity**.
        
    
-   To view staging lanes and dock door locations, View the Staging page.
    
    1.  Select one of the following modules: **Receiving** or **Shipping**.
        
    2.  Select **Staging**.
        
    

## View detailed location information

1.  Perform one of the following tasks:
    -   [View locations](#View_locations).
        
    -   View a grid with a link for a location.
2.  In the grid, click the location. The location details are displayed.
3.  Select **Summary** and view information in the [Location Summary fields](#Location_Summary_fields).
4.  Select **Items** and view information in the [Location Items fields](#Location_Items_fields).
5.  Select **LPNs** and view information in the [LPN detail field listings](procedures-for-lpns.md).
6.  Select **Minimum Handling Unit** and view information in the [Location Minimum Handling Unit fields](#Location_Minimum_Handling_Unit_fields).
7.  Select **History** and view information in the [Location History fields](#Location_History_fields).

## Inventory mass update

You use inventory mass update to modify inventory attributes of multiple LPNs at the same time.

You enter the selection criteria to find the inventory that you want to change, and then enter new values for selected attributes. If you change the manufacturing or expiration date of existing inventory associated with an aging profile, the application recalculates the dates and updates the inventory status. If you change the footprint of existing inventory, the application recalculates the current quantity, volume, and length values for the locations where the inventory resides.

1.  View the Inventory page.
    
    1.  Select one of the following modules: **Inventory**, **Outbound Planner**, **Picking**, **Production**, **Receiving**, or **Shipping**.
    2.  Select **Inventory**.
    
2.  Select **On-Site**, and then select the **Locations**, **Items**, or **LPNs** tab.
3.  From the **Actions** drop-down list, select **Inventory Mass Update**. The Inventory Mass Update page is displayed with all the LPNs.
4.  In the filter, enter search criteria to select the inventory to change.

**IMPORTANT**: Attribute updates are applied to all of the displayed inventory.

6.  Click **Update Attributes**. The Update Attributes window is displayed.
7.  From the **Reason** drop-down list, select the reason for modifying the inventory.
8.  To add more information, in the **Comment** field, enter the information.
9.  Enter information in the [Inventory Attributes fields](#Inventory_Attributes_fields).
10.  Click **Save**. A confirmation message is displayed.
11.  Click **Yes**.
12.  Click **Done**.

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
| Voice Check Digit | Number used to represent the location in facilities that use voice terminals. When the voice terminal operator is required to confirm a location, the operator can speak the voice check digit to identify the location to the application.<br > By default, the three check digit fields for a location are titled **First (Primary)**, **Middle**, and **Last**. The value in the first (primary) field is the number that operators must speak to confirm the location during voice operations. However, if the **Check Digit Rotation** field is set to Yes in the voice picking configuration, the voice device prompts the operator for one of the three check digit values to use for a picking assignment.<br > For example, when an operator begins a picking assignment, the voice device might speak "Middle," meaning the operator must use the middle check digit value to confirm each pick and deposit location for the assignment. The application randomly selects a check digit for each assignment.<br > You can change the description that is spoken to voice operators for each check digit field using the Voice Check Digit Schemes configuration. See [Configure voice picking](../../configuration/outbound/picking/voice-picking.md).<br > If check digit rotation is disabled, then the middle and last check digits are not needed.<br > **Note**: Check digit rotation is only used during picking operations. During other voice operations that require check digit confirmation, such as replenishments, putaway, or distribution, the application always prompts for the first (primary) check digit. |
| Verification Code | Code that identifies a physical location in a warehouse, and that can be used to ensure that operators are traveling to and scanning a particular physical location. For facilities that use verification codes and location codes to identify locations, you can require that RF operators scan the verification code to confirm that they have arrived at a particular physical location. If scanning the verification code is required, and the operator scans the location code instead, then a message is displayed indicating that the verification code must be entered. The operator cannot continue until the verification code is scanned. If the verification code is not unique, the operator is also required to scan the location code. |
| ABC Code | Code that determines how often the item is counted in a single count period. Select an ABC code if the application is configured to generate cycle counts by item automatically. The frequency assigned to each ABC code is defined in inventory counting settings. You typically select a code based on the value of the item; for example, assign the A code to expensive items that you want to closely monitor, and the C code to items to do not need to be counted as often. |
| Velocity Category | Identifies the speed at which inventory stored in a location moves in and out of the warehouse. Velocity is used to optimize warehouse space and inventory handling by placing fast moving items in the best locations for quick picking, and slower moving items in the less accessible storage locations. The application accomplishes this by attempting to match the velocity of an item with the velocity of a location when finding a location for storing an item. |
| Top-Off Replenishment Percentage | Level of inventory to which the application attempts to replenish a location. This value represents a percentage of maximum capacity for the location. For example, if you set the percentage to 90, the application replenishes the location to 90% of its capacity. |
| Replenishment Percentage | Percentage of a pickface location's maximum capacity that is eligible to be filled by an emergency or demand replenishment. For example, assume the value of this field is 60% and the location has a capacity of 200. If inventory is being moved to this destination location to satisfy a demand or emergency replenishment, then the maximum that can be allocated is 120 (60% of 200).<br > In order for replenishments to a destination location to be successful, the location must have available capacity, or the location must be in a movement zone configured with the **Fill to Capacity** field set to Yes. |
| Dock Access | Dock access group assigned to the location. A dock access group is an attribute that can be assigned to transport equipment types and dock door locations. The application uses the dock access group to sort and display locations during check in and when moving equipment to a door location based on the transport equipment type. If the dock access group assigned to an available door location is also assigned to the type of transport equipment being checked in or moved, then the door location is displayed first in the list of available locations (before the mismatched doors). See [Dock Access Groups](../../configuration/warehouse/locations/dock-access-groups.md). |
| Backfill Location | Name for the backfill location associated with the master location. A backfill location is a warehouse location that can be accessed from two separate physical aisles with different coordinates. The back of the location in one aisle is used to deposit or replenish inventory to the location, and the front of the location in the second aisle is used for picking inventory from or counting inventory in the location. The backfill location is not used in warehouse processing and is not stored in the master location database table. Instead, the backfill location name serves as an alternate identifier when an operator confirms a backfill location during a deposit or replenishment. Additionally, you can search and filter data using the backfill location name. See [Backfill locations](../../configuration/warehouse/locations/location-types.md). |
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
<br > For examples, see [Location capacity](../../configuration/warehouse/locations.md). |
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
| Location Access | Name that can be assigned to locations and to pieces of warehouse equipment. In work management, the application offers directed work to operators based on whether their equipment access group matches the access group assigned to the location in which the directed work takes place. The application does not offer directed work to an operator if their equipment does not have an access group that matches that of the location in which the work needs to be performed. See [Location Access Groups](../../configuration/equipment/equipment/location-access-groups.md). |
| Escalation Type | Specifies the value by which the application escalates directed pick work.<br>-   • **Maximum Pallets**: The application escalates directed pick work from the selected location when the pallet quantity in the location exceeds the defined amount.
<br>-   • **Threshold Percent**: The application escalates directed pick work from the selected location when the pallet quantity percentage in the location exceeds the defined percent.
<br>-   • **Blank (no selection)**: Escalation of directed pick work is not determined by the location.
<br > You define the amount or percent in the **Escalation Threshold** field. |
| Escalation Threshold | Value by which the application escalates work in the location. When the amount of pallets in the location exceeds this threshold, the application increases the priority of existing pick work in the location. This value is only effective when an escalation type is selected in the **Escalation Type** field.<br > The escalation increment and time are determined by the work operation. See [Escalation based on a location](../../configuration/work/work/work-operations.md). |
| Travel Sequence | Numeric value, ranging from low to high, that represents the optimal travel sequence in which an operator is directed from one location to the next when performing directed work. |
| Count Sequence | Number that is used to sequence counting activities within the facility. When requesting counts for a range of locations, the application can use this value to determine the order in which to count the locations within the range. |
| Slotting Sequence | Number that is used by Slotting to determine the order in which this location is considered for slotting. A slotting sequence number is a common location attribute on which to base an attribute rule for a location set. Attribute rules direct Slotting in how to slot locations. An attribute rule that combines the slotting sequence number with an increasing sort order directs Slotting to use the slotting sequence number value for each location within a location set. Then, based on those values, Slotting arranges the locations so that the location with the lowest sequence number is slotted first. |
| Storage Sequence | Numeric value that represents the sequence in which the application considers the location for putaway in relation to other locations with storage sequences in the same storage zone. The application evaluates the sequence in order from lowest number to highest. If a storage sequence is not defined, the application uses the travel sequence.<br > **Note**: For outbound inventory (such as during picking), the application uses travel sequence to direct an operator from one location to the next. |
| Allocate to Empty Sequence | Value that identifies the sequence in which inventory in the location is allocated when compared to other locations in the same zone. When a pick zone is configured with the **Allocate to Empty** field set to Yes, the application allocates from one location in the zone until it is empty before allocating from another location.<br > The **Allocate to Empty Sequence** determines the order in which the application considers locations in a zone for allocation; the lower the sequence value, the higher the location's allocation priority. The sequence is set automatically by the application or manually by a user, depending on the pick zone configuration.<br > For example, assume ITEM01 is stored in LOC-A and LOC-B, and that LOC-A and LOC-B have allocate to empty sequences of 100 and 200, respectively. When the application allocates ITEM01, the inventory in LOC-A is allocated first until the location is empty, and then the application allocates ITEM01 from LOC-B.<br > The allocate to empty process is intended to be used in pick zones that have single-item locations, not pickface locations. See [Allocate to empty process](../../configuration/outbound/allocation/pick-zones.md).<br > **Note**: If two or more locations have identical allocate to empty sequence numbers, the application evaluates the allocate to empty dates and uses the location that had its allocate to empty sequence set first as the primary allocation source. |
| Allocate to Empty Date | Date on which inventory in the location was first allocated in a pick zone with the **Allocate to Empty** field set to Yes. |
| Replenishment | If Yes and if replenishment processing is enabled, the application evaluates this location for replenishment opportunities.<br > If No, the application does not evaluate the location for replenishment. |
| Storable | If Yes, the location is used to store inventory, and the application evaluates the location for the purpose of directing additional inventory to the location.<br > If No, the location can still be used to store inventory, but the application does not direct additional inventory to the location. |
| Pickable | If Yes, the application evaluates the inventory in the location during order allocation processing to determine if it can be used for order fulfillment.<br > If No, the application does not include the location in order allocation processing. |
| Summarize Existing Picks | If Yes, then when verifying inventory for existing picks before allocating new pick requests, the application logically combines existing eligible outstanding picks for the same item into one summarized pick for this location. Eligible picks are at the sub-load and detail level, have the same required attributes, and use simple allocation rules or no allocation rules. This allows for faster allocation of remaining inventory in the location and does not affect the picking process.<br > If No, then when verifying inventory for existing picks before allocating new pick requests, the application does not summarize existing picks for this location. Picks are allocated separately, which may result in longer processing times.<br > For example, assume there are 500 existing eligible picks for a location and 5 new requests for the same item. If this field is set to Yes, then to verify the available inventory in the location before allocating the new requests, the application reprocesses and reserves the total quantity of the existing picks as one summarized pick to be allocated at the same time. Therefore, the application processes 6 pick requests during allocation, one for the 500 existing picks and five more for the new requests. If this field is set to No, then the application reprocesses and reserves inventory for the 500 existing picks separately. Therefore, the application processes 505 pick requests during allocation. Regardless of how this field is configured, the picks are completed separately. |
| Count Back | If Yes, the location is enabled for count back. Count back is a pick verification task that applies when the operator is picking less than a full pallet from a location. If the item, location, UOM, and the operator (user) are enabled for count back, then the application requires the operator to capture the quantity of inventory that is left in addition to the quantity of inventory being picked. If the remaining quantity does not match the application-expected quantity, a count is generated. If the operator is authorized to do the count, the application prompts the operator to complete it; otherwise, a supervisor must resolve the discrepancy using an audit count.<br > If No, count back picking verification is not enabled or required for the location. |
| Permanently Assigned | If Yes, then the location is permanently assigned to an item even after assignments made using location preference rules are deleted or the location is emptied. If the preference rule assignment is deleted, then the location is reserved for future use with no specific item. Also, if set to Yes, and if the **Assignment** field is also set to Yes, replenishment processing does not use the location for future item assignments to the location.<br > If No, then the location is not permanently assigned to an item. If this field is set to No and a replenishment item configuration exists and the location is already assigned to an item, the assignment remains selected. However, if this field is set to No and a replenishment item configuration does not exist, the application clears the assignment when the location is emptied so that a different item than previously assigned can be stored in the location. |
| Assignment | If Yes, and the location is a storage location, the location is reserved for an item as defined by a location preference rule. The application does not direct operators to store any other item in the location. A location to which an item has been assigned cannot be deleted until the item location assignment is removed. If the location is not a storage location, selecting Yes indicates that the location is reserved for a specific purpose, such as to reserve it (if it were a staging lane) for a specific carrier.<br > If Slotting is installed and enabled, location assignments are created by the slotting plan. When the slotting plan is executed, some locations may not be slotted, resulting in the location assignments being removed and setting this field to No.<br > If No, then there is no item assigned to the location. |
| Assigned Item | Item that is assigned to the location. One or more items can be assigned to a location through storage location preference rules. When an item is assigned to a location, the application does not direct any other item to the location even if the location becomes empty. If multiple items have been assigned, then only the first item is displayed in the **Assigned Item** field. |
| Billing | If Yes, the location is evaluated for inventory that belongs to a client that is enabled for third-party billing. If this field is set to Yes, then on a scheduled basis, the application captures the details of the client's inventory in the location and generates a client billing transaction. Billing transactions are sent to the External Billing application. The **Billing** field is only available if an External Billing System is integrated with Warehouse Management. See [General Integration](../../configuration/integration/general-integration.md).<br > If No, the location is not included in billing storage transactions. |
| Report Printer | Name of the printer that will be used to print reports from this location. Only printers that have been configured to print reports are available for selection. You can assign a printer to a location so that when printing takes place at the location as a result of a workflow action, paperwork is directed to the assigned printer by default. |
| Label Printer | Name of the printer that will be used to print labels from this location. Only label printers that have been set up and configured to work with the application are available for selection. You can assign a printer to a location so that when printing takes place at the location as a result of a workflow action, paperwork is directed to the assigned printer by default. |

## Location Summary fields

 
| Field | Description |
| --- | --- |
| Max Capacity | Maximum capacity of the location based on the location capacity code. |
| ABC Classification | Code that determines how often the item is counted in a single count period. The frequency assigned to each ABC code is defined in inventory counting settings. |
| Stack Method | Name of the stack method used for stacking pallets in a location. This stack method is used when the pallet level UOM for the item footprint is stored in locations configured with a pallet stack restriction. |
| Velocity | Identifies the speed at which inventory stored in a location moves in and out of the warehouse. Velocity is used to optimize warehouse space and inventory handling by placing fast moving items in the best locations for quick picking, and slower moving items in the less accessible storage locations. The application accomplishes this by attempting to match the velocity of the item with the velocity of the location when finding a location for storing the item. |
| Building | Unique identifier for a building. A building is a warehouse entity consisting of one or more areas. Inventory and location information can be reported by building. |
| Aisle | Identifier for a passageway in the facility where operators and equipment move between racks or blocks of locations, typically to put away or pick inventory. You typically define aisles and then, in the process of defining storage locations, you can assign locations to the aisle in which they are located (a single location can be assigned to only one aisle). |
| Area | Identifier for an area. Areas are used for grouping and sorting locations in the warehouse. For example, an area named STAGING can be used to group ship staging locations; an area named CASEPICK can be used to group case pickface locations. |
| Work Zone | Name or number that identifies a work zone. A work zone is a logical division of warehouse space made on the basis of physical layout and access by different types of warehouse equipment. A work zone exists inside a work area. |
| Storage Zone | A storage zone represents a group of locations that have the same attributes (consolidation, item mixing, date control, and others) for storing inventory. |
| Pick Zone | Name of a pick zone. A pick zone represents a group of locations that share the same attributes for picking, such as the LPN level at which picks can be allocated, the cartonization group to which it belongs, and whether the location supports replacement picks and pre-inventory allocation. The search path searches pick zones when attempting to find inventory for allocation. |
| Movement Zone | Name of a movement zone. A movement zone represents a group of locations to and from which inventory can be moved. For example, storage locations to which inventory can be deposited and processing locations to which inventory is moved for packing are the types of locations that must be assigned to a movement zone for the application to select those locations for putaway or deposit.<br > Source, hop, and destination locations must be assigned to a movement zone so that a movement path can be defined to use each of those locations. |
| Count Zone | Unique identifier for the count zone to which this override applies. A count zone is a method of grouping locations for an inventory count. |
| Verification Code | Code that identifies a physical location in a warehouse, and that can be used to ensure that operators are traveling to and scanning a particular physical location. For facilities that use verification codes and location codes to identify locations, you can require that RF operators scan the verification code to confirm that they have arrived at a particular physical location. If scanning the verification code is required, and the operator scans the location code instead, then a message is displayed indicating that the verification code must be entered. The operator cannot continue until the verification code is scanned. If the verification code is not unique, the operator is also required to scan the location code. |
| Voice Check Digit | Number used to represent the location in facilities that use voice terminals. When the voice terminal operator is required to confirm a location, the operator can speak the voice check digit to identify the location to the application.<br > By default, the three check digit fields for a location are titled **First (Primary)**, **Middle**, and **Last**. The value in the first (primary) field is the number that operators must speak to confirm the location during voice operations. However, if the **Check Digit Rotation** field is set to Yes in the voice picking configuration, the voice device prompts the operator for one of the three check digit values to use for a picking assignment.<br > For example, when an operator begins a picking assignment, the voice device might speak "Middle," meaning the operator must use the middle check digit value to confirm each pick and deposit location for the assignment. The application randomly selects a check digit for each assignment.<br > You can change the description that is spoken to voice operators for each check digit field using the Voice Check Digit Schemes configuration. See [Configure voice picking](../../configuration/outbound/picking/voice-picking.md).<br > If check digit rotation is disabled, then the middle and last check digits are not needed.<br > **Note**: Check digit rotation is only used during picking operations. During other voice operations that require check digit confirmation, such as replenishments, putaway, or distribution, the application always prompts for the first (primary) check digit. |
| Current Capacity | Graphical values that show the current available and used capacity of the location, as well as any committed or pending quantities that will change the location's capacity level. |
| Mixing Restrictions | Values that define the mixing restrictions that must be satisfied for inventory to be stored in the location. For example, a mixing restriction can ensure that only items from the same item family can be stored in the location. |

## Location Items fields

 
| Field | Description |
| --- | --- |
| Item | Identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). Before the application can effectively store, track, and manipulate inventory, you must assign an item identifier and define the attributes of each item you want to track. When defining an item, you specify information such as how the item is packaged and handled, along with details that define how it should be received, stored, allocated, shipped, counted, and valued (cost information). |
| Quantity | Quantity of inventory residing in the location. |
| Footprint | Name that identifies a footprint, which describes the packaging dimensions and units of measure for the item with which it is associated. |
| Status | Quality status of an item. Defines the quality or disposition of the item. |
| Client | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. |

## Location Minimum Handling Unit fields

 
| Field | Description |
| --- | --- |
| Handling Unit Type | Unique identifier for a serialized handling unit type. A handling unit type represents a group of handling units that have the same characteristics, such as size and weight, as well as whether they are temporary or considered a container. The application tracks the on-hand quantity of handling units by type and, for serialized handling units, by handling unit identifier. |
| Manufacturer | Name of the company that produced the handling unit. |
| Model | Alphanumeric model number for the individual handling unit. Manufacturers use model numbers to differentiate similar products. |
| Client | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. |
| Location Minimum | Number that defines the minimum number of serialized handling units required in the location. |

## Location History fields

 
| Field | Description |
| --- | --- |
| User | User who last worked in the location. |
| Date/Time | Date and time at which the most recent activity in the location took place. |
| Operation | Work operation that identifies the type of directed work that was most recently performed in the location. |
| Activity | Value that identifies the work activity that was last performed in the location. |
| LPN | License plate number (LPN) that is associated with the most recent activity performed in the location. |
| Moved From | Location from which the LPN associated with the most recent activity was moved to the current location. |
| Moved To | Location to which the LPN associated with the most recent activity was moved. |
| Count Activity | Details of the most recent count activity that was performed in the location. |

## Inventory Attributes fields

 
| Field | Description |
| --- | --- |
| LPN | Unique identifier for inventory. Typically, an LPN refers to a pallet; however, it can refer to inventory received at less than pallet quantity. The LPN is the license plate by which the inventory is tracked in the facility. |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Lot | Identifier assigned to a quantity of an item during the manufacturing process for the purpose of tracking an attribute of that item, such as an expiration date. Lots differentiate distinct groups of inventory with the same item number. Items that may require a lot number include pharmaceuticals, fabrics, food, and other products with limited shelf life. Lots are user defined and are not necessarily unique since the same lot number can be applied to different items. However, lot and item combinations must be unique. |
| Origin Code | Identifier assigned to an item to identify the item's country of origin. It is typically used for export paperwork. Origin codes are user defined. |
| Revision Level | Identifier that is assigned to an item number to differentiate revisions of the same item number. |
| Supplier | Identifier for a supplier. A supplier can be an individual, organization, or another warehouse within your own organization from which you repeatedly receive inventory or handling units. |
| Supplier Lot | Identifier that is an attribute of an item or item and lot combination and is assigned by the item's supplier. A supplier lot number used to uniquely identify and track the inventory to which it is assigned. The supplier lot number is a different attribute than the lot number, which is a manufacturer or production lot number. |
| Consignment Change Point | Value that determines when ownership of consigned inventory is transferred from the supplier to the warehouse. The consignment values defined for the supplier item override those defined for the supplier, which override those defined for the warehouse.<br>-   • **Consignment Days**: Ownership is transferred after the specified number of consignment days (defined in the **Consignment Days** field) have passed.
<br>-   • **Putaway**: Ownership is transferred when the putaway work for the inventory is complete.
<br>-   • **Receipt**: Ownership is transferred when the inventory is received by the warehouse.
<br>-   • **Transport Equipment Close**: Ownership is transferred when the outbound transport equipment on which the consigned inventory is loaded is closed.
<br>-   • **Transport Equipment Dispatch**: Ownership is transferred when the outbound transport equipment on which the consigned inventory is loaded is dispatched. |
| Consignment Days | Number of days after receiving consigned inventory that the ownership is transferred from the supplier to the warehouse. If **Consignment Days** is selected as the change point, then this value represents the number of days after receipt during which the supplier has ownership of the consigned inventory. A schedule-based job is configured to run daily to determine when the specified number of consignment days has passed, at which point ownership is transferred to the warehouse.<br > **Note**: The application sets the consignment end date for inventory on an ASN shipment based on when the inventory was received and put away to storage. For non-ASN shipments, the application sets the consignment end date based on when the inventory was identified. For example, if the Consignment Days value is 30, then when an ASN shipment is received, the consignment change point is 30 days from when the inventory is put away to storage; when a non-ASN shipment is received, the change point is 30 days from when the inventory is identified. |
| Remaining Consignment Days | Number of days remaining to transfer the ownership from the supplier to the warehouse, calculated based on the current date and the consignment end date. If **Consignment Days** is selected as the **Consignment Change Point**, then this value represents the number of days after receipt during which the supplier retains ownership of the consigned inventory. Only available if the change point is Consignment Days. |
| Consignment End Date | The date at which the ownership of the inventory is transferred from the supplier to the warehouse. Only available if the change point is Consignment Days. |
| Handling Unit | Unique identifier for a handling unit that is tracked as an individual as well as collectively by handling unit type. You may want to track valuable handling units, such as CHEP pallets, as individuals. All transport equipment handling units are tracked as individuals. Handling units tracked as individuals can be further identified with a serial number. |
| Rotation | Unique identifier that the application generates and automatically assigns to bonded inventory during receipt of that inventory into a bonded warehouse. The rotation ID is tracked with the inventory as long as the inventory is in the warehouse. |
| Under Bond | If Yes, then the inventory is bonded. Bonded inventory is inventory for which customs duties and excise duties are required and have not yet been paid.<br > If No, then the inventory is not bonded. |

## Add Inventory fields

 
| Field | Description |
| --- | --- |
| LPN | Unique identifier for inventory. Typically, an LPN refers to a pallet; however, it can refer to inventory received at less than pallet quantity. The LPN is the license plate by which the inventory is tracked in the facility. |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Item Client | Name of the client who stores this item in the facility. This field is only displayed in a 3PL environment. |
| Description | Text that further describes the item. |
| Quantity | Quantity of inventory that you want to adjust. |
| Inventory Status | Value that defines the quality or disposition of the inventory. |
| Footprint | Name that identifies a footprint, which describes the packaging dimensions and units of measure for the item with which it is associated. |
| Lot | Identifier assigned to a quantity of inventory that is uniquely identified during the manufacturing process for the purpose of tracking an attribute of that inventory, such as its expiration date. Lots differentiate distinct groups of inventory that have the same item number. Lots are user defined and are not necessarily unique since the same lot can be applied to different items. However, lot and item combinations must be unique. |
| Handling Unit Type | Handling unit type assigned to the LPN. A handling unit type is a category that classifies a group of handling units (for example, pallets or totes) that share the same characteristics such as size and weight, as well as whether they are serialized, temporary, or considered a container. |
| Wrap | Indicates the LPN-level packaging attribute for inventory.<br > LPN packaging attributes are user-defined fields that are used to indicate requirements such as pallet wrapping, use of a slip sheet, and the application of labels on all four sides of a pallet of inventory. |
| Double Wrap | Indicates the LPN-level packaging attribute for inventory.<br > LPN packaging attributes are user-defined fields that are used to indicate requirements such as pallet wrapping, use of a slip sheet, and the application of labels on all four sides of a pallet of inventory. |
| Slip Sheet | Indicates the LPN-level packaging attribute for inventory.<br > LPN packaging attributes are user-defined fields that are used to indicate requirements such as pallet wrapping, use of a slip sheet, and the application of labels on all four sides of a pallet of inventory. |
| Label 4 Sides | Indicates the LPN-level packaging attribute for inventory.<br > LPN packaging attributes are user-defined fields that are used to indicate requirements such as pallet wrapping, use of a slip sheet, and the application of labels on all four sides of a pallet of inventory. |
| Reason Code | Code as defined in the web client that identifies the reason why you are adding inventory to a location. |
| Adjustment Reference One | Identifier for the host account to which the inventory adjustment was performed. This information was included when the inventory adjustment transaction was sent to the host. |
| Adjustment Reference Two | Identifier for the host account to which the inventory adjustment was performed. This information was included when the inventory adjustment transaction was sent to the host. |
| Keep location in Error after Adjustment | If Yes, then the location remains in an error status after the adjustment has been made. Select Yes if you want to prevent inventory activity from taking place in the location after the adjustment has been made.<br > If No, then after the adjustment is complete, the application removes the error status from the location.<br > **Note**: If inventory adjustment thresholds are defined and an adjustment exceeds a threshold, the location is set to Locked status until the adjustment is approved; this field has no effect on location status when an adjustment requires approval. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
