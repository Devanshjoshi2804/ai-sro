---
title: "Pick Confirmation"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/pick_confirmation.htm"
source: "/content/pick_confirmation.htm"
toc_path:
  - "Warehouse Management"
  - "Picking"
  - "Pick Confirmation"
sections:
  - "Paper-based picking process"
  - "Confirm picks"
  - "View pick confirmation history"
  - "Cancel picks"
  - "Pick Confirmation History fields"
images: []
source_sha1: 385eb2e023345785d6ad43c06b94d233fc06bf8a
---
# Pick Confirmation

You use the Pick Confirmation page to manually confirm released picks that are completed outside of the application, such as those that are completed using a paper-based picking process. You can confirm undirected and directed pick work, and you can cancel picks. The Active tab on the Pick Confirmation page displays picks that have not been confirmed, and the History tab displays picks that are confirmed.

**Note**: There are certain limitations to manual pick confirmation. See [Confirm picks](#Confirm_picks).

When you confirm a pick, the application updates the location of the picked inventory to the destination location or LPN, and then completes any additional processes (such as updating order line quantities or initiating workflows). When you first access the page, depending on how the application is configured, a prompt may be displayed that allows you to enter or scan a barcode (carton number, work assignment identifier, or work reference). See [Configure pick settings](../configuration/outbound/picking/pick-settings.md). If a prompt is not displayed, then you can either enter search criteria or select a quick filter to view pick information, or manually display the prompt to scan a barcode.

After you select the picks to be confirmed, either by scanning a barcode at the prompt or by using the **Actions** drop-down list on the Active tab, the Confirm Picks window is displayed. The Confirm Picks window is split into the following sections:

-   **Grid (left pane)**: Displays the picks that will be confirmed. When you select a grid row, the fields displayed in the right pane are updated to reflect the selected pick. For example, if a pick is for an item that is date-tracked, the ability to enter a manufactured or expiration date is available when the pick is selected in the grid. If there are blank fields in the right pane for a selected pick, the **Information Needed** tag is displayed in the grid row. However, the tag does not prevent you from confirming a pick, unless the missing information is needed by the application to logically move the correct inventory. The tag in the left pane is removed when all of the displayed fields for a pick have a value in the right pane.
    
    **Note**: If you filter out picks on the Confirm Picks window, they are still confirmed with the rest of the visible picks. To exclude a pick that was initially selected to be confirmed, you must remove it from the list (click **Remove**).
    
-   **Fields (right pane)**: Displays the fields that are relevant to the selected pick in the grid. The fields are dynamic and can change based on the selected pick and what the application requires to confirm it. Two fields, **Quantity** and **UOM**, are always displayed and required. Additional fields are displayed based on the attributes of the pick, the source location, and the destination location. For example, if a pick is for a case (sub-LPN), the **To LPN** field is displayed to specify the destination LPN to which the picked case is being deposited. However, if the pick is for a pallet, the **To LPN** field is not displayed because an entire pallet (LPN) is already being moved.
    
    The application attempts to confirm picks with as little information as possible. However, in addition to the UOM and quantity of the pick, more information may be required to process the pick. For example, assume a source location has multiple LPNs of a lot-tracked item, with each LPN containing a different lot. To confirm a case pick from this location, you must enter the quantity and UOM, and then enter either the lot number or the source LPN (**From LPN** field). Both values are not required because either one identifies the specific inventory, so the application knows which LPN to deduct the picked inventory from. Alternatively, if the source location contained LPNs with mixed lots, then the application would require both the LPN and the lot.
    
    **Note**: Since the information needed to confirm a pick is relative to the circumstances, there is no visual indication (such as an asterisk) of which fields are required beyond **UOM** and **Quantity**.
    

The Confirm Picks window supports capturing serial numbers (cradle to grave only) and catch quantity, and also allows you to enter multiple sub-LPNs or detail LPNs for picks that require it. Additionally, you can split a pick, which creates a new grid row, by entering a quantity that is less than the expected quantity. For example, assume that the lot number must be specified for a pick with a quantity of 50. If half the quantity is from Lot1 and half is from Lot2, then with the row for the pick selected, you can enter a quantity of 25, and a new line is automatically created with a quantity of 25. You can then specify a separate lot for each quantity in the pick.

When you manually confirm picks, certain outbound or background workflows may be initiated, depending on the exit point. In addition to the Pick Confirmation outbound workflow exit point, which only occurs when using the Pick Confirmation page, the following outbound workflow exit points also occur when you manually confirm picks on the Confirm Picks window: Pre-Pick, Post-Pick, and Carton Complete (which is also a background workflow exit point). See [Warehouse Workflows](../configuration/work/warehouse-workflows.md).

## Paper-based picking process

After a shipment is allocated, the inventory required to fulfill the outbound orders must be picked. Depending on the release rule configuration used by the application, either directed or undirected pick work is created during the pick release process and when a replenishment is requested.

For facilities that do not use RF devices or when a location is not accessible by RF devices, you can configure the pick method release rules to print pick labels or pick sheets to be used by operators performing the undirected pick work. The picks must then be confirmed at a workstation, using the Pick Confirmation page.

The following steps are typically performed to accomplish paper-based picking:

1.  Obtain the printed pick labels or pick sheets.
2.  Travel to the specified pick location and pick the inventory.
3.  To use pick labels, apply the labels to the picked inventory.
4.  Take the inventory to its destination location and deposit the inventory.
5.  At a workstation, confirm the pick work using the Pick Confirmation page.
6.  Process the pick work and perform any workflows, if prompted to do so.
    

## Confirm picks

Pick confirmation is used to manually confirm released picks for which a location is reserved in all of the defined movement zones for the path (**Reserve During Pick Release** field set to All.) See [Pick Methods](../configuration/outbound/picking/pick-methods.md).

During pick confirmation, the application verifies the pick zone for the confirmed picks, but does not verify the order details or the role of the user who confirmed the pick (which are only verified during RF picking). In addition, the application does not send any labor transactions or performance calculations for manually confirmed picks.

You cannot use this procedure to confirm threshold picks or slotted picks (to a trolley, for example). These types of picks are performed using RF picking.

1.  Select **Picking > Pick Confirmation**.
2.  If a barcode prompt is displayed, perform one of the following tasks: 
    -   Scan or enter a carton number, work assignment, or work reference. If necessary, click Process.
    -   Click **Cancel**. The grid is displayed.
3.  If the grid is displayed, perform one of the following tasks:
    -   To enter an identifier:
        1.  On the **Active** tab, above the grid, click **Enter Barcode**.
        2.  Scan or enter a carton number, work assignment, or work reference. If necessary, click Process.
    -   To search for released picks to confirm:
        1.  Enter search criteria or select a quick filter.
        2.  In the grid, select the check box for the picks to confirm.
        3.  From the **Actions** drop-down list, select **Confirm Picks**. The Confirm Picks window is displayed.
4.  To view information for a pick, in the left pane of the Confirm Picks window, select a pick. Information is displayed in the right pane.
5.  If the **Information Needed** tag is displayed for a pick, enter information in the required fields:
    -   **Quantity**: Pick quantity to confirm in the specified UOM.
    -   **UOM**: Unit of measure for the pick.
        
        **Note**: The application attempts to confirm picks with as little information as possible. However, in addition to the UOM and quantity of the pick, more information may be required to process the pick. Since the information needed to confirm a pick is relative to the circumstances of the pick and can change, there is no visual indication (such as an asterisk) of which fields are required beyond **UOM** and **Quantity**.
        
6.  To split a pick:
    
    **Note**: You can split a pick, which creates a new grid row, by entering a quantity that is less than the expected quantity. However, splitting a cartonized pick into a new carton is not supported. For example, assume that the lot number must be specified for a pick with a quantity of 50. If half the quantity is from Lot1 and half is from Lot2, then with the row for the pick selected, you can enter a quantity of 25, and a new line is automatically created with a quantity of 25. You can then specify a separate lot for the remaining quantity in the pick.
    
    1.  In the left pane, select the grid row for a pick, and then in the **Quantity** field, enter a value that is less than the expected pick quantity.
    2.  Select the new row and enter the required information.
7.  To overpick a replenishment (confirm a quantity greater than the replenishment quantity): 
    
    **Note**: You cannot overpick an order pick using manual confirmation.
    
    1.  In the left pane, select the grid row for the replenishment to overpick, and then in the **Quantity** field, enter the UOM quantity for the overage (not including the expected quantity). The application automatically creates a new line with a quantity equal to the remaining quantity minus the quantity entered on the first pick line; adjust the quantity as necessary.
        
        **Note**: If the overage quantity is equal to the expected quantity, then enter a quantity less than expected to create a new pick line first, and then adjust the quantities.
        
    2.  Select the new pick row and enter the quantity. Since the overage quantity is being confirmed on the original line, the quantity of the new line would typically match the original remaining (expected) quantity.
8.  To remove a pick from being confirmed, select the row for the pick, and then click **Remove**.
    
    **Note**: Removing a pick does not cancel or delete the pick, it only removes it from the list of picks to be confirmed; the removed pick remains in a Released status.
    
9.  If additional information is needed, click **Additional Information** and perform the following tasks:
    1.  If the inventory is serialized and requires serial number capturing, then under **Serial Numbers**, enter a serial number for each LPN that requires it.
        
        **Note**: To enter a range of serial numbers, click **Enter Range**, then enter the range of numbers to apply to the inventory, and then press **Tab**.
        
    2.  If the inventory is catch tracked and requires a catch quantity, under **Catch Quantity**, enter a value for each LPN that requires it.
    3.  Perform one of the following tasks:
        -   To confirm the additional information, click **Confirm**. The Confirm Picks window is displayed.
        -   To discard the additional information, click **Back**. The Confirm Picks window is displayed.
10.  Click **Confirm Picks**.
     
     **Note**: A message is displayed that indicates whether any of the picks failed confirmation. If any picks could not be confirmed, the Confirm Picks window is displayed and only the failed picks are listed.
     
11.  To resolve pick confirmation errors: 
     1.  Select the grid row for a failed pick, and then view the error message displayed in the right pane.
     2.  Resolve the error messages and then click **Confirm Picks**.

## View pick confirmation history

1.  Select **Picking > Pick Confirmation**.
2.  If a prompt is displayed, click **Cancel**.
3.  Select **History**.
4.  Enter search criteria or select a quick filter.
5.  View information in the [Pick Confirmation History fields](#Pick_confirmation_history_fields).

## Cancel picks

1.  Perform one of the following tasks:
    -   Select **Picking > Pick Confirmation**. If a prompt is displayed, click **Cancel**.
    -   [View picks](../shared-functions/waves-and-picks/procedures-for-picks-and-work-assignments.md).
2.  In the grid, select the check box next to the pick work to cancel.
3.  From the **Actions** drop-down list, select **Cancel Picks**. The Cancel Picks window is displayed.
4.  From the **Select Cancel Code** drop-down list, select a reason for cancelling the pick.
5.  To place the pick location in error, select the **Put locations in Error Status** check box. No picking or putaway can be performed in a location that is in error until the location is reset.
6.  Click **OK**.

## Pick Confirmation History fields

 
| Field | Description |
| --- | --- |
| Pick Status | Current status of the pick.<br>-   • **Pending**: Pick work inventory is reserved for allocation until automatically released by the application.
<br>-   • **Hold**: Pick work inventory is reserved for allocation until manually released by a user.
<br>-   • **Released**: Pick work is released to the work queue.
<br>-   • **Complete**: Pick work is complete.
<br>-   • **Un-Assigned**: Pick work is unassigned from a work assignment.
<br>-   • **Ready For List**: Pick work has been released and the pick is qualified for a work assignment. A background process builds these picks into either a handling unit-based or regular work assignment.
<br>-   • **Error**: Pre-manifesting the package for the pick work failed. The application allows packages to be pre-manifested; that is, manifested to hold. These packages are typically manifested during allocation (before the inventory is picked) and usually so that a label can be printed in advance for the package. You can view the specific error code and description on the Waves and Picks page. See [Waves and Picks](../shared-functions/waves-and-picks.md). |
| Source | Location where the work originated, such as the location from which inventory is picked, at which a count is performed, or from which transport equipment is moved. |
| Destination | Location where the work is completed, such as the location to which inventory is delivered or to which transport equipment is moved. |
| Load | Unique identifier for a load. A load is one or more shipments grouped together into one or more stops that are shipped on a single piece of transport equipment. |
| Shipment | Unique identifier for an outbound shipment. A shipment is a group of orders or order lines that are allocated together and shipped to the same location. |
| Order | Unique number that identifies an order. An order is a request for a supply of material or product. |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Description | Description of the item involved in the pick that further describes the inventory. |
| Pick Quantity | Quantity (in terms of material handling or stock keeping units) of the item that should be picked based on the order, work order, or replenishment. |
| Picked Quantity | Quantity (in terms of material handling or stock keeping units) of inventory that is picked based on the order, work order, or replenishment. |
| Pick UOM | Unit of measure in which the **Pick Quantity** is displayed. |
| Work ID | Unique application-assigned identifier for a piece of work in the work queue. |
| Work Status | Current status of the work.<br>-   • **Undirected**: The work is undirected; this means that a user can perform it from a workstation, or an RF operator can perform it using an undirected work menu option. Undirected work is not available to be performed through the RF Directed Work menu option.
<br>-   • **Pending**: The directed work has been allocated and released to the queue. Work in this status will be offered to an operator through the RF Directed Work function, based on permissions, priority, and proximity.
<br>-   • **Waiting**: The directed work is assigned to an operator, but the operator has not acknowledged it yet.
<br>-   • **Acknowledged**: The directed work has been acknowledged (accepted) by an operator.
<br>-   • **Suspended**: The directed work is temporarily suspended, indicating that the application will not offer it an operator through the RF Directed Work function.
<br>-   • **Locked**: The directed work is locked and is not released until the application finds an available pickface location. This status is used with the demand replenishment operation (PIARPL) to prevent work from being released until there is room in the location for the replenishment inventory. |
| Work Order | Identifier for a work order. A work order is an internal order used to find, allocate, and deliver product to a work-in-process area for assembly or disassembly, conversion, kitting, or repackaging. |
| Work Order Line | Unique identifier for a work order line. The number corresponds to the order line's position in the work order. |
| Order Line | Unique number that identifies the order line. The number corresponds to the line's position on the order. The first order line is automatically assigned a line number of 0001. Additional order lines are then automatically numbered sequentially, beginning with 0002. |
| Lot Tracked | Indicates whether the item is lot tracked (**Lot Tracking** field set to Yes in the item configuration). A lot is a batch (quantity) of an item uniquely identified by a lot number during the manufacturing process for the purpose of tracking that batch of inventory. |
| Origin Tracked | Indicates whether the item is tracked by its origin (**Origin Code** field set to Yes in the item configuration). The origin code is typically an identifier for the country or area of the world in which the item was manufactured. |
| Revision Tracked | Indicates whether the item is revision tracked (**Revision** field set to Yes in the item configuration). A revision may be used to identify a specific manufactured version of the item, so that when the item is modified or improved, the manufacturer may assign a new version number to reflect the change. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
