---
title: "Procedures for workflows"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/procedures_for_workflows.htm"
source: "/content/procedures_for_workflows.htm"
toc_path:
  - "Warehouse Management"
  - "Shared functions"
  - "Workflows"
  - "Procedures for workflows"
sections:
  - "Confirm a workflow"
  - "Manually perform a workflow"
  - "Reverse a confirmed workflow"
  - "Assign a user or role to perform a workflow"
  - "View workflows"
  - "Inbound Workflow fields"
  - "Outbound Workflow fields"
  - "Equip/Production Workflow fields"
  - "Background Workflow fields"
  - "RF Operator Workflow fields"
images: []
source_sha1: 43477668191d51c4722fbdd930a2d031b8830acc
---
# Procedures for workflows

You can perform these procedures using the Workflows page, which is accessible from the following modules: **Inventory**, **Picking**, **Production**, **Receiving**, **Shipping**, or **Yard**.

## Confirm a workflow

1.  If you are prompted to confirm a workflow, perform one of the following tasks:
    -   To continue without completing the workflow, in the **Perform Workflow** field, select **No**, and then click **Complete**. The workflow remains incomplete and is displayed on the In Process tab.
        
        **Note**: If, during warehouse operations, you are prompted to perform a required workflow, and you set the **Perform Workflow** field to No, you are returned to the same workflow execution page until it is complete. You cannot continue with the warehouse process until you perform the workflow.
        
    -   To acknowledge that you will perform the workflow, in the **Perform Workflow** field, select **Yes**. If the workflow includes instructions, the configured user instructions are displayed.
2.  To complete a workflow having no user instructions, click **Complete**.
3.  To complete a workflow having user instructions that do not require a response, click **Complete**.
4.  To complete a workflow having user instructions:
    
    **Note**: You may click **Cancel** at any time while performing inbound or outbound user instructions, or non-inventory user instructions for work orders or work order details. In those cases, if you click **Cancel** in the middle of a series of user instructions, the associated workflow will not be marked as completed successfully, even if you complete some of the user instructions. You cannot cancel a warehouse equipment workflow; you must complete it.
    
    1.  To answer all instructions at once with a single selection, select **Yes to All**.
        
        **Note**: This check box is available only if your application is configured to display it.
        
    2.  To pass a user instruction, select **Yes**.
    3.  To fail a user instruction, select **No**.
        
        **Note**: If you complete a workflow with a No response to any instruction, the workflow is marked as FAIL.
        
    4.  Continue performing the user instructions until you have performed all of them.
    5.  Click **Complete**.
        
        **Note**: Based on your responses to the user instructions, the application may trigger a corresponding action. The triggered action may execute a web form, generate an Event Management alert, print a report, run a MOCA command, change the status of inventory, or apply a hold to inventory on the current LPN.
        
    6.  If the workflow is configured to prompt for values, enter the requested information in the fields.
    7.  Click **OK**.
        
        **Notes**: Based on the application configuration, you may encounter the following scenarios:
        
        -   If the application is configured to reschedule the workflow on failure, the workflow and its configured user instructions are displayed until the workflow is successfully completed.
        -   If the application is configured to fail the workflow if the response to a user instruction is No, then the subsequent user instructions cannot be performed.
        

## Manually perform a workflow

Use this procedure to perform workflows that have been skipped or added after the workflow exit point has passed (meaning the application will not automatically prompt you to confirm the workflow).

1.  View the Workflows page.
    
    1.  Select one of the following modules: **Inventory,** **Picking,** **Production,** **Receiving,** **Shipping,** or **Yard**.
        
    2.  Select **Workflows**.
        
    
2.  Select the type of workflow to perform (**Inbound**, **Outbound**, or **Equip/Production**) and then select **In Process**.
3.  In the grid, select the row for the workflow to perform.
4.  Click **Perform Workflow**.
    
    **Note**: If you are performing an Inbound workflow, then you must select **Perform Workflow** from the **Actions** drop-down list. If **Perform Workflow** is not enabled, then you have selected a workflow that has already been acknowledged.
    
5.  [Confirm a workflow](#Confirm_a_workflow).

## Reverse a confirmed workflow

After a workflow is confirmed, you may need to reverse the confirmation because it was incorrectly applied, needs to be reapplied, or to handle errors.

**IMPORTANT**: Reversing a workflow only changes the workflow from being completed back to in process. It does not undo any workflow instruction actions that were performed when the workflow was originally completed.

1.  View the Workflows page.
    
    1.  Select one of the following modules: **Inventory,** **Picking,** **Production,** **Receiving,** **Shipping,** or **Yard**.
        
    2.  Select **Workflows**.
        
    
2.  Select the type of workflow to perform (**Inbound**, **Outbound**, or **Equip/Production**).
3.  Perform one of the following tasks:
    
    -   To reverse a workflow that failed, select **Failed**.
    -   To reverse a workflow that passed, select **History**.
    
    **Note**: You can also reverse a failed workflow from the **History** tab.
    
4.  Select the row of the workflow to reverse, and then click **Reverse Workflow**. A confirmation message is displayed.

**Note**: If you are reversing an Inbound workflow, then you must select **Reverse Workflow** from the **Actions** drop-down list.

6.  Click **OK**. The workflow is reversed and is displayed on the **In Process** tab.

## Assign a user or role to perform a workflow

You use this procedure to limit the user or role to which the application presents an incomplete inbound workflow for inventory received through an inbound shipment. When the assigned user (or a user within the assigned role) logs in to an RF device and selects directed work, the application prompts the user to perform the inbound workflow.

**IMPORTANT**: The operator and the equipment that the operator is logged in on must be authorized to perform the operation (INBSERV operation) before the application will prompt the operator to complete the workflow.

1.  View the Workflows page.
    
    1.  Select one of the following modules: **Inventory,** **Picking,** **Production,** **Receiving,** **Shipping,** or **Yard**.
        
    2.  Select **Workflows**.
        
    
2.  Select **Inbound**, and then select **In Process**.
3.  In the grid, select the row for the workflow to assign.
4.  From the **Actions** drop-down list, perform one of the following tasks:
    -   To assign a user, select **Assign User**. The Inbound Workflow Assign User window is displayed.
    -   To assign a role, select **Assign Role**. The Inbound Workflow Assign Role window is displayed.
5.  Select the user or role to perform the workflow, and then click **OK**. Directed work is created, which you can view on the Work Queue page.

## View workflows

1.  View the Workflows page.
    
    1.  Select one of the following modules: **Inventory,** **Picking,** **Production,** **Receiving,** **Shipping,** or **Yard**.
        
    2.  Select **Workflows**.
        
    
2.  To view inbound workflows, select **Inbound**, and view information in the [Inbound Workflow fields](#Inbound_workflow_fields). Select **Planned**, **In Process**, **Failed**, or **History** to view the workflows in each processing state. See [Workflows](../workflows.md).
3.  To view outbound workflows, select **Outbound**, and view information in the [Outbound Workflow fields](#Outbound_workflow_fields). Select **Planned**, **In Process**, **Failed**, or **History** to view the workflows in each processing state.
4.  To view equipment or production workflows, select **Equip/Production**, and view information in the [Equip/Production Workflow fields](#Equip/Production_workflow_fields). Select **In Process**, **Failed**, or **History** to view the workflows in each processing state.
5.  To view background workflows, select **Background**, and view information in the [Background Workflow fields](#Background_workflow_fields).
6.  To view RF operator workflows, select **RF Operator**, and view information in the [RF Operator Workflow fields](#RF_Operator_workflow_fields).

## Inbound Workflow fields

 
| Field | Description |
| --- | --- |
| Added | Date and time when the workflow request was initiated by the application. |
| Workflow | Identifier for a workflow process. |
| Workflow Rate | Sampling rate to be applied on LPNs for the workflow. The rate is a percentage (such as 10, 25, or 50 percent) of a quantity of LPNs. For example, if you define a sampling rate of 25% for the first 200 LPNs that are processed for an inbound shipment, then the application prompts the user to perform the workflow on a random selection of 50 LPNs out of the 200 that are processed. |
| Required | A check mark in this column indicates that the user is required to complete the workflow before returning to their interrupted work. If the user does not complete the workflow, the application does not allow the user to continue to process the inventory. |
| Shipment | Unique identifier for an outbound shipment. A shipment is a group of orders or order lines that are allocated together and shipped to the same location. |
| Planned Order | Identifier for an inbound order that is associated with a specific supplier. |
| Order Line | Unique number that identifies the order line. The number corresponds to the line's position on the order. The first order line is automatically assigned a line number of 0001. Additional order lines are then automatically numbered sequentially, beginning with 0002. |
| Supplier | Identifier for a supplier. A supplier can be an individual, organization, or another warehouse within your own organization from which you repeatedly receive inventory or handling units. |
| LPN | Unique identifier for inventory. Typically, an LPN refers to a pallet; however, it can refer to inventory received at less than pallet quantity. The LPN is the license plate by which the inventory is tracked in the facility. |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Client | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. |
| Progress | Percentage of inventory for which the workflow has been performed. Additionally, an X of Y value displays the quantity of inventory for which the workflow has been performed out of the total quantity; for example, (50 of 100). |
| Quantity | Quantity of inventory on which the workflow has been performed. |
| User | User that is performing (or performed) the workflow. |
| Device | Identifier for the RF device or workstation on which the workflow is being (or was) performed. |
| Completed | Date and time at which the workflow was completed. |
| Exit Point | Point in the warehouse process at which the application executes workflows to which the exit point has been assigned. |
| Results | Execution status of the workflow (PASS or FAIL). |
| Instruction | Instruction for the RF operator performing the workflow. |
| Sequence Number | Number that defines the sequence in which the application processes the list of instructions. The application prompts the instructions in sequential order (starting with 1) to the RF operator. |
| Instruction Type | Type of action performed by an RF operator in response to a workflow instruction. |
| Response | Answer provided by the RF operator for the workflow instruction. |
| Prompt | Value provided by an RF operator for the configured prompt variable during the completion of a workflow instruction. |
| Value Entered | Value entered by the user of the specified variable when the workflow has been performed. The field name of the variable is configured to display as a confirmation value (**Confirmation Value** is set to **Using the default "Confirmation Value" variable**) or a description of the specified variable (**Confirmation Value** is set to **Specify a prompt using an existing system variable**).<br > The **Confirmation Value** field is configured for a master workflow. |

## Outbound Workflow fields

 
| Field | Description |
| --- | --- |
| Added | Date and time when the workflow request was initiated by the application. |
| Workflow | Identifier for a workflow process. |
| Workflow Rate | Sampling rate to be applied on LPNs for the workflow. The rate is a percentage (such as 10, 25, or 50 percent) of a quantity of LPNs. For example, if you define a sampling rate of 25% for the first 200 LPNs that are processed for an inbound shipment, then the application prompts the user to perform the workflow on a random selection of 50 LPNs out of the 200 that are processed. |
| Required | A check mark in this column indicates that the user is required to complete the workflow before returning to their interrupted work. If the user does not complete the workflow, the application does not allow the user to continue to process the inventory. |
| Load | Unique identifier for a load. A load is one or more shipments grouped together into one or more stops that are shipped on a single piece of transport equipment. |
| Shipment | Unique identifier for an outbound shipment. A shipment is a group of orders or order lines that are allocated together and shipped to the same location. |
| Order | Unique number that identifies an order. An order is a request for a supply of material or product. |
| Order Line | Unique number that identifies the order line. The number corresponds to the line's position on the order. The first order line is automatically assigned a line number of 0001. Additional order lines are then automatically numbered sequentially, beginning with 0002. |
| LPN | Unique identifier for inventory. Typically, an LPN refers to a pallet; however, it can refer to inventory received at less than pallet quantity. The LPN is the license plate by which the inventory is tracked in the facility. |
| Item | Identifier for the item being processed and shipped from the warehouse. |
| Client | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. |
| Route to | Name and address of the distributor or organization to which the shipment is initially sent. |
| Departure Time | Date and time that the transport equipment associated with a load is scheduled to depart from the warehouse. |
| Progress | Percentage of inventory for which the workflow has been performed. Additionally, an X of Y value displays the quantity of inventory for which the workflow has been performed out of the total quantity; for example, (50 of 100). |
| Quantity | Quantity of inventory on which the workflow has been performed. |
| Exit Point | Point in the warehouse process at which the application executes workflows to which the exit point has been assigned. |
| User | User that is performing (or performed) the workflow. |
| Device | Identifier for the RF device or workstation on which the workflow is being (or was) performed. |
| Completed | Date and time at which the workflow was completed. |
| Results | Execution status of the workflow (PASS or FAIL). |
| Instruction | Instruction for the RF operator performing the workflow. |
| Sequence Number | Number that defines the sequence in which the application processes the list of instructions. The application prompts the instructions in sequential order (starting with 1) to the RF operator. |
| Instruction Type | Type of action performed by an RF operator in response to a workflow instruction. |
| Response | Answer provided by the RF operator for the workflow instruction. |
| Prompt | Value provided by an RF operator for the configured prompt variable during the completion of a workflow instruction. |
| Value Entered | Value entered by the user of the specified variable when the workflow has been performed. The field name of the variable is configured to display as a confirmation value (**Confirmation Value** is set to **Using the default "Confirmation Value" variable**) or a description of the specified variable (**Confirmation Value** is set to **Specify a prompt using an existing system variable**).<br > The **Confirmation Value** field is configured for a master workflow. |

## Equip/Production Workflow fields

 
| Field | Description |
| --- | --- |
| Added | Date and time when the workflow request was initiated by the application. |
| Workflow | Identifier for a workflow process. |
| Exit Point | Point in the warehouse process at which the application executes workflows to which the exit point has been assigned. |
| Required | A check mark in this column indicates that the user is required to complete the workflow before returning to their interrupted work. If the user does not complete the workflow, the application does not allow the user to continue to process the inventory. |
| Equipment Type | Type of equipment on which the workflow is being (or was) performed, such as transport equipment or warehouse equipment. |
| Equipment | Identifier for the equipment on which the workflow is being (or was) performed. |
| Carrier | Identifier for a carrier that delivers inbound inventory to the warehouse or outbound shipments to a customer. This is the identifier that will be displayed to users on the application windows and reports. In the application, a carrier can be associated with a customer, order, inbound shipment, outbound shipment, load, and service levels (such as Ground, Next Day, and Saturday Delivery). |
| Item | Identifier for the item being processed and shipped from the warehouse. |
| User | User that is performing (or performed) the workflow. |
| Device | Identifier for the RF device or workstation on which the workflow is being (or was) performed. |
| Work Order | Identifier for a work order. A work order is an internal order used to find, allocate, and deliver product to a work-in-process area for assembly or disassembly, conversion, kitting, or repackaging. |
| Work Order Revision | Identifier for one instance of a work order that allows you to use a standard work order multiple times. |
| Work Order Line | Unique identifier for a work order line. The number corresponds to the order line's position in the work order. |
| Results | Execution status of the workflow (PASS or FAIL). |
| Instruction | Instruction for the RF operator performing the workflow. |
| Sequence Number | Number that defines the sequence in which the application processes the list of instructions. The application prompts the instructions in sequential order (starting with 1) to the RF operator. |
| Instruction Type | Type of action performed by an RF operator in response to a workflow instruction. |
| Response | Answer provided by the RF operator for the workflow instruction. |
| Prompt | Value provided by an RF operator for the configured prompt variable during the completion of a workflow instruction. |
| Value Entered | Value entered by the user of the specified variable when the workflow has been performed. The field name of the variable is configured to display as a confirmation value (**Confirmation Value** is set to **Using the default "Confirmation Value" variable**) or a description of the specified variable (**Confirmation Value** is set to **Specify a prompt using an existing system variable**).<br > The **Confirmation Value** field is configured for a master workflow. |

## Background Workflow fields

 
| Field | Description |
| --- | --- |
| Added | Date and time when the workflow request was initiated by the application. |
| Workflow | Identifier for a workflow process. |
| Exit Point | Point in the warehouse process at which the application executes workflows to which the exit point has been assigned. |
| Equipment Number | Identifier for the equipment used in the workflow. |
| Shipment | Unique identifier for an outbound shipment. A shipment is a group of orders or order lines that are allocated together and shipped to the same location. |
| Stop | Unique identifier for a stop. A stop is a collection of one or more outbound shipments making up a delivery to a single customer. |
| PRO Number | Progressive routing order (PRO) number assigned to a load, shipment, or stop. A PRO number is assigned as a reference to a shipment for a carrier, and is used by the carrier for most correspondence in relation to tracking the shipment. |
| LPN | Unique identifier for inventory. Typically, an LPN refers to a pallet; however, it can refer to inventory received at less than pallet quantity. The LPN is the license plate by which the inventory is tracked in the facility. |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Quantity | Quantity of inventory on which the workflow has been performed. |
| Carton | Unique identifier for a carton involved in the workflow. A carton is a corrugated box or container of any size that serves as packaging for an items. |
| Source | Location where the workflow originated. |
| Destination | Identifier for the location where the workflow was completed. |
| User | User that is performing (or performed) the workflow. |

## RF Operator Workflow fields

 
| Field | Description |
| --- | --- |
| Added | Date and time when the workflow request was initiated by the application. |
| Workflow | Identifier for a workflow process. |
| Exit Point | Point in the warehouse process at which the application executes workflows to which the exit point has been assigned. |
| Required | A check mark in this column indicates that the user is required to complete the workflow before returning to their interrupted work. If the user does not complete the workflow, the application does not allow the user to continue to process the inventory. |
| User | User that is performing (or performed) the workflow. |
| Device | Identifier for the RF device or workstation on which the workflow is being (or was) performed. |
| Completed | Date and time at which the workflow was completed. |
| Supplier | Identifier for a supplier. A supplier can be an individual, organization, or another warehouse within your own organization from which you repeatedly receive inventory or handling units. |
| Inbound Shipment | Unique identifier used for inventory tracking for an inbound shipment of inventory. An inbound shipment is a group of orders that are transported to the warehouse together or received together. When inventory arrives at the warehouse on a piece of transport equipment, an inbound shipment represents the contents of the transport equipment; however, one or more inbound shipments can be associated with a piece of transport equipment. |
| Inbound Order | Identifier for an inbound order or planned inbound order that is associated with a specific supplier. |
| Inbound Order Line | Unique identifier for an inbound order line. The order line is the section of an order that provides detailed information about an individual item that the order requests. |
| Outbound Load | Unique identifier for a load. A load is one or more shipments grouped together into one or more stops that are shipped on a single piece of transport equipment. |
| Shipment | Unique identifier for an outbound shipment. A shipment is a group of orders or order lines that are allocated together and shipped to the same location. |
| Outbound Order | Unique identifier for an outbound order. An order is a request for a supply of material or product. |
| Outbound Order Line | Identifier for an outbound order line. |
| LPN | Unique identifier for inventory. Typically, an LPN refers to a pallet; however, it can refer to inventory received at less than pallet quantity. The LPN is the license plate by which the inventory is tracked in the facility. |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Client | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. |
| Route to | Name and address of the distributor or organization to which the shipment is initially sent. |
| Quantity | Quantity of inventory on which the workflow has been performed. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
