---
title: "Procedures for work queue"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/procedures_for_work_queue.htm"
source: "/content/procedures_for_work_queue.htm"
toc_path:
  - "Warehouse Management"
  - "Shared functions"
  - "Work Queue"
  - "Procedures for work queue"
sections:
  - "Manage the work queue"
  - "Assign a manual work sequence"
  - "View ineligible work"
  - "View work in the work queue"
  - "View the work queue summary"
  - "Work Queue fields"
  - "Work Queue Summary fields"
  - "Ineligible Work fields"
images: []
source_sha1: b64517914c93246ecb9b26ec5b5b4d274d996655
---
# Procedures for work queue

You can perform these procedures using the Work Queue page, which is accessible from the following modules: **Inventory**, **Outbound Planner**, **Picking**, **Production**, **Receiving**, **Shipping**, or **Yard**.

## Manage the work queue

1.  View the Work Queue page.
    
    1.  Select one of the following modules: **Inventory**, **Outbound Planner**, **Picking**, **Production**, **Receiving**, **Shipping**, or **Yard**.
        
    2.  Select **Work Queue**.
        
    
2.  To limit the work queue entries that are displayed, enter search criteria, or from the **Quick Filters** drop-down list, select a filter.
3.  To assign directed work to a specific user:
    
    **Note**: If the work is already assigned to a user role, this operation overrides it and assigns it to the selected user.
    
    1.  In the grid, select the check box next to the work to assign.
    2.  From the **Actions** drop-down list, select **Assign User**.
    3.  In the **Assign User** grid, select a user. If a user is currently logged into a workstation or device, a check mark is displayed in the **Logged In** column for the user.
    4.  Click **Select**. A confirmation message is displayed.
    5.  Click **OK**.
4.  To assign directed work to a specific role:
    
    **Note**: If the work is already assigned to a user, this operation overrides it and assigns it to the selected user role.
    
    1.  In the grid, select the check box next to the work to assign.
    2.  From the **Actions** drop-down list, select **Assign Role**.
    3.  In the **Assign Role** grid, select a role.
    4.  Click **Select**. A confirmation message is displayed.
    5.  Click **OK**.
5.  To unassign directed work from the assigned user or role:
    1.  In the grid, select the check box next to the work to unassign.
    2.  From the **Actions** drop-down list, select **Unassign**. A confirmation message is displayed.
    3.  Click **OK**.
6.  To change the priority of work:
    
    **Note**: The value for Priority is green if the value is higher than the base priority defined for the work operation. The base priority represents the priority at which work enters the work queue. Priority can be escalated manually by a user or automatically by the application. See [Priority escalation processes](../../configuration/work/work/work-operations.md).
    
    1.  In the grid, select the check box next to the work to change.
    2.  From the **Actions** drop-down list, select **Change Priority**.
    3.  Under **Enter Priority Level**, or enter a value in the text box.
    4.  Click **Save**.
7.  To resume suspended directed work:
    1.  In the grid, select the check box next to the work to resume.
    2.  From the **Actions** drop-down list, select **Resume Work**. A confirmation message is displayed.
    3.  Click **OK**.
8.  To suspend directed work:
    1.  In the grid, select the check box next to the work to suspend.
    2.  From the **Actions** drop-down list, select **Suspend Work**. A confirmation message is displayed.
    3.  Click **OK**.
9.  To unlock directed work:
    1.  In the grid, select the check box next to the work to unlock.
    2.  From the **Actions** drop-down list, select **Unlock Work**. A confirmation message is displayed.
    3.  Click **OK**.
10.  To cancel directed work:
     
     **Note**: When you cancel the directed work for a pick or count, the work remains in the queue as undirected work. If the cancelled directed work is not a pick or count, the work entry is removed from the application.
     
     1.  In the grid, select the check box next to the work to cancel.
     2.  From the **Actions** drop-down list, select **Cancel Work**. A confirmation message is displayed.
     3.  Click **OK**.
11.  To cancel picks:
     
     **Note**: When you cancel a pick, the work is removed from the work queue and is no longer available as directed or undirected work in the application.
     
     1.  In the grid, select the check box next to the pick work to cancel.
     2.  From the **Actions** drop-down list, select **Cancel Picks**. The Cancel Picks window is displayed.
     3.  From the **Select Cancel Code** drop-down list, select a reason for cancelling the pick.
     4.  To place the pick location in error, select the **Put locations in Error Status** check box. No picking or putaway can be performed in a location that is in error until the location is reset. See [Set or reset a location error status](../inventory/procedures-for-locations.md).
     5.  Click **OK**.

## Assign a manual work sequence

You can assign a manual sequence to pieces of work when outbound work sequencing is enabled for the warehouse, when the selected work is in Locked status, and when the load associated with the work is assigned the manual work sequence release type. See [Outbound work sequencing](../../configuration/outbound/shipping/outbound-staging.md). You can use the Manual Sequencing quick filter on the Work Queue page to display the work to which a manual sequence number can be assigned.

The application initially locks all work for a load with the manual release type, and unlocks it based on the manual work release sequence assigned to each piece of pick work, with the lowest sequence released first. At any time, the application will start or resume unlocking work only when there is a manual work release sequence assigned to each piece of work for a load with the manual release type.

1.  View the Work Queue page.
    
    1.  Select one of the following modules: **Inventory**, **Outbound Planner**, **Picking**, **Production**, **Receiving**, **Shipping**, or **Yard**.
        
    2.  Select **Work Queue**.
        
    
2.  To limit the work queue entries that are displayed, enter search criteria, or from the **Quick Filters** drop-down list, select a filter.
3.  In the grid, select the check box next to the work.
    
    **Note**: You can select multiple pieces of work by selecting each check box.
    
4.  From the **Actions** drop-down list, select **Assign Manual Sequence**. The Manual Work Sequence window is displayed.
5.  Enter the sequence number.
    
    **Note**: You can enter a manual work release sequence between 0 and 999999999. You can change the manual sequence for a piece of work to any value until all work for a load has an assigned sequence. At that point, work sequences can only be updated to a value that is higher than the lowest sequence number for a load; you cannot change a work sequence to be the same or lower (higher priority) than the current lowest sequenced work for the load.
    
6.  Click **Apply**. A confirmation message with the status of the manual sequence assigned is displayed.
7.  Click **OK**.

## View ineligible work

You can view ineligible work to determine why RF directed work is not offered to a particular user (RF operator) that is logged into the application on a particular device. Ineligible work can also apply to voice devices. See [Ineligible work](../work-queue.md).

1.  View the Work Queue page.
    
    1.  Select one of the following modules: **Inventory**, **Outbound Planner**, **Picking**, **Production**, **Receiving**, **Shipping**, or **Yard**.
        
    2.  Select **Work Queue**.
        
    
2.  From the **Actions** drop-down list, select **Ineligible Work**.
3.  In the **Device** field, enter or select an identifier for an RF device. The username of the user who is currently logged into the device is populated in the **User** field.
4.  To populate the **Device** field based on a specific user, in the **User** field, enter or select an identifier for a user that is currently logged into an RF device. The associated device code is populated in the **Device** field.
5.  Click **Search**.
6.  View the information in the [Ineligible Work fields](#Ineligible_Work_fields).
7.  To reset the search criteria and results, click **Clear**.

## View work in the work queue

1.  View the Work Queue page.
    
    1.  Select one of the following modules: **Inventory**, **Outbound Planner**, **Picking**, **Production**, **Receiving**, **Shipping**, or **Yard**.
        
    2.  Select **Work Queue**.
        
    
2.  Select **Work**.
3.  To limit the work queue entries that are displayed, enter search criteria, or from the **Quick Filters** drop-down list, select a filter.
4.  View the information in the [Work Queue fields](#Work_Queue_fields).

## View the work queue summary

1.  View the Work Queue page.
    
    1.  Select one of the following modules: **Inventory**, **Outbound Planner**, **Picking**, **Production**, **Receiving**, **Shipping**, or **Yard**.
        
    2.  Select **Work Queue**.
        
    
2.  Select **Summary**.
3.  View the information in the [Work Queue Summary fields](#Work_queue_summary_fields).
    
    **Note**: The right side of the work queue summary grid displays the work areas in the warehouse, and the number of work queue entries in the areas for each operation.
    
4.  To view the details for a group of work queue entries by work area, operation, and status, click the number of work queue entries. The Work tab is displayed and shows the work details.
    

## Work Queue fields

 
| Field | Description |
| --- | --- |
| Work Added | Date and time when the work was added to the work queue. |
| Work Status | Current status of the work.<br>-   • **Undirected**: The work is undirected; this means that a user can perform it from a workstation, or an RF operator can perform it using an undirected work menu option. Undirected work is not available to be performed through the RF Directed Work menu option.
<br>-   • **Pending**: The directed work has been allocated and released to the queue. Work in this status will be offered to an operator through the RF Directed Work function, based on permissions, priority, and proximity.
<br>-   • **Waiting**: The directed work is assigned to an operator, but the operator has not acknowledged it yet.
<br>-   • **Acknowledged**: The directed work has been acknowledged (accepted) by an operator.
<br>-   • **Suspended**: The directed work is temporarily suspended, indicating that the application will not offer it an operator through the RF Directed Work function.
<br>-   • **Locked**: The directed work is locked and is not released until the application finds an available pickface location. This status is used with the demand replenishment operation (PIARPL) to prevent work from being released until there is room in the location for the replenishment inventory. |
| Operation | Work operation that identifies the type of directed work that was created. |
| Priority | Current priority of directed work in the work queue. This value represents the base priority defined for the operation plus any escalation increments that have been applied over time to the work request. For example, if the base priority of work is 20 and it is defined to escalate by 5 every hour, then after 2 hours it has an effective (current) priority of 10. The value for Priority is green if the value has been escalated from the base priority defined for the work operation.<br > The lowest number has the highest priority. For example, 1 is the highest priority; 10 is a higher priority than 20. |
| Wave | Value that is assigned to the group of pick-type work requests (picks, replenishments, and cross docks) that are created when the wave is planned. The wave name distinguishes one group of pick-type work requests from another, which enables you to track the requests through the application. For example, if you allocate inventory for a single shipment, then all of the picks, replenishments, and cross docks generated for the shipment have the same wave name. |
| Count Group | Identifier for a group of counts. |
| Load | Unique identifier for a load. A load is one or more shipments grouped together into one or more stops that are shipped on a single piece of transport equipment. |
| Shipment | Unique identifier for an outbound shipment. A shipment is a group of orders or order lines that are allocated together and shipped to the same location. |
| Outbound Order | Unique identifier for an outbound order. An order is a request for a supply of material or product. |
| Work Zone | Name or number that identifies a work zone. A work zone is a logical division of warehouse space made on the basis of physical layout and access by different types of warehouse equipment. A work zone exists inside a work area. |
| Work Area | Unique identifier for a work area. A work area consists of a number of work zones. For the purpose of work management, area of the warehouse in which similar types of operations are performed. For example, narrow-aisle storage and floor storage can be configured as different work areas if each supports different types of operations and different types of equipment. |
| Assigned User | User that is assigned to perform the work or, if the work has been acknowledged, the user that signed on to perform the work. |
| Source | Location where the work originated, such as the location from which inventory is picked, at which a count is performed, or from which transport equipment is moved. |
| Destination | Location where the work is completed, such as the location to which inventory is delivered or to which transport equipment is moved. |
| LPN | Unique identifier for an LPN of inventory associated with the work in the queue. |
| Role | Role that is assigned to the work. A role is a category that is used to group menu options for the purpose of maintaining user authorizations. Roles are assigned to the appropriate users to control the tasks that users are authorized to perform. |
| Acknowledged User | Unique identifier for the user that acknowledged (signed on to perform) a piece of work. |
| Acknowledged Device | Unique identifier for a piece of equipment, such as a radio frequency terminal or voice device, with which the user acknowledged (signed on to perform) the work. |
| Work | Unique application-assigned identifier for a piece of work in the work queue. |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Description | Text that further describes the item. |
| Client | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. |
| Pick Quantity | Quantity (in terms of material handling or stock keeping units) of the item that should be picked based on the order, work order, or replenishment. |
| Picked Quantity | Quantity (in terms of material handling or stock keeping units) of inventory that is picked based on the order, work order, or replenishment. |
| Pick UOM | Unit of measure in which the **Pick Quantity** is displayed. |
| Work Order | Identifier for a work order. A work order is an internal order used to find, allocate, and deliver product to a work-in-process area for assembly or disassembly, conversion, kitting, or repackaging. |
| Work Order Revision | Identifier for one instance of a work order that allows you to use a standard work order multiple times. |
| Inbound Shipment | Unique identifier used for inventory tracking for an inbound shipment of inventory. An inbound shipment is a group of orders that are transported to the warehouse together or received together. When inventory arrives at the warehouse on a piece of transport equipment, an inbound shipment represents the contents of the transport equipment; however, one or more inbound shipments can be associated with a piece of transport equipment. |
| Planned Inbound Order | Identifier for a planned inbound order that is associated with a specific supplier. A planned inbound order is an authorization to receive specific inventory and quantities from a supplier. It is used, but not required, to receive inventory into the warehouse. |
| Work Request | Unique application-assigned identifier for work that resides in the work queue. This is used for tracking purposes. For example, when pick work or a transport equipment move is released to the work queue, the application assigns a work request to each pick and transport equipment move. When work is completed, the work request is deleted from the work queue. |
| Customer PO | Number that identifies the customer's purchase order. |
| Date Added | Date on which the work was added to the work queue. |
| Date Acknowledged | Date on which the work was acknowledged (signed on to be performed) by a user. |
| Date Deposited | Date on which the inventory was deposited into the destination location for a piece of work. |
| Date Issued | Date and time the work was issued. |
| Date Picked | Date on which the product was picked or moved from the source location for a piece of work. |
| Label Batch | Unique identifier for a group of picks that belong to the same label batch. The label batch is assigned at pick release when labels are printed. |
| Label Sequence | Order in which picks will print on pick labels. Order can be determined by source location, destination location, or item. |
| Last Escalation Date | Date that the priority of the piece of work was last escalated. |
| Location Access | Code that classifies a location for work management purposes. The application uses location access codes to permit or restrict warehouse equipment type access to a location when performing directed work. Warehouse equipment will not be assigned directed work in locations that do not have a matching location access group. The access group for warehouse equipment is specified in the web client. |
| LPN Level | Packaging level at which inventory is tracked. |
| Pallet Control Work | If Pallet & Load Optimization is installed and enabled, indicates that a piece of work is associated with a Pallet & Load Optimization generated plan. |
| Pick Exception | Indicates that the pick is part of a work assignment for which some of the work allocated short; that is, there are outstanding replenishments on the assignment. When inventory for a work assignment is allocated, and some of the inventory required for picks on the assignment is unavailable, then the **Pick Exception** check box is selected for all of the picks (pick work) on the work assignment. |
| Source Aisle ID | Unique identifier for the aisle in which a piece of work originates, such as the aisle from which inventory is picked or at which a count is performed. |
| Source Building ID | Unique identifier for the building in which a piece of work originates, such as the building in which inventory is picked, in which a count is performed, or from which a piece of transport equipment is moved. |
| Source Work Zone | Reference Location Identifier for the work zone in which the work originates. A work zone is a logical division of warehouse space made on the basis of physical layout and access by different types of warehouse equipment. A work zone exists inside a work area. |
| Reference Location | For work related to an LPN associated with transport equipment, this is the unique number that identifies the stop (stop ID). For work related to a transport equipment move, this is the alphanumeric identifier of the transport equipment (transport equipment number). |
| Work Assignment | Unique identifier that the application assigns to a work assignment when the assignment is created. A work assignment is a list of individual picks that an operator can perform in one picking tour, moving from one pick location to another until the assignment is complete. |
| Work Type | Type of pick work.<br>-   • **Bulk Pick**: Work type used to perform bulk picks.
<br>-   • **Demand Replenishment**: Replenishment work type generated when pre-inventory allocation is enabled and a pick location does not have inventory to complete an order. The application generates demand-based replenishments from reserve storage locations to the pick locations, and then generates picks based on the inventory pending to the pick locations.
<br>-   • **Emergency Replenishment**: Replenishment work type generated automatically when there is insufficient inventory in a pick zone to satisfy a shipment line.
<br>-   • **Kit**: Work type used to pick component items to fill a work order.
<br>-   • **Manual Replenishment**: Replenishment work type initiated by an operator for a specific location.
<br>-   • **Pick**: Work type used to pick inventory to fill an order.
<br>-   • **Replenishment**: Work type used to fill a pickface location with inventory from a storage location.
<br>-   • **Stage Transfer**: Pick work generated to transfer inventory typically from a cross docking location to a staging lane.
<br>-   • **Top-off Replenishment**: Replenishment work type generated automatically at timed intervals.
<br>-   • **Triggered Replenishment**: Replenishment work type generated automatically when an item in a zone or a location has dropped below a user-defined level. |
| Zone Travel Sequence | Numeric value, ranging from low to high, that identifies the travel sequence from one work zone to another, regardless of work area boundaries. Movement from one work zone to another is accomplished through the use of travel sequence assignments. |
| Location Travel Sequence | Value that identifies the proximity of one location to another. Movement from one location to another is accomplished through the use of travel sequence assignments, which are alphanumeric and range from low to high. |
| Item Family | Item family associated with the work for outbound work sequencing. See [Outbound work sequencing](../../configuration/outbound/shipping/outbound-staging.md). |
| Volume | Total cubic volume of the items in the work. The total cubic volume of the items in the work is calculated using the formula Volume of pick UOM x Number of units in pick UOM. Number of units in pick UOM can be calculated using the formula Pick quantity in the stocking (unit) UOM / Stocking units per pick UOM. For example, if the pick quantity in the stocking (unit) UOM is 100, pick UOM is case and stocking units per pick UOM (case) is 10, then the Number of units in pick UOM = (100/10) = 10 cases.<br > The volume for pick UOM can be calculated using the formula Length x Width x Height of pick UOM. For example, if pick UOM is case and the length, width and height of pick UOM is 5 inches each, then the Volume of a case = (5 inches x 5 inches x 5 inches) = 125 cubic inches per case. Total cubic volume of the items in the work is then 10 cases x 125 cubic inches per case = 1250 cubic inches. |
| Weight | Total weight of the items in the work. The total weight is calculated using the formula Gross weight for pick UOM x Number of units in pick UOM. Number of units in pick UOM can be calculated using the formula Pick quantity in the stocking (unit) UOM / Stocking units per pick UOM. For example, if the pick quantity in the stocking (unit) UOM is 100, pick UOM is case and stocking units per pick UOM (case) is 10, then Number of units in pick UOM = (100/10) = 10 cases. If gross weight for pick UOM (case) is 50 lb, then the total weight is (50 lb per case ´ 10 cases) = 500 lb. |
| Customer | Name used to identify a business to whom you ship inventory. Each customer has a profile that is used to define how their inventory is handled, how their orders are processed, and how their inventory is shipped. |
| Manual Work Sequence | The work sequence number assigned to the work for manual outbound work sequencing. See [Outbound work sequencing](../../configuration/outbound/shipping/outbound-staging.md). |
| Stop | Unique identifier for a stop. A stop is a collection of one or more outbound shipments making up a delivery to a single customer. |

## Work Queue Summary fields

 
| Field | Description |
| --- | --- |
| Operation | Work operation that identifies the type of directed work that was created. |
| Status | Current status of the work.<br>-   • **Undirected**: The work is undirected; this means that a user can perform it from a workstation, or an RF operator can perform it using an undirected work menu option. Undirected work is not available to be performed through the RF Directed Work menu option.
<br>-   • **Pending**: The directed work has been allocated and released to the queue. Work in this status will be offered to an operator through the RF Directed Work function, based on permissions, priority, and proximity.
<br>-   • **Waiting**: The directed work is assigned to an operator, but the operator has not acknowledged it yet.
<br>-   • **Acknowledged**: The directed work has been acknowledged (accepted) by an operator.
<br>-   • **Suspended**: The directed work is temporarily suspended, indicating that the application will not offer it an operator through the RF Directed Work function.
<br>-   • **Locked**: The directed work is locked and is not released until the application finds an available pickface location. This status is used with the demand replenishment operation (PIARPL) to prevent work from being released until there is room in the location for the replenishment inventory. |
| Total Work | Total number of work queue entries for a work operation in a specific status. |

## Ineligible Work fields

 
| Field | Description |
| --- | --- |
| Work Request | Unique application-assigned identifier for work that resides in the work queue. This is used for tracking purposes. For example, when pick work or a transport equipment move is released to the work queue, the application assigns a work request to each pick and transport equipment move. When work is completed, the work request is deleted from the work queue. |
| Operation | Work operation that identifies the type of directed work that was created. |
| Source Work Zone | Reference Location Identifier for the work zone in which the work originates. A work zone is a logical division of warehouse space made on the basis of physical layout and access by different types of warehouse equipment. A work zone exists inside a work area. |
| Aisle | Identifier for a passageway in the facility where operators and equipment move between racks or blocks of locations to pick inventory. |
| Building | Name of the building in which the zone resides. |
| Source Location | Location where the work originated, such as the location from which inventory is picked, at which a count is performed, or from which transport equipment is moved. |
| Source Work Area | Identifier for the work area in which the work originates. A work area consists of a number of work zones. For the purpose of work management, area of the warehouse in which similar types of operations are performed. For example, narrow-aisle storage and floor storage can be configured as different work areas if each supports different types of operations and different types of equipment. |
| Work Status | Current status of the work.<br>-   • **Undirected**: The work is undirected; this means that a user can perform it from a workstation, or an RF operator can perform it using an undirected work menu option. Undirected work is not available to be performed through the RF Directed Work menu option.
<br>-   • **Pending**: The directed work has been allocated and released to the queue. Work in this status will be offered to an operator through the RF Directed Work function, based on permissions, priority, and proximity.
<br>-   • **Waiting**: The directed work is assigned to an operator, but the operator has not acknowledged it yet.
<br>-   • **Acknowledged**: The directed work has been acknowledged (accepted) by an operator.
<br>-   • **Suspended**: The directed work is temporarily suspended, indicating that the application will not offer it an operator through the RF Directed Work function.
<br>-   • **Locked**: The directed work is locked and is not released until the application finds an available pickface location. This status is used with the demand replenishment operation (PIARPL) to prevent work from being released until there is room in the location for the replenishment inventory. |
| Reason | Reason why directed work is not offered to a particular user (RF or voice operator) that is logged into the application on a particular device. If the application indicates that a user is ineligible for a work request, the work request is not offered to the user until the reasons for ineligible work are resolved. See [Ineligible work](../work-queue.md). |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
