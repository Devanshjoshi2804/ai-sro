---
title: "Procedures for work orders"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/procedures_for_work_orders.htm"
source: "/content/procedures_for_work_orders.htm"
toc_path:
  - "Warehouse Management"
  - "Production"
  - "Work Orders"
  - "Procedures for work orders"
sections:
  - "View work orders"
  - "View detailed work order information"
  - "Add or modify a work order"
  - "Delete a work order"
  - "Delete a work order line"
  - "Copy a work order"
  - "Allocate inventory for a work order"
  - "Deallocate inventory from a work order"
  - "Start or stop a work order"
  - "Move a work order to a different production line or staging location"
  - "Release picks for a work order"
  - "Request additional inventory for an assembly work order"
  - "Cancel a replenishment for a work order"
  - "Request an additional quantity of finished goods for a disassembly work order"
  - "Confirm picks for a work order"
  - "Cancel picks for a work order"
  - "Cancel cross docking for a work order"
  - "Unpick inventory"
  - "Receive or putaway a top-level or component item"
  - "Return to stock"
  - "Close a work order"
  - "Work order field listings"
  - "Work Order fields"
  - "Work Order detail fields"
  - "Movement Work Orders fields"
  - "Allocate Work Order fields"
  - "Copy Work Order fields"
  - "Return to Stock or Receive fields"
  - "Complete Work Order Page fields"
  - "Work Order details: Summary fields"
  - "Work Order details: Order Lines fields"
  - "Work Order details: Picks fields"
  - "Work Order details: Shorts fields"
  - "Work Order details: Pending Replenishment fields"
  - "Work Order details: Cross Dock fields"
  - "Work Order details: Waiting Orders fields"
  - "Work Order details: Picked and Produced field listings"
  - "Work order field listings"
  - "Work order line field listings"
images: []
source_sha1: e116c6158bf30d4daa8d91988be2c14e74154a8b
---
# Procedures for work orders

You can perform the following procedures on work orders.

## View work orders

Perform one of the following tasks:

-   Select **Production > Production Lines**, and then click a production line. The production line details and the assigned work orders are displayed.
-   Select **Production > Work Orders**.

## View detailed work order information

1.  Perform one of the following tasks:
    -   Select **Production > Production Lines**, then expand or click a production line, and then in the grid, click a work order.
    -   Select **Production > Work Orders**, and then in the grid, click a work order.
2.  View information in the [Work Order detail fields](#Work_order_detail_fields).
3.  To view general information about the work order, select **Summary**, and view information in the [Summary fields](#Work_order_details:_Summary_fields).
4.  To view the component level details, select **Order Lines**, and view information in the [Order Lines fields](#Work_order_details:_Order_lines_fields).
5.  To view pick work for the work order, select **Picks**, and view information in the [Picks fields](#Work_order_details:_Picks_fields).
6.  To view work order lines that were generated short, select **Shorts,** and view information in the [Shorts fields](#Work_Order_details:_Shorts_fields).
7.  To view replenishment pick work for the work order, select **Pending Replens**, and view information in the [Pending Replenishment fields](#Work_order_details:_Pending_replenishment_fields).
8.  To view cross docking work for the work order, select **Cross Dock**, and view information in the [Cross Dock fields](#Work_order_details:_Cross_Dock_fields).
9.  To view completed pick work, select **Picked**, and view information in the Picked and Produced fields. See [Picked and Produced field listings](#Work_order_details:_Picked_and_Produced_field_listings). Click an LPN to view the LPN details. See [View detailed LPN information](../../shared-functions/inventory/procedures-for-lpns.md).
10.  To view the finished items in the production line, select **Produced**, and view information in the Picked and Produced fields. See [Picked and Produced field listings](#Work_order_details:_Picked_and_Produced_field_listings). Click an LPN to view the LPN details. See [View detailed LPN information](../../shared-functions/inventory/procedures-for-lpns.md).
11.  To view shipments and orders that are to be fulfilled with the work order's top-level item or component items, select **Waiting Orders**, and view information in the [Waiting Orders fields](#Work_Order_details:_Waiting_Orders_fields).

## Add or modify a work order

Use this procedure to add or modify a work order and its work order lines. The top-level item and all of the component items specified in a work order must already be defined in the application.

1.  Select **Production > Work Orders**.
2.  Perform one of the following tasks:
    -   To add a work order:
        1.  From the **Actions** drop-down list, select **Add**. The Add Work Order window is displayed.
        2.  From the drop-down list, select the type of work order to add.
        3.  Click **OK**. The Add Assembly Work Order or Disassembly Work Order window is displayed.
            
            **Note**: You can configure the work order types available for selection. See [Add or modify a work order type](../../configuration/production/work-order-types.md).
            
    -   To modify a work order, in the grid select the check box next to the work order, and from the **Actions** drop-down list, select **Modify**. The Modify Work Order window is displayed.
3.  Enter information in the work order fields. See [Work order field listings](#Work_order_field_listings).
    
    **Note**: Some fields are available only for assembly or only for disassembly work orders.
    
4.  If you are maintaining a disassembly work order, then to define the criteria that is used to allocate inventory for the work order:
    
    **Note**: For more information, see [Allocation Rules](../../configuration/outbound/allocation/allocation-rules.md).
    
    1.  In the left pane, click **Allocation Rules**, and under **Criteria Definition**, click **Expression**.
    2.  Select a column (attribute) to use, such as **Lot Number**.
    3.  Select the qualifier to use, such as "=".
    4.  Enter the attribute to use, such as **LOT1234** (based on the qualifier, the lot number that must be allocated for the order line).
    5.  To add additional rows of criteria:
        1.  Select the mathematical argument used to evaluate multiple rows of criteria.
            -   **Or**: Must match either group of the defined criteria.
            -   **And**: Must match both groups of the defined criteria.
            -   **(**: Opening argument used to group criteria together.
            -   **)**: Closing argument used to group criteria together.
                
                **Note**: Other operators that represent a combination of these arguments, such as ")And(" are also available. The operator determines how the application evaluates the criteria. For example, if you have two criteria lines connected with the operator "And", that means the inventory must match both attributes to meet the criteria. If the two lines are connected with the operator "Or", the inventory only has to match one of the field values to meet the criteria.
                
        2.  Click **Expression**, and define its criteria.
5.  If you want to include any information or instructions related to the work order, then in the left pane, click **Notes** and enter information in the **Notes** field.
6.  Click **Save**. A message is displayed asking if you want to add work order lines.
7.  Perform one of the following tasks:
    -   To add work order lines:
        1.  Click **Yes**.
        2.  Click **Add**.
        3.  Enter information in the Work Order Line fields. See [Work order line field listings](#Work_order_line_field_listings).
        4.  If you want to include any information or instructions related to the work order line, then in the left pane, click **Notes** and enter information in the **Notes** field.
        5.  Click **Save.**
    -   To save the work order without adding lines, click **No**.

## Delete a work order

You can delete a work order that has a status of Pending or Closed.

1.  Perform one of the following tasks:
    -   [View work orders](#View_work_orders), and then in the grid, select the check box next to the work order.
    -   [View detailed work order information](#View_detailed_work_order_information).
2.  From the **Actions** drop-down list, select **Delete**. A confirmation message is displayed.
3.  Click **OK**.

## Delete a work order line

You can delete a work order line that is associated with a work order.

1.  Perform one of the following tasks:
    -   To delete a work order line when modifying a work order:
        1.  Perform one of the following tasks:
            -   [View work orders](#View_work_orders), and then in the grid, select the check box next to the work order.
            -   [View detailed work order information](#View_detailed_work_order_information).
        2.  From the **Actions** drop-down list, select **Modify**. The Modify Work Order window is displayed.
        3.  Click **Work Order Lines**.
        4.  In the grid, select the work order line to delete, and then click **Delete**. A confirmation message is displayed.
    -   To delete the work order line from the work order detail view:
        1.  [View detailed work order information](#View_detailed_work_order_information).
        2.  Click **Order Lines**.
        3.  Select the check box next to the work order line to delete.
        4.  From the **Actions** drop-down list, select **Delete Work Order Line**. A confirmation message is displayed.
2.  Click **OK**. The work order line is deleted.

## Copy a work order

You can copy a work order to create new work orders. When you copy a work order, the associated work order lines are also copied. After you copy the work order, the application updates the status of the new work order to Pending.

1.  Select **Production > Work Orders**.
2.  In the grid, select the check box next to the work order to copy.
3.  From the **Actions** drop-down list, select **Copy**. The Copy Work Order window is displayed.
4.  Enter information in [Copy Work Order fields](#Copy_work_order_fields).
5.  Click **Save**.

## Allocate inventory for a work order

After you create a work order, you allocate inventory and generate pick work for the component (assembly) or top-level (disassembly) items. Held picks can be released manually, or you can confirm held picks, which indicates the pick work has already been completed without actually releasing the pick work. When a work order is allocated, the application updates the work order status and processing status to In-Process and Undelivered, respectively.

1.  Perform one of the following tasks:
    -   [View work orders](#View_work_orders), and then in the grid, select the check box next to the work order.
    -   [View detailed work order information](#View_detailed_work_order_information).
2.  From the **Actions** drop-down list, select **Allocate**. The Allocate Work Order window is displayed.
3.  In the grid, select the check box next to the work order lines for which you want to allocate inventory.
4.  Click **ALLOCATE** or **Next**.
5.  Enter information in the [Allocate Work Order fields](#Allocate_work_order_fields).
6.  Click **Finish**.

## Deallocate inventory from a work order

You can reverse the allocation of component or top-level inventory for work orders that have been allocated to a hold status. When you deallocate the inventory, all of the held pick work, cross docks and replenishments are cancelled. It also cancels any existing cross docks or replenishments. You can then reallocate inventory for the work order. It is not possible to deallocate inventory after the pick work is released.

1.  Perform one of the following tasks:
    -   [View work orders](#View_work_orders), and then in the grid, select the check box next to the work order.
    -   [View detailed work order information](#View_detailed_work_order_information).
2.  From the **Actions** drop-down list, select **Unallocate**. A confirmation message is displayed.
3.  Click **OK**.

## Start or stop a work order

You start a work order after you create the work order, and before you move the inventory to the production station. This indicates that work order has started and is assigned to a production line. You can also stop a work order that is in in-process status.

**Note**: You can start or stop only one work order at a time.

1.  Perform one of the following tasks:
    -   [View work orders](#View_work_orders), and then in the grid, select the check box next to the work order.
    -   [View detailed work order information](#View_detailed_work_order_information).
2.  Perform one of the following tasks:
    -   To start a work order, from the **Actions** drop-down list, select **Start**. A confirmation message is displayed.
    -   To stop a work order:
        1.  From the **Actions** drop-down list, select **Stop**. The Stop Work Order window is displayed.
        2.  From the **Reason** drop-down list, select a reason to stop the work order, and click **OK**. A confirmation message is displayed.
            
            **Note**: If you are starting or stopping a work order associated with assembly workflows, then the Production work flows window is displayed. Select the workflow to perform, and confirm the workflow. When you are finished performing workflows, click **Complete**. See [Confirm a workflow](../../shared-functions/workflows/procedures-for-workflows.md).
            
3.  Click **OK**.

## Move a work order to a different production line or staging location

You can move a work order that is in Pending, Waiting, or In-Process status to a different production line or to a staging location. For example, if a conveyor in a production line becomes damaged, you can move the work order to a different line where operators can continue assembling or disassembling the top-level item. Alternatively, if none of the component (assembly) or top-level (disassembly) inventory has been delivered to the production line, you can move the work order to a staging lane until the inventory is delivered.

**Notes**:

-   You can move only one work order at a time.
-   You cannot move a work order that has been started or is in closed status.

1.  Perform one of the following tasks:
    -   [View work orders](#View_work_orders), and then in the grid, select the check box next to the work order.
    -   [View detailed work order information](#View_detailed_work_order_information).
2.  From the **Actions** drop-down list, select **Move**. The Move Work Order window is displayed.
3.  Enter information in the [Movement Work Orders fields](#Movement_work_orders_fields).
4.  Click **Move Work Order**. A confirmation message is displayed.
    
    **Note**: If you are moving a work order associated with assembly workflows, then the Production work flows window is displayed. Select the workflow to perform, and confirm the workflow. When you are finished performing workflows, click **Complete**. See [Confirm a workflow](../../shared-functions/workflows/procedures-for-workflows.md).
    
5.  Click **OK**.
6.  If you have chosen to preview or print the Work Order Movement Report, the Work Order Movement window is displayed. Perform the following tasks:
    1.  In the Work Order Movement window, enter information in the following fields:
        
        | Field | Description |
        | --- | --- |
        | Printer | Printer that will print the report. |
        | Copies | Number of copies of the report to print. |
        | Print Report and Send for Digital Signature | If Yes, after clicking **Print**, the report is sent for printing at the device entered in the **Printer** field, and a PDF and XML file of the report are generated and sent to an integrated third-party digital capture application.If No and the **Send for Digital Signature** field is set to Yes, the behavior of **Print** is determined by the **Send for Digital Signature** field.<br > If No and the **Send for Digital Signature** field is set to No, the behavior of **Print** is determined by the **Printer** field. |
        | Send for Digital Signature | If Yes and the **Print Report and Send for Digital Signature** field is set to No, after clicking **Print**, a PDF and XML file of the report are generated and sent to an integrated third-party digital capture application. The **Printer** field is ignored. If the **Print Report and Send for Digital Signature** field is set to Yes, it determines the behavior of clicking **Print** regardless of the **Send for Digital Signature** setting.<br > If No and the **Print Report and Send for Digital Signature** field is set to Yes, the behavior of clicking **Print** is determined by the **Print Report and Send for Digital Signature** field.<br > If No and the **Print Report and Send for Digital Signature** field is set to No, the behavior of clicking **Print** is determined by the **Printer** field.<br > **Note**: The **Print Report and Send for Digital Signature** and **Send for Digital Signature** fields are only available if this instance is integrated with a third-party digital signature capture application, and the selected report is enabled and configured for capturing digital signatures. |
        
    2.  Click **Print**. A confirmation message is displayed.
    3.  Click **OK**.

## Release picks for a work order

You can release all or some of the picks for a work order. To release held picks, you must first release them to a Pending status, and then you can release them to a Released status, so an operator can perform the work.

1.  To release held picks for a work order at the work order level:
    1.  [View work orders](#View_work_orders), and then in the grid, select the check box next to the work order.
    2.  From the **Actions** drop-down list, select **Release Work Order**. The Release Work Order window is displayed.
    3.  In the **Percentage** field, enter the percentage of picks to be released.
    4.  Click **OK**. A confirmation message is displayed.
    5.  Click **OK**. The picks are released to a Pending status.
2.  To release held picks for a work order at the work order detail level:
    1.  [View detailed work order information](#View_detailed_work_order_information).
    2.  Select **Picks**.
    3.  In the grid, select the check box next to the pick work to be released.
    4.  From the **Actions** drop-down list, select **Release Held Picks**.
    5.  Click **OK**. A confirmation message is displayed.
    6.  Click **OK**. The picks are released to a Pending status.
3.  To release picks for a work order:
    1.  [View detailed work order information](#View_detailed_work_order_information).
    2.  Select **Picks**.
    3.  In the grid, select the check box next to the pick work to be released.
    4.  From the **Actions** drop-down list, select **Release Picks**.
    5.  Click **OK**. A confirmation message is displayed.
    6.  Click **OK**. The picks are released to a Released status.

## Request additional inventory for an assembly work order

You can request an additional quantity or catch quantity of a component item to complete an assembly work order. When you request an additional quantity, the application increases the line quantity and pick quantity for the item on the work order line. When you request an additional catch quantity for the item, the application increases the line catch quantity for the item on the work order line. After you request additional components, you are required to allocate the work order again to have the quantity picked and delivered. You can only request additional components after a work order has been allocated.

**Note**: The additional catch quantity field is displayed only if the component item is catch tracked (**Catch Code** field in the item configuration is not blank).

1.  [View detailed work order information](#View_detailed_work_order_information).
2.  Click **Order Lines**.
3.  In the grid, select the check box next to the work order line for the component item.
4.  From the **Actions** drop-down list, select **Request Component**. The Request Component window is displayed.
5.  Enter the additional quantity or catch quantity of the component item to be delivered to the line.
6.  Click **OK**. A confirmation message is displayed.
7.  Click **OK**.

## Cancel a replenishment for a work order

Cancelling a replenishment stops the application from attempting to fill a short allocation. You may want to cancel a replenishment if you do not require the product to fulfill a work order.

1.  [View detailed work order information](#View_detailed_work_order_information).
2.  Perform one of the following tasks:
    -   Select **Pending Replenishments**, then in the grid, select the row for the replenishment, and then click **Cancel Replen**. A confirmation message is displayed.
    -   Select **Shorts**, then in the grid, select the row for the short order line associated with the replenishment, and then click **Cancel Short**. A confirmation message is displayed.
3.  Click **OK**.

## Request an additional quantity of finished goods for a disassembly work order

You can request an additional quantity or catch quantity of a top-level item needed to complete a disassembly work order. When you request an additional quantity of a top-level item, the application increases the pick quantity for the item on the work order. When you request an additional catch quantity for the item, the application increases the line catch quantity for the item on the work order. After you request additional finished goods, you are required to allocate the work order again to have the quantity picked and delivered. You can only request an additional quantity after a work order has been allocated.

**Note**: The additional catch quantity field is displayed only if the top-level item is catch tracked (**Catch Code** field in the item configuration is not blank).

1.  Perform one of the following tasks:
    -   [View work orders](#View_work_orders), and then in the grid, select the check box next to the work order.
    -   [View detailed work order information](#View_detailed_work_order_information).
2.  From the **Actions** drop-down list, select **Request Finished Goods**. The Request Finished Goods window is displayed.
3.  Enter the additional quantity or catch quantity of the top-level item on the work order to be delivered to the line.
4.  Click **OK**. A confirmation message is displayed.
5.  Click **OK**.

## Confirm picks for a work order

The application supports picking component or top-level inventory for a work order without releasing the actual pick work. This is typically done as a paper-based process in which operators travel to a location, pick the inventory for a work order, and then deliver the inventory to a work-in-process location. To update the application records, you allocate a work order to the hold status and then, without releasing the pick work, you confirm that the pick work has already been completed.

You can confirm picks for a work order only if the following prerequisites are met:

-   The picks are held (not released)
-   The work order status is In Process
-   Replenishments or cross-docks do not exist for the work order
-   The catch quantity is not configured for the item in the work order
-   RF pick verification settings are not configured

**Note**: To confirm pick work that has been released, use Pick Confirmation. See [Confirm picks](../../picking/pick-confirmation.md).

1.  Perform one of the following tasks:
    -   [View work orders](#View_work_orders), and then in the grid, select the check box next to the work order.
    -   [View detailed work order information](#View_detailed_work_order_information).
2.  From the **Actions** drop-down list, select **Confirm Picks**. A confirmation message is displayed.
3.  Click **OK**.

## Cancel picks for a work order

You can cancel all or some of the picks for a work order.

1.  [View detailed work order information](#View_detailed_work_order_information).
2.  Select **Picks**.
3.  In the grid, select the check box next to the pick status, and then from the **Actions** drop-down list, select **Cancel Picks**. The Cancel Picks window is displayed.
4.  From the **Select Cancel Code** drop-down list, select a reason for cancelling the pick.
5.  To prevent any inventory activity from taking place in the location, select the **Put location in error status** check box.
6.  Click **Apply**. A confirmation message is displayed.
7.  Click **OK**.

## Cancel cross docking for a work order

When you cancel a cross dock, you have the option of canceling the associated picks; you can also uncheck the **Cross Dock** field on the order line, so it not considered for future cross dock opportunities.

You may want to cancel cross docking work or clear cross docking from the work order line, for example, if inventory to fill the cross docking request is not received, or only a portion of the inventory is received and the customer does not allow the order to be shipped short.

1.  [View detailed work order information](#View_detailed_work_order_information).
2.  Click **Cross Dock**.
3.  In the grid, select the check box next to the cross dock.
4.  Click **Cancel Cross Dock**. The Cancel Cross Dock window is displayed.
5.  Enter information in the following fields:
    
     
    | Field | Description |
    | --- | --- |
    | Unflag Order Line | Indicates that in addition to cancelling the cross docking work, the **Cross Dock** field for the work order line is unchecked. If deselected, then the work order line remains marked for cross docking. |
    | Cancel Picks | Indicates that in addition to cancelling the cross docking work, any picks associated with the work order line are also cancelled. If deselected, then the picks for the order line are not cancelled. The drop-down list displays the unique identifier for the cancelling the picks. It is a configuration that determines how the application processes a pick cancellation to which the code is applied. |
    
6.  Click **OK**. A confirmation message is displayed.
7.  Click **OK.**

## Unpick inventory

You can undo the pick (unpick) of an LPN and cancel the associated picks. To unpick an LPN, it must either not be picked from the storage location or must have been deposited in a production station. You cannot unpick inventory after it has been deposited in a production line or production station.

1.  [View detailed work order information](#View_detailed_work_order_information), and then select **Picked**.
2.  In the grid, select the check box next to the LPN, and then from the **Actions** drop-down list, select **Unpick**. The Unpick window is displayed.
3.  From the **Cancel code** drop-down list, select the cancel code to assign to the pick cancellation.
4.  In the **Location** field, enter the location to which to move the component inventory.
5.  Click **OK**.
6.  A confirmation message is displayed.
7.  Click **OK**.

## Receive or putaway a top-level or component item

After top-level items are assembled or disassembled, they must be received into the warehouse. The process, known as internal receiving, consists of identifying the new top-level or component items and putting them away. The process typically occurs at the production line or work order location in which the top-level items were assembled or disassembled. For this reason, internal receiving is also known as production line receiving.

During assembly, operators typically build a pallet of a finished top-level item and identify the entire pallet. Another option is to identify individual eaches or cases of inventory. When identifying serialized items, the items are identified individually, rather than by case or pallet. If you are identifying top-level items for work orders with component tracking, then, after specifying the attributes for the top-level item, you also need to specify the attributes of the components that were used to build the top-level item.

1.  Perform one of the following tasks:
    -   [View work orders](#View_work_orders), and then in the grid, select the check box next to the work order.
    -   [View detailed work order information](#View_detailed_work_order_information).
2.  From the **Actions** drop-down list, select **Receive**.
3.  In the grid, select the check box next to the work order or work order line that you want to identify.
4.  Enter information in the [Return to Stock or Receive fields](#Return_to_Stock_or_Receive_fields).
5.  Click **Receive**.
6.  If component tracking is enabled for the work order, and the Component Tracking window is displayed, perform the following tasks:
    1.  Confirm and update the component attributes as necessary.
        
        **Notes**:
        
        -   The fields that can be updated are highlighted with a yellow border.
        -   Component serial tracking is limited only to Sub-LPN and Detail LPN serialization levels.
            -   If the component serialization level is LPN, the serial number cannot be updated regardless of whether the item is serialized or not.
            -   If serialization level of the top-level item is LPN, then the component serial numbers cannot be updated even if the component serialization level is Sub-LPN and Detail LPN.
        -   Multiple cases or eaches cannot be received at the same time for component tracked work orders. If you need to receive 10 cases, then you must perform the receiving operation 10 times (once for each case).
        -   Component serial numbers captured are not displayed on the Component Serial Number page.
        
    2.  Click **Submit**.
        
        **Note**: If serial number or catch quantity capturing is not required for the item, and if the item is tracked at the LPN level and you are receiving a quantity of 1, then the application processes the received inventory. If you did not enter an LPN, an identifier is automatically generated.
        
7.  If the Number Capture window is displayed, perform the following tasks:
    1.  Under **Quantity**, perform one of the following tasks:
        -   To automatically generate the identifiers, click **Generate LPNs**.
        -   To enter a range of identifiers, click **Enter a range**, then enter a starting and ending value, and then press **Tab**.
        -   To enter individual identifiers, in the text box, enter the first identifier and then press **Enter**. Repeat this process until you have entered the required number of identifiers.
    2.  If the inventory is serialized and requires serial number capturing, then under **Serial Numbers**, enter a serial number for each LPN that requires it.
        
        **Note**: To enter a range of serial numbers, click **Enter Range**, then enter the range of numbers to apply to the inventory, and then press **Tab**.
        
    3.  If the inventory is catch tracked and requires a catch quantity, under **Catch Quantity**, enter a value for each LPN that requires it.
    4.  Click **Receive**.
8.  To putaway an item:
    1.  Click **Putaway**.
    2.  In the gird, select the check box next to the LPN to putaway.
    3.  Under **Putaway Method**, perform the following tasks:
        1.  Select how a storage location is found:
            -   **System selects location**: The application automatically selects the putaway location.
            -   **User selects location**: You manually select the putaway location. If you select this option, then in the **Location** field, enter the putaway location.
        2.  Select the storage method for the inventory:
            -   **Add to work queue**: Directed putaway work is created in the work queue. If you select this option, then you can also select a specific operator to which the work is assigned.
            -   **Move immediately**: The application is immediately updated to reflect that the inventory has been moved to the putaway location.
        3.  To print a label for the LPN, set the **Print Label** field to Yes, and then enter a value in the **Number of Labels** field.
    4.  Click **Putaway**.

## Return to stock

Any unconsumed inventory needs to be returned to storage. You can return the inventory with a new LPN or use the existing LPN. If you do not provide an LPN while returning the inventory to stock, then the application assigns a new LPN to the inventory. This applies to both assembly and disassembly work orders.

1.  Perform one of the following tasks:
    -   [View work orders](#View_work_orders), and then in the grid, select the check box next to the work order.
    -   [View detailed work order information](#View_detailed_work_order_information).
2.  From the **Actions** drop-down list, select **Complete**. The Complete Work Order window is displayed.
3.  To return an item to stock:
    1.  Click **Return to Stock**.
    2.  The Return to Stock window is displayed.
    3.  In the grid, select the check box next to the work order or work order line that you want to identify, and then enter information in the [Return to Stock or Receive fields](#Return_to_Stock_or_Receive_fields).
4.  To putaway an item:
    1.  Click **Putaway**.
    2.  In the gird, select the check box next to the LPN to putaway.
    3.  Under **Putaway Method**, perform the following tasks:
        1.  Select how a storage location is found:
            -   **System selects location**: The application automatically selects the putaway location.
            -   **User selects location**: You manually select the putaway location. If you select this option, then in the **Location** field, enter the putaway location.
        2.  Select the storage method for the inventory:
            -   **Add to work queue**: Directed putaway work is created in the work queue. If you select this option, then you can also select a specific operator to which the work is assigned.
            -   **Move immediately**: The application is immediately updated to reflect that the inventory has been moved to the putaway location.
        3.  To print a label for the LPN, set the **Print Label** field to Yes, and then enter a value in the **Number of Labels** field.
    4.  Click **Putaway**.

## Close a work order

A work order can be closed after the assembly or disassembly of all the items in the work order and the following tasks have been completed:

-   Top-level items (for an assembly work order) or component items (for a disassembly work order) have been put away, and any unconsumed inventory has been returned to stock.
-   Inbound shipments related to the work order are closed.
-   Any picks, replenishments, or cross docks that exist are completed.
-   The reported scrapped quantity does not exceed the expected scrap percentage defined for the work order.

1.  Perform one of the following tasks:
    -   [View work orders](#View_work_orders), and then in the grid, select the check box next to the work order.
    -   [View detailed work order information](#View_detailed_work_order_information).
2.  From the **Actions** drop-down list, select **Complete**. The Complete Work Order window is displayed.
3.  If you are prompted to close the inbound shipments that are related to the work order, click **Yes**.
4.  Enter information in the [Complete Work Order Page fields](#Complete_work_order_page_fields).
5.  Identify any return-to-stock, top-level, or component items. See [Receive or put away a top-level or component item](#Receive_or_putaway_a_top-level_or_component_item).
6.  [Return to stock](#Return_to_stock).
7.  Click **Close**. The Close Work Order window is displayed.
8.  If you are prompted with the following information, review it, and then click **Yes**.
    -   Picks, replenishments, or cross docks exist, and closing the work order will automatically cancel them.
    -   Waiting work order lines exist on the assembly work order, and closing the work order will automatically cancel them.
    -   Inventory produced from the work order is not received into the warehouse, and closing the work order will automatically cancel them.
    -   Work order lines have exceeded the expected scrap quantity, and closing the work order will automatically cancel them.
        
        **Note**: If you are closing a work order associated with assembly workflows, then the Production work flows window is displayed. Select the workflow to perform, and confirm the workflow. When you are finished performing workflows, click **Complete**. See [Confirm a workflow](../../shared-functions/workflows/procedures-for-workflows.md).
        
9.  Click **Save**. A confirmation message is displayed.
10.  Click **OK**.

## Work order field listings

### Work Order fields

 
| Field | Description |
| --- | --- |
| Work Order | Identifier for a work order. A work order is an internal order used to find, allocate, and deliver product to a work-in-process area for assembly or disassembly, conversion, kitting, or repackaging. |
| Work Order Type | Unique identifier for the work order type. A work order type is a category into which work orders are grouped based on similar processing characteristics. |
| Item | Top-level item (finished good) to be built using component items or to be disassembled into component items as specified by the work order. |
| Image | Media tool that displays the image that is associated with the entity. If an image has not been associated with the entity, a default image is displayed. You can view an enlarged version of the image and, depending on the settings, you can add, change, or remove the associated image file. |
| Quantity | Total number of finished items that must be assembled or disassembled. |
| Revision | Unique identifier for this instance of the work order, which enables you to use a standard work order multiple times. |
| Status | Position of the work order in the work order process.<br>-   • **Pending**: The work order has been created.
<br>-   • **In Process**: The work order has been allocated.
<br>-   • **Waiting for Work Order**: Another work order must be generated and allocated to replenish inventory for a top-level, component item.
<br>-   • **Closed**: The work order is complete. |
| Due Date | Date and time when the work order must be completed. |
| Production Line | Name of the production line. A production line is an arrangement of machines or sequence of operations (production stations) involved with the assembly or disassembly of top-level item. |
| Progress | Percentage of top-level items that have been assembled or disassembled relative to the total expected quantity for the work order assigned to the production line. Additionally, an X of Y value displays the number of top-level items assembled or disassembled out of the total expected quantity; for example, (50 of 100). |
| Plan Sequence | Number that represents the order in which a work order is to be processed as compared to other work orders that are to be processed on a sequence-based production line. The Plan Sequence is only a visual cue to help operators producing work orders on a production line. The application does not force operators to produce work orders in the specified sequence. Only available if the **Plan Type** configured for the production line is Sequence. |
| Processing Priority | Number that identifies the priority at which work orders are allocated. Orders with the highest priority are allocated first. Processing priority numbers range from 1 to 9 with 1 being the highest priority. If this field is left blank, the application will set the processing priority to 5 by default. |
| Scheduled Start Date | Date and time on which the processing of a work order on a production line is scheduled to start. Only available if the **Plan Type** configured for the production line is Scheduled. |
| Processing Status | Processing status of the work order.<br>-   • **Pending**: The component (assembly) or top-level (disassembly) inventory for the work order or work order line has not yet been allocated.
<br>-   • **Waiting**: The component (assembly) or top-level (disassembly) inventory has been allocated for the work order or work order line resulting in replenishments, but all of the replenishments have not yet been filled.
<br>-   • **Undelivered**: The component (assembly) or top-level (disassembly) inventory has been allocated for the work order or work order line resulting in pick work, but none of the component (assembly) or top-level (disassembly) inventory has been delivered to the processing location yet.
<br>-   • **Partially Delivered**: Some of the component (assembly) or top-level (disassembly) inventory has been delivered to the processing location (such as, a production station for a work order line), but there is either not enough of the component inventory to build a top-level item for an assembly work order; or, for assembly and disassembly, the work order was stopped in the middle of production.
<br>-   • **Delivered**: All of the required component (assembly) or top-level (disassembly) items specified in the work order or work order line have been delivered to the processing location, but the work order has not yet been started.
<br>-   • **Ready**: For a work order, the work order has been started and (for assembly) enough component inventory has arrived at the processing location to build at least one top-level item or at least one top-level item has been delivered to the production line for break down. For a work order line, the work order has been started and enough of the component inventory specified by the work order line has arrived to be used in making at least one top-level item.
<br>-   • **Completed**: For a work order, all of the top-level items for the work order have been built and identified, or all component items have been identified from the broken down top-level items. For a work order line, all of the component inventory specified in the work order line has been consumed.
<br>-   • **Closed**: The work order has been closed. |
| Work Order Client | Unique identifier for a client who is responsible for creating the work order and is not necessarily the client that houses the top-level item specified in the work order. Only displayed in a 3PL environment. |
| Disassembly | Indicates whether the work order is for disassembling a top-level item into component items. If not, the work order is for assembling component items into a top-level item. |
| Inventory Status | Defines the quality or disposition of the inventory. This is the default inventory status that is displayed when an operator identifies completed top-level items or disassembled component items for the work order. However, the operator may change the status. |
| Rule Name | Name of the allocation rule. An allocation rule is a processing command that specifies the inventory attribute values that are acceptable to fulfill an order line, work order detail, work order line, or bill of materials (BOM) detail. |
| Lot Number | Identifier assigned to a quantity of inventory that is uniquely identified during the manufacturing process for the purpose of tracking an attribute of that inventory, such as its expiration date. Lots differentiate distinct groups of inventory that have the same item. Lots are user defined and are not necessarily unique since the same lot can be applied to different items. However, lot and item number combinations must be unique. |
| Supplier Lot Number | Identifier that is an attribute of an item or item and lot combination and is assigned by the item's supplier. A supplier lot number used to uniquely identify and track the inventory to which it is assigned. The supplier lot number is a different attribute than the lot number, which is a manufacturer or production lot number. |
| Revision | Unique identifier for this instance of the work order, which enables you to use a standard work order multiple times. |
| Origin Code | Origin code to assign to top-level items built for the work order. An origin code is a unique identifier that is assigned to an item to identify the item's place of origin. Typically used for export paperwork. Origin codes are user defined. Only available for assembly work orders and if the top-level item requires this attribute. |
| Total Delivered Quantity | Total quantity of the top-level or component item that has been delivered to the production line. |
| In Process Quantity | Quantity of allocated items that must be delivered to the production line for the work order. |
| Pick Quantity | Quantity (in terms of material handling or stock keeping units) of the item to be picked for the disassembly work order. |
| Created | Date and time when the work order was created in the application. |
| Allocation Date | Date and time on which the inventory was allocated from storage to fulfill the order or work order. |
| Completion Date | Date and time by when the processing of the work order must be completed. |
| Priority Code | Code that identifies the priority at which picks for an order or work order are released. Orders with the highest priority codes are released first. Priority codes range from 1 to 99 with 1 being the highest priority. |
| Processing Area | Area in your facility in which production lines are located. |
| Production Tolerance (%) | Value that determines the minimum and maximum percentage of the total number of required finished items that can be assembled or disassembled. For example, if you enter a production tolerance of 10, then you can assemble and identify anywhere from 90% to 110% of the number of finished items required for the work order. |
| Project Number | Project number assigned to the assembly work order. The project number is sent to the host application and used for reporting purposes. |
| Account Number | Account number, such as a general ledger account number assigned to the work order. Account numbers are used in host transactions and for report purposes. Only available for assembly work orders. |
| Production Catch Quantity | Total catch unit quantity of top-level items that have been assembled for this work order. A catch unit quantity is a variable measure of inventory (such as weight, volume, or length) that is associated with one material handling (stock keeping) unit of the inventory. Only available if the top-level item requires catch quantities. |
| Production Quantity | Total number of top-level items that have been assembled for this work order. |
| Work Order Catch Quantity | Total catch unit quantity of top-level items to assemble or disassemble for this work order. A catch unit quantity is a variable measure of inventory (such as weight, volume, or length) that is associated with one material handling (stock keeping) unit of the inventory. Only available if the top-level item requires catch quantities. |
| Completion User ID | User ID of the operator that closed the work order. |
| Component Tracking | Indicates whether the application tracks the attributes of the component items after the top-level item on work order is assembled and identified. A check mark is displayed if the application tracks the attributes of the component items.<br > Only available for assembly work orders. |
| Release Remaining Lines | Indicates whether the pick work for the unmarked work order lines will be released as usual or will be held until the inventory that is marked for cross docking is received and allocated. A check mark is displayed in this field if the pick work for the unmarked work order lines will be released as usual. |
| Date Last Modified | Date and time indicating when the work order line was last modified. |
| Exclusively Occupy Production Line | Indicates whether the work order is to exclusively occupy a production line (the work order is not to be processed at the same time as other work orders on the same production line). If it does, then the work order must be started either on an exclusive production line (if the **Exclusive Work Order** field for the production line is set to Yes) or on a non-exclusive production line that has no other work orders started on it. A check mark is displayed in this field if the work order exclusively occupies a production line. |
| Started | Indicates whether the work order processing has started. A check mark is displayed in this field if the work order processing has started. |
| Automatically Release Pick | Indicates whether the application is to automatically release the pick work for the component items for a work order in advance of the work order's scheduled start date. The amount of time in advance of the scheduled start date is defined by the value in the **Automatically Release Pick Time** field. A check mark is displayed in this field if the application automatically releases the pick work for the component items. |
| Automatically Release Pick Time | Number of minutes in advance of a work order's scheduled start time that the application is to automatically release picks for the work order's items. |
| Duration Time | Amount of time, in minutes, to complete the work order. The duration time is either downloaded from the host application or is specified manually by a user, and is typically based on historical production information. |
| Without Components | Indicates whether the work order does not need work order details (lines), does not need component inventory allocation, does not need the application to direct an operator to pick component inventory from a storage location to a production line, and does not need to track the component inventory. The only operations associated with this type of work order are to identify the top-level items and put them away. Work orders without components are especially useful for facilities that do not track their component inventory in the application.<br > A check mark is displayed in this field if the work order does not need work order details (lines), component inventory allocation, does not need the application to direct an operator to pick component inventory from a storage location to a production line, and does not need to track the component inventory.<br > Only available for assembly work orders. |
| Activity Code | Code that defines the specific activity being performed to build up or break down the top-level item specified by the BOM. |
| Disassembly Station | Disassembly station to which the top-level items for the work order are to be moved. A disassembly station is a position on a production line where a specific operation is performed during the disassembly of the top-level item (finished good). Only available when the work order type is Disassembly. |
| Inventory Status Progression | Inventory status progression of the allocated component items. An inventory status progression is a series of inventory statuses that define the levels of quality at which a customer is willing to accept a product. When an inventory status progression is specified on an order, then the application can select product to satisfy that order based on a prioritized list of acceptable inventory statuses rather than a single status. This functionality lets customers define a wider range of acceptable inventory as well as specify their preference on the quality of the inventory that they are willing to accept. |
| Round Pick Quantity | Indicates whether the allocation is to automatically round up the pick quantity to the next highest UOM. This option is beneficial, for example, in situations where it is easier to pick an entire case or pallet of an item than to break a unit of measure (UOM) to complete a pick. A check mark is displayed in this field if the allocation automatically rounds up the pick quantity to the next highest UOM. |
| Cross Dock | Indicates whether inventory is moved directly from receiving to a cross dock location or a specified staging location to satisfy an outbound order or work order, when the inventory specified on this outbound order or work order line is identified. A check mark is displayed in this field when the order or work order line uses cross docked inventory. |
| Allow Cross-Dock | Indicates whether the inventory produced from the assembly work order or the disassembly work order line can be cross docked. If the inventory can be cross docked, a check mark is displayed in this column. |
| Pick Catch Quantity | Catch unit quantity of the component item that has not yet been allocated for the work order. When you first create the work order, this value matches the value entered in the **Line Catch Quantity** field. As the component item is successfully allocated, this quantity will decrease to zero. If you later determine that you need more of the component than originally planned, enter the additional quantity in this field. You can then reallocate the work order line for the additional quantity. Only available for assembly work orders. |
| Over-Alloc In-Process Qty | Quantity of over-allocated items that was delivered to the production line. |
| Units Per Pack | Default number of units (pieces) per inner pack to be supplied for the order line or work order line. |
| Units per Case | Default number of units (pieces) per case supplied for the order line or work order line. |
| Footprint Code | Name that identifies a footprint, which describes the packaging dimensions and units of measure for the item with which it is associated. |
| Over Allocation Amount | Total amount of inventory that is allocated over the requested quantity when the allocation code is **Quantity**, or percentage of inventory that can be allocated when the allocation code is **Percentage**. If the over-allocation code is **Percentage**, then the over-allocation amount should be a value from 1 to 100 that indicates the percentage of the order quantity that can be over-allocated. If the over-allocation code is **Quantity**, then the over-allocation amount should be a value that represents the number that can be over-allocated. |
| Over Allocation Code | Code that identifies how over allocation is performed.<br>-   • **Percentage**: The application is permitted to allocate a certain percentage more, as defined in the **Over Allocation Amount** field, of the original quantity of component items required for the order line.
<br>-   • **Quantity**: The application is permitted to allocate a certain quantity more, as defined in the **Over Allocation Amount** field, of the original quantity of component items required for the order line.
<br > Over allocation is the process of allocating more than the indicated amount of inventory to satisfy an order or work order. Over allocation is beneficial in situations where it is easier to pick an entire case or pallet instead of breaking a case to complete a pick. |
| Inventory Rotation Method | Value that represents the order in which the allocation process selects available inventory for allocation. Select an inventory rotation method if you want the application to search for inventory based on date processing or location.<br>-   • **FEFO-ORDER-BY and FEFO-ORDER-BY-ABSOLUTE**: First-expiration, first-out. The first inventory to expire will be selected first.
<br>-   • **FIFO-ORDER-BY and FIFO-ORDER-BY-ABSOLUTE**: First-in, first-out. The oldest inventory will be selected first.
<br>-   • **LEFO-ORDER-BY and LEFO-ORDER-BY-ABSOLUTE**: Last-expiration, first-out. The last inventory to expire will be selected first.
<br>-   • **LIFO-ORDER-BY and LIFO-ORDER-BY-ABSOLUTE**: Last-in, first-out. The newest inventory will be selected first.
<br>-   • **LOCATION-ORDER-BY**: Locations are ordered within a pick zone (maintaining the allocation search path order) by the location attributes specified for the **Location Sort** field in inventory selection settings.
<br>-   •
    
    **No selection (blank)**: The application uses the inventory rotation method of the highest defined level of precedence. For information on precedence, see [Inventory rotation allocation processing](../../configuration/outbound/allocation/inventory-rotation-allocation.md).
    
    <br>
    
    **Note**: Inventory rotation methods defined at a lower precedence (except the default method) are automatically copied to the order line or work order line when the line is created. For example, if an order line is created for a date-tracked item with a rotation method defined, the rotation method is copied from the item to the order line, and then the application uses the order line rotation method during allocation.
    
    <br > If no inventory rotation method is defined at any level, then the application uses the allocation search path sequence and allocates the first available inventory it finds that matches all of the required attributes.
<br > When using inventory rotation methods that are not absolute, the application searches for inventory by allocation search path in sequence until it finds a pick zone that contains the inventory, and then allocates inventory that is closest to the preferred processing date. Therefore, the application stops searching at the first pick zone in which matching inventory is found.<br > When using absolute inventory rotation methods, the application searches either all of the allocation search paths for inventory that is closest to the preferred processing date or, if absolute groups are defined, each absolute group in sequence until it finds matching inventory and then allocates inventory that is closest to the preferred processing date from the pick zones within the absolute group. Therefore, the absolute method allows for more a comprehensive search to find the inventory. |
| Minimum Shelf Life (Hours) | Minimum number of hours away from expiration that a date-tracked item must be considered for allocation. For example, if this value is 10, then the application only allocates inventory that has at least 10 hours to reach its expiration date. Only available if the item specified on the order line is date-tracked. |
| Total Consumed Quantity | Total quantity of the top-level items or component items that have been consumed as tracked by the application. |
| Sub Work Order Number | Identifier for a nested work order. |
| Sub Work Order Revision | Unique identifier for the instance of the sub-work order, which enables you to use a standard sub-work order multiple times. |
| Returned Quantity | Total quantity of the component item (for assembly work orders), or top-level items (for disassembly work orders) that was returned to stock. This field is display only. |
| Customs Consignment | Unique identifier assigned to an assembly work order of bonded inventory. A customs consignment is an application-generated ID number that consists of a prefix (the warehouse ID) plus the next value in the customs consignment ID sequence. For example, if your warehouse ID is WMD1 and the next number in the sequence is 123456, then the customs consignment ID will be WMD1123456. |
| Customs Type | Identifier that defines the type of customs tracking required for the inventory. |
| Customs Commodity Code | Commodity code that is used by a duty management application to determine the type of duty to be paid for this item. The code must match a commodity code that is defined in the duty management application; Warehouse Management does not validate this code. |
| Default Origin Code | Country in which the item was manufactured. This value is displayed by default on the planned inbound order line for the item but during receiving it can be changed. Only applies to items for which customs or excise duties need to be paid. |
| Customs VAT Code | Code for the value added tax (VAT) for the item. A customs VAT is charged on goods and some services that are imported from countries outside the European Unit (EU) and brought into the United Kingdom (UK) from other EU countries. It is also charged on most goods and services that VAT-registered businesses provide in the UK.<br>-   • **Standard**: The standard customs VAT rate is charged for this item.
<br>-   • **Zero**: No customs VAT is charged for this item. |
| Duty Stamp Tracked | Indicates that the inventory requires a duty stamp. A duty stamp is a form of tax on certain excise goods, the payment of which is certified by the attaching or impressing of an official stamp on the taxed item. Only available if customs is enabled for the warehouse. |
| Customs Cost | Monetary amount that is paid to customs for the item. Only applies to items for which customs or excise duties need to be paid. |
| Customs Currency | Unique identifier that is used to represent the currency for the warehouse. For example, the U.S. dollar is represented by the code USD. Monetary values entered for this record are saved in the currency code displayed. The currency for the warehouse is specified by locale. |
| Allow Putaway to Transport Equipment | Indicates whether the inventory produced from the work order can be put away to storage transport equipment during directed putaway. If the inventory can be put away to storage transport equipment, a check mark is displayed. |
| Transport Equipment | Alphanumeric identifier of the storage transport equipment to which the inventory produced from the work order can be putaway. The storage transport equipment is used only when the **Allow Putaway to Transport Equipment** field is set to Yes for the work order. Multiple work orders can be assigned to the same storage transport equipment. |

### Work Order detail fields

 
| Field | Description |
| --- | --- |
| Type | Unique identifier for the work order type. A work order type is a category into which work orders are grouped based on similar processing characteristics. |
| Production Line | Name of the production line. A production line is an arrangement of machines or sequence of operations (production stations) involved with the assembly or disassembly of top-level item. |
| Started | If Yes, the work order processing has started. If No, the work order processing has not started. |
| Due Date | Date and time when the work order must be completed. |
| Created | Date and time when the work order was created in the application. |
| Processing Status | Processing status of the work order.<br>-   • **Pending**: The component (assembly) or top-level (disassembly) inventory for the work order or work order line has not yet been allocated.
<br>-   • **Waiting**: The component (assembly) or top-level (disassembly) inventory has been allocated for the work order or work order line resulting in replenishments, but all of the replenishments have not yet been filled.
<br>-   • **Undelivered**: The component (assembly) or top-level (disassembly) inventory has been allocated for the work order or work order line resulting in pick work, but none of the component (assembly) or top-level (disassembly) inventory has been delivered to the processing location yet.
<br>-   • **Partially Delivered**: Some of the component (assembly) or top-level (disassembly) inventory has been delivered to the processing location (such as, a production station for a work order line), but there is either not enough of the component inventory to build a top-level item for an assembly work order; or, for assembly and disassembly, the work order was stopped in the middle of production.
<br>-   • **Delivered**: All of the required component (assembly) or top-level (disassembly) items specified in the work order or work order line have been delivered to the processing location, but the work order has not yet been started.
<br>-   • **Ready**: For a work order, the work order has been started and (for assembly) enough component inventory has arrived at the processing location to build at least one top-level item or at least one top-level item has been delivered to the production line for break down. For a work order line, the work order has been started and enough of the component inventory specified by the work order line has arrived to be used in making at least one top-level item.
<br>-   • **Completed**: For a work order, all of the top-level items for the work order have been built and identified, or all component items have been identified from the broken down top-level items. For a work order line, all of the component inventory specified in the work order line has been consumed.
<br>-   • **Closed**: The work order has been closed. |
| Progress | Percentage of top-level items that have been assembled or disassembled relative to the total expected quantity for the work order assigned to the production line. Additionally, an X of Y value displays the number of top-level items assembled or disassembled out of the total expected quantity; for example, (50 of 100). |
| Work Order Quantity | Total number of items that must be assembled or disassembled. |

### Movement Work Orders fields

 
| Field | Description |
| --- | --- |
| Current Production Line | Production line to which the work order is currently assigned. A production line is an arrangement of machines and/or sequence of operations (production stations) involved with a single manufacturing operation or production process. |
| Default Staging Location | Staging location to which you want to move the component or top-level inventory for the work order that you are moving.<br > **Note**: You can only move a work order from a production line to a staging location if none of the component or top-level inventory has been delivered to a production station.<br > The Default Staging Location field displays the staging location for the new production line, if a staging location was specified for that line. A staging location is a location in your facility where component or top-level inventory used to supply the production line is temporarily deposited prior to being moved to the production line for use in building or disassembling a top-level item to fill a work order. Typically, you only want to enter a value in this field if you do not have a staging locations configured for the new production line or its production stations. Picked component or top-level inventory is delivered to the production station staging location specified for the work order detail. If it is not specified on the work order line, then picked component or top-level inventory is delivered to the production line staging location specified for the work order. If it is not specified on the work order, then picked component or top-level inventory is delivered to the default staging location specified in this field or during allocation. |
| Start After Movement | Indicates that the work order starts immediately after moving it to the new production line. If you will be producing the work order at a later time instead of immediately after the move, then deselect this check box. |
| New Production Line | Production line to which the work order is being moved. A production line is an arrangement of machines and/or sequence of operations (production stations) involved with a single manufacturing operation or production process. |
| Disassembly Station | Disassembly station to which the top-level items for the work order are to be moved. A disassembly station is a position on a production line where a specific operation is performed during the disassembly of the top-level item (finished good). Only available when the work order type is Disassembly. |
| New Production Station | Production station, to which the work order detail's component inventory is to be moved. A production station is a position on a production line where a specific operation is performed during the production of a top-level item (finished good). A production station can be assigned to more than one production line. |
| Do Not Print Report | Indicates that you do not want to print the Work Order Movement report. The Work Order Movement report lists the component inventory that needs to be moved manually after a work order movement. |
| Preview The Report | Indicates that you want to view the Work Order Movement report on the screen, but you do not want to print it. The Work Order Movement report lists the component inventory that needs to be moved manually after a work order movement. |
| Print Report | Indicates that you want to print the Work Order Movement report. The Work Order Movement report lists the component inventory that needs to be moved manually after a work order movement. |
| Printers | Printer to which to print the Work Order Movement report. |

### Allocate Work Order fields

 
| Field | Description |
| --- | --- |
| Staging Location | Location in which allocated inventory used to supply the production line is temporarily deposited prior to being moved to the production line for use in assembling or disassembling a top-level item to fill a work order. Select the staging location for the picked inventory.<br>-   • If the staging location specified on the production line or for each individual production station is used, the field is blank and cannot be changed.
<br>-   • If the staging location specified on the production line is used, the value is displayed but cannot be changed. |
| Release Remaining Lines | Used for cross docking purposes.<br > If Yes, the pick work for the unmarked work order lines will be released as usual.<br > If No, then the pick work created for unmarked work order lines will be held until the inventory that is marked for cross docking is received and allocated. |
| Start After Allocation | If Yes, the application automatically starts the work order after the inventory is allocated. If you will be starting the work order at a later time instead of immediately after the allocation, then select No. |
| LPN Levels Marked for Immediate Release | Indicates that the LPN is to be released immediately after allocation. If deselected, the application generates the LPN level picks with a held status. |
| UOMs Marked for Immediate Release | Indicates that the unit of measure (UOM) is to be released immediately after allocation. If deselected, the application generates the UOM level picks with a held status. If you select a UOM for immediate release, you must also select the related load level for immediate release. For example, if you select the Pallet UOM for immediate release, you need to also select the Load Pick check box in order for the application to immediately release pallet picks. |
| Allow Bulk Pick Processing | If Yes, the selected work orders will be allocated using bulk pick processing. Bulk pick processing allocates matching inventory for multiple work order lines together into larger unit of measure (UOM) bulk picks so as to reduce the number of smaller UOM picks required to satisfy the work orders. If set to Yes, the application groups work order detail line quantities from multiple work orders into larger bulk pick UOM quantities. The work order type to which the selected work orders are associated must be enabled for bulk picking, and the work order line UOMs must also be enabled for bulk picking in order for the application to use bulk pick processing when allocating the work orders.<br > If No, the inventory required for each work order detail line is picked separately. |

### Copy Work Order fields

 
| Field | Description |
| --- | --- |
| Work Order | Identifier for a work order. A work order is an internal order used to find, allocate, and deliver product to a work-in-process area for assembly or disassembly, conversion, kitting, or repackaging. |
| Work Order Revision | Identifier for one instance of a work order that allows you to use a standard work order multiple times. |
| Work Order Client | Unique identifier for a client who is responsible for creating the work order and is not necessarily the client that houses the top-level item specified in the work order. Only displayed in a 3PL environment. |

### Return to Stock or Receive fields

 
| Field | Description |
| --- | --- |
| LPN | Unique identifier for inventory. Typically, an LPN refers to a pallet; however, it can refer to inventory received at less than pallet quantity. The LPN is the license plate by which the inventory is tracked in the facility. |
| Item | Top-level item or component item that you want to return to stock or receive. |
| Item Client | Name of the client who stores this item in the facility. This field is only displayed in a 3PL environment. |
| Description | Text that further describes the item. |
| Quantity | Quantity of the item in the unit of measure (UOM) that you want to return to stock or receive. |
| Inventory Status | Value that defines the quality or disposition of the inventory. |
| Footprint | Name that identifies a footprint, which describes the packaging dimensions and units of measure for the item with which it is associated. |
| Handling Unit Type | Category that classifies a group of handling units (for example, pallets, totes, transport equipment, or vehicles) that share the same characteristics such as size and weight, as well as whether they are serialized, temporary, or considered a container. The application tracks the on-hand quantity of handling units by type and, for serialized handling units, by handling unit identifier. |
| Wrap | LPN-level packaging attribute for inventory. LPN packaging attributes are user-defined fields that are used to indicate requirements such as pallet wrapping, use of a slip sheet, and the application of labels on all four sides of a pallet of inventory. |
| Double Wrap | LPN-level packaging attribute for inventory. LPN packaging attributes are user-defined fields that are used to indicate requirements such as pallet wrapping, use of a slip sheet, and the application of labels on all four sides of a pallet of inventory. |
| Label 4 Sides | LPN-level packaging attribute for inventory. LPN packaging attributes are user-defined fields that are used to indicate requirements such as pallet wrapping, use of a slip sheet, and the application of labels on all four sides of a pallet of inventory. |
| Slip Sheet | LPN-level packaging attribute for inventory. LPN packaging attributes are user-defined fields that are used to indicate requirements such as pallet wrapping, use of a slip sheet, and the application of labels on all four sides of a pallet of inventory. |

### Complete Work Order Page fields

 
| Field | Description |
| --- | --- |
| Work Order Line | Unique number that identifies the work order line. A work order line describes a component item and its attributes that is to be built into the top-level item or that will result from disassembling the top-level item defined by the work order. |
| Work Order | Identifier for a work order. A work order is an internal order used to find, allocate, and deliver product to a work-in-process area for assembly or disassembly, conversion, kitting, or repackaging. |
| Item | Top-level item (finished good) to be built using component items or to be disassembled into component items as specified by the work order. |
| Line Quantity | Component quantity to be delivered (for assembly work orders) or produced (for disassembly work orders). For example, if the work order requests 10 top-level items and it takes 4 units of this component item to build one top-level item, then the value in this field would be 40. |
| Reported Scrapped Quantity | Total number of the component item that is reported as being scrapped. Typically, these component items are damaged and are not returned to stock. |
| Returned Quantity | Total quantity of the component item (for assembly work orders), or top-level items (for disassembly work orders) that was returned to stock. This field is display only. |
| Reported Consumed Quantity | Total number of the component item that was manually reported as consumed. Because this value is based on user input, it may differ from the application value. For example, if 40 units of a component item are delivered to the production line, but 2 were damaged and replaced, then the reported consumed quantity (42) would not match the quantity recorded by the application (40). |
| Reported WIP Quantity | Total quantity of the component item that was reported as being moved to the work-in-process (WIP) supply location. For example, if one roll of paper is delivered from a WIP supply location to the production line to wrap 100 gift baskets, and 20% (.2) of the roll is used to wrap the gift baskets, 80% (.8) of the roll would be reported as being returned to the WIP supply location.<br > The WIP quantity is auto calculated based on the BOM quantity, and is editable, only if the respective item is a WIP item that has not been allocated.<br > You can close a work order without balancing WIP component items. For example, the quantity used at the production line and the quantity returned to the WIP supply location does not need to equal 100%. |
| BOM Quantity | Quantity (in terms of material handling or stock keeping units) of the component item required to assemble one top-level item. This is the quantity of the component item that will be consumed when assembling the top-level item. If a BOM is defined for the top-level item, then this value can be populated by the BOM. |
| Pick Quantity | Quantity (in terms of material handling or stock keeping units) of the item that is picked based on the order, work order, or replenishment. |
| Total Delivered Quantity | Total quantity of the top-level or component item that has been delivered to the production line. |
| In Process Quantity | Quantity of allocated component inventory that has been delivered to the production line. |
| Total Consumed Quantity | Total quantity of the top-level item that has been consumed as tracked by the application for disassembly work orders. |
| Cross Dock | Indicates that when the inventory specified on the outbound order or work order line is identified, it is moved directly from its receiving point to a cross dock area or a specified staging location to satisfy an outbound order or work order. |
| Over Allocation Amount | Total amount of inventory that is allocated over the requested quantity when the allocation code is **Quantity**, or percentage of inventory that can be allocated when the allocation code is **Percentage**. If the over-allocation code is **Percentage**, then the over-allocation amount should be a value from 1 to 100 that indicates the percentage of the order quantity that can be over-allocated. If the over-allocation code is **Quantity**, then the over-allocation amount should be a value that represents the number that can be over-allocated. |
| Over-Alloc In-Process Qty | Quantity of over-allocated items that was delivered to the production line. |
| Expected Scrap (%) | Value that determines the minimum and maximum percentage of the BOM quantity (specified in the **BOM Quantity** field) for the component item that the application will allow being scrapped (not reusable). For example, if you enter a scrap percentage of 50, then you can scrap anywhere from 50% to 150% of the specified BOM quantity when disassembling the top-level item. |
| Consumption Tolerance (%) | Value that determines the minimum and maximum percentage of the BOM quantity (specified in the **BOM Quantity** field) for the component item that the application will allow. For example, if you enter a Consumption Tolerance Percentage of 10, then you can consume anywhere from 90% to 110% of the specified consumed quantity when assembling the top-level item. |
| Display Line Quantity | Total number of component level items in terms of the display unit of measure (UOM) to be delivered to the production line to build all of the work order's top level items. For example, if the top-level item is packaged 10 eaches to a case, the value in the **Line Quantity** field is 240, and the display UOM is cases, then the **Display Line Quantity** field displays "24 CS 0 EA." |
| Line Catch Quantity | Total catch unit amount of the component item to be delivered to the production line to build the expected quantity of the work order's top-level items. For example, if the work order requests 10 top-level items and it takes 4 pounds of this component item to build one top-level item, then the value in this field would be 40. Only available for assembly work orders. |
| BOM Catch Quantity | Catch unit amount of the component item required to assemble one top-level item. This is the catch unit quantity of the component item that will be consumed when assembling the top-level item. |
| Pick Catch Quantity | Catch unit quantity of the component item that has not yet been allocated for the work order. When you first create the work order, this value matches the value entered in the **Line Catch Quantity** field. As the component item is successfully allocated, this quantity will decrease to zero. If you later determine that you need more of the component than originally planned, enter the additional quantity in this field. You can then reallocate the work order line for the additional quantity. Only available for assembly work orders. |
| Round Pick Quantity | Indicates that allocation automatically rounds up the pick quantity to the next highest UOM. The pick quantity may be rounded up only within the bounds defined by the values specified for **Over Allocation Amount** and **Over Allocation Code**. This option is beneficial, for example, in situations where it is easier to pick an entire case or pallet of an item than to break a unit of measure (UOM) to complete a pick. |
| Display Quantity | Quantity of the item in terms of the display UOM that is picked based on the order, work order, or replenishment. |
| Disassembly Quantity | Quantity (in terms of material handling or stock keeping units) of the component item that has been produced from disassembling the top-level item for the work order. Only available for disassembly work orders. |
| Disassembly Catch Quantity | Catch quantity of the component item that has been produced from disassembling the top-level item for the work order. |
| Inventory Status | Defines the quality or disposition of the inventory. This is the default inventory status that is displayed when an operator identifies completed top-level items for the work order. However, the operator may change the status. Only available for assembly work orders. |
| Delivered Inventory Status | Defines the quality status assigned to the component item when it is delivered to the production line. This status is used to determine whether the inventory status of the component inventory has changed during production. Only available for assembly work orders. |
| Inventory Status Progression | Inventory status progression of the allocated component items. An inventory status progression is a series of inventory statuses that define the levels of quality at which a customer is willing to accept a product. When an inventory status progression is specified on an order, then the application can select product to satisfy that order based on a prioritized list of acceptable inventory statuses rather than a single status. This functionality lets customers define a wider range of acceptable inventory as well as specify their preference on the quality of the inventory that they are willing to accept. |
| Lot | Identifier to assign to top-level items built for the work order. A lot is an identifier assigned to a quantity of product that is uniquely identified during the manufacturing process for the purpose of tracking an attribute of that product, such as expiration date. Only available for assembly work orders and if the top-level item requires this attribute. |
| Supplier Lot | Supplier lot identifier to assign to top-level items built for the work order. A supplier lot is a unique identifier that is assigned to a quantity of product during the manufacturing process that identifies the lot of the product as specified by the supplier. Only available for assembly work orders and if the top-level item requires this attribute. |
| Origin Code | Origin code to assign to top-level items built for the work order. An origin code is a unique identifier that is assigned to an item to identify the item's place of origin. Typically used for export paperwork. Origin codes are user defined. Only available for assembly work orders and if the top-level item requires this attribute. |
| Supplier | Identifier for a supplier. A supplier can be an individual, organization, or another warehouse within your own organization from which you repeatedly receive inventory or handling units. |
| Manufactured Date | Date on which the item identified on this line was manufactured. The date is stored in the database and displayed in the web client in the original captured time zone, not converted to a different time zone, such as a user preferred time zone. |
| Expiration Date | Date and time that the inventory will expire. This field defaults to the date calculated by the application based on the manufactured date and aging profile name of the item. The date and time are stored in the database and displayed in the web client in the original captured time zone, not converted to a different time zone, such as a user preferred time zone. |
| Minimum Shelf Life (Hours) | Minimum number of hours away from expiration that a date-tracked item must be considered for allocation. For example, if this value is 10, then the application only allocates inventory that has at least 10 hours to reach its expiration date. Only available if the item specified on the order line is date-tracked. |
| Production Station | Production station to which the component inventory defined on the work order line is to be delivered. This value can be populated from a BOM line. A production station is a position on a production line where a specific operation is performed during the production of a top-level item (finished good). |
| Old Production Station | Production station from which the component inventory defined as part of Move inventory operation is to be delivered to the new production station. A production station is a position on a production line where a specific operation is performed during the production of a top-level item (finished good). |
| Processing Status | Processing status of the work order.<br>-   • **Pending**: The component (assembly) or top-level (disassembly) inventory for the work order or work order line has not yet been allocated.
<br>-   • **Waiting**: The component (assembly) or top-level (disassembly) inventory has been allocated for the work order or work order line resulting in replenishments, but all of the replenishments have not yet been filled.
<br>-   • **Undelivered**: The component (assembly) or top-level (disassembly) inventory has been allocated for the work order or work order line resulting in pick work, but none of the component (assembly) or top-level (disassembly) inventory has been delivered to the processing location yet.
<br>-   • **Partially Delivered**: Some of the component (assembly) or top-level (disassembly) inventory has been delivered to the processing location (such as, a production station for a work order line), but there is either not enough of the component inventory to build a top-level item for an assembly work order; or, for assembly and disassembly, the work order was stopped in the middle of production.
<br>-   • **Delivered**: All of the required component (assembly) or top-level (disassembly) items specified in the work order or work order line have been delivered to the processing location, but the work order has not yet been started.
<br>-   • **Ready**: For a work order, the work order has been started and (for assembly) enough component inventory has arrived at the processing location to build at least one top-level item or at least one top-level item has been delivered to the production line for break down. For a work order line, the work order has been started and enough of the component inventory specified by the work order line has arrived to be used in making at least one top-level item.
<br>-   • **Completed**: For a work order, all of the top-level items for the work order have been built and identified, or all component items have been identified from the broken down top-level items. For a work order line, all of the component inventory specified in the work order line has been consumed.
<br>-   • **Closed**: The work order has been closed. |
| Units Per Pack | Default number of units (pieces) per inner pack supplied for the order line or work order line. |
| Units per Case | Default number of units (pieces) per case supplied for the order line or work order line. |
| Sub Work Order Number | Identifier for a nested work order. |
| Sub Work Order Revision | Unique identifier for the instance of the sub-work order, which enables you to use a standard sub-work order multiple times. |
| Allocate by Catch Quantity | Indicates that the application will allocate the component inventory based on catch unit quantity instead of material handling (stock keeping) quantity. |
| Footprint | Name that identifies a footprint, which describes the packaging dimensions and units of measure for the item with which it is associated. |
| Inventory Rotation Method | Value that represents the order in which the allocation process selects available inventory for allocation. Select an inventory rotation method if you want the application to search for inventory based on date processing or location.<br>-   • **FEFO-ORDER-BY and FEFO-ORDER-BY-ABSOLUTE**: First-expiration, first-out. The first inventory to expire will be selected first.
<br>-   • **FIFO-ORDER-BY and FIFO-ORDER-BY-ABSOLUTE**: First-in, first-out. The oldest inventory will be selected first.
<br>-   • **LEFO-ORDER-BY and LEFO-ORDER-BY-ABSOLUTE**: Last-expiration, first-out. The last inventory to expire will be selected first.
<br>-   • **LIFO-ORDER-BY and LIFO-ORDER-BY-ABSOLUTE**: Last-in, first-out. The newest inventory will be selected first.
<br>-   • **LOCATION-ORDER-BY**: Locations are ordered within a pick zone (maintaining the allocation search path order) by the location attributes specified for the **Location Sort** field in inventory selection settings.
<br>-   •
    
    **No selection (blank)**: The application uses the inventory rotation method of the highest defined level of precedence. For information on precedence, see [Inventory rotation allocation processing](../../configuration/outbound/allocation/inventory-rotation-allocation.md).
    
    <br>
    
    **Note**: Inventory rotation methods defined at a lower precedence (except the default method) are automatically copied to the order line or work order line when the line is created. For example, if an order line is created for a date-tracked item with a rotation method defined, the rotation method is copied from the item to the order line, and then the application uses the order line rotation method during allocation.
    
    <br > If no inventory rotation method is defined at any level, then the application uses the allocation search path sequence and allocates the first available inventory it finds that matches all of the required attributes.
<br > When using inventory rotation methods that are not absolute, the application searches for inventory by allocation search path in sequence until it finds a pick zone that contains the inventory, and then allocates inventory that is closest to the preferred processing date. Therefore, the application stops searching at the first pick zone in which matching inventory is found.<br > When using absolute inventory rotation methods, the application searches either all of the allocation search paths for inventory that is closest to the preferred processing date or, if absolute groups are defined, each absolute group in sequence until it finds matching inventory and then allocates inventory that is closest to the preferred processing date from the pick zones within the absolute group. Therefore, the absolute method allows for more a comprehensive search to find the inventory. |
| Date Window | Amount of time in relation to the inventory’s received date or expiration date during which inventory is considered the same age for allocation when one of the FEFO/FIFO/LEFO/LIFO or absolute FEFO/FIFO/LEFO/LIFO inventory rotation methods is required. |
| Date Window Unit | Unit of time (minutes, hours, or days) for the outbound date window. |
| Date Last Modified | Date and time indicating when the work order line was last modified. |
| Last Modified By | Username of the last person who modified the work order line. |
| Remainder Display Line Quantity | Quantity of the item identified against the line quantity that is less than the display UOM. For example, if the total identified line quantity is 10 cases and 5 eaches, and the display UOM is Case, then the remainder quantity would be 5 Eaches. |
| Remainder Display Pick Quantity | Quantity of the item identified against the pick quantity that is less than the display UOM. For example, if the total identified pick quantity is 10 cases and 5 eaches, and the display UOM is Case, then the remainder quantity would be 5 Eaches. |

### Work Order details: Summary fields

 
| Field | Description |
| --- | --- |
| Work Order Client | Unique identifier for a client who is responsible for creating the work order and is not necessarily the client that houses the top-level item specified in the work order. Only displayed in a 3PL environment. |
| Revision | Unique identifier for this instance of the work order, which enables you to use a standard work order multiple times. |
| Added Workflow | If Yes, a workflow has been added to the work order. If No, a workflow has not been added to the work order. |
| Processing Area | Area in your facility in which production lines are located. |
| No Components | If Yes, the work order does not need work order details (lines), does not need component inventory allocation, does not need the application to direct an operator to pick component inventory from a storage location to a production line, and does not need to track the component inventory. The only operations associated with this type of work order are to identify the top-level items and put them away. Work orders without components are especially useful for facilities that do not track their component inventory in the application.<br > If No, the work order needs work order details (lines), component inventory allocation, needs the application to direct an operator to pick component inventory from a storage location to a production line, and needs to track the component inventory.<br > Only available for assembly work orders. |
| Exclusively Occupy Production Line | If **Yes**, the work order or BOM is to exclusively occupy a production line (the work order is not to be processed at the same time as other work orders on the same production line). This means that the work order must be started either on an exclusive production line (**Exclusive Work Order** is configured for the production line) or on a non-exclusive production line that has no other work orders started on it.<br > If **No**, another work order or BOM can be started at the same time on the same production line as this work order. Only available as selection criteria or if a schedule-based production line is selected from the **Production Line** drop-down list. |
| Automatically Release Pick | If Yes, the application is to automatically release the pick work for the component items for a work order in advance of the work order's scheduled start time (Scheduled Begin Date). The amount of time in advance of the scheduled start date is defined by the value for **Release Pick Time**.<br > If No, the application does not release the pick work automatically for the component items for the work order. |
| Release Pick Time | Number of minutes in advance of a work order's scheduled start time that the application is to release picks for the work order. |
| Duration Time | Amount of time, in minutes, to complete the work order. The duration time is either downloaded from the host application or is specified manually by a user, and is typically based on historical production information. |
| Production Quantity | Total number of top-level items that have been assembled for this work order. |
| In Process Quantity | Quantity of allocated items that must be delivered to the production line for the work order. |
| Over-Alloc In-Process Qty | Quantity of over-allocated items that must be delivered to the production line for disassembly work orders. |
| Pick Quantity | Quantity (in terms of material handling or stock keeping units) of the item that should be picked based on the order, work order, or replenishment. |
| Total Consumed Quantity | Total quantity of the top-level items or component items that have been consumed as tracked by the application. |
| Total Delivered Quantity | Total quantity of the top-level or component item that has been delivered to the production line. |
| Type | Identifier that defines the type of customs tracking required for the inventory on the work order. Defining a customs type on the planned inbound order overrides the customs type defined for the items on the work order. Only displayed if Customs functionality is enabled.<br>-   • **Customs**: Customs duties need to be paid for the items on the work order. Available if the address for the warehouse is designated as a Customs site type.
<br>-   • **Excise**: Excise duties need to be paid for the items on the work order; customs duties may also be required. Available if the address for the warehouse is designated as a Customs and Excise site type.
<br>-   • **Free**: Customs duties or excise duties need not be paid. |
| VAT Code | Code for the value added tax (VAT) for the item. A customs VAT is charged on goods and some services that are imported from countries outside the European Unit (EU) and brought into the United Kingdom (UK) from other EU countries. It is also charged on most goods and services that VAT-registered businesses provide in the UK.<br>-   • **Standard**: The standard customs VAT rate is charged for this item.
<br>-   • **Zero**: No customs VAT is charged for this item. |
| Consignment | Unique identifier assigned to a receipt of bonded inventory. A customs consignment is an application-generated ID number that consists of a prefix (the warehouse ID) plus the next value in the customs consignment ID sequence. For example, if your warehouse ID is WMD1 and the next number in the sequence is 123456, then the customs consignment ID will be WMD1123456.<br > Only displayed if Customs functionality is enabled for the warehouse and the item is configured for customs tracking. |
| Commodity Code | Code that identifies a commodity. Commodities are categories created to group inventory that has the same qualities and specifications, regardless of their source. For example, wheat is a commodity. Commodity codes are standardized to provide carriers with a standard by which to determine pricing and to simplify the shipment process. The Commodity Code is usually printed on the bill of lading (BOL). If the commodity is printed on the BOL, all products of the same commodity are totaled. |
| Default Origin Code | Country in which the item was manufactured. This value is displayed by default on the planned inbound order line for the item but during receiving it can be changed. Only applies to items for which customs or excise duties need to be paid. |
| Duty Stamp Tracked | If Yes, the item is duty stamp tracked. If No, the item is not duty stamp tracked.<br > Only applies to items for which excise duties need to be paid. |
| Customs Cost | Monetary amount that is paid to customs for the item. Only applies to items for which customs or excise duties need to be paid. |

### Work Order details: Order Lines fields

 
| Field | Description |
| --- | --- |
| Work Order | Identifier for a work order. A work order is an internal order used to find, allocate, and deliver product to a work-in-process area for assembly or disassembly, conversion, kitting, or repackaging. |
| Work Order Line | Unique number that identifies the work order line. A work order line describes a component item and its attributes that is to be built into the top-level item or that will result from disassembling the top-level item defined by the work order. |
| Item | Component item used to assemble a top-level item or that will result from disassembling the top-level item as specified in the work order. |
| Line Quantity | Total quantity of the component item (in terms of material handling or stock keeping units) to be delivered to the production line to build all of the work order's top-level items. For example, if the work order requests 10 top-level items and it takes 4 units of this component item to build one top-level item, then the value in this field would be 40. Only available for assembly work orders. |
| BOM Quantity | Quantity (in terms of material handling or stock keeping units) of the component item required to assemble one top-level item. This is the quantity of the component item that will be consumed when assembling the top-level item. If a BOM is defined for the top-level item, then this value can be populated by the BOM. |
| Pick Quantity | Quantity (in terms of material handling or stock keeping units) of the item that is picked based on the order, work order, or replenishment. |
| Total Delivered Quantity | Total quantity of the top-level or component item that has been delivered to the production line. |
| In Process Quantity | Quantity of allocated component inventory that has been delivered to the production line. |
| Total Consumed Quantity | Total quantity of the component item that has been consumed as tracked by the application. |
| Reported Scrapped Quantity | Total number of the component item that is reported as being scrapped. Typically, these component items are damaged and are not returned to stock. |
| Returned Quantity | Total quantity of the component item (for assembly work orders), or top-level items (for disassembly work orders) that was returned to stock. This field is display only. |
| Cross Dock | Indicates that when the inventory specified on the outbound order or work order line is identified, it is moved directly from its receiving point to a cross dock area or a specified staging location to satisfy an outbound order or work order. |
| Over-Alloc In-Process Qty | Quantity of over-allocated component items that must be delivered to the production line. |
| Expected Scrap (%) | Value that determines the minimum and maximum percentage of the BOM quantity (specified in the **BOM Quantity** field) for the component item that the application will allow being scrapped (not reusable). For example, if you enter a scrap percentage of 50, then you can scrap anywhere from 50% to 150% of the specified BOM quantity when disassembling the top-level item. |
| Consumption Tolerance (%) | Value that determines the minimum and maximum percentage of the BOM quantity (specified in the **BOM Quantity** field) for the component item that the application will allow. For example, if you enter a Consumption Tolerance Percentage of 10, then you can consume anywhere from 90% to 110% of the specified consumed quantity when assembling the top-level item. |
| Reported Consumed Quantity | Total number of the component item that was manually reported as consumed. Because this value is based on user input, it may differ from the application value. For example, if 40 units of a component item are delivered to the production line, but 2 were damaged and replaced, then the reported consumed quantity (42) would not match the quantity recorded by the application (40). |
| Reported WIP Quantity | Total quantity of the component item that was reported as being moved to the work-in-process (WIP) supply location. For example, if one roll of paper is delivered from a WIP supply location to the production line to wrap 100 gift baskets, and 20% (.2) of the roll is used to wrap the gift baskets, 80% (.8) of the roll would be reported as being returned to the WIP supply location.<br > The WIP quantity is auto calculated based on the BOM quantity, and is editable, only if the respective item is a WIP item that has not been allocated.<br > You can close a work order without balancing WIP component items. For example, the quantity used at the production line and the quantity returned to the WIP supply location does not need to equal 100%. |
| Display Line Quantity | Total number of component level items in terms of the display unit of measure (UOM) to be delivered to the production line to build all of the work order's top level items. For example, if the top-level item is packaged 10 eaches to a case, the value in the **Line Quantity** field is 240, and the display UOM is cases, then the **Display Line Quantity** field displays "24 CS 0 EA." |
| Line Catch Quantity | Total catch unit amount of the component item to be delivered to the production line to build the expected quantity of the work order's top-level items. For example, if the work order requests 10 top-level items and it takes 4 pounds of this component item to build one top-level item, then the value in this field would be 40. Only available for assembly work orders and if the **Allocate by Catch Quantity** check box is selected. |
| BOM Catch Quantity | Catch unit amount of the component item required to assemble one top-level item. This is the catch unit quantity of the component item that will be consumed when assembling the top-level item. Only available if the **Allocate by Catch Quantity** check box is deselected. |
| Pick Catch Quantity | Catch unit quantity of the component item that has not yet been allocated for the work order. When you first create the work order, this value matches the value entered in the **Line Catch Quantity** field. As the component item is successfully allocated, this quantity will decrease to zero. If you later determine that you need more of the component than originally planned, enter the additional quantity in this field. You can then reallocate the work order line for the additional quantity. Only available for assembly work orders. |
| Round Pick Quantity | Indicates whether the allocation is to automatically round up the pick quantity to the next highest UOM. This option is beneficial, for example, in situations where it is easier to pick an entire case or pallet of an item than to break a unit of measure (UOM) to complete a pick. A check mark is displayed in this field if the allocation automatically rounds up the pick quantity to the next highest UOM. |
| Inventory Status | Defines the quality or disposition of the inventory. This is the default inventory status that is displayed when an operator identifies completed top-level items or disassembled component items for the work order. However, the operator may change the status. |
| Delivered Inventory Status | Defines the quality status assigned to the component item when it is delivered to the production line. This status is used to determine whether the inventory status of the component inventory has changed during production. Only available for assembly work orders. |
| Inventory Status Progression | Inventory status progression of the allocated component items. An inventory status progression is a series of inventory statuses that define the levels of quality at which a customer is willing to accept a product. When an inventory status progression is specified on an order, then the application can select product to satisfy that order based on a prioritized list of acceptable inventory statuses rather than a single status. This functionality lets customers define a wider range of acceptable inventory as well as specify their preference on the quality of the inventory that they are willing to accept. |
| Lot | Lot number that allocated component items must have. If any lot is acceptable, leave this field blank. A lot is an identifier assigned to a quantity of product that is uniquely identified during the manufacturing process for the purpose of tracking an attribute of that product, such as expiration date. Lots differentiate distinct groups of inventory with the same item number. Only available if the component item requires this attribute. |
| Supplier Lot | Supplier lot number that allocated component items must have. If any supplier lot is acceptable, leave this field blank. A supplier lot is a unique identifier that is assigned to a quantity of product during the manufacturing process that identifies the lot of the product as specified by the supplier. Only available if the component item requires this attribute. |
| Origin Code | Identifier assigned to an item to identify the item's country of origin. It is typically used for export paperwork. Origin codes are user defined. |
| Supplier | Identifier for a supplier. A supplier can be an individual, organization, or another warehouse within your own organization from which you repeatedly receive inventory or handling units. |
| Manufactured Date | Date on which the item identified on this line was manufactured. The date is stored in the database and displayed in the web client in the original captured time zone, not converted to a different time zone, such as a user preferred time zone. If left blank, this date defaults to the date the inventory was identified, or received. This date is the basis of application date calculations for date-controlled items. Typically, this date is used for first in, first out (FIFO) order processing. Only available if the item is date controlled. |
| Expiration Date | Date and time that the inventory will expire. This field defaults to the date calculated by the application based on the manufactured date and aging profile name of the item. The date and time are stored in the database and displayed in the web client in the original captured time zone, not converted to a different time zone, such as a user preferred time zone. |
| Minimum Shelf Life (Hours) | Minimum number of hours away from expiration that a date-tracked item must be considered for allocation. For example, if this value is 10, then the application only allocates inventory that has at least 10 hours to reach its expiration date. Only available if the item specified on the order line is date-tracked. |
| Production Station | Production station to which the component inventory defined on the work order line is to be delivered. This value can be populated from a BOM line. A production station is a position on a production line where a specific operation is performed during the production of a top-level item (finished good). |
| Old Production Station | Production station from which the component inventory defined as part of Move inventory operation is to be delivered to the new production station. A production station is a position on a production line where a specific operation is performed during the production of a top-level item (finished good). |
| Processing Status | Processing status of the work order.<br>-   • **Pending**: The component (assembly) or top-level (disassembly) inventory for the work order or work order line has not yet been allocated.
<br>-   • **Waiting**: The component (assembly) or top-level (disassembly) inventory has been allocated for the work order or work order line resulting in replenishments, but all of the replenishments have not yet been filled.
<br>-   • **Undelivered**: The component (assembly) or top-level (disassembly) inventory has been allocated for the work order or work order line resulting in pick work, but none of the component (assembly) or top-level (disassembly) inventory has been delivered to the processing location yet.
<br>-   • **Partially Delivered**: Some of the component (assembly) or top-level (disassembly) inventory has been delivered to the processing location (such as, a production station for a work order line), but there is either not enough of the component inventory to build a top-level item for an assembly work order; or, for assembly and disassembly, the work order was stopped in the middle of production.
<br>-   • **Delivered**: All of the required component (assembly) or top-level (disassembly) items specified in the work order or work order line have been delivered to the processing location, but the work order has not yet been started.
<br>-   • **Ready**: For a work order, the work order has been started and (for assembly) enough component inventory has arrived at the processing location to build at least one top-level item or at least one top-level item has been delivered to the production line for break down. For a work order line, the work order has been started and enough of the component inventory specified by the work order line has arrived to be used in making at least one top-level item.
<br>-   • **Completed**: For a work order, all of the top-level items for the work order have been built and identified, or all component items have been identified from the broken down top-level items. For a work order line, all of the component inventory specified in the work order line has been consumed.
<br>-   • **Closed**: The work order has been closed. |
| Units Per Pack | Default number of units (pieces) per inner pack supplied for the order line or work order line. |
| Units per Case | Default number of units (pieces) per case supplied for the order line or work order line. |
| Sub Work Order Number | Identifier for a nested work order. |
| Sub Work Order Revision | Unique identifier for the instance of the sub-work order, which enables you to use a standard sub-work order multiple times. |
| Allocate by Catch Quantity | Indicates that the application will allocate the component inventory based on catch unit quantity instead of material handling (stock keeping) quantity. For example, select this check box to allocate a liquid component item based on number of gallons instead of based on number of drums. Only available if the component item entered in the **Item** field requires catch units. |
| Footprint | Name that identifies a footprint, which describes the packaging dimensions and units of measure for the item with which it is associated. |
| Inventory Rotation Method | Value that represents the order in which the allocation process selects available inventory for allocation. Select an inventory rotation method if you want the application to search for inventory based on date processing or location.<br>-   • **FEFO-ORDER-BY and FEFO-ORDER-BY-ABSOLUTE**: First-expiration, first-out. The first inventory to expire will be selected first.
<br>-   • **FIFO-ORDER-BY and FIFO-ORDER-BY-ABSOLUTE**: First-in, first-out. The oldest inventory will be selected first.
<br>-   • **LEFO-ORDER-BY and LEFO-ORDER-BY-ABSOLUTE**: Last-expiration, first-out. The last inventory to expire will be selected first.
<br>-   • **LIFO-ORDER-BY and LIFO-ORDER-BY-ABSOLUTE**: Last-in, first-out. The newest inventory will be selected first.
<br>-   • **LOCATION-ORDER-BY**: Locations are ordered within a pick zone (maintaining the allocation search path order) by the location attributes specified for the **Location Sort** field in inventory selection settings.
<br>-   •
    
    **No selection (blank)**: The application uses the inventory rotation method of the highest defined level of precedence. For information on precedence, see [Inventory rotation allocation processing](../../configuration/outbound/allocation/inventory-rotation-allocation.md).
    
    <br>
    
    **Note**: Inventory rotation methods defined at a lower precedence (except the default method) are automatically copied to the order line or work order line when the line is created. For example, if an order line is created for a date-tracked item with a rotation method defined, the rotation method is copied from the item to the order line, and then the application uses the order line rotation method during allocation.
    
    <br > If no inventory rotation method is defined at any level, then the application uses the allocation search path sequence and allocates the first available inventory it finds that matches all of the required attributes.
<br > When using inventory rotation methods that are not absolute, the application searches for inventory by allocation search path in sequence until it finds a pick zone that contains the inventory, and then allocates inventory that is closest to the preferred processing date. Therefore, the application stops searching at the first pick zone in which matching inventory is found.<br > When using absolute inventory rotation methods, the application searches either all of the allocation search paths for inventory that is closest to the preferred processing date or, if absolute groups are defined, each absolute group in sequence until it finds matching inventory and then allocates inventory that is closest to the preferred processing date from the pick zones within the absolute group. Therefore, the absolute method allows for more a comprehensive search to find the inventory. |
| Date Window | Amount of time in relation to the inventory’s received date or expiration date during which inventory is considered the same age for allocation when one of the FEFO/FIFO/LEFO/LIFO or absolute FEFO/FIFO/LEFO/LIFO inventory rotation methods is required. |
| Date Window Unit | Unit of time (minutes, hours, or days) for the outbound date window. |
| Date Last Modified | Date and time indicating when the work order line was last modified. |
| Last Modified By | Username of the last person who modified the work order line. |
| Remainder Display Line Quantity | Quantity of the item identified against the line quantity that is less than the display UOM. For example, if the total identified line quantity is 10 cases and 5 eaches, and the display UOM is Case, then the remainder quantity would be 5 Eaches. |
| Remainder Display Pick Quantity | Quantity of the item identified against the pick quantity that is less than the display UOM. For example, if the total identified pick quantity is 10 cases and 5 eaches, and the display UOM is Case, then the remainder quantity would be 5 Eaches. |
| Display Pick Quantity | Quantity of the item in terms of the display UOM that is picked based on the order, work order, or replenishment. |
| Over Allocation Amount | Total amount of inventory that is allocated over the requested quantity when the allocation code is **Quantity**, or percentage of inventory that can be allocated when the allocation code is **Percentage**. If the over-allocation code is **Percentage**, then the over-allocation amount should be a value from 1 to 100 that indicates the percentage of the order quantity that can be over-allocated. If the over-allocation code is **Quantity**, then the over-allocation amount should be a value that represents the number that can be over-allocated. |
| Disassembly Quantity | Quantity (in terms of material handling or stock keeping units) of the component item that has been produced from disassembling the top-level item for the work order. Only available for disassembly work orders. |
| Disassembly Catch Quantity | Catch quantity of the component item that has been produced from disassembling the top-level item for the work order. |

### Work Order details: Picks fields

 
| Field | Description |
| --- | --- |
| Pick Status | Current status of the pick.<br>-   • **Pending**: Pick work inventory is reserved for allocation until automatically released by the application.
<br>-   • **Hold**: Pick work inventory is reserved for allocation until manually released by a user.
<br>-   • **Released**: Pick work is released to the work queue.
<br>-   • **Complete**: Pick work is complete.
<br>-   • **Un-Assigned**: Pick work is unassigned from a work assignment.
<br>-   • **Ready For List**: Pick work has been released and the pick is qualified for a work assignment. A background process builds these picks into either a handling unit-based or regular work assignment.
<br>-   • **Error**: Pre-manifesting the package for the pick work failed. The application allows packages to be pre-manifested; that is, manifested to hold. These packages are typically manifested during allocation (before the inventory is picked) and usually so that a label can be printed in advance for the package. You can view the specific error code and description on the Waves and Picks page. See [Waves and Picks](../../shared-functions/waves-and-picks.md). |
| Operation | Work operation that identifies the type of directed work that was created. |
| Work Assignment Status | Processing status of the work assignment.<br>-   • **Pending**: The assignment has not been released for picking.
<br>-   • **Released**: The assignment has been released for picking but has not been started.
<br>-   • **Picking In Process**: An operator has acknowledged (signed on to) the assignment.
<br>-   • **Complete**: Picking for the assignment is complete. |
| Source | Location where the work originated, such as the location from which inventory is picked, at which a count is performed, or from which transport equipment is moved. |
| Destination | Location where the work is completed, such as the location to which inventory is delivered or to which transport equipment is moved. |
| Load | Unique identifier for a load. A load is one or more shipments grouped together into one or more stops that are shipped on a single piece of transport equipment. |
| Shipment | Unique identifier for an outbound shipment. A shipment is a group of orders or order lines that are allocated together and shipped to the same location. |
| Order | Unique number that identifies an order. An order is a request for a supply of material or product. |
| Item | The allocated item that must be picked for assembly or disassembly as specified in the work order. |
| Description | Text that further describes the item. |
| User | User who picked the inventory. |
| Pick Priority | Current priority of directed work in the work queue. This value represents the base priority defined for the operation plus any escalation increments that have been applied over time to the work request. For example, if the base priority of work is 20 and it is defined to escalate by 5 every hour, then after 2 hours it has an effective (current) priority of 10. The value for Priority is green if the value has been escalated from the base priority defined for the work operation.<br > The lowest number has the highest priority. For example, 1 is the highest priority; 10 is a higher priority than 20. |
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
| Work Order Line | Unique number that identifies the work order line. A work order line describes a component item and its attributes that is to be built into the top-level item or that will result from disassembling the top-level item defined by the work order. |
| Work Order Revision | Identifier for one instance of a work order that allows you to use a standard work order multiple times. |
| Picked Catch Quantity | Quantity (in terms of material handling or stock keeping units) of inventory that is picked based on the catch unit measurements for the order, work order, or replenishment. |
| Order Line | Unique number that identifies the order line. The number corresponds to the line's position on the order. The first order line is automatically assigned a line number of 0001. Additional order lines are then automatically numbered sequentially, beginning with 0002. |
| Date Completed | Date and time when the picking operator completed picking inventory to fulfill the order. |
| Cartonization Error | Indicates that the dimensions or weight of the cartonized item exceeds the limits that are defined for the largest available carton enabled for picking cartonization and its repack class. Additionally, there could be an incorrect repack class assignment, or the weight and dimensions defined for an item footprint may not be correct. |
| Lot Tracked | Indicates whether the item is lot tracked (**Lot Tracking** field set to Yes in the item configuration). A lot is a batch (quantity) of an item uniquely identified by a lot number during the manufacturing process for the purpose of tracking that batch of inventory. |
| Origin Tracked | Indicates whether the item is tracked by its origin (**Origin Code** field set to Yes in the item configuration). The origin code is typically an identifier for the country or area of the world in which the item was manufactured. |
| Revision Tracked | Indicates whether the item is revision tracked (**Revision** field set to Yes in the item configuration). A revision may be used to identify a specific manufactured version of the item, so that when the item is modified or improved, the manufacturer may assign a new version number to reflect the change. |
| Estimated Goal Time | Goal time estimated by Warehouse Labor Management to complete this wave in seconds. This is only applicable if Warehouse Labor Management is integrated with Warehouse Management. |
| Carton Number | Unique identifier assigned to the carton into which inventory is picked. |
| Role | Role that is assigned to the work. A role is a category that is used to group menu options for the purpose of maintaining user authorizations. Roles are assigned to the appropriate users to control the tasks that users are authorized to perform. |
| Wave | Value that is assigned to the group of pick-type work requests (picks, replenishments, and cross docks) that are created when the wave is planned. The wave name distinguishes one group of pick-type work requests from another, which enables you to track the requests through the application. For example, if you allocate inventory for a single shipment, then all of the picks, replenishments, and cross docks generated for the shipment have the same wave name. |
| Handling Unit Type | Category that classifies a group of handling units (for example, pallets, totes, transport equipment, or vehicles) that share the same characteristics such as size and weight, as well as whether they are serialized, temporary, or considered a container. The application tracks the on-hand quantity of handling units by type and, for serialized handling units, by handling unit identifier. |
| Carrier | Identifier for a carrier that delivers inbound inventory to the warehouse or outbound shipments to a customer. This is the identifier that will be displayed to users on the application windows and reports. In the application, a carrier can be associated with a customer, order, inbound shipment, outbound shipment, load, and service levels (such as Ground, Next Day, and Saturday Delivery). |
| LPN UCC | Uniform Code Council (UCC) standard inventory identification number for the LPN. |
| Sub-LPN UCC | Uniform Code Council (UCC) standard inventory identification number for the sub-LPN. |
| Work Type | Type of pick work.<br>-   • **Bulk Pick**: Work type used to perform bulk picks.
<br>-   • **Demand Replenishment**: Replenishment work type generated when pre-inventory allocation is enabled and a pick location does not have inventory to complete an order. The application generates demand-based replenishments from reserve storage locations to the pick locations, and then generates picks based on the inventory pending to the pick locations.
<br>-   • **Emergency Replenishment**: Replenishment work type generated automatically when there is insufficient inventory in a pick zone to satisfy a shipment line.
<br>-   • **Kit**: Work type used to pick component items to fill a work order.
<br>-   • **Manual Replenishment**: Replenishment work type initiated by an operator for a specific location.
<br>-   • **Pick**: Work type used to pick inventory to fill an order.
<br>-   • **Replenishment**: Work type used to fill a pickface location with inventory from a storage location.
<br>-   • **Stage Transfer**: Pick work generated to transfer inventory typically from a cross docking location to a staging lane.
<br>-   • **Top-off Replenishment**: Replenishment work type generated automatically at timed intervals.
<br>-   • **Triggered Replenishment**: Replenishment work type generated automatically when an item in a zone or a location has dropped below a user-defined level. |

### Work Order details: Shorts fields

 
| Field | Description |
| --- | --- |
| Work Order | Identifier for a work order. A work order is an internal order used to find, allocate, and deliver product to a work-in-process area for assembly or disassembly, conversion, kitting, or repackaging. |
| Work Order Line | Unique number that identifies the work order line. A work order line describes a component item and its attributes that is to be built into the top-level item or that will result from disassembling the top-level item defined by the work order. |
| Work Order Revision | Identifier for one instance of a work order that allows you to use a standard work order multiple times. |
| Wave | Value that is assigned to the group of pick-type work requests (picks, replenishments, and cross docks) that are created when the wave is planned. The wave name distinguishes one group of pick-type work requests from another, which enables you to track the requests through the application. For example, if you allocate inventory for a single shipment, then all of the picks, replenishments, and cross docks generated for the shipment have the same wave name. |
| Item | Top-level item (finished good) to be built using component items or to be disassembled into component items as specified by the work order. |
| Short Quantity | Amount of inventory that the application could not allocate to a staging location or production line. |
| Reason | Value that indicates why the application could not allocate inventory. |
| Details | Additional details about why the short allocation occurred. For example, if the reason inventory could not be allocated was an inventory attribute mismatch, this field displays the order line criteria for which the application could not locate inventory to satisfy. |
| Replenishment Count | Number of times that the application has attempted to fulfill the short quantity through reallocation. |
| Maximum Retries | Maximum number of attempts for the application to reallocate the short inventory. This value is defined in the error control configurations; see [Configure replenishment settings](../../configuration/inventory/replenishments/replenishment-settings.md). |
| Late Ship Date | Last day of the outbound shipment range. To define a single shipment date, enter the first day of the shipment range. The application uses both delivery and ship dates to consolidate order lines into shipments, depending on the values defined for order consolidation. |
| Ship Short Allowed | Indicates whether the work order line with unfulfilled inventory is allowed to be shipped short. If the order line can be shipped short, a check mark is displayed in this column. |
| Allocation Date | Date and time on which the inventory was allocated from storage to fulfill the order or work order. |
| Allocated Quantity | Quantity (in terms of material handling or stock keeping units) of inventory that has been allocated from storage to fulfill the work order. |
| Shipment | Unique identifier for an outbound shipment. A shipment is a group of orders or order lines that are allocated together and shipped to the same location. |
| Destination Location | Location within the destination zone to which picked inventory for the shipments is to be moved. A location is a uniquely identified position within a zone of the warehouse used to store, stage, or manipulate product. |
| Lot | Identifier assigned to a quantity of an item during the manufacturing process for the purpose of tracking an attribute of that item, such as an expiration date. Lots differentiate distinct groups of inventory with the same item number. Items that may require a lot number include pharmaceuticals, fabrics, food, and other products with limited shelf life. Lots are user defined and are not necessarily unique since the same lot number can be applied to different items. However, lot and item combinations must be unique. |
| Origin | Identifier assigned to an item to identify the item's country of origin. It is typically used for export paperwork. Origin codes are user defined. |
| Revision | Identifier that is assigned to an item number to differentiate revisions of the same item number. |
| Replenishment Reference | Unique code that identifies a piece of replenishment work. A replenishment is a request for a supply of product to be moved from a storage location to an empty or diminished picking location. |
| Replenishment Status | Current status of the replenishment.<br>-   • **Work Order Pending Production Line Busy**: Work order is generated, but the required production line is busy.
<br>-   • **Pending Deposit**: Replenishment is pending deposit to the pickface location.
<br>-   • **Failed to Allocate Inventory**: Failed to allocate the inventory due to no inventory in storage locations.
<br>-   • **Failed to Allocate Initial Storage Local**: Failed to find a storage location from which to allocate inventory for an emergency replenishment (for example, location with inventory in error/locked status).
<br>-   • **Failed to Allocate Second Hop Location**: Failed to locate the second hop location to deposit inventory as part of the defined allocation movement path.
<br>-   • **Failed (Unknown)**: Replenishment failed, but the reason is unknown.
<br>-   • **Waiting for Work Order**: Waiting for a work order to be completed so that the inventory produced as a result of that work order can be used for satisfying the item line quantity.
<br>-   • **Processing through Cross Dock**: Inventory for replenishment, when received, is not staged after picking, but is directed to the cross dock location to be loaded on to the transport equipment.
<br>-   • **Issued**: Replenishment issued (generated) due to no inventory at pickface.
<br>-   • **Expired**: Replenishment has expired because the application could not fulfill it within the defined time limit.
<br>-   • **Complete**: Replenishment is satisfied and deposited at pickface. |
| Order Line | Unique number that identifies the order line. The number corresponds to the line's position on the order. The first order line is automatically assigned a line number of 0001. Additional order lines are then automatically numbered sequentially, beginning with 0002. |

### Work Order details: Pending Replenishment fields

 
| Field | Description |
| --- | --- |
| Work | Unique application-assigned identifier for a piece of work in the work queue. |
| Work Type | Type of pick work.<br>-   • **Bulk Pick**: Work type used to perform bulk picks.
<br>-   • **Demand Replenishment**: Replenishment work type generated when pre-inventory allocation is enabled and a pick location does not have inventory to complete an order. The application generates demand-based replenishments from reserve storage locations to the pick locations, and then generates picks based on the inventory pending to the pick locations.
<br>-   • **Emergency Replenishment**: Replenishment work type generated automatically when there is insufficient inventory in a pick zone to satisfy a shipment line.
<br>-   • **Kit**: Work type used to pick component items to fill a work order.
<br>-   • **Manual Replenishment**: Replenishment work type initiated by an operator for a specific location.
<br>-   • **Pick**: Work type used to pick inventory to fill an order.
<br>-   • **Replenishment**: Work type used to fill a pickface location with inventory from a storage location.
<br>-   • **Stage Transfer**: Pick work generated to transfer inventory typically from a cross docking location to a staging lane.
<br>-   • **Top-off Replenishment**: Replenishment work type generated automatically at timed intervals.
<br>-   • **Triggered Replenishment**: Replenishment work type generated automatically when an item in a zone or a location has dropped below a user-defined level. |
| Item | Identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). Before the application can effectively store, track, and manipulate inventory, you must assign an item identifier and define the attributes of each item you want to track. When defining an item, you specify information such as how the item is packaged and handled, along with details that define how it should be received, stored, allocated, shipped, counted, and valued (cost information). |
| Priority | Current priority of directed work in the work queue. |
| Pick Quantity | Quantity (in terms of material handling or stock keeping units) of the item that should be picked based on the order, work order, or replenishment. |
| Allocated Quantity | Quantity (in terms of material handling or stock keeping units) of inventory that has been allocated from storage to fulfill the work order. |
| Order Line | Unique number that identifies the order line. The number corresponds to the line's position on the order. The first order line is automatically assigned a line number of 0001. Additional order lines are then automatically numbered sequentially, beginning with 0002. |
| Source | Location where the work originated, such as the location from which inventory is picked, at which a count is performed, or from which transport equipment is moved. |
| Destination | Location where the work is completed, such as the location to which inventory is delivered or to which transport equipment is moved. |
| Client | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. |
| Replenishment Status | Current status of the replenishment.<br>-   • **Work Order Pending Production Line Busy**: Work order is generated, but the required production line is busy.
<br>-   • **Pending Deposit**: Replenishment is pending deposit to the pickface location.
<br>-   • **Failed to Allocate Inventory**: Failed to allocate the inventory due to no inventory in storage locations.
<br>-   • **Failed to Allocate Initial Storage Local**: Failed to find a storage location from which to allocate inventory for an emergency replenishment (for example, location with inventory in error/locked status).
<br>-   • **Failed to Allocate Second Hop Location**: Failed to locate the second hop location to deposit inventory as part of the defined allocation movement path.
<br>-   • **Failed (Unknown)**: Replenishment failed, but the reason is unknown.
<br>-   • **Waiting for Work Order**: Waiting for a work order to be completed so that the inventory produced as a result of that work order can be used for satisfying the item line quantity.
<br>-   • **Processing through Cross Dock**: Inventory for replenishment, when received, is not staged after picking, but is directed to the cross dock location to be loaded on to the transport equipment.
<br>-   • **Issued**: Replenishment issued (generated) due to no inventory at pickface.
<br>-   • **Expired**: Replenishment has expired because the application could not fulfill it within the defined time limit.
<br>-   • **Complete**: Replenishment is satisfied and deposited at pickface. |
| Work Order Line | Unique number that identifies the work order line. A work order line describes a component item and its attributes that is to be built into the top-level item or that will result from disassembling the top-level item defined by the work order. |
| Allocation Date | Date and time on which the inventory was allocated from storage to fulfill the order or work order. |
| Display Pick Quantity | Quantity of the item in terms of the display UOM that should be picked based on the order, work order, or replenishment. |
| Display Allocated Quantity | Quantity of inventory in terms of the display unit of measure (UOM) that has been allocated from storage to fulfill the work order line. |
| Replenishment Count | Number of times that the application has attempted to fulfill the short quantity through reallocation. |
| Message | Information that explains the reason why the process failed to allocate the required inventory. |
| Replenishment Reference | Unique code that identifies a piece of replenishment work. A replenishment is a request for a supply of product to be moved from a storage location to an empty or diminished picking location. |
| Ship Short Allowed | Indicates whether the order line with unfulfilled inventory is allowed to be shipped short. If the order line can be shipped short, a check mark is displayed in this column. This is determined by the **Partial** field on the order line. |

### Work Order details: Cross Dock fields

 
| Field | Description |
| --- | --- |
| Order Line | Unique number that identifies the order line. The number corresponds to the line's position on the order. The first order line is automatically assigned a line number of 0001. Additional order lines are then automatically numbered sequentially, beginning with 0002. |
| Cross Dock | Unique identifier associated with a piece of cross docking work. |
| Item | Identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). Before the application can effectively store, track, and manipulate inventory, you must assign an item identifier and define the attributes of each item you want to track. When defining an item, you specify information such as how the item is packaged and handled, along with details that define how it should be received, stored, allocated, shipped, counted, and valued (cost information). |
| Type | Value that identifies the type of cross docking work to perform.<br>-   • **Shipment**: The cross docking work was generated during allocation to fill an order line (marked for cross docking) that is included in a shipment.
<br>-   • **Replenishment**: The cross docking work was generated during receiving to fill an emergency replenishment. |
| Pick Quantity | Quantity (in terms of material handling or stock keeping units) of the item that should be picked based on the order, work order, or replenishment. |
| Cross Dock Quantity | Quantity (in terms of material handling or stock keeping units) of inventory that is available to be cross docked to fulfill the order line. |
| Allocated Quantity | Quantity (in terms of material handling or stock keeping units) of inventory that has been allocated from storage to fulfill the order line. |
| Minimum Shelf Life (Hours) | Minimum number of hours away from expiration that a date-tracked item must be considered for allocation. For example, if this value is 10, then the application only allocates inventory that has at least 10 hours to reach its expiration date. Only available if the item specified on the order line is date-tracked. |
| Pallet Load Sequence | Sequence number that identifies the order in which the pallets should be loaded onto transport equipment. |
| Pallet Position | Name of the place within the location where pallets are built for orders or shipments. |
| Pallet | Maximum number of pallets allowed on the shipment. The number of pallets per shipment can be obtained during shipment planning, and represents an estimate of the number of pallet picks that the shipment requires. |
| Shipment | Unique identifier for an outbound shipment. A shipment is a group of orders or order lines that are allocated together and shipped to the same location. |
| Ship-To Customer | Address name for the customer to whom the order must be shipped. |
| Round Pick Quantity | Indicates that allocation automatically rounds up the pick quantity to the next highest UOM. The pick quantity may be rounded up only within the bounds defined by the values specified for **Over Allocation Amount** and **Over Allocation Code**. This option is beneficial, for example, in situations where it is easier to pick an entire case or pallet of an item than to break a unit of measure (UOM) to complete a pick. |
| Display Pick Quantity | Quantity of the item in terms of the display UOM that should be picked based on the order, work order, or replenishment. |
| Display Pick UOM | Unit of measure in which the **Display Pick Quantity** is displayed. |
| Display Pick Quantity Remainder | Quantity of item identified against the pick quantity that is less than the display UOM. For example, if the total identified pick quantity is 10 cases and 5 eaches, and the display UOM is Case, then the remainder quantity would be 5 Eaches. |
| Display Pick Remainder UOM | Unit of measure in which the **Display Pick Quantity Remainder** is displayed. |
| Display Cross Dock Quantity | Quantity of inventory in terms of display UOM that is available to be cross docked to fulfill the work order line. |
| Display Cross Dock UOM | Unit of measure in which the **Display Cross Dock Quantity** is displayed. |
| Display Cross Dock Quantity Remainder | Quantity of item identified against the cross dock quantity that is less than the display UOM. For example, if the total identified cross dock quantity is 10 cases and 5 eaches, and the display UOM is Case, then the remainder quantity would be 5 Eaches. |
| Display Cross Dock Remainder UOM | Unit of measure in which the **Display Cross Dock Quantity Remainder** is displayed. |
| Work Order Line | Unique number that identifies the work order line. A work order line describes a component item and its attributes that is to be built into the top-level item or that will result from disassembling the top-level item defined by the work order. |
| Work Order Revision | Identifier for one instance of a work order that allows you to use a standard work order multiple times. |
| Case Splitting | If Yes, then you allow the allocation of less than full case quantities to fulfill the order line when necessary.<br > If No, then you require the allocation of full case quantities to satisfy the order line. As a result, the application does not allocate less than full case quantities for the order line, nor does it enable detail level picking. |

### Work Order details: Waiting Orders fields

 
| Field | Description |
| --- | --- |
| Shipment | Unique identifier for an outbound shipment. A shipment is a group of orders or order lines that are allocated together and shipped to the same location. |
| Shipment Line | Unique name or code that identifies a shipment line. A shipment line is the section of a shipment that provides detailed information about an individual item being shipped. |
| Order | Unique number that identifies an order. An order is a request for a supply of material or product. |
| Order Line | Unique number that identifies the order line. The number corresponds to the line's position on the order. The first order line is automatically assigned a line number of 0001. Additional order lines are then automatically numbered sequentially, beginning with 0002. |
| Line Quantity | Total quantity of the component item (in terms of material handling or stock keeping units) to be delivered to the production line to build all of the work order's top-level items. For example, if the work order requests 10 top-level items and it takes 4 units of this component item to build one top-level item, then the value in this field would be 40. Only available for assembly work orders. |
| Client | Unique identifier for a client who is responsible for creating the order or work order. |
| Work Order | Identifier for a work order. A work order is an internal order used to find, allocate, and deliver product to a work-in-process area for assembly or disassembly, conversion, kitting, or repackaging. |
| Work Order Line | Unique number that identifies the work order line. A work order line describes a component item and its attributes that is to be built into the top-level item or that will result from disassembling the top-level item defined by the work order. |
| Work Order Revision | Identifier for one instance of a work order that allows you to use a standard work order multiple times. |
| Order Sub-Line | Identifying number assigned to an outbound order sub-line. By default, the first line of each order line has a sub-line number of 0000, and it identifies the finished product. The remaining sub-lines are numbered sequentially, beginning with 0001, and they identify the component items required to complete the order line. |

### Work Order details: Picked and Produced field listings

#### Basics fields

 
| Field | Description |
| --- | --- |
| LPN | Unique identifier for inventory. Typically, an LPN refers to a pallet; however, it can refer to inventory received at less than pallet quantity. The LPN is the license plate by which the inventory is tracked in the facility. |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Quantity | Quantity of inventory on the LPN. |
| Footprint | Name that identifies a footprint, which describes the packaging dimensions and units of measure for the item with which it is associated. |
| Inventory Status | Value that defines the quality or disposition of the inventory. |
| Location | Unique name for a location within the facility that is used to receive, store, process, or ship inventory. |
| Case Identifier | Unique identifier for inventory being tracked at the sub-LPN (case) level. A sub-LPN is always a uniquely identifiable portion of the pallet LPN. This field only displays if the item requires tracking at the sub-LPN level. |
| Case Tag | RFID tag value for a case pick. |
| Catch Quantity | Actual measured quantity of the inventory that you want to identify. Catch quantity is typically obtained at receipt and may be verified prior to shipment. |
| Catch Unit Type | Unit of measure, such as feet, gallons or pounds, to use when capturing catch weight measurements. This value may not be changed while inventory exists for this item. Only available if a catch code is selected for the item. |
| Component Key | Unique application-assigned identifier for a component item. |
| Distribution Candidate | Indicates if the incoming inventory is marked for distribution. |
| LPN Tag | RFID tag value for a pallet pick. |
| LPN UCC | Uniform Code Council (UCC) standard inventory identification number for the LPN. |
| Master Handling Unit | A handling unit that holds different or multiple handling unit types. |
| Mater Handling Unit Type | Unique identifier for a master handling unit type. A handling unit type is a group of handling units (such as pallets, totes, pieces of equipment, or vehicles) that share the same characteristics such as size and weight as well as whether they are serialized, temporary, or considered a container. A master handling unit holds different or multiple handling unit types. |
| Master LPN | Unique identifier for a master handling unit. Typically, an LPN refers to a pallet; however, it can refer to inventory received at less than pallet quantity. The LPN is the license plate by which the master handling unit is tracked in the facility. |
| Physical Case | Actual inventory being tracked at the sub-LPN (case) level that is different from the system-defined inventory. |
| Physical Piece | Actual inventory being tracked at the detail (each) level that is different from the system-defined inventory. |
| Piece Identifier | Unique identifier for inventory being tracked at the detail (each) level. A detail LPN is always a uniquely identifiable portion of the pallet LPN. This field only displays if the item requires tracking at the detail level. |
| Receive Key | Unique application-assigned identifier for inventory that is received. |
| Remained Display Unit Quantity | Quantity of item identified against the unit quantity that is less than the display UOM. For example, if the total identified unit quantity is 10 cases and 5 eaches, and the display UOM is Case, then the remainder quantity would be 5 Eaches. |
| Slot Number | Identifier for the slot. Applicable only for inventory associated with an asset. |
| Storage Zone | A storage zone represents a group of locations that have the same attributes (consolidation, item mixing, date control, and others) for storing inventory. |
| Sub-LPN UCC | Uniform Code Council (UCC) standard inventory identification number for the sub-LPN. |
| Tracking Number | Unique identifier used by a parcel carrier to track a parcel throughout the delivery process. |
| Unit Quantity | Number of individual units of the item contained in the unit of measure (UOM). The application automatically updates this value based on the values for UOM Quantity and next UOM. For example, if the configuration has Pallet, Case, and Each UOMs, and there are 10 eaches per Case and 10 cases per Pallet, then the unit quantity for Pallet is 100. |
| Work Reference | Unique application-assigned identifier for a piece of work in the work queue. |
| Work Reference Detail | Unique application-assigned identifier for a piece of work (used by the system in case of bulk pick). |

#### Attributes fields

 
| Field | Description |
| --- | --- |
| LPN | Unique identifier for inventory. Typically, an LPN refers to a pallet; however, it can refer to inventory received at less than pallet quantity. The LPN is the license plate by which the inventory is tracked in the facility. |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Lot | Identifier assigned to a quantity of an item during the manufacturing process for the purpose of tracking an attribute of that item, such as an expiration date. Lots differentiate distinct groups of inventory with the same item number. Items that may require a lot number include pharmaceuticals, fabrics, food, and other products with limited shelf life. Lots are user defined and are not necessarily unique since the same lot number can be applied to different items. However, lot and item combinations must be unique. |
| Origin | Identifier assigned to an item to identify the item's country of origin. It is typically used for export paperwork. Origin codes are user defined. |
| Revision | Identifier that is assigned to an item number to differentiate revisions of the same item number. |
| Supplier | Identifier for a supplier. A supplier can be an individual, organization, or another warehouse within your own organization from which you repeatedly receive inventory or handling units. |
| Supplier Lot | Supplier lot identifier to assign to top-level items built for the work order. A supplier lot is a unique identifier that is assigned to a quantity of product during the manufacturing process that identifies the lot of the product as specified by the supplier. Only available for assembly work orders and if the top-level item requires this attribute. |
| Consignment Change Point | Value that determines when ownership of consigned inventory is transferred from the supplier to the warehouse. The consignment values defined for the supplier item override those defined for the supplier, which override those defined for the warehouse.<br>-   • **Consignment Days**: Ownership is transferred after the specified number of consignment days (defined in the **Consignment Days** field) have passed.
<br>-   • **Putaway**: Ownership is transferred when the putaway work for the inventory is complete.
<br>-   • **Receipt**: Ownership is transferred when the inventory is received by the warehouse.
<br>-   • **Transport Equipment Close**: Ownership is transferred when the outbound transport equipment on which the consigned inventory is loaded is closed.
<br>-   • **Transport Equipment Dispatch**: Ownership is transferred when the outbound transport equipment on which the consigned inventory is loaded is dispatched. |
| Consignment Days | Number of days after receiving consigned inventory that the ownership is transferred from the supplier to the warehouse. If **Consignment Days** is selected as the change point, then this value represents the number of days after receipt during which the supplier has ownership of the consigned inventory. A schedule-based job is configured to run daily to determine when the specified number of consignment days has passed, at which point ownership is transferred to the warehouse.<br > **Note**: The application sets the consignment end date for inventory on an ASN shipment based on when the inventory was received and put away to storage. For non-ASN shipments, the application sets the consignment end date based on when the inventory was identified. For example, if the Consignment Days value is 30, then when an ASN shipment is received, the consignment change point is 30 days from when the inventory is put away to storage; when a non-ASN shipment is received, the change point is 30 days from when the inventory is identified. |
| Remaining Consignment Days | Number of days remaining to transfer the ownership from the supplier to the warehouse, calculated based on the current date and the consignment end date. If **Consignment Days** is selected as the **Consignment Change Point**, then this value represents the number of days after receipt during which the supplier retains ownership of the consigned inventory. Only available if the change point is Consignment Days. |
| Consignment End Date | The date at which the ownership of the inventory is transferred from the supplier to the warehouse. Only available if the change point is Consignment Days. |
| Handling Unit Type | Category that classifies a group of handling units (for example, pallets, totes, transport equipment, or vehicles) that share the same characteristics such as size and weight, as well as whether they are serialized, temporary, or considered a container. The application tracks the on-hand quantity of handling units by type and, for serialized handling units, by handling unit identifier. |
| Child Handling Unit ID | Unique identifier for another handling unit associated with the parent handling unit. The two handling units are tracked together; the location of the child handling unit is the same as that of the parent. You cannot specify another child handling unit as a parent handling unit; however, multiple (child) handling units can be associated with a parent. Only available when the handling unit type category is set to Inventory. |
| Child Handling Unit Type | Category that classifies a group of sub (child) handling units (for example, pallets, totes, transport equipment, or vehicles) that share the same characteristics such as size and weight, as well as whether they are serialized, temporary, or considered a container. The application tracks the on-hand quantity of child handling units by type and, for serialized handling units, by child handling unit identifier. |
| Consigned | Indicates that the supplier retains ownership of the inventory until purchased by the client. The change of ownership and sale occur at pre-defined events in the warehouse. |
| Consignment Type | Value that determines when ownership of consigned inventory is transferred from the supplier to the warehouse. The consignment values defined for the supplier item override those defined for the supplier, which override those defined for the warehouse.<br>-   • **Receipt**: Ownership is transferred when the inventory is received by the warehouse.
<br>-   • **Putaway**: Ownership is transferred when the putaway work for the inventory is complete.
<br>-   • **Trailer Close**: Ownership is transferred when the shipping transport equipment on which the consigned inventory is loaded is closed.
<br>-   • **Trailer Dispatch**: Ownership is transferred when the shipping transport equipment on which the consigned inventory is loaded is dispatched.
<br>-   • **Consignment Days**: Ownership is transferred after the specified number of consignment days, defined in the **Consignment Days** field, have passed. |
| Default Origin Code | Country in which the item was manufactured. This value is displayed by default on the planned inbound order line for the item but during receiving it can be changed. Only applies to items for which customs or excise duties need to be paid. |
| LPN Handling Unit Height | Height of the handling unit type. |
| LPN Handling Unit ID | Unique identifier assigned to the handling unit type. |
| LPN Handling Unit Length | Length of the handling unit type. |
| LPN Handling Unit Weight | Weight of the handling unit type. If this is a type of handling unit that can contain inventory, this is the tare (empty) weight of the handling unit type. |
| LPN Handling Unit Width | Width of the handling unit type. |
| Units Per Case | Default number of items per packaging type. For example, for the Each/Case packaging type, it is the quantity of pieces or eaches of the item that is typically received in a single case. If a pallet of the item is received with a different quantity in the cases, the receiver can change the Each/Case value for that specific pallet. This field is not available if you select a footprint code for the item. |
| Units per Pack | Default number of items per packaging type. For example, for the Each/Inner Pack packaging type, it is the quantity of pieces or eaches of the item that is typically received in a single inner pack. If a pallet of the item is received with a different quantity in the inner packs, the receiver can change the Each/Inner Pack value for that specific pallet. This field is not available if you select a footprint code for the item. |

#### Dates fields

 
| Field | Description |
| --- | --- |
| LPN | Unique identifier for inventory. Typically, an LPN refers to a pallet; however, it can refer to inventory received at less than pallet quantity. The LPN is the license plate by which the inventory is tracked in the facility. |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Aging Profile | Name of the aging profile representing the aging process assigned to this item. An inventory aging profile is a configuration that defines a series of inventory statuses, each of which is associated with an age, such as 2 hours, 10 days, or 4 weeks. You assign an aging profile to a date-tracked item when you want the application to automatically update the inventory status of inventory for the item as it ages in the warehouse.<br > Included in the aging profile is the option to define an expired status. The application uses the age of the expired status to calculate the expiration date of an item that is tracked by its expiration date. When an item is tracked by both its manufactured date and expiration date, then you must assign either an aging profile or a shelf life to the item. |
| FIFO | Date used by the application for processing inventory when the first in, first out (FIFO) inventory rotation method is used. FIFO ensures that the oldest inventory is selected first. |
| Manufactured Date | Date on which the item identified on this line was manufactured. The date is stored in the database and displayed in the web client in the original captured time zone, not converted to a different time zone, such as a user preferred time zone. |
| Expire | Date on which the inventory will expire. The expiration date is determined by aging profile or shelf life assigned to the item configuration. The date is stored in the database and displayed in the web client in the original captured time zone, not converted to a different time zone, such as a user preferred time zone. |
| Received | Date on which the inventory was received into the warehouse. |
| Bill Through | Date for initial anniversary storage charges for the product that was not bought into the warehouse through the normal receiving process. |
| Consignment Days | Number of days after receiving consigned inventory that the ownership is transferred from the supplier to the warehouse. If **Consignment Days** is selected as the change point, then this value represents the number of days after receipt during which the supplier has ownership of the consigned inventory. A schedule-based job is configured to run daily to determine when the specified number of consignment days has passed, at which point ownership is transferred to the warehouse.<br > **Note**: The application sets the consignment end date for inventory on an ASN shipment based on when the inventory was received and put away to storage. For non-ASN shipments, the application sets the consignment end date based on when the inventory was identified. For example, if the Consignment Days value is 30, then when an ASN shipment is received, the consignment change point is 30 days from when the inventory is put away to storage; when a non-ASN shipment is received, the change point is 30 days from when the inventory is identified. |
| Consignment End Date | The date at which the ownership of the inventory is transferred from the supplier to the warehouse. Only available if the change point is Consignment Days. |
| Last Activity | Date and time at which an activity was last performed on an LPN, sub-LPN, or detail-LPN. |
| Last Move | Date and time at which an LPN, sub-LPN, or detail-LPN was last moved. |
| Remaining Consignment Days | Number of days remaining to transfer the ownership from the supplier to the warehouse, calculated based on the current date and the consignment end date. If **Consignment Days** is selected as the **Consignment Change Point**, then this value represents the number of days after receipt during which the supplier retains ownership of the consigned inventory. Only available if the change point is Consignment Days. |

### Work order field listings

#### General Work Order fields

 
| Field | Description |
| --- | --- |
| Work Order | Identifier for a work order. A work order is an internal order used to find, allocate, and deliver product to a work-in-process area for assembly or disassembly, conversion, kitting, or repackaging. |
| Work Order Revision | Identifier for one instance of a work order that allows you to use a standard work order multiple times. |
| Work Order Client | Unique identifier for a client who is responsible for creating the work order and is not necessarily the client that houses the top-level item specified in the work order; the client that houses the top-level item is selected from the **Item / Client** drop-down list and can either match or differ from the client ID. Only displayed in a 3PL environment. |
| Item / Client | Unique identifier for an item and the name of the client who stores the inventory in the facility. This is the client that houses the item specified in the work order and is not necessarily the client that created the work order. The client responsible for creating the work order is selected from the **Work Order Client** drop-down list and can either match or differ from the item client. Only displayed in a 3PL environment. |
| BOM Items Only | Indicates the ability to look up for BOM items. If selected, the **Item / Client** field lists only the items that are associated with the BOM. In the **Item / Client** field, if you enter an item that is defined by a BOM and you press TAB, the application lists the BOM associated with the item. If there are more than one BOMs associated with an item, you can choose the BOM, and the application populates the work order and work order line details from the respective BOM.<br > If deselected, then the **Item / Client** field lists all the items listed in the application. |
| Inventory Status | Defines the quality or disposition of the inventory. This is the default inventory status that is displayed when an operator identifies completed top-level items for the work order. However, the operator may change the status. Only available for assembly work orders. |
| Origin Code | Origin code to assign to top-level items built for the work order. An origin code is a unique identifier that is assigned to an item to identify the item's place of origin. Typically used for export paperwork. Origin codes are user defined. Only available for assembly work orders and if the top-level item requires this attribute. |
| Revision Level | Revision level to assign to top-level items built for the work order. A revision level is a unique identifier that is assigned to an item to differentiate revisions of the same item. Revision levels are user defined. Only available for assembly work orders and if the top-level item requires this attribute. |
| Lot | Identifier to assign to top-level items built for the work order. A lot is an identifier assigned to a quantity of product that is uniquely identified during the manufacturing process for the purpose of tracking an attribute of that product, such as expiration date. Only available for assembly work orders and if the top-level item requires this attribute. |
| Supplier Lot | Supplier lot identifier to assign to top-level items built for the work order. A supplier lot is a unique identifier that is assigned to a quantity of product during the manufacturing process that identifies the lot of the product as specified by the supplier. Only available for assembly work orders and if the top-level item requires this attribute. |
| Work Order Quantity | Total number of items that must be assembled or disassembled. |
| Work Order Catch Quantity | Total catch unit quantity of top-level items to assemble or disassemble for this work order. A catch unit quantity is a variable measure of inventory (such as weight, volume, or length) that is associated with one material handling (stock keeping) unit of the inventory. Only available if the top-level item requires catch quantities. |
| Due Date | Date and time when the processing of a work order on a production line is scheduled to end. |
| Without Components | If Yes, the work order does not need work order lines, does not need component inventory allocation, does not need the application to direct an operator to pick component inventory from a storage location to a production line, and does not need to track the component inventory. The only operations associated with this type of work order are to identify the top-level items and put them away. Work orders without components are especially useful for facilities that do not track their component inventory in the application.<br > If No, the work order needs work order lines, component inventory allocation, needs the application to direct an operator to pick component inventory from a storage location to a production line, and needs to track the component inventory.<br > Only available for assembly work orders. |
| Allow Putaway to Transport Equipment | If Yes, then during directed putaway, the work order can be assigned to storage transport equipment. When this field is Yes, you can select specific storage transport equipment for the work order, and operators can also select storage transport equipment as the putaway location on an RF device.<br > Storage transport equipment is used for inventory that has been identified, but not allocated or picked for a shipment. Once loaded, the storage transport equipment can be moved to the yard or to another warehouse for storage. For example, if you want inventory for an item to be stored on a trailer or in another warehouse as safety stock, you can set this field to Yes to putaway inventory to storage transport equipment. This field can be set to Yes by downloading the work order from host or when creating or modifying a work order.<br > **Note**: On the work order or a work order line, if both the **Allow Produced Inventory to be Cross Docked** field and this field are set to Yes, then cross docking is given priority. The inventory that is remaining after cross docking can be putaway to storage transport equipment.<br > If No, then the work order cannot be assigned to storage transport equipment for putaway, and the RF operator cannot specify storage transport equipment as the destination location during putaway.<br > **Note**: With this field set to No, inventory from the work order could still be directed by the application to storage transport equipment, if the application is configured to do so. For information on storage transport equipment configuration, see [Storage transport equipment](../../shipping/shipping-concepts/storage-transport-equipment.md). However, with this field set to Yes, you have more control over the specific storage transport equipment to which the work order inventory is put away, and the operator can select any other storage transport equipment during putaway. |
| Transport Equipment | Alphanumeric identifier of the storage transport equipment to which the inventory produced from the work order can be putaway. Storage transport equipment is used for inventory that has been identified, but not allocated or picked for a shipment. The storage transport equipment selected in this field is used only when the **Allow Putaway to Transport Equipment** field is Yes. A storage transport equipment can be entered when you create or modify a work order (not by downloading a work order from host). When you create or modify a work order, you can either select an existing or add a new storage transport equipment. You can assign multiple work orders to the same storage transport equipment.<br > The storage transport equipment must be checked in (with a status of Loading or Open for Loading) to put away the inventory. If the storage transport equipment is unavailable, the production inventory can be moved to a P&D or staging location to be loaded later using an inventory move. Alternatively, during putaway, the operator can override this storage transport equipment and put away the inventory elsewhere. If the operator changes the transport equipment, the new equipment is displayed in this field on the work order or order line, and the subsequent LPNs are directed to the new dock door. |

#### Processing work order fields

 
| Field | Description |
| --- | --- |
| Priority Code | Code that identifies the priority at which picks for an order or work order are released. Orders with the highest priority codes are released first. Priority codes range from 1 to 99 with 1 being the highest priority. |
| Production Tolerance (%) | Value that determines the minimum and maximum percentage of the total number of required finished items that can be assembled or disassembled. For example, if you enter a production tolerance of 10, then you can assemble and identify anywhere from 90% to 110% of the number of finished items required for the work order. |
| Processing Area | Area in your facility in which production lines are located. |
| Production Line | Name of the production line. A production line is an arrangement of machines or sequence of operations (production stations) involved with the assembly or disassembly of top-level item. |
| Disassembly Station | Disassembly station to which the top-level items for the work order are to be moved. A disassembly station is a position on a production line where a specific operation is performed during the disassembly of the top-level item (finished good). Only available when the work order type is Disassembly. |
| Account Number | Account number, such as a general ledger account number assigned to the work order. Account numbers are used in host transactions and for report purposes. Only available for assembly work orders. |
| Duration Time | Amount of time, in minutes, to complete the work order. The duration time is either downloaded from the host application or is specified manually by a user, and is typically based on historical production information. |
| Project Number | Project number assigned to the assembly work order. The project number is sent to the host application and used for reporting purposes. |
| Processing Priority | Number that identifies the priority at which work orders are allocated. Orders with the highest priority are allocated first. Processing priority numbers range from 1 to 9 with 1 being the highest priority. If this field is left blank, the application will set the processing priority to 5 by default. |
| Plan Sequence | Number that represents the order in which a work order is to be processed as compared to other work orders that are to be processed on a sequence-based production line. The Plan Sequence is only a visual cue to help operators producing work orders on a production line. The application does not force operators to produce work orders in the specified sequence. Only available if the **Plan Type** configured for the production line is Sequence. |
| Scheduled Start Date | Date and time on which the processing of a work order on a production line is scheduled to start. Only available if the **Plan Type** configured for the production line is Scheduled. |
| Scheduled End Date | Date and time on which the work order ends. Only available if the **Plan Type** configured for the production line is Scheduled. |
| Component Tracking | If Yes, the application tracks the attributes of the component items after the top-level item on work order is assembled and identified.<br > If No, the application does not track the attributes of the component items.<br > Only available for assembly work orders. |
| Release Remaining Lines | Used for cross docking purposes.<br > If Yes, the pick work for the unmarked order or work order lines will be released as usual.<br > If No, then the pick work created for unmarked order or work order lines will be held until the inventory that is marked for cross docking is received and allocated. |
| Automatically Release Pick | If Yes, the application automatically releases the pick work for the top-level items for a work order in advance of the work order's scheduled start time. The amount of time in advance of the scheduled start date is defined by the value for **Automatically Release Pick Time**. Only available as selection criteria or if a schedule-based production line is selected from the **Production Line** drop-down list. |
| Automatically Release Pick Time | Number of minutes in advance of a work order's scheduled start time that the application is to automatically release picks for the work order's items. Only available if **Automatically Release Pick** is set to Yes. |
| Exclusively Occupy Production Line | If **Yes**, the work order or BOM is to exclusively occupy a production line (the work order is not to be processed at the same time as other work orders on the same production line). This means that the work order must be started either on an exclusive production line (**Exclusive Work Order** is configured for the production line) or on a non-exclusive production line that has no other work orders started on it.<br > If **No**, another work order or BOM can be started at the same time on the same production line as this work order. Only available as selection criteria or if a schedule-based production line is selected from the **Production Line** drop-down list. |
| Allow Cross Dock of Produced Inventory | If Yes, then inventory produced from the assembly work order or the disassembly work order line can be cross docked. If the inventory can fulfill a cross dock, when it is identified, it is moved directly from production receiving to a cross dock location or a staging location to satisfy an outbound order.<br > If No, then the inventory produced from the work order or order line cannot be used to satisfy cross dock requests.<br > **Note**: If a work order is downloaded from a host and there is no defined value for this field, the value on the work order is set automatically based on the production settings configuration (**Allow Cross Dock of Produced Inventory** field). See [Configure production settings](../../configuration/production/production-settings.md). |

#### Disassembly Work Order fields

 
| Field | Description |
| --- | --- |
| Over Allocation Code | Code that identifies how over allocation is performed.<br>-   • **Percentage**: The application is permitted to allocate a certain percentage more, as defined in the **Over Allocation Amount** field, of the original quantity of component items required for the order line.
<br>-   • **Quantity**: The application is permitted to allocate a certain quantity more, as defined in the **Over Allocation Amount** field, of the original quantity of component items required for the order line.
<br > Over allocation is the process of allocating more than the indicated amount of inventory to satisfy an order or work order. Over allocation is beneficial in situations where it is easier to pick an entire case or pallet instead of breaking a case to complete a pick. |
| Over Allocation Amount | Total amount of inventory that can be allocated over the requested quantity when the allocation code is Quantity, or percentage of inventory that can be allocated when the allocation code is Percentage. If the over-allocation code is Percentage, then the over-allocation amount should be a value from 1 to 100 that indicates the percentage of the order quantity that can be over-allocated. If the over-allocation code is Quantity, then the over-allocation amount should be a value that represents the number that can be over-allocated. |
| Date Window Unit | Unit of time (minutes, hours, or days) for the outbound date window. |
| Date Window | Amount of time in relation to the inventory’s received date or expiration date during which inventory is considered the same age for allocation when one of the FEFO/FIFO/LEFO/LIFO or absolute FEFO/FIFO/LEFO/LIFO inventory rotation methods is required. |
| Inventory Rotation Method | Value that represents the order in which the allocation process selects available inventory for allocation. Select an inventory rotation method if you want the application to search for inventory based on date processing or location.<br>-   • **FEFO-ORDER-BY and FEFO-ORDER-BY-ABSOLUTE**: First-expiration, first-out. The first inventory to expire will be selected first.
<br>-   • **FIFO-ORDER-BY and FIFO-ORDER-BY-ABSOLUTE**: First-in, first-out. The oldest inventory will be selected first.
<br>-   • **LEFO-ORDER-BY and LEFO-ORDER-BY-ABSOLUTE**: Last-expiration, first-out. The last inventory to expire will be selected first.
<br>-   • **LIFO-ORDER-BY and LIFO-ORDER-BY-ABSOLUTE**: Last-in, first-out. The newest inventory will be selected first.
<br>-   • **LOCATION-ORDER-BY**: Locations are ordered within a pick zone (maintaining the allocation search path order) by the location attributes specified for the **Location Sort** field in inventory selection settings.
<br>-   •
    
    **No selection (blank)**: The application uses the inventory rotation method of the highest defined level of precedence. For information on precedence, see [Inventory rotation allocation processing](../../configuration/outbound/allocation/inventory-rotation-allocation.md).
    
    <br>
    
    **Note**: Inventory rotation methods defined at a lower precedence (except the default method) are automatically copied to the order line or work order line when the line is created. For example, if an order line is created for a date-tracked item with a rotation method defined, the rotation method is copied from the item to the order line, and then the application uses the order line rotation method during allocation.
    
    <br > If no inventory rotation method is defined at any level, then the application uses the allocation search path sequence and allocates the first available inventory it finds that matches all of the required attributes.
<br > When using inventory rotation methods that are not absolute, the application searches for inventory by allocation search path in sequence until it finds a pick zone that contains the inventory, and then allocates inventory that is closest to the preferred processing date. Therefore, the application stops searching at the first pick zone in which matching inventory is found.<br > When using absolute inventory rotation methods, the application searches either all of the allocation search paths for inventory that is closest to the preferred processing date or, if absolute groups are defined, each absolute group in sequence until it finds matching inventory and then allocates inventory that is closest to the preferred processing date from the pick zones within the absolute group. Therefore, the absolute method allows for more a comprehensive search to find the inventory. |
| Footprint Code | Name that identifies a footprint, which describes the packaging dimensions and units of measure for the item with which it is associated. |
| Units Per Pack | Default number of units (pieces) per inner pack to be supplied for the order line or work order line. If left blank, there is no specific quantity needed in a pack, and the application can allocate any quantity in a pack while still allocating the total quantity needed for the order line. For example, if this field is blank, and if the warehouse stocks an item with 8 units in a pack and 10 units in a pack, then the application can allocate either pack quantity according to other allocation rules. However, if 10 is the value in **Units Per Pack**, the application allocates from the location with packs of 10 so the customer gets the specified inner pack quantity. |
| Units Per Case | Default number of units (pieces) per case to be supplied for the order line or work order line. If left blank, there is no specific quantity needed in a case, and the application can allocate any quantity in a case while still allocating the total quantity needed for the order line. For example, if this field is blank, and if the warehouse stocks an item with 80 units in a case and 100 units in a case, then the application can allocate either case quantity according to other allocation rules. However, if 100 is the value in **Units Per Case**, the application allocates from the location with cases of 100 so the customer gets the specified case quantity. |
| Inventory Status Progression | Inventory status progression that the allocated top-level item must have. An inventory status progression is a series of inventory statuses that define the levels of quality at which a customer is willing to accept a product. When an inventory status progression is specified on an order, then the application can select product to satisfy that order based on a prioritized list of acceptable inventory statuses rather than a single status. This functionality lets customers define a wider range of acceptable inventory as well as specify their preference on the quality of the inventory that they are willing to accept. Available only for disassembly work orders. |
| Pick Quantity | Quantity (in terms of material handling or stock keeping units) of the item to be picked for the disassembly work order. |
| Cross Dock | If Yes, then inventory for the disassembly work order header is to be cross docked to a production line staging location or a cross dock location at receipt instead of allocated out of storage.<br > If No, inventory for the disassembly work order header is to be allocated from storage. |
| Round Pick Quantity | If Yes, the allocation is to automatically round up the pick quantity to the next highest UOM. The pick quantity may be rounded up only within the bounds defined by the values specified for **Over Allocation Amount** and **Over Allocation Code**. This option is beneficial, for example, in situations where it is easier to pick an entire case or pallet of an item than to break a unit of measure (UOM) to complete a pick.<br > If No, the allocation does not round up the pick quantity. |

#### Allocation Rules Work Order fields

 
| Field | Description |
| --- | --- |
| Rule Name | Name of the allocation rule. An allocation rule is a processing command that specifies the inventory attribute values that are acceptable to fulfill an order line, work order detail, work order line, or bill of materials (BOM) detail. |
| Description | Description that further defines the allocation rule. |

#### Customs Work Order fields

 
| Field | Description |
| --- | --- |
| Type | Identifier that defines the type of customs tracking required for the inventory on the work order. Defining a customs type on the planned inbound order overrides the customs type defined for the items on the work order. Only displayed if Customs functionality is enabled.<br>-   • **Customs**: Customs duties need to be paid for the items on the work order. Available if the address for the warehouse is designated as a Customs site type.
<br>-   • **Excise**: Excise duties need to be paid for the items on the work order; customs duties may also be required. Available if the address for the warehouse is designated as a Customs and Excise site type.
<br>-   • **Free**: Customs duties or excise duties need not be paid. |
| VAT Code | Code for the value added tax (VAT) for the item. A customs VAT is charged on goods and some services that are imported from countries outside the European Unit (EU) and brought into the United Kingdom (UK) from other EU countries. It is also charged on most goods and services that VAT-registered businesses provide in the UK.<br>-   • **Standard**: The standard customs VAT rate is charged for this item.
<br>-   • **Zero**: No customs VAT is charged for this item. |
| Consignment ID | Unique identifier assigned to a receipt of bonded inventory. A customs consignment is an application-generated ID number that consists of a prefix (the warehouse ID) plus the next value in the customs consignment ID sequence. For example, if your warehouse ID is WMD1 and the next number in the sequence is 123456, then the customs consignment ID will be WMD1123456.<br > Only displayed if Customs functionality is enabled for the warehouse and the item is configured for customs tracking. |
| Commodity Code | Code that identifies a commodity. Commodities are categories created to group inventory that has the same qualities and specifications, regardless of their source. For example, wheat is a commodity. Commodity codes are standardized to provide carriers with a standard by which to determine pricing and to simplify the shipment process. The Commodity Code is usually printed on the bill of lading (BOL). If the commodity is printed on the BOL, all products of the same commodity are totaled. |
| Default Origin Code | Country in which the item was manufactured. This value is displayed by default on the planned inbound order line for the item but during receiving it can be changed. Only applies to items for which customs or excise duties need to be paid. |
| Customs Cost | Monetary amount that is paid to customs for the item. Only applies to items for which customs or excise duties need to be paid. |
| Duty Stamp Tracked | If Yes, the item is duty stamp tracked. If No, the item is not duty stamp tracked.<br > Only applies to items for which excise duties need to be paid. |
| Notes | Additional information related to the work order. You use this field, for example, to describe the work order and when it was created. This field is for informational purposes only; it is not used by any process. |

### Work order line field listings

#### General Work Order Line fields

 
| Field | Description |
| --- | --- |
| Work Order Line | Unique number that identifies the work order line. A work order line describes a component item and its attributes that is to be built into the top-level item or that will result from disassembling the top-level item defined by the work order. |
| Item / Client | Unique identifier for an item and the name of the client who stores the inventory in the facility. This is the client that houses the item specified in the work order and is not necessarily the client that created the work order. The client responsible for creating the work order is selected from the **Work Order Client** drop-down list and can either match or differ from the item client. Only displayed in a 3PL environment. |
| Inventory Status Progression | Inventory status progression of the top-level item. An inventory status progression is a series of inventory statuses that define the levels of quality at which a customer is willing to accept a product. When an inventory status progression is specified on an order, then the application can select product to satisfy that order based on a prioritized list of acceptable inventory statuses rather than a single status. This functionality lets customers define a wider range of acceptable inventory as well as specify their preference on the quality of the inventory that they are willing to accept. Applicable only for assembly work orders. |
| BOM Quantity | Quantity (in terms of material handling or stock keeping units) of the component item required to assemble one top-level item. This is the quantity of the component item that will be consumed when assembling the top-level item. If a BOM is defined for the top-level item, then this value can be populated by the BOM. |
| BOM Line Quantity | Total quantity of this component item (in terms of material handling or stock keeping units) to be disassembled from the top-level item and delivered to the production line. For example, if the work order requests 10 top-level items and it takes 4 units of this component item to build one top-level item, then the value in this field would be 40. Only available for disassembly work orders. |
| Inventory Status | Defines the quality or disposition of the inventory. This is the default inventory status that is displayed when an operator identifies component items for the work order. However, the operator may change the status. Only available for disassembly work orders. |
| Line Quantity | Total quantity of the component item (in terms of material handling or stock keeping units) to be delivered to the production line to build all of the work order's top-level items. For example, if the work order requests 10 top-level items and it takes 4 units of this component item to build one top-level item, then the value in this field would be 40. Only available for assembly work orders. |
| Revision Level | Revision level that allocated component items must have. If any revision level is acceptable, leave this field blank. A revision level is a unique identifier that is assigned to an item to differentiate revisions of the same item. Revision Levels are user defined. Only available if the component item entered in the **Item/Client** field requires revision level tracking. |
| Lot | Lot number that allocated component items must have. If any lot is acceptable, leave this field blank. A lot is an identifier assigned to a quantity of product that is uniquely identified during the manufacturing process for the purpose of tracking an attribute of that product, such as expiration date. Lots differentiate distinct groups of inventory with the same item number. Only available if the component item requires this attribute. |
| Supplier Lot | Supplier lot number that allocated component items must have. If any supplier lot is acceptable, leave this field blank. A supplier lot is a unique identifier that is assigned to a quantity of product during the manufacturing process that identifies the lot of the product as specified by the supplier. Only available if the component item requires this attribute. |
| Supplier Number | Unique code that identifies a supplier. A supplier is considered to be any source from which you receive product. For example, a supplier can be an individual, an organization, or another plant within your own organization from which you repeatedly receive product. |
| Pick Quantity | Quantity (in terms of material handling or stock keeping units) of the item that should be picked based on the order, work order, or replenishment. |
| Allocate by Catch Quantity | Indicates that the application will allocate the component inventory based on catch unit quantity instead of material handling (stock keeping) quantity. |
| Line Catch Quantity | Total catch unit amount of the component item to be delivered to the production line to build the expected quantity of the work order's top-level items. For example, if the work order requests 10 top-level items and it takes 4 pounds of this component item to build one top-level item, then the value in this field would be 40. Only available for assembly work orders and if the **Allocate by Catch Quantity** check box is selected. |
| Pick Catch Quantity | Catch unit quantity of the component item that has not yet been allocated for the work order. When you first create the work order, this value matches the value entered in the **Line Catch Quantity** field. As the component item is successfully allocated, this quantity will decrease to zero. If you later determine that you need more of the component than originally planned, enter the additional quantity in this field. You can then reallocate the work order line for the additional quantity. Only available for assembly work orders. |
| BOM Catch Quantity | Catch unit amount of the component item required to assemble one top-level item. This is the catch unit quantity of the component item that will be consumed when assembling the top-level item. Only available if the **Allocate by Catch Quantity** check box is deselected. |

#### Processing Work Order Line fields

 
| Field | Description |
| --- | --- |
| Footprint Code | Name that identifies a footprint, which describes the packaging dimensions and units of measure for the item with which it is associated. |
| Over Allocation Code | Code that identifies how over allocation is performed.<br>-   • **Percentage**: The application is permitted to allocate a certain percentage more, as defined in the **Over Allocation Amount** field, of the original quantity of component items required for the order line.
<br>-   • **Quantity**: The application is permitted to allocate a certain quantity more, as defined in the **Over Allocation Amount** field, of the original quantity of component items required for the order line.
<br > Over allocation is the process of allocating more than the indicated amount of inventory to satisfy an order or work order. Over allocation is beneficial in situations where it is easier to pick an entire case or pallet instead of breaking a case to complete a pick. |
| Over Allocation Amount | Total amount of inventory that can be allocated over the requested quantity when the allocation code is Quantity, or percentage of inventory that can be allocated when the allocation code is Percentage. If the over-allocation code is Percentage, then the over-allocation amount should be a value from 1 to 100 that indicates the percentage of the order quantity that can be over-allocated. If the over-allocation code is Quantity, then the over-allocation amount should be a value that represents the number that can be over-allocated. |
| Date Window Unit | Unit of time (minutes, hours, or days) for the outbound date window. |
| Inventory Rotation Method | Value that represents the order in which the allocation process selects available inventory for allocation. Select an inventory rotation method if you want the application to search for inventory based on date processing or location.<br>-   • **FEFO-ORDER-BY and FEFO-ORDER-BY-ABSOLUTE**: First-expiration, first-out. The first inventory to expire will be selected first.
<br>-   • **FIFO-ORDER-BY and FIFO-ORDER-BY-ABSOLUTE**: First-in, first-out. The oldest inventory will be selected first.
<br>-   • **LEFO-ORDER-BY and LEFO-ORDER-BY-ABSOLUTE**: Last-expiration, first-out. The last inventory to expire will be selected first.
<br>-   • **LIFO-ORDER-BY and LIFO-ORDER-BY-ABSOLUTE**: Last-in, first-out. The newest inventory will be selected first.
<br>-   • **LOCATION-ORDER-BY**: Locations are ordered within a pick zone (maintaining the allocation search path order) by the location attributes specified for the **Location Sort** field in inventory selection settings.
<br>-   •
    
    **No selection (blank)**: The application uses the inventory rotation method of the highest defined level of precedence. For information on precedence, see [Inventory rotation allocation processing](../../configuration/outbound/allocation/inventory-rotation-allocation.md).
    
    <br>
    
    **Note**: Inventory rotation methods defined at a lower precedence (except the default method) are automatically copied to the order line or work order line when the line is created. For example, if an order line is created for a date-tracked item with a rotation method defined, the rotation method is copied from the item to the order line, and then the application uses the order line rotation method during allocation.
    
    <br > If no inventory rotation method is defined at any level, then the application uses the allocation search path sequence and allocates the first available inventory it finds that matches all of the required attributes.
<br > When using inventory rotation methods that are not absolute, the application searches for inventory by allocation search path in sequence until it finds a pick zone that contains the inventory, and then allocates inventory that is closest to the preferred processing date. Therefore, the application stops searching at the first pick zone in which matching inventory is found.<br > When using absolute inventory rotation methods, the application searches either all of the allocation search paths for inventory that is closest to the preferred processing date or, if absolute groups are defined, each absolute group in sequence until it finds matching inventory and then allocates inventory that is closest to the preferred processing date from the pick zones within the absolute group. Therefore, the absolute method allows for more a comprehensive search to find the inventory. |
| Units Per Case | Default number of units (pieces) per case to be supplied for the order line or work order line. If left blank, there is no specific quantity needed in a case, and the application can allocate any quantity in a case while still allocating the total quantity needed for the order line. For example, if this field is blank, and if the warehouse stocks an item with 80 units in a case and 100 units in a case, then the application can allocate either case quantity according to other allocation rules. However, if 100 is the value in **Units Per Case**, the application allocates from the location with cases of 100 so the customer gets the specified case quantity. |
| Units Per Pack | Default number of units (pieces) per inner pack to be supplied for the order line or work order line. If left blank, there is no specific quantity needed in a pack, and the application can allocate any quantity in a pack while still allocating the total quantity needed for the order line. For example, if this field is blank, and if the warehouse stocks an item with 8 units in a pack and 10 units in a pack, then the application can allocate either pack quantity according to other allocation rules. However, if 10 is the value in **Units Per Pack**, the application allocates from the location with packs of 10 so the customer gets the specified inner pack quantity. |
| Date Window Unit | Unit of time (minutes, hours, or days) for the outbound date window. |
| Date Window | Value for the outbound date window. Only available if **Date Window Unit** value is selected. |
| Consumption Tolerance (%) | Value that determines the minimum and maximum percentage of the BOM quantity (specified in the **BOM Quantity** field) for the component item that the application will allow. For example, if you enter a Consumption Tolerance Percentage of 10, then you can consume anywhere from 90% to 110% of the specified consumed quantity when assembling the top-level item. |
| Expected Scrap (%) | Value that determines the minimum and maximum percentage of the BOM quantity (specified in the **BOM Quantity** field) for the component item that the application will allow being scrapped (not reusable). For example, if you enter a scrap percentage of 50, then you can scrap anywhere from 50% to 150% of the specified BOM quantity when disassembling the top-level item. |
| Cross Dock | If Yes, then when the inventory specified on this outbound order or work order line is identified, it is moved directly from receiving to a cross dock location or a specified staging location to satisfy an outbound order or work order.<br > If No, then the order or work order line does not use cross docked inventory. |
| Round Pick Quantity | Indicates that allocation automatically rounds up the pick quantity to the next highest UOM. The pick quantity may be rounded up only within the bounds defined by the values specified for **Over Allocation Amount** and **Over Allocation Code**. This option is beneficial, for example, in situations where it is easier to pick an entire case or pallet of an item than to break a unit of measure (UOM) to complete a pick. |
| Allow Cross Dock of Produced Inventory | If Yes, then inventory produced from the assembly work order or the disassembly work order line can be cross docked. If the inventory can fulfill a cross dock, when it is identified, it is moved directly from production receiving to a cross dock location or a staging location to satisfy an outbound order.<br > If No, then the inventory produced from the work order or order line cannot be used to satisfy cross dock requests.<br > **Note**: If a work order is downloaded from a host and there is no defined value for this field, the value on the work order is set automatically based on the production settings configuration (**Allow Cross Dock of Produced Inventory** field). See [Configure production settings](../../configuration/production/production-settings.md). |

#### Allocation Rules Work Order Line fields

 
| Field | Description |
| --- | --- |
| Rule Name | Name of the allocation rule. An allocation rule is a processing command that specifies the inventory attribute values that are acceptable to fulfill an order line, work order detail, work order line, or bill of materials (BOM) detail. |
| Description | Description that further defines the allocation rule. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2023 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
