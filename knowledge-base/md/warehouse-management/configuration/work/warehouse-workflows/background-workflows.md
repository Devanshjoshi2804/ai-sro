---
title: "Background Workflows"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/background_workflows.htm"
source: "/content/background_workflows.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Work"
  - "Warehouse Workflows"
  - "Background Workflows"
sections:
  - "Background workflow exit points"
  - "Add or modify a background workflow"
  - "Delete a background workflow"
  - "Background Workflow fields"
images: []
source_sha1: eedb80306f97046f9f71e0bf21db27558200f8a0
---
# Background Workflows

A background workflow is the warehouse-specific configuration of a master workflow. It defines when and how often the master workflow performs internal application processes, such as automatically printing labels, producing shipment documentation, or sending Event Management notifications.

When you create a background workflow, you specify the following attributes:

-   Master workflow that defines the process that takes place. See [Master Workflows](../workflows/master-workflows.md).
-   Exit points during warehouse processing at which the workflow is executed.

## Background workflow exit points

An exit point is the processing point at which the application initiates any actions, such as workflows, associated with the exit point.

When you create a warehouse-specific background workflow, you assign one or more exit points to the workflow. During warehouse processing, when the exit point occurs, the application executes the workflow.

The following table identifies the background workflow exit points.

 
| Exit point | Description |
| --- | --- |
| Allocate Inventory | Occurs when a shipment is allocated. |
| Carton Complete | Occurs when the user completes packing a cartonized or overpack carton.<br > Also occurs when a user manually confirms picks using the Pick Confirmation page. |
| Carton Initiation | Occurs when the operator enters a valid carton ID and confirms the carton is being worked on. This action is completed in Carton Confirmation Operations. On an RF device, this action can be completed through undirected or directed case confirm; and for cluster picking, the exit point occurs when the operator enters a valid carton ID and it has been added to the batch. The outbound workflows for this exit point process before the background workflows. |
| Deposit Last Inventory for Outbound Order | Occurs when the last LPN for an outbound order that is destined for the selected movement zone has been deposited to it. |
| Dock Door For Receiving Transport Equipment | Occurs when the operator prints the paperwork for receiving transport equipment. |
| Dock Door for Shipping Transport Equipment | Occurs when the operator prints the paperwork for shipping transport equipment. |
| Expected Residual | Occurs when the operator finishes a distribution deposit assignment and there is expected residual inventory. The workflow or command for this exit point is generally used to print labels for the expected residual inventory. |
| Inbound Pallet Label Start | Occurs when the operator builds a new pallet on the RF Inbound Pallet Build screen. When this inbound exit point is used, the application attempts to print a label for the pallet. |
| Inventory Consolidation Completed | Occurs when the operator completes a carton or pallet consolidation on the Inventory Close RF screen. The background workflow for this exit point is generally used to create directed work to move the completed carton or pallet out of the distribution consolidation location. |
| List Pick Start | Occurs when the operator starts a picking work assignment. |
| Load Transport Equipment | Occurs when the operator loads inventory onto outbound transport equipment. |
| Manifest Carton | Occurs when the user manifests a carton. |
| Manifest Closed | Occurs when the user closes a manifest. |
| Master Receipt Check In | Occurs when the user checks in an inbound shipment without transport equipment. |
| Master Receipt Unload | Occurs when the user unloads an inbound shipment to a staging location so that it can be received from the staging location instead of from the transport equipment. |
| Move Inventory | Occurs when the user moves inventory from one location to another. |
| Open New Container | Occurs when the operator opens a new container on the Distribution Deposit RF screen during the distribution put-to-store process. You use the background exit point to initiate a background workflow associated with the new container. |
| Pack Close Out | Occurs in the close out stage of pack station processing after a carton number is assigned to the completed shipping carton. The close out stage occurs either automatically after the application determines that all items assigned to a specific shipping carton have been packed into the shipping carton, or manually after the pack station operator closes the shipping carton (and after errors are reported, if any). |
| Pack Initiation | Occurs after the pack station operator enters the identifier for a picking container from which the operator will remove items to pack into a shipping container. This action is performed at the pack station. |
| Pack Item Scanned | Occurs after the pack station operator indicates the items that the operator is packing into the shipping container at the pack station. |
| Pack Station Processing | Occurs when the pack station operator tabs out of a processing field. This exit point is generally used to validate a processing field. |
| Packing Error | Occurs when a problem is detected and the pack station operator logs an error at the pack station. |
| Pick Initiation | Occurs when the operator acknowledges work for a pick or enters a work reference to start a pick, but before the application displays the pick information. This exit point is used for workflows that must be executed before the operator moves to the pick location.<br > The Pick Initiation exit point occurs prior to a pick; regardless of whether the pick is in a work assignment. The List Initiation exit point occurs prior to a work assignment. |
| Post-Allocate | Occurs when allocation of outbound inventory is complete and the optimal dock door calculation has chosen a staging lane. |
| Pre-Deposit | Occurs when the operator has finished picking inventory but before the inventory is deposited. This action is completed when the user indicates they are finished confirming a carton or moving inventory. On an RF device, this action can be completed by selecting an LPN on the Product Deposit RF screen. The background workflows for this exit point process after the outbound workflows. |
| Prepare for Shipping | Occurs when the user closes transport equipment. |
| Print Distribution Exception | Occurs when the user prints the Distribution Exception report. |
| Receiving Operations | Occurs when the user closes transport equipment in Receiving Operations. The workflow for this exit point is generally used to print the associated paperwork. |
| Returns Close | Occurs when the operator closes a return order using the Returns module. |
| Returns Process Item | Occurs when the operator processes a return item using the Returns module. |
| RF Outbound Audit Complete | Occurs when the operator completes an outbound audit of picked inventory. |
| Shipment Complete | Occurs when a pack station operator completes the last carton for a shipment. |
| Shipment Created | Occurs when the user creates a shipment. The only data included with this exit point is the warehouse ID and the shipment ID. |
| Special Handling Merge Complete | Occurs after the pack station operator merges newly picked inventory into the original picking container on the Merge Container window that is accessed from Special Handling Operations. |
| Stop Complete | Occurs when the user completes a stop. |
| Transport Equipment Pre-Load Pre-Unload | Occurs when the user starts an inventory-related activity, such as unloading incoming shipments or loading outbound shipments, for transport equipment. This is useful, for example, for creating directed receiving work. |
| Transport Equipment Closed | Occurs when the user closes transport equipment. |
| Transport Equipment Dispatched | Occurs when the user dispatches transport equipment. |
| Transport Equipment Loaded | Occurs when the user completes loading transport equipment. |
| Transport Equipment To Dock Door | Occurs when the user moves transport equipment to a dock door. |
| Unexpected Residual | Occurs when the operator finishes a distribution deposit assignment and there is unexpected residual inventory. The workflow or command for this exit point is generally used to print labels for the unexpected residual inventory. |
| Unpick from Ship Staging | Occurs when the operator unpicks inventory that has been deposited to a ship staging location. |
| Work Assignment Complete | Occurs when an operator completes the last pick for a work assignment. This exit point only applies to work assignments used to pick sequenced orders. |

## Add or modify a background workflow

1.  Select **Configuration > Work > Warehouse Workflows > Background Workflows**.
2.  Perform one of the following tasks:
    -   To add a new background workflow, click **Add**.
    -   To modify a background workflow, in the grid, click the workflow.
    -   To copy a background workflow, in the grid, select the check box next to the workflow, and then click **Copy**.
3.  Enter information in the [Background Workflow fields](#Background_Workflow_fields).

1.  To assign the processing points at which the application executes the workflow:
    1.  Click **Exit Points**. The Exit Points page is displayed.
    2.  In the **Available in** column, select the exit points to use.
    3.  Click **Save**.
2.  Click **Save**.

## Delete a background workflow

1.  Select **Configuration > Work > Warehouse Workflows > Background workflows**.
2.  In the grid, select the check box next to the background workflow to delete.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Background Workflow fields

 
| Field | Description |
| --- | --- |
| Enable Workflow | If Enabled, the application executes the workflow according to the sampling, criteria, and exit points defined for the workflow.<br > If Disabled, you can still configure the workflow, but it will not be executed or performed. |
| Master Workflow | Unique identifier for a workflow process. The master workflow defines the activity code that is logged for the workflow, tasks and instructions for completing the workflow, how the workflow is acknowledged, and the actions that take place upon completion of the workflow.<br > Every warehouse workflow is based on a master workflow. The warehouse workflow specifies the sampling, criteria, and exit points at which a master workflow is applied to specific entities (such as warehouse or transport equipment) or inventory. |
| Description | Text that further describes the master workflow. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
