---
title: "Picking Issues"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/picking_issues.htm"
source: "/content/picking_issues.htm"
toc_path:
  - "Warehouse Management"
  - "Picking"
  - "Picking Issues"
sections:
  - "Picking issue: Not pickable"
  - "Picking issue: Cancelled picks"
  - "Picking issue: Unallocated orders"
  - "Picking issue: Picked UOM discrepancy"
images: []
source_sha1: de6d927f168464e1089cbc2d997fb866dfe3a23c
---
# Picking Issues

Picking issues are problems that can affect the picking process and whether orders can be fulfilled and shipped on time.

Some picking issues represent problems in the picking process that prevent inventory for an order from being successfully picked. For example, the inventory might not be pickable because the application cannot locate it in the search path, or picks were cancelled, or inventory cannot be allocated for an order.

When you select **Picking > Picking Issues**, the navigation bar displays the list of issues and the number of locations, LPNs, items, or orders affected by the issue. You can click an issue to view additional information and to further investigate the issue, and to take actions to resolve the issue, where applicable.

## Picking issue: Not pickable

Inventory is considered not pickable when the application cannot locate the inventory or if the pick cannot be completed for another reason. The Not Pickable page displays the locations where inventory is stored but cannot be picked to fulfill an order.

The following table describes the reasons why inventory is not pickable, and how to research and resolve the issue.

  
| Reasons | Research Task | Options for Resolution |
| --- | --- | --- |
| **Location Out of Service**<br>-   • The location configuration is disabled.
<br>-   • The location has been set to out of service due to damage or some other problem with the location.
<br>-   • The location has been set to inventory error due to an inventory count or adjustment taking place. | View the location configuration. | Modify the location to enable its configuration. |
| **Location Not Pickable**<br > The **Pickable** field on the location configuration is set to No. | View the location configuration. | Modify the location to set the **Pickable** field to Yes. |
| **No Pick Zone Assigned**<br > The storage location in which the inventory resides is not assigned to a pick zone. | View the location configuration. | Assign a pick zone to a location or group of locations. |
| **Zone not in Search Path**<br > The storage location is assigned to a pick zone, but the pick zone is not assigned to an allocation search path. | View the allocation search path configuration. | Add or modify an allocation search path and assign the pick zone to one of its search path rules. |
| **UOM Not Pickable**<br > The storage location is assigned to a pick zone that is assigned to an allocation search path, but there is no search path for allocating the required UOM. | View the allocation search path configuration. | Add or modify an allocation search path and configure one of its search path rules to allocate the required UOM. |

See [Manage inventory that is not pickable](../inventory/inventory-issues/procedures-for-inventory-issues.md) and [View and manage inventory that is not pickable](picking-issues/procedures-for-picking-issues.md).

## Picking issue: Cancelled picks

Picks are typically cancelled when the pick cannot be completed. Users on a workstation are able to cancel any pick that has been released and not started. RF operators may need to cancel picks for various reasons such as the inventory is not in the proper condition to fulfill a customer order.

You can view cancelled picks for the current day, or you can view cancelled picks by selecting a date range or a previous date. See [View cancelled picks](picking-issues/procedures-for-picking-issues.md).

The following are some scenarios in which a pick can be cancelled:

-   A pick location is in error or there is an inventory discrepancy in the location.
-   A short order needs to be shipped today and can be shipped short (so the unfulfilled picks are cancelled).
-   Inventory in a pickface is not pickable for some reason (for example, it is damaged).
-   A work assignment pick cannot be completed, such as when a picking location is empty or the item to be picked will not fit on a pallet.

When a pick is cancelled, the user or operator must select a reason the pick was cancelled, which also determines how the application processes the cancellation. The pick cancellation reasons are configurable. See [Pick Cancellation](../configuration/outbound/picking/pick-cancellation.md).

## Picking issue: Unallocated orders

Unallocated orders become an issue when the inventory remains unallocated on the date on which the order is supposed to ship as determined by the appointment departure time or late ship date defined on the order line.

The Orders Not Allocated page displays the orders and loads with unallocated inventory scheduled to ship on the current day, or you can filter by selecting a date range or specific date. See [View unallocated orders](picking-issues/procedures-for-picking-issues.md).

## Picking issue: Picked UOM discrepancy

A picked UOM discrepancy occurs when a picking operator performs a pick in a unit of measure (UOM) that is different from what was specified by the work reference. For example, instead of picking 3 cases (40 eaches per case), the operator picks 1 case and 80 eaches; or, instead of picking 1 pallet (10 cases per pallet), the operator picks 10 cases.

Picked UOM discrepancies are logged if the application is integrated with Warehouse Labor Management, and the integration is configured to send pick information in the UOM that was actually picked. Multiple picked UOM discrepancies by the same operator can be an indicator that the operator is picking at a different UOM to earn more work credit (and in turn, higher pay incentives).

See [View picked UOM discrepancies](picking-issues/procedures-for-picking-issues.md).

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
