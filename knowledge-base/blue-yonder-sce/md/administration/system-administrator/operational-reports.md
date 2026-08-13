---
title: "Operational Reports"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/admin/operational_reports.htm"
source: "/content/admin/operational_reports.htm"
toc_path:
  - "Administration"
  - "System Administrator"
  - "Operational Reports"
sections:
  - "Active Work Assignment Overview"
  - "Cancelled Shorts"
  - "Demand Evaluation"
  - "Dispatch Summary"
  - "Pick Summary by Area"
  - "Pick Summary by Hour"
  - "Pick Summary by Work Zone"
  - "User Activity"
  - "Job Code Performance"
  - "User Performance Overview"
  - "Unprocessed Demand"
images: []
source_sha1: 01df798bb710befd15e52cb546b806fe960512c4
---
# Operational Reports

You use the Operational Reports menu option to access various warehouse and labor display pages that contain information you can use to proactively manage warehouse processes, troubleshoot issues before they occur, and monitor user performance. You can filter the data to display information that matches specific criteria. Additionally, each display contains a summary row, at the bottom of the grid, that shows the total quantity for each column.

## Active Work Assignment Overview

The Active Work Assignment Overview display page contains information related to the work assignments that have been started but not yet completed. You can view information such as the customer for a work assignment, its expected delivery date, and the picked quantity, among other details. This page also shows the estimated time to complete each work assignment.

**Note**: Warehouse Labor Management must be installed and integrated with Warehouse Management for the estimated time value to populate.

You can use this page to verify the remaining work assignment tasks for the shift or day, and then you can take appropriate action to ensure the assignments are completed on time. You can also track picking progress for specific customers and adjust operations based on expected delivery dates.

## Cancelled Shorts

The Cancelled Shorts display page shows information related to the orders and items that were allocated short, and for which the short allocation was cancelled. You can view information such as the user that cancelled the short and the reason for the cancellation. You can then determine the operational needs required to ensure inventory is available for other orders requiring the same inventory. This page is useful in tracking specific items that are frequently shorted and taking appropriate action to reduce the number of orders that are allocated short.

## Demand Evaluation

The Demand Evaluation display page shows information related to items that are subject to be out of stock based on the allocation demand to fulfill outbound orders. You can view the available inventory levels for the items and the expected short quantity. This page also displays the quantity of an ordered item that is in the warehouse but is on hold or unavailable, as well as the quantity that was received on the current date.

This page is useful for gathering exact inventory levels for the items that are in demand for outbound orders to assist in wave planning and order fulfillment.

## Dispatch Summary

The Dispatch Summary display page shows customer information for inventory quantities on dispatched transport equipment. You can use this page to view information such as the customer, dispatch time, and department. By default, this page displays data for the current day, but you can adjust the date range. Data is sorted by the **Dispatch Date Time** in descending order (most recent dispatch record displayed first).

## Pick Summary by Area

The Pick Summary by Area display page shows information for pending (allocated), in progress, completed, and percent completed pick work for each of the storage areas defined in the warehouse. You can use this page to view the status of an area's pick work for the current date and monitor the remaining amount of work to perform in each area. Pallet quantities are for LPN-level picks, Case quantities are for sub-LPN level picks, and Quantities are for all other UOMs. Based on this information, you can adjust operations to ensure picking assignments are completed on time.

The Directed Pickers column displays the number of operators who are performing directed pick work in each area. Undirected picking information is not included on this page.

## Pick Summary by Hour

The Pick Summary by Hour display page shows information for pending (allocated) and completed pallet (LPN level), case (sub-LPN level), and quantity (other-UOMs) picks for up to the last 15 days. You can use this page to view the hourly pick summary for the last 24 hours (by default), and to monitor the remaining amount of work to perform per hour for a specific assignment. Based on this information, you can adjust operations to ensure picking assignments are completed on time.

The Pick Summary by Hour job (PICK-SUMMARY-BY-HOUR) must be enabled and configured to run on an hourly basis. Jobs are maintained in the Console, under Jobs.

**Notes**:  

-   The **Active Pickers** field value refers to the number of users logged on to a device and performing picking tasks.
-   A pick is counted at completion, not at acknowledgment, and a pick is counted for the hour in which it is was completed. Work assignment picks are not counted until the entire work assignment is complete.
-   A completed pick is not an indicator that the pick was deposited to a staging lane or loaded; it only indicates the inventory was picked to a device.
-   Replenishment picks are not included on this display page.

## Pick Summary by Work Zone

The Pick Summary by Work Zone display page shows information for pending (allocated), in progress, completed, and percent completed pick work for each of the work zones defined in the warehouse. You can use this page to view the status of a zone's pick work for the current date and monitor the remaining amount of work to perform in each work zone. Pallet quantities are for LPN-level picks, Case quantities are for sub-LPN level picks, and Quantities are for all other UOMs. Based on this information, you can adjust operations to ensure picking assignments are completed on time.

The Directed Pickers column displays the number of operators who are performing directed pick work in each work zone. Undirected picking information is not included on this page.

## User Activity

The User Activity display page shows directed assignment details for the users that are actively performing work in the warehouse on an RF device, voice device, workstation, or mobile device. You can use this page to monitor the activity of one or more users from the start of the first assignment of a shift. This page shows the number of active users on site, assignment start and end times, and the current job for each user, among other activity details. If a user is signed on to more than one device, a record is displayed for each device until one of the sessions is ended and the user is logged out.

The User Activity display is helpful in analyzing current directed work operations to gain insight on resource utilization.

**Note**: Warehouse Labor Management must be installed and integrated with Warehouse Management before information is displayed on this page.

## Job Code Performance

The Job Code Performance display page shows information for each job that was performed in the warehouse during a specified time period. You can filter the performance data based on the assignment completion time. If no date is entered, then the page displays information for the last 24 hours. This page shows the number of picks and work tasks that were performed (per UOM) and displays the average performance of all work tasks for a job code. The performance represents whether the goal time for an assignment is being met. Performance is calculated based on the number of goal time seconds completed and the number of actual seconds operators have spent on the assignment.

**Note**: Warehouse Labor Management must be installed and integrated with Warehouse Management before information is displayed on this page.

## User Performance Overview

The User Performance Overview display page shows pick performance information for specific users by job code. You can filter the performance data based on the assignment completion time. If no date is entered, then the page displays information for the last 24 hours. This page shows the number of picks that were performed (per UOM), the amount of time users spent working on the tasks for each job code, and the calculated user performance. The performance represents whether the goal time for an assignment is being met. Performance is calculated based on the number of goal time seconds completed and the number of actual seconds operators have spent on the assignment.

**Note**: Warehouse Labor Management must be installed and integrated with Warehouse Management before information is displayed on this page.

## Unprocessed Demand

The Unprocessed Demand display page shows information related to the orders and items that are not yet processed and fulfilled. The orders displayed on this page are either not yet planned in a wave, or are included in a wave that has not been allocated. You can use this page to analyze the unprocessed demand in relation to the available inventory in the warehouse. With this information, you can then take appropriate action to effectively plan and allocate unprocessed waves according to the available inventory. When an order is allocated, it is no longer displayed on the Unprocessed Demand display page.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
