---
title: "Hold Reasons"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/hold_reasons.htm"
source: "/content/hold_reasons.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inventory"
  - "Holds"
  - "Hold Reasons"
sections:
  - "Add or modify a hold reason"
  - "Delete a hold reason"
images: []
source_sha1: 9ae55643327fd7a8f8dfd2aeb0a0b190491528b2
---
# Hold Reasons

Hold reasons are codes that are appended to transactions in the application to further explain the reason for the hold. In a 3PL environment, you can assign hold reasons to specific clients, so that users can select only the reason associated with the client for the selected record.

## Add or modify a hold reason

1.  Select **Configuration > Inventory > Holds > Hold Reasons.**
2.  Perform one of the following tasks:
    -   To add a hold reason, click **Add.**
    -   To modify a hold reason, in the grid, click the reason.
    -   To copy a hold reason, in the grid, select the check box next to the reason, and then click **Copy**.
3.  Enter information in the following fields:
    
     
    | Field | Description |
    | --- | --- |
    | Hold Reason Code | Code that is appended to application transactions to further explain the reason for the hold. Only available when the **System Generated** check box is deselected. |
    | System Generated | Select this check box if you want the application to create a reason code. The code is displayed in the **Hold Reason Code** field after you click **Save**. |
    | Hold Reason | Text that describes the reason code and is displayed on the application windows and in reports. |
    
4.  For a 3PL environment, assign the reason code to specific clients:
    1.  Click **Clients**.
    2.  In the **Available** column, select the check box next to the clients that use the reason.
    3.  Click **Apply**.
5.  Click **Save**.

## Delete a hold reason

1.  Select **Configuration > Inventory > Holds > Hold Reasons.**
2.  In the grid, select the check box next to the hold reason to delete.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
