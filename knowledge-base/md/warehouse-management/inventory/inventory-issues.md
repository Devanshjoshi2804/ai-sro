---
title: "Inventory Issues"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/inventory_issues.htm"
source: "/content/inventory_issues.htm"
toc_path:
  - "Warehouse Management"
  - "Inventory"
  - "Inventory Issues"
sections:
  - "Inventory issue: Not receivable"
  - "Inventory issue: Not pickable"
  - "Inventory issue: Not shippable"
  - "Inventory issue: Expiring"
  - "Inventory issue: Locations in error"
  - "Inventory issue: Mixing violations"
  - "Inventory issue: No location"
  - "Inventory issue: Location overrides"
  - "Inventory issue: Damaged"
  - "Inventory issue: Out of sequence"
images: []
source_sha1: 4a4b711f8d9cacbc72311e9ec971ddbbf094115a
---
# Inventory Issues

Inventory issues are problems that prevent inventory from being received, allocated, put away, or picked. The Inventory Issues page displays the summary for the most significant issues and the amount of inventory affected by those issues.

When you select **Inventory > Inventory Issues**, the navigation bar displays a list of issues and a count of the number of LPNs, locations, or items affected by each issue.

You can click an issue to perform the following tasks:

-   Display a list of inventory, locations, or items affected by the issue.
-   Display the details of each LPN, location, or item to further investigate the issue.
-   Access relative configuration options that can be used to resolve the issue.

## Inventory issue: Not receivable

An item may not be receivable because it is new or the item configuration has the **Receivable** field set to No. Items that are not receivable are displayed on the Not Receivable page when the associated inbound shipment is assigned to a staging lane, or when the associated transport equipment is checked in. If an operator attempts to receive (scan) an item that is not receivable during identification, an error is displayed.

Typically new items are sent from the host with the **Receivable** field set to No so that users will verify the item footprint for sizing, the item family for storage, and the cost for adjustments before enabling the item for receiving.

The following table describes the reasons why inventory cannot be received, and how to research and resolve the issue.

  
| Reasons | Research Tasks | Options for Resolution |
| --- | --- | --- |
| -   • The item configuration prevents receiving.
<br>-   • The item configuration is missing footprint information. | -   • View the inventory display of item and footprint information.
<br>-   • View storage configuration rules.
<br>-   • View item mixing restrictions. | -   • Add or modify the item configuration and set the **Receivable** field to Yes.
<br>-   • Modify the item configuration to add or modify footprint information.
<br>-   • Add or modify a storage search path for storing the inventory after it is received.
<br>-   • Add or modify mixing restrictions to allow for storing the inventory.
<br > See [Manage inventory that is not receivable](inventory-issues/procedures-for-inventory-issues.md). |

## Inventory issue: Not pickable

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

See [Manage inventory that is not pickable](inventory-issues/procedures-for-inventory-issues.md) and [View and manage inventory that is not pickable](../picking/picking-issues/procedures-for-picking-issues.md).

## Inventory issue: Not shippable

Inventory is considered not shippable if it has been placed on hold or in an inventory status that does not allow shipping. For example, if quality inspections are required for certain inventory prior to shipping, a temporary hold may be placed on the inventory until the inspection is complete, during which time the inventory is not shippable.

Alternatively, the status of inventory may have changed during processing to indicate, for example, that it is damaged or expired (for date-tracked inventory).

  
| Reasons | Research Tasks | Options for Resolution |
| --- | --- | --- |
| -   • A hold is applied to the item.
<br>-   • The user assigned one of the not shippable statuses to the inventory.
<br>-   • During inventory status change operation, the operator changes the status of the inventory to not shippable. | -   • Determine why the inventory is put on hold.
<br>-   • Determine why the inventory is in a status where it is ineligible for shipping.
<br>-   • View inventory history to determine the cause. | Change the status of the inventory, after it has been inspected.<br > See [Manage inventory for not shippable items](inventory-issues/procedures-for-inventory-issues.md). |

## Inventory issue: Expiring

Expiring inventory is date-tracked inventory that will expire in a specified amount of time. The expiration window (time in advance of an item's expiration date that inventory is considered expiring) is defined by the configuration of the item.

The following table describes the reasons why inventory is expiring, and how to research and resolve the issue.

  
| Reasons | Research Tasks | Options for Resolution |
| --- | --- | --- |
| -   • The item is a date-tracked item that is configured with the Time To Warn for Expiration inventory attribute. This attribute specifies the amount of time prior to the item's expiration date that the application notifies users that the item will be expiring.
<br>-   • The date on which the item will expire is defined by either the shelf life or aging profile assigned to the item. | -   • View the inventory display for the item.
<br>-   • View the item configuration.
<br>-   • View the aging profile for the item.
<br>-   • View the inventory history. | Verify that the inventory is in the correct location to be allocated and picked. If it is not, perform one of the following tasks:<br>-   • Schedule a move of the inventory to a proper location.
<br>-   • Change the shelf life or aging profile for the item.
<br > See [Manage expiring inventory](inventory-issues/procedures-for-inventory-issues.md). |

## Inventory issue: Locations in error

Location in error is a location status that temporarily prevents inventory activity from taking place in the location. When a location is in error, the location is no longer available for storage or for reserving the inventory in the location for orders. Any inventory activity for the location that was in progress before setting the location in error can be completed, but no new activity is created.

The following table describes the reason for a location in the error status, and how to research and resolve the issue.

  
| Reasons | Research Tasks | Options for Resolution |
| --- | --- | --- |
| -   • An inventory adjustment is taking place at the location.
<br>-   • A user has manually set the location to the error status. | -   • View the location to determine what inventory is in the location.
<br>-   • View inventory history to determine the reason for the location being in error. | -   • Reset the location to remove the error status.
<br>-   • Schedule a count for the location to verify the inventory quantities at the location.
<br > See [Manage locations in error](inventory-issues/procedures-for-inventory-issues.md). |

## Inventory issue: Mixing violations

A mixing violation exists when inventory is stored in a location with other inventory that violates the mixing restrictions defined for the warehouse, building, storage zone, or LPN. Mixing restrictions are configured to prevent the storage of selected item or inventory attributes (such as item, lot, or handling unit) in the same location.

The following events are examples of how a mixing violation can occur:

-   A user overrides a deposit location or moves inventory to a location where the inventory is not compatible with mixing restrictions.
-   Inventory in a location changes (such as its status) to a value that is not compatible with mixing restrictions.

The following table describes the reason for mixing violations, and how to research and resolve the issue.

  
| Reasons | Research Tasks | Options for Resolution |
| --- | --- | --- |
| Inventory is stored in a location with other inventory that is incompatible with mixing restrictions. | View the inventory display for the location with the mixing violation. | Schedule a move of the inventory to a proper location.<br > See [Manage mixing violations](inventory-issues/procedures-for-inventory-issues.md). |

## Inventory issue: No location

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
<br > See [Manage items without a valid storage location](inventory-issues/procedures-for-inventory-issues.md). |

When inventory is in the no location error, you can view it using the No Location page. If your warehouse has a location configured for problem inventory, an operator may deposit the inventory in that location to clear the inventory error. When the error is removed from the inventory, the inventory is no longer displayed as an issue.

You can manually initiate putaway for an item without a valid storage location by executing a storage location search. When the application is finished searching, you can view the search results, which include a list of locations that were considered for storage, and the storage zone rules that were applied during the search.

If the search is successful and there is a defined movement path for the inventory from its current location to the storage location, then directed work is created to move the inventory to the location that was found.

## Inventory issue: Location overrides

Location overrides represent inventory that was put away to a location as a result of an operator overriding the application-directed storage location. An operator may choose to override a directed deposit location because there is something wrong with the location or with the inventory in the location, such as damage, the location is full, or mixing is not allowed and the inventory to deposit is not compatible with the inventory currently residing in the location. Upon overriding a location, the operator may select an override reason that results in one or more of the following events:

-   Changes the status of the location to full, and updates and location's maximum capacity to the current capacity
-   Changes the status of the location to inventory error
-   Generates a cycle count for the location

The following table describes the reason for overrides, and how to research and resolve the issue.

  
| Reasons | Research Tasks | Options for Resolution |
| --- | --- | --- |
| During putaway or an inventory move, the operator selected to override the application-directed deposit location and deposited the inventory in a different, manually selected location. | -   • View the inventory to determine other locations in which the inventory is stored.
<br>-   • View the storage search paths to verify that an appropriate rule has been defined.
<br>-   • View inventory history to determine the cause. | -   • Modify the item and footprint configuration to allow storage.
<br>-   • Add or modify a storage search path.
<br>-   • Modify existing mixing restrictions.
<br>-   • Schedule a move of the inventory to a proper location.
<br > See [Manage inventory in override locations](inventory-issues/procedures-for-inventory-issues.md). |

## Inventory issue: Damaged

Inventory is considered damaged when one of the "damaged" inventory statuses has been assigned to it. The inventory statuses that are tracked as "damaged" are defined in the configuration for closing an inbound shipment. See [Configure close inbound shipments](../configuration/inbound/receiving/close-inbound-shipment.md).

**Note**: The Damaged display shows the inventory that is currently in damaged status. It does not show the inventory that was in damaged status earlier and is currently in another state.

The following table describes the reasons for damaged inventory, and how to research and resolve the issues.

  
| Reasons | Research Tasks | Options for Resolution |
| --- | --- | --- |
| -   • During receiving, the user assigned one of the damage statuses to the inventory.
<br>-   • As part of inventory status change operation, the user changed the inventory status to damaged. | View inventory history to determine when the inventory was set to damaged. | Change the status of the inventory, after the inventory has been inspected.<br > See [Manage damaged inventory](inventory-issues/procedures-for-inventory-issues.md). |

On the Damaged page, you can click on an LPN to view its details. When viewing LPN details, you can perform actions on the LPN.

## Inventory issue: Out of sequence

Inventory is considered out of sequence when it is stored in a manner that violates the defined item class level configurations. The Out of Sequence page displays the inventory that is being vertically stored out of class level sequence.

An item class is a category you can create to group items for processing typically based on matching characteristics, such as hazardous or flammable material. An item class level is a configuration that can be used (depending on the storage zone configuration) to determine the level at which an item class can be stored in relation to other item class levels.

With item class levels, 1 is the lowest possible level and must not be stored above any other item class level. Item class level 2 can be stored above item class level 1 but must not be stored above higher item class levels, and so on. Therefore, if inventory belonging to item class level 1 is stored above inventory in item class level 2 in the same bay, then the inventory is out of sequence, and all of the locations in the bay are displayed on the Out of Sequence page. See [Item Class Levels](../configuration/inventory/items/item-class-levels.md).

  
| Reasons | Research Tasks | Options for Resolution |
| --- | --- | --- |
| Inventory stored in a storage zone enabled for item class level storage is out of class level sequence. For example, a lower class level is stored above a higher class level. | View the inventory (and associated item class levels) that is stored out of sequence in the bay. | -   • Move the inventory so it no longer is out of sequence.
<br>-   • Adjust the class level assigned to the item class for the inventory so it is no longer out of sequence.
<br > See [Manage out of sequence inventory](inventory-issues/procedures-for-inventory-issues.md). |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
