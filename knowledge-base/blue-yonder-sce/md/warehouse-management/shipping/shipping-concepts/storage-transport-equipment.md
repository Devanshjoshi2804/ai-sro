---
title: "Storage transport equipment"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/storage_transport_equipment.htm"
source: "/content/storage_transport_equipment.htm"
toc_path:
  - "Warehouse Management"
  - "Shipping"
  - "Shipping concepts"
  - "Storage transport equipment"
sections:
  - "Storage transport equipment loading and unloading processes"
  - "Loading"
  - "Unloading"
  - "Storage transport equipment shipping process"
  - "Storage transport equipment scenarios"
  - "Use transport equipment for storage"
  - "Fulfill outbound order with hot items"
  - "Specify as a putaway location"
images: []
source_sha1: 4a4bf3b62f13836359681f96f657d39ce959d409
---
# Storage transport equipment

Storage transport equipment is equipment that is used for storing inventory that has been identified. Once loaded, storage transport equipment can be moved to the yard until either storage space becomes available in the warehouse, or demand for the inventory, in the form of outbound orders, requires the inventory to be allocated and shipped.

The following actions can be performed on storage transport equipment:

-   Loaded by moving inventory from a location in the warehouse to the storage transport equipment (no picking necessary)
-   Unloaded by moving inventory from the storage transport equipment to a location in the warehouse (no unpicking necessary)
-   Specified as a putaway location, such as for finished goods coming off of a production line
    
    **Note**: While storage transport equipment can be a valid putaway location, the inventory that is loaded is not eligible for allocation.
    
-   Moved as wanted between shipping dock door and yard locations
-   Reopened after being closed
-   Converted to shipping transport equipment so that the inventory contained within the equipment can be delivered to a customer
-   Included as the pick zone in an allocation or replenishment search path as the location from which inventory is allocated
    
-   Load the transport equipment (inventory move or transfer functions are used instead)

The application does not let you perform the following actions on storage transport equipment:

-   Assign or deassign a outbound load
-   Maintain inbound orders

You can create a piece of storage transport equipment and, if necessary, convert it to shipping transport equipment. For details, see [Add or modify transport equipment](../../shared-functions/transport-equipment/procedures-for-transport-equipment.md) and [Convert storage transport equipment to shipping equipment](../../shared-functions/transport-equipment/procedures-for-transport-equipment.md).

## Storage transport equipment loading and unloading processes

The following processes describe loading and unloading storage transport equipment.

### Loading

The following process describes how storage transport equipment is loaded:

1.  Add a storage transport equipment. See [Add or modify transport equipment](../../shared-functions/transport-equipment/procedures-for-transport-equipment.md). The transport equipment is created with a status of Expected.
    
    **Note**: A piece of shipping or receiving transport equipment can be changed to storage transport equipment if it does not contain inventory and does not have an outbound load assigned to it.
    
2.  The transport equipment is checked in to a shipping dock door and has a status of Open for Loading. The application creates a location for the equipment in a location type that is configured for storage transport equipment. The location of the storage transport equipment is identified by the value in the **Shipment Location** field.
3.  Inventory from any location can be transferred to the storage transport equipment using the web client, RF LPN Transfer, or RF Case Transfer. See [Move inventory](../../shared-functions/inventory/procedures-for-lpns.md).
4.  When the first LPN is placed on the transport equipment, the status of the equipment changes to Loading.
5.  When inventory transfer is complete, you can move the transport equipment to a yard location and close the equipment using the web client or RF Close Transport Equipment.

### Unloading

The following process describes how storage transport equipment is unloaded:

1.  The storage equipment must be moved to a shipping dock door in order to be unloaded.
2.  If the equipment has been closed, it must be reopened using the web client or RF Reopen Transport Equipment.
3.  You use the web client, RF LPN Transfer, or RF Case Transfer to move the inventory off the transport equipment. After the inventory is unloaded, it is subject to the normal putaway or cross docking processes that would take place for received inventory.
4.  The unloaded transport equipment can be closed and moved to another location.

## Storage transport equipment shipping process

A piece of storage transport equipment that has been loaded can be converted to shipping transport equipment so that its inventory can be shipped without having to move it to another piece of transport equipment. See [Convert storage transport equipment to shipping equipment](../../shared-functions/transport-equipment/procedures-for-transport-equipment.md).

The following is the process by which storage transport equipment is converted to shipping transport equipment:

1.  Create an appointment for the storage transport equipment. See [Add or modify an appointment](../../shared-functions/appointments/procedures-for-appointments.md).
2.  Find the storage transport equipment that needs to be converted. The equipment must have a status of Loading or Closed.
3.  Prepare the transport equipment for shipping.
    
    **Notes**:
    
    -   If inventory on the equipment is on hold, it cannot be shipped. You must either remove the hold or move the inventory off the transport equipment.
    -   If inventory on the transport equipment is serialized (either Cradle to Grave or Inbound Capture/Outbound Validation), it cannot be shipped.
    
4.  You use the Prepare for Shipping page to specify the client (for a 3PL environment), ship-to customer and address, and allocation profile that is to be applied to the inventory. If inventory falls outside the allocation profile, those details are displayed but the inventory can still be shipped.
5.  If inventory can be shipped, the application automatically performs the following actions:
    -   Creates an order for the inventory on the transport equipment
    -   Creates a shipment for the outbound order
    -   Assigns the outbound shipment to the storage transport equipment
    -   Creates a stop with the load sequence 1
    -   Creates an outbound load for the transport equipment and the stop
    -   Assigns the shipment to the stop
    -   Creates the work assignment for picking the inventory and sets the picking as Complete
    -   Sets the shipment and stop status to Complete
    -   Changes the transport equipment code from Storage Transport Equipment to Shipping Transport Equipment
    -   Leaves the transport equipment status at Loaded
6.  The transport equipment can be closed and dispatched.
    

## Storage transport equipment scenarios

The following scenarios provide examples of storage transport equipment use.

### Use transport equipment for storage

You can configure transport equipment to be used for storage by assigning the storage transport equipment type and setting the **Use** field to Storage. For example, a storage zone in a warehouse is full and ran out of space to store inventory that arrives into the warehouse. In this scenario, transport equipment can be used as storage. Once the inventory is loaded, the storage transport equipment can be moved to the yard until storage space becomes available in the warehouse. See [Add or modify a transport equipment type](../../configuration/equipment/equipment/transport-equipment-type.md) and [Add or modify transport equipment](../../shared-functions/transport-equipment/procedures-for-transport-equipment.md).

**Note**: Shipping or receiving transport equipment can be changed to storage transport equipment if it does not contain inventory and does not have an outbound load assigned to it.

### Fulfill outbound order with hot items

You can configure the processing priority to fulfill short orders with hot items from receiving or storage transport equipment. When there is not enough inventory available in the warehouse to satisfy an outbound order, but the inventory is on receiving or storage transport equipment, the item is considered hot. The application can fulfill the short order using the hot inventory in the configured priority.

You use inbound receiving identification to select the priority by which the application will attempt to find inventory for short allocation demand. The application applies the Hot tag to receiving or storage transport equipment that contains inventory that could be used to satisfy an order that was allocated short. If no priority is set, the application attempts to find the inventory first on receiving transport equipment and then on storage transport equipment. To configure the processing priority for transport equipment with hot items, see [Configure inbound identification](../../configuration/inbound/receiving/inbound-identification.md).

### Specify as a putaway location

You can configure storage search paths to use storage transport equipment. For example, you receive inventory into the warehouse and would like to store it. If you want storage transport equipment to be considered as a putaway location, configure an inbound storage search path to use the storage transport equipment zone. To be considered for putaway, the storage transport equipment must be parked at shipping dock door. See [Add or modify a storage search path](../../configuration/inbound/storage/storage-search-paths.md).

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
