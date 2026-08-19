---
title: "Locations"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/locations.htm"
source: "/content/locations.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Warehouse"
  - "Locations"
sections:
  - "Location configuration process"
  - "Location capacity"
  - "Pallet stack height and stack methods"
  - "Location handling unit capacity"
  - "Narrow aisle overview"
images: []
source_sha1: ebe8a983ac678aab312fac771096e268e7992cec
---
# Locations

A location is a uniquely identified position within an area of your facility. You use locations to receive, store, stage, and ship inventory. A location inherits the attributes of the location type to which it belongs, but some location attributes can be configured differently from other locations of the same type.

Typically, locations are defined during installation; however, you can add, modify, and delete locations at any time to meet changing storage and facility requirements.

## Location configuration process

The process of creating and configuring locations is similar for all types of locations. The following list provides an overview of each step in the process:

1.  Before you add locations, you must have already defined the location type for the locations. Every location is assigned to a location type. Location type attributes define how the application tracks and processes inventory or transport equipment in the location. See [Location Types](locations/location-types.md).
2.  Add areas and locations. Use this step to add locations to a new or existing area. When you perform this step, the application directs you through the following task flow:
    1.  Adding an area or selecting an existing area.
    2.  For locations other than storage locations, specifying a range of locations and the function (location type) for the locations.
    3.  For storage locations, adding or selecting a storage template, location naming scheme, and velocity.
        -   The storage template defines the storage level, dimensions, capacity, and pallet stacking restrictions.
        -   The location naming scheme defines a structure for location names that can include identifiers for bay, area, aisle, position, and other segments that you define.
        -   Velocity is a value that represents the speed at which inventory is picked from the locations. It is a common attribute applied to storage path configurations used, for example, to direct fast-moving items to the most accessible pickface locations.
    4.  Verifying and correcting any conflicts with existing locations that have the same name.
    5.  Defining the location capacity, dimensions, and pallet stacking restrictions. Location capacity is not required for dock doors and is specified elsewhere for storage locations.
    6.  Reviewing the list of locations that you added. At this point you can go back and make changes, or finish the process to save the locations.
3.  Modify multiple locations. This step is typically performed after you add a range of locations, but can be performed anytime you want to change one or more attributes of multiple locations at the same time. This step is performed in the locations grid, using the **Update Location Attributes** option available from the **Action** drop-down list.
4.  Modify a location. This step is typically performed to enable or disable a location, or to change one or more attributes of single location.

## Location capacity

The application calculates a location's capacity as inventory is added to it. The application uses the location capacity along with the maximum capacity specified for a location to determine when a location is full.

For locations that are configured to use a pallet stacking restriction (either Interlock Stack Method or Pallet Stack Height), the application uses the stack method or stack height associated with the item footprint being stored in the location to determine when the location is full.

When you define locations to which inventory can be moved (such as storage, staging, and pickup and deposit locations), you can specify one of the following location capacity options:

-   **Pallet**: Expresses capacity in the number of pallets or LPNs that the location can hold. For example, if the maximum capacity specified for a location is 2 pallets, then the application allows 2 pallets or LPNs into the location before changing its status to full. For example, assume the following values:
    
    -   The maximum capacity defined for a location is 2 pallets.
    -   Item A has a packaging configuration of 1 each per drum and 6 drums per pallet.
    -   One pallet of Item A, identified as LPN100, is directed to the location, and the inventory now shows 6 eaches in the location.
    -   One drum of Item A, identified as LPN200, is directed to the same location, and the inventory now shows 7 eaches in the location.
        
    
    As a result, the application changes the location status to full because it contains 2 LPNs, even though one is a partial LPN.
    
    **Note**: If a pallet stack restriction is specified for a pallet-tracked location, the application may adjust capacity based on the item being stored in the location.
    
-   **Length**: Expresses capacity by the length of the location. Capacity by length is typically used for case flow rack locations. The application determines the number of cases that can fit within the length of location when the cases are placed end to end. For example, if the maximum capacity specified for a location is a length of 250, it will be considered full when the length of all the cases in the location adds up to 250. For example, assume the following values:
    
    -   The maximum capacity defined for a flow rack location is 250.
    -   Item A has a footprint of 30Lx15Hx20W for 1 case.
        
    
    As a result, the application does not allow more than 8 cases into this location (8 x 30 = 240) to ensure that the total length of the LPNs does not exceed the location’s length. The application also evaluates the height of the LPNs to see if they fit into the location.
    
-   **Volume**: Expresses capacity in the volume (length x width x height) of space available in the location. To determine capacity by volume, the application multiplies the maximum height that inventory can be stacked in the location by the width and length of the location. Capacity by volume is typically used for floor storage locations or for pickfaces when items are not assigned to specific locations. For example, assume the following values:
    
    -   The maximum capacity defined by volume for an each pick location is 7200 (24Lx20Hx15W=7200).
    -   Item A has a footprint of 5Lx12Hx4W=240 for one unit.
    -   Item B has a footprint of 2Lx4Hx3W=24 for one unit.
        
    
    The application allows 30 units of Item A (30 x 240 = 7200) or 300 units of Item B (300 x 24 = 7200) in the location. The application also considers the height of the item footprint to see if it fits into the location.
    
    **Note**: If a pallet stack restriction is specified for a volume-tracked location, the application may adjust capacity based on the item being stored in the location.
    
-   **Each**: Expresses capacity as the quantity of pieces (stocking units of measure) of inventory that fit in the location. Typically, items that are picked by eaches are assigned to a specific location. For example, a bin location that is assigned or reserved for 7-inch screws can be defined to hold 500 of those screws.
-   **Case Dimension**: Expresses capacity by the dimension of a case of inventory. When location capacity is set to **Case Dimension**, the **How many cases can case dimension location hold** field is also available for you to define the maximum capacity. The location can support a case of any size, as long as it fits within the location dimensions. In addition, you can limit the number of cases stored in the location by specifying a value for maximum capacity. The location can support a case of any size, as long as it fits within the location dimensions. The application calculates available space based on the assumption that cases are stored side by side.

## Pallet stack height and stack methods

Pallet stack height, specified for an item footprint, defines the number of pallets of an item that can be stacked on top of one another in a location that is configured to respect pallet stack height.

A stack method, assigned to an item footprint, is the interlock stack method that is used to stack pallets of an item in a location that is configured to respect interlock stack methods. A standard stack method places one layer of pallets on top of another with all layers being equal (such as 9 pallets on top of 9 pallets, and so on to reach the pallet stack height). An interlock stack method is a configuration that differs from the standard stack method by reducing the number of pallets that can be added to certain levels. It can define, for example, that the second level of a single pallet width stack has 1 less pallet than the floor level, the third level has 2 less pallets than the floor level, and the fourth level has 3 less pallets than the floor level.

The pallet stack restriction defined for a location specifies whether pallet stack height is limited in the location, and if so, how it is calculated. A pallet stack restriction can be defined for locations that have a capacity code of Pallet or Volume. The application uses a pallet stack restriction to direct pallet stacking by displaying the stack method to the operator, and recalculating, if necessary, the location’s maximum capacity based on the item stored in the location.

The recalculation of the location's maximum capacity takes place when single-item, single-footprint inventory is deposited to an empty location that is configured to respect pallet stack height or an interlock stack method. The calculations are based on the item footprint definition. When a location is emptied, the value of its original maximum capacity is restored.

Location capacity recalculation does not take place if the following conditions exist:

-   Location is configured for Interlock Stack Method, but the item footprint has no stack method specified.
-   Location is configured for Pallet Stack Height, but the item footprint does not specify a stack height.
-   Location is not empty when the deposit is made.
-   Inventory being deposited contains either multiple items or multiple item footprints.
-   Location capacity code for the location is something other than Pallet or Volume.

For locations in which capacity is defined by Pallet or Volume, the following pallet stack restrictions are available:

-   **Pallet Stack Height**: The application uses the stack height defined for the item footprint as well as the location's maximum capacity to determine when the location is full. For example, a stack height may limit the number of pallets of the item that can be stored in the location. If a location has room for 4 levels of an item, but the item footprint's stack height is 3, then the location is considered full after 3 levels are deposited.
-   **Interlock Stack Method**: The application uses the stack method defined for the item footprint as well as the location’s maximum capacity to determine when the location is full. For example, the stack method may require that each layer of a single pallet width stack contain 1 less pallet than the previous layer, which means fewer pallets would fit in the location.
-   **No Stacking Restrictions**: The application considers the location's maximum capacity to determine when the location is full, regardless of whether a stack method or stack height is specified for the item footprint.

## Location handling unit capacity

If inventory handling unit tracking is enabled for the warehouse, then for a location, you can define the minimum number of serialized handling units, by type, that are required in a location.

To ensure that the number of handling units does not fall below your defined minimum, you can configure a task to evaluate handling unit levels periodically (using the Console) and an Event Management event to alert you when the levels fall below your minimum level. Location handling unit capacity tracking is only available for empty, serialized handling units in the Inventory handling unit category. Serialized handling units are those that are tracked as individuals by a unique handling unit identifier.

## Narrow aisle overview

A narrow aisle storage area typically consists of racks of storage locations separated by very narrow aisles. The aisle is typically the width of one material handling vehicle and may not provide enough room for multiple vehicles or for a vehicle to turn around in the aisle.

You can configure the application to achieve an optimal flow of inventory in and out of narrow aisle storage locations. See [Narrow aisle inventory movement and storage configuration points](../inbound/storage/storage-zones.md) and [Narrow aisle inventory replenishment configuration points](../inventory/replenishments/narrow-aisle-inventory-replenishment-configuration-points.md).

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
