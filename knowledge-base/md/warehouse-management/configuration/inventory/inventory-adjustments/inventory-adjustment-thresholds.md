---
title: "Inventory Adjustment Thresholds"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/inventory_adjustment_thresholds.htm"
source: "/content/inventory_adjustment_thresholds.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inventory"
  - "Inventory Adjustments"
  - "Inventory Adjustment Thresholds"
sections:
  - "Inventory adjustment threshold processing"
  - "Configure inventory adjustment thresholds"
images: []
source_sha1: 3119bb4411c3c7d965521dc609958701a97e4d2d
---
# Inventory Adjustment Thresholds

An inventory adjustment threshold defines the limit at and above which an inventory adjustment requires an approval to be completed. A threshold value of 0 (zero) indicates that an approval is never required.

You can define the following types of thresholds for the current warehouse, as well as for users, roles, and (in a 3PL environment) clients and client groups.

-   **Cost threshold**: Defines the limit as a monetary value. The application determines the cost of an adjustment by multiplying the quantity of the adjustment by the unit cost for the item.
-   **Unit threshold**: Defines the limit by the number of units based on the stocking unit of measure (UOM) defined for the item being adjusted.

Thresholds take effect whenever a user performs an inventory adjustment, such as during an audit count or from a workstation. Thresholds are not enforced, however, when an inventory status change moves inventory out of four-wall inventory to a logical location, such as a Damage location.

If a user attempts to adjust inventory equal to or above a defined threshold, the adjustment is saved so that an authorized user (such as a supervisor) can approve or reject it.

## Inventory adjustment threshold processing

The application processes cost and unit adjustment thresholds according to the following rules:

-   If there are multiple adjustment thresholds defined, the application applies the threshold that occurs first in this order of precedence: user, role, client, client group, and warehouse.
-   If the user is assigned to multiple roles and there are no user thresholds defined, then approval is required only when the largest role threshold is met or exceeded.
-   If both a cost and unit threshold apply, then approval is required when either of the thresholds is met or exceeded.

If a user attempts to adjust (increase or decrease) inventory that is configured to be adjustable equal to or above a defined threshold, the adjustment is allowed but not completed, and the location is set to a Locked status. This is done to prevent any other changes at the location until the adjustment is approved or rejected. The adjustment is saved so that an authorized user (such as a supervisor) can approve or reject it using Inventory Adjustment Approval. During RF inventory adjustments due to count discrepancies, if a user attempts to adjust non-adjustable inventory by an amount equal to or above a defined adjustment threshold, the quantity in the location is adjusted, but the location is not locked and no approval is sent.

If Event Management is integrated with Warehouse Management, then an event (WMD-INVADJ-APPROVAL) can be sent to notify appropriate personnel that an inventory adjustment is pending approval.

## Configure inventory adjustment thresholds

1.  Select **Configuration > Inventory > Inventory Adjustments > Inventory Adjustment Thresholds**.
2.  To define thresholds for the current warehouse, enter information in the following fields:
    
     
    | Field | Description |
    | --- | --- |
    | Cost Threshold | Monetary value of an inventory adjustment (increase or decrease) at or above which an approval is required. A value of 0 (zero) indicates that approval is not required for an inventory adjustment. |
    | Unit Threshold | Number of units (in the stocking unit of measure) of an inventory adjustment (increase or decrease) at or above which an approval is required. |
    
3.  To define thresholds for specific users, roles, clients, or client groups:
    1.  Click **Users**, **Roles**, **Clients**, or **Client Groups**. The grid displays a list of existing entities.
    2.  In the **Cost Threshold** column, enter the monetary value of an adjustment at or above which an approval is required.
    3.  In the **Unit Threshold** column, enter the number of stocking units of an adjustment at or above which an approval is required.
    4.  To set a threshold values to zero, in the grid, select the rows that have a value, and then click **Clear Thresholds**.
    5.  Click **Save**.
4.  Click **Save**.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
