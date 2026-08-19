---
title: "LPN Handling"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/lpn_handling.htm"
source: "/content/lpn_handling.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inventory"
  - "LPN Handling"
sections:
  - "Handling unit categories"
  - "Handling unit features"
  - "Handling unit cartons"
images: []
source_sha1: 2d5eec5eeedffe14b2df6e2da9e812166266433d
---
# LPN Handling

A handling unit is an object (such as a pallet, tote, or a piece of transport equipment) that has value and that you want to track either individually or collectively.

When you configure the application to track handling units, you define the following information:

-   **Handling unit settings**: Used to enable and configure handling unit categories. See [Handling unit categories](#Handling_unit_categories) and [Configure handling unit settings](lpn-handling/handling-unit-settings.md).
-   **Handling unit types**: Used to define the types of handling units in use, such as pallets, totes, containers, and equipment. For each type you specify the size, capacity, and how the handling unit type is tracked (serialized, temporary, or as a container). For Transport Equipment handling unit types, you can define features for confirming that an attribute (such as temperature) is within a specified acceptable range. See [Add or modify a handling unit type](lpn-handling/handling-unit-types.md).
-   **Handling units**: Used to define the unique identifier and attributes of handling units that are tracked as individuals. Each handling unit that belongs to a handling unit type that is configured as serialized must be defined as an individual handling unit. See [Add or modify a handling unit](lpn-handling/handling-units.md).
-   **LPN attributes**: Used to define the LPN-level packaging attributes that can be applied to inventory. You can configure up to five user-defined attributes, and enable the ones that you want to be available for selection during various application processes. See [Configure LPN attributes](lpn-handling/lpn-attributes.md).

## Handling unit categories

A handling unit category is a setting that is used to enable a level of handling unit tracking for the warehouse. The following categories of tracking can be enabled:

-   **Inventory**: Enables tracking of all serialized and non-serialized handling units, with the exception of transport equipment. When this level of tracking is enabled, you can perform the following functions:
    
    -   Receive empty and non-empty handling units
    -   Identify an LPN or sub-LPN of inventory with a handling unit
    -   Move inventory to and remove inventory from a handling unit
    -   Associate a handling unit with inventory while picking for an order
    -   Enable handling units for use with picking work assignments
    -   Track handling units collectively by handling unit type
    -   Track individual handling units for handling unit types that are configured as serialized
    -   Ship empty and non-empty handling units
    -   Adjust the warehouse's on-hand quantity of non-serialized handling units
    -   Enable Event Management events related to handling unit quantities and movements. See [Event Management integration](../integration/event-management.md).
        
    
    Enable the Inventory category when you want to be able to use all functionality available in the application for tracking and maintaining inventory handling units.
    
-   **Picking Container**: Enables tracking of serialized and non-serialized handling units only during the process of picking and deposit inventory for work assignments. With this level of tracking enabled, the application prompts for and tracks handling units that are used during picking work assignments.
    
    For example, you may want to track handling units such as trolleys, cages, or totes that are used during picking work assignments to move items within the warehouse, especially if these handling units are pre-labeled with identifiers. With the Picking Container category enabled, you have visibility to the location of these handling units and the inventory that they contain. Once the work assignment is complete and the handling unit is empty it is available to be used for a new work assignment.
    
    Enable the Picking Container category (and not the Inventory category) if you are only interested in tracking handling units during picking work assignments, but not during receiving, shipping, and other inventory movement operations.
    
-   **Transport Equipment**: Enables tracking of individual pieces of transport equipment. Each handling unit type that is configured as transport equipment is defined as serialized and tracked as an individual.

## Handling unit features

A handling unit feature is intended to be used with the Transport Equipment handling unit category. A feature is used to define a range for some measurable attribute (such as temperature, humidity, or light sensors) of the transport equipment. For example, if you have refrigerated trailers defined as a handling unit type, you can assign a temperature feature with a minimum and maximum range to the handling unit type.

A feature can be assigned to a handling unit type or to an individually tracked handling unit.

Operators are prompted to capture the value of the handling unit when the Trailer Temperature Capture (CAPTURE-TRLR-TEMP) workflow is enabled and configured. This is a transport equipment workflow that uses a master workflow configured to execute a standard RF screen that supports the entry of a confirmation value. The workflow can be configured to execute, for example, during check in or when moving the transport equipment to a dock door. See [Master Workflows](../work/workflows/master-workflows.md) and [Transport Equipment Workflows](../work/warehouse-workflows/transport-equipment-workflows.md).

## Handling unit cartons

For each handling unit type that is enabled for work assignments, you can specify the types of cartons that can be included in the work assignments for the purpose of supporting cartonized picks. Only the cartons specified for a handling unit type can be assigned to work assignments that are based on that handling unit type.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
