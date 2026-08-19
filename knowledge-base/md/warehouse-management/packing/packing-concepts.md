---
title: "Packing concepts"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/packing_concepts.htm"
source: "/content/packing_concepts.htm"
toc_path:
  - "Warehouse Management"
  - "Packing"
  - "Packing concepts"
sections:
  - "Pack stations"
  - "Packing operations"
  - "Options available during processing"
  - "Packing user interface"
  - "Pack locations reserved by shipment"
  - "Carton type options during packing"
  - "Weight capture during packing"
  - "Serial number capture during packing"
  - "Order lines and sub-lines during packing"
  - "Mixing restrictions during packing"
  - "Bonded inventory during packing"
  - "Pallet consolidation after packing"
  - "Packing errors"
  - "Manifest at pack station"
images: []
source_sha1: 5ba6d831233f5d52ec97579c20ad2dc8ae509144
---
# Packing concepts

You use the Packing module to manage the people, equipment, inventory, and processing involved in packing inventory into containers. You can make adjustments to inventory, work, pack stations, and other factors that can improve the productivity and efficiency of warehouse packing activities.

The following information will help you understand how to use the Packing module:

-   Pack station processing procedures differ depending on how packing is configured for the warehouse. See [Packing operations](#Packing_operations).
-   The options available during pack station processing differ depending on the procedure that you use. See [Options available during processing](#Options_available_during_processing).
-   The user interface directs the operator through the process of inducting picked inventory and then packing inventory into shipping containers. Processing starts by selecting your workstation and then scanning the picking container (container, slot, or location) that contains the picked inventory. See [Packing user interface](#Packing_user_interface).
-   The application notifies the operator of data entry and other errors and prevents processing invalid inventory. See [Packing errors](#Packing_errors).
-   Step-by-step procedures guide you through the packing process. See [Procedures for packing](procedures-for-packing.md).

## Pack stations

A pack station is a processing location where an operator moves picked inventory out of a picking container (which can be a container, slot, or location) and packs it into one or more shipping containers, as directed by the application. When a container is completed, the application moves it to the pack staging location. If damaged inventory, unexpected inventory, overages, shortages or other errors occur during the packing process, the picking container (along with any inventory that has not been completed) is directed to a special handling location, where a packing exception operator processes the picking container.

## Packing operations

Pack station processing supports the following operations:

-   **Pack one shipping container at a time**: The operator inducts inventory into the pack station by scanning an identifier (LPN, sub-LPN, or location, depending on what is configured for the warehouse). The operator scans the picked inventory and packs it into a shipping container until the container is either filled or contains all the required inventory. The operator selects the next shipping container and continues packing.
-   **Pack multiple containers simultaneously**: The operator inducts inventory into the pack station by scanning an identifier. The operator can pack into any of the shipping containers without having to close one container before starting the next container. The operator scans each item and packs it into the appropriate shipping container, as directed by the application.
-   **Pack with shipping cartonization enabled**: When shipping cartonization is enabled, the application displays the optimal carton type for packing the inventory. This process allows the inventory for one shipment to be picked to multiple picking containers. On the initiation page, the application displays partially packed shipping containers for which additional inventory is required. During packing, when all inventory from a picking container has been packed, the application prompts the operator to scan the next picking container so that the packing of partially packed (in-process) shipping containers can continue. In-process shipping containers that require inventory from another picking container are displayed on the initiation and processing pages with a label that states "Inventory Remaining".

## Options available during processing

When performing packing operations, the following options are available:

-   **Update quantity**: During packing, the operator can select an item and change its quantity. If the quantity is increased, a new line item is added to the grid with a status of OVERAGE. The operator can reverse the status of an OVERAGE by the updating the quantity of that line item to 0 (zero).
-   **Mark damaged**: During packing, the operator can select an item and mark all or a partial quantity as DAMAGED. If a partial quantity is damaged, a new line item is added to the grid. The status is changed to DAMAGED. This action can be reversed by changing the damaged quantity to 0 (zero).
-   **Split a container quantity to another container**: The operator can close (complete) a partially packed shipping container, so that the rest of its intended contents are placed in a new shipping container. This is typically done when no more inventory will fit into the original container. The application directs the remaining inventory for the original container to a new shipping container (created automatically in the same position). If shipping cartonization is enabled, the split can be done from the identifier page where partially packed shipping containers are displayed. Otherwise, the split is done during processing.
    
    **Note**: If the packing general settings option that forces all items into a single container is set to Yes, then the operator is not allowed to split a quantity to another container.
    
-   **Skip a container that is partially packed**: The operator can stop packing a shipping container, start packing another container, and then return to the partially packed shipping container. The application maintains the status of all the items that have been packed into each shipping container. The operator selects a container by clicking it. If packing one shipment at a time, a confirmation message is displayed asking the operator to confirm that they want to pack a different container.
    
    **Note**: If the pack station configuration option to pack multiple shipments simultaneously is set to Yes, skipping a shipping container is part of the process and so the confirmation message is not displayed.
    
-   **Pack an item to any container that requires it**: Each piece of inventory is picked for a specific shipment; however, when packing multiple containers at the same time, if the operator scans an item for a different container but the item is identical to the one required, the item can be packed to the current container if the following conditions exist:
    -   The inventory attributes specified on the order line match the inventory that is being used. For example, if the order line specifies a particular lot, then only inventory with a matching lot can be used.
    -   The LPN level of the inventory being replaced matches the inventory being used.
    -   For a sub-LPN (case), the quantity associated with the sub-LPN matches the inventory being used.
-   **Cancel picking container**: After inducting a picking container, the operator can cancel processing from the processing page by clicking **Cancel Picking Container**. As a result, the current picking container is cancelled and the initiation page is displayed. Inventory that has been completed (packed into containers that were completed) cannot be cancelled. Shipping containers that were in progress (partially packed) are cleared as if they had not been packed. Therefore, the operator must remove inventory from partial shipping containers and return it to the picking container.

If the operator scans the same picking container, only the shipping containers that were not completed are displayed.

When packing for a shipping container is complete, the following actions take place:

-   **Operator completes the shipping container**: If auto-close carton is enabled, then when packing for a shipping container is complete, the application moves the container to the pack staging location, and the scan identifier page is displayed to the operator. The operator does not have to click **Complete** to close the container. If auto-close carton not enabled, then when packing is complete for a container, the operator clicks **Complete**.
-   **Special handling**: Error processing, which is initiated by clicking **Error Picking Container**, is used to direct a picking container to a special handling location when one or more of the following errors occur:
    -   Any portion of picked inventory is damaged
    -   The quantity packed does not match the required quantity
    -   The user scans inventory that is not expected for the current shipping container

At the special handling location, the special handling operator typically unpicks the inventory from the container. If the special handling operator uses a cancel code that reallocates the picks, the reallocated picks are directed to a new picking container. The operator can merge the new container to the original picking container and move the container back to the pack station. The packing operator can scan the picking container and resume packing the shipping container.

## Packing user interface

The following user interface elements are part of packing operations:

**Note**: After selecting the packing function, you may be prompted to select the workstation that you are using to perform packing operations. After that, the initiation page is displayed.

-   **Initiation page**: Displays a field with a label that states **Scan identifier to get started**. The required identifier is an LPN, sub-LPN, or location that contains the picked inventory that needs to be packed. The configuration of packing general settings defines the identifiers that operators can scan to initiate packing.
    
    You can also initiate pack station processing by scanning a handling unit (such as a trolley) and handling unit slot. Multiple shipping containers can be packed with the inventory from the slot (picking container). After the contents of the slot have been packed, the operator can scan the next slot and continue packing the shipping containers. This feature is available when handling unit tracking is enabled for inventory or picking containers, and the packing general settings default scan level is defined as LPN.
    
-   **In-process containers**: If shipping cartonization is enabled and there are any in-process (partially packed) shipping containers, they are displayed with a message that states "Inventory Remaining." This means that the shipping container is partially packed, but requires inventory from another picking container before it can be completed.
-   **Processing page**: Displays the following shipping container and item information:
    -   **Carton fields**: When a shipping container is selected, the shipping container identifier, carton type, and weight fields are displayed. Estimated weight represents the weight of the carton and its contents (based on item footprint configuration). Actual weight represents the weight obtained from an integrated scale measuring the actual weight of the carton and its contents. If a scale is not integrated with the workstation, the operator can enter actual weight based on the estimated weight or the weight obtained from a standalone scale.
    -   **Inventory identifier fields**: Inventory identifier fields allow the operator to scan each piece of picked inventory and pack it to the shipping container as directed by the application. The application uses these fields to uniquely identify the inventory. Scanning the inventory without having to select it from a grid is the fastest packing process.
    -   **Grid view of picked inventory**: When an item is scanned or a shipping container is selected, a grid displays the items that the application expects in the picking container. The operator can select an item to change its quantity, mark it as damaged, or process (pack) it.
    -   **Shipping containers**: To the right of the inventory fields, one or more shipping containers are displayed. Each one is identified by a container identifier (sub-LPN), carton type, and a progress bar that shows the packing status of the container (the quantity required, quantity packed, and percent complete). By scanning any piece of inventory, the user is directed to the correct shipping container.
        
        Each container is also identified with a number (such as 1, 2, or 3) that represents the position of the container on the floor. If a container becomes full before all of the inventory it requires is packed, then when it is completed, the application creates a new container in the same position and directs the rest of the inventory required for the original container to the new container.
        
    -   **Process button**: Indicates that the selected items have been packed into the shipping container, and changes the status of selected items to PACKED.
    -   **Unpack button**: Used to removed packed inventory from a shipping container.
    -   **Mark All Damaged button**: Changes the status of all the inventory in the grid to DAMAGED.
    -   **Print Paperwork button**: Prints the paperwork (reports or labels) for the picking container.
    -   **Capture Weight button**: Used to capture the weight of a packed container or pallet based on the value provided by an integrated scale. If a scale is integrated with the pack station, the button is aways available; otherwise, it is hidden. When the button is clicked, the weight is captured and displayed in the **Actual Weight** field, overwriting any previous value. If weight cannot be captured, the reading returns to zero and a notification is displayed to the operator.
    -   **Error Picking Container button**: Initiates error processing, which is used to direct a picking container to a special handling location when one or more of the following errors occur:
        -   Any portion of picked inventory is damaged
        -   The quantity packed does not match the required quantity
        -   The user scans inventory that is not expected for the current shipping container
    
    At the special handling location, the special handling operator typically unpicks the inventory from the container. If the special handling operator uses a cancel code that reallocates the picks, the reallocated picks are directed to a new picking container.
    
    -   **Cancel Picking Container button**: Cancels the current picking container and displays the initiation page. If shipping cartonization is not enabled, shipping containers that were in progress (partially packed) are cleared as if they had not been packed. If shipping cartonization is enabled and the operator scans the same picking container, any in-process shipping containers are displayed.
    -   **Complete button**: Completes the current shipping container. Used to indicate that all the inventory required for the container has been packed, or that no additional inventory can fit into the container.
        -   If no additional inventory can fit into a container that requires additional items, then when the operator clicks **Complete**, a confirmation message is displayed asking if there is inventory left in the container. If Yes, the application completes the container and creates a new shipping container to contain the rest of the inventory that was required for the original container. If No, a new container is not created.
        -   If exception inventory was packed, clicking **Complete** displays the Log Error window for the operator to select a reason for the error and a special handling location. If inventory was inducted from a location (not a picking container), the application prompts the operator to enter a new picking container to use to transfer the inventory to the special handling location. When the operator clicks **Log Error**, the picking container is moved to the selected location, and the initiation page is displayed for the operator to scan the next identifier.
            
            **Note**: Exception inventory is inventory that is unexpected, damaged, or over or short the required quantity.
            
    -   **Add Media and View Media buttons**: Used to view or capture media. Images (such as JPEG, PNG, GIF, and BMP) can be added or viewed. Files (such as TXT, DOC, and PDF) can be added or downloaded for viewing in their respective application, such as a text editor, Microsoft Word, or Adobe Reader. Images and files can also be deleted.
        

## Pack locations reserved by shipment

On the packing initiation page, a grid displays the following statuses for locations in the workstation's processing zone that are reserved by shipment:

**Notes**:

-   When a pack location is reserved by shipment, then inventory for a different shipment is not directed to the location until the current inventory has been packed.
    
-   The **Prevent Packing Until Inventory Arrival** field in the pack station configuration determines whether packing is prevented until all of the inventory to be packed for a shipment has arrived.
    

-   **Not Ready - Inventory Pending**: Indicates that configuration prevents packing until all of the inventory to be packed for a shipment has arrived, and that some inventory has not arrived.
-   **Ready to Pack - Inventory Arrived**: Indicates that configuration prevents packing until all of the inventory to be packed for a shipment has arrived, and that all of the inventory has arrived.
-   **Pack as inventory arrives**: Indicates that configuration does not prevent packing until all of the inventory to be packed for a shipment has arrived, and that some or all of the inventory has not arrived.
-   **Ready to Pack**: Indicates that configuration does not prevent packing until all of the inventory to be packed for a shipment has arrived, and that all of the inventory has arrived.
-   **Packed - Inventory Processed**: Indicates that packing is complete for the shipment, and the location remains reserved by the packed shipment until the next shipment reserves the location. This status is only displayed if the **Automatically Clear Processing** field is set to No for the location type.

The grid also allows the operator to view the picking containers that have been deposited to each pack location reserved by shipment.

The operator can start packing from any location that is in either Ready to Pack status, or from locations that are not reserved by shipment.

## Carton type options during packing

When picked inventory arrives at the pack station in a carton or box, the operator can use one of the following options to avoid packing the carton or box to another carton:

-   **Pack to a generic carton**: During pack station processing, the operator can change the carton type to a generic carton type. This allows the operator to process the inventory for the carton or box without packing it to a shipping container. When the operator scans the next item from the picking container, the generic carton type is displayed. For example, if a quantity of 6 was picked as a case instead of individual eaches, the packing operator can process this pick as a generic carton instead of over-packing it to another carton.
    
    During processing, if dimensions were not pre-defined for the generic carton type, a window is displayed for the operator to enter its dimensions. If they were pre-defined, the operator can choose to edit the dimensions.
    
-   **Pack to a pallet type carton**: During pack station processing, the operator can change the carton type to a pallet type carton. This allows the operator to process picked inventory directly to a pallet without packing it to another carton. After packing to the pallet, the operator can edit the dimensions and enter the actual number of cartons that were placed on the pallet. The application does not allow the operator to complete the shipping container without entering a value for height. If the operator selects a pallet type carton, the operator cannot select a different carton type as the shipping container without cancel the picking container and starting over.

## Weight capture during packing

There are two options for obtaining the weight of a packed shipping container or pallet: estimated weight and actual weight.

-   Estimated weight is a displayed value provided by the application. It represents the weight of the packed inventory (based on item footprint configurations) and the weight of the empty carton type. The value of this field is display only, and is incremented as inventory is packed.
-   Actual weight is calculated by a scale that is integrated (through a network connection) to the pack station workstation. Weight capture can be configured to take place automatically when a shipping container is closed, or when an operator initiates the capture by clicking **Capture Weight**. If a scale is not integrated, the operator can enter a value for actual weight manually.

If automatic weight capture is enabled, then the following processes take place:

-   If no scale is integrated with the workstation, then a message is displayed when the operator starts the pack station functionality indicating that the scale is not connected.
-   If the weight cannot be captured from the scale or the scale returns a reading of zero, then an error is displayed and the operator is not allowed to complete the shipping container.

If automatic weight capture is not enabled, then one of the following processes takes place:

-   If the operator is not required to capture weight, the estimated weight is used and a value for actual weight is not required.
-   If the actual weight is zero and the operator is required to capture weight, then the operator must enter a value in the **Actual Weight** field. If weight capture is required and the **Actual Weight** field is left blank, then an error is displayed and the operator is not allowed to complete the shipping container until a value is provided.

If the actual weight is different from the estimated weight, and the discrepancy exceeds the tolerance limits (minimum and maximum percentage allowed), then an error is displayed. If the application is configured to prevent closing a shipping container when tolerance limits are exceeded, then the operator is not allowed to complete the shipping container.

A shipping container that cannot be closed due to a weight error must be sent to an exception operator for processing. The Weight Discrepancy reason code is provided for this type of exception.

## Serial number capture during packing

As inventory is moved in and around a warehouse, specific items may be marked with serial numbers that need to be tracked in the warehouse.

If an item is configured with a serialization type, the serialization type determines when serial number capture and validation takes place.

-   For the Cradle to Grave serialization type, serial numbers are captured during receiving and anytime the inventory quantity is changed. Serial numbers are validated for every partial move or transfer, and during packing.
-   For the Outbound Capture Only serialization type, serial numbers are captured during outbound processes, after picking, while confirming a paper pick, and after packing. For items with this configuration, serial numbers are validated during packing.
-   For the Outbound Capture Only serialization type, an additional configuration dictates that serial number capture is delayed until packing. For items with this configuration, serial numbers are captured during packing.

Serial number capture or validation (depending on the serialization type) can take place at the pack station for items that are configured for serialization at the Detail LPN level.

**Note**: For serial numbers to be validated during packing, Serial Number must be configured as a processing field. See [Processing fields](../configuration/inventory/items/items.md).

When serial-tracked inventory is processed at the pack station, the application displays the serial numbers (by serial number type) that have been captured for the inventory. If capture needs to take place during packing for an item, then the application displays the serial number types for that item for which serial numbers must be recorded.

The following processes take place during packing to support serial number capture after the operator scans the initial identifier (picking container or location):

-   Items that require a serial number are tagged as "Serialized".
-   If the operator scans an item that requires one or more serial numbers, or selects a serialized item in the grid, the serial number type fields are displayed for entering the serial numbers.
-   If the quantity of the item is greater than 1, the **Enter a range** link is displayed. The operator can enter serial numbers one by one, or click on the link and enter the start and end serial range values in the **Start** and **End** fields.
    
    **Note**: Depending on configuration, you may not be allowed to capture multiple (or a range) of serial numbers for an item quantity greater than 1. Instead, each item must be scanned and captured, as it is done for a quantity of 1.
    
-   If the operator selects multiple serialized items in the grid, the **Process** button is not available because the operator must enter serial numbers for each different item individually.
-   If the operator unpacks a serialized item from the shipping container, the operator is prompted to enter the serial number of the item. If the operator unpacks the entire quantity of a serialized item, the operator is not prompted for serial numbers because they have all been unpacked.

The application does not allow operators to enter a duplicate serial number for the same serial number type.

## Order lines and sub-lines during packing

An order line is a quantity of an item specified on an order. A sub-line is a quantity of a different item (also specified on the order) that is required to be shipped with an order line. For example, an order line quantity may be for 1 camera, and a sub-line quantity may be for 1 user manual. One user manual must be shipped with each camera. An order line may have one or more sub-lines, or no sub-lines.

**IMPORTANT**: This is feature is only supported when the sub-line number for the main item on the order line is 0 (zero), which is the default value. However, if it is configured to be any other value, the application will consider it a sub-line and not the main item.

If the application is configured to automatically pack sub-lines with order lines, then the following processes take place:

-   When the packing operator scans or selects a line item to pack, then its sub-lines are automatically processed along with the line item.
-   When the operator scans or selects a sub-line item to pack, then its related line item and sub-lines are automatically processed along with the sub-line item.
-   When the operator scans or selects a partial quantity of a line item or sub-line item to pack, then a proportionate quantity of its line and sub-line items are also automatically selected and processed along with it. If a proportionate quantity cannot be packed, an error is displayed and the partial quantity is not allowed to be packed. For example, if a line item for 2 cameras has a sub-line for 2 user manuals and 6 battery packs, the operator is not allowed to pack 2 battery packs because 3 battery packs are required for each camera.
-   If any sub-line item is serialized, the sub-line is not automatically packed even if auto-packing is enabled.
-   If an order line item is bonded inventory and its sub-lines are duty free, the sub-lines are packed together with the bonded line item.
-   If the operator unpacks a main item, all of its sub-line items are unpacked as well.
-   Sub-lines are displayed in a different color than the main item for enhanced visibility to the operator.

If the application is not configured to automatically pack sub-lines with order lines, then the operator is required to select or scan each line item and sub-line item to pack it.

## Mixing restrictions during packing

Mixing restrictions prevent processing mixed inventory (based on selected attributes) to the same shipping container. Mixing restrictions for packing can be defined for a warehouse or, for a 3PL environment, by client.

During pack station processing, the application supports the separation of inventory that should not be mixed. It validates the inventory prior to packing and creates additional shipping containers as needed so that inventory that should not be mixed can be packed to separate containers. It also prevents closing a shipping container that has been packed with mixed inventory that violates restrictions.

For example, if the item family attribute is defined as a mixing restriction, then during pack station processing, the application validates the inventory's item family. If multiple item families are included in the same shipment, the application creates additional shipping containers for packing each item family in a separate container.

## Bonded inventory during packing

Bonded inventory is inventory for which customs and excise duties are required. In a bonded warehouse (one that is integrated with a duty management application), the application tracks and processes bonded inventory so that it can be properly assessed for payment of required duties, taxes, and other charges.

For outbound processing, the application uses customs order types to determine whether fees and taxes must be paid when bonded inventory is shipped. The customs order type can be configured to allow or disallow mixing of bonded and duty free inventory in the same shipping container.

During pack station processing, when mixing bonded and duty-free inventory is not allowed (based on the configuration of the custom order type), the application creates additional shipping containers as needed to ensure that bonded inventory is not packed in the same container as duty-free inventory. When packing bonded inventory, a tag is displayed under the shipping container indicating it is Under Bond. The tag is used to notify the operator that the shipping container is reserved for bonded inventory. The application directs packing bonded and duty-free inventory to separate shipping containers unless the customs order type is configured to allow mixing.

## Pallet consolidation after packing

The packing operator may be directed to consolidate complete, non-pallet shipping containers to a pallet in a location near the pack station.

The application supports the following pallet building operations for packed shipping containers:

-   When a workstation is enabled for consolidation and the next move for a completed shipping container is the pack station's consolidation zone, the application directs the operator to move the completed shipping container to a designated pallet LPN.
    
    Location reservation criteria (such as by load or by stop) determines the location (in the consolidation zone) to which the shipping container is directed.
    
    Pallet building consolidation rules determine the pallet to which inventory can be consolidated.
    
    -   If a pallet with matching inventory exists, the operator can still override the deposit to another pallet with matching inventory.
    -   If the consolidation location does not contain a pallet or the pallet in the location is full, the operator can create a new pallet, and if required, define its handling unit type.
-   When a workstation is not enabled for consolidation, the operator deposits completed shipping containers to the processing destination zone. If the shipping container's next destination is a consolidation movement staging zone, another operator moves the container to the consolidation staging zone, and another operator consolidates the shipping container to an appropriate pallet LPN, as directed.

## Packing errors

The application displays errors during pack station processing to alert the operator when conflicts occur with the inventory or identifiers that the operator is attempting to process.

The following table describes the data entry errors that can take place, the process during which each error occurs, and the resulting effect on processing.

**Note**: Error messages, other than statuses, are only displayed if the packing general settings are configured to allow it.

  
| Error | Process | Result |
| --- | --- | --- |
| Invalid container ID | Operator scans an identifier for an invalid picking container. | The following actions occur:<br>-   • A message is displayed stating that the container ID is invalid.
<br>-   • The Identifier field is cleared so that the operator can scan the correct identifier. |
| Inventory is not required. | Operator scans an item that is not required for any of the shipping container associated with the picked inventory container. | The following actions occur:<br>-   • A new row is added to grid view for the item with a status of INVALID.
<br>-   • Updating the quantity to 0 allows the operator to remove the line item from the grid.
<br>-   • If the operator attempts to complete the container, an error is logged. The operator must move the inventory (from shipping containers that were not completed) back to the picking container and direct the picking container to a special handling location. |
| Inventory is not required for the currently selected shipping container. | Operator scans an item that is not required for the current in-process shipping container, but is required for one of the other displayed shipping containers associated with the picked inventory container. | The following actions occur:<br>-   • A message is displayed stating that the identified inventory is not for the current shipment.
<br>-   • The item attribute fields are cleared, preventing the operator from packing the item. |
| Quantity processed is greater than what is required. | Operator scans a quantity greater than the required quantity. | The following actions occur:<br>-   • The status of the displayed line item is changed to OVERAGE.
<br>-   • Updating the quantity to 0 allows the operator to remove the line item from the grid.
<br > If the operator attempts to complete the container, an error is logged. The operator must move the inventory (from shipping containers that were not completed) back to the picking container and direct the picking container to a special handling location. |
| Quantity processed is less than what is required. | Operator scans a quantity less than the required quantity. | When the operator completes the shipping container, a confirmation message is displayed asking if there is any more inventory left in the picking container.<br > If the operator answers No, then an error is logged. The operator must move the inventory (from shipping containers that were not completed) back to the picking container and direct the picking container to a special handling location. |
| Inventory replacement not allowed. | Operator attempts to process a similar item that is not identical to one required by the shipping container.<br > **Note**: Inventory replacement (swapping) is not allowed if the inventory attributes, LPN level, or quantity of the sub-LPN does not match. | The following actions occur:<br>-   • A message is displayed stating that the identified inventory is not for the current shipment.
<br>-   • The item attribute fields are cleared, preventing the operator from packing the item. |
| Duplicate number for the serial type. | Operator enters a serial number that has already been entered for the same serial number type. | The following actions occur:<br>-   • A message is displayed stating that the serial number is a duplicate for the serial number type.
<br>-   • The operator is prompted to enter a different serial number for the item. |

## Manifest at pack station

Manifesting parcels at a pack station occurs immediately after the packing operator completes a packed shipping container. When a shipping container is completed, depending on application configurations, the Manifesting page is displayed for the operator to manifest the parcel manually, or the application automatically manifests the parcel.

**Note**: Manifesting functionality is only available when Warehouse Management is integrated with a parcel application through Parcel Handler.

During manual manifesting at a pack station, after the packing operator completes packing the shipping containers, the Manifesting page is displayed with the shipping container ID populated in the **Identifier** field. The operator can perform manifesting operations such as rate shopping and, if allowed, carrier change. After a parcel is manifested, the Packing page is displayed for the operator to resume packing operations.

**Notes**:

-   To enable manual manifesting at a pack station, set the **Manifest at Pack Station** field to Yes. See [Add or modify a workstation](../configuration/equipment/hardware/workstations.md).
-   If the packing operator is not authorized to view the Manifesting page or if the selected container is a pallet carton type, then the Manifesting page is not displayed.

During automatic manifesting at pack station, after the packing operator completes packing the shipping container, the Manifesting page is not displayed; instead, the application automatically manifests the parcel and generates a tracking number.

**Notes**:

-   To enable automatic manifesting at a pack station, you must enable the Manifest Shipping Container outbound workflow and ensure it is configured to execute at the Pack Close Out exit point. The Manifest Shipping Container outbound workflow is associated with the Manifest Shipping Container master workflow (MNFST-SHP-CTN), which is configured with an instruction action to automatically manifest the completed package. See [Add or modify a background workflow](../configuration/work/warehouse-workflows/background-workflows.md).
-   If you enable the Manifest Shipping Container outbound workflow, then the **Manifest at Pack Station** field should be set to No for all workstations.
    

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
