---
title: "Warehouse Labor Management"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/warehouse_labor_management.htm"
source: "/content/warehouse_labor_management.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Integration"
  - "Warehouse Labor Management"
sections:
  - "Pick reporting to Warehouse Labor Management"
  - "Work type attributes for Warehouse Labor Management"
  - "Setup"
  - "Configure Warehouse Labor Management integration"
  - "Warehouse Labor Management fields"
  - "Activities fields"
images: []
source_sha1: 9b8ea19b08caa53a78b763ebd7dda56e4e385755
---
# Warehouse Labor Management

Warehouse Labor Management is an extensive labor scheduling and reporting solution designed to help warehouse managers maximize employee (user) performance and warehouse operation through improved planning, workload balancing, real-time feedback, and productivity reporting. It is designed to provide you with an effective labor management solution, either as a standalone application or as a fully integrated component of the Blue Yonder product line.

The time and incentives functionality of Warehouse Labor Management is a single source solution for time and attendance tracking, incentive pay calculations, labor planning, and workforce planning. It helps companies drive greater productivity gains, reduce distribution costs, and streamline labor data administration and reporting.

The modeling functionality of Warehouse Labor Management integrates engineering standards data (such as patterns, timings, and master standard data \[MSD\] elements) into the application and provides the ability to edit and manage that data for your environment.

For more information, see the _Warehouse Management and Warehouse Labor Management Integration Guide_.

## Pick reporting to Warehouse Labor Management

The application is capable of sending pick information to Warehouse Labor Management (WLM) for the purpose of crediting operators with the work performed. A pick is reported by one or more obtain records with each record specifying the UOM quantity that was picked.

The application can send pick information to WLM in the following UOMs: pallet, layer, case, inner pack, and each. For example, if the operator fulfills a pick request for 25 eaches by picking 1 case (20 eaches) and 5 eaches, then two obtain records are created, one for the case pick quantity and one for the each pick quantity.

To configure the reporting of pick information to WLM, you must enable the activity codes for which transactions should be sent. For example, to send transactions for case picks, you must enable the Case Pick activity code.

For less than full pallet picks, you can also enable the application to report picked quantities to WLM in a specified UOM instead of the UOM in which the inventory was actually picked. If this functionality is enabled, then you can specify a UOM for each pick-type activity code. For example, if an item footprint has 20 eaches to a case, and you have configured the activity code to send pick quantities in the Case UOM, then a pick quantity of 25 eaches is reported as 1 case and 5 eaches, regardless of the UOM in which the quantity was actually picked. When this functionality is enabled, a warehouse default UOM is used when pick work is performed for an activity code that does not have a UOM specified. This functionality only applies to less than full pallet pick quantities; full pallet picks are reported in the UOM that is configured as the pallet equivalent UOM.

**Note**: If a reporting UOM is not used and an operator picks a UOM that does not have a system-equivalent, then the application reports the quantity in the UOM that is configured as Case equivalent UOM.

The reason for reporting pick information in a specified UOM is to provide greater consistency in labor reporting and to reduce inflated performance caused by operators that select a more time-consuming UOM than the one that was actually picked.

The following footprint examples show how pick information is sent when the application is configured to report pick information in a specified UOM:

-   **Example 1:**
    -   **Reporting UOM**: Case
    -   **Footprint**: 4 inner packs per case
    -   **Pick Quantity**: 5 inner packs
    -   **Reported Quantity**: 1 case and 1 inner pack
-   **Example 2:**
    -   **Reporting UOM**: Each
    -   **Footprint**: 10 eaches per case; 5 cases per pallet
    -   **Pick Quantity**: 1 case and 5 eaches
    -   **Reported Quantity**: 15 eaches
-   **Example 3:**
    -   **Reporting UOM**: Each
    -   **Footprint**: 10 eaches per case; 10 cases per pallet
    -   **Pick Quantity**: 1 pallet
    -   **Reported Quantity**: 1 pallet
        
        **Note**: Full pallet pick quantities are reported in the pallet equivalent UOM; the reporting UOM does not apply to full pallet quantities.
        

## Work type attributes for Warehouse Labor Management

A work type is a category within Warehouse Labor Management (WLM) that is used to represent a basic type of work (for example, selection or putaway) performed in a facility. A work type is associated to an activity code in Warehouse Management (WM) and to a job code in WLM. An attribute defined for a work type is used by WLM to filter job codes and select the appropriate job for an assignment. You can define up to twenty attributes for each work type. The available attributes are the fields (columns) from database tables such as Country, Item Family, Order, Shipment, and Supplier.

For example, assume picking cases of inventory in the Frozen item family has different performance standards than picking cases in the Canned item family. To apply separate job codes to the different case pick assignments, you can define Item Family as a work type attribute for the Case Pick work type (in WM and WLM), and then you can define a specific item family (Canned or Frozen) for each job code mapped to the Case Pick work type (in WLM). If a case picking assignment for frozen inventory is downloaded, then the application identifies the correct job code based on matching work type, aisle area, client or customer, and work type attribute value (Item Family = Frozen).

### Setup

You must perform the following tasks to send and utilize work type attribute information for job code mapping: 

1.  In Warehouse Management, set the **Send Work Type Attributes** field to Yes, and then define the work type attributes to send. See [Configure Warehouse Labor Management integration](#Configure_Warehouse_Labor_Management_integration).
2.  In the Console, under **Tasks**, ensure that the **SL\_ASYNC\_EVENT** task is started.
3.  Perform the following tasks in Warehouse Labor Management:
    1.  Enable the **Enable Job Code Mapping Using Work Type Attributes** policy.
    2.  Define the attributes for a work type in Work Type Attribute Maintenance ensuring the attributes match those that are defined for the work type in WM.
    3.  Define values for the work type attributes on the **Advanced Mapping** tab in Job Code Maintenance.

## Configure Warehouse Labor Management integration

1.  Select **Configuration > Integration > Warehouse Labor Management**. The Warehouse Labor Management page displays the following information:
    -   Status of the Integrator tasks associated with the integration
    -   Status of the Integrator transactions associated with the integration
2.  Enter information in the [Warehouse Labor Management fields](#Warehouse_Labor_Management_fields).
3.  To configure activities for which an integration transaction should be sent to Warehouse Labor Management when the activity is performed:
    1.  Click **Activity Codes**.
    2.  Perform one of the following tasks:
        -   To add an activity, click **Add**.
        -   To modify an activity, in the grid, click the activity.
        -   To copy an activity, in the grid, select the check box next to the activity, and then click **Copy**.
    3.  Enter information in the [Activities fields](#Activities_fields).
    4.  Click **Apply**.
    5.  Click **Apply**.
4.  To define the attributes of a work type:
    
    **Note**: A work type attribute is defined for a work type and used by Warehouse Labor Management to filter job codes and select the appropriate job for an assignment. You can define up to twenty attributes for each work type. See [Work type attributes for Warehouse Labor Management](#Work_type_attributes_for_Warehouse_Labor_Management).
    
    1.  Click **Work Type Attributes**.
    2.  In the grid, click the work type to which you want to add attributes.
    3.  In an attribute field, enter an attribute for which specific values can be defined and mapped to a job code associated with the selected work type.
    4.  Click **Save**.
5.  Click **Save**.

## Warehouse Labor Management fields

 
| Field | Description |
| --- | --- |
| Enable Warehouse Labor Management | If Enabled, Warehouse Labor Management functionality is available for use in Warehouse Management.<br > If Disabled, then Warehouse Labor Management functionality it is not available for use. |
| Warehouse Labor Management Service URL | Service URL of the Warehouse Labor Management instance with which you want to integrate Warehouse Management. Only required if Warehouse Labor Management is installed in a separate instance from Warehouse Management. |
| Prompt for End of Day | If Yes, then when a user logs out of Warehouse Management, a message is displayed asking if it is the end of the day. The application uses this message to determine whether to send a transaction to Warehouse Labor Management when the user logs out.<br > If you choose to have the message displayed, then you can also select whether an IEND or ISTOP transaction is sent when the user answers Yes to the message.<br > If No, no message is displayed. |
| WLM Activity | Type of transaction that is sent when the user answers Yes to the end of day message. The end of day message is a notice that is displayed when the user logs out of Warehouse Management; the message typically asks the user if it is the end of their work day. If the user answers No to the end of day message, no transaction is sent is when user logs out.<br>-   • **IEND**: Transaction that indicates the end of the user's activities in Warehouse Management, and allows the ISTOP (end of the day) transaction to be sent by another system when the user punches out.
<br>-   • **ISTOP**: Transaction that indicates the end of the user's work day. |
| Send Labor Data for Unmeasured Users | If Yes, labor data is sent to Warehouse Labor Management for users that are configured as Unmeasured. An unmeasured user is typically a user for whom labor tracking is not required, such as a seasonal or temporary employee, or a new employee during a probationary period.<br > If No, labor data is not sent for users configured as Unmeasured. |
| Enable Location Synchronization | If Yes, locations are built jointly between Warehouse Labor Management and Warehouse Management.<br > If No, locations are not built jointly between the applications. |
| Labor Goal Time | If Yes, you want Warehouse Labor Management to provide goal time estimates for picks, pick work assignments, putaway, and replenishments. Set Labor Goal Time to Yes to enable Warehouse Labor Management to calculate the goal time estimates for picks, pick work assignments, putaway, and replenishments. Goal time estimates are calculated by creating Future Assignments in Warehouse Labor Management.<br > Goal time calculations should be considered estimates because they can change based on multiple factors, such as skipped picks, use of different travel sequences, and transition move travel time. <br > The following goal time calculation exceptions exist:<br>-   • The goal time calculation does not factor in transition moves because those moves can only be calculated when the actual work happens. That time is reflected in Actual Assignments. 
<br>-   • While goal times can be calculated for both directed and undirected work, they cannot be calculated for putaway work that is performed immediately. A putaway work task must exist in the work queue in order for Warehouse Management to send the assignment details, such as the destination location, to Warehouse Labor Management for goal time calculation.
<br>-   • Goal time calculation is not available when a user picks more than one work reference without depositing the previous pick. In this case, the Summary screen displays Goal Time as "N/A".
<br>-   • The goal time estimated for a threshold pick is less than the actual goal time because the location to which excess inventory is deposited is unknown until it occurs.
<br>-   • Goal time cannot be calculated for a manual replenishment.
<br>-   • Goal times are not available when the warehouse transfer is in progress.
<br > If No, goal time estimates are not displayed. |
| Receive Pre Plan Days | Defines the number of days in advance of the arrival of an inbound shipment when labor planning for the inbound shipment should be performed.<br > For example, you can set the value for Receive Pre Plan Days to 2. Then, if the expected date of an inbound shipment is January 12, WLM initiates planning for the inbound shipment on January 10. If the value for Receive Pre Plan Days is less than 0, planning will be disabled regardless of the expected date of an inbound shipment. |
| Order Line Estimate | If Yes, WLM provides pick goal time estimates for order lines.<br > If No, pick goal times for order lines are not displayed. |
| Deferred | If Yes, Warehouse Management will defer sending pick information to Warehouse Labor Management by using a background process. If you choose to defer the information, you must also configure a background process to send the deferred information to Warehouse Labor Management.<br > If No, Warehouse Management will send pick information to Warehouse Labor Management immediately during the pick release process. If you choose to send the information immediately, the pick release process in Warehouse Management could slow down significantly. |
| Limit Locations For Movement Cost Calculation | If Yes, then the number of locations that are sent by Warehouse Management (WM) to Warehouse Labor Management (WLM) for cost movement calculations is limited to the value you define in the **Maximum Locations For Movement Cost Calculation** field. Movement cost calculation is used to determine the best location to deposit a piece of inventory when WM attempts to allocate a location during a system-directed inventory move. During this calculation, WLM considers the device and equipment of the operator as well as the travel distances between the source location and eligible destination locations sent by WM.<br > **IMPORTANT**: Limiting the number of locations considered for movement cost calculation can reduce processing time when WM and WLM are installed in separate instances, especially if the WLM instance is on a remote server. However, this setting has no effect on system performance when WM and WLM are installed in the same instance.<br > If you do not limit the number of locations or you set the limit too high, the processing time for movement cost calculation will increase. A lower limit will decrease the processing time, however, only the limited number of locations will have an actual calculated movement cost. For example, if a large facility with thousands of locations does not set a limit, then each time the system attempts to find a deposit location for inventory, WM sends every eligible deposit location (for the operation) to WLM for movement cost calculation. Alternatively, if limiting is enabled and the **Maximum Locations For Movement Cost Calculation** field value is 100, then WM sends only the first 100 locations for movement calculations to determine the best location; the first 100 locations are selected using the configured location sorting settings for the current operations, such as putaway. Set this field to Yes and define a limit to avoid a significant decrease in system performance during system-directed inventory movements.<br > If No, then the number of locations that WM sends to WLM for movement cost calculation is unlimited. |
| Maximum Locations For Movement Cost Calculation | Maximum number of locations that Warehouse Management (WM) sends to Warehouse Labor Management (WLM) for movement cost calculation. Movement cost calculation is used to determine the best location to deposit a piece of inventory when WM attempts to allocate a location during a system-directed inventory move. During this calculation, WLM considers the device and equipment of the operator as well as the travel distances between the source location and eligible destination locations sent by WM.<br > **IMPORTANT**: Limiting the number of locations considered for movement cost calculation can reduce processing time when WM and WLM are installed in separate instances, especially if the WLM instance is on a remote server. However, this setting has no effect on system performance when WM and WLM are installed in the same instance.<br > If you do not limit the number of locations or you set the limit too high, the processing time for movement cost calculation will increase. A lower limit will decrease the processing time, however, only the limited number of locations will have an actual calculated movement cost. For example, if a large facility with thousands of locations does not set a limit, then each time the system attempts to find a deposit location for inventory, WM sends every eligible deposit location (for the operation) to WLM for movement cost calculation. Alternatively, if the limit is set at 100, then WM sends only the first 100 locations for movement cost calculation to determine the best location; the first 100 locations are selected using the configured location sorting settings for the current operations, such as putaway. You use this limit to avoid a significant decrease in system performance during system-directed inventory movements. |
| Work Order Planning | If Yes, you want to use the labor planning feature for work orders. Enabling the labor planning feature for work orders means that Warehouse Management will send work order information when a work order is automatically generated from a host transaction download or from a bill of material (BOM) with the **Auto-generate Work Order** check box selected, or when the goal time for a work order is manually requested. Warehouse Labor Management uses the work order information to create planning assignments and estimated goal times for the associated work orders.<br > If No, labor planning processing is disabled. |
| Deferred | If Yes, Warehouse Management will defer sending work order information to Warehouse Labor Management when a work order is automatically generated from a host transaction download or from a bill of material with the **Auto-generate Work Order** check box selected, or when the goal time for a work order is manually requested. Instead, it will be sent later by a background process. If you choose to defer the information, you must also configure a background process to send the deferred information to Warehouse Labor Management.<br > If No, Warehouse Management will send work order information to Warehouse Labor Management immediately (when a work order is automatically generated from a host transaction download or from a bill of material with the **Auto-generate Work Order** check box selected, or when the goal time for a work order is manually requested). If you choose to send the information immediately, the work order process in Warehouse Management could slow down significantly. |
| Release Appointment Picks By Labor Estimate | If Yes, picks are released in advance of an appointment date and time so that all of the inventory can be picked and loaded in time for the shipping transport equipment to meet its scheduled dispatch time. Labor planning must also be enabled.<br > If No, the pick release by labor estimate process is disabled. |
| Buffer Time | Additional amount of time to add to the total time in which to release picks to allow for additional time for activities such as processing paperwork or preparing the inventory for shipment. The additional amount of time can either be a percent or number of minutes. See the **Buffer Time Calculate By** field. |
| Buffer Time Calculate By | Option indicating how the number in the **Buffer Time** field is to be used in calculating additional time.<br>-   • **Percent**: Calculate the additional time as a percentage of the Warehouse Labor Management goal time and add the result. For example, if the Buffer Time is 10, the Buffer Time Calculated By is Percent and the Warehouse Labor Management goal time is 600, then the total time frame is 660 seconds \[600 + (10% x 600)\].
<br>-   • **Minutes**: Add the additional time as straight minutes to the Warehouse Labor Management goal time. For example, if the Buffer Time is 10, the Buffer Time Calculated By is Minutes and the Warehouse Labor Management goal time is 600, then the total time frame is 1200 seconds \[600 + (10 minutes x 60 seconds/minute)\]. |
| Processing Field | Date and time to use as the deadline for loading the transport equipment. If this field is left blank, then the application defaults to Start Date. |
| Release Ship Picks Estimate | In support of the release work by dispatch time feature, the Release Ship Picks by Labor Estimated policy enables you to release picks in advance of a shipment's early or late ship or delivery date and time so that all of the inventory can be picked and loaded in time for the shipping transport equipment to meet its scheduled dispatch time. Labor planning must also be enabled.<br > **Note**: If you use appointments in Warehouse Management, also see the **Release Appointment Picks by Labor Estimated** field. |
| Buffer Time | Additional amount of time to add to the total time in which to release picks. This is to allow for additional time for activities such as processing paperwork or preparing the inventory for shipment. The additional amount of time can either be a percent or number of minutes. See the **Buffer Time Calculate By** field. |
| Buffer Time Calculate By | Option indicating how the number in the **Buffer Time** field is to be used in calculating additional time.<br>-   • **Percent**: Calculate the additional time as a percentage of the Warehouse Labor Management goal time and add the result. For example, if the Buffer Time is 10, the Buffer Time Calculated By is Percent and the Warehouse Labor Management goal time is 600, then the total time frame is 660 seconds \[600 + (10% x 600)\].
<br>-   • **Minutes**: Add the additional time as straight minutes to the Warehouse Labor Management goal time. For example, if the Buffer Time is 10, the Buffer Time Calculated By is Minutes and the Warehouse Labor Management goal time is 600, then the total time frame is 1200 seconds \[600 + (10 minutes x 60 seconds/minute)\]. |
| Processing Field | Date and time to use as the deadline for loading the transport equipment. If this field is left blank, then the application defaults to Late Ship Date. |
| Field 1 through Field 5 | You can configure up to five user-defined fields for the purpose of providing additional data in transactions that are sent to Warehouse Labor Management. Warehouse Labor Management uses this data when determining the labor standards to apply to work that users perform in Warehouse Management.<br > Typically a User Field policy is mapped to planned inbound order information or outbound order information and used in Warehouse Labor Management as the source for the creation of custom labor standards.<br > You can configure the following policy field values:<br>-   • User Field 1
<br>-   • User Field 2
<br>-   • User Field 3
<br>-   • User Field 4
<br>-   • User Field 5
<br > Each of the User Field policies can be configured to provide data from one of the following fields:<br>-   • Carrier
<br>-   • Customer Inbound Order Number
<br>-   • Expected Arrival Date
<br>-   • Inbound Shipment
<br>-   • Order
<br>-   • Order Type
<br>-   • Originator Reference
<br>-   • Inbound Order
<br>-   • Planned Inbound Order
<br>-   • Inbound Order Type
<br>-   • Transport Equipment Type
<br > When you configure a User Field policy with one of the data fields, then integration transactions that are sent to Warehouse Labor Management as a result of work performed in Warehouse Management will include a value for the selected data field, if applicable. You can view generated transactions, including the value of populated data fields, in Labor Transaction Operations. |
| Send Work Type Attributes | If Yes, then Warehouse Management sends work type attribute information to Warehouse Labor Management for use in advanced job code mapping. If you set this field to Yes, then you can define up to twenty attributes for each work type. See [Work type attributes for Warehouse Labor Management](#Work_type_attributes_for_Warehouse_Labor_Management).<br > The available attributes are the fields (columns) from database tables such as Country, Item Family, Order, Shipment, and Supplier.<br > **Note**: For WM to send the information to WLM, the SL\_ASYNC\_EVENT task, which is maintained in the Console, must be started. For WLM to utilize the information sent from WM, you must enable the Enable Job Code Mapping Using Work Type Attributes policy in WLM. You must also define the same attributes for the work type in WLM as you define in WM.<br > If No, then WM does not send work type attribute information to WLM. |
| Change UOM Picked | If Yes, the application sends picked quantities to Warehouse Labor Management (WLM) at a specified UOM instead of the UOM in which the inventory was actually picked. This setting is useful in providing a greater level of consistency in labor information and to reduce inflated performance caused by operators that select a more time-consuming UOM than the one that was actually picked. The conversion does not apply to pallet level picks.<br > If this field is set to Yes, you can configure the **UOM** field with the warehouse default UOM, and pick-type activity codes with a UOM specific to a pick type. The warehouse default value is used if a UOM is not defined for the activity code associated with a pick.<br > If No, the application sends picked quantities to WLM in the UOM that was actually picked, based on the supported UOMs: each, inner pack, case, layer, or pallet.<br > See [Pick reporting to Warehouse Labor Management](#Pick_reporting_to_Warehouse_Labor_Management). |
| Picked UOM | Unit of measure (UOM) to which a completed pick quantity is converted for the purpose of reporting activity to Warehouse Labor Management (WLM). For example, an item footprint specifies 20 eaches to a case. The **Picked UOM** field is set to Case. Therefore, if the pick quantity is 25 eaches, two obtain records are reported to WLM: 1 case and 5 eaches.<br > The following UOMs are supported by WLM and are available for selection: Pallet, Layer, Case, Inner Pack, and Each.<br > The **Picked UOM** field is only available if the **Change UOM Picked** field is set to Yes for the Warehouse Labor Management integration. Additionally, if the **Labor Discrete Procedure** field is defined, then the **Picked UOM** field is irrelevant and not used in transactions to Warehouse Labor Management because it applies to picked inventory (an obtain and place activity, not a discrete procedure).<br > See [Pick reporting to Warehouse Labor Management](#Pick_reporting_to_Warehouse_Labor_Management). |

## Activities fields

 
| Field | Description |
| --- | --- |
| Activity Code | Unique code that identifies a work or non-work activity that is performed in Warehouse Management. For example, when an RF operator performs a case pick (work activity) or a user at a workstation creates a new order (non-work activity), a record of the activity is generated.<br > Warehouse Management provides a standard set of activity codes, each of which is associated with a server command that generates a record when the associated activity is performed. If additional activity codes are required, an associated server command is also required; contact your Blue Yonder project team for information on implementing additional activity codes and commands. |
| Description | Text that further describes the activity code. This is the value that is displayed in place of the code on other pages and windows, and in reports. |
| Activity Category | Group that is used to categorize the activity according to type. A category can be used as search criteria to limit the results of your search and display related activities.<br>-   • **General Activity**: Non-work activities that are logged as daily transactions.
<br>-   • **Inventory Activity**: Non-work activities related to inventory tracking.
<br>-   • **Order Activity**: Non-work activities related to order processing.
<br>-   • **Trailer Activity**: Non-work activities related to transport equipment movements.
<br>-   • **Work**: Work activities that are logged to daily transactions when a user performs an action (usually an RF function) in Warehouse Management. Work activities are typically configured to be sent to Warehouse Labor Management for labor tracking. |
| Voice Code | Code used to represent the piece of equipment in facilities that use voice terminals. When the voice terminal operator is prompted for the equipment, the operator can speak the voice code to identify the equipment to the application. |
| Send to Labor | If Yes, an integration transaction is generated to send the assignment information to Warehouse Labor Management when the activity is performed.<br > If No, no integration transaction is generated to Warehouse Labor Management when the activity is performed.<br > This field is only available if Warehouse Management is integrated with Warehouse Labor Management. |
| Work Type | Code defined in Warehouse Labor Management that corresponds to the activity code, and identifies the basic unit of work that was performed in the facility such as picking cases to a pallet or loading transport equipment from a staging lane. The work type is associated with a job code that is used to determine the labor standard for the activity.<br > This field is displayed only if Warehouse Labor Management is enabled for the warehouse. Values are displayed in the field only if Warehouse Labor Management is integrated with Warehouse Management.<br > This field is required when the **Assignment Type** field value is Direct. |
| Labor Discrete Procedure | Identifier for a discrete procedure, defined in Warehouse Labor Management. A discrete procedure is used by Warehouse Labor Management to account for additional time in a work assignment that is not accounted for by the job code (standard) for the assignment's work type. The discrete procedure is used, for example, to account for the time differential that occurs when a cycle count is presented to a user during a picking activity. The cycle count can extend the time of the picking assignment but does not require travel time.<br > This field is only available if Warehouse Management is integrated with Warehouse Labor Management.<br > **Note**: If you enter a value in this field, the **Assignment Key** and **Picked UOM** fields are irrelevant and not used in transactions to Warehouse Labor Management. This is because discrete procedures are always sent with an assignment key of A, and the UOM field only applies to picked inventory (an obtain and place activity, not a discrete procedure). |
| Assignment Key | Transaction type from which Warehouse Labor Management should get location information for matching to a job standard (job code) when processing assignments. Most assignments have at least one obtain and one place transaction for a single activity.<br>-   • **Obtain**: Transaction type that indicates an inventory pickup action, such as receiving or picking.
<br>-   • **Place**: Transaction type that indicates an inventory deposit action, such as moving and depositing inventory.
<br > This field is only available if Warehouse Management is integrated with Warehouse Labor Management. If the **Labor Discrete Procedure** field is defined, the value of the **Assignment Key** field is irrelevant since discrete procedure transactions are always sent with an assignment key of A. |
| Assignment Type | Type of assignment that was performed.<br>-   • **Direct**: A work task, such as picking or loading, that can have a cost applied against a specific object.
<br>-   • **Indirect**: A work task that does not have a cost that can be applied against a specific object, such as a client or customer. It can refer, for example, to management or maintenance time, such as a battery change for a fork truck. If you select this option, the **Labor Discrete Procedure** field can be blank (no value) because it is not used by the application.
<br > This field is only available if Warehouse Management is integrated with Warehouse Labor Management. |
| Picked UOM | Unit of measure (UOM) to which a completed pick quantity is converted for the purpose of reporting activity to Warehouse Labor Management (WLM). For example, an item footprint specifies 20 eaches to a case. The **Picked UOM** field is set to Case. Therefore, if the pick quantity is 25 eaches, two obtain records are reported to WLM: 1 case and 5 eaches.<br > The following UOMs are supported by WLM and are available for selection: Pallet, Layer, Case, Inner Pack, and Each.<br > The **Picked UOM** field is only available if the **Change UOM Picked** field is set to Yes for the Warehouse Labor Management integration. Additionally, if the **Labor Discrete Procedure** field is defined, then the **Picked UOM** field is irrelevant and not used in transactions to Warehouse Labor Management because it applies to picked inventory (an obtain and place activity, not a discrete procedure).<br > See [Pick reporting to Warehouse Labor Management](#Pick_reporting_to_Warehouse_Labor_Management). |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
