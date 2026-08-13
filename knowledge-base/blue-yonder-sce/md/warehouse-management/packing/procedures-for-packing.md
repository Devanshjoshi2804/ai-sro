---
title: "Procedures for packing"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/procedures_for_packing.htm"
source: "/content/procedures_for_packing.htm"
toc_path:
  - "Warehouse Management"
  - "Packing"
  - "Procedures for packing"
sections:
  - "Pack one shipping container at a time"
  - "Pack multiple containers at the same time"
  - "Pack with shipping cartonization enabled"
  - "View keyboard shortcuts for packing"
  - "Packing fields"
images:
  - "/content/resources/images/keyboardhelp_29x20.png"
  - "/content/resources/images/image524298.png"
  - "/content/resources/images/keyboardhelp_29x20.png"
  - "/content/resources/images/image524298.png"
  - "/content/resources/images/keyboardhelp_29x20.png"
  - "/content/resources/images/image524298.png"
  - "/content/resources/images/keyboardhelp_29x20.png"
source_sha1: b71c52d1c33de16b69966e89c4a60a1ba59ab577
---
# Procedures for packing

You can perform the following packing procedures.

## Pack one shipping container at a time

The following procedure presents the steps required to pack one shipping container at a time from a picking container that contains inventory for one or more shipments. This process requires the operator to scan the identifier (LPN, sub-LPN, or location, depending on what is required by the configuration), and then scan the items to pack. You use this procedure when the pack station configuration option to pack multiple shipments simultaneously is set to No.

**Note**: Some actions on the Packing page may be configured with keyboard shortcuts. To view the configured shortcuts, in the page title bar, click ![Keyboard Shortcuts](../../../images/resources/images/keyboardhelp_29x20.png).

1.  Select **Packing > ** **Packing**. If this is your first login, the Select Workstation window is displayed; otherwise, a field is displayed for you to scan an identifier.
2.  If you are required to select a workstation, in the grid, click the workstation that you are using, and then click **Select**.
3.  Perform one of the following tasks:
    -   Scan the identifier that contains the picked inventory. The processing page is displayed, listing the shipping containers that should be packed for the identifier that you scanned. The progress bar indicates the percentage complete and the number of items required for the container.
    -   In the grid, select the check box next to the location, and then click **Start Packing**.
        
        **Note**: If labor tracking is enabled, and there is no inventory available to pack, click **Waiting**, so that the time spent waiting is not charged to your performance.
        

1.  Select the shipping container to pack. The inventory required for the shipping container is displayed.

1.  To change the carton type:
    1.  Select a shipping container.
    2.  From the **Type** drop-down list, select a carton type. A confirmation message is displayed.
        
        **Note**: If you want to use a carton for which you can define the dimensions at the pack station, select **Generic Carton**. To use a physical pallet instead of a carton, select a pallet carton type.
        
    3.  Click **Yes**.
    4.  To enter dimensions for a generic carton, in the **Container Length**, **Container Width**, and **Container Height** fields, enter the values, and then click **Apply**.
        
        **Note**: For a generic carton, you can enter dimensions any time prior to the shipping container being completed. The application does not let you complete a shipping container that uses a generic carton until its dimensions are defined.
        
2.  To change the dimensions of a generic or pallet type carton, click **Edit Dimensions**, enter the values, and then click **Apply**.
    
    **Note**: For a pallet carton type, you can also enter the number of boxes on the pallet.
    

1.  Process the items by performing one of the following tasks:
    -   Scan the item to pack.
    -   Scan the required fields.
        
        **Note**: The required fields must be populated to uniquely identify the inventory. When the item is scanned, processing fields that are configured for auto-fill are populated automatically. Serial number type fields are displayed for serial number validation.
        
    -   In the grid, select one or more items to pack, and then click **Process**.
        
        **Note**: If the application is configured to automatically pack sublines with order lines, then scanning or selecting an item or sub-line automatically selects the related item and sub-lines.
        
        The shipping container is updated with the selected quantities, and the status for each item is changed to PACKED. While a shipping container is in progress, no other shipping containers can be packed.
        

1.  To capture serial numbers for a serialized item, perform one of the following tasks:
    -   For an item quantity of 1, enter the serial number in each serial number type field for the item.
        
        **Note**: Depending on configuration, you may not be allowed to capture multiple (or a range) of serial numbers for an item quantity greater than 1. Instead, each item must be scanned and captured, as it is done for a quantity of 1.
        
    -   For an item quantity greater than 1, enter the serial number in each serial number type field for the entire quantity one by one.
    -   For an item quantity greater than 1, enter a range of consecutive serial numbers for each serial number type:
        1.  Click **Enter a range**.
        2.  In the **Start** field, enter the first serial number in the range.
        3.  In the **End** field, enter the last serial number in the range.
        4.  Click **OK**.

1.  To change the quantity of a displayed item:
    1.  In the grid, select the item, and then click **Update Quantity**.
    2.  In the **Update Quantity** field, enter the quantity, and then click **OK**. The status of the item changes to either SHORT or OVERAGE depending on whether the amount is less than or greater than the order line quantity. An overage results in another line item added to the grid.
        
        **Note**: When you update a quantity for a serialized item, you must enter the serial number for item that is added or removed.
        
    3.  To undo an overage, in the grid, select the item with the OVERAGE status, click **Update Quantity**, enter a quantity of zero, and then click **OK**. The line item is removed from the grid.
2.  To indicate that a quantity is damaged:
    1.  In the grid, select the item, and then click **Mark Damaged**.
    2.  In the **Damaged Quantity** field, enter the quantity that is damaged, and then click **OK**. If a partial quantity is marked damaged, a line is added to the grid to identify the damaged quantity. The damaged quantity has a status of DAMAGED.
    3.  To undo a damaged quantity, select the item with the DAMAGED status, click **Update Quantity**, enter a quantity of zero, and then click **OK**. The line item is removed from the grid.
        
        **Note**: When you mark a serialized item as damaged or change it from damaged, you must enter the serial number for item.
        

1.  To associate a media file with an item:
    1.  In the grid, select the item, and then click **Add Media**. The Add Media page is displayed.
    2.  Enter information in the [Media fields](../../get-started/media.md).
    3.  Click **Save**.
2.  To view or delete a media file associated with an item:
    1.  In the grid, select the item, and then click **View Media**. The Media page is displayed.
    2.  If the media file is an image, to enlarge the view, click the thumbnail.
    3.  If the media file is a digital document (such as TXT, DOC, or PDF), to download and view the file, click the thumbnail.
        
        **Note**: You must have the associated application installed to open DOC and PDF files. See [Media](../../get-started/media.md).
        
    4.  To delete a media file:
        1.  Select the check box next to the media thumbnail.
        2.  From the Actions drop-down list, select **Delete**. A confirmation message is displayed.
        3.  Click **OK**.
    5.  Click ![Close](../../../images/resources/images/image524298.png) .

1.  To skip a partially processed shipping container:
    1.  Select a different shipping container. A skip shipment confirmation message is displayed.
    2.  To skip the container, click **Yes**. The grid displays the items for the selected container. The skipped container remains available for selection.
    3.  Process the items for the selected container.

1.  To complete a shipping container that is either physically full or contains all the required inventory, select the shipping container, and then click **Complete**.
    
    **Note**: If auto-close is enabled and the container contains all the required inventory, then you do not have to click **Complete**. The application automatically completes the shipping container when 100% of the expected inventory is packed. If configured to do so, the application automatically captures the weight of the shipping container, provided by an integrated scale.
    
    -   If other shipping containers still require inventory from the picking container, the closed container remains displayed but is no longer available for selection. If there are no other shipping containers that require inventory, the initiation page is displayed.
    -   If the shipping container requires additional items, a message is displayed asking if there is inventory left in the picking container. To create a new shipping container for the rest of the inventory that was required for the original shipping container, click **Yes**. The new shipping container is displayed with same position number as the original container.
    -   If weight capture is required but not automatic, and there is an integrated scale, click **Capture Weight**. If there is no integrated scale, then in the **Actual Weight** field, enter the weight of the packed shipping container. You can obtain the weight from the **Estimated Weight** field or from a standalone scale.
    -   If consolidation is enabled, confirm the pallet deposit location or enter a new pallet LPN, and then click **Consolidate Shipping Container**.
    -   If exception inventory was packed or a container weight issue occurred, then the Log Error window is displayed. Perform the following tasks:
        1.  In the **Reason** and **Location** fields, enter the values.
        2.  If the initial identifier was a location, then in the **Picking Container** field, enter the identifier for the container to which the picks have been transferred.
        3.  Click **Log Error**. The picking container is directed to the special handling location.
            
            **Note**: Exception inventory is inventory that is unexpected, damaged, or over or short the required quantity. A container that has a weight discrepancy is also considered an exception.
            

1.  If the application is configured to allow manual manifesting at the pack station, then the Manifesting page is displayed for you to proceed with manifesting operations. See [Manifest at pack station](packing-concepts.md).

## Pack multiple containers at the same time

The following procedure presents the steps required to open multiple shipping containers at the pack station and then pack them simultaneously. When the operator scans an item from the picking container, the application directs the operator to deposit the item to the correct shipping container. The operator does not have to skip shipments to pack into multiple shipping containers. This operation is only available if the pack station configuration option to pack multiple shipments simultaneously is set to Yes.

**Note**: Some actions on the Packing page may be configured with keyboard shortcuts. To view the configured shortcuts, in the page title bar, click ![Keyboard Shortcuts](../../../images/resources/images/keyboardhelp_29x20.png).

1.  Select **Packing > ** **Packing**. If this is your first login, the Select Workstation window is displayed; otherwise, a field is displayed for you to scan an identifier.
2.  If you are required to select a workstation, in the grid, click the workstation that you are using, and then click **Select**.
3.  Perform one of the following tasks:
    -   Scan the identifier that contains the picked inventory. The processing page is displayed, listing the shipping containers that should be packed for the identifier that you scanned. The progress bar indicates the percentage complete and the number of items required for the container.
    -   In the grid, select the check box next to the location, and then click **Start Packing**.
        
        **Note**: If labor tracking is enabled, and there is no inventory available to pack, click **Waiting**, so that the time spent waiting is not charged to your performance.
        

1.  To change the carton type:
    1.  Select a shipping container.
    2.  From the **Type** drop-down list, select a carton type. A confirmation message is displayed.
        
        **Note**: If you want to use a carton for which you can define the dimensions at the pack station, select **Generic Carton**. To use a physical pallet instead of a carton, select a pallet carton type.
        
    3.  Click **Yes**.
    4.  To enter dimensions for a generic carton, in the **Container Length**, **Container Width**, and **Container Height** fields, enter the values, and then click **Apply**.
        
        **Note**: For a generic carton, you can enter dimensions any time prior to the shipping container being completed. The application does not let you complete a shipping container that uses a generic carton until its dimensions are defined.
        
2.  To change the dimensions of a generic or pallet type carton, click **Edit Dimensions**, enter the values, and then click **Apply**.
    
    **Note**: For a pallet carton type, you can also enter the number of boxes on the pallet.
    

1.  Process the items by performing one of the following tasks:
    -   Scan the item to pack and place it into the selected shipping container. The application automatically selects the correct shipping container based on the item that was scanned.
    -   Select the shipping container to pack, and then in the grid, select the items to pack, and then click **Process**.
        
        **Note**: If the application is configured to automatically pack sub-lines with order lines, then scanning or selecting an item or sub-line automatically selects the related item and sub-lines.
        

The status of the items is changed to PACKED. A progress bar under the shipping container displays the packing status for that container.

1.  To capture serial numbers for a serialized item, perform one of the following tasks:
    -   For an item quantity of 1, enter the serial number in each serial number type field for the item.
        
        **Note**: Depending on configuration, you may not be allowed to capture multiple (or a range) of serial numbers for an item quantity greater than 1. Instead, each item must be scanned and captured, as it is done for a quantity of 1.
        
    -   For an item quantity greater than 1, enter the serial number in each serial number type field for the entire quantity one by one.
    -   For an item quantity greater than 1, enter a range of consecutive serial numbers for each serial number type:
        1.  Click **Enter a range**.
        2.  In the **Start** field, enter the first serial number in the range.
        3.  In the **End** field, enter the last serial number in the range.
        4.  Click **OK**.

1.  To change the quantity of a displayed item:
    1.  In the grid, select the item, and then click **Update Quantity**.
    2.  In the **Update Quantity** field, enter the quantity, and then click **OK**. The status of the item changes to either SHORT or OVERAGE depending on whether the amount is less than or greater than the order line quantity. An overage results in another line item added to the grid.
        
        **Note**: When you update a quantity for a serialized item, you must enter the serial number for item that is added or removed.
        
    3.  To undo an overage, in the grid, select the item with the OVERAGE status, click **Update Quantity**, enter a quantity of zero, and then click **OK**. The line item is removed from the grid.
2.  To indicate that a quantity is damaged:
    1.  In the grid, select the item, and then click **Mark Damaged**.
    2.  In the **Damaged Quantity** field, enter the quantity that is damaged, and then click **OK**. If a partial quantity is marked damaged, a line is added to the grid to identify the damaged quantity. The damaged quantity has a status of DAMAGED.
    3.  To undo a damaged quantity, select the item with the DAMAGED status, click **Update Quantity**, enter a quantity of zero, and then click **OK**. The line item is removed from the grid.
        
        **Note**: When you mark a serialized item as damaged or change it from damaged, you must enter the serial number for item.
        

1.  To associate a media file with an item:
    1.  In the grid, select the item, and then click **Add Media**. The Add Media page is displayed.
    2.  Enter information in the [Media fields](../../get-started/media.md).
    3.  Click **Save**.
2.  To view or delete a media file associated with an item:
    1.  In the grid, select the item, and then click **View Media**. The Media page is displayed.
    2.  If the media file is an image, to enlarge the view, click the thumbnail.
    3.  If the media file is a digital document (such as TXT, DOC, or PDF), to download and view the file, click the thumbnail.
        
        **Note**: You must have the associated application installed to open DOC and PDF files. See [Media](../../get-started/media.md).
        
    4.  To delete a media file:
        1.  Select the check box next to the media thumbnail.
        2.  From the Actions drop-down list, select **Delete**. A confirmation message is displayed.
        3.  Click **OK**.
    5.  Click ![Close](../../../images/resources/images/image524298.png) .

1.  To complete a shipping container that is either physically full or contains all the required inventory, select the shipping container, and then click **Complete**.
    
    **Note**: If auto-close is enabled and the container contains all the required inventory, then you do not have to click **Complete**. The application automatically completes the shipping container when 100% of the expected inventory is packed. If configured to do so, the application automatically captures the weight of the shipping container, provided by an integrated scale.
    
    -   If other shipping containers still require inventory from the picking container, the closed container remains displayed but is no longer available for selection. If there are no other shipping containers that require inventory, the initiation page is displayed.
    -   If the shipping container requires additional items, a message is displayed asking if there is inventory left in the picking container. To create a new shipping container for the rest of the inventory that was required for the original shipping container, click **Yes**. The new shipping container is displayed with same position number as the original container.
    -   If weight capture is required but not automatic, and there is an integrated scale, click **Capture Weight**. If there is no integrated scale, then in the **Actual Weight** field, enter the weight of the packed shipping container. You can obtain the weight from the **Estimated Weight** field or from a standalone scale.
    -   If consolidation is enabled, confirm the pallet deposit location or enter a new pallet LPN, and then click **Consolidate Shipping Container**.
    -   If exception inventory was packed or a container weight issue occurred, then the Log Error window is displayed. Perform the following tasks:
        1.  In the **Reason** and **Location** fields, enter the values.
        2.  If the initial identifier was a location, then in the **Picking Container** field, enter the identifier for the container to which the picks have been transferred.
        3.  Click **Log Error**. The picking container is directed to the special handling location.
            
            **Note**: Exception inventory is inventory that is unexpected, damaged, or over or short the required quantity. A container that has a weight discrepancy is also considered an exception.
            

1.  If the application is configured to allow manual manifesting at the pack station, then the Manifesting page is displayed for you to proceed with manifesting operations. See [Manifest at pack station](packing-concepts.md).

## Pack with shipping cartonization enabled

The following procedure presents the steps required to pack a shipping container with inventory from multiple picking containers. When shipping cartonization is enabled, picks destined for a single shipping container may be directed to multiple picking containers. Also, when shipping cartonization is enabled, the application selects the optimal carton type to use, and directs the process of splitting the shipping container during packing, if needed.

**Note**: Some actions on the Packing page may be configured with keyboard shortcuts. To view the configured shortcuts, in the page title bar, click ![Keyboard Shortcuts](../../../images/resources/images/keyboardhelp_29x20.png).

1.  Select **Packing > ** **Packing**. If this is your first login, the Select Workstation window is displayed; otherwise, a field is displayed for you to scan an identifier.
2.  If you are required to select a workstation, in the grid, click the workstation that you are using, and then click **Select**.
3.  Perform one of the following tasks:
    -   Scan the identifier that contains the picked inventory. The processing page is displayed, listing the shipping containers that should be packed for the identifier that you scanned. The progress bar indicates the percentage complete and the number of items required for the container.
    -   In the grid, select the check box next to the location, and then click **Start Packing**.
        
        **Note**: If labor tracking is enabled, and there is no inventory available to pack, click **Waiting**, so that the time spent waiting is not charged to your performance.
        

1.  To change the carton type:
    1.  Select a shipping container.
    2.  From the **Type** drop-down list, select a carton type. A confirmation message is displayed.
        
        **Note**: If you want to use a carton for which you can define the dimensions at the pack station, select **Generic Carton**. To use a physical pallet instead of a carton, select a pallet carton type.
        
    3.  Click **Yes**.
    4.  To enter dimensions for a generic carton, in the **Container Length**, **Container Width**, and **Container Height** fields, enter the values, and then click **Apply**.
        
        **Note**: For a generic carton, you can enter dimensions any time prior to the shipping container being completed. The application does not let you complete a shipping container that uses a generic carton until its dimensions are defined.
        
2.  To change the dimensions of a generic or pallet type carton, click **Edit Dimensions**, enter the values, and then click **Apply**.
    
    **Note**: For a pallet carton type, you can also enter the number of boxes on the pallet.
    

1.  Select one of the displayed shipping containers. The picking container inventory that is required for the shipping container is displayed in the grid.
    
    **Note**: The message "Inventory Remaining" indicates that inventory for the shipping container is needed not only from the current picking container, but from another picking container. Therefore, when you complete packing displayed inventory, the shipping container remains open (in-process) until the rest of its required inventory is packed.
    
2.  Process the items by performing one of the following tasks:
    -   Scan the items to pack, and place them in the selected shipping container.
    -   In the grid, select one or more items to pack, and then click **Process**.
        
        **Note**: If the application is configured to automatically pack sub-lines with order lines, then scanning or selecting an item or sub-line automatically selects the related item and sub-lines.
        

The shipping container is updated with the packed quantities, and the status of each item is changed to PACKED.

1.  To capture serial numbers for a serialized item, perform one of the following tasks:
    -   For an item quantity of 1, enter the serial number in each serial number type field for the item.
        
        **Note**: Depending on configuration, you may not be allowed to capture multiple (or a range) of serial numbers for an item quantity greater than 1. Instead, each item must be scanned and captured, as it is done for a quantity of 1.
        
    -   For an item quantity greater than 1, enter the serial number in each serial number type field for the entire quantity one by one.
    -   For an item quantity greater than 1, enter a range of consecutive serial numbers for each serial number type:
        1.  Click **Enter a range**.
        2.  In the **Start** field, enter the first serial number in the range.
        3.  In the **End** field, enter the last serial number in the range.
        4.  Click **OK**.

1.  To change the quantity of a displayed item:
    1.  In the grid, select the item, and then click **Update Quantity**.
    2.  In the **Update Quantity** field, enter the quantity, and then click **OK**. The status of the item changes to either SHORT or OVERAGE depending on whether the amount is less than or greater than the order line quantity. An overage results in another line item added to the grid.
        
        **Note**: When you update a quantity for a serialized item, you must enter the serial number for item that is added or removed.
        
    3.  To undo an overage, in the grid, select the item with the OVERAGE status, click **Update Quantity**, enter a quantity of zero, and then click **OK**. The line item is removed from the grid.
2.  To indicate that a quantity is damaged:
    1.  In the grid, select the item, and then click **Mark Damaged**.
    2.  In the **Damaged Quantity** field, enter the quantity that is damaged, and then click **OK**. If a partial quantity is marked damaged, a line is added to the grid to identify the damaged quantity. The damaged quantity has a status of DAMAGED.
    3.  To undo a damaged quantity, select the item with the DAMAGED status, click **Update Quantity**, enter a quantity of zero, and then click **OK**. The line item is removed from the grid.
        
        **Note**: When you mark a serialized item as damaged or change it from damaged, you must enter the serial number for item.
        

1.  To associate a media file with an item:
    1.  In the grid, select the item, and then click **Add Media**. The Add Media page is displayed.
    2.  Enter information in the [Media fields](../../get-started/media.md).
    3.  Click **Save**.
2.  To view or delete a media file associated with an item:
    1.  In the grid, select the item, and then click **View Media**. The Media page is displayed.
    2.  If the media file is an image, to enlarge the view, click the thumbnail.
    3.  If the media file is a digital document (such as TXT, DOC, or PDF), to download and view the file, click the thumbnail.
        
        **Note**: You must have the associated application installed to open DOC and PDF files. See [Media](../../get-started/media.md).
        
    4.  To delete a media file:
        1.  Select the check box next to the media thumbnail.
        2.  From the Actions drop-down list, select **Delete**. A confirmation message is displayed.
        3.  Click **OK**.
    5.  Click ![Close](../../../images/resources/images/image524298.png) .

1.  To skip a partially processed shipping container:
    
    **Note**: You cannot skip a shipping container that is 100% packed. Complete the shipping container first, and then select the next shipping container.
    
    1.  Select a different shipping container. A skip shipment confirmation message is displayed.
    2.  To skip the container, click **Yes**. The grid displays the items for the selected container. The skipped container remains available for selection.
    3.  Process the items.
2.  Select the next shipping container and process the items.
3.  If a selected shipping container is packed to 100%, click **Complete**. The application moves the container to the pack staging location.
    
    **Note**: If auto-close is enabled and the container contains all the required inventory, then you do not have to click **Complete**. The application automatically completes the shipping container when 100% of the expected inventory is packed.
    
4.  When the last item from the picking container has been packed, click **Complete**. The initiation page is displayed. If any in-process (partially packed) shipping containers require inventory from a different picking container, they are displayed on the initiation page with the message "Picking container remaining".
5.  To pack in-process shipping containers from another picking container:
    1.  On the initiation page, scan an identifier that contains picked inventory for any of the remaining open shipping containers. The processing page is displayed.
    2.  Select a shipping container. The picked inventory required for the shipping container is displayed in the grid.
    3.  Process the items to the selected shipping container.
    4.  Continue processing items to shipping containers, completing the shipping containers that are 100% packed, until the last item from the picking container has been packed.
    5.  Repeat this step until there are no more in-process shipping containers.
6.  To complete an in-process shipping container from the initiation page, on the initiation page, select an open shipping container, and then click **Complete**. The container is completed, and a new container is displayed in the same position to which the remaining inventory required for the original container can be packed.
    
    **Note**: If the packing general settings option that forces all items into a single shipping container is set to Yes, then the operator is not allowed to split a quantity to another container.
    
7.  If weight capture is required but not performed automatically when container is completed, perform one of the following tasks:
    -   If there is an integrated scale, click **Capture Weight**.
    -   If there is not an integrated scale, then in the **Actual Weight** field, enter the weight of the packed container. The weight may be obtained from the value in the **Estimated Weight** field or from a standalone scale.
8.  If the application is configured to allow manual manifesting at the pack station, then the Manifesting page is displayed for you to proceed with manifesting operations. See [Manifest at pack station](packing-concepts.md).

## View keyboard shortcuts for packing

A keyboard shortcut is a special key or combination of keys that executes a specific action on the Packing page.

1.  Select **Packing > Packing**. If this is your first login, the Select Workstation window is displayed; otherwise, a field is displayed for you to scan an identifier.
2.  If you are required to select a workstation, in the grid, click the workstation that you are using, and then click **Select**.
3.  If shortcuts are configured for the page, in the page title bar, click ![Keyboard Shortcuts](../../../images/resources/images/keyboardhelp_29x20.png). The Keyboard Shortcut window is displayed listing each shortcut and corresponding action that is configured for packing operations.

## Packing fields

 
| Field | Description |
| --- | --- |
| Item | Identifier for the item being processed at the pack station. |
| Item Client | Name of the client who stores this item in the facility. This field is only displayed in a 3PL environment. |
| Lot | Identifier for the lot associated with the selected inventory. A lot is a batch (quantity) of an item uniquely identified by a lot during the manufacturing process for the purpose of tracking that batch of inventory. Lot tracking is commonly associated with pharmaceuticals, fabrics, paints, dyes, food, and items that have a limited shelf life. |
| Serial Number | Unique identifier that is used to identify a piece of inventory in the warehouse. The identifier may contain numbers, letters, and check digits as required by the serial number type, and may be captured for an LPN, sub-LPN or detail LPN of inventory. The point at which the serial number is captured is determined by the serialization type assigned to the item. |
| Shipping Container | Unique identifier for the specific shipping container to which inventory is packed. The identifier is typically supplied by the application automatically when the shipping container is created. |
| Estimated Weight | Estimated weight of the inventory that has been packed into the shipping container. The estimated weight is based on the item footprint UOMs for the inventory in the shipping container, and includes the weight of the carton type itself. This field is display only; the operator is not allowed to overwrite the displayed value. |
| Actual Weight | Actual weight of a shipping container and its contents. If a weight scale is connected to the workstation, the operator can capture weight manually by clicking **Capture Weight**. If a weight scale is not connected to the workstation or if a scale error occurs, the operator can enter a weight into this field.<br > If the application is configured to capture weight automatically, the weight is automatically captured when the shipping container is closed, and it is not possible for the operator to enter the weight.<br > If the application is not configured to capture weight automatically, the operator can manually capture the weight; but if that is not done, the estimated weight is copied into the **Actual Weight** field.<br > To change a measurement unit, click the unit next to the field, and select a different unit. |
| Type | Type of carton to use as the shipping container. Only the cartons enabled for use as shipping and pack station cartons are available for selection, as well as the generic carton. The carton configuration specifies the dimensions and weight capacity of the carton, its repack classes, and how it can be used.<br > If the carton is a Pallet Type, it represents a physical pallet instead of a carton (box). Select a pallet type of carton if you want to pack inventory directly to a pallet instead of to another carton or box. This is useful when picked inventory is already boxed in a carton suitable for shipping.<br > If the carton is a generic carton type, you can define the dimensions of the carton to represent the physical carton that you are packing. This is useful if the picked inventory is already boxed in a carton suitable for shipping, or you need to use a non-standard carton that has not been defined in the application. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
