---
title: "Production Workflows"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/production_workflows.htm"
source: "/content/production_workflows.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Work"
  - "Warehouse Workflows"
  - "Production Workflows"
sections:
  - "Examples: Production workflows"
  - "Production workflow exit points"
  - "Production configuration criteria"
  - "Add or modify a production workflow"
  - "Delete a production workflow"
  - "Production Workflow fields"
images: []
source_sha1: 9dbe6bc631aca0cbaa7d708dff59d1aac34962b9
---
# Production Workflows

A production workflow is the warehouse-specific configuration of a master workflow. It defines when and how often the master workflow is to be performed on a bill of material (BOM), work order, component item, top-level item, or production station. Like inbound and outbound workflows, production workflows can be performed manually and can be canceled by an operator.

When you create a production workflow, you specify the following attributes:

-   Master workflow that defines the activity that is logged when the workflow is performed, how the workflow is acknowledged, whether an operator can select "yes to all" when answering multiple questions in a workflow, the questions presented to the operator who performs the workflow, and the actions that take place upon completion of the workflow. See [Master Workflows](../workflows/master-workflows.md).
-   Sampling configuration that defines how often the application requires the workflow to be performed. See [Sampling Configurations](../workflows/sampling-configurations.md).
-   Exit points during warehouse processing at which the operator is prompted to perform the workflow. See [Production workflow exit points](#Production_workflow_exit_points).

## Examples: Production workflows

Production workflows can be configured to prompt or direct operators through the completion of the following processes:

-   Installing a component into a top-level item at a specific production station
-   Performing special handling instructions of component items prior to moving a work order to a different production line
-   Performing production line setup tasks prior to starting work orders generated from a specific bill of material (BOM)

## Production workflow exit points

An exit point is the processing point at which the application initiates any actions, such as workflows, associated with the exit point.

When you create a warehouse-specific production workflow, you assign one or more exit points to the workflow. During warehouse processing, when the exit point occurs, the application prompts the operator to complete the workflow.

**Note**: If a workflow is required and the user does not perform the workflow, the work will not be completed.

The following table identifies the production workflow exit points.

 
| Exit point | Description |
| --- | --- |
| Close Work Order | Occurs when the user closes a work order. |
| Move Work Order | Occurs when the user moves a work order to a different production line. |
| Work Order Process | Occurs when the user performs a production station workflow. |
| Work Order Start | Occurs when the user starts a work order. |
| Work Order Stop | Occurs when the user stops a work order. |

## Production configuration criteria

The application uses the criteria that you specify for a warehouse-specific production workflow to select a bill of material (BOM), work order, component item, top-level item, or production station to which the workflow is applied.

The following table identifies the criteria that can be applied to a warehouse-specific production workflow.

 
| Criteria | Application |
| --- | --- |
| Bill of Material | All work orders generated from the bill of material (BOM) with the specified BOM number. For example, you want to display the assembly instructions every time an operator starts a work order generated from the BOM. |
| Bill of Material Detail | All work order details generated from the BOM detail with the specified BOM number and BOM line number. |
| Component | All component items with the specified item and, for a 3PL environment, item client. For example, you want to display special handling instructions whenever an operator moves the component item's work order to a different production line. |
| Finish Good | All top-level items with the specified item and, for a 3PL environment, item client. |
| Item Class | All work orders with the items assigned to the selected item class. |
| Work Order | All work orders with the specified work order number and revision. |
| Work Order Detail | All work order details with the specified work order number, revision and work order line. For example, you want to display component item preparation instructions every time an operator starts a certain work order. |

## Add or modify a production workflow

1.  Select **Configuration > Work > Warehouse Workflows > Production Workflows**.
2.  Perform one of the following tasks:
    -   To add a new production workflow, click **Add**.
    -   To modify an production workflow, in the grid, click the workflow.
    -   To copy an production workflow, in the grid, select the check box next to the workflow, and then click **Copy**.
3.  Enter information in the [Production Workflow fields](#Production_Workflow_fields).
4.  To set the frequency at which the workflow is applied to inventory matching specific criteria:
    1.  Under **CRITERIA**, click **Sampling and Criteria**. The Sampling and Criteria page is displayed.
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
        
    4.  In the inventory attribute fields (related to the criteria type), enter the values that inventory must match for the workflow to be applied. See [Production configuration criteria](#Production_configuration_criteria).
    5.  Click **Save**.

1.  To assign the processing points at which the application executes the workflow:
    1.  Click **Exit Points**. The Exit Points page is displayed.
    2.  In the **Available in** column, select the exit points to use.
    3.  Click **Save**.
2.  Click **Save**.

## Delete a production workflow

1.  Select **Configuration > Work > Warehouse Workflows > Production Workflows**.
2.  In the grid, select the check box next to the production workflow to delete.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Production Workflow fields

 
| Field | Description |
| --- | --- |
| Enable Workflow | If Enabled, users are prompted to perform the workflow according to the sampling, criteria, and exit points defined for the workflow.<br > If Disabled, you can still configure the workflow, but users are never prompted to perform it. |
| Master Workflow | Unique identifier for a workflow process. The master workflow defines the activity code that is logged for the workflow, tasks and instructions for completing the workflow, how the workflow is acknowledged, and the actions that take place upon completion of the workflow.<br > Every warehouse workflow is based on a master workflow. The warehouse workflow specifies the sampling, criteria, and exit points at which a master workflow is applied to specific entities (such as warehouse or transport equipment) or inventory. |
| Description | Text that further describes the master workflow. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
