---
title: "Work Operations"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/work_operations.htm"
source: "/content/work_operations.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Work"
  - "Work"
  - "Work Operations"
sections:
  - "Work management priorities"
  - "Priority escalation processes"
  - "Directed work by proximity"
  - "Add or modify a work operation"
  - "Delete a work operation"
  - "Add a work operation form flow"
  - "Work Operations fields"
images: []
source_sha1: 6974f03b912227ff7fd957e44e50bb7acf830418
---
# Work Operations

A work operation is a defined activity within the facility usually performed by an operator using a device such as an RF terminal or voice headset. A standard set of work operations is provided with the application, and these define activities such as receiving, counting, picking, distribution, and loading and unloading transport equipment.

**IMPORTANT**: When you add a new work operation, the new operation and associated RF form flow must also be added to the RDTALLOPR/DEFAULT-FORM-FLOW group policy. This policy controls the sequence in which RF screens are displayed for each type of operation. Without a default RF form flow defined for the operation, the application will not display any RF screens to an operator that attempts to perform the operation. Default form flows are maintained in [Policy Maintenance](../../../../administration/system-administrator/configuration/policy/policy-maintenance.md). See [Add a work operation form flow](#Add_a_work_operation_form_flow).

To each work operation, you assign the users and equipment that you want to authorize to perform it. For example, you may want to authorize certain users and only handheld terminals to perform counts.

**Note**: Equipment authorizations for a work operation only apply to directed work. You cannot limit the undirected work that can be performed with a piece of equipment. For example, if a piece of equipment is not authorized for Receiving, it can still be used to receive inventory through undirected work.

To each work operation, you also assign a base priority, which determines the priority of a piece of work when it enters the work queue. For example, if the work operation for Case Pick has a priority of 35, then a piece of work created for case picks is initially assigned a priority of 35. You can also define the increments at which priorities are escalated.

**Note**: The lower the number, the higher the priority. For example, 1 is the highest priority; 10 is a higher priority than 20.

For facilities that use voice terminals, you can associate a work operation such as CPK (Case Pick) or PCK (Pallet Pick) to a generic voice function, such as Picking. This association is defined so that when the voice operator selects a function, such as Picking, the application can attempt to find directed work for any of the operations associated with that function. If no work operation is assigned to a voice function, then directed work cannot be retrieved for that function.

## Work management priorities

Work management functionality presents directed work to operators who use devices such as radio frequency (RF) and voice terminals to request directed work. Each work request is based on a work operation; examples of operations include Identify, Piece Pick, Case Transfer, and Trailer Unload.

You can use the work management functionality to define priorities for operations, which determine the sequence in which directed work is displayed, so that more important work is displayed sooner than less important work. You can also define priorities for work areas and work zones, to determine when work is of a sufficient priority to move an operator from the current work area or work zone to another one to perform the work. These priorities are designed to ensure that operators are working efficiently, but they do not override user and vehicle authorizations. That is, operators are not moved if they or their vehicles are not authorized to perform the higher priority work.

With priority, the lower the number, the higher priority. For example, 1 is the highest priority; 10 is a higher priority than 20.

-   **Base priority**: Base priority is assigned to a work operation and determines the priority at which the work initially enters the work queue. It is the priority at which a work request is created. This can be used, for example, to assign a higher priority to pick work than to count work, to ensure that pick work is completed before count work.
-   **Maximum escalation priority**: Maximum escalation priority is assigned to a work operation and determines the maximum priority to which the base priority for an operation can be escalated. You use it to limit the effective priority of an operation. For example, you may want to escalate the priority of count work based on how long it remains in the work queue, but you may not want the priority of count work to exceed that of pick work; therefore, if your pick work has a base priority of 20, you may want to assign a maximum escalation priority of 25 to your count work.
-   **Effective priority**: Effective priority is the current priority of a work request in the work queue. This value represents the base priority defined for the operation plus any escalation increments that have been applied over time to the work request. For example, if the base priority of pick work is 20 and it is defined to escalate by 5 every hour, then after 2 hours it has an effective (current) priority of 10.
-   **Absolute priority**: Absolute priority is assigned to work areas and work zones.
    
    -   For work areas, it defines the priority at which the application should display work in another work area, rather than the operator's current work area.
    -   For work zones, it defines the priority at which the application should display work in another work zone in the same work area, rather than the operator's current work zone.
        
    
    For example, if there is work with a priority higher than the absolute priority in another work zone in the same work area, the operator is offered the work in the other work zone.
    
    As another example, consider that an operator is working in Zone A, and the highest priority work in Zone A is 50. If the absolute priority defined for Zone A is 30, and there is work in another work zone in the work area that has a priority of less than 30 (such as 29), the application displays the work in another zone.
    
-   **Delta priority**: Delta priority is assigned to work areas and work zones.
    
    -   For work areas, it defines the difference that must exist between the highest effective priority work in the current work area, and the highest effective priority work in another work area in order for the application to display work in another work area.
    -   For work zones, it defines the difference that must exist between the highest effective priority work in the current work zone, and the highest effective priority work in another work zone in the same work area in order for the application to display the work in another work zone.
        
    
    For example, if you define a delta priority of 20 for a work zone, you are indicating that the application should display work in another zone in the same work area only if there is a work request with a priority that is 20 higher than the highest effective priority work in the current zone.
    
    As another example, consider that an operator is working in Zone A, the highest effective priority work request in this zone is 50, and the delta priority defined for Zone A is 20. If a work request exists in another zone in the work area that has a priority value of less than 30 (such as 29), the application displays the work in other work zone.
    
-   **Home work area absolute priority**: Home work area absolute priority is assigned to a work area. It defines the priority at which an operator, who has the area as a home work area but is currently working in another work area, is given work in the operator's home work area. This value is used to keep operators in their current work area until work of sufficient priority exists to warrant their return to the home work area.

## Priority escalation processes

**Escalation based on time**

A work operation can be configured with an escalation value and time, so that the priority of the directed work is escalated by a specific amount depending on how long it remains unacknowledged in the work queue. Escalating the priority increases the probability that the piece of work is acknowledged.

**Note**: Timer-based escalations can be used with ship date escalations because each process uses a different escalation increment.

For example, if a request for a case pick is sent to the work queue with a priority of 35, it can be automatically escalated by 10 every 60 minutes until it reaches a pre-configured maximum priority, such as 5.

The following table shows an example of how work escalation takes place. A piece of work for a case pick enters the work queue with a priority of 35 at 9:00 A.M., and every 60 minutes the priority of the work escalates by 10, until it reaches a maximum priority of 5. Thereafter, it remains at 5 until it is acknowledged by an operator.

 
| Time | Priority |
| --- | --- |
| 9:00 A.M. | 35 |
| 10:00 A.M. | 25 |
| 11:00 A.M. | 15 |
| 12 noon | 5 (maximum) |
| 1:00 P.M. | 5 |

**Escalation based on a server command**

To define rules for escalation that are specific to an operation code, you can specify and enable a command that will run after timed work escalation has occurred.

You can use this command, for example, to escalate replenishment work to a higher priority if the fill percentage at the location is less than a specific value; that is, the location is close to being empty. The specific command for escalating replenishment work for locations that are at 10% of capacity is "process work escalation for replenishments where thrpct = 10"; after this command runs, if the destination location for a replenishment is less than 10% full, then the application sets the priority of the replenishment to the maximum escalation priority defined for the operation.

**Escalation based on a location**

You can configure a location to escalate work based on a threshold defined for a specific number of pallets or a percentage of pallets in that location. Once the location reaches the threshold, the application continues to escalate work with the highest priority until the inventory amount in the location is below the threshold. For more information on configuring a location, see [Locations](../../warehouse/locations.md). The application uses the existing configurations in the operation code to determine the escalation time and increment.

This is beneficial, for example, for configuring a pickup and deposit (P&D) location so that it doesn't become full and stall the receiving process.

**Escalation based on ship date and order type**

You can configure an operation to escalate work to a specific priority (not incremental) based on the amount of time remaining before the shipment date or delivery date defined on the shipment for which the work was created. You can also override this setting by order type; for example, to increase the priority for orders that take more time to pick or require post-pick processing.

Escalation based on shipment or delivery date is used to escalate the following types of operations:

-   Pick work for an outbound shipment
-   Inventory transfers, such as from a pickup and deposit (P&D) location to a staging location, to satisfy an outbound shipment

If a pick is cancelled and reallocated, the priority of the cancelled pick is automatically assigned to the reallocated pick, so that the escalation process does not need to be restarted.

**Note**: Ship date escalations can be used with timer-based escalations because each process uses a different escalation increment.

For outbound work, if the source location contains more than one LPN, the application continues to escalate work until the required LPN is moved. The application escalates the work with the highest priority first.

**Example**

The following example shows how the application escalates work based on ship date and order type:

1.  Pallet Pick is a work operation that is configured with the following attributes:
    -   Base priority = 30
    -   Ship date escalation time and priority = 60 minutes from late ship date escalate to priority of 10.
    -   Override by order type:
        -   Cartonization order type = 60 minutes from late ship date escalate to priority of 5.
2.  Two orders are allocated with a late shipment date of 4:00 P.M.
    -   Customer order = 1 pallet pick
    -   Cartonization order = 1 pallet pick
3.  A background job runs on a regularly scheduled basis to process ship date escalation.
4.  When the job runs and finds the time is within an hour of the late ship date (such as 3:00 P.M.), the following changes occur:
    -   Escalates the pallet pick for the customer order to a priority of 10.
    -   Escalates the pallet pick for the cartonization order to a priority of 5.

## Directed work by proximity

Warehouse Management distributes directed work based on priority, work zone changes, and travel sequence. If Warehouse Labor Management is integrated with Warehouse Management, you can take advantage of the Warehouse Labor Management travel distance calculations to give an operator the piece of work that is physically closer rather than the next piece of work identified by travel sequence. This is known as the directed work by proximity functionality.

To accomplish directed work by proximity, Warehouse Management first sends Warehouse Labor Management an ordered list that includes the starting location for each piece of work. Warehouse Labor Management then uses this information to calculate the travel distance from the operator's current location to each piece of work's starting location. Warehouse Management retrieves the calculations, and then orders the list of locations from lowest travel distance to highest travel distance. Warehouse Management can then assign the piece of work closest to the operator's current location (piece of work with the lowest travel distance).

The application provides a policy to determine how many milliseconds Warehouse Management waits to receive the travel distance calculations from Warehouse Labor Management. Setting this value too high could result in a long wait for the closest starting work location to be assigned. Setting this value too low could mean that not all of the locations get analyzed and Warehouse Labor Management sends back a partial list, which also means that the closest piece of work may not be assigned to the operator (there was not enough time to analyze the location). To help offset this issue, the directed work by proximity functionality includes a policy to randomize the list of locations so that the list is not sent to Warehouse Labor Management in travel sequence order, which does not always indicate the physically closest location. For example, if you have set up your travel sequence in a serpentine pick pattern, then travel sequence is a very poor indicator of physical closeness of locations.

To take advantage of the directed work by proximity functionality, you must complete the following tasks:

1.  Make sure that Warehouse Labor Management is integrated with your instance of Warehouse Management.
2.  Configure the following policies:
    
    **Note**: You use Policy Maintenance to configure policies.
    
    -   **Acceptable Delay**: Number of milliseconds to allow for external calls to Warehouse Labor Management for determining travel distances. Warehouse Management will request travel distances from Warehouse Labor Management and then wait this number of milliseconds for as many travel distances as Warehouse Labor Management can generate in that time.
    -   **Directed Work by Proximity Enabled**: If enabled, the application displays the piece of work that has a starting location closest to the operator's current location; that is, based on proximity rather than travel sequence.
    -   **Subset Behavior**: If enabled, the list of locations for the directed work by proximity will be ordered randomly before Warehouse Management sends the list to Warehouse Labor Management for analysis. If disabled, the locations will be sent in travel sequence order.
3.  If you are also integrated with Event Management, then configure the **Error During Warehouse Labor Management Communications** field and set up the appropriate users in Event Management to receive and respond to the alerts. See [Configure Event Management integration](../../integration/event-management.md).

## Add or modify a work operation

1.  Select **Configuration > Work > Work > Work Operations**.
2.  Perform one of the following tasks:
    -   To add a work operation, click **Add**.
    -   To modify a work operation, in the grid, click the operation.
    -   To copy a work operation, in the grid, select the check box next to the operation, and then click **Copy**.
3.  Enter information in the [Work Operations fields](#Work_Operations_fields).
4.  To define ship date escalation settings:
    
    **Note**: Ship date escalation settings are only available if **Ship Date Escalation** is set to Yes.
    
    1.  Under **ESCALATION BASED ON SHIP DATE**, click **Escalation Settings**.
    2.  Perform one of the following tasks:
        -   To add an escalation setting, click **Add**.
        -   To modify an escalation setting, in the grid, click the value to change.
    3.  Enter information in the following fields:
        
         
        | Field | Description |
        | --- | --- |
        | Ship Date Escalation Time (Min) | Amount of time, in minutes, before the shipment or delivery date (as defined in the **Shipping Date Option** field) that you want the application to update the work priority. |
        | Ship Date Escalated Priority | Priority to which the work should be updated when the application evaluates the work for ship date escalation. |
        
    4.  Click **Apply**.
5.  To specify overrides to ship date escalation based on order type:
    
    **Note**: **Override Escalation Settings by Order Type** is only available if **Ship Date Escalation** is set to Yes.
    
    1.  Under **ESCALATION BASED ON SHIP DATE**, click **Override Escalation Settings by Order Type**.
    2.  Perform one of the following tasks:
        -   To add an order type, click **Add**.
        -   To modify an order type, in the grid, click the value to change.
            
            **Note**: You can add overrides for multiple order types and multiple overrides for a single order type.
            
    3.  Enter information in the following fields:
        
         
        | Field | Description |
        | --- | --- |
        | Order Type | Name of an order type. An order type is a category that is used to group orders based on the warehouse processing necessary to fulfill the order. For example, customer orders and distribution orders require different processing by the application, and so an order type can be assigned to categorize each order separately. The application uses order types, for example, to identify orders that are eligible for bulk picking, or to direct orders to specific destination locations. |
        | Ship Date Escalation Time (Min) | Amount of time, in minutes, before the shipment or delivery date (as defined in the **Shipping Date Option** field) that you want the application to update the work priority. |
        | Ship Date Escalated Priority | Priority to which the work should be updated when the application evaluates the work for ship date escalation. |
        
    4.  Click **Apply**.
6.  To assign the work operation to users:
    1.  Under **AUTHORIZATION**, click **Users**.
    2.  In the **Available** column, select the check box next to the users that are authorized for the operation.
    3.  Click **Apply**.
7.  To assign the work operation to equipment:
    
    **Note**: Equipment authorizations for the work operation only apply to directed work. You cannot limit the undirected work that can be performed with a piece of equipment. For example, if a piece of equipment is not authorized for Receiving, it can still be used to receive inventory through undirected work.
    
    1.  Under **AUTHORIZATION**, click **Equipment**.
    2.  In the **Available** column, select the check box next to the equipment that is authorized for the work operation.
    3.  Click **Apply**.
8.  Click **Save**.

## Delete a work operation

1.  Select **Configuration > Work > Work > Work Operations**.
2.  In the grid, select the check box next to the work operation to delete.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Add a work operation form flow

When you add a new work operation, the new operation and associated RF form flow must also be added to the RDTALLOPR/DEFAULT-FORM-FLOW group policy. This policy controls the sequence in which RF screens are displayed for each type of operation. Without a default RF form flow defined for the operation, the application will not display any RF screens to an operator that attempts to perform the operation. Default form flows are maintained in [Policy Maintenance](../../../../administration/system-administrator/configuration/policy/policy-maintenance.md).

1.  Select **System Administrator > Configuration > Policy > Policy Maintenance**.
2.  Add a work operation form flow policy:
    1.  From the **Actions** drop-down list, select **Add**.
    2.  Enter information in the Policy Maintenance fields.
        
        -   In the **Policy Code** field, enter RDTALLOPR.
        -   In the **Policy Variable** field, enter DEFAULT-FORM-FLOW.
        -   In the **Policy Value** field, enter the new work operation code.
        -   In the **Comments** field, enter a description of the purpose of the policy or functional area to which the policy is related, and information about how the policy is used.
    3.  Click **Save**.
        
3.  Add the default form flow policy details:<br>
    
    **Note**: Repeat this process for each RF screen that should be included in the operational flow.
    
    1.  Under **DETAILS**, from the **Actions** drop-down list, select **Add**.
    2.  Enter information in the following fields.<br>
        
        | Field | Description |
        | --- | --- |
        | Sort Sequence | Order in which the RF screens display during a work operation. If you do not enter a value, the sort sequence is application-generated starting with a value of 0. Use the sort sequence when you define more than one RF screen and you want to specify the order of their appearance. |
        | Return String 1 | Name of the RF form displayed on the RF screen (such as LOOK\_WORK). |
        | Comments | Description of the policy value and information about how the policy value is used. |
        
4.  Click **Save**.

## Work Operations fields

 
| Field | Description |
| --- | --- |
| Operation | Work operation that identifies the type of work that is created, such as piece pick, case pick, kit pick, list pick, pallet pick, or replenishment pick. |
| Base Priority | Number representing the priority of this type of work operation when it is first sent to the work queue. The lower the number, the higher the initial priority of this type of work operation. |
| Use Source Work Area | If Yes, priorities associated with the source work area are used to determine the attributes of a work request for this type of work operation.<br > If No, priorities associated with the destination work area are used to determine the attributes of a work request for this type of work operation. |
| Description | Text that further describes the work operation. |
| Initial Creation Status | Status of the work at the time of creation.<br>-   • **Pending**: The work is allocated and released.
<br>-   • **Suspended**: The work is suspended and is not released.
<br>-   • **Locked**: The work is locked and does not release until the application finds an available pickface location. This status is used with the demand replenishment operation (PIARPL) to prevent work from being released until there is room in the location for the replenishment inventory. If you select the Locked status, then in the Release Work Command field, enter the server command that is used to release work when there is room in the location.
<br>-   •
    
    **Luminate Pending**: The work is allocated, released, and sent to Warehouse Execution System and Robotics Hub. This status (abbreviated as LUMI) is used to ensure that the tasks are not consumed immediately by RF, mobile app, or voice users. Tasks in this status are processed by Warehouse Execution System, and as a result, the work status and role information in the Work Management work queue are updated based on bot event messages received from Warehouse Execution System. The Luminate Pending status is used when Warehouse Management is integrated with Warehouse Execution System and Robotics Hub. See the _Warhouse Execution System and Robotics Hub User Guide_.
    
    <br>
    
    **Note**: If a task is created in Luminate Pending status but needs to be performed by an RF, mobile app, or voice user, then you can suspend and resume the task in the work queue. When you resume a suspended task, the task status changes to Pending, and a user can perform the work. However, if the status is changed to Pending, then the task status cannot be reverted to Luminate Pending.
    
    <br> |
| Release Work Command | Server command that helps determine whether there is available capacity at the pick location and, if there is, changes the status of the work from Locked to Pending. This allows the release of any work that currently fits into the location. Specify a command if you defined this work operation to be created in the Locked status. The application uses the release work command to change the status of the work from Locked to Pending so that it can be released. |
| Force Scan of Acknowledged Location | If Yes, then operators that perform this work operation are required to scan the source location after acknowledging the directed work.<br > If No, then operators are not required to scan the source location after acknowledging the directed work.<br > **Note**: This field is only available for directed work operations that require the user to acknowledge the source location. |
| Use Escalation Command | If Yes, the priority of a work operation is escalated based on the **Escalation Command** selection.<br > If No, the priority of a work operation is not escalated based on a selected command. |
| Escalation Command | Server command that tells the application how to escalate the priority of an operation based on the parameters of the command. |
| Begin | Day and time on which the priority for this type of directed work begins escalating. |
| End | Day and time on which the priority for this type of directed work stops escalating. |
| Escalation Time | Number of minutes that this type of work operation can exist in the work queue before its priority is automatically escalated. Each time this number of minutes elapses, the number representing the effective (current) priority of this type of work decreases by the escalation increment defined for the operation, thus escalating the priority of the work. |
| Escalation Increment | Amount the priority of this type of work operation increases each time the expiration time elapses. This number is subtracted from the number representing the effective (current) priority of the work each time the specified expiration time elapses, thus escalating the priority of the work. |
| Maximum Priority | Number representing the maximum priority to which this type of work operation can be escalated. The lower the number, the higher the priority that this type of work operation can reach. |
| Shipping Date Escalation | If Yes, the application uses the shipping escalation settings to determine whether the priority of directed work should be escalated based on the ship date escalation settings. This process is typically used with picking and inventory transfer operations associated with an outbound shipment. Select Yes if you want the priority of work to be escalated as the ship date approaches. If you set this field to Yes, then you must select a shipping date and configure the settings that determine when and to what priority the work is escalated.<br > If No, the application does not escalate priority based on a shipping date associated with the work. |
| Shipping Date Option | Type of date, as specified on a shipment, that determines when the priority of the work operation is escalated. This value is only effective if **Shipping Date Escalation** is set to Yes, and values for time and priority are defined by the **Escalation Settings**. Ship date escalation can be used for picking and inventory transfer operations associated with an outbound shipment.<br>-   • **Early Delivery Date**: Earliest date that the shipment may be delivered to the customer.
<br>-   • **Early Ship Date**: Earliest date that the shipment may be shipped to the customer.
<br>-   • **Late Delivery Date**: Latest date that the shipment may be delivered to the customer.
<br>-   • **Late Ship Date**: Latest date that the shipment may be shipped to the customer. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
