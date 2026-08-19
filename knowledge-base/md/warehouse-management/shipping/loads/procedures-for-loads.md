---
title: "Procedures for loads"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/procedures_for_loads.htm"
source: "/content/procedures_for_loads.htm"
toc_path:
  - "Warehouse Management"
  - "Shipping"
  - "Loads"
  - "Procedures for loads"
sections:
  - "Modify a load"
  - "Modify load details"
  - "Assign a shipment or load to a staging lane"
  - "Close shipping transport equipment"
  - "Dispatch shipping or storage transport equipment"
  - "Reopen closed transport equipment"
  - "Assign a shipment to an existing load"
  - "Load a stop"
  - "Modify the loading sequence of a stop"
  - "Delete a stop from a load"
  - "Change the carrier for a load"
  - "Split a shipment on a load"
  - "Unassign a shipment from a stop"
  - "Load or unload empty handling units"
  - "View and manage notes for a load"
  - "View loads"
  - "View detailed load information"
  - "View stop details"
  - "Load procedures field listings"
  - "Loads detail fields"
  - "Add or Modify Load fields"
  - "Load Stop fields"
  - "Stops detail fields"
  - "Modify Load details fields"
  - "Equipment Information fields"
  - "Close Shipping Equipment fields"
images:
  - "/content/resources/images/image430285.png"
source_sha1: 411147e78824ca19a4998f73681877fc4fcac17f
---
# Procedures for loads - Loads

You can perform the following procedures on loads.

## Modify a load

1.  Perform one of the following tasks:
    -   Select **Outbound Planner > Outbound > Loads**, and then in the grid, click the load ID or select the row for the load.
    -   Select **Shipping > Loads**, and then in the grid, click the load ID. The load details are displayed.
2.  In the grid, select the row for the load or click the load. The load details are displayed.
    
    **Note**: To add or modify a BOL, PRO, or Seal Number to the load or to the stops on load, while viewing the load details, enter information in the **BOL**, **PRO**, and **Seal Number** fields as necessary.
    
3.  From the **Actions** drop-down list, select **Modify Load**.
4.  Enter information in the [Add or Modify Load fields](#Add_or_Modify_Load_fields).
5.  Click **Next** or **STOPS**.
6.  In the grid, select the check box for the shipments to add to the load.
7.  Click **Finish**.

## Modify load details

1.  Perform one of the following tasks:
    -   [View loads](../../outbound-planner/outbound/procedures-for-loads.md), and then in the grid, click the load.
    -   View the Staging page, and then under **Lanes**, select the shipping status bar associated with the load, and then from the **Actions** drop-down list, select **View Load**.
        
        1.  Select one of the following modules: **Receiving** or **Shipping**.
            
        2.  Select **Staging**.
            
        
2.  From the **Actions** drop-down list, select **Load Details**.
3.  View and enter information in the [Modify Load details fields](#Modify_load_details_fields).
4.  To edit transport equipment information:
    1.  Under **Equipment**, click **Edit**.
    2.  Enter information in the [Equipment Information fields](#Transport_Equipment_Information_fields).
    3.  Click **Save**.
5.  Click **Save**.

## Assign a shipment or load to a staging lane

Use this procedure to assign a lane to a staged shipment or mixed shipment, or load.

**Notes**:

-   If you assign the lane for a mixed-shipment LPN and send the move to the work queue, the application will create directed work (based on the outbound staging configuration) to assign the lane only if it is being assigned to an outbound staging lane. The application does not support assigning the receiving staging or production staging lane for mixed-shipment LPNs through directed work. If a staging lane is used for receiving and shipping, then the application allows the directed lane assignment only if the mixed-shipment LPN is associated with an outbound shipment.
    
-   If you use an external pallet control system, assigning the staging lane for a mixed-shipment LPN is not supported.
-   The application creates directed work for assigning the staging lanes based on the action and operation selected in the outbound staging configuration. See [Configure outbound staging](../../configuration/outbound/shipping/outbound-staging.md).

1.  Perform one of the following tasks:
    -   To assign a shipment, [view shipments](../../outbound-planner/outbound/procedures-for-shipments.md).
    -   To assign a load, [view loads](../../outbound-planner/outbound/procedures-for-loads.md).
    -   To assign a stop, [view stop details](../../outbound-planner/outbound/procedures-for-loads.md).

**Note**: To assign multiple shipments or loads to a staging lane at the same time, use the **Shipments or Loads** tab on the Outbound page.

3.  In the grid, select the row for the shipment, or load; or click the shipment, or load.
4.  From the **Actions** drop-down list, select **Assign Lane**. The Assign Lanes page is displayed.
5.  To include a shipment or stop in the lane assignment, in the grid, confirm the check box for the shipment or load is selected If assigning a load, then to unassign a specific stop from the lane, clear the check box.
    
6.  Under **Available Lanes**, click **Find Lanes**, and then select the staging lane to which you want to assign the shipment.
7.  Click **Save**.
8.  Perform one of the following tasks:

-   When a message is displayed confirming the move, click **OK**.
-   To resolve issues with partially staged shipments:
    1.  On the **Lane Changes** window, select one of the following options:
    
    -   **Redirect remaining LPNs**: Indicates that the remaining LPNs not already in the staging lane are redirected to the new staging lane. LPNs currently in the original lane are not moved.
    -   **Move staged and redirect remaining**: Indicates that the LPNs currently staged in the original lane are moved to the new staging lane. This option is available when all the expected LPNs for a shipment are staged.
        
        **Note**: If the entire shipment has not yet been staged (for example, if additional LPNs are still being picked), this option is **Move staged and redirect remaining**. This indicates that the application moves any LPNs currently in the original staging lane to the new lane, and also redirects any in-process LPNs to the new lane.
        
        -   **Add to work queue**: Indicates that directed work is created for an operator to complete the staging lane change.
            
        
        -   **Move Immediately**: Indicates that the application is immediately updated with the LPN's new staging lane, and no work is created. Typically, you select this option if the physical move has already taken place.
    
    3.  Click **Save**.

## Close shipping transport equipment

1.  Perform one of the following tasks:
    -   [View loads](../../outbound-planner/outbound/procedures-for-loads.md), and then in the grid, click the load associated with the equipment.
        
        **Note**: To close equipment from the load details using a workstation, transport equipment must be assigned to the load and all inventory must be loaded.
        
    -   View the Staging page, and then under **Doors**, click the shipping status bar associated with the equipment.
        
        1.  Select one of the following modules: **Receiving** or **Shipping**.
            
        2.  Select **Staging**.
            
        
    -   View the Door Activity page, and then under **Doors**, click the shipping status bar associated with the equipment.
        
        1.  Select one of the following modules: **Receiving**, **Shipping**, or **Yard**.
            
        2.  Select **Door Activity**.
            
        
2.  From the **Actions** drop-down list, select **Close Equipment**.
3.  Enter information in the [Close Shipping Equipment fields](#Close_Shipping_Equipment_fields).
4.  To view information for inventory associated with the equipment that is not shippable or is short, click **Not Shippable** or **Short**.
5.  To add another seal to the transport equipment, click **Add Another Seal**, and then enter the seal number.
6.  Click **Save**. A confirmation message is displayed.
7.  Click **OK**.

## Dispatch shipping or storage transport equipment

You can also dispatch transport equipment on the [Check Out](../../yard/check-out.md) page in the Yard module, and specifically for [receiving equipment](../../shared-functions/staging/procedures-for-staging.md) on other application pages.

**Note**: If the **Tractor** field in the outbound loading configuration is set to Yes, then you must first have a tractor assigned to the transport equipment before the equipment can be dispatched. See [Associate a tractor with transport equipment](../../shared-functions/transport-equipment/procedures-for-transport-equipment.md).

1.  Perform one of the following tasks:
    
    **Note**: In addition to the following tasks, on the Staging, Door Activity, or Loads page, you can also click the **Dispatch** tag associated with the equipment, and then click **Dispatch Load**.
    
    -   [View loads](../../outbound-planner/outbound/procedures-for-loads.md), and then in the grid, click the load associated with the equipment.
        
        **Note**: Storage transport equipment cannot be dispatched from the load view. To dispatch shipping equipment from the load details, the equipment must be assigned to the load and closed.
        
    -   View the Staging page, and then click the shipping or storage status bar associated with the equipment.
        
        1.  Select one of the following modules: **Receiving** or **Shipping**.
            
        2.  Select **Staging**.
            
        
    -   View the Door Activity page, and then click the shipping or storage status bar associated with the equipment.
        
        1.  Select one of the following modules: **Receiving**, **Shipping**, or **Yard**.
            
        2.  Select **Door Activity**.
            
        
2.  From the **Actions** drop-down list, select **Dispatch**.
3.  Enter information in the following fields:
    
     
    | Field | Description |
    | --- | --- |
    | Tractor Number | Number of the tractor that is hauling the transport equipment. |
    | Driver | Name of the driver who delivered or picked up the transport equipment. |
    | Driver License | Driver license number for the transport equipment driver. |
    
4.  Click **Save**. A confirmation message is displayed.
5.  Click **OK**.

## Reopen closed transport equipment

1.  Perform one of the following tasks:
    -   [View loads](../../outbound-planner/outbound/procedures-for-loads.md), and then in the grid, click the load associated with the equipment.
        
        **Note**: To reopen closed equipment from the load details, transport equipment must be assigned to the load.
        
    -   View the Staging page, and then under **Doors**, click the shipping status bar associated with the equipment.
        
        1.  Select one of the following modules: **Receiving** or **Shipping**.
            
        2.  Select **Staging**.
            
        
    -   View the Door Activity page, and then under **Doors**, click the shipping status bar associated with the equipment.
        
        1.  Select one of the following modules: **Receiving**, **Shipping**, or **Yard**.
            
        2.  Select **Door Activity**.
            
        
2.  From the **Actions** drop-down list, select **Reopen Closed Equipment**. A confirmation message is displayed.
3.  Click **OK**. A message is displayed confirming the equipment is reopened, or stating that the equipment could not be reopened. Dispatched equipment cannot be reopened.
4.  Click **OK**.

## Assign a shipment to an existing load

When you assign a shipment to an existing load, you can create a new stop for the shipment if its destination location does not match an existing stop; or, you can assign the shipment to an existing stop on the load if its destination matches that of an existing stop.

**Note**: When you assign shipments to a stop, you can view the load measurements as they adjust for the added inventory so you can monitor the load size.

1.  To assign a shipment to a stop on a load:
    1.  [View stop details](../../outbound-planner/outbound/procedures-for-loads.md).
    2.  From the **Actions** drop-down list, select **Assign Shipments**.
    3.  In the grid, select the check box for the shipments to assign to the stop.
        
        **Note**: If no shipments are displayed, then there are no existing unassigned shipments destined to the route-to customer on the stop.
        
    4.  Click **Save**.
2.  To assign a staged shipment to a load:
    1.  View the Staging page.
        
        1.  Select one of the following modules: **Receiving** or **Shipping**.
            
        2.  Select **Staging**.
            
        
    2.  Under **Lanes**, click the **Unassigned** tag associated with the shipment, and then click **Assign to existing load**.
    3.  To ensure the shipment will be assigned to an existing load, under **Selected Shipments**, confirm the check box for the shipment is selected.
    4.  Under **Available Loads**, select the load to which the shipment should be assigned.
    5.  Click **Save**.

## Load a stop

Use this procedure to load a stop either immediately or by creating work for the work queue. If you load the final stop for the load, you can also close and dispatch the transport equipment. You can load a stop when all inventory for the stop is staged.

1.  [View loads](#View_loads), and then in the grid, click the load containing the stop.
2.  Select **Stops**.
3.  In the grid, select the check box next to the stop you want to load.
4.  Click **Load Stop**.
5.  Enter information in the [Load Stop fields](#Load_Stop_fields).
6.  To view inventory associated with the stop that cannot be shipped, click **Not Shippable** and view the applicable [Not Shippable Inventory fields](../shipping-issues/procedures-for-shipping-issues.md).
7.  To view inventory associated with the stop that was allocated short, click **Short** and view the applicable [Short Inventory fields](../shipping-issues/procedures-for-shipping-issues.md).
8.  Click **Save**.

## Modify the loading sequence of a stop

Use this procedure to rearrange the loading sequence for the stops on a load.

**Note**: You can only modify the sequence of a stop if the loading work for the stop has not started.

1.  [View loads](#View_loads), then then in the grid, click the load. The load details are displayed.
2.  Select **Stops**.
3.  In the grid, click and drag the row of the stop to a new sequence position in the list of stops. A confirmation message is displayed.
    
    **Note**: An unloaded stop cannot be positioned prior to a stop for which loading has started or is complete.
    
4.  Click **Yes**.

## Delete a stop from a load

Use this procedure to delete a stop from an outbound load.

**IMPORTANT**: If you delete a stop, all of the shipments assigned to that stop are unassigned from the outbound load.

1.  [View loads](#View_loads).
2.  In the grid, click the load. The load details are displayed.
3.  Select **Stops**.
4.  In the grid, select the check box next to the stop to delete.
5.  Click **Delete**. A confirmation message is displayed.
6.  Click **Yes**.

## Change the carrier for a load

You can change the carrier for a load only if the application is configured to allow a carrier change in the outbound order settings, and if the **Change Carrier** field on the orders is set to Yes. However, if the load has assigned shipments and transport equipment, a carrier change is now allowed.

1.  [View loads](#View_loads).
2.  In the grid, click a load. The load details are displayed.
3.  From the **Actions** drop-down list, select **Change Carrier**. The Change Carrier window is displayed.
4.  Enter information in the following fields:
    
     
    | Field | Description |
    | --- | --- |
    | Carrier | Identifier for a carrier that delivers inbound inventory to the warehouse or outbound shipments to a customer. This is the identifier that will be displayed to users on the application windows and reports. In the application, a carrier can be associated with a customer, order, inbound shipment, outbound shipment, load, and service levels (such as Ground, Next Day, and Saturday Delivery). |
    | Service Level | Identifier for the service and transit time provided by the carrier that transports an order or shipment to the customer. For example, for a parcel carrier it may be used to indicate services such as express, second-day air, or standard delivery. |
    
5.  Click **OK**.

## Split a shipment on a load

If you split a shipment for which inventory has already been loaded, the loaded inventory remains as one shipment, and the application assigns a new shipment identifier to the remaining, unloaded inventory that is split.

1.  [View stop details](#View_stop_details).
2.  In the grid, select the check box next to the shipment you want to split.
3.  From the **Actions** drop-down list, select **Split Shipment**.
4.  Enter information in the following fields:
    
     
    | Field | Description |
    | --- | --- |
    | Assign Inventory to Load | Determines how the application processes the remaining inventory that is part of the shipment but has not been picked or is picked but not yet loaded.<br>-   • **Assign to an existing load with the same carrier**: Indicates that the remaining inventory is assigned to a load that is shipped with the same carrier. If you select this option, you also select the existing load from the drop-down list to which the inventory is assigned.
    <br>-   •
        
        **Leave as unassigned shipments**: Indicates that the remaining inventory is not assigned to a load, but is assigned a new shipment identifier.
        
        <br>
    <br>-   • **Create a new load**: Indicates that the remaining inventory is assigned to a new, application-generated load, and is assigned a new shipment identifier. |
    | Move Inventory | Staging lane to which you want to move the remaining inventory (and to which pending inventory for the shipment is also directed). If you do not select a new staging lane, the inventory remains in its original staging lane. |
    
5.  Click **Save**.

## Unassign a shipment from a stop

1.  [View stop details](#View_stop_details).
2.  In the grid, select the check box next to the shipment you want to unassign.
3.  From the **Actions** drop-down list, select **Unassign Shipments**. A confirmation message is displayed.
4.  Click **Yes**.

## Load or unload empty handling units

To load empty non-serialized handling units, the shipment must be staged, in the process of being loaded, or loaded, and the transport equipment must be checked in to the dock door.

**Note**: To load and unload empty serialized handling units, you must use an RF device.

1.  [View shipments](../../outbound-planner/outbound/procedures-for-shipments.md).
2.  In the grid, click an outbound shipment. The shipment details are displayed.
3.  Select **Empty Handling Units**.
4.  To load empty handling units:
    1.  From the **Actions** drop-down list, select **Load Empty Handling Units**.
    2.  Enter information in the [Load Empty Handling Units fields](../../outbound-planner/outbound/procedures-for-shipments.md).
    3.  Click **Load**. The application updates the loaded/shipped quantity for the handling unit type.
        
        **Note**: If a quantity of the handling unit type has already been loaded for the shipment, the new quantity is added to the existing quantity. If the handling unit type has not been previously loaded, then a new row is displayed in the Empty Handling Units grid with the loaded quantity.
        
5.  To unload empty handling units:
    1.  In the grid, select the row for the handling unit type to unload.
    2.  From the **Actions** drop-down list, select **Unload Empty Handling Units**.
    3.  In the **Quantity** field, enter the number of handling units to unload.
    4.  Click **Unload**. The application updates the loaded/shipped quantity for the handling unit type. If you unloaded the entire quantity of a handling unit type, the row is removed from the Empty Handling Units grid.

## View and manage notes for a load

Use this procedure to view, add, or modify notes for an outbound load or its associated transport equipment or appointment.

1.  [View loads](#View_loads).
2.  In the grid, click the load for which you want to view or manage notes. The load details are displayed.
3.  Click **Notes**.
4.  Perform one of the following tasks:
    -   To manage notes for the load, select the load identifier.
    -   To manage notes for the transport equipment, select the equipment identifier.
    -   To manage notes for the appointment, select the appointment date and time.
5.  To add or modify a note, in the text box, add or modify the note text, and then click **Save**.
6.  To delete an entire note:
    1.  In the text box, click ![Delete](../../../../images/resources/images/image430285.png). A confirmation message is displayed.
    2.  Click **Yes**.

## View loads

You can access the display of loads from the Outbound Planner, Shipping, and Picking modules. Some grid views require the entry of search criteria prior to displaying data on the page.

Perform one of the following tasks:

-   Select **Outbound Planner > Outbound > Loads**.
-   Select **Shipping > Loads**.
-   Select **Picking > Picks and Waves > Waves**, and then in the grid, click a wave, and then select **Loads**.

## View detailed load information

Use this procedure to view detailed load information, including information for the stops, orders, and shipments associated with a load.

1.  Perform one of the following tasks:
    -   [View loads](#View_loads).
    -   View a grid with a link for a load.
2.  Click the load for which you want to view detailed information.
3.  View information in the [Loads detail fields](#Loads_detail_fields).
4.  Select **Stops** and view information in the [Stops detail fields](#Stops_detail_fields).
5.  Select **Orders** and view information in the [Order detail fields](../../outbound-planner/outbound/procedures-for-orders.md).
6.  Select **Shipments** and view information in the [Shipment detail fields](../../outbound-planner/outbound/procedures-for-shipments.md).
7.  Select **Picks** and view information in the [Picks detail fields](../../shared-functions/waves-and-picks/procedures-for-picks-and-work-assignments.md).
8.  Select **LPNs** and view information in the [LPN detail field listings](../../shared-functions/inventory/procedures-for-lpns.md).
9.  Select **Shorts** and view information in the [Shorts detail fields](../../outbound-planner/outbound/procedures-for-shorts-and-replenishments.md).
10.  Select **Pending Replens** and view information in the [Pending Replenishment detail fields](../../outbound-planner/outbound/procedures-for-shorts-and-replenishments.md).

**Note**: Demand replenishments created as a result of pre-inventory allocation (PIA) processing are not displayed on the **Pending Replens** tab, because they are created as pick work and not replenishment work. You can view demand replenishments on the Picking and Outbound Planner Dashboards.

12.  Select **Cross Dock** and view information in the [Cross Dock detail fields](../../outbound-planner/outbound/procedures-for-shorts-and-replenishments.md).

## View stop details

1.  [View loads](#View_loads).
2.  In the grid, click the load containing the stop. The load details are displayed.
3.  Select **Stops**.
4.  In the grid, click the stop, and then view the information in the [Stops detail fields](#Stops_detail_fields).

## Load procedures field listings

### Loads detail fields

 
| Field | Description |
| --- | --- |
| Departure | Date and time that the transport equipment associated with a load is scheduled to depart from the warehouse. |
| Load | Unique identifier for a load. A load is one or more shipments grouped together into one or more stops that are shipped on a single piece of transport equipment. |
| Route | Number of stops on the load. |
| Carrier | Identifier for a carrier that delivers inbound inventory to the warehouse or outbound shipments to a customer. This is the identifier that will be displayed to users on the application windows and reports. In the application, a carrier can be associated with a customer, order, inbound shipment, outbound shipment, load, and service levels (such as Ground, Next Day, and Saturday Delivery). |
| Equipment | Alphanumeric identifier for transport equipment. Transport equipment numbers are not unique, can exist multiple times, and can be associated with various carriers. |
| Measures | Estimated measurement values of the outbound load such as the number of pallets, the weight, and the load volume. The values are estimated based on the item's UOM configuration, and the application does not consider additional processing that may consolidate inventory during picking and outbound operations. |
| Location | Unique name for a location within the facility that is used to receive, store, process, or ship inventory. |
| Allocated | Percentage of inventory that has been allocated. Additionally, an X of Y value displays the number of eaches that are allocated out of the total number of expected eaches; for example, (50 of 100). The values for this field represent the amount of allocated inventory for the displayed entity (order, shipment, load, or wave). |
| Picked | Percentage of inventory that has been picked. Additionally, an X of Y value displays the number of eaches that are picked out of the total number of expected eaches; for example, (50 of 100). The values for this field represent the amount of picked inventory for the displayed entity (order, shipment, stop, load, or wave). |
| Loaded | Percentage of inventory that has been loaded. Additionally, an X of Y value displays the number of eaches that are loaded out of the total number of expected eaches; for example, (50 of 100). The values for this field represent the amount of loaded inventory for the displayed entity (order, shipment, stop, load, or wave). |
| Wave | Value that is assigned to the group of pick-type work requests (picks, replenishments, and cross docks) that are created when the wave is planned. The wave name distinguishes one group of pick-type work requests from another, which enables you to track the requests through the application. For example, if you allocate inventory for a single shipment, then all of the picks, replenishments, and cross docks generated for the shipment have the same wave name. |
| BOL | Bill of lading (BOL) number assigned to the load or stop. The BOL is a carrier's contract and receipt for goods that it agrees to transport from one place to another, and to deliver to a designated person or assignees. |
| PRO | Progressive routing order (PRO) number assigned to a load, shipment, or stop. A PRO number is assigned as a reference to a shipment for a carrier, and is used by the carrier for most correspondence in relation to tracking the shipment. |
| Seal Number | Identifying number that is displayed on the seal or tag used to close shipping transport equipment. |

### Add or Modify Load fields

 
| Field | Description |
| --- | --- |
| Load | Unique identifier for a load. A load is one or more shipments grouped together into one or more stops that are shipped on a single piece of transport equipment. |
| Carrier | Identifier for a carrier that delivers inbound inventory to the warehouse or outbound shipments to a customer. This is the identifier that will be displayed to users on the application windows and reports. In the application, a carrier can be associated with a customer, order, inbound shipment, outbound shipment, load, and service levels (such as Ground, Next Day, and Saturday Delivery). |
| Equipment | Alphanumeric identifier for transport equipment. Transport equipment numbers are not unique, can exist multiple times, and can be associated with various carriers. |
| Transport Mode | Name of the transport mode used to ship inventory. |
| PRO Number | Progressive routing order (PRO) number assigned to a load, shipment, or stop. A PRO number is assigned as a reference to a shipment for a carrier, and is used by the carrier for most correspondence in relation to tracking the shipment. |
| Document Number | Unique number that identifies the paperwork associated with shipping inventory. Document numbers are applied at the outbound load, stop, or shipment level. |
| Maximum Users | Maximum number of users who are allowed to perform directed and undirected work for the load. For example, if this value is 1, then if one user is performing work (such as picking) for the load, then no other users can perform work (such as picking, transferring, staging, or loading) for the load. If this value is 0, then there is no limit to the number of users who can perform work for the load. |
| PARS Number | Pre-Arrival Review System (PARS) number that is used by some countries for importing goods into the country. It allows for shipment information to be processed by customs before goods arrive at the border. A PARS number is required on outbound loads destined for countries that require it. |
| Lock User | If Yes, then a user who is performing work (such as picking, transferring, staging, or loading) for the outbound load is not allowed to perform work for other loads until there is no longer any pending work for this load.<br > If No, then a user performing work on this load can perform work for other loads while there is pending work for this load. |
| Ignore Stop Sequence | If Yes, then an operator can load the transport equipment as needed and does not need to follow the stop sequence order. This overrides the break stop sequence.<br > If No, then the operator must follow the stop sequence order. |
| Load Host External ID | Alternate identifier for the route-to address information. This identifier is typically sent from the host, and it is used to reconcile address information with the information contained in the host application. |
| Work Sequencing Release Type | Value that determines how locked pick work (for the purpose of outbound work sequencing) will be unlocked so an operator can perform the work. This field is used in controlling the sequence in which picked inventory is delivered to ship staging. For example, if the sequence is by stop, then pick work for stop 1 is unlocked first. After it has been picked and deposited to ship staging, pick work for stop 2 is unlocked, and so on. This field is enabled only when **Enable Outbound Work Sequencing** is set to Yes. See [Outbound work sequencing](../../configuration/outbound/shipping/outbound-staging.md).<br > The following options are available for selection:<br>-   •
    
    **Item Family**: Work is unlocked based on the work release sequence (from lowest number to highest) defined for each item family required for the load.
    
    <br>
    
    **Note**: Since this value ignores stop sequence, if it is selected for a load that is being fluid loaded (skips staging), then the **Ignore Stop Sequence** field on the load should be set to Yes to ensure loading is not dictated by stop sequence.
    
    <br>
<br>-   • **Manual**: Worked is unlocked based on the manual work release sequence assigned to each piece of pick work, with the lowest sequence released first. At any time, the system will start or resume unlocking work only when there is a manual work release sequence assigned to each piece of work for a load with the manual release type. If pick work with this release type is cancelled, a configuration determines whether the manual sequence is retained for the reallocated pick.
<br>-   • **None**: Work is excluded from outbound work sequencing and is not locked in the work queue.
<br>-   • **Stop**: Work is unlocked based on the stop's loading sequence (defined on the load) in order from lowest to highest. For example, stop 1, 2, 3, and so on.
<br>-   • **Stop/Item Family**: Work is unlocked based on the work release sequence defined for each item family within a stop, and then based on the stop's loading sequence (defined on the load) in order from lowest to highest. The work for the first item family on the first stop is unlocked, and after it has been staged, the work for the next item family on the first stop is unlocked, and so on. After the first stop is staged, the first item family for the next sequential stop is unlocked, and so on.
<br > **Note**: You can define a work release type for a load, customer, and warehouse. If a work sequencing release type is not defined for a load when a stop with shipments is added to the load, the application uses the value defined for the customer. If no release type is defined for the load and customer, the application uses the warehouse value. If there are multiple customers on the load, then the application uses the value for the customer associated with the first shipment picked for the load. The work release type cannot be updated from host transactions. |

### Load Stop fields

 
| Field | Description |
| --- | --- |
| Dock Door | Dock door at which the transport equipment is or will be checked in. |
| Move Method | The method by which the inventory is moved onto the transport equipment.<br>-   • **Send work to work queue**: Indicates that a work request is sent to the work queue for an RF operator to load the stop. If you select this option, you can also select a specific operator from the drop-down list to which the work is assigned.
<br>-   • **System loads stop immediately**: Indicates that the application will immediately consider the stop as loaded and no work request is sent. |
| Assign to User | Operator to which the work for loading the stop is assigned. |
| Close Equipment | Indicates the transport equipment is immediately closed upon completing the stop. This field is only available if you select to load the stop immediately and if it is the final stop to be loaded on the equipment. |
| Dispatch Equipment | If Yes, then the transport equipment is immediately dispatched upon completing the stop. This field is only available if you first select to load the stop immediately, close the equipment, and if it is the final stop to be loaded on the equipment.<br > If No, then the transport equipment is not dispatched upon completing the stop. |
| Stop Seal | Identification number of the stop seal assigned to the stop when the application immediately loads the stop. |

### Stops detail fields

 
| Field | Description |
| --- | --- |
| Customer | Name and address information used to identify the business to whom the inventory on the stop is to be shipped. |
| BOL | Bill of lading (BOL) number assigned to the load or stop. The BOL is a carrier's contract and receipt for goods that it agrees to transport from one place to another, and to deliver to a designated person or assignees. |
| PRO | Progressive routing order (PRO) number assigned to a load, shipment, or stop. A PRO number is assigned as a reference to a shipment for a carrier, and is used by the carrier for most correspondence in relation to tracking the shipment. |
| Seal Number | Identification number of the stop seal assigned to the stop when the application immediately loads the stop. |
| Picked | Percentage of inventory that has been picked. Additionally, an X of Y value displays the number of eaches that are picked out of the total number of expected eaches; for example, (50 of 100). The values for this field represent the amount of picked inventory for the displayed entity (order, shipment, stop, load, or wave). |
| Loaded | Percentage of inventory that has been loaded. Additionally, an X of Y value displays the number of eaches that are loaded out of the total number of expected eaches; for example, (50 of 100). The values for this field represent the amount of loaded inventory for the displayed entity (order, shipment, stop, load, or wave). |

### Modify Load details fields

 
| Field | Description |
| --- | --- |
| BOL | Bill of lading (BOL) number assigned to the load or stop. The BOL is a carrier's contract and receipt for goods that it agrees to transport from one place to another, and to deliver to a designated person or assignees. |
| PRO | Progressive routing order (PRO) number assigned to a load, shipment, or stop. A PRO number is assigned as a reference to a shipment for a carrier, and is used by the carrier for most correspondence in relation to tracking the shipment. |
| Appointment Time | Date and time that identifies the start and end of the appointment associated with the load. |
| Appointment Location | Code that identifies the dock set or dock door location at which that appointment occurs. Only dock sets that are available during the defined date and time are available for selection. |
| Use | Value that describes the purpose of the transport equipment, which can help is assigning an appropriate yard or dock door location. You can designate transport equipment for one of the following uses:<br>-   • Receiving
<br>-   • Shipping
<br>-   • Storage |
| Type | Transport equipment type assigned to the transport equipment. A transport equipment type identifies characteristics that are shared by individual pieces of transport equipment. For example, you can create a type for flatbed trailers, one 48 ft. rear load trailers, and another for equipment that has a liftgate. See [Transport Equipment Type](../../configuration/equipment/equipment/transport-equipment-type.md). |
| Check in immediately | Indicates that the transport equipment is immediately checked in. The drop-down list that is displayed shows dock door and yard locations at which the transport equipment can be checked in.<br > This check box is only available if transport equipment is added to the appointment and default Equipment Status is not Checked In. |
| Carrier | Identifier for a carrier that delivers inbound inventory to the warehouse or outbound shipments to a customer. This is the identifier that will be displayed to users on the application windows and reports. In the application, a carrier can be associated with a customer, order, inbound shipment, outbound shipment, load, and service levels (such as Ground, Next Day, and Saturday Delivery). |
| Service Level | Identifier for the service and transit time provided by the carrier that transports an order or shipment to the customer. For example, for a parcel carrier it may be used to indicate services such as express, second-day air, or standard delivery. |
| Carrier Phone Number | Phone number at which the carrier can be contacted (typically, a cell phone number). |
| Appointment Notes | Text that further explains any additional appointment information. |
| Transport Equipment Notes | Text that further explains any additional transport equipment information. |

### Equipment Information fields

 
| Field | Description |
| --- | --- |
| Equipment | Alphanumeric identifier for transport equipment. Transport equipment numbers are not unique, can exist multiple times, and can be associated with various carriers. |
| Carrier | Identifier for a carrier that delivers inbound inventory to the warehouse or outbound shipments to a customer. This is the identifier that will be displayed to users on the application windows and reports. In the application, a carrier can be associated with a customer, order, inbound shipment, outbound shipment, load, and service levels (such as Ground, Next Day, and Saturday Delivery). |
| Use | Value that describes the purpose of the transport equipment, which can help is assigning an appropriate yard or dock door location. You can designate transport equipment for one of the following uses:<br>-   • Receiving
<br>-   • Shipping
<br>-   • Storage |
| Type | Transport equipment type assigned to the transport equipment. A transport equipment type identifies characteristics that are shared by individual pieces of transport equipment. For example, you can create a type for flatbed trailers, one 48 ft. rear load trailers, and another for equipment that has a liftgate. See [Transport Equipment Type](../../configuration/equipment/equipment/transport-equipment-type.md). |
| Equipment Size | Size of the transport equipment. The size helps you select an appropriate yard storage or dock door location. |
| Equipment Weight | Current weight of the transport equipment. If you want to change the measurement unit, click the unit next to the field, and then select a different unit. |
| Equipment Condition | Description of the current condition of the transport equipment. |
| Reference | Optional internal alphanumeric reference number assigned to a piece of transport equipment when it is checked in to the warehouse. If you specify a reference number, then it is a required entry when performing a yard audit, and is used by the application to validate the equipment being audited. |
| Delivery | If Yes, this shipping transport equipment is for delivery equipment. If the shipping equipment is to be used for delivery, it must be defined as such prior to check in (while the equipment status is Expected). This field is only available for shipping transport equipment.<br > If No, this transport equipment is not used for delivery. |
| Refrigerated | If Yes, the transport equipment can accommodate inventory that requires refrigeration.<br > If No, the transport equipment is not able to accommodate inventory that requires refrigeration. |
| Turn Around | If Yes, this receiving equipment can be turned around after it is unloaded and then used for shipping. Receiving equipment must be associated with a carrier before it can be turned around. Only available for receiving transport equipment.<br > If No, this receiving equipment cannot be immediately used for shipping once the equipment is empty. |
| Image | Media tool that displays the image that is associated with the entity. If an image has not been associated with the entity, a default image is displayed. You can view an enlarged version of the image and, depending on the settings, you can add, change, or remove the associated image file. |
| Tractor | Alphanumeric identifier for a tractor. Vehicles used to haul the transport equipment, such as tractors, rail engines, and ships, are referred to as tractors. Tractor numbers are not unique, can exist multiple times, and can be associated with various carriers. |
| Driver | Name of the driver who delivered or picked up the transport equipment. |
| License | Driver license number for the driver who delivered or picked up the transport equipment. |
| Equipment Broker | Name of the person or company that owns the transport equipment. |
| Live | If Yes, a driver is waiting with the transport equipment.<br > If No, a driver is not waiting with the transport equipment. |
| Seal 1 | Identifying number that is displayed on the seal or tag used to close shipping transport equipment. |
| Seal 2 | Identifying number that is displayed on the seal or tag used to close shipping transport equipment. |
| Seal 3 | Identifying number that is displayed on the seal or tag used to close shipping transport equipment. |
| Seal 4 | Identifying number that is displayed on the seal or tag used to close shipping transport equipment. |
| Transport Equipment Notes | Text that further explains any additional transport equipment information. |
| Tractor Reference | Optional internal alphanumeric reference number assigned to tractor when it is checked in to the facility. |

### Close Shipping Equipment fields

 
| Field | Description |
| --- | --- |
| Seal 1 | Identifying number that is displayed on the seal or tag used to close shipping transport equipment. |
| Dispatch Equipment | If Yes, then the transport equipment is dispatched immediately after it is closed.<br > If No, then you can select a date on which to manually dispatch the transport equipment. |
| Set Expected Dispatch Date | Date on which you expect to manually dispatch the transport equipment. Only available if the **Dispatch Equipment** field is set to Yes. |
| Move Equipment (Optional) | Location to which the closed transport equipment is to be moved. Only available if the **Dispatch Equipment** field is set to No. |
| Assign User (Optional) | User that is assigned to move the transport equipment. Only available if the **Dispatch Equipment** field is set to No. |
| Tractor Reference | Optional internal alphanumeric reference number assigned to tractor when it is checked in to the facility. |
| Driver | Name of the driver who delivered or picked up the transport equipment. |
| Driver License | Driver license number for the transport equipment driver. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2023 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
