---
title: "Post Allocation"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/post_allocation.htm"
source: "/content/post_allocation.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Outbound"
  - "Allocation"
  - "Post Allocation"
sections:
  - "Configure post allocation settings"
  - "Post Allocation fields"
images: []
source_sha1: 545b7dc52500b6f46102c46aef265a70397563fe
---
# Post Allocation

Post allocation settings are used to configure the actions that take place prior to pick release after an allocation has been attempted. These settings determine the following attributes:

-   When replenishments are attempted for short orders
-   Whether picks are released prior to replenishment work being completed
-   Technical settings for generating allocation log files and specifying processing threads

## Configure post allocation settings

1.  Select **Configuration > Outbound > Allocation > Post Allocation**.
2.  Enter information in the [Post Allocation fields](#Post_Allocation_fields).
    
3.  Click **Save**.

## Post Allocation fields

 
| Field | Description |
| --- | --- |
| Create Replenishment Requests | If Yes, the application creates a replenishment request (emergency replenishment) when a shipment line cannot be fulfilled during allocation. Select Yes if you want the application to attempt to reallocate and avoid shorting the order if at all possible. Replenishments depend on the replenishment processing configurations to be enabled and defined.<br > If No, the application does not create replenishments even if inventory is missing. |
| Hold Replenishments and Cross Docks | If Yes, then after allocation, the application retains the Hold status of any pick work for replenishments and cross docks, if the picks are in a UOM or LPN level that is not marked for immediate release. For example, if a replenishment pick for 5 cases is allocated and the Case UOM is not marked for immediate release, then the application sets the status of the pick to Hold. With this field set to Yes, after allocation is complete, the application retains the Hold status on the replenishment pick until a user manually releases it. However, if Case is marked for immediate release, then the pick is set to Pending status, regardless of this configuration. Select Yes if you want to retain the hold on replenishment pick work and cross docks reserved during the allocation process.<br > If No, then following allocation, any remaining replenishment and cross dock pick work that was not immediately released is set to a Pending status (until it is automatically released by the application).<br > **Note**: If you set this field to No, then other factors can still prevent the picks from being set to a Pending status. For example, a hold may be applied (manually or automatically) to specific inventory for another reason, or the location in which the inventory resides may be in error. |
| In Line with Allocation (PIA) | If Yes, then if pre-inventory allocation is enabled and inventory required for an outbound order is unavailable, the application creates attempts to create a PIA replenishment at the time of allocation. If created successfully, then the pick work is released without waiting for the replenishment work to be completed.<br > If No, then if pre-inventory allocation is enabled and inventory required for an outbound order is unavailable, the application does not attempt to generate a PIA replenishment until all of the other order lines in the batch are processed. The replenishment then takes place in a separate automated background job. Picks are not released until the background job has successfully processed all order lines that are in need of a PIA replenishment. |
| Fill Locations To Capacity (PIA) | If Yes, then during pre-inventory allocation, the application attempts to fill a location to capacity before using another location. Locations are sorted based on the pending quantity (the quantity already being replenished to the location), not the available capacity of the locations. For example, assume there are two assigned locations for an item that both have a capacity of 100 cases, and the first location already has a pending replenishment quantity of 20 cases. If there is an additional pre-inventory allocation request for 50 cases of the item, then the application uses the first location because it has a higher pending quantity, and the first location is used until its capacity is reached.<br > If No, then during pre-inventory allocation, the application is not required to fill a location to capacity before using another location, meaning that one or more additional locations may be used before a single location is full. When this field is set to No, the application uses the location with the highest available capacity rather than sorting locations by highest pending quantity. For example, assume there are two assigned locations for an item that both have a capacity of 100 cases, and the first location already has a pending replenishment quantity of 20 cases. If there is an additional pre-inventory allocation request for 50 cases of the item, then the application uses the second location, because it has a higher available capacity (100 cases) than the first location (80 cases). If another pre-inventory allocation request for 30 cases is received, then the application uses the first location again because its available capacity (80 cases) is higher then the available capacity of the second location (50 cases). This is the default value.<br > **Note**: Assigned locations for an item are filled before unassigned (dynamic) locations, regardless of the **Fill Locations To Capacity (PIA)** field value. |
| Search Path Logging | If Yes, then the application logs information for the list of allocation processes that took place during inventory allocation. The list can include allocation log files for picks, demand replenishments, and emergency replenishments. You can view the search path log file for a short order line by viewing the short order line details, and then selecting the Search Path Log tab. If set to Yes, then logging always takes place during allocation, regardless of whether the **Search Path Logging** check box for an individual wave is selected.<br > If No, then allocation search path information is not logged by the application. The short allocation reason is still displayed, but the Search Path Log tab does not contain any information.<br > **Note**: If set to No, you can still enable search path logging for an individual wave by selecting the **Search Path Logging** check box on the wave. |
| Allocation Threads | Number of threads the application should use to allocate inventory as part of the allocation process. A single thread supports the allocation of shipment lines serially in a single repetitive process. With multiple threads, the application is able to submit intelligently grouped shipment lines to multiple threads concurrently. The optimum number of threads to use depends upon your configuration, hardware specifications, and data volume. For assistance in determining the optimum number of threads to use, contact your Blue Yonder project team.<br>
**Notes**:

<br>

-   •
    
    The default number of threads is 10. The amount of hardware computing resources that are consumed per thread during allocation can negatively affect the processing speed for other warehouse operations happening at the same time. It is recommended that you consider your hardware limitations and processing performance when defining the number of threads used by the application for allocation.
    
    <br>
<br>-   •
    
    Allocation as a Service does not support this configuration. If the **Enable Allocation as a Service** field is enabled in the manual allocation configuration, then the number of allocation threads is invalid because they are not used in allocation processing.
    
    <br>
<br>

 |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
