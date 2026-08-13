---
title: "Allocation Building Sequence"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/allocation_building_sequence.htm"
source: "/content/allocation_building_sequence.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Outbound"
  - "Allocation"
  - "Allocation Building Sequence"
sections:
  - "Configure allocation building sequence"
images: []
source_sha1: 811e2cbb4eef97f26fcc67bf0bebdc9d3ac1d0fb
---
# Allocation Building Sequence

To control picking access and hierarchy, you can define the sequence of buildings in which the application attempts to find inventory to fulfill orders processed from the building.

For example, if you define the building sequence for BUILDING1 to be BUILDING1, BUILDING2, and BUILDING3, then when orders are processed, the application attempts to find and reserve inventory from locations in BUILDING1, based on allocation search path configurations. However, if inventory cannot be reserved from BUILDING1, the application attempts to find it in BUILDING2, and finally in BUILDING3.

## Configure allocation building sequence

For each building, you can select the buildings that the application should search for inventory to fulfill orders, and then place the selected buildings in the preferred search order.

1.  Select **Configuration > Outbound > Allocation > Allocation Building Sequence**.
2.  In the grid, click the building to modify.
3.  In the **Available** column, select the check box next to the buildings to include in the search for inventory.
4.  In the **Selected** column, click and drag the building to the preferred position in the sequence.
5.  Click **Save**.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
