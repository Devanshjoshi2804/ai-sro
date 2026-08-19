---
title: "Procedures for check in"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/procedures_for_check_in.htm"
source: "/content/procedures_for_check_in.htm"
toc_path:
  - "Warehouse Management"
  - "Shared functions"
  - "Check In"
  - "Procedures for check in"
sections:
  - "Check in transport equipment"
  - "Add or modify an appointment"
  - "Assign an inbound shipment to a staging lane"
  - "Appointment Details fields"
  - "Recurrence Pattern fields"
  - "Transport Equipment Information and Equipment Details fields"
  - "Tractor Information fields"
images:
  - "/content/resources/images/image430108.png"
  - "/content/resources/images/image430109.png"
  - "/content/resources/images/image430108.png"
  - "/content/resources/images/image430109.png"
source_sha1: aed086c6617c13f6c494aa070bebec06b3dc07b9
---
# Procedures for check in

You can perform these procedures using the Check In page, which is accessible from the following modules: **Receiving**, **Shipping,** or **Yard**.

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
                
            -   [View transport equipment](../transport-equipment/procedures-for-transport-equipment.md), select the check box next to the equipment to check in, and then from the **Actions** drop-down list, select **Check In Transport Equipment**.
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
            
        -   [View transport equipment](../transport-equipment/procedures-for-transport-equipment.md), and select the check box next to the equipment to check in, and then from the **Actions** drop-down list, select **Check In Transport Equipment**.
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
3.  To assign a tractor to the transport equipment, in the **Tractor** field, enter the tractor; for more information, see [Associate a tractor with transport equipment](../transport-equipment/procedures-for-transport-equipment.md).
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

## Add or modify an appointment

1.  Perform one of the following tasks:
    -   To add or modify an appointment using the Appointments page:
        1.  Perform one of the following tasks:
            -   View the Appointments page.
                
                1.  Select one of the following modules: **Receiving**, **Shipping**, or **Yard**.
                    
                2.  Select **Appointments**.
                    
                
            -   View the Check In page, and then click **Add Appointment**.
                
                1.  Select one of the following modules: **Receiving**, **Shipping**, or **Yard**.
                    
                2.  Select **Check In**.
                    
                
                **Note**: If **Add appointment** is not available, first click **Check in with appointment**.
                
        2.  To change the display, select one of the following options:
            -   **Dock Sets**: Displays a list of dock sets that can be expanded to display individual doors in each set.
            -   **Doors**: Displays a list of individual doors.
            -   **All**: Displays a list of all doors and dock sets in the warehouse.
        3.  To search for an available time slot or an existing appointment, in the **Search** fields, enter the criteria, and then click **Go**.
            
            **Note**: To change the timeline view for appointments, click ![Earlier time](../../../../images/resources/images/image430108.png) (earlier time) or ![Later time](../../../../images/resources/images/image430109.png) (later time).
            
        4.  To add a new appointment, perform one of the following tasks:
            -   In the row for the door or dock set, click and drag from the appointment's start time to the end time of the appointment.
                
                **Note**: The Add Appointment window contains the required fields to create an appointment. Click **Additional Information** to enter additional details. Otherwise, click **Save**.
                
            -   Click **Add Appointment to Dock Set** or **Add Appointment to Door**.
                
                **Note**: These options are only available if you searched for a specific date, time, and duration.
                
        5.  To modify an appointment, click the appointment bar, and then click **Edit**.
    -   To add or modify an appointment using the status bar associated to transport equipment:
        1.  Perform one of the following tasks:
            -   View the Staging page.
                
                1.  Select one of the following modules: **Receiving** or **Shipping**.
                    
                2.  Select **Staging**.
                    
                
            -   View the Door Activity page.
                
                1.  Select one of the following modules: **Receiving**, **Shipping**, or **Yard**.
                    
                2.  Select **Door Activity**.
                    
                
        2.  Under **Doors**, **Lanes**, or **Yard Locations**, click the status bar associated with the transport equipment.
        3.  Under **APPOINTMENT**, perform one of the following tasks:
            -   To add an appointment, click **Add Appointment**.
            -   To modify an appointment, click the appointment time.
2.  Enter information in the [Appointment Details fields](#Appointment_details_fields).
3.  If you add or edit a recurrence pattern, enter information in the [Recurrence Pattern fields](#Recurrence_Pattern_fields).
4.  To edit equipment details associated with the appointment, click **Equipment Details**, and then enter information in the [Equipment Details fields](#Transport_Equipment_Information_fields).
5.  To assign or remove an inbound shipment or outbound load for the appointment:
    1.  Select **Load Details** or **Inbound Shipment Details**.
        
        **Note**: This option depends on whether you are working with a receiving appointment (Inbound Shipment Details) or shipping appointment (Load Details).
        
    2.  To assign an inbound shipment or load:
        1.  Click **Add**.
        2.  Select the check box next to the inbound shipment or load.
        3.  Click **Select**.
    3.  To remove an inbound shipment or load, select the check box, and then click **Delete**.
6.  Click **Save**.

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

## Appointment Details fields

 
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

## Recurrence Pattern fields

 
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

## Transport Equipment Information and Equipment Details fields

 
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

## Tractor Information fields

 
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

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
