---
title: "Warehouse Workflows"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/warehouse_workflows.htm"
source: "/content/warehouse_workflows.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Work"
  - "Warehouse Workflows"
sections: []
images: []
source_sha1: fa18c1d4ffc24fba601086887c47643ed203d1ce
---
# Warehouse Workflows

A warehouse workflow allows you to enable a master workflow to be used in the current warehouse. For each warehouse workflow, you can configure the conditions and exit points that determine when the workflow takes place.

Background workflows take place without user intervention; all other workflows require the user to acknowledge the workflow and either confirm or complete the associated instructions for it.

The application supports the following types of workflows:

-   **Inbound**: Performed on inventory during receiving, putaway, and cross-docking processes.
-   **Outbound**: Performed on picked inventory prior to shipping.
-   **Production**: Performed during work order processing such as when a work order is started, stopped, moved, or closed.
-   **Warehouse equipment**: Performed on the warehouse equipment (such as fork-lifts, cranes, and clamp trucks) that is configured for use in your warehouse. See [Warehouse Equipment Type](../equipment/equipment/warehouse-equipment-type.md).
-   **Transport equipment**: Performed on transport equipment for the purpose of completing safety checks, checking the condition of the equipment, and capturing audit information.
-   **RF operator**: Performed when the assigned user attempts to move or put away inventory. The workflow directs the user to deposit the inventory in an intermediate location, where the inventory accuracy is validated before being directed to its destination location.
-   **Background**: Performed without operator intervention to accomplish such tasks as automatic printing of reports and labels, releasing of held picks, or sending an Event Management alert.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
