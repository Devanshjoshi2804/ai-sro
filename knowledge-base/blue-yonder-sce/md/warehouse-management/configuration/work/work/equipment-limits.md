---
title: "Equipment Limits"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/equipment_limits.htm"
source: "/content/equipment_limits.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Work"
  - "Work"
  - "Equipment Limits"
sections:
  - "Configure equipment limits"
images: []
source_sha1: ffb72bdfe8a68de3d0acf6f29eeab57d6108bffe
---
# Equipment Limits

An equipment limit is a value that limits the number of material handling vehicles (equipment) that are directed to perform work in a work area or work zone. Specifically, when the equipment limit is reached, the application does not release any other work requests for the work area or zone until the work is completed and the number falls below the limit.

An equipment limit total can be specified for a work zone. Alternatively, an equipment limit based on equipment type can be specified for a work area or work zone.

Equipment limits are only applied during work management processing. The application does not offer directed work to an operator if doing so would exceed an equipment limit defined for either the work area or work zone in which the work needs to take place.

The application does not consider equipment performing undirected work (such as a manual count or manual pick) against the equipment limit unless configured to do so. See [Work RF Settings](work-rf-settings.md).

## Configure equipment limits

You can set a limit by equipment type for either a work area or for the work zones in the work area; but not for both. If you want to set a limit for a work area and limits are already set for a work zone in the area, then you must first clear the work zone limits. If you want to set a limit for a work zone and limits are already set for the work area, then you must first clear the work area limits.

1.  Select **Configuration > Work > Work > Equipment Limits**.
2.  Above the grid, select **Work Areas** or **Work Zones**.
3.  In the grid, click the area or zone to configure.
4.  In the **Available** column, select the check box next to the equipment that applies.
5.  For each selected equipment type, under **Equipment Type Limit**, enter the quantity of the equipment type allowed in the work area or zone at the same time.
    
    **Note**: When the equipment limit is reached, the application stops offering directed work in the work area or zone to operators using the equipment type.
    
6.  Click **Save**.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
