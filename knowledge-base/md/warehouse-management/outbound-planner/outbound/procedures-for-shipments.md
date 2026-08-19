---
title: "Procedures for shipments"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/procedures_for_shipments.htm"
source: "/content/procedures_for_shipments.htm"
toc_path:
  - "Warehouse Management"
  - "Outbound Planner"
  - "Outbound"
  - "Procedures for shipments"
sections:
  - "Add or modify a shipment"
  - "Add or remove a shipment line"
  - "Perform shipment mass update"
  - "Assign a shipment or load to a staging lane"
  - "Cancel a shipment"
  - "Delete a shipment"
  - "Change the carrier of a shipment"
  - "Split a shipment on a load"
  - "Stage a shipment"
  - "Load or unload empty handling units"
  - "View shipments"
  - "View detailed shipment information"
  - "Shipment detail fields"
  - "Add or Modify Shipment fields"
  - "Shipment Mass Update fields"
  - "Load Empty Handling Units fields"
  - "Empty Handling Units detail fields"
images: []
source_sha1: 9fba10a9b27bb08dda6903707c814e1a347be9b0
---
# Procedures for shipments

You can perform the following procedures on shipments.

## Add or modify a shipment

1.  Perform one of the following tasks:
    -   To add a shipment, select **Outbound Planner > Outbound > Shipments**, and then from the **Actions** drop-down list, select **Add Shipment**.
        
        **Note**: You can only add a shipment from the Outbound Planner module.
        
    -   To modify a shipment:
        1.  Perform one of the following tasks:
            -   [View shipments](#View_shipments).
            -   View a grid that displays a link for the shipment.
        2.  In the grid, click the shipment. The shipment details are displayed.
        3.  From the **Actions** drop-down list, select **Modify Shipment**.
2.  Enter information in the [Add or Modify Shipment fields](#Add_or_modify_shipment_fields).
3.  To add a work assignment rule reference to override the work assignment rule for the shipment:
    1.  In the **Work Assignment Rule Reference** field, click **Add New**. The Add New Work Assignment Rule Reference window is displayed.
    2.  Enter the **Work Assignment Rule Reference** name, **Description**, and **Short Description**.
    3.  Click **Save**.
        
        **Note**: The application does not process an override rule for the shipment unless the rule reference is included as selection criteria for the override rule. For more information on setting up work assignment rule references, see [Work assignment rule reference setup](../../configuration/outbound/picking/work-assignments.md).
        
4.  To maintain shipment lines:
    
    **Note**: Shipment lines are automatically created when you add an order line to a shipment; therefore, the two terms (shipment line and order line) are used interchangeably in this context.
    
    1.  Click **Shipment Lines**.
    2.  To add a shipment line:
        
        **Note**: Each order line you select represents a new shipment line that is added to the shipment.
        
        1.  Under **Available Orders**, select the check box next to the order lines to add to the shipment.
        2.  Click **Add Shipment Line**. The lines are displayed under Shipment Lines.
    3.  To remove a shipment line from the shipment:
        1.  Under **Shipment Lines**, select the check box next to the line.
        2.  Click **Delete**. A confirmation message is displayed.
        3.  Click **OK**.
    4.  To cancel a shipment line: 
        
        **Note**: When you cancel a shipment line, any pending picks, replenishments, and cross docks are also cancelled. If a shipment line is already picked, it must be unpicked before it can be cancelled.
        
        1.  Under **Shipment Lines**, select the check box next to the line.
        2.  Click **Cancel**. A confirmation message is displayed.
        3.  Click **OK**.
5.  Click **Save**.

## Add or remove a shipment line

Shipment lines are automatically created when you add an order line to a shipment; therefore, the two terms (shipment line and order line) are used interchangeably in this context.

1.  Perform one of the following tasks:
    -   [View shipments](#View_shipments).
    -   View a grid that displays a link for the shipment.
2.  In the grid, click the shipment. The shipment details are displayed.
3.  From the **Actions** drop-down list, select **Modify Shipment**.
4.  Click **Shipment Lines**.
5.  Perform one of the following tasks:
    -   To add a shipment line:
        1.  Under **Available Order Lines**, select the check box next to the order lines to add to the shipment.
            
            **Note**: Each order you select represents a new shipment line that is added to the shipment.
            
        2.  Click **Add Shipment Line**. The lines are displayed under Shipment Lines.
            
            **Note**: If a selected order line could not be added to the shipment, the Create Shipment Line Failure window is displayed with the reason the order line could not be added.
            
    -   To remove a shipment line:
        1.  Under **Shipment Lines**, select the check box next to the line.
        2.  Click **Delete**. A confirmation message is displayed.
        3.  Click **OK**.
6.  Click **Save**.

## Perform shipment mass update

You can query for shipments that you want to change, and then for multiple selected shipments, update the attribute values in one process instead of having to change the attribute for each individual shipment.

**Note**: No restrictions are applied to shipment mass update, and you can perform shipment mass update before and after allocation.

1.  View the Shipment Mass Update page.
    
    1.  Select one of the following modules: **Outbound Planner**, **Picking**, or **Shipping**.
    2.  Select **Shipment Mass Update**.
    
2.  In the filter, enter search criteria to select the shipments to update.
3.  Click **Update Shipments**. The Update Shipments window is displayed.
4.  To manage additional fields that are available for mass update:
    1.  Click **Manage**. The Shipment Update Fields window is displayed.
    2.  To add fields for mass update, in the **Available** column, select the check box next to each field.
    3.  To remove fields from mass update, in the **Available** column, deselect the check box next to each field.
    4.  Click **Save**.
5.  On the Update Shipments window, select the check box next to each attribute you want to update, and then enter information in the applicable [Shipment Mass Update fields](#Shipment_mass_update_fields).
6.  Click **Save**.

After a mass update is processed, you can view the results to determine whether the action was successful. If an updated value is not applicable to one or more shipments, a failure message is displayed. For example, a shipment cannot be updated to Saturday delivery if the shipment has a carrier that does not provide Saturday delivery.

## Assign a shipment or load to a staging lane

Use this procedure to assign a lane to a staged shipment or mixed shipment, or load.

**Notes**:

-   If you assign the lane for a mixed-shipment LPN and send the move to the work queue, the application will create directed work (based on the outbound staging configuration) to assign the lane only if it is being assigned to an outbound staging lane. The application does not support assigning the receiving staging or production staging lane for mixed-shipment LPNs through directed work. If a staging lane is used for receiving and shipping, then the application allows the directed lane assignment only if the mixed-shipment LPN is associated with an outbound shipment.
    
-   If you use an external pallet control system, assigning the staging lane for a mixed-shipment LPN is not supported.
-   The application creates directed work for assigning the staging lanes based on the action and operation selected in the outbound staging configuration. See [Configure outbound staging](../../configuration/outbound/shipping/outbound-staging.md).

1.  Perform one of the following tasks:
    -   To assign a shipment, [view shipments](#View_shipments).
    -   To assign a load, [view loads](procedures-for-loads.md).
    -   To assign a stop, [view stop details](procedures-for-loads.md).

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

## Cancel a shipment

You cannot cancel a shipment for which picking has begun; however, individual orders can still be cancelled as long as picking for the order has not started.

1.  [View shipments](#View_shipments).
    
    **Note**: To cancel multiple shipments at the same time, use the Shipments tab on the Outbound page.
    
2.  In the grid, select the check box for each shipment to cancel; or click a shipment to display the shipment details.
3.  From the **Actions** drop-down list, select **Cancel Shipment**. The status of the shipment is changed to Cancelled.

## Delete a shipment

Deleting a shipment permanently removes the record from the application. You cannot recover a deleted shipment, and there is no history of it existing in the application.

1.  [View shipments](#View_shipments).
    
    **Note**: To delete multiple shipments at once, use the Shipments tab on the Outbound page.
    
2.  In the grid, select the check box for each shipment to delete; or click a shipment to display shipment details.
3.  From the **Actions** drop-down list, select **Delete Shipment**. A confirmation message is displayed.
4.  Click **OK**.

## Change the carrier of a shipment

You can change the carrier of a shipment only if the application is configured to allow a carrier change in the outbound order settings, if the **Change Carrier** field on the orders on the shipment is set to Yes, and if the shipment is not assigned to a load.

1.  [View shipments](#View_shipments).
    
    **Note**: To change the carrier of multiple shipments at once, use the Shipments tab on the Outbound page.
    
2.  In the grid, select the check box for each shipment for which to change the carrier; or click a shipment to display shipment details.
3.  From the **Actions** drop-down list, select **Change Carrier**. The Change Carrier window is displayed.
4.  Enter information in the following fields:
    
     
    | Field | Description |
    | --- | --- |
    | Carrier | Identifier for a carrier that delivers inbound inventory to the warehouse or outbound shipments to a customer. This is the identifier that will be displayed to users on the application windows and reports. In the application, a carrier can be associated with a customer, order, inbound shipment, outbound shipment, load, and service levels (such as Ground, Next Day, and Saturday Delivery). |
    | Service Level | Identifier for the service and transit time provided by the carrier that transports an order or shipment to the customer. For example, for a parcel carrier it may be used to indicate services such as express, second-day air, or standard delivery. |
    | System Moves Shipment Immediately | If Yes, then the staged shipment is automatically moved to the new staging lane in the application. This field is relevant if the new carrier and service level is associated with a different staging lane than the lane in which the parcels were originally staged.<br > If No, then directed work is created to move the shipment. |
    
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

## Stage a shipment

A shipment must be fully picked and in a staging lane before it can be staged.

1.  Perform one of the following tasks:
    -   [View shipments](#View_shipments), and then in the grid, click the shipment. The shipment details are displayed.
    -   [View stop details](procedures-for-loads.md), and then in the grid, select the check box next to the shipment you want to stage.
2.  From the **Actions** drop-down list, select **Stage Shipment**. A confirmation message is displayed.
3.  Click **OK**. A confirmation message is displayed confirming that the shipment is staged, or that the shipment could not be staged.
4.  Click **OK**.

## Load or unload empty handling units

To load empty non-serialized handling units, the shipment must be staged, in the process of being loaded, or loaded, and the transport equipment must be checked in to the dock door.

**Note**: To load and unload empty serialized handling units, you must use an RF device.

1.  [View shipments](#View_shipments).
2.  In the grid, click an outbound shipment. The shipment details are displayed.
3.  Select **Empty Handling Units**.
4.  To load empty handling units:
    1.  From the **Actions** drop-down list, select **Load Empty Handling Units**.
    2.  Enter information in the [Load Empty Handling Units fields](#Load_Empty_Handling_Units_fields).
    3.  Click **Load**. The application updates the loaded/shipped quantity for the handling unit type.
        
        **Note**: If a quantity of the handling unit type has already been loaded for the shipment, the new quantity is added to the existing quantity. If the handling unit type has not been previously loaded, then a new row is displayed in the Empty Handling Units grid with the loaded quantity.
        
5.  To unload empty handling units:
    1.  In the grid, select the row for the handling unit type to unload.
    2.  From the **Actions** drop-down list, select **Unload Empty Handling Units**.
    3.  In the **Quantity** field, enter the number of handling units to unload.
    4.  Click **Unload**. The application updates the loaded/shipped quantity for the handling unit type. If you unloaded the entire quantity of a handling unit type, the row is removed from the Empty Handling Units grid.

## View shipments

You can access the display of outbound shipments from the Outbound Planner, Shipping, and Picking modules. Some grid views require the entry of search criteria prior to displaying data on the page.

Perform one of the following tasks:

-   Select **Outbound Planner > Outbound > Shipments**.
    
-   Select **Shipping > Loads**, and then in the grid, click a load, and then select **Shipments**.
    
-   Select **Picking > Waves and Picks > Waves**, and then in the grid, select a wave, and then select **Shipments**.
    

## View detailed shipment information

1.  Perform one of the following tasks:
    -   [View shipments](#View_shipments).
    -   View a grid with a link for an outbound shipment.
2.  In the grid, click the shipment. The shipment details are displayed.
3.  View information in the [Shipment detail fields](#Shipment_detail_fields).
4.  Select **Orders** and view information in the [Order detail fields](procedures-for-orders.md).
5.  Select **Picks** and view information in the [Picks detail fields](../../shared-functions/waves-and-picks/procedures-for-picks-and-work-assignments.md).
6.  Select **LPNs** and view information in the [LPN detail field listings](../../shared-functions/inventory/procedures-for-lpns.md).
7.  Select **Shorts** and view information in the [Shorts detail fields](procedures-for-shorts-and-replenishments.md).
8.  Select **Pending Replens** and view information in the [Pending Replenishment detail fields](procedures-for-shorts-and-replenishments.md).

**Note**: Demand replenishments created as a result of pre-inventory allocation (PIA) processing are not displayed on the **Pending Replens** tab, because they are created as pick work and not replenishment work. You can view demand replenishments on the Picking and Outbound Planner Dashboards.

10.  Select **Customs** and view information in the [Customs Order fields](procedures-for-orders.md).
11.  Select **Cross Dock** and view information in the [Cross Dock detail fields](procedures-for-shorts-and-replenishments.md).
12.  Select **Empty Handling Units** and view information in the [Empty Handling Units detail fields](#Empty_Handling_Units_detail_fields).

## Shipment detail fields

 
| Field | Description |
| --- | --- |
| Shipment | Unique identifier for an outbound shipment. A shipment is a group of orders or order lines that are allocated together and shipped to the same location. |
| Status | Status that represents the processing state of the shipment.<br>-   • **Ready**: The shipment has been created or planned and is ready for allocation. Shipments can be created automatically by host download, or manually.
<br>-   • **In-Process**: Inventory for the shipment has been allocated.
<br>-   • **Staged**: The shipment has been staged manually or automatically. A shipment is staged when all inventory for the shipment has been picked and deposited in the ship staging location and is ready to be loaded onto the transport equipment.
<br>-   • **Loading**: At least one pallet, case, or piece of inventory has been deposited onto the transport equipment.
<br>-   • **Loaded**: All inventory for the shipment has been loaded onto the transport equipment.
<br>-   • **Complete**: The transport equipment containing the shipment has been closed and dispatched from the facility.
<br>-   • **Transfer**: Inventory for the shipment is being moved to a different ship staging location.
<br>-   • **Cancelled**: The shipment has been cancelled with a shipped quantity of zero. |
| Carrier | Identifier for a carrier that delivers inbound inventory to the warehouse or outbound shipments to a customer. This is the identifier that will be displayed to users on the application windows and reports. In the application, a carrier can be associated with a customer, order, inbound shipment, outbound shipment, load, and service levels (such as Ground, Next Day, and Saturday Delivery). |
| Load | Unique identifier for a load. A load is one or more shipments grouped together into one or more stops that are shipped on a single piece of transport equipment. |
| Carton Routing Group | Name of the carton routing group assigned to the shipment. A carton routing group specifies one or more carton types or a number of carton types (such as less than 3 or more than 6) that are grouped together for processing. For example, if certain pack stations in the warehouse operate more efficiently (higher throughput) based on the carton types or number of carton types that pass through it, then you can create a carton routing group that can be used to direct shipments that require certain carton types to specific pack stations. See [Carton routing groups](../../configuration/outbound/picking/pick-cartonization.md). |
| Ship-To Address | Address name for the customer to whom the order must be shipped. |
| Destination | Staging location to which picked inventory for the shipment is sent. |
| Allocated | Percentage of inventory that has been allocated. Additionally, an X of Y value displays the number of eaches that are allocated out of the total number of expected eaches; for example, (50 of 100). The values for this field represent the amount of allocated inventory for the displayed entity (order, shipment, load, or wave). |
| Picked | Percentage of inventory that has been picked. Additionally, an X of Y value displays the number of eaches that are picked out of the total number of expected eaches; for example, (50 of 100). The values for this field represent the amount of picked inventory for the displayed entity (order, shipment, stop, load, or wave). |
| Loaded | Percentage of inventory that has been loaded. Additionally, an X of Y value displays the number of eaches that are loaded out of the total number of expected eaches; for example, (50 of 100). The values for this field represent the amount of loaded inventory for the displayed entity (order, shipment, stop, load, or wave). |
| Wave | Identifier for the wave in which the shipment was planned. The wave name distinguishes one group of pick-type work requests from another, which enables you to track the requests through the application. For example, if you allocate inventory for a single shipment, then all of the picks, replenishments, and cross docks generated for the shipment have the same wave name. |

## Add or Modify Shipment fields

 
| Field | Description |
| --- | --- |
| Shipment ID | Unique identifier for an outbound shipment. A shipment is a group of orders or order lines that are allocated together and shipped to the same location. |
| Route to Address | Name and address of the distributor or organization to which the shipment is initially sent. The route-to address and ship-to address are the same if the shipment does not require an initial stop. |
| Host Client | Unique name or code that identifies the client's host application. |
| Host External ID | Alternate identifier for the route-to address information. This identifier is typically sent from the host, and it is used to reconcile address information with the information contained in the host application. |
| Carrier | Identifier for a carrier that delivers inbound inventory to the warehouse or outbound shipments to a customer. This is the identifier that will be displayed to users on the application windows and reports. In the application, a carrier can be associated with a customer, order, inbound shipment, outbound shipment, load, and service levels (such as Ground, Next Day, and Saturday Delivery). |
| Service Level | Identifier for the service and transit time provided by the carrier that transports an order or shipment to the customer. For example, for a parcel carrier it may be used to indicate services such as express, second-day air, or standard delivery. |
| Carrier Group | Code that identifies a group of carriers, one of which is expected to transport an order or a shipment to the customer. This is the required carrier group unless the order is configured to allow a carrier to be assigned after the order is created. |
| Document Number | Unique number that identifies the paperwork associated with shipping inventory. Document numbers are applied at the outbound load, stop, or shipment level. |
| PRO Number | Progressive routing order (PRO) number assigned to a load, shipment, or stop. A PRO number is assigned as a reference to a shipment for a carrier, and is used by the carrier for most correspondence in relation to tracking the shipment. |
| Booking Number | Number for the advance reservation or confirmation made in the FedEx booking system for a shipment being tendered to FedEx by a shipper. |
| Freight Code | Code that is used in shipping paperwork to determine who takes financial responsibility for the shipment.<br>-   • **FOB Destination**: Seller takes responsibility for the goods while in transit.
<br>-   • **FOB Source**: Buyer takes responsibility for the goods while in transit. |
| Release Remaining Lines | Used for cross docking purposes.<br > If Yes, then the pick work for the order lines in the shipment that are not marked for cross docking is released as usual.<br > If No, then the pick work created for the order lines in the shipment that are not marked for cross docking is held until the inventory that is marked for cross docking is received and allocated. |
| Wave Set | Optional shipment attribute that identifies a group of shipments that you want to include in a particular wave. A wave is a method of combining orders or shipments into logical sets (such as all shipments that are scheduled to ship tomorrow on a particular carrier) to achieve efficient picking for release and fulfillment. |
| Saturday Delivery | If Yes, then the carrier delivers shipments on Saturday, if required.<br > If No, then the carrier does not deliver on Saturday. |
| Delivery Sequence Loading Order | Determines whether orders on the shipment should be loaded in ascending or descending order of the delivery numbers and delivery sequence. For example assume a shipment includes four orders, two with a delivery number of A1 and two with a delivery number of B1. Also assume that the orders for both A1 and B1 have a delivery sequence of 1 and 2. If this field is set to Descending, then the orders are loaded in the following sequence: B1 2, B1 1, A1 2, A1 1. See [Delivery sequence loading](../outbound-planning-concepts.md).<br > **Note**: The delivery sequence loading order defined for a shipment overrides the client value, which overrides the warehouse value. However, if there is no selection (blank) in the Delivery Sequence Loading Order field on a shipment, the value is inherited from the outbound loading settings or, in a 3PL environment, the client configuration.<br>-   • **Ascending**: Operators are directed to load orders on the shipment from the lowest to the highest value of the delivery number and delivery sequence defined on the orders (for example, 0 to 9 or A to Z).
<br>-   • **Descending**: Operators are directed to load orders on the shipment from the highest to the lowest value of the delivery number and delivery sequence defined on the orders (for example, 9 to 0 or Z to A).
<br>-   • **Disabled**: The application does not enforce sequence loading, and orders can be loaded in any sequence.
<br>-   • **No selection (blank)**: The delivery sequence loading order for the shipment is inherited from the outbound loading settings or, in a 3PL environment, the client configuration.
<br > **Note**: To ensure proper loading, all shipments within a stop should have the same delivery sequence loading order. |
| Work Assignment Rule Reference | Identifier for the work assignment rule reference assigned to the shipment, which the application uses to override a base work assignment rule that would normally be used to build work assignments for the shipment.<br > The work assignment rule reference is a value that is not only assigned to a shipment, but it is included as selection criteria in the override rule. When the application executes the override rule, it uses the work assignment rule reference as selection criteria, meaning that only the shipments with the defined reference identifier are selected and included in the work assignment. For information on setting up work assignment rule references, see [Work assignment rule references](../../configuration/outbound/picking/work-assignments.md). |
| Stop | Unique identifier for a stop. A stop is a collection of one or more outbound shipments making up a delivery to a single customer. |
| Currency Code | Unique identifier that is used to represent the currency for the warehouse. For example, the U.S. dollar is represented by the code USA dollar. |
| Movement Zone | Name of a movement zone. A movement zone represents a group of locations to and from which inventory can be moved. For example, storage locations to which inventory can be deposited and processing locations to which inventory is moved for packing are the types of locations that must be assigned to a movement zone for the application to select those locations for putaway or deposit.<br > Source, hop, and destination locations must be assigned to a movement zone so that a movement path can be defined to use each of those locations. |
| Destination Location | Location within the destination zone to which picked inventory for the shipments is to be moved. A location is a uniquely identified position within a zone of the warehouse used to store, stage, or manipulate product. |
| Freight Rate | Charge for transporting goods per unit, such as per pound or per package. |
| Freight Charge | Single-character value that indicates the shipment should have a freight charge at the defined freight rate. |
| Early Ship Date | First day of the outbound shipment range. The shipment range identifies a series of dates on which an outbound order line must be shipped. The application uses both delivery and ship dates to consolidate order lines into shipments, depending on the values defined for order consolidation. |
| Late Ship Date | Last day of the outbound shipment range. To define a single shipment date, enter the first day of the shipment range. The application uses both delivery and ship dates to consolidate order lines into shipments, depending on the values defined for order consolidation. |
| Late Delivery Date | Last day of the delivery range. To define a single delivery date, enter the first day of the delivery range. The application uses both delivery and ship dates to consolidate outbound order lines into outbound shipments, depending on the values defined for order consolidation. |
| AES Number | Unique internal transaction number (ITN) that is generated by the Automated Export System (AES) administered by the United States Census Bureau's Foreign Trade division. An ITN is required for shipping non-exempt shipments out of the United States and is obtained by using one of the AESDirect products. If the shipment is exempt, leave this field blank. |
| AES Type | Value that indicates how you have filed or will file the shipment with the Automated Export System (AES).<br>-   • **Pre-shipment**: You filed before the shipment shipped, which requires an AES internal transaction number (ITN) and an acceptance date.
<br>-   • **Post-shipment**: You will file after the shipment is shipped, but before the shipment arrived at customs, which does not require an AES ITN.
<br>-   • **Server down**: You attempted to file, but the AES server was down. |
| AES Accepted Date | Date and time that the international shipment was accepted by the Automated Export System (AES) and an internal transaction number (ITN) was given. A value is only required if the value for **AES Type** is **Pre-Shipment**. |
| FTSR Number | Foreign Trade Statistics Regulations (FTSR) number (an Automated Export System \[AES\] exemption citation). This is the number of the section or provision in the FTSR where the particular exemption is provided (for example, 30.55h). Warehouse Management passes the information to a parcel application (integrated through Parcel Handler), but does not receive the information from the parcel application. Required for shipments out of the United States that are exempt (the AES Number field is blank).<br > A value is only required if the AES Number field is blank. |

## Shipment Mass Update fields

 
| Field | Description |
| --- | --- |
| Route to Address | Name and address of the distributor or organization to which the shipment is initially sent. The route-to address and ship-to address are the same if the shipment does not require an initial stop. |
| Host Client | Unique name or code that identifies the client's host application. |
| Host External ID | Alternate identifier for the route-to address information. This identifier is typically sent from the host, and it is used to reconcile address information with the information contained in the host application. |
| Carrier | Identifier for a carrier that delivers inbound inventory to the warehouse or outbound shipments to a customer. This is the identifier that will be displayed to users on the application windows and reports. In the application, a carrier can be associated with a customer, order, inbound shipment, outbound shipment, load, and service levels (such as Ground, Next Day, and Saturday Delivery). |
| Service Level | Identifier for the service and transit time provided by the carrier that transports an order or shipment to the customer. For example, for a parcel carrier it may be used to indicate services such as express, second-day air, or standard delivery. |
| Carrier Group | Code that identifies a group of carriers, one of which is expected to transport an order or a shipment to the customer. This is the required carrier group unless the order is configured to allow a carrier to be assigned after the order is created. |
| Document Number | Unique number that identifies the paperwork associated with shipping inventory. Document numbers are applied at the outbound load, stop, or shipment level. |
| Booking Number | Number for the advance reservation or confirmation made in the FedEx booking system for a shipment being tendered to FedEx by a shipper. |
| PRO Number | Progressive routing order (PRO) number assigned to a load, shipment, or stop. A PRO number is assigned as a reference to a shipment for a carrier, and is used by the carrier for most correspondence in relation to tracking the shipment. |
| Freight Code | Code that is used in shipping paperwork to determine who takes financial responsibility for the shipment.<br>-   • **FOB Destination**: Seller takes responsibility for the goods while in transit.
<br>-   • **FOB Source**: Buyer takes responsibility for the goods while in transit. |
| Release Remaining Lines | Used for cross docking purposes.<br > If Yes, then the pick work for the order lines in the shipment that are not marked for cross docking is released as usual.<br > If No, then the pick work created for the order lines in the shipment that are not marked for cross docking is held until the inventory that is marked for cross docking is received and allocated. |
| Wave Set | Optional shipment attribute that identifies a group of shipments that you want to include in a particular wave. A wave is a method of combining orders or shipments into logical sets (such as all shipments that are scheduled to ship tomorrow on a particular carrier) to achieve efficient picking for release and fulfillment. |
| Saturday Delivery | If Yes, then the carrier delivers shipments on Saturday, if required.<br > If No, then the carrier does not deliver on Saturday. |
| Freight Rate | Charge for transporting goods per unit, such as per pound or per package. |
| Freight Charge | Single-character value that indicates the shipment should have a freight charge at the defined freight rate. |
| Early Ship Date | First day of the outbound shipment range. The shipment range identifies a series of dates on which an outbound order line must be shipped. The application uses both delivery and ship dates to consolidate order lines into shipments, depending on the values defined for order consolidation. |
| Early Delivery Date | First day of the delivery range. The delivery range identifies a series of expected delivery dates for the outbound order line. The application uses both delivery and ship dates to consolidate order lines into outbound shipments, depending on the values defined for order consolidation. |
| Late Ship Date | Last day of the outbound shipment range. To define a single shipment date, enter the first day of the shipment range. The application uses both delivery and ship dates to consolidate order lines into shipments, depending on the values defined for order consolidation. |
| Late Delivery Date | Last day of the delivery range. To define a single delivery date, enter the first day of the delivery range. The application uses both delivery and ship dates to consolidate outbound order lines into outbound shipments, depending on the values defined for order consolidation. |
| AES Number | Unique internal transaction number (ITN) that is generated by the Automated Export System (AES) administered by the United States Census Bureau's Foreign Trade division. An ITN is required for shipping non-exempt shipments out of the United States and is obtained by using one of the AESDirect products. If the shipment is exempt, leave this field blank. |
| AES Type | Value that indicates how you have filed or will file the shipment with the Automated Export System (AES).<br>-   • **Pre-shipment**: You filed before the shipment shipped, which requires an AES internal transaction number (ITN) and an acceptance date.
<br>-   • **Post-shipment**: You will file after the shipment is shipped, but before the shipment arrived at customs, which does not require an AES ITN.
<br>-   • **Server down**: You attempted to file, but the AES server was down. |
| AES Accepted Date | Date and time that the international shipment was accepted by the Automated Export System (AES) and an internal transaction number (ITN) was given. A value is only required if the value for **AES Type** is **Pre-Shipment**. |
| FTSR Number | Foreign Trade Statistics Regulations (FTSR) number (an Automated Export System \[AES\] exemption citation). This is the number of the section or provision in the FTSR where the particular exemption is provided (for example, 30.55h). Warehouse Management passes the information to a parcel application (integrated through Parcel Handler), but does not receive the information from the parcel application. Required for shipments out of the United States that are exempt (the AES Number field is blank).<br > A value is only required if the AES Number field is blank. |

## Load Empty Handling Units fields

 
| Field | Description |
| --- | --- |
| Handling Unit Type | Category that classifies a group of handling units (for example, pallets or totes) that share the same characteristics such as size and weight, as well as whether they are serialized, temporary, or considered a container. The application tracks the on-hand quantity of handling units by type and, for serialized handling units, by handling unit identifier. Only handling unit types configured with a **Handling Unit Category** of Inventory can be loaded and unloaded. |
| Handling Unit Status | Current condition of the handling unit, such as active or inactive. This value is only used for reporting purposes. |
| Client | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. |
| Quantity | Quantity of the empty handling unit type to be loaded on the transport equipment for the outbound shipment. |

## Empty Handling Units detail fields

 
| Field | Description |
| --- | --- |
| Handling Unit Type | Category that classifies a group of handling units (for example, pallets, totes, transport equipment, or vehicles) that share the same characteristics such as size and weight, as well as whether they are serialized, temporary, or considered a container. The application tracks the on-hand quantity of handling units by type and, for serialized handling units, by handling unit identifier. |
| Client | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. |
| Handling Unit Status | Current condition of the handling unit, such as active or inactive. This value is only used for reporting purposes. |
| Handling Unit LPN | Unique identifier for a handling unit that is tracked as an individual as well as collectively by handling unit type. You may want to track valuable handling units, such as CHEP pallets, as individuals. Handling units tracked as individuals can be further identified with a serial number. |
| Quantity Loaded/Shipped | Quantity of empty handling units of the specified type that have been loaded or shipped on the outbound shipment. |
| Serial Number | Alphanumeric value that can represent the serial number associated with an individual handling unit. |
| Manufacturer ID | Name of the company that produced the individual handling unit. |
| Model | Alphanumeric model number for the individual handling unit. Manufacturers use model numbers to differentiate similar products. |
| Purchase Date | Date on which the individual handling unit was purchased. |
| Warranty Date | Date on which the warranty of the individual handling unit expires. |
| Parent Handling Unit LPN | Unique identifier for another handling unit on or in which this (child) handling unit resides. The two handling units are tracked together; the location of the child handling unit is the same as that of the parent. You cannot specify another child handling unit as a parent handling unit; however, multiple (child) handling units can be associated with a parent. Only available when the handling unit type category is set to Inventory. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
