---
title: "Procedures for inbound shipments"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/procedures_for_inbound_shipments.htm"
source: "/content/procedures_for_inbound_shipments.htm"
toc_path:
  - "Warehouse Management"
  - "Receiving"
  - "Inbound Shipments"
  - "Procedures for inbound shipments"
sections:
  - "Add or modify an inbound shipment"
  - "Add or modify an inbound order"
  - "Add or modify an inbound order line"
  - "Add a planned inbound order to an inbound shipment"
  - "Auto receive an inbound shipment"
  - "Copy an inbound order and order lines to an inbound shipment"
  - "Add or modify a distribution from an inbound order line"
  - "Assign an inbound shipment to a staging lane"
  - "Set the average catch quantity for an order"
  - "Receive inventory"
  - "Receive empty handling units"
  - "Put away received inventory"
  - "Reverse the receipt of an LPN"
  - "View over, short, and damaged inventory"
  - "Complete an inbound shipment"
  - "Delete an inbound shipment"
  - "Delete an inbound order"
  - "Delete an inbound order line"
  - "Report an inbound quality issue using the Inbound Shipments page"
  - "View LPNs associated with an inbound shipment"
  - "View received empty handling units"
  - "View detailed inbound shipment information"
  - "View detailed inbound order information"
  - "Inbound shipments field listings"
  - "Add or Modify Inbound Shipment fields"
  - "Add Inbound Order fields"
  - "Inbound Order Line fields"
  - "Receiving fields"
  - "Add Empty Unexpected Handling Units fields"
  - "Distribution Information fields"
  - "Distribution Customers and Quantities fields"
  - "Empty Handling Units Fields"
  - "Inbound Shipment detail fields"
  - "Inbound Order detail fields"
  - "Inbound Order Line detail fields"
images: []
source_sha1: 81ec905214974908c0e3ab00064bd2d974f921a4
---
# Procedures for inbound shipments

You can perform the following procedures on inbound shipments.

## Add or modify an inbound shipment

1.  Select **Receiving > Inbound Shipments**.
2.  Perform one of the following tasks:
    -   To add an inbound shipment, from the **Actions** drop-down list, select **Add Inbound Shipment**.
    -   To edit an inbound shipment, in the grid, select the check box next to the shipment, and then from the **Actions** drop-down list, select **Modify Inbound Shipment**.
3.  Enter information in the [Add or Modify Inbound Shipment fields](#Add_or_modify_inbound_shipment_fields).
4.  Click **Save**.

## Add or modify an inbound order

1.  Select **Receiving > Inbound Shipments**.
2.  Click **Inbound Orders**.
3.  Perform one of the following tasks:
    -   To add an inbound order, from the **Actions** drop-down list, select **Add Inbound Order**.
    -   To modify an inbound order, in the grid, select the check box next to the order or click the order, and then from the **Actions** drop-down list, select **Modify Inbound Order**.
4.  Enter information in the [Add Inbound Order fields](#Add_Inbound_Order_fields).
5.  Click **Save**.
6.  If you selected to immediately begin adding order lines, enter information in the available [Inbound Order Line fields](#Inbound_Order_Line_fields), and then click **Save**.

## Add or modify an inbound order line

1.  Select **Receiving > Inbound Shipments**.
2.  Perform one of the following tasks:
    -   To add or modify an inbound order line:
        1.  Click **Inbound Orders**.
        2.  In the grid, click the inbound order to which you want to add or modify a line. The inbound order and order line details are displayed.
    -   To add or modify a planned inbound order line:
        1.  In the grid, click the shipment that contains the planned inbound order to which you want to add or modify a line. The inbound shipment details are displayed.
        2.  In the grid, click the planned inbound order to which you want to add or modify a line. The planned inbound order and order line details are displayed.
3.  Perform one of the following tasks:
    -   To add a new order line, from the **Actions** drop-down list, select **Add Line**.
    -   To modify an order line, in the grid, select the check box next to the order line, and from the **Actions** drop-down list, select **Modify Line**.
4.  Enter information in the available [Inbound Order Line fields](#Inbound_Order_Line_fields).
5.  If you are adding an order line, then to continually add more lines, select the **Add Next Line** check box; otherwise, clear it to be finished adding lines.
6.  Click **Save**.

## Add a planned inbound order to an inbound shipment

1.  Select **Receiving > Inbound Shipments**.
2.  In the grid, click the inbound shipment to which you want to add an order. The inbound shipment details are displayed.
3.  Above the orders grid, from the **Actions** drop-down list, select **Add Planned Inbound Order**.
4.  Enter information in the [Add Inbound Order fields](#Add_Inbound_Order_fields).
5.  Click **Save**.
6.  Enter information in the [Inbound Order Line fields](#Inbound_Order_Line_fields).

**Note**: The Planned Inbound Order Line window is only displays if the **Add Line** check box is selected.

8.  Click **Save**.

## Auto receive an inbound shipment

To perform auto receiving, the inbound shipment must be associated with an ASN from a trusted supplier enabled for auto receiving. See [ASN auto receiving from trusted suppliers](../receiving-concepts.md).

1.  Perform one of the following tasks:
    -   Select **Receiving > Inbound Shipments**, and then in the grid, select a shipment.
    -   Select **Receiving > Staging**, and then under Doors, select the status bar for an inbound shipment.
    -   Select **Receiving > Door Activity**, and then under Doors, select the status bar for an inbound shipment.
2.  From the **Actions** drop-down list, select **Auto Receive**.
3.  Under **Empty Locations**, select the receiving staging lane to which the application systematically moves the LPNs on the inbound shipment during auto receiving.
4.  Click **Next** or **Move Equipment**.
5.  Under **Move Equipment**, perform one of the following tasks:
    
    **Note**: The transport equipment is not moved until receiving is complete. Additionally, if there are errors during auto receiving, then the transport equipment is not moved or dispatched.
    
    -   To move the equipment to a new door or yard location:
        1.  Select **Move to New Location**, and then under **Available Locations**, select a new location.
        2.  Select the move method:
            -   **Add to Work Queue**: Directed work is created in the work queue to move the equipment. If you select this option, then you can also select a specific operator or role to which the work is assigned.
                
            -   **Move Immediately**: The application is immediately updated to reflect the equipment's new location; no work request is created.
                
    -   To leave the equipment at the dock door, select **Leave at door**.
    -   To dispatch the transport equipment, select **Dispatch equipment**.
6.  Under **Complete Receiving**, select whether to close the inbound shipment:
    -   **Yes**: The inbound shipment is closed and the transport equipment is closed. When you complete receiving, the application removes existing receiving work and pre-identification inventory details created from an ASN from the application. If inbound shipment information has not yet been communicated to the host, it is sent at this time.
        
        **Note**: It is recommended that all received inventory be staged before the transport equipment or inbound shipment is closed. If inventory is received, but not staged, it is noted as a discrepancy during the completion process.
        
    -   **No**: The inbound shipment and transport equipment remain open.
7.  Click **Next** or **Review**.
8.  When you are finished reviewing the auto receiving details, click **Finish**. The auto receiving progress bar is displayed, and then a confirmation message is displayed when processing is complete.
9.  Click **OK**.
    
    **Note**: If the application failed to auto receive LPNs on the inbound shipment, view the details of the shipment, and then click the auto receive status Completed with Error to view the details of the error.
    

## Copy an inbound order and order lines to an inbound shipment

You can copy either an entire order and its order lines to an inbound shipment, or you can select specific order lines to copy to a shipment. A new planned inbound order is created from the selected inbound order or order lines and added to the inbound shipment.

1.  Select **Receiving > Inbound Shipments**.
2.  In the grid, click the inbound shipment to which you want to add an order. The inbound shipment details are displayed.
3.  Above the orders grid, from the **Actions** drop-down list, select **Copy Inbound Orders to Shipment**.
4.  In the **Inbound Orders** grid, perform one of the following tasks:
    -   To copy one or more orders (including all order lines), select the check box next to one or more orders.
    -   To copy specific lines from an order, expand the order to display the lines, and then select the check box next to one or more order lines.
5.  Click **Add to Shipment**. A planned inbound order is added to the shipment and assigned an application-generated identifier.

## Add or modify a distribution from an inbound order line

You can also [add or modify a distribution for an outbound order line](../../outbound-planner/outbound/procedures-for-orders.md).

1.  Select **Receiving > Inbound Shipments**.
2.  Perform one of the following tasks:
    -   Above the grid, click **Inbound Orders**, and then in the grid click the order containing the line to distribute.
    -   In the grid, click the inbound shipment containing the inbound order line to distribute, and then click the order containing the line.
3.  Perform one of the following tasks:
    -   To add a distribution:
        1.  In the grid, select the inbound order line for which to create a distribution.
            
            **Note**: An inbound order line can be associated with multiple distributions; if it is, the application uses the distribution type configuration to determine how the inventory is distributed to multiple stores. See [Distribution Types](../../configuration/outbound/distribution/distribution-types.md).
            
        2.  From the **Actions** drop-down list, select **Add Distribution**.
    -   To modify a distribution, in the row for the order line, in the **Distribution** column, click the distribution quantity, and then click **Back** or **DISTRIBUTION INFORMATION**.
4.  Enter information in the [Distribution Information fields](#Distribution_information_fields).
5.  Click **Next** or **CUSTOMERS & QUANTITIES**.
6.  Add customers to the distribution:
    1.  From the **Actions** drop-down list, select **Add Customer**. The Select Customers window is displayed.
        
        **Note**: Only customers configured to receive distributions are displayed. See [Existing Customers](../../configuration/partners/customers/existing-customers.md).
        
    2.  Select the check box next to the customers that will receive the distribution, and then click **Select**.
7.  To distribute the inbound order line quantity evenly across the customers:
    1.  Click **Distribute Quantity Evenly**.
    2.  Select one of the following options:
        -   **Distribute total quantity evenly**: Indicates that the remaining (not already included in a distribution) expected quantity on the inbound order line is divided evenly to the customers you selected on the distribution. Select this option to ensure all customers receive the same amount of inventory. If there is an uneven quantity to distribute, the first customer in the list receives the remaining inventory.
        -   **Distribute specific quantity evenly**: Indicates that the quantity that you specify is divided evenly to the customers selected for the distribution. If you select this option, then you must also enter a quantity to distribute evenly. For example, if an inbound order line has a quantity of 100, but you only want to distribute 80 evenly, then you would enter "80." The remaining quantity can either be assigned to a specific customer on the distribution or is available for storage.
8.  In the grid, enter information in the [Distribution Customers and Quantities fields](#Distribution_customers_and_quantities_fields).
9.  To delete a customer:
    1.  In the grid, select the check box next to the customer.
    2.  From the **Actions** drop-down list, select **Delete Customer**. A confirmation message is displayed.
    3.  Click **OK**.
10.  Click **Finish**.

## Assign an inbound shipment to a staging lane

You can assign an inbound shipment that is not associated with transport equipment to a staging lane so that operators can receive inventory from the shipment. Inbound shipments must be in an Expected status to be assigned to a staging lane. When you assign an inbound shipment to a lane, the shipment's status is updated to Checked In.

1.  Perform one of the following tasks:
    -   Select **Receiving > Inbound Shipments**, and then select the check box next to one or more inbound shipments; and then from the **Actions** drop-down list, select **Assign to Staging Lane**.
    -   View the Staging page, and then click **Assign Inbound Shipment**.
        
        1.  Select one of the following modules: **Receiving** or **Shipping**.
            
        2.  Select **Staging**.
            
        
    -   View the Check In page, and then click **Assign Inbound Shipment to Staging Lane**.
        
        1.  Select one of the following modules: **Receiving**, **Shipping**, or **Yard**.
            
        2.  Select **Check In**.
            
        
2.  To add an inbound shipment to assign:
    
    **Note**: You can add multiple inbound shipments and assign them to the same staging lane.
    
    1.  Click **Add**. The Unassigned Inbound Shipments page is displayed.
    2.  In the grid, select the shipment to assign.
    3.  Click **Assign**.
3.  Under **Lanes**, select the row for the staging lane to which to assign the inbound shipments.
    
    **Note**: The application displays receiving lanes that are not in error, that do not have a resource code assigned, and that have available capacity.
    
4.  Click **Save**. A confirmation message is displayed.

## Set the average catch quantity for an order

If an item is enabled for average catch quantity capture, then when an order line consisting of a single item is received, the operator can enter and validate the gross weight of the order line. You can then apply the average catch quantity per UOM to the received inventory.

1.  Select **Receiving > Inbound Shipments**.
2.  Click the shipment that contains the order for which you want to set the average catch quantity.
3.  Click the order for which you want to set the average catch quantity.
4.  From the **Actions** drop-down list, select **Set Average Catch Qty**.
5.  Enter the total catch quantity for the order lines.
6.  Click **Save**.

## Receive inventory

1.  Select **Receiving > Inbound Shipments**.
2.  Perform one of the following tasks:
    -   To receive inventory from an inbound shipment:
        1.  In the grid, select the check box next to the inbound shipment; or click the inbound shipment from which to receive inventory.
        2.  From the header-level **Actions** drop-down list, select **Receive Inventory**.
    -   To receive inventory from a specific planned inbound order:
        1.  In the grid, click the shipment that contains the inbound order from which to receive. The shipment details are displayed.
        2.  In the grid, select the check box next to the inbound order; or click the inbound order from which to receive inventory.
        3.  From the grid-level **Actions** drop-down list, select click **Receive Inventory**.
3.  From the list of items and corresponding planned inbound orders, select the item you want to receive.
4.  Enter information in the [Receiving fields](#Receiving_fields).
5.  Click **Receive**.
    
    **Note**: If serial number or catch quantity capturing is not required for the item, and if the item is tracked at the LPN level and you are receiving a quantity of 1, then the application processes the received inventory. If you did not enter an LPN, an identifier is automatically generated. See [Put away received inventory](#Put_away_received_inventory).
    
6.  If the Number Capture window is displayed, perform the following tasks:
    1.  Under **Quantity**, perform one of the following tasks:
        -   To automatically generate the identifiers, click **Generate LPNs**.
        -   To enter a range of identifiers, click **Enter a range**, then enter a starting and ending value, and then press **Tab**.
        -   To enter individual identifiers, in the text box, enter the first identifier and then press **Enter**. Repeat this process until you have entered the required number of identifiers.
    2.  If the inventory is serialized and requires serial number capturing, then under **Serial Numbers**, enter a serial number for each LPN that requires it.
        
        **Note**: To enter a range of serial numbers, click **Enter Range**, then enter the range of numbers to apply to the inventory, and then press **Tab**.
        
    3.  If the inventory is catch tracked and requires a catch quantity, under **Catch Quantity**, enter a value for each LPN that requires it.
    4.  Click **Receive**.
    5.  See [Put away received inventory](#Put_away_received_inventory).

## Receive empty handling units

In order to receive empty handling units, the transport equipment that contains the empty handling unit must be checked in to a dock door location. See [Handling unit receiving](../receiving-concepts/receiving-processes.md).

**Note**: Use this procedure to receive empty non-serialized handling units. You can receive serialized handling units during receiving, or you can receive empty serialized handling units using an RF or mobile device.

1.  Select **Receiving > Inbound Shipments**.
2.  In the grid, click the inbound shipment against which you want to receive empty handling units. The shipment details are displayed.
3.  Perform one of the following tasks:
    -   In the grid, select the check box next to the planned inbound order against which to receive handling units, and then from the grid-level **Actions** drop-down list, select **Add Empty Unexpected Handling Units**.
    -   In the grid, click the planned inbound order against which to receive handling units, and then from the header-level **Actions** drop-down list, select **Add Empty Unexpected Handling Units**.
4.  Enter information in the [Add Empty Unexpected Handling Units fields](#Add_Empty_Unexpected_Handling_Units_fields).
5.  Click **Receive and Putaway**. The application updates the total quantity of the handling unit type.

## Put away received inventory

1.  If you have not already done so, [Receive inventory](#Receive_inventory).
2.  Click **Putaway**.
3.  If the Select Workstation window is displayed, select a workstation, and then click **Select**.
4.  In the grid, select the check box next to the LPN you want to put away.
    
    **Note**: You can select multiple check boxes to put away multiple LPNs at the same time.
    
5.  Under **Putaway Method**, perform the following tasks:
    1.  In the **Location** field, enter the location to which the inventory should be put away. If you leave this field blank, the application automatically selects the putaway location.
    2.  Select the storage method for the inventory:
        -   **Add To Work Queue**: Directed putaway work is created in the work queue. If you select this option, then you can also select a specific operator or role to which the work is assigned.
        -   **Move Immediately**: The application is immediately updated to reflect that the inventory has been moved to the putaway location.
    3.  To print a label for the LPN, set the **Print Label** field to Yes, and then enter a value in the **Number of Labels** field.
        
        **Note**: If this field is set to Yes, then the application only prints the Pallet Label (pallbl) label format for the inventory.
        
6.  Click **Putaway**.

## Reverse the receipt of an LPN

When you reverse receive an LPN, you are removing the identified and received quantity information from the application. You can configure reverse receiving attributes, including whether reversing the receipt of an LPN is allowed. See [Configure reverse receiving](../../configuration/inbound/receiving/reverse-receiving.md).

1.  Perform one of the following tasks:
    -   View LPNs received against an inbound shipment:
        1.  Select **Receiving > Inbound Shipments**.
        2.  Perform one of the following tasks:
            -   In the grid, click the shipment containing the LPN to reverse receive, and then click **View LPNs**.
            -   If it is not already selected, select **All LPNs**.
        3.  Select the check box for the LPN you want to reverse receive, or click the LPN.
    -   View a grid with a link for an LPN, and then click the LPN.
        
        **Note**: Reverse receiving is only available for LPNs that have been received from an inbound shipment.
        
2.  From the **Actions** drop-down list, select **Reverse LPN**. A confirmation message is displayed.
3.  Click **Yes**.
4.  To receive the LPN again, see [Receive inventory](#Receive_inventory).

## View over, short, and damaged inventory

1.  Select **Receiving > Inbound Shipments**.
2.  In the grid, click the shipment for which to view OSD information. The inbound shipment details are displayed.
3.  Click **OSD/Complete**.
4.  To view items received over the expected quantity, click **Over**.
5.  To view items received under the expected quantity, click **Short**.
6.  To view items that have a Damaged inventory status or are in a Damaged location, click **Damaged**.
7.  Perform one or more of the following tasks:
    -   Click **Basics** and view the information in the [Inventory Basics fields](../../shared-functions/inventory/procedures-for-lpns.md).
    -   Click **Attributes** and view the information in the [Inventory Attributes fields](../../shared-functions/inventory/procedures-for-lpns.md).
    -   Click **Dates** and view the information in the [Inventory Dates fields](../../shared-functions/inventory/procedures-for-lpns.md).
8.  To close the shipment, see [Complete an inbound shipment](#Complete_an_inbound_shipment).

## Complete an inbound shipment

Use this procedure to complete an inbound shipment. When you complete an inbound shipment, the transport equipment is also closed if there are no additional open inbound shipments on the equipment.

1.  Select **Receiving**.
2.  Perform one of the following tasks:
    -   To select a shipment to complete by its associated staging lane:
        1.  Select **Staging**.
        2.  Under **Lanes**, click the status bar of the inbound shipment to complete.
        3.  From the **Actions** drop-down list, select **Review and** **Complete Receiving**.
    -   To select a shipment to complete by the shipment identifier:
        1.  Select **Inbound Shipments**.
        2.  In the grid, click the shipment to complete. The inbound shipment details are displayed.
        3.  Click **OSD/Complete**.
        4.  Click **Complete Inbound Shipment**.
3.  If a prompt is displayed asking if you want to close all of the shipments on the transport equipment, perform one of the following tasks:
    -   To complete all of the inbound shipments and close the transport equipment, click **Yes**.
        
        **Note**: If you close inbound shipments that have not been received, then the application displays a list of the receiving discrepancies. If you are authorized to complete receiving with discrepancies, you can choose to do so without resolving the discrepancies. However, if you close an inbound shipment before all the incoming inventory is received, you must reopen the transport equipment or inbound shipment to receive the remaining inventory. If you are not authorized to close inbound shipments with discrepancies, then the inbound shipments remain in their current status, and inventory information is not sent to the host until all inbound shipments on the transport equipment are received.
        
    -   To complete only the selected inbound shipment and keep the transport equipment open, click **No**.
        
        **Note**: Inbound shipment inventory information is sent to the host immediately after a received shipment is closed. It is recommended that all received inventory be stored before the inbound shipment is closed. If inventory is received but not stored, it is noted as a discrepancy during the completion process.
        
4.  If all of the inbound shipments on the transport equipment are closed, then on the confirmation window, perform one of the following tasks:
    -   To leave the closed equipment at the dock door, select **Leave equipment at door**, and then click **OK**.
    -   To dispatch the transport equipment, select **Dispatch equipment**, and then click **OK**.
    -   To turn around the receiving transport equipment to shipping equipment:
        1.  Select **Turnaround**.
        2.  Click **OK**.
        3.  Enter information in the following fields:
            
            | Field | Description |
            | --- | --- |
            | Carrier | Identifier for a carrier that delivers inbound inventory to the warehouse or outbound shipments to a customer. This is the identifier that will be displayed to users on the application windows and reports. In the application, a carrier can be associated with a customer, order, inbound shipment, outbound shipment, load, and service levels (such as Ground, Next Day, and Saturday Delivery). |
            | To | Location to which the application moves the transport equipment.<br>-   •
                
                **Leave Equipment at current Location**
                
                <br>
                
                Indicates that the transport equipment remains at its current door location.
                
                <br>
            <br>-   •
                
                **Move Equipment to another Location**
                
                <br>
                
                Indicates that the transport equipment will be moved to a new door location. If you select this option, then you must also select a location from the **Select Location** drop-down list.
                
                <br> |
            | Move Equipment Method | Method by which the transport equipment is moved to the location.<br>-   •
                
                **Send work to Work Queue for RF operator**
                
                <br>
                
                Indicates that directed work is created for an operator to move the transport equipment to a new location.
                
                <br>
            <br>-   •
                
                **System moves equipment immediately**
                
                <br>
                
                Indicates the transport equipment's location is immediately updated in the application.
                
                <br> |
            
        4.  Click **OK**.

## Delete an inbound shipment

You can delete inbound shipments that have a status of Expected.

1.  Select **Receiving > Inbound Shipments**.
2.  In the grid, select the check box next to each shipment to delete; or click an inbound shipment.
3.  From the **Actions** drop-down list, select **Delete Inbound Shipment**. A confirmation message is displayed.
4.  Click **OK**.

## Delete an inbound order

1.  Select **Receiving > Inbound Shipments**.
2.  Perform one of the following tasks:
    -   To delete an inbound order:
        1.  Click **Inbound Orders**.
        2.  In the grid, select the check box next to the order or click the order.
        3.  From the **Actions** drop-down list, select **Delete Inbound Order**. A confirmation message is displayed.
    -   To delete a planned inbound order from a shipment:
        
        **Note**: You cannot delete an order for which receiving is in progress or suspended.
        
        1.  In the grid, click the shipment from which you want to delete a planned inbound order. The shipment details are displayed.
        2.  In the grid, select the check box next to the planned inbound order.
        3.  From the **Actions** drop-down list, click **Delete Planned Inbound Order**. A confirmation message is displayed.
3.  Click **Yes**.

## Delete an inbound order line

1.  Select **Receiving > Inbound Shipments**.
2.  Perform one of the following tasks:
    -   To delete an inbound order line:
        1.  Click **Inbound Orders**.
        2.  In the grid, click the order from which to delete an inbound order line. The inbound order details are displayed.
        3.  In the grid, select the check box next to the inbound order line.
        4.  From the **Actions** drop-down list, select **Delete Line**. A confirmation message is displayed.
    -   To delete a planned inbound order line from a shipment:
        1.  In the grid, click the shipment that contains the order from which to delete a planned inbound order line. The inbound shipment details are displayed.
        2.  In the grid, click the order from which you want to delete a planned inbound order line. The order details are displayed.
        3.  In the grid, select the check box next to the planned inbound order line.
            
            **Note**: You cannot delete an order line for which receiving is in progress or suspended.
            
        4.  From the **Actions** drop-down list, select **Delete Line**. A confirmation message is displayed.
3.  Click **OK**.

## Report an inbound quality issue using the Inbound Shipments page

You can report an inbound quality issue using the Inbound Shipments page. Alternatively, see [Add an inbound quality issue using the Receiving Issues page](../receiving-issues/procedures-for-receiving-issues.md).

1.  Select **Receiving > Inbound Shipments**.
2.  In the grid, click the inbound shipment.
3.  Perform one of the following tasks:
    -   To report on a shipment, from the **Actions** drop-down list, select **Report Quality Issue**.
    -   To report on a planned inbound order:
        1.  In the grid, select the check box next to the order.
        2.  From the grid-level **Actions** drop-down list, select **Report Quality Issue**.
    -   To report a quality issue for a planned inbound order line:
        1.  Click the inbound order. Order details are displayed.
        2.  In the grid, select the check box next to the order line.
        3.  From the grid-level **Actions** drop-down list, select **Report Quality Issue**.
4.  Enter information in the [Inbound Quality Issue fields](../receiving-issues/procedures-for-receiving-issues.md).
    
    **Note**: The level at which you report the quality issue determines the information that is automatically populated and view-only. For example, at the planned inbound order line level, the item and supplier are populated, but they are not at the inbound shipment level.
    
5.  Click **Save**.

## View LPNs associated with an inbound shipment

1.  Select **Receiving > Inbound Shipments**.
2.  In the grid, click the shipment for which to view received LPNs. The inbound shipment details are displayed.
3.  Click **View LPNs**.
4.  If it is not already selected, select **All LPNs**.
5.  Perform one or more of the following tasks:
    -   Click **Basics** and view the information in the [Inventory Basics fields](../../shared-functions/inventory/procedures-for-lpns.md).
    -   Click **Attributes** and view the information in the [Inventory Attributes fields](../../shared-functions/inventory/procedures-for-lpns.md).
    -   Click **Dates** and view the information in the [Inventory Dates fields](../../shared-functions/inventory/procedures-for-lpns.md).

## View received empty handling units

Use this procedure to view the empty handling units that are expected or have been received against an inbound shipment.

**Note**: To view empty handling units, the facility must be configured to track inventory handling units. See [Configure handling unit settings](../../configuration/inventory/lpn-handling/handling-unit-settings.md).

1.  Select **Receiving > Inbound Shipments**.
2.  In the grid, click the shipment for which to view empty handling units. The inbound shipment details are displayed.
3.  Click **Handling Units**.
4.  View information in the [Empty Handling Units fields](#Empty_Handling_Units_Fields).

## View detailed inbound shipment information

1.  Perform one of the following tasks:
    -   To view inbound shipment information from the Inbound Shipments page:
        1.  Select **Receiving > Inbound Shipments**.
        2.  In the grid, click the inbound shipment. The inbound shipment details are displayed.
            
            **Note**: You can also view shipment details in the Inbound Shipments grid; additional fields are displayed in the grid that are not displayed when viewing the details of a specific shipment.
            
    -   To view inbound shipment information from the Staging page:
        1.  View the Staging page.
            
            1.  Select one of the following modules: **Receiving** or **Shipping**.
                
            2.  Select **Staging**.
                
            
        2.  Under **Lanes** or **Doors**, click the receiving status bar associated with the inbound shipment. The status bar details are displayed.
        3.  Under **Inbound Shipment**, click the shipment.
    -   To view inbound shipment information from the Door Activity page:
        1.  View the Door Activity page.
            
            1.  Select one of the following modules: **Receiving**, **Shipping**, or **Yard**.
                
            2.  Select **Door Activity**.
                
            
        2.  Under **Doors** or **Yard Locations**, click the receiving status bar associated with the inbound shipment.
        3.  Under **Inbound Shipment**, click the shipment.
2.  View information in the [Inbound Shipment detail fields](#Inbound_shipment_detail_fields).

## View detailed inbound order information

1.  Perform one of the following tasks:
    -   To view planned inbound order information, [view detailed inbound shipment information](#View_detailed_inbound_shipment_information).
    -   To view inbound oder information, select **Receiving > Inbound Shipments**, and then click **Inbound Orders**.
2.  In the grid, click the inbound order. The order details are displayed.
    
    **Note**: You can also view inbound order details in the grid without clicking the order.
    
3.  View information in the [Inbound Order detail fields](#Inbound_order_detail_fields).
4.  In the grid, view information in the [Inbound Order Line detail fields](#Inbound_Order_Line_detail_fields).

## Inbound shipments field listings

### Add or Modify Inbound Shipment fields

 
| Field | Description |
| --- | --- |
| Inbound Shipment | Unique identifier used for inventory tracking for an inbound shipment of inventory. An inbound shipment is a group of orders that are transported to the warehouse together or received together. When inventory arrives at the warehouse on a piece of transport equipment, an inbound shipment represents the contents of the transport equipment; however, one or more inbound shipments can be associated with a piece of transport equipment. |
| Inbound Shipment Reference | Additional information that identifies a group of inbound shipments. For example, a carrier is a typical inbound shipment reference. |
| Transport | Alphanumeric identifier used to identify a piece of transport equipment associated with an outbound load or inbound shipment. Identifier for the carrier with which the transport equipment number is associated. |
| Gross Weight | Weight of the inventory on the shipment that includes its packaging and the containers on which it is shipped. |
| Number of Pallets | Number of pallets on the inbound shipment. |
| Freight Cost | Cost of shipping product, based on the selected currency code. This value is for information only; the application does not verify this information during receiving. |
| Number of Cases | Number of cases of inventory on the inbound shipment. |
| Transportation Method | Method in which the inbound order will be or was transported to the warehouse. This value is for information only; the application does not verify this information during receiving. |
| Expected Receipt Area | Area from which the product on this inbound shipment will be received into the warehouse. When putting product away, the application uses the storage rules that are defined for the building in which this area exists. This value is required and can be modified up until the time that inventory is identified against the planned inbound order associated with the inbound shipment. |
| Device Code | Unique identifier for a piece of equipment such as a radio frequency (RF) or mobile device that has access to or communicates with the application. The device code is the display name for the device and represents a logical location during warehouse operations. For example, during picking, an inventory display shows the device code as the location of the inventory until the inventory is deposited. |
| Expected Date | Date on which the inbound shipment or inbound order is expected to arrive at the warehouse. |
| Shipped Date | Date on which the inbound shipment originated. |
| Produce Labels | If Yes, then the application prints labels when the incoming inventory on the inbound shipment is identified. Select Yes if the inventory on the inbound shipment will be identified by RF operators, and you want to provide them with printed labels containing the LPN and storage location when the inventory is identified.<br > **Note**: If this field is set to Yes, then the application only prints the Pallet Label (pallbl) label format for the identified inventory.<br > If No, then the application does not print labels for the inventory on the inbound shipment. |
| Printer | Printer that will print the labels. Only available when the **Produce Labels** field is set to Yes. |

### Add Inbound Order fields

 
| Field | Description |
| --- | --- |
| **Inbound Order** | Identifier for an inbound order or planned inbound order that is associated with a specific supplier. |
| BOL | Bill of lading (BOL) number assigned to the planned inbound order. The BOL is a carrier's contract and receipt for goods that it agrees to transport from one place to another, and to deliver to a designated person or assignees. |
| Order Type | Code that represents the purpose of the inbound order.<br>-   • **Customer Return**: Indicates that the inbound order is for a blanket return, such as in a recall of shipped inventory.
<br>-   • **Production**: Indicates that the inbound order is an internal work order.
<br>-   • **Inbound Order**: Indicates that the inbound order is an expected order for inventory.
<br>-   • **Flow Purchase Order**: Indicates that the inbound order is of ordered inventory from an external source.
<br>-   • **Work Order Receipt**: Indicates that the inbound order is from an internal work order for assembly, disassembly, conversion, kitting, or repacking. |
| Supplier | Identifier for a supplier. A supplier can be an individual, organization, or another warehouse within your own organization from which you repeatedly receive inventory or handling units. |
| Client | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. |
| Originator Reference | Information that identifies the shipment in the supplier's system. This information can be defined by the supplier and used for reporting and host transactions. |
| SAD Number | Shipment and delivery (SAD) number that is used for reporting and host transactions. |
| Waybill | Bill of lading number for the inbound order. The bill-of-lading number typically is displayed on the receiving paperwork. |
| Order Status | Indicates the processing status of an order. This field is used to determine whether items on the order are currently available for receiving.<br>-   • **Open**: Order is available to be received against.
<br>-   • **Suspended**: Order is being researched. Receiving should be temporarily stopped until the research is complete and the order is reset to an Open status.
<br>-   • **Closed**: Order can no longer be received against and should be archived for historical purposes. |
| Receipt Date | Date on which the order is to be received. |
| Customs Type | Identifier that defines the type of customs tracking required for the inventory on the inbound order (or line). Defining a customs type on the inbound order overrides the customs type defined for the items on the order. If you select a bonded customs type (Customs or Excise) for the entire order, you will not be able to override specific customs information for the items on the order lines. Only displayed when customs functionality is enabled for the warehouse.<br>-   • **Blank (no selection)**: Customs related fields are available for edit. Customs information is based off the item if no customs information is defined on the order line.
<br>-   • **Free**: None of the inventory on this inbound order is under bond. Customs information is cleared from the order line and the customs related fields are not available for edit.
<br>-   • **Customs**: All of the inventory on this inbound order is under bond. Customs related fields on the order line are not available for edit.
<br>-   • **Excise**: All of the inventory on this inbound order is under bond and requires a duty stamp. Customs related fields on the order line are not available for edit. |
| Do you want to immediately begin adding lines to this Inbound Order | If Yes, then after you click **Save**, the Add Inbound Order Line window is displayed, and you can immediately start adding order lines to the order.<br > If No, then after you click **Save**, you are not immediately prompted to add order lines, but you can add lines at a later time.<br > This field is only available when adding a new inbound order (unplanned). |
| Add Line | Indicates that you want to immediately begin adding planned inbound order lines to the planned inbound order. If selected, then after you click **Save**, the Add Planned Inbound Order Line window is displayed, and you can immediately begin adding lines.<br > If deselected, then after you click **Save**, the planned inbound order is saved without order lines, but you can add lines at a later time.<br > This field is only available when adding a planned inbound order. |

### Inbound Order Line fields

 
| Field | Description |
| --- | --- |
| Line Number | Unique identifier for an inbound order line. The order line is the section of an order that provides detailed information about an individual item that the order requests. |
| Sub Line | Identifying number assigned to an inbound order sub-line. By default, the first line of each order line has a sub-line number of 0000, and it identifies the finished product. The remaining sub-lines are numbered sequentially, beginning with 0001, and they identify the component items required for the order line. |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Expected Quantity | Total number of eaches that are expected to be received from the inbound shipment, inbound order, or inbound order line. |
| Description | Text that further describes the item. |
| Receive Status | Value that defines the quality or disposition of inventory. When defined for an item, it represents the status assigned to inventory by default during receiving. |
| Item Client | Name of the client who stores this item in the facility. This field is only displayed in a 3PL environment. |
| From Host Account | Account number for the customer or supplier host system from which order information is sent. This information is optionally provided by the customer or supplier and is used for their reporting and host transaction purposes only. |
| To Host Account | Account number for the customer or supplier host application to which information regarding this order or shipment will be sent. This information is optionally provided by the customer or supplier and is used for their reporting and host transaction purposes only. |
| Distribute Overage | Indicates that any unplanned inventory received over the expected amount for distributions tied to the order line should be pushed out to customers as an over distribution instead of holding the inventory as stock quantity. If you want to over distribute any excess inventory received for this inbound order, this check box must be selected. In order for a store to receive the over distribution, the store's distribution with which this order line is associated must also allow over distribution, otherwise the store will not receive any excess inventory. |
| Immediate Ownership Transfer | Indicates that the ownership of consigned inventory received against the inbound order line is immediately transferred to the warehouse upon receipt. If this check box is cleared, ownership is retained by the consignee (supplier) until the consignment change point is reached, as defined in the supplier configuration. |
| Lot | Identifier assigned to a quantity of inventory that is uniquely identified during the manufacturing process for the purpose of tracking an attribute of that inventory, such as its expiration date. Lots differentiate distinct groups of inventory that have the same item. Lots are user defined and are not necessarily unique since the same lot can be applied to different items. However, lot and item number combinations must be unique. If a lot has been specified on the planned inbound order line, then during receiving, the application verifies that the lot entered by the operator is identical to the lot specified. If the operator enters a different lot number, then the application retains the line for the original lot number and creates a new planned inbound order line for the new lot number. |
| Expiration Date | Date and time that the inventory will expire. During receiving or inventory identification, this date defaults to the date calculated by the application based on the manufactured date and aging profile assigned to the item number. If you are identifying date-tracked inventory, you can override the application-calculated date by manually entering an expiration date. This is useful when you see that the inventory will expire faster than it normally would, or the inventory is marked with an expiration date. If you manually enter an expiration date, it cannot be changed. The date and time are stored in the database and displayed in the web client in the original captured time zone, not converted to a different time zone, such as a user preferred time zone. The expiration date is used for first expired, first out (FEFO) order processing so that inventory with the oldest expiration date is allocated first. This field only available if the item requires this attribute.  |
| Manufactured Date | Date on which the item identified on this line was manufactured. The date is stored in the database and displayed in the web client in the original captured time zone, not converted to a different time zone, such as a user preferred time zone. If left blank, this date defaults to the date the inventory was identified, or received. This date is the basis of application date calculations for date-controlled items. Typically, this date is used for first in, first out (FIFO) order processing. Only available if the item is date controlled. |
| Commodity Code | Code that identifies a commodity. Commodities are categories created to group inventory that has the same qualities and specifications, regardless of their source. For example, wheat is a commodity. Commodity codes are standardized to provide carriers with a standard by which to determine pricing and to simplify the shipment process. The Commodity Code is usually printed on the bill of lading (BOL). If the commodity is printed on the BOL, all products of the same commodity are totaled. |
| Customs Type | Identifier for the type of customs tracking required for the inventory on the inbound order line. Defining a customs type on the inbound order line overrides the customs type and customs information defined for the items on the order. Only displayed when customs functionality is enabled for the warehouse. Only available when the **Customs Type** on the inbound order is Blank (no selection).<br>-   • **Blank (no selection)**: Customs related fields are available for edit. Customs information is based off the item.
<br>-   • **Free**: None of the inventory on this inbound order line is under bond. Customs information is cleared from the order line and the customs related fields are not available for edit.
<br>-   • **Customs**: All of the inventory on this inbound order line is under bond. Customs related fields on the order line are available for edit.
<br>-   • **Excise**: All of the inventory on this inbound order line is under bond and requires a duty stamp. Customs related fields on the order line are available for edit.
<br>-   • **Item Default**: The item's default customs type is used. |
| Consignment ID | Unique identifier assigned to a receipt of bonded inventory. A customs consignment is an application-generated ID number that consists of a prefix (the warehouse ID) plus the next value in the customs consignment ID sequence. For example, if your warehouse ID is WMD1 and the next number in the sequence is 123456, then the customs consignment ID will be WMD1123456.<br > **Note**: You can configure the application to automatically populate the Consignment ID field with a consignment number. If there is no customs type specified on the planned inbound order or on the item, the consignment ID will be cleared from this field.<br > Only displayed if Customs functionality is enabled for the warehouse. Only available if the item is configured for customs tracking. |
| Customs Cost | Monetary amount that is paid to customs for the item. The amount is paid in the currency defined in the currency field. Only available if the **Customs Item Type** is either Customs or Excise. |
| VAT Code | Code for the value added tax (VAT) for the item. A customs VAT is charged on goods and some services that are imported from countries outside the European Unit (EU) and brought into the United Kingdom (UK) from other EU countries. It is also charged on most goods and services that VAT-registered businesses provide in the UK.<br>-   • **Standard**: The standard customs VAT rate is charged for this item.
<br>-   • **Zero**: No customs VAT is charged for this item. |
| Default Origin Code | Country in which the item was manufactured. This value is displayed by default on the planned inbound order line for the item but during receiving it can be changed. Only available if the value for **Customs Type** is either Customs or Excise. |
| Duty Stamp Tracked | Indicates that the inventory requires a duty stamp. A duty stamp is a form of tax on certain excise goods, the payment of which is certified by the attaching or impressing of an official stamp on the taxed item. Only available if customs is enabled for the warehouse. |

### Receiving fields

 
| Field | Description |
| --- | --- |
| Planned Inbound Order | Identifier for a planned inbound order that is associated with a specific supplier. A planned inbound order is an authorization to receive specific inventory and quantities from a supplier. It is used, but not required, to receive inventory into the warehouse. |
| LPN | Unique identifier for inventory. Typically, an LPN refers to a pallet; however, it can refer to inventory received at less than pallet quantity. The LPN is the license plate by which the inventory is tracked in the facility. |
| Item | Identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). Before the application can effectively store, track, and manipulate inventory, you must assign an item identifier and define the attributes of each item you want to track. When defining an item, you specify information such as how the item is packaged and handled, along with details that define how it should be received, stored, allocated, shipped, counted, and valued (cost information). |
| Item Client | Name of the client who stores this item in the facility. This field is only displayed in a 3PL environment. |
| Description | Text that further describes the item. |
| Quantity | Quantity of the item in the unit of measure (UOM) to receive. |
| UOM | Packaging unit of measure (UOM), such as a pallet, case, or each, in which you want to receive the item. |
| Catch Quantity | Actual measured quantity of the inventory to receive. Catch quantity is typically obtained at receipt and may be verified prior to shipment. |
| Inventory Status | Value that defines the quality or disposition of the inventory. |
| Footprint | Code that identifies an item footprint, which defines the packaging dimensions and units of measure (UOM) for the item to which it is associated. Only the footprint codes defined for the item are available for selection. |
| Lot | Identifier assigned to a quantity of inventory that is uniquely identified during the manufacturing process for the purpose of tracking an attribute of that inventory, such as its expiration date. Lots differentiate distinct groups of inventory that have the same item. Lots are user defined and are not necessarily unique since the same lot can be applied to different items. However, lot and item number combinations must be unique. If a lot has been specified on the planned inbound order line, then during receiving, the application verifies that the lot entered by the operator is identical to the lot specified. If the operator enters a different lot number, then the application retains the line for the original lot number and creates a new planned inbound order line for the new lot number. |
| Supplier Lot | Identifier that is an attribute of an item or item and lot combination and is assigned by the item's supplier. A supplier lot number used to uniquely identify and track the inventory to which it is assigned. The supplier lot number is a different attribute than the lot number, which is a manufacturer or production lot number. |
| Handling Unit Type | Handling unit type assigned to the LPN. A handling unit type is a category that classifies a group of handling units (for example, pallets, totes, or equipment) that share the same characteristics such as size and weight, as well as whether they are serialized, temporary, or considered a container. |
| Handling Unit | Unique identifier for a serialized handling unit. A serialized handling unit is a single object (such as a container or pallet) associated with a warehouse that has value and that you want to track as an individual. A handling unit may or may not contain inventory and may or may not be associated with a specific serial number. This field is only displayed if inventory handling unit tracking is enabled for the warehouse, and if a serialized handling unit type is specified in the **Handling Unit Type** field. |
| Sub Handling Type | Identifier for a handling unit type assigned to a sub-LPN. This field is only displayed if inventory handling unit tracking is enabled for the warehouse, and if the application allows inventory sub-LPNs to be associated with handling units. |
| LPN Attribute | If Yes, the attribute is required by default for a pallet LPN of inventory that uses the footprint. An LPN attribute is a configurable attribute; therefore, the list of available LPN attributes may vary depending on what is configured and enabled for your warehouse. LPN attributes that are enabled are displayed during inventory identification, inventory attribute change operations, and picking (if specified on an order line).<br > If No, the attribute is not required by default for the pallet LPN. |
| Origin Code | Identifier assigned to an item to identify the item's country of origin. It is typically used for export paperwork. Origin codes are user defined. |
| Revision Level | Identifier that is assigned to an item number to differentiate revisions of the same item number. |
| Case Identifier | Unique identifier for inventory being tracked at the sub-LPN (case) level. A sub-LPN is always a uniquely identifiable portion of the pallet LPN. This field only displays if the item requires tracking at the sub-LPN level. |
| Piece Identifier | Unique identifier for inventory being tracked at the detail (each) level. A detail LPN is always a uniquely identifiable portion of the pallet LPN. This field only displays if the item requires tracking at the detail level. |
| Customs Type | Identifier that defines the type of customs tracking required for the inventory on the planned inbound order. The customs type can only be modified when the planned inbound order status is Excepted or Pending. Defining a customs type on the planned inbound order overrides the customs type defined for the items on the order. If you select a bonded customs type (Customs or Excise) for the entire order, you cannot override specific customs information for the items on the order lines. Only displayed if Customs functionality is enabled for the warehouse.<br>-   • **Blank (no selection)**: Customs related fields are available for edit on the order line. Customs information is based off the item if no customs information is defined on the order line.
<br>-   • **Free**: None of the inventory on this planned inbound order is under bond. Customs information is cleared from the order line and the customs related fields are not available for edit.
<br>-   • **Customs**: All of the inventory on this planned inbound order is under bond. Customs related fields on the order line are not available for edit, with the exception of the customs consignment ID.
<br>-   • **Excise**: All of the inventory on this planned inbound order is under bond and requires a duty stamp. Customs related fields on the order line are not available for edit, with the exception of the customs consignment ID. |
| Commodity Code | Code that identifies a commodity. Commodities are categories created to group inventory that has the same qualities and specifications, regardless of their source. For example, wheat is a commodity. Commodity codes are standardized to provide carriers with a standard by which to determine pricing and to simplify the shipment process. The Commodity Code is usually printed on the bill of lading (BOL). If the commodity is printed on the BOL, all products of the same commodity are totaled. |
| Consignment ID | Unique identifier assigned to a receipt of bonded inventory. A customs consignment is an application-generated ID number that consists of a prefix (the warehouse ID) plus the next value in the customs consignment ID sequence. For example, if your warehouse ID is WMD1 and the next number in the sequence is 123456, then the customs consignment ID will be WMD1123456.<br > **Note**: You can configure the application to automatically populate the Consignment ID field with a consignment number. If there is no customs type specified on the planned inbound order or on the item, the consignment ID will be cleared from this field.<br > Only displayed if Customs functionality is enabled for the warehouse. Only available if the item is configured for customs tracking. |
| Customs Cost | Monetary amount that is paid to customs for the item. The amount is paid in the currency defined in the currency field. Only available if the **Customs Item Type** is either Customs or Excise. |
| VAT Code | Code for the value added tax (VAT) for the item. A customs VAT is charged on goods and some services that are imported from countries outside the European Unit (EU) and brought into the United Kingdom (UK) from other EU countries. It is also charged on most goods and services that VAT-registered businesses provide in the UK.<br>-   • **Standard**: The standard customs VAT rate is charged for this item.
<br>-   • **Zero**: No customs VAT is charged for this item. |
| Default Origin Code | Country in which the item was manufactured. This value is displayed by default on the planned inbound order line for the item but during receiving it can be changed. Only available if the value for **Customs Type** is either Customs or Excise. |

### Add Empty Unexpected Handling Units fields

 
| Field | Description |
| --- | --- |
| **Handling Unit Type** | Category that classifies a group of handling units (for example, pallets, totes, transport equipment, or vehicles) that share the same characteristics such as size and weight, as well as whether they are serialized, temporary, or considered a container. The application tracks the on-hand quantity of handling units by type and, for serialized handling units, by handling unit identifier. |
| **Handling Unit Status** | Current condition of the handling unit, such as active or inactive. This value is only used for reporting purposes. |
| **Client** | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. |
| **Quantity** | Quantity of the handling unit type to be received against the planned inbound order. |

### Distribution Information fields

 
| Field | Description |
| --- | --- |
| Distribution Type | Name of the distribution type assigned to the distribution. The distribution type specifies the manner in which the application assigns distribution inventory to customers. See [Distribution Types](../../configuration/outbound/distribution/distribution-types.md). |
| Department | Identifier for a department within the customer's facility. A department can be specified for a customer type, customer, order, order line, distribution, and item. It can be used to group information for the purpose of sorting and searching data, consolidating distribution inventory in customer-specific storage locations, and to help customers direct inventory to the proper department when it arrives at their facility. |
| Over Distribute | If Yes, then if there is unplanned, excess inventory identified for the distribution, the application allows for an over distribution of the inventory to customers. Over distribution prevents additional inventory not originally listed on the planned inbound order from being held as stock, and instead the application pushes the inventory to customers who would then receive more product than originally planned in the distribution. In order for a customer to receive the over distribution, the inbound order line with which the distribution is associated must allow over distribution, otherwise the customer will not receive any excess inventory.<br > If No, the distribution does not allow for over distribution. |
| Allocate From Storage for Shorts | If Yes, then inventory can be allocated from storage to fill any shortages the distribution may have. When inventory is allocated from storage, a new order line is created and associated with the original distribution's outbound order, so that the order lines are allocated together and planned on the same shipment.<br > If No, then inventory cannot be allocated from storage to fill a shortage. |
| Promotion Code | User-defined code that identifies the specific promotion for which the distribution is being created or modified. The **Promotion Code** can be used to search for and select distributions assigned to the promotion. |
| Auto-Create Outbound Order | If Yes, then the distribution order and order line is automatically created by the application based on the information that you provide on the CUSTOMERS AND QUANTITIES page, such as the order type and allocation profile.<br > If No, then you must provide the existing outbound order and order line information for the distribution. |

### Distribution Customers and Quantities fields

 
| Field | Description |
| --- | --- |
| Customer | Identifier for the customer to whom the distribution inventory is shipped. |
| Address | Identifier of the address to which the distribution is shipped. The address name typically identifies the individual or organization with which an address is associated. The application automatically fills in this field when you select a customer. |
| Quantity | Quantity of the item to be shipped to the specified customer for the distribution. The sum of all customer quantities on the distribution cannot exceed the Total Quantity to Distribute. |
| Outbound Order | Unique number that identifies the existing order and line for which you want to create a distribution. Only available if the **Auto-Create Outbound Order** field is set to No. |
| Processing Priority | Number that indicates the order in which you want this distribution to be selected and processed as compared to other distributions. Distributions with the highest priority will be selected and processed by the application first. Priorities range from 1 to 9 with 1 being the highest priority. This field defaults to the processing priority configured for the customer. See [Add or modify a customer](../../configuration/partners/customers/existing-customers.md). |
| Late Ship Date | Last day of the outbound shipment range. To define a single shipment date, enter the first day of the shipment range. The application uses both delivery and ship dates to consolidate order lines into shipments, depending on the values defined for order consolidation. |
| Allocation Profile | Default level of quality at which the customer is willing to accept inventory. An allocation profile is a prioritized list of inventory statuses that identifies which statuses can be shipped. It can be applied to both date-controlled and non-date-controlled items. |
| Order Type | Name of an outbound order type. An order type is a category that is used to group outbound orders based on the warehouse processing necessary to fulfill the order. For example, customer orders and distribution orders require different processing by the application, and so an order type can be assigned to categorize each order separately. The application uses order types, for example, to identify orders that are eligible for bulk picking, or to direct orders to specific destination locations. Only available if the **Auto-Create Outbound Order** field is set to Yes. |
| Early Delivery Date | First day of the delivery range. The delivery range identifies a series of expected delivery dates for the outbound order line. The application uses both delivery and ship dates to consolidate order lines into outbound shipments, depending on the values defined for order consolidation. |
| Early Ship Date | First day of the outbound shipment range. The shipment range identifies a series of dates on which an outbound order line must be shipped. The application uses both delivery and ship dates to consolidate order lines into shipments, depending on the values defined for order consolidation. |
| Late Delivery Date | Last day of the delivery range. To define a single delivery date, enter the first day of the delivery range. The application uses both delivery and ship dates to consolidate outbound order lines into outbound shipments, depending on the values defined for order consolidation. |

### Empty Handling Units Fields

 
| Field | Description |
| --- | --- |
| Supplier | Identifier for a supplier. A supplier can be an individual, organization, or another warehouse within your own organization from which you repeatedly receive inventory or handling units. |
| Inbound Order | Identifier for an inbound order or planned inbound order that is associated with a specific supplier. |
| Handling Unit Type | Category that classifies a group of handling units (for example, pallets, totes, transport equipment, or vehicles) that share the same characteristics such as size and weight, as well as whether they are serialized, temporary, or considered a container. The application tracks the on-hand quantity of handling units by type and, for serialized handling units, by handling unit identifier. |
| Client | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. |
| Handling Unit LPN | Unique identifier for a handling unit that is tracked as an individual as well as collectively by handling unit type. You may want to track valuable handling units, such as CHEP pallets, as individuals. Handling units tracked as individuals can be further identified with a serial number. |
| Expected Quantity | Number of empty handling units of the specified handling unit type that are expected to be received against the inbound shipment. If multiple serialized handling units of the same type are expected, each handling unit is displayed as a separate record. |
| Received Quantity | Number of empty handling units of the specified handling unit type that have been received against the inbound shipment. If multiple serialized handling units of the same type have been received, each handling unit is displayed as a separate record. |
| Serial Number | Alphanumeric value that can represent the serial number associated with an individual handling unit. |
| Manufacturer ID | Name of the company that produced the individual handling unit. |
| Model | Alphanumeric model number for the individual handling unit. Manufacturers use model numbers to differentiate similar products. |
| Purchase Date | Date on which the individual handling unit was purchased. |
| Warranty Date | Date on which the warranty of the individual handling unit expires. |
| Parent Handling Unit LPN | Unique identifier for another handling unit on or in which this (child) handling unit resides. The two handling units are tracked together; the location of the child handling unit is the same as that of the parent. You cannot specify another child handling unit as a parent handling unit; however, multiple (child) handling units can be associated with a parent. Only available when the handling unit type category is set to Inventory. |

### Inbound Shipment detail fields

 
| Field | Description |
| --- | --- |
| Transport | Alphanumeric identifier used to identify a piece of transport equipment associated with an outbound load or inbound shipment. Identifier for the carrier with which the transport equipment number is associated. |
| Inbound Shipment | Unique identifier used for inventory tracking for an inbound shipment of inventory. An inbound shipment is a group of orders that are transported to the warehouse together or received together. When inventory arrives at the warehouse on a piece of transport equipment, an inbound shipment represents the contents of the transport equipment; however, one or more inbound shipments can be associated with a piece of transport equipment. |
| Status | Application-assigned status that identifies the condition of the inbound shipment as it moves through the receiving process.<br>-   • **Expected**: Inbound shipment is created or downloaded and ready to be checked in for receiving.
<br>-   • **Checked In**: Inbound shipment is checked in to a receiving staging location or, if it is on a piece of transport equipment, checked in to a dock door.
<br>-   • **Receiving**: Receiving from the inbound shipment has been started. The inbound shipment may be located in a receiving staging location or associated with a piece of transport equipment parked at a dock door.
<br>-   • **Suspended**: Receiving from the transport equipment has been started, but because the equipment was moved from the dock door to a yard location, receiving has been suspended. If receiving work exists in the work queue for this shipment, it is also suspended. Receiving work will not be offered to RF operators until the transport equipment is moved back to a dock door location.
<br>-   • **Closed**: Receiving has been completed for the inbound shipment. |
| Auto Receive Status | Status of auto receiving for the shipment. Auto receiving is a process in which the application immediately receives all of the LPNs on an inbound shipment and systematically moves them to a receiving staging lane. Auto receiving status can be In Progress, Complete, or Complete with Error. See [ASN auto receiving from trusted suppliers](../receiving-concepts.md). |
| Check In | Date and time at which the transport equipment associated to the inbound shipment was checked in to a dock door; or when the inbound shipment was checked in to a staging location if there is no equipment. |
| Receipt Confirmation Date | Date on which the receipt confirmation transaction was sent to the host. A receipt confirmation identifies the inventory and quantities that have been put away to locations from which the inventory can be allocated. A receipt confirmation is used to inform the host that the inventory is available for allocation to fulfill orders. |
| Orders | Number of planned inbound orders on the inbound shipment. |
| Location | Location at which the transport equipment associated with the inbound shipment is checked in; or the location at which the inbound shipment is checked in if there is no equipment. |
| Received | Percentage of inventory that has been received against the expected quantity. Additionally, an X of Y value displays the number of eaches that are received out of the total number of expected eaches; for example, (50 of 100). |
| Stored | Percentage of the expected inventory that has been received and stored. Additionally, an X of Y value displays the number of eaches that are stored out of the total number of expected eaches; for example, (50 of 100). |
| Measures | Measurement values of the inbound shipment such as the number of pallets, the weight, and the load volume. |
| Expected Quantity | Total number of eaches that are expected to be received from the inbound shipment, inbound order, or inbound order line. |
| Identified Quantity | Total number of eaches that have been identified from the inbound shipment. |
| Received Quantity | Total number of eaches that have been received against the inbound shipment. |
| Stored Quantity | Total number of eaches from the inbound shipment that have been stored (put away). |
| Suppliers | Number of suppliers from which inventory on the inbound shipment is sent. A supplier is a vendor from which you receive inventory. |

### Inbound Order detail fields

 
| Field | Description |
| --- | --- |
| Inbound Order | Identifier for an inbound order or planned inbound order that is associated with a specific supplier. |
| Order Type | Inbound order type that represents a category used to group inbound orders that have the same purpose and processing characteristics, such as unplanned inbound orders, warehouse transfers, or customer returns. |
| Location | Location of the inbound order. If the inbound shipment is not checked in yet, this field is blank (no value). When the inbound shipment is checked in, the location for the inbound order is the receiving door at which the transport equipment was checked in to. |
| Lines | Number of order lines on the inbound order. |
| Expected Date | Date on which the inbound shipment or inbound order is expected to arrive at the warehouse. |
| Arrival Date | Date and time at which the inbound shipment, on which the order is included, was checked in. All inbound orders associated with the same inbound shipment or transport equipment have the same arrival date. |
| Customs Type | Identifier that defines the type of customs tracking required for the inventory on the inbound order (or line). Defining a customs type on the inbound order overrides the customs type defined for the items on the order. If you select a bonded customs type (Customs or Excise) for the entire order, you will not be able to override specific customs information for the items on the order lines. Only displayed when customs functionality is enabled for the warehouse.<br>-   • **Blank (no selection)**: Customs related fields are available for edit. Customs information is based off the item if no customs information is defined on the order line.
<br>-   • **Free**: None of the inventory on this inbound order is under bond. Customs information is cleared from the order line and the customs related fields are not available for edit.
<br>-   • **Customs**: All of the inventory on this inbound order is under bond. Customs related fields on the order line are not available for edit.
<br>-   • **Excise**: All of the inventory on this inbound order is under bond and requires a duty stamp. Customs related fields on the order line are not available for edit. |

### Inbound Order Line detail fields

 
| Field | Description |
| --- | --- |
| Line | Unique identifier for an inbound order line. The order line is the section of an order that provides detailed information about an individual item that the order requests. |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Distribution | Quantity of the item on the inbound order line that is to be distributed. Distribution is an automatic process that fulfills one or more outbound order lines with inventory from an inbound order line. |
| Quantity | Total quantity of the item expected on the inbound order line. |
| Customs Type | Identifier for the type of customs tracking required for the inventory on the inbound order line. Defining a customs type on the inbound order line overrides the customs type and customs information defined for the items on the order. Only displayed when customs functionality is enabled for the warehouse. Only available when the **Customs Type** on the inbound order is Blank (no selection).<br>-   • **Blank (no selection)**: Customs related fields are available for edit. Customs information is based off the item.
<br>-   • **Free**: None of the inventory on this inbound order line is under bond. Customs information is cleared from the order line and the customs related fields are not available for edit.
<br>-   • **Customs**: All of the inventory on this inbound order line is under bond. Customs related fields on the order line are available for edit.
<br>-   • **Excise**: All of the inventory on this inbound order line is under bond and requires a duty stamp. Customs related fields on the order line are available for edit.
<br>-   • **Item Default**: The item's default customs type is used. |
| Received | Percentage of inventory that has been received against the expected quantity. Additionally, an X of Y value displays the number of eaches that are received out of the total number of expected eaches; for example, (50 of 100). |
| Stored | Percentage of the expected inventory that has been received and stored. Additionally, an X of Y value displays the number of eaches that are stored out of the total number of expected eaches; for example, (50 of 100). |
| Attributes | Values for the following attributes that can be specified for the inbound order line:<br>-   • **Lot**: Identifier assigned to a quantity of inventory that is uniquely identified during the manufacturing process for the purpose of tracking an attribute of that inventory, such as its expiration date. Lots differentiate distinct groups of inventory that have the same item. Lots are user defined and are not necessarily unique since the same lot can be applied to different items. However, lot and item number combinations must be unique.
<br>-   • **Revision Level**: Identifier that is assigned to an item number to differentiate revisions of the same item number.
<br>-   • **Origin Code**: Identifier assigned to an item to identify the item's country of origin. It is typically used for export paperwork. Origin codes are user defined. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2023 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
