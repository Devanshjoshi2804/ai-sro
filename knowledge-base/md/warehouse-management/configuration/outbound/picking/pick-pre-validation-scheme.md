---
title: "Pick Pre-Validation Scheme"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/pick_pre-validation_scheme.htm"
source: "/content/pick_pre-validation_scheme.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Outbound"
  - "Picking "
  - "Pick Pre-Validation Scheme"
sections:
  - "Example: Pick pre-validation scheme"
  - "Add or modify a pick pre-validation scheme"
  - "Delete a pick pre-validation scheme"
  - "Pick Pre-Validation Scheme fields"
images: []
source_sha1: 1806e0c2d4e65c6c94dcf29287a3828b7f9206b3
---
# Pick Pre-Validation Scheme

Pick pre-validation is a process that determines whether inventory is available in a location prior to displaying the pick to an operator. A pre-validation scheme is a configuration that is assigned to a pick method, and determines what occurs when a pick fails pre-validation, such as for one of the following reasons:

-   The source location of the pick is in a Locked status due to an inventory count being performed after allocation.
-   The location is in error due to a violation of the inventory mixing rules.
-   Inventory was put on hold after the pick was released, but prior to picking.

Using pre-validation schemes can help prevent an operator from being directed to a location that no longer contains available inventory for the pick.

After you have created a pick pre-validation scheme, you must assign the scheme to a pick method for the type of pick to which it applies. Assigning a pre-validation scheme to a pick method determines how the application handles pre-validation for the each pick method. See [Pick Methods](pick-methods.md).

## Example: Pick pre-validation scheme

The following table provides examples of pick pre-validation scheme configurations, and describes the processing that takes place for each configuration.

     
| Name | Information level | Fail action | Skip limit | Cancel action | Description |
| --- | --- | --- | --- | --- | --- |
| Skip Without Prompt | Do not prompt user | Skip the pick | 5 | Cancel -reallocate | If pre-validation fails, the pick is skipped without notifying the operator. If pre-validation fails more than 5 times, the pick is cancelled. |
| Cancel with Notification | Notify user | Cancel the pick | 0 | Cancel -reallocate | If pre-validation fails, the operator is notified, and then the pick is cancelled. |
| Confirm with User | Confirm with user | Skip the pick | 2 | Cancel - reallocate | If pre-validation fails, the operator is notified and is asked to confirm the fail action. The operator can override the fail action and continue with the pick, or allow the application to skip the pick. Each time the pick fails pre-validation the operator must confirm the fail action. After 2 skipped picks, the pick is cancelled. |
| Disable Pre-Validation | Disable Pre-Validation |   |   |   | Pre-validation is not performed. If the operator finds that inventory is not available in the location, the operator decides whether to skip or cancel the pick. |

**Note**: The cancel action is a configuration that determines how the application processes the pick cancellation. See [Pick Cancellation](pick-cancellation.md).

## Add or modify a pick pre-validation scheme

1.  Select **Configuration > Outbound > Picking > Pick Pre-Validation Scheme**.
2.  Perform one of the following tasks:
    -   To add a new pre-validation scheme, click **Add**.
    -   To modify a pre-validation scheme, in the grid, select the description of the scheme.
3.  Enter information in the [Pick Pre-Validation Scheme fields](#Pick_Pre-Validation_Scheme_fields).
4.  Click **Save**.

## Delete a pick pre-validation scheme

1.  Select **Configuration > Outbound > Picking > Pick Pre-Validation Scheme**.
2.  In the grid, select the check box next to the pre-validation scheme to delete.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Pick Pre-Validation Scheme fields

 
| Field | Description |
| --- | --- |
| Name | Unique identifier assigned to the pick pre-validation scheme. |
| Description | Meaningful description of the pick pre-validation scheme. |
| Information Level | Determines if pick pre-validation is enabled for the scheme and, if enabled, determines the processing that takes place when inventory cannot be picked from a pick location.<br>-   • **Disable Pre-Validation**: The application does not determine whether pickable inventory is available in a location prior to displaying the pick to an operator.
<br>-   • **Do not prompt user**: When a pick fails pre-validation, the application does not display a message to the operator stating that a pick has been skipped or cancelled.
<br>-   • **Notify user**: When a pick fails pre-validation, the application displays a message to the operator stating that a pick has been skipped or cancelled.
<br>-   • **Confirm with user**: When a pick fails pre-validation, the application displays a message to the operator stating that the location does not have enough inventory to fulfill the pick, and asking the operator to confirm the fail action configured in the scheme. The operator can override the fail action if inventory becomes available and then continue with the pick, or allow the application to skip or cancel the pick according to the fail action defined for the scheme. |
| Fail Action | Determines if the application skips or cancels the pick when pre-validation fails or when there is insufficient inventory in the location to complete the pick.<br>-   • **Skip pick, use skip limit and cancel action**: The application skips the pick and the pick is moved to the bottom of the work assignment.
<br>-   • **Cancel pick**: The application cancels the pick.
<br > Only available if pre-validation is enabled. |
| Skip Limit | Determines the number of times a pick can be skipped before the application cancels it automatically. For example, if you enter 5, then after a pick is skipped 5 times, and the inventory is still not available the next time the application pre-validates the pick, the application cancels the pick. Only available when **Skip pick** is selected in the **Fail Action** field. |
| Cancel Action | Cancel code configuration that determines how the application processes a cancelled pick. Only available if pre-validation is enabled. See [Pick Cancellation](pick-cancellation.md). |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
