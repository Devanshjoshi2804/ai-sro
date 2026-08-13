---
title: "Procedures for picks and work assignments"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/procedures_for_picks_and_work_assignments.htm"
source: "/content/procedures_for_picks_and_work_assignments.htm"
toc_path:
  - "Warehouse Management"
  - "Shared functions"
  - "Waves and Picks"
  - "Procedures for picks and work assignments"
sections:
  - "Perform actions on picks"
  - "Reset unassigned picks"
  - "Reprint a pick label"
  - "Create work assignment"
  - "Remove a pick from a work assignment"
  - "View picks"
  - "View work assignment details"
  - "View carton pick details"
  - "Picks detail fields"
  - "Work Assignment detail fields"
  - "Carton Pick detail fields"
images: []
source_sha1: 65bf8f843d74df9b3d6380be976e26e3e92fa119
---
# Procedures for picks and work assignments

You can perform these procedures using the Waves and Picks page, which is accessible from the following modules: **Outbound Planner**, **Picking**, or **Production**.

## Perform actions on picks

1.  [View picks](#View_picks).
    
    **Note**: To perform some these actions on a work assignment, you may first need to click the identifier for the assignment in the **Operation** column to view the assignment details.
    
2.  In the grid, select the check box next to the pick work to manage.
3.  To cancel picks:
    1.  From the **Actions** drop-down list, select **Cancel Picks**. The Cancel Picks window is displayed.
    2.  From the **Select Cancel Code** drop-down list, select a reason for cancelling the pick.
    3.  To place the pick location in error, select the **Put locations in Error Status** check box. No picking or putaway can be performed in a location that is in error until the location is reset.
    4.  Click **OK**.
4.  To release picks:
    
    **IMPORTANT**: All piece picks of a carton pick must be released together to ensure that the application creates a carton pick successfully.
    
    1.  From the **Actions** drop-down list, select **Release Picks**. A confirmation message is displayed.
    2.  Click **OK**.
5.  To release held picks:
    1.  From the **Actions** drop-down list, select **Release Held Picks**. A confirmation message is displayed.
    2.  Click **OK**.
6.  To reset picks:
    
    **Note**: Resetting picks updates the picks from Error status to Pending status.
    
    1.  From the **Actions** drop-down list, select **Reset Picks**. A confirmation message is displayed.
    2.  Click **OK**.
7.  [Reprint a pick label](#Reprint_a_pick_label).
8.  [Create work assignment](#Create_work_assignment).
9.  To assign picks to a specific user:
    
    **Note**: If the pick is already assigned to a user role, this operation overrides it and assigns it to the selected user.
    
    1.  From the **Actions** drop-down list, select **Assign User**.
    2.  In the **Assign User** grid, select a user. If a user is currently logged into a workstation or device, a check mark is displayed under **Logged In** for the user.
    3.  Click **Select**. A confirmation message is displayed.
    4.  Click **OK**.
10.  To assign picks a specific role:
     
     **Note**: If the pick is already assigned to a user, this operation overrides it and assigns it to the selected user role.
     
     1.  From the **Actions** drop-down list, select **Assign Role**.
     2.  In the Assign Role grid, select a role.
     3.  Click **Select**. A confirmation message is displayed.
     4.  Click **OK**.
11.  To unassign picks from the assigned user or role:
     1.  From the **Actions** drop-down list, select **Unassign**. A confirmation message is displayed.
     2.  Click **Yes**. A confirmation message is displayed.
     3.  Click **OK**.
12.  To change the priority of picks:
     1.  From the **Actions** drop-down list, select **Change Priority**.
     2.  Under **Enter Priority Level**, enter a value in the text box.
     3.  Click **Save**.
13.  To suspend picks:
     1.  From the **Actions** drop-down list, select **Suspend Picks**. A confirmation message is displayed.
         
         **Note**: For work assignments, select **Suspend Work Assignment**; for carton picks, select **Suspend Work**.
         
     2.  Click **OK**.
14.  To resume picks:
     1.  From the **Actions** drop-down list, select **Resume Picks**. A confirmation message is displayed.
         
         **Note**: For work assignments, select **Suspend Work Assignment**; for carton picks, select **Suspend Work**.
         
     2.  Click **OK**.

## Reset unassigned picks

When a pick is cancelled using a cancel code with the **Work Assignments** field set to **A user will manually assign**, the pick is set to an Unassigned status. You can reset the unassigned pick to change its status to Pending which allows the application to release and include it in work assignment processing at the next opportunity.

1.  [View picks](#View_picks).
2.  From the **Quick Filters** drop-down list, select **Unassigned**.
3.  In the grid, select the check box next to the unassigned pick.
4.  From the **Actions** drop-down list, select **Reset Unassigned Picks**. A confirmation message is displayed.
5.  Click **OK**.

## Reprint a pick label

1.  Perform one of the following tasks:
    -   [View picks](#View_picks).
    -   [View work assignment details](#View_work_assignment_details).
    -   [View carton pick details](#View_carton_pick_details).
2.  In the grid, select the check box next to the pick.
3.  From the **Actions** drop-down list, select **Reprint**.
4.  Enter information in the following fields:
    
     
    | Field | Description |
    | --- | --- |
    | Label Format | Unique identifier for the label format. A label format is a specific instance of a label document type. |
    | Document Type | Unique identifier for the document type. A document type is the configuration for a type of report (such as a bill of lading) or type of label (such as for a pallet or storage location). |
    | Printer | Printer that will print the label. |
    | Locale | Identifier that determines the culture-specific attributes displayed or printed on the report or label. Culture-specific attributes include language, time and date formats, currency formats, and measurement unit system. |
    
5.  Under **Criteria**, enter information in the fields that are displayed based on the selected label format and document type.
6.  Click **Print**. A confirmation message is displayed.
7.  Click **OK**.

## Create work assignment

Work assignments are created using a work assignment rule or rule group. See [Work assignment rules](../../configuration/outbound/picking/work-assignments.md) and [Work assignment rule groups](../../configuration/outbound/picking/work-assignments.md).

1.  [View picks](#View_picks).
2.  From the **Actions** drop-down list, select **Create Work Assignment**. The Create Work Assignment window is displayed.
3.  Perform one of the following tasks:
    -   Select **Rules**, and then select a work assignment rule to create the assignment.
    -   Select **Groups**, and then select a work assignment rule group to create the assignment.
4.  Click **Create**. A confirmation message is displayed.

## Remove a pick from a work assignment

1.  [View picks](#View_picks).
2.  In the grid, in the **Operation** column, click the work assignment identifier. The work assignment details are displayed.
3.  In the grid, select the check box for the pick to remove from the work assignment.
4.  From the **Actions** drop-down list, select **Remove from Work Assignment**. A confirmation message is displayed.
    
    **Note**: If the pick cannot be removed from the work assignment, the displayed message includes the reason why the removal was not successful.
    
5.  Click **OK**.

## View picks

1.  To view picks from the Waves and Picks page:
    1.  View the Waves and Picks page.
        
        1.  Select one of the following modules: **Outbound Planner**, **Picking**, or **Production**.
            
        2.  Select **Waves and Picks**.
            
        
    2.  Select **Picks**.
2.   To view picks for a wave:
    1.  View Waves and Picks page and select **Waves**, or view a grid with a link for a wave.
        
        1.  Select one of the following modules: **Outbound Planner**, **Picking**, or **Production**.
            
        2.  Select **Waves and Picks**.
            
        
    2.  In the grid, click a wave, and then select **Picks**.
3.  To view picks for a load:
    1.  [View loads](../../outbound-planner/outbound/procedures-for-loads.md), or view a grid with a link for a load.
    2.  In the grid, click a load, and then select **Picks**.
4.  To view picks for a shipment:
    1.  [View shipments](../../outbound-planner/outbound/procedures-for-shipments.md), or view a grid with a link for a shipment.
    2.  In the grid, click a shipment, and then select **Picks**.
5.  To view picks for an order:
    1.  [View outbound orders](../../outbound-planner/outbound/procedures-for-orders.md), or view a grid with a link for an order.
    2.  In the grid, click an order, and then select **Picks**.

## View work assignment details

1.  [View picks](#View_picks).
2.  In the grid, in the **Operation** column, click the work assignment identifier. The work assignment details are displayed.
3.  View information in the [Work Assignment detail fields](#Work_assignment_detail_fields).

## View carton pick details

1.  Perform one of the following tasks:
    -   [View picks](#View_picks).
    -   [View work assignment details](#View_work_assignment_details).
2.  In the grid, in the **Operation** column, click the carton pick identifier. The carton pick details are displayed.
3.  View information in the [Carton Pick detail fields](#Carton_pick_detail_fields).

## Picks detail fields

 
| Field | Description |
| --- | --- |
| Pick Status | Current status of the pick.<br>-   • **Pending**: Pick work inventory is reserved for allocation until automatically released by the application.
<br>-   • **Hold**: Pick work inventory is reserved for allocation until manually released by a user.
<br>-   • **Released**: Pick work is released to the work queue.
<br>-   • **Complete**: Pick work is complete.
<br>-   • **Un-Assigned**: Pick work is unassigned from a work assignment.
<br>-   • **Ready For List**: Pick work has been released and the pick is qualified for a work assignment. A background process builds these picks into either a handling unit-based or regular work assignment.
<br>-   • **Error**: Pre-manifesting the package for the pick work failed. The application allows packages to be pre-manifested; that is, manifested to hold. These packages are typically manifested during allocation (before the inventory is picked) and usually so that a label can be printed in advance for the package. You can view the specific error code and description on the Waves and Picks page. See [Waves and Picks](../waves-and-picks.md). |
| Operation | Work operation that identifies the type of directed work that was created. |
| Source | Location where the work originated, such as the location from which inventory is picked, at which a count is performed, or from which transport equipment is moved. |
| Destination | Location where the work is completed, such as the location to which inventory is delivered or to which transport equipment is moved. |
| Load | Unique identifier for a load. A load is one or more shipments grouped together into one or more stops that are shipped on a single piece of transport equipment. |
| Shipment | Unique identifier for an outbound shipment. A shipment is a group of orders or order lines that are allocated together and shipped to the same location. |
| Order | Unique number that identifies an order. An order is a request for a supply of material or product. |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Description | Description of the item involved in the pick that further describes the inventory. |
| User | User that is assigned to perform the work or, if the work has been acknowledged, the user that signed on to perform the work. |
| Role | Role that is assigned to the work. A role is a category that is used to group menu options for the purpose of maintaining user authorizations. Roles are assigned to the appropriate users to control the tasks that users are authorized to perform. |
| Pick Priority | Current priority of directed work in the work queue. This value represents the base priority defined for the operation plus any escalation increments that have been applied over time to the work request. For example, if the base priority of work is 20 and it is defined to escalate by 5 every hour, then after 2 hours it has an effective (current) priority of 10. The value for Priority is green if the value has been escalated from the base priority defined for the work operation.<br > The lowest number has the highest priority. For example, 1 is the highest priority; 10 is a higher priority than 20. |
| Pick Quantity | Quantity (in terms of material handling or stock keeping units) of the item that should be picked based on the order, work order, or replenishment. |
| Picked Quantity | Quantity (in terms of material handling or stock keeping units) of inventory that is picked based on the order, work order, or replenishment. |
| Pick UOM | Unit of measure in which the **Pick Quantity** is displayed. |
| Work ID | Unique application-assigned identifier for a piece of work in the work queue. |
| Work Status | Current status of the work.<br>-   • **Undirected**: The work is undirected; this means that a user can perform it from a workstation, or an RF operator can perform it using an undirected work menu option. Undirected work is not available to be performed through the RF Directed Work menu option.
<br>-   • **Pending**: The directed work has been allocated and released to the queue. Work in this status will be offered to an operator through the RF Directed Work function, based on permissions, priority, and proximity.
<br>-   • **Waiting**: The directed work is assigned to an operator, but the operator has not acknowledged it yet.
<br>-   • **Acknowledged**: The directed work has been acknowledged (accepted) by an operator.
<br>-   • **Suspended**: The directed work is temporarily suspended, indicating that the application will not offer it an operator through the RF Directed Work function.
<br>-   • **Locked**: The directed work is locked and is not released until the application finds an available pickface location. This status is used with the demand replenishment operation (PIARPL) to prevent work from being released until there is room in the location for the replenishment inventory. |
| Work Order | Identifier for a work order. A work order is an internal order used to find, allocate, and deliver product to a work-in-process area for assembly or disassembly, conversion, kitting, or repackaging. |
| Work Order Revision | Identifier for one instance of a work order that allows you to use a standard work order multiple times. |
| Work Order Line | Unique identifier for a work order line. The number corresponds to the order line's position in the work order. |
| Picked Catch Quantity | Quantity (in terms of material handling or stock keeping units) of inventory that is picked based on the catch unit measurements for the order, work order, or replenishment. |
| Order Line | Unique number that identifies the order line. The number corresponds to the line's position on the order. The first order line is automatically assigned a line number of 0001. Additional order lines are then automatically numbered sequentially, beginning with 0002. |
| Handling Unit Type | Category that classifies a group of handling units (for example, pallets, totes, transport equipment, or vehicles) that share the same characteristics such as size and weight, as well as whether they are serialized, temporary, or considered a container. The application tracks the on-hand quantity of handling units by type and, for serialized handling units, by handling unit identifier. |
| Date Completed | Date and time when the picking operator completed picking inventory to fulfill the order. |
| Lot Tracked | Indicates whether the item is lot tracked (**Lot Tracking** field set to Yes in the item configuration). A lot is a batch (quantity) of an item uniquely identified by a lot number during the manufacturing process for the purpose of tracking that batch of inventory. |
| Origin Tracked | Indicates whether the item is tracked by its origin (**Origin Code** field set to Yes in the item configuration). The origin code is typically an identifier for the country or area of the world in which the item was manufactured. |
| Revision Tracked | Indicates whether the item is revision tracked (**Revision** field set to Yes in the item configuration). A revision may be used to identify a specific manufactured version of the item, so that when the item is modified or improved, the manufacturer may assign a new version number to reflect the change. |
| Carton Number | Unique identifier assigned to the carton into which inventory is picked. |

## Work Assignment detail fields

 
| Field | Description |
| --- | --- |
| Wave | Value that is assigned to the group of pick-type work requests (picks, replenishments, and cross docks) that are created when the wave is planned. The wave name distinguishes one group of pick-type work requests from another, which enables you to track the requests through the application. For example, if you allocate inventory for a single shipment, then all of the picks, replenishments, and cross docks generated for the shipment have the same wave name. |
| Added | Date and time at which the work assignment was created. |
| Work Status | Current status of the work.<br>-   • **Undirected**: The work is undirected; this means that a user can perform it from a workstation, or an RF operator can perform it using an undirected work menu option. Undirected work is not available to be performed through the RF Directed Work menu option.
<br>-   • **Pending**: The directed work has been allocated and released to the queue. Work in this status will be offered to an operator through the RF Directed Work function, based on permissions, priority, and proximity.
<br>-   • **Waiting**: The directed work is assigned to an operator, but the operator has not acknowledged it yet.
<br>-   • **Acknowledged**: The directed work has been acknowledged (accepted) by an operator.
<br>-   • **Suspended**: The directed work is temporarily suspended, indicating that the application will not offer it an operator through the RF Directed Work function.
<br>-   • **Locked**: The directed work is locked and is not released until the application finds an available pickface location. This status is used with the demand replenishment operation (PIARPL) to prevent work from being released until there is room in the location for the replenishment inventory. |
| Pick Status | Current status of the pick.<br>-   • **Pending**: Pick work inventory is reserved for allocation until automatically released by the application.
<br>-   • **Hold**: Pick work inventory is reserved for allocation until manually released by a user.
<br>-   • **Released**: Pick work is released to the work queue.
<br>-   • **Complete**: Pick work is complete.
<br>-   • **Un-Assigned**: Pick work is unassigned from a work assignment.
<br>-   • **Ready For List**: Pick work has been released and the pick is qualified for a work assignment. A background process builds these picks into either a handling unit-based or regular work assignment.
<br>-   • **Error**: Pre-manifesting the package for the pick work failed. The application allows packages to be pre-manifested; that is, manifested to hold. These packages are typically manifested during allocation (before the inventory is picked) and usually so that a label can be printed in advance for the package. You can view the specific error code and description on the Waves and Picks page. See [Waves and Picks](../waves-and-picks.md). |
| Effective Priority | Current priority of a work request in the work queue. This value represents the base priority defined for the operation plus any escalation increments that have been applied over time to the work request. For example, if the base priority of pick work is 20 and it is defined to escalate by 5 every hour, then after 2 hours it will have an effective (current) priority of 10. |
| Assigned User | User that is assigned to perform the work or, if the work has been acknowledged, the user that signed on to perform the work. |
| Role | Role that is assigned to the work. A role is a category that is used to group menu options for the purpose of maintaining user authorizations. Roles are assigned to the appropriate users to control the tasks that users are authorized to perform. |
| Progress | Percentage of inventory that has been picked. Additionally, an X of Y value displays the number of eaches that are picked out of the total number of expected eaches; for example, (50 of 100). |
| Operation | Work operation that identifies the type of directed work that was created. |
| Source | Location where the work originated, such as the location from which inventory is picked, at which a count is performed, or from which transport equipment is moved. |
| Destination | Location where the work is completed, such as the location to which inventory is delivered or to which transport equipment is moved. |
| Load | Unique identifier for a load. A load is one or more shipments grouped together into one or more stops that are shipped on a single piece of transport equipment. |
| Shipment | Unique identifier for an outbound shipment. A shipment is a group of orders or order lines that are allocated together and shipped to the same location. |
| Order | Unique number that identifies an order. An order is a request for a supply of material or product. |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Pick Quantity | Quantity (in terms of material handling or stock keeping units) of the item that should be picked based on the order, work order, or replenishment. |
| Picked Quantity | Quantity (in terms of material handling or stock keeping units) of inventory that is picked based on the order, work order, or replenishment. |
| Pick UOM | Unit of measure in which the **Pick Quantity** is displayed. |
| Work ID | Unique application-assigned identifier for a piece of work in the work queue. |

## Carton Pick detail fields

 
| Field | Description |
| --- | --- |
| Wave | Value that is assigned to the group of pick-type work requests (picks, replenishments, and cross docks) that are created when the wave is planned. The wave name distinguishes one group of pick-type work requests from another, which enables you to track the requests through the application. For example, if you allocate inventory for a single shipment, then all of the picks, replenishments, and cross docks generated for the shipment have the same wave name. |
| Pick Status | Current status of the pick.<br>-   • **Pending**: Pick work inventory is reserved for allocation until automatically released by the application.
<br>-   • **Hold**: Pick work inventory is reserved for allocation until manually released by a user.
<br>-   • **Released**: Pick work is released to the work queue.
<br>-   • **Complete**: Pick work is complete.
<br>-   • **Un-Assigned**: Pick work is unassigned from a work assignment.
<br>-   • **Ready For List**: Pick work has been released and the pick is qualified for a work assignment. A background process builds these picks into either a handling unit-based or regular work assignment.
<br>-   • **Error**: Pre-manifesting the package for the pick work failed. The application allows packages to be pre-manifested; that is, manifested to hold. These packages are typically manifested during allocation (before the inventory is picked) and usually so that a label can be printed in advance for the package. You can view the specific error code and description on the Waves and Picks page. See [Waves and Picks](../waves-and-picks.md). |
| Carton Status | Current status of the carton.<br>-   • **Complete**: All inventory intended for the carton has been picked to the carton.
<br>-   • **In Process**: Inventory has been allocated to the carton and picking has been started.
<br>-   • **Pending**: Inventory has been allocated to the carton, but picking has not been started. |
| Work Status | Current status of the work.<br>-   • **Undirected**: The work is undirected; this means that a user can perform it from a workstation, or an RF operator can perform it using an undirected work menu option. Undirected work is not available to be performed through the RF Directed Work menu option.
<br>-   • **Pending**: The directed work has been allocated and released to the queue. Work in this status will be offered to an operator through the RF Directed Work function, based on permissions, priority, and proximity.
<br>-   • **Waiting**: The directed work is assigned to an operator, but the operator has not acknowledged it yet.
<br>-   • **Acknowledged**: The directed work has been acknowledged (accepted) by an operator.
<br>-   • **Suspended**: The directed work is temporarily suspended, indicating that the application will not offer it an operator through the RF Directed Work function.
<br>-   • **Locked**: The directed work is locked and is not released until the application finds an available pickface location. This status is used with the demand replenishment operation (PIARPL) to prevent work from being released until there is room in the location for the replenishment inventory. |
| Added | Date and time at which the carton pick was created. |
| Effective Priority | Current priority of a work request in the work queue. This value represents the base priority defined for the operation plus any escalation increments that have been applied over time to the work request. For example, if the base priority of pick work is 20 and it is defined to escalate by 5 every hour, then after 2 hours it will have an effective (current) priority of 10. |
| Assigned User | User that is assigned to perform the work or, if the work has been acknowledged, the user that signed on to perform the work. |
| Role | Role that is assigned to the work. A role is a category that is used to group menu options for the purpose of maintaining user authorizations. Roles are assigned to the appropriate users to control the tasks that users are authorized to perform. |
| Progress | Percentage of inventory that has been picked. Additionally, an X of Y value displays the number of eaches that are picked out of the total number of expected eaches; for example, (50 of 100). |
| Source | Location where the work originated, such as the location from which inventory is picked, at which a count is performed, or from which transport equipment is moved. |
| Destination | Location where the work is completed, such as the location to which inventory is delivered or to which transport equipment is moved. |
| Work ID | Unique application-assigned identifier for a piece of work in the work queue. |
| Carton Number | Unique identifier assigned to the carton into which inventory is picked. |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Description | Description of the item involved in the pick that further describes the inventory. |
| Pick Quantity | Quantity (in terms of material handling or stock keeping units) of the item that should be picked based on the order, work order, or replenishment. |
| Picked Quantity | Quantity (in terms of material handling or stock keeping units) of inventory that is picked based on the order, work order, or replenishment. |
| Pick UOM | Unit of measure in which the **Pick Quantity** is displayed. |
| Load | Unique identifier for a load. A load is one or more shipments grouped together into one or more stops that are shipped on a single piece of transport equipment. |
| Shipment | Unique identifier for an outbound shipment. A shipment is a group of orders or order lines that are allocated together and shipped to the same location. |
| Order | Unique number that identifies an order. An order is a request for a supply of material or product. |
| Carton Type | Code that identifies the type of carton. A carton type defines the dimensions and attributes that identify what the carton can hold and how the carton is used. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
