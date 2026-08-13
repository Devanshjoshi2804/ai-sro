---
title: "Inbound Workflows"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/inbound_workflows.htm"
source: "/content/inbound_workflows.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Work"
  - "Warehouse Workflows"
  - "Inbound Workflows"
sections:
  - "Inbound workflow exit points"
  - "Inbound configuration criteria"
  - "Examples: Inbound workflows"
  - "Add or modify an inbound workflow"
  - "Delete an inbound workflow"
  - "Inbound Workflow fields"
images: []
source_sha1: 98e937af5937581107d9a89c5a127e0224526383
---
# Inbound Workflows

An inbound workflow is the warehouse-specific configuration of a master workflow. It defines when and how often the master workflow is to be performed on inventory that is received from an external source, such as a supplier. Inbound workflows are performed on inventory associated with an inbound order or order line, and can be configured to be performed during product identification or putaway.

After inbound workflows are defined, they can be added to an inbound workflow plan, which is used to associate workflows with specific inbound orders and order lines.

When you create an inbound workflow, you specify the following attributes:

-   Master workflow that defines the activity that is logged when the workflow is performed, how the workflow is acknowledged, whether an operator can select "yes to all" when answering multiple questions in a workflow, the questions presented to the operator who performs the workflow, and the actions that take place upon completion of the workflow. See [Master Workflows](../workflows/master-workflows.md).
-   Criteria for the inventory that requires the workflow, such as whether it is limited to mixed item LPNs, non-receivable items, or inventory with a specific inventory status.
-   Sampling configuration that defines how often the application requires the workflow to be performed. See [Sampling Configurations](../workflows/sampling-configurations.md).
-   Exit points during warehouse processing at which the operator is prompted to perform the workflow.

## Inbound workflow exit points

An exit point is the processing point at which the application initiates any actions, such as workflows, associated with the exit point.

When you create a warehouse-specific inbound workflow, you assign one or more exit points to the workflow. During warehouse processing, when the exit point occurs, such as at the start of putaway, the application prompts the operator to complete the workflow.

**Note**: If a workflow is required and the user does not perform the workflow, the identification or putaway cannot be completed.

The following table identifies the inbound workflow exit points.

 
| Exit point | Description |
| --- | --- |
| Post Cycle Count | Occurs when the operator completes a cycle count on an RF device (by entering **F6 Done**). |
| Expected Residual | Occurs when the operator finishes a distribution deposit assignment and there is expected residual inventory. The workflow or command for this exit point is generally used to print labels for the expected residual inventory. |
| Inbound Pallet Label Start | Occurs when the operator builds a new pallet on the RF Inbound Pallet Build screen. When this inbound exit point is used, the application attempts to print a label for the pallet. |
| Inventory Consolidation Completed | Occurs when the operator completes a carton or pallet consolidation on the RF Inventory Close screen. The inbound workflow for this exit point is generally used to list the inventory details of the completed inventory for the operator. |
| Open New Container | Occurs when the operator opens a new container on the RF Distribution Deposit screen during the distribution put-to-store process. When this inbound exit point is used, the inventory for the container is received inventory that has not yet been picked. |
| Post-Identify | Occurs when the user completes identifying inventory received from an external source, such as a supplier or another warehouse. |
| Post-Receive | Occurs when the user completes putting away inventory received from an external source. |
| Pre-Identify | Occurs when the user begins to identify inventory received from an external source. |
| Pre-Receive | Occurs when the user begins to put away inventory received from an external source. |
| Receive Deposit | Occurs when the operator completes identifying inventory. During configuration of the workflow, you can specify one or more locations to which the operator is directed to deposit the inventory. For example, you can use this exit point to direct the deposit of returned inventory to a returns processing location. |
| RF Pre Full Inventory Move | Occurs when the operator scans the source ID on the Full Inventory Move RF screen. |
| RF Pre Partial Inventory Move | Occurs when the operator scans the destination ID during a partial inventory move. |
| RF Post Full Inventory Move | Occurs when the operator deposits an LPN to its destination location during a full inventory move. |
| RF Post Partial Inventory Move | Occurs when the operator deposits a partial LPN to its destination LPN or location during a partial inventory move. |
| Unexpected Residual | Occurs when the operator finishes a distribution deposit assignment and there is unexpected residual inventory. The workflow or command for this exit point is generally used to print labels for the unexpected residual inventory. |

## Inbound configuration criteria

The application uses the criteria that you specify for a warehouse-specific inbound workflow to select the inventory to which the workflow is applied. For example, if you select Inventory Status, and a value of Damaged In-House, then the application prompts the user to perform the workflow on inventory in the Damaged In-House status; the prompt occurs at the exit points defined for the workflow.

The following table identifies the criteria that can be applied to a warehouse-specific inbound workflow.

 
| Criteria | Application |
| --- | --- |
| Carrier | All inventory received into the warehouse. |
| Inbound Shipment Type | All inventory received with the selected inbound shipment type. |
| Inventory Status | All inventory received with the selected status. For example, you receive product into your warehouse in a quality assurance inspection status and want to perform a QA sampling workflow before allowing the product to be available for shipping. |
| Item Class | All inventory received for the items assigned the selected item class. |
| Item Hierarchy | The selected item hierarchy whenever it is received. An item hierarchy is a set of user-defined values that are used to associate an item with a set of attributes by which the item can be identified, stored, allocated, and shipped. |
| Item Num/Inv Status | The selected item whenever it is received with the selected status. For example, you have an item that requires unique QA sampling workflows as opposed to other items that you receive with the QA sampling status. For a 3PL environment, operators will be requested to perform the default workflow on the selected item whenever it is received for the selected client and inventory status. |
| Item Number | The selected item whenever it is received. For example, you have a item that needs to be repackaged before being put away. For a 3PL environment, operators will be requested to perform the default workflow on the selected item whenever it is received for the selected client. |
| No Criteria | All inventory received into the warehouse. |
| Supplier Number | All inventory whenever it is received from the selected supplier. For example, you have an international supplier who ships inventory to you in special packaging to prevent damage during shipping and you want to repackage the inventory before putting it away into storage. For a 3PL environment, operators will be requested to perform the default workflow on all inventory whenever it is received from the selected supplier for the selected client. |
| Supplier Num/Item Num | All inventory received with the selected supplier and client and item number. |

## Examples: Inbound workflows

You can configure inbound workflows to prompt or direct operators through the completion of the following processes:

-   Processing returns
-   Verifying vendor compliance with labeling and packaging requirements
-   Inspecting incoming inventory
-   Printing and applying price ticket labels
-   Verifying footprint and dimension information for items received for the first time
-   Repackaging inventory
-   Measuring and recording the temperature of temperature-controlled items

## Add or modify an inbound workflow

1.  Select **Configuration > Work > Warehouse Workflows > Inbound Workflows**.
2.  Perform one of the following tasks:
    -   To add a new inbound workflow, click **Add**.
    -   To modify an inbound workflow, in the grid, click the workflow.
    -   To copy an inbound workflow, in the grid, select the check box next to the workflow, and then click **Copy**.
3.  Enter information in the [Inbound Workflow fields](#Inbound_Workflow_fields).
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
        
    4.  In the inventory attribute fields (related to the criteria type), enter the values that inventory must match for the workflow to be applied.
    5.  Click **Save**.
5.  To assign an inventory status to which the workflow applies:
    1.  Under **CRITERIA**, click **Inventory Status**.
    2.  In the **Available** column, select the check box next to the inventory statuses that apply.
    3.  Click **Apply**.
6.  To assign the processing points at which the application executes the workflow:
    
    1.  Under **EXIT POINTS**, click **Exit Points**. The Exit Points page is displayed.
    2.  In the **Available** in column, select the check box next to the exist points to use.
    
    1.  To specify the locations to which the operator is directed to deposit inventory:
        
        **Note**: This configuration is only available for exit points (such as Receive Deposit and Deposit to Processing Movement Zone) that can be used to direct an operator to a deposit location.
        
        1.  In the **Selected** column, click **Configure Locations** or, if locations are already displayed, click **Locations**.
        2.  In the **Available** column, select the locations that apply.
        3.  Click **Apply**.
    
    1.  Click **Apply**.
7.  Click **Save**.

## Delete an inbound workflow

1.  Select **Configuration > Work > Warehouse Workflows > Inbound Workflows**.
2.  In the grid, select the check box next to the inbound workflow to delete.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Inbound Workflow fields

 
| Field | Description |
| --- | --- |
| Enable Workflow | If Enabled, the workflow is active. If a warehouse workflow is enabled, then it will be included in the appropriate workflow plan and the user will be prompted to perform the workflow at the workflow exit point.<br > If Disabled, the workflow is disabled before a workflow plan is generated, it will not be included in that workflow plan. If a warehouse workflow is disabled after a workflow plan is generated, it will still be included in the workflow plan, but the user will not be required to perform the workflow for any inventory for which the workflow has not yet been required. |
| Master Workflow | Unique identifier for a workflow process. The master workflow defines the activity code that is logged for the workflow, tasks and instructions for completing the workflow, how the workflow is acknowledged, and the actions that take place upon completion of the workflow.<br > Every warehouse workflow is based on a master workflow. The warehouse workflow specifies the sampling, criteria, and exit points at which a master workflow is applied to specific entities (such as warehouse or transport equipment) or inventory. |
| Description | Text that further describes the master workflow. This description is displayed to users that are prompted to perform the workflow. |
| Mixed Inventory | If Yes, the workflow is applied if an LPN contains one or more items with different inventory attributes.<br > If No, the workflow is applied to an LPN of inventory that has all the same attributes. |
| Restrict Inventory | If Yes, the workflow will be restricted to specific inventory. If you restrict inventory for a workflow, then you can specify the type of item restricted.<br>-   • **Mixed items only**: Indicates the workflow is only required if an LPN that contains multiple items; for example, if the LPN contains a quantity of ItemA and a quantity of ItemB. Selecting **Mixed Items only** does not require a workflow for an LPN that contains mixed attributes of a single item, such as ItemA with a quantity of Lot1 and a quantity of Lot2. This option is only available if **Mixed Inventory** is set to Yes.
<br>-   • **Non-receivable items only**: Indicates the workflow is only required for non-receivable items. A non-receivable item is an item for which the **Receivable** field is set to No, indicating that it cannot be received into the warehouse.
<br > If No, the workflow is not restricted to either of the options. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
