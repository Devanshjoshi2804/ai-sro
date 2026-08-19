---
title: "Inventory Move Settings"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/inventory_move_settings.htm"
source: "/content/inventory_move_settings.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inventory"
  - "Inventory Moves"
  - "Inventory Move Settings"
sections:
  - "Consolidation criteria"
  - "Movement restrictions and overrides"
  - "Configure inventory move settings"
  - "Inventory Move Settings fields"
images: []
source_sha1: bda602ebb93e1e5ba80f0494fa4b49cc208177b1
---
# Inventory Move Settings

You can define how the application processes inventory moves initiated from an RF, and from the operations window available at a workstation. Specifically, you can define the following information:

-   Consolidation criteria that defines the inventory attributes that must match for the application to consolidate inventory being moved or created with inventory in the destination (deposit) location
-   Movement restrictions that define the movement zones to and from which selected LPN levels are not allowed to be moved. You can also define exceptions to existing movement restrictions to allow movement between otherwise restricted zones.
-   The attributes and behavior for moving full or partial LPNs of inventory using an RF device. An inventory move is the process of moving inventory from one location or LPN to another location or LPN.
-   A partial move involves moving part of an LPN (such as several cases from a full pallet) to another location or LPN. You can configure individual movement zones to allow or prevent an RF operator from performing partial moves out of the zone.
-   The areas to and from which inventory moves can be performed using a workstation
-   The attributes and behavior of the Inventory Movement Operations window

**Note**: User-initiated inventory moves (application does not allocate location) are validated against the destination location's pallet stack height and weight capacity, if enabled. Application-initiated inventory moves (application allocates a location) are validated against the location's **Maximum Capacity** value, in addition to the pallet stack height and weight capacity, if enabled.

## Consolidation criteria

Consolidation criteria defines the inventory attributes that must match in order for inventory created in or moved to a storage location to be consolidated with the inventory already in the location. When inventory is consolidated the quantities are combined, so that the application displays a single LPN for the consolidated inventory.

Consolidation takes place if the following requirements are met:

-   Existing inventory is moved to a storage location or new inventory is created in a storage location.
-   The storage location is in a pick zone that is configured to require the operator to scan either or both of the following pick levels: **Sub-LPN Level** or **Detail LPN Level**.
    
    **IMPORTANT**: If the **LPN Level Picks** field on the pick zone is set to **LPN Level**, then automatic consolidation will not take place when inventory is moved to or created in the storage location.
    
-   The destination storage zone is configured with the following attributes:
    -   **Mixing Rules** field is set to **Single Item** or **Mixed** to allow picking.
    -   **Automatic LPN Consolidation** field is set to Yes.
-   The required attributes (defined by the consolidation criteria) match. For example, if a lot is required, then the lot of the inventory being deposited must have the same lot as the inventory in the deposit location.
    
    **Note**: If **Automatic LPN Consolidation** is set to Yes, then LPN-level consolidation happens regardless of whether the inventory satisfies the consolidation criteria defined in the inventory movement settings. However, sub-LPN and detail LPN consolidation only happens if the inventory satisfies the consolidation criteria.
    

## Movement restrictions and overrides

A movement restriction is used to restrict the movement of inventory between zones (physical or logical) using an RF device or an operations window at a workstation. A movement restriction override represents an exception to a movement restriction, and is defined to allow movement between otherwise restricted zones. For example, you can define a movement restriction to prevent moving inventory from a ship staging zone to any other zone. You can then define a movement restriction override to allow moving inventory from a ship staging zone to a movement zone used for problem shipments. You can define a movement restriction or movement restriction override for a logical zone, for example, to prevent operators from moving inventory from one RF device to another or from ship staging to an RF device.

You can define restrictions and overrides by source zone, destination zone, and LPN level. For the source and destination zones you can select a specific movement zone (physical or logical), or a value of Any Zone to indicate that it applies to all movement zones. For the LPN level, you can select a specific level (such as sub-LPN) or apply the restriction or override to all LPN levels (LPN, sub-LPN, and detail LPN).

## Configure inventory move settings

1.  Select **Configuration > Inventory > Inventory Moves > Inventory Move Settings**.
2.  Enter information in the [Inventory Move Settings fields](#Inventory_Move_Settings_fields).
3.  To select the attributes that must match for inventory created in or moved to a storage location to be consolidated with existing inventory in the location:
    1.  Under **GENERAL**, click **Inventory Consolidation Attributes**.
    2.  In the **Available** column, select the check box next to the attributes that apply.
    3.  Click **Apply**.
4.  To restrict the movement of inventory into and out of selected movement zones:
    
    **Note**: The defined movement restrictions and overrides take precedence over the zones defined for partial quantity moves and the areas defined for stock transfers.
    
    1.  Under **RESTRICTIONS**, click **Movement Restrictions**.
    2.  Perform one of the following tasks:
        -   To add a move restriction, select **Restriction**, and then click **Add.** A restriction is defined to prevent moves from taking place.
        -   To add an exception to a move restriction, select **Override**. and then click **Add**. An override is an exception to an existing move restriction; it is defined to allow moves to take place.
    3.  Enter information in the following fields:
        
         
        | Field | Description |
        | --- | --- |
        | Source Zone | For a restriction, this is the source zone from which moves to the destination zone are restricted (prevented). For an override, this is the source zone from which you allow moves to the destination zone. The source zone can be either physical or logical. |
        | Destination Zone | For a restriction, this is the destination to which moves from the source zone are restricted (prevented). For an override, this is the destination zone to which moves are allowed from the source zone. The destination zone can be either physical or logical. |
        | LPN Level | LPN level to which the restriction or override applies. Options include **All LPN Levels**, **LPN**, **Sub-LPN**, and **Detail LPN**. |
        
    4.  Click **Apply**.
    5.  To delete a restriction or override:
        1.  Select **Restriction** or **Override**.
        2.  In the grid, select the check box next to the row to delete.
        3.  Click **Delete**. A confirmation message is displayed.
        4.  Click **OK**.
5.  To select the movement zones in which you allow RF operators to move a partial quantity from an LPN:
    1.  Under **RF MOVE SETTINGS**, click **Allow Partial Quantity**.
        
        **Note**: The default movement zone is cleared when you select a new zone. The setting for the DEFAULT zone defines the setting for all available zones.
        
    2.  In the **Available** column, select the check box next to the zones that apply.
    3.  To allow partial moves, in the **Selected** column, set the **Allow Partial Quantity** field to **Yes**.
    4.  Click **Apply**.
6.  To restrict the areas that are available for selection when moving inventory at a workstation:
    1.  Under **STOCK TRANSFERS**, perform one or both of the following tasks:
        -   To define the areas in which transfers are allowed out of any location, click **Allow Moves From Source**. Only available when **Allow only specified Source Areas** is set to **Yes**.
        -   To define the areas in which transfers are allowed into any location, click **Allow Moves To Destination**. Only available when **Allow only specified Destination Areas** is set to **Yes**.
    2.  In the **Available** column, select the check box next to the areas.
    3.  Click **Apply**.
7.  Click **Save**.

## Inventory Move Settings fields

 
| Field | Description |
| --- | --- |
| Allow Destination Scan at Pickup | If Yes, the operator can specify a destination at the time inventory is picked up during an inventory move.<br > If No, the operator is not prompted to specify a destination at the time inventory is picked up; however, the inventory is moved onto the device and the user will have to deposit the inventory using the Deposit screen. |
| Print Labels | If Yes, the operator is required to print a label for the inventory being moved during an inventory move.<br > If No, the operator is not prompted to print a label during an inventory move. |
| Allow only specified Source Areas | If Yes, the **Allow Moves From Source** button becomes available so that you can define the valid source areas from which moves can be made using a workstation.<br > If No, no source areas will be available for selection when moving inventory. |
| Allow only specified Destination Areas | If Yes, the **Allow Moves To Destination** button becomes available so that you can define the valid destination areas to which moves can be made using a workstation. During the transfer operation, if the user selects a destination movement zone instead of a destination location, then the movement zone selection overrides the selected destination area settings.<br > If No, no destination areas will be available for selection when moving inventory. |
| Processing Source | Source location for processing the picks.<br>-   • **PICK-LOCATION**: Uses the picking location in which the picks are confirmed as the source location for processing.
<br>-   • **PROCESSING-STATION**: After picks are confirmed, moves the inventory to a processing station location, such as PACK-01 or CONS-02; then uses the processing station as the source location for pick processing. |
| Stay in Process Form | If Yes, after a pick has been processed in the Process Inventory Movement window, a prompt is displayed asking the user to enter the next work reference number on which they want to work.<br > If No, after a pick has been processed, the Inventory Movement Operations window is displayed. |
| Verify Nonpick Work | Command that determines the attributes that must be confirmed during processing to verify non-pick work.<br>-   • **BASED-ON-LODLLV**: Work is verified based on its LPN level. |
| Auto Button Press on Complete | If Yes, inventory movements are processed automatically upon completion of data entry on the Process Inventory Movement window.<br > If No, the user is required to click the Process button in order to process inventory movements. |
| Allow Entry of User ID | If Yes, the user is allowed to enter a user ID when performing an inventory transfer or confirming a pick using the Inventory Movement Operations window.<br > If No, the User ID field is not displayed on the window. |
| Process Only When Complete | If Yes, the application does not process the LPN until the entire pick work is complete. If the pick work is not complete, then on the Process Inventory Movement window, when the user clicks Process Inventory, a message is displayed stating that picks are not complete, and that the work listed in the work queue will not be completed.<br > If No, the application processes the LPN even though the pick work may not be complete. |
| Confirm Allows Transfer | If Yes, operators can enter a work reference for a previously processed pick.<br > If No, when a work reference is entered for a previously processed pick, a message is displayed stating that the application cannot find pick work for the work reference and that the work will be completed. |
| Lot Validation | If Yes, then for lot-tracked inventory, the application validates whether the lot number already exists. If the lot number does not exist in the application, then the application prevents the identification and creation of inventory (through receiving or an adjustment).<br > If No, then for lot-tracked inventory, the application does not prevent operators from identifying and creating inventory with a new lot number. |
| Highlight Textbox | If Yes, foreground and background colors are used on the Inventory Movement Processing window. You enable highlighting to help the user quickly determine which field is currently selected for data entry.<br > If No, highlighting is not used on the Inventory Movement Processing windows. |
| Audible Warning | If Yes, the user is warned with a sound when invalid data, such as an invalid LPN, is entered in any one of the fields on the Process Inventory Movement window.<br > If No, the user is not warned with a sound when invalid data is entered. |
| Pick Defaults Command | Command that returns the default settings for pick processing.<br>-   • **GET DEFAULTS FOR PICK**: Uses a work reference number and returns the default settings for that pick. |
| Error Command (Default) Parameter | Command that contains the value is required to execute the command in **Error Command for Default** field.<br>-   • **BASED-ON-REQNUM**: Executes the command when a work request number is entered.
<br>-   • **BASED-ON-WRKREF**: Executes the command when a work reference number is entered. |
| Error Command for Default | Command that is executed when the user clicks the Error button on the Inventory Movement Operations window. This command is used when the source location is not a storage location. For example, if the command is CANCEL WORK, then when the user clicks Error, a window is displayed that lets the user cancel the work. This command works in conjunction with the value in the **Error Command (Default) Parameter** field. |
| Reprint Command Parameter | Command that contains the value is required to execute the command in **Reprint Command** field.<br>-   • **BASED-ON-REQNUM**: Executes the command when a work request number is entered.
<br>-   • **BASED-ON-WRKREF**: Executes the command when a work reference number is entered. |
| Reprint Command | Command that is executed when the user clicks the Reprint button on the Inventory Movement Operations window. For example, if the command is PRODUCE MOVESHEET, a move sheet based on the selected parameter is generated. This command works in conjunction with the value in the **Reprint Command Parameter** field. |
| Error Command (Storage) Parameter | Command that contains the value is required to execute the command in **Error Command for Storage** field.<br>-   • **BASED-ON-REQNUM**: Executes the command when a work request number is entered.
<br>-   • **BASED-ON-WRKREF**: Executes the command when a work reference number is entered. |
| Error Command for Storage | Command that is executed when the user clicks the Error button on the Inventory Movement Operations window. This command is used when the source location is a storage location. For example, if the command is CANCEL WORK, then when the user clicks Error, a window is displayed that lets the user cancel the work. This command works in conjunction with the value in the **Error Command (Storage) Parameter** field. |
| Changeable Mode | If Yes, users can only enter an actual unit quantity.<br > If No, users can enter an actual unit quantity and select the round up option. |
| Round-Up | If Yes, the **Round Up** check box is selected on the Move Request Operations window.<br > If No, the **Round Up** check box is deselected on the Move Request Operations window.<br > The Round Up attribute determines whether the application rounds up the unit quantity that you select to move to the next higher unit of measure (UOM), if it is a partial UOM. For example, if Round Up is selected, a pallet quantity is 5 cases and you select to move 3 cases, then the application generates the work request for a full pallet (5 cases). If Round Up is not selected, then the work request is for 3 cases. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
