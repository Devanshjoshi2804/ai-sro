---
title: "Inventory Adjustments"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/inventory_adjustments_config.htm"
source: "/content/inventory_adjustments_config.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inventory"
  - "Inventory Adjustments"
sections:
  - "Inventory adjustments configuration"
  - "Automatic inventory adjustments"
images: []
source_sha1: 19dc6fbe3958f9268adbafaa8ccc75a001b567dd
---
# Inventory Adjustments

Inventory adjustments are performed to modify the quantity of inventory in a storage location. For example, if you found inventory that had not been identified, you can perform an inventory adjustment to add the inventory to the proper storage location.

In addition, you can use inventory adjustments to modify inventory quantities. For example, if a pallet is received and put away at 12 cases per pallet and later it is determined that the pallet contained only 10 cases, you can perform an inventory adjustment to modify the quantity that is actually stored in the storage location.

An inventory adjustment is made when there is a noted discrepancy in physical inventory. The effect of an inventory adjustment is to bring book values (logical counts) into agreement with physical counts.

The following manual inventory adjustments can be made:

-   Adding inventory to a storage location, such as when inventory is found that has not been identified.
-   Removing inventory from the storage location, such as when inventory is lost.
-   Modifying inventory quantities within a storage location, such as when inventory is damaged.

You can perform adjustments at an LPN, sub-LPN, or detail-LPN level.

When you adjust inventory, the application places the storage location in error. You can choose to keep the storage locations in error to prevent any inventory activity from taking place in the location. If you choose to keep the location in error, then after the adjustments are made and you want to use the location again, you must reset the location status. Inventory adjustment transactions are sent (played) to the host automatically, if configured to do so; otherwise, you must do so manually.

Some manual inventory adjustments require approval by an authorized user, such as a supervisor. When a user performs an inventory adjustment that is equal to or exceeds a cost or unit adjustment threshold defined for the user, user's role, warehouse or (in a 3PL environment) for a client or client group, the adjusted location is locked, and the adjustment is not processed until it has been approved.

You use Inventory Adjustment Approval to view inventory adjustments that require approval and either approve or reject each adjustment. For details on Adjustment approvals, see [Adjustments](../../inventory/adjustments.md).

## Inventory adjustments configuration

Inventory adjustments are performed to modify the quantity of inventory in a storage location when there is discrepancy between logical and physical counts. For example:

-   If a pallet is identified with 12 cases per pallet and later it is determined that it contained only 10 cases, an inventory adjustment can be performed to reflect the actual quantity.
-   If inventory is found that has not been identified, an inventory adjustment can be performed to add it to a storage location.

You can configure the following inventory adjustment attributes:

-   General settings that define how the application processes inventory adjustments, when adjustments are sent to the host, and how adjustment quantities are grouped in transactions sent to the host.
-   Adjustment reasons that are used to explain why an inventory adjustment was made.
-   Approval reasons that are used to explain why an inventory adjustment was approved or denied.
-   Thresholds that define the cost and unit thresholds at and above which an approval is required before the adjustment is processed.

When you adjust inventory, the application places the storage location you are adjusting in error. After the adjustments are made, you must reset the storage location. Inventory adjustment transactions are sent (played) to the host automatically, if configured to do so; otherwise, you must do this manually.

## Automatic inventory adjustments

You can configure the application to automatically adjust inventory when a quantity discrepancy arises during a summary count in homogeneous locations. A homogeneous location is a location that contains either a single LPN of one distinct item, or multiple LPNs of inventory, with each LPN containing a distinct item. For example, the location can contain one LPN of ITEM1, one LPN of ITEM2, and one LPN of ITEM3, but not one LPN of both ITEM1 and ITEM2. If the location contains two LPNs of ITEM1, then the location is not homogeneous.

For a location to be classified as homogeneous, it must contain inventory that is not lot, revision, or origin code tracked, or if it is tracked, then all the inventory in a single LPN must contain the same lot, revision, and origin code. Inventory within homogeneous locations is not tracked at the sub-LPN or detail level.

Before the application can automatically adjust inventory in homogeneous locations, the following conditions must be met:

-   The initial summary count (such as a cycle count) must be configured to permit automatic adjustments on a quantity discrepancy for homogeneous locations.
-   The secondary detail count (such as an audit count) must be configured to follow the initial summary count and to permit the same RF operator who performed the summary count to perform the detail count.
-   The automatic adjustment must be less than the cost and unit count thresholds defined for the item or warehouse.

**Note**: The count thresholds defined for the item take precedence over the thresholds defined for the warehouse. The adjustment must be at or below both the cost and the unit count threshold if both are defined. If the cost and unit count threshold is not defined for an item, then the application considers the warehouse cost and unit count threshold when adjusting inventory.

-   The RF operator must be authorized to perform the secondary detail count work (such as an audit count).

If these conditions are met, then when a quantity discrepancy arises during a summary count, the application automatically adjusts the inventory, rather than requiring the RF operator to enter the LPN number and other inventory detail information for a detail count on the item. In addition, if the summary count is configured to prompt operators for a reason, then the operator must enter a reason for the automatic adjustment.

**Note**: If an item has the **Supports Inventory Adjustment** field set to No, and the counted quantity is less than expected but no secondary detail count is generated, then the inventory is sent to the lost location. See [Lost location for count discrepancies](counting/count-settings.md).

If the quantity discrepancy is less than the count thresholds defined for an item or the warehouse, but higher than the adjustment approval limit, then an approval request is created. The location is locked until the adjustment is approved.

If the quantity discrepancy is higher than the thresholds defined for an item or the warehouse, then a secondary detail count work (such as an audit count) is generated on the location.

**Note**: If there is a combination in a location where one or more items exceed adjustment approval limit and at least one item requires a secondary detail count, then the approval requests are not sent. This is to ensure that the detail count is completed without sending any requests for adjustments approval in the location. Similarly, if there are one or more items that are within the adjustment approval limit and at least one item exceeds the adjustment approval limit, then an approval request is sent, and the location is locked until the adjustment is approved. The discrepancy within the approval limit is automatically adjusted after the adjustment that exceeds the limit is approved.

For example, consider a location that contains one LPN each of the following items that have a quantity discrepancy:

-   ITEM1: The discrepancy is within the item or warehouse count threshold and the adjustment approval limit.
-   ITEM2: The discrepancy is within the item or warehouse count threshold, but higher than the adjustment approval limit.
-   ITEM3: The discrepancy exceeds the item or warehouse count threshold.

Since, there is at least one item that exceeds the item or warehouse count threshold, the application generates a secondary detail count for the location.

Instead, if the discrepancy for ITEM3 is within the item or warehouse count threshold and the adjustment approval limit, then ITEM2 is sent for adjustment approval, and the location is locked. ITEM 1 and ITEM3 are automatically adjusted after the adjustment for ITEM2 is approved.

When an automatic adjustment is complete, the application resets the location so that it is no longer in error. A message is displayed to notify the operator of the adjustment. However, voice operators do not receive notification of successful automatic adjustments. The adjustment can then be either manually or automatically played to the host (individually or in groups), depending on how the application is configured.

If any of the required conditions are not met when a summary count quantity discrepancy arises, then the application follows standard logic, creating a detail count (if configured to do so) to determine the specific inventory that needs to be adjusted.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
