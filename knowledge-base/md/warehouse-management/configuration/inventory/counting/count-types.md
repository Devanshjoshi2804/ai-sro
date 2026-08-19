---
title: "Count Types"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/count_types.htm"
source: "/content/count_types.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inventory"
  - "Counting"
  - "Count Types"
sections:
  - "How count near zero counts work"
  - "Add or modify a count type"
  - "Delete a count type"
  - "Count Types fields"
images: []
source_sha1: 86a45cb16dcf01f3f15e8df92b98ecc9e48c25dc
---
# Count Types

A count type is a means by which each type of inventory count can be configured with specific attributes that determine how the application processes the count. For example, a count type attribute determines whether a secondary count is generated if the first count does not match the application-expected quantity.

For a 3PL environment, you can define a client-specific configuration for each count type. The client-specific configuration can use different values for certain attributes. Counts that are performed for the client's items use the client-specific values for the count type that is being performed.

The application provides the following standard count types:

-   **Cancel Pick Count**: A count that is generated for a location by the cancel code that is applied when a pick from that location is canceled. Pickers determine when to cancel a pick and which cancel code to use if they arrive at a location and they cannot perform the pick. The cancel code selected determines whether the count is released automatically, immediately, or manually at a later time. Not all cancel codes generate a count.
-   **Audit Count**: A secondary count that can be used to verify that a physical count is accurate, or to recount a location when a count discrepancy occurs during a cycle, count near zero, or cancel pick count.
-   **Count Back**: A count verification task that requires an operator, if authorized for the count back operation, to capture the quantity of inventory that is left behind on the pallet or in the location in addition to the quantity of inventory being picked. If the picking operator is not authorized, another operator performs the count back. You can configure a count back to be required for a specific item, location, or UOM. By default, all users are required to perform the count back if the item, location, or pickable UOM requires it, but you can override the default for individual users.
    
    If an incorrect quantity is entered for a count back and recount, the resulting audit count displays the expected and confirmed pick quantities on the RF for the operator to confirm the quantities.
    
-   **Count Near Zero**: A count that is generated when inventory in a location falls below a specified threshold after a pick or inventory transfer is performed. The operator, if authorized for the count near zero operation, is prompted to perform the count immediately after the pick or inventory transfer. If the operator is not authorized, another operator performs the count near zero.
    
    Count near zero functionality can be enabled by item and by count zone. Therefore, a count near zero can be generated for a location, even if the item in the location is not enabled for it, as long as the location is in a count zone enabled for count near zero. Similarly, if an item is enabled and a count zone is not, a count can be generated for the item in that zone. If both the item and count zone are enabled for count near zero and have differing thresholds, the value defined for the item takes precedence.
    
-   **Cycle Count**: An inventory counting method in which counts of selected items are performed and reconciled with existing application inventory records. Cycle counts are performed for a portion of the total number of items on each day of a count period with the intent of counting all of the items by the end of the count period. Cycle counts for a particular item or location can be requested automatically, or manually. Cycle counts are generated automatically (using a scheduled job) or manually, and can be performed while the warehouse is operating. You can also configure client-specific and supplier-specific cycle counts. ABC code values can be overridden for clients if the ABC count is by item or by item and supplier. ABC codes values can be overridden for suppliers if the ABC count is by item and supplier.
-   **Detail Cycle Count**: A count type that is configured for detailed counting, indicating that the counter is prompted to enter an LPN and quantity for each LPN that is residing in the location being counted. If the count type is not configured for detail counting, the counter is prompted to enter the total quantity of inventory residing in the location (not by individual LPN).
-   **Manual Count**: A count that is initiated and performed by an operator at any location. Manual counts are not scheduled by the application. Operators typically request manual counts for items, locations, or location ranges when inventory issues arise and must be resolved quickly. If a manual count results in a discrepancy, and the manual count type is configured to be followed by an audit count, an authorized operator is directed to complete the audit count immediately following the manual count. If the operator is not authorized to perform an audit count, the count is placed in the work queue until an authorized operator acknowledges it.
-   **Physical Count**: The process of determining exact inventory quantities by performing a wall-to-wall count of an entire warehouse. During a physical inventory count, normal warehouse operations are halted. You can perform a physical inventory by scheduling and then generating a count for every storage location within your facility.
-   **Re-Count**: A secondary count that can be required when count discrepancies occur, for example, during a physical inventory count. It can also be required when a count discrepancy occurs and you want a second operator to recount the location, so that a subsequent audit count is only generated if the recount is also discrepant. For this configuration where an audit count is the next count type, the recount must not be set as a detail count.

## How count near zero counts work

A count near zero count is generated by the application when the inventory level of an item or count zone, enabled for count near zero, falls below the defined threshold during picking or an inventory transfer. A count near zero count is performed by authorized users.

When count near zero is enabled, cycle counts are performed in line with the pick or transfer operation (voice operators cannot perform inventory transfers). If the operator who performed the pick or transfer operation is authorized to perform a count near zero count, then the operator is immediately directed to perform the cycle count. When performing the count work for count near zero, all inventory in the location is counted, even if the location contains items that are not configured for count near zero.

You can also configure which UOMs need to be included in a count near zero for a pick zone. When a count near zero is triggered, the application prompts the operator to confirm a quantity in each UOM that is defined on the item footprint and is enabled for count near zero for the pick zone. If there are no common UOMs between the item footprint and pick zone, then the application prompts for all UOMs defined on the item footprint.

For example, assume the following information:

-   The footprint configuration for ITEM1 includes the Case and Each UOMs.
-   ITEM1 is configured for count near zero, and has a count near zero threshold of 2.
-   ITEM1 is stored in a pick zone that is configured to only require the Case UOM for a count near zero.
-   A location in the pick zone contains 12 cases of ITEM1.

If a picker arrives at the location and picks 11 cases, then count near zero is generated because the remaining quantity is lower than the threshold. The application’s prompt for count quantity includes only the Case UOM due to the pick zone configuration. If the pick zone is configured to require only the Pallet UOM for count near zero, then because the Pallet UOM is not defined on the item footprint, the application prompts for the Case and Each UOMs instead.

If the location has a quantity that is different from the expected quantity, such as there being 2 pallets remaining in the location instead of 1, then when the operator enters the quantity, the application generates another count of the next configured count type. Typically, the next count type is an audit count. Regardless of whether the count near zero quantity matches the application-expected quantity, the operator can continue picking after completing the count near zero.

Count near zero counts can be enabled for a count zone or for an item. See [Count Settings](count-settings.md).

## Add or modify a count type

1.  Select **Configuration > Inventory > Counting > Count Types**.
2.  Perform one of the following tasks:
    -   To add a count type, click **Add**.
    -   To modify a count type, in the grid, click the count type.
    -   To copy a count type, in the grid, select the check box next to the count type, and then click **Copy**.
3.  Enter information in the [Count Types fields](#Count_Types_fields).
4.  To configure a client-specific values for the count type:
    
    **Note**: The **Override Count Type Settings by Client** button is available only when, for count settings, the **Type of ABC Count** field is set to **By Item** or **By Item and Supplier**. See [Configure count settings](count-settings.md).
    
    1.  Click **Override Count Type Settings by Client**.
    2.  Perform one of the following tasks:
        -   To add a client-specific configuration, click **Add**, and then from the **Client** drop-down list, select a client.
        -   To modify a client-specific configuration, in the grid, click the client-specific count type.
        -   To copy a client-specific configuration, in the grid, select the check box next to the client, and then click **Copy**.
    3.  Enter information in the [Count Types fields](#Count_Types_fields).
    4.  Click **Apply**.
5.  Click **Save**.

## Delete a count type

1.  Select **Configuration > Inventory > Counting > Count Types**.
2.  In the grid, select the check box next to the count type to delete.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Count Types fields

 
| Field | Description |
| --- | --- |
| Count Type | Name of a type of inventory count. The attributes of a count type determine how the application processes the count. |
| Description | Description that further defines the count type. |
| Base Count Type | Base count type that determines how the count behaves. For example, if the base count type is Cycle Count, then the application processes counts of this type as cycle counts. A base count type is a count type that is distributed with the standard product.<br > When you add a new count type, you must associate it with a base count type. For example, if you want to create a new audit count type, you must select "Audit Count" as the base count type, so that the application processes counts of this type as audit counts.<br > It is also important to select the appropriate value in the **Operation Code** field for the count type. The operation defines how count work is added to the work queue, the priority of the work, and which users and equipment are authorized to perform it. For example, the Cycle Count operation is typically assigned to the cycle count types, so that cycle count work is added to the work queue. In the same way, the Count Audit operation is typically assigned to the audit count types. The operation code assigned to a new count type should match the operation code assigned to the count type selected as the base count type. |
| Operation | Work operation that the application uses when creating count work. The operation defines how count work is added to the work queue, the priority of the work, and which users and equipment are authorized to perform it.<br > **Note**: The operation defined for the count type does not apply to count by LPN counts, which may be enabled for the count type. To defined the operation for count by LPN counts, see [Configure count settings](count-settings.md).<br > For example, the Cycle Count operation is typically assigned to the cycle count types, so that cycle count work is added to the work queue. In the same way, the Count Audit operation is typically assigned to the audit count types. The operation code assigned to a new count type should match the operation code assigned to the count type selected in the **Base Count Type** field. |
| Next Count Type | Type of count that is generated if a secondary count (such as a recount or audit count) is required. A secondary count is required if a discrepancy occurs during counting, and the **End Location Count** field is set to "Generate New Count" or "Find match or Gen New Count". |
| End Location Count | Action that occurs when the count for a location is finished.<br>-   •
    
    **Check Threshold**: If the count quantity matches the previous count or the application count, no action occurs. If it does not match, the application evaluates the count threshold for the item and warehouse to determine if the adjustment is made or if a new count is generated using the count type selected for **Next Count Type**. The count threshold defined for the item overrides the count threshold defined for the warehouse. For example, location LOC3 contains 850 RUBBERBANDS and the item threshold is set to 1000. If a count is performed and there are actually only 800 RUBBERBANDS in LOC3, the application would not generate another count but would adjust the location count to 800 (because the discrepancy is less than the threshold value). However, if the count is performed and there are actually 1200 RUBBERBANDS in LOC3, the application would generate a count based on the next count type to verify (audit) the location before creating the adjustment (because the discrepancy is more than the threshold value).
    
    <br>
    
    **Note**: If the count is below the threshold but the application cannot complete the adjustment, the application does not display a notification of the failed adjustment, and a new count is not generated. An adjustment may fail, for example, if the application requires homogeneous adjustments and the inventory is not homogeneous.
    
    <br>
<br>-   • **Find a Match**: If the count quantity matches the previous count or the application count, no action occurs. If it does not match, then the location status is set to Inventory Error.
<br>-   •
    
    **Find match or Gen New Count**: If the count quantity matches the previous count or the application count, no action occurs. If it does not match, the application evaluates the count threshold for the item and warehouse to determine if the adjustment is made or if a new count is generated using the count type selected for **Next Count Type**. The count threshold defined for the item overrides the count threshold defined for the warehouse. If the count quantity is above the count threshold, then a new count is generated based on the **Next Count Type** value. If the count quantity is below the count threshold, then the adjustment is made, and a new count is not generated.
    
    <br>
    
    **Note**: If the count is below the threshold but the application cannot complete the adjustment, the application does not display a notification of the failed adjustment; however, a new count is generated based on the **Next Count Type**. An adjustment may fail, for example, if the application requires homogeneous adjustments and the inventory is not homogeneous.
    
    <br>
<br>-   • **Generate New Count**: A new count is generated.
<br>-   • **Log Discrepancies**: If the count quantity matches the previous count or the application count, no action occurs. If it does not match, the discrepancy is logged for future reporting but no additional action is performed. |
| Release Location Method | Method that determines when the location being counted is restored to the status it was in before the count was released. When a count for a location is released, the location is locked until the selected release location method occurs.<br>-   • **Lock Down**: The location is not released until the entire count is complete. Warehouses typically lock down a location when they use paper-based counting.
<br>-   • **Standard**: The location is released when the count for the location is complete. Warehouses typically use the Standard release when counting is performed using an RF device. |
| Adjustment Method | Specifies when to perform an adjustment.<br>-   • **Lock Down**: Adjustments, if any, are performed when the entire count is complete.
<br>-   • **Standard**: Adjustments, if any, are performed when the count for the location is complete. |
| Homogeneous Adjustment | If Yes, the application automatically adjusts inventory when there is a count discrepancy during a summary count in a homogeneous location. A homogeneous location is a location that contains either a single LPN of one distinct item, or multiple LPNs of inventory, with each LPN containing a distinct item. Homogeneous locations must also contain inventory that either is not tracked by lot, revision, or origin code, or if tracked, has the same lot, revision, or origin codes for all of the inventory contained on an LPN. Inventory within homogeneous locations must not be sub-LPN or detail LPN tracked. In order for automatic adjustments to occur in homogeneous locations, the following conditions must be met:<br>-   • The initial summary count must be configured to permit the same user who performed the summary count to perform the audit count.
<br>-   • The automatic adjustment must be less than the inventory adjustment cost and unit threshold defined for the item or warehouse. The thresholds defined for the item take precedence over the thresholds defined for the warehouse. The adjustment must be at or below both the cost and the unit threshold if both are defined.
<br > If No, the application does not automatically adjust inventory when there is a count discrepancy during a summary count in a homogeneous location. |
| Detail Count | If Yes, the counter must perform a detail count. A detail count requires the counter to enter each LPN and its quantity for a location. Select Yes if you want to ensure that each LPN in a location is counted.<br > If No, the counter is prompted to enter the total quantity of inventory residing in the location. Select No if you are only interested in the total quantity in a location; not each LPN quantity.<br > **Note**: For a configuration where the **Base Count Type** field is set to "Re-Count", if the **Next Count Type** field is set to "Audit Count", select No. If the **Detail Count** field is set to Yes, the application will not generate a detailed audit count after a detailed recount. |
| Prompt for Reentry | If Yes, then the following actions take place, depending on the type of count.<br>-   • For a Summary count, if the quantity entered does not match the expected quantity, the user is prompted to re-enter the quantity. If the re-entered quantity does not match the expected quantity, the next action configured for the count type takes place.
<br>-   • For a Detail count:
    -   • If the user enters a quantity for an existing LPN that is different from the expected quantity, the user is prompted to re-enter the quantity until two consecutively entered values match. If the result is different from the expected quantity, then an inventory adjustment is performed automatically or sent for approval.
    <br>-   • If the user enters a quantity for an LPN that does not exist in the location, the user is prompted to add the inventory to the system.
    <br>
<br > If No, then the following actions take place, depending on the type of count:<br>-   • For a Summary count, if the quantity entered does not match the expected quantity, the user is not prompted to re-enter the quantity. Instead, the next action configured for the count type takes place.
<br>-   • For a Detail count:
    -   • If the user enters a quantity for an existing LPN that is different from the expected quantity, then an inventory adjustment is performed automatically or sent for approval.
    <br>-   • If the user enters a quantity for an LPN that does not exist in the location, the user is prompted to add the inventory to the system.
    <br> |
| Warn on Unscanned LPNs | If Yes, then when an operator completes a detail count and there are unscanned (uncounted) LPNs in the count location, a warning message is displayed to confirm the removal of the unscanned LPNs from the location. For example, if the application shows that there are 5 LPNs in a location, but the operator only scans 4 LPNs during the detail count, then the application prompts the operator to confirm that the 5th LPN should be removed. If the operator confirms to remove the LPN, then the location inventory record is updated and the LPN is deleted. If the operator declines to remove the LPN, then the operator can scan the additional LPN that was missed before completing the count.<br > If No, then the application does not prompt the operator to confirm the removal of unscanned LPNs during a detail count. When the count is completed, any unscanned LPNs are removed from the application.<br > **Note**: This field is only available if the **Detail Count** field is set to Yes. |
| Empty Location | If Yes, the operator is directed to count empty locations. Select Yes if you want to verify that no unexpected inventory exists in locations that the application considers logically empty. This could happen, for example, if an operator moved inventory into a location without scanning the location,<br > If No, the operator is not directed to count empty locations. |
| Different User | If Yes, the user who originally counted a location is not allowed to perform the secondary (audit) count for that location if an audit count is generated, even if the user is authorized to perform audit counts. The audit count must be performed by another authorized user. Select Yes if you want to prevent an operator that is authorized to perform both initial counts and secondary counts from performing both counts at the same location.<br > If No, any authorized user may perform the audit count. |
| Prompt for Reason in RF | If Yes, then when an automatic inventory adjustment occurs, the RF operator performing the summary count that triggered the adjustment is prompted to enter a reason code for the adjustment. If a default reason code exists, then the default reason code is displayed, and the operator can either accept the default or select a new reason code.<br > If No, then the operator is not prompted to enter a reason code after an automatic inventory adjustment. |
| ABC Count | If Yes, the count type will be considered as an ABC count. Use this count type whenever an ABC count should be performed. See [Automated ABC counts](count-settings.md).<br > If No, the count type will be considered as a non-ABC count. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
