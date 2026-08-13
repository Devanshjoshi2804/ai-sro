---
title: "Send RF Message"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/message.htm"
source: "/content/message.htm"
toc_path:
  - "Warehouse Management"
  - "Shared functions"
  - "Send RF Message"
sections:
  - "Send a message to an RF device"
images:
  - "/content/resources/images/image1083390.png"
source_sha1: dc6c8a50941ea658be5e9e7f1fcf16ba8ec6db92
---
# Send RF Message

The Send RF Message page is accessible from the following modules: **Inventory**, **Outbound Planner**, **Picking**, **Production**, **Receiving**, **Shipping**, or **Yard**.

This page enables you to send messages to RF operators and, if necessary, shut down an operator's device. When you first access the page, you must select the recipient of the message. Specifically, you can select one or more recipients in the follows ways:

-   By logged in users. When you select a user that is logged in, the device on which the user is logged in is also selected.
-   By devices on which operators are currently logged in. When you select a device, the logged in user for that device is also selected.
-   By roles for which there is at least one user logged in on an RF device. When you select a role, the logged in users and associated RF devices are also selected. Messages are only sent to the users of the role that are logged in.

Message history is retained and displayed on the Message page under History, but since messages are not saved to the database, the history is cleared if you change the recipient list or navigate to a different application module.

## Send a message to an RF device

1.  View the Send RF Message page.
    
    1.  Select one of the following modules: **Inventory**, **Outbound Planner**, **Picking**, **Production**, **Receiving**, **Shipping**, or **Yard**.
    2.  Select **Send RF Message**.
    
2.  Under **Recipients**, click **Select Recipients**. The Select Recipients window is displayed.
3.  Perform one or more of the following tasks:
    
    **Note**: You can click **Clear** to deselect all of the selected recipients. You can click ![Refresh](../../../images/resources/images/image1083390.png) to refresh the display of logged in users and devices.
    
    -   Under **Logged In Users**, select the check box next to the user that will receive the message. The devices on which the user is logged in are automatically selected.
    -   Under **RF Devices In Session**, select the check box next to the device that will receive the message. The user logged in to the device is automatically selected.
    -   Under **Authorized Roles**, select the check box next to the roles that will receive the message. The logged in users (and the devices to which the users are logged in) assigned to the role are automatically selected.
4.  Click **OK**.
5.  In the **Message** field, enter text for the message to send to the selected recipients.
    
    **Note**: The maximum number of characters for a message is 200.
    
6.  Under **Message Type**, select the check box next to one or both of the following types:
    -   **Display**: The text entered in the **Message** field is sent to and displayed on the screen of the selected RF devices in session.
    -   **Shut Down**: The selected RF devices in session receive a message that will shut down the device. If you send a shut down message, the operator's device immediately loses connection to the host. If you send both a display message and shut down message, the device loses connection when the operator acknowledges the display message.
7.  Click **Send**. A confirmation message is displayed.
8.  Click **OK**.
9.  Under **History**, view the message history that displays the message text, and the date and time at which the message was sent.
    
    **Note**: Since messages are not saved to the database, the history is cleared if you change the recipient list or navigate to a different application module.
    

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
