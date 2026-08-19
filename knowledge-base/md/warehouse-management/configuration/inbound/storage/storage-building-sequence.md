---
title: "Storage Building Sequence"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/storage_building_sequence.htm"
source: "/content/storage_building_sequence.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inbound"
  - "Storage"
  - "Storage Building Sequence"
sections:
  - "Configure storage building sequence"
images: []
source_sha1: 8b9e2d599e13435b70b754dcbdf5bb4ab1583db5
---
# Storage Building Sequence

To control putaway access and hierarchy, you can define the sequence of buildings in which the application attempts to find storage locations for inventory that is received into the building.

During putaway, the application is uses location preference and storage search paths to find a location to store inventory.

-   If a building sequence is defined, the application searches for a storage zone based on the building sequence that is defined.
-   If a building sequence is not defined, the application searches storage search paths in order of priority without regard to building sequence.

For example, if you define the sequence for BUILDING1 to be BUILDING1 and then BUILDING2 (but not BUILDING3), when inventory is received into BUILDING1, the application attempts to store that inventory in BUILDING1; if no location is found, the application attempts to find a storage location in BUILDING2, but will not search BUILDING3.

## Configure storage building sequence

For each building, you can select the buildings that the application should search for storage locations, and then place the selected buildings in the preferred search order.

1.  Select **Configuration > Inbound > Storage > Storage Building Sequence**.
2.  In the grid, click the building to modify.
3.  In the **Available** column, select the check box next to the buildings to include in the search for storage locations.
4.  In the **Selected** column, click and drag the building to the preferred position in the sequence.
5.  Click **Save**.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
