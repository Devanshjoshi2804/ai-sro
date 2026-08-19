---
title: "Workflows"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/workflows_config.htm"
source: "/content/workflows_config.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Work"
  - "Workflows"
sections: []
images: []
source_sha1: e26aa6ddadac454d9bf9842863809ff234db633b
---
# Workflows - Configuration

A workflow is either a background process that takes place without user intervention or a notification that prompts the user to either confirm or perform one or more instructions. For example, a workflow may direct an operator to perform a safety check on equipment, verify inventory quality during receiving, apply a packing list to a completed shipping carton, or shrink wrap a pallet before loading it.

Workflows are configured to take place at specific points in warehouse processing, such as when transport equipment is checked in, when inventory is put away, when a carton is completed, or when all inventory for a shipment has been staged.

The following workflow configurations are required:

-   **Master workflows**: Used to define the instructions that are presented to users and the action, if any, that results from the user's response to an instruction. Master workflows are available globally to all warehouses in a multi-warehouse instance.
-   **Sampling configurations**: Used to define the rate or frequency at which a workflow is applied to inventory. Sampling configurations are available globally to all warehouses in a multi-warehouse instance.
-   **Warehouse workflows**: Used to define when a master workflow is applied; it is unique to the warehouse for which it is defined. A list of exit points specific to each type of workflow is available for you to specify the points at which the user is prompted to perform the workflow or at which a background workflow occurs.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
