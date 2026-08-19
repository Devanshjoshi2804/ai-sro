---
title: "Production Lines"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/production_lines.htm"
source: "/content/production_lines.htm"
toc_path:
  - "Warehouse Management"
  - "Production"
  - "Production Lines"
sections:
  - "Assign a work order to a production line"
  - "Unassign a work order from a production line"
  - "View production line information"
  - "View detailed work order information"
  - "Production Line fields"
images: []
source_sha1: d124ef1f6b769a47d7f891fb81bd706ea62e4e0b
---
# Production Lines

The Production Lines page provides visibility to the production lines that are created within the facility. The Production Lines page also displays summary information relating to the production lines, work orders, and associated picks. For example, you can view the number of production lines in use and the number of work orders in progress. You can click the following summary values to view the related information:

-   **Lines in Use**: Filters the page to display the production lines that are currently in use. Depending on the production line configurations for the facility, a single line may be used to process multiple work orders at once.
-   **Lines Not in Use**: Filters the page to display the production lines that are currently not in use.
-   **Work Orders Pending**: Displays the Work Orders page to show the work orders for which the inventory has not been allocated.
-   **Work Orders in Progress**: Displays the Work Orders page to show the work orders that are in process.

You can expand a production line to display the work orders assigned to the line, and you can click a production line to view the line details and perform additional tasks.

## Assign a work order to a production line

You can assign one or more work orders to a production line.

1.  Select **Production > Production Lines**.
2.  In the grid, click the production line. The production line details are displayed.
3.  From the **Actions** drop-down list, select **Assign Work Order**. The Assign Work Order window is displayed.
4.  In the grid, select the work order that you want to assign to the production line.
5.  Click **Save**. The Priority window is displayed.
6.  Enter the priority at which the work order will be processed in relation to other work orders assigned to the production line. Processing priority numbers range from 1 to 9 with 1 being the highest priority.
7.  Click **OK**.

## Unassign a work order from a production line

You can unassign one or more work orders from a production line.

1.  Select **Production > Production Lines**.
2.  In the grid, click the production line from which to unassign work orders. The production line details are displayed.
3.  In the grid, select the check box next to the work order to unassign.
4.  From the **Actions** drop-down list, select **Unassign Work Order**. The Unassign Work Orders window is displayed.
5.  Click **Yes** to remove the selected work order from the production line.

## View production line information

1.  Select **Production > Production Lines**, and then in the grid, click a production line.
2.  View information in the [Production Line fields](#Production_Line_fields).
    
    **Note**: The production line header displays the number of work orders assigned to the line, the plan type (which identifies how work is to be scheduled for the production line), the line's processing area, and the production lines's staging location.
    

## View detailed work order information

1.  Perform one of the following tasks:
    -   Select **Production > Production Lines**, then expand or click a production line, and then in the grid, click a work order.
    -   Select **Production > Work Orders**, and then in the grid, click a work order.
2.  View information in the [Work Order detail fields](work-orders/procedures-for-work-orders.md).
3.  To view general information about the work order, select **Summary**, and view information in the [Summary fields](work-orders/procedures-for-work-orders.md).
4.  To view the component level details, select **Order Lines**, and view information in the [Order Lines fields](work-orders/procedures-for-work-orders.md).
5.  To view pick work for the work order, select **Picks**, and view information in the [Picks fields](work-orders/procedures-for-work-orders.md).
6.  To view work order lines that were generated short, select **Shorts,** and view information in the [Shorts fields](work-orders/procedures-for-work-orders.md).
7.  To view replenishment pick work for the work order, select **Pending Replens**, and view information in the [Pending Replenishment fields](work-orders/procedures-for-work-orders.md).
8.  To view cross docking work for the work order, select **Cross Dock**, and view information in the [Cross Dock fields](work-orders/procedures-for-work-orders.md).
9.  To view completed pick work, select **Picked**, and view information in the Picked and Produced fields. See [Picked and Produced field listings](work-orders/procedures-for-work-orders.md). Click an LPN to view the LPN details. See [View detailed LPN information](../shared-functions/inventory/procedures-for-lpns.md).
10.  To view the finished items in the production line, select **Produced**, and view information in the Picked and Produced fields. See [Picked and Produced field listings](work-orders/procedures-for-work-orders.md). Click an LPN to view the LPN details. See [View detailed LPN information](../shared-functions/inventory/procedures-for-lpns.md).
11.  To view shipments and orders that are to be fulfilled with the work order's top-level item or component items, select **Waiting Orders**, and view information in the [Waiting Orders fields](work-orders/procedures-for-work-orders.md).

## Production Line fields

 
| Field | Description |
| --- | --- |
| Production Line | Name of the production line. A production line is an arrangement of machines or sequence of operations (production stations) involved with the assembly or disassembly of top-level item. |
| Current Item | Item that is currently being assembled or disassembled on the production line. |
| Next Item | Item that will be assembled or disassembled after the current item's processing is complete. |
| Processing Status | Processing status of the production line.<br>-   • **Not Usable**: The production line is not currently available.
<br>-   • **Unassigned**: No work orders are assigned to the production line.
<br>-   • **Assigned**: A work order is assigned to the production line, but the work order has not yet been started.
<br>-   • **Started**: A work order on the production line has been started, but none of the component items (assembly) or top-level items (disassembly) for the started work order have been delivered to the production line.
<br>-   • **Partially Delivered**: Some of the component items (assembly) or top-level items (disassembly) for a work order have been delivered to the production line.
<br>-   • **Ready**: Enough component items for an assembly work order have been delivered to the production line to begin building and identifying the work order's top-level item.
<br>-   • **Completely Delivered**: All of the component items (assembly) or top-level items (disassembly) for a work order have been delivered to the production line.
<br>-   • **Production In-Process**: At least one top-level item for an assembly work order has been identified off of the production line. For disassembly work orders, at least one component item has been identified from the top-level item that is being disassembled.
<br>-   • **Complete**: All of the top-level items for at least one of the started work orders are completely identified, but the work order has not yet been completed. For disassembly work orders, all of the component items for at least one of the started work orders are completely identified, but the work order has not yet been completed. |
| Plan Type | Option that identifies how work is to be scheduled for the production line.<br>-   • **Schedule**: Processes work orders based on the scheduled begin and end dates defined for the work order.
<br>-   • **Sequence**: Processes work orders in sequential order based on the plan sequence defined for the work order.
<br>-   • **Priority**: Processes work orders based on the processing priority defined for the work order. |
| Work Orders | Number of assigned work orders in the production line. |
| Produced | Percentage of top-level items that have been assembled or disassembled relative to the total expected quantity for the work orders assigned to the production line. Additionally, an X of Y value displays the number of top-level items assembled or disassembled out of the total expected quantity; for example, (50 of 100). |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
