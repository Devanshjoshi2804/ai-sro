---
title: "Yard concepts"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/yard_concepts.htm"
source: "/content/yard_concepts.htm"
toc_path:
  - "Warehouse Management"
  - "Yard"
  - "Yard concepts"
sections:
  - "Locations"
  - "Yard and door audits"
  - "Transport equipment properties"
  - "Transport equipment movements"
  - "Dock status"
  - "Location status"
  - "Transport equipment status"
  - "Yard status"
  - "Tractor status"
images: []
source_sha1: 2a94092841705abdf43b4d342fc4903a36a18158
---
# Yard concepts

You use the Yard module to manage the people, equipment, and inventory involved in yard processes. You can make adjustments to inventory, work, locations, and other factors that can improve the productivity and efficiency of warehouse yard activities.

## Locations

A yard is the area outside a warehouse where transport equipment and tractors are stored. Transport equipment and tractors are checked in to the yard when they arrive at the warehouse and are checked out when they leave. A yard consists of the following locations:

-   **Yards**: A yard location is an outdoor space in which transport equipment (used to receive, ship, and store product) and tractors can be stored or temporarily parked until they are either moved to a dock door or checked out from the yard.
-   **Dock doors**: A dock door location is an opening on the dock where transport equipment can be parked for the purpose of loading or unloading.

The application tracks transport equipment properties and allows you to manage and monitor their movement around the yard.

A status is a visual cue used to indicate conditions and provide other information (such as whether equipment is available for use) that helps you manage activities within the yard.

## Yard and door audits

You can request a yard or dock door (location) audit to verify that your yard information is accurate. For example, you can determine whether a yard or door location is empty or full, or whether specified transport equipment is actually parked in a location.

**Note**: You cannot use location audits to audit the inventory that is on transport equipment. Additionally, you cannot use audits to confirm whether the tractors assigned to transport equipment are actually parked in a location.

Audits are requested at a workstation and sent to the work queue to be distributed to and performed by RF operators in the yard. When RF operators perform an audit, they are required to confirm transport equipment in the audit locations, or verify that a location is empty. If expected equipment is not found in an audit location, the application applies the Missing Equipment tag to the location.

If a location fails an audit, you can reconcile the audit by updating the equipment's actual location in the application.

You can view scheduled audits on the [Work Queue](../shared-functions/work-queue.md) page, and you can view audit results on the [History](../shared-functions/history.md) page (**Inventory** tab).

## Transport equipment properties

The application tracks transport equipment properties. Transport equipment properties distinguish a piece of transport equipment, and can be entered or modified each time the equipment is checked in to the yard. Examples of transport equipment properties include the equipment number, code, type, and size.

-   When defining or modifying receiving transport equipment, you can indicate that the equipment will be turned around after incoming inventory is received and then used as shipping transport equipment. In addition, you can add or modify the inbound shipment information for the incoming inventory on the equipment.
-   When defining or modifying shipping transport equipment, you can assign it to a specific outbound load. You can then define which stops will be loaded onto the equipment.
-   When defining or modifying storage transport equipment, you can convert the storage equipment to shipping transport equipment. See [Convert storage transport equipment to shipping equipment](../shared-functions/transport-equipment/procedures-for-transport-equipment.md).

In addition, when you define transport equipment properties, you can add notes that provide additional status information and identify any unique circumstances that affect how the equipment is handled. For example, you can indicate that a trailer contains inbound or outbound product, is empty and ready to be picked up or loaded, and is assigned to a specific outbound load or dock door.

**Note**: The notes that you include for transport equipment are not displayed on RF screens nor do they affect any other area of the application.

## Transport equipment movements

You can manage and monitor the movement of transport equipment within a yard. The typical flow of activity in a yard includes moving transport equipment from yard locations to dock doors and back again.

A move request can be performed immediately or sent to the work queue and distributed to yard workers as RF directed work. Immediate moves are typically performed to confirm a transport equipment move; that is, they are performed when the transport equipment has already been moved, and you want to update the equipment's location in the application. For example, the dock manager notifies a yard jockey to move the transport equipment; after the equipment is moved, the yard jockey notifies the dock manager who updates the equipment's location in the application.

When moving a piece of transport equipment to or from a dock door, an operator may be prompted to perform workflows. See [Warehouse Workflows](../configuration/work/warehouse-workflows.md).

## Dock status

A dock status is assigned by the application to indicate whether there is transport equipment parked at the dock door. Since a door can be occupied by only one piece of transport equipment at a time, it can have one of the following statuses:

-   **Empty**: Indicates that there is no transport equipment checked in to the door.
-   **Full**: Indicates that transport equipment is checked in to the door.
-   **Pending**: Indicates that transport equipment is in the process of being moved either to or from the door. This status is displayed when the work is created to move a piece of transport equipment to or from a door but the work has yet to be completed.

## Location status

A location status, as it refers to a yard location, is assigned by the application and is based on the movement of transport equipment in and out of yard locations. The following are the standard yard location statuses:

-   **Empty**: Indicates that there is not transport equipment in the yard location.
-   **Full**: Indicates that the yard location has reached its maximum capacity as defined in the web client.
-   **Partially Full**: Indicates that there is transport equipment in the location but it is not filled to capacity.

## Transport equipment status

The application assigns statuses to transport equipment primarily for identifying the condition of the equipment in relation to the shipping and receiving processes. The following are standard transport equipment statuses:

-   **Expected**: Receiving, shipping, or storage transport equipment that is expected to arrive at the facility, but has not yet been checked in.
-   **Checked In**: Receiving or shipping transport equipment that is parked in a yard location and is waiting to be moved to a dock door so that receiving or unloading can begin.
-   **Open For Receiving**: Receiving transport equipment that is located at a dock door and is ready to be unloaded. Receiving has not yet begun.
-   **Receiving**: Receiving transport equipment that is parked at a dock door, and operators have started to identify and put the incoming inventory away.
-   **Open For Shipping**: Shipping transport equipment that is parked at a dock door and is ready to be loaded. Loading has not begun.
-   **Open For Loading**: Storage transport equipment that has been checked in and parked at a dock door and is ready to be loaded. Loading has not begun.
-   **Loading**: Shipping or storage transport equipment that is parked at a dock door, and operators have started to load the stops or move inventory onto the equipment. Or, work has been assigned to an RF operator to begin loading.
-   **Suspended**: Transport equipment has been moved from a dock door to a yard location after receiving or loading was started but not completed. When transport equipment has a Suspended status, receiving and loading work is put on hold. To begin receiving and loading again, the equipment must be moved back to a dock door location.
-   **Loaded**: Identifies a piece of transport equipment for which all shipments have been loaded. The equipment has not been closed or dispatched.
-   **Closed**: The transport equipment is loaded and is ready for dispatch (for shipping equipment), receiving has been completed on the transport equipment and the equipment is ready for dispatch (for receiving equipment), or storage equipment that has been loaded.
-   **Dispatched**: Identifies a piece of shipping or receiving transport equipment for which all loading or receiving has been completed, and that has been closed and departed from your facility.
-   **Pending From** or **Pending To Location**: Identifies a piece of transport equipment for which work has been created to move the equipment from one dock or yard location to another dock or yard location.

## Yard status

A yard status is a user-maintained status that is typically used to track the condition of a piece of transport equipment in the yard. You can also include notes to provide additional status information. They do not have an effect on any application processes.

The following are the standard pre-defined yard statuses:

-   Full
-   Empty
-   Out of Service
-   Assigned

You can redefine these codes to accurately reflect the activity in your yard. Yard status codes are defined using the yard\_stat column in Code Maintenance-Supervisor.

## Tractor status

The application assigns a status to a tractor based on the state of the tractor as it relates to its movements during the shipping and receiving processes. A status can be applied to standalone tractors or to tractors assigned to receiving, shipping, or storage transport equipment. A tractor can be in one of the following statuses:

-   **Expected**: The tractor is expected to arrive at the facility, or has arrived at the facility, but has not yet been checked in.
-   **At Site**: The tractor is checked in to the yard.
-   **Dispatched**: The tractor has been checked out of the yard and is no longer tracked by the application.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
