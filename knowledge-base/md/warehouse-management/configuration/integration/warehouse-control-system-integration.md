---
title: "Warehouse control system integration"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/warehouse_control_system_integration.htm"
source: "/content/warehouse_control_system_integration.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Integration"
  - "Warehouse control system integration"
sections:
  - "Add or modify a system for WCS integration standardization"
images: []
source_sha1: cb4134d352b6702ea4da03d329a72d8835d706eb
---
# Warehouse control system integration

Facilities that use automation to move pallets within their warehouses can use a warehouse control system (WCS) as the interface to control automated material handling equipment, such as an automated storage and retrieval system (ASRS), automated guided vehicle (AGV), and other field devices (for example, a manufacturing execution system (MES) or conveyor). When Warehouse Management is used for pallet level handling at a facility with a WCS, seamless integration is needed to reduce the field-driven customization, mapping, and overhead required to support different automation solutions.

The interface between Warehouse Management and a WCS is designed to use TCP sockets as the preferred communication method, and XML-based messages that are developed according to the Warehouse Management XML standards. See the Warehouse Control Standardization Integration Guide and Integrator (Supply Chain Execution) TCP Socket Emulator Configuration Guide.

This integration supports the following configuration options:

-   Warehouse Management controls the storage and picking of all inventory in the automated material handling equipment. Warehouse Management can be configured to view the automated material handling equipment as multiple locations.
-   The WCS controls the storage and picking of all inventory in the automated material handling equipment. This option is a black box model, where Warehouse Management can be configured to view the automated material handling equipment as a single, mixed location.
-   When an MES is used, information for inventory manufactured and identified in the MES can be used to reconcile work orders (if applicable), create inventory, and have pallets moved into automated storage.

To configure a Warehouse Management site to work with a WCS, you must fulfill the following prerequisites:

-   A WCS is installed and running.
-   The Warehouse Management web client is installed and the interface is running.
-   Valid connections to the Warehouse Management and WCS server installations exist.

For more information on WCS integration with warehouse processes, see [Setup tasks for WCS integration](warehouse-control-system-integration/setup-tasks-for-wcs-integration.md) and [Systems and settings for WCS integration](warehouse-control-system-integration/systems-and-settings-for-wcs-integration.md).

## Add or modify a system for WCS integration standardization

For each WCS that you are integrating with, you must add a system and define the associated settings.

1.  Select **Configuration > Integration > WCS Integration**.
2.  Perform one of the following tasks:
    -   To add a new system for WCS integration, click **Add.** The Add New WCS window is displayed.
    -   To modify an existing system for WCS integration, in the grid, click the WCS. The Modify WCS window is displayed.
3.  Enter information in the following fields:
    
     
    | Field | Description |
    | --- | --- |
    | WCS | Unique identifier assigned to the WCS. This is the identifier that the WCS uses. |
    | System | System ID for the destination system. |
    
4.  To enable cross dock functionality during WCS automated line receiving, set the **Cross Dock** field to **Yes**; otherwise, set the field to **No** to disable cross docking.
5.  To define the movement zones used by the WCS:
    1.  Click **Movement Zones**. The Movement Zones page is displayed.
    2.  In the **Available** column, select the check box next to the movement zone.
    3.  In the **Selected** column, set the **Create Putaway** field to Yes to generate a putaway.
    4.  Click **Apply**.
6.  To group pick work into a single message in transactions sent from Warehouse Management to the WCS system:
    1.  Click **Picking**. The Picking page is displayed.
    2.  In the **Available** column, select the check box next to the work type. The work type represents a basic type of work (for example, selection or putaway) performed in a facility. The work type is used to group related job codes.
    3.  In the **Selected** column, in the **Pick Grouping** column, for the selected work type, select the pick group used for the pick request messages when they are sent to Warehouse Management.
        -   **Order**: Pick requests are grouped by order when the message is sent to the WCS.
        -   **Order, Work Order**: Pick requests are grouped first by order and then by work order when the message is sent to the WCS.
        -   **Shipment**: Pick requests are grouped by shipment when the message is sent to the WCS.
        -   **Shipment, Work Order**: Pick requests are grouped first by shipment and then by work order when the message is sent to the WCS.
        -   **Wave**: Pick requests are grouped by wave when the message is sent to the WCS.
        -   **Entire WCS**: Pick requests are grouped into a single message and sent to the WCS.
        -   **No Grouping**: Pick requests are sent individually to the WCS.
    4.  Click **Apply**.
7.  To configure events that will be logged when an activity occurs in the WCS:
    1.  Click **Events**. The Events page is displayed.
    2.  In the **Available** column, select the check box next to the WCS event type that you want to configure.
    3.  In the **Selected** column, in the **Event** column, choose the name of the Warehouse Management event.
    4.  Click **Apply**.
8.  To configure fields that WCS system provides in an inventory snapshot to Warehouse Management:
    1.  Click **Inventory Reconciliation**. The Inventory Reconciliation page is displayed.
    2.  In the **Available** column, select the check box next to the WCS inventory attribute that must be included in the snapshot.
    3.  In the **Selected** column, in the **Sort Sequence** column, specify the order in which the inventory snapshot considers the associated attribute setting in the discrepancy comparison.
    4.  Click **Apply**.
9.  To configure integrator events that are logged when inventory is moved into, within, or out of the WCS system:
    1.  Click **Move Inventory**. The Move Inventory page is displayed.
    2.  In the **Available** column, select the check box next to the move direction. This indicates how inventory moves in relation to the WCS. The descriptions are given below:
        -   **Inbound**: Any movement between a source and the destination where destination is in the WCS, and not in the source.
        -   **Outbound**: Any movement between a source and the destination where the source is in the WCS, and not in the destination.
        -   **Within**: Any movement between a source and destination where both the source and destination are in the WCS.
    3.  Under **Selected**, in the **Event** column, select the name of the event. An event is a defined occurrence that triggers a transaction. The occurrence of an event causes integrator to gather data from the triggering system's database or from an inbound IFD for communication to a target system.
    4.  Click **Apply.**
10.  Click **Save.**

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
