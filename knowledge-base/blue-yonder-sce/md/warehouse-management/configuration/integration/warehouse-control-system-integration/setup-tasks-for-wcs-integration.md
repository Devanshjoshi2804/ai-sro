---
title: "Setup tasks for WCS integration"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/wcs_integration_standardization_setup_tasks.htm"
source: "/content/wcs_integration_standardization_setup_tasks.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Integration"
  - "Warehouse control system integration"
  - "Setup tasks for WCS integration"
sections:
  - "Location configuration"
  - "Cross docking configuration"
  - "Movement zone configuration"
  - "Pick release rules"
  - "Events configurations"
  - "Warehouse equipment configuration"
  - "Movement path configuration"
  - "Location preference rule configuration"
images: []
source_sha1: 272143c1d16b02f39ae4a42b02d3bed2f6d477fc
---
# Setup tasks for WCS integration

In order to fully integrate with the WCS, the following setup configurations must be completed.

## Location configuration

A location is a uniquely identified position within your facility. You use locations to store, stage, or manipulate product. All locations in your facility must be defined in Warehouse Management. Typical locations could include the following object types:

-   Section of a bin or shelf in a storage rack
-   Outlined space on the floor
-   Position inside of a shipping dock door
-   Table used for packing inventory into cartons
-   Conveyor used to transport inventory from one area to another

Specifically, you must configure the following locations to integrate with a WCS:

-   For a black box model configuration, create a single, mixed location.
-   For a non-black box configuration, create as many locations as needed. For example, you can create 1000 locations with a limit of one pallet each.

For more information, see [Locations](../../warehouse/locations.md).

## Cross docking configuration

Cross docking is the process of moving inventory directly from receiving to shipping to satisfy an outbound order line. This process bypasses the intermediate step of storage and speeds up the delivery to the customer. For more information, see [Cross Docking](../../inbound/cross-docking.md).

You can enable inventory being conveyed by the automated material handling equipment (such as a conveyor monorail or AGV) to be cross docked. Cross dock for WCS applies to both planned (order line marked for cross docking) and opportunistic cross dock opportunities (shorts, replenishment, or pick stealing).

If cross docking is enabled for a WCS system, then cross docking opportunities are evaluated by the Warehouse Management in WCS automated line receiving in any of the following cases:

-   An order line marked for cross docking
-   An order that has an allocation shortages
-   An order that satisfies an existing pick

Cross dock work is then created and the inventory is moved to a location that belongs to the movement zone configured for the WCS system.

If cross docking is disabled, the application will attempt to putaway the inventory to a storage location.

**Notes**:

-   Before enabling cross docking in the WCS integration configuration, you must enable cross docking in Warehouse Management, and also select the movement zones associated with the WCS. See [Cross docking setup](../../inbound/cross-docking.md) and [Movement zone configuration](#Movement_zone_configuration_for_WCS_integration_standardization) respectively.
-   Cross docking at WCS automated line receiving does not support splitting pallets; that is, the received quantity must not be greater than the cross dock quantity.
-   If enabled, WCS automated cross docking is applied when received quantity from production lines is less than or equal to the cross dock requested quantity.

## Movement zone configuration

A movement zone represents a group of locations that have the same attributes (such as for splitting LPNs, replenishments, and inventory consolidation) for moving inventory. Any location to or from which inventory is moved using directed work must belong to a movement zone; therefore, most locations in the warehouse will belong to a movement zone.

Specifically, you must configure the following movement zones to integrate with a WCS:

-   A movement zone for infeed (induction)
-   A movement zone for storage
-   A movement zone for outfeed
-   A movement zone for a hop. You must create a movement zone for a default hop at the infeed (induction). Additional hop movement zones are optional.

For more information, see [Movement Zones](../../inventory/movement/movement-zones.md).

## Pick release rules

Pick release rules enable you to specify how to release work. The release rule identifies the action (typically to create work or print documentation) that is required to perform the release, and the directed work operation that is performed to complete the work.

Specifically, you can group picks into a single transaction to integrate with the WCS.

For more information, see [Pick Methods](../../outbound/picking/pick-methods.md).

## Events configurations

You can set the integrator Warehouse Management events that are logged in response to the corresponding WCS events.

An event is a defined occurrence that triggers a transaction. The occurrence of an event causes Integrator to gather data from the triggering system's database or from an inbound IFD for communication to a target system.

An example of an event type could be a request to cancel an outstanding pick request of inventory (can be a single pick or a group of picks).

## Warehouse equipment configuration

Warehouse equipment can be equipment and material handling vehicles that an operator uses to perform directed work and other warehouse operations. In the case of an ASRS, these functions are automated.

Specifically, you must configure the following equipment to integrate with a WCS:

-   Create equipment with the same name as the WCS.
-   Create equipment for each robot inside the ASRS with a name that is different from the movement zones and locations.

For more information on warehouse equipment, see [Warehouse Equipment Type](../../equipment/equipment/warehouse-equipment-type.md).

## Movement path configuration

A movement path specifies the path that inventory takes through your facility when moving from one point to another, and is based on a source zone, destination zone, and LPN level. A movement path can include a hop, which is an intermediate zone to which inventory is moved (not its final destination). A hop is typically a zone that is set up for special processing or inventory handling.

For more information, see [Movement paths](../../inventory/movement/movement-paths.md).

## Location preference rule configuration

Location preference rules identify the guidelines that Warehouse Management uses to find optimal storage locations for inventory that you receive into your facility or identify from a production line.

For more information, see [Location Preference Rules](../../inbound/storage/location-preference-rules.md).

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
