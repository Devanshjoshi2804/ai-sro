---
title: "Replenishments"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/replenishments.htm"
source: "/content/replenishments.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inventory"
  - "Replenishments"
sections:
  - "Replenishment types"
  - "Replenishment setup tasks"
images: []
source_sha1: b10e3682adfef602f2392ee9415b6e659b7f4c41
---
# Replenishments

A replenishment is a request to move inventory from a storage location into a pick location. If enabled to take place, a replenishment can be accomplished automatically by the application in response to the following actions:

-   An order being allocated short
-   Inventory levels falling below a pre-defined threshold as a result of a pick or inventory move
-   A scheduled task that evaluates current inventory levels and generates replenishments to fill locations to the top-off replenishment percent defined for the location

Replenishments can also be generated manually by a user at a workstation or RF device.

When you configure replenishment functionality for the warehouse, you enable the types of automatic replenishments that you want the application to perform, and configure each type with the levels of inventory that you want to maintain.

## Replenishment types

The replenishment process determines what and how much inventory needs to be moved to forward pick locations so that it is available to be picked for an order. The application supports the following replenishment types:

**Note**: For information on how to set up and enable each type of replenishment, see [Replenishment setup tasks](#Replenishment_setup_tasks).

-   **Emergency replenishment**: A replenishment that is generated automatically by the application during allocation when there is insufficient inventory in a pick zone to satisfy an order or work order.
-   **Demand replenishment**: A replenishment that is generated automatically by the application during the pre-inventory allocation (PIA) process. The PIA process allocates inventory from a pick location prior to the inventory being available in the pick location, with the expectation that the location will be filled by a demand replenishment before the picker arrives at the location.
-   **Triggered replenishment**: A replenishment of an item that is generated automatically when inventory in the location or pick zone falls below a user-defined threshold. You can define what item you want to keep filled in one or more locations in a pick zone. A replenishment can be triggered, for example, as a result of a pick, inventory move, or adjustment.
-   **Top-off replenishment**: A replenishment process that is initiated automatically at timed intervals or started manually by a user, typically at a time that is considered a slow time of day for the warehouse. The top-replenishment process checks the inventory in pick zones configured for top-off replenishments. If the process finds quantities are below the top-off levels, it issues a replenishment request.
-   **Manual replenishment**: A replenishment that is initiated by a user at a workstation or RF device. It is typically generated when the user determines that a location requires replenishment of the item in that location. In response to the request, the application allocates the inventory and generates replenishment pick work to fill the location.

**Note**: If an order exists for an item for which there is currently a lower priority replenishment pending, such as a triggered replenishment, then the application prioritizes the lower priority replenishment to that of a demand replenishment to fulfill the order, if the job is configured and scheduled to run. Jobs are maintained in the Console, under Jobs.

The different types of replenishments may take place as needed during warehouse processing. For example, you can configure triggered replenishments to fill items at low levels and also configure top-off replenishments to fill all locations in selected pick zones, with inventory up to each location's top-off percentage. If you specify a number of locations in the pick zone to be filled with an item, and define a minimum quantity for the item in those locations to be 20 percent and the maximum quantity to be 100 percent, then the following replenishments occur:

-   During the day, if the inventory level in a location drops below the 20 percent capacity, the triggered replenishment process generates a replenishment to refill the location.
-   Toward the end of the day, as the allocation process slows down, the scheduled top-off replenishment process takes place, which generates replenishments to fill the locations to their top-off percentage in preparation for the next day.

## Replenishment setup tasks

You use the following tasks to set up replenishment processing in the warehouse:

1.  Configure pick methods. The configuration of pick methods is required to create the replenishment picks that need to be performed. A pick method defines the release action (such as to create work or produce pick sheets) that occurs for each type of replenishment. If the release action creates work, the pick method defines the type of pick that is created. A pick method must be assigned to a search path so that when the allocation process finds inventory using the search path, the action to pick the inventory can take place. See [Pick Methods](replenishments/pick-methods.md).
2.  Configure search paths. The configuration of search paths is required for all types of replenishments. A search path is a configuration that identifies a source zone from which the application should attempt to allocate inventory for a replenishment based on the attributes of the required inventory. The search path also specifies the pick method for releasing the action to perform the replenishment picks. Search paths are ordered according to the priority in which you want the application to search for inventory.
    
    **Note:** For triggered, top-off, and manual replenishments, the application only considers inventory attributes, such as Item Number, defined in the search path criteria. For demand and emergency replenishments, the application considers both inventory and order attributes, such as Client, defined in the search path criteria. This is because demand and emergency replenishments are generated to fulfill specific orders or work orders, but top-off, triggered, and manual replenishments are generated based on inventory levels in a pick zone.
    
    See [Replenishment Search Paths](replenishments/replenishment-search-paths.md).
    
3.  Configure settings.
    -   **Emergency and demand replenishments**: Shortages occur when an order is allocated and there is not enough inventory in pickable locations to fulfill the demand for the order. If configured to do so, the application responds to shortages by automatically generating replenishments to fill pick locations with the inventory required for the order. To accomplish this process, you must configure the following settings:
        -   **Zones to Keep Filled**: This configuration defines the zones to keep filled when orders need inventory for demand and emergency replenishments. You also specify the LPN level at which inventory is allocated to replenish the zone, and the final staging zone to which the inventory is directed after the order is picked. For each (piece) pick zones, you can also define a hop (intermediate) movement zone to which replenishment inventory can be moved in order to feed the pick locations, or to support cascading demand replenishments. See [Replenishment paths](replenishments/replenishment-settings.md).
        -   **General emergency replenishment settings**: Used to specify the values for timing that control how often the allocation process searches for inventory in the pick zone until the replenishment arrives, and the names of the log files used to record the replenishment process. See [Shortages](replenishments/replenishment-settings.md).
            
    -   **Triggered replenishments**: The application can generate replenishments automatically when inventory levels fall below the thresholds defined for each item that you want to be replenished. You can enable the application to generate triggered replenishments, select the items to be monitored for triggered replenishments, and specify the inventory levels that trigger this type of replenishment. The configuration of replenishment items is required for the following types of replenishments:
        -   **Triggered**: The application generates replenishments automatically when inventory levels fall below the thresholds defined for each item that you want to be replenished.
        -   **Top-off**: If top-off replenishments are configured to use the item configuration (instead of location quantities), then the replenishment item configurations are required.
        -   **Manual**: When a user generates a replenishment manually from a workstation or RF device, the replenishment process refers to the replenishment item configuration to determine the amount to replenish.
    -   **Top-off replenishments**: The application can evaluate the inventory levels for items or locations on a regularly scheduled basis and automatically generate replenishments if it finds inventory levels are below the thresholds defined for the replenishment item or if locations need to be filled (depending on the top-off method selected). You can enable top-off replenishment processing to take place, configure zones and items for which you want to maintain inventory levels, and view the schedule that defines the timing of these types of replenishments. See [Replenishment Settings](replenishments/replenishment-settings.md).
    -   **Date processing**. The attributes for replenishing date-tracked inventory are required for triggered and top-off replenishments. See [Inventory rotation allocation](../outbound/allocation/inventory-rotation-allocation.md).
4.  Configure voice replenishments. The configuration of voice replenishment is required if your facility uses voice recognition software and devices to communicate with RF operators, such as to provide them with directed work and record their activities in the application. See [Voice Replenishments](replenishments/voice-replenishments.md).
5.  Configure movement zones.
    -   In replenishment source movement zones, define whether you want to allocate a larger UOM than what is required for a replenishment pick (**Allocate Maximum UOM** field). See [Add or modify a movement zone](movement/movement-zones.md).
        
        **IMPORTANT**: If the source zone is for replenishments destined to a movement zone configured with the **Split Replenishment Residuals** field is set to Yes, then the **Allocate Maximum UOM** must be set to No on the source zone.
        
    -   In replenishment destination movement zones, define whether you want to enable splitting replenishment residuals (**Split replenishment residuals** field). See [Splitting replenishment residuals](replenishments/splitting-replenishment-residuals.md).
6.  Configure locations. Define the following values:
    -   For locations that you want to be able to replenish, set the **Replenishment** field to Yes, which enables the location for replenishment processing.
    -   For locations in the pick zones that are enabled for top-off replenishments, enter a value for the **Top-Off Replenishment Percentage**, which is the level of inventory to which the application attempts to replenish a location.
    -   For locations in which emergency replenishments can take place, enter a value for **Emergency Replenishment Percentage**, which is the percentage of a storage location's maximum capacity that is eligible to be removed from the location by the allocation of an emergency replenishment.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
