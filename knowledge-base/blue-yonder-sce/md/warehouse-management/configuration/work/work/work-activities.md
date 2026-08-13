---
title: "Work Activities"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/work_activities.htm"
source: "/content/work_activities.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Work"
  - "Work"
  - "Work Activities"
sections:
  - "Integration to Warehouse Labor Management"
  - "Mapping to work types and discrete procedures"
  - "Discrete procedure transactions"
  - "Pre-obtain discrete procedures"
  - "Inline discrete procedures"
  - "Discrete catch quantity procedures"
  - "Communication of completed work"
  - "Add or modify a work activity"
  - "Delete a work activity"
  - "Work Activity fields"
images: []
source_sha1: bedd9f8eec683b7ddbe1f55184aacc4810669f83
---
# Work Activities

An activity code is a unique code that identifies a work or non-work activity that is performed in Warehouse Management. Activity codes are used to report on work that has been completed in the application. For example, when an RF operator performs a case pick (work activity) or a user at a workstation creates a new order (non-work activity), a record of the activity is generated.

Warehouse Management provides a standard set of activity codes, each of which is associated with a server command that generates a record when the associated activity is performed.

**Note**: If additional activity codes are required, an associated server command is also required; contact your Blue Yonder project team for information on implementing additional activity codes and commands.

## Integration to Warehouse Labor Management

If Warehouse Labor Management is integrated with Warehouse Management, activity codes provide users, such as system administrators and project teams, with information that can assist in configuring, maintaining, and troubleshooting transactions between Warehouse Management and Warehouse Labor Management. Activity code configurations let users perform the following tasks:

-   Organize activity codes into meaningful categories, such as to separate activities for which time can be charged from activities that do not involve chargeable time like inventory tracking activities
-   Determine which activity codes should be sent to Warehouse Labor Management
-   Track additional activities (discrete procedures) within an assignment
-   Modify the names of activity codes to match customer preferences. For example, the standard activity code PCEPCK represents picking done at the piece level. However, if a facility refers to this activity as "each picking", the code can be changed to match the customer preference, such as EACHPK.

## Mapping to work types and discrete procedures

In order for Warehouse Management to record and send assignment information to Warehouse Labor Management, an activity code must be enabled and mapped to (associated with) a work type or discrete procedure that is maintained in Warehouse Labor Management.

Assignment information typically provides the start and stop time as well as the source and destination location of the activity.

An integration transaction from Warehouse Management to Warehouse Labor Management communicates assignment information that contains the activity code mapping so that Warehouse Labor Management can evaluate the work against labor standards and accurately measure employee performance.

## Discrete procedure transactions

A work activity (assignment) record is sent from Warehouse Management (WM) to Warehouse Labor Management (WLM) if the activity is configured with the **Send to Labor** field set to Yes. Work activities that are not discrete, such as picking or receiving, are sent with an assignment key of O (Obtain) and P (Place) to account for the pickup (O) and deposit (P) of inventory. Discrete procedures can also be sent to Warehouse Labor Management for activities that do not involve the movement of inventory (an obtain and place assignment). A discrete procedure is used by Warehouse Labor Management to account for additional time in an assignment that is not accounted for by the job code (standard) for the assignment's work type. The discrete procedure is used, for example, to account for the time differential that occurs when a count near zero is presented to a user during a picking activity. The count can extend the time of the picking assignment but does not require travel time.

Discrete procedures can be performed as standalone activities (not associated with any other directed work), before an obtain and place assignment (such as printing labels for cartons), or during an assignment (such as catch quantity capture). Whenever a discrete procedure is performed, if the related work activity is configured to be sent to WLM and includes a discrete procedure ID, the discrete activity is sent with an assignment key of A (Activity).

Standalone discrete work activities (such as a safety check) are always sent with a code of A, regardless of whether they have a discrete procedure ID defined. However, WLM does not process standalone discrete activity transactions unless they have a discrete procedure ID.

The application supports sending voice work activities to WLM (if configured to do so); however, voice functionality only supports three outbound workflow exit points (Pick Initiation, Post Pick, and Deposit to Processing Movement Zone). Therefore, reporting on discrete procedures is limited to workflows that can be executed at those points.

### Pre-obtain discrete procedures

Discrete procedures can be prompted by outbound workflows. You can configure an outbound workflow to include the transaction for the discrete procedure activity with the next main work activity that takes place.

For example, assume an operator is directed to perform a pick assignment that requires carton labels to be printed prior to picking, and that the workflow for printing carton labels is configured with the **Include Discrete Labor** field set to Yes. Also assume that both work activities are configured to be sent to WLM for labor calculations. The application sends a single assignment transaction with the information in the following table:

   
| Assignment | Assignment Key | Activity Code | Discrete Procedure |
| --- | --- | --- | --- |
| 001 | A | PRINT-CTN-LABEL | Print Carton Label |
| 001 | O | KITPCK |   |
| 001 | P | KITPCK |   |

In this example, if the **Include Discrete Procedure** field was set to No for the carton labels workflow, the application would send two different assignments; one for the discrete procedure activity and another for the pick (obtain and place) activity.

### Inline discrete procedures

Discrete procedures that occur inline (after the obtain activity but before the place activity) are automatically sent with the obtain and place assignment. However, if the work activity for the discrete procedure is not configured with the discrete procedure identifier (as defined in WLM), it is not sent with an activity type of A. For example, assume that an operator is directed to pick 2 pallets that require shrink wrapping before deposit. If the work activity configuration for shrink wrapping includes the discrete procedure ID, the assignment transaction that is sent to WLM includes the information in the following table.

  
| Assignment Key | Activity Code | Discrete Procedure |
| --- | --- | --- |
| O | PALPCK |   |
| A | SHRINK-WRAP | Shrink Wrap |
| A | SHRINK-WRAP | Shrink Wrap |
| P | PALPCK |   |

However, if the SHRINK-WRAP work activity did not have a discrete procedure defined, the assignment key for the shrink wrap procedure would be O instead of A, and the transaction would not include a discrete procedure ID.

### Discrete catch quantity procedures

Catch quantity activity information can be sent to WLM in different ways depending on when the capture takes place. However, regardless of when the capture takes place, if multiple captures are taken at once, they are grouped in the assignment transaction in a single segment indicating how many times the capture was repeated.

When an operator receives or adds inventory and captures the catch quantity, the capture activity is sent to WLM as a standalone discrete procedure assignment (regardless of the **Include Discrete Procedure** field on the workflow configuration). This is because catch quantity is captured during identification, and putaway may happen later and by a different operator or web client user. For example, assume an operator receives a pallet of 20 cases and that case level capture is enabled. After the operator captures the catch quantity and puts away the inventory, Warehouse Management sends the activities in two separate assignments that include the information in the following table:

    
| Assignment | Assignment Key | Activity Code | Discrete Procedure | Repetition |
| --- | --- | --- | --- | --- |
| 001 | A | CAPTURE-CATCH-WEIGHT | Catch Weight | 20 |
| 002 | O | RCV |   |   |
| 002 | P | RCV |   |   |

**Note**: If catch weight capture is required during picking (after obtain and before place), it is included within the picking assignment. If delayed catch weight capture is enabled, then it takes place after the inventory has been deposited, and the catch weight discrete activity is sent as a separate assignment.

## Communication of completed work

Activity codes are used to communicate completed work assignment information from Warehouse Management to an integrated instance of Warehouse Labor Management through the following process:

1.  A user performs an activity in Warehouse Management.
2.  A server command associated with the activity generates a record of the activity that has been performed.
3.  Warehouse Management uses activity code mappings in the following ways:
    1.  Determines the corresponding Warehouse Labor Management work type or discrete procedure.
    2.  Writes the work transaction to a history table, which can be viewed using Labor Transaction Operations.
4.  Warehouse Management generates an integration transaction that communicates the work type or discrete procedure along with the assignment information to Warehouse Labor Management.
5.  Warehouse Labor Management uses the work type, discrete procedure, location information, and other parameters included in the integration transaction to determine the job code against which to calculate the actual time for the assignment.
6.  Warehouse Labor Management evaluates actual time against goal time for the task to determine employee performance.

## Add or modify a work activity

Warehouse Management provides a standard set of activity codes, each of which is associated with a server command that generates a record when the associated activity is performed. You can modify the name of an activity, but adding an activity requires a server command to also be implemented.

**IMPORTANT**: If additional activity codes are required, an associated server command is also required. Contact your Blue Yonder project team for information on implementing additional activity codes and commands.

1.  Select **Configuration > Work > Work > Work Activities**.
2.  Perform one of the following tasks:
    -   To add an activity, click **Add**.
    -   To modify an activity, in the grid, click the activity.
    -   To copy an activity, in the grid, select the check box next to the activity, and then click **Copy**.
3.  Enter information in the [Work Activity fields](#Work_Activity_fields).
4.  Click **Save**.

## Delete a work activity

A standard set of work (and non-work) activity codes is provided by default in the application, and each of these activities is associated with a server command. To avoid unexpected behavior, contact your Blue Yonder project team before deleting a standard activity that is associated with a server command.

1.  Select **Configuration > Work > Work > Work Activities**.
2.  In the grid, select the check box next to the activity to delete.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Work Activity fields

 
| Field | Description |
| --- | --- |
| Activity Code | Unique code that identifies a work or non-work activity that is performed in Warehouse Management. For example, when an RF operator performs a case pick (work activity) or a user at a workstation creates a new order (non-work activity), a record of the activity is generated.<br > Warehouse Management provides a standard set of activity codes, each of which is associated with a server command that generates a record when the associated activity is performed. If additional activity codes are required, an associated server command is also required; contact your Blue Yonder project team for information on implementing additional activity codes and commands. |
| Description | Text that further describes the activity code. This is the value that is displayed in place of the code on other pages and windows, and in reports. |
| Activity Category | Group that is used to categorize the activity according to type. A category can be used as search criteria to limit the results of your search and display related activities.<br>-   • **General Activity**: Non-work activities that are logged as daily transactions.
<br>-   • **Inventory Activity**: Non-work activities related to inventory tracking.
<br>-   • **Order Activity**: Non-work activities related to order processing.
<br>-   • **Trailer Activity**: Non-work activities related to transport equipment movements.
<br>-   • **Work**: Work activities that are logged to daily transactions when a user performs an action (usually an RF function) in Warehouse Management. Work activities are typically configured to be sent to Warehouse Labor Management for labor tracking. |
| Voice Code | Code used to represent the piece of equipment in facilities that use voice terminals. When the voice terminal operator is prompted for the equipment, the operator can speak the voice code to identify the equipment to the application. |
| UOM | Unit of measure (UOM) to which a completed pick quantity is converted for the purpose of reporting activity to Warehouse Labor Management (WLM). For example, an item footprint specifies 20 eaches to a case. The **UOM** field is set to Case. Therefore, if the pick quantity is 25 eaches, two obtain records are reported to WLM: 1 case and 5 eaches.<br > The following UOMs are supported by WLM and are available for selection: Pallet, Layer, Case, Inner Pack, and Each.<br > The **UOM** field is only available if the **Change UOM Picked** field is set to Yes for the Warehouse Labor Management integration.<br > See [Pick reporting to Warehouse Labor Management](../../integration/warehouse-labor-management.md). |
| Send to Labor | If Yes, an integration transaction is generated to send the assignment information to Warehouse Labor Management when the activity is performed.<br > If No, no integration transaction is generated to Warehouse Labor Management when the activity is performed.<br > This field is only available if Warehouse Management is integrated with Warehouse Labor Management. |
| Work Type | Type of pick work.<br>-   • **Bulk Pick**: Work type used to perform bulk picks.
<br>-   • **Demand Replenishment**: Replenishment work type generated when pre-inventory allocation is enabled and a pick location does not have inventory to complete an order. The application generates demand-based replenishments from reserve storage locations to the pick locations, and then generates picks based on the inventory pending to the pick locations.
<br>-   • **Emergency Replenishment**: Replenishment work type generated automatically when there is insufficient inventory in a pick zone to satisfy a shipment line.
<br>-   • **Kit**: Work type used to pick component items to fill a work order.
<br>-   • **Manual Replenishment**: Replenishment work type initiated by an operator for a specific location.
<br>-   • **Pick**: Work type used to pick inventory to fill an order.
<br>-   • **Replenishment**: Work type used to fill a pickface location with inventory from a storage location.
<br>-   • **Stage Transfer**: Pick work generated to transfer inventory typically from a cross docking location to a staging lane.
<br>-   • **Top-off Replenishment**: Replenishment work type generated automatically at timed intervals.
<br>-   • **Triggered Replenishment**: Replenishment work type generated automatically when an item in a zone or a location has dropped below a user-defined level. |
| Labor Discrete Procedure | Identifier for a discrete procedure, defined in Warehouse Labor Management. A discrete procedure is used by Warehouse Labor Management to account for additional time in a work assignment that is not accounted for by the job code (standard) for the assignment's work type. The discrete procedure is used, for example, to account for the time differential that occurs when a cycle count is presented to a user during a picking activity. The cycle count can extend the time of the picking assignment but does not require travel time.<br > This field is only available if Warehouse Management is integrated with Warehouse Labor Management.<br > **Note**: If you enter a value in this field, the **Assignment Key** and **Picked UOM** fields are irrelevant and not used in transactions to Warehouse Labor Management. This is because discrete procedures are always sent with an assignment key of A, and the UOM field only applies to picked inventory (an obtain and place activity, not a discrete procedure). |
| Assignment Key | Transaction type from which Warehouse Labor Management should get location information for matching to a job standard (job code) when processing assignments. Most assignments have at least one obtain and one place transaction for a single activity.<br>-   • **Obtain**: Transaction type that indicates an inventory pickup action, such as receiving or picking.
<br>-   • **Place**: Transaction type that indicates an inventory deposit action, such as moving and depositing inventory.
<br > This field is only available if Warehouse Management is integrated with Warehouse Labor Management. If the **Labor Discrete Procedure** field is defined, the value of the **Assignment Key** field is irrelevant since discrete procedure transactions are always sent with an assignment key of A. |
| Assignment Type | Type of assignment that was performed.<br>-   • **Direct**: A work task, such as picking or loading, that can have a cost applied against a specific object.
<br>-   • **Indirect**: A work task that does not have a cost that can be applied against a specific object, such as a client or customer. It can refer, for example, to management or maintenance time, such as a battery change for a fork truck. If you select this option, the **Labor Discrete Procedure** field can be blank (no value) because it is not used by the application.
<br > This field is only available if Warehouse Management is integrated with Warehouse Labor Management. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
