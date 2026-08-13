---
title: "Master Workflows"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/master_workflows.htm"
source: "/content/master_workflows.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Work"
  - "Workflows"
  - "Master Workflows"
sections:
  - "Workflow types"
  - "Workflow instructions"
  - "Instruction and workflow actions"
  - "Add or modify a master workflow"
  - "Delete a master workflow"
  - "Master Workflow fields"
  - "Workflow Instruction fields"
  - "Instruction Action fields"
  - "Workflow Action fields"
images: []
source_sha1: aebd5a56367fa2ca3634f7be4cab6171a93b0512
---
# Master Workflows

A master workflow is a high-level configuration of a workflow process. The master workflow specifies a workflow type, how it is completed (confirmed), instructions that are displayed to users during the performance of the workflow, and actions resulting from the completion of individual instructions or the workflow itself.

For example, a master workflow can be configured to prompt users to perform a safety check on transport equipment. This workflow defines the activity that is logged when a user performs a safety check, the questions presented to the user, and the action that occurs (updates the equipment's safety status) based on how the questions are answered.

After you define master workflows, you can configure warehouse workflows. A warehouse workflow is a master workflow that is configured and enabled for a specified warehouse. For example, you can create a warehouse workflow based on the transport equipment safety check master workflow, and configure it so that a user is prompted to perform it whenever transport equipment is moved to a dock door. The workflow is prompted only in the warehouses for which it is enabled.

You configure workflows when you want automatic processes to take place or to be prompted at one or more points during the course of warehouse processing tasks.

## Workflow types

A workflow type is an application-defined category that determines how the application processes the workflow operations.

The application supports the following types of workflows:

-   **Inbound**: Used for operations performed on inventory that is received from an external source, typically prior to the inventory being stored or cross docked. See [Inbound Workflows](../warehouse-workflows/inbound-workflows.md).
-   **Outbound**: Used for operations performed on picked inventory prior to loading. See [Outbound Workflows](../warehouse-workflows/outbound-workflows.md).
-   **Production**: Used for operations performed on a bill of material, work order, component item, top-level item, or production station. See [Production Workflows](../warehouse-workflows/production-workflows.md).
-   **Warehouse Equipment**: Used for operations performed on a bill of material (BOM), work order, component item, top-level item, production station, or vehicle. See [Warehouse Equipment Workflows](../warehouse-workflows/warehouse-equipment-workflows.md).
-   **Transport Equipment**: Used for operation performed on inbound and outbound transport equipment, such as receiving and shipping trailers. See [Transport Equipment Workflows](../warehouse-workflows/transport-equipment-workflows.md).
-   **RF Operator**: Used to validate the receiving and picking activities of an RF operator by directing the operator to deposit inbound or picked inventory to a pickup and deposit location where it can be verified before being directed to its final destination. See [RF Operator Workflows](../warehouse-workflows/rf-operator-workflows.md).
-   **Background**: Used for an operation that is performed by the application without visual interaction with a user and as the result of internal application processes, such as printing labels, producing shipment documentation, and performing validations to meet the customer's specifications. See [Background Workflows](../warehouse-workflows/background-workflows.md).

## Workflow instructions

A workflow instruction is a single task in a workflow that either prompts the user to complete an action (such as "Apply tag to garment.") or asks the user a question ("Is the quantity correct?").

When a question is asked or a confirmation is required, the user's response determines whether the instruction passes or fails.

You can associate one or more instructions with a master workflow. You configure each instruction with the following attributes:

-   Whether the instruction requires a user response, such a confirmation (typically by pressing Enter) or answer (yes or no) to a question.
-   Whether the workflow is stopped when an instruction fails. For example, if the user fails to apply a tag to a garment, you may not want the user to perform the next instruction action of wrapping the garment; therefore, if the instruction to tag the garment is not confirmed, then the workflow is stopped.
-   Actions that take place based on the user's response or whether the instruction passed or failed. Actions include changing inventory status, creating a hold for inventory, displaying a different screen to the user, printing a report, generating an Event Management alert (if Warehouse Management is integrated with Event Management), or executing a command. You can associate a different action with each type of response (yes or no).
-   A workflow instruction can be associated with one or more master workflows.

## Instruction and workflow actions

An action is a process that takes place (such as printing a report or putting inventory on hold) when a workflow or instruction passes or fails, based on the user response. You create and associate actions with instructions and workflows during the configuration of a master workflow.

To specify when the action occurs, you must associate each action with one of the following results:

-   **Pass**: The action occurs because the user entered a positive response to the instruction or workflow.
-   **Fail**: The action occurs because user entered a negative response to the instruction or workflow.

You can configure one or more of the following actions for each instruction and workflow:

-   **Create Inventory Hold:** For instruction actions, creates an inventory hold; for example, to place a hold on inventory that failed a QA test. Configuring this action code includes defining the hold number, hold reason, hold prefix and hold action and places the inventory on hold. This action is only available for workflows associated with inventory.
    
    The hold is applied based on one of the following options:
    
    -   **Current LPN Only**: Creates the hold only for this LPN.
    -   **Current LPN and all other inventory previously received against the same inbound shipment line**: Creates a hold for the current LPN and all LPNs that have already been received from the inbound shipment line.
    -   **Current LPN and all future inventory received against the same inbound shipment**: Creates a hold for the current LPN and a future hold against any other LPNs for the item that will be received from the inbound shipment line.
    
-   **Execute Form**: For instruction actions, displays an RF screen or application window. For example, if the workflow instruction requires the user to retrieve the temperature of the inventory, you can configure the application to display a new screen or window that lets the user enter the temperature value. The application provides a standard workflow confirmation value RF screen and window that you can use to capture a 30-character response to your workflow instruction. The information entered then appears in displays.
    
-   **Generate EMS Event**: For both workflow and instruction actions, sends the Event Management event that you select. The event must be enabled in the application, and is only available if Warehouse Management is integrated with Event Management.
-   **Print Report**: For both workflow and instruction actions, prints the selected report.
-   **Run MOCA**: For both workflow and instruction actions, executes a server command; for example, to print a label.
-   **Status Change**: For instruction actions, changes the status of the inventory to the selected inventory status; for example, if an LPN passes QA inspection, you can direct the status to change to the Available status. This action is only available for workflows associated with inventory.

## Add or modify a master workflow

1.  Select **Configuration > Work > Workflows > Master Workflows**.
2.  Perform one of the following tasks:
    -   To add a master workflow, click **Add**.
    -   To modify a master workflow, in the grid, click the workflow.
    -   To copy a new master workflow, in the grid, select the check box next to the workflow, and then click **Copy**.
3.  Enter information in the [Master Workflow fields](#Master_Workflow_fields).
4.  To configure the instructions that will be presented to the user:
    1.  Under **INSTRUCTIONS**, click **User Instructions**.
    2.  Perform one of the following tasks:
        -   To add an instruction, click **Add**.
        -   To modify an instruction, in the grid, click the instruction.
    3.  Enter information in the [Workflow Instruction fields](#Workflow_Instruction_fields).
    4.  To configure the actions to be executed based on how the user responds:
        1.  Under **ACTIONS**, click **Instruction Actions**.
        2.  Perform one of the following tasks:
            -   To add an instruction action, click **Add**.
            -   To modify an instruction action, in the grid, click the instruction action.
        3.  Enter information in the [Instruction Action fields](#Instruction_Action_fields).
        4.  Click **Save**.
    5.  Click **Save**.
5.  To configure actions to be executed based on the overall results of all instructions in the workflow:
    1.  Under **RESULTS**, click **Workflow Actions**.
    2.  Perform one of the following tasks:
        -   To add a workflow action, click **Add**.
        -   To modify a workflow action, in the grid, click the action.
    3.  Enter information in the [Workflow Action fields](#Workflow_Action_fields).
    4.  Click **Save**.
6.  Click **Save**.

## Delete a master workflow

1.  Select **Configuration > Work > Workflows > Master Workflows**.
2.  In the grid, select the check box next to the master workflow to delete.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Master Workflow fields

 
| Field | Description |
| --- | --- |
| Workflow Name | Name of the master workflow. A master workflow defines the activity code that is logged for the workflow, tasks and instructions for completing the workflow, how the workflow is acknowledged, and the actions that take place upon completion of the workflow. |
| Description | Text that further describes the master workflow. This description is displayed to users that are prompted to perform the workflow. |
| Activity Code | Activity that the application records in the work history, once the user has completed the warehouse workflow. When a user completes a workflow, the application adds information about the workflow to the daily transaction log. If an activity code is defined for the workflow, the activity is included in the daily transaction information. |
| Type | Value that defines the kind of warehouse workflow and is used by the application to limit the options available for selection to only those options that apply to the type of workflow.<br > **Note**: This value cannot be changed after it is selected and the workflow is saved.<br>-   • **Production**: An operation that is performed on a bill of material (BOM), work order, component item, top-level item, or production station.
<br>-   • **Background**: An operation that is performed by the application for internal application processes, such as automatically printing labels, producing shipment documentation, or sending Event Management notifications.
<br>-   • **Inbound**: An operation that is performed on inventory that is received from an external source, such as supplier. Inbound workflows are performed on inventory associated with an inbound order or order line, and can be configured to be performed during inventory identification or putaway.
<br>-   • **Outbound**: An operation that is performed on inventory that is being moved from a picking location to transport equipment. Outbound workflows are performed on inventory associated with an outbound order or order line, and can be configured to be performed during picking.
<br>-   • **Transportation Equipment**: An operation that is performed on transport equipment. Many of these operations are based on safety checks or union and government compliance.
<br>-   • **RF User**: A validation operation configured for a specific user; for example, when a new or temporary employee performs RF receiving or RF picking, RF operator workflows enable you to validate the work prior to committing the work to storage or shipping.
<br>-   • **Warehouse Equipment**: An operation that is performed on mechanical or motorized devices (such as material handling equipment) within the warehouse. Many of these operations are based on safety checks or union and government compliance. |
| Image | Media tool that displays the image that is associated with the entity. If an image has not been associated with the entity, a default image is displayed. You can view an enlarged version of the image and, depending on the settings, you can add, change, or remove the associated image file. |
| User Acknowledgement | Determines whether a user action is required to start the workflow.<br>-   • **Automatically by the system**: The workflow starts automatically when the exit point occurs.
<br>-   • **Manually by the user pressing Enter**: The user is prompted to start the workflow when the exit point occurs and must press Enter to perform it. |
| Allow Yes to All | If Yes, then when there are multiple instructions in a workflow, the application provides the option to select **Yes to All**. Select Yes if you allow operators to respond to all of the Yes/No instructions at once with a single selection, which saves time.<br > If No, then when there are multiple instructions in a workflow, the user must respond to each instruction individually. |
| Reschedule Upon Failure | If Yes, the workflow is immediately rescheduled if the workflow fails. Select Yes, for example, if the workflow is required and you want to give the user another chance to perform it.<br > If No, the workflow is not rescheduled if the workflow fails. Select No, for example, if the workflow is not required and you do not require the workflow to pass. |

## Workflow Instruction fields

 
| Field | Description |
| --- | --- |
| Instruction | Instruction for the RF operator performing the workflow. If this workflow instruction requires a confirmation, then this is the text that is displayed to the user when the application prompts the user to perform the workflow instruction. |
| Confirmation | Value that defines how a user must respond to the workflow instruction.<br>-   • **Do not confirm**: No user interaction is required and therefore the instruction is never displayed to the user. Select this option, for example, for background workflows that do not require user interaction.
<br>-   • **Manually by the user pressing Enter**: A user must press **Enter** to acknowledge that the workflow instruction has been performed. Select this option, for example, for instructions that direct the user to perform an activity (such as applying a pallet label), but you not require a record that the user actually performed it by answering Yes.
<br>-   • **Manually by the user answering Yes or No**: A user must enter a response by answering Yes or No to the workflow instruction. Select this option, for example, if you want to record whether the user performed the instruction by answering Yes. This would be useful for an equipment or packaging inspection. |
| Discontinue Workflow On Fail | If Yes, then when an RF or Mobile device user responds no (fail) to an instruction, the application stops the workflow and does not display the remaining workflow instructions.<br > If No, if the user responds no (fail) to an instruction, the application continues to display the remaining workflow instructions. |

## Instruction Action fields

 
| Field | Description |
| --- | --- |
| Result | Value that specifies when the action should execute.<br>-   • **Pass**: The action executes when the workflow instruction passes.
<br>-   • **Fail**: The action executes if the workflow instruction fails. |
| Action | Value that determines the action that occurs when the instruction is completed.<br>-   • **Create Inventory Hold**: The application places a hold on the current LPN as defined by the hold parameters you enter.
<br>-   • **Execute Form**: The application displays a window as specified in the **RF Form** or **Web Form** field to allow entry of requested information.
<br>-   • **Generate EMS Event**: The application generates the Event Management event specified in the **EMS Event Name** field.
<br>-   • **Print Report**: The application prints the report as specified in the **Report Name** field.
<br>-   • **Run MOCA**: The application executes the MOCA command specified in the **Command** field, such as to update a transport equipment's safety status.
<br>-   • **Status Change**: The application changes the status of the inventory to the value specified in the **New Inventory Status** field. |
| New Inventory Status | Defines the quality or disposition of the inventory. The selected status is applied to the inventory on which the workflow was performed after the workflow instruction is completed. The **New Inventory Status** field is only available when **Status Change** is selected in the **Action** field. |
| RF Form | Name of the RF value confirmation form that is displayed during a workflow instruction to prompt a user to enter a confirmation value. The **RF Form** field is only available when **Execute Form** is selected in the **Action** field.<br > When **Execute Form** is selected, you must select either an RF Form, a Web Form, or both. |
| Web Form | Name of the web-based value confirmation form that is displayed during a workflow instruction to prompt a user to enter a confirmation value. If your Blue Yonder project team has not customized a web-based form for you, use **Value Entered**. The **RF Form** field is only available when **Execute Form** is selected in the **Action** field.<br > When **Execute Form** is selected, you must select either an RF Form, a Web Form, or both. |
| Confirmation Value | Name of the field (defined by a variable) that the application uses to store information that a user is prompted to enter during the performance of a workflow instruction. The **Confirmation Value** field is only available when **Execute Form** is selected from the **Action** list.<br > The application displays the confirmation value field on the selected forms (RF and workstation) based on the selected option.<br>-   • **Using the default "Confirmation Value" variable**: The value defined for the cnfrm\_val\_var\_nam variable is displayed on the selected form for user data entry.
<br>-   • **Specify a prompt using an existing system variable**: The value defined for the variable specified in the **Prompt** field is displayed on the selected for user data entry.
<br > **Note**: Variables are defined in the Variable Configuration pages. See [Variable Configuration](../../../../administration/system-administrator/configuration/variable-configuration.md). |
| Prompt | Name of an existing field (variable configuration) that the application uses to store information that a user enters during the completion of a workflow instruction. The application displays the selected field on the RF and workstation forms defined for the Execute Form action. For example, if you enter "ib\_issue", the operator performing the workflow is prompted with the "Issue" field.<br > The Prompt field is only available when **Specify a prompt using an existing system variable** is selected for the **Confirmation Value** field.<br > **Note**: Variables are defined in the Variable Configuration pages. See [Variable Configuration](../../../../administration/system-administrator/configuration/variable-configuration.md). |
| Post Processing Command | Server (MOCA) command that is processed when the user exits the RF or workstation form after entering a confirmation value for a workflow instruction. You can select a command, for example, that validates the data that the user entered for the confirmation value. The **Post Processing Command** field is only available when **Execute Form** is selected in the **Action** field. |
| EMS Event Name | Value that indicates the inbound shipment or inventory event that you want the application to send to Event Management after the user completes the workflow instruction. **EMS Event Name** is only available when **Generate EMS Event** is selected from the **Action** list. |
| Report Name | Unique identifier for a standard or custom inbound shipment or inventory report that you want the application to print after the workflow instruction is completed. The **Report Name** field is only available when **Print Report** is selected in the **Action** field. |
| Command | MOCA command that you want the application to carry out after the user completes the workflow instruction. The **Command** field is only available when **Run MOCA** is selected in the **Action** field. |
| Select the inventory that you would like to put on hold | Value that indicates the LPNs to which you want the hold applied, such as the current LPN only, the current LPN and all LPNs already received for the same inbound shipment line, or the current LPN and any future LPNs received for the same inbound shipment. These options are only available when **Create Inventory Hold** is selected in the **Action** field. |
| Hold | Unique identifier for a hold. A hold is an attribute of inventory independent of the inventory status associated with that inventory. A hold can indicate that inventory is not available for use or distribution. Optionally, a hold can be configured to allow inventory to which the hold is applied to be allocated and shipped.<br > The **Hold** field is only available when **Create Inventory Hold** is selected from the **Action** list. |
| Source | Prefix applied to the hold number. The hold source is typically site specific, and it distinguishes the holds placed on inventory at one site from holds placed on inventory at another site. The **Source** field is only available when **Create Inventory Hold** is selected in the **Action** field. |
| Reason | Value that indicates why you are applying an inventory hold. A reason is required whenever a hold is being applied to inventory. The **Reason** field is only available when **Create Inventory Hold** is selected in the **Action** field. |

## Workflow Action fields

 
| Field | Description |
| --- | --- |
| Result | Value that specifies when the action should execute.<br>-   • **Pass**: The action executes when the workflow instruction passes.
<br>-   • **Fail**: The action executes if the workflow instruction fails. |
| Action | Value that indicates the action that the application is to take.<br>-   • **Generate EMS Event**: The application generates the Event Management event specified from the **EMS Event Name** field.
<br>-   • **Print Report**: The application prints the report as specified in the **Report Name** field.
<br>-   • **Run MOCA**: The application runs the MOCA command specified in the **Command** field, such as updating a transport equipment's safety status. |
| EMS Event Name | Value that indicates the inbound shipment or inventory event that you want the application to send to Event Management after the user completes the workflow instruction. **EMS Event Name** is only available when **Generate EMS Event** is selected from the **Action** list. |
| Report Name | Unique identifier for a standard or custom inbound shipment or inventory report that you want the application to print after the workflow instruction is completed. The **Report Name** field is only available when **Print Report** is selected in the **Action** field. |
| Command | MOCA command that you want the application to carry out after the user completes the workflow instruction. The **Command** field is only available when **Run MOCA** is selected in the **Action** field. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
