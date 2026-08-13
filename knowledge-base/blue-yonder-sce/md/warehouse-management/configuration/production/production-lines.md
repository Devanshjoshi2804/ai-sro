---
title: "Production Lines"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/production_lines_config.htm"
source: "/content/production_lines_config.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Production"
  - "Production Lines"
sections:
  - "Production stations"
  - "Add or modify a production line"
  - "Delete a production line"
  - "Production Line fields"
images: []
source_sha1: 55f4cdb065fa0f5ce3d8d7d60488d27b47d7e2bc
---
# Production Lines - Configuration

A production line is an arrangement of machines or sequence of operations (production stations) involved with a single production or disassembly process. The production process assembles components into a top-level item (finished product). The finished product is then received into the warehouse from the production line at which it is built. The disassembly process disassembles top-level items and reduces them into component items. The component items are then received and either put away or used to fulfill another order or work order.

You can indicate that a production line can be occupied exclusively by one work order at a time or allow it to be shared by multiple work orders simultaneously.

You can also set up a staging location for a production line. A staging location can be shared by multiple work orders. You can also specify different delivery points (staging locations or production stations) for components on a production line.

If Warehouse Labor Management is integrated with Warehouse Management, you can specify the labor attributes for each work order. Alternatively, you can define the attributes once for the production line to have the labor values defaulted to each work order that is assigned to the production line.

## Production stations

A production station is a location on a production line where a specific operation is performed during the assembly or disassembly of the top-level item (finished good). Production stations provide the ability to incrementally build or disassemble a top-level item. A production line can be configured to contain one or more production stations. Production stations can be specified as the destination location for delivery of product associated with a work order or bill of material (BOM). This enables you to configure the application to direct operators to deposit different items at different points along the production line at which the item is physically used.

You can also assign a staging location to a production station. When the component or top-level inventory is needed (depending on the work order type), operators use the transfer functionality to move the inventory from the staging location to the production station.

A workflow can be configured to be performed at a production station. The workflow can be further configured so that activities for the production station workflow can be sent to an integrated instance of Warehouse Labor Management.

Production stations associated with non-exclusive production lines can be shared at the same time by multiple work order details belonging to multiple non-exclusive work orders. Production stations associated with exclusive production lines or the details of exclusive work orders cannot be shared at the same time with multiple work order details. A production station can be, but does not have to be, associated with a work order detail.

Production stations do not have to be in the same work-in-process area as their associated production line. This lets the production line (group of production stations) function as if it spans multiple work-in-process areas in the same or a different building even though the production line itself is assigned to only one work-in-process area. See [Production Locations](../warehouse/locations/production-locations.md).

## Add or modify a production line

Before you can add a production line, you must have defined the work-in-process area in which the production line is located. See [Areas](../warehouse/areas.md).

1.  Select **Configuration > Outbound > Production > Production Lines**.
2.  Perform one of the following tasks:
    -   To add a production line, click **Add**.
    -   To modify a production line, in the grid, click the production line.
    -   To copy a production line, in the grid, select the check box next to the production line, and then click **Copy**.
3.  Enter information in the [Production Line fields](#Production_Line_fields).
4.  To assign production stations to the production line:
    1.  Click **Production Stations**.
    2.  In the **Available** column, select the check box next to the production stations that apply.
    3.  In the **Selected** column, under **Staging Location**, select a staging location for the production station.
    4.  Click **Apply**.
5.  Click **Save**.

## Delete a production line

You cannot delete a production line if there are work orders in process on the line or if there is inventory associated with any of the production stations assigned to the line.

1.  Select **Configuration > Outbound > Production > Production Lines**.
2.  In the grid, select the check box next to the production line to delete.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Production Line fields

 
| Field | Description |
| --- | --- |
| Production Line | Name of the production line. A production line is an arrangement of machines or sequence of operations (production stations) involved with the assembly or disassembly of top-level item. |
| Plan Type | Option that identifies how work is to be scheduled for the production line.<br>-   • **Schedule**: Processes work orders based on the scheduled begin and end dates defined for the work order.
<br>-   • **Sequence**: Processes work orders in sequential order based on the plan sequence defined for the work order.
<br>-   • **Priority**: Processes work orders based on the processing priority defined for the work order. |
| Exclusive Work Order | If Yes, the production line allows only one started work order at a time. An exclusive production line is useful in a situation where there is a complex production line setup or the risk of mixing similar components for multiple work orders.<br > If No, the production line allows more than one started work order at the same time. A non-exclusive production line is useful in situations where it is possible and more efficient to work on multiple work orders simultaneously. |
| Production Area | Area in which the production line is located. |
| Staging Location | Location in which component inventory used to supply the production line is temporarily deposited prior to being moved to the production line for use in building or disassembling a top-level item to fill a work order. |
| Machine Speed | Number of finished goods (top-level items) produced or disassembled per hour. Only available if Warehouse Labor Management is integrated with Warehouse Management. |
| Activity | Code that defines the specific activity being performed to build or disassemble top-level items on the production line. Only available if Warehouse Labor Management is integrated with Warehouse Management. |
| Number of People | Number of people that will be working on the production line. Only available if Warehouse Labor Management is integrated with Warehouse Management. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
