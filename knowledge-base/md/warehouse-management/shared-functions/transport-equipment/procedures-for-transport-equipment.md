---
title: "Procedures for transport equipment"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/procedures_for_transport_equipment.htm"
source: "/content/procedures_for_transport_equipment.htm"
toc_path:
  - "Warehouse Management"
  - "Shared functions"
  - "Transport Equipment"
  - "Procedures for transport equipment"
sections:
  - "Add or modify transport equipment"
  - "Add or modify a tractor"
  - "Associate a tractor with transport equipment"
  - "Delete transport equipment"
  - "Delete a tractor"
  - "Check in transport equipment"
  - "Check in a tractor"
  - "Check out a tractor"
  - "Convert storage transport equipment to shipping equipment"
  - "Move transport equipment"
  - "Generate a door or yard location audit"
  - "View transport equipment safety workflow information"
  - "View transport equipment"
  - "View tractors"
  - "Transport Equipment field listings"
  - "Transport Equipment fields"
  - "Transport Equipment Information fields"
  - "Tractors fields"
  - "Tractor Information fields"
  - "Prepare for shipping fields"
  - "Equip/Production Workflow fields"
images:
  - "/content/resources/images/image632381.png"
  - "/content/resources/images/image632381.png"
  - "/content/resources/images/image430108.png"
  - "/content/resources/images/image430109.png"
source_sha1: e0f583219ed7c2a0069f10ccaf55f86616c63a99
---
# Procedures for transport equipment

You can perform the following procedures using the Transport Equipment page, which is accessible from the following modules: **Receiving**, **Shipping**, or **Yard**.

## Add or modify transport equipment

1.  View the Transport Equipment page.
    
    1.  Select one of the following modules: **Receiving**, **Shipping**, or **Yard**.
        
    2.  Select **Transport Equipment**.
        
    
2.  Select **Transport Equipment**.
3.  Perform one of the following tasks:
    -   To add transport equipment, from the **Actions** drop-down list, select **Add Transport Equipment**.
    -   To modify transport equipment, in the grid, select the check box next to the equipment, and then from the **Actions** drop-down list, select **Modify Transport Equipment**.
4.  To assign a tractor to the transport equipment, in the **Tractor** field, enter the tractor; for more information, see [Associate a tractor with transport equipment](#Associate_a_tractor_with_transport_equipment).
5.  Enter information in the [Transport Equipment Information fields](#Transport_Equipment_Information_fields).
6.  Click **Save**.

## Add or modify a tractor

1.  View the Transport Equipment page.
    
    1.  Select one of the following modules: **Receiving**, **Shipping**, or **Yard**.
        
    2.  Select **Transport Equipment**.
        
    
2.  Select **Tractors**.
3.  Perform one of the following tasks:
    -   To add tractor, from the **Actions** drop-down list, select **Add Tractor**.
    -   To modify tractor, in the grid, select the check box next to the tractor, and then from the **Actions** drop-down list, select **Modify Tractor**.
        
        **Note**: You can only modify a tractor in Expected or At Site status.
        
4.  To assign transport equipment to the tractor, in the **Transport Equipment** field, enter the transport equipment identifier.
5.  Enter information in the [Tractor Information fields](#Tractor_Information_fields).
6.  Click **Save**.

## Associate a tractor with transport equipment

You can assign (or unassign) a tractor to transport equipment by modifying the transport equipment or tractor details. You can only assign a tractor to transport equipment if the tractor is currently unassigned and is in a status of Expected or At Site. If the tractor does not exist in the application, you can also add a new tractor to assign with transport equipment.

1.  View the Transport Equipment page.
    
    1.  Select one of the following modules: **Receiving**, **Shipping**, or **Yard**.
        
    2.  Select **Transport Equipment**.
        
    
2.  To assign tractor to transport equipment:
    
    1.  Select **Transport Equipment**.
    2.  Perform one of the following tasks:
        -   To add transport equipment to which you want to assign a tractor, from the **Actions** drop-down list, select **Add Transport Equipment**.
        -   To assign or unassign a tractor from existing transport equipment, in the grid, select the check box next to the equipment, and then from the **Actions** drop-down list, select **Modify Transport Equipment**.
    3.  In the **Tractor** field, perform one of the following tasks:
        -   To assign an existing tractor, enter the tractor.
        -   To add a new tractor to assign:
            1.  Click ![Lookup](../../../../images/resources/images/image632381.png). The Tractor window is displayed.
            2.  Click **Add**.
            3.  Enter information in the [Tractor Information fields](#Tractor_Information_fields).
            4.  Click **Save**, and then click **Select**.
        -   To unassign a tractor, in the **Tractor** field, clear the tractor.
    4.  Click **Save**.
3.  To assign transport equipment to tractor:
    
    1.  Select **Tractor**.
    2.  Perform one of the following tasks:
        -   To add tractor to which you want to assign a transport equipment, from the **Actions** drop-down list, select **Add Tractor**.
        -   To assign or unassign a transport equipment from existing tractor, in the grid, select the check box next to the tractor, and then from the **Actions** drop-down list, select **Modify Tractor**.
    3.  In the **Transport Equipment** field, perform one of the following tasks:
        -   To assign an existing transport equipment, enter the transport equipment.
        -   To add a new transport equipment to assign:
            1.  Click ![Lookup](../../../../images/resources/images/image632381.png). The Transport equipment window is displayed.
            2.  Click **Add**.
            3.  Enter information in the [Transport Equipment Information fields](#Transport_Equipment_Information_fields).
            4.  Click **Save**, and then click **Select**.
        -   To unassign a transport equipment, in the **Transport Equipment** field, clear the transport equipment.
    4.  Click **Save**.

## Delete transport equipment

When you delete transport equipment assigned to a tractor, the tractor is unassigned and the transport equipment is deleted. You cannot delete transport equipment if it is in one of the following statuses: Closed, Loading, Loaded, Receiving, or Suspended.

1.  [View transport equipment](#View_transport_equipment).
2.  In the grid, select the check box next to the transport equipment to delete.
3.  From the **Actions** drop-down list, select **Delete Transport Equipment**. A confirmation message is displayed.
4.  Click **Yes**.

## Delete a tractor

When you delete a tractor assigned to transport equipment, the tractor is unassigned from the equipment, and then the tractor is deleted.

1.  [View tractors](#View_tractors).
2.  In the grid, select the check box next to the tractor to delete.
3.  From the **Actions** drop-down list, select **Delete Tractor**. A confirmation message is displayed.
4.  Click **Yes**.

## Check in transport equipment

You can check in transport equipment that is in an Expected status. If the transport equipment has an assigned tractor, the tractor is also checked in.

1.  Perform one of the following tasks:
    -   To check in equipment with an existing appointment:
        1.  Perform one of the following tasks:
            -   View the Check In page, enter search criteria related to the appointment, and then in the grid, select the appointment.
                
                1.  Select one of the following modules: **Receiving**, **Shipping**, or **Yard**.
                    
                2.  Select **Check In**.
                    
                
                **Note**: You can check in with or without an appointment. If necessary, after viewing the Check In page, click **Check in with appointment**. If this option is not available, you are already in the correct check in mode.
                
            -   View the Appointments page, and then in the appointment time line, click the appointment bar, and then click **Check In**.
                
                1.  Select one of the following modules: **Receiving**, **Shipping**, or **Yard**.
                    
                2.  Select **Appointments**.
                    
                
                **Note**: To change the timeline view for appointments, click ![Earlier time](../../../../images/resources/images/image430108.png) (earlier time) or ![Later time](../../../../images/resources/images/image430109.png) (later time).
                
            -   [View transport equipment](#View_transport_equipment), select the check box next to the equipment to check in, and then from the **Actions** drop-down list, select **Check In Transport Equipment**.
        2.  To change the selected appointment, click **Select a different appointment**, and then select a different appointment.
        3.  To change the appointment time:
            1.  Click **Change appointment time**.
            2.  In the **Start Date** and **End Date** fields, change the date and time of the appointment.
            3.  Click **Save**.
    -   To check in equipment without an appointment, perform one of the following tasks:
        -   View the Check In page, and then click **Check in without appointment**.
            
            1.  Select one of the following modules: **Receiving**, **Shipping**, or **Yard**.
                
            2.  Select **Check In**.
                
            
            **Note**: If you cannot click this option, you are already in the correct check in mode.
            
        -   [View transport equipment](#View_transport_equipment), and select the check box next to the equipment to check in, and then from the **Actions** drop-down list, select **Check In Transport Equipment**.
2.  Perform one of the following tasks:
    -   If transport equipment is already assigned, enter information in the applicable [Transport Equipment Information fields](#Transport_Equipment_Information_fields).
    -   To add transport equipment:
        1.  Click **Add Equipment**.
        2.  Enter information in the [Transport Equipment Information fields](#Transport_Equipment_Information_fields).
        3.  To add and assign tractor to the transport equipment:
            1.  Click **Add Tractor**.
            2.  Enter information in the [Tractor Information fields](#Tractor_Information_fields).
            3.  Click **Save**.
        4.  Click **Save**.
3.  To assign a tractor to the transport equipment, in the **Tractor** field, enter the tractor; for more information, see [Associate a tractor with transport equipment](#Associate_a_tractor_with_transport_equipment).
4.  To add or view equipment notes:
    1.  Click **View notes**.
    2.  In the text box, view or enter notes.
    3.  Click **Save**.
5.  To assign an inbound shipment or outbound load to the transport equipment:
    
    **Note**: This depends on whether you are working with receiving equipment (inbound shipment) or shipping equipment (load).
    
    1.  Under **Inbound Shipment** or **Load**, click **Add**.
    2.  Select the shipment or load to assign.
    3.  Click **Save**. A confirmation message is displayed.
    4.  Click **OK**.
6.  To remove a shipment or load from the transport equipment:
    1.  Select the check box next to the shipment or load.
    2.  Click **Delete**. A confirmation message is displayed.
    3.  Click **OK**.
7.  Perform one of the following tasks:
    -   To check in the equipment to a door location, click **Recommended Doors**, and then select the check box for the door.
    -   To check in the equipment to a yard location, click **Available Yard Locations**, and then select the check box for the location.
8.  Click **Check In**. A confirmation message is displayed.
9.  Click **OK**.

## Check in a tractor

You can check in a tractor that is in an Expected status. If the expected tractor is assigned to transport equipment that is also expected, then you must check in the transport equipment, which automatically checks in the tractor. See [Check in transport equipment](#Check_in_transport_equipment).

1.  [View tractors](#View_tractors).
2.  In the grid, select the check box next to the tractor to check in.
3.  From the **Actions** drop-down list, select **Check In Tractor**. A confirmation message is displayed.
4.  Click **OK**.

## Check out a tractor

You can check out a tractor that is in an At Site status. When you check out a tractor assigned to a transport equipment, the tractor is unassigned, and the corresponding transport equipment remains in the yard without an assigned tractor.

1.  [View tractors](#View_tractors).
2.  In the grid, select the check box next to the tractor to check out.
3.  From the **Actions** drop-down list, select **Check Out Tractor**. A confirmation message is displayed.
4.  Click **OK**.

## Convert storage transport equipment to shipping equipment

You can convert a piece of storage transport equipment to ship the inventory that is currently residing on the equipment. For details, see [Storage transport equipment](../../shipping/shipping-concepts/storage-transport-equipment.md).

**Notes**:

-   You cannot convert storage equipment if a hold that prevents shipping is applied to the inventory on the equipment, or if the inventory is serialized.
-   You can only convert storage transport equipment to shipping if all of the inventory on the equipment is in a status allowed for shipping, as defined by the selected allocation profile.

1.  Perform one of the following:
    -   View the Door Activity page, and then under **Doors**, click the status bar associated with the equipment.
        
        1.  Select one of the following modules: **Receiving**, **Shipping**, or **Yard**.
            
        2.  Select **Door Activity**.
            
        
    -   View the Transport Equipment page, and select the check box next to the transport equipment.
        
        1.  Select one of the following modules: **Receiving**, **Shipping**, or **Yard**.
            
        2.  Select **Transport Equipment**.
            
        
2.  From the **Actions** drop-down list, select **Prepare for Shipping**, and enter information in the [Prepare for shipping fields](#Prepare_for_shipping_fields).
3.  Click **Save**.

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
            
        
    -   [View transport equipment](#View_transport_equipment), and then in the grid, select the check box next to the transport equipment to move.
2.  From the **Actions** drop-down list, select **Move Transport Equipment**.
3.  In the **Select a Location** grid, select the location to which to move the equipment.
4.  Select the move method:
    -   **Add to Work Queue**: Directed work is created in the work queue to move the equipment. If you select this option, then you can also select a specific operator or role to which the work is assigned.
    -   **Move Immediately**: The application is immediately updated to reflect the equipment's new location; no work request is created.
5.  Click **OK**. A confirmation message is displayed.
6.  Click **OK**.

## Generate a door or yard location audit

You can generate a location audit for a door or yard location. The audit only accounts for the transport equipment in a location; no inventory is included in the audit. See [Yard and door audits](../transport-equipment.md).

Perform one of the following tasks:

-   To generate a location audit from the Door Activity page:
    1.  View the Door Activity page.
        
        1.  Select one of the following modules: **Receiving**, **Shipping**, or **Yard**.
            
        2.  Select **Door Activity**.
            
        
    2.  Perform one of the following tasks:
        -   To request an audit on a range of door or yard locations:
            1.  Click **Audit**. The Create Audit window is displayed.
            2.  Enter a **Starting Location** and an **Ending Location** for the audit.
                
                **Note**: To audit a single location, enter the same location in both fields.
                
            3.  Click **OK**. A confirmation message is displayed.
        -   To request an audit for a single location:
            1.  Under **Doors** or **Yard Locations**, click the location. The location details are displayed.
            2.  From the **Actions** drop-down list, select **Generate Location Audit**. A confirmation message is displayed.
    3.  Click **OK**.
-   To generate a location audit from the Transport Equipment page:
    1.  [View transport equipment](#View_transport_equipment).
    2.  In the grid, select the check box next to the equipment in the location for which you want to generate an audit.
    3.  From the **Actions** drop-down list, select **Audit Equipment Location**. A confirmation message is displayed.
    4.  Click **OK**.

## View transport equipment safety workflow information

1.  [View transport equipment](#View_transport_equipment).
2.  In the grid row for the transport equipment for which you want to view safety workflow details, click the value displayed in the **Safety Check Status** column, such as Passed, Pending (Waiting), Failed (Rescheduled), or Unknown. The equipment workflow information is displayed.
    
    **Note**: The **History** tab is displayed by default. Select **In Process** or **Failed** to view the workflows in each processing state, if applicable.
    
3.  View information in the [Equip/Production Workflow fields](#Equip/Production_workflow_fields).

## View transport equipment

1.  View the Transport Equipment page.
    
    1.  Select one of the following modules: **Receiving**, **Shipping**, or **Yard**.
        
    2.  Select **Transport Equipment**.
        
    
2.  Select the **Transport Equipment** tab.
3.  View the information in the [Transport Equipment fields](#Transport_Equipment_fields).

## View tractors

1.  View the Transport Equipment page.
    
    1.  Select one of the following modules: **Receiving**, **Shipping**, or **Yard**.
        
    2.  Select **Transport Equipment**.
        
    
2.  Select **Tractors**.
3.  View the information in the [Tractors fields](#Tractors_fields).

## Transport Equipment field listings

### Transport Equipment fields

 
| Field | Description |
| --- | --- |
| Transport Equipment | Alphanumeric identifier for transport equipment. Transport equipment numbers are not unique, can exist multiple times, and can be associated with various carriers. |
| Tractor | Alphanumeric identifier for a tractor. Vehicles used to haul the transport equipment, such as tractors, rail engines, and ships, are referred to as tractors. Tractor numbers are not unique, can exist multiple times, and can be associated with various carriers. |
| Carrier | Identifier for a carrier that delivers inbound inventory to the warehouse or outbound shipments to a customer. In the application, a carrier can be associated with a customer, order, inbound shipment, outbound shipment, load, and service levels (such as Ground, Next Day, and Saturday Delivery).<br > The carriers associated with the transport equipment and assigned tractor can be different. |
| Safety Check Status | Status of the safety check workflow for the transport equipment, which can be used to determine if the transport equipment is in proper condition for loading or unloading.<br>-   • **Passed**: A safety check workflow has been performed and passed.
<br>-   • **Unknown**: A safety check workflow has not been performed, because it has not been scheduled; indicating that either the safety check exit point has not been reached or there are no safety check workflows enabled for the warehouse.
<br>-   • **Pending (Waiting)**: A safety check workflow has not been performed, but is scheduled to be performed.
<br>-   • **Failed (Rescheduled)**: A safety check workflow has been performed, but failed and has been rescheduled. Work on the transport equipment cannot continue until the workflow is performed again and passes. |
| Equipment Status | Current status of the transport equipment.<br>-   • **Expected**: Receiving, shipping, or storage transport equipment that is expected to arrive at the facility, but has not yet been checked in.
<br>-   • **Checked In**: Receiving or shipping transport equipment that is parked in a yard location and is waiting to be moved to a dock door so that receiving or unloading can begin.
<br>-   • **Open For Receiving**: Receiving transport equipment that is located at a dock door and is ready to be unloaded. Receiving has not yet begun.
<br>-   • **Receiving**: Receiving transport equipment that is parked at a dock door, and operators have started to identify and put the incoming inventory away.
<br>-   • **Open For Shipping**: Shipping transport equipment that is parked at a dock door and is ready to be loaded. Loading has not begun.
<br>-   • **Open For Loading**: Storage transport equipment that has been checked in and parked at a dock door and is ready to be loaded. Loading has not begun.
<br>-   • **Loading**: Shipping or storage transport equipment that is parked at a dock door, and operators have started to load the stops or move inventory onto the equipment. Or, work has been assigned to an RF operator to begin loading.
<br>-   • **Suspended**: Transport equipment has been moved from a dock door to a yard location after receiving or loading was started but not completed. When transport equipment has a Suspended status, receiving and loading work is put on hold. To begin receiving and loading again, the equipment must be moved back to a dock door location.
<br>-   • **Loaded**: Identifies a piece of transport equipment for which all shipments have been loaded. The equipment has not been closed or dispatched.
<br>-   • **Closed**: The transport equipment is loaded and is ready for dispatch (for shipping equipment), receiving has been completed on the transport equipment and the equipment is ready for dispatch (for receiving equipment), or storage equipment that has been loaded.
<br>-   • **Dispatched**: Identifies a piece of shipping or receiving transport equipment for which all loading or receiving has been completed, and that has been closed and departed from your facility.
<br>-   • **Pending From** or **Pending To Location**: Identifies a piece of transport equipment for which work has been created to move the equipment from one dock or yard location to another dock or yard location. |
| Use | Value that describes the purpose of the transport equipment, which can help is assigning an appropriate yard or dock door location. You can designate transport equipment for one of the following uses:<br>-   • Receiving
<br>-   • Shipping
<br>-   • Storage |
| Type | Transport equipment type assigned to the transport equipment. A transport equipment type identifies characteristics that are shared by individual pieces of transport equipment. For example, you can create a type for flatbed trailers, one 48 ft. rear load trailers, and another for equipment that has a liftgate. See [Transport Equipment Type](../../configuration/equipment/equipment/transport-equipment-type.md). |
| Check-In Date | Date on which the transport equipment was checked in. |
| Load | Unique identifier for a load. A load is one or more shipments grouped together into one or more stops that are shipped on a single piece of transport equipment. |
| Inbound Shipment | Unique identifier used for inventory tracking for an inbound shipment of inventory. An inbound shipment is a group of orders that are transported to the warehouse together or received together. When inventory arrives at the warehouse on a piece of transport equipment, an inbound shipment represents the contents of the transport equipment; however, one or more inbound shipments can be associated with a piece of transport equipment. |
| Inbound Status | Application-assigned status that identifies the condition of the inbound shipment as it moves through the receiving process.<br>-   • **Expected**: Inbound shipment is created or downloaded and ready to be checked in for receiving.
<br>-   • **Checked In**: Inbound shipment is checked in to a receiving staging location or, if it is on a piece of transport equipment, checked in to a dock door.
<br>-   • **Receiving**: Receiving from the inbound shipment has been started. The inbound shipment may be located in a receiving staging location or associated with a piece of transport equipment parked at a dock door.
<br>-   • **Suspended**: Receiving from the transport equipment has been started, but because the equipment was moved from the dock door to a yard location, receiving has been suspended. If receiving work exists in the work queue for this shipment, it is also suspended. Receiving work will not be offered to RF operators until the transport equipment is moved back to a dock door location.
<br>-   • **Closed**: Receiving has been completed for the inbound shipment. |
| Location | Current location of the transport equipment in the yard. This location is either a yard location or a door location. A yard location is an outdoor space in which transport equipment can be stored or parked until it is either moved to a dock door or checked out. A door location is an opening on the dock where transport equipment can be parked for the purpose of loading or unloading. |
| Appointment | Application-generated code that identifies a scheduled appointment for a piece of transport equipment. |
| Client | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. |
| Refrigerated | If Yes, the transport equipment can accommodate inventory that requires refrigeration.<br > If No, the transport equipment is not able to accommodate inventory that requires refrigeration. |
| Seal 1 | Identifying number that is displayed on the seal or tag used to close shipping transport equipment. |
| Seal 2 | Identifying number that is displayed on the seal or tag used to close shipping transport equipment. |
| Seal 3 | Identifying number that is displayed on the seal or tag used to close shipping transport equipment. |
| Seal 4 | Identifying number that is displayed on the seal or tag used to close shipping transport equipment. |
| Shipment Location | Name of the logical location in the system where inventory for a shipment is moved as the inventory is loaded on the transport equipment. Only displayed for shipping transport equipment. |
| Equipment Broker | Name of the person or company that owns the transport equipment. |
| Yard Status | User-maintained value that is typically used to track the condition of a piece of transport equipment in the yard. A yard status is a visual cue that has no effect on nor is it changed by any application processes. |
| Driver License | Driver license number for the transport equipment driver. |
| Equipment Weight | Current weight of the transport equipment. If you want to change the measurement unit, click the unit next to the field, and then select a different unit. |
| Driver Name | Name of the driver who delivered or picked up the transport equipment. |
| Close Date | Date and time at which the transport equipment was closed. |
| Pending Date | Date and time the application expects the transport equipment to be dispatched. |
| Dispatch Date | Date and time at which the transport equipment was dispatched. |
| Second Transport Equipment | Identifier for a second piece of transport equipment. For example, if a tractor is pulling two trailers, one is identified as the second piece of transport equipment. |
| Tractor Reference | Optional internal alphanumeric reference number assigned to tractor when it is checked in to the facility. The reference number, if specified, can also be used as search criteria. |
| Equipment Reference | Optional internal alphanumeric reference number assigned to transport equipment when it is checked in to the facility. If you specify a transport equipment reference number, then it is a required entry when performing a yard audit, and is used by the application to validate the transport equipment being audited. The reference number, if specified, can also be used as search criteria. |
| Handling Unit | Unique identifier for a handling unit that is tracked as an individual as well as collectively by handling unit type. All transport equipment handling units are tracked as individuals. Handling units tracked as individuals can be further identified with a serial number. |
| Labor Estimate | Warehouse Labor Management estimated time in seconds to complete work associated with the transport equipment. |
| Appointment Start | Scheduled date and time at which the transport equipment's appointment is to start. |
| Appointment End | Scheduled date and time at which the transport equipment's appointment is to end. |
| Inbound Shipment Location | Name of the location associated with the inbound shipment. If the inbound shipment is associated with transport equipment, this is a dock door or yard location. If the inbound shipment is not associated with transport equipment or has been unloaded from equipment, this is typically a receiving staging location. |
| Auto Generated | Indicates the transport equipment was automatically created by the application with an assigned carrier and stops. A check mark is displayed in this field if the transport equipment was automatically generated. |
| Turn Equipment | Indicates that the receiving transport equipment can be turned around after it is unloaded and then used for shipping. A check mark is displayed in this field if the **Turn Around** field for the transport equipment is set to Yes. |
| Temporary Equipment | Indicates that the transport equipment is associated with a handling unit type that is configured to be temporary. A check mark is displayed in this field if the transport equipment's handling unit type is supposed to be deleted from application once all associated handling units leave the warehouse (are dispatched). |
| Delivery Equipment | Indicates the shipping transport equipment is for delivery. A check mark is displayed in this field if the transport equipment was defined as delivery equipment prior to being checked in (while the equipment status is Expected). |
| Condition | Description of the current condition of the transport equipment. |

### Transport Equipment Information fields

 
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

### Tractors fields

 
| Field | Description |
| --- | --- |
| Tractor | Alphanumeric identifier for a tractor. Vehicles used to haul the transport equipment, such as tractors, rail engines, and ships, are referred to as tractors. Tractor numbers are not unique, can exist multiple times, and can be associated with various carriers. |
| Carrier | Identifier for a carrier that delivers inbound inventory to the warehouse or outbound shipments to a customer. This is the identifier that will be displayed to users on the application windows and reports. In the application, a carrier can be associated with a customer, order, inbound shipment, outbound shipment, load, and service levels (such as Ground, Next Day, and Saturday Delivery). |
| Type | Value that describes the tractor. You can use the tractor type to determine an appropriate yard or door location for the tractor.<br>-   • **Tractors**: Used to haul trailers.
<br>-   • **Rail engines**: Used to haul rail cars.
<br>-   • **Ships**: Used to haul sea containers. |
| Tractor Status | Current status of the tractor. A status can be assigned to standalone tractors or those assigned to shipping, receiving, or storage transport equipment.<br>-   • **Expected**: The tractor is expected to arrive at the facility, or has arrived at the facility, but has not yet been checked in.
<br>-   • **At Site**: The tractor is checked in to the yard.
<br>-   • **Dispatched**: The tractor has been checked out of the yard and is no longer tracked by the application. |
| Reference | Optional internal alphanumeric reference number associated to the tractor when it is checked in to the facility. |
| Driver Name | Name of the driver who delivered or picked up the tractor. |
| Driver License | Driver license number for the tractor driver. |
| Transport Equipment | Alphanumeric identifier for transport equipment. Transport equipment numbers are not unique, can exist multiple times, and can be associated with various carriers. |
| Check-in Date | Date and time at which the tractor was checked in. |
| Dispatch Date | Date and time at which the tractor was dispatched. |
| Location | Current location of the tractor in the yard. This location is either a yard location or a door location. A yard location is an outdoor space in which transport equipment can be stored or parked until it is either moved to a dock door or checked out. A door location is an opening on the dock where transport equipment can be parked for the purpose of loading or unloading. |
| Client | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. |

### Tractor Information fields

 
| Field | Description |
| --- | --- |
| Carrier | Identifier for a carrier that delivers inbound inventory to the warehouse or outbound shipments to a customer. This is the identifier that will be displayed to users on the application windows and reports. In the application, a carrier can be associated with a customer, order, inbound shipment, outbound shipment, load, and service levels (such as Ground, Next Day, and Saturday Delivery). |
| Tractor | Alphanumeric identifier for a tractor. Vehicles used to haul the transport equipment, such as tractors, rail engines, and ships, are referred to as tractors. Tractor numbers are not unique, can exist multiple times, and can be associated with various carriers. |
| Reference | Optional internal alphanumeric reference number associated to the tractor when it is checked in to the facility. |
| Type | Value that describes the tractor. You can use the tractor type to determine an appropriate yard or door location for the tractor.<br>-   • **Tractors**: Used to haul trailers.
<br>-   • **Rail engines**: Used to haul rail cars.
<br>-   • **Ships**: Used to haul sea containers. |
| Driver Name | Name of the driver who delivered or picked up the tractor. |
| Driver License | Driver license number for the tractor driver. |
| Transport Equipment | Alphanumeric identifier for transport equipment. Transport equipment numbers are not unique, can exist multiple times, and can be associated with various carriers. |

### 

### Prepare for shipping fields

 
| Field | Description |
| --- | --- |
| Client | Client for which the inventory is being shipped. |
| Allocation Profile | Default level of quality at which the customer is willing to accept inventory. An allocation profile is a prioritized list of inventory statuses that identifies which statuses can be shipped. It can be applied to both date-controlled and non-date-controlled items. |
| Order Type | Name of an order type. An order type is a category that is used to group orders based on the warehouse processing necessary to fulfill the order. For example, customer orders and distribution orders require different processing by the application, and so an order type can be assigned to categorize each order separately. The application uses order types, for example, to identify orders that are eligible for bulk picking, or to direct orders to specific destination locations. |
| Ship-To Address | Address name for the customer to whom the order must be shipped. |
| Delivery Contact | Name or identifier of the person to be contacted upon delivery of an order. |
| Service Level | Identifier for the service and transit time provided by the carrier that transports an order or shipment to the customer. For example, for a parcel carrier it may be used to indicate services such as express, second-day air, or standard delivery. |

### Equip/Production Workflow fields

 
| Field | Description |
| --- | --- |
| Added | Date and time when the workflow request was initiated by the application. |
| Workflow | Identifier for a workflow process. |
| Exit Point | Point in the warehouse process at which the application executes workflows to which the exit point has been assigned. |
| Required | A check mark in this column indicates that the user is required to complete the workflow before returning to their interrupted work. If the user does not complete the workflow, the application does not allow the user to continue to process the inventory. |
| Equipment Type | Type of equipment on which the workflow is being (or was) performed, such as transport equipment or warehouse equipment. |
| Equipment | Identifier for the equipment on which the workflow is being (or was) performed. |
| Carrier | Identifier for a carrier that delivers inbound inventory to the warehouse or outbound shipments to a customer. This is the identifier that will be displayed to users on the application windows and reports. In the application, a carrier can be associated with a customer, order, inbound shipment, outbound shipment, load, and service levels (such as Ground, Next Day, and Saturday Delivery). |
| Item | Identifier for the item being processed and shipped from the warehouse. |
| User | User that is performing (or performed) the workflow. |
| Device | Identifier for the RF device or workstation on which the workflow is being (or was) performed. |
| Work Order | Identifier for a work order. A work order is an internal order used to find, allocate, and deliver product to a work-in-process area for assembly or disassembly, conversion, kitting, or repackaging. |
| Work Order Revision | Identifier for one instance of a work order that allows you to use a standard work order multiple times. |
| Work Order Line | Unique identifier for a work order line. The number corresponds to the order line's position in the work order. |
| Results | Execution status of the workflow (PASS or FAIL). |
| Instruction | Instruction for the RF operator performing the workflow. |
| Sequence Number | Number that defines the sequence in which the application processes the list of instructions. The application prompts the instructions in sequential order (starting with 1) to the RF operator. |
| Instruction Type | Type of action performed by an RF operator in response to a workflow instruction. |
| Response | Answer provided by the RF operator for the workflow instruction. |
| Prompt | Value provided by an RF operator for the configured prompt variable during the completion of a workflow instruction. |
| Value Entered | Value entered by the user of the specified variable when the workflow has been performed. The field name of the variable is configured to display as a confirmation value (**Confirmation Value** is set to **Using the default "Confirmation Value" variable**) or a description of the specified variable (**Confirmation Value** is set to **Specify a prompt using an existing system variable**).<br > The **Confirmation Value** field is configured for a master workflow. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2023 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
