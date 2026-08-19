---
title: "Outbound planning concepts"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/outbound_planning_concepts.htm"
source: "/content/outbound_planning_concepts.htm"
toc_path:
  - "Warehouse Management"
  - "Outbound Planner"
  - "Outbound planning concepts"
sections:
  - "Loads"
  - "Outbound orders"
  - "Order reservation"
  - "Example: Using the married code to ship sets of inventory"
  - "Example: Using the married code to ship a complete group of inventory"
  - "Handling unit types and LPN attributes on outbound order lines"
  - "Handling unit types and LPN attributes on outbound order lines setup and configuration"
  - "Order and order line cancellation"
  - "Cross docking process"
  - "Cross docking considerations"
  - "Outbound order lines cross-dock processing priority"
  - "Inventory allocation for shippable orders"
  - "Pick work released in time to load transport equipment"
  - "Setup"
  - "Waves"
  - "Wave status"
  - "Manual wave processing"
  - "Automatic shipment creation"
  - "Short allocations"
  - "Search path log"
  - "Replenishment destination log"
  - "Delivery sequence loading"
  - "Delivery sequence loading order setup"
images: []
source_sha1: 44bfd1f8da9030a188bc586af7c5172a490342bc
---
# Outbound planning concepts

You use the Outbound Planner module to manage the people, equipment, inventory, and processes that move outbound warehouse inventory. You can make adjustments to inventory, work, orders, shipments, loads, replenishments, equipment, and other factors that can improve the productivity and efficiency of warehouse activities.

## Loads

A load is a collection of stops that are shipped together on a single piece of transport equipment. Before you can load staged shipments onto transport equipment, they must be assigned to a stop that is part of an outbound load. Each stop is assigned a stop sequence that determines the order in which the stops must be loaded into the transport equipment. The application does not allow stops to be loaded out of sequence unless one of the following configurations is set:

-   The load is configured to ignore the stop sequence order.
-   An item on the shipment is part of an item family to which a break stop sequence code is applied. If a load is configured to ignore the stop sequence order, it overrides the break stop sequence code.

Load information is typically downloaded from the host; however, you can add and modify loads manually, when needed.

## Outbound orders

An outbound order is a request to supply material or inventory. Within the application, an order initiates the process of fulfilling a request for inventory stored in your facility. The order provides the information required to determine the following shipping information:

-   What to ship
-   How much to ship
-   When to ship
-   Who and where to ship to
-   How to ship

Typically, outbound orders are sent from a host application; however, you can create orders manually. When you create orders, you define both the order header and the order line information. You use the Outbound Planner module to create and maintain orders.

**IMPORTANT**: Creating an order manually does not automatically add the order to the host application.

## Order reservation

The application can be configured to perform order reservation. Order reservation reserves inventory for outbound order lines prior to allocation, but does not commit inventory from a specific location.

Order reservation is important in facilities where outbound orders are allocated without sufficient inventory available in the facility to satisfy all of the order lines. The process allows you to prioritize order lines so that you can ensure that available inventory is allocated for the most important orders first.

In addition, order reservation allows you to logically tie together, or marry, order lines. Marrying order lines is typically used to meet specific customer requirements. Order lines containing the same married code can be allocated and shipped in sets of inventory or only as a complete group of inventory.

### Example: Using the married code to ship sets of inventory

Assume that a customer order includes the following order lines:

-   Order line 0001 for 20 toy trains
-   Order line 0002 for 80 batteries

Both order lines, 0001 and 0002, have married code values of "A" and allow partial shipment.

If the application is only able to find 15 toy trains in the facility, it determines that the ratio between order lines 0001 and 0002 is 1:4, and reserves the following quantities:

-   15 toy trains
-   60 batteries

### Example: Using the married code to ship a complete group of inventory

Assume that a customer order includes the following order lines:

-   Order line 0001 for 3 cans of red paint
-   Order line 0002 for 2 paint rollers
-   Order line 0003 for 4 paint brushes

Order lines 0001, 0002, and 0003 all have married code values of "A" and do not allow partial shipments.

If the application is only able to find two cans of red paint in the facility, it will not reserve any of the inventory. That is, the application ships all or none of the three married order lines.

## Handling unit types and LPN attributes on outbound order lines

The application supports the selection of a handling unit type (such as a CHEP pallet) and LPN attributes (such as wrapping) on an outbound order line. These attributes can be applied whether the order line is created manually or downloaded from a host application.

A handling unit type and packaging attributes can be associated with inventory during receiving, changed for existing inventory, assigned to order lines, and considered during inventory allocation. See [Handling unit types and LPN attributes on outbound order lines setup and configuration](#Handling_unit_types_and_LPN_attributes_on_outbound_order_lines_setup_and_configuration).

When inventory is identified or received into the warehouse, its handling unit type and LPN attributes can be captured or assigned to the inventory.

During receiving, values for handling unit type and LPN attributes are populated by default if a handling unit type and LPN attributes were specified for a supplier item footprint, supplier item, supplier, and item footprint. The receiver can override these values if necessary.

If LPN attributes are downloaded on an ASN, the receiver is only required to verify them if the ASN is from a supplier that is not configured as Trusted.

After inventory has been identified into the warehouse, users can modify its LPN attributes. In addition, RF operators can change the LPN attributes of inventory as they complete the required processes (such as wrapping) and can transfer inventory to a different handling unit type if necessary. See [Procedures for LPNs](../shared-functions/inventory/procedures-for-lpns.md).

Handling unit type and LPN attributes can be specified for an outbound order line at the following levels:

**Note**: Values defined for customers and customer types are defaulted to the order line for any values that were not specified on the order line and if the Customer Requirements Processing policy is enabled.

-   **Customer type**: For a customer type, you can specify the following information:
    -   A handling unit type or range of acceptable handling unit types for a unit of measure (UOM)
    -   LPN attributes
        
        This is used to support the requirements of different types of customers. For example, European customers may require that only EURO1 pallets be used for their orders; whereas grocery customers may require that 48 X 40 CHEP pallets be used.
        
-   **Customer**: For a customer, you can specify a handling unit type or range of acceptable handling unit types for a UOM, as well as LPN attributes. This is used to support the requirements of different customers. For example, a customer may require that all of their pallet shipments be wrapped. The values specified for a customer override the values specified for a customer type.
-   **Order line**: When adding or modifying an order line, you can specify a handling unit type and LPN attributes directly on the line. For example, one order line may require an aluminum pallet because it is destined for outdoor storage, while another order line may require a standard wood pallet. The values specified directly on the order line override the values specified for a customer and customer type.

Allocation attempts to find inventory that matches the handling unit type and LPN attributes required by the order line.

-   When a handling unit type is specified for an order line, the application attempts to allocate inventory that is on the specified handling unit type. If an exact match is not found, it attempts to allocate inventory on another handling unit type. When picks are released, the application directs the operator to pick inventory that is already on the specified handling unit type or use the specified handling unit type for the inventory when completing the pick.
-   If there are certain LPN attributes that must be completed before inventory is shipped, the application attempts to allocate inventory that already has the LPN attributes required for shipment. If no such inventory exists, it attempts to allocate alternate inventory.

During allocation, if an exact match with the specified handling unit type or LPN attributes is not found, then available inventory is allocated, and the application prompts the operator during picking or prior to transport equipment loading (depending on what is configured for the warehouse) to change the handling unit and apply the required LPN attributes. If the inventory is not on the required handling unit type and the attributes are not completed, the application does not allow the inventory to be loaded on the transport equipment and forces the operator to deposit the inventory in a ship staging location until the requirements are met and confirmed on the RF.

For all shippable order lines, the handling unit type on which the inventory ships is recorded so that it can be printed on shipping documents and included in information sent to the host application.

## Handling unit types and LPN attributes on outbound order lines setup and configuration

The application supports the selection of a handling unit type (such as a CHEP pallet) and LPN attributes (such as wrapping) on an outbound order line. These attributes can be applied whether the order line is created manually or downloaded from a host application.

You must perform the following tasks to configure the application to support handling unit types and LPN attributes on outbound order lines.

1.  **Set up handling unit tracking.**
    
    To specify handling unit types on an order line, you must enable the Inventory handling unit category for the warehouse and define the handling unit types that you want to track. See [Configure handling unit settings](../configuration/inventory/lpn-handling/handling-unit-settings.md).
    
2.  **Configure LPN attributes.**
    
    You can define the LPN attributes (such as "Wrap" and "Slip Sheet") that you want to use. See [Configure LPN attributes](../configuration/inventory/lpn-handling/lpn-attributes.md).
    
3.  **Define the required handling type and LPN attributes on the order line.**
    
    You use the Outbound page in the Outbound Planner module to define the required attributes for an order line. Specifically, you specify the required handling unit type and LPN attributes for an order line. See [Add or modify an order line](outbound/procedures-for-orders.md).
    
4.  **If necessary, define handling unit types and LPN attributes for a customer and customer type.**
    
    If your application is configured to apply customer and customer type requirements to an order line for values that are not specified on an order line, then you may want to specify handling unit types and LPN attributes for a specific customer or customer type. These values are defaulted to order lines for the appropriate customer if the order line does not already have the values specified. See [Add or modify a customer](../configuration/partners/customers/existing-customers.md) and [Add or modify a customer type](../configuration/partners/customers/customer-types.md).
    
    The ability to specify handling unit type and picking UOM combinations gives you the flexibility to specify different combinations, such as for drums to be placed on CHEP pallets and cases to be placed on WOOD pallets.
    
5.  **Configure suppliers and item footprints.**
    
    Handling unit type and LPN attribute values, if required, are captured for inventory at the time it is received or identified into the warehouse. These values are populated automatically if values were defined for the supplier or for the item footprint.
    
    When the application attempts to find a default value, it looks first at the supplier item footprint, next at the supplier item, then at the supplier, and finally at the item footprint. If a default value is not found, the application prompts the operator to enter a value for the required attributes.
    
    You configure the default handling unit type and LPN attribute values for a supplier, specific items provided by that supplier, if item overrides are defined, specific item footprints provided for those items, as well as the default handling type and LPN attribute values for an item footprint.
    
    See [Add or modify a supplier](../configuration/partners/suppliers.md) and [Add or modify an item](../configuration/inventory/items/items.md).
    
6.  **Configure the point at which the handling unit type and LPN attribute requirements are displayed to the operator.**
    
    You can specify when an operator is prompted to apply any remaining handling unit type or LPN attributes to inventory before it is loaded on the transport equipment. See [Configure pick settings](../configuration/outbound/picking/pick-settings.md).
    
7.  **Configure whether the application prompts the user, during product identification, to confirm the handling unit type and LPN attributes if the user already confirmed those attributes for another receipt line (same item) on the planned inbound order.**
    
    You can save keystrokes by configuring the application to skip the handling unit type and LPN attribute confirmation prompt for items that have already been confirmed (set the **RF LPN Configuration** field to No). See [Configure inbound identification](../configuration/inbound/receiving/inbound-identification.md).
    

## Order and order line cancellation

You can cancel an order that has a status of Unallocated, Allocated, Picks Released, or Shipment Cancelled. You cannot cancel an order for which picking has begun; however, individual order lines within an order can still be cancelled as long as picking for the line has not started.

A cancelled order cannot be recovered, however, the application retains a record that it existed. Cancelled orders are purged from the application according to the console configuration.

When you cancel an order or order line, the following actions take place:

-   The application stops processing any work related to the inventory such as allocation, picks, or replenishments.
-   The outbound shipment line associated with a cancelled order is also cancelled.
-   If all the order lines for an order are cancelled, then the order to which they belong is also cancelled.
-   If a cancelled order is the only one assigned to an outbound shipment, then the shipment is also cancelled.

See [Cancel an order or order line](outbound/procedures-for-orders.md).

## Cross docking process

If your application is set up to allow cross docking, then on-demand, unprocessed replenishments, and marked outbound order lines are cross docked. Cross docking work is created when a shipment or work order is allocated and there is not enough inventory in storage to fulfill the required quantity, but additional inventory is found in receiving. The cross dock can be planned (order lines or work order details are marked for cross docking) or opportunistic, where the lines are not marked and are considered short. See [Cross Docking](../configuration/inbound/cross-docking.md) and [Pick replacement processing](../configuration/inbound/cross-docking.md).

Order lines can be received from the host system with cross docking specified, or they can be manually marked for cross docking. Marking order lines for cross docking is an optional step when manually processing orders.

If you are cross docking, then manual order processing consists of the following tasks:

1.  **Mark the order lines that you want to cross dock**.
    
    There are several ways in which you can mark order lines for cross docking. The method you use depends on the status of the order. If the order does not exist, then you can create the order; when you add the order line, you can mark the line to indicate that cross docking is required. If the order exists, then you can modify the order line and mark the line to indicate that cross docking is required.
    
    **IMPORTANT**: You can specify whether you want any remaining lines on the order to proceed through the standard allocation process. If you choose not to release remaining order lines, then pick work for those lines will not be released until the cross docked inventory is received and allocated.
    
2.  **Optionally, group the order into an outbound shipment**.
    
    All orders must be grouped into a shipment before they can be allocated, but you do not have to complete this step manually. If you do not create a shipment for an order before planning the order into a wave, the application automatically creates a shipment. For detailed information about creating shipments, see [Shipping process](../shipping/shipping-concepts.md).
    
3.  **Plan the order or shipment into a wave**.
    
    A wave is used to allocate inventory for outbound orders and shipments. If a wave has multiple orders, all of the orders are allocated at the same time. Waves help you control work and inventory flow in your facility. See [Waves](#Waves_overview).
    
4.  **Allocate the wave**.
    
    To trigger cross docking, the shipments must be allocated in a wave. During the allocation process, a cross docking work request is generated for marked order lines and allocation is bypassed. For detailed information about the allocation process, see [Inventory allocation for shippable orders](#Inventory_allocation_for_shippable_orders).
    
5.  **Perform the cross docking work**.
    
    Typically, cross docking opportunities are identified during the receiving process where the actual cross docking work begins. When product is identified and immediate putaway is selected, the application determines whether that product has been marked for cross docking or has a pending request for replenishment.
    
    **Note**: If manual putaway is selected during the receiving process, the application does not look for cross docking opportunities.
    
    When the application determines that cross docking is required, either for a marked order line (planned cross docking), unmarked short order line (opportunistic cross docking), or for an on-demand replenishment, one of the following actions occur:
    
    -   If a staging lane was specified when the order was allocated, then direct cross docking is performed, and the application performs the following processing tasks:
        1.  Determines the appropriate quantity to allocate for the order
        2.  Splits the pallet if the cross docking configurations allow pallet splitting, and the received quantity is greater than the quantity required for the order
            
            **Note**: When pallets are split, the new pallet configurations are displayed on either the RF screen or workstation window, and users can produce new pallet labels. Remaining product will be allocated to another cross docked order or replenishment, or to a storage location.
            
        3.  Moves the product to the specified staging lane to satisfy the order
            
            **Note**: For RF receiving, the new pallets are automatically moved onto the RF device and individually deposited. For workstation receiving, the move can be performed immediately or sent to the work queue. The queued work will be a pick operation from the receiving dock as the product will have already been allocated.
            
    -   If a staging lane was not specified when the order was allocated, or if the cross dock will satisfy an on-demand replenishment, then indirect cross docking is performed, and the application performs the following processing tasks:
        1.  Determines the cross docking location
            
            **Note**: Cross docking locations are defined in your application configurations.
            
        2.  Determines the appropriate quantity to allocate for the order
        3.  Splits the pallet if the cross docking policies allow pallet splitting, and the received quantity is greater than the quantity required for the order
            
            **Note**: When pallets are split, the new pallet configurations are displayed on either the RF or workstation windows, and users can produce new pallet labels. Remaining product will be allocated to another cross docked order or replenishment, or to a storage location.
            
        4.  Moves the inventory to the cross docking location
            
            **Note**: For RF receiving, the new pallets are automatically moved onto the RF device and individually deposited. For workstation receiving, the move can be performed immediately or sent to the work queue. The queued work will be a store operation to the cross dock location, and the inventory will be allocated when the inventory is deposited into that location.
            

## Cross docking considerations

The following considerations should be taken into account when using cross docking functionality:

-   **Cross docking after allocation:** **An order line cannot be marked for cross docking after it has been allocated.** Cross docking is triggered during allocation; therefore, an order line must be marked for cross docking before it is allocated. You can, however, mark an order line for cross docking after it is grouped into a shipment.
    
-   **Cross docking on-demand and unprocessed replenishments:** When an item is received, and immediate putaway is selected, the application determines if an on-demand replenishment request exists for that item. If it does, the amount required to fill the request is moved to the cross docking location, and the remainder is stored using storage search path rules.
    
-   **Over allocation:** **Cross docking can process over-allocation quantities.**
    
-   **Pallet splitting:** Cross docking has the ability to split pallets. If your application is configured to allow pallet splitting, cross docking can split a pallet into several pallets of the required quantities for orders or replenishments. Remaining inventory is stored using storage search path rules.
    
-   **Pallet splitting when receiving using an RF device:** If pallet splitting is in effect, and you are receiving by RF, a list of new pallet configurations is displayed and you can produce new pallet labels. The new pallets are automatically moved onto the RF device and then individually deposited.
    
-   **Pallet splitting when receiving in the application's Receiving module:** If pallet splitting is in effect, and you are receiving in the Receiving module, a list of the new pallet configurations is displayed and you can produce new pallet labels. You can choose to move the inventory immediately or send it to the work queue. If direct cross docking is performed, queued work will be a pick operation from the receiving dock, because the product will have already been allocated. If indirect cross docking is performed, queued work will be a store operation to the cross dock location, and the inventory will be allocated when the inventory is deposited into that location.
    
-   **Cross docking handle serialized product:** Because serialized product cannot be arbitrarily split when an order needs only a partial pallet, cross docking will take the following actions when serialized product is received:
    
    -   If the cross dock is indirect, the entire pallet is moved to the cross dock location, and the amount required for the order is allocated from that location when the product is deposited.
    -   If the cross dock is direct to a staging lane, the pallet is moved to a storage location within the warehouse, and the amount required for the order is allocated from that location when the product is deposited.
-   **Cross docking locations for received inventory are full:** When there are no cross docking locations available for received inventory, the application defaults to the standard storage path search rules.
    

## Outbound order lines cross-dock processing priority

Outbound order lines that are enabled for cross docking can be fulfilled with inventory that is moved directly from receiving to a cross dock location or a specified staging location. If multiple order lines require the same cross dock inventory, the application sorts and fulfills the outbound order lines based on their processing priority. If multiple order lines have the same processing priority, the application fulfills the order lines based on the following criteria:

1.  The shipment that has the earliest Appointment Start Date
2.  The trailer that has the earliest Arrival or Checked-in date and time (the application does not differentiate between the trailer at the door or at the yard)
3.  The shipment that has the closest early ship date
4.  The order line that has the closest early ship date
5.  The shipment that has the closest late ship date
6.  The order line that has the closest late ship date

## Inventory allocation for shippable orders

Allocation is the process of locating inventory for an order and creating the work to pick that inventory. An outbound order must be grouped into a shipment before it can be allocated; you can do this manually, or the application will automatically create a shipment when the wave in which the order is planned is allocated. The application uses the STD-ORDERSELECTION wave rule to create shipments for the orders in a wave.

**Note**: For information on allocating component inventory for a work order, see [Allocate inventory for a work order](../production/work-orders/procedures-for-work-orders.md). The application can be configured to automatically allocate waves, or you can manually allocate waves using the Outbound Planner or Picking module.

When a wave is allocated, the application completes the following steps:

1.  Determines if an order line on an outbound order is marked for cross docking.
    
    If an order line is marked for cross docking, then the application creates a cross docking work request but holds the allocation for that line until the inventory for that order line is received. During the receiving process, the application allocates the appropriate amount from the cross docking location and releases the work.
    
    **Note**: When you mark an order line for cross docking, you specify whether you want the application to hold pick work for all order lines on the order until the cross docked inventory is received.
    
    If no order lines are marked for cross docking, then the application continues with the allocation process.
    
2.  Searches the facility to locate an acceptable storage location that contains the inventory identified on the order line.
    
    This requires the application to verify the following information:
    
    -   Item
    -   Attribute values defined in the allocation rule
    -   Inventory status
    -   Packaging configuration
    -   Quantity

If more than one staging lane location has been assigned to the order, the application locates an acceptable storage location from which to pick the inventory that is in the same building as the appropriate assigned staging lane location.

**Note**: Acceptable storage locations are also determined by your allocation search path configurations. See [Allocation Search Paths](../configuration/outbound/allocation/allocation-search-paths.md).

5.  Commits inventory quantities at storage locations based on the processing attributes that you define on the order line.
6.  Generates the pick work based on the processing priorities that you define on the order line.

When you allocate the wave, you can define the following information:

-   Priority at which picks for the wave are released
-   A carrier (in some cases)
    
    **Note**: You can change a carrier only when the **Change Carrier** option for an order is selected and no carrier is defined. If you change the carrier of an order, its associated order lines are also updated.
    

9.  If allocation shortages occur, creates replenishment work.
    
    When the application is not able to allocate an entire order line, it generates a replenishment request. If allocation is still short, processing is based on the following order line attributes for partial shipments:
    
    -   If the order line allows partial (short) shipments, then allocation succeeds with a shortage.
    -   If the order line does not allow partial shipments, then any previous allocations and the order line are cancelled.
        
        You can view shorts and pending replenishments. See [View short order lines](outbound/procedures-for-shorts-and-replenishments.md) and [View pending replenishments](outbound/procedures-for-shorts-and-replenishments.md).
        
10.  If Warehouse Management is integrated with Warehouse Labor Management, Warehouse Management sends pick and replenishment information.
     
     Also, you can configure Warehouse Management to perform the following tasks:
     
     -   Send summary pick information. When the pick or replenishment work is generated, Warehouse Management sends the information to Warehouse Labor Management immediately or at a later time using a background process. Warehouse Labor Management uses the Warehouse Management summary pick information in its Overview Statistics function, which displays the hours remaining to complete work or the percentage of work completed for any given job code.
     -   Automatically release the pick work for the shipment in advance of the shipment's early or late ship or delivery date so that the inventory is picked and loaded onto the transport equipment in time for the transport equipment's scheduled dispatch. See [Pick work released in time to load transport equipment](#Pick_work_released_in_time_to_load_transport_equipment).

## Pick work released in time to load transport equipment

You can configure the application to automatically release pick work in advance of transport equipment arriving at the door door, so that inventory is staged and ready to be loaded when the transport equipment arrives.

If Warehouse Labor Management is integrated with Warehouse Management, you can configure Warehouse Management to automatically release picks in an appropriate time frame to ensure that the transport equipment is ready to be dispatched according to its scheduled dispatch time. The time frame is calculated based either on the start or end appointment date and time of the transport equipment or the early or late ship or delivery date and time of an outbound shipment.

When you configure this functionality, the following process is used to release picks by dispatch time:

1.  You allocate inventory for a wave so that the application creates picks in a held status (by not immediately releasing picks).
2.  Warehouse Management gets the goal times for completing the picks from Warehouse Labor Management.
3.  A scheduled process (REL-PICKS) checks on a regular basis to see if the time to pick the inventory for the wave plus any extra time that you allow (buffer) is within range of the release date.
    -   If the **Release Appointment Picks by Labor Estimate** field is set to Yes, then the REL-PICKS process checks for appointments that are in range of the appointment start or end date and time.
    -   If the **Release Ship Picks Estimate** field is set to Yes, then the REL-PICKS process checks for shipments that are in range of the shipment early or late ship or delivery date and time.
4.  For pick work that the REL-PICKS process determines is within range of its deadline, Warehouse Management changes the status of the picks from held to pending and then releases the picks using the general method to release picks.
    
    **Note**: As needed, you can update multiple shipments at the same time using Shipment Mass Update in the client-based user experience. For example, if you are releasing picks based on the Late Ship Date, you can select a group of shipments and change all of them to the same Late Ship Date at one time. See [Shipment Mass Update](../shared-functions/shipment-mass-update.md).
    

### Setup

Before the application can start automatically releasing pick work in time to load transport equipment, you must complete the following tasks:

1.  Make sure that Warehouse Labor Management is installed, configured, and integrated to work with your instance of Warehouse Management.
2.  Enable Warehouse Labor Management. See [Configure Warehouse Labor Management integration](../configuration/integration/warehouse-labor-management.md).
3.  Set the following configurations that support the release work by dispatch time feature:
    -   Labor Goal Time
    -   Release Appointment Picks By Labor Estimate
    -   Release Ship Picks Estimate
4.  Enable the scheduled process in the Console, under Jobs.
5.  When allocating inventory, make sure that the picks are created in a held status.

## Waves

A wave is used to allocate inventory for outbound orders and shipments. Wave processing can combine multiple outbound orders or shipments into logical sets to achieve efficient picking. Alternatively, a wave can also consist of a single order or shipment. When you plan outbound orders into a wave without first creating a shipment, the application automatically runs through a sequential list of shipment creation rules to create valid shipments.

For example, you can create a wave that consists of all the orders for a specific customer or carrier, or for orders that need to ship on a specific date. You can also create a wave and include a single order for allocation.

If a wave has multiple orders, all of the orders are allocated at the same time by default for both manual and automatic allocation. However, when automatically allocating shipment lines in a wave, the grouping level affects how many lines are allocated at one time. Waves help you control work and inventory flow in your facility.

You can plan and allocate a wave ahead of time and then view the pending replenishments. This enables you to be proactive in that you can fill the replenishments in advance, then release the picks for the wave as planned.

The following information relates to wave processing:

-   **Wave set**: A wave set is a name for a group of shipments included in the same wave. For example, if you group outbound shipments to three customers every Monday, you could name the wave set for these shipments "Monday". You assign a wave set to each shipment you want to allocate.
-   **Wave Number**: A wave number is a unique identifier for the wave that is generated by the application, or is user-defined, at the time that the wave is planned. The wave number distinguishes one wave from another, which enables you to track the wave through the application.
-   **Automatic wave processing**: The host marks outbound orders for wave processing and a background process (SALDAEPRC) automatically selects, plans, allocates, and releases the picks for the wave without any intervention of the user. See [Automatic allocation processing](../configuration/outbound/allocation/automatic-allocation.md).
-   **Manual wave processing**: An operator picks a wave rule and manually selects outbound orders or shipments based on the wave rule to plan, allocate, and release a wave. See [Manual wave processing](#Manual_wave_processing).

You can make the following modifications to a wave:

-   Add or remove an order or order line, a shipment, or a load. These actions can be performed on waves in a Planned, Allocated, or Released status. If you remove an order from a wave, it returns to an Unplanned status; if the order was assigned to a shipment, the order retains the associated shipment number. This can be done prior to allocation while the wave is in the Planned status, or after allocation when the shipment line has been picked and staged.
-   Manage pick work for the wave, including suspending, releasing, or cancelling picks, among other tasks.
-   Assign a shipment or load in the wave to a staging lane.
-   Manage short allocations, replenishments, and cross docks for a wave.
-   Unallocate a wave for which picking has not started; the wave returns to a Planned status.
-   Delete a wave. You can delete a wave while it has a Planned, Allocated, or Scheduled for Release status. Once picks are released, you cannot delete a wave unless you first cancel the picks from the wave. When you delete a wave, all wave information is removed from the application, but the orders and shipments remain and are returned to an Unplanned status.

## Wave status

A wave transitions through the following statuses:

-   **Planned**: Scheduled waves are planned, but not allocated.
-   **Allocation in Process**: The application is in the process of allocating the picks for the wave.
-   **Allocated**: The wave is allocated and picks for the wave have a Hold status. The Hold status allows you to control when picks are released, so that you can pre-plan a wave in advance and then release it at a later time. You can cancel the wave in the Allocated status without having to cancel individual picks.
-   **Scheduled for Release**: Picks are scheduled to be released. To delete a wave in the Scheduled for Release status, inventory for the wave cannot be picked.
-   **Released**: Picks in the wave have been released for picking.
-   **Complete**: Picking is complete for the wave.

## Manual wave processing

Manual wave allocation is the process of planning and allocating shipments without automatic processing; you must manually transition the wave from one status to the next.

You can also configure the application for automatic wave processing. See [Automatic allocation processing](../configuration/outbound/allocation/automatic-allocation.md).

To use custom wave rules during manual processing, add or modify the wave rules from which to generate a specific wave. See [Wave rules](../configuration/outbound/allocation/manual-allocation.md).

**Note**: During manual wave processing, you can use the page refresh tool to manually refresh the wave status.

The following steps represent the high-level process for manually generating waves:

1.  If you are using one of the shipment-based wave rules, build your orders into outbound shipments. You can manually group orders into a shipment, or the application can automatically group orders into a shipment.
    
    **Note**: During automatic shipment creation, the application groups order lines together and runs through a list of shipment creation rules to create valid shipments. See [Automatic shipment creation](#Automatic_shipment_creation) and [Order Consolidation](../configuration/outbound/order-processing/order-consolidation.md).
    
2.  If you are using the STD-PLANWAVE rule, make sure that all shipments that you want included in the wave have the same Wave Set. See [Add or modify a shipment](outbound/procedures-for-shipments.md).
3.  Plan the wave. The wave status changes to Planned. See [Plan a wave](../shared-functions/waves-and-picks/procedures-for-waves.md).
4.  Allocate inventory for the wave to create the picks to satisfy the shipments for the wave. The wave status changes to Allocated. See [Allocate a wave](../shared-functions/waves-and-picks/procedures-for-waves.md). Picks for the wave are created with a Held status.
5.  Schedule the picks for release. The wave status changes to Scheduled for Release, and the status of the picks changes to Pending. See [Release a wave](../shared-functions/waves-and-picks/procedures-for-waves.md).
6.  Picks are released based on your pick release configuration. The wave status changes to Released.
7.  If needed, modify waves. See [Remove an order from a wave](../shared-functions/waves-and-picks/procedures-for-waves.md) and [Remove a shipment or load from a wave](../shared-functions/waves-and-picks/procedures-for-waves.md).
8.  Monitor the progress of the wave by viewing information on the Waves dashboard and in the wave details. See [Procedures for waves](../shared-functions/waves-and-picks/procedures-for-waves.md).
9.  If needed, change the work queue priority of the picks in the wave. See [Change the priority of a wave](../shared-functions/waves-and-picks/procedures-for-waves.md).
10.  If needed, cancel picks or cross docks for a wave, or unallocate the entire wave. The wave status changes to Planned. See [Perform actions on picks](../shared-functions/waves-and-picks/procedures-for-picks-and-work-assignments.md), [Cancel cross docking](outbound/procedures-for-shorts-and-replenishments.md), or [Unallocate a wave](../shared-functions/waves-and-picks/procedures-for-waves.md). You can also delete a wave to remove it entirely from the application. See [Delete a wave](../shared-functions/waves-and-picks/procedures-for-waves.md).
11.  After all picking for the wave is complete, the wave status changes to Complete.

## Automatic shipment creation

When you plan outbound orders into a wave without first creating a shipment, the application automatically runs through a sequential list of shipment creation rules to create valid shipments.

The first three rules are applied to the entire wave. The remaining rules break the wave by looking for order lines with matching characteristics and grouping them into shipments.

The automatic process uses the following shipment creation rules:

1.  **Add missing married lines**: Ensures all order lines with the same married code are selected when you select order lines for a shipment. For example, if there are three order lines with a married code of "A," but you only select two of them, the application selects the third to ensure that the married lines ship together.
2.  **Add missing sub-lines**: Ensures all sub-lines for an order line are selected when you select order lines for a shipment. For example, if an order line has four sub-lines, but you only select three of them, the application selects the fourth to ensure that the sub-lines ship together.
3.  **Consolidate by married code**: Ensures that all order lines with the same married code are shipped together. To do this, the application searches your selected orders for all lines with a married code. It then populates a ship-with field on these lines with a sequence number. For example, all lines with a married code of "A" may be given a ship-with value of 12345, and all lines with a married code of "B" may be given a ship-with value of 54321. The application then ensures that all lines with the same ship-with value are grouped into the same shipment. This rule also applies to sub-lines.

## Short allocations

A short allocation occurs when a wave is allocated and there is not enough inventory available to fill an outbound order. Short allocations can occur for different reasons, including the following examples:

-   Necessary inventory is outside of the allocation search path.
-   Inventory is on a hold that does not allow allocation.
-   Inventory is in a location that is in error.
-   Attributes of the available inventory are different from the needs of the order.

When short allocations occur, you can view the reasons that caused the short. See [View short order line details](outbound/procedures-for-shorts-and-replenishments.md) or [Manage short loads and items](../shipping/shipping-issues/procedures-for-shipping-issues.md).

If the application is configured to generate emergency replenishments to find and pick the missing inventory for an order that was shorted, you can view and cancel them. See [Cancel a short and reallocate](dashboard.md).

## Search path log

The search path log provides access to the list of allocation processes that took place during inventory allocation for an order line. The list can include allocation log files for picks, demand replenishments, and emergency replenishments.

You can view the search path log for a short order line by viewing the short order line details, and then selecting the **Search Path Log** tab. See [View short order line details](outbound/procedures-for-shorts-and-replenishments.md).

**Note**: Log files are available if logging was enabled prior to allocation taking place. See [Manual Allocation](../configuration/outbound/allocation/manual-allocation.md) and [Post Allocation](../configuration/outbound/allocation/post-allocation.md).

You can select a log file to display processing details and a message that explains the reason that inventory could not be allocated. When you select a log file to view, the search path log displays the following information:

-   Sequence in which the allocation process took place for the item quantity
-   Allocation search path that was used to find inventory
-   Location that was evaluated for inventory
-   LPN in the location that was evaluated for inventory
-   Filter that the inventory failed to pass, and therefore, did not qualify for allocation
-   Message that explains why the process failed to allocate the required inventory

## Replenishment destination log

The replenishment destination log displays the processing details and the reason why replenishment could not find a destination location for replenishment inventory. For example, a replenishment destination can be disqualified for any of the following reasons:

-   Inventory could not fit in the location
-   LPN height is taller than location
-   Inventory could not be mixed with current inventory in location
-   For date-controlled inventory, the deposit would exceed the allowable date window when added to inventory already in the location
-   The intermediate hop location was full or in error status

You can view the replenishment destination log for a short order line by viewing the short order line details, and then selecting the **Replen Destination Log** tab. See [View short order line details](outbound/procedures-for-shorts-and-replenishments.md).

**Note**: Log files are available if logging was enabled prior to allocation taking place. See [Manual Allocation](../configuration/outbound/allocation/manual-allocation.md) and [Post Allocation](../configuration/outbound/allocation/post-allocation.md).

When you select a log file to view, the replenishment destination log displays the following information:

-   Building and storage location that the process attempted to replenish
-   Value that was compared to determine if the location was a match for the inventory
-   Value for the location to which the replenishment deposit was attempted
-   Value of the inventory that the application is attempting to put in the replenishment destination location
-   Reason that the destination location was not a match for the replenishment

## Delivery sequence loading

Delivery sequence loading is a process in which the orders on a stop are loaded in a specific sequence. You can use this process to sequence groups of orders on a stop, and to sequence the orders within each separate group, for loading and, if configured, building work assignments. For example, assume a stop has two orders for Store1 and two orders for Store2, and that the orders for Store2 need to be loaded in sequence first. Using delivery sequence loading, you can ensure that inventory is picked and loaded in the following sequence: Store2 Order1, Store2 Order2, Store1 Order1, and Store1 Order2.

The application processes delivery sequence loading based on the following attributes:

-   **Delivery Number**: Assigned to orders on a stop to group multiple orders together that need to be delivered to the same destination. Delivery numbers can be used when a customer stop on a load contains orders for multiple locations in the same geographic region. In this case, the deliveries on the stop are either made to each customer location (ship-to customer), or the stop is unloaded at an intermediate location (such as a route-to customer) prior to delivery. Orders destined to the same ship-to customer should have the same delivery number. For example, assume that a customer has two stores (A and B) near each other, and that their orders are included on the same stop. All orders for Store A would have the same delivery number (A01, for example), and all the orders for Store B would have a different delivery number (B01).
-   **Delivery Sequence**: Assigned to the orders within one or more delivery number groups on a stop so they are loaded in a specific sequence. If a stop includes 4 orders, you can assign a sequential number to each one, and the operator is directed to load the orders based on the sequence. If orders on a stop have different delivery numbers, then the application first sorts the orders by delivery number and then by delivery sequence. For example, assume that Store A and Store B (from the previous example) each have 2 orders on a stop. Also, assume that the orders for delivery number A01 have a delivery sequence of 1 and 2, and the orders for B01 have a delivery sequence of 1 and 2. If the application is configured to load in descending order, the orders are loaded in the following sequence: B01 2, B01 1, A01 2, and A01 1.
-   **Delivery Sequence Loading Order**: Determines whether inventory should be loaded in ascending or descending order of the delivery sequence defined for the orders in a stop. Alternatively, delivery sequence loading order can be disabled to load the orders in any sequence. For example, if the application is configured to load in ascending order, the orders from the previous example are loaded in the following sequence: A01 1, A01 2, B01 1, B01 2. Delivery sequence loading order can be defined for a warehouse, a client warehouse (in a 3PL environment), and a shipment. The value defined for a shipment overrides the client value, which overrides the warehouse value.

**Note**: To ensure proper loading sequence, all shipments on a stop should have the same delivery sequence loading order.

For example, assume that multiple orders on a stop are destined to the same route-to customer (CUST1); and from there, the orders are destined to two different ship-to customers. Also, assume that the orders have the following attributes:

   
| Ship-to Customer | Order | Delivery Number | Delivery Sequence |
| --- | --- | --- | --- |
| Store A | ORD1A | A01 | 1 |
| Store A | ORD2A | A02 | 3 |
| Store A | ORD3A | A02 | 2 |
| Store B | ORD1B | B02 | 1 |
| Store B | ORD2B | B02 | 2 |

If the delivery sequence loading order for the associated shipments is ascending, then the application enforces loading the orders in the following sequence (based on delivery number first and then delivery sequence): ORD1A, ORD3A, ORD2A, ORD1B, and ORD2B. Alternatively, if the loading sequence for the shipments was descending, then the orders would be loaded in reverse sequence.

You can use the delivery number and delivery sequence attributes as criteria for work assignment creation and wave rules (allocation). This allows you to group, sort, and sequence picks for allocation and work assignments based on one or more values for the delivery number or delivery sequence order attributes. See [Delivery sequence loading setup](#Delivery_sequence_loading_order_setup_).

For example, assume you want to build work assignments using the delivery number and delivery sequence from the previous example as criteria. A basic work assignment rule configuration might include the following attributes:

-   **Selection Criteria**: Route-To Customer (Outbound Order entity)
-   **Criteria Sequence**: Delivery Number (Descending)
-   **Pick Order**: Delivery Sequence (Descending)

When the application builds work assignments based on this rule, any order picks destined to CUST1 are considered to be eligible. The application then fills work assignments with picks for Store B first (delivery number B02), and then sets the pick order so that ORD2B picks are performed first followed by picks for ORD1B (delivery sequence 2 and 1, respectively).

## Delivery sequence loading order setup

Delivery sequence loading order indicates the order in which shipments should be loaded onto an outbound trailer based on the delivery number and delivery sequence on the outbound orders.

You must perform the following tasks to configure the delivery sequence loading order.

1.  Define the delivery sequence loading order. The loading order determines whether inventory should be loaded in ascending or descending order of the delivery numbers and delivery sequence defined for the orders in a stop. In a 3PL environment, you can define a loading order for a client and a shipment, but not for the warehouse; in a non-3PL environment, you can define a loading order for the warehouse and a shipment. The loading order defined for a shipment overrides the warehouse value and client value.
    
    **Note**: To ensure proper loading, all shipments within a stop should have the same delivery sequence loading order.
    
2.  Define delivery numbers and a delivery sequence for the orders on a stop. Delivery numbers are assigned to orders on a stop to group multiple orders together that need to be delivered to the same destination. Delivery sequence numbers are assigned to the orders within one or more delivery number groups on a stop so they are loaded in a specific sequence. Orders that are downloaded from the host may include these values. See [Add or modify an order](outbound/procedures-for-orders.md).
3.  To plan waves based on the delivery number or delivery sequence, configure wave rules. Specifically, you can select delivery number or delivery sequence as a field parameter, meaning that the application will only include orders that meet the parameter values in the wave for allocation. For example, you can create a wave rule so that only orders with specific delivery numbers are allocated using that rule. See [Wave rules](../configuration/outbound/allocation/manual-allocation.md).
4.  To build work assignment using the delivery number or delivery sequence, configure the following work assignment rule attributes:
    -   **Pick order**: Determines the order in which picks will be performed for a work assignment. For example, you can add delivery sequence as criteria and then define whether the application should sort them ascending or descending to ensure picks are listed on the work assignment in a specific order.
    -   **Selection criteria**: Determines which picks are eligible to be included in work assignments based on the rule. For example, you can add one or more delivery numbers as the selection criteria for the entity Outbound Order, ensuring that only picks for orders with the defined delivery numbers are added to work assignments created using the rule.
    -   **Criteria sequence**: Determines the order in which eligible picks are sorted before being added to a work assignment. For example, you can select the delivery number as criteria to be sorted in ascending order; the application sorts eligible picks based on the alphanumeric delivery numbers on the associated orders, and adds picks at the top of the list to the work assignment first.

See [Work assignment rules](../configuration/outbound/picking/work-assignments.md).

6.  If you are building work assignments using the delivery number or sequence, consider the following work assignment configurations to keep orders together:
    -   **Fill Work Assignment with Similar Picks First**: You can set this field to Orders to keep picks for an order together on the same assignment; work assignments are filled with picks for the same order first.
    -   **Prevent Pick Consolidation**: You can set this field to Yes to prevent the application from consolidating picks for the same item from the same location; consolidating such picks may result in the picks being performed out of delivery sequence loading order.
    -   **Pick Tasks on Existing Work Assignment**: You can set this field to No so that new picks for a different order are not added to a work assignment for an existing order that has capacity.
    -   **Assign Pick to Existing Assignment**: You can set this field to Never so that the content of a work assignment cannot be updated once the assignment has been generated.

See [Configure work assignments](../configuration/outbound/picking/work-assignments/procedures-for-work-assignments.md).

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
