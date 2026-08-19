---
title: "Customer Types"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/customer_types.htm"
source: "/content/customer_types.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Partners"
  - "Customers"
  - "Customer Types"
sections:
  - "Add or modify a customer type"
  - "Delete a customer type"
  - "Customer Type fields"
images: []
source_sha1: 419e14f74cb9486d311f05662f09c30a9ca4b9db
---
# Customer Types

A customer type is a method for grouping customers that have the same order processing requirements, such as for acceptable inventory statuses, date-controlled inventory attributes, carriers, handling unit types, and LPN attributes. You create a customer type, for example, to define the shared processing requirements for a chain of stores (such as grocery or convenience stores). The customer type is also used for searching, sorting, and reporting purposes.

The values defined for a customer type are only applied to the respective fields on an order or order line if the fields are not already populated when the order is created or by customer-specific values.

For example, if a carrier group is specified for a customer type, and it is not specified on the order line or by the customer record, then the application defaults the appropriate values from the customer type record to the order line.

## Add or modify a customer type

1.  Select **Configuration > Partners > Customers > Customer Types.**
2.  Perform one of the following tasks:
    -   To add a customer type, click **Add.**
    -   To modify a customer type, in the grid, click the customer type.
    -   To copy a customer type, select the check box next to the customer type, and then click **Copy**.
3.  Enter information in the [Customer Type fields](#Customer_Type_fields), and then click **Save**.
4.  To configure handling units for a customer:
    1.  Under **HANDLING UNIT TYPES**, click **Handling Units Types**.
    2.  In the **Available** column, select the check box next to the handling unit types that apply.
    3.  In the **Picking UOM** column, select the UOM that the customer requires to be shipped on the selected handling unit type.
    4.  Click **Apply**.
5.  Click **Save**.

## Delete a customer type

1.  Select **Configuration > Partners > Customers > Customer Types**.
2.  In the grid, select the check box next to the customer type that you want to delete.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Customer Type fields

 
| Field | Description |
| --- | --- |
| Customer Type | Name for a group of customers that share the same attributes defined by the customer type, such as for order processing, packaging, and shipping. It is used to provide attribute information that populates customer-related fields on an order line that were not populated either when the order line was created or by the values inherited from the customer profile. It is also used to group customers for reporting purposes. |
| Customer Type Description | Description that further defines the customer type identifier. |
| Department | Identifier for a department within the customer's facility. A department can be specified for a customer type, customer, order, order line, distribution, and item. It can be used to group information for the purpose of sorting and searching data, consolidating distribution inventory in customer-specific storage locations, and to help customers direct inventory to the proper department when it arrives at their facility. |
| Manufacturer | Name of the organization that manufactures the inventory supplied to a customer. The manufacturer is required when the application is configured to produce UCC128 (Uniform Commercial Code) identifiers for shipment labeling. |
| Create Shipment By | Method by which the customer wants their orders to be grouped into shipments. The method determines how the application builds orders into shipments.<br>-   • **Bill-To Customer**: All of the order lines in a shipment must be for the same bill-to customer. The bill-to customer is the address name of the location to which billing information is sent.
<br>-   • **Outbound Order Number**: All of the order lines in a shipment must be for the same order. A shipment consists of a single order.
<br>-   • **Route-To Customer**: All of the order lines in a shipment must be for the same route-to customer. The route-to customer is the address name of the location to which the shipment is sent (such as a distribution hub), before being directed to the ship-to customer.
<br>-   • **Ship-To Customer**: All of the order lines in a shipment must be for the same ship-to customer. The ship-to customer is the address name of the final destination of the shipment.
<br > **Note**: If additional values were configured for your application, those values will also be available for selection. |
| Pallet Building | Rule that determines the attributes that must be the same for inventory to be consolidated on the same pallet during pallet build operations. Pallet building is a process in which cases or repack cartons are consolidated after picking to create a new pallet. For example, if the rule is based on the shipment, then when an operator attempts to build a pallet, the application verifies that each case on the pallet is part of the same shipment. Alternatively, if the rule is based on staging lane, then inventory from different shipments can be added to the same pallet as long as the destination staging location is the same.<br > The options that are available are defined in shipping staging configuration. |
| Allocation Search Path Group | Name associated with allocation search paths for the purpose of grouping them for use during order allocation. If a search path group is specified on the order line, the application uses only the search paths that have a matching group name to find inventory for that order. This process reduces processing time by limiting the number of search paths the application uses during order allocation.<br > An allocation search path group can be assigned to a customer type, order line, allocation search path, and replenishment search path. |
| Inventory Rotation Method | Value that represents the order in which the allocation process selects available inventory for allocation. Select an inventory rotation method if you want the application to search for inventory based on date processing or location.<br>-   • **FEFO-ORDER-BY and FEFO-ORDER-BY-ABSOLUTE**: First-expiration, first-out. The first inventory to expire will be selected first.
<br>-   • **FIFO-ORDER-BY and FIFO-ORDER-BY-ABSOLUTE**: First-in, first-out. The oldest inventory will be selected first.
<br>-   • **LEFO-ORDER-BY and LEFO-ORDER-BY-ABSOLUTE**: Last-expiration, first-out. The last inventory to expire will be selected first.
<br>-   • **LIFO-ORDER-BY and LIFO-ORDER-BY-ABSOLUTE**: Last-in, first-out. The newest inventory will be selected first.
<br>-   • **LOCATION-ORDER-BY**: Locations are ordered within a pick zone (maintaining the allocation search path order) by the location attributes specified for the **Location Sort** field in inventory selection settings.
<br>-   •
    
    **No selection (blank)**: The application uses the inventory rotation method of the highest defined level of precedence. For information on precedence, see [Inventory rotation allocation processing](../../outbound/allocation/inventory-rotation-allocation.md).
    
    <br>
    
    **Note**: Inventory rotation methods defined at a lower precedence (except the default method) are automatically copied to the order line or work order line when the line is created. For example, if an order line is created for a date-tracked item with a rotation method defined, the rotation method is copied from the item to the order line, and then the application uses the order line rotation method during allocation.
    
    <br > If no inventory rotation method is defined at any level, then the application uses the allocation search path sequence and allocates the first available inventory it finds that matches all of the required attributes.
<br > When using inventory rotation methods that are not absolute, the application searches for inventory by allocation search path in sequence until it finds a pick zone that contains the inventory, and then allocates inventory that is closest to the preferred processing date. Therefore, the application stops searching at the first pick zone in which matching inventory is found.<br > When using absolute inventory rotation methods, the application searches either all of the allocation search paths for inventory that is closest to the preferred processing date or, if absolute groups are defined, each absolute group in sequence until it finds matching inventory and then allocates inventory that is closest to the preferred processing date from the pick zones within the absolute group. Therefore, the absolute method allows for more a comprehensive search to find the inventory. |
| Allocation Profile | Default level of quality at which the customer is willing to accept inventory. An allocation profile is a prioritized list of inventory statuses that identifies which statuses can be shipped. It can be applied to both date-controlled and non-date-controlled items. |
| Reservation Priority | Value that determines which orders receive inventory when there is not enough inventory in the warehouse to satisfy all orders for an item. This value applies only when the pick reservation process is used. |
| Bulk Picking | If Yes, customers created using this customer type are enabled for bulk pick processing. Bulk pick processing allocates matching inventory for multiple orders or work order lines together into larger unit of measure (UOM) picks so as to reduce the number of smaller UOM picks required to satisfy the orders.<br > If No, customers created using this customer type are not enabled for bulk picking processing.<br > You can still enable or disable bulk picking for specific customers regardless of the bulk picking value for the customer type. Only available if bulk picking is enabled for this warehouse. |
| LPN attribute | If Yes, the attribute is required by default for a pallet LPN of inventory. An LPN attribute is a configurable attribute; therefore, the list of available LPN attributes may vary depending on what is configured and enabled for your warehouse. LPN attributes that are enabled are displayed during inventory identification, inventory attribute change operations, and picking (if specified for an order line).<br > If No, the attribute is not required by default for the pallet LPN. |
| Date-Controlled Items | If Yes, customers of this type order date-controlled items. If this field is set to Yes, then you can specify the preferences for outbound date window and freshness date processing.<br > If No, customers of this type do not order date-controlled items, and so preferences for outbound date window and freshness date do not need to be configured. |
| Shelf Life | Minimum amount of time prior to the inventory's expiration date that must exist for date-controlled inventory to be considered for allocation. For example, a customer may order items that take approximately 6 days to reach a retail location. To ensure that the product can be sold for at least 4 days, the customer may request that only inventory that has at least 10 days (240 hours) to reach its expiration date be allocated to fill their orders.<br > Only available if the customer orders date-controlled inventory. |
| Outbound Date Window | Amount of time in relation to the inventory’s received date or expiration date during which inventory is considered the same age for allocation when one of the FEFO/FIFO/LEFO/LIFO or absolute FEFO/FIFO/LEFO/LIFO inventory rotation methods is required. The available time units include minutes (m), hours (h), or days (d). For example, an entry of "5h" defines the window (5) and unit (hours). During allocation, the application uses the assigned date window based on a pre-defined order of precedence. See [Allocation Inventory Selection](../../outbound/allocation/allocation-inventory-selection.md). |
| Freshness Date | Freshness date processing ensures that future shipments of a date-controlled item to a customer (for whom this attribute is enabled) always contain inventory that is fresher than earlier shipments of that same item.<br>-   • **Freshness Date Processing**: Indicates that the customer requires freshness date processing.
<br>-   • **No Freshness Date Processing**: Indicates that the customer does not require freshness date processing.
<br>-   • **Inherited Value**: Indicates that the value for this field will be provided on the order line by the customer type to which the customer belongs. This option is only available for a customer configuration; not for a customer type configuration.
<br > Only available if the customer orders date-controlled inventory. |
| Cross Dock Order Lines | Value that determines how the **Cross Dock** field on an outbound order line is set when an order is downloaded from a host without a defined cross dock value for the order lines.<br > **Note**: This value is used only if the **Cross Dock Order Lines** field for the customer is set to Inherit from customer type.<br>-   •
    
    **Inherit**: The application checks the setting for other customers on the order (in the default sequence Ship-to, Route-to or Bill-to customer). If the application finds a value (Yes or No) for any of the customers or their customer type in the same sequence, the application uses that value for the order line and stops checking other customers. For example, if Ship-to customer is set to Yes or No, the **Cross Dock** field on the order line is set to Yes or No, and the application will not check other customers.
    
    <br>
    
    **Note**: You can override the default sequence of Ship-to, Route-to, and Bill-to Customer by configuring the customer requirement processing preference configuration (CUSTOMER-REQUIREMENT-PROCESSING\\PREFERENCE) in the client-based user interface using Policy Maintenance
    
    <br>
    
    If the value is set to Inherit for all customers or their customer type, then the value of the **Cross Dock** field for order lines is set to No. For example, assume that the value for this field is Inherit and the customer value for this field is Inherit from customer type. If an order line is downloaded without a cross dock value, and if the Cross Dock Order Lines value for all other customers and customer types associated with the order is set to Inherit (or No), then the **Cross Dock** field for the order line is set to No.
    
    <br>
<br>-   • **Yes**: The **Cross Dock** field on the outbound order line is set to Yes.
<br>-   • **No**: The **Cross Dock** field on the outbound order line is set to No.
<br > Changing the value of this field affects only the order lines that will be downloaded from a host, not the existing order lines for the customer. You can override this configuration at the order line level before allocating inventory. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
