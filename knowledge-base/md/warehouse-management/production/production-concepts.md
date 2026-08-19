---
title: "Production concepts"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/production_concepts.htm"
source: "/content/production_concepts.htm"
toc_path:
  - "Warehouse Management"
  - "Production"
  - "Production concepts"
sections:
  - "Production planning and scheduling"
  - "Top level, component, and supply items"
  - "Component level tracking"
  - "Work orders"
  - "Work order processing"
  - "Work order processing task flow"
  - "Production line processing statuses"
  - "Work order and work order line processing statuses"
  - "Inventory allocation for a work order"
  - "Order processing functions"
  - "Work order completion process"
images: []
source_sha1: df2faf98351f1bc23b08ba215eadedaea9e4a956
---
# Production concepts

You use the Production module to manage the people, equipment, and inventory involved in production processes. You can make adjustments to inventory, work, production lines, and other factors that can improve the productivity and efficiency of warehouse production activities.

## Production planning and scheduling

Planning work orders involves assigning work orders to your production lines by creating work order assignments. Production planning also involves indicating when a production line is and is not available for processing work orders.

When you assign a work order to a specific production line, the application plans the work order based on the production line’s planning type. The following production line planning types are available:

-   **Schedule based**: Used to assign work orders to a production line for a specific beginning and ending date and time. You use a calendar display to plan work orders for selected dates and for one or more schedule-based production lines, and view the status of work orders. Different colors are used to represent different work order and production line statuses. See the information on production line schedule operations in the Supply Chain Execution Help.
-   **Sequence based**: Used to assign work orders to a production line in a sequence, indicating to operators that the first work order in the sequence is to be processed before the second work order, and so on. Work orders with a sequence are typically (but not necessarily) completed in the order specified by the sequence number (1 is the first sequence, 2 is the second sequence, and so on). The sequence is a suggested order; the application does not force you to process work orders in the planned sequence.
-   **Priority based**: Used to assign work orders to a production line with a number representing the importance of the work order. Higher priority work orders are typically (but not necessarily) completed before lower priority work orders (1 is the highest priority, 2 is the next priority, and so on). Work orders with the same priority will not have any kind of order within the priority and can, therefore, be worked on in any order you prefer. The priority is only informational; the application does not force you to process higher priority work orders before lower priority work orders.

You can schedule blocks of time when a production line is not available, such as when it is down for repairs or scheduled maintenance, and is not to be scheduled for a work order. You do this by creating unavailable time assignments.

You can configure the application to automatically release the picks for a work order's inventory in advance of the work order’s scheduled start time. Once the application date and time is within a specified number of minutes in advance of the scheduled start date and time, the application automatically releases the work order's pending and held picks.

## Top level, component, and supply items

A top-level item is an item that consists of multiple other items (components). A component item is an item that is used to create a top-level item. Depending on the type of work order (assembly or disassembly), component items are either used to produce a top-level item or they are the product of disassembling a top-level item. During assembly, component items are allocated and delivered to a processing location where they are assembled to create a top-level item (finished good). The finished good is then identified and received back into the warehouse. During disassembly, top-level items are allocated and delivered to a processing location where they are disassembled into component items. The component items are then received back into the warehouse and used to fulfill another order or work order.

The following are examples of top-level items:

-   **Battery pack**: A battery pack could be a top-level item that consists of the following component items: 3 AA batteries, 3 AAA batteries, 1 battery charger, and 1 battery set case.
-   **Shampoo**: A shampoo could be a top-level item that consists of certain fractional quantities (such as 0.2 ounce or 5.91 milliliters) of these component items: cleaning agent, dye, fragrance, water, and other ingredients.
-   **Lamp**: A finished lamp could be a top-level item that consists of the following component items: 1 lamp base, 1 lamp cord, and 1 lamp shade.

A supply item is an item that is used as a component in the top-level item, but is not allocated, picked, or delivered to a production staging location, line, or station. Instead, a supply item is typically stored in or near the production location (such as, in a non-inventory tracked work-in-process supply location) and is used by multiple production lines and top-level items. Cellophane and other wrapping materials are examples of supply items. Supply items are charged to a work order, either by specifying them in a bill of material (BOM) used to create the work order and setting the **Skip Allocation** field to Yes, or by specifying them when the work order is closed.

After component items are incorporated into the top-level item, the application considers the component items to be consumed and no longer exist as available inventory in the facility.

## Component level tracking

Component level tracking is an inventory tracking process in which the application continues to track the component items used to assemble a top-level item (finished good) after the finished good is assembled and received. Component tracking supports tracking component attributes (such as the lot, origin code, revision, and inventory status), kits within kits, and serialized components.

Using component tracking, a facility can quickly respond to recall events. For example, if an item used to make a top-level item is recalled, you can use component tracking to view all component inventory that was used to produce the top-level item, regardless of whether it was shipped or still exists in the warehouse.

## Work orders

A work order is an internal order used to find, allocate, and deliver items to a work-in-progress (WIP) location where the items are processed. Depending on the work order type assigned to a work order, the allocated items can be component items used to build a new top-level item (assembly) or top-level items that are disassembled into separate component items (disassembly). The new items or component items are then identified and received back into the warehouse.

A work order provides a detailed list of the items and quantities, along with the instructions and processing requirements, required to assemble or disassemble a top-level item (based on the work order type). A work order can also include customs information.

Work orders differ from shippable orders in that work orders do not require a customer or an address. A work order line is the section of a work order that provides detailed information about each individual component item that is to be built into the top-level item or that will result from disassembling the top-level item specified by the work order. Work orders and work order lines can be downloaded from a host, automatically generated from a bill of material (BOM), or generated manually.

You can use work orders for any situation in which you need to take existing inventory and either combine it to create a new item or disassemble it to create multiple new component items. Specifically, you use work orders to perform the following tasks:

-   Produce top-level items, such as by assembling a piece of furniture from its component items or mixing ingredients together to create a liquid product. See [Top-level, component, and supply items](#Top_level,_component,_and_supply_items).
-   Disassemble top-level items, such as by breaking down a piece of furniture or a gift pack to create multiple component items that can be identified and returned to storage or used to fill another order or work order
-   Modify existing inventory
-   Repackage existing inventory
-   Create kits, such as by assembling a gift pack, value pack, or a sample attached to another finished product
-   Provide value added services, such as by physically modifying a product or adding something to it

## Work order processing

Work order processing supports the ability to process internal orders, and is the act of taking items (component inventory) and combining them, such as assembling, kitting, or mixing, so that a new item (finished good, top-level item) is created. The finished good is then received into the warehouse (internal receiving) and stored, or cross-docked to ship staging to fill an order or to another production line for use as a sub-assembly in building a different top-level item. Finished goods can be used for filling outbound orders or as component inventory for a different top-level item.

Work order processing can also include disassembling a top-level item into component items, which can be received and stored or used to fulfill another order or work order. Work orders provide you the necessary tools to perform inventory manipulation. Typically, you use work orders to manipulate and receive inventory back into a facility as a different item. However, if you do not need to create a different item, then instead of work orders, you can use inventory processing options, such as service locations along a movement path to manipulate and ship inventory with the same item. The determining factor is whether you need to create a different item.

## Work order processing task flow

When processing work orders, you typically perform the following sequence of tasks:

1.  **Create the work order.**
    
    If work orders have not been received from a host application or generated automatically from a bill of material, you can manually create them. See [Add or modify a work order](work-orders/procedures-for-work-orders.md).
    
2.  **Optionally, schedule the work order for processing on a production line.**
    
    The application includes the ability to plan work for your production lines. See [Production planning and scheduling](#Production_planning_and_scheduling).
    
3.  **Allocate inventory for the work order.**
    
    Work order allocation is the process of locating component inventory (for assembly) or top-level items (for disassembly) for a work order and creating the work to pick that inventory. When allocating inventory, you can indicate the following information:
    
    -   The location to which the inventory will be delivered
    -   Which picks should be immediately released based on the LPN or UOM level of the pick
    -   How you want to handle items that are not marked for cross docking. This option is only required if one or more of the items on the work order are marked for cross docking.
    -   Whether to start the work order immediately after allocation

See [Allocate inventory for a work order](work-orders/procedures-for-work-orders.md).

**Note**: If Warehouse Management is integrated with Warehouse Labor Management and configured to send summary pick information, then when the pick or replenishment work is generated for the work order, Warehouse Management sends the information to Warehouse Labor Management immediately or at a later time using a background process. Warehouse Labor Management uses the Warehouse Management summary pick information in its Overview Statistics function, which displays the hours remaining to complete work or the percentage of work completed for any given job code.

6.  **Start the work order.**
    
    Before you can begin producing or disassembling a work order's top-level item, you need to start the work order. This indicates that the work order is actively being processed on a production line. See [Start or stop a work order](work-orders/procedures-for-work-orders.md).
    
7.  **Optionally, log in to a work order assignment.**
    
    If Warehouse Management is integrated with Warehouse Labor Management, then operators log in to indicate the work order, associated with a Warehouse Labor Management assignment, on which they are starting to work. See the information on work order assignment in the Supply Chain Execution Help.
    
8.  **Process the work order.**
    
    After allocating the inventory for a work order, you can perform several optional tasks, as needed, to process the work order. See [Procedures for work orders](work-orders/procedures-for-work-orders.md).
    
9.  **Monitor the progress of the work order.**
    
    Once a work order is allocated, you can view the following information:
    
    -   The pick work to be delivered to the production line
    -   The inventory picked for the work order
    -   The current location of any inventory picked for the work order
    -   The remaining picks to be completed for the work order

See [View detailed work order information](production-lines.md).

11.  **Pick the inventory.**
     
     After a work order is allocated and the pick work is released, operators on the warehouse floor pick the inventory needed for the work order.
     
     The process consists of going to a specified location, picking the inventory, and then delivering it to the specified production staging location or work-in-process location (production line or production station). Picking items for a work order is the same process as picking inventory for allocated shipments.
     
     Inventory picked to a staging location must be moved to the appropriate work-in-process location before assembly or disassembly begins. Inventory movement is accomplished using Move Inventory function. See [Inventory movement](../shared-functions/inventory.md).
     
12.  **Assemble or disassemble the top-level item.**
     
     After the items for a work order are picked and delivered to a production line location, operators can physically assemble or disassemble the top-level items.
     
     For assembly, operators can also use supply inventory that was not included on the work order to assemble the top-level item. Operators must determine if there is enough inventory in a location to begin the assembly or disassembly process. When assembling or disassembling the items, it is important for operators to review any notes or special instructions that accompany a work order to ensure that all requirements and special conditions are met.
     
13.  **If necessary, perform production station workflows.**
     
     When processing a work order at a particular production station, you may be required to perform associated production station workflows. However, you can perform workflows only when you start, stop, close, and complete a work order. See [Procedures for work orders](work-orders/procedures-for-work-orders.md).
     
14.  **Receive the top-level or component items.**
     
     After top-level items are assembled or disassembled, they must be received into the warehouse. The process, known as internal receiving, consists of identifying the new top-level or component items and putting them away. The process typically occurs at the production line or work order location in which the top-level items were assembled or disassembled. For this reason, internal receiving is also known as production line receiving. You can also capture a serial number for an item or, for a 3PL facility, an item and client combination. You can also capture and track serial numbers for all sub-LPN or detail LPN tracked components in a top-level item.
     
     During assembly, operators typically build a pallet of a finished top-level items and identify the entire pallet. Another option is to identify individual eaches or cases of inventory. When identifying serialized items, the items are identified individually, rather than by case or pallet. If you are identifying top-level items for work orders with component tracking, then, after specifying the attributes for the top-level item, you also need to specify the attributes of the components that were used to build the top-level item.
     
     When identifying items, operators can use the receive and putaway functionality. The RF Production screen can only be used in a limited manner. You cannot use an RF device to perform identification if the details of the consumed components used to make a top-level item cannot be absolutely determined (for example, when any of the component inventory is serialized, or if any of the components are attribute-tracked and the default information has not been supplied using a work order setup). You can use an RF device to perform identification if the consumed component inventory for a top-level item is entered and set up prior to identification, using a work order setup. For example, if one of the components is tracked by lot number, the default lot number must be defined on the associated work order setup. If you use an RF to identify top-level items and track components, work order setups are required for all work orders.
     
     Putaway can direct the items to a storage location or ship staging location (to fill a waiting shipment). Putting away finished top-level items or disassembled component items is the same process as putting away inventory that is received externally. See [Receive or put away a top-level or component item](work-orders/procedures-for-work-orders.md) or [Return to stock](work-orders/procedures-for-work-orders.md).
     
15.  **Complete and close the work order.**
     
     After a work order is allocated and the top-level items are assembled or disassembled, and the inventory is received into the warehouse, you must complete and close the work order. Completing and closing a work order indicates that all production processing for the work order is finished. This includes the tasks such as balancing the item quantity for assembly work orders, returning unused inventory to stock, and receiving the top-level or component items. When a work order is closed, Warehouse Management sends the appropriate transactions to the host application. See [Work order completion process](#Work_order_completion_process).
     

## Production line processing statuses

The following table describes production line processing statuses.

 
| Status | Description |
| --- | --- |
| Not Usable | The production line is not currently available. |
| Unassigned | No work orders are assigned to the production line. |
| Assigned | A work order is assigned to the production line, but the work order has not yet been started. |
| Started | A work order on the production line has been started, but none of the component items (assembly) or top-level items (disassembly) for the started work order have been delivered to the production line. |
| Partially Delivered | Some of the component items (assembly) or top-level items (disassembly) for a work order have been delivered to the production line. |
| Ready | Enough component items for an assembly work order have been delivered to the production line to begin building and identifying the work order's top-level item. |
| Completely Delivered | All of the component items (assembly) or top-level items (disassembly) for a work order have been delivered to the production line. |
| Production In-Process | At least one top-level item for an assembly work order has been identified off of the production line. For disassembly work orders, at least one component item has been identified from the top-level item that is being disassembled. |
| Complete | All of the top-level items for at least one of the started work orders are completely identified, but the work order has not yet been completed. For disassembly work orders, all of the component items for at least one of the started work orders are completely identified, but the work order has not yet been completed. |

## Work order and work order line processing statuses

The following table describes work order and work order line processing statuses.

 
| Status | Description |
| --- | --- |
| Pending | The component (assembly) or top-level (disassembly) inventory for the work order or work order line has not yet been allocated. |
| Waiting | The component (assembly) or top-level (disassembly) inventory has been allocated for the work order or work order line resulting in replenishments, but all of the replenishments have not yet been filled. |
| Undelivered | The component (assembly) or top-level (disassembly) inventory has been allocated for the work order or work order line resulting in pick work, but none of the component or top-level inventory has been delivered to the processing location yet. |
| Partially Delivered | Some of the component (assembly) or top-level (disassembly) inventory has been delivered to the processing location (such as, a production station for a work order line), but there is either not enough of the component inventory to build a top-level item for an assembly work order; or, for assembly and disassembly, the work order was stopped in the middle of production. |
| Delivered | All of the required component (assembly) or top-level (disassembly) items specified in the work order or work order line have been delivered to the processing location, but the work order has not yet been started. |
| Ready | For a work order, the work order has been started and (for assembly) enough component inventory has arrived at the processing location to build at least one top-level item, or (for disassembly) at least one top-level item has been delivered to the production line for break down. For a work order line, the work order has been started and enough of the component inventory specified by the work order line has arrived to be used in making at least one top-level item. |
| Completed | For a work order, all of the top-level items for the work order have been built and identified (assembly), or all component items have been identified from the broken down top-level items (disassembly). For a work order line, all of the component inventory specified in the work order line has been consumed. |
| Closed | The work order has been closed. |

## Inventory allocation for a work order

Inventory allocation for work orders is the process of locating component (assembly) or top-level (disassembly) inventory for a work order and creating the work to pick that inventory. You can manually allocate inventory to work orders.

You can perform the following inventory allocation tasks:

-   **Allocate one or more work orders**: You can allocate and generate pick work for the component or top-level inventory for one or more work orders at the same time (the picks generated by the allocation are still separated by work order).
-   **Allocate without inventory in stock**: You can allocate a work order even when the warehouse does not contain enough inventory to fill the requested amount of component or top-level inventory. The application generates cross dock or replenishment work for the needed inventory as it would for a regular order.
-   **Select a destination for picked inventory**: You can specify the staging location for work orders as the destination for picked inventory.
-   **Release picks by LPN level and UOM**: You can select the LPN level and unit of measure (UOM) at which picks for component or top-level inventory are released immediately (the rest of the picks are held for manual release). For example, you can specify that only sub-LPN picks are released. This is useful, for example, if you want to release case picks before pallet picks because the case picks take longer to perform.

The application performs the following tasks when a work order is allocated:

1.  Determines if any of the work order lines are marked for cross docking. If so, then the application creates a cross docking work request but holds the allocation for the work order line until the inventory for the work order line is received. During the receiving process, the application allocates the appropriate amount from the cross docking location and releases the pick work.
    
    **Note**: When you mark a work order line for cross docking, you specify whether or not you want the application to hold the pick work for all work order lines on the work order that you are allocating until the cross docked inventory is received.
    
2.  Executes a search, using the defined allocation search paths, for the inventory identified on the work order line.
3.  Commits inventory quantities at storage locations based on the processing attributes that you define on the work order line.
4.  Generates the pick work and releases picks based on the specified LPN levels and UOMs, while holding picks for the other LPN levels.
5.  Generates a replenishment request if it is not able to allocate an entire work order. When the replenishment is complete, the application attempts to complete the allocation.

## Order processing functions

The application uses bills of material (BOMs), along with work orders, to support the following order processing functions:

-   **Configure to order**: An order processing function in which the application automatically generates a work order based on a pre-defined BOM. The process begins when the host allocates an order for a top-level item for which no inventory exists in the warehouse. The application first generates a replenishment. When the replenishment fails, the application attempts to use a BOM that is defined for the item and enabled for generating work orders (the **Auto Generate Work Order** field is set to Yes for the BOM). If a BOM is found, a work order is generated and allocated.
    
    **IMPORTANT**: To perform this function, both cross docking and emergency replenishments must be enabled for your application.
    
-   **Build to stock (BTS)**: An order processing function in which a work order that exists in the application (created manually or downloaded from the host) is allocated for the purpose of assembling finished goods and returning them to stock for use at a later time. However, since standard putaway processes are followed when the product is identified, it is possible that the finished goods can be cross docked to an order or an outstanding work order. BTS is a proactive approach to keeping top-level items in stock.
-   **Order Explosion (OE)**: An order processing function in which an order for a top-level item is downloaded from the host, and the order load process explodes the order into an order for the component items, as defined by the BOM for that item. All component items are represented as sub-lines under the original order line.
    
    **IMPORTANT**: Before order explosion can occur, the order must be an order explosion type and have a BOM defined for the top-level item.
    

## Work order completion process

After a work order is allocated, and the items are assembled or disassembled (based on the work order type), you must complete and close the work order. When a work order is closed, the application sends the appropriate transactions to the host and clears the production line location for another work order.

You must perform the following tasks to complete a work order:

-   Balance the item quantity values by updating the **Reported Scrapped Quantity**, **Returned Quantity**, **Reported Consumed Quantity**, and **Reported WIP Quantity** fields for assembly work order lines on the Complete Work Order window.
-   Identify unused component or top-level inventory as the first step in returning the inventory to stock. See [Receive or put away a top-level or component item](work-orders/procedures-for-work-orders.md).
-   Identify finished goods or disassembled inventory. See [Receive or put away a top-level or component item](work-orders/procedures-for-work-orders.md).
-   Put away unused, or assembled or disassembled inventory to a storage location. See [Return to stock](work-orders/procedures-for-work-orders.md).
-   Close a work order to indicate that all production processing for the work order is finished. See [Close a work order](work-orders/procedures-for-work-orders.md).

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
