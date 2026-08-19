---
title: "Find alert"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/em/find_alert.htm"
source: "/content/em/find_alert.htm"
toc_path:
  - "Event Management"
  - "Administration"
  - "Find alert"
sections:
  - "View and manage alerts and events"
  - "View and manage alert details"
  - "View and manage event details"
  - "Find Alert fields"
  - "Alert Details fields"
  - "Subscriber fields"
  - "Event Details fields"
images: []
source_sha1: 78441e2a143782fb22487b2e920db52f99b38073
---
# Find alert

An Event Management user can only view the alerts that have been added to the user's Alert Inbox page. However, many more alerts exist in the application. As an administrative Event Management user, the Find Alert page is a tool that enables you to view all or a subset of the alerts that currently exist in the application, and then make changes to an alert, its event, or event subscribers to resolve alert issues. For example, you can view the following groups of alerts:

-   Alerts that were created on a specific day and time range
-   Held alerts, alerts in a status that is considered an error, expired alerts, or escalated alerts. Several [quick filters](../../get-started/filters.md) are available to limit the display to certain frequently requested types of alerts.

If an alert is associated with one or more subscribers, the application includes a row in the grid for each subscriber and the cell in the User column displays the subscriber's user identifier and, if available, first and last names. If an alert has no subscribers, the application includes one row in the grid and the cell in the User column is blank.

The Find Alert and alert details pages also enable you to view whether an alert has duplicates and the number of duplicates, and the alert's priority (critical or actionable). See [Duplicate alerts](system-configuration.md) and [Priorities](../alerts.md).

After finding an alert or group of alerts, you can update the alert's status or delete the alert. You can also perform tasks related to an alert's detail, such as acknowledging the alert and viewing a list of subscribers to the alert's event. Finally, you can perform tasks related to an alert's event detail, such as modifying the event.

## View and manage alerts and events

1.  Select **Event Management > Administration > Find Alert**.
2.  To limit the list of alerts that is displayed, perform one or more of the following tasks:
    -   Enter search criteria or select a filter. See [Filters](../../get-started/filters.md).
    -   Enter a date and time range, and then click **Go**.
3.  View information in the [Find Alert fields](#Find_Alert_fields).
4.  To modify the status of an alert:
    1.  In the grid, select the check box next to the alert. You can select more than one alert.
    2.  From the **Actions** drop-down list, select **Update Status**.
    3.  From the **Preferred Status** drop-down list, select the new status. See the [Find Alert fields](#Find_Alert_fields) for status definitions.
        
        **Note**: The **Preferred Status** drop-down list displays the statuses that are valid based on the alert's current status. If multiple alerts are selected, the **Preferred Status** drop-down list displays the statuses that are valid based on all the selected alerts' current statuses.
        
    4.  Click **Save**.
5.  To delete an alert:
    
    **IMPORTANT**: Only select alerts that have a user listed in the **User** column. The application does not allow you to delete alerts without an assigned user.
    
    1.  In the grid, select the check box next to the alert. You can select more than one alert.
    2.  From the **Actions** drop-down list, select **Delete**. A confirmation message is displayed.
    3.  Click **OK**.
6.  To view the alert's details, acknowledge or reject the alert, or manage subscriptions to the alert's event, in the grid, click the alert and continue to [View and manage alert details](#View_and_manage_alert_details).
7.  To view the details of the alert's event or modify the event, in the grid, click the event name and continue to [View and manage event details](#View_and_manage_event_details).

## View and manage alert details

1.  Select **Event Management > Administration > Find Alert**.
2.  To limit the list of alerts that is displayed, perform one or more of the following tasks:
    -   Enter search criteria or select a filter. See [Filters](../../get-started/filters.md).
    -   Enter a date and time range, and then click **Go**.
3.  In the grid, click the alert.
4.  View the [Alert Details fields](#Alert_Details_fields).
5.  To acknowledge an unacknowledged alert, click **Acknowledge**.
    
    **Notes**:
    
    -   You are recorded as the acknowledging user, not the alert's subscriber.
    -   The **Acknowledge** button is only displayed if the alert requires acknowledgment.
    
6.  To undo the acknowledgment of an acknowledged alert, click **Unacknowledge**. The **Acknowledged By** field is updated to be blank.
7.  To manage subscriptions:
    1.  Under **Alert Subscribers**, perform one of the following tasks:
        -   To manage the subscription of a user that is displayed, in the grid, click the user.
        -   To manage the subscription of a user that is not displayed, click **Manage Subscription**.
    2.  To add or modify a subscription:
        1.  Enter information in the [Subscriber fields](#Subscriber_fields).
        2.  To add a qualifier, under **QUALIFIERS**, enter information in the fields, and then click **Add**.
        3.  To delete a qualifier:
            1.  In the grid, select the check box next to the qualifier, and then click **Delete**. A confirmation message is displayed.
            2.  Click **OK**.
    3.  To unsubscribe the user from the event, select the **Unsubscribe user to this event** check box.
    4.  Click **Save**.

## View and manage event details

1.  Select **Event Management > Administration > Find Alert**.
2.  To limit the list of alerts that is displayed, perform one or more of the following tasks:
    -   Enter search criteria or select a filter. See [Filters](../../get-started/filters.md).
    -   Enter a date and time range, and then click **Go**.
3.  In the grid, perform one of the following tasks:
    -   Click the event name.
    -   Click the alert, and then click the event name.
4.  View the information in the [Event Details fields](#Event_Details_fields).
5.  To modify the event:
    1.  Click **Edit Global Event Details**.
    2.  Enter information in the [Event fields](event-configuration.md).
    3.  To configure expiration, under **ESCALATION/EXPIRATION**:
        1.  To immediately expire an unacknowledged alert, in the **Hours** and **Minutes** fields, enter 0 (zero).
        2.  To specify a duration to elapse before an unacknowledged alert is expired, in the **Hours** and **Minutes** fields, enter the values.
        3.  Leave the **Event/Command** field blank.
    4.  To configure escalation, under **ESCALATION/EXPIRATION**:
        1.  To immediately escalate an unacknowledged alert, in the **Hours** and **Minutes** fields, enter 0 (zero).
        2.  To specify a duration to elapse before escalating an unacknowledged alert, in the **Hours** and **Minutes** fields, enter the values.
        3.  In the **Event/Command** field, enter either the event that is used to create a follow-up alert or the command that is executed when the alert is escalated.
    5.  Click **Save**.
    6.  To view and manage qualifiers, under **QUALIFIERS**:
        1.  Click **Set qualifiers for this event**.
        2.  To add or modify a qualifier:
            1.  To add a qualifier, click **Add Qualifier**.
            2.  To modify a qualifier, in the grid, click the field name.
            3.  Enter information in the qualifier fields.
            4.  Click **Save**.
        3.  To delete a qualifier:
            1.  In the grid, select the check box next to the qualifier, and then click **Delete**. A confirmation message is displayed.
            2.  Click **OK**.
    7.  To add, modify, or copy event subscribers, under **EVENT SUBSCRIBERS**:
        1.  To add an event subscriber, click **Add**.
        2.  To copy an event subscriber, select the check box next to the subscriber, and then click **Copy**.
        3.  To modify an event subscriber, click the subscriber.
        4.  Enter information in the [Subscriber fields](#Subscriber_fields).
        5.  Click **Save**.
    8.  To delete an event subscriber, under **EVENT SUBSCRIBERS**:
        1.  Select the check box next to the subscriber.
        2.  Click **Delete**. A confirmation message is displayed.
        3.  Click **OK**.

## Find Alert fields

 
| Field | Description |
| --- | --- |
| Alert | Summary description of the alert that may also contain alert details, such as a specific item. This field is based on the **Subject** field that is defined for the alert's event. |
| Event Name | Brief description or unique identifier for the event. This field displays the **Short Description** configured for the event, if it is not blank; otherwise, this field displays the **Name** configured for the event. See [Configure an event](event-configuration.md). |
| Time | Date and time that the alert was created in Event Management (not the date and time that the alert occurred in the integrated application). |
| Status | Current state or condition of the alert, especially with respect to its progression through the Event Management processing.<br>-   • **Acknowledged**: The alert has been acknowledged. See [Acknowledgment](../alerts.md). To undo the acknowledgment, you can change the alert's status from Acknowledged to Who Found.
<br>-   • **Attachment Error**: An issue prevented adding the attachment to the alert notification email. After fixing the attachment issue, you can change the alert's status from Attachment Error to Pending to reprocess the alert.
<br>-   • **Bad XML in Remainder String**: The alert XML file sent from the integrated application cannot be successfully parsed by Event Management.
<br>-   • **Escalated**: The alert was escalated successfully; no event was involved (command-based escalation). To undo the escalation, you can change the alert's status from Escalated to Who Found or Who Not Found.
<br>-   • **Escalated Event**: The alert was escalated successfully; an event was involved. To undo the escalation, you can change the alert's status from Escalated to Who Found or Who Not Found.
<br>-   • **Escalated Event Error**: The alert was not escalated successfully because a follow-up alert could not be sent for the escalation event. To retry the escalation or allow another opportunity for acknowledgment, you can change the alert's status from Escalated Event Error to Who Found or Who Not Found.
<br>-   • **Escalation Error**: The alert was not escalated successfully because the escalation command did not complete successfully. To retry the escalation or allow another opportunity for acknowledgment, you can change the alert's status from Escalation Error to Who Found or Who Not Found.
<br>-   • **Expired**: The alert has expired. To undo the expiration, you can change the alert's status from Expired to Who Found or Who Not Found.
<br>-   • **Invalid Attachment Path**: The alert's attachment file name or path to the attachment location is invalid. After fixing the attachment file name or location, you can change the alert's status from Invalid Attachment Path to Pending to reprocess the alert.
<br>-   • **No Escalation Event Specified**: The alert indicates that escalation occurred at a specific date and time, but does not specify the escalation event. This can happen when an alert has an escalation date because the alert's event was previously configured for escalation but by the time escalation occurs, the event has been reconfigured to no longer escalate. To retry the escalation or allow another opportunity for acknowledgment, you can change the alert's status from No Escalation Event Specified to Who Found or Who Not Found.
<br>-   • **On Hold**: The alert has been held. See [Held alerts](held-alerts.md). You can change the alert's status from On Hold to Pending to reprocess the alert.
<br>-   • **Pending**: The alert has been received from the integrated application and is waiting to be processed and delivered to subscribers.
<br>-   • **Who Found**: One or more subscribers have been found for the pending alert and the alert will be delivered.
<br>-   • **Who Generation Failed**: The alert could not be successfully finalized for delivery because of subscriber, event qualifier, attachment, or other processing issues. After fixing the issue, you can change the alert's status from Who Generation Failed to Pending to reprocess the find subscriber process. You can also hold the alert by changing its status from Who Generation Failed to On Hold.
<br>-   • **Who Not Found**: No subscribers were found for the pending alert. See [Subscription](../configuration.md). After fixing the subscription, you can retry the find subscriber process by changing the alert's status from Who Not Found to Pending. Alternatively, you can put the alert on hold by changing its status from Who Not Found to On Hold. |
| User | Unique identifier of the user who subscribed to the event, and received or is to receive the alert. If no users are subscribed to the event, this field is blank. |
| Acknowledgment | Text that indicates whether the alert has been read and necessary action has been or will be taken.<br>-   • **Acknowledged**: The subscriber has clicked Acknowledge for the alert on the Alert Inbox page or an administrator has acknowledged the alert using the Find Alert page. See [View and manage alerts](../alerts.md) or [View and manage alert details](#View_and_manage_alert_details).
<br>-   • **Not Required**: The event is not configured to require acknowledgment. See [Configure an event](event-configuration.md).
<br>-   • **Required**: Either the alert has not yet been acknowledged, or the acknowledgment was undone on the Find Alert page by updating the alert's status to Who found. See [View and manage alerts and events](#View_and_manage_alerts_and_events). |

## Alert Details fields

 
| Field | Description |
| --- | --- |
| Expires or Escalates | Date and time that the alert has or will expire or escalate. If the alert's event is configured to expire, the field label displays **Expires**. If the alert's event is configured to escalate, the field label displays **Escalates**. If the alert's event is not configured to require acknowledgment, this field is not displayed. |
| Alert ID | Unique identifier for an alert. You can use the Alert ID during troubleshooting to match an alert to its corresponding database row or trace file contents. |
| Event Name | Brief description or unique identifier for the event. This field displays the **Short Description** configured for the event, if it is not blank; otherwise, this field displays the **Name** configured for the event. See [Configure an event](event-configuration.md). |
| Source System | Code for the integrated application that sent the alert. |
| Command/Event | Value that indicates whether the alert's event is configured to escalate and, if so, what the system has or will do at escalation.<br>-   • **Command**: MOCA command or SQL statement that the system has or will run at alert escalation.
<br>-   • **Event**: Event that has or will be raised to send a follow-up alert at alert escalation.
<br>-   • **Blank**: The alert's event is not configured to escalate. It is either configured to expire or does not require acknowledgment. |
| Acknowledged By | Unique identifier of the first user who acknowledged the alert. If this field is blank, either no user has acknowledged the alert yet, or the alert's event is not configured to require acknowledgment. |
| Date/Time | Date and time that the alert was created in Event Management (not the date and time that the alert occurred in the integrated application). |
| Message | Full description with additional alert details that can be used to respond to the alert. Additional alert details can include the alert's specific qualifier fields, such as "Low Inventory - Widget01" or "Low Inventory - ComponentA". This field is based on the Message field that is defined for the alert's event. |
| Qualifier | Qualifier field associated with the event or alert. Qualifiers are specified when you subscribe to the event. See [Qualifiers](../configuration.md). |
| Value | Value of the alert's qualifier field. |
| Subscriber | Unique identifier of a user who has subscribed to the event. |
| Notification | Value that indicates whether an alert has been sent to the subscriber. If an issue occurred during alert delivery, this field displays a message to help with diagnosing the issue. |
| Account | Notification account (or accounts, if more than one is configured for the same alert priority) to which an email or instant message is sent to notify the event subscriber of an alert. See [Notification accounts](../configuration.md). |
| Attachment | File that is included with the alert. Clicking the link displays the file. If the alert includes more than one attachment, this file is a ZIP that contains all the attachments and clicking the link downloads the ZIP to your PC. This field is only displayed if an attachment is included with the alert. |

## Subscriber fields

 
| Field | Description |
| --- | --- |
| User | Unique identifier of the person subscribed to the event so that the person receives alerts. See [Subscription](../configuration.md). This field is typically display only, but is available when an administrator needs to specify the user for which the administrator is adding a subscription. See [View and manage alert details](#View_and_manage_alert_details), [View and manage event details](#View_and_manage_event_details), and [Configure an event](event-configuration.md). |
| Priority | Priority to associate with the alerts that are sent when the business process action occurs. For example, an alert that is informational for most users and is sent with a default priority of informational may be critical to you. Changing the priority of your alerts does not change the priority of another subscriber's alerts for the same event. See [Priorities](../alerts.md). |
| Send Attachments | Specifies whether the alert is to include attachments such as a report (if any are sent with the alert). The default event may include attachments. However, you may not want your alert to include attachments, for example, when you want to know the business process action occurred but do not need the attachment.<br > Attachments are never sent to an instant message (IM) account. |
| Disable Subscription | If Yes, Event Management stops sending alerts for the event to the subscriber specified in the **User** field.<br > If No, Event Management sends alerts for the event to the subscriber.<br > See [Subscription](../configuration.md). |
| Field | Variable name and data type associated with the event to be checked to qualify the alert. Formatted as <_Variable_> as <_Data Type_>. The <_Variable_> is typically a database table column name (for example, wh\_id) from the integrated application. The <_Data Type_> (for example, STRING or INTEGER) specifies the type of information that you need to enter in the **Statement** field.<br > **Note**: A qualifier is defined by the information entered in the **Field**, **Operator**, and **Statement** fields. See [Qualifiers](../configuration.md). |
| Operator | Comparison operator between the entries in the **Field** and **Statement** fields.<br>-   • **\=**: Equal to.
<br>-   • **<**: Less than.
<br>-   •  > : Greater than.
<br>-   • **<=**: Less than or equal to.
<br>-   • **>=**: Greater than or equal to.
<br>-   • **!=**: Not equal to.
<br>-   • **like**: Similar to the text specified in the **Statement** field. Typically used when the **Statement** field contains the wildcard character (%).
<br>-   • **in**: Contained within the group of entities specified in the **Statement** field. |
| Statement | Value to compare to the **Field** drop-down list selection. See the **Field** drop-down list selection to determine the type of data (for example, STRING or INTEGER) that you need to enter. You can also enter a valid SQL in-clause. String values must be enclosed in single quotes; for example, 'CUST01'. Do not enclose numeric values or SQL expressions in quotes.<br > If you are entering multiple entries (for example, when selecting **in** from the **Operator** drop-down list), surround the entire list with parentheses and separate each item in the list with commas. For example, enter ('CUST1234','CUST1235','CUST1236') to receive alerts for customers CUST1234, CUST1235, and CUST1236.<br > Use a percent sign (%) as the wildcard character to represent one or more letters or numbers. For example, to match all warehouse storage locations that start with RACK, enter RACK%.<br > When using the **in** or **like** operator in the **Operator** field, the **Statement** field can be any valid SQL construct that can be used in the in-clause of a SQL query. If **Statement** is an invalid SQL construct for an in-clause, the query fails and Event Management treats the business process action as not matching the qualifier, so no alert is created. |

## Event Details fields

 
| Field | Description |
| --- | --- |
| Group | Event group associated with the event. See [Event groups](../configuration.md). |
| Primer Lock | If Yes, the event cannot be primed. This setting prevents an integrated application from overwriting the configuration of the event in Event Management. If you have modified the configuration of a pre-configured event in Event Management, then it is suggested that you set the **Primer Lock** field to **Yes**.<br > If No, the event can be primed. This setting enables an integrated application to overwrite the configuration of the event, which is useful if the integrated application sends an updated event. |
| Escalation/Expiration | Time delay, in hours and minutes, before the event's alerts escalate or expire. |
| Recommended Priority | Priority that is specified by the integrated application that sends the event or alert, or set by an Event Management administrator. Users can specify a different Priority for their alerts when they subscribe to the event. Priority is a code that describes the importance of an event or alert. Code that describes the importance of an event or alert.<br>-   • **Informational**: The event or alert is noteworthy but typically requires no action.
<br>-   • **Actionable**: The event or alert requires action.
<br>-   • **Critical**: The event or alert is severe and requires immediate action.
<br > See [Priorities](../alerts.md). |
| Acknowledgment Required | If Yes, the event's alerts must be acknowledged.<br > If No, the event's alerts do not require acknowledgment.<br > See [Acknowledgment](../alerts.md). |
| Event/Command | Value that specifies how to perform escalation or expiration of an alert. This value is applicable only when an event's alert must be acknowledged.<br>-   •
    
    **Event**: After the amount of time specified in the **Hours** and **Minutes** fields elapses, if the original event's alert has not been acknowledged, Event Management escalates the alert by using the event specified in the **Event/Command** field to create a follow-up alert.
    
    <br>
    
    **IMPORTANT**: The event specified in the **Event/Command** field must be defined in Event Management; otherwise, the event is assumed to be a command. See [Configure an event](event-configuration.md). Also, users must subscribe to the escalation event to receive an alert; users subscribed to the original event are not automatically subscribed to the escalation event. See [Subscription](../configuration.md).
    
    <br>
    
    **Note**: The event specified in the **Event/Command** field can be the same as the original event.
    
    <br>
<br>-   • **Command**: After the amount of time specified in the **Hours** and **Minutes** fields elapses, if the original event's alert has not been acknowledged, Event Management runs the command specified in the **Event/Command** field. Valid commands are MOCA commands or SQL statements. When executing the command, Event Management provides the command with the original alert's details, such as event name, qualifiers, and values, for optional use by the command.
<br>-   • **Blank**: After the amount of time specified in the **Hours** and **Minutes** fields elapses, if the original event's alert has not been acknowledged, Event Management expires the alert. |
| Subject | Text to use as a template for the alert subject. The subject typically provides a short summary of the alert. The subject is used to specify the subject line of the alert email and alert summary on the Event Management Alert Inbox page. The subject is not used for an alert instant message.<br > The subject can contain qualifier fields associated with the event to provide specific information about the alert. For example, "Low Inventory - @prtnum" could resolve to "Low Inventory - Widget01" or "Low Inventory - ComponentA" in an actual alert message subject line. See [Qualifiers](../configuration.md).<br > **Note**: Use @ to preface field names so that those parts of the message are automatically replaced with specific data when the alert notification is sent. |
| Locale | Locale of the **Subject** and **Message** fields.<br > Event Management generates alert text using the **Subject** and **Message** fields with a locale that matches the subscriber's locale. If there is no subject and message combination with a locale that matches the subscriber's locale, Event Management generates the alert subject and message based on the instance's default locale. See [Configure Event Management](system-configuration.md). |
| Description | Explanation of the event, such as its purpose or function. |
| Message | Text to use as a template for the alert message body. The message typically provides a description with details of the alert that can be used to respond to the alert.<br > The message can contain qualifier fields associated with the event to provide specific information about the alert. For example, "Item Identifier Low Inventory - @prtnum" could resolve to "Low Inventory - Widget01" or "Low Inventory - ComponentA" in an actual alert message body text. See [Qualifiers](../configuration.md).<br > **Note**: Use @ to preface field names so that those parts of the message are automatically replaced with specific data when the alert notification is sent. |
| Field Name | Qualifier field associated with the event or alert. Qualifiers are specified when you subscribe to the event. See [Qualifiers](../configuration.md). |
| Field Type | Data type of field (for example, string). |
| Subscriber | Unique identifier of a user who has subscribed to the event. |
| Account | Notification account (or accounts, if more than one is configured for the same alert priority) to which an email or instant message is sent to notify the event subscriber of an alert. See [Notification accounts](../configuration.md). |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
