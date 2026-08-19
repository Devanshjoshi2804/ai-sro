---
title: "Procedures for staging"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/procedures_for_staging.htm"
source: "/content/procedures_for_staging.htm"
toc_path:
  - "Warehouse Management"
  - "Shared functions"
  - "Staging"
  - "Procedures for staging"
sections:
  - "Assign a shipment to an existing load"
  - "Assign an inbound shipment to a staging lane"
  - "Auto receive an inbound shipment"
  - "Change the lane for staged inventory"
  - "Close receiving transport equipment"
  - "Close shipping transport equipment"
  - "Complete an inbound shipment"
  - "Dispatch receiving transport equipment"
  - "Dispatch shipping or storage transport equipment"
  - "Edit appointment details"
  - "Edit transport equipment details"
  - "Modify load details"
  - "Move transport equipment"
  - "Perform a safety check"
  - "Reassign an inbound shipment to a new staging lane"
  - "Reopen closed transport equipment"
  - "Unload an inbound shipment"
  - "View hot inventory"
  - "Staging field listings"
  - "Close Shipping Equipment fields"
  - "Appointment Details fields"
  - "Recurrence Pattern fields"
  - "Modify Load Details fields"
  - "Equipment Information and Details fields"
images: []
source_sha1: aa60d6cff4826cf03c1ee8738459b04d9563c188
---
# Procedures for staging

You can perform these procedures using the Staging page, which is accessible from the following modules: **Receiving** or **Shipping**.

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

## Assign an inbound shipment to a staging lane

You can assign an inbound shipment that is not associated with transport equipment to a staging lane so that operators can receive inventory from the shipment. Inbound shipments must be in an Expected status to be assigned to a staging lane. When you assign an inbound shipment to a lane, the shipment's status is updated to Checked In.

1.  Perform one of the following tasks:
    -   Select **Receiving > Inbound Shipments**, and then select the check box next to one or more inbound shipments; and then from the **Actions** drop-down list, select **Assign to Staging Lane**.
    -   View the Staging page, and then click **Assign Inbound Shipment**.
        
        1.  Select one of the following modules: **Receiving** or **Shipping**.
            
        2.  Select **Staging**.
            
        
    -   View the Check In page, and then click **Assign Inbound Shipment to Staging Lane**.
        
        1.  Select one of the following modules: **Receiving**, **Shipping**, or **Yard**.
            
        2.  Select **Check In**.
            
        
2.  To add an inbound shipment to assign:
    
    **Note**: You can add multiple inbound shipments and assign them to the same staging lane.
    
    1.  Click **Add**. The Unassigned Inbound Shipments page is displayed.
    2.  In the grid, select the shipment to assign.
    3.  Click **Assign**.
3.  Under **Lanes**, select the row for the staging lane to which to assign the inbound shipments.
    
    **Note**: The application displays receiving lanes that are not in error, that do not have a resource code assigned, and that have available capacity.
    
4.  Click **Save**. A confirmation message is displayed.

## Auto receive an inbound shipment

To perform auto receiving, the inbound shipment must be associated with an ASN from a trusted supplier enabled for auto receiving. See [ASN auto receiving from trusted suppliers](../../receiving/receiving-concepts.md).

1.  Perform one of the following tasks:
    -   Select **Receiving > Inbound Shipments**, and then in the grid, select a shipment.
    -   Select **Receiving > Staging**, and then under Doors, select the status bar for an inbound shipment.
    -   Select **Receiving > Door Activity**, and then under Doors, select the status bar for an inbound shipment.
2.  From the **Actions** drop-down list, select **Auto Receive**.
3.  Under **Empty Locations**, select the receiving staging lane to which the application systematically moves the LPNs on the inbound shipment during auto receiving.
4.  Click **Next** or **Move Equipment**.
5.  Under **Move Equipment**, perform one of the following tasks:
    
    **Note**: The transport equipment is not moved until receiving is complete. Additionally, if there are errors during auto receiving, then the transport equipment is not moved or dispatched.
    
    -   To move the equipment to a new door or yard location:
        1.  Select **Move to New Location**, and then under **Available Locations**, select a new location.
        2.  Select the move method:
            -   **Add to Work Queue**: Directed work is created in the work queue to move the equipment. If you select this option, then you can also select a specific operator or role to which the work is assigned.
                
            -   **Move Immediately**: The application is immediately updated to reflect the equipment's new location; no work request is created.
                
    -   To leave the equipment at the dock door, select **Leave at door**.
    -   To dispatch the transport equipment, select **Dispatch equipment**.
6.  Under **Complete Receiving**, select whether to close the inbound shipment:
    -   **Yes**: The inbound shipment is closed and the transport equipment is closed. When you complete receiving, the application removes existing receiving work and pre-identification inventory details created from an ASN from the application. If inbound shipment information has not yet been communicated to the host, it is sent at this time.
        
        **Note**: It is recommended that all received inventory be staged before the transport equipment or inbound shipment is closed. If inventory is received, but not staged, it is noted as a discrepancy during the completion process.
        
    -   **No**: The inbound shipment and transport equipment remain open.
7.  Click **Next** or **Review**.
8.  When you are finished reviewing the auto receiving details, click **Finish**. The auto receiving progress bar is displayed, and then a confirmation message is displayed when processing is complete.
9.  Click **OK**.
    
    **Note**: If the application failed to auto receive LPNs on the inbound shipment, view the details of the shipment, and then click the auto receive status Completed with Error to view the details of the error.
    

## Change the lane for staged inventory

Use this procedure to move a staged shipment or mixed shipment of an outbound order from one staging lane to another. When shipping on a schedule, the transport equipment may get filled up. If that occurs, all remaining shipments or partial shipments need to be moved to another piece of equipment or to a pack and hold location to wait for another piece of transport equipment.

**IMPORTANT**: If inventory for a shipment is located on an RF device, then the application will not let you change the staging location for that shipment.

**Notes**:

-   If you change the lane for a mixed-shipment LPN and send the move to the work queue, the application will create directed work (based on the outbound staging configuration) to change the lane only if it is being transferred to an outbound staging lane. The application does not support changing the receiving staging or production staging lane for mixed-shipment LPNs through directed work. If a staging lane is used for receiving and shipping, then the application allows the directed lane change only if the mixed-shipment LPN is associated with an outbound shipment.
    
-   If you use an external pallet control system, changing the staging lane for a mixed-shipment LPN is not supported.
-   The application creates directed work for the staging lane transfer based on the action and operation selected in the outbound staging configuration. See [Configure outbound staging](../../configuration/outbound/shipping/outbound-staging.md).
    

1.  View the Staging page.
    
    1.  Select one of the following modules: **Receiving** or **Shipping**.
        
    2.  Select **Staging**.
        
    
2.  Under **Lanes**, click the status bar associated with the staged inventory for which you want to change the lane. The display shows information related to the equipment, appointment, and inventory associated with the status bar.
3.  From the **Actions** drop-down list, select **Change Lane**.
4.  In the **Shipments** grid, select the check box next to the shipments to move.
5.  Under **Available Lanes**, click **Find Lanes**. When the results are displayed, select the new lane.
6.  Click **Save**.
7.  Perform one of the following tasks:
    -   When a message is displayed confirming the move, click **OK**.
    -   To resolve issues with partially staged shipments:
        1.  On the **Lane Changes** window, select one of the following options:
            -   **Redirect remaining LPNs**: Indicates that the remaining LPNs not already in the staging lane are redirected to the new staging lane. LPNs currently in the original lane are not moved.
            -   **Move staged and redirect remaining**: Indicates that the LPNs currently staged in the original lane are moved to the new staging lane. This option is available when all the expected LPNs for a shipment are staged.
                
                **Note**: If the entire shipment has not yet been staged (for example, if additional LPNs are still being picked), this option is **Move staged and redirect remaining**. This indicates that the application moves any LPNs currently in the original staging lane to the new lane, and also redirects any in-process LPNs to the new lane.
                
                -   **Add to work queue**: Indicates that directed work is created for an operator to complete the staging lane change.
                -   **Move Immediately**: Indicates that the application is immediately updated with the LPN's new staging lane, and no work is created. Typically, you select this option if the physical move has already taken place.
        2.  Click **Save**.

## Close receiving transport equipment

1.  Perform one of the following tasks:
    -   View the Staging page, and then under **Doors**, click the receiving status bar associated with the equipment.
        
        1.  Select one of the following modules: **Receiving** or **Shipping**.
            
        2.  Select **Staging**.
            
        
    -   View the Door Activity page, and then under **Doors**, click the receiving status bar associated with the equipment.
        
        1.  Select one of the following modules: **Receiving**, **Shipping**, or **Yard**.
            
        2.  Select **Door Activity**.
            
        
2.  From the **Actions** drop-down list, perform one of the following tasks:
    -   To close the transport equipment and leave it at the door, select **Close Equipment > Leave at Door**.
    -   To turn around the receiving transport equipment to shipping equipment:
        1.  Select **Close Equipment > Turnaround**.
        2.  Enter information in the following fields:
            
            | Field | Description |
            | --- | --- |
            | Carrier | Identifier for a carrier that delivers inbound inventory to the warehouse or outbound shipments to a customer. This is the identifier that will be displayed to users on the application windows and reports. In the application, a carrier can be associated with a customer, order, inbound shipment, outbound shipment, load, and service levels (such as Ground, Next Day, and Saturday Delivery). |
            | To | Location to which the application moves the transport equipment.<br>-   •
                
                **Leave Equipment at current Location**
                
                <br>
                
                Indicates that the transport equipment remains at its current door location.
                
                <br>
            <br>-   •
                
                **Move Equipment to another Location**
                
                <br>
                
                Indicates that the transport equipment will be moved to a new door location. If you select this option, then you must also select a location from the **Select Location** drop-down list.
                
                <br> |
            | Move Equipment Method | Method by which the transport equipment is moved to the location.<br>-   •
                
                **Send work to Work Queue for RF operator**
                
                <br>
                
                Indicates that directed work is created for an operator to move the transport equipment to a new location.
                
                <br>
            <br>-   •
                
                **System moves equipment immediately**
                
                <br>
                
                Indicates the transport equipment's location is immediately updated in the application.
                
                <br> |
            
    -   To dispatch the transport equipment:
        1.  Select **Close Equipment > ** **Dispatch**.
        2.  Enter information in the following fields:
            
            | Field | Description |
            | --- | --- |
            | Tractor Number | Number of the tractor that is hauling the transport equipment. |
            | Driver | Name of the driver who delivered or picked up the transport equipment. |
            | Driver License | Driver license number for the transport equipment driver. |
            
        3.  Click **Dispatch**.
3.  Click **OK**.

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

## Complete an inbound shipment

Use this procedure to complete an inbound shipment. When you complete an inbound shipment, the transport equipment is also closed if there are no additional open inbound shipments on the equipment.

1.  Select **Receiving**.
2.  Perform one of the following tasks:
    -   To select a shipment to complete by its associated staging lane:
        1.  Select **Staging**.
        2.  Under **Lanes**, click the status bar of the inbound shipment to complete.
        3.  From the **Actions** drop-down list, select **Review and** **Complete Receiving**.
    -   To select a shipment to complete by the shipment identifier:
        1.  Select **Inbound Shipments**.
        2.  In the grid, click the shipment to complete. The inbound shipment details are displayed.
        3.  Click **OSD/Complete**.
        4.  Click **Complete Inbound Shipment**.
3.  If a prompt is displayed asking if you want to close all of the shipments on the transport equipment, perform one of the following tasks:
    -   To complete all of the inbound shipments and close the transport equipment, click **Yes**.
        
        **Note**: If you close inbound shipments that have not been received, then the application displays a list of the receiving discrepancies. If you are authorized to complete receiving with discrepancies, you can choose to do so without resolving the discrepancies. However, if you close an inbound shipment before all the incoming inventory is received, you must reopen the transport equipment or inbound shipment to receive the remaining inventory. If you are not authorized to close inbound shipments with discrepancies, then the inbound shipments remain in their current status, and inventory information is not sent to the host until all inbound shipments on the transport equipment are received.
        
    -   To complete only the selected inbound shipment and keep the transport equipment open, click **No**.
        
        **Note**: Inbound shipment inventory information is sent to the host immediately after a received shipment is closed. It is recommended that all received inventory be stored before the inbound shipment is closed. If inventory is received but not stored, it is noted as a discrepancy during the completion process.
        
4.  If all of the inbound shipments on the transport equipment are closed, then on the confirmation window, perform one of the following tasks:
    -   To leave the closed equipment at the dock door, select **Leave equipment at door**, and then click **OK**.
    -   To dispatch the transport equipment, select **Dispatch equipment**, and then click **OK**.
    -   To turn around the receiving transport equipment to shipping equipment:
        1.  Select **Turnaround**.
        2.  Click **OK**.
        3.  Enter information in the following fields:
            
            | Field | Description |
            | --- | --- |
            | Carrier | Identifier for a carrier that delivers inbound inventory to the warehouse or outbound shipments to a customer. This is the identifier that will be displayed to users on the application windows and reports. In the application, a carrier can be associated with a customer, order, inbound shipment, outbound shipment, load, and service levels (such as Ground, Next Day, and Saturday Delivery). |
            | To | Location to which the application moves the transport equipment.<br>-   •
                
                **Leave Equipment at current Location**
                
                <br>
                
                Indicates that the transport equipment remains at its current door location.
                
                <br>
            <br>-   •
                
                **Move Equipment to another Location**
                
                <br>
                
                Indicates that the transport equipment will be moved to a new door location. If you select this option, then you must also select a location from the **Select Location** drop-down list.
                
                <br> |
            | Move Equipment Method | Method by which the transport equipment is moved to the location.<br>-   •
                
                **Send work to Work Queue for RF operator**
                
                <br>
                
                Indicates that directed work is created for an operator to move the transport equipment to a new location.
                
                <br>
            <br>-   •
                
                **System moves equipment immediately**
                
                <br>
                
                Indicates the transport equipment's location is immediately updated in the application.
                
                <br> |
            
        4.  Click **OK**.

## Dispatch receiving transport equipment

You can also dispatch shipping and receiving equipment on the [Check Out](../../yard/check-out.md) page in the Yard module, and specifically for [shipping or storage equipment](#Dispatch_shipping_or_storage_transport_equipment) on other application pages.

**Note**: If the **Tractor** field in the outbound loading configuration is set to Yes, then you must first have a tractor assigned to the transport equipment before the equipment can be dispatched. See [Associate a tractor with transport equipment](../transport-equipment/procedures-for-transport-equipment.md).

1.  Perform one of the following tasks:
    
    **Note**: In addition to the following tasks, on the Staging or Door Activity page, you can also click the **Dispatch** tag associated with the equipment, and then click **Dispatch Equipment**.
    
    -   View the Staging page, and then under **Doors**, click the receiving status bar associated with the equipment.
        
        1.  Select one of the following modules: **Receiving** or **Shipping**.
            
        2.  Select **Staging**.
            
        
    -   View the Door Activity page, and then under **Doors**, click the receiving status bar associated with the equipment.
        
        1.  Select one of the following modules: **Receiving**, **Shipping**, or **Yard**.
            
        2.  Select **Door Activity**.
            
        
2.  From the **Actions** drop-down list, select **Dispatch Equipment**. The Dispatch Equipment window is displayed.
    
    **Note**: If the equipment has not been closed, select **Close Equipment > Dispatch**.
    
3.  Enter information in the following fields:
    
     
    | Field | Description |
    | --- | --- |
    | Tractor Number | Number of the tractor that is hauling the transport equipment. |
    | Driver | Name of the driver who delivered or picked up the transport equipment. |
    | Driver License | Driver license number for the transport equipment driver. |
    
4.  Click **Dispatch**. A confirmation message is displayed.
5.  Click **OK**.

## Dispatch shipping or storage transport equipment

You can also dispatch transport equipment on the [Check Out](../../yard/check-out.md) page in the Yard module, and specifically for [receiving equipment](#Dispatch_receiving_transport_equipment) on other application pages.

**Note**: If the **Tractor** field in the outbound loading configuration is set to Yes, then you must first have a tractor assigned to the transport equipment before the equipment can be dispatched. See [Associate a tractor with transport equipment](../transport-equipment/procedures-for-transport-equipment.md).

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

## Edit appointment details

1.  Perform one of the following tasks:
    -   View the Staging page.
        
        1.  Select one of the following modules: **Receiving** or **Shipping**.
            
        2.  Select **Staging**.
            
        
    -   View the Door Activity page.
        
        1.  Select one of the following modules: **Receiving**, **Shipping**, or **Yard**.
            
        2.  Select **Door Activity**.
            
        
2.  Click the status bar with the appointment you to edit. The display shows information related to the equipment, appointment, and inventory associated with the status bar or appointment bar.
3.  Under **APPOINTMENT**, click the appointment time.
    
    **Note**: If the equipment does not have an existing appointment, you can click **Add Appointment** to define new appointment details.
    
4.  Enter information in the [Appointment Details fields](#Appointment_details_fields).
5.  If you add or edit a recurrence pattern, enter information in the [Recurrence Pattern fields](#Recurrence_Pattern_fields).
6.  To edit equipment details associated with the appointment, click **Equipment Details**, and then enter information in the [Equipment Details fields](#Transport_Equipment_Information_fields).
7.  To assign or remove an inbound shipment or outbound load for the transport equipment:
    1.  Click **Load Details** or **Inbound Shipment Details**.
        
        **Note**: This option depends on whether you are working with a receiving appointment (Inbound Shipment Details) or shipping appointment (Load Details).
        
    2.  To assign a shipment or load:
        1.  Click **Add**.
        2.  Select the check box next to the shipment or load.
        3.  Click **Select**.
    3.  To remove a shipment or load, select the check box, and then click **Delete**.
8.  Click **Save**.

## Edit transport equipment details

1.  Perform one of the following tasks:
    -   View the Staging page.
        
        1.  Select one of the following modules: **Receiving** or **Shipping**.
            
        2.  Select **Staging**.
            
        
    -   View the Door Activity page.
        
        1.  Select one of the following modules: **Receiving**, **Shipping**, or **Yard**.
            
        2.  Select **Door Activity**.
            
        
2.  Click the status bar associated with the transport equipment to edit. The display shows information related to the equipment, appointment, and inventory associated with the status bar or appointment bar.
3.  Under **Transport Equipment**, click the identifier for the equipment.
4.  Enter information in the [Equipment Information fields](#Transport_Equipment_Information_fields).
5.  Click **Save**.

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

## Move transport equipment

Use this procedure to move checked-in transport equipment from a dock door or yard location to another dock door or yard location.

**Note**: A tractor associated to transport equipment is assumed to be in the same location as the transport equipment.

1.  Perform one of the following tasks:
    -   View the Staging page, and then click the status bar associated with the equipment to move.
        
        1.  Select one of the following modules: **Receiving** or **Shipping**.
            
        2.  Select **Staging**.
            
        
    -   View the Door Activity page, and then click the status bar associated with the equipment to move.
        
        1.  Select one of the following modules: **Receiving**, **Shipping**, or **Yard**.
            
        2.  Select **Door Activity**.
            
        
    -   [View transport equipment](../transport-equipment/procedures-for-transport-equipment.md), and then in the grid, select the check box next to the transport equipment to move.
2.  From the **Actions** drop-down list, select **Move Transport Equipment**.
3.  In the **Select a Location** grid, select the location to which to move the equipment.
4.  Select the move method:
    -   **Add to Work Queue**: Directed work is created in the work queue to move the equipment. If you select this option, then you can also select a specific operator or role to which the work is assigned.
    -   **Move Immediately**: The application is immediately updated to reflect the equipment's new location; no work request is created.
5.  Click **OK**. A confirmation message is displayed.
6.  Click **OK**.

## Perform a safety check

1.  Perform one of the following tasks:
    
    **Note**: In addition to the following tasks, on the Staging, Door Activity, and Yard Activity pages, you can also click the **Safety** tag associated with the transport equipment, and then click **Perform Safety Check**.
    
    -   View the Staging page.
        
        1.  Select one of the following modules: **Receiving** or **Shipping**.
            
        2.  Select **Staging**.
            
        
    -   View the Door Activity page.
        
        1.  Select one of the following modules: **Receiving**, **Shipping**, or **Yard**.
            
        2.  Select **Door Activity**.
            
        
2.  Click the status bar associated with the transport equipment for which you want to perform a safety check.
3.  From the **Actions** drop-down list, select **Safety Check**.
4.  For each safety check question, perform one of the following tasks:
    -   If the transport equipment satisfies the requirement of the safety check question, select **Pass**.
    -   If the transport equipment does not satisfy the requirement of the safety check question, select **Fail**.
5.  Click **Save**.
    
    **Note**: You can view the results of a safety check on the Workflows page (Equipment tab).
    

## Reassign an inbound shipment to a new staging lane

Use this procedure to move an inbound shipment that is not associated with transport equipment from one receiving staging lane to another. You can reassign an inbound shipment only if receiving has not started.

1.  View the Staging page.
    
    1.  Select one of the following modules: **Receiving** or **Shipping**.
        
    2.  Select **Staging**.
        
    
2.  Under **Lanes**, click the status bar of the inbound shipment to reassign.
3.  From the **Actions** drop-down list, select **Reassign Inbound Shipment**.
4.  On the Reassign Inbound Shipment window, under **Available Staging Lanes**, select the lane to which the inbound shipment should be reassigned.
    
    **Note**: The application displays receiving lanes (or lanes configured for both shipping and receiving staging) that are not in error, that do not have a resource code assigned, and that have available capacity.
    
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

## Unload an inbound shipment

Use this procedure to unload all of the inventory from a piece of transport equipment before or during receiving. After inventory is unloaded, you still must receive the inventory into the warehouse. See [Receive inventory](../../receiving/inbound-shipments/procedures-for-inbound-shipments.md).

1.  Perform one of the following tasks:
    -   View the Staging page.
        
        1.  Select one of the following modules: **Receiving** or **Shipping**.
            
        2.  Select **Staging**.
            
        
    -   View the Door Activity page.
        
        1.  Select one of the following modules: **Receiving**, **Shipping**, or **Yard**.
            
        2.  Select **Door Activity**.
            
        
2.  Under **Doors**, click the status bar of the transport equipment that contains the shipment to unload.
3.  From the **Actions** drop-down list, select **Unload All**.
4.  Under **Empty Locations**, select the lane in which to unload the shipment.
5.  Click **Next**.
6.  Under **Move Equipment**, perform one of the following tasks:
    -   To turn around the receiving transport equipment to shipping equipment:
        1.  Select **Turn Around for Shipping**.
        2.  Select one of the following move options:
            -   **Move: Immediately**: Indicates the transport equipment's location is immediately updated in the application. If you select this option, then under **Available Locations**, select a new location.
            -   **Move: Work Queue**: Indicates that directed work is created for an operator to move the transport equipment to a new location. If you select this option, then under **Available Locations**, select a new location. You can also assign a specific user or role to perform the work.
            -   **Leave in Current Location**: Indicates that the transport equipment remains checked in at its current door location.
    -   To move the equipment to a new door or yard location, select **Move to New Location**, and then under **Available Locations**, select a new location.
    -   To leave the closed equipment at the dock door, select **Leave at door**.
    -   To dispatch the transport equipment, select **Dispatch equipment**.
7.  Click **Next**. The Review page is displayed showing the summary of the unloading activity.
8.  Click **Finish**.

## View hot inventory

Hot inventory is inventory that is on an inbound shipment that is scheduled to arrive to the warehouse before an outbound order that requires the inventory is scheduled to leave. Sometimes there is not enough inventory in the warehouse to fill a shippable outbound order and that order is allocated short; inbound inventory that can fulfill the short allocation is considered hot.

You can also [View hot transport equipment](../../outbound-planner/outbound/procedures-for-shorts-and-replenishments.md).

1.  Perform one of the following tasks:
    -   View the Staging page.
        
        1.  Select one of the following modules: **Receiving** or **Shipping**.
            
        2.  Select **Staging**.
            
        
    -   View the Door Activity page.
        
        1.  Select one of the following modules: **Receiving**, **Shipping**, or **Yard**.
            
        2.  Select **Door Activity**.
            
        
2.  From the **Quick Filters** drop-down list, select **Hot**.
3.  Under a receiving status bar, click the **Hot** tag. The hot item, hot quantity, and location of the inventory is displayed.
4.  To view the receiving progress of hot inventory:
    1.  Click the receiving status bar associated with the hot inventory.
    2.  Select **Hot Items**, and view information in the following fields:
        
        | Field | Description |
        | --- | --- |
        | Item | Identifier for the hot item that is needed to fulfill an outbound order. |
        | For Order | Unique number that identifies the outbound order that was allocated short and for which the hot inventory is needed. |
        | Hot | Quantity of the hot item that is needed to fulfill the outbound order. |
        | Early Ship Date | First day of the outbound shipment range defined on the short order line. |
        | Progress | Percentage of hot inventory that has been picked. Additionally, an X of Y value displays the number of eaches that are picked out of the total number of expected eaches; for example, (50 of 100). |
        

## Staging field listings

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

### Appointment Details fields

 
| Field | Description |
| --- | --- |
| From | Start time of the appointment. This field is populated with the time you selected in the grid; however, you can use the drop-down list to change the time. This field is displayed on the Add Appointment window. |
| To | End time of the appointment. This field is populated with the time you selected in the grid; however, you can use the drop-down list to change the time. This field is displayed on the Add Appointment window. |
| Appointment Start | Start date and time of the appointment. This fields is populated with the date and time you selected in the grid; however, you can use the calendar and drop-down list to change the start date and time. |
| Appointment End | End date and time of the appointment. This field is populated with the date and time you selected in the grid; however, you can use the calendar and drop-down list to change the end date and time. |
| Carrier | Identifier for a carrier that delivers inbound inventory to the warehouse or outbound shipments to a customer. This is the identifier that will be displayed to users on the application windows and reports. In the application, a carrier can be associated with a customer, order, inbound shipment, outbound shipment, load, and service levels (such as Ground, Next Day, and Saturday Delivery). |
| Dock Door | Dock door at which the transport equipment is or will be checked in. |
| Equipment | Alphanumeric identifier for transport equipment. Transport equipment numbers are not unique, can exist multiple times, and can be associated with various carriers. |
| Check in Immediately | Indicates that the transport equipment is immediately checked in. The drop-down list that is displayed shows dock door and yard locations at which the transport equipment can be checked in.<br > This check box is only available if transport equipment is added to the appointment and default Equipment Status is not Checked In. |
| Recurrence Pattern | Indicates that this is a recurring appointment based on the pattern details. |
| Appointment Location | Code that identifies the dock set or dock door location at which that appointment occurs. Only dock sets that are available during the defined date and time are available for selection. |
| Carrier Phone Number | Phone number at which the carrier can be contacted (typically, a cell phone number). |
| Requested Equipment Type | Transport equipment type that is being requested for the appointment by Transportation Manager (TM). When TM sends appointment information to Warehouse Management, the requested equipment type may be included. For example, if the load associated with an appointment sent from TM contains perishable inventory, the requested equipment type for the appointment may be for refrigerated equipment.<br > If the requested equipment type exists in WM, then the transport equipment type description is displayed. If the equipment type does not exist in WM, the code value received from TM is displayed; you can accept the TM code value or add the transport equipment type in WM configuration to display a description. WM does not validate that the assigned and requested equipment types are the same.<br > **Note**: If you change the value of this field, no information is sent back to TM. It is for WM reference purposes only. |
| Appointment Notes | Text that further explains any additional appointment information. |

### Recurrence Pattern fields

 
| Field | Description |
| --- | --- |
| Repeat | Frequency of the appointment.<br>-   • **Daily**: Sets the appointment's recurrence schedule in day intervals.
<br>-   • **Weekly**: Sets the appointment's recurrence schedule in week intervals.
<br>-   • **Monthly**: Sets the appointment's recurrence schedule in month intervals.
<br>-   • **Yearly**: Sets the appointment's recurrence schedule in year intervals. |
| Repeat Every | Number of days, weeks, months, or years the appointment will be created. |
| Repeat On | Indicates the days of the week on which the appointment will be created. |
| Starts On | Date that the appointment recurrence schedule goes into effect. |
| Ends: After | Indicates that the appointment recurrence schedule will expire after creating the specified number of appointments. For example, if you set this value to 20, after the twentieth appointment is created the application will stop creating this appointment until the recurrence information is reset. |
| Ends: On | Expiration date of the appointment recurrence schedule. |
| Summary | Displays the full recurrence pattern selected. |

### Modify Load Details fields

 
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

### Equipment Information and Details fields

 
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

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2023 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
