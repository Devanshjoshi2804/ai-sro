---
title: "Procedures for waves"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/procedures_for_waves.htm"
source: "/content/procedures_for_waves.htm"
toc_path:
  - "Warehouse Management"
  - "Shared functions"
  - "Waves and Picks"
  - "Procedures for waves"
sections:
  - "Plan a wave"
  - "Allocate a wave"
  - "Change the priority of a wave"
  - "Delete a wave"
  - "Release a wave"
  - "Unallocate a wave"
  - "Remove a shipment or load from a wave"
  - "Remove an order from a wave"
  - "Resize a carton"
  - "View waves"
  - "View detailed wave information"
  - "Allocate Wave fields"
  - "Wave detail fields"
images:
  - "/content/resources/images/image1076719.png"
  - "/content/resources/images/image1076720.png"
  - "/content/resources/images/image429922.png"
source_sha1: fc600602e6c6a9a7149f6cab5d628ff627e0a230
---
# Procedures for waves

You can perform these procedures using the Waves and Picks page, which is accessible from the following modules: **Outbound Planner**, **Picking**, or **Production**.

## Plan a wave

The first step in allocating inventory for outbound orders or shipments is planning them into a wave; all orders must be planned into a wave prior to allocation. See [Manual wave processing](../../outbound-planner/outbound-planning-concepts.md).

You can enter criteria that is used to select the orders or shipments you want to plan into a wave. For each wave rule, you can save criteria values used for waves that are frequently planned.

1.  View the Waves and Picks page.
    
    1.  Select one of the following modules: **Outbound Planner**, **Picking**, or **Production**.
        
    2.  Select **Waves and Picks**.
        
    
2.  Select **Waves**.
3.  From the **Actions** drop-down list, select **Plan Wave**.
    
    **Note**: To expand and pin open the Search Criteria fields, click ![Expand](../../../../images/resources/images/image1076719.png). To temporarily expand the criteria fields, click **Search Criteria**.
    
4.  Under **Search Criteria**, from the **Rule Name** drop-down list, select the rule that defines the parameters by which to search for orders or shipments.
    
    **Note**: To manage the wave rules that are available for selection, see [Wave rules](../../configuration/outbound/allocation/manual-allocation.md).
    
5.  To limit the orders or shipments that the application selects for the wave, enter information for one or more parameters associated with the wave rule.
6.  To select a pre-defined set of values for the selected rule criteria, from the **Saved Filter** drop-down list, select the filter.
7.  To save the values you entered for the parameters associated with the selected wave rule:
    
    **Note**: If you modify the values for an existing filter, the updated values overwrite the previously saved values.
    
    1.  Click **Save**.
    2.  In the **Name** field, enter a name for the filter.
    3.  Click **OK**.
8.  Click **Search**. The orders or shipments that meet the search criteria are displayed.
9.  Select the orders or shipments to include in the wave. The wave estimates update with each order or shipment you select.
    
    **Note**: To expand and pin open the Estimates fields, click ![Expand](../../../../images/resources/images/image1076720.png). To temporarily expand the fields, click **Estimates**.
    
10.  Click **Plan Wave**.
11.  Enter information in the following fields:
     
      
     | Field | Description |
     | --- | --- |
     | Wave Name | Value that is assigned to the group of pick-type work requests (picks, replenishments, and cross docks) that are created when the wave is planned. The wave name distinguishes one group of pick-type work requests from another, which enables you to track the requests through the application. For example, if you allocate inventory for a single shipment, then all of the picks, replenishments, and cross docks generated for the shipment have the same wave name.<br > If you do not enter a value, the application automatically generates an identifier for the wave. |
     | Destination Zone | Ship staging zone to which inventory for this wave will be sent. |
     | Staging Lane | Ship staging lane in the selected destination zone to which inventory for this wave will be sent. |
     
12.  Click **OK**.

## Allocate a wave

1.  View the Waves and Picks page.
    
    1.  Select one of the following modules: **Outbound Planner**, **Picking**, or **Production**.
        
    2.  Select **Waves and Picks**.
        
    
2.  Select **Waves**.
    
3.  In the grid, perform one of the following tasks:
    -   Select the row for the wave.
    -   Click the wave. The wave details are displayed.
4.  From the **Actions** drop-down list, select **Allocate Wave**.
5.  Enter information in the [Allocate Wave fields](#Allocate_Wave_fields).
    
    **Note**: Picks in a specific LPN level are released whenever the check box for the LPN level is selected for immediate release or when all three LPN levels are deselected.
    
6.  Click **OK**.
    
    **Note**: If the application cannot allocate enough inventory to satisfy the entire wave, the Short tag is displayed on the wave as well as on the associated order, shipment, and load that is short.
    

## Change the priority of a wave

Wave priority determines how the work associated with the wave is ranked in the work queue in relation to other work queue entries. The application uses priority to determine the sequence in which directed work is assigned. The lower the number, the higher the priority, with 1 being the highest priority.

To change the priority of individual pieces of work for the wave instead of all the work, use the [Work Queue](../work-queue.md) page. You can also manage individual pieces of pick work while viewing the details for a wave, order, shipment, or load. See [Perform actions on picks](procedures-for-picks-and-work-assignments.md).

1.  View the Waves and Picks page.
    
    1.  Select one of the following modules: **Outbound Planner**, **Picking**, or **Production**.
        
    2.  Select **Waves and Picks**.
        
    
2.  Select **Waves**.
    
3.  In the grid, perform one of the following tasks:
    -   Select the row for the wave.
    -   Click the wave. The wave details are displayed.
4.  From the **Actions** drop-down list, select **Change Priority**.
5.  In the **Priority** field, enter the priority to assign to the work queue entries associated with the wave.
6.  Click **OK**.

## Delete a wave

When you delete a wave, the application cancels all of the picks, replenishments, and cross docks for the wave. To cancel individual picks in a wave, see [Perform actions on picks](procedures-for-picks-and-work-assignments.md). You cannot cancel pick work that has been completed. You can only delete a wave for which no picks or cross docks have been completed.

1.  View the Waves and Picks page.
    
    1.  Select one of the following modules: **Outbound Planner**, **Picking**, or **Production**.
        
    2.  Select **Waves and Picks**.
        
    
2.  Select **Waves**.
    
3.  In the grid, perform one of the following tasks:
    -   Select the row for the wave.
    -   Click the wave. The wave details are displayed.
4.  From the **Actions** drop-down list, select **Delete Wave**.
5.  Click **OK**.

## Release a wave

Releasing a wave generates pick work in the work queue so that an operator can pick the inventory needed to fill the orders in the wave. Before you can release a wave of picks, you must plan it and then allocate inventory for it.

**Note**: When allocating the wave, if you selected to immediately release all of the LPN levels and UOMs, then you do not need to perform this procedure.

1.  View the Waves and Picks page.
    
    1.  Select one of the following modules: **Outbound Planner**, **Picking**, or **Production**.
        
    2.  Select **Waves and Picks**.
        
    
2.  Select **Waves**.
    
3.  In the grid, perform one of the following tasks:
    -   Select the row for the wave.
    -   Click the wave. The wave details are displayed.
4.  From the **Actions** drop-down list, select **Release Wave**.
5.  Click **OK**.

## Unallocate a wave

When you unallocate a wave, the application cancels any pending replenishments, cross-docks, and picks associated with the wave. A wave can be unallocated only if no picks or cross docks for the wave have been completed.

1.  View the Waves and Picks page.
    
    1.  Select one of the following modules: **Outbound Planner**, **Picking**, or **Production**.
        
    2.  Select **Waves and Picks**.
        
    
2.  Select **Waves**.
    
3.  In the grid, perform one of the following tasks:
    -   Select the row for the wave.
    -   Click the wave. The wave details are displayed.
4.  From the **Actions** drop-down list, select **Unallocate Wave**.
5.  Click **OK**.

## Remove a shipment or load from a wave

You can remove a shipment or load from a wave if there are no outstanding picks for the shipment or load. To cancel outstanding picks, see [Perform actions on picks](procedures-for-picks-and-work-assignments.md).

Removing a shipment or load removes the associated inventory from the wave, meaning it is not included in the pick work when the wave is released, but the shipment or load is retained in the application.

1.  View the Waves and Picks page.
    
    1.  Select one of the following modules: **Outbound Planner**, **Picking**, or **Production**.
        
    2.  Select **Waves and Picks**.
        
    
2.  Select **Waves**.
    
3.  In the grid, click the wave. The wave details are displayed.
4.  Perform one of the following tasks:
    -   To remove a shipment select **Shipments**.
    -   To remove a load, select **Loads**.
5.  In the grid, select the shipment or load to remove.
6.  From the **Actions** drop-down list, select **Remove from Wave**.
7.  Click **OK**.

## Remove an order from a wave

You can remove an order from a wave if there are no outstanding picks. To cancel outstanding picks, see [Perform actions on picks](procedures-for-picks-and-work-assignments.md).

Removing an order removes the associated inventory from the wave, meaning it is not included in the pick work when the wave is released, but the order and associated order lines are retained in the application.

1.  View the Waves and Picks page.
    
    1.  Select one of the following modules: **Outbound Planner**, **Picking**, or **Production**.
        
    2.  Select **Waves and Picks**.
        
    
2.  Select **Waves**.
    
3.  In the grid, click the wave number. The wave details are displayed.
4.  Select **Orders**.
5.  In the grid, select the check box next to the order.
6.  From the **Actions** drop-down list, select **Remove from Wave**.
7.  Click **OK**.

## Resize a carton

If automatic cartonization is configured and the application selects a carton that is too small or too large for the picks, then after picking has started, you can resize the carton by selecting a new carton type with the appropriate dimensions. The existing carton number is retained and associated with the new carton type.

**Note**: You can resize a carton only if at least one pick is complete and if no pick is in progress; you can also resize a carton for which all picks are complete.

1.  View the Waves and Picks page.
    
    1.  Select one of the following modules: **Outbound Planner**, **Picking**, or **Production**.
        
    2.  Select **Waves and Picks**.
        
    
2.  Select **Waves**.
    
3.  Select **Picks**. The pick details are displayed.
4.  In the grid, select the check box next to the pick for which you want to reassign the carton size.
5.  From the **Actions** drop-down list, select **Resize Carton**. The Resize Carton window is displayed.
6.  From the **New Carton Type** drop-down list, select the carton type you want.
7.  Click **Save**. The carton type is updated.

## View waves

1.  View the Waves and Picks page.
    
    1.  Select one of the following modules: **Outbound Planner**, **Picking**, or **Production**.
        
    2.  Select **Waves and Picks**.
        
    
2.  Select **Waves**.
    

## View detailed wave information

1.  View the Waves and Picks page.
    
    1.  Select one of the following modules: **Outbound Planner**, **Picking**, or **Production**.
        
    2.  Select **Waves and Picks**.
        
    
2.  Select **Waves**.
    
3.  In the grid, click the wave.
4.  View information in the [Wave detail fields](#Wave_detail_fields).
5.  To view orders and order lines in the wave:
    1.  Select **Orders**, and then view information in the [Order detail fields](../../outbound-planner/outbound/procedures-for-orders.md).
    2.  To view the order lines for an order, click ![Expand](../../../../images/resources/images/image429922.png), and view information in the [Order Lines detail fields](../../outbound-planner/outbound/procedures-for-orders.md).
6.  Select **Shipments** and view information in the [Shipment detail fields](../../outbound-planner/outbound/procedures-for-shipments.md).
7.  Select **Loads** and view information in the [Loads detail fields](../../outbound-planner/outbound/procedures-for-loads.md).
8.  Select **Picks** and view information in the [Picks detail fields](procedures-for-picks-and-work-assignments.md).
9.  Select **Shorts** and then view information in the [Shorts detail fields](../../outbound-planner/outbound/procedures-for-shorts-and-replenishments.md).
10.  Select **Pending Replens**, and view information in the [Pending Replenishments detail fields](../../outbound-planner/outbound/procedures-for-shorts-and-replenishments.md).

**Note**: Demand replenishments created as a result of pre-inventory allocation (PIA) processing are not displayed on the **Pending Replens** tab, because they are created as pick work and not replenishment work. You can view demand replenishments on the Picking and Outbound Planner Dashboards.

12.  Select **Cross Dock**, and view information in the [Cross Dock detail fields](../../outbound-planner/outbound/procedures-for-shorts-and-replenishments.md).

## Allocate Wave fields

 
| Field | Description |
| --- | --- |
| Destination Zone | Ship staging zone to which inventory for this wave will be sent. |
| Staging Lane | Ship staging lane in the selected destination zone to which inventory for this wave will be sent. |
| LPN | Indicates that LPN picks for the wave are immediately released for picking when the wave is allocated. If deselected, LPN picks that are not held may still be immediately released, but you must manually release any held picks.<br > **Note**: LPN level picks are held whenever the **LPN** check box is deselected for immediate release and one or both of the other LPN levels are selected. LPN level picks are released whenever the **LPN** check box is selected for immediate release or when all three LPN levels are deselected. |
| Sub-LPN | Indicates that sub-LPN picks for the wave are immediately released for picking when the wave is allocated. If deselected, sub-LPN picks that are not held may still be immediately released, but you must manually release any held picks.<br > **Note**: Sub-LPN level picks are held whenever the **Sub-LPN** check box is deselected for immediate release and one or both of the other LPN levels are selected. Sub-LPN level picks are released whenever the **Sub-LPN** check box is selected for immediate release or when all three LPN levels are deselected. |
| Detail LPN | Indicates that detail picks for the wave are immediately released for picking when the wave is allocated. If deselected, then detail picks must be released manually.<br > **Note**: Detail LPN level picks are held whenever the **Detail LPN** check box is deselected for immediate release and one or both of the other LPN levels are selected. Detail LPN level picks are released whenever the **Detail LPN** check box is selected for immediate release or when all three LPN levels are deselected. |
| Pick Type | Type of allocation that is performed for a wave.<br>-   • **Order Picks and Replenishments**: Commit inventory, create pick work entries, and create any needed replenishments.
<br>-   • **Order Picks**: Commit inventory and create pick work entries. Replenishments are not created, even if inventory is missing.
<br>-   • **Replenishments**: Create any needed replenishments.
<br>-   • **Top-off replenishment**: Create any needed top-off replenishments. |
| UOMs for release | For each unit of measure (UOM) listed, indicates that inventory in that UOM is immediately released for picking when the wave is allocated. If deselected, then picks in the UOM that are not held may still be immediately released, but you must manually release any held picks. |
| Consolidation | Value that defines how the application groups picks for the wave.<br>-   • **Outbound Order Number**: Only picks for the same order can be grouped together.
<br>-   • **Route-To Customer**: Only picks for the same route-to customer can be grouped together.
<br>-   • **Ship-To Customer**: Only picks for the same ship-to customer can be grouped together.
<br>-   • **Shipment**: Only picks for the same shipment can be grouped together.
<br>-   • **Stop**: Only picks for the same stop can be grouped together. |
| Wave Priority | Number that indicates the priority at which the released picks for the wave enter the work queue. Priority determines the sequence in which directed work is offered to operators. The lower the number, the higher the priority, with 1 being the highest priority. If a wave is unallocated, resulting in cancelled picks, then when it is reallocated, the application uses the priority that was established when the picks initially entered the work queue (before cancellation). |
| Manually Sequence Work | Indicates that the work release sequence type for all loads in the wave will be updated to Manual before wave allocation. If this check box is selected, the manual sequence overrides any other work release sequence type (except None) for the load. See [Assign a manual work sequence](../work-queue/procedures-for-work-queue.md).<br > If deselected, the work release sequence type for the load is not changed before wave allocation.<br > This field is enabled only when Enable Outbound Work Sequencing is set to Yes for the warehouse. See [Outbound work sequencing](../../configuration/outbound/shipping/outbound-staging.md). |
| Release Remaining Lines | Used for cross docking purposes.<br > If Yes, then the pick work for the order or work order lines that are not marked for cross docking are released as usual.<br > If No, then the pick work created for order or work order lines that are not marked for cross docking is held until the inventory that is marked for cross docking is received and allocated. |
| Allow bulk pick processing | If Yes, the wave is allocated using bulk pick processing. Bulk pick processing allocates matching inventory for multiple order or shipment lines together into larger unit of measure (UOM) picks so as to reduce the number of smaller UOM picks required to satisfy the lines. If set to Yes, the application groups order or shipment line quantities in the wave into larger bulk pick UOM quantities. This field is automatically set to Yes if the warehouse for which the wave was created is enabled for bulk picking.<br > If No, the inventory required for each order or shipment line in the wave is picked separately. You can select No to disable bulk pick processing for the wave; however, to enable bulk pick processing here, the warehouse must first be enabled for bulk picking. |
| Search Path Logging | Indicates that the application logs information for the list of allocation processes that took place during inventory allocation for the wave. The list can include allocation log files for picks, demand replenishments, and emergency replenishments. You can view the search path log file for a short order line in the wave by viewing the short order line details, and then selecting the Search Path Log tab.<br > If deselected, then allocation search path information is not logged by the application for this wave (unless configured to do so in the post allocation settings). The short allocation reason is still displayed, but the Search Path Log tab does not contain any information.<br > **Note**: If the **Search Path Logging** field is set to Yes in the post allocation configuration settings, then logging always takes place during allocation, regardless of whether the check box for the wave is selected. |

## Wave detail fields

 
| Field | Description |
| --- | --- |
| Total LPN picks | Total number of LPN picks required to fulfill the wave. |
| Estimated LPN Picks | Total number of estimated LPN picks required to fulfill the wave. |
| Completed LPN Picks | Total number of LPN picks that have been completed for the wave. |
| Estimated Weight | Estimated weight of the inventory that has been planned into the wave. The estimated weight is based on the item footprint UOMs for the inventory in the wave. This field is display only. |
| Estimated Volume | Estimate volume of the inventory for the wave. The measurement unit (such as cubic inches) is also displayed. |
| Estimated Goal Time | Goal time estimated by Warehouse Labor Management to complete this wave in seconds. This is only applicable if Warehouse Labor Management is integrated with Warehouse Management. |
| Assigned Lanes | Staging lane to which inventory for this wave has been assigned. If only one lane is assigned, the lane is displayed. If more than one is assigned, "Many (X)" is displayed, where X is the number of lanes. If there is many, you can click the value to display the lanes. |
| Customers | Number of customers to which inventory in the wave is to be sent. |
| Allocated | Percentage of inventory that has been allocated. Additionally, an X of Y value displays the number of eaches that are allocated out of the total number of expected eaches; for example, (50 of 100). The values for this field represent the amount of allocated inventory for the displayed entity (order, shipment, load, or wave). |
| Picked | Percentage of inventory that has been picked. Additionally, an X of Y value displays the number of eaches that are picked out of the total number of expected eaches; for example, (50 of 100). The values for this field represent the amount of picked inventory for the displayed entity (order, shipment, stop, load, or wave). |
| Staged | Percentage of inventory that has been staged. Additionally, an X of Y value displays the number of eaches that are staged out of the total number of expected eaches; for example, (50 of 100). The values for this field represent the amount of staged inventory for the displayed entity (order, shipment, stop, load, or wave). |
| Departure | End appointment date and time of the load associated with the wave; if multiple loads are associated with the wave, the earliest date is displayed. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
