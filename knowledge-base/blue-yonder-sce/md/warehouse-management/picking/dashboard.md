---
title: "Dashboard"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/dashboard_picking.htm"
source: "/content/dashboard_picking.htm"
toc_path:
  - "Warehouse Management"
  - "Picking"
  - "Dashboard"
sections:
  - "Monitor orders and picks on the Dashboard"
  - "Monitor picking progress on the Dashboard"
  - "Cancel a short and reallocate"
  - "Cancel short inventory on an order line"
  - "Change the priority of a replenishment"
  - "View pending replenishments"
  - "View short order lines"
  - "View hot transport equipment"
  - "Pending Replenishments detail fields"
  - "Shorts detail fields"
  - "Hot Transport Equipment fields"
images: []
source_sha1: c7ac4d11898af043ee3b2b0eb6f8ce7fba9ccd5f
---
# Dashboard - Picking

You use the Dashboard to monitor the status and progress of the active outbound orders in the warehouse and the picks to fulfill the orders. This information helps you ensure that orders are being allocated and fulfilled on time, and gives you the ability to research and resolve allocation issues.

Specifically, the Dashboard displays the following information:

-   **Orders**: Displays the total number of active (not complete) orders, rush orders, the number of orders with unallocated order lines, and the number of orders that are short.
-   **Picks**: Displays the number of remaining picks for allocated orders, the number of held picks and replenishments, and the number of picks with a priority included in the selected range.
-   **Progress**: The left pane displays a graphical representation of the picking progress by waves or overall summary. The progress bars indicate the quantity and percentage of picks that have been allocated, released, picked, staged, and loaded. If you select a wave (or view the summary) in the left pane, the right pane displays the number of picks for the wave (or all waves in the summary) and the number of users currently picking in each source work zone. Pick quantities are displayed by the pick type: bulk, pallet, case, work assignment, each, or replenishment.
-   **Issues**: Displays the number of short order lines and pending replenishments. In addition to viewing the information, you can perform tasks to help resolve the issue so that orders can be shipped on time; for example, cancel and reallocate a replenishment or ship an order line short.
-   **Labor**: Displays workload progression statistics related to the criteria associated with a planning profile. Only displayed if Warehouse Management is integrated with Warehouse Labor Management in a single instance. See tab information for [Outbound Planner](../outbound-planner/dashboard/labor-tab.md) or [Picking](dashboard/labor-tab.md).

## Monitor orders and picks on the Dashboard

1.  Perform one of the following tasks:
    -   Select **Outbound Planner > Dashboard**.
    -   Select **Picking > Dashboard**.
2.  Under **Orders**, view the following information:
    
    **Note**: In the Outbound Planner module, you can click a quantity to view the specific orders in a category. For example, if you click the value for **Rush**, you navigate away from the Dashboard to the Outbound page where only the rush orders are displayed.
    
    -   **Total**: Number of total, in-progress (not completed) outbound orders for the warehouse.
    -   **Rush**: Number of orders that are flagged as "rush" (or urgent) orders.
    -   **Unallocated**: Number of orders that are not allocated, regardless of their ship date and whether they are planned into a wave.
    -   **Short**: Number of orders that were allocated short. A short allocation occurs when a wave is allocated and there is not enough inventory available to fill one or more lines on the order.
3.  Under **Picks**, view the following information:
    
    **Note**: You can click a quantity to view the specific picks in a category. For example, if you click the value for **Not Released**, you navigate away from the Dashboard to the Picks tab where only the picks that have not been released are displayed.
    
    -   **Remaining**: Number of remaining (not completed) picks for all of the allocated outbound orders.
    -   **Not Released**: Number of picks that have not been released (status of Pending or Hold).
    -   **Priority**: Number of picks with a priority that falls within the specified range. You can click the priority range to update the value to a different priority range.
    -   **Replenishments**: Number of replenishment picks needed to satisfy short order lines.

## Monitor picking progress on the Dashboard

1.  Perform one of the following tasks:
    -   Select **Outbound Planner > Dashboard**.
    -   Select **Picking > Dashboard**.
2.  Select **Progress**.
3.  In the left pane, next to **View By**, select one of the following:
    -   **Summary**: Displays the combined picking progress for all of the allocated waves.
    -   **Waves**: Displays picking progress by each individual wave.
4.  View the information in the left pane. The horizontal bar chart represents the overall picking progress or the progress by wave. Each bar is color-coded to represent the number of picks in the following stages of outbound processing: Allocated, Released, Picked, Staged, and Loaded.
5.  View the information in the right pane. The horizontal bar chart represents the number of picks, by pick type, that are sourced from a work zone. Each bar is color-coded to represent one of the following pick types: Bulk, Pallet, Case, Work Assignment, Each, and Replenishment. Additionally, the number of current users performing pick work in each zone is displayed.
    
    **Notes**: 
    
    -   If you selected to view picking progress by wave, the information in the right pane pertains only to the selected wave. If you select a different wave, the information in the right pane is updated to reflect that wave.<br>
    -   You can use this information to monitor picking progress in different zones. For example, if you notice excess users in a zone with little work, you may want to reassign users to a zone with a large amount of work and not enough users.
    

## Cancel a short and reallocate

When you cancel a short and reallocate, the replenishment is removed and the application allocates the inventory again. This procedure is useful if an attribute on the short order line is changed, and it might affect the outcome of allocation. For example, assume an order line is allocated short, and as a result, you change the allocation rule on the order line to broaden the search. You can then cancel the short and reallocate the inventory based on the updated allocation rule on the order line.

1.  Perform one of the following tasks:
    -   [View short order lines](#View_short_order_lines).
    -   [View pending replenishments](#View_pending_replenishments).
2.  In the grid, select the row for the replenishment or the short order line.
    
    **Note**: If you are viewing short order lines, you can also click the order line to view additional details and complete the procedure.
    
3.  From the **Actions** drop-down list, select **Cancel Short and Reallocate**.

## Cancel short inventory on an order line

You may want to cancel the short inventory on an order line when the short inventory is not currently available in the warehouse or you do not have time to wait for the inventory to arrive. This procedure is part of the special handling process to resolve outbound inventory auditing and packing issues. When you cancel short inventory, any outstanding replenishment for the order line is also canceled.

**Note**: You can only ship an order short (shipping a quantity that is less than the requested quantity) if the associated order line permits partial shipping (the **Partial** field on the order line is set to Yes), and the short shipment line does not violate any requirements for groups of shipment lines to be shipped together (controlled by the **Married Code** field).

You can also perform this task when you [Manage short loads and items](../shipping/shipping-issues/procedures-for-shipping-issues.md).

1.  Perform one of the following tasks:
    -   [View short order lines](#View_short_order_lines).
    -   [View pending replenishments](#View_pending_replenishments).
2.  In the grid, select the row for the order line.
    
    **Note**: If you are viewing short order lines, you can also click the order line to view additional details and complete the procedure.
    
3.  From the **Actions** drop-down list, select **Cancel Short**. The application cancels any outstanding replenishments for the order line.
4.  If a message is displayed stating the shipment has been unassigned from the stop, click **OK**.
    
    **Note**: A shipment is unassigned from a stop if the shipment line (order) for which you cancelled short inventory is the only line on the shipment and has no fulfilled quantity.
    

## Change the priority of a replenishment

1.  [View pending replenishments](#View_pending_replenishments).
    
2.  In the grid, select the replenishment.
    
3.  From the **Actions** drop-down list, select **Change Priority**.
    
4.  In the **Priority** field, enter the priority to assign to the work queue entry associated with the replenishment.
    
5.  Click **Save**.
    

## View pending replenishments

You can access the display of pending replenishments while viewing the details for an order, load, shipment, or wave.

**Note**: Demand replenishments created as a result of pre-inventory allocation (PIA) processing are not displayed on the **Pending Replens** tab, because they are created as pick work and not replenishment work. You can view demand replenishments on the Picking and Outbound Planner Dashboards.

1.  Perform one of the following tasks:
    -   Select the **Outbound Planner** or **Picking** module, and then select **Dashboard > Issues**.
    -   Select **Outbound Planner > Waves and Picks > Waves**, and then in the grid, click a wave.
    -   Select **Outbound Planner > Outbound**, and then select **Orders**, **Shipments**, or **Loads**, and then in the grid, click an order, shipment, or load.
    -   Select **Picking > Waves and Picks > Waves**, and then in the grid, click a wave.
    -   Select **Shipping > Loads**, and then in the grid, click a load.
2.  Select **Pending Replens** or **Replenishments**.
3.  View information in the [Pending Replenishments detail fields](#Pending_Replenishments_detail_fields).

## View short order lines

1.  Perform one of the following tasks:
    -   Select the **Outbound Planner** or **Picking** module, and then select **Dashboard > Issues**.
    -   Select **Outbound Planner > Waves and Picks > Waves**, and then in the grid, click a wave.
    -   Select **Outbound Planner > Outbound**, and then select **Orders**, **Shipments**, or **Loads**, and then in the grid, click an order, shipment, or load.
    -   Select **Picking > Waves and Picks > Waves**, and then in the grid, click a wave.
    -   Select **Shipping > Loads**, and then in the grid, click a load.
2.  Select **Shorts** or **Short Order Lines**.
3.  View information in the [Shorts detail fields](#Shorts_detail_fields).

## View hot transport equipment

Hot transport equipment is any equipment used to transport inventory that can be used to fill a shippable order that was allocated short. You can also [View hot inventory](../shared-functions/staging/procedures-for-staging.md).

1.  Perform one of the following tasks:
    -   [View short order lines](#View_short_order_lines).
    -   [View pending replenishments](#View_pending_replenishments).
2.  To view additional details of a short order line, click the order line. See [View short order line details](../outbound-planner/outbound/procedures-for-shorts-and-replenishments.md).
3.  From the **Actions** drop-down list, select **Hot Transport Equipment**.
4.  View information in the [Hot Transport Equipment fields](#Hot_transport_equipment_fields).

## Pending Replenishments detail fields

 
| Field | Description |
| --- | --- |
| Work | Unique application-assigned identifier for a piece of work in the work queue. |
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
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Priority | Current priority of directed work in the work queue. This value represents the base priority defined for the operation plus any escalation increments that have been applied over time to the work request. For example, if the base priority of work is 20 and it is defined to escalate by 5 every hour, then after 2 hours it has an effective (current) priority of 10. The value for Priority is green if the value has been escalated from the base priority defined for the work operation.<br > The lowest number has the highest priority. For example, 1 is the highest priority; 10 is a higher priority than 20. |
| Pick Quantity | Quantity (in terms of material handling or stock keeping units) of the item that should be picked based on the order, work order, or replenishment. |
| Allocated Quantity | Quantity (in terms of material handling or stock keeping units) of inventory that has been allocated from storage to fulfill the order line. |
| Order Line | Unique number that identifies the order line. The number corresponds to the line's position on the order. The first order line is automatically assigned a line number of 0001. Additional order lines are then automatically numbered sequentially, beginning with 0002. |
| Source | Location where the work originated, such as the location from which inventory is picked, at which a count is performed, or from which transport equipment is moved. |
| Destination | Location where the work is completed, such as the location to which inventory is delivered or to which transport equipment is moved. |
| Client | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. |

## Shorts detail fields

 
| Field | Description |
| --- | --- |
| Order Line | Unique number that identifies the order line. The number corresponds to the line's position on the order. The first order line is automatically assigned a line number of 0001. Additional order lines are then automatically numbered sequentially, beginning with 0002. |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Short Quantity | Quantity of inventory for the order line that the application could not successfully allocate. |
| Reason | Reason that the ordered quantity cannot be fulfilled. |
| Details | Additional details about why the short allocation occurred. For example, if the reason inventory could not be allocated was an inventory attribute mismatch, this field displays the order line criteria for which the application could not locate inventory to satisfy. |
| Replenishment Count | Number of times that the application has attempted to fulfill the short quantity through reallocation. |
| Late Ship Date | Last day of the outbound shipment range. To define a single shipment date, enter the first day of the shipment range. The application uses both delivery and ship dates to consolidate order lines into shipments, depending on the values defined for order consolidation. |
| Ship Short Allowed | Indicates whether the order line with unfulfilled inventory is allowed to be shipped short. If the order line can be shipped short, a check mark is displayed in this column. This is determined by the **Partial** field on the order line. |
| Maximum Retries | Maximum number of attempts for the application to reallocate the short inventory. This value is defined in the error control configurations; see [Configure replenishment settings](../configuration/inventory/replenishments/replenishment-settings.md). |
| Pick Quantity | Quantity (in terms of material handling or stock keeping units) of the item that should be picked based on the order, work order, or replenishment. |
| Picked Quantity | Quantity (in terms of material handling or stock keeping units) of inventory that is picked based on the order, work order, or replenishment. |

## Hot Transport Equipment fields

 
| Field | Description |
| --- | --- |
| Item | Item on the hot transport equipment that is needed to fulfill an outbound order line that was allocated short. |
| Inbound Shipment | Unique identifier for the inbound shipment that contains inventory needed to fulfill an outbound order line that was allocated short. An inbound shipment is a group of orders that are transported to the warehouse together or received together. |
| Transport Equipment | Alphanumeric identifier for transport equipment. Transport equipment numbers are not unique, can exist multiple times, and can be associated with various carriers. |
| Carrier | Identifier for a carrier that delivers inbound inventory to the warehouse or outbound shipments to a customer. This is the identifier that will be displayed to users on the application windows and reports. In the application, a carrier can be associated with a customer, order, inbound shipment, outbound shipment, load, and service levels (such as Ground, Next Day, and Saturday Delivery). |
| Yard Location | Current location of the transport equipment in the yard. This location is either a yard location or a door location. A yard location is an outdoor space in which transport equipment can be stored or parked until it is either moved to a dock door or checked out. A door location is an opening on the dock where transport equipment can be parked for the purpose of loading or unloading. |
| Status | Current status of the transport equipment.<br>-   • **Expected**: Receiving, shipping, or storage transport equipment that is expected to arrive at the facility, but has not yet been checked in.
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
| Hot Qty | Quantity of the item that is needed to fulfill one or more outbound order lines that were allocated short. |
| Applied Qty | Quantity of inventory that has been reserved for an order. |
| Arrival | Date and time at which the inbound shipment was delivered to the warehouse. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
