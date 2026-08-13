---
title: "Transportation Manager"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/transportation_manager.htm"
source: "/content/transportation_manager.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Integration"
  - "Transportation Manager"
sections:
  - "Configure Transportation Manager integration"
images: []
source_sha1: 8f0d72edaf921177c445dbb78224435a24d1b797
---
# Transportation Manager

Transportation Manager (TM) provides transportation planning and load tendering for outbound orders received from Warehouse Management (WM). When a carrier accepts the tender for the load or the tender is auto-accepted, TM sends the details of the load plan to WM. This information allows WM to begin its process to fulfill and run the load. Load header information, stops, shipments, shipping/delivery dates, quantities, weight, and volume are supplied as part of the load plan data to WM.

The start of the allocation process prompts WM to send a load status update request to TM. TM accepts the load status update request from WM and updates a reference number on the load to provide the TM user visibility to the WM status. After WM completes its process and dispatches the transport equipment, WM sends a load confirmation with details of what was shipped to TM. After the load confirmation is reconciled with the load plan that TM created, TM stores the load that is shipped from WM and allows the TM user to do additional processing such as financials and reporting.

See the Transportation Manager and Warehouse Management Integration Guide.

## Configure Transportation Manager integration

1.  Select **Configuration > Integration > Transportation Manager**. The Transportation Manager page displays the following information:
    -   Status of Integrator tasks associated with the integration.
    -   Status of the Integrator transactions associated with the integration.
2.  To enable integration, in the **Enable Transportation Manager** field, select **ENABLED.**
3.  Enter information in the following fields: 
    
     
    | Field | Description |
    | --- | --- |
    | Cube Conversion Factor | The cube conversion factor is used to convert a larger measurement unit (MU) for volume to a smaller MU for volume (for example, cubic feet to cubic inches). If the volume MU used by Transportation Manager is larger than the volume MU used by Warehouse Management, then enter a conversion factor. Warehouse Management converts the volume it receives from Transportation Manager by multiplying it by the cube conversion factor. For example, the factor used to convert cubic feet to cubic inches in 1728. If the volume MU is the same for both systems, enter a value of 1. See the Transportation Manager and Warehouse Management Integration Guide. |
    | Send Order Line Details | If Yes, and if Transportation Manager (TM) is integrated with Warehouse Management, then when an order line is downloaded from the host, Warehouse Management sends the order line details to Transportation Manager (such as volume and weight measurements, item family, commodity code, and a hazardous material indicator). Order line details are sent based on the scheduled job SEND-TMS-ORDER-LINE-MEASURES; jobs are maintained in the Console, under Jobs.<br > When the scheduled job runs, the system sends the details for all of the order lines on the order to TM through an integrator transaction (ORDER\_UPDATE\_TO\_CANONICAL). TM uses the details to estimate and plan loads more accurately before sending load plan information back to Warehouse Management. On the Outbound page, you can filter order lines to view only those for which details have not yet been sent to Transportation Manager (**Pending to TM** field).<br > **Note**: If updates are made to an order line prior to the job running, then the updated information is sent to TM. If updates to an order line are downloaded after the order line details have been sent to TM, the updated order line details are not sent unless another new order line is downloaded, and the details are sent again.<br > If No, then order line details are not sent to Transportation Manager. |
    
4.  Click **Save**.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
