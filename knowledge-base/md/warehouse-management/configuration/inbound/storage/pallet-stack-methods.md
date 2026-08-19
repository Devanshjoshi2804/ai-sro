---
title: "Pallet Stack Methods"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/pallet_stack_methods.htm"
source: "/content/pallet_stack_methods.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inbound"
  - "Storage"
  - "Pallet Stack Methods"
sections:
  - "Location capacity recalculation"
  - "Pallet stack restrictions setup"
  - "Add or modify a pallet stack method"
  - "Delete a pallet stack method"
images: []
source_sha1: 9a3e4d39481d744b8965bc93255154ceccfd16f8
---
# Pallet Stack Methods

A stack method is a configuration that defines how pallets need to be stacked in a location. Regular pallet stacking allows for the placement of the same number of pallets on each layer of a stack (such as 9 pallets on top of 9 pallets, and so on to reach the pallet stack height). An interlock stack method reduces the number of pallets that can be added to certain levels. It can specify, for example, that the second level of a single-pallet-width stack has 2 fewer pallets than the floor level, the third level has 4 fewer pallets than the floor level, and so on.

After you define a stack method, you can assign it to an item footprint. This indicates that stack method applies to inventory that uses the item footprint.

If inventory that uses an interlock stack method is deposited to an empty location, and the location is configured to respect an interlock stack method, then the application notifies the operator of the stack method to use when depositing the inventory. The application also recalculates the default maximum capacity of the location based on the stack method.

## Location capacity recalculation

Location capacity recalculation is the process by which the application automatically recalculates the capacity of a location during putaway based on the configuration of the item footprint being deposited to the location. For example, if the location has a default maximum capacity of 40 pallets, but when a certain interlock stack method is used only 36 pallets fit in the location, then when that method is used the application notifies the operator that the location is full after 36 pallets have been deposited.

Recalculation takes place when the following conditions exist:

-   The location is configured to respect pallet stack height or an interlock stack method.
-   The location is empty when the operator deposits single-item, single-footprint inventory to the location.
-   The item footprint of the deposited inventory is configured with a pallet stack height or an interlock stacking method.

**Note**: If a location's capacity is recalculated, then when the location is emptied, the value of its original default maximum capacity is restored.

Recalculation does not take place if the following conditions exist:

-   The location is configured to respect an interlock stack method, but the item footprint has no stack method specified.
-   The location is configured to respect pallet stack height, but the item footprint does not specify a stack height.
-   The location is not empty when the deposit is made.
-   The inventory being deposited contains either multiple items or multiple item footprints, or its item footprint does not specify a pallet stack height or interlock stacking method.
-   The location capacity code for the location is something other than Pallet or Volume.

## Pallet stack restrictions setup

Perform the following tasks to configure your warehouse for storing items based on the pallet stack method assigned to a location:

1.  Configure stack methods. Define each of the interlock stack methods that are used in the warehouse. See [Add or modify a pallet stack method](#Add_or_modify_a_pallet_stack_method).
2.  Configure item footprints.
    -   Specify the pallet stack height, which is the number of pallets of an item that can be stacked on top of one another in a location that is configured to respect pallet stack height.
    -   Specify the interlock stack method. The interlock stack method describes how pallets of the item should be stacked in locations that are configured to respect interlock stack methods.
        
        See [Add or modify an item](../../inventory/items/items.md).
        
3.  Configure storage locations. Specify a location's pallet stack restriction so that the application uses an item footprint's interlock stack method when calculating the location's maximum capacity. You can select one of the following pallet stack restrictions for locations for which capacity is tracked by either Pallet or Volume:
    -   **Pallet Stack Height**: The application uses the stack height defined for the item footprint as well as the location's maximum capacity to determine when the location is full. For example, a stack height may limit the number of pallets of the item that can be stored in the location. If a location has room for 4 levels of an item, but the item footprint's stack height is 3, then the location is considered full after 3 levels of the item are deposited.
    -   **Interlock Stack Method**: The application uses the interlock stack method defined for the item footprint as well as the location’s maximum capacity to determine when the location is full. For example, the stack method may require that each layer of a single pallet width stack contain 2 fewer pallets than the previous layer, which means fewer pallets would fit in the location.
    -   **No Stacking Restrictions**: The application uses the location's maximum capacity to determine when the location is full, regardless of whether a stack method or stack height is specified for the item footprint.
        
        See [Add storage areas or locations](../../warehouse/locations/storage-locations.md).
        

## Add or modify a pallet stack method

When you configure a pallet stack method, you specify the number of levels in the stack that contain pallets. A level represents a single-pallet-width layer of pallets. You then enter the number of pallets by which to reduce each level from the base; the base is the floor (level 1), which is always 0.

1.  Select **Configuration > Inbound > Storage > Pallet Stack Methods**.
2.  Perform one of the following tasks:
    -   To add a stack method, click **Add**.
    -   To modify a stack method, in the grid, click the stack method.
    -   To copy a stack method, in the grid, select the check box next to the stack method, and then click **Copy**.
3.  In the **Name** and **Description** fields, enter the values for the stack method.
4.  In the **Levels** field, enter the number of levels allowed in a pallet stack. For example, if a stack can be 4 pallets high, then enter 4. The levels are displayed graphically.
    
    **Note**: During putaway, the application does not allow pallets to be stacked higher than the levels defined by the pallet stack method.
    
5.  In the **Reduce by** field for each level above level 1, enter the number of pallets by which the level must be reduced from the number of pallets in level 1. For example, a value of 1 indicates that the level has 1 less pallet than the number of pallets at the floor level; a value of 2 indicates that the level has 2 less pallets than the number of pallets at the floor level, and so on. The **Reduce by** value is defined for a single-pallet-width stack and applies to each column of a stack that is multiple pallets wide. The graphic display shows the level being reduced by the number that you enter.
6.  Click **Save**.

## Delete a pallet stack method

You cannot delete a pallet stack method that is assigned to an item footprint.

1.  Select **Configuration > Inbound > Storage > Pallet Stack Methods**.
2.  In the grid, select the check box next to the pallet stack method to delete.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **Save**.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
