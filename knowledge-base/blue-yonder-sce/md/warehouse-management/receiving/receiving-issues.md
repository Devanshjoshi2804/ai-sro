---
title: "Receiving Issues"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/receiving_issues.htm"
source: "/content/receiving_issues.htm"
toc_path:
  - "Warehouse Management"
  - "Receiving"
  - "Receiving Issues"
sections:
  - "Receiving issues: Not expected"
  - "Receiving issues: No location"
  - "Receiving issues: Not receivable"
  - "Receiving issues: Location overrides"
  - "Receiving issues: Overage"
  - "Receiving issues: Shortages"
  - "Receiving issues: Damaged"
  - "Receiving issues: Distribution exceptions"
  - "Receiving issues: Inbound quality"
images: []
source_sha1: da0eeea5abd0bbf263d6553f8c99b27a917397bb
---
# Receiving Issues

Receiving issues represent the disposition of inventory or unexpected receiving activity that can prevent the successful progression of receiving inventory into the warehouse.

When you select **Receiving > Receiving Issues**, the navigation bar displays a list of issues and the number of items affected by the issue.

You can click an issue to view the item details and other relevant information that can help you resolve the issue.

**Note**: Inventory attribute differences (receiving inventory with different characteristics than expected) are indicated as quantity discrepancies (overage or shortage). For example, if an inbound order should have 20 eaches from lot A, but you received 20 eaches from lot B, then two issues are noted: a shortage of 20 eaches for lot A and an overage of 20 eaches for lot B.

## Receiving issues: Not expected

Unexpected items represent inventory, identified into the warehouse, that was not associated with an inbound order or planned inbound order. Without a planned inbound order line, the inventory description and quantities cannot be checked against expected items and quantities.

Users can receive unexpected items if the warehouse is configured to allow it. The list of unexpected items only represents inventory that did not match any planned inbound order line. The list does not include inventory that matched the requirements of a planned inbound order line but had an attribute (such as a lot number, revision level, origin code, or inventory status) that was not specified on the order line.

See [Manage unexpected items](receiving-issues/procedures-for-receiving-issues.md).

## Receiving issues: No location

Inventory for which the application could not find a storage location during putaway, based on the storage search path configurations, is considered to be problem inventory and is put in error.

The following table contains some of the reasons why a location may not be found, as well as possible research and resolution tasks.

  
| Reasons | Research Tasks | Options for Resolution |
| --- | --- | --- |
| -   • The inventory does not match any existing storage search path.
<br>-   • The LPN does not fit in eligible locations in the storage zone (capacity exceeded).
<br>-   • The LPN cannot be mixed with any existing inventory in the storage locations (for example, the lot is different from what is currently being stored).
<br>-   • For date-controlled inventory, the LPN exceeds the allowable date window for eligible locations. | -   • View the inventory for which a location cannot be found.
<br>-   • View inventory item and footprint configurations to see if there are issues, such as missing or incorrect dimensions.
<br>-   • View the storage search paths to verify that an appropriate rule has been defined.
<br>-   • View mixing restrictions to determine if a restriction is preventing inventory storage.
<br>-   • View inventory history to determine other causes. | -   • Modify the item and footprint configuration to allow storage.
<br>-   • Add or modify a storage search path.
<br>-   • Modify existing mixing restrictions.
<br > See [Manage items without a valid storage location](../inventory/inventory-issues/procedures-for-inventory-issues.md). |

When inventory is in the no location error, you can view it using the No Location page. If your warehouse has a location configured for problem inventory, an operator may deposit the inventory in that location to clear the inventory error. When the error is removed from the inventory, the inventory is no longer displayed as an issue.

You can manually initiate putaway for an item without a valid storage location by executing a storage location search. When the application is finished searching, you can view the search results, which include a list of locations that were considered for storage, and the storage zone rules that were applied during the search.

If the search is successful and there is a defined movement path for the inventory from its current location to the storage location, then directed work is created to move the inventory to the location that was found.

See [Manage items without a valid storage location](receiving-issues/procedures-for-receiving-issues.md).

## Receiving issues: Not receivable

An item may not be receivable because it is new, or the item configuration has the **Receivable** field set to No. Items that are not receivable are displayed on the Not Receivable page when the associated inbound shipment is assigned to a staging lane, or when the associated transport equipment is checked in. If an operator attempts to receive (scan) an item that is not receivable during identification, an error is displayed.

Typically new items are sent from the host with the **Receivable** field set to No so that users will verify the item footprint for sizing, the item family for storage, and the cost for adjustments before enabling the item for receiving.

To receive the item for the first time, you can perform the following tasks:

-   Add the item configuration, if it does not already exist.
-   Measure and weigh the item so that its item footprint can be added with accurate size and weight information.
-   Configure the item to be receivable.

See [Manage non-receivable items](receiving-issues/procedures-for-receiving-issues.md).

## Receiving issues: Location overrides

The application determines the best location for an operator to deposit an LPN based on the following factors:

-   Putaway rules
-   Location capacity
-   Current inventory in the location
-   Location status
-   Location distance relative to the operator
-   The configured movement path
-   Inventory rotation methods

An operator may override the application-directed putaway location if there is a problem with the location or if there is an alternative location that is in closer proximity to the operator. When an operator performs a location override, the operator must enter an override reason.

See [View items deposited in an override location](receiving-issues/procedures-for-receiving-issues.md).

## Receiving issues: Overage

An overage is a quantity received against a planned inbound order line that is greater than the expected quantity on the order line.

Users and RF operators can perform over-receiving in quantities up to the threshold values (based on cost, quantity, or percentage) that are defined for a supplier, item, client, or over-receipt configuration (in that order of precedence).

A user at a workstation can perform over-receiving above the threshold values if the user is assigned to a role that is authorized to do so.

See [Manage items received over the expected quantity](receiving-issues/procedures-for-receiving-issues.md).

## Receiving issues: Shortages

A shortage is a received quantity that is less than the expected quantity on a planned inbound order line. Shortages are only recorded and displayed after the inbound shipment for the affected planned inbound order is closed.

The application considers a received item quantity to be short in the following cases:

-   The item quantity that is received at your warehouse is less than the expected quantity.
-   An operator receives an item quantity less than the expected quantity.
-   The item quantity that is put away is less than the expected quantity.

See [Manage items received under the expected quantity](receiving-issues/procedures-for-receiving-issues.md).

## Receiving issues: Damaged

Damaged inventory can be indicated as such by its status or if it is deposited to a location designated for damaged inventory (regardless of inventory status). Items can be designated as damaged at any point during the receiving process, at which point they are displayed as a receiving issue. Damaged inventory also is displayed on the Over, Short, and Damaged (OSD) Report.

See [Manage damaged items](receiving-issues/procedures-for-receiving-issues.md).

## Receiving issues: Distribution exceptions

A distribution exception occurs when there is a discrepancy in the amount of actual residual (excess) inventory and the expected residual quantity at the end of the distribution deposit process and the audit fails (if an audit is required). When an audit is performed, the operator enters the quantity and the application compares the entered residual quantity against the expected residual quantity. See [Residual inventory and exceptions](distribution-concepts.md) and [Distribution deposit process](distribution-concepts.md).

When an audit fails, the operator is directed to deposit the unplanned inventory into an unexpected exceptions location. A user must determine what the issue is and then gather information on how to resolve it. When resolved, the operator can clear the exception and move the inventory out of the unexpected exception location. See [View and resolve distribution exceptions](receiving-issues/procedures-for-receiving-issues.md).

## Receiving issues: Inbound quality

To help you monitor the level of quality that you receive from suppliers and carriers delivering product to your facility, the application enables you to document any quality issues that you encounter as you receive inventory into the warehouse. For example, you can document the amount of damaged product that a supplier delivers, or whenever a particular carrier arrives late. A default set of supplier and carrier issue types is provided, but you can add other issues that you want available for selection when a quality issue is reported. See [Configure close inbound shipments](../configuration/inbound/receiving/close-inbound-shipment.md).

You can document quality issues on the **Receiving Issues > Inbound Quality Issues** page, or against a specific inbound shipment or order from the Inbound Shipments page.

After issues are documented, you can manage quality issues in the following ways:

-   View any supplier or carrier issues associated with planned inbound orders
-   Change the details of a documented issue
-   Delete documented issues that have been resolved

See [View or modify an inbound quality issue](receiving-issues/procedures-for-receiving-issues.md).

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
