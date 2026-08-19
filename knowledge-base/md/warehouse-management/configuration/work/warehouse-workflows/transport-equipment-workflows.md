---
title: "Transport Equipment Workflows"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/transport_equipment_workflows.htm"
source: "/content/transport_equipment_workflows.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Work"
  - "Warehouse Workflows"
  - "Transport Equipment Workflows"
sections:
  - "Examples: Transport equipment workflows"
  - "Safety checks"
  - "Deferred safety checks"
  - "Immediate safety checks"
  - "Safety check setup"
  - "Transport equipment workflows exit points"
  - "Transport equipment configuration criteria"
  - "Add or modify a transport equipment workflow"
  - "Delete a transport equipment workflow"
  - "Transport Equipment Workflow fields"
images: []
source_sha1: 796d560d46e817d88f7866985e2e17b0f5f68737
---
# Transport Equipment Workflows

A transport equipment workflow is the warehouse-specific configuration of a master workflow. It defines when and how often the master workflow is to be performed on transport equipment. Many of these operations are based on safety checks or union and government compliance. Like inbound and outbound workflows, transport equipment workflows can be performed manually. However, transport equipment workflows cannot be canceled by the operator prompted to perform the workflows. The operator must confirm the workflow and any workflow instructions configured for that workflow.

When you create a transport equipment workflow, you specify the following attributes:

-   Master workflow that defines the activity that is logged when the workflow is performed, how the workflow is acknowledged, whether an operator can select "yes to all" when answering multiple questions in a workflow, the questions presented to the operator who performs the workflow, and the actions that take place upon completion of the workflow. See [Master Workflows](../workflows/master-workflows.md).
-   Sampling configuration that defines how often the application requires the workflow to be performed. See [Sampling Configurations](../workflows/sampling-configurations.md).
-   Exit points during warehouse processing at which the operator is prompted to perform the workflow. See [Transport equipment workflows exit points](#Transport_equipment_workflows_exit_points).

## Examples: Transport equipment workflows

Transport equipment workflows can be configured to prompt or direct operators through the completion of the following processes:

-   Capturing audit information, such as recording the temperature and fuel level of refrigerated transport equipment in the yard or dock to meet FDA and quality audit requirements
-   Performing safety checks whenever transport equipment is moved to or from a dock door to meet safety requirements
-   Checking the condition of transport equipment when checking in or dispatching to show whether any damage occurred at your facility

## Safety checks

A transport equipment safety check is a workflow that presents a series of questions to the user or RF operator regarding the condition of transport equipment that is checked in for receiving or shipping. A safety check is typically performed to verify that transport equipment is in proper condition for loading or unloading. Safety check workflows are typically performed on the RF or by using a workstation when performing receiving or shipping operations, or transport equipment moves, depending on whether the workflow is immediate or deferred, and which exit point is associated with the workflow.

### Deferred safety checks

A deferred safety check is a workflow that is required to be performed using a work station and is associated with the Dock Door Operations exit point. In this case, when an RF operator starts an inventory-related activity, such as unloading inbound shipments or loading outbound shipments, the RF operator is prompted that workflows must be completed in order to continue. Because of the deferred workflow and the exit point, an RF operator cannot complete the safety check. Instead, it must be completed from a workstation. This type of workflow ensures that transport equipment safety checks can only be completed at a workstation and not from an RF device.

**Note**: Deferred safety checks are generally used when you want to ensure that only supervisors can perform the workflow.

### Immediate safety checks

An immediate safety check is a workflow that can be performed using a workstation or an RF device and is typically associated with the Transport Equipment Pre-Load Pre-Unload exit point. In this case, when an operator starts an inventory-related activity, such as unloading inbound shipments or loading outbound shipments, the RF operator is prompted to complete the safety check workflow in order to continue working with the transport equipment. Because of the immediate workflow and exit point, a user can complete the safety checks on an RF device or by using a workstation.

### Safety check setup

Before the application can run transport equipment safety check workflows, you must complete the following tasks. See [Transport Equipment Workflows](#).

1.  To set up immediate transport equipment safety check workflows:
    1.  Enable the INIT-SAFETY-CHECK workflow and ensure that it is associated with the Transport Equipment to Dock Door exit point. This workflow is used to schedule non-inventory workflows when transport equipment is checked in at a dock door. If this background workflow is not set up, no immediate/deferred safety check is scheduled for the transport equipment upon check in.
    2.  Enable the SAFETY-CHK-IMMEDIATE non-inventory workflow and ensure it is associated with the Transport Equipment Pre-Load Pre-Unload exit point. This exit point occurs when an operator starts an inventory-related activity, such as unloading inbound shipments or loading outbound shipments.
2.  To set up deferred transport equipment safety check workflows:
    1.  Enable the INIT-SAFETY-CHECK workflow and ensure that it is associated with the Transport Equipment to Dock Door exit point. This workflow is used to schedule non-inventory workflows when transport equipment is checked in at a dock door. If this background workflow is not set up, no immediate/deferred safety check is scheduled for the transport equipment upon check in.
    2.  Enable the SAFETY-CHK-DEFERRED non-inventory workflow and ensure it is associated with the Dock Door Operations exit point. This exit point occurs when an operator starts an inventory-related activity, such as unloading inbound shipments or loading outbound shipments.
3.  To set up safety check workflows that take place upon moving transport equipment to a dock door.
    
    Enable the PERFORM-TRLR-SAF-CHK non-inventory workflow and ensure it is associated with the Transport Equipment to Dock Door exit point. This exit point occurs when transport equipment is moved to a dock door.
    
4.  Configure the workflow instructions for the safety check non-inventory workflows that you want to use.
    
    You can configure the workflow's general attributes, and add or modify the specific instructions that you want the application to present to the user/operator during the workflow. See [Master Workflows](../workflows/master-workflows.md).
    

## Transport equipment workflows exit points

An exit point is the processing point at which the application initiates any actions, such as workflows, associated with the exit point.

When you create a warehouse-specific transport equipment workflow, you assign one or more exit points to the workflow. During warehouse processing, when the exit point occurs, the application prompts the operator to complete the workflow.

**Note**: If a workflow is required and the user does not perform the workflow, the work will not be completed.

The following table identifies the transport equipment workflow exit points.

 
| Exit point | Description |
| --- | --- |
| Dock Door Operations | Occurs when the user starts an inventory-related activity, such as unloading inbound shipments or loading outbound shipments, for transport equipment.<br > A workflow associated with this exit point can only be completed from a workstation. This is useful, for example, if you do not want RF operators to complete certain workflows, such as safety checks, at this exit point. |
| Transport Equipment Audit | Occurs when the user performs a yard audit to verify the location of transport equipment in the yard. |
| Transport Equipment Check In | Occurs when the user checks in transport equipment. |
| Transport Equipment Closed | Occurs when the user closes transport equipment. |
| Transport Equipment Dispatched | Occurs when the user dispatches transport equipment. |
| Transport Equipment From Dock Door | Occurs when the user moves transport equipment away from a dock door. |
| Transport Equipment Pre-Load Pre-Unload | Occurs when the user starts an inventory-related activity, such as unloading inbound shipments or loading outbound shipments, for transport equipment. This is useful, for example, for initiating a safety check. |
| Transport Equipment To Dock Door | Occurs when the user moves transport equipment to a dock door. |
| Transport Equipment Turnaround from Receiving to Shipping | Occurs when the user closes receiving transport equipment that has the Turn Flag selected, indicating the transport equipment is turned around and used as shipping transport equipment. This action is completed from a workstation. This exit point processes after the Transport Equipment Closed exit point. |

## Transport equipment configuration criteria

The application uses the criteria that you specify for a warehouse-specific transport equipment workflow to select the inventory to which the workflow is applied.

The following table identifies the criteria that can be applied to a warehouse-specific transport equipment workflow.

 
| Criteria | Application |
| --- | --- |
| Transport Equipment Type | All transport equipment of the selected type. For example, for refrigerated transport equipment you may be required to record the temperature and fuel level for FDA compliance. |
| Transport Equipment Code | All transport equipment of the selected code. This code identifies the purpose of the transport equipment. |

## Add or modify a transport equipment workflow

1.  Select **Configuration > Work > Warehouse Workflows > Transport Equipment Workflows**.
2.  Perform one of the following tasks:
    -   To add a new transport equipment workflow, click **Add**.
    -   To modify a transport equipment workflow, in the grid, click the workflow.
    -   To copy a transport equipment workflow, in the grid, select the check box next to the workflow, and then click **Copy**.
3.  Enter information in the [Transport Equipment Workflow fields](#Transport_Equipment_Workflow_fields).
4.  To set the frequency at which the workflow is applied:
    1.  Click **Sampling and Criteria**. The Sampling and Criteria page is displayed.
    2.  Perform one of the following tasks:
        -   To add a new sampling configuration, click **Add**.
        -   To modify a sampling configuration, in the grid, click the sampling configuration.
        -   To copy a sampling configuration, in the grid, select the check box next to the sampling configuration, and then click **Copy**.
    3.  Enter information in the following fields:
        
        | Field | Description |
        | --- | --- |
        | Sampling Configuration | Configuration that controls the frequency at which a workflow is applied to LPNs. A sampling configuration includes one or more sampling rates that specify the number of LPNs to include in the workflow. See [Sampling Configurations](../workflows/sampling-configurations.md). |
        | Required | If Yes, the user is required to complete the workflow before returning to the interrupted work. If the user does not complete the workflow, the application does not allow the user to continue work.<br > If No, the user can choose to continue without performing the workflow. |
        | Criteria Type | Attribute for which you can enter a value. The application directs the workflow to be performed on entities that match the criteria and values that you enter. After you select a criteria type, one or more attribute fields are displayed. |
        
    4.  In the attribute fields (related to the criteria type), enter the values that transport equipment must match for the workflow to be applied. See [Transport equipment configuration criteria](#Transport_equipment_configuration_criteria).
    5.  Click **Save**.

1.  To assign the processing points at which the application executes the workflow:
    1.  Click **Exit Points**. The Exit Points page is displayed.
    2.  In the **Available in** column, select the exit points to use.
    3.  Click **Save**.
2.  Click **Save**.

## Delete a transport equipment workflow

1.  Select **Configuration > Work > Warehouse Workflows > Transport Equipment Workflows**.
2.  In the grid, select the check box next to the transport equipment workflow to delete.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Transport Equipment Workflow fields

 
| Field | Description |
| --- | --- |
| Enable Workflow | If Enabled, users are prompted to perform the workflow according to the sampling, criteria, and exit points defined for the workflow.<br > If Disabled, you can still configure the workflow, but users are never prompted to perform it. |
| Master Workflow | Unique identifier for a workflow process. The master workflow defines the activity code that is logged for the workflow, tasks and instructions for completing the workflow, how the workflow is acknowledged, and the actions that take place upon completion of the workflow.<br > Every warehouse workflow is based on a master workflow. The warehouse workflow specifies the sampling, criteria, and exit points at which a master workflow is applied to specific entities (such as warehouse or transport equipment) or inventory. |
| Description | Text that further describes the master workflow. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
