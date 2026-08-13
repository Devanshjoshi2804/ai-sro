---
title: "Outbound Workflows"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/outbound_workflows.htm"
source: "/content/outbound_workflows.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Work"
  - "Warehouse Workflows"
  - "Outbound Workflows"
sections:
  - "Examples: Outbound workflows"
  - "Outbound workflow exit points"
  - "Outbound configuration criteria"
  - "Add or modify an outbound workflow"
  - "Delete an outbound workflow"
  - "Outbound Workflow fields"
images: []
source_sha1: e3156647cd2f6a26bba8eabfb2aea489a442f50e
---
# Outbound Workflows

An outbound workflow is the warehouse-specific configuration of a master workflow. It defines when and how often the master workflow is to be performed on inventory that is being moved from a picking location to transport equipment. Outbound workflows are performed on inventory associated with an outbound order or order line, and can be configured to be performed during picking.

After outbound workflows are defined, they can be added to an outbound workflow plan, which is used to associate workflows with specific outbound orders and order lines.

When you create an outbound workflow, you specify the following attributes:

-   Master workflow that defines the activity that is logged when the workflow is performed, how the workflow is acknowledged, whether an operator can select "yes to all" when answering multiple questions in a workflow, the questions presented to the operator who performs the workflow, and the actions that take place upon completion of the workflow. See [Master Workflows](../workflows/master-workflows.md).
-   Criteria for the inventory that requires the workflow, such as whether it is limited to mixed inventory LPNs, and the LPN level at which the workflow is applied.
-   Sampling configuration that defines how often the application requires the workflow to be performed. See [Sampling Configurations](../workflows/sampling-configurations.md).
-   Exit points during warehouse processing at which the operator is prompted to perform the workflow. See [Outbound workflow exit points](#Outbound_workflow_exit_points).

## Examples: Outbound workflows

You can configure outbound workflows to prompt or direct operators through the completion of the following processes:

-   Inserting a spacer between shipments and shipments for other stops on transport equipment
-   Packing hazardous materials in special packaging and applying hazmat labels prior to shipping
-   Printing a packing list or customer compliant label and applying it to a carton
-   Testing a sample of the inventory that is picked for a customer or order to check it for quality

## Outbound workflow exit points

An exit point is the processing point at which the application initiates any actions, such as workflows, associated with the exit point.

When you create a warehouse-specific outbound workflow, you assign one or more exit points to the workflow. During warehouse processing, when the exit point occurs, such as at the start of picking, the application prompts the operator to complete the workflow.

**Note**: If a workflow is required and the user does not perform the workflow, the identification or picking cannot be completed.

The following table identifies the outbound workflow exit points.

 
| Exit point | Description |
| --- | --- |
| Carton Complete | Occurs when the user completes packing a cartonized or overpack carton.<br > Also occurs when a user manually confirms picks using the Pick Confirmation page. |
| Carton Initiation | Occurs when the operator enters a valid carton ID and confirms the carton is being worked on. This action is completed in Carton Confirmation Operations. On an RF device, this action can be completed through undirected or directed case confirm; and for cluster picking, the exit point occurs when the operator enters a valid carton ID and it has been added to the batch. The outbound workflows for this exit point process before the background workflows. |
| Close Outbound Transport Equipment | Occurs when the user closes outbound transport equipment in Dock Door Operations. This exit point processes at the same time as the non-inventory Trailer Closed exit point. |
| Deposit to Processing Movement Zone | Occurs when the operator moves inventory out of a source movement zone or into a destination movement zone. During configuration of the workflow, you specify the source or destination movement zones for which the workflow is initiated. You can also define one or more locations to which the operator is directed to deposit the inventory. |
| First Load Pick | Occurs when the operator picks the first LPN in a work assignment on the Product Pickup RF screen. |
| First Load Transport Equipment | Occurs when the operator loads the first LPN of an order line onto transport equipment using the Load Trailer RF screen. |
| Identify Manifest Carton | Occurs when the operator identifies a manifest carton by scanning the package's inventory identifier on the Manifesting page or on the Parcel Manifest RF screen. |
| Inventory Consolidation Completed | Occurs when the operator completes a carton or pallet consolidation on the RF Inventory Close screen. The outbound workflow for this exit point is generally used to list the inventory details of the consolidated inventory for the operator. |
| List Initiation | Occurs before the operator starts picking a work assignment. The workflow for this exit point is used to determine whether there are notes available for the work assignment. |
| Load Transport Equipment | Occurs when the operator deposits an LPN on the transport equipment. |
| Manifest Carton | Occurs when the user manifests a carton. |
| Manifest Last Carton For Outbound Order | Occurs when the user manifests the last carton for an order. |
| Move From Processing Area | Occurs when the user moves inventory out of a processing location (such as a ship staging location). |
| Move Last Inv From Processing Area For Outbound Order | Occurs when the user moves the last piece of inventory required for an order out of a processing location (such as a ship staging location). |
| Open New Container | Occurs when the operator opens a new container on the Distribution Deposit RF screen during the distribution put-to-store process. When the outbound exit point is used, the inventory for the container is picked inventory that is being distributed. |
| Order Consolidation Operations | Occurs when the user processes a consolidation in Order Consolidation Operations. The workflow or command for this exit point is used to determine whether there are notes available for the order being consolidated and, if so, to enable the Notes button. |
| Pack Close Out | Occurs in the close out stage of pack station processing after a carton number is assigned to the completed shipping carton. The close out stage occurs either automatically after the application determines that all items assigned to a specific shipping carton have been packed into the shipping carton, or manually after the pack station operator closes the shipping carton (and after errors are reported, if any). |
| Pack Initiation | Occurs after the pack station operator enters the identifier for a picking container from which the operator will remove items to pack into a shipping container. This action is performed at the pack station. |
| Pack Item Scanned | Occurs after the pack station operator indicates the items that the operator is packing into the shipping container at the pack station. |
| Pack Station Processing | Occurs when the pack station operator tabs out of a processing field. This exit point is generally used to validate a processing field. |
| Packing Error | Occurs when a problem is detected and the pack station operator logs an error at the pack station. |
| Pick Confirmation | Occurs when a user manually confirms picks using the Pick Confirmation page. |
| Pick Initiation | Occurs when the operator acknowledges directed work for a pick or enters a work reference to start a pick, but before the application displays specific pick information. This exit point is used for workflows that must be executed before the operator moves to the pick location. The exit point can also be assigned to a note type that is configured for auto display.<br > The Pick Initiation exit point occurs prior to a pick; regardless of whether the pick is in a work assignment. The List Initiation exit point occurs prior to a work assignment.<br > If this exit point is used for workflows and for note types, the application first processes the workflows and then displays the notes. |
| Post Count Audit | Occurs when the operator (authorized to perform audit counts) completes an audit count that was generated from a count back discrepancy. This exit point only applies to audit counts that are performed after a count back. |
| Post-Pick | Occurs when the operator completes a pick for an outbound order. The exit point occurs after the operator has confirmed the pick, and the application has logically moved the inventory to the pick-to LPN or handling unit.<br > Also occurs when a user manually confirms picks using the Pick Confirmation page.<br>
**Notes**:

<br>

-   •
    
    The exit point does not apply to replenishment picks, work order picks, and cartonized picks.
    
    <br>
<br>-   •
    
    You can configure whether the exit point occurs for every completed pick in a work assignment or only once per work assignment. See [Post pick workflow every pick policy](../../../../administration/system-administrator/configuration/policy/post-pick-workflow-every-pick-policy.md).
    
    <br>
<br>

 |
| Pre-Carton Pick | Occurs when the operator scans a carton before picking inventory. The workflow or command for this exit point is generally used to print a label for the cartons being used in the picking assignment. |
| Pre Count Back | Occurs when the operator (authorized to perform a count back) completes a pick, before the count back is performed. |
| Pre-Deposit | Occurs when the user has finished picking inventory but before the inventory is deposited to a location. This action is completed in Carton Confirmation Operations or Inventory Movement Operations. On an RF device, this action is completed by selecting a load on the Product Deposit RF screen. The outbound workflows for this exit point process before the background workflows. Workflows associated to this exit point display the destination location for the inventory. |
| Pre-Pick | Occurs when the operator performs a pick for an outbound order. The exit point occurs after the operator has confirmed the pick, but before the application has logically moved the inventory to the pick-to LPN or handling unit.<br > Also occurs when a user manually confirms picks using the Pick Confirmation page.<br > **Note**: The exit point does not apply to replenishment picks, work order picks, and cartonized picks. |
| RF Pre Full Inventory Move | Occurs when the operator scans the source ID on the Full Inventory Move RF screen. |
| RF Pre Partial Inventory Move | Occurs when the operator scans the destination ID during a partial inventory move. |
| RF Post Full Inventory Move | Occurs when the operator deposits an LPN to its destination location during a full inventory move. |
| RF Post Partial Inventory Move | Occurs when the operator deposits a partial LPN to its destination LPN or location during a partial inventory move. |
| Small Package Operations | Occurs when the user closes a parcel manifest in Small Package Operations. Workflows associated with this exit point contain shipment IDs and warehouse IDs. |
| Stop Complete | Occurs when the user manually completes a stop. |
| Work Assignment Complete | Occurs when an operator completes the last pick for a work assignment. This exit point only applies to work assignments used to pick sequenced orders. |

## Outbound configuration criteria

The application uses the criteria that you specify for a warehouse-specific outbound workflow to select the inventory to which the workflow is applied. For example, if you select Order Type, and a value of Cartonization then the application prompts the user to perform the workflow on inventory in the Cartonization status; the prompt occurs at the exit points defined for the workflow.

The following table identifies the criteria that can be applied to a warehouse-specific outbound workflow.

 
| Criteria | Application |
| --- | --- |
| Carrier | All inventory picked for the selected carrier. |
| Carrier Code/Service Level | All inventory picked for the selected carrier code or service level. |
| Customer Number | All inventory picked for the selected customer. |
| Customer Type | All inventory picked for the selected customer type. |
| Customer Type/Outbound Order Type | The selected item whenever it is picked for the selected customer type with the selected order type. |
| Customer/Item Num | The selected item whenever it is picked for the selected customer with the selected item. |
| Final Destination Zone | All inventory for the selected final destination zone. |
| Item Class | All inventory for the items assigned the selected item class. |
| Item Cost | All inventory for the selected item cost. |
| Item Num/Inv Status | The selected item whenever it is picked with the selected status. |
| Item Number | All inventory picked for the selected item. |
| No Criteria | All outbound inventory. |
| Order Type | All inventory for the selected order type. |
| Outbound Order Line | All inventory for the selected order line. |
| Outbound Order Num | All inventory for the selected order. |

## Add or modify an outbound workflow

1.  Select **Configuration > Work > Warehouse Workflows > Outbound Workflows**.
2.  Perform one of the following tasks:
    -   To add a new outbound workflow, click **Add**.
    -   To modify an outbound workflow, click the workflow.
    -   To copy an outbound workflow, select the check box next to the workflow, and then click **Copy**.
3.  Enter information in the [Outbound Workflow fields](#Outbound_Workflow_fields).
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
        
    4.  In the inventory attribute fields (related to the criteria type), enter the values that inventory must match for the workflow to be applied. See [Outbound configuration criteria](#Outbound_configuration_criteria).
    5.  Click **Save**.
5.  To assign the processing points at which the application executes the workflow:
    
    1.  Under **EXIT POINTS**, click **Exit Points**. The Exit Points page is displayed.
    2.  In the **Available in** column, select the check box next to the exist points to use.
    
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

## Delete an outbound workflow

1.  Select **Configuration > Work > Warehouse Workflows > Outbound Workflows**.
2.  In the grid, select the check box next to the outbound workflow to delete.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Outbound Workflow fields

 
| Field | Description |
| --- | --- |
| Enable Workflow | If Enabled, the workflow is active. If a warehouse workflow is enabled, then it will be included in the appropriate workflow plan and the user will be prompted to perform the workflow at the workflow exit point.<br > If Disabled, the workflow is disabled before a workflow plan is generated, it will not be included in that workflow plan. If a warehouse workflow is disabled after a workflow plan is generated, it will still be included in the workflow plan, but the user will not be required to perform the workflow for any inventory for which the workflow has not yet been required. |
| Master Workflow | Unique identifier for a workflow process. The master workflow defines the activity code that is logged for the workflow, tasks and instructions for completing the workflow, how the workflow is acknowledged, and the actions that take place upon completion of the workflow.<br > Every warehouse workflow is based on a master workflow. The warehouse workflow specifies the sampling, criteria, and exit points at which a master workflow is applied to specific entities (such as warehouse or transport equipment) or inventory. |
| Description | Text that further describes the master workflow. |
| Mixed Inventory | If Yes, the workflow is applied if an LPN contains one or more items with different inventory attributes.<br > If No, the workflow is applied to an LPN of inventory that has all the same attributes. |
| LPN Level | LPN level to which the workflow should be applied.<br>-   • **LPN**: The workflow is applied to each LPN. Typically, an LPN refers to a pallet.
<br>-   • **Sub-LPN**: The workflow is applied to each case on a pallet. |
| Include Discrete Labor | If Yes, then when a workflow is performed for a work activity that is sent to Warehouse Labor Management (WLM), the application groups the discrete procedure transaction (for the workflow) with the next obtain and place transaction. For example, assume that a discrete work activity for printing carton labels is configured to be sent to WLM, and the **Include Discrete Labor** field is set to Yes on the outbound workflow that prompts the operator to perform this activity. Prior to performing a pick, the operator is prompted to print the labels, and then the pick can be completed. Upon pick completion (when the inventory is deposited), a single transaction is sent to WLM that contains a segment for the discrete procedure of printing labels (assignment key = A), and two additional segments for the pick assignment, one for obtaining the inventory (assignment key = O) and one for placing the inventory (assignment key = P).<br > If you set this field to Yes, depending on the workflow configuration, certain labor time calculations may be inaccurate because discrete procedures that are performed as standalone activities will not be reported as such. For example, if a user performs a standalone safety check in the web user interface, it will not be sent to WLM until a subsequent (and possibly unrelated) obtain and place assignment is completed. This can increase the time recorded for the obtain and place assignment due to the possible time lapse between the standalone discrete procedure and the next assignment.<br > If No, then the discrete activity associated with the workflow is sent to WLM as a separate assignment. Using the previous example, this means that the system first sends a transaction to WLM for the discrete activity of printing labels, and then sends another (containing the obtain and place assignment) when the pick is complete.<br > See [Discrete procedure transactions](../work/work-activities.md). |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
