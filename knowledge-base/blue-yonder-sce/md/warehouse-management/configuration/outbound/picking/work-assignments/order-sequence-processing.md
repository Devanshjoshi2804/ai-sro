---
title: "Order sequence processing"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/order_sequence_processing_config.htm"
source: "/content/order_sequence_processing_config.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Outbound"
  - "Picking "
  - "Work Assignments"
  - "Order sequence processing"
sections:
  - "Order sequence processing setup"
  - "Automatic shipping for sequenced orders"
  - "Item family set sequence"
images: []
source_sha1: d40bee06a2859bd109373c68da17587a4b98ebd0
---
# Order sequence processing - Configuration

Order sequence processing is a process for picking and shipping inventory for the same item family (or item family set) for multiple orders in a sequenced fashion. The sequence matches the order in which the items are required at a production line for the assembly of a top-level item (such as an automobile).

Specifically, the application supports the following processes:

-   **Planned Order Sequence field on orders**. This is a sequence value assigned to the order and downloaded from the host. It is used to plan corresponding work assignment picks into a slot on a master handling unit.
-   **Reserve a slot for a specific order**. Work assignment rules can be configured so that each slot on a master handling unit is reserved for a single order. When an order spans multiple master handling units, all of its order lines reside in the same sequential slot. For example, if an order has order lines for three different item family sets, then each order line is planned to a different work assignment and occupies the same slot number (such as slot 1) in each of the three master handling units.
    
    If configured to do so, allocation releases work assignment picks for an order to a slot on a master handling unit. The application sequences the picks and the slots, based on the order's planned order sequence, and enforces picking in accordance with the sequence.
    
-   **Block Slot field on order lines**. This field indicates that an order line is not allocated but leaves the slot that it is planned to blocked for inventory. The reason for blocking a slot on a master handling unit is to preserve the sequence in which orders are picked to slots on a master handling unit. Multiple orders for the same item family set can be planned to the same work assignment and master handling unit. Each order occupies a different slot. For example, order A occupies slot 1, order B occupies slot 2, order C occupies slot 3, and so on until all of the slots on the master handling unit are filled.
    
    In order to preserve the slot position of an order on each master handling unit, the slot must be reserved for the order when there is no order line quantity for the slot. To reserve a slot, an order line is configured with the **Block Slot** field selected. Blocking a slot prevents other inventory from being picked to the slot. For example, when a work assignment includes orders for item families A, B, and C; then if one of the orders does not include an item quantity for B, the slot sequence for the item is blocked to prevent another item from being picked to the slot. Blocking the slot retains the slot sequence of each order in the work assignment and on the master handling unit. Whenever a user cancels a pick from a slot and the slot becomes empty, the application blocks the slot if no reallocated pick is planned to the slot. In addition, if a pick is cancelled and not reallocated, or reallocation is shorted, an Event Management event can be sent indicating that reallocation failed.
    
-   **Automatic allocation**. For order sequence processing, the host downloads sequenced orders without shipments. A sequenced order is an order that has a planned order sequence value assigned by the host.
    
    Automatic allocation checks for sequenced orders and creates a shipment for each order so that each shipment can be allocated and released to a work assignment right away. Shipments do not remain as they are created. Order lines may be assigned to different work assignments. As work assignments are completed, the picked lines are split from shipments so that each work assignment can be shipped.
    
    When a wave is allocated, orders that have a planned slot sequence number are allocated in ascending order. If a reset value is configured for work assignments (**Reset Planned Order Sequence** field), then it is possible for multiple orders to have the same slot sequence number, because the numbers are reused. In this scenario, the application sorts the orders (ascending) based on the date on which they were added (downloaded from the host) and then allocates according to the planned slot sequence number.
    
    For example, assume that the reset value is 1, and that there are orders in a wave with planned slot sequence numbers of 1, 1, 2, 2, 3, 3. Since some orders share the same planned slot sequence number, the application sorts the orders based on their add date, with the reset value indicating a new group of sequenced orders. In this example, the application allocates the orders in sequence (1, 2, 3) (1, 2, 3) with the first set of orders (since they were added first) being allocated first, and then the second set of orders.
    
-   **Work assignment configurations**:
    -   **Sequenced item family sets**. An item family set is a user-defined list of item families that can be planned into the same work assignment. For example, if an item family set consists of item families A, B, and C, then sequential orders that require picks from item families A, B, and C are eligible to be planned to the same work assignment. However, picks for item family D would not be included on the same work assignment.
        
        Item family set sequence is used to specify the order in which work assignments for the same item family set are performed. Work assignment picks for an item family set must be completed before the next work assignment for the same item family set can be started. For example, if there are three work assignments for the same item family set, the application increases the sequence by one for each work assignment that is generated. The application prevents the other two work assignments from being started until the first one is completed.
        
    -   **Work assignment creation**. You can add and update multiple work assignment rules at the same time. This is useful in supporting order sequence processing, which requires two work assignment rules (one for the master handling unit and one for the slot handling unit) for each item family set and handling unit combination. It is also used to add rules for new master handling units and item family sets that get added to the application.
    -   **Work assignment planning and release**. When multiple work assignments for an item family set are pending release, the application releases one work assignment at a time; the next available assignment is released only after the first one is completed. After a work assignment is released, the application assigns the item family set sequence value to the work assignment, and the sequence value is automatically released into the next work assignment.
        
        To achieve efficient utilization of a master handling unit, you can configure the application to prevent the release of work assignment picking for an item family until all of the slots on the master handling unit are reserved. If all the slots for a work assignment have not been planned, but picks have been released for the planned slots, then when an operator finishes picking the planned slots, the application does not automatically complete the work assignment. Instead, it directs the operator to deposit the master handling unit to a pickup and deposit (P&D) location to wait for additional picks to be planned to the empty slots.
        
        The following options are available for closing a partially completed work assignment:
        
        -   The operator indicates that the vehicle (warehouse equipment) is full.
        -   A user manually closes the work assignment from the Order Sequence Processing page in the Picking module.
        -   The close time is reached.
    -   **Work assignment cutoff time**. The cutoff time determines the point at which new picks are no longer added to the work assignment because they cannot be completed in time to meet the ship date. It is used, for example, to indicate when a handling unit can be released early, when it is typically configured to wait until it is fully planned. A cutoff time can be entered manually or derived (if Warehouse Labor Management is integrated with the application) from the closest shipping or delivery date for the orders.
        
        When the cutoff time is reached, the operator is allowed to complete the current pick, but any remaining picks are planned to the next sequential item family set's work assignment.
        
    -   **Work assignment close time**. The close time determines the point at which the work assignment must be completed in order to meet a shipping or delivery date. When the close time is reached, the operator is allowed to finish picking to a slot that has already been started. The remaining picks are re-planned into the next work assignment and the current work assignment is closed. However, if any existing pick is going to miss the shipping or delivery date, all picks from the slot will be canceled.
        
        Close time is entered manually or derived (if Warehouse Labor Management is integrated with the application) from the closest shipping or delivery date.
        
        The application checks for close time when the operator starts a work assignment, after each pick, and when an operator resumes a work assignment from a P&D location.
        
    -   **Unit quantity break value for a slot**: You can define a unit quantity break value for a work assignment rule. This quantity can be used, for example, to limit the pick quantity to a single unit per slot.
-   **Cancel and reallocate remaining picks to preserve order sequence.** If the operator cancels and reallocates a pick, the operator is directed to pick the reallocated pick (preserving order sequence) before picking to the next slot. If inventory is not available (reallocation fails), the slot is blocked to prevent other inventory from being picked to it. You can configure an Event Management alert to notify interested parties that reallocation has failed.
-   **Automatic loading and closing of shipments**. In situations where the manufacturing facility is connected to the warehouse, there is not always a need to go through the entire shipping procedure. Instead, for sequenced orders, you can configure the work assignment to systematically ship the work assignment inventory. The configuration is defined for a work assignment by movement zone and carrier. For example, when picking for an item family set is complete, it is delivered to a movement zone configured to automatically ship. The order lines are split to a shipment that includes the other order lines on the work assignment. The application systematically loads, closes, ships, and dispatches the shipment. However, the application preserves item family set sequence, and does not allow inventory for a work assignment to be shipped out of sequence. If the carrier allows automatic shipping, an RF operator can manually auto-ship the inventory, such as when the inventory arrives out of sequence or when the movement zone is not configured for automatic shipping.
    
    When work assignment picking for sequenced orders is completed, the application automatically splits each order from its original shipment and consolidates the orders into one shipment. When loading the pallet to the transport equipment, the application validates that pallets are loaded according to item family set sequence, ascending or descending, depending on the order sequence loading configuration for the work assignment.
    
-   **Visibility to master handling units used for sequenced order processing.** The Order Sequence Processing page, available in the Picking module, displays the progress of picking work assignments for master handling units that contain multiple slots. You can view handling units that are in progress and closed. For a selected LPN in progress, you can perform the following actions:
    -   Change the cut-off time for the master handling unit.
    -   Cut a handling unit so that no more picks are planned to the work assignment.
    -   Change the close time for the master handling unit.
    -   Close a master handling unit. and re-plan remaining picks to a new work assignment. Re-planning may involve canceling picks that will miss their shipping or delivery date.
        
        **Note**: Picks for a slot are always handled together. If picking for a slot has started, the application does not close the handling unit until remaining picks for the same slot are all picked. If any pick for a slot needs to be cancelled because of insufficient time, then all picks for the same slot are cancelled.
        
    -   Print labels for the slots on a master handling unit.
    -   Print label report for a master handling unit.
    -   Print a summary report of the inventory picked to slots on a master handling unit.
    -   Automatically ship a handling unit.

## Order sequence processing setup

You must perform the following tasks to configure the application for order sequence processing:

1.  **Define item family sets**. Item family sets are required if you want to create work assignment rules based on an item family set. An item family set defines the item families that can be included in a work assignment. For example, if an item family set consists of item families A, B, and C, then an order that has picks from item families A, B, and C is eligible to be planned to the same work assignment. However, picks for item family D would not be included on the same work assignment. See [Item family set sequence](#Item_family_set_sequence).
2.  **Create handling unit types**. Order sequence processing is used to pick a work assignment to the slots on a master handling unit type. The following configurations are required:
    
    1.  Define the handling unit type that represents a slot on a master handling unit.
    2.  Define the master handling unit type, enable it for work assignments, and then assign to it the handling unit slots to which inventory can be picked.
    
    See [Handling Unit Types](../../../inventory/lpn-handling/handling-unit-types.md).
    
3.  **Configure work assignments and rules**. For order sequence processing, work assignment rules are configured to allow only one item family (or item family set) to be released to a master handling unit with one order per slot.
    
    1.  **Configure work assignment processing**. The following attributes are specific to order sequence processing:
        -   **Prevent release by item family until the handling unit is fully utilized.** You can prevent the work assignment for a master handling unit from being released until picks have been planned for all the slots on the handling unit.
        -   **Suppress pick quantity of 1.** You can specify the pick zones in which RF operators are not required to enter a pick quantity if the pick quantity is 1. This saves keystrokes for the operator.
        -   **Shipping date for cutoff and close.** You can select from the early or late ship date or delivery date.
            -   The cutoff time determines that point at which new picks can no longer be added to the work assignment. Cutoff time is calculated using the closest shipping or delivery date of all order lines on the work assignment plus the estimated picking time for the work assignment and the travel time from the last pick's source location to the staging location. A cutoff time can be defined manually, for example, if Warehouse Labor Management is not integrated or if a user wants to override it.
            -   The close time determines the point at which the handling unit is closed. When the handling unit is closed, the application allows the operator to complete the current pick (for a non-slotted handling unit) or the picks for the current slot (for a slotted handling unit). Any remaining picks are re-planned to slots on another master handling unit as long as there is still time before the close time to complete the picks for shipping. If there is not enough time to complete the picks, the picks are cancelled. Close time is the closest shipping or delivery date for all order lines minus the travel time from the last pick's source location to the staging location. A close time can be defined manually, for example, if Warehouse Labor Management is not integrated or if a user wants to override it.
        -   **Automatic shipping.** You can enable carriers and movement zones for automatic shipping. If the carrier and movement zone is configured for automatic shipping, the application systematically loads, closes, ships, and dispatches the handling unit LPN. If the handling unit is deposited to a staging lane that is not enabled for automatic shipping, but the carrier for the shipment is enabled for it, then a user can initiate automatic shipping for the LPN.
    2.  **Create a master work assignment rule**. For the master work assignment rule, select the master handling unit (such as a stillage or trolley) for the rule. The rule can also be configured for reverse sequence picking, if required. Additionally, configure whether the application should prevent the consolidation of picks for the same item on sequenced orders. Preventing consolidation is especially useful in retaining the correct deposit sequence on non-slotted handling units.
    3.  **Create a slot work assignment rule**. This rule specifies how picks are directed to each slot on the master handling unit. For order sequence processing, a single rule is used because the same rule must be used for all of the slots on a master handling unit. For order sequence processing, configure the following attributes:
        -   **Pick order**: Select to sort the picks that have been planned into a list in order by planned order sequence; this determines the order in which they are picked.
        -   **Selection criteria**: Select an item family (or set) to limit the work assignment to orders that have picks allocated for the item family or item family set.
        -   **Criteria grouping**: Select item family (or set) and order to group picks for each order and item family (or set). If an order is allocated with multiple item families and some are not included in the criteria grouping, the order is split between 2 work assignments and master handling units.
        -   **Criteria sequence**: Select to sequence by Planned Order Sequence in ascending order. The value for Planned Order Sequence is defined on each order to indicate the sequence (in relation to other orders) in which it is planned to a slot on a master handling unit. For example, order A occupies slot 1; order B occupies slot 2, and so on.
    
    See [Add or modify work assignment rules](procedures-for-work-assignments.md).
    
4.  **Configure automatic allocation**. Configure automatic allocation to define when and what orders are candidates for automatic allocation based on the Planned Order Sequence attribute on the order. See [Configure automatic allocation settings](../../allocation/automatic-allocation.md).<br>
5.  **Track the pick progress and completion of the shipments**. You use the Order Sequence Processing page, available in the Picking module, to view the work assignments for sequenced orders and perform related actions on the handling units.

## Automatic shipping for sequenced orders

Automatic shipping is a process that systematically loads, closes, ships, and dispatches the staged inventory for completed master handling units. Automatic shipping can be performed on shipments that consist of sequenced orders that have been picked to slots on a master handling unit.

When sequenced orders are downloaded from the host, the application creates a shipment for each order so that orders can be allocated. This process is performed by a job named Process Advance Allocation Routes. Sequenced orders are picked to handling unit slots based on work assignments. Each work assignment is restricted to an item family set. Work assignments are processed (picked) according to item family set sequences.

When a work assignment for sequenced orders is completed, the application automatically splits the shipments from the orders and consolidates the orders into a single shipment for the master handling unit. The application retains the LPN for the master handling unit, so that it can be loaded in sequential order; that is, according to item family set sequence.

Automatic shipping is configured for work assignments, and requires you to enable automatic shipping for the carriers that allow it. Optionally, you can configure the movement zones in which automatic shipping takes place for carriers that allow it. When a shipment is staged to a zone that is not enabled for automatic shipping, but the carrier allows it, a user can initiate automatic shipping manually. See [Auto-ship a handling unit](../../../../picking/order-sequence-processing.md).

Automatic shipping can take place if the shipment meets the following criteria:

-   The shipment is not already closed.
-   All of the inventory for the shipment has been staged, is related to the same work assignment, and is on the same LPN or master LPN (master handling unit).
-   There are no in-process item family set sequences for the same item family set (not on this shipment) that should be shipped first. This is important to ensure that shipments are dispatched in sequential order.

## Item family set sequence

Item family set sequence is a configuration used to manage the release of work assignments during order sequence processing. An item family set is a user-defined list of one or more item families. An item family can belong to multiple item family sets.

You create an item family set for the item families that you want to be able to plan into the same work assignment. For example, if an item family set consists of item families A, B, and C, then sequenced orders that require picks from item families A, B, and C are eligible to be planned to same work assignment. However, picks for item family D would not be included on the same work assignment.

When you configure an item family set, you define the length of its sequence number. The sequence number is used to control the release of work assignments for the same item family set. For example, if there are three work assignments planned for the same item family set, the application increases the sequence by one for each work assignment that is generated. The application prevents the last two work assignments from being started until the first one is completed.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
