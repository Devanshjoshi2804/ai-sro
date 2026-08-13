---
title: "User configuration"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/em/user_configuration.htm"
source: "/content/em/user_configuration.htm"
toc_path:
  - "Event Management"
  - "Administration"
  - "User configuration"
sections:
  - "Configure event subscriptions for a user"
  - "Set the out of office feature on or off for a user"
  - "Configure notification accounts for a user"
images: []
source_sha1: b30372dd1d1f67afd473baa4b9447f75470dab95
---
# User configuration

You can use the User Configuration page to configure the following features for another user:

-   Event and event group subscriptions with optional qualifiers. See [Subscription](../configuration.md), [Event groups](../configuration.md), and [Qualifiers](../configuration.md).
-   Out of office feature. See [Out of office feature](../configuration.md).
-   Notification accounts. See [Notification accounts](../configuration.md).

## Configure event subscriptions for a user

1.  Select **Event Management > Administration > User Configuration**.
2.  In the grid, click the user name.
3.  Under **EVENT SUBSCRIPTION**, click **What events would you like to receive alert notifications on**.
4.  To receive alerts and alert notifications for an event or modify an existing subscription:
    1.  In the grid, expand the event group to which the event belongs and select the event.
    2.  To receive alerts and alert notifications, click **Subscribe**.
    3.  To modify an existing subscription, click **Modify**.
    4.  Enter information in the [Subscriber fields](event-subscribers.md).
    5.  To add a qualifier, under **QUALIFIERS**, enter information in fields, and then click **Add**.
    6.  To delete a qualifier:
        1.  In the grid, select the check box next to the qualifier, and then click **Delete**. A confirmation message is displayed.
        2.  Click **OK**.
    7.  Click **Save**. A check mark is displayed in the grid next to the event.
5.  To permanently stop receiving alerts and alert notifications for an event, in the grid, expand the event group to which the event belongs, select the event, and then click **Unsubscribe**. A check mark is no longer displayed next to the event.
    
    **IMPORTANT**: When you unsubscribe from an event, all personalization (such as qualifiers) is deleted and must be configured again if you decide to resubscribe to the event. Instead, you can perform one of the following tasks:
    
    -   To temporarily stop receiving alerts and alert notifications for one or more specific subscribed events, modify the event subscription and set the **Disable Subscription** field to **Yes**.
    -   To temporarily stop receiving alerts and alert notifications for all subscribed events, set the out of office feature on. See [Set the out of office feature on or off](../configuration.md) or [Set the out of office feature on or off for a user](#Set_the_out_of_office_feature_on_or_off_for_a_user).
    
6.  To automatically subscribe to new events as they are added to an event group, in the grid, select the event group, and then click **Subscribe**. A check mark is displayed in the grid next to the event group.
7.  To stop automatically subscribing to new events as they are added to an event group, in the grid, select the event group, and then click **Unsubscribe**. A check mark is no longer displayed in the grid next to the event group. You must manually subscribe to new events after they are added to the event group.

## Set the out of office feature on or off for a user

1.  Select **Event Management > Administration > User Configuration**.
2.  In the grid, click the user name.
3.  To set the out of office feature on, under **OUT OF OFFICE**:
    1.  Set the **Use out of office settings** field to **On**.
    2.  To stop alerts and alert notifications, select **Stop Alert Delivery**.
    3.  To forward alerts and alert notifications to another user, select **Forward Alerts To**, and then from the **select user** drop-down list, select the user.
4.  To set the out of office feature off, under **OUT OF OFFICE**, set the **Use out of office settings** field to **Off**.

## Configure notification accounts for a user

1.  Select **Event Management > Administration > User Configuration**.
2.  In the grid, click the user name.
3.  Under **NOTIFICATION ACCOUNTS**, click **Configure notification accounts that should receive alert notifications**.
4.  Perform one of the following tasks:
    -   To add an account, click **Add Account**.
    -   To modify an account, in the grid, click the account.
5.  Enter information in the [Account fields](../configuration.md).
6.  Perform one of the following tasks:
    -   To save your changes and send a test message, click **Save and Send a Test Email**.
    -   To save your changes without sending a test message, click **Save**.
7.  To delete an account:
    
    **Notes**:
    
    -   You can select and delete more than one account at the same time.
    -   You cannot delete the default account.
    
    1.  In the grid, select the check box next to the account, and then click **Remove Account(s)**. A confirmation message is displayed.
    2.  Click **OK**.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
