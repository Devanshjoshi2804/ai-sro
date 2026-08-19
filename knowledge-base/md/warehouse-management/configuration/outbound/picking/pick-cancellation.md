---
title: "Pick Cancellation"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/pick_cancellation.htm"
source: "/content/pick_cancellation.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Outbound"
  - "Picking "
  - "Pick Cancellation"
sections:
  - "Cancel code use scenarios"
  - "Configure pick cancellation"
  - "Pick Cancellation fields"
  - "Cancel Code fields"
images: []
source_sha1: f4fecb7219b3d18bcbb39efd7060d532df9341d3
---
# Pick Cancellation

Pick cancellation is a configuration that determines how the application processes an attempt to cancel a released pick. Users on a workstation are able to cancel any pick that has been released and not started. RF operators need permission to cancel a pick. RF operators may need to cancel picks for various reasons such as an inventory discrepancy in the location or inventory that is not in the proper condition to fulfill a customer order.

If pick cancellation is allowed for an RF operator, the configured cancel code determines how the application processes the cancelled pick. For example, one cancel code can be configured to cancel a pick and reallocate it, while another cancel code can be configured to cancel the pick and not reallocate it.

All of the cancel codes are available to users that perform pick cancellation operations from a workstation. After a pick is canceled, the user has the option of putting the source location in error. You can view locations that have been placed in "Inventory Error" on the Errored Location Display window.

## Cancel code use scenarios

Cancel codes define the processing that takes place when you cancel a pick. The following are some examples of circumstances in which a user may select a particular cancel code:

**Note**: The application provides the standard cancel codes that you can use or modify. New cancel codes are not typically added. If you require new cancel codes, consult with your Blue Yonder project team.

-   **Cancel and reallocate**: Can be used if there is a problem with a pick location and you want the application to look for inventory elsewhere in the warehouse that can be picked.
-   **Cancel and do not reallocate**: Can be used for an order that needs to be shipped today and can be shipped short if allowed in the warehouse.
-   **Cancel, replenish, and reallocate**: Can be used when the inventory in a pickface is not pickable for some reason (for example, it is damaged), and you want the application to look for inventory in storage that can be used to replenish the pickface so that the pick can be reallocated and picked.
-   **Cancel, reallocate, and reuse location**: Can be used with cluster picking. For example, if the container being used becomes full before the picks are complete, the user can cancel the remaining picks with a cancel code that is configured to reallocate and to reuse the location, so that, ideally, reallocating the inventory will send the user back to the original location for picking.
-   **Cancel, reallocate, and manually re-plan to list**: Can be used when a user encounters a situation in which a work assignment pick cannot be completed, such as when the picking location is empty or the item to be picked will not fit on the pallet. The user can cancel the remaining picks with a cancel code that reallocates the picks, but requires users to manually re-plan the pick to another work assignment. Manual re-planning lets users group the picks as they see fit because when a pick is manually re-planned, the application does not verify that the pick matches the work assignment rules.
-   **Cancel and generate a cycle count**: Can be used when you want to maintain inventory accuracy without requiring the operator to access other functions to manually create a count for a location. For example, if a count is generated and released, an operator could perform the count immediately.

## Configure pick cancellation

1.  Select **Configuration > Outbound > Picking > Pick Cancellation**.
2.  Enter information in the [Pick Cancellation fields](#Pick_Cancellation_fields).
3.  To define cancel codes:
    1.  Under **CANCEL CODES**, click **Definition**.
    2.  Perform one of the following tasks:
        -   To add a new cancel code, click **Add**.
        -   To modify a cancel code, in the grid, click the cancel code.
        -   To copy a code, in the grid, select the check box next to the cancel code, and then click **Copy**.
    3.  Enter information in the [Cancel Code fields](#Cancel_Code_fields).
    4.  Click **Apply**.
4.  Click **Save**.

## Pick Cancellation fields

 
| Field | Description |
| --- | --- |
| Allowed Cancellations | Determines whether an RF operator can cancel any pick or only the currently displayed pick.<br>-   • **Any Pick**: The operator is allowed to access the RF Cancel Pick screen and enter a work reference number to cancel a pick any time after the pick is released for picking. Typically, the work reference number is printed on pick labels and can also be viewed from a workstation. This may be useful if an order or shipment is cancelled and the picks are no longer needed. In that case, the operator can manually cancel all the picks using the work reference numbers for the picks and is not limited to cancelling only the current pick.
<br>-   • **Current Pick**: The operator is allowed to cancel the current pick by accessing the RF Cancel Pick screen from the Pickup screen while the pick is displayed. The work reference number for the current pick appears on the RF Cancel Pick screen, but it cannot be changed and so the operator is limited to cancelling only the current pick. |
| Enhanced Cancel Pick | If Yes, then the system cancels picks using a more efficient process to increase the performance of pick cancellation. Set this field to Yes to enable enhanced cancel pick processing in standard (non-customized) environments.<br > If No, then the system cancels picks using the classic pick cancellation process. Set this field to No to maintain system compatibility in a customized cancel pick environment. |
| Commit Cancelled Pick Immediately | If Yes, the application commits the pick cancellation to the database while processing the request to cancel the pick. In facilities that routinely cancel mass quantities of picks, committing the changes during processing can help eliminate problems with multiple locations being locked while processing a large number of pick cancellations all at once.<br > If No, the application commits the pick cancellation after the pick cancellation has been completely processed. |
| Default Cancel Code | Cancel code that displays by default when a user attempts to cancel a pick; however, the user can select a different cancel code if necessary. For a default cancel code, select the code that you want to be used for most pick cancellations. If you leave this field blank (no value), a cancel code is not displayed by default, and users are required to select a cancel code when cancelling a pick. |
| Skip Pick Limit | Maximum number of times an operator can manually skip a displayed pick before the application automatically cancels the pick. For example, if the value is 5, then if the operator skips a pick 5 times, the application automatically cancels the pick. |
| Cancel Code | Unique identifier for the cancel code that is applied when the application automatically cancels a pick because the skip limit has been reached. For example, if the skip limit is 5 and an operator skips the same pick 5 times, the application automatically cancels the pick and processes the cancellation according to this cancel code. |

## Cancel Code fields

 
| Field | Description |
| --- | --- |
| Cancel Code | Unique identifier for the cancel code. A cancel code is a configuration that determines how the application processes a pick cancellation to which the code is applied. |
| Description | Text that further describes the cancel code. Typically, the description identifies the reason for the cancellation or the actions that occur after the cancellation. For example, a cancel code of CANCEL-NO-REALLOC can be used to indicate that the application does not reallocate inventory for the cancelled pick work. The cancel code and its description are displayed to users for selection during a pick cancellation. |
| Short Description | Brief description of the cancel code that is displayed in RF screens. |
| RF | If Yes, the cancel code appears in the list of cancel codes available to RF operators for selection.<br > If No, the cancel code is only available for selection when a user cancels a pick from a workstation. You may want to prevent RF operators from using cancel codes that perform certain functions. For example, you may allow RF operators to select a code that cancels and reallocates a pick, but not one that cancels a pick without reallocating it. |
| Voice | Value used by facilities that use voice terminals. When the voice terminal operator is prompted for the cancel code, the operator can speak the numeric value to select the cancel code. |
| Reallocation | If Yes, then when a user selects the cancel code during pick cancellation, the application attempts to reallocate the pick based on the reallocation settings. For example, set this field to Yes for codes such as C-RA (cancel and reallocate) and C-R-R-L (cancel and reallocate, reuse location).<br > If No, then when a user selects the cancel code, the pick is not reallocated. Cancelling a pick without reallocating it is typically used to short an order so that picked inventory ships on time or to cancel a pick that is no longer needed because the order was cancelled. For example, set this field to No for a code such as CNREALL (cancel no reallocation). |
| Location Reuse | If Yes, then when a cancelled pick is reallocated, the application includes the source location from which the pick was originally allocated when searching for available inventory. Selecting Yes does not limit the search to the original location, but it does include that location in the search. You may select Yes, for example, for cancel codes used during carton picking when the picking container becomes full. If the remaining picks are cancelled and reallocated, the application could still allocate inventory from the original location since there was no shortage of inventory.<br > **Note**: If the operator sets the location to error status, the application skips the location during reallocation.<br > If No, then during reallocation, the application omits the source location from which the pick was originally allocated when searching for available inventory. This option is useful when a location is damaged and not suitable for reallocation.<br > Only available if the cancel code automatically reallocates the pick. |
| Type of Picks | Determines the type of pick that is created when the cancel code reallocates a pick. The application :<br>-   • **Order**: Attempts to allocate only outbound picks, not replenishments. Use this value if you want the application to attempt allocate the pick and not wait for the replenishment to finish.
<br>-   • **Replenishment**: Attempts to reallocate only replenishments. Use this value if you want the application to cancel a replenishment pick (such as for a top-off replenishment) and then reallocate it.
<br>-   • **Order and Replenishment**: Attempts to allocate the outbound picks and, if the pickface is empty, replenishments. Use this value if you want the application to attempt to reallocate the pick and avoid shorting the order if at all possible.
<br>-   • **Top-off Replenishment**: Attempts to allocate a new top-off replenishment only. Use this value if you want the application to cancel a replenishment and generate a top-off replenishment, but not a demand or emergency replenishment.
<br > Only available if the cancel code automatically reallocates the pick. |
| Work Assignments | Determines whether a new pick, resulting from the reallocation of a cancelled pick, can be added to a work assignment.<br>-   • **A user will manually assign**: The application does not attempt to assign the new picks automatically. From a workstation, the user may want to manually assign the new picks to work assignments if the reason for the cancellation requires manual intervention.
<br>-   • **The system will automatically assign**: The application attempts to reassign the picks automatically.
<br > Only available if the cancel code automatically reallocates the pick. |
| Stage Shipment | If Yes, the shipment for which a pick is cancelled using the cancel code is automatically staged when the rest of the inventory for the shipment has been deposited to the staging lane or cancelled with a cancel code that allows auto-staging to take place. Select Yes if you want to allow an incomplete shipment to be staged.<br > If No, the shipment for which a pick is cancelled is not staged automatically. Instead, it must be staged manually. Select No, for example, if you want to postpone staging until the inventory for reallocated picks arrives at the staging location. |
| Send Alert | If Yes, Event Management sends an alert to users that are configured to be notified of picks cancelled using this code.<br > If No, Event Management does not send an alert when picks are cancelled using this code. |
| Count Inventory | Determines whether a count is generated when a pick is cancelled using this code.<br>-   • **Never**: A count is never generated when using the cancel code. Select this option for cancel codes that are used when, for example, a pick is no longer needed because the order is cancelled.
<br>-   • **Always**: A count is always generated when using the cancel code, but the count must be released manually. Select this option for cancel codes that are used when, for example, a pick is cancelled due to an inventory inaccuracy but you want to delay the release of counts until resources are available to complete them.
<br>-   • **Always and immediately release**: A count is always generated when using the cancel code and the count is released immediately. Select this option for cancel codes that are used when, for example, a pick is cancelled due to an inventory inaccuracy in a location and you want the counts released immediately.
<br>-   • **Based on Tolerance**: A count is generated and released only if the value of the cancelled pick exceeds the count threshold cost or unit value defined for the item or the warehouse. Select this option if you only want to generate a count for a significant inventory discrepancy. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
