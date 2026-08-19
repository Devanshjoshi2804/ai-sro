---
title: "Production Settings"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/production_settings.htm"
source: "/content/production_settings.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Production"
  - "Production Settings"
sections:
  - "Configure production settings"
  - "Production Settings fields"
images: []
source_sha1: 7175be6221036c6e89fc0e3387b80be876a6171b
---
# Production Settings

You can define how the application performs production (work order) processing. Specifically, you can define the following attributes and settings:

-   Default receipt type that is created when inventory is identified from a production line
-   Application actions that are performed at various points during allocation
-   Options for receiving unexpected items from and closing a disassembly work order
-   Storage zones for inventory that is received from a production line
-   Production areas, including the areas in which over-consumption and under-consumption are allowed
-   Production line processing, including reasons why a production line is unavailable
-   Areas to which the application automatically moves finished goods for an item family
-   Reasons for stopping a work order

## Configure production settings

1.  Select **Configuration > Outbound > Production > Production Settings**.
2.  Enter information in the [Production Settings fields](#Production_Settings_fields).
3.  To select the storage zones for inventory that is received from a production line:
    1.  Click **Storage Zones**.
    2.  In the **Available** column, select the check box next to the storage zones that apply.
    3.  Click **Apply**.
4.  To enable the use of Production Line Operations for a workstation:
    
    **Note**: The Production Line Operations window is accessed from the Supply Chain Execution (SCE) client.
    
    1.  Click **Production Areas**.
    2.  Perform one of the following tasks:
        -   To add a workstation, click **Add**.
        -   To modify a workstation, in the grid, click the workstation.
    3.  Enter information in the following fields:
        
         
        | Field | Description |
        | --- | --- |
        | Workstation | Workstation device that is used to access Production Line Operations. |
        | Area | Area in which the production lines are located. The workstation can be used to access Production Line Operations to view and manage production lines in the selected area. |
        | Supervisor | If Yes, then in Production Line Operations, the user can view processing areas other than the one to which the workstation is assigned.<br > If No, the user is able to view and manage only the production lines assigned to the selected area. |
        
    4.  Click **Apply**.
5.  To select the areas in which users can change reported consumed quantities for component items when closing a work order:
    
    **Note**: In the selected areas, the user is allowed to modify consumed component quantities for a work order detail to report over-consumption, under-consumption, return to stock, or scrapped inventory.
    
    1.  Click **Allow Over- and Under-Consumption**.
    2.  In the **Available** column, select the check box next to the production areas in which users are allowed modify component quantities when closing a work order.
    3.  Click **Apply**.
6.  To define the reasons that an operator can select to indicate why a production line is unavailable:
    1.  Click **Production Line Reasons**.
    2.  Perform one of the following tasks:
        -   To add a new reason, click **Add**.
        -   To modify an reason, in the grid, click the reason.
        -   To copy a reason, in the grid, select the check box next to the reason, and then click **Copy**.
    3.  Perform one of the following tasks:
        -   In the **Production Line Reason Code** field, enter a reason code.
        -   To have the application supply a reason code, select the **System Generated** check box.
    4.  In the **Production Line Reason** field, enter a description of the reason.
    5.  To assign the reason to clients:
        1.  Click **Clients**. The Clients page is displayed.
        2.  In the **Available** column, select the check next to the clients that use the reason.
        3.  Click **Apply**.
7.  To select the areas to which the application should automatically move finished goods for an item family after the inventory has been identified:
    1.  Under **AUTO MOVE**, click **Putaway Areas**.
    2.  Perform one of the following tasks:
        -   To add an item family, click **Add**.
        -   To modify an item family, in the grid, click the item family.
    3.  Enter information in the following fields:
        
        | Field | Description |
        | --- | --- |
        | Item Family | Identifier used to group similar items together. Typically, all of the items within a family have the same material handling characteristics. |
        | Area | Storage area to which finished goods that belong to an item family are automatically moved when those finished goods are identified |
        | Storage Location | Location in the selected area to which finished goods that belong to an item family are automatically moved when those finished goods are identified. |
        
    4.  Click **Apply**.
8.  To define the reasons that an operator can select to indicate why a work order was stopped:
    1.  Under **WORK ORDER REASONS**, click **Reasons**.
    2.  Perform one of the following tasks:
        -   To add a new reason, click **Add**.
        -   To modify an reason, in the grid, click the reason.
        -   To copy a reason, in the grid, select the check box next to the reason, and then click **Copy**.
    3.  Perform one of the following tasks:
        -   In the **Work Order Reason Code** field, enter a reason code.
        -   To have the application supply a reason code, select the **System Generated** check box.
    4.  In the **Reason** field, enter a description of the reason.
    5.  To assign the reason to clients:
        1.  Click **Clients**. The Clients page is displayed.
        2.  In the **Available** column, select the check next to the clients that use the reason.
        3.  Click **Apply**.
9.  Click **Save**.

## Production Settings fields

 
| Field | Description |
| --- | --- |
| Receipt Type | Default inbound order type that is created when inventory is identified from a production line. |
| Allocation Type | Type of allocation that is performed for a work order.<br>-   • **Order Picks**: Commit inventory, create pick work entries, and create shipment information. Replenishments are not created, even if inventory is missing.
<br>-   • **Order Picks and Replenishments**: Commit inventory, create pick work entries, and create any needed replenishments. This option is typically selected since top-level items cannot be created without all of the component items.
<br>-   • **Replenishments**: Creates any needed replenishments.
<br>-   • **Top-off Replenishment**: Creates any needed top-off replenishments. |
| Post-Release Action | Valid server command that is executed when picks are released from a hold status. This command runs after the PROCESS PICK RELEASE command. |
| Post-Deallocation Action | Valid server command that is executed when inventory that had been allocated for a work order is deallocated. This command is run after the DEALLOCATE WORK ORDER command. |
| Pre-Allocation Validation Action | Validation or processing server command, based on work order revision, client, and warehouse that is executed prior to allocation. Typically used to validate a work order configuration, this command is run before the CREATE WORK ORDER command. If validation is not successful, then allocation does not occur. |
| Post-Confirmation Action | Valid server command that is executed when picks that were allocated to a hold status are confirmed without being released. This command runs after the CONFIRM PICKS FOR WORK ORDERS command. |
| Post-Allocation Action | Valid server command that is executed when a work order is allocated. The command is run after the ALLOCATE WORK ORDER command. |
| Allow Unexpected Item | If Yes, then during disassembly, if an operator identifies a component item that does not belong to the disassembly work order, a message is displayed to the operator. The message allows the operator to select whether to continue identifying the component item and adding it to the disassembly work order.<br > If No, then if an operator identifies a component item that is not included on the disassembly work order, an error message is displayed and the operator is not allowed to identify the item as a component of the work order. |
| Allow Close When Expected Scrap Percentage Exceeded | If Yes, the application allows an operator to close a disassembly work order when the components exceed the expected scrap percentage defined for the work order. If set to Yes, then when an operator attempts to close a disassembly work order for which the component scraps exceed the expected percentage, a warning message is displayed and the operator can choose whether to close the work order or not.<br > If No, the application does not allow an operator to close a disassembly work order when the component scraps exceed the expected percentage defined for the work order. |
| Auto Create Work Order Setup | If Yes, the application automatically creates a work order setup when the component items of a work order are delivered to a production line or station. If set to Yes, the application uses the attribute values specified for the component items that are attribute-tracked and creates the work order setup. After the top-level item is identified, the attribute values are displayed when identifying the component items used to build the top-level item.<br > If No, then work order setups are not created automatically. |
| Default Supplier for Identified Inventory | Default supplier used for inventory that is identified from a production line. A supplier can be an individual, organization, or another warehouse within your own organization from which you repeatedly receive inventory or handling units. |
| Allocation Profile Progression | Identifier for a prioritized list of inventory statuses that defines which statuses can be shipped. This is the default allocation profile that is assigned to a work order line that is generated automatically. A work order line is generated automatically when an operator delivers inventory to a production line, and the inventory does not match the inventory defined on any existing work order line. |
| Allow Restricted Lot Status for Work Orders | If Yes, component inventory from restricted item lots can be allocated for work orders. The restricted status can indicate, for example, a safety issue within a specific lot or that the inventory requires testing or validation before it can be shipped to an end customer. When restricted component inventory is built into finished goods, if component tracking is not enabled, the application does not track the restricted inventory. For this reason, some facilities prevent restricted inventory from being used to fulfill a work order.<br > If No, component inventory from restricted item lots cannot be allocated for work orders. |
| Check Consumption Tolerance By LPN | If Yes, the application checks consumption tolerances by LPN. The consumption tolerance, defined for a work order line, represents the minimum and maximum percentage of a consumed quantity that is allowed for the component item in building finished goods. Select Yes if you want to evaluate consumption tolerance for each LPN that is identified.<br > If No, the application checks consumption tolerances by work order, after all of the LPNs for the work order have been identified. |
| Close Work Order Automatically When Complete | If Yes, the application automatically closes the work order after all of the component inventory is either consumed, returned to stock, or returned to the work in process supply area. If set to Yes, the application also closes a work order automatically when finished goods are identified and the work order quantity is fulfilled.<br > If No, the application does not automatically close the work order. |
| RF Production Receiving Against Item | If Yes, the **Item** field is displayed on the RF Production screen, which allows the operator to scan an item or alternate item to find the production line and work order from which to start receiving. If set to Yes, then if an operator scans an alternate item, such as a universal product code (UPC), the application attempts to match an in-progress work order with the item. If multiple items associated with the alternate item are expected for in-progress work orders, the operator is prompted to select the correct item to receive.<br > If No, the **Item** field is not displayed on the RF Productions screen. Instead, the operator starts receiving by entering a production line or work order. |
| Require Minimum Components for Processing | If Yes, an operator can start to identify finished goods before all of the component items or pending picks required to complete the work order have not been delivered to the production area. Select Yes if you allow LPNs to be identified prior to all of the required inventory arriving at the production line.<br > If No, the application does not allow operators to start identifying inventory from a production line until all of the required component items or pending picks are delivered to the production line. |
| Consume Unexpected Inventory | If Yes, then during the work order completion process, the user can add unexpected component inventory after finished goods have been identified. Select Yes if you want to allow the user to add a work order detail for component inventory that was not allocated for the work order but was consumed in building the work order's top-level item.<br > If No, the user is not allowed to add a work order detail for component inventory that was not allocated for the work order but was consumed in building the work order's top-level item. |
| Allow Cross Dock of Produced Inventory | If Yes, then when you create a new assembly or disassembly work order, the **Allow Cross Dock of Produced Inventory** field on the work order (assembly) or work order line (disassembly) is set to Yes by default. Therefore, the inventory produced from the work order or work order line can be cross docked. If the inventory can fulfill a cross dock, when it is identified, it is moved directly from production receiving to a cross dock location or a staging location to satisfy an outbound order.<br > If No, then when you create a new assembly or disassembly work order, the **Allow Cross Dock of Produced Inventory** field on the work order (assembly) or work order line (disassembly) is set to No by default. Therefore, the inventory produced from the work order or order line cannot be cross docked.<br > **Note**: You can override this configuration for an assembly work order or a disassembly work order line. |
| Lane Display | Amount of time that must elapse before information on the Production Line Operations window is refreshed. Production Line Operations displays the processing status of work orders that have been assigned to production lines. The information includes progress information for picks, replenishments, and cross docks. |
| Maximum Identical LPNs | Integer value representing the maximum number of identical LPNs (full pallets) that a user is allowed to identify at one time from a production line. Allowing a user to identify multiple pallets of the same item at one time reduces the amount of data entry required. The user is prompted to provide a different LPN for each pallet, but only has to enter the attribute values once for the set of identical LPNs received. |
| Minimum LPN Length | Minimum number of characters that the application accepts when an LPN is scanned or typed into an **LPN** field during the identification of inventory from a production line. If the entered value falls outside of the range (for example, if a larger bar code number is scanned into the **LPN** field), then the application does not accept that value. |
| Maximum LPN Length | Maximum number of characters that the application accepts when an LPN is scanned or typed into an **LPN** field during the identification of inventory from a production line. If the entered value falls outside of the range (for example, if a shorter bar code number is scanned into the **LPN** field), then the application does not accept that value. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
