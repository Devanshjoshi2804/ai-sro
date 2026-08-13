---
title: "Splitting replenishment residuals"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/splitting_replenishment_residuals.htm"
source: "/content/splitting_replenishment_residuals.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inventory"
  - "Replenishments"
  - "Splitting replenishment residuals"
sections:
  - "Setup"
images: []
source_sha1: 603851e983a1254a6a2131186233f0bd21baae70
---
# Splitting replenishment residuals

The application supports the ability to split the residual inventory from a replenishment and direct it elsewhere. The split residual inventory can be used to fulfill cross docks (if allowed), or the application runs putaway to find a location. Replenishments processed without this functionality cannot be split, and the entire quantity of the replenishment pick must be able to fit in the destination location for the application to release the replenishment work.

For example, assume the following circumstances:

-   Location1 has a capacity of 50 eaches
-   There are 10 eaches currently in Location1 (available capacity for 40 eaches)
-   An order is downloaded that requires 20 eaches from Location1
-   Location1 has an replenishment percentage of 200%

When splitting replenishment residuals is enabled, the following actions take place:

1.  The application allocates and releases a pick for 100 eaches, which is 200% of the location's capacity of 50 eaches. The pick work is released regardless of whether the entire quantity can fit in the replenishment location; however, if the replenishment amount (10 eaches) would not fit into the location, then the work remains locked.
2.  The operator completes the replenishment pick, and is then directed to the replenishment destination location. At Location1, the application prompts the operator to deposit 40 eaches to fill the location to capacity (10 + 40 = 50).
3.  The operator confirms the quantity and deposits 40 eaches into Location1, leaving a residual quantity of 60 eaches on the operator's device.
    
    **Note**: If the **Overfill Location** field is set to Yes in the replenishment settings configuration, then when prompted with the deposit quantity that fills the replenishment location, the operator can override the quantity with a quantity that exceeds the location capacity.
    
4.  The application processes the residual inventory:
    -   If cross docking residual replenishment is enabled, then the application can use the 60 eaches to fulfill a cross dock opportunity. If the residuals can be cross docked, the application directs the operator to deposit the inventory in the cross dock staging location.
    -   If cross dock opportunities do not exist, or if this functionality is disabled, then the application runs putaway for the 60 eaches. If allowed, the operator can override the application-directed location.
5.  When the residual inventory is processed, the original order picks from Location1 can be completed.

**Note**: When multiple replenishments are pending to the same location in a zone enabled for splitting replenishment residuals, the application determines whether there is a replenishment currently released to the location to satisfy a pick. If so, then no additional replenishment picks are released to the location unless the application determines that the remaining inventory in the location (after the first pick is complete) is not sufficient to satisfy the next largest committed-quantity pick. However, if the replenishment quantity is under the replenishment percentage, then an additional replenishment to the location can be released even if there is sufficient inventory for the next largest pick.

## Setup

You must complete the following setup tasks before the application will split replenishment residuals:

1.  Set the **Allocate Maximum UOM** field on the replenishment source movement zone to No. See [Add or modify a movement zone](../movement/movement-zones.md).
2.  Configure the pickface (replenishment destination) locations. Define the **Top-Off Replenishment Percentage** and the **Replenishment Percentage** values to determine the quantity of inventory the application can allocate to the location. To create replenishment residuals, the value must be great than 100%. See [Modify a storage location](../../warehouse/locations/storage-locations.md).
3.  Configure the replenishment destination movement zone. To allow the splitting of residuals from replenishments destined to the zone, set the **Split Replenishment Residuals** field to Yes. See [Add or modify a movement zone](../movement/movement-zones.md).
4.  Configure the following replenishment settings:
    -   Select whether residual inventory from a replenishment can be used to fulfill cross dock opportunities (**Cross Dock Residual Inventory** field).
    -   Select whether operators are allowed to overfill replenishment locations (**Overfill Location** field). See [Configure replenishment settings](replenishment-settings.md).
5.  To enable an EMS alert for when the operator enters a deposit quantity of 0 at the replenishment destination location, set the **Replenishment Split Quantity 0** field to Yes. See [Configure Event Management integration](../../integration/event-management.md).

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
