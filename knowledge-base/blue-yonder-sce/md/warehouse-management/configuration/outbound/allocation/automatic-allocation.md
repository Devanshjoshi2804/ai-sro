---
title: "Automatic Allocation"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/automatic_allocation.htm"
source: "/content/automatic_allocation.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Outbound"
  - "Allocation"
  - "Automatic Allocation"
sections:
  - "Allocation methods"
  - "Example: Allocation method"
  - "Automatic allocation processing"
  - "Automatic allocation of unplanned orders"
  - "Setup"
  - "Example: Automatic allocation of unplanned orders"
  - "Set up automatic wave processing"
  - "Configure automatic allocation settings"
  - "Automatic Allocation fields"
  - "Method fields"
images: []
source_sha1: 44527599c888b37e99cf28e828471eead0145e28
---
# Automatic Allocation

Automatic allocation is the process by which the application chooses when and which orders or shipments to allocate automatically on a scheduled basis.

You can configure the application to automatically allocate selected orders or work orders when they are downloaded from a host or when the order falls within the auto allocation method's time criteria. The order or work order must satisfy all of the defined criteria for a method in order to qualify for auto allocation. You use the Automatic settings to configure and enable auto allocation methods and the criteria for each method.

## Allocation methods

An allocation method is a configuration that defines when and which orders are automatically allocated. An order or work order must satisfy all of the defined criteria in the method in order to qualify for automatic allocation.

When you configure an auto allocation method, you specify the following information:

-   Whether the method is enabled
-   A unique identifier and description
-   The event at which orders or work orders that match the method's criteria become candidates for automatic allocation. You can specify the event to occur when the order or work order is downloaded from the host, when the specified method date of the order or work order falls within the method's time window, or whichever happens first.
-   If the method should be used for orders or work orders
-   A date related to the order or work order, such as the late delivery date, that you want to use for scheduling auto allocation, and the amount of time in hours prior to that date your facility wants the inventory to be allocated. For example, if a method specifies 24 hours and Late Delivery Date, then an order that has a late delivery date of July 10th would be a candidate for allocation on July 9th to allow for the 24 hour lead time, assuming that July 9th is a picking day and is not a defined exception day.
-   Whether the method includes unplanned orders (outbound orders that have not been planned into a shipment or wave)

## Example: Allocation method

The following example shows how you can configure an auto allocation method and its related criteria.

The following table shows the configuration of an auto allocation method that takes effect 48 hours in advance of the late delivery date and includes unplanned orders.

   
| Event | Hours Prior to Date | Date | Include Unplanned Orders |
| --- | --- | --- | --- |
| Scheduled | 48 | Late Delivery Date | Yes |

The following table shows the configuration of method criteria. The criteria specifies that outbound orders for which the Ship-To Customer is CustomerA are candidates for auto allocation.

  
| Entity | Column | Value |
| --- | --- | --- |
| Order | Ship-To Customer | CustomerA |

Since the event is defined as Scheduled, orders (both planned and unplanned) that meet the criteria would be auto allocated once the PROCESS-AUTO-ALLOCATION job runs within 48 working hours of the late delivery date. For example, if the late delivery date on an order that meets the method criteria is July 21st, and the job runs inside of 48 working hours prior to July 21st, then the application would process the auto allocation for that order.

Additionally, if an unplanned order that matches the criteria and wave rule exists in the application when the auto allocation job runs within the specified time frame, it is automatically planned and allocated. During this process, the application plans the distribution order into a wave (based on the wave rule defined for the method), automatically creates the shipment and shipment line information, and then allocates the wave. When the inventory is received, it can be cross docked to fulfill the order (if the order lines are set to allow cross docking). If the method does not include unplanned orders, they must be manually planned into a wave or they remain unallocated.

If the method was configured to run on download, then any orders meeting the criteria (and wave rule, for unplanned orders) that are downloaded within the 48 period prior to the late delivery date are eligible for auto allocation immediately.

## Automatic allocation processing

Automatic allocation offers a consistent process for allocating waves and maintaining a constant flow of work within a warehouse. Automatic wave processing runs on a timer (or when the the orders are downloaded from the host, depending on the configuration), searches a list of unallocated shipment lines to find lines that are ready to be allocated, and allocates the shipment lines as batches.

**Note**: Even if Allocation as a Service is enabled, only a single thread is used during automatic allocation processing.

The application uses the following process to automatically allocate shipments:

1.  Searches for unplanned orders, if the allocation method is configured to include unplanned orders. If any are found, then the application creates a new schedule batch (wave), creates shipment lines for the unplanned orders, and then adds the shipment lines to the wave. For information about including unplanned orders for automatic allocation, see [Automatic allocation of unplanned orders](#Automatic_allocation_of_unplanned_orders).
    
2.  Searches for eligible unallocated shipment lines using rule criteria for the method.
    
    The application searches through existing shipment lines, either within an existing wave (which could include shipment lines created in step 1), or all shipment lines not linked to any wave, depending on the method configuration.
    
    Often, the rule criteria includes a value on the order line, such as the carrier, order type, transport equipment number, customer, **Pick Group 1** from the order line, or wave set. Additionally, the application checks for any shipment lines that contain a pick exclusion value. The application does not allocate a shipment that contains a shipment line with a pick exclusion.
    
3.  Assigns shipment lines to a pick group based on the grouping policy.
    
    Shipment lines are grouped for allocation based on wave, wave and shipment, or wave and item, depending on the value of the **Auto Allocation Grouping Level** field.
    
    **Notes**:
    
    -   A pick group can only contain either shipment lines from the same wave or shipment lines without a wave.
        
    
    -   If a shipment line is not already linked to a wave prior to the allocation process, then a new wave is generated to associate with the picks, but the shipment lines are not assigned to a wave. Shipment lines assigned to an existing wave remain linked to the wave.
        
    
4.  Allocates the pick group.
    

This process repeats until all found eligible orders or work orders are allocated. If there are multiple pick groups within a single wave, steps 3 and 4 are repeated for each pick group in the wave until the whole wave is allocated, and then the process repeats from step 1.

## Automatic allocation of unplanned orders

You can configure an automatic allocation method to include unplanned orders. An unplanned order is any outbound order that has not yet been planned into a shipment or included in a wave for allocation. Auto allocation for unplanned orders is especially useful in facilities that want to use cross docking to fulfill distributions for which existing shipment information does not exist. The application automatically creates shipment and shipment line information when planning orders into a wave based on the wave rule specified in the method.

If an unplanned order satisfies the method criteria but does not match the method's wave rule, it remains unplanned; alternatively, if the order matches the wave rule but violates the method criteria, it also remains unplanned. Additionally, unplanned orders must have a date value that matches the date specified in a method to be considered for automatic allocation. For example, if a method's date is Early Ship Date, and an unplanned order is created that meets all of the method's criteria, including the wave rule, but does not have an early ship date specified, then the order remains unplanned and not allocated.

Use of this feature can alleviate delays in processing unplanned distribution orders, which would otherwise require manual allocation before cross docking can be performed.

**Note**: Allocation methods configured to include unplanned orders cannot include shipment or shipment line criteria since the application creates shipment data during the auto allocation process.

The application can plan and allocate unplanned orders that are downloaded, manually created, or automatically created from the following host transactions:

-   Distribution Information (DISTRO\_INB\_IFD)
-   Order Information (ORDER\_INB\_IFD)
-   Order Line Information (ORDER\_LINE\_INB\_IFD)
-   Receipt Authorization Information (RA\_INB\_IFD)
-   Receipt Information (RCPT\_INB\_IFD)

### Setup

You must perform the following tasks to automatically plan and allocate unplanned orders:

1.  Configure a wave rule to be used by the application when planning a wave of unplanned orders that match the criteria of an automatic allocation method. See [Wave rules](manual-allocation.md) and [Configure manual allocation](manual-allocation.md).
2.  Configure an automatic allocation method with the following attributes:
    
    -   Set the **Include Unplanned Orders** field to Yes.
    -   Define method criteria that matches the attributes of the unplanned orders to include.
    -   Select the wave rule you created in step 1, by which the unplanned orders that match the method criteria are planned into picking waves and allocated.
    
    See [Allocation methods](#Allocation_methods) and [Configure automatic allocation settings](#Configure_automatic_allocation_settings).
    

## Example: Automatic allocation of unplanned orders

When an unplanned order that meets the method criteria is downloaded or created in the application, it becomes eligible for auto allocation based on the method configurations. See [Automatic allocation of unplanned orders](#Automatic_allocation_of_unplanned_orders).

For example, assume an allocation method is configured with the following field values:

-   **Include Unplanned Orders**: Yes
-   **Event**: Scheduled and On Download (Orders that meet the criteria are eligible for auto allocation when they are downloaded from the host within the date and time window, or based on the date and time window and when the PROCESS-AUTO-ALLOCATION job runs within that window, whichever comes first.)
-   **Hours Prior To Date**: 48
-   **Date**: Late delivery date

If an unplanned order that meets the method's criteria and planning wave rule is downloaded within 48 hours of the late delivery date, the application automatically plans the order into a wave (based on the wave rule), and then allocates the wave. If any order lines allow cross docking, when the inventory is received, it can be immediately cross-docked to fulfill the lines. However, if the unplanned order was created prior to the 48 hour window, it would not be planned or allocated until the PROCESS-AUTO-ALLOCATION job runs within that time frame.

## Set up automatic wave processing

You must perform the following tasks to set up automatic allocation processing:

1.  Configure your host to set Pick Group 1 on each waveable order to a different value, depending on which wave you want the order to be in.
2.  Configure the timer for the processing waves automatically. The timer, named Wave Generation, is configured in the Console, under Jobs.
3.  [Configure automatic allocation settings](#Configure_automatic_allocation_settings).

## Configure automatic allocation settings

1.  Select **Configuration > Outbound > Allocation > Automatic Allocation**.
    
    **Note**: The Job Schedule for Automatic Allocation displays the days and times on which the automatic allocation process runs. The schedule is maintained in the Console, under Jobs.
    
2.  Enter information in the [Automatic Allocation fields](#Automatic_Allocation_fields).
3.  To define the methods that determine which orders are automatically allocated, according to the schedule:
    1.  Click **Define Methods**.
    2.  Perform one of the following tasks:
        -   To add a method, click **Add**.
        -   To modify a method, in the grid, click the method.
    3.  Enter information in the [Method fields](#Method_fields).
    4.  To define the criteria that is used to find orders to allocate:
        1.  Under **Criteria Definition**, click **Expression**.
        2.  Select an entity that has the attribute to use, such as **Order.**
        3.  Select the attribute to use, such as **Ship-To Customer**.
        4.  Select the qualifier to use, such as "**\=**".
        5.  Select the value to use, such as **CustomerA** (the name of the shipping address for the order).
    5.  Click **Save**.
    6.  To delete an allocation method:
        1.  In the grid, select the check box next to the method to delete.
        2.  Click **Delete**. A confirmation message is displayed.
        3.  Click **OK**.
4.  Click **Save**.

## Automatic Allocation fields

 
| Field | Description |
| --- | --- |
| Allocate Shipments in Wave | If Yes, then shipments that have been added to a wave are processed (allocated) automatically. When this field is set to Yes, the Wave Generation job runs based on the job timer, which is maintained in the Console. If you enable automatic allocation of shipments in waves, then you can use the **Exclusion Command** field to specify the command used to exclude specific shipments or shipment lines (such as those that are cancelled) from the automatic allocation process.<br > If No, then waves are not processed (allocated) automatically. When this field is set to No, the Wave Generation job does not run, and shipments in waves must be manually allocated. |
| Exclusion Action | Server command used to exclude specific shipments or shipment lines (such as those that are cancelled) from automatic wave processing. This setting is only used if you want to exclude certain shipments or shipment lines marked as waveable (such as those that are cancelled) from automatic wave processing. |
| Maximum In Process | Maximum number of waves that are processed at the same time. Enter a value if automatic wave processing is enabled. |
| Auto Allocation Grouping Level | Level at which shipment lines are grouped together for automatic allocation. The grouping level affects how many shipment lines are allocated at one time, which can impact processing time and picking operations. During allocation, the database is locked, which prevents operators from picking allocated inventory; therefore, larger allocation batches may result in longer processing times and delayed picking operations.<br>-   •
    
    **Wave**: All shipment lines in a wave are grouped and allocated together as a single batch. This is the default value.
    
    <br>
<br>-   •
    
    **Shipment**: All shipment lines for a single shipment in a wave are grouped and allocated together as a single batch. Each shipment in a wave is allocated in a separate batch.
    
    <br>
<br>-   •
    
    **Item**: All shipment lines for a unique item in a wave are grouped and allocated together as a single batch. Each group of shipment lines for an item in a wave is allocated in a separate batch.
    
    <br>
<br > **Note**: If a shipment line is not already linked to a wave, such as a shipment in an unplanned order, then a new wave is generated to associate with the picks, but the shipment lines are not assigned to a wave. Shipment lines assigned to an existing wave remain linked to the wave. |

## Method fields

 
| Field | Description |
| --- | --- |
| Enable Method | If ENABLED, the application uses the method during automatic allocation processing to determine if there are any orders or work orders matching the selection criteria that can be allocated. If there are, the process attempts to allocate the orders and work orders automatically.<br > If DISABLED, the application does not consider the method during automatic allocation processing. |
| Method Name | Name of the method used to find orders for automatic allocation. |
| Method Description | Text that further describes the method. |
| Include Unplanned Orders | If Yes, the application includes unplanned orders that are found by the specified criteria. An unplanned order is any outbound order that has not yet been planned into a shipment or included in a wave for allocation. If set to Yes, when an unplanned order that meets the method criteria is downloaded or created in the application, it becomes eligible for auto allocation based on the method configurations. During the auto allocation of an unplanned order, the application plans the order into a wave (based on the rule specified in the **Planning Wave Rule** field), automatically creates the shipment and shipment line information, and then allocates the wave. See [Automatic allocation of unplanned orders](#Automatic_allocation_of_unplanned_orders).<br > **Note**: Allocation methods that include unplanned orders cannot include shipment or shipment line criteria since the application creates shipment data during the auto allocation process. If the method is already configured with shipment or shipment line criteria, and you set this field to Yes, a message is displayed indicating that shipment and shipment line criteria will be removed if you continue.<br > If No, then the application does not consider unplanned orders when using this method. |
| Planning Wave Rule | Wave rule that is used to group unplanned orders into a wave for automatic allocation. When an unplanned order is included in automatic allocation and wave processing, the application plans the wave based on this rule, which automatically creates shipment information for the order, and then allocates the wave. Only available if the **Include Unplanned Orders** field is set to Yes.<br > **Note**: Wave rules related to shipments are not available for selection since the rule only applies to unplanned orders (orders not yet planned into a shipment or wave). |
| Always Run | If Yes, then the application allocates orders and shipments that fit the method criteria whenever the scheduled auto allocation job runs. If set to Yes, the **Event**, **Date**, and **Hours Prior To Date** fields are not available because shipments that meet the criteria are always eligible for auto allocation.<br > **Note**: This field can be set to Yes for only one automatic allocation method. Typically, the method set to always run is configured to allocate shipments that had previously failed address validation or carrier selection. See [Parcel address validation and carrier selection](../shipping/parcel.md).<br > If No, then orders and shipments that fit the method criteria are eligible for automatic allocation according to the **Event**, **Date**, and **Hours Prior To Date** fields. |
| Event | Value that determines when the orders or work orders that meet the method criteria become eligible for auto allocation.<br>-   • **Scheduled**: Occurs based on the date window defined for the method. For example, if the **Hours Prior To Date** is set to 24, and the **Date** field is set to Early Ship Date, then an order that matches the method's criteria becomes eligible for auto allocation when the current date and time is within 24 hours of the early ship date defined for the order.
<br>-   • **On Download**: Occurs when the order or work order is received from the host within the date and time window for the method.
<br>-   • **Scheduled and On Download**: Occurs when the order or work order is received from the host within the date and time window, or based on the date and time window defined for the method, whichever comes first. |
| Hours Prior To Date | Number of hours prior to the date specified in the **Date** field that defines the date and time window in which orders or work orders that match the method criteria become eligible for auto allocation. For example, if the **Date** is Early Ship Date and your facility needs to allocate 2 working days before the early ship date, then set the **Hours Prior To Date** to 48. |
| Date | Date field associated with the order or work order that you want to use for scheduling auto allocations. The **Hours Prior to Date** field determines how far in advance of the select date the order or work order becomes eligible for auto allocation. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
