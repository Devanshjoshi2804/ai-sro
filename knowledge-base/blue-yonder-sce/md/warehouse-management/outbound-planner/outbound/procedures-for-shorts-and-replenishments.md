---
title: "Procedures for shorts and replenishments"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/procedures_for_shorts_and_replenishments.htm"
source: "/content/procedures_for_shorts_and_replenishments.htm"
toc_path:
  - "Warehouse Management"
  - "Outbound Planner"
  - "Outbound"
  - "Procedures for shorts and replenishments"
sections:
  - "Cancel a short and reallocate"
  - "Cancel short inventory on an order line"
  - "Cancel cross docking"
  - "Change the priority of a replenishment"
  - "View pending cross docks"
  - "View pending replenishments"
  - "View short order lines"
  - "View short order line details"
  - "View hot transport equipment"
  - "Cross Dock detail fields"
  - "Pending Replenishments detail fields"
  - "Shorts detail fields"
  - "Short item fields"
  - "Short location fields"
  - "Search Path fields"
  - "Search Path Log fields"
  - "Replen Destination Log fields"
  - "Hot Transport Equipment fields"
images: []
source_sha1: 4c9b083dc70e61d1d2ef600182b3008fa57c819a
---
# Procedures for shorts and replenishments

You can perform the following procedures on shorts and replenishments.

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

You can also perform this task when you [Manage short loads and items](../../shipping/shipping-issues/procedures-for-shipping-issues.md).

1.  Perform one of the following tasks:
    -   [View short order lines](#View_short_order_lines).
    -   [View pending replenishments](#View_pending_replenishments).
2.  In the grid, select the row for the order line.
    
    **Note**: If you are viewing short order lines, you can also click the order line to view additional details and complete the procedure.
    
3.  From the **Actions** drop-down list, select **Cancel Short**. The application cancels any outstanding replenishments for the order line.
4.  If a message is displayed stating the shipment has been unassigned from the stop, click **OK**.
    
    **Note**: A shipment is unassigned from a stop if the shipment line (order) for which you cancelled short inventory is the only line on the shipment and has no fulfilled quantity.
    

## Cancel cross docking

When you cancel a cross dock, you have the option of canceling the associated picks; you can also set the **Cross Dock** field on the order line to No, so it not considered for future cross dock opportunities.

You may want to cancel cross docking work or clear cross docking from the order line, for example, if inventory to fill the cross docking request is not received, or only a portion of the inventory is received and the customer does not allow the order to be shipped short.

**Note**: You can modify an order line to clear cross docking if the order line has not yet been allocated. See [Add or modify an order line](procedures-for-orders.md).

1.  [View pending cross docks](#View_pending_cross_docks).
2.  In the grid, select the cross dock to cancel.
3.  Click **Cancel Cross Dock**.
4.  Enter information in the following fields:
    
     
    | Field | Description |
    | --- | --- |
    | Clear Cross Dock from Order Line | If Yes, then in addition to cancelling the cross dock work, the **Cross Dock** field for the order line is set to No. If No, then the order line remains marked for cross docking. |
    | Cancel Picks | If Yes, then in addition to cancelling the cross dock work, any picks associated with the order line are also cancelled.<br > If No, then the picks for the order line are not cancelled. |
    | Cancel Code | Unique identifier for the cancel code. A cancel code is a configuration that determines how the application processes a pick cancellation to which the code is applied. |
    
5.  Click **OK**.

## Change the priority of a replenishment

1.  [View pending replenishments](#View_pending_replenishments).
    
2.  In the grid, select the replenishment.
    
3.  From the **Actions** drop-down list, select **Change Priority**.
    
4.  In the **Priority** field, enter the priority to assign to the work queue entry associated with the replenishment.
    
5.  Click **Save**.
    

## View pending cross docks

You can access the display of pending cross docks while viewing the details for an order, load, shipment, or wave.

1.  Perform one of the following tasks:
    -   Select **Outbound Planner > Waves and Picks > Waves**, and then in the grid, click a wave.
    -   Select **Outbound Planner > Outbound**, and then select **Orders**, **Shipments**, or **Loads**, and then in the grid, click an order, shipment, or load.
    -   Select **Picking > Waves and Picks > Waves**, and then in the grid, click a wave.
    -   Select **Shipping > Loads**, and then in the grid, click a load.
2.  Select **Cross Dock**.
3.  View information in the [Cross Dock detail fields](#Cross_Dock_detail_fields).

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

## View short order line details

1.  [View short order lines](#View_short_order_lines).
2.  In the grid, click the order line. The short order line details are displayed.
3.  View the [Shorts detail fields](#Shorts_detail_fields).
4.  Select **Item** and view the information in the [Short item fields](#Short_item_fields).
5.  Select **Location** and view the information in the [Short location fields](#Short_location_fields).
6.  Select **LPNs** and view the information in the [LPN detail field listings](../../shared-functions/inventory/procedures-for-lpns.md).
    
    **Note**: The LPNs that are displayed are those that contain the item on the short order line but could not be allocated.
    
7.  Select **Search Path** and view the information in the [Search Path fields](#Search_Path_fields).
    
    **Note**: The Search Path tab displays the allocation search paths that the application should use when allocating inventory based on the item and order line attributes. The information displayed on the Search Path tab does not capture the actual details of the allocation path that was executed to result in a short.
    
8.  Select **Search Path Log** and view the information in the [Search Path Log fields](#Search_Path_Log_fields).
    
    **Note**: See [Search path log](../outbound-planning-concepts.md).
    
9.  Select **Replen Destination Log** and view the information in the [Replen Destination Log fields](#Replen_Destination_Log_fields).
    
    **Note**: See [Replenishment destination log](../outbound-planning-concepts.md).
    

## View hot transport equipment

Hot transport equipment is any equipment used to transport inventory that can be used to fill a shippable order that was allocated short. You can also [View hot inventory](../../shared-functions/staging/procedures-for-staging.md).

1.  Perform one of the following tasks:
    -   [View short order lines](#View_short_order_lines).
    -   [View pending replenishments](#View_pending_replenishments).
2.  To view additional details of a short order line, click the order line. See [View short order line details](#View_short_order_line_details).
3.  From the **Actions** drop-down list, select **Hot Transport Equipment**.
4.  View information in the [Hot Transport Equipment fields](#Hot_transport_equipment_fields).

## Cross Dock detail fields

 
| Field | Description |
| --- | --- |
| Order Line | Unique number that identifies the order line. The number corresponds to the line's position on the order. The first order line is automatically assigned a line number of 0001. Additional order lines are then automatically numbered sequentially, beginning with 0002. |
| Cross Dock | Unique identifier associated with a piece of cross docking work. |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Type | Value that identifies the type of cross docking work to perform.<br>-   • **Shipment**: The cross docking work was generated during allocation to fill an order line (marked for cross docking) that is included in a shipment.
<br>-   • **Replenishment**: The cross docking work was generated during receiving to fill an emergency replenishment. |
| Pick Quantity | Quantity (in terms of material handling or stock keeping units) of the item that should be picked based on the order, work order, or replenishment. |
| Cross Dock Quantity | Quantity (in terms of material handling or stock keeping units) of inventory that is available to be cross docked to fulfill the order line. |
| Allocated Quantity | Quantity (in terms of material handling or stock keeping units) of inventory that has been allocated from storage to fulfill the order line. |

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
| Maximum Retries | Maximum number of attempts for the application to reallocate the short inventory. This value is defined in the error control configurations; see [Configure replenishment settings](../../configuration/inventory/replenishments/replenishment-settings.md). |
| Pick Quantity | Quantity (in terms of material handling or stock keeping units) of the item that should be picked based on the order, work order, or replenishment. |
| Picked Quantity | Quantity (in terms of material handling or stock keeping units) of inventory that is picked based on the order, work order, or replenishment. |

## Short item fields

 
| Field | Description |
| --- | --- |
| Description | Text that further describes the item. |
| Client | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. |
| Item Family | Identifier used to group similar items together. Typically, all of the items within a family have the same material handling characteristics. |
| Receive Status | Value that defines the quality or disposition of inventory. When defined for an item, it represents the status assigned to inventory by default during receiving. |
| Date Controlled | Indicates whether date tracking is enabled for the item (**Date Code** field in the item configuration is not blank). The date by which the item is tracked is displayed; for example, the manufactured or expiration date. |
| LPN Level | Value that determines the minimum LPN level at which the item is identified during the receiving process and tracked in the application.<br>-   • **LPN (Pallet)**: An identification label is required for the pallet. When inventory for this item is received, the operator is required to identify the pallet (or partial pallet).
<br>-   • **Sub-LPN (Case)**: An identification label is required for each case on a pallet.
<br>-   • **Detail LPN (Box)**: An identification label is required for each piece in a case. |
| Lot Tracked | Indicates whether the item is lot tracked (**Lot Tracking** field set to Yes in the item configuration). A lot is a batch (quantity) of an item uniquely identified by a lot number during the manufacturing process for the purpose of tracking that batch of inventory. |
| Origin Tracked | Indicates whether the item is tracked by its origin (**Origin Code** field set to Yes in the item configuration). The origin code is typically an identifier for the country or area of the world in which the item was manufactured. |
| Revision Tracked | Indicates whether the item is revision tracked (**Revision** field set to Yes in the item configuration). A revision may be used to identify a specific manufactured version of the item, so that when the item is modified or improved, the manufacturer may assign a new version number to reflect the change. |
| Serialization | Indicates whether the item is serialized. A check mark is displayed in this field if the item is serialized. |
| Catch Tracked | Indicates that the item is tracked by catch unit measurements (**Catch Code** field in the item configuration is not blank). Catch unit measurements are variable weights or sizes of inventory that may exist within the same material handling (stock keeping) unit. A check mark is displayed in this field if the item is catch tracked. |
| Item Type | User-defined code that you can use to group similar items. This value is not used in warehouse processing, but can be displayed in shipped history reports. |
| Velocity | Identifies the speed at which inventory stored in a location moves in and out of the warehouse. Velocity is used to optimize warehouse space and inventory handling by placing fast moving items in the best locations for quick picking, and slower moving items in the less accessible storage locations. The application accomplishes this by attempting to match the velocity of the item with the velocity of the location when finding a location for storing the item. |
| Current Quantity in Each | Quantity of the item in Eaches in the following categories:<br>-   • **Current**: Quantity that is currently within the warehouse.
<br>-   • **Committed**: Quantity that is currently committed to a warehouse process, such as picking for an order, an inventory move, or a replenishment.
<br>-   • **Pending In**: Quantity that is pending for an inventory activity. For an item, the pending quantity equals the committed quantity.
<br>-   • **Forecast**: Expected quantity of the item to be received against inbound order lines. |
| Unit Cost | Cost of a single stocking unit of the item. The application uses unit cost during processing, for example, to evaluate whether cost thresholds have been exceeded for automatic inventory adjustments, inventory adjustment approvals, playing inventory adjustments to the host, over receiving, inventory count discrepancies, and generating a count near zero count when a pick is cancelled. Costs are also displayed in reports, for example, to show the cost of counted inventory in a Count Activity report or count variances in a Count Audit Worksheet report. |
| Currency | Identifier for the currency in which the monetary value is saved. |
| ABC Classification | Code that determines how often the item is counted in a single count period. The frequency assigned to each ABC code is defined in inventory counting settings. |

## Short location fields

 
| Field | Description |
| --- | --- |
| Location | Location in which the item that was allocated short is located. If inventory for the item is found in a location but could not be allocated, you can view the **Reason** field to determine what prevented successful allocation. |
| Status | Current status of a location: Full, Partially Full, Empty, Inventory Error, or Locked. |
| Reason | Reason that the application cannot allocate an item from a location, such as the location was not included in the allocation search path. |
| Total Quantity | Total quantity of the item in the specified location. |
| Available Quantity | Quantity of the item in the specified location that is available for allocation. |
| Pending Quantity | Quantity of the item that has a pending move to the specified location. |
| Committed Quantity | Quantity of the item in the specified location that is already committed to other order lines. |
| Unmatched Quantity | Quantity of the item with a mismatched attribute between what is required on the order line and the actual attributes of the inventory in the location. For example, if the order requires inventory from lot A and the location has a quantity of 100 of lot B instead, the unmatched quantity is 100. |
| Hold Quantity | Quantity of the item in the specified location that is on hold. |
| Unmatched Attributes | Attributes that are required of the item on the short order line and do not match the attributes of the inventory in the specified location. |

## Search Path fields

 
| Field | Description |
| --- | --- |
| Path Priority | Position of this search path in the list of search paths. The position determines the priority in which the application evaluates the search path when attempting to allocate inventory. The higher the number the lower the priority (1 is the highest priority, 2 is lower, and so on). |
| Search Path | Name of the search. The name is displayed in lists that display search paths. An allocation search path is a configuration that identifies the source zone from which the application should attempt to allocate inventory for a pick based on the attributes of the required inventory. |
| Rule Priority | Number that determines the priority in which the application evaluates the search path rule in relation to other search path rules when attempting to find inventory. The application begins by evaluating the rule with the highest priority (1), and then moves to the rule with the next highest priority (2), and so on. |
| Pick Zone | Name of a pick zone. A pick zone represents a group of locations that share the same attributes for picking, such as the LPN level at which picks can be allocated, the cartonization group to which it belongs, and whether the location supports replacement picks and pre-inventory allocation. The search path searches pick zones when attempting to find inventory for allocation. |
| LPN Level | LPN level at which picks can be allocated from locations in the pick zone.<br>-   • **LPN**: Inventory at the full LPN level can be reserved from locations in this zone to satisfy the requirements of an order or replenishment. Typically, an LPN refers to a pallet. When inventory is allocated at the LPN level, operators are required to scan or enter an LPN.
<br>-   • **Sub-LPN**: Inventory at the case level can be reserved from locations in this zone to satisfy the requirements of an order or replenishment.
<br>-   • **Detail LPN**: Inventory at the each (or piece) level can be reserved from locations in this zone to satisfy the requirements of an order or replenishment.
<br>-   • **Any**: Inventory at any LPN level can be reserved from locations in this zone to satisfy the requirements of an order or replenishment. |
| UOM | Unit of measure in which the item can be allocated a picked from a location (using the search path rule) regardless of the quantity that is allocated. For example, you may configure a search path for a pick zone from which pallet quantities can be allocated (as specified by the **Maximum UOM** field), but the allocated quantity can only be picked as cases (as specified by the **Allocation UOM** field). |
| Pick Method | A set of configurations that define how picks are created and released. You can create separate pick methods for outbound picks, which fulfill orders shipped from the warehouse, and for replenishment picks, which restock picking locations in the warehouse. |

## Search Path Log fields

 
| Field | Description |
| --- | --- |
| Sequence | Sequence in which processing took place in relation to other processing lines in the log file. |
| Allocation Search Path | Name of the allocation search path that the application used to find inventory for the order line. |
| Location | Location in the allocation search path from which the application attempted to allocate inventory for the order line. |
| LPN | LPN in the source location that was evaluated for allocation. |
| Message | Information that explains the reason why the process failed to allocate the required inventory. |

## Replen Destination Log fields

 
| Field | Description |
| --- | --- |
| Building | Name of the building that contains the storage location that the application attempted to replenish. |
| Storage Location | Destination location that the replenishment process attempted to replenish. |
| Compared Value | Value that was compared to determine if the location was a match for the inventory. |
| Location Value | Value for the location to which the replenishment deposit was attempted. The difference between the compared value and location value can indicate the reason why the location could not be used. |
| Load Value | Value of the inventory that the application is attempting to put in the replenishment destination location. This is an inventory attribute value that the application compares when attempting to replenish a location. |
| Reason | Reason why the destination location was not a match for deposit of the replenishment inventory. |

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
