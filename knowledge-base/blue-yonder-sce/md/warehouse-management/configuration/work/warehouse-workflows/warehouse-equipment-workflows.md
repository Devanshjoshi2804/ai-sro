---
title: "Warehouse Equipment Workflows"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/warehouse_equipment_workflows.htm"
source: "/content/warehouse_equipment_workflows.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Work"
  - "Warehouse Workflows"
  - "Warehouse Equipment Workflows"
sections:
  - "Warehouse equipment workflows exit points"
  - "Warehouse equipment configuration criteria"
  - "Add or modify a warehouse equipment workflow"
  - "Delete a warehouse equipment workflow"
  - "Warehouse Equipment Workflow fields"
images: []
source_sha1: e584092ca0e8c7476f46e46a1c2297207c05ccb3
---
# Warehouse Equipment Workflows

A warehouse equipment workflow is the warehouse-specific configuration of a master workflow. It defines when and how often the master workflow is to be performed on mechanical or motorized devices (such as material handling equipment) within the warehouse. Many of these operations are based on safety checks or union and government compliance. Like inbound and outbound workflows, warehouse equipment workflows can be performed manually. However, warehouse equipment workflows cannot be canceled by the operator prompted to perform the workflows. The operator must confirm the workflow, and any workflow instructions configured for that workflow.

When you create a warehouse equipment workflow, you specify the following attributes:

-   Master workflow that defines the activity that is logged when the workflow is performed, how the workflow is acknowledged, whether an operator can select "yes to all" when answering multiple questions in a workflow, the questions presented to the operator who performs the workflow, and the actions that take place upon completion of the workflow. See [Master Workflows](../workflows/master-workflows.md).
-   Sampling configuration that defines how often the application requires the workflow to be performed. See [Sampling Configurations](../workflows/sampling-configurations.md).
-   Exit points during warehouse processing at which the operator is prompted to perform the workflow. See [Warehouse equipment workflows exit points](#Warehouse_equipment_workflows_exit_points).

The application is distributed with the following master workflows for warehouse equipment:

-   **Perform Vehicle Safety Check (PERFORM-VEH-SAF-CHK)**: Used to create warehouse equipment workflows for warehouse equipment types that are not individually captured or subject to being locked when a safety check fails. If warehouse equipment fails this safety check workflow, the application does not prevent the operator from using the equipment in warehouse operations. It is recommended that this workflow is used for warehouse equipment types that have the Capture Warehouse Equipment field set to No.
    
-   **Perform Equipment Safety Check (PERFORM-EQP-SAF-CHK)**: Used to create warehouse equipment workflows for warehouse equipment types that have the Capture Warehouse Equipment field set to Yes and that have unique warehouse equipment IDs defined. This workflow includes an instruction action with the following attributes: Result = Fail; Action = Run MOCA; Command = lock warehouse equipment. After an operator enters the equipment ID and the workflow is triggered at one of the exit points, the operator performs the safety check workflow. If the workflow fails, then the application automatically runs the command and locks the operator’s equipment. Warehouse equipment can be locked and unlocked manually on the Warehouse Equipment Operations page. See [Warehouse Equipment Operation](../../../shared-functions/warehouse-equipment-operations.md).
    

## Warehouse equipment workflows exit points

An exit point is the processing point at which the application initiates any actions, such as workflows, associated with the exit point.

When you create a warehouse-specific warehouse equipment workflow, you assign one or more exit points to the workflow. During warehouse processing, when the exit point occurs, the application prompts the operator to complete the workflow.

**Note**: If a workflow is required and the user does not perform the workflow, the work will not be completed.

The following table identifies the warehouse equipment workflow exit points.

 
| Exit point | Description |
| --- | --- |
| Warehouse Equipment Change Type | Occurs when the operator changes to a different type of warehouse equipment. |
| Warehouse Equipment Log Off | Occurs when the operator logs off warehouse equipment. |
| Warehouse Equipment Log On | Occurs when the operator logs on to warehouse equipment. |

## Warehouse equipment configuration criteria

The application uses the criteria that you specify for a warehouse-specific warehouse equipment workflow to select the equipment to which the workflow is applied.

The following table identifies the criteria that can be applied to a warehouse-specific warehouse equipment workflow.

 
| Criteria | Application |
| --- | --- |
| Warehouse Equipment Type | All warehouse equipment of the selected type. |

## Add or modify a warehouse equipment workflow

1.  Select **Configuration > Work > Warehouse Workflows > Warehouse Equipment Workflows**.
2.  Perform one of the following tasks:
    -   To add a new warehouse equipment workflow, click **Add**.
    -   To modify a warehouse equipment workflow, click the warehouse equipment workflow.
    -   To copy a warehouse equipment workflow, select the check box next to the warehouse equipment workflow, and then click **Copy**.
3.  Enter information in the [Warehouse Equipment Workflow fields](#Warehouse_Equipment_Workflow_fields).
4.  To set the frequency at which the workflow is applied:
    1.  Click **Sampling and Criteria**. That Sampling and Criteria page is displayed.
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
        
    4.  In the attribute fields (related to the criteria type), enter the values that inventory must match for the workflow to be applied.
    5.  Click **Save**.

1.  To assign the processing points at which the application executes the workflow:
    1.  Click **Exit Points**. The Exit Points page is displayed.
    2.  In the **Available in** column, select the exit points to use.
    3.  Click **Save**.
2.  Click **Save**.

## Delete a warehouse equipment workflow

1.  Select **Configuration > Work > Warehouse Workflows > Warehouse Equipment Workflows**.
2.  In the grid, select the check box next to the warehouse equipment workflow to delete.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Warehouse Equipment Workflow fields

 
| Field | Description |
| --- | --- |
| Enable Workflow | If Enabled, users are prompted to perform the workflow according to the sampling, criteria, and exit points defined for the workflow.<br > If Disabled, you can still configure the workflow, but users are never prompted to perform it. |
| Master Workflow | Unique identifier for a workflow process. The master workflow defines the activity code that is logged for the workflow, tasks and instructions for completing the workflow, how the workflow is acknowledged, and the actions that take place upon completion of the workflow.<br > Every warehouse workflow is based on a master workflow. The warehouse workflow specifies the sampling, criteria, and exit points at which a master workflow is applied to specific entities (such as warehouse or transport equipment) or inventory. |
| Description | Text that further describes the master workflow. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
