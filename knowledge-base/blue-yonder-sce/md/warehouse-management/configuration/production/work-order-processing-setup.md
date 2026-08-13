---
title: "Work order processing setup"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/work_order_processing_setup.htm"
source: "/content/work_order_processing_setup.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Production"
  - "Work order processing setup"
sections: []
images: []
source_sha1: e2b76dfd350f93ce26552efc59f36a422328f3cf
---
# Work order processing setup

You must perform the following tasks to configure the application to process work orders:

1.  Configure location types. The following location types are used for work order processing: production stations and production staging. See [Location Types](../warehouse/locations/location-types.md).
2.  Define the areas and locations where production takes place. The following locations are used for work order processing:
    
    -   Production areas with production station locations
    -   Production staging locations for production lines and production stations
        
    
    You must define at least one area to be used to for production lines. See [Production Locations](../warehouse/locations/production-locations.md).
    
3.  Define the production lines. When you define a production line, you can also associate one or more production stations with the line. See [Production Lines](production-lines.md).
4.  Define the work order types used to distinguish between assembly and disassembly processes. See [Work Order Types](work-order-types.md).
5.  Configure work order settings that define general work order processing characteristics. See [Production Settings](production-settings.md).
6.  Configure the work stations that are used on the production lines. See [Workstations](../equipment/hardware/workstations.md).
7.  Configure storage search paths for directing putaway of the inventory received from production lines. See [Storage Search Paths](../inbound/storage/storage-search-paths.md).
8.  Configure work assignment picking for work order processing. See [Work Assignments](../outbound/picking/work-assignments.md).
9.  Configure cross docking to work with work order processing. Define the movement zones in which to deposit items that are needed for an existing cross docked line. See [Cross Docking](../inbound/cross-docking.md).
10.  Configure RF deposit behavior for depositing all sub-LPNs and detail-LPNs together on the same LPN. See [Storage Settings](../inbound/storage/storage-settings.md).
11.  Define the top-level, component, and supply items that you want to use or assemble in work order processing. See [Items](../inventory/items/items.md).
12.  Configure the bill of materials (BOM) purge task. You use the Console to configure jobs and tasks.
13.  Enable work order processing Event Management events. See [Event Management integration](../integration/event-management.md).
14.  If integrated with Warehouse Labor Management, configure the following attributes:
     
     -   Estimating goal times for work orders
     -   Defer sending work order information to Warehouse Labor Management
         
     
     See [Warehouse Labor Management integration](../integration/warehouse-labor-management.md).
     

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
