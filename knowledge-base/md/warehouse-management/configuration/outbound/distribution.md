---
title: "Distribution"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/distribution.htm"
source: "/content/distribution.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Outbound"
  - "Distribution"
sections:
  - "Distribution setup"
images: []
source_sha1: 4dee943cf1aa6be2e8a93dfb3e66cac862ef5f65
---
# Distribution

Distribution is an automatic process that fulfills one or more outbound order lines with inventory from an inbound order line. The distribution process connects an inbound order line to one or more outbound orders, and defines how expected inbound quantities are distributed to the outbound orders.

When you configure distribution processing, you set up the following components:

-   **Distribution rule sets**: Used to determine the quantities and the order in which inbound inventory is distributed between customers to satisfy outbound orders.
-   **Distribution types**: Used to define the attributes and rule sets to use for a specific distribution of inbound inventory.
-   **Outbound routes**: Used to define the fixed schedules that define when shipments are routinely picked up from the warehouse for delivery.
-   **Voice distribution settings**: Used to specify the operations and attributes for performing distribution work using a voice device.

**Note**: For the complete list of setup tasks, see [Distribution setup](#Distribution_setup).

## Distribution setup

You must perform the following tasks to configure the application for flow-through distribution operations:

1.  Define the customers to whom you will be shipping flow-through distributions, and configure the distribution processing attributes for the customer. See [Existing Customers](../partners/customers/existing-customers.md).
2.  Configure inter-warehouse shipping, if necessary. This is required if you are setting up an interim warehouse for merge-in-transit. See [Configure shipping between warehouses](../warehouse/warehouses/multi-warehouse.md).
3.  Configure distribution processing attributes for the location types that support the deposit of allocated distribution inventory, and those that support the deposit of unallocated distribution inventory. See [Location Types](../warehouse/locations/location-types.md).
4.  Configure the movement zones:
    
    -   Specify whether the application automatically closes a shipping container when the last pick for a shipment is deposited in the container by an operator performing distribution deposit in the movement zone.
        
        **Note**: If you choose to automatically close shipping containers, then you must also configure the application to reserve locations in the distribution deposit movement zone by shipment. See [Processing Location Reservation](../inventory/movement/processing-location-reservation.md).
        
    -   Specify whether operators are required to perform an audit upon completing the deposit process for a distribution to verify the quantity of residual inventory.
        
    
    See [Movement Zones](../inventory/movement/movement-zones.md).
    
5.  Configure the items:
    
    -   Specify a department name for each item that you want to sort and process by department.
    -   Configure the item footprint UOMs that must be packed into a separate carton prior to being added to an LPN in a distribution shipment.
        
    
    See [Items](../inventory/items/items.md).
    
6.  Configure distribution components:
    -   Distribution rule sets. See [Distribution Rule Sets](distribution/distribution-rule-sets.md).
    -   Distribution rules. See [Distribution rules](distribution/distribution-rule-sets.md).
    -   Distribution types. See [Distribution Types](distribution/distribution-types.md).
7.  Create distributions for specific order lines:
    -   Specify which inbound order lines allow over distribution. See Add or modify an inbound order line.
    -   Create a distribution from an expected inbound order line or for each outbound order line that you want to fulfill with inventory from an inbound order line. See [Add or modify a distribution from an inbound order line](../../receiving/inbound-shipments/procedures-for-inbound-shipments.md) or [Add or modify a distribution for an outbound order line](../../outbound-planner/outbound/procedures-for-orders.md).
    -   Define the distribution attributes for each outbound order line. See [Add or modify an order line](../../outbound-planner/outbound/procedures-for-orders.md).
8.  Optionally, configure an auto allocation method to include unplanned orders. Use of this feature can alleviate delays in processing unplanned distribution orders, which would otherwise require manual allocation before cross docking can be performed. See [Automatic allocation of unplanned orders](allocation/automatic-allocation.md) and [Configure automatic allocation settings](allocation/automatic-allocation.md).

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
