---
title: "Holds"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/holds.htm"
source: "/content/holds.htm"
toc_path:
  - "Warehouse Management"
  - "Inventory"
  - "Holds"
sections:
  - "Inbound hold criteria"
  - "Holds actions"
  - "Hold view"
images: []
source_sha1: 9d82d7d6fc13ea577dde495ada41893c11c90c4a
---
# Holds

A hold is an attribute that is applied to inventory without changing the inventory status. For example, if HOLD1 is applied to LPN1, LPN2, and LPN3 for ITEMA, the inventory status can remain as Available without being changed to a Hold status. With HOLD1 applied to the inventory, the hold can be configured to allow the LPNs to be allocated and shipped. For example, for damaged inventory, the hold allows the "held" inventory to have an Available inventory status for shipping to another location, such as for disposal.

A hold can be defined, maintained, and applied manually by a user or automatically through inbound integration transactions. Specifically, the application can receive the Hold Definition Information (HOLD\_DEF\_INB\_IFD) transaction to create, modify, enable, or disable a hold, and the Hold Assignment Information (HOLD\_ASSIGNMENT\_INB\_IFD) transaction to apply or remove a hold from inventory. Hold activity, displayed on the Holds page, identifies the date and time the hold was created and modified, and by whom. The user name SUPER identifies hold activity initiated by an integration transaction.

Holds are warehouse specific. The hold prefix, which is configured for the warehouse, can be used to identify the warehouse in which the hold was created.

A hold type is a category used to group holds that are similar, and typically identifies the purpose of the hold. For example, you can define a Customer Service hold type and an Inventory Control hold type to identify the departments for which the hold was created. There can be more than one hold applied the same LPN (or inventory) at the same time; for example, both HOLD1 and HOLD2 can be applied to LPN01.

You can configure a hold to prevent the status of inventory on hold from being changed. For example, if your facility uses aging profiles, you may want to prevent the status of inventory on hold from being changed automatically as it ages. The hold assigned to inventory can be configured to prevent the inventory from being allocated or shipped, but the hold itself does not change the inventory status.

## Inbound hold criteria

You can define an inbound (future) hold by setting the **Apply to Inbound Inventory** field to Yes, and then defining the criteria for the inventory to which it will be applied. An inbound hold is applied automatically to inventory that matches the criteria when the inventory is identified (such as during receiving, production line receiving, or an inventory adjustment) or, if an area or location is specified, moved to the specified area or location.

For example, if you configure inbound hold criteria for a specific item, lot, and supplier, then when inventory matching the item, lot, and supplier is identified, the hold is applied automatically. In addition, if existing inventory is adjusted (added or modified) to match the item, lot, and supplier (for example, if it was originally identified with the wrong lot), the hold is applied to that inventory as well.

**IMPORTANT**: If you select to apply the hold to inbound inventory, but you do not specify any inbound hold criteria, then the hold will be applied to all inventory that is identified or adjusted.

When configuring inbound hold criteria, you can specify an area or location to limit the locations in which the hold is applied automatically. If you specify an area or location, then the following behavior occurs:

-   The hold is applied to matching inventory that is either identified to, adjusted into, or moved into the specified area or location. If the hold is applied to the inventory, it remains applied when the inventory is moved out of the area or location.
-   The hold is not automatically applied to matching inventory that currently exists in the area or location.
-   The hold is not automatically applied to matching inventory that is identified to, adjusted into, or moved into other areas or locations.

For example, a hold is defined with the following inbound hold criteria:

-   **Item**: ITEM01
-   **Manufacturing Date**: **From** 5/1/2019, **To** 5/31/2019

If a pallet of ITEM01 is received with a manufacturing date of 5/2/2019, the hold is applied. If another pallet of ITEM01 is received with an incorrect date of 4/31/2019, the hold is not applied. After the pallet is put away to a storage location, a user performs an inventory adjustment to correct the manufacturing date to 5/2/2019. Now the inventory matches the hold criteria, and the hold is applied automatically.

As another example, a hold is defined with the following inbound hold criteria:

-   **Item**: ITEM01
-   **Manufacturing Date**: **From** 5/1/2019, **To** 5/31/2019
-   **Area**: Expected Receipts

If a pallet of ITEM01 is received with a manufacturing date of 5/2/2019, the hold is applied. If another pallet of ITEM01 is received with an incorrect date of 4/31/2019, the hold is not applied. After the pallet is put away to a storage location, a user performs an inventory adjustment to correct the manufacturing date to 5/2/2019. However, the hold is not applied.

Since you specified the Expected Receipts area, the hold is applied to matching inventory during receiving, but it is not applied when making inventory attribute changes to existing inventory in other areas of the warehouse, and it is not applied to matching inventory received from a production line.

## Holds actions

The Holds page provides visibility to the enabled and disabled hold definitions and holds applied to the inventory in the warehouse. You use the Holds page to configure hold definitions that define the purpose of a hold and the actions that are taken when a hold is applied. You use inventory hold operations to apply or remove holds on inventory within your facility. You can filter holds on the Holds page by the hold number or type.

The following actions can be performed from the Holds page:

-   **Add hold**: To define a new hold definition, see [Add a hold](holds/procedures-for-holds.md).
-   **Enable or disable hold**: To enable or disable a hold definition, see [Enable a hold](holds/procedures-for-holds.md) or [Disable a hold](holds/procedures-for-holds.md).
-   **Apply hold**: To apply a hold to inventory, see [Apply a hold to inventory](holds/procedures-for-holds.md).
-   **Release hold**: To remove a hold from inventory, see [Release a hold from inventory](holds/procedures-for-holds.md).

Holds are applied to inventory at the item and LPN level from the following pages:

-   Items and LPNs tabs in Inventory page
-   Item view and LPN view from the Location, Items and LPNs tabs in the Inventory page
-   LPN view from the LPNs tabs in the Hold view

You can apply multiple holds to an LPN. The application supports multi-level holds, which means that you can place multiple holds on inventory for different reasons. The multi-level hold functionality is designed to accommodate those facilities that need to hold inventory at different times to meet multiple job function requirements. For example, you can place two holds on a product to prohibit it from being allocated until it is repackaged, and shipped before it passes a final inspection.

If a hold is applied to an item, all the inventory belonging to that item is held, regardless of the LPN on which the inventory is located. If a hold is applied to inventory on a specific LPN, only the inventory on that LPN is held. When a hold is applied to inventory, a Hold tag is applied to the item or LPN to which the hold is applied. The Hold tag displays information about all the holds applied to the inventory, along with the date and time when the hold was applied.

You can click a hold definition in the Active Holds and Disabled Holds grid to view the details. The hold details are displayed in the following tabs:

-   **Active Holds**: Displays all enabled hold definitions. The hold definition displays the number of LPNs to which the hold is applied.
-   **Disabled Holds**: Displays the hold definitions that are disabled. A hold definition that is disabled cannot be applied to inventory.
-   **History**: Displays a list of the hold actions (apply or release hold) performed on the inventory.

## Hold view

You can display the hold view from both the Active Holds and Disabled Holds tabs by clicking the hold definition. You cannot perform any actions on a disabled hold. The following information can be displayed for a hold selected from the Holds grid:

-   Heading information
    -   The description of the item, hold type, and severity level
    -   The configuration settings for the hold such as Allows Shipping, Allows Allocation, Allows Status Change, Applies To Inbound Inventory, and Allows Movement for RF Outbound Audit
-   Summary information
    -   The activities performed on the LPN, including Date Created, User, number of LPNs, and locations
    -   The inbound inventory criteria such as, item and client
    -   Notes entered for the hold
    -   An action is available to release all inventory associated with the hold. This action is useful when a hold is applied to a large number of LPNs.
-   LPN information
    -   Basic information for items, quantities and footprints, and location
    -   Attributes of the items on the LPN
    -   Date information for the inventory on the LPN
    -   An action is available to release the hold on the LPN. You can release the hold from all inventory to which the hold is applied or from individual LPNs.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
