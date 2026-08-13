---
title: "Shipping concepts"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/shipping_concepts.htm"
source: "/content/shipping_concepts.htm"
toc_path:
  - "Warehouse Management"
  - "Shipping"
  - "Shipping concepts"
sections:
  - "Shipping functionality"
  - "Shipping process"
  - "Loads"
  - "Shipments"
  - "Manual shipment creation"
  - "Shipment adjustments"
  - "Adjustment process flow"
  - "Shipment to staging lane assignments"
  - "Example: Multiple staging lanes in multiple buildings"
  - "Example: Multiple staging lanes in one building"
  - "How it works"
  - "Handling unit shipping"
images: []
source_sha1: 3d3457935f42033b13a50d1ac544a7c2878993cc
---
# Shipping concepts

You use the Shipping module to manage the people, equipment, inventory, and processes that ship inventory from the warehouse to your customers. You can make adjustments to inventory, work, shipments, loads, equipment, and other factors that can improve the productivity and efficiency of the warehouse shipping activities.

## Shipping functionality

Shipping is the act of transporting inventory from the warehouse with all the required paperwork and transactions. The following events must take place before you can begin the process of shipping inventory from your facility:

-   An order must be created manually or downloaded from the host system.
-   The order must be planned into a wave.
-   The wave must be allocated.
-   Inventory for the wave must be picked and delivered to a ship staging location. When using RF fluid loading, you can deliver picked inventory directly to the transport equipment without staging it.

## Shipping process

The shipping process consists of the following tasks:

1.  **Stage the shipment**. A shipment is staged, either manually or automatically, when all the inventory for the shipment has been delivered to a staging lane. When a shipment is staged, the inventory is available for directed loading. To ensure that a shipment is ready to stage, you can verify that the arrived quantity, applied quantity, and pick quantity for a selected shipment are equal. After you stage a shipment, you no longer have the ability to reallocate any inventory that is missing due to cancelled picks or shipment adjustments.
2.  **Change the carrier**. After a shipment is staged, you may change the carrier if the order allows it and the order processing configuration allows it.
3.  **Create an outbound load**. Before staged shipments can be loaded onto the transportation equipment, they must be assigned to an outbound load. A load defines the stops that the transportation equipment makes to deliver shipments. Typically, load information is sent from a host or transportation application; however, you can create and modify loads manually or have the application generate one for you.
4.  **Print the paperwork**. Paperwork can be a simple packing list, the bill of lading, or custom paperwork. You can print paperwork at either the stop, shipment, or load level.
5.  **Load the stop**. When you load a stop, the inventory is moved from the staging lane to the transport equipment. You can determine a move method, and then you determine how you want to close and dispatch the transportation equipment.
    
    **Note**: When single scan loading is enabled in the outbound loading configuration, the operator can scan the dock door (location) to load all of the LPNs at once.
    
    When inventory is loaded onto transport equipment, it is tracked in a logical location type. This can be designed as four-wall inventory, so that the inventory in this area can be included in inventory summaries sent to the host. When the shipping transport equipment is dispatched, the inventory is automatically moved to a logical dispatch location type, where it is not considered four-wall inventory.
    
    When loading a stop, an operator may be prompted to perform workflows. After loading all of the stops, if any of the shipments on the transportation equipment contain inventory for which you captured the average catch quantity that are out of tolerance, a **Tolerance** tag is displayed. LPNs on the transportation equipment can be out of tolerance if they were consolidated and the newer catch quantity for the LPN caused older pieces of inventory on the LPN to go out of tolerance. See [Tags](../shared-functions/transport-equipment/tags.md).
    
6.  **Split a less-than-truckload (LTL) shipment (optional)**. As you load an LTL shipment, you may find that the entire shipment will not fit on the transportation equipment. When this occurs, if the application is configured to allow it (**LTL Loads** field set to Yes), you can split the existing LTL shipment. When you split a shipment, you move the remaining inventory to a new shipment or to a different, existing shipment. When you split inventory to a new shipment, you can specify a document number and PRO number. See [Configure outbound loading](../configuration/outbound/shipping/outbound-loading.md).
    
    **Note**: If the **Partial** field is set to No on an order line, then the application does not allow inventory associated with the order line to be split onto a new shipment.
    
7.  **Close the transport equipment**. After the transportation equipment is closed, you can choose to dispatch the equipment immediately or hold it in the yard. When you hold transportation equipment in the yard, you specify a dispatch date.
8.  **Dispatch the transport equipment**. The transport equipment must be closed before it can be dispatched. When you dispatch shipping transport equipment, inventory on the equipment is automatically moved to a logical dispatch location type, where it is no longer considered four-wall inventory.

## Loads

A load is a collection of stops that are shipped together on a single piece of transport equipment. Before you can load staged shipments onto transport equipment, they must be assigned to a stop that is part of an outbound load. Each stop is assigned a stop sequence that determines the order in which the stops must be loaded into the transport equipment. The application does not allow stops to be loaded out of sequence unless one of the following configurations is set:

-   The load is configured to ignore the stop sequence order.
-   An item on the shipment is part of an item family to which a break stop sequence code is applied. If a load is configured to ignore the stop sequence order, it overrides the break stop sequence code.

Load information is typically downloaded from the host; however, you can add and modify loads manually, when needed.

## Shipments

A shipment is a group of orders or order lines that are allocated together and shipped to the same location. Within the application, shipments can be created manually or automatically based on a series of pre-defined rules.

## Manual shipment creation

When you manually create shipments, you are responsible for ensuring the validity of the shipment. That is, you must be sure that the orders you select to ship together have the same route-to customer, destination zone, carrier, carrier service, payment terms, shipping date, and delivery date. You must also verify acceptable shipment weights.

## Shipment adjustments

A shipment adjustment is a procedure in which picked inventory is adjusted off of a shipment. The inventory is typically directed to a problem location where it can be evaluated for further processing or returned to storage. Shipment adjustments are made for a number of reasons, some of which include the following examples:

-   Inventory is damaged
-   Inventory has aged past its expiration date
-   The order line for which the inventory was picked is cancelled

If the order line is not cancelled, the removed inventory causes the shipment to be short. Therefore, the inventory can be reallocated and picked so that the shipment is complete; otherwise, the shipment remains short of the original pick quantity.

**IMPORTANT**: You cannot adjust inventory off of a shipment until the inventory for the shipment has been staged.

## Adjustment process flow

A shipment adjustment consists of a multi-step process that removes inventory from a shipment and determines how the application handles the adjusted inventory. The following process outlines the basic steps for adjusting inventory off of a shipment:

1.  **Move the inventory**. When a shipment adjustment is performed, the inventory is logically moved to a temporary adjustment location, and is removed from the shipment. The pick quantity for the original shipment is reduced by the adjusted amount, and then added to the pick quantity for the order. The shipment is no longer staged and its status reverts to In Process. If desired, the picks are then reallocated and the operator completes the pick work for the adjusted quantity. If you do not want to reallocate for the adjusted inventory, you must cancel the remaining quantity required for the shipment line.
2.  **If necessary, build a new LPN**. If a partial quantity of inventory (such as a portion of a pallet or separate cartons) is adjusted off of the shipment, then the operator can build a new LPN from the adjusted inventory. The new LPN is used to split mixed pallets or cartons into separate LPNs, or to combine inventory into a single LPN. For example, a pallet is adjusted off of a shipment, but the pallet contains cases of four different items. If your facility does not allow these different items to be stored together, the operator must build four separate LPNs, one for each item.
3.  **Complete the LPN**. To complete the LPN, the operator must finish any necessary sorting, re-labeling, or consolidating to prepare the inventory for storage. After completing an LPN, it is ready for putaway.
4.  **Put away the LPN**. During the adjustment putaway process, the operator selects a storage location manually or lets the application select the optimal location. After confirmation that the adjusted inventory was placed in a storage location, the operator has the option to print and apply pallet labels.

## Shipment to staging lane assignments

When you have large outbound shipments that will fill more than one staging lane, or contain product from more than one building requiring a staging lane in each building, you can manually assign as many staging lanes as you need for a shipment. You can also stage from multiple buildings to the same destination building.

### Example: Multiple staging lanes in multiple buildings

If you are in the grocery industry, you might store your dry inventory in one building (B1) and your frozen inventory in another building (B2). Therefore, you need two staging lanes, one in B1 to which to pick your dry inventory and one in B2 to which to pick your frozen inventory.

### Example: Multiple staging lanes in one building

You may want to assign multiple staging lanes in the same building for a particular outbound load so that shipments for specific customers are staged in predefined staging lanes, or so that large shipments that require more space than is available in one staging lane can be staged to multiple staging lanes.

### How it works

The following steps describe how to assign multiple staging lanes to a shipment:

1.  Assign a shipment or load to a staging lane.
2.  When allocating inventory, the application will assign a destination location to the picks based on the source building of the inventory and the assigned staging lane.
    
    **Note**: If the inventory exceeds the capacity of a staging lane and multiple staging lanes were assigned in the same destination building, the application routes the picks that would exceed the capacity of a staging lane to the next staging lane in order by priority.
    
3.  An operator picks inventory to the staging lanes that were assigned by allocation.

## Handling unit shipping

If your application is configured for inventory handling unit tracking, then you can load and ship empty serialized and non-serialized handling units on shipping transport equipment. You may want to ship empty handling units to maintain a distributed quantity between customers or warehouses.

Non-serialized handling units are tracked by the total quantity of a specific handling unit type. Serialized handling units are tracked individually, by handling unit LPN. When you load empty non-serialized handling units, the application updates the on-hand quantity for the handling unit type, and adds the handling unit type quantity information to the shipment. When you load serialized handling units, the application tracks the unique handling unit LPN and any associated attributes.

**Note**: To load empty serialized handling units, you must use an RF device.

To load empty non-serialized handling units, see [Load or unload empty handling units](../outbound-planner/outbound/procedures-for-shipments.md).

You can view a summary of loaded and shipped empty serialized and non-serialized handling units on a shipment. See [View detailed shipment information](../outbound-planner/outbound/procedures-for-shipments.md).

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
