---
title: "Dashboard"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/dashboard_inventory.htm"
source: "/content/dashboard_inventory.htm"
toc_path:
  - "Warehouse Management"
  - "Inventory"
  - "Dashboard"
sections:
  - "Monitor inventory issues on the dashboard"
  - "Monitor inventory holds on the dashboard"
  - "Monitor inventory counts on the dashboard"
  - "Monitor inventory adjustments on the dashboard"
  - "Monitor storage zone utilization on the dashboard"
images: []
source_sha1: f4beebf0b3354421c7c424d59dc6e4b14cc399b7
---
# Dashboard - Inventory

You use the Dashboard to monitor the current status of inventory issues, the impact of warehouse activities on space utilization and inventory accuracy, and the progress of counting activities against the day's goals.

The dashboard displays a summary view of the most important metrics for inventory issues, holds, counts, adjustments, and utilization. Each heading can be clicked to display a detailed view of relevant metrics for the specified inventory issues, holds, counts, adjustments, or utilization category.

Specifically, the Dashboard displays the following information:

-   **Inventory issues**: Inventory issues are problems that prevent inventory from being received, put away, allocated, or picked. The dashboard displays summary information for the most significant issues and the amount of inventory affected by those issues. When you click the Inventory Issues heading, additional details for each inventory issue are displayed, including the top items, locations, and clients affected by the issue. You can click an inventory issue to access the Inventory Issues page where you can obtain item, location, and LPN information, as well as perform actions to resolve the issue.

-   **Holds**: A hold is an attribute of inventory that indicates the inventory is not available for use or distribution. The dashboard displays summary information for the highest severity holds and the amount of inventory affected by each type. When you click the Holds heading, the active holds, and the inbound and outbound orders affected by inventory on hold are displayed. You can click any of those headings to display a window that provides further details.

-   **Counts**: An inventory count is used to determine whether the actual quantities of physical inventory in a location match the logical quantity calculated by the application. The dashboard displays an overview of counts in progress that you can limit by selected criteria.

-   **Adjustments**: An inventory adjustment is a process by which a user adjusts the logical quantities of inventory in a location. If the adjustment exceeds a configured limit, then a supervisor approval is required before the application will process the adjustment. The dashboard displays an overview of costs and quantities resulting from manual inventory adjustments, and enables you to limit the display by selected criteria.
-   **Utilization**: Utilization represents the amount of storage space currently being utilized in relation to the amount of space available. The dashboard displays a graph that shows the percentage of storage space currently being used, opportunities for consolidating inventory into fewer locations, and details on space utilization by storage zone and location.

## Monitor inventory issues on the dashboard

You use the Inventory Dashboard to view inventory issues and obtain details on the locations, items, clients, reasons, expiration details, and users associated with an issue, as well as to view the dates on which date-tracked inventory will expire.

**Notes**:

-   The dashboard displays the UOM for inventory in cases, except for not receivable issues, which is in eaches.
-   The dashboard does not display pop-ups or links to the Inventory Issues page for not receivable inventory issues and out of position issues.

1.  Select **Inventory > Dashboard**. The Dashboard page displays the number of LPNs and quantities for the top two issue types based on the highest values.
2.  If **Expiring** is displayed as one of the top two issues in the summary view, from the drop-down list, select a value to view inventory that will expire in the next 30, 60, or 90 days.
3.  On the Dashboard, click the **Inventory Issues** column heading. The list of issues is displayed, along with the quantities affected by each issue.
4.  Perform one or more of the following tasks:
    -   Click **Not Pickable**. The display shows the top reasons, clients, and items affected by inventory that is required for an order but is not pickable.
    
    **Note**: Some grids contain values that you can click to view additional details, or a link that you can click to view all inventory associated with the issue. See the [Inventory](../shared-functions/inventory.md) page.
    
    -   Click **Not Shippable**. The display shows the top reasons, customers, and items affected by inventory that is required for an order but is not shippable.
    -   Click **Expiring**. A calendar is displayed showing the number of LPNs that will expire on each date in a month. Use the drop-down list to limit the display to view inventory that will expire in the next 30, 60, or 90 days.
    
    **Note**: When the calendar is displayed, you can click a number to view the details of the LPNs that are going to expire.
    
    -   Click **Not Receivable**. The display shows the top items and clients affected by inventory that was scanned but could not be received.
    -   Click **Locations in Error**. The display shows the top locations that are in the inventory error status.
    -   Click **Out of Position**. The display shows the ABC classifications, velocities, and velocity changes affected by inventory that is incompatible with its current storage location.
    -   Click **Mixing Violations**. The display shows the top locations and clients affected by inventory that is incompatible with other inventory in the same location.
    -   Click **No Location**. The display shows the top reasons, clients, and items affected by inventory for which no storage location could be found.
    -   Click **Overrides**. The display shows the top reasons, users, items, and clients affected by inventory that was deposited to a location other than the application-directed location.
    -   Click **Damaged**. The display shows the top reasons, users, items, and clients affected by inventory that was received or changed to a damage status. It also displays the list of items that were set to damaged status in the particular day.

## Monitor inventory holds on the dashboard

You use the Inventory Dashboard to view information on holds and obtain details on the orders that are affected by inventory on hold.

1.  Select **Inventory > Dashboard**. The Dashboard page displays the number of holds for the top two severity levels and the inventory quantities that are on hold.
2.  On the Dashboard, click the **Holds** column heading. The following information is displayed:
    -   **Active Holds**: Total number of orders, LPNs, and quantities affected by holds placed on inventory in the warehouse, and a breakdown of those values by hold type.
    -   **Outbound Orders Affected**: Total number of outbound orders affected by holds currently in place, along with the following metrics:
        -   **Not Shippable Orders**: Total number of orders that have been allocated but cannot be shipped because a hold that prevents shipping exists for all or a portion of the inventory on the order.
        -   **Orders Pending Allocation**: Total number of orders that cannot be allocated or shipped because a hold that prevents allocation exists for all or a portion of the inventory on the order.
        -   **Picked**: Quantity of inventory on hold that has been picked.
        -   **Staged**: Quantity of inventory on hold that has been staged.
        -   **Loaded**: Quantity of inventory on hold that has been loaded.
        
        **Note**: An outbound order affected by an active hold can be both pending allocation and unshippable. Therefore, the value for **Outbound Orders Affected** is not necessarily the sum of the values for **Unshippable Orders** and **Orders Pending Allocation**.
        
    -   **Inbound Orders Affected:** Total number of planned inbound orders that contain inventory to which a hold will be assigned during receiving.
3.  To view the severity of the active holds:
    1.  Click **Active Holds**. A window is displayed that lists the severity of each active hold.
    2.  To view all active holds, click **View all Active Holds.**
4.  To view the details of an active holds:
    1.  Under **Active Holds**, click a hold type. A window displays the name of the hold, reason for the hold, number of LPNs and locations affected by the hold, and whether the hold allows shipping and allocation, or applies to inbound inventory.
    2.  To view all inventory to which the hold applies, click **View all holds of this type**.
5.  To view the details of outbound orders affected by holds, under **Outbound Orders Affected**, click a value. A window is displayed showing the details.
6.  To view details about inbound orders affected by holds, click **Inbound Orders Affected.** A window is displayed showing the hold and number of planned inbound orders to which the hold is applied.

## Monitor inventory counts on the dashboard

You use the Inventory Dashboard to view information on current and pending counts, and limit the display of information by type of count, count zone, and/or date range.

1.  Select **Inventory > Dashboard**. The Dashboard page displays the following Counts information:
    -   **Blocking Outbound**: Number of orders and quantities that cannot be processed because of counts or approvals in process.
    -   **Priority Counts:** Number of pending counts based on the selected range for priority that is assigned to the counts.
    
    **Note**: Use the drop-down list under **Priority Counts** to select the range for displaying the number of counts based on priority.
    
2.  On the Dashboard, click the **Counts** column heading. The **Today's Counts** area displays the following count details for the selected zone and date range:
    -   **All Counts:** Total number of counts that are scheduled. Select a count type from the drop-down list to display the number of counts by each count type. Clicking on the number of counts displays the counts in the Counts page.
    -   **Cancel Pick Count**: Number of counts pending as a result of cancelled picks.
    -   **ABC Progress**: Number of counts for the current day that are scheduled and completed.
    -   **All Counts**: Total number of ABC and non-ABC counts that are scheduled during the selected date range. The drop-down list displays the following options:
        -   **ABC Counts**: Number of automatically scheduled counts for the selected count zone and date range.
        -   **Non-ABC Counts**: Number of manually scheduled counts for the selected count zone and date range.
    -   **Accuracy**: Overall accuracy of counts for the selected count type, count zone, and date range. The accuracy is represented by the percentage of counts that were correct, and the quantity and monetary net gain or loss of inventory.
    
    **Note**: Use the count type and count zone drop-down lists, and the date/time field to select the count type, count zone, and date, relative date or date range for displaying the accuracy and bar chart data.
    
    -   **Bar chart**: Displays inventory gains/losses for each workday for the selected count type, count zone, and date range. The bars are grouped by work week. An individual bar in the chart represents the number of counts performed that day; blue represents accurate counts and red represents inaccurate counts. The line graph plots quantity gained (green), quantity lost (red), and ABC estimate (gray) during a count on that day.
3.  To view counts for a specific day, in the bar chart, click a bar. A window displays inventory gains and losses, the net discrepancy between the gain and loss, and the total discrepancy for the selected day. Each metric displays the counts, inventory quantities, and monetary value for the metric. To view count details, in the window, click **View details**.

## Monitor inventory adjustments on the dashboard

You use the Inventory Dashboard to view information on inventory adjustments that are pending, approved, completed, and rejected. Quantity and monetary values show the impact on inventory gains and losses.

1.  Select **Inventory > Dashboard**. The Dashboard page displays the following Adjustments information:
    -   **Pending Approvals**: Total number of manual adjustments that require supervisor approval to be completed, and the inventory quantity associated with the adjustment.
    -   **Today's Net Adjustments**: Net cost (gain/loss) or cases of the day's manual adjustments that have been completed. The net value represents the results of the inventory adjustments (gains and losses) that were recorded. A gain represents inventory that was adjusted in, and a loss represents inventory that was adjusted out. Select a value from the drop-down list to display the adjustment value in cost or cases.
2.  On the Dashboard, click the **Adjustments** column heading. The **Today's Adjustments** area displays the following information:
    -   **Approved**: Total number of manual adjustments that required approval and were approved.
    -   **Rejected**: Total number of manual adjustments that required approval but were rejected.
    -   **Most Frequent**: Item most frequently adjusted and number of adjustments for that item.
    -   **Reason**: Most frequent reason for which inventory was manually adjusted and number of adjustments for that reason.
    -   **Adjustment History**: Total number of adjustments, inventory quantities, and cost of adjustments that were performed during the selected date range.
    
    **Note**: You use the date field to select a date, relative date, or date range for displaying the adjustment history and bar chart data.
    
    -   **Bar chart**: Displays the quantity of adjusted inventory for each workday, and whether the adjustment represented adding (blue) or deleting (red) inventory quantities.
3.  To view adjustments for a specific day, in the bar chart, click a bar. A window displays inventory gains and losses, the discrepancy between the gains and losses, and the total discrepancy for the day selected.

## Monitor storage zone utilization on the dashboard

You use the Inventory Dashboard to view information on space utilization in your warehouse and to determine whether opportunities exist for consolidating inventory from multiple locations into one location. A consolidation opportunity exists when multiple locations containing the same item are partially full. By consolidating, you can store all the inventory in fewer locations, which allows empty locations to be used for other items.

1.  Select **Inventory > Dashboard**. The Dashboard page displays the percentage of the warehouse that is currently being utilized for storage.
2.  Click **Utilization**. The **Utilization by Zone** area displays the following information:
    -   **Bar chart**: Displays a bar representing utilization for each storage zone. Each bar contains color coding that represents one of the following statuses:
        -   **Full (Dark blue)**: Percentage of locations within the zone that are full.
        -   **Partial (Light blue)**: Percentage of locations within the zone that are partially full.
        -   **Empty (Gray)**: Percentage of locations within the zone that contain no inventory at all.
        -   **Location Overage (Yellow)**: Percentage of locations within the zone that are over capacity.
        -   **Zone Overage (Red)**: Percentage at which the entire zone is over capacity.
        
        **Note**: Zone overage is a percentage over all locations that are over capacity. For example, if the zone is completely full (no empty or partial locations), and the locations that are over capacity are 10% over capacity, the entire zone is 10% over capacity.
        
    -   **Pie chart**: Displays a color-coded circular graph that represents an overview of the utilization for all locations within a selected zone.
3.  To view the utilization of locations in a storage zone, click a bar in the bar chart. The pie chart displays the information.
4.  To view utilization percentages for locations in a zone, click the section of the pie chart that represents the utilization percent you want to view. A window displays the locations within the range you selected.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
