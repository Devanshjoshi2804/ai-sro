---
title: "Settings and Pack Station"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/settings_and_pack_station.htm"
source: "/content/settings_and_pack_station.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Outbound"
  - "Packing"
  - "Settings and Pack Station"
sections:
  - "Processing fields"
  - "Inventory mixing restrictions for packing"
  - "Cartonization at the pack station"
  - "Pallet building at the pack station setup"
  - "Pack location reservation"
  - "Configure packing settings"
  - "Configure pack station processing"
  - "Packing Settings fields"
  - "Pack Station fields"
  - "Processing Field fields"
  - "Weight Configuration Overrides fields"
images:
  - "/content/resources/images/keyboardhelp_29x20.png"
source_sha1: 5a844a9b50151ef4a4cb966300cef66844275032
---
# Settings and Pack Station

Warehouses use pack stations to move picked inventory into shipping containers that can be directed to staging lanes for shipping.

When you configure packing, you define the following attributes:

-   General settings
    -   General settings for pack station processing
    -   Sequence in which inventory is displayed to the operator. If an operator picks inventory for multiple shipping containers into a single picking container, and the user scans the picking container into the pack station, the user can view a list of inventory that belongs to each shipping carton. You can define the order in which inventory is displayed. For example, a break on value of carrier and the sequencing set to shipment ID would direct the user to pack based on carrier and the inventory would be displayed in shipment order to ensure shipments are packed together.
    -   Movement zones that contain the locations in which pack station processing takes place.
-   Pack station processing
    -   Automatic cartonization. Automatic cartonization, which considers the inventory in a picking container and determines what shipping carton type the operator should use and how many will be needed. The application then defaults to that shipping carton type automatically.
    -   Sub-line packing that determines whether the application automatically packs sub-lines when an order line is processed.
    -   Quantity configuration that determines what quantity will be processed when the operator scans a piece of inventory. If they set it to User Specified, the user can set a value that will be processed every time a user scans inventory.
    -   Shipping container processing attributes
    -   Processing attributes, including the zone to which completed shipping containers are deposited, the processing fields for which values must be captured during packing, whether multiple shipments can be packed at the same time, and whether packing is prevented until all inventory for shipment is deposited to the pack location
    -   Packing mixing restrictions
    -   Weight capture processing
    -   Post packing movement path exceptions

## Processing fields

A processing field is an inventory attribute for which a value is required during pack station processing. When you configure pack station processing, you can select and configure each of the processing fields (such as Item) that you require to capture information about the picked inventory.

For a 3PL environment, you can define an override by client to specify the set of attributes that the client requires. During packing, the application determines which client is associated with a shipping container, and prompts the operator to validate the attributes the client requires. If no client override is defined, the default attributes are used.

You use the setting for **Auto Fill** to determine whether the application automatically populates the processing field with the expected value based on the contents of the picking container. The application does not populate the field until the operator enters the item attributes that identify which item is being packed; so, the field may not populate after the first scan.

You use the setting for **Visible** to determine whether the processing field is displayed or hidden (not visible to the operator).

The following scenarios explain how these settings can be used:

-   To allow the operator to quickly pack inventory, set **Auto Fill** to Yes and set **Visible** to Yes. The expected value is populated in the displayed processing field.
-   To require operators to enter each required attribute, for example, to verify that they are packing the correct item into the shipping container, set **Auto Fill** to No and set **Visible** to Yes. The operator must scan a value for each required processing field.
-   If the value of the field needs to be captured, for example for a custom validation command, but the operator does not need to see the information, set **Auto Fill** to Yes and set **Visible** to No. The value of the processing field is automatically set to the value of the current in-process item but the field is not displayed on the screen.
-   If the expected field value is not directly associated with the in-process inventory and the value must be set by a custom command, set **Auto Fill** to No and set **Visible** to No. The field is not displayed on the screen. Contact your Blue Yonder project team for more information on custom validation commands. This setting combination is also useful if the field value does not need to be validation but you do not want to remove the field from the screen.

## Inventory mixing restrictions for packing

You can configure packing mixing restrictions to prevent processing mixed inventory (based on selected attributes) to the same shipping container. Mixing restrictions for packing can be defined for a warehouse or, for a 3PL environment, by client.

During pack station processing, the application supports the separation of inventory that should not be mixed. It validates the inventory prior to packing and creates additional shipping containers as needed so that inventory that should not be mixed can be packed to separate containers. It also prevents closing a shipping container that has been packed with mixed inventory that violates restrictions.

For example, if the item family attribute is defined as a mixing restriction, then during pack station processing, the application validates the inventory's item family. If multiple item families are included in the same shipment, the application creates additional shipping containers for packing each item family in a separate container.

**Note**: If Customs is enabled for the warehouse, you can specify for a customs order type whether you allow mixing of bonded and duty-free inventory in the same shipping container. See [Configure outbound customs](../shipping/outbound-customs.md).

## Cartonization at the pack station

Cartonization at the pack station is an automatic cartonization process that determines which type of carton to use as the shipping container for picked inventory that has been deposited to a pack station. See [Automatic cartonization](../picking/pick-cartonization.md).

-   **Shipping Cartonization**: Shipping cartonization happens at pick release. It looks at all of the inventory destined for a shipment (or whatever the break on value is) and groups the inventory together so when it arrives at the pack station the application knows what carton type to pack into and how many cartons it will need. It also assigns a container ID to the inventory at pick release. This also allows the application to plan the shipment to be spread over multiple picking containers.
-   **Automatic cartonization**: Cartonization that takes place at the pack station. The application uses the inventory in a picking container to determine what size and how many shipping containers are needed.

## Pallet building at the pack station setup

You must perform the following tasks to set up pallet building at the pack station:

1.  Configure outbound pallet building. This process involves defining the locations, movement zones, movement paths, pallet positions, and pallet consolidation rules. See [Outbound pallet building setup](../shipping/outbound-staging.md).
2.  Configure the packing workstations for consolidation. For each pack station at which you want to perform consolidation, enable consolidation and then select the movement zones to which shipping containers processed at the workstation can be consolidated. See [Add or modify a workstation](../../equipment/hardware/workstations.md).
3.  Configure shipping cartonization. To use pallet building at the pack station with cartonization enabled, the **Shipping Container LPN Level** field must be set to Sub-LPN. This ensures that when a non-pallet shipping container is consolidated to an LPN, the shipping container retains its identifier. If this field is set to LPN, then the container identifier is removed when the inventory is consolidated to the LPN. See [Configure shipping cartonization](../shipping/outbound-cartonization.md).

## Pack location reservation

The location reservation process can be used to reserve a location for a shipment as soon as inventory for the shipment is deposited to the location. For example, when a pack location is reserved by shipment, then inventory for a different shipment is not directed to the location until the current inventory has been packed.

The process for reserving pack locations by shipment requires adding pack locations to a movement zone, and then using the location reservation process to assign a resource type of Derived and an attribute of Shipment ID. See [Processing Location Reservation](../../inventory/movement/processing-location-reservation.md).

For pack locations that are reserved by shipment, the following functionality is available:

-   The application can be configured (by warehouse or client) to prevent packing until all inventory (to be packed) for a shipment has been deposited to the pack location. See [Configure pack station processing](#Configure_pack_station_processing).
-   On the pack initiation page, the operator can view the shipment completion status for each location in the workstation's processing zone. The status indicates whether packing can begin. The operator can also view the picking containers in each location that is reserved by shipment.

## Configure packing settings

1.  Select **Configuration > Outbound > Packing > Packing Settings**.
2.  Enter information in the [Packing Settings fields](#Packing_settings_fields).
3.  To select how picks for multiple shipments are grouped and displayed to the operator:
    1.  Click **Sequence Multiple Shipments**.
    2.  To select criteria from displayed entities:
        1.  If the advanced query is displayed, click **Simple**.
        2.  If the available entities are not displayed, click **Show Available**.
        3.  In the **Available** grid, select the entities that you want to use as criteria.
        4.  Click **Add selected**. The entities are added to the **Selected** grid.
        5.  To remove criteria, in the **Selected** grid, select the criteria to remove, and click **Remove selected**.
        6.  To reorder the criteria, in the **Selected** grid, click a row, and then click the up or down arrow to move the selected criteria. The application applies the criteria in sequential order according to how it is displayed in the grid.
    3.  To enter criteria using database entities, click **Advanced**, and then enter the column and field name, using a period to separate the column and field. Multiple column and field entries must be separated by a comma and space.
        
        You can use operators like IS NULL or IS NOT NULL to build an advanced query. For example, <column name>.<field name > IS NOT NULL, <column name>.< field name>.
        
    4.  Click **Apply**.
4.  To select the movement zones in which packing is allowed:
    1.  Click **Packing Zones**.
    2.  In the **Available** column, select the check box next to the zones used for packing.
    3.  Click **Apply**.
5.  Click **Save**.

## Configure pack station processing

**Note**: Some actions on the Packing page may be configured with keyboard shortcuts. To view the configured shortcuts, in the page title bar, click ![Keyboard Shortcuts](../../../../../images/resources/images/keyboardhelp_29x20.png).

1.  Select **Configuration > Outbound > Packing > Pack Station**.
2.  Enter information in the [Pack Station fields](#Pack_Station_fields).
3.  To define the criteria used for automatic cartonization at a pack station:
    1.  Under **CARTONIZATION**, perform the following tasks:
        1.  To select the values and sequence in which to process a group of items for cartonization, click **Order-By**.
        2.  To select the values and sequence that determine when a new shipping container is started, click **Break-On Values**.
    2.  To select criteria from displayed entities:
        1.  If the advanced query is displayed, click **Simple**.
        2.  If the available entities are not displayed, click **Show Available**.
        3.  In the **Available** grid, select the entities that you want to use as criteria.
        4.  Click **Add selected**. The entities are added to the **Selected** grid.
        5.  To remove criteria, in the **Selected** grid, select the criteria to remove, and click **Remove selected**.
        6.  To reorder the criteria, in the **Selected** grid, click a row, and then click the up or down arrow to move the selected criteria. The application applies the criteria in sequential order according to how it is displayed in the grid.
    3.  To enter criteria using database entities, click **Advanced**, and then enter the column and field name, using a period to separate the column and field. Multiple column and field entries must be separated by a comma and space.
        
        You can use operators like IS NULL or IS NOT NULL to build an advanced query. For example, <column name>.<field name > IS NOT NULL, <column name>.< field name>.
        
    4.  Click **Apply**.
4.  To select the clients that allow automatic packing of sub-lines:
    
    **Note**: A sub-line is an item that must be shipped with the order line item (such as a user guide for a camera). The client configuration is only available in a 3PL environment and only if **Automatic Subline Packing** is set to Yes. Also, this feature is only supported when the sub-line number for the main item on the order line is 0 (zero), which is the default value.
    
    1.  Under **SUBLINE PACKING,** click **Clients**.
    2.  In the **Available Clients** column, select the check box next to the clients that allow automatic packing of sub-lines.
    3.  Click **Save**.
5.  To specify mixing restrictions for shipping containers:
    1.  Under **PROCESSING**, click **Packing Mixing Restrictions**.
    2.  For a 3PL environment, perform one of the following tasks:
        -   To add a client configuration, click **Add**, and then from the **Client** drop-down list, select the client.
            
            **Note**: To define warehouse default restrictions, from the **Client** drop-down list, select **Default**. Client-specific restrictions override the warehouse default restrictions.
            
        -   To modify a client configuration, in the grid, click the client.
        -   To copy a client configuration, in the grid, select the check box next to the client, click **Copy,** and then from the **Client** drop-down list, select the client.
    3.  In the **Attribute** column, select the check box next to the attributes for which different values are not allowed in the same shipping container.
    4.  Click **Apply**.
6.  To specify a print message for a client:
    
    **Note**: For each client you can specify whether a message is displayed to the packing operator indicating that paperwork is printed. The message is displayed when the last shipping carton for a shipment is completed. You can also specify the content of the message.
    
    1.  Under **PROCESSING**, click **Print Message Overrides**.
    2.  In the grid, click the client to configure.
    3.  To display a print message during packing operations:
        1.  Set the **Print Message** field to Yes.
        2.  In the **Message** field, enter the text that is displayed to the packing operator when paperwork is printed for a completed shipment.
        3.  Click **Apply**.
7.  To define the fields that are used to process an item at the pack station:
    1.  Under **PROCESSING**, click **Capture Fields During Packing**.
    2.  Perform one of the following tasks:
        -   To add a field, click **Add**.
        -   To modify a field, in the grid, click the field.
        -   To copy a field, in the grid, select the check box next to the field, and then click **Copy**.
    3.  Enter information in the [Processing Field fields](#Processing_Field_fields).
        
        **Note**: If you select the Custom field, you must also enter the command in the **Custom Field Parse Command** field.
        
    4.  Click **Apply**.
8.  For a 3PL environment, to select the clients that want to prevent packing until all inventory for a shipment has arrived at the pack location:
    
    **Note**: This configuration only takes effect in pack locations that are reserved by shipment, and does not apply to inventory (for the shipment) that is not processed at a pack station.
    
    1.  Under **PROCESSING**, click **Prevent Packing Until Inventory Arrival** **Configuration Overrides**.
    2.  In the **Available** column, select the check box next to the clients that apply.
    3.  Click **Apply**.
9.  For a 3PL environment, to select the clients that require packing operators to enter (or scan) both the item and serial number for each serialized item during packing:
    1.  Under **PROCESSING**, click **Capture Serialized Inventory**.
    2.  In the **Available** column, select the check box next to the clients that apply.
    3.  Click **Apply**.
10.  For a 3PL environment, to configure weight capture and weight tolerance by client:
     1.  Under **WEIGHT**, click **Weight Configuration Overrides**.
     2.  Perform one of the following tasks:
         -   To add a client configuration, click **Add**.
         -   To modify a client configuration, in the grid, click the client.
         -   To copy a client configuration, in the grid, select the check box next to the client, and then click **Copy**.
     3.  Enter information in the [Weight Configuration Overrides fields](#Weight_Configuration_Overrides_fields).
     4.  Click **Apply**.
11.  To define the movement path hop zones that should be skipped after packing based on the carton type that is processed:
     
     **Note**: This configuration is only available if **Skip Movement Hops** is set to Yes.
     
     1.  Under **POST PACKING** **MOVEMENT PATH EXCEPTIONS**, click **Movement Hops to Skip**.
     2.  Perform one of the following tasks:
         -   To define the hops to skip when pallet type cartons are processed, above the grid, select **Pallets**.
         -   To define the hops to skip when regular cartons are processed, above the grid, select **Cartons**.
     3.  Under **Available Zones**, select the check box next to the hop zones that should be skipped in the movement path after packing is complete.
     4.  Click **Apply**.
12.  Click **Save**.

## Packing Settings fields

 
| Field | Description |
| --- | --- |
| Close Carton | If Yes, when the final item from the picking container is confirmed as being packed into a shipping container, the application automatically closes the container and returns the operator to the pack initiation screen. The application determines when a shipping container is completely packed. Select Yes to eliminate the step that requires the operator to close the container.<br > If No, the packing operator must close the shipping container by clicking the Complete button. In this scenario, the packing operator determines when the shipping container is completely packed. This is useful when you want the packing operator record any potential overages. |
| Single Carton | If Yes, the packing operator is directed to pack all inventory for a single shipment into one shipping container. This is useful if you want to ensure all of the inventory for a single customer is packed into one container.<br > If No, the packing operator can pack the inventory for a single shipment into one or more shipping containers. |
| Default Scan Levels | Determines the identifier that the operator can enter (scan) to initiate pack station processing during packing. The initiation scan types defined for a specific workstation override the **Default Scan Levels**. See [Workstations](../../equipment/hardware/workstations.md).<br > **Note**: If the operator scans an identifier that is not enabled, the application displays a message stating that the device is not configured to scan this type of inventory identifier.<br>-   •
    
    **Location**: The operator can enter the location that contains the picked inventory that needs to be packed into a shipping container.
    
    <br>
    
    You might want to scan locations if you have small shelf locations set up at the pack station, if pickers deposit inventory into one side of a shelf location, and if the packing operator scans the shelf location ID while moving the inventory from the other side of the shelf location to the shipping container. This value is required if operators are using the Park Area Operations to pack the container.
    
    <br>
<br>-   • **LPN**: The operator can enter the LPN (such as a pallet LPN) that contains the picked inventory that needs to be packed into a shipping container.
<br>-   • **Sub-LPN**: The operator can enter the sub-LPN (such as for a case on a pallet or a tote on a cart) that contains the picked inventory that needs to be packed into a shipping container. |
| Special Handling Location | Location to which picked inventory containers are directed when errors (such as missing inventory, unexpected inventory or the wrong quantity of inventory) are encountered during pack station processing. The location appears as the default special handling location during pack station operations but can be changed by the packing operator to select a different special handling location. If a special handling location is defined for a specific workstation, then when packing is performed on that workstation and an error occurs, the picked inventory is directed to the special handling location defined for the workstation, not the location defined in this field. See [Workstations](../../equipment/hardware/workstations.md).<br > However, if you use the same special handling location to correct errors, you can set one location as the default. |
| Display Error Messages | If Yes, when the expected value does not match the entered value, the application displays a message. If the operator does not re-enter the correct value, then the error handling process is used.<br > If No, the application does not display an error message. However, the error is still visible to the operator in the Status column. This is useful if error correction is handled as a separate step at a special handling location. |
| Refresh Timer | Time duration, in seconds, that indicates how often the application updates the status of the locations on the Pack Area Operations window. The Pack Area Operations window displays the status of each of the packing station locations in which pack area operations can be performed. When the timer expires, the application refreshes the status of the displayed locations, for example, by updating a location from a status of Packing in Progress to Complete. |

## Pack Station fields

 
| Field | Description |
| --- | --- |
| Automatic Cartonization | If Yes, the application uses the inventory in a picking container to determine what size and how many shipping containers are needed.<br > If No, the operator performs cartonization without any planning or guidance from the application. |
| Break-On | If Yes, a packing operator cannot pack an item into a shipping container if doing so violates the separation of items based on the defined break-on values. For example, if the break-on value is Shipment, the application does not permit the operator to pack an item into a container that contains items for a different shipment.<br > If No, a packing operators can pack items into a single shipping container regardless of the break-on values. |
| Automatic Subline Packing | If Yes, then during pack station processing, if an order line has sub-lines, then a line and its sub-lines are automatically packed together. For example, if an order line for 2 cameras has two sub-lines, one for 2 user manuals, and one for 6 battery packs, then if the packing operator scans any of the items for packing, the rest of the items are selected. During sub-line packing, the application maintains the ratio of quantities required for the main item. Using the example, if the operator selects 3 battery packs, then the application automatically selects 1 camera and 1 user manual.<br>
**Notes**:

<br>

-   • If the item on an order line is bonded, then its sub-lines are considered bonded as well and are packed together with it.
<br>-   • This is feature is only supported when the sub-line number for the main item on the order line is 0 (zero), which is the default value.
<br>

<br > If No, then during pack station processing, order lines and sub-lines are not automatically packed together when one of the items is selected.<br > **Note**: If you select No (or in a 3PL environment, if you select Yes but do not include all clients), then at least one of the defined processing fields in the pack station configuration must have the **Use for Identification** field set to Yes. This enables the operator to manually select and scan the items to pack when auto packing is disabled. |
| Quantity Default | Determines the value (quantity) that is processed by default when the operator scans a piece of inventory. The operator is not allowed to override these values unless the **Override Quantity** field is set to Yes.<br>-   • **User Specified**: The **Value** field becomes available so that you can specify the default value that will be processed every time a user scan inventory. This can reduce the number of keystrokes required if the value is always (or almost always) the same, such as 1.
<br>-   • **Unit Quantity**: The quantity in individual units of each unique group of items. Items with the same item number can be separated into unique groups based on several attributes, such as lot, origin, and serial number. This option is useful when you want the packing operator to verify the inventory attributes while packing the shipping container. For example, there is a total of 5 units of ITEM01 in the picking container; 2 units are lot A and 3 units are lot B. If the packing operator scans an ITEM01 with lot B, the Quantity field defaults to 3 units. If the pack station operator scans ITEM01 with lot A, the UOM Quantity field defaults to 2 units. This lets the packing operator verify the quantity of each lot.
<br>-   • **Pick Quantity**: The value processed is whatever the pick quantity was when an item was scanned. So for example, if the operator has 5 of item PEN in the picking container, when the operator scans one of the item PEN the application will automatically process all 5. Then it is up to the operator to find the other 4 and put them all in the shipping container at once. This is useful if you want to require less operator interaction to speed up the packing process. |
| Value | Number displayed by default in the **Quantity** field when a packing operator is packing items into shipping containers. Only available when **User Specified** is selected in the **Quantity Default** field. |
| Override Quantity | If Yes, a packing operator can click the Update Quantity button during packing operations to enter a quantity and unit of measure different from the displayed default value of the item that is being packed into a shipping container.<br > If No, the operator is not allowed to override the default value for the item being packed. |
| Auto Process on Change | If Yes, picked inventory is automatically moved to the ready-to-process state when a shipping container is selected. This is useful if you want to reduce the number of clicks the operator is required to perform during pack station operations.<br > If No, the packing operator must click Process to move the inventory to the shipping container. |
| Parse Carton Type | If Yes, the application populates the Carton Type field when the packing operator enters a shipping container ID. The value for the carton type is parsed from the shipping container ID using the command specified in the **Parse Command** field.<br > If No, the operator must select a carton type for the shipping container. |
| Parse Command<br>  | Command used to parse a carton type from the shipping container ID that is entered during packing. The resulting carton type is displayed in the Type field. This sample command is provided: **Parse Carton Code for Carton Number**. It includes instructions and an example of how to write a command that would parse a carton type from a bar code. You or your project team can use the instructions as a starting point in determining how to code the input (information the command needs to run) and output (error messages and other data that results from running the command). For more information, contact your Blue Yonder project team.<br > Only available when the **Parse Carton Type** field is set to Yes. |
| Processing Destination Zone | Movement zone to which a completed packed shipping container is to be deposited. A completed packed shipping container is automatically moved to the zone. |
| Custom Field Parse Command | Name of the command that processes the value entered into the Custom field, if it has been configured to be used during packing operations.<br > If the Custom field has been selected to be captured during packing, you must enter the command used to parse information from the value that is entered into the Custom field. The command can be used, for example, to parse information from a bar code scan (such as item number, expiration date, and lot number) to populate other processing fields.<br > The following sample command is provided: **Parse Packout Custom Field**. It includes instructions and an example of how to write a command that would parse multiple fields from a bar code. You or your project team can use the instructions as a starting point in determining how to process the input (information the command needs to run) and output (error messages and other data that results from running the command). For more information, contact your Blue Yonder project team. Only used if a Custom processing field value is selected to be captured during packing. |
| Pack Multiple Shipments Simultaneously | If Yes, packing operators can pack containers for multiple shipments at the same time. This functionality is typically used for high-volume pack stations, such as those fulfilling multiple shipments for online orders. During this process, the operator can scan any piece of inventory at the pack station and the application directs the operator to pack the inventory in the appropriate shipping container; this functionality retains the original inventory-to-shipment assignment that is determined during picking.<br > Select Yes, for example, if your warehouse processes a high volume of e-commerce orders where multiple eaches of different items are picked to different slots on a master handling unit. In this scenario, an operator can scan the master handling unit and also a specific slot number to uniquely identify the inventory. The operator is not required to locate a specific piece of inventory and can scan any inventory from the slot. The application then directs the operator to the correct shipping container based on the inventory that was scanned.<br > If No, packing operators can only pack inventory for a single shipment, but the application uses dynamic pairing functionality to pair scanned inventory with the shipping container that is being packed, regardless of whether the inventory was originally assigned to that shipment.<br > For example, assume two eaches of the same item are picked for two different shipments. If the packing operator scans the inventory assigned to the shipment that is not currently being packed, the application verifies that the inventory does not violate any order line restrictions for the current shipment. If it does not, the application swaps the inventory and allows the operator to pack the inventory for the current shipment. If the scanned inventory violates any order line attributes, an error is displayed and the operator must locate the correct inventory.<br > **Note**: Generally, the most common break-on value for packing containers is Shipment; however, this configuration applies to any defined break-on value. For example, if the break-on value was Customer, then with this configuration set to Yes, packing operators could pack shipping containers for multiple customers at the same time. |
| Prevent Packing Until Inventory Arrival | If Yes, an operator is not allowed to start packing until all of the inventory for a shipment has been deposited to the pack location. This setting only takes effect for pack locations that are reserved by shipment. That is, the pack location belongs to a movement zone that has a resource type of Derived and an attribute of Shipment ID. See [Processing Location Reservation](../../inventory/movement/processing-location-reservation.md).<br > Select Yes if you want the application to prevent the operator from starting to pack a shipment before all of the inventory for the shipment has arrived at the pack location, not including inventory that is not destined for a pack location. If set to Yes, the pack initiation page displays a status for each location in the workstation's processing zone that is reserved by shipment. The status indicates whether packing can begin, and the grid provides visibility to the picking containers in the location.<br > If No, the application allows the operator to start packing even if all of the inventory for a shipment has not arrived. |
| Print Message | If Yes, the application displays a message when paperwork is printed during pack station processing when a shipment is completed. Select Yes if you want a message to be displayed to the packing operator indicating that the paperwork has been printed. If you select Yes, then in the **Message** field, enter the message that you want to be displayed to the packing operator.<br > **Note**: A background workflow can be configured to print a packing slip report when the last container for a shipment is closed. See [Background Workflows](../../work/warehouse-workflows/background-workflows.md).<br > If No, then a message is not displayed to the packing operator when paperwork is printed after a shipment is complete. |
| Message | Text that is displayed to the packing operator during pack station processing when paperwork is printed for a completed shipment. This field is only available if **Print Message** is set to Yes. For example, the following message could be displayed: Packing slip is printing. Retrieve from the printer. |
| Capture Serialized Inventory | If Yes, then when packing serialized items, the packer is required to enter (or scan) each item and then the serial number for that item. The packer is not allowed to enter multiple serial numbers or a range of serial numbers for an item quantity greater than 1.<br > If No, the packer is allowed to scan an item and then, for an item quantity greater than 1, enter multiple serial numbers or a range of serial numbers. |
| Validate Maximum Carton Weight | If Yes, the application validates the weight of the shipping container being packed and displays a message to the operator if the packed weight exceeds the maximum weight defined for the carton type. The weight validation is performed against the actual weight (provided by a scale) or an estimated weight. The estimated weight is calculated by the application as the operator packs each item. The application retrieves the gross weight of the item from its item footprint and accumulates the weight of the items added to the container. If the weight is more than the maximum allowed weight defined for the carton type, a warning message is displayed. The packing operator can then either cancel packing an item into the current shipping container (saving it for a different shipping container for the same shipment) or ignore the warning and pack the item in the container. Also, if the packing operator chooses to ignore the overweight warning, additional items can be packed into the shipping container, but no additional weight warnings are displayed.<br > If No, the application does not display a message to the operator if the packed weight exceeds the maximum weight defined for the carton type. This means that the packing operator must manually ensure that the items packed into a shipping container do not exceed the maximum allowed weight defined for the carton type. |
| Capture Required | If Yes, the packing operator is required to enter an actual weight for each shipping container. The weight can be captured, for example, from an integrated or standalone scale. The application does not allow the operator to close a shipping container without capturing the weight.<br > If No, the application allows the operator to close a shipping container without capturing the carton weight. |
| Automatically Capture Weight from Scale | If Yes, then during pack station processing, the application captures the actual weight of a packed shipping container when the operator attempts to close the container. If weight capture is required but the weight cannot be captured (for example, because of a problem with the scale), the operator must direct the carton to an exception location for processing.<br > If No, then during pack station processing, the application does not automatically capture the weight of a packed shipping container. If weight capture is required, the operator must enter an actual weight, for example, based on an integrated or standalone scale. |
| Percent Below | Percentage of weight below the estimated weight that is allowed for a packed shipping container. The application calculates estimated weight based on the item footprint information for the items packed into the shipping container, and compares that weight to the actual weight. Actual weight is provided by the operator or an integrated scale. The minimum tolerance level is used to help verify that the correct quantities have been packed into the shipping container.<br > For example, if this value is set to 10 (10%), and the estimated container weight is 100 pounds, then if the actual container weight is 90 pounds, the container is acceptable. However, if the actual container weight is less than 90 pounds and the **Prevent Closure on Weight Discrepancy** field is set to Yes, the operator is not allowed to close the container. If the **Prevent Closure on Weight Discrepancy** field is set to No, then the operator is warned that the captured weight is outside of tolerance, but the operator can choose to close the container. |
| Percent Above | Percentage of weight above the estimated weight that is allowed for a packed shipping container. The application calculates estimated weight based on the item footprint information for the items packed into the shipping container, and compares that weight to the actual weight. Actual weight is provided by the operator or an integrated scale. The maximum tolerance level is used to help verify that the correct quantities have been packed into the shipping container.<br > For example, if this value is set to 10 (10%) and the estimated container weight is 100 pounds, then if the actual container weight is 110 pounds, the container is acceptable. However, if the actual container weight is greater than 110 pounds and the **Prevent Closure on Weight Discrepancy** field is set to Yes, the operator is not allowed to close the container. If the **Prevent Closure on Weight Discrepancy** field is set to No, then the operator is warned that the captured weight is outside of tolerance, but the operator can choose to close the container. |
| Prevent Closure on Weight Discrepancy | If Yes, then when the difference between the actual weight of a packed shipping container and its estimated weight is greater than the tolerance values, the application prevents the operator from closing the shipping container.<br > If No, the application does not prevent closing a shipping container based on a discrepancy between actual and estimated weights. |
| Skip Movement Hops | If Yes, then when inventory is processed at the pack station, the movement path for the inventory is automatically updated to skip the hop zones you defined based on the carton type being processed. Typically this configuration is used to update the movement path for pallet type cartons to avoid unnecessary hops. A pallet type carton is a physical pallet that is used, for example, to pack full cases or boxed items directly to a pallet without overpacking to a shipping container.<br > For example, picked inventory is usually packed into shipping cartons, which are directed to a consolidation location for building into pallets, and then to a final staging location (the final destination on the movement path). However, for pallet type cartons, there is no need for consolidation. For this scenario you can skip the consolidation zone for pallet type cartons so that they can be directed to the final staging zone. Alternatively, for a shipping carton requires consolidation, you can include the consolidation zone but may want to skip a hop intended only for pallet type cartons, such as a wrapping zone.<br > If No, then the movement path out of the pack station is not updated to skip movement hops for any type of carton. |

## Processing Field fields

 
| Field | Description |
| --- | --- |
| Client | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. During packing, the application determines which client is associated with the shipping container, and prompts the operator to validate the attributes that the client requires. If you do not specify fields for a specific client, then during packing, the fields specified for the Default client are used. |
| Sequence | Number that defines the order in which the **Field** value is displayed during pack station processing when the item information is displayed. |
| Field | Attribute used to process an item being packed into a shipping container. Depending on how you configure the application, this field value is used to capture information about the item or is also used to specifically identify the item as it is being packed into a shipping container. |
| Auto Fill | If Yes, during pack station processing, the value of the processing field is populated automatically with the expected value based on the contents of the picking container.<br > If No, the operator must enter in the field value.<br > See [Processing fields](#Processing_fields). |
| Use for Identification | If Yes, the application uses the **Field** value to identify the item being packed. Select Yes if you want the processing field to be used during pack station operations to determine (identify) the specific item from the picking container that is being packed into the shipping container.<br > If No, the **Field** value is not used to identify or validate the item, but instead is used to capture information about the item that is needed for other processes.<br>
**Notes**:

<br>

-   • Unless the packing operator uses drag-and-drop selections exclusively, at least one of the processing fields must have the **Use for Identification** field set to Yes. Also, the combination of fields used for identification must be specific enough that the application can display a unique item and item client based on the inventory in the picking container.
<br>-   • If the **Automatic Subline Packing** field in the pack station configuration is set to No (or in a 3PL environment, if it is set to Yes but not all clients are included), then at least one of the processing fields must have the **Use for Identification** field set to Yes. This enables the operator to manually select and scan the items to pack when auto packing is disabled.
<br>

 |
| Enable Barcode Scanning | If Yes, operators can scan a GS1-128 barcode into the processing field while packing inventory. The application parses the relevant data from the barcode and populates the processing field with the value. For example, if you are configuring the Lot field for pack station processing and you set this field to Yes, then an operator can scan a barcode while the cursor is focused on the Lot field, and the application populates the field with the parsed lot number.<br > If No, the application does not parse values from a scanned barcode for this processing field. |
| Visible | If Yes, the processing field is displayed to the operator during pack station operations.<br > If No, the field is not displayed. This is useful in situations where you need a value for a particular field, such as for use in custom code, but packing operator does not use the field or its value on the screen. Contact your Blue Yonder project team for more information on using hidden fields on windows.<br > See [Processing fields](#Processing_fields). |

## Weight Configuration Overrides fields

 
| Field | Description |
| --- | --- |
| **Client** | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. During packing, the application determines which client is associated with the shipping container, and prompts the operator to validate the attributes that the client requires. If you do not specify fields for a specific client, then during packing, the fields specified for the Default client are used. |
| Capture Required | If Yes, the packing operator is required to enter an actual weight for each shipping container. The weight can be captured, for example, from an integrated or standalone scale. The application does not allow the operator to close a shipping container without capturing the weight.<br > If No, the application allows the operator to close a shipping container without capturing the carton weight. |
| Automatically Capture Weight from Scale | If Yes, then during pack station processing, the application captures the actual weight of a packed shipping container when the operator attempts to close the container. If weight capture is required but the weight cannot be captured (for example, because of a problem with the scale), the operator must direct the carton to an exception location for processing.<br > If No, then during pack station processing, the application does not automatically capture the weight of a packed shipping container. If weight capture is required, the operator must enter an actual weight, for example, based on an integrated or standalone scale. |
| Percent Below | Percentage of weight below the estimated weight that is allowed for a packed shipping container. The application calculates estimated weight based on the item footprint information for the items packed into the shipping container, and compares that weight to the actual weight. Actual weight is provided by the operator or an integrated scale. The minimum tolerance level is used to help verify that the correct quantities have been packed into the shipping container.<br > For example, if this value is set to 10 (10%), and the estimated container weight is 100 pounds, then if the actual container weight is 90 pounds, the container is acceptable. However, if the actual container weight is less than 90 pounds and the **Prevent Closure on Weight Discrepancy** field is set to Yes, the operator is not allowed to close the container. If the **Prevent Closure on Weight Discrepancy** field is set to No, then the operator is warned that the captured weight is outside of tolerance, but the operator can choose to close the container. |
| Percent Above | Percentage of weight above the estimated weight that is allowed for a packed shipping container. The application calculates estimated weight based on the item footprint information for the items packed into the shipping container, and compares that weight to the actual weight. Actual weight is provided by the operator or an integrated scale. The maximum tolerance level is used to help verify that the correct quantities have been packed into the shipping container.<br > For example, if this value is set to 10 (10%) and the estimated container weight is 100 pounds, then if the actual container weight is 110 pounds, the container is acceptable. However, if the actual container weight is greater than 110 pounds and the **Prevent Closure on Weight Discrepancy** field is set to Yes, the operator is not allowed to close the container. If the **Prevent Closure on Weight Discrepancy** field is set to No, then the operator is warned that the captured weight is outside of tolerance, but the operator can choose to close the container. |
| Prevent Closure on Weight Discrepancy | If Yes, then when the difference between the actual weight of a packed shipping container and its estimated weight is greater than the tolerance values, the application prevents the operator from closing the shipping container.<br > If No, the application does not prevent closing a shipping container based on a discrepancy between actual and estimated weights. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
