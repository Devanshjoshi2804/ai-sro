---
title: "Dashboard"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/dashboard_receiving.htm"
source: "/content/dashboard_receiving.htm"
toc_path:
  - "Warehouse Management"
  - "Receiving"
  - "Dashboard"
sections:
  - "Monitor receiving issues on the dashboard"
  - "Monitor staging lanes on the receiving dashboard"
  - "Monitor doors on the dashboard"
  - "Monitor appointments on the receiving dashboard"
  - "Monitor receiving progress on the dashboard"
images:
  - "/content/resources/images/image430108.png"
  - "/content/resources/images/image430109.png"
source_sha1: 08cfb186fc98f3efa0d180cf3ff81a772d828cd0
---
# Dashboard - Receiving

You use the Dashboard to monitor the information relevant to warehouse receiving operations. The dashboard provides a high-level overview of the day's current and expected activities, so you can quickly assess the progress and status of receiving operations.

Specifically, the Dashboard displays the following information:

-   **Receiving Issues:** Receiving issues are the problems that prevent inventory from being received or stored. This area of the dashboard displays the number of hot items and related inbound shipments, the items that are not receivable or have no location, as well as the number of supplier or carrier inbound quality issues. You use the drop-down list to select the system equivalent UOM (Eaches, Cases, or Pallets) in which to display the inventory affected by other issues.
    
    **Note**: The values in the **View By** drop-down list (displayed next to Receiving Issues and Progress) represent the system equivalent UOMs, as defined on the item footprint, for Pallet and Case. "Pallets" represents the LPN level; "Cases" represents the sub-LPN level; and "Eaches" represents the detail LPN level (the lowest UOM defined on the item footprint). For example, if you select Pallets, the application looks for the pallet-equivalent LPN level (LPN) UOM defined on the item footprint to determine quantity. If you select Cases, quantities are displayed based on the case-equivalent LPN level (sub-LPN) UOM defined on the item footprint. The application rounds inventory to the UOM selected in the **View By** drop-down list. For example, assume a partial pallet of 5 cases is received as damaged. If you select Cases from the drop-down, then the quantity displayed is 5; however, if you select Pallets, then the displayed quantity is 1, even though the quantity is less than a full LPN.
    
-   **Staging Lanes**: The number of items per unit of measure (UOM) that currently reside in a receiving staging lane. The progress bar displays the number of receiving staging lanes currently in use.
-   **Doors**: The number of inbound shipments for which a driver is waiting with the transport equipment, and the number of pieces of equipment ready to be dispatched. The progress bar displays the number of receiving dock doors currently in use.
-   **Appointments**: The number of appointments that are waiting to be checked in, late to arrive, or late to depart. The progress bar displays the number of appointments that have arrived (been checked in) out of the total number of expected inbound appointments for the current date.
-   **Progress**: The progress area displays a line graph that shows the amount of inventory that is expected as well as inventory that has been received and stored over the displayed range of time. You use the drop-down list to select the system equivalent UOM (Eaches, Cases, or Pallets) in which to display the inventory affected by other issues.

## Monitor receiving issues on the dashboard

The Receiving Dashboard displays the receiving issues for the current date.

1.  Select **Receiving > Dashboard**.
2.  To change the UOM in which quantities are displayed in the Receiving Issues area, from the **View By** drop-down list, select the UOM.
    
    **Note**: The drop-down values represent the system equivalent UOMs, as defined on the item footprint, for Pallet and Case. "Pallets" represents the LPN level; "Cases" represents the sub-LPN level; and "Eaches" represents the detail LPN level (the lowest UOM defined on the item footprint). For example, if you select Pallets, the application looks for the pallet-equivalent LPN level (LPN) UOM defined on the item footprint to determine quantity. If you select Cases, quantities are displayed based on the case-equivalent LPN level (sub-LPN) UOM defined on the item footprint.
    

Under **Receiving Issues**, perform one or more of the following tasks:

**Note**: If you click a value to navigate to additional details, the selected system equivalent UOM from the dashboard is used for inventory quantities on the subsequent page.

-   To view items that can be used to fill an outbound order that was allocated short (hot items):
    1.  In the **HOT** row, click **Items**.
        
        **Note**: The display grids contain details such as the item, hot quantity, and the outbound order that was allocated short for the item.
        
    2.  To modify the priority of the directed receiving work associated with a hot item, in the **Priority** column, enter the priority. A lower number indicates a higher priority, with 1 being the highest priority.
    3.  To view the inbound shipment and transport equipment information for a hot item, in the **Location** column, click the location.
        
        **Note**: If you click a location, the Door Activity dashboard is displayed with an active filter for the location you clicked, and you can perform additional tasks on the shipment or equipment. See [Door Activity](../shared-functions/door-activity.md).
        
-   To view the inbound shipment or transport equipment on which hot items reside, in the **HOT** row, click **Inbound Shipments**.
    
    **Note**: If you click Inbound Shipments, the Door Activity dashboard is displayed with an active filter showing the hot shipment or equipment, and you can perform additional tasks. See [Door Activity](../shared-functions/door-activity.md).
    
-   View the following information:

**Note**: The Receiving Issues grid contains linked values that you can click to view information for the inventory associated with the issue. For example, you can click the number of not receivable items and the Receiving Issues > Not Receivable page is displayed. See [Receiving issues](receiving-issues.md).

-   **Not Receivable**: Number of items (and quantities) that could not be received. Generally, this applies to new items that are missing attributes, such as an item footprint. Additional action needs to be taken before receiving can be completed, such as defining the necessary attributes and configuring the item as receivable.
-   **No Location**: Number of LPNs (and quantities) for which the application could not find a valid location for putaway.
-   **Overrides**: Number of LPNs (and quantities) deposited in a user-selected location after overriding the application-directed location.
-   **Inbound Quality Issues**: Number of unresolved quality issues that were reported against the suppliers and carriers of inbound inventory.
-   **Overage**: Quantity of inventory that was received over the expected quantity on the inbound shipment.
-   **Short**: Quantity of inventory that was received under the expected quantity on the inbound shipment.
-   **Damaged**: Quantity of inventory that was received with a Damaged inventory status or was moved to a Damaged location.
-   **Not Expected**: Quantity of inventory that was received but was not expected on the inbound shipment.

## Monitor staging lanes on the receiving dashboard

1.  Select **Receiving > Dashboard**.
2.  Under **Staging Lanes**, view the staged UOM information.
    
    **Note**: The Staging Lanes status bar shows the number of receiving staging lanes currently in use out of the total number of receiving staging lanes available. You can click the status bar to link directly to the Staging dashboard. See [Staging](../shared-functions/staging.md).
    

## Monitor doors on the dashboard

1.  Select **Receiving > Dashboard**.
2.  Under **Doors**, perform one or more of the following tasks:
    
    **Note**: The Doors status bar shows the number of doors configured for receiving that are currently in use. You can click the status bar to link directly to the Door Activity dashboard. See [Door Activity](../shared-functions/door-activity.md).
    
    -   Click **Live Inbound Shipments**. The display shows the inbound shipments associated with transport equipment for which a driver is waiting.
    -   Click **Ready to Dispatch**. The display shows the transport equipment associated with inbound shipments that have been unloaded and completed.

## Monitor appointments on the receiving dashboard

1.  Select **Receiving > Dashboard**.
2.  Under **Appointments**, perform one or more of the following tasks:
    
    **Note**: The Appointment status bar shows the number of appointments that are checked in (arrived) out of the total number of inbound appointments scheduled for the day. You can click the status bar to link directly to the Appointments dashboard. See [Appointments](../shared-functions/appointments.md).
    
    -   Click **Waiting**. The display shows the appointments for transport equipment that has been checked into the yard but has not yet been moved to a dock door by the start of its scheduled appointment time.
    -   Click **Late to Arrive**. The display shows the appointments for transport equipment that has not arrived at the warehouse (has not been checked in to the yard) by the start of its scheduled appointment time. Once the equipment is checked in, it is no longer displayed as late to arrive.
    -   Click **Late to Depart**. The display shows the appointments for transport equipment that has not been closed and dispatched by the end of its scheduled appointment time.
    -   Click **No Show**. The display shows the appointments for transport equipment that has not arrived at the warehouse by the end of its scheduled appointment time.

## Monitor receiving progress on the dashboard

You use the Receiving dashboard to monitor the hourly receiving progress, which helps you determine how receiving activities are progressing against your daily productivity goals.

1.  Select **Receiving > Dashboard**.
2.  To change the UOM in which quantities are displayed in the Progress area, from the **View By** drop-down list, select the UOM.
    
    **Note**: The drop-down values represent the system equivalent UOMs, as defined on the item footprint, for Pallet and Case. "Pallets" represents the LPN level; "Cases" represents the sub-LPN level; and "Eaches" represents the detail LPN level (the lowest UOM defined on the item footprint). For example, if you select Pallets, the application looks for the pallet-equivalent LPN level (LPN) UOM defined on the item footprint to determine quantity. If you select Cases, quantities are displayed based on the case-equivalent LPN level (sub-LPN) UOM defined on the item footprint.
    
3.  Under **Progress**, view the line graph that shows the following information:
    -   **Expected**: Quantity of inventory expected to arrive on an inbound shipment or transport equipment. Expected inventory is based on the items listed on the inbound orders associated with checked in appointments.
    -   **Received**: Quantity of inventory that have been received into four-wall inventory but have not been deposited to a staging lane or stored.
    -   **Stored**: Quantity of inventory that have been deposited to a receiving staging location or put away in a storage location.
4.  To change the timeline of the line graph (in four-hour increments), click ![Earlier time](../../../images/resources/images/image430108.png) or ![Later time](../../../images/resources/images/image430109.png).
    
    **Note**: You can only view progress up to the current date and time; if you are viewing progress for the current hour, you can only scroll back in time.
    
5.  To view receiving progress details for a specific time, in the line graph, click a point in time (indicated by a circle every half hour) and view the following information:
    -   Date and time
    -   Expected quantity to be received
    -   Actual received quantity and the percent received against what is expected
    -   Stored quantity and percent stored against what is expected

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
