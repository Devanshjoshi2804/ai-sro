---
title: "RF Operator Workflows"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/rf_operator_workflows.htm"
source: "/content/rf_operator_workflows.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Work"
  - "Warehouse Workflows"
  - "RF Operator Workflows"
sections:
  - "Example: RF operator workflow"
  - "RF operator workflow exit points"
  - "RF operator configuration criteria"
  - "Add or modify an RF operator workflow"
  - "Delete an RF operator workflow"
  - "RF Operator Workflow fields"
images: []
source_sha1: 7397584dea58c31427f520f3f66049f69d335400
---
# RF Operator Workflows

An RF operator workflow is the warehouse-specific configuration of a master workflow. It defines when and how often the master workflow is to be performed. Default RF operator workflows are configured for a specific user; for example, when a new or temporary employee performs RF receiving or RF picking, RF operator workflows enable you to validate the work prior to committing the work to storage or shipping.

RF operator workflows do not use workflow instructions or workflow instruction actions.

When you create an RF operator workflow, you specify the following attributes:

-   Master workflow that defines the activity that is logged when the workflow is performed, how the workflow is acknowledged, and the actions that take place upon completion of the workflow. See [Master Workflows](../workflows/master-workflows.md).
-   Sampling configuration that defines how often the application requires the workflow to be performed. See [Sampling Configurations](../workflows/sampling-configurations.md).
-   Exit points during warehouse processing at which the operator is prompted to perform the workflow. See [RF operator workflow exit points](#RF_operator_workflow_exit_points).

## Example: RF operator workflow

The following scenario illustrates the RF operator workflow process.

A facility has hired a new employee to perform receiving or picking work using an RF device. Prior to beginning the work, the supervisor creates a default workflow, specifically for the new RF operator, that directs the operator to deposit received or picked inventory to a specific location where it can be validated for accuracy by another worker before being put away.

The following steps illustrate the process flow:

1.  The new RF operator (for whom the workflow was created) identifies or picks inventory.
2.  The application executes the workflow based on the RF operator's user name and the type of work being performed.
3.  The workflow directs the operator to deposit the inventory to a specific location (identified on the workflow), where the pick or receiving work can be validated.
4.  One of the following actions occurs:
    -   The new RF operator takes the inventory to the directed location and deposits it. The application automatically completes the workflow.
    -   If the new RF operator overrides the location (directed by the workflow) and deposits the inventory to a different location, the application does not complete the workflow. Instead, the next time the inventory is picked up (by the same or another operator), the application directs the inventory to the location specified by the RF operator workflow.
5.  After the inventory is deposited to the directed location, an experienced employee prints the RF User Workflow Report and uses it to validate the inventory.
6.  Any authorized operator can then move the inventory to its destination location, such as to storage for inbound inventory or to staging for outbound inventory. This can be done using inventory move function from either the RF or a workstation.
    
    **Note**: Directed work is not automatically created to move the inventory from the validation P&D location to its next location, unless the location is part of a movement path and a work operation has been assigned to the zone.
    

## RF operator workflow exit points

An exit point is the processing point at which the application initiates any actions, such as workflows, associated with the exit point.

When you create a warehouse-specific RF operator workflow, you assign one or more exit points to the workflow. During warehouse processing, when the exit point occurs, the application prompts the operator to deposit the inventory to a specific location. When the operator deposits the inventory in the location specified by the workflow, the application completes the workflow.

**Note**: If the operator overrides the directed location and deposits the inventory elsewhere, the workflow is not completed. The next operator that attempts to move the inventory is directed to deposit it to the specified workflow location.

The following table identifies the RF operator workflow exit points.

 
| Exit point | Description |
| --- | --- |
| Deposit to Processing Movement Zone | Occurs when the operator moves inventory out of a source movement zone or into a destination movement zone. During configuration of the workflow, you specify the source or destination movement zones for which the workflow is initiated. You can also define one or more locations to which the operator is directed to deposit the inventory. |
| Receive Deposit | Occurs when the operator completes identifying inventory. During configuration of the workflow, you can specify one or more locations to which the operator is directed to deposit the inventory. |

## RF operator configuration criteria

The application uses the criteria that you specify for a warehouse-specific RF operator workflow to select the operator to whom the workflow is applied.

The following table identifies the criteria that can be applied to a warehouse-specific RF operator workflow.

 
| Criteria | Application |
| --- | --- |
| User ID | All selected users. |

## Add or modify an RF operator workflow

1.  Select **Configuration > Work > Warehouse Workflows > RF Operator Workflows**.
2.  Perform one of the following tasks:
    -   To add a new RF operator workflow, click **Add**.
    -   To modify an RF operator workflow, in the grid, click the workflow.
    -   To copy an RF operator workflow, in the grid, select the check box next to the workflow, and then click **Copy**.
3.  Enter information in the [RF Operator Workflow fields](#RF_Operator_Workflow_fields).
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
        
    4.  In the attribute fields (related to the criteria type), enter the RF operator to whom the workflow is applied. For more information, see [RF operator configuration criteria](#RF_operator_configuration_criteria).
    5.  Click **Save**.
5.  To assign the processing points at which the application executes the workflow:
    
    1.  Under **EXIT POINTS**, click **Exit Points**. The Exit Points page is displayed.
    2.  In the **Available in** column, select the check box next to the exits points to use.
    
    1.  To specify the movement zones for which the workflow is initiated when inventory is moved:
        
        **Note**: This configuration is only available for exit points (such as Deposit to Processing Movement Zone) that require a source or destination zone.
        
        1.  In the **Selected** column, click **Configure Zones** or, if zones have already been added, click **Add**.
        2.  Enter information in the following fields:
            
            | Field | Description |
            | --- | --- |
            | Source Zone | Movement zone from which the inventory is moved. The operator is prompted to perform the workflow when inventory is moved out of the zone. If the workflow exit point requires a destination zone and you select a destination zone, then you can leave the **Source Zone** field blank to indicate any movement zone. The **Source Zone** is only available if the workflow exit point requires a source zone. |
            | Destination Zone | Movement zone to which inventory is deposited. The operator is prompted to perform the workflow when inventory is deposited to the zone. If the workflow exit point requires a source zone and you select a source zone, then you can leave the **Destination Zone** field blank to indicate any area. The **Destination Zone** is only available if the workflow exit point requires a destination zone. |
            
        3.  Click **Apply** or **Apply & Add Another**.
    
    1.  To specify the locations to which the operator is directed to deposit inventory:
        
        **Note**: This configuration is only available for exit points (such as Receive Deposit and Deposit to Processing Movement Zone) that can be used to direct an operator to a deposit location.
        
        1.  In the **Selected** column, click **Configure Locations** or, if locations are already displayed, click **Locations**.
        2.  In the **Available** column, select the locations that apply.
        3.  Click **Apply**.
    
    1.  Click **Apply**.

1.  Click **Save**.

## Delete an RF operator workflow

1.  Select **Configuration > Work > Warehouse Workflows > RF Operator Workflows**.
2.  In the grid, select the check box next to the RF operator workflow to delete.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## RF Operator Workflow fields

 
| Field | Description |
| --- | --- |
| Enable Workflow | If Enabled, the application executes the workflow according to the sampling, criteria, and exit points defined for the workflow.<br > If Disabled, you can still configure the workflow, but it will not be executed or performed. |
| Master Workflow | Unique identifier for a workflow process. The master workflow defines the activity code that is logged for the workflow, tasks and instructions for completing the workflow, how the workflow is acknowledged, and the actions that take place upon completion of the workflow.<br > Every warehouse workflow is based on a master workflow. The warehouse workflow specifies the sampling, criteria, and exit points at which a master workflow is applied to specific entities (such as warehouse or transport equipment) or inventory. |
| Description | Text that further describes the master workflow. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
