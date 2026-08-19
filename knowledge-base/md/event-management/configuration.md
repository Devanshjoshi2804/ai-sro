---
title: "Configuration"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/em/configuration.htm"
source: "/content/em/configuration.htm"
toc_path:
  - "Event Management"
  - "Configuration"
sections:
  - "Subscription"
  - "Event groups"
  - "Qualifiers"
  - "Out of office feature"
  - "Notification accounts"
  - "Configure event subscriptions"
  - "Set the out of office feature on or off"
  - "Configure notification accounts"
  - "Subscriber fields"
  - "Account fields"
images: []
source_sha1: 989385629e5a947ad1e7476e6a5c2ef2c9c8c7f6
---
# Configuration

Users with access to the Configuration page can supply their own configuration for the following features:

-   Event and event group subscriptions, with optional qualifiers
-   Out of office feature
-   Notification accounts

Users without access are typically configured by an administrator. See [User Configuration](administration/user-configuration.md).

## Subscription

Subscription is the act of specifying whether you want to receive alerts and alert notifications whenever a business process action occurs in an integrated application. You subscribe to events to receive their corresponding alerts and alert notifications. You only receive alerts and alert notifications for events to which you are subscribed.

Subscription can be performed by a user (depending on configuration settings) or by an administrator on behalf of a user on the Event Subscription page (see [Configure event subscriptions](#Configure_event_subscriptions) or [Configure event subscriptions for a user](administration/user-configuration.md)). The Event Subscription page enables you to view the following information:

-   All available events and event groups
-   Subscribed events
-   Event groups that have been enabled for automatic future subscription

In addition, the Event Subscription page enables you to perform the following tasks:

-   Select the events for which to receive alerts and alert notifications (subscribe to events)
-   Personalize the following alert attributes and functionality:
    -   Priority to assign to the alert. See [Priorities](alerts.md).
    -   Whether to receive alert attachments
    -   Qualifiers to specify the criteria to determine exactly which alerts and alert notifications are sent (instead of receiving all alerts and alert notifications for an event). See [Qualifiers](#Qualifiers).
-   Stop receiving alerts and alert notifications without permanently removing the associated event subscription by disabling the event subscription
-   Select the events for which to permanently stop receiving alerts and alert notifications (unsubscribe from events)
-   Select the event groups to which to automatically subscribe to new events as they are added to the event group (subscribe to event groups). See [Event groups](#Event_groups).
-   Select the subscribed event groups for which to stop automatically subscribing to future events (unsubscribe from event groups)

If no users subscribe to an event, then no alerts or alert notifications are sent by Event Management when the business process action occurs.

Unsubscribing is the act of specifying whether a user no longer wants to receive alerts and alert notifications whenever a business process action occurs in an integrated application. Unsubscribing is permanent and any user-specific configuration of the subscription (such as priority and qualifiers) is removed. Optionally, you can temporarily stop receiving alerts and alert notifications by disabling the event subscription or using the out of office feature. See [Out of office feature](#Out_of_office_feature).

## Event groups

An event group is a code that specifies the category of the event. Assigning an event to an event group helps manage the events since many events can be added to an Event Management instance. In addition, the event group supports automatic new event subscription. If you are subscribed to an event group and a new event is added to the group, you are automatically subscribed to the new event. Subscribing to an event group does not subscribe you to all the events in the event group. This behavior gives you the flexibility of only subscribing to the events in an event group for which you want to receive alerts and alert notifications, while not having to constantly check for new events that are added after you subscribe. When you receive the first alert or alert notification for a newly added event in a subscribed event group, you can choose to remain subscribed and keep receiving alerts and alert notifications, or navigate to the Event Subscription page to unsubscribe from the new event to stop receiving alerts and alert notifications.

An event can belong to only one event group.

**Example**: A payroll event group contains payroll report events. Each payroll report event corresponds to a business process action that can occur when a different payroll report is generated. Payroll reports contain time-sensitive information, so payroll clerks want to be notified when a report that is associated with their department is available. During initial configuration, a payroll clerk only subscribes to a few relevant report events in the payroll event group. However, new reports are added quarterly. Instead of checking Event Management on a regular basis and subscribing to a new relevant report event, the payroll clerk subscribes to the payroll event group. When new events assigned to the payroll event group are added to Event Management, the payroll clerk is automatically subscribed to the new events. When the payroll clerk receives the first alert or alert notification for generation of the new report, the payroll clerk can choose to unsubscribe if the new report is not relevant. By subscribing to the event group in addition to some of its individual events, the payroll clerk does not miss alerts or alert notifications about new reports.

## Qualifiers

A qualifier is a filter that enables you to control the alerts and alert notifications that you receive. Qualifiers are optional. The following examples illustrate how you might use qualifiers:

-   Instead of being notified every time inventory changes, you add a qualifier to the low inventory event subscription that specifies the quantity where you want to start being notified.
-   Instead of being notified every time a pick is cancelled, you add a qualifier to the cancelled pick event subscription that specifies a customer so that you only receive an alert and alert notification when a cancelled pick is associated with the customer. In addition, you can add another qualifier that specifies an item number so that you only receive an alert and alert notification when a cancelled pick is associated with the customer and is for the specific item number.

You specify a qualifier when you subscribe to an event. See [Configure event subscriptions](#Configure_event_subscriptions).

A qualifier is comprised of the following parts:

-   Field
    
-   Operator
    
-   Statement
    

Events typically include a list of qualifier fields from which you can choose to build your user-specific qualifier. Administrators can add qualifier fields to events.

If you specify more than one qualifier, then all the qualifiers must be true for you to receive an alert and alert notification. For example, if you specify customer = CUST1 and item = SOAP for the cancelled pick event, then you only receive an alert and alert notification when the cancelled pick is for CUST1 and SOAP, not for CUST1 and some other item, or SOAP and some other customer.

You can also specify multiple values for a qualifier to receive alerts and alert notifications that match or are similar to one of the values. For example, you can specify that you only want to receive alerts and alert notifications associated with CUST1, CUST2, and CUST3, or you only want to receive alerts and alert notifications associated with storage locations that start with RACK.

**Note**: You do not need to configure qualifiers for the **Client** field unless you only want to receive alerts and alert notifications for specific authorized clients instead of all authorized clients. Event Management automatically filters alerts by the clients for which you are authorized.

## Out of office feature

The out of office feature enables you to temporarily stop receiving alerts and alert notifications or redirect them to another user without unsubscribing from the associated events. For example, before a vacation you may want to temporarily stop receiving alerts and alert notifications, so you set the out of office feature on. When you return from vacation, you can resume receiving alerts and alert notifications by setting the out of office feature off. When the out of office feature is on, you do not receive alerts or alert notifications for any of your subscribed events, and after you set the out of office feature off, you do not receive the alerts or alert notifications that occurred while the out of office feature was on.

The out of office feature can be managed by a user (depending on configuration settings) or by an administrator on behalf of a user. See [Set the out of office feature on or off](#Set_the_out_of_office_feature_on_or_off) or [Set the out of office feature on or off for a user](administration/user-configuration.md).

**Notes**:

-   To permanently stop receiving alerts and alert notifications, unsubscribe from the associated event instead of setting the out of office feature on.
-   To temporarily stop receiving alerts and alert notifications for one or more specific subscribed events instead of all subscribed events, disable the event subscription.
-   See [Configure event subscriptions](#Configure_event_subscriptions) or [Configure event subscriptions for a user](administration/user-configuration.md).

## Notification accounts

Notification accounts enable you to specify the email and instant message accounts to which Event Management is to send your alert notifications based on the priority you configure for the event subscription. Notification accounts enable you to specify that alerts of a certain priority are sent to a specific account.

You must also designate one of your accounts as the default account. If you do not configure an account for a specific priority, alert notifications with that priority are sent to your default account.

After adding accounts, you can use the Notification Accounts page to view, modify, and delete accounts.

Notification accounts can be managed by a user (depending on configuration settings) or by an administrator on behalf of a user. See [Configure notification accounts](#Configure_notification_accounts) or [Configure notification accounts for a user](administration/user-configuration.md).

## Configure event subscriptions

1.  Select **Event Management > Configuration**.
2.  Under **EVENT SUBSCRIPTION**, click **What events would you like to receive alert notifications on**.
3.  To receive alerts and alert notifications for an event or modify an existing subscription:
    1.  In the grid, expand the event group to which the event belongs and select the event.
    2.  To receive alerts and alert notifications, click **Subscribe**.
    3.  To modify an existing subscription, click **Modify**.
    4.  Enter information in the [Subscriber fields](#Subscriber_fields).
    5.  To add a qualifier, under **QUALIFIERS**, enter information in the fields, and then click **Add**.
    6.  To delete a qualifier:
        1.  In the grid, select the check box next to the qualifier, and then click **Delete**. A confirmation message is displayed.
        2.  Click **OK**.
    7.  Click **Save**. A check mark is displayed in the grid next to the event.
4.  To permanently stop receiving alerts and alert notifications for an event, in the grid, expand the event group to which the event belongs, select the event, and then click **Unsubscribe**. A check mark is no longer displayed next to the event.
    
    **IMPORTANT**: When you unsubscribe from an event, all personalization (such as qualifiers) is deleted and must be configured again if you decide to resubscribe to the event. Instead, you can perform one of the following tasks:
    
    -   To temporarily stop receiving alerts and alert notifications for one or more specific subscribed events, modify the event subscription and set the **Disable Subscription** field to **Yes**.
    -   To temporarily stop receiving alerts and alert notifications for all subscribed events, set the out of office feature on. See [Set the out of office feature on or off](#Set_the_out_of_office_feature_on_or_off) or [Set the out of office feature on or off for a user](administration/user-configuration.md).
    
5.  To automatically subscribe to new events as they are added to an event group, in the grid, select the event group, and then click **Subscribe**. A check mark is displayed in the grid next to the event group.
6.  To stop automatically subscribing to new events as they are added to an event group, in the grid, select the event group, and then click **Unsubscribe**. A check mark is no longer displayed in the grid next to the event group. You must manually subscribe to new events after they are added to the event group.

## Set the out of office feature on or off

1.  Select **Event Management > Configuration**.
2.  To set the out of office feature on, under **OUT OF OFFICE**:
    1.  Set the **Use out of office settings** field to **On**.
    2.  To stop alerts and alert notifications, select **Stop Alert Delivery**.
    3.  To forward alerts and alert notifications to another user, select **Forward Alerts To**, and then from the **select user** drop-down list, select the user.
3.  To set the out of office feature off, under **OUT OF OFFICE**, set the **Use out of office settings** field to **Off**.

## Configure notification accounts

1.  Select **Event Management > Configuration**.
2.  Under **NOTIFICATION ACCOUNTS**, click **Configure notification accounts that should receive alert notifications**.
3.  Perform one of the following tasks:
    -   To add an account, click **Add Account**.
    -   To modify an account, in the grid, click the account.
4.  Enter information in the [Account fields](#Account_fields).
5.  Perform one of the following tasks:
    -   To save your changes and send a test message, click **Save and Send a Test Email**.
    -   To save your changes without sending a test message, click **Save**.
6.  To delete an account:
    
    **Notes**:
    
    -   You can select and delete more than one account at the same time.
    -   You cannot delete the default account.
    
    1.  In the grid, select the check box next to the account, and then click **Remove Account(s)**. A confirmation message is displayed.
    2.  Click **OK**.

## Subscriber fields

 
| Field | Description |
| --- | --- |
| User | Unique identifier of the person subscribed to the event so that the person receives alerts. See [Subscription](#Subscription). This field is typically display only, but is available when an administrator needs to specify the user for which the administrator is adding a subscription. See [View and manage alert details](administration/find-alert.md), [View and manage event details](administration/find-alert.md), and [Configure an event](administration/event-configuration.md). |
| Priority | Priority to associate with the alerts that are sent when the business process action occurs. For example, an alert that is informational for most users and is sent with a default priority of informational may be critical to you. Changing the priority of your alerts does not change the priority of another subscriber's alerts for the same event. See [Priorities](alerts.md). |
| Send Attachments | Specifies whether the alert is to include attachments such as a report (if any are sent with the alert). The default event may include attachments. However, you may not want your alert to include attachments, for example, when you want to know the business process action occurred but do not need the attachment.<br > Attachments are never sent to an instant message (IM) account. |
| Disable Subscription | If Yes, Event Management stops sending alerts for the event to the subscriber specified in the **User** field.<br > If No, Event Management sends alerts for the event to the subscriber.<br > See [Subscription](#Subscription). |
| Field | Variable name and data type associated with the event to be checked to qualify the alert. Formatted as <_Variable_> as <_Data Type_>. The <_Variable_> is typically a database table column name (for example, wh\_id) from the integrated application. The <_Data Type_> (for example, STRING or INTEGER) specifies the type of information that you need to enter in the **Statement** field.<br > **Note**: A qualifier is defined by the information entered in the **Field**, **Operator**, and **Statement** fields. See [Qualifiers](#Qualifiers). |
| Operator | Comparison operator between the entries in the **Field** and **Statement** fields.<br>-   • **\=**: Equal to.
<br>-   • **<**: Less than.
<br>-   •  > : Greater than.
<br>-   • **<=**: Less than or equal to.
<br>-   • **>=**: Greater than or equal to.
<br>-   • **!=**: Not equal to.
<br>-   • **like**: Similar to the text specified in the **Statement** field. Typically used when the **Statement** field contains the wildcard character (%).
<br>-   • **in**: Contained within the group of entities specified in the **Statement** field. |
| Statement | Value to compare to the **Field** drop-down list selection. See the **Field** drop-down list selection to determine the type of data (for example, STRING or INTEGER) that you need to enter. You can also enter a valid SQL in-clause. String values must be enclosed in single quotes; for example, 'CUST01'. Do not enclose numeric values or SQL expressions in quotes.<br > If you are entering multiple entries (for example, when selecting **in** from the **Operator** drop-down list), surround the entire list with parentheses and separate each item in the list with commas. For example, enter ('CUST1234','CUST1235','CUST1236') to receive alerts for customers CUST1234, CUST1235, and CUST1236.<br > Use a percent sign (%) as the wildcard character to represent one or more letters or numbers. For example, to match all warehouse storage locations that start with RACK, enter RACK%.<br > When using the **in** or **like** operator in the **Operator** field, the **Statement** field can be any valid SQL construct that can be used in the in-clause of a SQL query. If **Statement** is an invalid SQL construct for an in-clause, the query fails and Event Management treats the business process action as not matching the qualifier, so no alert is created. |

## Account fields

 
| Field | Description |
| --- | --- |
| Account Type | Type of digital messaging account to which alert notifications are sent.<br>-   • **Email**: Email account.
<br>-   • **Instant-Message**: Jabber instant message account. |
| Account | If you select **Email** from the **Account Type** drop-down list, **Account** is the address for the email account (for example, [\[email protected\]](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/em/cdn-cgi/l/email-protection)). If you select **Instant-Message** from the **Account Type** drop-down list, **Account** is the address for the Jabber-based instant message account (for example, [\[email protected\]](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/em/cdn-cgi/l/email-protection)).<br > **Note**: Jabber-based instant message accounts use email-like notation for the account address. |
| Priority | Priority of the alert notifications to be delivered to the account.<br>-   • **Informational**: Deliver alert notifications with an informational priority to the account.
<br>-   • **Actionable**: Deliver alert notifications with an actionable priority to the account.
<br>-   • **Critical**: Deliver alert notifications with a critical priority to the account.
<br > See [Priorities](alerts.md).<br > **Note**: You do not need to create a notification account for each priority. Your alerts with priorities that are not assigned to a specific account are sent to your default account defined in the **Set as Default** field. |
| Set as Default | Specifies whether the notification account is the default account for your alert notifications when none of your other accounts apply based on priority. If an account is not specified for a priority, your alert notifications with that priority are sent to your default account. Only one of your accounts can be specified as the default account. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
