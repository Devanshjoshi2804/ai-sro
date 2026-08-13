---
title: "Procedures for LPNs"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/procedures_for_lpns.htm"
source: "/content/procedures_for_lpns.htm"
toc_path:
  - "Warehouse Management"
  - "Shared functions"
  - "Inventory"
  - "Procedures for LPNs"
sections:
  - "Apply a hold to inventory"
  - "Release a hold from inventory"
  - "Move an LPN to a different shipment"
  - "Move inventory"
  - "Add inventory to a location or LPN"
  - "Adjust inventory"
  - "Remove inventory"
  - "Print compliant labels"
  - "Relabel an LPN"
  - "Reprint an LPN label"
  - "Modify serial number"
  - "Modify a customs consignment"
  - "Transfer client ownership of inventory"
  - "Unpick and return inventory"
  - "Change the status of the inventory"
  - "Inventory mass update"
  - "Modify inventory attributes"
  - "View LPNs"
  - "View detailed LPN information"
  - "View picked inventory"
  - "View shipped inventory"
  - "LPN procedures field listings"
  - "Unpick and Return fields"
  - "Add Inventory fields"
  - "Adjust Inventory fields"
  - "Remove Inventory fields"
  - "Modify Consignment fields"
  - "Modify Inventory Attributes fields"
  - "Component fields"
  - "LPN detail field listings"
  - "Inventory Basics fields"
  - "Inventory Attributes fields"
  - "Inventory Dates fields"
  - "Inventory Shipping fields"
  - "Inventory Receiving fields"
  - "Serialized Inventory fields"
  - "LPN Delivery fields"
images: []
source_sha1: 101b7a716b2d513aee9a6776191625d860ec6955
---
# Procedures for LPNs

You can perform these procedures using the Inventory page, which is accessible from the following modules: **Inventory**, **Outbound Planner**, **Picking**, **Production**, **Receiving**, or **Shipping**.

## Apply a hold to inventory

You can apply one or more holds to the same inventory. When you apply a hold to an item, all of the inventory for that item is held, regardless of the LPN on which the inventory is located. When you apply a hold to inventory on a specific LPN, only the inventory on that LPN is held.

You can also apply a hold to an item or inventory in a location by viewing the detailed information for a location or item (on the Summary tab). See [View detailed LPN information](#View_detailed_LPN_information) and [View detailed item information](procedures-for-items.md).

1.  Perform one of the following tasks:
    -   View the Inventory page, select **On-Site**, and then perform one of the following tasks:
        
        1.  Select one of the following modules: **Inventory**, **Outbound Planner**, **Picking**, **Production**, **Receiving**, or **Shipping**.
        2.  Select **Inventory**.
        
        -   To apply a hold to an item, select **Items**, and then in the grid, select the check box next to the item.
        -   To apply a hold to inventory on a specific LPN, select **LPNs**, and then in the grid, select the check box next to the LPN.
        -   To apply a hold to inventory in a specific location:
            1.  Select **Locations**.
            2.  In the grid, click the location. The location details are displayed.
            3.  Perform one of the following tasks:
                -   To apply a hold to an item in the location, select **Items**, and then in the grid, select the check box next to the item.
                -   To apply a hold to an LPN in the location, select **LPNs**, and then in the grid, select the check box next to the LPN.
    -   View a grid with a link for a location, click the location, and then select one of the following: **Items** or **LPNs**.
    -   View a grid with a link for an item, and then click the item.
2.  From the **Actions** drop-down list, select **Apply Hold**. The Apply Hold page is displayed with a list of existing hold definitions.
3.  To add a hold definition:
    1.  Click **Add Hold**.
    2.  Enter information in the [Holds fields](../../inventory/holds/procedures-for-holds.md).
    3.  If the **Apply to Inbound Inventory** field is set to Yes, then define the criteria for the inventory to which the hold will be automatically applied at the time of receipt:
        1.  Under **INBOUND PROCESSING**, click **Inventory Criteria**.
        2.  Enter information in the [Inbound Hold Criteria fields](../../inventory/holds/procedures-for-holds.md).
        3.  Click **Apply**.
    4.  Click **Save**.
4.  In the grid, select the hold to apply, and then click **Apply**. The Apply Hold window is displayed.
5.  Enter information in the following fields:
    
     
    | Field | Description |
    | --- | --- |
    | Change Inventory Status | Status to which the held inventory is changed. This field is only displayed if the **Inventory Status** field on the hold configuration is set to Yes. |
    | Change Only Certain Statuses | Indicates that the status for certain held inventory is to be changed based on its current status. If selected, then for each inventory status, in the **To Inventory Status** column, select the status to apply to the inventory. For example, you may only want to update the status for inventory that has an Available status, while keeping the remaining held inventory in its current status. This field is only displayed if the **Inventory Status** field on the hold configuration is set to Yes. |
    | Reason | Value that indicates why the hold is being applied. A reason is required whenever a hold is applied to inventory. |
    
6.  Click **OK**. A confirmation message is displayed.

**Note**: If the application was unable to apply the hold, then a list of the LPNs is displayed with the reason the hold could not be applied.

8.  Click **OK**.

## Release a hold from inventory

You can release a hold to remove the hold from the inventory.

1.  Perform one of the following tasks:
    -   View the Inventory page, select **On-Site**, and then perform one of the following tasks:
        
        1.  Select one of the following modules: **Inventory**, **Outbound Planner**, **Picking**, **Production**, **Receiving**, or **Shipping**.
        2.  Select **Inventory**.
        
        -   To release a hold from an item, select **Items**, and then in the grid, select the check box next to the item.
        -   To release a hold from inventory on a specific LPN, select **LPNs**, and then in the grid, select the check box next to the LPN.
        -   To release a hold from inventory in a specific location:
            1.  Select **Locations**.
            2.  In the grid, click the location. The location details are displayed.
            3.  Perform one of the following tasks:
                -   To release a hold to an item in the location, select **Items**, and then in the grid, select the check box next to the item.
                -   To release a hold to an LPN in the location, select **LPNs**, and then in the grid, select the check box next to the LPN.
    -   Select **Inventory > Holds**, and then perform the following tasks:
        1.  Select **Active Holds**.
        2.  Click a hold, and then select **LPNs**.
        3.  In the grid, select the check box next to the LPN, or click the LPN.
        
        **Note**: To release all inventory under an active hold, instead of selecting **LPNs**, select **Summary** and then from the **Actions** drop-down list, select **Release All Inventory**. The Release Hold page is displayed.
        
    -   View a grid with a link for a location, click the location, and then select one of the following: **Items** or **LPNs**.
    -   View a grid with a link for an item, and then click the item.
2.  From the **Actions** drop-down list, select **Release Hold**. The Release Hold page is displayed.
3.  Select the hold to release, and click **Apply**. The Release Hold window displays.
4.  Enter information in the following fields:
    
     
    | Field | Description |
    | --- | --- |
    | Change Inventory Status | Status to which the held inventory is changed. This field is only displayed if the **Inventory Status** field on the hold configuration is set to Yes. |
    | Change Only Certain Statuses | Indicates that the status for certain held inventory is to be changed based on its current status. If selected, then for each inventory status, in the **To Inventory Status** column, select the status to apply to the inventory. For example, you may only want to update the status for inventory that has an Available status, while keeping the remaining held inventory in its current status. This field is only displayed if the **Inventory Status** field on the hold configuration is set to Yes. |
    | Reason | Value that indicates why the hold is being applied. A reason is required whenever a hold is applied to inventory. |
    
5.  Click **OK**. A confirmation message is displayed.
6.  Click **OK**.

## Move an LPN to a different shipment

1.  [View picked inventory](#View_picked_inventory).
2.  In the grid, select the check box next to the LPN to move, or click the LPN.

**Note**: If you view picked inventory on the Inventory page, you must click the LPN to display the LPN detail view to perform this procedure.

1.  From the **Actions** drop-down list, select **Move LPNs to Different Shipment**. The Split Shipment window is displayed.
2.  Enter information in the following fields:
    
     
    | Field | Description |
    | --- | --- |
    | Assign Inventory to Load | Determines how the application processes the remaining inventory that is part of the shipment but has not been picked or is picked but not yet loaded.<br>-   • **Assign to an existing load with the same carrier**: Indicates that the remaining inventory is assigned to a load that is shipped with the same carrier. If you select this option, you also select the existing load from the drop-down list to which the inventory is assigned.
    <br>-   •
        
        **Leave as unassigned shipments**: Indicates that the remaining inventory is not assigned to a load, but is assigned a new shipment identifier.
        
        <br>
    <br>-   • **Create a new load**: Indicates that the remaining inventory is assigned to a new, application-generated load, and is assigned a new shipment identifier. |
    | Move Inventory | Staging lane to which you want to move the remaining inventory (and to which pending inventory for the shipment is also directed). If you do not select a new staging lane, the inventory remains in its original staging lane. |
    
3.  Click **Save**.

## Move inventory

In order to move inventory, you must first enable moves from source areas to destination areas in the inventory moves configuration. After specifying the source and destination areas in the configuration, you can move inventory.

**Note**: User-initiated inventory moves (application does not allocate location) are validated against the destination location's pallet stack height and weight capacity, if enabled. Application-initiated inventory moves (application allocates a location) are validated against the location's **Maximum Capacity** value, in addition to the pallet stack height and weight capacity, if enabled.

See [Configure inventory move settings](../../configuration/inventory/inventory-moves/inventory-move-settings.md).

1.  [View LPNs](#View_LPNs).
2.  In the grid, click the LPN. The LPN details are displayed.
3.  To move a sub-LPN, in the grid, select the check box next to the sub-LPN.
4.  From the **Actions** drop-down list, select **Move Inventor**y. The Move LPN window is displayed.
5.  Perform one of the following tasks:
    -   To move a partial inventory:
        1.  In the **Quantity** field, enter the quantity to move.
        2.  In the **Destination LPN** field, enter an LPN for the quantity that is being moved.
        3.  In the **Destination Location** field, enter a destination location for the inventory.
    -   To move the complete LPN, in the **Destination Location** field, enter a destination location for the inventory.
6.  Perform one of the following tasks:
    -   To update the location immediately, select **Move Immediately**.
    -   To create directed work for the move:
        1.  Select **Add to Work Queue**.
        2.  To round up the value (in case of a partial move) to the next highest value defined in the footprint configuration, select **Round Up**.
7.  From the **Move Reason** drop-down list, select a reason for the move.
8.  Click **Move**. A confirmation message is displayed.
9.  Click **OK**.

## Add inventory to a location or LPN

You can add inventory to a storage location or LPN, such as when inventory is found that has not been identified. When you add the inventory, you can define all the inventory attributes.

1.  Perform one of the following tasks:
    -   [View locations](procedures-for-locations.md).
    -   [View LPNs](#View_LPNs).
2.  In the grid, select the check box next to the location or LPN, or click the LPN.
3.  From the **Actions** drop-down list, select **Add Inventory**. The Add Inventory window is displayed.
4.  Enter information in the [Add Inventory fields](#Add_inventory_fields).
5.  Click **Next**.

**Note**: If serial number or catch quantity capturing is not required for the item, and if the item is tracked at the LPN level and you are receiving a quantity of 1, then the application processes the inventory. If you did not enter an LPN, an identifier is automatically generated.

7.  If the Number Capture window is displayed, perform the following tasks:
    1.  Under **Quantity**, perform one of the following tasks:
        -   To automatically generate the identifiers, click **Generate LPNs**.
        -   To enter a range of identifiers, click **Enter a range**, then enter a starting and ending value, and then press **Tab**.
        -   To enter individual identifiers, in the text box, enter the first identifier and then press **Enter**. Repeat this process until you have entered the required number of identifiers.
    2.  If the inventory is serialized and requires serial number capturing, then under **Serial Numbers**, enter a serial number for each LPN that requires it.
    
    **Note**: To enter a range of serial numbers, click **Enter Range**, then enter the range of numbers to apply to the inventory, and then press **Tab**.
    
    4.  If the inventory is catch tracked and requires a catch quantity, under **Catch Quantity**, enter a value for each LPN that requires it.
    5.  Click **Finish**.

## Adjust inventory

You can adjust inventory quantities at an LPN level, such as when inventory is damaged. When you adjust inventory, you cannot modify any of the item attributes except the quantity of the item, the reason code, references and Keep location in error after adjustment fields.

1.  [View LPNs](#View_LPNs).
2.  In the grid, select a check-box next to an LPN to adjust.
3.  From the **Actions** drop-down list, select **Adjust Inventory**.
4.  Enter information in the [Adjust Inventory fields](#Adjust_inventory_fields).
5.  Click **Finish**.

## Remove inventory

You can remove inventory quantities, such as when inventory is lost.

1.  [View LPNs](#View_LPNs).
2.  In the grid, select the check-box next to the LPN or click the LPN.
3.  From the **Actions** drop-down list, select **Remove Inventory**. The Remove Inventory window is displayed.
4.  Enter information in the [Remove Inventory fields](#Remove_Inventory_fields).
5.  Click **Save**.

## Print compliant labels

1.  Perform one of the following tasks:
    
    -   To print from the Print Compliant Labels page:
        1.  Select one of the following modules: **Inventory**, **Packing**, **Picking**, **Receiving**, or **Shipping**.
        2.  Select **Print Compliant Labels**.
    -   To print from the LPN grid view:
        1.  [View LPNs](#View_LPNs).
        2.  In the grid, select the check box next to the LPN, sub-LPN, or-detail-LPN; or click the LPN to display the LPN details.
        3.  From the **Actions** drop-down list, select **Print Compliant Labels**.
    
2.  Enter information in the following fields:
    
     
    | Field | Description |
    | --- | --- |
    | LPN or Location | Enter the inventory identifier, such as LPN or location. |
    | Exit Point | Point in the warehouse process at which the report or label has been configured to automatically print. A list of labels that match the compliance configurations is displayed.<br > **Note**: The exit point and label formats are configured when modifying a document type. For more information, see [Add or modify a document type](../../configuration/integration/reports-and-labels/document-types.md). |
    
3.  Select the check box for the required label formats.
    
4.  Select a printer at which the labels should be printed.
    
    **Note**: If a default printer is configured in [Label Formats](../../configuration/integration/reports-and-labels/label-formats.md), the configured printer is displayed in the **Printer** field.
    
5.  Enter the number of copies.
    
6.  Click **Print**. The print status is displayed.
    
7.  Click **OK**.
    

## Relabel an LPN

You relabel an LPN to associate a new inventory identifier to an LPN. You can relabel only one LPN at a time. The application checks the uniqueness of the new identifier entered.

1.  [View LPNs](#View_LPNs).
2.  In the grid, select the check box next to the LPN to relabel.
3.  From the **Actions** drop-down list, select **Relabel LPN**. The Relabel LPN window is displayed.
4.  In the **New LPN** field, enter an LPN.
5.  Click **Save**. A confirmation message is displayed.
6.  Click **OK**.

## Reprint an LPN label

1.  [View LPNs](#View_LPNs).
2.  In the grid, click the LPN. The LPN details are displayed.
3.  From the **Actions** drop-down list, select **Reprint Label**.
4.  Enter information in the following fields:
    
     
    | Field | Description |
    | --- | --- |
    | Label Format | Unique identifier for the label format. A label format is a specific instance of a label document type. |
    | Document Type | Unique identifier for the document type. A document type is the configuration for a type of report (such as a bill of lading) or type of label (such as for a pallet or storage location). |
    | Printer | Printer that will print the label. |
    | Locale | Identifier that determines the culture-specific attributes displayed or printed on the report or label. Culture-specific attributes include language, time and date formats, currency formats, and measurement unit system. |
    
5.  Under **Criteria**, enter information in the fields that are displayed based on the selected label format and document type.
6.  Click **Print**.
7.  Click **OK**.

## Modify serial number

You can change the serial number or range of serial numbers that are currently assigned to the inventory. When you change the serial number, you replace the serial number that was previously assigned. You can also add a serial number to inventory that requires a serial number to be captured.

One or more serial numbers can be assigned to the inventory at the following LPN levels: LPN, sub-LPN, and detail-LPN, depending on the serialization level and serialization types defined for the item.

1.  View the Inventory page.
    
    1.  Select one of the following modules: **Inventory**, **Outbound Planner**, **Picking**, **Production**, **Receiving**, or **Shipping**.
    2.  Select **Inventory**.
    
2.  Select **On-Site**, and then select **LPNs**.
3.  In the grid, select the check box next to the LPN, sub-LPN, or-detail-LPN; or click the LPN to display the LPN details.
4.  From the **Actions** drop-down list, select **Modify Serial Number**. The Modify Serial Numbers page is displayed showing the LPNs to which serial numbers have been assigned.
5.  In the **LPN** column, select the LPN that has the serial number you want to change.
6.  In the **Serial Numbers** column, enter the new serial number.
7.  Click **Save**. A confirmation message is displayed.
8.  Click **OK**.

## Modify a customs consignment

A customs consignment is a set of customs-related information that is associated with a specific receipt of bonded inventory. You can modify customs consignment information to rectify any incorrect details, but you cannot change the consignment status. This action is only available if the LPN is associated with a consignment, and the consignment is in a Pending status.

**Note**: Customs information is only available if customs functionality is enabled for the warehouse.

1.  [View LPNs](#View_LPNs).

**Note**: You can only modify a customs consignment for bonded inventory.

3.  In the grid, click an LPN. The LPN details are displayed.
4.  From the **Actions** drop-down list, select **Modify Consignment**. The Modify Consignment window is displayed.
5.  Enter information in the [Modify Consignment fields](#Modify_Consignment_fields).
6.  Click **Apply**.

## Transfer client ownership of inventory

1.  [View LPNs](#View_LPNs).
2.  In the grid, select the check-box next to the LPN; or click the LPN to display the LPN details.
3.  From the **Actions** drop-down list, select **Transfer Client Ownership**.
4.  To change the item that is assigned to the selected inventory, in the **Item** field, select the new item.

**Note**: If you are transferring to another item, and if that item contains multiple footprints, you must select the footprint for the item.

6.  To change the client that is assigned to the selected inventory, in the **Client** field, select the new client.
7.  To change the footprint that is assigned to the selected inventory, in the **Footprint** field, select the footprint.
8.  From the **Reason** drop-down list, select a reason for the change.
9.  To include additional information related to the change, in the **Comments** field, enter the information.
10.  Click **Save**. A confirmation message is displayed.
11.  Click **OK**.

## Unpick and return inventory

You can unpick or return inventory that has been picked. You can also perform this task on inventory that is not shippable. See [Manage inventory that is not shippable](../../shipping/shipping-issues/procedures-for-shipping-issues.md).

1.  [View picked inventory](#View_picked_inventory).
2.  In the grid, select the check box next to the LPN, or click the LPN.

**Note**: If you view picked inventory on the Inventory page, you must click the LPN to display the LPN detail view to perform this procedure.

4.  From the **Actions** drop-down list, select **Unpick/Return**. The Unpick/Return window is displayed.
5.  Enter information in the [Unpick and Return fields](#Unpick_and_return_fields).
6.  Click **Save**.

## Change the status of the inventory

1.  View the Inventory page.
    
    1.  Select one of the following modules: **Inventory**, **Outbound Planner**, **Picking**, **Production**, **Receiving**, or **Shipping**.
    2.  Select **Inventory**.
    
2.  Select **On-Site**, and then select **LPNs**.
3.  In the grid, select the check-box next to the LPNs to change.
4.  From the **Actions** drop-down list, select **Change Inventory Status.** The Change Inventory Status window is displayed.
5.  From the **Status** drop-down list, select the status to which you want to change the inventory status.
6.  From the **Reason** drop-down list, select the reason for changing the inventory status.
7.  Click **OK**. A confirmation message is displayed.
8.  Click **OK**.

## Inventory mass update

You use inventory mass update to modify inventory attributes of multiple LPNs at the same time.

You enter the selection criteria to find the inventory that you want to change, and then enter new values for selected attributes. If you change the manufacturing or expiration date of existing inventory associated with an aging profile, the application recalculates the dates and updates the inventory status. If you change the footprint of existing inventory, the application recalculates the current quantity, volume, and length values for the locations where the inventory resides.

1.  View the Inventory page.
    
    1.  Select one of the following modules: **Inventory**, **Outbound Planner**, **Picking**, **Production**, **Receiving**, or **Shipping**.
    2.  Select **Inventory**.
    
2.  Select **On-Site**, and then select the **Locations**, **Items**, or **LPNs** tab.
3.  From the **Actions** drop-down list, select **Inventory Mass Update**. The Inventory Mass Update page is displayed with all the LPNs.
4.  In the filter, enter search criteria to select the inventory to change.

**IMPORTANT**: Attribute updates are applied to all of the displayed inventory.

6.  Click **Update Attributes**. The Update Attributes window is displayed.
7.  From the **Reason** drop-down list, select the reason for modifying the inventory.
8.  To add more information, in the **Comment** field, enter the information.
9.  Enter information in the [Inventory Attributes fields](#Inventory_Attributes_fields).
10.  Click **Save**. A confirmation message is displayed.
11.  Click **Yes**.
12.  Click **Done**.

## Modify inventory attributes

You can modify the inventory attributes of an LPN by entering the selection criteria to find the inventory that you want to change, and then entering new values for selected attributes. If you change the manufacturing or expiration date of existing inventory associated with an aging profile, the application recalculates the dates and updates the inventory status. If you change the footprint of existing inventory, the application recalculates the current quantity, volume, and length values for the locations where the inventory resides.

1.  View the Inventory page.
    
    1.  Select one of the following modules: **Inventory**, **Outbound Planner**, **Picking**, **Production**, **Receiving**, or **Shipping**.
    2.  Select **Inventory**.
    
2.  Select **On-Site**, and then select the **Locations**, **Items**, or **LPNs** tab.
3.  From the **Actions** drop-down list, select **Modify Inventory Attributes**. The Modify Inventory Attributes window is displayed.
4.  Enter information in the [Modify Inventory Attributes fields](#Modify_Inventory_Attributes_fields).
    
5.  Click **Save**. The Modify Inventory Attributes window is displayed.
6.  From the **Reason** drop-down list, select the reason for modifying the inventory.
7.  To add more information, in the **Comment** field, enter the information.
8.  Click **OK**. A confirmation message is displayed.
9.  Click **OK**.

## View LPNs

1.  To view LPNs from the Inventory page:
    
    **Note**: The ability to export LPN data from the Inventory page is currently unavailable.
    
    1.  View the Inventory page.
        
        1.  Select one of the following modules: **Inventory**, **Outbound Planner**, **Picking**, **Production**, **Receiving**, or **Shipping**.
        2.  Select **Inventory**.
        
    2.  Perform one of the following tasks:
        -   To view LPNs that have not been shipped, select **On-Site**, and then select **LPNs**.
        
        **Note**: From the **On-Site** tab, you can also select **Locations,** and then click on a location and select **LPNs** to view the LPNs in a location.
        
        -   To view shipped LPNs, select **Shipped**.
        
        **Note**: You cannot perform actions on a shipped LPN.
        
2.  To view LPNs from the Staging page:
    1.  View the Staging page.
        
        1.  Select one of the following modules: **Receiving** or **Shipping**.
            
        2.  Select **Staging**.
            
        
    2.  Under **Lanes** or **Doors**, click the status bar associated with the LPNs. The display shows information related to the equipment, appointment, and inventory associated with the status bar or appointment bar.
    3.  From the **Actions** down-down list, select **View LPNs**.
3.  To view LPNs from the Door Activity page:
    1.  View the Door Activity page.
        
        1.  Select one of the following modules: **Receiving**, **Shipping**, or **Yard**.
            
        2.  Select **Door Activity**.
            
        
    2.  Under **Doors** or **Yard Locations**, click the status bar associated with the LPNs.
    3.  From the **Actions** drop-down list, select **View LPNs**.
4.  To view LPNs for a load:
    1.  [View loads](../../outbound-planner/outbound/procedures-for-loads.md), or view a grid with a link for a load.
    2.  In the grid, click the load, and then select **LPNs**.
5.  To view LPNs for an outbound order:
    1.  [View outbound orders](../../outbound-planner/outbound/procedures-for-orders.md), or view a grid with a link for an order.
    2.  In the grid, click the order, and then select **LPNs**.
6.  To view LPNs for an outbound shipment:
    1.  [View shipments](../../outbound-planner/outbound/procedures-for-shipments.md), or view a grid with a link for a shipment.
    2.  In the grid, click the shipment, and then select **LPNs**.
7.  To view LPNs received against an inbound shipment:
    1.  Select **Receiving > Inbound Shipments**.
    2.  In the grid, click the shipment, and then click **View LPNs**.
    3.  Select **All LPNs**.

## View detailed LPN information

In addition to the following tasks, you can access detailed LPN information from other application pages by clicking the LPN link in a grid view, where applicable.

1.  [View LPNs](#View_LPNs).
2.  In the grid, click an LPN. The LPN details are displayed.
3.  To view LPN details:
    
    -   Click **Basics** and view the [Inventory Basics fields](#Inventory_Basics_fields).
    -   Click **Attributes** and view the [Inventory Attributes fields](#Inventory_Attributes_fields).
    -   Click **Dates** and view the [Inventory Dates fields](#Inventory_Dates_fields).
    -   Click **Shipping** and view the [Inventory Shipping fields](#Inventory_Shipping_fields).
    -   Click **Receiving** and view the [Inventory Receiving fields](#Inventory_Receiving_fields).
    -   If the inventory is serialized, click **Serialized** and view the [Serialized Inventory fields](#Serialized_inventory_fields).

## View picked inventory

You can view picked inventory from the Inventory page by selecting the Quick Filter named "Picked". You also view picked inventory by viewing the details of an order, shipment, load, or wave.

1.  To view picked inventory from the Inventory page:
    1.  View the Inventory page.
        
        1.  Select one of the following modules: **Inventory**, **Outbound Planner**, **Picking**, **Production**, **Receiving**, or **Shipping**.
        2.  Select **Inventory**.
        
    2.  Select **On-Site > LPNs**.
    3.  Enter search criteria; or from the **Quick Filter** drop-down list, select **Picked**.
2.  To view picked inventory from the Staging page:
    1.  Select **Shipping** or **Receiving > Staging**.
    2.  Under **Lanes** or **Doors**, click the shipping status bar associated with the LPNs. The display shows information related to the equipment, appointment, and inventory associated with the status bar or appointment bar.
    3.  From the **Actions** down-down list, select **View LPNs**.
3.  To view picked inventory from the Door Activity page:
    1.  Select **Shipping** or **Receiving > Door Activity**.
    2.  Under **Doors**, click the shipping status bar associated with the LPNs.
    3.  From the **Actions** drop-down list, select **View LPNs**.
4.  To view picked inventory for an order:
    1.  Perform one of the following tasks:
        -   [View outbound orders](../../outbound-planner/outbound/procedures-for-orders.md).
        -   View a grid that displays a link for the order.
    2.  In the grid, click the order and then click **LPNs**.
5.  To view picked inventory for a shipment:
    1.  Perform one of the following tasks:
        -   [View shipments](../../outbound-planner/outbound/procedures-for-shipments.md).
        -   View a grid that displays a link for the shipment.
    2.  In the grid, click the shipment and then click **LPNs**.
6.  To view picked inventory for a load:
    1.  Perform one of the following tasks:
        -   [View loads](../../outbound-planner/outbound/procedures-for-loads.md).
        -   View a grid that displays a link for the load.
    2.  In the grid, click the load and then select **LPNs**.

## View shipped inventory

1.  View the Inventory page.
    
    1.  Select one of the following modules: **Inventory**, **Outbound Planner**, **Picking**, **Production**, **Receiving**, or **Shipping**.
    2.  Select **Inventory**.
    
2.  Select **Shipped**.
3.  In the filter, enter search criteria, such as an LPN, load, or order number.
4.  Perform one or more of the following tasks:
    
    -   Click **Basics** and view the [Inventory Basics fields](#Inventory_Basics_fields).
    -   Click **Attributes** and view the [Inventory Attributes fields](#Inventory_Attributes_fields).
    -   Click **Dates** and view the [Inventory Dates fields](#Inventory_Dates_fields).
    -   Click **Shipping** and view the [Inventory Shipping fields](#Inventory_Shipping_fields).
    -   Click **Receiving** and view the [Inventory Receiving fields](#Inventory_Receiving_fields).
    -   If the inventory is serialized, click **Serialized** and view the [Serialized Inventory fields](#Serialized_inventory_fields).

## LPN procedures field listings

### Unpick and Return fields

 
| Field | Description |
| --- | --- |
| Quantity | Quantity of the item to unpick from the LPN. To unpick the entire LPN, enter the full LPN quantity. |
| Weight | Total catch unit weight of the quantity of inventory that is adjusted. Catch unit measurements are variable weights or sizes of inventory that may exist within the same material handling (stock keeping) unit. Only displayed if the item is tracked by a catch unit type of weight. |
| LPN | Unique identifier for inventory. Typically, an LPN refers to a pallet; however, it can refer to inventory received at less than pallet quantity. The LPN is the license plate by which the inventory is tracked in the facility. |
| System Generated LPN | Indicates that the application generates an LPN for the unpicked inventory. If this check box is deselected, you must enter a value in the **LPN** field. |
| Print New Labels | Indicates that you want new LPN labels to be printed when you process the unpicked inventory. |
| Location | Unique name for a location within the facility that is used to receive, store, process, or ship inventory. |
| System Generated Location | Indicates that the application generates the location in which the unpicked inventory is to be moved. If this check box is deselected, you must define a location in the **Location** field. |
| On Hand | Quantity of the displayed item that is currently in storage. |
| Expected | Quantity of the item expected to be received into the warehouse. |
| Allocate | Indicates that the application will attempt to allocate inventory for the quantity that is being unpicked. |
| Ship Short | Indicates that the unpicked quantity is not reallocated and the shipment is to be shipped short. |

### Add Inventory fields

 
| Field | Description |
| --- | --- |
| LPN | Unique identifier for inventory. Typically, an LPN refers to a pallet; however, it can refer to inventory received at less than pallet quantity. The LPN is the license plate by which the inventory is tracked in the facility. |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Item Client | Name of the client who stores this item in the facility. This field is only displayed in a 3PL environment. |
| Description | Text that further describes the item. |
| Quantity | Quantity of inventory that you want to adjust. |
| Inventory Status | Value that defines the quality or disposition of the inventory. |
| Footprint | Name that identifies a footprint, which describes the packaging dimensions and units of measure for the item with which it is associated. |
| Lot | Identifier assigned to a quantity of inventory that is uniquely identified during the manufacturing process for the purpose of tracking an attribute of that inventory, such as its expiration date. Lots differentiate distinct groups of inventory that have the same item number. Lots are user defined and are not necessarily unique since the same lot can be applied to different items. However, lot and item combinations must be unique. |
| Handling Unit Type | Handling unit type assigned to the LPN. A handling unit type is a category that classifies a group of handling units (for example, pallets or totes) that share the same characteristics such as size and weight, as well as whether they are serialized, temporary, or considered a container. |
| Wrap | Indicates the LPN-level packaging attribute for inventory.<br > LPN packaging attributes are user-defined fields that are used to indicate requirements such as pallet wrapping, use of a slip sheet, and the application of labels on all four sides of a pallet of inventory. |
| Double Wrap | Indicates the LPN-level packaging attribute for inventory.<br > LPN packaging attributes are user-defined fields that are used to indicate requirements such as pallet wrapping, use of a slip sheet, and the application of labels on all four sides of a pallet of inventory. |
| Slip Sheet | Indicates the LPN-level packaging attribute for inventory.<br > LPN packaging attributes are user-defined fields that are used to indicate requirements such as pallet wrapping, use of a slip sheet, and the application of labels on all four sides of a pallet of inventory. |
| Label 4 Sides | Indicates the LPN-level packaging attribute for inventory.<br > LPN packaging attributes are user-defined fields that are used to indicate requirements such as pallet wrapping, use of a slip sheet, and the application of labels on all four sides of a pallet of inventory. |
| Reason Code | Code as defined in the web client that identifies the reason why you are adding inventory to a location. |
| Adjustment Reference One | Identifier for the host account to which the inventory adjustment was performed. This information was included when the inventory adjustment transaction was sent to the host. |
| Adjustment Reference Two | Identifier for the host account to which the inventory adjustment was performed. This information was included when the inventory adjustment transaction was sent to the host. |
| Keep location in Error after Adjustment | If Yes, then the location remains in an error status after the adjustment has been made. Select Yes if you want to prevent inventory activity from taking place in the location after the adjustment has been made.<br > If No, then after the adjustment is complete, the application removes the error status from the location.<br > **Note**: If inventory adjustment thresholds are defined and an adjustment exceeds a threshold, the location is set to Locked status until the adjustment is approved; this field has no effect on location status when an adjustment requires approval. |

### Adjust Inventory fields

 
| Field | Description |
| --- | --- |
| LPN | Unique identifier for inventory. Typically, an LPN refers to a pallet; however, it can refer to inventory received at less than pallet quantity. The LPN is the license plate by which the inventory is tracked in the facility. |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Item Client | Name of the client who stores this item in the facility. This field is only displayed in a 3PL environment. |
| Description | Text that further describes the item. |
| Quantity | Quantity of inventory that you want to adjust. |
| Inventory Status | Value that defines the quality or disposition of the inventory. |
| Footprint | Name that identifies a footprint, which describes the packaging dimensions and units of measure for the item with which it is associated. |
| Lot | Identifier assigned to a quantity of inventory that is uniquely identified during the manufacturing process for the purpose of tracking an attribute of that inventory, such as its expiration date. Lots differentiate distinct groups of inventory that have the same item number. Lots are user defined and are not necessarily unique since the same lot can be applied to different items. However, lot and item combinations must be unique. |
| Handling Unit Type | Handling unit type assigned to the LPN. A handling unit type is a category that classifies a group of handling units (for example, pallets or totes) that share the same characteristics such as size and weight, as well as whether they are serialized, temporary, or considered a container. |
| Wrap | Indicates the LPN-level packaging attribute for inventory.<br > LPN packaging attributes are user-defined fields that are used to indicate requirements such as pallet wrapping, use of a slip sheet, and the application of labels on all four sides of a pallet of inventory. |
| Double Wrap | Indicates the LPN-level packaging attribute for inventory.<br > LPN packaging attributes are user-defined fields that are used to indicate requirements such as pallet wrapping, use of a slip sheet, and the application of labels on all four sides of a pallet of inventory. |
| Label 4 Sides | Indicates the LPN-level packaging attribute for inventory.<br > LPN packaging attributes are user-defined fields that are used to indicate requirements such as pallet wrapping, use of a slip sheet, and the application of labels on all four sides of a pallet of inventory. |
| Slip Sheet | Indicates the LPN-level packaging attribute for inventory.<br > LPN packaging attributes are user-defined fields that are used to indicate requirements such as pallet wrapping, use of a slip sheet, and the application of labels on all four sides of a pallet of inventory. |
| Customs Type | Identifier that defines the type of customs tracking required for the inventory. |
| Commodity Code | Code that identifies a commodity. Commodities are categories created to group inventory that has the same qualities and specifications, regardless of their source. For example, wheat is a commodity. Commodity codes are standardized to provide carriers with a standard by which to determine pricing and to simplify the shipment process. The Commodity Code is usually printed on the bill of lading (BOL). If the commodity is printed on the BOL, all products of the same commodity are totaled. |
| Consignment ID | Unique identifier assigned to a receipt of bonded inventory. A customs consignment is an application-generated ID number that consists of a prefix (the warehouse ID) plus the next value in the customs consignment ID sequence. For example, if your warehouse ID is WMD1 and the next number in the sequence is 123456, then the customs consignment ID will be WMD1123456.<br > **Note**: You can configure the application to automatically populate the Customs Consignment ID field with a consignment number.<br > Only displayed if Customs functionality is enabled for the warehouse. Only available if the item is configured for customs tracking. |
| Customs Cost | Monetary amount that is paid to customs for the item. The amount is paid in the currency defined in the currency field. Only available if the **Customs Item Type** is either Customs or Excise. |
| VAT Code | Code for the value added tax (VAT) for the item. A customs VAT is charged on goods and some services that are imported from countries outside the European Unit (EU) and brought into the United Kingdom (UK) from other EU countries. It is also charged on most goods and services that VAT-registered businesses provide in the UK.<br>-   • **Standard**: The standard customs VAT rate is charged for this item.
<br>-   • **Zero**: No customs VAT is charged for this item. |
| Default Origin Code | Country in which the item was manufactured. This value is displayed by default on the planned inbound order line for the item but during receiving it can be changed. Only available if the value for **Customs Type** is either Customs or Excise. |
| Reason Code | Code as defined in the web client that identifies the reason why you are adding inventory to a location. |
| Adjustment Reference 1 | Identifier for the host account to which the adjustment should be charged. This information is included in the adjustment transaction that is sent to the host. |
| Adjustment Reference 2 | Identifier for the host account to which the adjustment should be charged. This information is included in the adjustment transaction that is sent to the host. |
| Keep location in Error after Adjustment | If Yes, then the location remains in an error status after the adjustment has been made. Select Yes if you want to prevent inventory activity from taking place in the location after the adjustment has been made.<br > If No, then after the adjustment is complete, the application removes the error status from the location.<br > **Note**: If inventory adjustment thresholds are defined and an adjustment exceeds a threshold, the location is set to Locked status until the adjustment is approved; this field has no effect on location status when an adjustment requires approval. |

### Remove Inventory fields

 
| Field | Description |
| --- | --- |
| Quantity to be Removed | Quantity of the item that you want to remove from the LPN. |
| Adjustment Reason | Reason that indicates why you are adjusting the inventory. |
| Adjustment References | Identifier for the host account to which the adjustment should be charged. This information is included in the adjustment transaction that is sent to the host. |
| Keep location in Error after Adjustment | If Yes, then the location remains in an error status after the adjustment has been made. Select Yes if you want to prevent inventory activity from taking place in the location after the adjustment has been made.<br > If No, then after the adjustment is complete, the application removes the error status from the location.<br > **Note**: If inventory adjustment thresholds are defined and an adjustment exceeds a threshold, the location is set to Locked status until the adjustment is approved; this field has no effect on location status when an adjustment requires approval. |

### Modify Consignment fields

 
| Field | Description |
| --- | --- |
| Consignment ID | Unique identifier assigned to a receipt of bonded inventory. A customs consignment is an application-generated ID number that consists of a prefix (the warehouse ID) plus the next value in the customs consignment ID sequence. For example, if your warehouse ID is WMD1 and the next number in the sequence is 123456, then the customs consignment ID will be WMD1123456.<br > Only displayed if Customs functionality is enabled for the warehouse and the item is configured for customs tracking. |
| Customs Receipt Type | Receipt type that is on the customs paperwork for the transport equipment. Only available if the consignment is not for a work order.<br>-   • **From EU States**: The order originated from another country in the European Union (EU), and the current warehouse is in the EU.
<br>-   • **From Importation**: The order originated from a country outside the EU, and the current warehouse is within the EU.
<br>-   • **Other Sources**: The order originated from a source not identified by other receipt types; for example, from an adjustment or production line.
<br>-   • **Other UK Warehouses**: The order originated from another warehouse in the United Kingdom.
<br>-   • **Gains in Store**: The order is for an adjustment in the quantity of existing inventory. |
| Customs Status | Status of the customs consignment:<br>-   • **Complete**: Receiving has been completed in Warehouse Management, and the consignment has been sent to a duty management application for processing.
<br>-   • **Duty Processed**: The consignment was successfully processed by a duty management application.
<br>-   • **Pending**: The consignment has not completed receiving in Warehouse Management and therefore has not been sent to a duty management application for processing. |
| Customs Entry Date | Date and time on which the planned inbound order entered customs. |
| CWC | Country Whence Consigned. Country from which the goods were initially dispatched to the importing country without any commercial transaction occurring in intermediate countries. |
| Supplier | Identifier for a supplier. A supplier can be an individual, organization, or another warehouse within your own organization from which you repeatedly receive inventory or handling units. |
| AAD Consignor's Excise Number | Value entered from Box 2 on the Accompanying Administrative Document (AAD), which is a five-part document set that must be used in the duty-suspended movement of excisable goods between member states of the European Union (EU). Only is displayed if the **Customs Receipt Type** value is From EU States. |
| AAD Reference Number | Value entered from Box 3 on the Accompanying Administrative Document (AAD), which is a five-part document set that must be used in the duty-suspended movement of excisable goods between member states of the European Union (EU). Only is displayed if the **Customs Receipt Type** value is From EU States. |
| UCR | A unique consignment reference (UCR) number is a collection of identifiers that helps create a unique end-to-end audit trail for bonded inventory from the order process through delivery. The UCR is specified for a customs consignment when the customs receipt type for the consignment is From Importation.<br > You can configure the application to require the UCR to be identified in the 16.3 UCR format during receiving. |
| Note Text | Additional status information or special instructions related to the consignment. |

### Modify Inventory Attributes fields

 
| Field | Description |
| --- | --- |
| Lot | Identifier assigned to a quantity of inventory that is uniquely identified during the manufacturing process for the purpose of tracking an attribute of that inventory, such as its expiration date. Lots differentiate distinct groups of inventory that have the same item number. Lots are user defined and are not necessarily unique since the same lot can be applied to different items. However, lot and item combinations must be unique. |
| Supplier Lot | Identifier that is an attribute of an item or item and lot combination and is assigned by the item's supplier. A supplier lot number used to uniquely identify and track the inventory to which it is assigned. The supplier lot number is a different attribute than the lot number, which is a manufacturer or production lot number. |
| Manufactured Date Time | Date and time on which the inventory identified on this LPN was manufactured. This date is the basis for date calculations (such as for aging and shelf life) that the application performs for date-tracked items. The date and time are stored in the database and displayed in the web client in the original captured time zone, not converted to a different time zone, such as a user preferred time zone. |
| Expiration Date Time | Date and time on which the inventory will expire. The expiration date is determined by the aging profile or shelf life assigned to the item configuration. The date and time are stored in the database and displayed in the web client in the original captured time zone, not converted to a different time zone, such as a user preferred time zone. |
| Revision Level | Identifier that is assigned to an item number to differentiate revisions of the same item number. |
| Country of Origin | Identifier assigned to an item to identify the item's country of origin. It is typically used for export paperwork. |
| Units per Case | Default number of items per packaging type. For example, for the Each/Case packaging type, it is the quantity of pieces or eaches of the item that is typically received in a single case. If a pallet of the item is received with a different quantity in the cases, the receiver can change the Each/Case value for that specific pallet. |
| Units Per Pack | Default number of items per packaging type. For example, for the Each/Inner Pack packaging type, it is the quantity of pieces or eaches of the item that is typically received in a single inner pack. If a pallet of the item is received with a different quantity in the inner packs, the receiver can change the Each/Inner Pack value for that specific pallet. |
| Footprint | Name that identifies a footprint, which describes the packaging dimensions and units of measure for the item with which it is associated. |
| Under Bond | If Yes, then the inventory is bonded. Bonded inventory is inventory for which customs duties and excise duties are required and have not yet been paid.<br > If No, then the inventory is not bonded. |
| Aging Profile | Name of the aging profile representing the aging process assigned to this item. An inventory aging profile is a configuration that defines a series of inventory statuses, each of which is associated with an age, such as 2 hours, 10 days, or 4 weeks. You assign an aging profile to a date-tracked item when you want the application to automatically update the inventory status of inventory for the item as it ages in the warehouse.<br > Included in the aging profile is the option to define an "Expired" status. The application uses the age of the "Expired" status to calculate the expiration date of an item that is tracked by its expiration date. An aging profile is required if the item is date-tracked by both manufactured date and expiration date. This field only available if the item requires this attribute.  |
| Use aging profile to determine status | If Yes, then the application automatically updates the inventory status of inventory for the item as it ages in the warehouse.<br > If No, then the application does not update the inventory status. |
| Use aging profile to determine Expiration Date | If Yes, then the application uses the aging profile to calculate the expiration date of an item that is tracked by its expiration date.<br > If No, then the application does not use the aging profile to calculate the expiration date of the item. |
| Handling Unit | Unique identifier for a handling unit that is tracked as an individual as well as collectively by handling unit type. You may want to track valuable handling units, such as CHEP pallets, as individuals. All transport equipment handling units are tracked as individuals. Handling units tracked as individuals can be further identified with a serial number. |
| Wrap | Indicates the LPN-level packaging attribute for inventory.<br > LPN packaging attributes are user-defined fields that are used to indicate requirements such as pallet wrapping, use of a slip sheet, and the application of labels on all four sides of a pallet of inventory. |
| Double Wrap | If Yes, this LPN-level packaging attribute is applied to the LPN. LPN packaging attributes are user-defined fields that are used to indicate requirements such as pallet wrapping, use of a slip sheet, and the application of labels on all four sides of a pallet of inventory. Select Yes to enable the use of this LPN packaging attribute.<br > If No, the attribute is not applied to the LPN. |
| Label 4 Sides | If Yes, this LPN-level packaging attribute is applied to the LPN. LPN packaging attributes are user-defined fields that are used to indicate requirements such as pallet wrapping, use of a slip sheet, and the application of labels on all four sides of a pallet of inventory. Select Yes to enable the use of this LPN packaging attribute.<br > If No, the attribute is not applied to the LPN. |
| Slip Sheet | If Yes, this LPN-level packaging attribute is applied to the LPN. LPN packaging attributes are user-defined fields that are used to indicate requirements such as pallet wrapping, use of a slip sheet, and the application of labels on all four sides of a pallet of inventory. Select Yes to enable the use of this LPN packaging attribute.<br > If No, the attribute is not applied to the LPN. |

### Component fields

 
| Field | Description |
| --- | --- |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Lot | Lot identifier of the component items consumed in an assembly work order. A lot is an identifier assigned to a quantity of product that is uniquely identified during the manufacturing process for the purpose of tracking an attribute of that product, such as expiration date. |
| Revision | Revision level of the component item consumed in an assembly work order. A revision level is a unique identifier that is assigned to an item to differentiate revisions of the same item. Revision levels are user defined. |
| Origin Code | Origin code of the component items consumed in an assembly work order. An origin code is a unique identifier that is assigned to an item to identify the item's place of origin. Typically used for export paperwork. Origin codes are user defined. |
| Component Key | Unique application-assigned identifier for a component item. |
| Sub-Component Key | Unique application-assigned identifier for a sub-component item. |
| Sub-LPN | Unique identifier for a case of inventory. |
| Detail LPN | Unique identifier for inventory at the unit or each unit of measure. |
| BOM Quantity | Quantity (in terms of material handling or stock keeping units) of the component item required to assemble one top-level item. This is the quantity of the component item that will be consumed when assembling the top-level item. If a BOM is defined for the top-level item, then this value can be populated by the BOM. |
| Supplier | Identifier for a supplier. A supplier can be an individual, organization, or another warehouse within your own organization from which you repeatedly receive inventory or handling units. |
| Customs Consignment | Unique identifier assigned to an assembly work order of bonded inventory. A customs consignment is an application-generated ID number that consists of a prefix (the warehouse ID) plus the next value in the customs consignment ID sequence. For example, if your warehouse ID is WMD1 and the next number in the sequence is 123456, then the customs consignment ID will be WMD1123456. |
| Rotation | Unique identifier that the application generates and automatically assigns to bonded inventory during receipt of that inventory into a bonded warehouse. The rotation ID is tracked with the inventory as long as the inventory is in the warehouse. |
| Supplier Lot | Supplier lot identifier to assign to component items. A supplier lot is a unique identifier that is assigned to a quantity of product during the manufacturing process that identifies the lot of the product as specified by the supplier. |
| Sequence | Unique number that identifies a set of components with the same attributes, such as lot. This value is used to differentiate mixed attribute components that are consumed to satisfy the work order detail. Sequence number 0 represents the component inventory requested by the original work order detail. Sequence numbers greater than 0 (such as 1, 2, or 3) represent the actual component inventory that was consumed to fill the work order detail.<br > For example, if 100 units of lot-tracked ItemA were requested; this value would have sequence number 0. If 75 units of ItemA Lot1 were consumed and 25 units of ItemA Lot2 were consumed, then they would have sequence number 1 and 2 respectively. The sequence number is automatically assigned when creating a work order detail or identifying component-tracked top-level items. However, the sequence number is manually assigned when adding or modifying consumed component inventory. Only available when adding consumed component inventory. |
| Inventory Status | Value that defines the quality or disposition of the inventory. |

## LPN detail field listings

### Inventory Basics fields

 
| Field | Description |
| --- | --- |
| LPN | Unique identifier for inventory. Typically, an LPN refers to a pallet; however, it can refer to inventory received at less than pallet quantity. The LPN is the license plate by which the inventory is tracked in the facility. |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Quantity | Quantity of inventory on the LPN. |
| Footprint | Name that identifies a footprint, which describes the packaging dimensions and units of measure for the item with which it is associated. |
| Inventory Status | Value that defines the quality or disposition of the inventory. |
| Client | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. |
| Location | Unique name for a location within the facility that is used to receive, store, process, or ship inventory. |

### Inventory Attributes fields

 
| Field | Description |
| --- | --- |
| LPN | Unique identifier for inventory. Typically, an LPN refers to a pallet; however, it can refer to inventory received at less than pallet quantity. The LPN is the license plate by which the inventory is tracked in the facility. |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Lot | Identifier assigned to a quantity of an item during the manufacturing process for the purpose of tracking an attribute of that item, such as an expiration date. Lots differentiate distinct groups of inventory with the same item number. Items that may require a lot number include pharmaceuticals, fabrics, food, and other products with limited shelf life. Lots are user defined and are not necessarily unique since the same lot number can be applied to different items. However, lot and item combinations must be unique. |
| Origin Code | Identifier assigned to an item to identify the item's country of origin. It is typically used for export paperwork. Origin codes are user defined. |
| Revision Level | Identifier that is assigned to an item number to differentiate revisions of the same item number. |
| Supplier | Identifier for a supplier. A supplier can be an individual, organization, or another warehouse within your own organization from which you repeatedly receive inventory or handling units. |
| Supplier Lot | Identifier that is an attribute of an item or item and lot combination and is assigned by the item's supplier. A supplier lot number used to uniquely identify and track the inventory to which it is assigned. The supplier lot number is a different attribute than the lot number, which is a manufacturer or production lot number. |
| Consignment Change Point | Value that determines when ownership of consigned inventory is transferred from the supplier to the warehouse. The consignment values defined for the supplier item override those defined for the supplier, which override those defined for the warehouse.<br>-   • **Consignment Days**: Ownership is transferred after the specified number of consignment days (defined in the **Consignment Days** field) have passed.
<br>-   • **Putaway**: Ownership is transferred when the putaway work for the inventory is complete.
<br>-   • **Receipt**: Ownership is transferred when the inventory is received by the warehouse.
<br>-   • **Transport Equipment Close**: Ownership is transferred when the outbound transport equipment on which the consigned inventory is loaded is closed.
<br>-   • **Transport Equipment Dispatch**: Ownership is transferred when the outbound transport equipment on which the consigned inventory is loaded is dispatched. |
| Consignment Days | Number of days after receiving consigned inventory that the ownership is transferred from the supplier to the warehouse. If **Consignment Days** is selected as the change point, then this value represents the number of days after receipt during which the supplier has ownership of the consigned inventory. A schedule-based job is configured to run daily to determine when the specified number of consignment days has passed, at which point ownership is transferred to the warehouse.<br > **Note**: The application sets the consignment end date for inventory on an ASN shipment based on when the inventory was received and put away to storage. For non-ASN shipments, the application sets the consignment end date based on when the inventory was identified. For example, if the Consignment Days value is 30, then when an ASN shipment is received, the consignment change point is 30 days from when the inventory is put away to storage; when a non-ASN shipment is received, the change point is 30 days from when the inventory is identified. |
| Remaining Consignment Days | Number of days remaining to transfer the ownership from the supplier to the warehouse, calculated based on the current date and the consignment end date. If **Consignment Days** is selected as the **Consignment Change Point**, then this value represents the number of days after receipt during which the supplier retains ownership of the consigned inventory. Only available if the change point is Consignment Days. |
| Consignment End Date | The date at which the ownership of the inventory is transferred from the supplier to the warehouse. Only available if the change point is Consignment Days. |
| Handling Unit | Unique identifier for a handling unit that is tracked as an individual as well as collectively by handling unit type. You may want to track valuable handling units, such as CHEP pallets, as individuals. All transport equipment handling units are tracked as individuals. Handling units tracked as individuals can be further identified with a serial number. |
| Rotation | Unique identifier that the application generates and automatically assigns to bonded inventory during receipt of that inventory into a bonded warehouse. The rotation ID is tracked with the inventory as long as the inventory is in the warehouse. |
| Under Bond | If Yes, then the inventory is bonded. Bonded inventory is inventory for which customs duties and excise duties are required and have not yet been paid.<br > If No, then the inventory is not bonded. |

### Inventory Dates fields

 
| Field | Description |
| --- | --- |
| LPN | Unique identifier for inventory. Typically, an LPN refers to a pallet; however, it can refer to inventory received at less than pallet quantity. The LPN is the license plate by which the inventory is tracked in the facility. |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Aging Profile | Name of the aging profile representing the aging process assigned to the inventory. An aging profile defines the status transitions that automatically occur over time as date-tracked inventory ages. The aging profile can also calculate the expiration date of inventory for this item when it is received (based on the expired status configured for the aging profile). |
| FIFO | Date used by the application for processing inventory when the first in, first out (FIFO) inventory rotation method is used. FIFO ensures that the oldest inventory is selected first. |
| Manufactured Date | Date on which the inventory identified on this LPN was manufactured. The date is stored in the database and displayed in the web client in the original captured time zone, not converted to a different time zone, such as a user preferred time zone. This date is the basis for date calculations (such as for aging and shelf life) that the application performs for date-tracked items. For example, this date can be used for first in, first out (FIFO) order processing. |
| Expire | Date on which the inventory will expire. The expiration date is determined by aging profile or shelf life assigned to the item configuration. The date is stored in the database and displayed in the web client in the original captured time zone, not converted to a different time zone, such as a user preferred time zone. |
| Received | Date on which the inventory was received into the warehouse. |

### Inventory Shipping fields

 
| Field | Description |
| --- | --- |
| LPN | Unique identifier for inventory. Typically, an LPN refers to a pallet; however, it can refer to inventory received at less than pallet quantity. The LPN is the license plate by which the inventory is tracked in the facility. |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Shipment | Unique identifier for an outbound shipment. A shipment is a group of orders or order lines that are allocated together and shipped to the same location. |
| Shipment Line | Unique name or code that identifies a shipment line. A shipment line is the section of a shipment that provides detailed information about an individual item being shipped. |
| Load | Unique identifier for a load. A load is one or more shipments grouped together into one or more stops that are shipped on a single piece of transport equipment. |
| Stop | Unique identifier for a stop. A stop is a collection of one or more outbound shipments making up a delivery to a single customer. |
| Order | Unique number that identifies an order. An order is a request for a supply of material or product. |
| Order Line | Unique number that identifies the order line. The number corresponds to the line's position on the order. The first order line is automatically assigned a line number of 0001. Additional order lines are then automatically numbered sequentially, beginning with 0002. |
| Pick Date | Date on which the inventory was picked. |
| User | User who picked the inventory. |
| Shipping Address | Address of the customer to which the inventory is being shipped. This field defaults to the address defined for customer. |
| Stop Address | Address of the stop at which the inventory is to be delivered. A stop is a collection of one or more outbound shipments making up a delivery to a single customer. |
| Distribution | Unique code that is used to identify a distribution. The distribution identifier can be application-generated or user-specified. A distribution is a pre-allocation of a warehouse planned inbound order to a store. |

### Inventory Receiving fields

 
| Field | Description |
| --- | --- |
| LPN | Unique identifier for inventory. Typically, an LPN refers to a pallet; however, it can refer to inventory received at less than pallet quantity. The LPN is the license plate by which the inventory is tracked in the facility. |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Inbound Shipment | Unique identifier used for inventory tracking for an inbound shipment of inventory. An inbound shipment is a group of orders that are transported to the warehouse together or received together. When inventory arrives at the warehouse on a piece of transport equipment, an inbound shipment represents the contents of the transport equipment; however, one or more inbound shipments can be associated with a piece of transport equipment. |
| Planned Inbound Order | Identifier for a planned inbound order that is associated with a specific supplier. A planned inbound order is an authorization to receive specific inventory and quantities from a supplier. It is used, but not required, to receive inventory into the warehouse. |
| Inbound Order | Identifier for an inbound order or planned inbound order that is associated with a specific supplier. |
| Inbound Order Line | Unique identifier for an inbound order line. The order line is the section of an order that provides detailed information about an individual item that the order requests. |

### Serialized Inventory fields

 
| Field | Description |
| --- | --- |
| LPN | Unique identifier for inventory. Typically, an LPN refers to a pallet; however, it can refer to inventory received at less than pallet quantity. The LPN is the license plate by which the inventory is tracked in the facility. |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Serial Number | Unique identifier that is used to identify a piece of inventory in the warehouse. The identifier may contain numbers, letters, and check digits as required by the serial number type, and may be captured for an LPN, sub-LPN or detail LPN of inventory. The point at which the serial number is captured is determined by the serialization type assigned to the item. |

### LPN Delivery fields

 
| Field | Description |
| --- | --- |
| LPN | Unique identifier for inventory. Typically, an LPN refers to a pallet; however, it can refer to inventory received at less than pallet quantity. The LPN is the license plate by which the inventory is tracked in the facility. |
| Delivery Date | Date on which the LPN was delivered to the customer. Delivery dates reflect the time zone used in the web client, which can be either the default system time zone or a user preferred time zone. |
| Reason | Value that represents the reason for the discrepancy between the quantity that was shipped to the customer and the quantity the customer reported as received. For LPN-tracked shipments, this is the reason that a full LPN was not confirmed as received by the customer; or if it was received, the reason can indicate the disposition of the LPN (such as damaged inventory). For example, reasons can include Damaged Part, Incorrect Receipt, Incorrect Pick, and Missing Item. The proof of delivery transaction from the host can include the discrepancy reason provided by the customer if it matches one of the reasons defined in the application.<br > **Note**: A list of standard reasons is distributed. Customers must use the reasons that are defined in the application. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2023 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
