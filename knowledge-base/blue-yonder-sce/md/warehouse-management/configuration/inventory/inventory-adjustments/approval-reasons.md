---
title: "Approval Reasons"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/approval_reasons.htm"
source: "/content/approval_reasons.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inventory"
  - "Inventory Adjustments"
  - "Approval Reasons"
sections:
  - "Add or modify an approval reason"
images: []
source_sha1: 7178a3e8a848b40636acfd8a49109a13e6236d1e
---
# Approval Reasons

An inventory adjustment approval reason is the user's response to explain why an inventory adjustment approval was either accepted or rejected.

Some inventory adjustments require approval by an authorized user, such as a supervisor. When a user performs an inventory adjustment that is equal to or exceeds a cost or unit adjustment threshold defined for the user, user's role, warehouse, or (in a 3PL environment) for a client or client group, the adjusted location is locked and the adjustment is not processed until it has been approved. If an adjustment is approved, the location is unlocked and the quantity in the location is adjusted; if an adjustment is rejected, the location is unlocked, and the quantity is not adjusted.

## Add or modify an approval reason

1.  Select **Configuration > Inventory > Inventory Adjustments > Approval Reasons**.
2.  Perform one of the following tasks:
    -   To add a new approval reason, click **Add**.
    -   To modify an approval reason, in the grid, click the reason.
    -   To copy an approval reason, in the grid, select the check box next to the reason, and then click **Copy**.
3.  Perform one of the following tasks:
    -   In the **Approval Reason** field, enter a reason code.
    -   To have the application supply a reason code, select the **System Generated** check box.
4.  In the **Approval Reason Description** field, enter a description of the reason.
5.  To assign the approval reason to clients:
    1.  Click **Clients**. The Clients page is displayed.
    2.  In the **Available** column, select the check box next to the clients that use the approval reason.
    3.  Click **Apply**.
6.  Click **Save**.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
