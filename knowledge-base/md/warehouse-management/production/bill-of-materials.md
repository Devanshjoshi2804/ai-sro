---
title: "Bill of Materials"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/bill_of_materials_prod.htm"
source: "/content/bill_of_materials_prod.htm"
toc_path:
  - "Warehouse Management"
  - "Production"
  - "Bill of Materials"
sections:
  - "Bill of Materials page"
  - "View detailed bill of materials information"
  - "Add or modify a bill of materials"
  - "Add or modify a bill of materials line"
  - "Copy a bill of materials"
  - "Delete a bill of materials"
  - "Bill of materials field listings"
  - "General BOM fields"
  - "Processing BOM fields"
  - "Disassembly BOM fields"
  - "Allocation Rule BOM fields"
  - "Customs BOM fields"
  - "Bill of materials line field listings"
  - "General BOM Line fields"
  - "Processing BOM line fields"
  - "Allocation BOM line fields"
  - "Allocation Rule BOM fields"
  - "Identify BOM line fields"
  - "Bill of materials detail field listings"
  - "Summary fields"
  - "BOM Lines fields"
images: []
source_sha1: da6ff4764daf061bad829326ba812c591f6fa8fa
---
# Bill of Materials

A bill of materials (BOM) is a detailed list of the component items and quantities, and processing requirements, required to assemble or disassemble a top-level item. A multi-level BOM defines an item that has one or more top-level items listed as component items. A BOM is not an order for a top-level item, nor does it, by itself, activate the process to assemble or disassemble a top-level item. It is a recipe for assembling or disassembling a top-level item.

BOMs are optional; you can process work orders without using BOMs. However, BOMs are useful because of the following reasons:

-   A BOM provides the ability to specify one time the components of a frequently built top-level item and then use the BOM to generate work orders that are the starting point for the work order process, instead of creating multiple work orders for the same top-level item.
-   A BOM provides the ability to specify the disassembly processing location for top-level items. A single BOM can direct work orders to different processing locations based on the work order type; that is, whether the work order is for assembly of component items or disassembly of a top-level item.
-   A BOM can be configured to automatically generate a work order when an order for a top-level item is allocated and no inventory can be found in the facility.
-   A BOM can be used as a template to support order explosion processing, and to help you manually create work orders.

When you use a BOM to automatically generate or manually create a work order, the application uses the BOM lines to create the work order lines. A BOM line is the section of a BOM that provides detailed information about each individual component item that is to be built into the top-level item specified by the BOM.

You can define more than one BOM for a specific top-level item. This approach allows you to specify slightly different assembly or disassembly configurations for the same finished good, which is especially useful when you have revisions of a top-level item. For example, you can create BOM1 for top-level item GIFTBASKET to consist of the following component items: 1 LOTION, 1 SOAP, 1 SPONGE, and 2 CANDLES; while BOM2 for same top-level item, GIFTBASKET, consists of the following component items: 1 LOTION, 1 SOAP, 1 SPONGE, 2 CANDLES, 1 BATH OIL, and 1 BRUSH. When you create multiple BOMs for a top-level item, you can configure one of the BOMs as the default BOM to be used when none of the BOMs match the attributes of the ordered top-level item.

## Bill of Materials page

The Bill of Materials page provides visibility to the BOMs that are created within the facility. You can add, modify, or delete a BOM or BOM line. When you click on a BOM, the BOM details are displayed, and you have access to the following tabs:

-   **Summary**: Displays the following BOM details:
    -   General information about the BOM.
    -   Allocation attributes of the top-level items for a disassembly work order created using the BOM.
    -   Allocation rules that define the inventory attributes required to fulfill the BOM.
    -   Customs information that applies to the finished good for an assembly work order created using the BOM.
    -   Processing details that define the specific production stations to which component items are delivered when an assembly work order is created using the bill of material (BOM). For each component item, the page displays the assembly work order type associated to the production station to which the component is delivered for assembly.
-   **BOM Lines**: Displays the BOM line (component item) details.

## View detailed bill of materials information

1.  Perform one of the following tasks: 
    -   Select **Production > Bill of Materials**.
    -   Select **Configuration > Outbound > Production > Bill of Materials**.
2.  In the grid, click a BOM, and view information in the [Summary fields](#Summary_fields) and [BOM Lines fields](#BOM_Lines_fields).

## Add or modify a bill of materials

**IMPORTANT**: Before you can add a BOM, the top-level item and all of the component items must be defined in the application.

**Note**: To make a copy of an existing BOM, see [Copy a bill of materials](#Copy_a_bill_of_materials).

1.  Perform one of the following tasks: 
    -   Select **Production > Bill of Materials**.
    -   Select **Configuration > Outbound > Production > Bill of Materials**.
2.  Perform one of the following tasks:
    -   To add a BOM, from the **Actions** drop-down list, select **Add**. The Add Bill of Material window is displayed.
    -   To modify a BOM, in the grid select the check box next to the BOM, and from the **Actions** drop-down list, select **Modify**. The Modify Bill of Material window is displayed.

1.  Enter information in the [Bill of materials field listings](#Bill_of_materials_fields).
2.  To add the processing details:
    1.  In the left pane, click **Processing**, and click **Add**. The Processing window is displayed.
    2.  Enter information in the [Processing BOM fields](#Processing_BOM_fields).
    3.  Click **OK**.
3.  To add or modify the criteria definition for the selected allocation rule, under **Criteria Definition**:
    
    **Note**: For more information, see [Allocation Rules](../configuration/outbound/allocation/allocation-rules.md).
    

1.  To add a new expression, click **Expression**.
2.  Select a column (attribute) to use, such as Lot Number.
3.  Select the qualifier to use, such as "=".
4.  Enter the attribute to use, such as LOT1234 (based on the qualifier, the lot number that must be allocated for the order line).
5.  To add additional rows of criteria:
    1.  Select the mathematical argument used to evaluate multiple rows of criteria.
        -   **Or**: Must match either group of the defined criteria.
        -   **And**: Must match both groups of the defined criteria.
        -   **(**: Opening argument used to group criteria together.
        -   **)**: Closing argument used to group criteria together.
        
        **Note**: Other operators that represent a combination of these arguments, such as ")And(" are also available. The operator determines how the application evaluates the criteria. For example, if you have two criteria lines connected with the operator "And", that means the inventory must match both attributes to meet the criteria. If the two lines are connected with the operator "Or", the inventory only has to match one of the field values to meet the criteria.
        
    2.  Click **Expression**, and define its criteria.

5.  Click **Save**.
6.  If a message is displayed asking if you want to add BOM lines, perform one of the following tasks:
    -   To add BOM lines:
        1.  Click **Yes**.
        2.  Click **Add**.
        3.  Enter information in the [Bill of materials line field listings](#Bill_of_materials_line_fields).
        4.  To include the processing details:
            1.  In the left pane, click **Processing** and enter information in the [Processing BOM Line fields](#Processing_BOM_line_fields).
            2.  Click **Add**. Enter the following details:
                -   **Work Order Type**: Unique identifier for the work order type. A work order type is a category into which work orders are grouped based on similar processing characteristics.
                -   **Production Station**: Production station to which the component inventory or the top-level item defined for the BOM or work order is to be delivered. A production station is a position on a production line where a specific operation is performed during the assembly or disassembly of a top-level item (finished good).
        5.  Click **Save**.
    -   To save the BOM without adding lines, click **No**.

## Add or modify a bill of materials line

1.  Perform one of the following tasks: 
    -   Select **Production > Bill of Materials**.
    -   Select **Configuration > Outbound > Production > Bill of Materials**.
2.  In the grid, click the BOM. The BOM details are displayed.
3.  Click **BOM Lines**.
4.  Perform one of the following tasks:
    -   To add a BOM, click **Add**.
    -   To modify a BOM line, click **Modify**, and click **BOM Lines**.
5.  Enter information in the [Bill of materials detail field listings](#Bill_of_materials_detail_fields).
6.  Click **Save**.

## Copy a bill of materials

You can copy a bill of material (BOM) to create a new BOM. When you copy a BOM, the associated BOM lines are also copied.

1.  Perform one of the following tasks: 
    -   Select **Production > Bill of Materials**.
    -   Select **Configuration > Production > Bill of Materials**.
2.  In the grid select the check box next to the BOM.
3.  From the **Actions** drop-down list, select **Copy**. The Copy BOM window is displayed.
4.  Enter information in the following fields:
    

 
| Field | Description |
| --- | --- |
| **Bill of Material** | Identifier for a bill of material. A BOM is a detailed list of the component items and quantities, and processing requirements, required to assemble or disassemble a top-level item. It is a template for assembling or disassembling a top-level item. |
| **Bill of Material Client** | Client responsible for creating the BOM and is not necessarily the client which houses the top-level item specified in the BOM. Only displayed in a 3PL environment. |

8.  Click **Save**.

## Delete a bill of materials

1.  Perform one of the following tasks:

-   Select **Production > Bill of Materials**, and in the grid, select the check box next to the BOM.
-   [View detailed BOM information](#View_detailed_bill_of_materials_information).

3.  From the **Actions** drop down list, select **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Bill of materials field listings

### General BOM fields

 
| Field | Description |
| --- | --- |
| Bill of Material | Identifier for a bill of material. A BOM is a detailed list of the component items and quantities, and processing requirements, required to assemble or disassemble a top-level item. It is a template for assembling or disassembling a top-level item. |
| Bill of Material Client | Client responsible for creating the BOM. This client is not necessarily the same client that houses the top-level item specified in the BOM. The client that houses the top-level item is defined in the **Item/Client** field and can either match or differ from the **Bill of Material Client**. Only displayed in a 3PL environment. |
| Item/Client | Name of the client who stores the top-level item in the facility. This is the client that houses the item specified in the BOM and is not necessarily the client that created the BOM. The client responsible for creating the BOM is defined in the **Bill of Material Client** field. Only displayed in a 3PL environment. |
| Inventory Status | Defines the quality or disposition of the inventory. This is the default inventory status that is displayed when an operator identifies completed top-level items for the work order. However, the operator may change the status. Only available for assembly work orders. |
| Lot | Identifier to assign to top-level items built for the work order. A lot is an identifier assigned to a quantity of product that is uniquely identified during the manufacturing process for the purpose of tracking an attribute of that product, such as expiration date. Only available for assembly work orders and if the top-level item requires this attribute. |
| Supplier Lot | Supplier lot identifier to assign to top-level items built for the work order. A supplier lot is a unique identifier that is assigned to a quantity of product during the manufacturing process that identifies the lot of the product as specified by the supplier. Only available for assembly work orders and if the top-level item requires this attribute. |
| Country of Origin | Identifier assigned to an item to identify the item's country of origin. It is typically used for export paperwork. |
| Minimum Quantity to Produce | Minimum quantity of top-level items that can be built. If this BOM is configured to automatically generate work orders, and an order for the top-level item is allocated for less than the minimum quantity that you specify here, the application will create the work order for the minimum quantity. If a work order based on this BOM is created manually, users will not be able to specify a top-level item quantity of less than the minimum quantity. However, if you specify a percentage in the **Production Tolerance** field, then it is possible that the total number of top-level items assembled and received into inventory could be less than the quantity specified in the **Minimum Quantity to Produce** field. |
| Production Tolerance (%) | Value that determines the minimum and maximum percentage of the total number of required finished items that can be assembled or disassembled. For example, if you enter a production tolerance of 10, then you can assemble and identify anywhere from 90% to 110% of the number of finished items required for the work order. |
| Bill of Material Code | Code that identifies how long a BOM is to remain in the application before it is automatically removed. You can manually delete a BOM regardless of the code value.<br>-   • **Good Until**: The BOM will be removed on the date that you specify in the Until Date field.
<br>-   • **Permanent**: The BOM will be used again to create work orders, and it will not be removed.
<br>-   • **Temporary**: The BOM is for one time use, and it will be removed after a work order is created.
<br>-   • **Blank** (no selection): The BOM is not removed automatically. |
| Until Date | Date and time on which the application will automatically purge this BOM. The date selected in the Until Date field is only used if the value for **Bill of Material Code** is Good Until. |
| Auto Generate Work Order | If **Yes**, then this BOM will be used to automatically create a work order for the top-level item.<br > If **No**, then this BOM will not be used to create a work order for the top-level item. |
| Default Bill of Materials | If **Yes**, the application will use this BOM to auto-generate a work order for this top-level item when the attributes specified on the order do not exactly match those on any BOM for this item.<br > If **No**, the application will not use this BOM to auto-generate a work order. |
| Component Tracking | If **Yes**, the application will track the attributes of the component items after the top-level item on this BOM or work order is assembled and identified.<br > If **No**, the application will not track the attributes of the component items after the top-level item on this BOM or work order is assembled and identified.<br > Only available for assembly work orders. |
| Exclusively Occupy Production Line | If **Yes**, the work order or BOM is to exclusively occupy a production line (the work order is not to be processed at the same time as other work orders on the same production line). This means that the work order must be started either on an exclusive production line (**Exclusive Work Order** is configured for the production line) or on a non-exclusive production line that has no other work orders started on it.<br > If **No**, another work order or BOM can be started at the same time on the same production line as this work order. Only available as selection criteria or if a schedule-based production line is selected from the **Production Line** drop-down list. |
| Minimum Catch Quantity to Produce | Minimum catch unit quantity of top-level items that can be built, such as 10 gallons or 50 pounds. If this BOM is configured to automatically generate work orders, and an order for the top-level item is allocated for less than the minimum catch quantity that you specify here, the application will create the work order for the minimum catch quantity. If a work order based on this BOM is created manually, users will not be able to specify a top-level item quantity of less than the minimum catch quantity. Only available if the top-level item requires catch quantities. |

### Processing BOM fields

 
| Field | Description |
| --- | --- |
| Work Order Type | Unique identifier for the work order type. A work order type is a category into which work orders are grouped based on similar processing characteristics. |
| Processing Area | Production line area in which the top-level item specified on this bill of material or work order will be assembled or disassembled. |
| Production Line | Production line at which the top-level items for the BOM or work order are to be built. If you leave this field blank, the application will allocate a production line in the area selected from the Processing Area list. A production line is an arrangement of machines or sequence of operations (production stations) involved with a single manufacturing operation or production process. |
| Disassembly Station | Disassembly station at which the top-level items for the BOM or work order are to be broken down. A disassembly station is a position on a production line where a specific operation is performed during the disassembly of the top-level item (finished good). If you leave this field blank, the application will deliver the top-level items to the staging location of the specified production line, from which they can be moved to a station for disassembly. |
| Default | Indicates that the work order type will be the default type for work orders that are automatically generated from this BOM. For example, if you set this field to Yes for an assembly work order type processing configuration, while you still can manually create assembly and disassembly work orders using this BOM, when a work order is automatically generated using this BOM, the work order type is Assembly. There can only be one default generation work order type for a BOM. |

### Disassembly BOM fields

 
| Field | Description |
| --- | --- |
| Over Allocation Code | Code that identifies how over allocation is performed.<br>-   • **Percentage**: The application is permitted to allocate a certain percentage more, as defined in the **Over Allocation Amount** field, of the original quantity of component items required for the order line.
<br>-   • **Quantity**: The application is permitted to allocate a certain quantity more, as defined in the **Over Allocation Amount** field, of the original quantity of component items required for the order line.
<br > Over allocation is the process of allocating more than the indicated amount of inventory to satisfy an order or work order. Over allocation is beneficial in situations where it is easier to pick an entire case or pallet instead of breaking a case to complete a pick. |
| Over Allocation Amount | Total amount of inventory that can be allocated over the requested quantity when the allocation code is Quantity, or percentage of inventory that can be allocated when the allocation code is Percentage. If the over-allocation code is Percentage, then the over-allocation amount should be a value from 1 to 100 that indicates the percentage of the order quantity that can be over-allocated. If the over-allocation code is Quantity, then the over-allocation amount should be a value that represents the number that can be over-allocated. |
| Inventory Rotation Method | Value that represents the order in which the allocation process selects available inventory for allocation. Select an inventory rotation method if you want the application to search for inventory based on date processing or location.<br>-   • **FEFO-ORDER-BY and FEFO-ORDER-BY-ABSOLUTE**: First-expiration, first-out. The first inventory to expire will be selected first.
<br>-   • **FIFO-ORDER-BY and FIFO-ORDER-BY-ABSOLUTE**: First-in, first-out. The oldest inventory will be selected first.
<br>-   • **LEFO-ORDER-BY and LEFO-ORDER-BY-ABSOLUTE**: Last-expiration, first-out. The last inventory to expire will be selected first.
<br>-   • **LIFO-ORDER-BY and LIFO-ORDER-BY-ABSOLUTE**: Last-in, first-out. The newest inventory will be selected first.
<br>-   • **LOCATION-ORDER-BY**: Locations are ordered within a pick zone (maintaining the allocation search path order) by the location attributes specified for the **Location Sort** field in inventory selection settings.
<br>-   •
    
    **No selection (blank)**: The application uses the inventory rotation method of the highest defined level of precedence. For information on precedence, see [Inventory rotation allocation processing](../configuration/outbound/allocation/inventory-rotation-allocation.md).
    
    <br>
    
    **Note**: Inventory rotation methods defined at a lower precedence (except the default method) are automatically copied to the order line or work order line when the line is created. For example, if an order line is created for a date-tracked item with a rotation method defined, the rotation method is copied from the item to the order line, and then the application uses the order line rotation method during allocation.
    
    <br > If no inventory rotation method is defined at any level, then the application uses the allocation search path sequence and allocates the first available inventory it finds that matches all of the required attributes.
<br > When using inventory rotation methods that are not absolute, the application searches for inventory by allocation search path in sequence until it finds a pick zone that contains the inventory, and then allocates inventory that is closest to the preferred processing date. Therefore, the application stops searching at the first pick zone in which matching inventory is found.<br > When using absolute inventory rotation methods, the application searches either all of the allocation search paths for inventory that is closest to the preferred processing date or, if absolute groups are defined, each absolute group in sequence until it finds matching inventory and then allocates inventory that is closest to the preferred processing date from the pick zones within the absolute group. Therefore, the absolute method allows for more a comprehensive search to find the inventory. |
| Minimum Shelf Life (Hours) | Minimum number of hours away from expiration that a date-tracked item must be considered for allocation. For example, if this value is 10, then the application only allocates inventory that has at least 10 hours to reach its expiration date. Only available if the item specified on the order line is date-tracked. |
| Footprint Code | Name that identifies a footprint, which describes the packaging dimensions and units of measure for the item with which it is associated. |
| Allocation Profile | Identifier for the levels of quality at which the customer is willing to accept inventory. The allocation profile is a prioritized list of inventory statuses that defines which statuses can be shipped. It is applied to both date-controlled and non-date-controlled inventory. If you select **Inherited Value**, the value defined for the customer type is used. |
| Date Window Unit | Unit of time (minutes, hours, or days) for the outbound date window. |
| Date Window | Amount of time in relation to the inventory’s received date or expiration date during which inventory is considered the same age for allocation when one of the FEFO/FIFO/LEFO/LIFO or absolute FEFO/FIFO/LEFO/LIFO inventory rotation methods is required. |
| Cross Dock | If Yes, then when the inventory specified on this BOM, outbound order, or work order line is identified, is moved directly from its receiving point to a cross dock area or a specified staging location to satisfy an outbound order or work order.<br > If No, the inventory is to be allocated from storage. |
| Round Pick Quantity | If Yes, the allocation is to automatically round up the pick quantity to the next highest UOM. The pick quantity may be rounded up only within the bounds defined by the values specified for **Over Allocation Amount** and **Over Allocation Code**. This option is beneficial, for example, in situations where it is easier to pick an entire case or pallet of an item than to break a unit of measure (UOM) to complete a pick.<br > If No, the allocation does not round up the pick quantity. |

### Allocation Rule BOM fields

 
| Field | Description |
| --- | --- |
| Rule Name | Name of the allocation rule. An allocation rule is a processing command that specifies the inventory attribute values that are acceptable to fulfill an order line, work order detail, work order line, or bill of materials (BOM) detail. |
| Description | Description that further defines the allocation rule. |

### Customs BOM fields

 
| Field | Description |
| --- | --- |
| Customs Type | Identifier that defines the type of customs tracking required for the inventory on the work order or BOM. Only displayed if Customs functionality is enabled for the warehouse.<br>-   • **Customs**: Customs duties need to be paid for the items on the work order. Available if the address for the warehouse is designated as a Customs site type.
<br>-   • **Excise**: Excise duties need to be paid for the items on the work order; customs duties may also be required. Available if the address for the warehouse is designated as a Customs and Excise site type.
<br>-   • **Free**: Customs duties or excise duties need not be paid. |
| VAT Code | Code for the value added tax (VAT) for the item. A customs VAT is charged on goods and some services that are imported from countries outside the European Unit (EU) and brought into the United Kingdom (UK) from other EU countries. It is also charged on most goods and services that VAT-registered businesses provide in the UK.<br>-   • **Standard**: The standard customs VAT rate is charged for this item.
<br>-   • **Zero**: No customs VAT is charged for this item. |
| Commodity Code | Code that identifies a commodity. Commodities are categories created to group inventory that has the same qualities and specifications, regardless of their source. For example, wheat is a commodity. Commodity codes are standardized to provide carriers with a standard by which to determine pricing and to simplify the shipment process. The Commodity Code is usually printed on the bill of lading (BOL). If the commodity is printed on the BOL, all products of the same commodity are totaled. |
| Default Country | Country in which the item was manufactured. Only applies to items for which customs or excise duties need to be paid. |
| Customs Cost | Monetary amount that is paid to customs for the item. Only applies to items for which customs or excise duties need to be paid. |
| Duty Stamp Tracked | If Yes, the item is duty stamp tracked. If No, the item is not duty stamp tracked.<br > Only applies to items for which excise duties need to be paid. |

## Bill of materials line field listings

### General BOM Line fields

 
| Field | Description |
| --- | --- |
| Bill of Material Line | Unique identifier for the bill of material line. |
| Item/Client | Name of the client who stores the top-level item in the facility. This is the client that houses the item specified in the BOM and is not necessarily the client that created the BOM. The client responsible for creating the BOM is defined in the **Bill of Material Client** field. Only displayed in a 3PL environment. |
| BOM Quantity | Quantity (in terms of material handling or stock keeping units) of the component item required to assemble one top-level item. This is the quantity of the component item that will be consumed when assembling the top-level item. If a BOM is defined for the top-level item, then this value can be populated by the BOM. |
| BOM Catch Quantity | Catch unit amount of the component item required to assemble one top-level item. This is the catch unit quantity of the component item that will be consumed when assembling the top-level item. Only available if the **Allocate by Catch Quantity** check box is deselected. |

### Processing BOM line fields

 
| Field | Description |
| --- | --- |
| Consumption Tolerance (%) | Value that determines the minimum and maximum percentage of the BOM quantity (specified in the **BOM Quantity** field) for the component item that the application will allow. For example, if you enter a Consumption Tolerance Percentage of 10, then you can consume anywhere from 90% to 110% of the specified consumed quantity when assembling the top-level item. |
| Expected Scrap (%) | Value that determines the minimum and maximum percentage of the BOM quantity (specified in the **BOM Quantity** field) for the component item that the application will allow being scrapped (not reusable). For example, if you enter a scrap percentage of 50, then you can scrap anywhere from 50% to 150% of the specified BOM quantity when disassembling the top-level item. |
| Cross Dock | If Yes, then when the inventory specified on this BOM, outbound order, or work order line is identified, is moved directly from its receiving point to a cross dock area or a specified staging location to satisfy an outbound order or work order.<br > If No, the inventory is to be allocated from storage. |
| Round Pick Quantity | If Yes, the allocation is to automatically round up the pick quantity to the next highest UOM. The pick quantity may be rounded up only within the bounds defined by the values specified for **Over Allocation Amount** and **Over Allocation Code**. This option is beneficial, for example, in situations where it is easier to pick an entire case or pallet of an item than to break a unit of measure (UOM) to complete a pick.<br > If No, the allocation does not round up the pick quantity. |

### Allocation BOM line fields

 
| Field | Description |
| --- | --- |
| Allocation Profile | Identifier for the levels of quality at which the customer is willing to accept inventory. The allocation profile is a prioritized list of inventory statuses that defines which statuses can be shipped. It is applied to both date-controlled and non-date-controlled inventory. If you select **Inherited Value**, the value defined for the customer type is used. |
| Skip Allocation | If Yes, then this component item will not be allocated when work orders based on this bill of material or work order are allocated. This option is useful for packaging or supply items that must be tracked for cost purposes, but not picked, because they are often stored in a work-in-process supply location type.<br > If No, then this component item will be allocated when work orders based on this bill of material or work order are allocated. |
| Footprint | Name that identifies a footprint, which describes the packaging dimensions and units of measure for the item with which it is associated. |
| Inventory Rotation Method | Value that represents the order in which the allocation process selects available inventory for allocation. Select an inventory rotation method if you want the application to search for inventory based on date processing or location.<br>-   • **FEFO-ORDER-BY and FEFO-ORDER-BY-ABSOLUTE**: First-expiration, first-out. The first inventory to expire will be selected first.
<br>-   • **FIFO-ORDER-BY and FIFO-ORDER-BY-ABSOLUTE**: First-in, first-out. The oldest inventory will be selected first.
<br>-   • **LEFO-ORDER-BY and LEFO-ORDER-BY-ABSOLUTE**: Last-expiration, first-out. The last inventory to expire will be selected first.
<br>-   • **LIFO-ORDER-BY and LIFO-ORDER-BY-ABSOLUTE**: Last-in, first-out. The newest inventory will be selected first.
<br>-   • **LOCATION-ORDER-BY**: Locations are ordered within a pick zone (maintaining the allocation search path order) by the location attributes specified for the **Location Sort** field in inventory selection settings.
<br>-   •
    
    **No selection (blank)**: The application uses the inventory rotation method of the highest defined level of precedence. For information on precedence, see [Inventory rotation allocation processing](../configuration/outbound/allocation/inventory-rotation-allocation.md).
    
    <br>
    
    **Note**: Inventory rotation methods defined at a lower precedence (except the default method) are automatically copied to the order line or work order line when the line is created. For example, if an order line is created for a date-tracked item with a rotation method defined, the rotation method is copied from the item to the order line, and then the application uses the order line rotation method during allocation.
    
    <br > If no inventory rotation method is defined at any level, then the application uses the allocation search path sequence and allocates the first available inventory it finds that matches all of the required attributes.
<br > When using inventory rotation methods that are not absolute, the application searches for inventory by allocation search path in sequence until it finds a pick zone that contains the inventory, and then allocates inventory that is closest to the preferred processing date. Therefore, the application stops searching at the first pick zone in which matching inventory is found.<br > When using absolute inventory rotation methods, the application searches either all of the allocation search paths for inventory that is closest to the preferred processing date or, if absolute groups are defined, each absolute group in sequence until it finds matching inventory and then allocates inventory that is closest to the preferred processing date from the pick zones within the absolute group. Therefore, the absolute method allows for more a comprehensive search to find the inventory. |
| Over Allocation Code | Code that identifies how over allocation is performed.<br>-   • **Percentage**: The application is permitted to allocate a certain percentage more, as defined in the **Over Allocation Amount** field, of the original quantity of component items required for the order line.
<br>-   • **Quantity**: The application is permitted to allocate a certain quantity more, as defined in the **Over Allocation Amount** field, of the original quantity of component items required for the order line.
<br > Over allocation is the process of allocating more than the indicated amount of inventory to satisfy an order or work order. Over allocation is beneficial in situations where it is easier to pick an entire case or pallet instead of breaking a case to complete a pick. |
| Over Allocation Amount | Total amount of inventory that can be allocated over the requested quantity when the allocation code is Quantity, or percentage of inventory that can be allocated when the allocation code is Percentage. |
| Date Window Unit | Unit of time (minutes, hours, or days) for the outbound date window. |
| Date Window | Value for the outbound date window. Only available if **Date Window Unit** value is selected. |
| Minimum Shelf Lift (Hours) | Minimum number of hours away from expiration that a date-tracked item must be considered for allocation. For example, if this value is 10, then the application only allocates inventory that has at least 10 hours to reach its expiration date. Only available if the item specified on the order line is date-tracked. |

### Allocation Rule BOM fields

 
| Field | Description |
| --- | --- |
| Rule Name | Name of the allocation rule. An allocation rule is a processing command that specifies the inventory attribute values that are acceptable to fulfill an order line, work order detail, work order line, or bill of materials (BOM) detail. |
| Description | Description that further defines the allocation rule. |

### Identify BOM line fields

 
| Field | Description |
| --- | --- |
| Inventory Status | Defines the quality or disposition of the inventory. This is the default inventory status that is displayed when an operator identifies component items for the work order. However, the operator may change the status. Only available for disassembly work orders. |
| Lot | Lot number that allocated component items must have. If any lot is acceptable, leave this field blank. A lot is an identifier assigned to a quantity of inventory that is uniquely identified during the manufacturing process for the purpose of tracking an attribute of that inventory, such as its expiration date. Lots differentiate distinct groups of inventory that have the same item number. Lots are user defined and are not necessarily unique since the same lot number can be applied to different items. However, lot and item combinations must be unique. Only available if the component item entered in the **Item** field requires lot number tracking. |
| Supplier Lot | Supplier lot number that allocated component items must have. If any supplier lot is acceptable, leave this field blank. A supplier lot number is a unique identifier that is assigned to a quantity of product during the manufacturing process that identifies the lot of the product as specified by the supplier. Only available if the component item entered in the **Item** field requires supplier lot tracking. |
| Revision Level | Revision level that allocated component items must have. If any revision level is acceptable, leave this field blank. A revision level is a unique identifier that is assigned to an item to differentiate revisions of the same item. Revision Levels are user defined. Only available if the component item entered in the **Item/Client** field requires revision level tracking. |
| Origin Code | Origin code of the component items consumed in an assembly work order. An origin code is a unique identifier that is assigned to an item to identify the item's place of origin. Typically used for export paperwork. Origin codes are user defined. |

## Bill of materials detail field listings

### Summary fields

 
| Field | Description |
| --- | --- |
| Bill of Material Client | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client ID distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. This is the client responsible for creating the BOM and is not necessarily the client which houses the top-level item specified in the BOM. |
| Default Bill of Materials | Indicates whether the application will use this BOM to auto-generate a work order for this top-level item when the attributes specified on the order do not exactly match those on any BOM for this item. |
| Auto Generate Work Order | Indicates whether this BOM will be used to automatically create a work order for the top-level item. |
| Track Components | Indicates whether the application tracks the attributes of the component items after the top-level item on work order is assembled and identified. A check mark is displayed if the application tracks the attributes of the component items.<br > Only available for assembly work orders. |
| Bill of Material Code | Code that identifies how long a BOM is to remain in the application before it is automatically removed. You can manually delete a BOM regardless of the code value.<br>-   • **Good Until**: The BOM will be removed on the date that you specify in the Until Date field.
<br>-   • **Permanent**: The BOM will be used again to create work orders, and it will not be removed.
<br>-   • **Temporary**: The BOM is for one time use, and it will be removed after a work order is created.
<br>-   • **Blank** (no selection): The BOM is not removed automatically. |
| Inventory Status | Defines the quality or disposition of the inventory. This is the default inventory status that is displayed when an operator identifies completed top-level items for the work order. However, the operator may change the status. Only available for assembly work orders. |
| Until Date | Date and time on which the application will automatically purge this BOM. The date selected in the Until Date field is only used if the value for **Bill of Material Code** is Good Until. |
| Production Tolerance (%) | Value that determines the minimum and maximum percentage of the total number of required finished items that can be assembled or disassembled. For example, if you enter a production tolerance of 10, then you can assemble and identify anywhere from 90% to 110% of the number of finished items required for the work order. |
| Minimum Quantity to Produce | Minimum quantity of top-level items that can be built. |
| Minimum Catch Quantity | Minimum catch quantity per stocking unit of measure. Enter a value that represents the lowest acceptable catch quantity that you accept for a unit of the item. During inventory identification, if the operator enters a lower catch quantity when capturing the actual catch quantity measurement, the application displays a message stating that the quantity is unacceptable and not allowed. This is helpful in alerting the operator to either an inaccurate entry or unacceptable inventory. Only available if a catch code is selected for the item. |
| Exclusively Occupy Production Line | Indicates whether the work orders created from the BOM must exclusively occupy a production line. This means that the work order must be started either on an exclusive production line (if the **Exclusive Work Order** field for the production line is set to Yes) or on a non-exclusive production line that has no other work orders started on it. If other work orders can be started at the same time on the same production line as work orders created from the BOM, then deselect the **Exclusively Occupy Production Line** check box. |
| Over Allocation Code | Code that identifies how over allocation is performed.<br>-   • **Percentage**: The application is permitted to allocate a certain percentage more, as defined in the **Over Allocation Amount** field, of the original quantity of component items required for the order line.
<br>-   • **Quantity**: The application is permitted to allocate a certain quantity more, as defined in the **Over Allocation Amount** field, of the original quantity of component items required for the order line.
<br > Over allocation is the process of allocating more than the indicated amount of inventory to satisfy an order or work order. Over allocation is beneficial in situations where it is easier to pick an entire case or pallet instead of breaking a case to complete a pick. |
| Over Allocation Amount | Total amount of inventory that can be allocated over the requested quantity when the allocation code is Quantity, or percentage of inventory that can be allocated when the allocation code is Percentage. |
| Inventory Rotation Method | Value that represents the order in which the allocation process selects available inventory for allocation. Select an inventory rotation method if you want the application to search for inventory based on date processing or location.<br>-   • **FEFO-ORDER-BY and FEFO-ORDER-BY-ABSOLUTE**: First-expiration, first-out. The first inventory to expire will be selected first.
<br>-   • **FIFO-ORDER-BY and FIFO-ORDER-BY-ABSOLUTE**: First-in, first-out. The oldest inventory will be selected first.
<br>-   • **LEFO-ORDER-BY and LEFO-ORDER-BY-ABSOLUTE**: Last-expiration, first-out. The last inventory to expire will be selected first.
<br>-   • **LIFO-ORDER-BY and LIFO-ORDER-BY-ABSOLUTE**: Last-in, first-out. The newest inventory will be selected first.
<br>-   • **LOCATION-ORDER-BY**: Locations are ordered within a pick zone (maintaining the allocation search path order) by the location attributes specified for the **Location Sort** field in inventory selection settings.
<br>-   •
    
    **No selection (blank)**: The application uses the inventory rotation method of the highest defined level of precedence. For information on precedence, see [Inventory rotation allocation processing](../configuration/outbound/allocation/inventory-rotation-allocation.md).
    
    <br>
    
    **Note**: Inventory rotation methods defined at a lower precedence (except the default method) are automatically copied to the order line or work order line when the line is created. For example, if an order line is created for a date-tracked item with a rotation method defined, the rotation method is copied from the item to the order line, and then the application uses the order line rotation method during allocation.
    
    <br > If no inventory rotation method is defined at any level, then the application uses the allocation search path sequence and allocates the first available inventory it finds that matches all of the required attributes.
<br > When using inventory rotation methods that are not absolute, the application searches for inventory by allocation search path in sequence until it finds a pick zone that contains the inventory, and then allocates inventory that is closest to the preferred processing date. Therefore, the application stops searching at the first pick zone in which matching inventory is found.<br > When using absolute inventory rotation methods, the application searches either all of the allocation search paths for inventory that is closest to the preferred processing date or, if absolute groups are defined, each absolute group in sequence until it finds matching inventory and then allocates inventory that is closest to the preferred processing date from the pick zones within the absolute group. Therefore, the absolute method allows for more a comprehensive search to find the inventory. |
| Minimum Shelf Life (Hours) | Minimum number of hours away from expiration that a date-tracked item must be considered for allocation. For example, if this value is 10, then the application only allocates inventory that has at least 10 hours to reach its expiration date. Only available if the item specified on the order line is date-tracked. |
| Footprint Code | Name that identifies a footprint, which describes the packaging dimensions and units of measure for the item with which it is associated. |
| Units per Case | Case configuration (number of units for each case) that allocated top-level items must have. |
| Units per Pack | Inner pack configuration (number of units for each inner pack) that allocated top-level items must have. |
| Allocation Profile | Identifier for the levels of quality at which the customer is willing to accept inventory. The allocation profile is a prioritized list of inventory statuses that defines which statuses can be shipped. It is applied to both date-controlled and non-date-controlled inventory. |
| Cross Dock | Indicates whether, when the inventory specified on the work order line is identified, it will be moved directly from its receiving point to a cross dock location or a specified staging location to satisfy an order or work order. |
| Round Pick Quantity | Indicates whether allocation is to automatically round up the pick quantity to the next highest unit of measure. The pick quantity may be rounded up only within the bounds defined by the values specified in the **Over Allocation Amount** and **Over Allocation Code**. This option is beneficial, for example, in situations where it is easier to pick an entire case or pallet instead of breaking a case or pallet to complete a pick. |
| Rule Name | Name of the allocation rule. An allocation rule is a processing command that specifies the inventory attribute values that are acceptable to fulfill an order line, work order detail, work order line, or bill of materials (BOM) detail. |
| Description | Description that further defines the allocation rule. |
| Customs Type | Identifier that defines the type of customs tracking required for the inventory on the planned inbound order. The customs type can only be modified when the planned inbound order status is Excepted or Pending. Defining a customs type on the planned inbound order overrides the customs type defined for the items on the order. If you select a bonded customs type (Customs or Excise) for the entire order, you cannot override specific customs information for the items on the order lines. Only displayed if Customs functionality is enabled for the warehouse.<br>-   • **Blank (no selection)**: Customs related fields are available for edit on the order line. Customs information is based off the item if no customs information is defined on the order line.
<br>-   • **Free**: None of the inventory on this planned inbound order is under bond. Customs information is cleared from the order line and the customs related fields are not available for edit.
<br>-   • **Customs**: All of the inventory on this planned inbound order is under bond. Customs related fields on the order line are not available for edit, with the exception of the customs consignment ID.
<br>-   • **Excise**: All of the inventory on this planned inbound order is under bond and requires a duty stamp. Customs related fields on the order line are not available for edit, with the exception of the customs consignment ID. |
| VAT Code | Code for the value added tax (VAT) for the item. A customs VAT is charged on goods and some services that are imported from countries outside the European Unit (EU) and brought into the United Kingdom (UK) from other EU countries. It is also charged on most goods and services that VAT-registered businesses provide in the UK.<br>-   • **Standard**: The standard customs VAT rate is charged for this item.
<br>-   • **Zero**: No customs VAT is charged for this item. |
| Commodity Code | Code that identifies a commodity. Commodities are categories created to group inventory that has the same qualities and specifications, regardless of their source. For example, wheat is a commodity. Commodity codes are standardized to provide carriers with a standard by which to determine pricing and to simplify the shipment process. The Commodity Code is usually printed on the bill of lading (BOL). If the commodity is printed on the BOL, all products of the same commodity are totaled. |
| Default Country | Country in which the item was manufactured. This value is displayed by default on the planned inbound order line for the item, but can be changed during receiving. Only available if the value for **Customs Item Type** is either **Customs** or **Excise**. |
| Duty Stamp Tracked | Indicates whether the item is duty stamp tracked or not. Only applies to items for which excise duties need to be paid. |
| Customs Cost | Monetary amount that is paid to customs for the item. The amount is paid in the currency defined in the currency field. Only available if the **Customs Item Type** is either Customs or Excise. |
| Work Order Type | Unique identifier for the work order type. A work order type is a category into which work orders are grouped based on similar processing characteristics. |
| Processing Area | Production line area in which the top-level item specified on this bill of material or work order will be assembled or disassembled. |
| Production Line | Production line at which the top-level items for the BOM or work order are to be built. If you leave this field blank, the application will allocate a production line in the area selected from the Processing Area list. A production line is an arrangement of machines or sequence of operations (production stations) involved with a single manufacturing operation or production process. |
| Disassembly Station | Disassembly station at which the top-level items for the BOM or work order are to be broken down. A disassembly station is a position on a production line where a specific operation is performed during the disassembly of the top-level item (finished good). If you leave this field blank, the application will deliver the top-level items to the staging location of the specified production line, from which they can be moved to a station for disassembly. |
| Default | Indicates that the work order type will be the default type for work orders that are automatically generated from this BOM. For example, if you set this field to Yes for an assembly work order type processing configuration, while you still can manually create assembly and disassembly work orders using this BOM, when a work order is automatically generated using this BOM, the work order type is Assembly. There can only be one default generation work order type for a BOM. |

### BOM Lines fields

 
| Field | Description |
| --- | --- |
| Bill of Material Line | Unique identifier for the bill of material line. |
| Item/Client | Unique identifier for an item and the name of the client who stores the inventory in the facility. This is the client that houses the item specified in the work order and is not necessarily the client that created the work order. Only displayed in a 3PL environment. |
| BOM Quantity | Quantity (in terms of material handling or stock keeping units) of the component item required to assemble one top-level item. This is the quantity of the component item that will be consumed when assembling the top-level item. If a BOM is defined for the top-level item, then this value can be populated by the BOM. |
| Over Allocation Amount | Total amount of inventory that can be allocated over the requested quantity when the allocation code is Quantity, or percentage of inventory that can be allocated when the allocation code is Percentage. |
| Round Pick Quantity | Indicates whether allocation is to automatically round up the pick quantity to the next highest unit of measure. The pick quantity may be rounded up only within the bounds defined by the values specified in the **Over Allocation Amount** and **Over Allocation Code**. This option is beneficial, for example, in situations where it is easier to pick an entire case or pallet instead of breaking a case or pallet to complete a pick. |
| Lot Number | Identifier assigned to a quantity of inventory that is uniquely identified during the manufacturing process for the purpose of tracking an attribute of that inventory, such as its expiration date. Lots differentiate distinct groups of inventory that have the same item. Lots are user defined and are not necessarily unique since the same lot can be applied to different items. However, lot and item number combinations must be unique. |
| Units Per Case | Default number of items per packaging type. For example, for the Each/Case packaging type, it is the quantity of pieces or eaches of the item that is typically received in a single case. If a pallet of the item is received with a different quantity in the cases, the receiver can change the Each/Case value for that specific pallet. This field is not available if you select a footprint code for the item. |
| Allocation Profile | Identifier for the levels of quality at which the customer is willing to accept inventory. The allocation profile is a prioritized list of inventory statuses that defines which statuses can be shipped. It is applied to both date-controlled and non-date-controlled inventory. |
| Allocate by Catch Quantity | Indicates that the application will allocate the component inventory based on catch unit quantity instead of material handling (stock keeping) quantity. |
| Allocation Rule | Name of the allocation rule. An allocation rule is a processing command that specifies the inventory attribute values that are acceptable to fulfill an order line, work order detail, work order line, bill of materials (BOM), or BOM detail. |
| BOM Catch Quantity | Catch unit amount of the component item required to assemble one top-level item. This is the catch unit quantity of the component item that will be consumed when assembling the top-level item. |
| Consumption Tolerance (%) | Value that determines the minimum and maximum percentage of the BOM quantity (specified in the **BOM Quantity** field) for the component item that the application will allow. For example, if you enter a Consumption Tolerance Percentage of 10, then you can consume anywhere from 90% to 110% of the specified consumed quantity when assembling the top-level item. |
| Created Date | Date and time at which the BOM was created. |
| Cross Dock | Indicates whether, when the inventory specified on the work order line is identified, it will be moved directly from its receiving point to a cross dock location or a specified staging location to satisfy an order or work order. |
| Date Last Modified | Date and time indicating when the BOM was last modified. |
| Date Window | Amount of time in relation to the inventory’s received date or expiration date during which inventory is considered the same age for allocation when one of the FEFO/FIFO/LEFO/LIFO or absolute FEFO/FIFO/LEFO/LIFO inventory rotation methods is required. |
| Date Window Unit | Unit of time (minutes, hours, or days) for the outbound date window. |
| Expected Scrap (%) | Value that determines the minimum and maximum percentage of the BOM quantity (specified in the **BOM Quantity** field) for the component item that the application will allow being scrapped (not reusable). For example, if you enter a scrap percentage of 50, then you can scrap anywhere from 50% to 150% of the specified BOM quantity when disassembling the top-level item. |
| Footprint | Name that identifies a footprint, which describes the packaging dimensions and units of measure for the item with which it is associated. |
| Inserted User | User who created the BOM. |
| Inventory Rotation Method | Value that represents the order in which the allocation process selects available inventory for allocation. Select an inventory rotation method if you want the application to search for inventory based on date processing or location.<br>-   • **FEFO-ORDER-BY and FEFO-ORDER-BY-ABSOLUTE**: First-expiration, first-out. The first inventory to expire will be selected first.
<br>-   • **FIFO-ORDER-BY and FIFO-ORDER-BY-ABSOLUTE**: First-in, first-out. The oldest inventory will be selected first.
<br>-   • **LEFO-ORDER-BY and LEFO-ORDER-BY-ABSOLUTE**: Last-expiration, first-out. The last inventory to expire will be selected first.
<br>-   • **LIFO-ORDER-BY and LIFO-ORDER-BY-ABSOLUTE**: Last-in, first-out. The newest inventory will be selected first.
<br > When using inventory rotation methods that are not absolute, the application searches for inventory by allocation search path in sequence until it finds a pick zone that contains the inventory, and then allocates inventory that is closest to the preferred processing date. Therefore, the application stops searching at the first pick zone in which matching inventory is found.<br > When using absolute inventory rotation methods, the application searches either all of the allocation search paths for inventory that is closest to the preferred processing date or, if absolute groups are defined, it searches each absolute group in sequence until it finds matching inventory and then allocates inventory that is closest to the preferred processing date from the pick zones within the absolute group. Therefore, the absolute method allows for more a comprehensive search to find the inventory. |
| Inventory Status | Defines the quality or disposition of the inventory. This is the default inventory status that is displayed when an operator identifies completed top-level items for the work order. However, the operator may change the status. Only available for assembly work orders. |
| Last Modified By | Name of the person who last modified the BOM. |
| Minimum Shelf Life (Hours) | Minimum number of hours away from expiration that a date-tracked item must be considered for allocation. For example, if this value is 10, then the application only allocates inventory that has at least 10 hours to reach its expiration date. Only available if the item specified on the order line is date-tracked. |
| Revision | Unique identifier for this instance of the work order, which enables you to use a standard work order multiple times. |
| Skip Allocation | Indicates that this component item will not be allocated when work orders based on this bill of material or work order are allocated. This option is useful for packaging or supply items that must be tracked for cost purposes, but not picked, because they are often stored in a work-in-process supply location type. |
| Supplier Lot Number | Identifier that is an attribute of an item or item and lot combination and is assigned by the item's supplier. A supplier lot number used to uniquely identify and track the inventory to which it is assigned. The supplier lot number is a different attribute than the lot number, which is a manufacturer or production lot number. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
