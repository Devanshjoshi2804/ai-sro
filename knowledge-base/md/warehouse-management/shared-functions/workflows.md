---
title: "Workflows"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/workflows.htm"
source: "/content/workflows.htm"
toc_path:
  - "Warehouse Management"
  - "Shared functions"
  - "Workflows"
sections:
  - "Tabs"
  - "Subtabs"
  - "Automatic workflow process"
  - "RF operator workflow process scenario"
images: []
source_sha1: 301eb85ffc10442df5c29eb2d49a5ee28e0a4a90
---
# Workflows

The Workflows page is accessible from the following modules: **Inventory**, **Picking**, **Production**, **Receiving**, **Shipping**, or **Yard**.

This page provides visibility into the various workflows that are scheduled, in-process, or complete. On a daily basis, operators and users perform extra handling of product in the warehouse to check the quality of, add value to, or handle unique situations (such as damaged) of inventory and equipment. These activities are known as workflows. You can use the application to automate this process so that your operators are prompted to perform the activity and, based on the results of the activity, the application automatically takes the appropriate actions.

A workflow is an application-directed operation to be performed on inventory, work orders, component items, or transport equipment at a pre-defined breakpoint or exit point (workflow exit point), in the warehouse.

### Tabs

The Workflows page consists of the following tabs:

-   **Inbound**: Displays inbound workflows as they transition through various statuses. An inbound workflow is used for operations performed on inventory that is received from an external source, typically prior to the inventory being stored or cross docked. See [Inbound Workflows](../configuration/work/warehouse-workflows/inbound-workflows.md).
-   **Outbound**: Displays outbound workflows as they transition through various statuses. An outbound workflow is used for operations performed on picked inventory prior to loading. See [Outbound Workflows](../configuration/work/warehouse-workflows/outbound-workflows.md).
-   **Equip/Production**: Displays the production, warehouse equipment, and transport equipment workflows as they transition through various statuses. A production workflow is used for operations performed on a bill of material, work order, component item, top-level item, or production station. A warehouse equipment workflow is used for operations performed on a bill of material (BOM), work order, component item, top-level item, production station, or vehicle. A transport equipment workflow is used for operation performed on inbound and outbound transport equipment, such as receiving and shipping trailers. See [Production Workflows](../configuration/work/warehouse-workflows/production-workflows.md), [Warehouse Equipment Workflows](../configuration/work/warehouse-workflows/warehouse-equipment-workflows.md), and [Transport Equipment Workflows](../configuration/work/warehouse-workflows/transport-equipment-workflows.md).
-   **Background**: Displays the history of the background workflows that have been performed. A background workflow is used for an operation that is performed by the application without visual interaction with a user and as the result of internal application processes, such as printing labels, producing shipment documentation, and performing validations to meet the customer's specifications. See [Background Workflows](../configuration/work/warehouse-workflows/background-workflows.md).
-   **RF Operator**: Displays the history of the RF operator workflows that have been performed. An RF operator workflow is used to validate the receiving and picking activities of an RF operator by directing the operator to deposit inbound or picked inventory to a pickup and deposit location where it can be verified before being directed to its final destination. See [RF Operator Workflows](../configuration/work/warehouse-workflows/rf-operator-workflows.md).

### Subtabs

The Inbound, Outbound, and Equip/Production tabs contain some or all of the following subtabs:

-   **Planned**: Displays the workflows that are planned for inbound or outbound inventory. Workflows that fail and are rescheduled are displayed on this subtab. Additional information for each workflow is also displayed, some of which includes the date and time at which it was planned, the purpose of the workflow, and the inbound shipment or outbound order associated with the inventory on which the workflow is to be performed.
    
    **Note**: The Planned subtab is not displayed on the Equip/Production tab.
    
-   **In Process**: Displays the workflows that need to be performed or have been acknowledged and are currently being performed, but not yet complete. Additional information is also displayed, some of which includes the user completing the workflow (if confirmed) and the exit point at which the workflow was executed. Workflows that are reversed are also displayed on this subtab.
-   **Failed**: Displays the workflow attempts that have failed. You can expand a failed workflow to view information such as the instructions included in the workflow and the operator responses.
-   **History**: Displays the history of completed failed and passed workflow attempts. You can expand a workflow to view information such as the instructions included in the workflow and the operator responses.

## Automatic workflow process

Workflows may be confirmed in-line during normal warehouse processes, such as receiving, picking, shipping, work order processing, and working with transport equipment or RF devices. The following is the process:

1.  When a workflow is required, an RF screen or workstation window is displayed and asks you if you want to confirm the workflow. You can choose to perform the workflow or skip it (because it does not need to be performed or you decide to perform it later. If the workflow is required and you choose not to confirm it, the current warehouse process cannot be completed. If the warehouse process has already been completed (for example, at the Post Identify workflow exit point), the application does not allow you to continue with the next process on the inventory (for example, putaway) until the required workflow is completed.
    
    **Note**: Warehouse and transport equipment workflows (except those that are work order related) cannot be cancelled by the operator prompted to perform the workflow. The operator must confirm the workflow and any workflow instructions configured for that workflow.
    
2.  If you choose to confirm the workflow and the workflow has instructions assigned to it, the application displays the workflow instructions. You can choose to perform the workflow instructions or skip them.
3.  If you choose to confirm a workflow instruction, after performing the workflow instruction and responding to the prompt (Yes or No acknowledge), if the workflow instruction has actions assigned to it, the application performs those actions. If the action displays an RF screen or workstation windows, such as the standard workflow confirmation value entry screen or window, you can respond appropriately.
4.  You can continue the process until you have confirmed or skipped all of the workflow instructions assigned to the workflow.
5.  If another workflow is required, the entire process starts over. You repeat the process until you have confirmed or skipped all of the workflows.
    
    **IMPORTANT**: If you skip any required workflows or workflow instructions, you cannot complete the specific warehouse process that was interrupted by the workflow.
    
6.  After you confirm all of the required workflows and workflow instructions, you can resume the warehouse process.

## RF operator workflow process scenario

A facility has hired a temporary or new worker to perform receiving or picking work using an RF device. Prior to beginning the work, a supervisor has created an RF operator workflow that would require the untrained RF operator to temporarily deposit received or picked inventory into a pick up and deposit location where it is validated for accuracy by another worker. The RF operator workflow process can be illustrated by the following:

1.  The temporary or new RF operator identifies or picks the inventory.
2.  An RF screen informs the operator to move the inventory to a specific location for validation.
3.  The operator moves the inventory to the workflow location and the application automatically completes the workflow.
    
    **Note**: If the operator deposits the inventory in a pick up and deposit location other than the one for the workflow, the application does not complete the workflow. Instead, when the next operator picks up the inventory to move it (this may be the same operator or another operator), the application directs the inventory to the location for the RF operator workflow.
    
4.  An experienced operator prints out the RF Operator Workflow Report and uses it to validate the inventory.
5.  After validation, the new RF operator (or another operator, depending on your business process) chooses the Transfer option from the RF device menu, scans the LPN and is directed to deposit the inventory in a location, such as storage or staging.
    
    **Note**: Work is not automatically created to move the inventory from the validation pick up and deposit location to its next location.
    

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
