---
title: "Warehouse Equipment Type"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/warehouse_equipment_type.htm"
source: "/content/warehouse_equipment_type.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Equipment"
  - "Equipment"
  - "Warehouse Equipment Type"
sections:
  - "Warehouse equipment LPN limits"
  - "Add or modify a warehouse equipment type"
  - "Add warehouse equipment"
  - "Delete a warehouse equipment type"
  - "Delete warehouse equipment"
  - "Warehouse Equipment Type fields"
images: []
source_sha1: 88152034200b954883106aeddeaf01fff633cd3d
---
# Warehouse Equipment Type

Warehouse equipment refers to the material handling vehicles that an operator uses to perform directed work and other warehouse operations. A warehouse equipment type defines the characteristics that apply to a group of warehouse equipment. When you add a warehouse equipment type, you define the following attributes:

-   Type of equipment (for example, fork truck, crane, or handheld terminal).
-   Voice code assigned to the equipment (if the facility uses voice terminals).
-   Whether to capture the identifier for a specific piece of warehouse equipment during the log in and equipment change processes. If capturing is enabled, you must add specific pieces of warehouse equipment for each equipment type you define. See [Add warehouse equipment](#Add_warehouse_equipment).
    
    You can configure and enable the Perform Equipment Safety Check (PERFORM-EQP-SAF-CHK) workflow to automatically lock the warehouse equipment (identified by its equipment ID) that fails a safety check. Locked warehouse equipment cannot be used until a supervisor manually unlocks the equipment in the web client using the Warehouse Equipment Operations page. See [Warehouse Equipment Workflows](../../work/warehouse-workflows/warehouse-equipment-workflows.md).
    
-   Number of LPNs that the warehouse equipment type can move at one time. See [Warehouse equipment LPN limits](#Warehouse_equipment_LPN_limits).
-   Location access groups used to prevent an operator from being directed to perform work in a location that is incompatible with the equipment being used to perform the work. See [Location Access Groups](location-access-groups.md).

## Warehouse equipment LPN limits

The warehouse equipment LPN limit is the maximum number of LPNs that can reside on warehouse equipment before the operator is instructed to deposit the LPNs. This value eliminates the need for the operator to indicate that the equipment is full. The application evaluates the warehouse equipment limits during the following operations: receiving, picking, staging, loading, inventory moves, and transfers.

When the operator picks up an LPN, if the limit is reached, the putaway or deposit screen is displayed, depending on the operation being performed. If the limit is not reached, the operator can continue to pick up another LPN. If the LPN limit is reached, the operator can choose to either deposit the LPNs, or override the limit and continue with the current operation. The override is not recorded as a transaction. The application determines the order in which LPNs are deposited; however, the operator can choose to deposit a different LPN if the application is configured to allow it.

If the operator overrides the warning and continues picking up LPNs, the application no longer warns the operator about being over the limit. However, after depositing the LPNs, the LPN limit is again enforced. If the operator is performing a work assignment, a warning is not displayed when a pick exceeds the limit, as long as the operator is picking for the same list.

During any of the pickup operations, if the LPN limit is not reached, the operator can still exit the pickup function. This could be done, for example, after identifying the last LPN or during a single-pallet operation.

**Note**: If the **Directed Multiple Work Assignments** field in the voice picking configuration is set to Yes, then when a voice operator is picking multiple directed work assignments, the LPN equipment limit instead represents the number of directed work assignments that the operator using the equipment can accept. For example, a value of 3 indicates that operators using the equipment can accept up to 3 directed work assignments. During multiple directed work assignment picking, the maximum number of LPNs is not enforced by the application; therefore, the operator is not prompted that the equipment is full or when to deposit LPNs.

## Add or modify a warehouse equipment type

1.  Select **Configuration > Equipment > Equipment > Warehouse Equipment Type**.
2.  Perform one of the following tasks:
    -   To add a new equipment type, click **Add**.
    -   To modify an equipment type, in the grid, click the equipment type.
    -   To copy an equipment type, in the grid, select the check box next to the equipment type, and then click **Copy**.
3.  Enter information in the [Warehouse Equipment Type fields](#Warehouse_equipment_type_fields).
4.  To assign location access groups to the equipment type:
    
    **Note**: If you assign a location access group, then the equipment type can be directed to perform work only in locations that have a matching location access group.
    
    1.  Under **LOCATION ACCESS**, click **Limit Equipment Access In Locations**.
    2.  In the **Available** column, select the check box next to the location access groups that apply.
    3.  Click **Apply**.
5.  To set limits for the equipment type by work zone or work area:
    1.  Under **EQUIPMENT LIMITS**, click **Equipment Limits by Work Zone or Work Area**.
    2.  Above the grid, select **Work Areas** or **Work Zones**.
    3.  In the grid, click the area or zone to configure.
    4.  In the **Available** column, select the check box next to the work area or work zone that applies.
    5.  For each selection, under **Equipment Type Limit**, enter the quantity of the equipment type allowed in the work area or zone at the same time.
        
        **Note**: When the equipment type limit is reached, the application stops offering directed work in the work area or zone to operators using the equipment type.
        
    6.  Click **Apply**.
6.  Click **Save**.

## Add warehouse equipment

You can add a piece of warehouse equipment (with a unique identifier) to any warehouse equipment type that is configured to capture warehouse equipment (**Capture Warehouse Equipment** field set to Yes). Newly added warehouse equipment has a status of Idle.

1.  Select **Configuration > Equipment > Equipment > Warehouse Equipment Type**.
2.  In the grid, click the value displayed in the **\# of Associated Warehouse Equipment** column for the equipment type for which you want to add warehouse equipment.
    

**Note**: If there is no value displayed for a warehouse equipment type, then the **Capture Warehouse Equipment** field is set to No for the equipment type, and you cannot add warehouse equipment for the type.

4.  Click **Add**.
5.  In the **Warehouse Equipment** field, enter an identifier for the warehouse equipment. This value is what an operator enters or speaks when logging in, changing warehouse equipment, or performing a vehicle safety check (if configured).
6.  Click **Save**. A confirmation message is displayed.
7.  Click **OK**.

## Delete a warehouse equipment type

1.  Select **Configuration > Equipment > Equipment > Warehouse Equipment Type.**
2.  In the grid, select the check box next to the equipment type to delete.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Delete warehouse equipment

You can only delete warehouse equipment that has a status of Idle.

1.  Select **Configuration > Equipment > Equipment > Warehouse Equipment Type**.
2.  In the grid, click the value displayed in the **\# of Associated Warehouse Equipment** column for the equipment type from which you want to delete warehouse equipment.
    
3.  In the grid, select the check box next to the warehouse equipment to delete.
    
4.  Click **Delete**. A confirmation message is displayed.
    
5.  Click **OK**.
    

## Warehouse Equipment Type fields

 
| Field | Description |
| --- | --- |
| Equipment | Identifier for the equipment or material handling unit used in warehouse operations. |
| Description | Text that further describes the warehouse equipment. |
| Voice Code | Code used to represent the warehouse equipment type in facilities that use voice terminals. When the voice terminal operator is prompted for the vehicle type, the operator can speak the voice code to identify the equipment type to the application. |
| Capture Warehouse Equipment | If Yes, then when an RF or voice operator selects the equipment type when logging in or changing equipment, and if the equipment type is associated to one or more defined equipment IDs, then the application requires the operator to enter the equipment identifier. After the operator enters the identifier, the system changes the equipment's status to Active and records the current user and login time, which can be viewed in the web client on the Warehouse Equipment Operations page.<br>
**Note**: If you set this field to Yes, it is required that the equipment type is associated with specific warehouse equipment (with unique IDs) defined in the application.

<br > If No, then operators are not required to enter an identifier for equipment of this type. |
| Use Work Area Associations | If Yes, then the system finds directed work (for an operator using this equipment type) based on work area associations. A work area association is a configuration that defines the sequence in which the system searches selected work areas to find directed work. With work area associations, the system considers the association between work areas (typically based on proximity) over work priority, while still following the absolute and delta priorities defined for the home and current work areas. Enable the use of work area associations if you want to reduce travel by limiting the work areas to which an operator is directed to perform work. See [Work Area Associations](../../work/work/work-area-associations.md).<br > If No, then work area associations are not considered when the system attempts to find work for an operator using this equipment. |
| LPN Equipment Limit | Maximum number of LPNs that can reside on a piece of equipment before an operator is prompted to deposit them. If a value is not entered, the application uses a value of "0", which indicates an unlimited number of LPNs. It also represents the number of directed pick work assignments that a voice operator can select to perform at the same time. See [Equipment LPN limits](#Warehouse_equipment_LPN_limits).<br > **Note**: If the **Directed Multiple Work Assignments** field in the voice picking configuration is set to Yes, then it is recommended that the LPN equipment limit is not unlimited; enter a value greater than 0 (zero). |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
