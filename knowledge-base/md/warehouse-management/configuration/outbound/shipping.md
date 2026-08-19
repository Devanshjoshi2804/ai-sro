---
title: "Shipping "
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/shipping_config.htm"
source: "/content/shipping_config.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Outbound"
  - "Shipping "
sections:
  - "Optimal outbound dock door"
  - "Optimal outbound dock door setup"
images: []
source_sha1: 1e9136f353e52b44df81a1948cd9f9138e4319f3
---
# Shipping - Configuration

The shipping process begins after a shipment is allocated and picked. During the shipping process, picked inventory is packed into shipping containers, if required, and then staged and loaded onto transport equipment. Shipping configurations define the attributes and behavior of each of these processes.

In addition, shipping configurations define the following options:

-   Parcel processing attributes, if the application is integrated with a parcel application through Parcel Handler
-   Paperwork processing and printing requirements
-   Automatic carrier selection to assign a carrier to a shipment
-   Using a voice device to load transport equipment
-   Customs processing, if the application is integrated with a duty management application
-   Mixing restrictions that specify the attributes of picked inventory that cannot be mixed on the same LPN

## Optimal outbound dock door

Optimal outbound door assignment is the process by which the application recommends the optimal dock door for outbound transport equipment based on the staging lane in which the inventory for the equipment's load is staged. The optimal dock door is the door that offers the shortest average distance to the locations of the selected UOM picks.

**IMPORTANT**: Optimal outbound door assignment requires that Warehouse Labor Management is integrated and enabled with Warehouse Management. Additionally, a warehouse map with location coordinates must be created, and Warehouse Labor Management must be configured to determine distance between locations.

Optimal dock doors are presented during transport equipment check in. An operator can manually choose a different dock door at any point in the transport equipment check-in process, including overriding the application-suggested dock door. If a dock door could not be chosen, the application notifies the operator.

## Optimal outbound dock door setup

You must perform the following steps to configure the application to recommend an optimal dock door for shipping:

1.  Integrate and enable Warehouse Labor Management with Warehouse Management. See [Warehouse Labor Management integration](../integration/warehouse-labor-management.md).
2.  Create a warehouse map with location coordinates and ensure Warehouse Labor Management is configured to determine distances between locations.
3.  Create transport modes. For each transport mode, you select which units of measure (UOMs) will support optimal dock doors. These transport modes can be used across multiple warehouses within your facility. See [Transport Modes](../partners/carriers/transport-modes.md).
4.  Assign a transport mode to an outbound load. Based on the transport mode, the application identifies the selected UOMs that can be used for optimal dock door.
5.  Enable the Set Optimal Staging Lane workflow and ensure that the Post-Allocate exit point is assigned to it so that the application runs the workflow to calculate the optimal dock door using your configurations. See [Background Workflows](../work/warehouse-workflows/background-workflows.md).

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
