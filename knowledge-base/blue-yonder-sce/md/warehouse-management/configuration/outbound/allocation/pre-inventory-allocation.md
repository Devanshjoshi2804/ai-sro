---
title: "Pre-inventory allocation"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/pre-inventory_allocation.htm"
source: "/content/pre-inventory_allocation.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Outbound"
  - "Allocation"
  - "Pre-inventory allocation"
sections:
  - "Pre-inventory allocation replenishments"
  - "Pre-inventory allocation setup and configuration"
images: []
source_sha1: 0fb526f30c5cc8141b4688a8e64f9caa838c4b38
---
# Pre-inventory allocation

Pre-inventory allocation (PIA) is a process in which picks are allocated from a pickface location before the necessary inventory physically exists at that location. With PIA enabled, if a pick location does not have inventory to complete an order, then the application generates demand-based replenishments from reserve storage locations to the pick location, and then generates picks based on the inventory pending to the pick location.

Demand replenishment work is typically created at a higher priority than other pick or replenishment work (such as triggered and top-off replenishments), so it arrives at the pick location before the pick work being performed. If the demand replenishment fails, then normal replenishment takes place and the application continually looks for inventory to bring to the pickface.

**Note**: You can define the number of times the application attempts to generate a demand replenishment. See [Pre-inventory allocation setup and configuration](#Pre-inventory_allocation_setup_and_configuration).

This feature supports all allocatable units of measure, and the application allocates them from the highest available unit of measure to the lowest to reduce the amount of pick work. By using PIA, work can begin on an order immediately instead of waiting for the entire order to be physically present at the pick location.

When PIA is enabled, the application attempts to allocate all or part of an order line quantity using PIA processing. If the entire order line quantity can be picked in a UOM enabled for PIA, then the application performs PIA processing on the entire quantity. For example, if the Case UOM is enabled for PIA processing, then for an order line quantity of two cases, the application processes the entire quantity using PIA.

If the order line quantity is not a whole-number multiple of a UOM enabled for PIA, then the application performs PIA processing on the quantity that can be picked in a UOM enabled for PIA, and shorts the remainder that must be picked in a UOM not enabled for PIA. For example, if the Case UOM is enabled for PIA processing, but the Each UOM is not, then for an order line quantity of two cases and four eaches, the application processes the two cases using PIA, and generates a short allocation for the four eaches.

## Pre-inventory allocation replenishments

With pre-inventory allocation, if there are multiple pickfaces for a single item, the replenishments are balanced across the locations based on replenishment item configurations. When the demand for an item causes all assigned pick locations to reach maximum capacity and the zone is configured to use unassigned locations, the application temporarily replenishes unassigned locations for the item until the orders are filled. During this process, the application checks the capacity of the item's assigned locations defined by the replenishment item configuration. If demand requires, locations in the same zone to which an item has not been assigned are used to store the replenishment item as long as the maximum number of locations allowed in the zone for the item is not exceeded.

Filling additional pickfaces is not always an option when locations are full, so you can control the flow of replenishments to pickface locations using by configuring the operation for demand replenishment work to be created in a Locked status. This prevents it from being released to full pickface locations. When pick locations can accept more inventory from allocated replenishments, the application uses an assigned release command to determine when the pick location can accept more inventory and, if it can, releases the pick work to bring additional quantities to the pickface.

A PIA replenishment can fail if there is no available inventory to fulfill the replenishment or if a suitable destination location for the inventory cannot be found. You can configure whether the application attempts to find a destination location multiple times if the first location cannot be used. This configuration allows the application to search for another eligible location in the replenishment path to deposit the replenishment inventory for the PIA picks.

Additionally, you can configure the number of times the application attempts to create a demand replenishment if the first attempt fails due to insufficient inventory, or the lack of suitable source or destination location. See [Pre-inventory allocation setup and configuration](#Pre-inventory_allocation_setup_and_configuration).

## Pre-inventory allocation setup and configuration

You must perform the following tasks to set up and configure pre-inventory allocation.

1.  Enable pre-inventory allocation to occur in line during allocation. On the post allocation configuration, set the **In Line with Allocation (PIA)** field to Yes to ensure that pre-inventory allocation runs at the time of allocation. If this field is set to No, the demand replenishment allocation takes place through a scheduled job.
    
    If you want pick locations to be filled to capacity before another location is used during pre-inventory allocation, set the **Fill Locations To Capacity (PIA)** field to Yes. See [Post Allocation](post-allocation.md).
    
2.  Configure pick zones for pre-inventory allocation. Set the **Pre-Inventory Allocation (PIA)** field to Yes. See [Pick Zones](pick-zones.md).
3.  Configure pick locations for replenishment. For each location that you want to replenish, set the **Replenishment** field to Yes. Only locations enabled for replenishment will be replenished. See [Replenishments](../../inventory/replenishments.md).
4.  Configure the demand replenishment (PIARPL) directed work operation to be created in a Locked status. Set the **Initial Creation Status** field to Locked to prevent replenishments from being released to a full pickface location.
    
    You can also assign a release work action to the operation that determines when the pickface is able to accept additional inventory, and changes the status from Locked to Pending, so that the pick work can be performed. See [Work Operations](../../work/work/work-operations.md).
    
5.  Configure for a movement zone whether the application validates mixing restrictions for a demand replenishment when the replenishment pick work is unlocked. Set the **Ignore Mixing Restrictions on Release** field. See [Movement Zones](../../inventory/movement/movement-zones.md).
6.  Configure allocation search paths for replenishments. Ensure that replenishment search paths are defined that identify the source zone for replenishing pickface destination zones. See [Replenishment Search Paths](../../inventory/replenishments/replenishment-search-paths.md).
7.  Configure replenishment paths that define the movement zones to keep filled when orders need inventory for demand and emergency replenishments. See [Replenishment paths](../../inventory/replenishments/replenishment-settings.md).
8.  Configure whether the application attempts to search for a demand replenishment destination location multiple times. This occurs if the application fails to allocate the first destination location it finds. The destination of the replenishment inventory is the source location for the PIA pick. Set the **Retry Multiple PIA Locations** field. See [Replenishment Settings](../../inventory/replenishments/replenishment-settings.md).
9.  Configure the maximum number of times the application should attempt to create a demand replenishment before it creates an emergency replenishment. Enter the number in the **Demand Replenishment Retry Count** field. See [Replenishment Settings](../../inventory/replenishments/replenishment-settings.md).
10.  Configure replenishment by item. You can set parameters that the application uses to determine how the inventory is released to the pick location. Increment configuration can be defined as units or as a percentage, and is used for balancing demand across locations for which their capacity is maximized. In addition, you can enter a release percentage, which allows a location's capacity to be greater than usual for the purpose of releasing inventory for immediate picking. See [Replenishment items](../../inventory/replenishments/replenishment-settings.md).
11.  Configure the pick method for types of picks used to perform demand replenishments. When you configure the pick method, you define the release rules for the zones to which PIA replenishment picks are delivered. See [Pick Methods](../../inventory/replenishments/pick-methods.md).

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
