---
title: "Outbound Staging"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/outbound_staging.htm"
source: "/content/outbound_staging.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Outbound"
  - "Shipping "
  - "Outbound Staging"
sections:
  - "Outbound pallet building"
  - "Outbound pallet building setup"
  - "Outbound work sequencing"
  - "Setup"
  - "Receiving, shipping, and processing resource codes"
  - "Resource types"
  - "Configure outbound staging"
  - "Outbound Staging fields"
images: []
source_sha1: dd78f49f24bd01099f1086975da24dad9703357c
---
# Outbound Staging

Staging is the process of organizing picked inventory near the shipping dock doors and preparing it for shipment.

When you configure staging, you define the following attributes:

-   Whether to allocate a staging lane from only the lanes assigned to the expected dock door or dock set, and if applicable, the priority the application excludes when allocating a lane.
-   Automatic staging that changes a shipment's status to Staged when the last pick for the shipment is deposited to a staging location.
-   Ship staging lane assignments that the application performs based on the selection sequence that you define and how staging locations are reserved for specific inventory.
-   Pallet positions, which identify (usually by number) the positions in a location where a pallet can be built and to which inventory can be deposited. Generally, pallet positions correspond to places that you have marked on the floor of your warehouse where you build pallets. A pallet building location can have multiple positions and each position supports building one pallet at a time.
-   Pallet building consolidation rules. Pallet building is a process in which cases or repack cartons are consolidated after picking to create a new pallet. For example, if a consolidation rule is based on the shipment, then when an operator attempts to build a pallet, the application verifies that each case or repack carton on the pallet is part of the same shipment. Alternatively, if the rule was based on a staging lane, then inventory from different shipments can be built on the same pallet as long as the destination staging location is the same, such as for small carrier (parcel) shipments.
    
    After you configure the pallet build consolidation rules, you can assign a rule to a customer, customer type, and transport mode. The consolidation rule assigned to a transport mode overrides the customer configuration, which overrides the customer type.
    
-   Whether operators are allowed to override an application-directed staging location with a different staging location and if so, whether released picks that have the resource code are also redirected to the new staging location.
-   Locations other than staging locations that are used to temporarily store unpicked inventory. This is inventory that was picked for a shipment but then removed from it for some reason, such as damage, overpick, or it is no longer needed for the order.
-   Staging lanes designated for small shipments. Enables you to define the maximum number of pallets that are allowed at a shipment staging lane for it to be classified as a small shipment staging lane. If you enter a value, then the pick release process will only use small staging lanes when they can contain at least 50% of the pallets required by the shipment. This prevents small lanes from being completely consumed by one large shipment.
-   Checkpoints at which the application verifies that there are no holds or inventory statuses applied to inventory that are configured to disallow shipping.
-   Shipment adjustment attributes related to label printing, putaway, and LPN identifiers.
-   Staging lane transfer configurations that define the action and operation used by the application to create directed work for assigning or changing the ship staging lanes. See [Configure outbound staging](#Configure_outbound_staging).

## Outbound pallet building

Outbound pallet building is a process in which cases or repack cartons are consolidated after picking to create a new pallet. Pallets can be built in any pickup and deposit (P&D) or hop location using an RF device or a workstation.

Pallet build consolidation rules determine what inventory can be consolidated together on the same pallet. For example, if a consolidation rule is based on shipment, then when an operator attempts to build a pallet, the application verifies that each case on the pallet is part of the same shipment. Alternatively, if the rule is based on staging lane, then cases from different shipments can be built on the same pallet as long as the destination staging location is the same, as it can be for small carrier shipments.

After you configure the pallet build consolidation rules, you can assign a rule to a customer, customer type, and transport mode. The consolidation rule assigned to a transport mode overrides the customer configuration, which overrides the customer type configuration. For example, assume that two orders for two different customers are destined for the same staging location. If both customers are configured with a pallet build rule that consolidates pallets by order, but the transport mode being used by both customers is configured to consolidate by staging lane, then the orders can be consolidated on the same pallet as defined by the transport mode rule.

Typically, the small package transport mode would be configured to consolidate by staging lane, while the full truckload and less than truckload transport modes would not be configured with a rule so that the application uses the customer or customer type configuration instead.

You can use pallet building to perform the following tasks:

-   Build multiple consolidated pallets at the same time
-   View the number of cases remaining during pallet building

## Outbound pallet building setup

Outbound pallet building can be done at the final staging location or at a processing location before the final staging location. Either way, outbound shipments must have movement paths configured correctly. Perform the following tasks to configure the application for pallet building:

1.  Define a pallet building location type. For this location type, you can set the **Automatically Clear Processing** field to Yes, so that processing locations are automatically released whenever a pallet build is complete. This prevents you from having to manually clear the processing locations. See [Location Types](../../warehouse/locations/location-types.md).
2.  Define the area and locations in which pallet building can take place. Locations should be based on the pallet building location type. See [Staging Locations](../../warehouse/locations/staging-locations.md) or [Processing Locations](../../warehouse/locations/processing-locations.md).
3.  Define a movement zone for the pallet build locations. The attachment strategy of the movement zone should be set to never attach. See [Movement Zones](../../inventory/movement/movement-zones.md).
4.  Define movement paths for the movement zone. See [Movement Paths](../../inventory/movement/movement-paths.md).
    -   If the pallet building location is not the final staging location, you may need to define a movement path from the picking locations to pallet build staging locations, then to pallet building locations, and then to final ship staging locations.
    -   If the pallet building location is the final staging location, you may need to define a movement path from picking locations to pallet build staging locations, and then to final ship staging locations.
5.  Define the pallet positions within each location. Pallet positions are typically numbered; for example, 01, 02, 03, and so on. See [Outbound Staging](#Outbound_Staging).
6.  Configure the pallet build consolidation rules that are used by the application to restrict the inventory that can be consolidated to the same pallet. See [Outbound Staging](#Outbound_Staging).
7.  Assign a consolidation rule to customers, customer types, and transport modes for which you want to be able to perform pallet building. See [Existing Customers](../../partners/customers/existing-customers.md), [Customer Types](../../partners/customers/customer-types.md), and [Transport Modes](../../partners/carriers/transport-modes.md).

## Outbound work sequencing

Outbound work sequencing manages the sequence in which picked inventory for an outbound load is delivered to ship staging by locking and unlocking directed pick and transfer work in a controlled manner. For example, if products in different item families must be separated on transport equipment, you can use work sequencing to ensure that all inventory for one item family is delivered to ship staging for loading before the next item family in sequence can be delivered to staging, and so on.

**Notes**:

-   The application does not support work sequencing for bulk picking, distributions, or undirected picking.
-   It is recommended that you do not use outbound work sequencing if you also use an external pallet control system.
-   Cross docking work (and indirect cross docking transfer work) and fluid loading is supported by outbound work sequencing as long as directed work is created for the moves.

The application considers locking work for any of the operations you select when you [configure outbound staging](#Configure_outbound_staging). If a load has at least one stop assigned to it, the application then locks and unlocks pieces of work based on the work release type on the load and whether the movement path contains a pre-stage zone, or if the source location is in a pre-stage zone. A pre-stage movement zone is used in the outbound work sequencing process to provide buffer hop locations in the movement path to which picked inventory can be deposited. See [Add or modify a movement zone](../../inventory/movement/movement-zones.md).

Work is unlocked by a scheduled background job (OUTBOUND-WORK-SEQUENCING), if enabled. The schedule is maintained in the Console, under Jobs.

**Note**: Any operations that were locked by other functionality in the application will not be unlocked by the work release sequence functionality.

You can define a work release type for a load, customer and warehouse. If a work sequencing release type is not defined for a load when a stop with shipments is added to the load, the application uses the value defined for the customer. If no release type is defined for the load and customer, the application uses the warehouse value.

For a work release type, when the last LPN of the first work release sequence is deposited to the staging location (or transport equipment, if fluid loading), the work for the second release sequence is unlocked, and so on. You can control the sequence of work using one of the following work release types:

-   **Item Family**: Work is unlocked based on the work release sequence (from lowest number to highest) defined for each item family required for the load. Since this value ignores stop sequence, if it is selected for a load that is being fluid loaded (skips staging), then the **Ignore Stop Sequence** field on the load should be set to Yes to ensure loading is not dictated by stop sequence.
-   **Stop**: Work is unlocked based on the stop's loading sequence (defined on the load) in order from lowest to highest. For example, stop 1, 2, 3, and so on.
-   **Stop and Item Family**: Work is unlocked based on the work release sequence defined for each item family within a stop, and then based on the stop's loading sequence (defined on the load) in order from lowest to highest. The work for the first item family on the first stop is unlocked, and after it has been staged, the work for the next item family on the first stop is unlocked, and so on. After the first stop is staged, the first item family for the next sequential stop is unlocked, and so on.
-   **Manual**: Work is unlocked based on the manual work release sequence assigned to each piece of pick work, with the lowest sequence released first. At any time, the application will start or resume unlocking work only when there is a manual work release sequence assigned to each piece of work for a load with the manual release type. If pick work with this release type is cancelled, a configuration determines whether the manual sequence is retained for the reallocated pick.
-   **None**: Work is excluded from outbound work sequencing and is not locked in the work queue.

When the application locks work for a load based on outbound work sequencing, removing a shipment from the load or re-planning a shipment into a different load may lead to unexpected sequencing behavior. If you remove a shipment from a load, any pending work is unchanged. However, any locked work for the shipment may need to be manually unlocked and is not included in any sequencing until the shipment is re-planned into a load that is being sequenced. Additionally, if you add the shipment to a load for which work has already been unlocked, it is possible that inventory is delivered to ship staging out of sequence.

### Setup

You must complete the following tasks to use outbound work sequencing:

1.  Configure outbound work sequencing for the warehouse. See [Configure outbound staging](#Configure_outbound_staging).
    -   Enable outbound work sequencing.
    -   If applicable, select a default work release type for the warehouse.
    -   Select the operations that can be locked by outbound work sequencing.
    -   Indicate whether a cancelled pick retains its assigned release sequence when the manual work release type is used.
2.  If applicable, define a work sequencing release type for customers. See [Add or modify a customer](../../partners/customers/existing-customers.md).
3.  For use with a work release type that includes item family, define the work release sequence for each item family. See [Add or modify an item family](../../inventory/items/item-families.md).
4.  If applicable, define movement zones as a pre-stage zones. See [Add or modify a movement zone](../../inventory/movement/movement-zones.md).

## Receiving, shipping, and processing resource codes

Receiving resource codes for a location are set when a location is assigned for inbound inventory; this occurs during putaway after inventory has been identified. For example, if the resource variable is set to be the LPN against which the inventory is received, then after the inventory is received and directed to a location, that location's receiving resource code is set to the LPN. Only inventory received for that specific LPN is allowed to be placed in the location until the location is emptied.

Shipping resource codes for a location are set during inventory allocation when the ship staging location is assigned for the outbound inventory. For example, if the resource variable is set to be the carrier, then when a shipment is assigned to a location, the location is set to the carrier associated with the outbound inventory. Thereafter, only inventory scheduled to be shipped by that specific carrier is allowed to be placed in the location.

Processing resource codes for a location are set when the location is assigned for deposit. The deposit process involves placing picked or cross-docked inventory for multiple orders into separate locations. For example, if the resource variable is set to be the item family, then the resource code is set to the item family to which the inventory belongs.

You can configure location types to automatically clear the resource codes for shipping and processing locations. However, for warehouses that want processing or ship staging locations reserved even after the location is emptied (such as for the same customer or for inventory in a specific item family) the location type can be configured to not clear the location, meaning the resource code is retained.

## Resource types

A resource type is a method by which a deposit location in a staging or processing movement zone is reserved for specific inventory. The application uses the resource type to obtain a resource code for a location, which identifies the inventory allowed in the location. The following resource types are available for use in location reservation processing:

-   **Command**: The resource code is generated based on the results of running the command specified as the resource variable. The command must be defined in the application and must accept a work reference; the published value from the command is used as the resource code. For example, if inventory is moving through the zone, the application runs the specified command and uses the result as the resource code.
-   **Derived**: The resource code is derived from a column name (field) on the pick work, shipment, shipment header, outbound order, and outbound order header tables. The resource code can be assigned to a location when inventory is allocated or when it is being moved from one zone in the movement path to the next, depending on the configuration for the outbound pick method. After a location is assigned a code, only inventory that has the same value (such as a specific carrier) is deposited to the location until the the location is emptied of all inventory and is released either manually or automatically. If you select a derived resource type, you select one or more resource variables from a list that includes column names (fields) from the aforementioned tables. For example, if you select Derived as the resource type and you select Carrier as the resource variable, the application will set the location's resource code to the carrier that is responsible for shipping the inventory.
-   **Unrestricted**: The resource code specifies that any inventory can be mixed in the location until the location capacity is reached. The application does not match the resource code value to an inventory attribute value in order to assign inventory to the location; all inventory can be routed to a location with an unrestricted resource code.
-   **Generate**: The resource code value is an application-generated value based on the control number that you select as the resource variable.
-   **Location Assigned**: The resource code specifies the location within a zone to which all inventory is directed regardless of the location's capacity. For example, if inventory is moving through a zone where staging takes place, the resource variable you specify is the location within the zone where you want the inventory placed. For received items, the assigned resource variable for the zone is the location where inbound inventory is placed. For picked inventory, the resource code is set upon allocation, and the location is also assigned to the pick move for inventory moving through the zone for distribution or shipment. The outbound inventory moving through the zone would be directed to the specified location.

## Configure outbound staging

1.  Select **Configuration > Outbound > Shipping > Outbound Staging**.
2.  Enter information in the [Outbound Staging fields](#Outbound_Staging_fields).
3.  To select the movement zones to enable for automatic staging:
    
    **Note**: Automatic staging is a process that changes the status of a shipment to Staged when the last pick for the shipment is deposited to a staging lane.
    
    1.  Under **SHIPMENT STATUS**, Click **Automatic Staging**.
    2.  In the **Available** column, select the check box next to the zones that apply.
    3.  Click **Apply**.
4.  To define the sort order in which the staging locations are searched during pick release:
    
    **Note**: During the allocation process, the application assigns a staging location to outbound order picks. You use the **Location Sort** configuration to specify the order in which staging locations are evaluated for selection.
    
    1.  Under **SHIP STAGING LANE ASSIGNMENT**, click **Location Sort**.
    2.  To select criteria from displayed entities:
        1.  If the advanced query is displayed, click **Simple**.
        2.  If the available entities are not displayed, click **Show Available**.
        3.  In the **Available** grid, select the entities that you want to use as criteria.
        4.  Click **Add selected**. The entities are added to the **Selected** grid.
        5.  To remove criteria, in the **Selected** grid, select the criteria to remove, and click **Remove selected**.
        6.  To reorder the criteria, in the **Selected** grid, click a row, and then click the up or down arrow to move the selected criteria. The application applies the criteria in sequential order according to how it is displayed in the grid.
    3.  To enter criteria using database entities, click **Advanced**, and then enter the column and field name, using a period to separate the column and field. Multiple column and field entries must be separated by a comma and space.
        
        You can use operators like IS NULL or IS NOT NULL to build an advanced query. For example, <column name>.<field name > IS NOT NULL, <column name>.< field name>.
        
    4.  Click **Save**.
5.  To define how the application assigns a resource code to reserve locations within a movement zone:
    
    **Notes**:
    
    -   The location reservation process reserves a staging location for picked inventory based on the attributes that you define. For example, the location can be reserved for a specific shipment.
    -   If the warehouse uses a user-defined item hierarchy or if user-defined inventory attributes are enabled, those fields are available for selection. Field descriptions are not provided for user-defined fields.
    
    1.  Under **SHIP STAGING LANE ASSIGNMENT**, click **Location Reservation**.
    2.  In the grid, click the movement zone for which you want to define a resource variable.
        
        **Note**: A movement zone is only displayed when at least one ship staging location is associated to the movement zone.
        
    3.  To reserve locations using the returned value of a server command:
        1.  From the **Resource Type** drop-down list, select **Command**.
        2.  In the **Command** field, enter the command.
    4.  To reserve locations using a value derived from an attribute associated with the inventory:
        1.  From the **Resource Type** drop-down list, select **Derived**.
        2.  To select the attributes by which to reserve locations:
            1.  Click **Reserve All Locations in Zone**.
            2.  Perform one of the following tasks:
                -   To select criteria from displayed entities:
                    1.  If the advanced query is displayed, click **Simple**.
                    2.  If the available entities are not displayed, click **Show Available**.
                    3.  In the **Available** grid, select the entities that you want to use as criteria.
                    4.  Click **Add Selected**. The entities are added to the **Selected** grid.
                    5.  To remove criteria, in the **Selected** grid, select the criteria to remove, and click **Remove selected**.
                -   To enter criteria using database entities, click **Advanced**, and then enter the column and field name, using a period to separate the column and field. Multiple column and field entries must be separated by a comma and space.
            3.  Click **Save**.
        3.  To assign attribute values to locations:
            1.  Click **Reserve Specific Locations in Zone**.
            2.  In the grid next to the location, click the attribute column, and enter a value.
            3.  Click **Save**.
    5.  To reserve locations using a control number:
        1.  From the **Resource Type** drop-down list, select **Generate**.
        2.  In the **Control Number Description** field, enter the control.
    6.  To reserve a single location to which all inventory should be directed when moved into this zone:
        1.  From the **Resource Type** drop-down list, select **Location Assigned**.
        2.  In the **Location** field, enter the location.
    7.  To allow all inventory to be deposited in a single lane (no restrictions), from the **Resource Type** drop-down list, select **Unrestricted**.
    8.  Click **Apply**.
6.  To select the reason codes that are available for an operator to select when overriding a staging location:
    1.  Under **SHIP STAGING LANE ASSIGNMENT**, click **Reason Codes**.
    2.  Perform one of the following tasks:
        -   To add a reason, click **Add**.
        -   To modify a reason, in the grid, click the reason.
        -   To copy a reason, in the grid, select the check box next to the reason, and then click **Copy**.
    3.  In the **Staging Lane Override Reason** field, enter the reason.
    4.  To select the clients that use the reason code:
        1.  Click **Clients**.
        2.  In the **Available** column, select the check box next to the clients that apply.
        3.  Click **Save**.
    5.  Click **Save**.
7.  If outbound work sequencing is enabled, then select the operations that can be locked by the application for outbound work sequencing:
    1.  Under **OUTBOUND WORK SEQUENCING**, click **Operations for Sequencing Pick Work**.
    2.  In the **Available** column, select the check box next to the operations.
    3.  Click **Apply**.
8.  To define pallet positions:
    1.  Under **PALLET BUILDING**, click **Pallet Positions**.
    2.  To add a pallet position:
        1.  Click **Add**.
        2.  Enter information in the following fields:
            
            | Field | Description |
            | --- | --- |
            | Location | Location that contains the pallet position. Locations that are configured as staging or processing locations are available for selection. |
            | Pallet Position | Identifier for the position. Positions can be identified, for example, as 01, 02, 03, and so on. |
            
        3.  Click **Apply**.
    3.  To delete a pallet position:
        1.  In the grid, select the check box next to the pallet position to delete.
        2.  Click **Delete**. A confirmation message is displayed.
        3.  Click **OK**.
9.  To define the consolidation rules that determine whether cases of inventory can be consolidated after picking:
    1.  Under **PALLET BUILDING**, perform one of the following tasks:
        -   To add a consolidation rule, click **Add**.
        -   To modify a rule, in the grid, click the rule.
    2.  In the **Rule Name** field, enter a name for the pallet build consolidation rule.
    3.  In the **Available** column, select the check box next to the attributes that must match for picked inventory to be consolidated on the same pallet.
    4.  Click **Apply**.
10.  To define whether operators can override an application-directed staging lane with a different location:
     1.  Under **SHIP STAGING LANE OVERRIDE**, click **Override Behavior**.
     2.  In the grid, enter information in the following fields:
         
         | Field | Description |
         | --- | --- |
         | Allow Override | Indicates that an operator can override the application-directed staging location and deposit picked inventory to a different staging location. |
         | Override Remaining | Indicates that if the staging location was overridden when depositing a pick, then the released picks that have the same resource code as that pick should also be redirected to the new staging location. If location overrides are limited to locations in the same zone, then select this check box for the zone. To enable this "follow the leader" functionality across different movement zones, this check box must be selected for both the original and the new staging movement zones. |
         
     3.  Click **Apply**.
11.  To select the carrier services that allow a ship staging location to be overridden:
     1.  Under **SHIP STAGING LANE OVERRIDE**, click **Carrier Service Levels**.
     2.  In the **Available** column, select the check box next to the carrier service levels that allow overrides.
     3.  Click **Apply**.
12.  To define problem ship locations used to temporarily store unshippable inventory that was removed from a shipment:
     1.  Under **PROBLEM SHIP LOCATIONS**, click **Locations**.
     2.  In the **Available** column, select the check box next to the locations.
     3.  Click **Save**.
13.  To define the storage zones that are available for selection when performing putaway of the inventory that was removed from a shipment:
     1.  Under **SHIPPING ADJUSTMENT**, click **Shipment Adjustment Storage Zones**.
     2.  In the **Available** column, select the check box next to the zones.
     3.  Click **Apply**.
14.  Click **Save**.

## Outbound Staging fields

 
| Field | Description |
| --- | --- |
| Eligible Staging Lanes | If Yes, then the list of locations available for staging shipments are reloaded for each pick. It is recommended that you select Yes if you have dock door associations defined to assist in the assignment of staging locations.<br > If No, the list of locations is not reevaluated for each pick. Select No to avoid slowing down pick release processing. |
| Allocate Only Assigned Lanes | If Yes, then the application allocates a staging lane for a load from only the lanes assigned to the expected dock door or dock set. The dock lane assignment configuration defines prioritized associations between staging lanes and specific dock doors, typically based on proximity. If this field is set to Yes, then the application will only allocate a shipping staging lane that is assigned to the dock door as defined in the dock lane assignment configuration. If the assigned staging lanes are unavailable, or have a priority the application is configured to ignore, then the application does not allocate a staging location for the shipments during pick release, and the picks are not released.<br > **Note**: A staging lane may be unavailable for reasons such as it being already full or having a priority that the application is configured to ignore, as defined in the **Ignore Lane Priority** field.<br > Set this field to Yes to limit the staging lanes to which a load can be assigned based on its expected dock door; this prevents the application from allocating an unassigned staging lane that is not in close proximity to the load's transport equipment.<br > If No, then the application can allocate a staging lane for a load that is not assigned to the expected dock door or dock set. If this field is set to No, the application first attempts to allocate a staging lane that is assigned to the expected dock set for a load. When the assigned staging lanes are unavailable, the application considers all staging lanes in the same movement zone, and selects the lane with the highest priority.<br > Set this field to No to allow the application to search for a staging lane outside of the lanes assigned to the expected appointment location; however, this can result in the application allocating an unassigned staging lane that is not in close proximity to the load's transport equipment.<br > For more information, see [Dock Lane Assignment](dock-lane-assignment.md). |
| Exclude Lane Priority | Priority of the staging lane that the application excludes when allocating a lane. When you assign a staging lane to a dock door, you can define the priority in which you want the application to select the staging lane. If the priority of a staging lane matches this value, the application does not allocate the lane. For example, assume there is a staging lane you want to reserve for a specific purpose. You can set **Exclude Lane Priority** to 99, and then update the staging lane priority to 99 in the dock lane assignment configuration. When picks are released for a load and the application attempts to allocate a staging lane, the staging lane with priority 99 is excluded from allocation. |
| Enable Outbound Work Sequencing | If Yes, then outbound work sequencing is enabled for the warehouse. Outbound work sequencing manages the sequence in which picked inventory is delivered to ship staging by locking and unlocking directed pick work in the work queue in a controlled manner. See [Outbound work sequencing](#Outbound_work_sequencing).<br > If No, the outbound work sequencing is disabled for the warehouse. |
| Work Sequencing Release Type | Value that determines how locked pick work (for the purpose of outbound work sequencing) will be unlocked so an operator can perform the work. This field is used in controlling the sequence in which picked inventory is delivered to ship staging. For example, if the sequence is by stop, then pick work for stop 1 is unlocked first. After it has been picked and deposited to ship staging, pick work for stop 2 is unlocked, and so on. This field is enabled only when **Enable Outbound Work Sequencing** is set to Yes. See [Outbound work sequencing](#Outbound_work_sequencing).<br > The following options are available for selection:<br>-   •
    
    **Item Family**: Work is unlocked based on the work release sequence (from lowest number to highest) defined for each item family required for the load.
    
    <br>
    
    **Note**: Since this value ignores stop sequence, if it is selected for a load that is being fluid loaded (skips staging), then the **Ignore Stop Sequence** field on the load should be set to Yes to ensure loading is not dictated by stop sequence.
    
    <br>
<br>-   • **Manual**: Worked is unlocked based on the manual work release sequence assigned to each piece of pick work, with the lowest sequence released first. At any time, the system will start or resume unlocking work only when there is a manual work release sequence assigned to each piece of work for a load with the manual release type. If pick work with this release type is cancelled, a configuration determines whether the manual sequence is retained for the reallocated pick.
<br>-   • **None**: Work is excluded from outbound work sequencing and is not locked in the work queue.
<br>-   • **Stop**: Work is unlocked based on the stop's loading sequence (defined on the load) in order from lowest to highest. For example, stop 1, 2, 3, and so on.
<br>-   • **Stop/Item Family**: Work is unlocked based on the work release sequence defined for each item family within a stop, and then based on the stop's loading sequence (defined on the load) in order from lowest to highest. The work for the first item family on the first stop is unlocked, and after it has been staged, the work for the next item family on the first stop is unlocked, and so on. After the first stop is staged, the first item family for the next sequential stop is unlocked, and so on.
<br > **Note**: You can define a work release type for a load, customer, and warehouse. If a work sequencing release type is not defined for a load when a stop with shipments is added to the load, the application uses the value defined for the customer. If no release type is defined for the load and customer, the application uses the warehouse value. If there are multiple customers on the load, then the application uses the value for the customer associated with the first shipment picked for the load. The work release type cannot be updated from host transactions. |
| Retain Sequence on Reallocated Cancelled Pick | If Yes, then when pick work with a manual work release sequence type is cancelled and reallocated (using the Cancel - Reallocate and Cancel - Reallocate – Reuse Loc cancel codes), the same sequence number is reassigned to the reallocated pick work. This field is enabled only when **Enable Outbound Work Sequencing** is set to Yes.<br > If No, then when pick work with a manual work release sequence is cancelled and reallocated, a new sequence number needs to be assigned manually to the reallocated pick work. |
| Action | Action that the application performs when moving a staged shipment from one staging lane to another. The application creates a work request for staging lane transfer, which is added to the work queue so that an RF operator can perform it. |
| Operations | Work operation that identifies the type of directed work that is created, such as Shipment Transfer. |
| Enable | If Yes, you can select the problem shipping locations that are used to temporarily store inventory related to a shipping issue or due to a cancelled order. The problem inventory is typically unpicked from a shipment. Inventory placed in a problem location can be moved to a quality assurance location or back into storage.<br > If No, no problem shipping locations are defined for use. |
| Small Staging Lanes | If Yes, then you can limit the use of small staging lanes to prevent them from being used for large quantities of picked inventory. You may want to restrict the use of small staging lanes, such as a parcel lane or a space that is limited due to an obstruction or physical layout, so you can control what is sent there. For example, you may want to avoid having a shipment distributed across many lanes when the entire shipment could have fit in one larger staging lane. If you set this field to Yes, then in the **Pallet Limit** field, you define the maximum number of pallets allowed in a staging lane for it to be considered small. Small staging lanes are only reserved if a lane has the capacity for at least 50% of the picked inventory.<br > **Note**: If the application reserves a staging lane for a portion of picked inventory that was too large for a small staging lane, the application will consider staging the remaining picked inventory in a small staging lane if it meets the 50% requirement. For example, assume a small staging lane has a pallet limit of 2. If 6 pallets need to be staged, the application will not use small lanes because they cannot hold 3 pallets, or 50% of the pick group. However, if the application reserves a lane for 4 of the pallets, a small staging lane could be used for the remaining 2 pallets because it has the capacity for at least 50% of the picks (1 pallet).<br > If No, then small staging lane processing is disabled. |
| Pallet Weight | Numeric value that represents the weight of an empty standard pallet (tare weight). This value is not used in application processing but may be displayed on application reports. |
| Pallet Limit | Pallet capacity that defines a small staging lane. If you enter a value, the pick release process will reserve a small staging lane if the lane has the capacity for at least 50% of the picked inventory. For example, assume the **Pallet Limit** field is set to 8, meaning that any ship staging lane with a maximum capacity of 8 or fewer pallets is considered a small staging lane. If a group of 16 pallet picks is being released, the application considers small staging lanes because the location has capacity for at least 50% of the 16 pallets (8). However, if a group of 20 pallet picks is being released, small staging lanes are not considered because they do not have the capacity for 10 pallets, or 50% of the picks. |
| Pallet Volume | Numeric value used by the pick release process to estimate how many pallet footprints are needed in a zone so that it can determine the number of locations to allocate. This number uses the same unit of measure as that of the footprint master length, width, and height. |
| Carriers | If Yes, then you can change the carrier that is assigned to a shipment after the shipment is staged.<br > **Note**: Before a carrier change can happen, the **Carriers** field in the outbound order settings must be set to Yes, the **Change Carrier** field on the order must be set to Yes.<br > If No, then you cannot change the carrier assigned to a staged shipment, even if the order configuration allows it. |
| Inventory Hold Checkpoints | Point in the shipping process at which you want the application to verify whether inventory that was picked for a shipment is still eligible for shipping. This is the point at which the application determines whether an inventory hold is applied that does not allow shipping.<br>-   • **Transport Equipment Load**: The checkpoint occurs when the operator starts to load the transport equipment.
<br>-   • **Transport Equipment Dispatch**: The checkpoint occurs when the operator attempts to dispatch the transport equipment.
<br>-   • **Transport Equipment Close**: The checkpoint occurs when the operator attempts to close the transport equipment. |
| Inventory Status Checkpoints | Point in the shipping process at which you want the application to verify whether inventory that was picked for a shipment is still eligible for shipping. This is the point at which the application determines whether any inventory is in an inventory status that does not allow shipping.<br>-   • **Transport Equipment Load**: The checkpoint occurs when the operator starts to load the transport equipment.
<br>-   • **Transport Equipment Dispatch**: The checkpoint occurs when the operator attempts to dispatch the transport equipment.
<br>-   • **Transport Equipment Close**: The checkpoint occurs when the operator attempts to close the transport equipment. |
| Create New Labels | If Yes, labels are printed for inventory that was removed from a shipment.<br > If No, the application does not automatically print a new label for inventory that is removed from a shipment. |
| Number of Labels | Number of labels the application prints for each LPN of inventory that is removed from a shipment. |
| Allow user to change Default Number of Labels | If Yes, the user is allowed to change the default number of labels the application prints when inventory is removed from a shipment.<br > If No, the user is not allowed to change the number of labels the application prints. The application prints the number of labels defined in the **Number of Labels** field. |
| Select Storage Location | Determines how you want to select a storage location when inventory that has been adjusted off of a shipment is ready to be put away.<br>-   • **Automatic**: The application provides a suggested storage location for inventory to be put away. The application performs standard putaway processing to find a location in one of the storage zones that you selected under **Shipment Adjustment Storage Zones**. If the **Allow user to change Default Storage Location** field is set to Yes, the user can override this location.
<br>-   • **Manual**: The user is prompted to select the storage location for inventory that is removed from a shipment. |
| Allow user to change Default Storage Location | If Yes, then if the application suggested a putaway location for inventory that was removed from a shipment (**Automatic** is selected in the **Select storage Location** field), then the user can override the application-selected location.<br > If No, the user is not allowed to change the application-selected location for putaway. |
| Shipment Adjustment LPN Identifiers | Field name used to indicate how the LPN is identified. |
| Shipment Adjustment sub-LPN Identifiers | Field name used to indicate how a case or sub-LPN is identified. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
