---
title: "Systems and settings for WCS integration "
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/systems_and_settings_for_wcs_integration_standardization_.htm"
source: "/content/systems_and_settings_for_wcs_integration_standardization_.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Integration"
  - "Warehouse control system integration"
  - "Systems and settings for WCS integration "
sections:
  - "Movement zone settings"
  - "Pick grouping settings"
  - "Event settings"
  - "Inventory reconciliation settings"
  - "Inventory movement settings"
images: []
source_sha1: 433d4cafc7a3f0f0f68449ce71dc486485395bcb
---
# Systems and settings for WCS integration

For each WCS that you are integrating with, you must select a system. The following systems are available:

-   **AGV\_OUT**: Used for partial (outbound to) WCS integration.
-   **ASRS\_OUT**: Used for partial (outbound to) WCS integration.
-   **WCS**: Master system that is used for complete integration between Warehouse Management and the WCS.
-   **WCS\_IN**: Not currently active for WCS integration.
-   **WCS\_RECON**: Not currently active for WCS integration.

For each system, configure the following settings:

-   Movement zones
-   Pick groupings
-   Events
-   Inventory reconciliation
-   Inventory movement

## Movement zone settings

You can set the Warehouse Management movement zones associated with the WCS. Typical movement zones include those used for moving inventory into the ASRS, storing inventory in the ASRS, and moving inventory out of the ASRS.

For more information, see [Movement Zones](../../inventory/movement/movement-zones.md).

## Pick grouping settings

You can set the way in which messages are grouped for specific work types when they are sent from Warehouse Management to the WCS.

You can configure the following pick groupings:

-   **Order**: Pick requests are grouped by order when the message is sent to the WCS.
-   **Order, Work Order**: Pick requests are grouped first by order and then by work order when the message is sent to the WCS.
-   **Shipment**: Pick requests are grouped by shipment when the message is sent to the WCS.
-   **Shipment, Work Order**: Pick requests are grouped first by shipment and then by work order when the message is sent to the WCS.
-   **Wave**: Pick requests are grouped by wave when the message is sent to the WCS.
-   **Entire WCS**: Pick requests are grouped into a single message and sent to the WCS.
-   **No Grouping**: Pick requests are sent individually to the WCS.

You can configure the following work types:

-   **Pick**: Work type used to pick inventory to fill an order.
-   **Kit**: Work type used to pick component items to fill a work order.
-   **Bulk Pick**: This work type is not currently supported.
-   **Manual Replenishment**: Work type used for manual replenishment. A manual replenishment is an inventory move request initiated by a user or RF operator that serves as a top-off replenishment. It is typically generated when the user determines that a location must be replenished with a specific item. In response to the move request, the application allocates the inventory and generates replenishment pick work to fill the location with inventory. If initiated by an RF operator, the application assigns the replenishment pick work to the requesting operator.
-   **Top-off Replenishment**: Work type used for top-off replenishment. A top-off replenishment is a replenishment process that can be automatically generated at timed intervals or started manually by a user at a specific time (for example, a slow time of day for the warehouse). When initiated, the top-off replenishment process checks the quantities of items in areas and locations that are configured for top-off replenishments. If the process finds quantities that have dropped below the top-off levels, it issues a replenishment request.
-   **Triggered Replenishment**: Work type used for triggered replenishment. A triggered replenishment is the replenishment of a location that is generated automatically when an operator picks inventory from a location to the point that the quantity of the inventory falls below a user-defined level for the location.
-   **Emergency Replenishment**: Work type used for emergency replenishment. If replenishment processing is enabled, an emergency replenishment is generated automatically during allocation when there is insufficient inventory in a pick location to satisfy an order or work order line. The quantity that is replenished is based on the order demand and the replenishment item configuration; however, you can configure the application to allocate not only the replenishment quantity but any additional quantity needed to fill the pickface location to its maximum capacity, if it can be done without generating an additional pick.
-   **Replenishment**: Work type used to pick component items to fill a work order.
-   **Stage Transfer**: Work type used for stage transfer. Stage transfer is pick work generated to transfer inventory typically from a cross docking area to a staging lane.
-   **Demand Replenishment**: Work type used for demand replenishment. A demand replenishment is generated when pre-inventory allocation (PIA) is enabled, and a pick location does not have sufficient inventory to complete an order. PIA is a process in which picks are allocated from a pickface location before the necessary inventory physically exists at the location. With PIA enabled, the application generates demand replenishments from reserve storage locations to the pick location, and then generates picks based on the inventory pending to the pick location. The quantity that is replenished is based on the order demand; however, you can configure the application to allocate not only the replenishment quantity but any additional quantity needed to fill the pickface location to its maximum capacity, if it can be done without generating an additional pick.

## Event settings

You can set the Warehouse Management events that are logged in response to the corresponding WCS events. The following table is an example of the available event settings.

  
| Event Type (in the WCS) | Event (in Warehouse Management) | Description |
| --- | --- | --- |
| Cancel Pick | PICK\_CANCEL | Request to cancel an outstanding pick request of inventory (can be a single pick or a group of picks). |
| Inventory Attribute Change | INVENTORY\_ATTR\_CHANGE | Request to change an attribute of inventory. |
| Inventory Status Change | INVENTORY\_ATTR\_CHANGE | Request to change the inventory status. |
| Pallet Pick | PICK\_REQUEST | Request to pick inventory for an outbound order, work order, or replenishment (emergency, manual, top-off, demand, or trigger). |
| WCS Destination Redirect | MOVEMENT\_REQUEST | Request that a pallet be moved from a specified source location (does not include the pallet contents). |
| WCS Induction Request | INDUCTION | Request that a pallet be moved from a specified source location and includes the contents of the pallet. If Warehouse Management controls storage and picking, the destination location is specified. If the WCS determines storage and picking, the destination location is not specified. |
| WCS Label Response | LABEL\_RESPONSE | Request to communicate whether the pallet label or shipping label information was generated in response to the Label Request message, including the file name and path for the requested pallet LPN. |
| WCS Load Error | LOAD\_ERROR | Request to inform the WCS that the pallet provided in the Request transaction was not found in Warehouse Management. |
| WCS Load Request | LOAD\_DETAIL | Request for a label. If a label is required, Warehouse Management generates a label file for either a pallet label or shipping label and, through the LABEL\_RESPONSE message, makes that file available to the WCS. |

## Inventory reconciliation settings

Inventory data reconciliation is the ability to compare the inventory data in Warehouse Management to an inventory snapshot of the inventory data in the WCS. Inventory snapshots from the WCS are assumed to be the current state of the WCS. Additional configuration is required in the WCS to handle and process inventory snapshots. Inventory snapshots are not saved. For example, you can configure the following fields to include in your comparison of inventory data:

-   **Attribute**: Information expected from the WCS for use in the discrepancy comparison. The **Storage Location** and **Load Number** fields are expected and do not have to be configured.
-   **Sort Sequence**: Order in which the inventory snapshot considers the associated **Attribute** setting in the discrepancy comparison.

## Inventory movement settings

You can set the events that are logged when inventory moves within the WCS. The following table is an example of the available inventory movements.

  
| Direction | Event | Description |
| --- | --- | --- |
| Inbound | INDUCTION | Inventory moves into the WCS. |
| Within | MOVEMENT\_REQUEST | Inventory moves inside the WCS. |
| Outbound | REMOVAL | Inventory moves out of the WCS. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
