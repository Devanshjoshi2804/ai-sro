---
title: "Tags"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/tags_inbound_shipments.htm"
source: "/content/tags_inbound_shipments.htm"
toc_path:
  - "Warehouse Management"
  - "Receiving"
  - "Inbound Shipments"
  - "Tags"
sections:
  - "Inventory tags"
  - "Order and load tags"
  - "Transport equipment tags"
  - "Location tags"
images: []
source_sha1: dc903a7c2577e6efa4e78066f3db7b7ab61daf7a
---
# Tags - Inbound Shipments

Tags are displayed throughout multiple application modules and pages. Tags can relate to inventory, transport equipment, or locations. You can perform searches by entering a tag name, or by selecting it from a **Quick Filter** drop-down. For example, you can search inventory by the Hazardous tag, and only hazardous items are displayed; or you can search orders by the Short tag to view all of the orders for which inventory was allocated short.

You can also click a tag to view additional information, or in some cases, perform a task. For example, you can click a Hazardous tag to view the hazardous item, or you can click an Unassigned tag to assign a shipment to a new or existing load. If more tags apply to the equipment, inventory, or location than can be displayed, an ellipsis tag is also displayed, which you can click to view additional tags.

Tags are either displayed as red or gray. A red tag indicates a higher priority action must be performed in order to successfully process the inventory, such as resolving a short shipment. A gray tag indicates a lower priority action can be performed, such as indicating that an unassigned shipment can be assigned to a load; or it can be an informational tag (no actions needed), such as identifying inventory as hazardous.

**Note**: Some of the following tags are only displayed on certain application pages or only for inventory, equipment, or locations specific to shipping or receiving.

## Inventory tags

The application uses the following inventory tags:

-   **Components**: Indicates the components that comprise a LPN of a top-level item (finished good) in an assembly work order when the **Component Tracking** field for the work order is set to Yes. Click the tag, and click **View Components** to view the [Component fields](../../shared-functions/inventory/procedures-for-lpns.md).
-   **Consignment**: Indicates that inventory is supplier-consigned. When clicked, this tag displays information about the supplier and the consignment change point. For example, if the consignment change point is Consignment Days, then the tag displays the number of consignment days, remaining consignment days, and the consignment end date.
-   **Hazardous**: Indicates that an item is defined as hazardous material. This is used to tag LPNs, orders, or shipments that contain hazardous items.
-   **Hold**: Indicates that an item has a hold applied to it. This is used to tag LPNs that contain held inventory. You can click the tag to view all holds that are applied to a specific LPN.
-   **Hot**: Indicates that an item is hot, meaning that it is required to fulfill an outbound order that was allocated short. This is used to tag inbound shipments or transport equipment that contain hot items.
-   **Not Receivable**: Indicates that an item is not receivable. This is used to tag inbound shipments or orders that contain an item that is not receivable. An item may not be receivable because it is new or the item configuration has the **Receivable** field set to No.
-   **Not Shippable**: Indicates that inventory cannot be shipped due to a hold or inventory status that does not allow shipping. This is used to tag shipments or loads that contain inventory that is not shippable.
-   **Tolerance**: Indicates that inventory cannot be shipped as the captured catch quantity is beyond the normal tolerance limits and within the configured extreme tolerance limits. It can be shipped after a supervisor approves the catch quantity or after the catch quantity is adjusted within limits.
-   **Pending Parcel**, **In Progress Parcel**, **Failed Parcel**: Indicates the status of address validation and carrier selection required for one or more order types on the parcel shipment. See [Parcel address validation and carrier selection](../../configuration/outbound/shipping/parcel.md).
-   **Pending Move**: Indicates that directed work exists to move inventory from its current location to a new location.
-   **Picked**: Indicates that inventory has been picked. This is used to tag LPNs or loads for which at least one item has been picked.
-   **Short**: Indicates that an order line has an unfulfilled quantity (allocated short).
-   **Unassigned**: Indicates that a shipment has been picked and staged but has not been assigned to an outbound load.
-   **Restricted**: Indicates that the lot for inventory is restricted. This is used to tag LPNs with restricted lot inventory. See [Item lot restrictions](../../configuration/inventory/items/items.md).

## Order and load tags

The application uses the following tags for inbound orders, outbound orders, or loads:

-   **Auto Receive**: Indicates that an inbound shipment is eligible for auto receiving. See [ASN auto receiving from trusted suppliers](../receiving-concepts.md).
-   **ASN**: Indicates that an inbound shipment contains advanced shipment notification (ASN) information.
-   **Non-Trusted**: Indicates that an ASN is not from a trusted supplier and the item information must be verified.
-   **Notes**: Indicates that there are notes associated with an order line or load.
-   **Rush**: Indicates that an order is flagged for rush processing (**Rush Flag** set to Yes).

## Transport equipment tags

The application uses the following equipment tags:

-   **Close**: All inventory for the load associated with the transport equipment has been loaded and the equipment is ready to be closed.
-   **Dispatch**: All loading or receiving work has been completed, and the transport equipment is ready to be dispatched.
-   **Failed Safety**: An equipment safety check has been performed but failed.
-   **Late**: The transport equipment was checked in after it is scheduled appointment start time. Alternatively, if the equipment was checked in on time, this can also indicate that the appointment start time has passed, but the equipment is not at a dock door.
-   **Live**: A driver is waiting with the transport equipment.
-   **Move Pending**: Directed work has been created to move the transport equipment or inventory from its current location to another location.
-   **Notes**: Indicates that there are notes associated with the transport equipment.
-   **Over**: The appointment end time for the transport equipment has passed and the equipment has not been checked out.
-   **Safety**: An equipment safety check must be performed on the transport equipment.
-   **Suspended**: Directed work associated with the inventory or equipment has been suspended.
-   **Waiting**: The transport equipment is checked in and the associated appointment start time has passed, but the equipment is not at a dock door. This tag only applies to equipment that is also tagged as **Live**.

## Location tags

The application uses the following location tags:

-   **Access Mismatch:** Indicates that the dock access group assigned to a location does not match any of the dock access groups assigned to the type of transport equipment that is being checked in or moved to a door location. See [Dock Access Groups](../../configuration/warehouse/locations/dock-access-groups.md).
-   **Count in Progress**: Indicates that a count is in progress in a location, which makes the location unavailable for processing until the count is complete.
-   **Error**: Indicates that a location is in error and not available to be used for warehouse processing. Unlike setting a location out of service, a location is typically put in error for only a short period of time because of an inventory adjustment, for example. A location that is in error cannot be used until the error is resolved.
-   **Missing Equipment**: Indicates that during a location audit, an operator entered information that differs from the existing information in the application. For example, if the application expects a piece of transport equipment in a specific yard location and the operator does not confirm that equipment during an audit, this tag is applied to the location due to the missing equipment. This tag is only displayed on the Yard Activity page.
-   **Not Pickable**: Indicates that a storage location is not available for allocation or picking. The application assigns this tag if a location's **Pickable** configuration is set to No.
-   **Not Storable**: Indicates that a storage location is not available for putaway and storage.
-   **Out of Service**: Indicates that a location is out of service and is not available to be used for any warehouse processing. A location is typically set to be out of service because of long-term maintenance rendering the location unusable, or because the location is not efficient for storing inventory.
-   **Pending Audit**: Indicates that an audit has been generated for a yard location.
-   **Pending Count**: Indicates that a count (other than a count-back count) has been scheduled for a location, but has not yet started.
-   **Pending Replenishment**: Indicates that a replenishment exists for a location.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
