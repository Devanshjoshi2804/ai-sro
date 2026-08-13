---
title: "Handling Unit Types"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/handling_unit_types_section.htm"
source: "/content/handling_unit_types_section.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inventory"
  - "LPN Handling"
  - "Handling Unit Types"
sections:
  - "Handling unit groups"
  - "Add or modify a handling unit type"
  - "Delete a handling unit type"
  - "Add or modify a handling unit type group"
  - "Delete a handling unit type group"
  - "Handling Unit Type fields"
images: []
source_sha1: dfdcf2cfce1e7281c4ee293e111b732543ed6e90
---
# Handling Unit Types

A handling unit type is a classification of handling units (such as pallets, totes, or warehouse equipment) that share the same characteristics such as size and weight as well as whether they are serialized, temporary, or considered a container. If configured to do so, the application tracks the on-hand quantity of handling units by handling unit type and individually by handling unit ID.

## Handling unit groups

A handling unit group is a group of handling unit types that can be substituted for one another during order allocation. When a handling unit type is specified on an order line, allocation attempts to allocate the inventory on that handling unit type.

If inventory on the requested handling unit type cannot be found, the application searches for the inventory on one of the other handling unit types assigned to the same handling unit group as the one that was requested. If inventory is available on one of those handling unit types, the allocation takes place. However, prior to shipping, the inventory must be transferred to the handling unit type that was requested on the order line.

For example, an order is placed for BLUEHATS on handling unit type CHEP. In the warehouse, BLUEHATS is currently located on handling unit type CHEP01 but not on CHEP. However, CHEP, CHEP01, and CHEP02 are part of the CHEPS handling unit group. In this scenario, the application successfully allocates the inventory located on CHEP01.

If inventory did not exist on the requested handling unit type or on one of the alternate handling unit types in the handling unit group, then allocation would fail. When allocation fails, the application creates a short allocation.

A handling unit group can contain multiple handling unit types; however, each handling unit type can only be assigned to one handling unit group.

The application uses handling unit groups during allocation and, if configured to do so, for pick replacements. See [Configure cross docking](../../inbound/cross-docking.md).

When allocating date-controlled inventory, the application looks for a match of the handling unit or handling unit group before considering the inventory rotation method.

## Add or modify a handling unit type

1.  Select **Configuration > Inventory > LPN Handling > Handling Unit Types**.
2.  Above the grid, select **Types**.
3.  Perform one of the following tasks:
    -   To add a handling unit type, from the **Actions** drop-down list, select **Add**.
    -   To modify a handling unit type, in the grid, click the handling unit type.
    -   To copy a handling unit type, in the grid, select the check box next to the handling unit type, and then from the **Actions** drop-down list, select **Copy**.
4.  Perform the following tasks:
    1.  Enter information in the [Handling Unit Type fields](#Handling_Unit_Type_fields).
    2.  To define slots on the handling unit type:
        
        **Note**: Define slots if the handling unit type is enabled for work assignments and contains handling unit types to which an operator can pick inventory; such as to totes on a trolley.
        
        1.  Under **WORK ASSIGNMENT** select **Handling Unit Slots**.
        2.  Click **Add**.
        3.  Enter information in the following fields:
            
            **Note**: When defining multiple slot codes for a single slot handling unit type, numerical slot codes that have different lengths are sorted on the Handling Unit Slots page in order from the lowest number (1 being the lowest) to the highest.
            
            | Field | Description |
            | --- | --- |
            | Slot Handling Unit Type | Handling unit to use as a slot when a work assignment is configured to pick to handling unit slots. This is the handling unit that resides on a primary handling unit. |
            | Starting Slot Code | First code in a range of slot codes to assign to the handling unit type. For example, to define 3 slot codes that use the TOTE1 handling unit type, enter 1 for the starting slot code and 3 for the ending slot code. Each slot code must be unique, but you can define slot codes for multiple handling unit types. |
            | Ending Slot Code | Last code in a range of slot codes. |
            
        4.  Click **Apply**.
    3.  To select cartons to which inventory can be picked during a work assignment:
        
        **Note**: Define slots if the handling unit type is enabled for work assignments and supports cartonized picks.
        
        1.  Under **WORK ASSIGNMENT** select **Cartons**.
        2.  In the **Available** column, select the check box next to the cartons to use.
        3.  Click **Apply**.
    4.  To define features for transport equipment handling unit types:
        
        **Note**: The **Handling Unit Category** must be set to Transport Equipment in order to define features.
        
        1.  Under **TRANSPORT EQUIPMENT** select **Features**.
        2.  In the **Available** column, select the check box next to the features to use.
        3.  In the **Minimum** field, enter the first value in the range of acceptable values.
        4.  In the **Maximum** field, enter the last value in the range of acceptable values.
        5.  Click **Apply**.
5.  Click **Save**.

## Delete a handling unit type

1.  Select **Configuration > Inventory > LPN Handling > Handling Unit Types**.
2.  Above the grid, select **Types**.
3.  In the grid, select the check box next to the handling unit type to delete.
4.  From the **Actions** drop-down list, select **Delete**. A confirmation message is displayed.
5.  Click **OK**.

## Add or modify a handling unit type group

1.  Select **Configuration > Inventory > LPN Handling > Handling Unit Types**.
2.  To add or modify a handling unit type group from the **Groups** grid:
    1.  Above the grid, select **Groups**.
    2.  Perform one of the following tasks:
        -   To add a group, click **Add**.
        -   To modify a group, in the grid, click the handling unit group.
    3.  In the **Name** and **Description** fields, enter the values.
    4.  In the **Available** column, select the check box next to the handling unit types to add to the group.
    5.  Click **Save**.
3.  To add or modify a handling unit type group from the **Types** grid:
    1.  Above the grid, select **Types**.
    2.  In the grid, select the check box next to each handling unit type to add to the group.
    3.  To add the handling unit types to a new group:
        1.  From the **Actions** drop-down list, select **Create New Group**.
        2.  In the **Group Name** and **Description** fields, enter the values.
        3.  Click **Save**.
    4.  To add the handling unit types to an existing group:
        1.  From the **Actions** drop-down list, select **Add to Existing Group**.
        2.  From the **Group Name** drop-down list, select the group to which to add the handling unit types.
        3.  Click **Save**.

## Delete a handling unit type group

You cannot delete a group if there are handling unit types assigned to the group.

1.  Select **Configuration > Inventory > LPN Handling > Handling Unit Types**.
2.  Above the grid, select **Groups**.
3.  In the grid, select the group to delete.
4.  Click **Delete**. A confirmation message is displayed.
5.  Click **OK**.

## Handling Unit Type fields

 
| Field | Description |
| --- | --- |
| Name | Name of the handling unit type. A handling unit type represents a group of handling units that have the same characteristics, such as size and weight, as well as whether they are serialized, temporary, or considered a container. The application tracks the on-hand quantity of handling units by type. |
| Description | Description of the handling unit type. |
| Handling Unit Category | Category that identifies how the handling unit type is used. A handling unit type can belong to one of the following categories: Inventory, Transport Equipment, and Picking Container. For tracking to take place, the category to which the handling unit belongs must be enabled. See [Handling unit categories](../lpn-handling.md). |
| Voice Code | Code used to represent the handling unit type in facilities that use voice devices. When the voice operator is prompted for the handling unit type, the operator can speak the voice code to identify the handling unit type to the application. |
| Length | Length of the handling unit type. To change a measurement unit, click the unit next to the field, and select a different unit. |
| Width | Width of the handling unit type. To change a measurement unit, click the unit next to the field, and select a different unit. |
| Height | Height of the handling unit type. To change a measurement unit, click the unit next to the field, and select a different unit. |
| Level Units | Number of level units (width) that the handling unit type occupies when deposited to a location that is associated with a level type. The value you enter here must be considered in relation to other elements of level type configuration, such as the total level units defined for a level type, and how many handling units of this type can be stored on the level. For example, if a level can fit 5 handling units of this type and a level has 10 total level units, then the level unit value for this handling unit type is 2. See [Level units](../../warehouse/locations/level-types.md). |
| Handling Unit Weight | Weight of the handling unit type. If this is a type of handling unit that can contain inventory, this is the tare (empty) weight of the handling unit type. To change a measurement unit, click the unit next to the field, and select a different unit. |
| Volume | Maximum cubic volume of inventory that the handling unit type can hold. If the handling unit type will never contain inventory, then enter 0. To change a measurement unit, click the unit next to the field, and select a different unit. |
| Maximum Weight | Maximum weight of inventory that the handling unit type can hold. If the handling unit type will never contain inventory, then enter 0. To change a measurement unit, click the unit next to the field, and select a different unit.<br > **Note**: The application only considers the **Maximum Weight** during outbound processing (such as picking). The **Maximum Weight** is not used to regulate handling unit types during receiving or when adding inventory through an adjustment. |
| Serialized | If Yes, each handling unit of this type is tracked individually within the application by a unique identifier. A serialized handling unit does not have to be associated with a serial number, but that and other specific information about the handling unit (such as its model number and manufacturer) can be associated with the handling unit. All handling units in the Transport Equipment category are serialized.<br > If No, handling units of this type are not tracked as individuals. They are, however, still tracked collectively by handling unit type. |
| Temporary | If Yes, handling units of this type are deleted from the application once they leave the warehouse, when they are either shipped out (inventory handling units) or dispatched (transport equipment handling units). A serialized, temporary handling unit is deleted from the application and would need to be created as a new handling unit if it returns to the warehouse. Non-serialized, temporary handling units are not tracked after they leave the warehouse, so you can determine the on-hand quantity in the current warehouse, but not in the external locations to which these handling units were shipped.<br > If No, the handling unit is considered permanent and remains in the application after it leaves the warehouse, is tracked by location, and is recognized by the application when it returns. Non-serialized, permanent handling units are tracked after they leave the warehouse, so you can determine the on-hand quantity in the current warehouse as well as the on-hand quantity in the locations to which they were shipped or transferred. |
| Container | If Yes, handling units of this type are considered a container (such as a tote, barrel, or crate) that can contain inventory and that has edges that stand up around the inventory.<br > If No, handling units of this type are not considered a container. Non-container handling units never contain inventory (such as furniture or equipment) or, if they could contain inventory, are either flat or do not have sides that would encompass the contents.<br > The application calculates the volume of container handling units differently from non-container handling units. For container handling units, the application only considers the handling unit's volume (defined by the handling units type) when calculating whether the handling unit plus its inventory, if any, can fit into a particular storage location, since the inventory is contained inside the handling unit. For non-container handling units that contain inventory, the application considers the handling unit's size plus the size of its inventory to determine whether it can fit into a particular storage location.<br > Only available when the handling unit category is Inventory or Picking Container. |
| LPN Tracked | If Yes, then when the application prompts the operator to identify the handling unit type at the start of or during a picking work assignment, the operator is also required to scan or enter the identifier for the slot handling unit, even if the handling unit is not serialized. Select Yes if you want to enable slot LPN tracking for a non-serialized handling unit (such as a tote or container) that is used during picking work assignments.<br > If No, then when the application prompts the operator to identify the handling unit type at the start of or during a picking work assignment, the operator is not prompted to scan or enter a slot LPN for the handling unit unless the handling unit is serialized.<br > **Note**: This field does not affect whether the master handling unit (such as a trolley) identifier is required; the application prompts for the master handling unit ID regardless of this field. |
| Enabled for Work Assignments | If Yes, handling units of this type can be assigned to a picking work assignment. When the work assignment is executed, the application uses the assigned handling unit as the basis for the work assignment. When the work assignment is released, the operator is directed to pick up the handling unit, and pick to the handling unit. If cartonized picks are included in the list, then the application assigns a supported carton to the handling unit to contain the carton picks. If the handling unit contains slots, picking can be directed to slots on the handling unit.<br > **Note**: If a handling unit type is specified on the order line, the application uses that handling unit type and does not assign the picks for that order line to a work assignment that uses a different handling unit type.<br > If No, handling units of this type cannot be assigned to a picking work assignment.<br > Only available when the handling unit category is Inventory. |
| Maximum Cartons | Maximum number of cartons that can be added to a work assignment that is based on this handling unit type. If zero (0), then the handling unit type supports any number of cartons.<br > Only available when the handling unit type is enabled for work assignments. |
| Maximum Orders | Maximum number of orders that can be added to a work assignment that is based on this handling unit type. If blank, then the handling unit type supports any number of orders.<br > Only available when the handling unit type is enabled for work assignments. |
| Maximum Order Lines | Maximum number of order lines that can be added to a work assignment that is based on this handling unit type. If blank, then the handling unit type supports any number of order lines.<br > Only available when the handling unit type is enabled for work assignments. |
| Maximum Work Orders | Maximum number of work orders that can be added to a work assignment that is based on this handling unit type. If blank, then the handling unit type supports any number of work orders.<br > Only available when the handling unit type is enabled for work assignments. |
| Maximum Work Order Lines | Maximum number of work order lines that can be added to a work assignment that is based on this handling unit type. If blank, then the handling unit type supports any number of work order lines.<br > Only available when the handling unit type is enabled for work assignments. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
