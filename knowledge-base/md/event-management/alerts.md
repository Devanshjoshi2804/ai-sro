---
title: "Alerts"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/em/alerts.htm"
source: "/content/em/alerts.htm"
toc_path:
  - "Event Management"
  - "Alerts"
sections:
  - "Notification details"
  - "Priorities"
  - "Acknowledgment"
  - "View and manage alerts"
  - "Alerts fields"
  - "Alert details fields"
images:
  - "/content/resources/images/image1033123.png"
  - "/content/resources/images/image1033123.png"
source_sha1: eb5dce7b1e8b22dfcdeadcc4939a3815fe54c8c3
---
# Alerts

An Event Management alert is an actual occurrence of a subscribed event in an integrated application. For example, Pick cancelled - @cancod is the alert for a specific occurrence of the WMD-CANCEL-PICK event that is a potential action that can occur during the cancel pick business process. When Event Management receives an alert, it adds the alert to each subscriber’s Alert Inbox page and sends each subscriber an alert notification. You use alerts to determine the actions, if any, to perform in response to the business process action. See [Events](events.md).

Alert notifications can be sent to you in the following formats:

-   Email message
-   Jabber instant message
-   Event Management Alert Inbox page

You can always view your alerts on the Event Management Alert Inbox page. You specify the other formats to use when you define your notification accounts. See [Notification accounts](configuration.md).

You can perform the following tasks for your alerts:

-   View the different parts of each alert
-   Acknowledge alerts
-   Mark alerts as read or unread
-   Delete alerts

On the Alert Inbox page, alerts that have not been read are displayed in bold text; once read, the alerts are displayed in normal text.

You should regularly delete alerts to keep your list small and manageable. Also, until an alert is acknowledged by at least one subscriber or deleted by all subscribers, the alert is still active and can continue to cause further processing, such as escalation (if configured to do so), and uses space in the database unnecessarily. Deleted alerts are not immediately removed from the database. Instead, they are permanently removed after the purging job runs on its configured schedule.

## Notification details

An alert and alert notification are comprised of the following parts:

-   **Subject**: Summary of the alert including applicable attributes (for example, order number).
-   **Priority**: Code that describes the importance of the alert. See [Priorities](#Priorities).
-   **Acknowledgment**: Whether you have acknowledged the alert, if the corresponding event is configured to require acknowledgment. See [Acknowledgment](#Acknowledgment).
-   **Duplicate count**: Number of duplicates, if any, for the alert. See [Duplicate alerts](administration/system-configuration.md).
-   **Date and time**: Date and time the alert was received by Event Management (not the date and time the business process action occurred in the integrated application).
-   **Source system**: Code for the integrated application that sent the alert.
-   **Message**: Description that includes details of the alert and specific attributes, such as order number or item number. The message is helpful in understanding and determining how to respond to the alert.
-   **Attachments**: Additional information, if any, sent with the alert, such as a report. The attachment icon (![Attachment](../../images/resources/images/image1033123.png)) is displayed for alerts that have an attachment.

## Priorities

A priority is a code that describes the importance of an event or alert.

-   **Informational**: The event or alert is noteworthy but typically requires no action. On the Alert Inbox, alert details, and Find Alert pages, informational alerts are not labeled.
-   **Actionable**: The event or alert requires action. On the Alert Inbox, alert details, and Find Alert pages, actionable alerts are labeled with a gray box that displays ACTIONABLE.
-   **Critical**: The event or alert is severe and requires immediate action. On the Alert Inbox, alert details, and Find Alert pages, critical alerts are labeled with a red box that displays CRITICAL.

The priority of an event or alert defaults to the priority specified by the integrated application that sends the event or alert, or set by an Event Management administrator. You can change the priority to associate with an event's alerts when you subscribe to the event. For example, an alert that is informational for most users and is sent with a default priority of informational may be critical to you. Changing the priority of your alert does not change the priority of other users' alerts for the same event. See [Configure event subscriptions](configuration.md). (Administrators, see [Configure event subscriptions for a user](administration/user-configuration.md).)

You can also use the priority to control the notification account that is used to send alert notifications. For example, you might want Event Management to send all critical messages to a mobile phone email account and send all other messages to a desktop computer email account. See [Configure notification accounts](configuration.md). (Administrators, see [Configure notification accounts for a user](administration/user-configuration.md).)

## Acknowledgment

Acknowledgment is the act of specifying whether an alert has been read and necessary action has been or will be taken. Only one user needs to acknowledge an alert, even if more than one user is subscribed to the alert. Event Management users acknowledge alerts by using the Alert Inbox page; Event Management administrators can acknowledge any user's alert on the Find Alert page. On the Alert Inbox page in the Acknowledgment column of the grid, acknowledged alerts display Acknowledged, alerts that need to be acknowledged display Required, and alerts that do not require acknowledgment display Not Required.

An alert only needs to be acknowledged if its corresponding event is configured to require acknowledgment. Additionally, only events that require acknowledgment can be configured to escalate or expire. If such an alert is not acknowledged by at least one subscriber within the configured time frame, the alert is escalated or expired.

The integrated application that sends the event to Event Management specifies whether the event requires acknowledgment. However, an administrator can change this requirement and configure escalation or expiration. See [Configure an event](administration/event-configuration.md).

## View and manage alerts

You can mark an alert as read without viewing the alert details, or the application automatically marks the alert as read once the alert details are viewed.

1.  Select **Event Management > Alert Inbox > Alerts**.
2.  To limit the list of alerts that is displayed, enter search criteria or select a filter. See [Filters](../get-started/filters.md).
3.  View information in the [Alerts fields](#Alerts_fields).
4.  To mark an alert as read without viewing the alert details, in the grid, select the check box next to the alert, and then from the **Actions** drop-down list, select **Mark as read**.
5.  To mark an alert as unread, in the grid, select the check box next to the alert, and then from the **Actions** drop-down list, select **Mark as unread**.
6.  To acknowledge an alert without viewing the alert details, in the grid, select the check box next to the alert, and then from the **Actions** drop-down list, select **Acknowledge**.
    
    **Note**: This option is only available if the alert requires acknowledgment.
    
7.  To delete an alert without viewing the alert details:
    1.  In the grid, select the check box next to the alert, and then from the **Actions** drop-down list, select **Delete**. A confirmation message is displayed.
    2.  Click **OK**.
8.  To view alert details:
    1.  In the grid, click the event.
    2.  View information in the [Alert details fields](#Alert_details_fields).
    3.  To mark the alert as unread, from **Actions** menu, click **Mark as unread**.
    4.  To acknowledge the alert, from the **Actions** menu, click **Acknowledge**.
        
        **Note**: This option is only available if the alert requires acknowledgment.
        
    5.  To delete the alert:
        1.  From the **Actions** menu, click **Delete**. A confirmation message is displayed.
        2.  Click **OK**.
    6.  To view the alert attachment under **Attachment**, click the file.
        
        **Note**: The **Attachment** area is only displayed if an attachment was sent with the alert.
        

## Alerts fields

 
| Field | Description |
| --- | --- |
| Event | Brief description or unique identifier for the event. This field displays the **Short Description** configured for the event, if it is not blank; otherwise, this field displays the **Name** configured for the event. See [Configure an event](administration/event-configuration.md). |
| Description | Summary description of the alert that may also contain alert details, such as a specific item. This field is based on the **Subject** field that is defined for the alert's event. |
| Acknowledgment | Text that indicates whether the alert has been read and necessary action has been or will be taken.<br>-   • **Acknowledged**: The subscriber has clicked Acknowledge for the alert on the Alert Inbox page or an administrator has acknowledged the alert using the Find Alert page. See [View and manage alerts](#View_and_manage_alerts) or [View and manage alert details](administration/find-alert.md).
<br>-   • **Not Required**: The event is not configured to require acknowledgment. See [Configure an event](administration/event-configuration.md).
<br>-   • **Required**: Either the alert has not yet been acknowledged, or the acknowledgment was undone on the Find Alert page by updating the alert's status to Who found. See [View and manage alerts and events](administration/find-alert.md). |
| Attachment | If a file is included with the alert, displays ![Attachment](../../images/resources/images/image1033123.png); otherwise, the cell is blank. |
| Date/Time | Date and time that the alert was created in Event Management (not the date and time that the alert occurred in the integrated application). |

## Alert details fields

 
| Field | Description |
| --- | --- |
| Expires or Escalates | Date and time that the alert has or will expire or escalate. If the alert's event is configured to expire, the field label displays **Expires**. If the alert's event is configured to escalate, the field label displays **Escalates**. If the alert's event is not configured to require acknowledgment, this field is not displayed. |
| Alert ID | Unique identifier for an alert. You can use the Alert ID during troubleshooting to match an alert to its corresponding database row or trace file contents. |
| Event Name | Name of the event that corresponds to the alert. An event is a potential action that could occur during a business process in an integrated application, and can be monitored and reported to Event Management. See [Events](events.md). |
| Source System | Code for the integrated application that sent the alert. |
| Command/Event | Value that indicates whether the alert's event is configured to escalate and, if so, what the system has or will do at escalation.<br>-   • **Command**: MOCA command or SQL statement that the system has or will run at alert escalation.
<br>-   • **Event**: Event that has or will be raised to send a follow-up alert at alert escalation.
<br>-   • **Blank**: The alert's event is not configured to escalate. It is either configured to expire or does not require acknowledgment. |
| Acknowledged By | Unique identifier of the first user who acknowledged the alert. If this field is blank, either no user has acknowledged the alert yet, or the alert's event is not configured to require acknowledgment. |
| Date/Time | Date and time that the alert was created in Event Management (not the date and time that the alert occurred in the integrated application). |
| Message | Full description with additional alert details that can be used to respond to the alert. Additional alert details can include the alert's specific qualifier fields, such as "Low Inventory - Widget01" or "Low Inventory - ComponentA". This field is based on the Message field that is defined for the alert's event. |
| Qualifier | Qualifier field associated with the event or alert. Qualifiers are specified when you subscribe to the event. See [Qualifiers](configuration.md). |
| Value | Value of the alert's qualifier field. |
| Attachment | File that is included with the alert. Clicking the link displays the file. If the alert includes more than one attachment, this file is a ZIP that contains all the attachments and clicking the link downloads the ZIP to your PC. This field is only displayed if an attachment is included with the alert. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
