---
title: "Storage Override Reasons"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/storage_override_reasons.htm"
source: "/content/storage_override_reasons.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inbound"
  - "Storage"
  - "Storage Override Reasons"
sections:
  - "Add or modify a storage override reason"
  - "Delete a storage override reason"
  - "Storage Override Reasons fields"
images: []
source_sha1: 9d1287aa875044a556255abe00659273af8c3156
---
# Storage Override Reasons

An override reason is a configuration that provides the reason for a location override, and the processing that takes place as a result of the override.

When an RF operator overrides an allocated location during directed putaway, the operation selects a reason for the override. RF operators may need to override a putaway location for multiple reasons, such as if there is damaged inventory in the location, if mixing items is not allowed, or if no more inventory will fit in the location. An override reason can be configured to generate a cycle count, change the location's status (such as to place it in Error) and, if the location status is changed to Full, update the location's maximum capacity to the current capacity.

## Add or modify a storage override reason

1.  Select **Configuration > Inbound > Storage > Storage Override Reasons**.
2.  Perform one of the following tasks:
    -   To add an override reason, click **Add**.
    -   To modify an override reason, in the grid, click the override reason ID.
    -   To copy an override reason, in the grid, select the check box next to the override reason, and then click **Copy**.
3.  Enter information in the [Storage Override Reasons fields](#Storage_Override_Reasons_fields).
4.  Click **Save**.

## Delete a storage override reason

1.  Select **Configuration > Inbound > Storage > Storage Override Reasons**.
2.  In the grid, select the check box next to the override reasons to delete.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Storage Override Reasons fields

 
| Field | Description |
| --- | --- |
| Override Reason ID | Value that represents the reason for a location override during directed putaway, and the processing that takes place as a result of the override.<br > When an RF operator overrides an allocated location during directed putaway, the operation selects a reason for the override. This is the value the operator selects on the RF device. |
| Default | If Yes, indicates that this is the override reason that is displayed on the RF Override Location screen by default when the RF operator attempts to override an allocated location during directed putaway. The operator can accept the default value or select a different one. Only one override reason can be configured as the default. |
| Description | Description of the override reason that explains why the inventory cannot be put away to the application-allocated location. This description is displayed on the override location lookup screen on the RF device. |
| Cycle Count Action | Code that identifies whether a cycle count is automatically generated for the location whenever the override reason is applied.<br>-   • **Do Not Generate Count**: A cycle count is not generated.
<br>-   • **Generate but Do Not Release Count**: A cycle count is generated but the count work is not released; it must be released manually.
<br>-   • **Generate/Release Count**: A cycle count is generated and the count work is released.
<br>-   • **Generate/Release Based on Tolerance**: A cycle count is generated and released only if the value of the cancelled pick exceeds the count threshold cost or unit value defined for the item or the warehouse. |
| Set Location Status To | Value that determines whether the status of a location is changed when an RF operator overrides a directed putaway to the location using the override reason.<br>-   • **Error**: The location status is set to Error. Select Error, for example, for an override reason that is used to indicate that the inventory in the location or the location itself is damaged.
<br>-   • **Full**: The location status is set to Full if the storage zone is configured to allow it; otherwise, the status is not changed. Select Full, for example, for an override reason that is used to indicate there is no room for any more inventory in the location. Setting the status to Full prevents additional inventory from being directed to the location.
<br>-   • **No Change**: The location remains in its current status. Select No Change, for example, for an override reason that is used when there is nothing wrong with the location. |
| Set Maximum Capacity | Indicates that the maximum capacity for the location is set to its current capacity when an RF operator overrides a directed putaway to the location using the override reason. The capacity is reset only if the storage zone is configured to allow the maximum capacity to be reset.<br > If the check box is selected and if the storage zone allows the capacity to be changed, then when this override reason is used, the location's default maximum capacity is overridden and set to the current capacity of the location. The capacity change remains in effect until the location is emptied and no replenishment item configuration exists.<br > If deselected or if the storage zone does not allow the maximum capacity to be reset, then the location's maximum capacity is not changed. Only available if the value for the **Set Location Status To** field is set to Full. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
