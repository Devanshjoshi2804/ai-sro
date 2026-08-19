---
title: "Shipping Issues"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/shipping_issues.htm"
source: "/content/shipping_issues.htm"
toc_path:
  - "Warehouse Management"
  - "Shipping"
  - "Shipping Issues"
sections:
  - "Shipping issue: Short"
  - "Shipping issue: Not shippable inventory"
  - "Shipping issue: Problem inventory"
  - "Shipping issue: RF outbound audit"
images: []
source_sha1: 69aeba7c950fa3516656222930adf055debda8bb
---
# Shipping Issues

Shipping issues represent the disposition of inventory that can prevent an outbound load from being shipped on time and provide visibility to problems that arise in the shipping process.

When you select **Shipping > Shipping Issues**, the navigation bar displays a list of issues and the number of items, LPNs, or loads affected by the issue.

You can click an issue to perform the following tasks:

-   Display a list of LPNs, loads, or items affected by the issue
-   Display additional details for each LPN, load, or item to further investigate the issue
-   Take action to resolve the issue, where applicable

## Shipping issue: Short

A short allocation occurs when a wave is allocated and there is not enough inventory available to fill the order. Short allocations can occur for different reasons including the following examples:

-   The necessary inventory is outside of the allocation search path.
-   Inventory is on a hold that does not allow allocation.
-   Inventory is in a location that is in error.
-   Attributes of the available inventory are different from that needed for the order.

After the appropriate research is done to identify why a short allocation exists, you can take the necessary steps to resolve the issue and reallocate the inventory, or you can ship the inventory short if the order line allows a partial quantity.

See [Short allocations](../outbound-planner/outbound-planning-concepts.md) and [Manage short loads and items](shipping-issues/procedures-for-shipping-issues.md).

## Shipping issue: Not shippable inventory

Inventory may be not shippable because it has been placed on a hold, in an inventory status that does not allow shipping, or the catch quantity is beyond the normal tolerance limits and within the extreme tolerance limits. Additionally, if sub-LPN catch quantity is required and has not been captured, then the inventory is not shippable.

For example, if quality inspections are required for certain inventory prior to shipping, a temporarily hold may be placed on the inventory until the inspection is complete, during which time the inventory is not shippable.

Alternatively, the status of inventory may have changed during processing to indicate, for example, that it is damaged or expired (for date-tracked inventory).

See [Manage inventory that is not shippable](shipping-issues/procedures-for-shipping-issues.md).

## Shipping issue: Problem inventory

Problem inventory refers to inventory that cannot be shipped for reasons other than a hold or inventory status. For example, if inventory was picked for an order, and the order was cancelled, the picked inventory is considered problem inventory because the order no longer exists.

Alternatively, if a picked LPN is damaged after it has been staged, it is considered problem inventory because while it should not be shipped, the application would still allow it because its status does not change.

Operators must move problem inventory to a designated problem location, from which it can be returned to storage (if an order was canceled, for example) or moved to a quality assurance location (if a staged LPN was damaged, for example).

See [View problem inventory](shipping-issues/procedures-for-shipping-issues.md).

## Shipping issue: RF outbound audit

An outbound audit is a process that is performed by an RF operator to validate that the inventory picked for a shipment matches the expected inventory. When an audit is pending or started, it becomes visible as a shipping issue; additionally, you can view detailed information for completed audits and for audits with discrepancies. A discrepancy occurs when the attribute value entered by the operator is different from what the application expected.

For each audit record, you can view the following general information:

-   Date and time on which the audit was started
-   Identifier for the inventory being audited
-   Current location of the audited inventory
-   User that completed (or will complete) the audit
-   Order and shipment identifiers for the inventory under audit
-   Supplier and client to which the inventory belongs<br>

Regardless of whether the audit is pending, complete, or has discrepancies, when you select the identifier for which an audit exists, you can view the following detailed information, when applicable:

-   Basic information such as item, LPN, and quantity details
-   Attribute details such as the item lot, origin, and associated handling unit
-   Dates related to the inventory under audit such as the aging profile, manufactured and expiration date, and the date on which the inventory was received
-   Shipping details such as the date on which the inventory was picked, the associated order line, and load and stop identifiers
-   Serial numbers for serialized inventory

See [View audited inventory](shipping-issues/procedures-for-shipping-issues.md).

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
