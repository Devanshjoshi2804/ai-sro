---
title: "Replenishment Settings"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/replenishment_settings.htm"
source: "/content/replenishment_settings.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inventory"
  - "Replenishments"
  - "Replenishment Settings"
sections:
  - "Shortages"
  - "Error controls"
  - "Replenishment paths"
  - "Example: Replenishment path"
  - "Replenishment items"
  - "Date processing for replenishments"
  - "Cascading demand replenishments"
  - "Partial replenishment utilization"
  - "Configure replenishment settings"
  - "Replenishment Settings fields"
  - "Zones To Keep Filled fields"
  - "Items That Generate Demand Replenishment fields"
  - "Emergency Replenishment Settings fields"
  - "Replenishment Preference Rules fields"
  - "Error Controls fields"
  - "Items To Replenish When Low fields"
  - "Top Off Replenishments fields"
  - "Items that use Top-off Replenishments fields"
images: []
source_sha1: 16127612b26a08e1234f37dbf1c62e5bb5764ec5
---
# Replenishment Settings

Replenishment settings are used to enable and configure triggered and top-off replenishments. Specifically, you can define the following processes:

-   Whether automatic triggered replenishments are enabled
-   How top-off replenishments are generated
-   Logging of replenishment processing
-   How to search for date-tracked inventory with which to replenish pick locations

The Replenishment Settings page also provides a display that shows the schedule for top-off replenishments. The schedule is maintained in the Console, under Jobs.

## Shortages

A shortage occurs when the application attempts to allocate an order or work order line and there is not enough available inventory in a pickable location to fulfill the order. You can enable the application to automatically generate a replenishment request to move the required inventory from storage to a pickable location so that the order can be fulfilled. This type of replenishment is called an emergency replenishment.

You can configure the timing and technical aspects of emergency replenishment processing:

-   Whether replenishments should be allocated to a hold status until the picks are allocated (based on the available replenishment inventory), so that both can be released together
-   The timers that control how often and how many times the application attempts to fulfill replenishment picks before it stops searching for inventory
-   Whether log files are generated that record emergency replenishment processing

## Error controls

The error controls are used to configure the number of times and how often the application attempts to fulfill a replenishment request. These settings are defined by your Blue Yonder project team and do not typically require modification.

**IMPORTANT**: Setting the Retry Delay to less than 5 minutes for a status other than Busy can have a negative impact on application performance.

The application resets the status of a replenishment based on the number of retry counts and the time in between each retry. For example, if the Retry Delay is set to 15 minutes, then if allocation fails to find inventory after one try, the replenishment status changes back to Issued. In 15 minutes, the application searches for inventory again and if not found, the status changes from Allocation Failed back to Issued and waits for another 15 minutes before searching again.

In this example, if Retry Count is set to 100, and if inventory is not found after 100 tries, the application uses the cancelled command. If the command is set to Cancel Replenishment and Shipment, the application cancels the replenishment (it longer searches for inventory) and then cancels the shipment.

The Cancelled Command settings ensure replenishment requests are not cancelled automatically by the application when you want the application to keep searching for inventory to fill short orders, or until you manually cancel each replenishment request. For example, if inventory cannot be found, and the retry count for allocation failed is 3, the application cancels the replenishment and does not attempt to look for inventory after 3 tries.

Retry Delay times for all status are typically set to an equivalent of the Timer Length. Typically, this is a minimum of 5 minutes to avoid putting an excessive load on the application to re-check failed requests. The exception may be the Busy status which could be a shorter interval.

You can ignore the entries for Status - Default unless you have defined custom statuses.

## Replenishment paths

A replenishment path specifies the pick movement zone to which replenishment inventory is deposited. If replenishment processing for emergency or demand replenishments is enabled, and if there is not enough available inventory in a pick zone to fulfill an order allocation, the application generates a replenishment. The replenishment process attempts to allocate inventory to satisfy the replenishment based on a search path configuration, and if it is successful, it finds a location to deposit the replenishment inventory based on the replenishment path configuration. You use the Zones to Keep Filled setting to configure a replenishment path.

**IMPORTANT**: A replenishment path is required for every pick and destination movement zone combination for which you want to perform emergency and demand replenishments, and for every LPN level used to replenish the pick movement zone.

A replenishment path defines the following attributes:

-   Path name and the criteria, if any, that determines which inventory is directed to the specified pick movement zone. For example, you can limit a path to a specific item, item family, or (for a 3PL environment) client.
-   Whether the path applies each pick movement zones or case pick movement zones
-   LPN level (such as LPN or sub-LPN) at which the replenishment is allocated to fill the pick zone
-   Pick movement zone to keep filled with inventory
-   Final staging destination (movement zone) for the order
-   For a replenishment path for each order picks:
    -   A hop movement zone that can be defined. The hop is can be used to move the replenishment inventory to a temporarily location if there is not enough room in the each pick locations, or it can be used to support cascading demand replenishments. See [Cascading demand replenishments](#Cascading_demand_replenishments).
    -   LPN level that can be moved to the hop movement zone.

## Example: Replenishment path

A replenishment path defines the pick movement zone that should be replenished based on the destination of the order picks. The path type defined for the replenishment path specifies whether the path is used to replenish a zone for case picks or for each (piece) picks; it also specifies the LPN level allocated to replenish the pick zone.

You must create a replenishment path for each pick movement zone and destination zone combination, and for each LPN level that is allocated to replenish the pick zone.

For example, assume that you perform each picks from the EACHPICK pick zone, and the picks have a final destination of the HANDPACK movement zone. If you want EACHPICK1 to be replenished with either cases or pallets, then you must define two replenishment paths (one for allocating replenishments by sub-LPN and another for allocating replenishments by LPN) as follows:

-   **Path1**
    -   **Path Type**: Replenishment Path for Each Order Picks
    -   **Allocation Level to Fill Pick Zone**: Sub-LPN
    -   **Zone to Keep Filled**: EACHPICK1
    -   **Final Staging Destination**: HANDPACK
-   **Path2**
    -   **Path Type**: Replenishment Path for Each Order Picks
    -   **Allocation Level to Fill Pick Zone**: LPN
    -   **Zone to Keep Filled**: EACHPICK1
    -   **Final Staging Destination**: HANDPACK

If Path1 and Path2 are arranged in sequential order, then if a shortage occurs and a replenishment is issued, the application attempts to replenish the EACHPICK1 pick zone at the case level (sub-LPN), then at the pallet level (LPN).

## Replenishment items

A replenishment item is a configuration (see [Items to Replenish When Low fields](#Items_to_Replenish_When_Low_fields)) that specifies the amount of inventory that you want to maintain for a particular item and the pick zone in which the inventory should be maintained.

Replenishment items are required for triggered and manual replenishments, and for top-off replenishments that are based on item configurations.

The replenishment item configuration defines whether an item is assigned to specific location or, if not assigned to a specific location, it specifies the replenishment values for a pick zone.

If the item is assigned to a location, then when there is demand for the item, the application replenishes the assigned locations first.

-   If demand exceeds the capacity of the assigned locations for an item, the application attempts to find an unassigned location in the pick zone that is empty. If it finds an empty location with no pending inventory, and the item has not exceeded its maximum amount of unassigned locations, the application replenishes the empty location. The item remains in the replenished unassigned locations until its inventory is completely picked and thus empties the location.
-   If the replenishment item configuration is for a pick zone, then when there is demand for the item, the application moves the replenishments into empty locations in the pick zone. This method requires less item and location maintenance.

## Date processing for replenishments

The date processing attributes govern the selection of inventory to satisfy replenishments, and whether the application should ignore the storage date window defined for the item so that replenishments can be deposited in the locations for which they were intended.

When you configure date processing for replenishments, you specify the following attributes:

-   Inventory rotation method. This method is used by default if no other rotation method is defined for the requested inventory, such for the order line or item for which the replenishment is required. See [Inventory rotation methods](../../outbound/allocation/inventory-rotation-allocation.md).
-   When the application allocates inventory for a replenishment using an inventory rotation method, it uses an order of precedence to determine the sequence in which to look for a rotation method to apply. The application looks for an inventory rotation method in the following sequence:
    1.  Order line or work order line
    2.  Customer item
    3.  Item
    4.  Customer (ship to)
    5.  Customer type
    6.  Client
    7.  Default replenishment configuration
        
        **Note**: The default replenishment configuration for inventory rotation method is only used when there is no rotation method defined at the previous sequence levels.
        
-   Date window that determines the window of time (such as 2 days) in which inventory with different dates is considered the same for replenishment allocation. For example, if you specified FIFO-ORDER-BY for the inventory rotation method, and 2 days for the date window, then when the application finds the oldest inventory, it considers other inventory within the same location up to 2 days newer to be the same date and will include it in the allocation if needed. Using a date window allows the application to allocate inventory within the window without continuing to search and allocate out of other locations.
    
    Since date windows are defined at multiple levels, you can configure the order of precedence in which the application looks for a date window to apply. The replenishment configuration is only used if the application is processing a replenishment and no date window is defined for the entities with a lower sequence number (higher priority). See [Configure inventory selection settings](../../outbound/allocation/allocation-inventory-selection.md).
    
-   Whether replenishment processing ignores the age of date-tracked inventory existing in a location when attempting to replenish the location. If you select to ignore the age of date-tracked inventory in the location, then the storage date window defined for an item does not prevent the deposit of replenishment inventory to a location with existing inventory for the item. Otherwise, the storage date window is respected and prevents the replenishment from succeeding if inventory cannot be found that fits within the storage date window of existing inventory in the location.
    
    **Note**: The storage date window for an item defines the maximum acceptable age difference allowed in a location between the oldest and newest inventory for an item number based on its date window type (expiration date, manufactured date, or received date).
    

## Cascading demand replenishments

The cascading replenishment process is used to support situations in which the inventory needed to fulfill a demand replenishment only exists at an LPN level that cannot be used to replenish the pick location. This replenishment process creates two separate demand replenishments: one to move an LPN (pallet) of inventory to a sub-LPN (case) location; and one to move the case quantity of inventory to the detail LPN (each) pick location.

**Note**: Demand replenishments are created during pre-inventory allocation (PIA) processing to allow the application to release picks based on the quantity of inventory pending to the pick location.

For example, assume that pre-inventory allocation requires a quantity of inventory to replenish an each pickface, and the pickface requires case-level replenishments. If the replenishment path for the each-pick zone is configured with a hop (intermediate movement zone) that accepts pallets, then the application can direct a pallet of inventory to the hop location and from there direct a case quantity to the pickface.

To ensure that the LPN replenishment pick is completed first, the sub-LPN replenishment pick is created in a hold status until the LPN replenishment is complete, at which time the hold status is either automatically or manually released. It is automatically released if the sub-LPN UOM is configured for immediate release for shipping allocation; otherwise, it must be released manually. See [Units of Measure](../units-of-measure.md).

To enable cascading demand replenishments to take place:

1.  Configure the pick zones from which the replenishments will be sourced to be enabled for PIA. See [Pick Zones](../../outbound/allocation/pick-zones.md).
2.  Configure replenishment settings. See [Replenishment Settings](#).
3.  For the each-pick movement zones that are filled by sub-LPNs, configure the replenishment path with a hop to a sub-LPN movement zone. This is the zone to which the LPN level replenishment pick is deposited. See [Replenishment paths](#Replenishment_paths).
4.  Configure the UOMs that should be released immediately when allocated for shipping. See [Units of Measure](../units-of-measure.md).

## Partial replenishment utilization

The application supports partial replenishment utilization for demand and emergency replenishments. This is when the remaining replenishment quantity is be used for another order line even if the quantity only partially fulfills the order line.

For example, assume there are two order lines each requiring a quantity of 30 cases for the same item, and the pick location for the item has a capacity of 50 cases but is empty. When the order lines are allocated, the application generates a replenishment of 50 to fill the pick location, with a quantity of 30 allocated for the first order line, and a remaining quantity of 20. If this field is set to Yes, then the remaining quantity (20) is applied to the second order line, and then the application attempts a new replenishment to fill the location and satisfy the unfulfilled quantity (10). If the new replenishment fails, then the unfulfilled quantity on the order line is shorted.

**Note**: If the remaining replenishment quantity fully satisfies another order line, then the application applies the quantity to the order line regardless of the **Use Remaining Quantity for Partial Fulfillment** field.

Partial fulfillment of demand replenishments to pick locations that have a capacity equal to a full pallet replenishment quantity is functional regardless of this field. Using the previous example, assume that one full pallet is 50 cases, equal to the location's capacity. Even if this field is set to No, when a demand replenishment is required, then the first replenishment of one pallet is allocated to the first order line (30 cases) and the second order line (20 cases), and then a second replenishment for another pallet is attempted to fulfill the remaining quantity (10). However, if the location has a capacity of 100 cases (2 pallets), when this field is set to No, then a quantity of 30 from the first demand replenishment (50 cases) is allocated for the first order and the remaining quantity (20) is stored in the location. A second replenishment of one pallet is required to satisfy the second order line quantity of 30 cases. Alternatively, if this field is set to Yes, then the remaining quantity of 20 cases from the first demand replenishment is allocated to the second order line, and the second replenishment is needed only to satisfy the remaining 10 cases.

## Configure replenishment settings

1.  Select **Configuration > Inventory > Replenishments > Replenishment Settings**.
2.  Enter information in the [Replenishment Settings fields](#Replenishment_Settings_fields).
3.  Define the replenishment paths for demand replenishments:
    1.  Under **DEMAND REPLENISHMENTS**, click **Zones to Keep Filled**.
    2.  Perform one of the following tasks:
        -   To add a replenishment path, click **Add**.
        -   To modify a replenishment path, in the grid, click the path.
        -   To copy a replenishment path, in the grid, select the check box next to the sequence, and then click **Copy**.
    3.  Enter information in the [Zones To Keep Filled fields](#Zones_to_Keep_Filled_fields).
    4.  Click **Save**.
4.  To define the items that allow demand replenishments to be created:
    1.  Under **DEMAND REPLENISHMENTS**, click **Items That Generate Demand Replenishments**.
    2.  Perform one of the following tasks:
        -   To add an item, click **Add**.
        -   To modify an item, in the grid, click the item.
        -   To copy an item, in the grid, select the check box next to the item, and then click **Copy**.
    3.  Enter information in the [Items That Generate Demand Replenishment fields](#Items_That_Generate_Demand_Replenishment_fields).
    4.  Click **Save**.
5.  Define the replenishment paths for emergency replenishments:
    1.  Under **EMERGENCY REPLENISHMENTS**, click **Zones to Keep Filled**.
    2.  Perform one of the following tasks:
        -   To add a replenishment path, click **Add**.
        -   To modify a replenishment path, in the grid, click the path.
        -   To copy a replenishment path, in the grid, select the check box next to the sequence, and then click **Copy**.
    3.  Enter information in the [Zones To Keep Filled fields](#Zones_to_Keep_Filled_fields).
    4.  Click **Save**.
6.  To specify the preferred locations to use when determining pick destinations for emergency replenishments:
    1.  Under **EMERGENCY REPLENISHMENTS**, click **Replenishment Preference Rules**.
    2.  Perform one of the following tasks:
        -   To add a replenishment preference rule, click **Add**.
        -   To modify a replenishment preference rule, in the grid, click the sequence.
        -   To copy a replenishment preference rule, in the grid, select the check box next to the sequence, and then click **Copy**.
    3.  Enter information in the [Replenishment Preference Rules fields](#Replenishment_Preference_Rules_fields).
    4.  Click **Save**.
7.  Configure the settings that control emergency replenishment processing:
    1.  Under **EMERGENCY REPLENISHMENTS**, click **Emergency Replenishment Settings**.
    2.  Enter information in the [Emergency Replenishment Settings fields](#Emergency_Replenishment_Settings_fields).
    3.  Set how often the application attempts to fill an outstanding replenishment:
        1.  Under **TIMER AND CONTROLS**, click **Error Controls**.
        2.  In the grid, enter information in the [Error Controls fields](#Error_Controls_fields).
        3.  Click **Apply**.
    4.  Click **Save**.
8.  Configure the items and levels that will trigger a replenishment:
    1.  Under **TRIGGER REPLENS WHEN LOW**, click **Items That Trigger Replenishments**.
    2.  Perform one of the following tasks:
        -   To add an item, click **Add**.
        -   To modify an item, in the grid, click the item.
        -   To copy an item, in the grid, select the check box next to the item, and then click **Copy**.
    3.  Enter information in the [Items To Replenish When Low fields](#Items_to_Replenish_When_Low_fields).
    4.  Click **Save**.
9.  Define the settings used to create top-off replenishments:
    1.  Under **TOP OFF REPLENISHMENTS**, click **Top Off Replenishments**.
    2.  Enter information in the [Top Off Replenishments fields](#Top_Off_Replenishments_fields).
    3.  Select the zones to be topped off to the maximum quantity allowed in the location:
        1.  Click **Available Movement Zones to Top Off**.
        2.  In the **Available** column, select the check box next to the movement zones that apply.
        3.  Click **Apply**.
    4.  Select the items to be replenished according to the schedule:
        1.  Click **Items that use Top-off Replenishments**.
        2.  Perform one of the following tasks:
            -   To add an item, click **Add**.
            -   To modify an item, in the grid, click the item.
            -   To copy an item, in the grid, select the check box next to the item, and then click **Copy**.
        3.  Enter information in the [Items That Use Top-off Replenishments fields](#Items_that_use_Top-off_Replenishments_fields).
        4.  Click **Save**.
10.  Click **Save**.

## Replenishment Settings fields

 
| Field | Description |
| --- | --- |
| Maximum Active Replenishments | Maximum number of replenishments that can be released, which prevents the creation of a new top-off or triggered replenishment. The application does not allow the creation of a top-off or triggered replenishment that would cause the number of released replenishments to exceed the maximum. However, the application continues to allow the creation of other types of replenishments. Use this value to limit the amount of non-critical replenishment work pending or in progress.<br > For example, assume the value of this field is 10, and that there are 4 existing top-off replenishments, 4 emergency replenishments, and 2 demand replenishments. If a location quantity falls below the threshold and a triggered replenishment is requested, the application does not immediately create the replenishment because there are already 10 replenishments released in the warehouse. However, if an emergency replenishment is requested instead, then the application successfully creates the replenishment because this value only affects whether additional top-off or triggered replenishments are created. |
| Use Remaining Quantity for Partial Fulfillment | If Yes, then the remaining replenishment quantity can be used for another order line even if the quantity only partially fulfills the order line. The application attempts a new replenishment to satisfy the unfulfilled quantity. See [Partial replenishment utilization](#Partial_replenishment_utilization).<br > If No, then the remaining replenishment quantity is not used to satisfy an order line if it is less than the order line quantity, and the application attempts a new replenishment for the entire order line quantity. If the new replenishment fails, then the entire order line quantity is shorted.<br>
**Note**: This field only applies to demand and emergency replenishments for outbound order picks.

 |
| Demand Replenishment Retry Count | Number of times the application attempts to create a demand replenishment before cancelling it and creating an emergency replenishment. A pre-inventory allocation (PIA) demand replenishment can fail, for example, if there is no suitable inventory or no destination location available to allocate. For example, if you specify 5 attempts, then if inventory cannot be located in the first allocation attempt, the application attempts to allocate the replenishment 4 additional times. |
| Retry Multiple PIA Locations | If Yes, then when a pre-inventory allocation (PIA) demand replenishment fails because the initial destination location cannot be used, the application continues to search for a different destination location (source of the PIA pick) for the replenishment inventory.<br > For example, assume the application attempts to generate a PIA demand replenishment but cannot use the first pickface location due to mixing restrictions. With this field set to Yes, instead of failing the attempt and creating a short allocation, the application continues to search all eligible locations in the replenishment path until an suitable destination location for the replenishment (or source location for the PIA pick) is found.<br > **Note**: Depending on the number of eligible destination locations available, enabling this configuration may affect application performance speeds.<br > If No, then the application does not attempt to allocate a different destination location if the initial destination for a demand replenishment fails. Select No to ensure that only the initial destination location is used and to avoid application performance issues. |
| Cross Dock Residual Inventory | If Yes, then residual inventory from a split replenishment can be used to fulfill cross dock opportunities. For example, assume that an operator is replenishing a location (capacity of 50 eaches) in a zone configured for splitting replenishment residuals. If the operator picks 50 eaches to satisfy a replenishment for 30 eaches, and there is currently 10 eaches in the replenishment location, then the operator deposits 40 eaches to fill the location to capacity. When the deposit is complete, the application attempts to fulfill pending cross docks with the residual inventory (10 eaches).<br > If No, then residual inventory from the split replenishment cannot be used to fulfill cross docks, and the application runs putaway to find a location. If allowed, the operator can override the application-selected location.<br > **Note**: This field only applies to replenishments destined to a movement zone that is configured to allow splitting replenishment residuals. See [Splitting replenishment residuals](splitting-replenishment-residuals.md). |
| Overfill Location | If Yes, then when an operator completes a replenishment deposit to a zone configured for splitting replenishment residuals, the operator can override the deposit quantity with a quantity that exceeds the location capacity. For example, assume that a pickface location with a capacity of 1 pallet (50 eaches) currently contains 10 eaches, and that a pallet has been allocated and picked to replenish the location. At the replenishment destination location, the application prompts the operator to deposit 40 eaches to fill the location to capacity. With this field set to Yes, the operator can override the deposit quantity and deposit the entire pallet to overfill the location by 10 eaches (10 + 50 = 60). See [Splitting replenishment residuals](splitting-replenishment-residuals.md).<br > **Note**: When this field is set to Yes, an operator can overfill a location by any quantity; there is no limit. Operational circumstances should be considered, such as if the replenishment is for a fast moving item, or if the location is in a wide aisle.<br > If No, then an operator cannot override the replenishment deposit quantity to overfill the location. |
| Enable Triggered Replenishments | If Yes, the application generates a replenishment automatically when the quantity or percentage of inventory in the location falls below a specified threshold. This process is called a triggered replenishment or a quantity-triggered replenishment and typically takes place in response to a pick, inventory move, or adjustment that causes the available quantity in the location to fall below a threshold value. The threshold values are defined for replenishment items.<br > If No, the application does not generate replenishments automatically based on the inventory level in a location falling below a specified threshold. |
| Logging Triggered | If Yes, then log files are created and added to the LES/log directory during a triggered replenishment. A log file is a record of the process that the application performed for a triggered replenishment. These files are used when troubleshooting triggered replenishments. Select Yes if you need to determine the cause of an issue associated with triggered replenishments.<br > If No, the application does not generate log files during a triggered replenishment. Select No if you do not require a record of the process that the application performed for a triggered replenishment. |
| Inventory Rotation Method | Value that represents the order in which the allocation process selects available inventory for allocation. Select an inventory rotation method if you want the application to search for inventory based on date processing or location.<br>-   • **FEFO-ORDER-BY and FEFO-ORDER-BY-ABSOLUTE**: First-expiration, first-out. The first inventory to expire will be selected first.
<br>-   • **FIFO-ORDER-BY and FIFO-ORDER-BY-ABSOLUTE**: First-in, first-out. The oldest inventory will be selected first.
<br>-   • **LEFO-ORDER-BY and LEFO-ORDER-BY-ABSOLUTE**: Last-expiration, first-out. The last inventory to expire will be selected first.
<br>-   • **LIFO-ORDER-BY and LIFO-ORDER-BY-ABSOLUTE**: Last-in, first-out. The newest inventory will be selected first.
<br > When using inventory rotation methods that are not absolute, the application searches for inventory by allocation search path in sequence until it finds a pick zone that contains the inventory, and then allocates inventory that is closest to the preferred processing date. Therefore, the application stops searching at the first pick zone in which matching inventory is found.<br > When using absolute inventory rotation methods, the application searches either all of the allocation search paths for inventory that is closest to the preferred processing date or, if absolute groups are defined, it searches each absolute group in sequence until it finds matching inventory and then allocates inventory that is closest to the preferred processing date from the pick zones within the absolute group. Therefore, the absolute method allows for more a comprehensive search to find the inventory. |
| Outbound Date Window | Amount of time in relation to the inventory’s received date or expiration date during which inventory is considered the same age for allocation. You can define a window of time in minutes, hours, or days. The allocation process for replenishments only uses the outbound date window when one of the FEFO/FIFO/LEFO/LIFO or absolute FEFO/FIFO/LEFO/LIFO inventory rotation methods is required.<br > If an outbound date window is defined, the application can allocate inventory within the date window from a single location, even if inventory closer to the processing date exists in another location. Also, if a replenishment requires a full pallet, the application can allocate a full pallet of inventory with expiration or receiving dates that fall within the outbound date window, even if partial pallets with dates closer to the preferred processing date are available. |
| Disable Storage Date Window Check | If Yes, replenishment processing ignores the age of date-tracked inventory existing in a location when attempting to replenish the location. If this field is set to Yes, the application does not consider the storage date window defined for date-tracked items when allocating replenishments for a location. Select Yes if you want to ensure that replenishments can be deposited in locations even when the replenishment inventory may not fit within the storage date window of the existing inventory in the location.<br > If No, then for date-tracked inventory, replenishments are not allocated unless replenishment inventory is found that fits within the storage date window of inventory existing in the locations that require replenishment. |

## Zones To Keep Filled fields

 
| Field | Description |
| --- | --- |
| Path Name | Name of the replenishment path. A replenishment path specifies the pick zone to which replenishment inventory is deposited. |
| Path Type | Determines the type of order pick for which the replenishment path is used.<br>-   • **Replenishment Path for Case Order Picks**: Used when order allocation results in case picks for which replenishments are needed.
<br>-   • **Replenishment Path for Each Order Picks**: Used when order allocation results in each picks for which replenishments are needed. |
| Criteria | Attribute of the inventory that is required to be fulfilled by the replenishment:<br>-   • **Client**: Unique identifier for a client that houses product within a multi-client (third-party logistics) warehouse. This is the client associated with the inventory required for the replenishment.
<br>-   • **Item Family**: Name used to group similar items, typically with the same material handling characteristics. This is the item family of the inventory required for the replenishment.
<br>-   • **Item Number**: Item identifier for the inventory required for the replenishment. This attribute is not typically used because of the level to which it restricts the path.
<br>-   • **None**: No inventory criteria applies. |
| Hop to Zone | Movement zone that can provide a temporary deposit location (such as a pickup and deposit location) for replenishment inventory that does not fit in the pick zone that needs to be replenished.<br > A hop is used, for example, when a full pallet replenishment does not fit in any of the small pick locations. For example, some facilities define locations for inventory used to feed the locations in an each pick zone.<br > A hop can also be used to support cascading demand replenishments. This process directs an LPN-level replenishment to the hop movement zone, so that from there a sub-LPN level replenishment can be moved to the each pick zone. See [Cascading demand replenishments](#Cascading_demand_replenishments).<br > A hop movement zone can be selected if the replenishment path is for each order picks. |
| Hop Allocation Level | Packaging level of the replenishment inventory that can be allocated to the hop movement zone.<br>-   • **LPN**: Inventory at the pallet level.
<br>-   • **Sub-LPN**: Inventory at the case level.
<br>-   • **Detail LPN**: Inventory at the each (piece) level. |
| Allocation Level to Fill Pick Zone | Packaging level of the replenishment picks that you want to be allocated to fill the pick zone.<br>-   • **LPN**: Inventory at the pallet level.
<br>-   • **Sub-LPN**: Inventory at the case level.
<br>-   • **Detail LPN**: Inventory at the each (piece) level. |
| Zone to Keep Filled | Name of the pick zone that contains the locations to be replenished by this replenishment path. This is the pick zone to which the replenishment inventory is deposited, unless a hop is specified. |
| Final Staging Destination | Name of the movement zone that contains the final staging destination location for the pick that generated the replenishment. This movement zone typically contains processing or staging locations to which orders are directed before being loaded onto transport equipment. |

## Items That Generate Demand Replenishment fields

 
| Field | Description |
| --- | --- |
| Item | Item to keep filled in a pick location or any location in a pick zone. |
| Inventory Status | Inventory status that is required for inventory used to replenish the item. |
| Move Zone to Fill | Zone in which you want the item to be replenished. The application attempts to find the item in the zone and then replenish that location. If the item is not in a location in the zone, then the application attempts to move the replenishment to an empty location in the zone. |
| Maximum Locations For Item | Maximum number of locations in the move zone that you want to keep filled with the item. The replenishment process uses the values for **Minimum/Maximum Item Levels** to keep this number of locations filled. If you enter 1, then the application replenishes one location in the zone. If you enter 3, then the application replenishes three locations in the zone. This value is typically used for fast moving items that tend to empty fast during picking. Defining more than one location helps eliminate short orders.<br > This field is only available if there is no value entered in the **Location to Fill** field.<br > **Note**: If you want to configure both a maximum number of locations and specific locations for an item, then you can add additional Item to Replenish entries for the same item in the zone. Only one entry for a unique item in the zone can have a **Maximum Locations For Item** value, and the locations to fill specified in additional entries for the same item count toward the maximum number of locations. For example, if you add an Item to Replenish and enter 3 in the **Maximum Locations For Item** field, then you can create an additional configuration for the same item with a specified **Location to Fill**. When the item needs to be replenished, the application replenishes the **Location to Fill** first, and then replenishes a maximum of two additional locations in the zone. |
| Minimum/Maximum Item Levels | Defines the minimum and maximum quantity that you want to maintain in the pick zone or location.<br>-   • **Percentage**: Indicates that the value in the **Maximum** and **Minimum** fields is a percentage of the location capacity.
<br>-   • **Units**: Indicates that the value in the **Maximum** and **Minimum** fields is a unit quantity.
<br>-   • **Maximum**:
    -   • If **Percentage** is selected, this is the maximum percentage of a location capacity to fill with the item when a replenishment is generated. If set to 100% maximum, the application attempts to fill the location to its maximum location capacity. This may fill the location with more inventory than the order pick needs, but is an efficient process for filling the location in one move. If you allow the location to be overfilled, you can set this value to be greater than 100%.
    <br>-   • If **Units** is selected, this is the maximum number of units/eaches of the item to replenish to the pick zone or specified location. If you want to allow more units in the location capacity, you can set this value to be greater than the location capacity. Typically units is not used unless the item is assigned to a location.
    <br>
<br>-   • **Minimum**:
    -   • If **Percentage** is selected, this is the minimum percentage of a location capacity to keep filled with the item. If the amount in a location falls below this value, a triggered replenishment is generated if configured to do so. For example, if set to 20%, then when inventory level is below 20% capacity, the location should be filled.
    <br>-   • If **Units** is selected, this is the minimum number of units/eaches of the item to replenish to the pick zone or specified location. If the amount in a location or pick zone falls below this value, a triggered replenishment is generated if configured to do so.
    <br> |
| Balancing Replenishment Across Multiple Locations | Amount of inventory that can be replenished to the locations in the event that demand exceeds the capacity of the location. When demand has allocated all capacity in the assigned and unassigned locations for the item, the replenishment process attempts to balance the distribution of the replenishment inventory across all of the locations (up to the number of locations defined by the **Maximum Locations For Item** field) and direct inventory to each location according to the percentage or unit value. This value is used to balance the distribution of inventory across the maximum locations defined for the item when a large replenishment is generated, without overfilling.<br>-   • **Percentage**: Percentage of the location's capacity that can be filled. For example, if you set this value to 20% and the location's capacity is 200, then the application would replenish the location in increments of 40 units when balancing the remaining replenishment quantity across multiple locations. If you enter "0", the location is not filled over its capacity. Percentage is typically used because it does not depend on the item configuration (size of an each UOM) of the item that is in the location.
<br>-   • **Units**: Number of units that can be replenished to the location in the event that demand exceeds the capacity of the location. For example, if you enter 50, then the application replenishes the location in quantities of 40 when balancing the remaining replenishment quantity across multiple locations. Typically units is not used unless every location in the pick zone is assigned to items that have a similar size each UOM, where the quantity that you specify would be similar for each item.
<br > For example, if there are two pickfaces that have been filled to capacity, and there are still 500 units left to allocate, the application would look to balance the remaining allocation across the available locations, up to the maximum locations for the item. If the value is configured as 100 units for location 1 and 200 units for location 2, then the application would replenish the locations in this order: 100 units at Location 1, 200 units at Location 2, 100 units at Location 1, and 100 units at Location 2. |
| Release Percent | Maximum percentage capacity of the location the application will use to determine if the replenishment work should be released. For example, if you want to allow more quantity into the location then there is capacity for, you can set this value to be greater than 100%. This is done with the assumption that the extra inventory will be immediately picked for an order. The release percent is only used for work operations configured with the release command of "process work status change by capacity".<br > For example, if a location can hold 100 units and the **Release Percent** is set to 110%, then when the location's inventory falls below 10 units, the replenishment is released and can be filled to 110%. The **Release Percent** multiplied by the location capacity equals the adjusted maximum capacity (110% X 100 = 110). You can subtract the replenishment quantity from the adjusted maximum capacity to determine the allowable level the inventory must reach before the replenishment is released (110 - 100 = 10). |
| Location To Fill | Location within the selected move zone that you want to keep filled with the replenishment item. If you specify a location to fill, then the value for **Maximum Locations For Item** is set to 0 and is unavailable, and the application fills only the specified location.<br > Select a location if you want to assign the item to a specific location.<br>
**Notes**:

<br>

-   •
    
    If you enter a location in this field, then the application creates a location preference rule for the item.
    
    <br>
<br>-   •
    
    If you want to specify more than one location to keep filled with the item in this zone, then you can add an additional Item to Replenish configuration for the same item with a different location.
    
    <br>
<br>

 |

## Emergency Replenishment Settings fields

 
| Field | Description |
| --- | --- |
| Enable Replenishment Manager | If Enabled, the application generates a replenishment automatically during allocation when there is insufficient pickable inventory to satisfy an order or work order.<br > If Disabled, the application does not generate replenishments automatically when allocation fails to find pickable inventory to satisfy an order or work order. |
| Timer Length | Amount of time between replenishment attempts. When a shortage occurs, the application attempts to fulfill the shortage by generating a replenishment. This timer defines the amount of time that must elapse between the attempts that the application makes to find inventory to fulfill the needed replenishment. |
| Time to Wait | Amount of time the application waits before an emergency replenishment expires and is removed so that the application no longer attempts to replenish the shortage. |
| Minimum Replenishment Time | Minimum amount of time that must elapse between when the replenishment is allocated and when it is released by the application to be performed. |
| Logging Active Replenishments | Name of the file created in the LES/log directory that is used to log active emergency replenishments. A log file is a record of the process that the application performs for an emergency replenishment. These files are used when troubleshooting to determine the cause of an issue associated with the replenishment. |
| Commit During Processing | If Yes, the application commits changes to the database immediately during an emergency replenishment. It is recommended that you select Yes to improve performance if you expect to perform replenishments while the application is processing other updates, such as those that take place during normal warehouse operations. In facilities that routinely run a high number of replenishments, selecting Yes could help eliminate problems with multiple locations being locked while processing of a large number of replenishments.<br > If No, the application commits changes to the database after replenishment processing has taken place. |
| Logging Cancelled Replenishments | Name of the file created in the LES/log directory that is used to log cancelled emergency replenishments. A log file is a record of the process that the application performed for cancelling a replenishment. These files are used when troubleshooting to determine the cause of an issue associated with the cancellation. |
| Skip Help Replenishments | If Yes, when emergency replenishments are generated the replenishment work remains in a Issued status until the picks are released. The application skips processing replenishments that were issued for picks on hold to prevent replenishments from being allocated until the picks are released. This process is used to ensure that inventory being picked for a replenishment will fit into the location being replenished.<br > If No, replenishments are processed and inventory is moved to the proper pick locations, but picks for the order are allocated to a hold status until the replenishments are complete. |

## Replenishment Preference Rules fields

 
| Field | Description |
| --- | --- |
| Storage Options | Value used to define the criteria that the application uses to evaluate whether inventory should be directed to the location or range of locations. You can use this field to create a location preference rule that is specific to an item, item family, item class, handling unit type, client, or supplier. |
| Sequence Number | Number that defines the sequence in which the application processes the list of location preference rules to find an appropriate location or range of locations for the inventory to be put away. The application evaluates the rules in sequential order (starting with 1), and stops processing when it finds a matching location. |
| LPN Attribute | Identifier that describes the inventory's physical composition. The application uses this value to direct inventory with a matching value to locations specified by the location preference rule.<br > For example, you can direct inventory that meets the criteria for Heavy to floor-level pick locations. The values for physical composition are defined by the LPN composition attributes. See [Configure storage settings](../../inbound/storage/storage-settings.md). |
| Begin Location | First location in the range of locations to which the application will attempt to direct inventory that matches the criteria on the location preference rule. |
| End Location | Last location in the range of locations to which the application will attempt to direct inventory that matches the criteria on the location preference rule. To limit the search path to a single location, enter the same location specified for **Begin Location**. |
| Assigned Location | Indicates that the defined item number, item family, supplier, or client is assigned to the specified location or range of locations in the location preference rule. Assigning one of these storage options to a location or range of locations reserves the location exclusively for inventory that matches that criteria. |
| Item | Identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). Before the application can effectively store, track, and manipulate inventory, you must assign an item identifier and define the attributes of each item you want to track. When defining an item, you specify information such as how the item is packaged and handled, along with details that define how it should be received, stored, allocated, shipped, counted, and valued (cost information). Only displayed when you select Item in the **Storage Options** field. |
| Item Family | Identifier used to group similar items together. Typically, all of the items within a family have the same material handling characteristics. Only displayed when you select Item Family in the **Storage Options** field. |
| Client | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another and enables the application effectively manage activity for multiple clients in one warehouse. Only displayed in a 3PL environment when you select Supplier or Client in the **Storage Options** field. |
| Supplier | Unique code that identifies a supplier. A supplier is a provider who supplies goods or services. Only displayed when you select Supplier in the **Storage Options** field. |
| Handling Unit | Identifier for a handling unit type. A handling unit type is a group of handling units (such as pallets, totes, or equipment) that share the same characteristics such as size and weight as well as whether they are serialized, temporary, or considered a container. Only displayed when you select Handling Unit Type in the **Storage Options** field. |

## Error Controls fields

 
| Field | Description |
| --- | --- |
| Status | Status that indicates the reason the application failed to fulfill a replenishment request.<br>-   • **Default**: Failure is due to a reason other than the replenishment request expired, the allocation failed, the hop allocation failed, the location allocation failed, or the production line was busy (location status is in Inventory Error status).
<br>-   • **Expired**: The replenishment request expired.
<br>-   • **Allocation Failed**: The application failed to allocate inventory for the replenishment.
<br>-   • **Hop Allocation Failed**: The application failed to find a storage location in a hop or feed movement zone for a replenishment request.
<br>-   • **Location Allocation Failed**: The application failed to find a storage location to deposit inventory for a replenishment request.
<br>-   • **Busy**: A production line is busy (location status is in Inventory Error status). |
| Retry Count | Number of times the application attempts to fulfill a replenishment request. For example, if you set the **Retry Count** value to 3, the application tries to fulfill a replenishment request 3 times before executing the command specified in the **Cancelled Command** field. |
| Retry Delay | Amount of time in minutes that the application should wait after a replenishment request fails before changing the replenishment request status to the status specified in the **Retry Status** field. |
| Retry Status | Status applied to the replenishment request after the application fails to fulfill the request and the time specified in the **Retry Delay** field has expired. |
| Cancelled Command | Valid server command that is executed when the application fails to fulfill a replenishment request after a defined number of attempts. |

## Items To Replenish When Low fields

 
| Field | Description |
| --- | --- |
| Item | Item to keep filled in a pick location or any location in a pick zone. |
| Inventory Status | Inventory status that is required for inventory used to replenish the item. |
| Move Zone to Fill | Zone in which you want the item to be replenished. The application attempts to find the item in the zone and then replenish that location. If the item is not in a location in the zone, then the application attempts to move the replenishment to an empty location in the zone. |
| Maximum Locations For Item | Maximum number of locations in the move zone that you want to keep filled with the item. The replenishment process uses the values for **Minimum/Maximum Item Levels** to keep this number of locations filled. If you enter 1, then the application replenishes one location in the zone. If you enter 3, then the application replenishes three locations in the zone. This value is typically used for fast moving items that tend to empty fast during picking. Defining more than one location helps eliminate short orders.<br > This field is only available if there is no value entered in the **Location to Fill** field.<br > **Note**: If you want to configure both a maximum number of locations and specific locations for an item, then you can add additional Item to Replenish entries for the same item in the zone. Only one entry for a unique item in the zone can have a **Maximum Locations For Item** value, and the locations to fill specified in additional entries for the same item count toward the maximum number of locations. For example, if you add an Item to Replenish and enter 3 in the **Maximum Locations For Item** field, then you can create an additional configuration for the same item with a specified **Location to Fill**. When the item needs to be replenished, the application replenishes the **Location to Fill** first, and then replenishes a maximum of two additional locations in the zone. |
| Minimum/Maximum Item Levels | Defines the minimum and maximum quantity that you want to maintain in the pick zone or location.<br>-   • **Percentage**: Indicates that the value in the **Maximum** and **Minimum** fields is a percentage of the location capacity.
<br>-   • **Units**: Indicates that the value in the **Maximum** and **Minimum** fields is a unit quantity.
<br>-   • **Maximum**:
    -   • If **Percentage** is selected, this is the maximum percentage of a location capacity to fill with the item when a replenishment is generated. If set to 100% maximum, the application attempts to fill the location to its maximum location capacity. This may fill the location with more inventory than the order pick needs, but is an efficient process for filling the location in one move. If you allow the location to be overfilled, you can set this value to be greater than 100%.
    <br>-   • If **Units** is selected, this is the maximum number of units/eaches of the item to replenish to the pick zone or specified location. If you want to allow more units in the location capacity, you can set this value to be greater than the location capacity. Typically units is not used unless the item is assigned to a location.
    <br>
<br>-   • **Minimum**:
    -   • If **Percentage** is selected, this is the minimum percentage of a location capacity to keep filled with the item. If the amount in a location falls below this value, a triggered replenishment is generated if configured to do so. For example, if set to 20%, then when inventory level is below 20% capacity, the location should be filled.
    <br>-   • If **Units** is selected, this is the minimum number of units/eaches of the item to replenish to the pick zone or specified location. If the amount in a location or pick zone falls below this value, a triggered replenishment is generated if configured to do so.
    <br> |
| Balancing Replenishment Across Multiple Locations | Amount of inventory that can be replenished to the locations in the event that demand exceeds the capacity of the location. When demand has allocated all capacity in the assigned and unassigned locations for the item, the replenishment process attempts to balance the distribution of the replenishment inventory across all of the locations (up to the number of locations defined by the **Maximum Locations For Item** field) and direct inventory to each location according to the percentage or unit value. This value is used to balance the distribution of inventory across the maximum locations defined for the item when a large replenishment is generated, without overfilling.<br>-   • **Percentage**: Percentage of the location's capacity that can be filled. For example, if you set this value to 20% and the location's capacity is 200, then the application would replenish the location in increments of 40 units when balancing the remaining replenishment quantity across multiple locations. If you enter "0", the location is not filled over its capacity. Percentage is typically used because it does not depend on the item configuration (size of an each UOM) of the item that is in the location.
<br>-   • **Units**: Number of units that can be replenished to the location in the event that demand exceeds the capacity of the location. For example, if you enter 50, then the application replenishes the location in quantities of 40 when balancing the remaining replenishment quantity across multiple locations. Typically units is not used unless every location in the pick zone is assigned to items that have a similar size each UOM, where the quantity that you specify would be similar for each item.
<br > For example, if there are two pickfaces that have been filled to capacity, and there are still 500 units left to allocate, the application would look to balance the remaining allocation across the available locations, up to the maximum locations for the item. If the value is configured as 100 units for location 1 and 200 units for location 2, then the application would replenish the locations in this order: 100 units at Location 1, 200 units at Location 2, 100 units at Location 1, and 100 units at Location 2. |
| Release Percent | Maximum percentage capacity of the location the application will use to determine if the replenishment work should be released. For example, if you want to allow more quantity into the location then there is capacity for, you can set this value to be greater than 100%. This is done with the assumption that the extra inventory will be immediately picked for an order. The release percent is only used for work operations configured with the release command of "process work status change by capacity".<br > For example, if a location can hold 100 units and the **Release Percent** is set to 110%, then when the location's inventory falls below 10 units, the replenishment is released and can be filled to 110%. The **Release Percent** multiplied by the location capacity equals the adjusted maximum capacity (110% X 100 = 110). You can subtract the replenishment quantity from the adjusted maximum capacity to determine the allowable level the inventory must reach before the replenishment is released (110 - 100 = 10). |
| Location To Fill | Location within the selected move zone that you want to keep filled with the replenishment item. If you specify a location to fill, then the value for **Maximum Locations For Item** is set to 0 and is unavailable, and the application fills only the specified location.<br > Select a location if you want to assign the item to a specific location.<br>
**Notes**:

<br>

-   •
    
    If you enter a location in this field, then the application creates a location preference rule for the item.
    
    <br>
<br>-   •
    
    If you want to specify more than one location to keep filled with the item in this zone, then you can add an additional Item to Replenish configuration for the same item with a different location.
    
    <br>
<br>

 |

## Top Off Replenishments fields

 
| Field | Description |
| --- | --- |
| Enable Top-Off Replenishments | If Yes, the application generates replenishments automatically on a regularly scheduled basis. During the replenishment process, the application evaluates inventory levels according to the selected top-off method. If the process finds that quantities are below the top-off levels, it issues a replenishment request. The schedule is defined in the Console, under Jobs.<br > If No, the application does not generate replenishments automatically on a regularly scheduled basis. |
| Top-Off Method | Method that is used to find locations for top-off replenishments.<br>-   • **Check the item configuration and use defined rules**: Uses the configuration defined for the replenishment item, which specifies the item, inventory status, zones or locations to keep filled, and the minimum and maximum amount of the item to maintain in the locations.
<br>-   • **Check current level and fill location to maximum capacity**: Uses the configuration defined for the storage location to determine the inventory level to which the location should be replenished. The level defined at the location for Top-Off Threshold Percentage is a percentage of the location's maximum capacity. |
| Floor Percentage Prompt | If Yes, then when a user generates a manual top-off replenishment, the application prompts the user to enter a floor percentage to determine which locations are topped-off. The floor percentage limits the replenishment to locations that are filled to less than the defined percentage of location capacity. If a location's fill percentage is equal to or greater than the defined floor percentage, then the location is excluded from the replenishment.<br > For example, assume Location1 has a quantity of 65 and Location2 has a quantity of 70, the location capacity code for both locations is Each, and the capacity for both locations is 100. If a user generates a manual replenishment for the locations and enters 70% for the floor percentage, then only Location1 is replenished. A replenishment is not generated for Location2, because it is filled to 70% of its capacity, which is equal to the entered floor percentage of 70%.<br > If No, then the application does not prompt for a floor percentage when a user manually generates a replenishment. |
| Logging Top-Off | If Yes, then log files are created and added to the LES/log directory during a top-off replenishment. A log file is a record of the process that the application performed for a top-off replenishment. These files are used when troubleshooting top-off replenishments. Select Yes if you need to determine the cause of an issue associated with top-off replenishments.<br > If No, the application does not generate log files during a top-off replenishment. Select No if you do not require a record of the process that the application performed for a top-off replenishment. |

## Items that use Top-off Replenishments fields

 
| Field | Description |
| --- | --- |
| Item | Item to keep filled in a pick location or any location in a pick zone. |
| Inventory Status | Inventory status that is required for inventory used to replenish the item. |
| Move Zone to Fill | Zone in which you want the item to be replenished. The application attempts to find the item in the zone and then replenish that location. If the item is not in a location in the zone, then the application attempts to move the replenishment to an empty location in the zone. |
| Maximum Locations For Item | Maximum number of locations in the move zone that you want to keep filled with the item. The replenishment process uses the values for **Minimum/Maximum Item Levels** to keep this number of locations filled. If you enter 1, then the application replenishes one location in the zone. If you enter 3, then the application replenishes three locations in the zone. This value is typically used for fast moving items that tend to empty fast during picking. Defining more than one location helps eliminate short orders.<br > This field is only available if there is no value entered in the **Location to Fill** field.<br > **Note**: If you want to configure both a maximum number of locations and specific locations for an item, then you can add additional Item to Replenish entries for the same item in the zone. Only one entry for a unique item in the zone can have a **Maximum Locations For Item** value, and the locations to fill specified in additional entries for the same item count toward the maximum number of locations. For example, if you add an Item to Replenish and enter 3 in the **Maximum Locations For Item** field, then you can create an additional configuration for the same item with a specified **Location to Fill**. When the item needs to be replenished, the application replenishes the **Location to Fill** first, and then replenishes a maximum of two additional locations in the zone. |
| Minimum/Maximum Item Levels | Defines the minimum and maximum quantity that you want to maintain in the pick zone or location.<br>-   • **Percentage**: Indicates that the value in the **Maximum** and **Minimum** fields is a percentage of the location capacity.
<br>-   • **Units**: Indicates that the value in the **Maximum** and **Minimum** fields is a unit quantity.
<br>-   • **Maximum**:
    -   • If **Percentage** is selected, this is the maximum percentage of a location capacity to fill with the item when a replenishment is generated. If set to 100% maximum, the application attempts to fill the location to its maximum location capacity. This may fill the location with more inventory than the order pick needs, but is an efficient process for filling the location in one move. If you allow the location to be overfilled, you can set this value to be greater than 100%.
    <br>-   • If **Units** is selected, this is the maximum number of units/eaches of the item to replenish to the pick zone or specified location. If you want to allow more units in the location capacity, you can set this value to be greater than the location capacity. Typically units is not used unless the item is assigned to a location.
    <br>
<br>-   • **Minimum**:
    -   • If **Percentage** is selected, this is the minimum percentage of a location capacity to keep filled with the item. If the amount in a location falls below this value, a triggered replenishment is generated if configured to do so. For example, if set to 20%, then when inventory level is below 20% capacity, the location should be filled.
    <br>-   • If **Units** is selected, this is the minimum number of units/eaches of the item to replenish to the pick zone or specified location. If the amount in a location or pick zone falls below this value, a triggered replenishment is generated if configured to do so.
    <br> |
| Balancing Replenishment Across Multiple Locations | Amount of inventory that can be replenished to the locations in the event that demand exceeds the capacity of the location. When demand has allocated all capacity in the assigned and unassigned locations for the item, the replenishment process attempts to balance the distribution of the replenishment inventory across all of the locations (up to the number of locations defined by the **Maximum Locations For Item** field) and direct inventory to each location according to the percentage or unit value. This value is used to balance the distribution of inventory across the maximum locations defined for the item when a large replenishment is generated, without overfilling.<br>-   • **Percentage**: Percentage of the location's capacity that can be filled. For example, if you set this value to 20% and the location's capacity is 200, then the application would replenish the location in increments of 40 units when balancing the remaining replenishment quantity across multiple locations. If you enter "0", the location is not filled over its capacity. Percentage is typically used because it does not depend on the item configuration (size of an each UOM) of the item that is in the location.
<br>-   • **Units**: Number of units that can be replenished to the location in the event that demand exceeds the capacity of the location. For example, if you enter 50, then the application replenishes the location in quantities of 40 when balancing the remaining replenishment quantity across multiple locations. Typically units is not used unless every location in the pick zone is assigned to items that have a similar size each UOM, where the quantity that you specify would be similar for each item.
<br > For example, if there are two pickfaces that have been filled to capacity, and there are still 500 units left to allocate, the application would look to balance the remaining allocation across the available locations, up to the maximum locations for the item. If the value is configured as 100 units for location 1 and 200 units for location 2, then the application would replenish the locations in this order: 100 units at Location 1, 200 units at Location 2, 100 units at Location 1, and 100 units at Location 2. |
| Release Percent | Maximum percentage capacity of the location the application will use to determine if the replenishment work should be released. For example, if you want to allow more quantity into the location then there is capacity for, you can set this value to be greater than 100%. This is done with the assumption that the extra inventory will be immediately picked for an order. The release percent is only used for work operations configured with the release command of "process work status change by capacity".<br > For example, if a location can hold 100 units and the **Release Percent** is set to 110%, then when the location's inventory falls below 10 units, the replenishment is released and can be filled to 110%. The **Release Percent** multiplied by the location capacity equals the adjusted maximum capacity (110% X 100 = 110). You can subtract the replenishment quantity from the adjusted maximum capacity to determine the allowable level the inventory must reach before the replenishment is released (110 - 100 = 10). |
| Location To Fill | Location within the selected move zone that you want to keep filled with the replenishment item. If you specify a location to fill, then the value for **Maximum Locations For Item** is set to 0 and is unavailable, and the application fills only the specified location.<br > Select a location if you want to assign the item to a specific location.<br>
**Notes**:

<br>

-   •
    
    If you enter a location in this field, then the application creates a location preference rule for the item.
    
    <br>
<br>-   •
    
    If you want to specify more than one location to keep filled with the item in this zone, then you can add an additional Item to Replenish configuration for the same item with a different location.
    
    <br>
<br>

 |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
