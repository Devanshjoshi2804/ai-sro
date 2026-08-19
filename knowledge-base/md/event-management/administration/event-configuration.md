---
title: "Event configuration"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/em/event_configuration.htm"
source: "/content/em/event_configuration.htm"
toc_path:
  - "Event Management"
  - "Administration"
  - "Event configuration"
sections:
  - "Configure an event"
  - "Event grid fields"
  - "Event fields"
  - "Qualifiers fields"
  - "Subscriber fields"
images:
  - "/content/resources/images/image429922.png"
source_sha1: 2ba4f69ab5fe747aacbf12385b484c59efb09df7
---
# Event configuration

An event is a potential action that could occur during a business process in an integrated application, and can be monitored and reported to Event Management. Event Management uses events as templates for the alerts that an integrated application can potentially send to Event Management.

Several Supply Chain Execution (SCE) applications include pre-configured Event Management events that can be sent to Event Management (also known as priming events).

Event Management can only manage alerts for which it has a corresponding event. When Event Management is first installed, only the Event Management events can be displayed. As you install applications that can integrate with Event Management, you must configure the other applications to send events to Event Management. See the Event Management Configuration Guide.

Events can be overridden in Event Management to make them better fit your business needs. You can also manually create an event, if needed.

To save processing time and lower the overall number of events and alerts to manage, you should only include the events that you are using.

## Configure an event

1.  Select **Event Management > Administration > Events**.
2.  View the list of event groups and associated [Event grid fields](#Event_grid_fields).
3.  To view, modify, or delete an event, in the grid, click ![Expand](../../../images/resources/images/image429922.png) next to the event's event group.
4.  To add or modify an event:
    1.  To add an event, click **Add Event**.
    2.  To modify an event, in the grid, click the event.
    3.  Enter information in the [Event fields](#Event_fields).
    4.  To configure expiration, under **ESCALATION/EXPIRATION**:
        
        **Note**: The **Acknowledgment Required** field must be set to Yes for the ESCALATION/EXPIRATION fields to be enabled.
        
        1.  To immediately expire an unacknowledged alert, in the **Hours** and **Minutes** fields, enter 0 (zero).
        2.  To specify a duration to elapse before an unacknowledged alert is expired, in the **Hours** and **Minutes** fields, enter the values.
        3.  Leave the **Event/Command** field blank.
    5.  To configure escalation, under **ESCALATION/EXPIRATION**:
        
        **Note**: The **Acknowledgment Required** field must be set to Yes for the ESCALATION/EXPIRATION fields to be enabled.
        
        1.  To immediately escalate an unacknowledged alert, in the **Hours** and **Minutes** fields, enter 0 (zero).
        2.  To specify a duration to elapse before escalating an unacknowledged alert, in the **Hours** and **Minutes** fields, enter the values.
        3.  In the **Event/Command** field, enter either the event that is used to create a follow-up alert or the command that is executed when the alert is escalated.
    6.  Click **Save**.
    7.  To view and manage qualifiers, under **QUALIFIERS**:
        1.  Click **Set qualifiers for this even**t.
        2.  To add or modify a qualifier:
            1.  To add a qualifier, click **Add Qualifier**.
            2.  To modify a qualifier, in the grid, click the field name.
            3.  Enter information in the [Qualifiers fields](#Qualifiers_fields).
            4.  Click **Save**.
        3.  To delete a qualifier:
            1.  In the grid, select the check box next to the qualifier, and then click **Delete**. A confirmation message is displayed.
            2.  Click **OK**.
    8.  To add, modify, or copy event subscribers, under **EVENT SUBSCRIBERS**:
        1.  To add an event subscriber, click **Add**.
        2.  To copy an event subscriber, select the check box next to the subscriber, and then click **Copy**.
        3.  To modify an event subscriber, click the subscriber.
        4.  Enter information in the [Subscriber fields](#Subscriber_fields).
        5.  Click **Save**.
    9.  To delete an event subscriber, under **EVENT SUBSCRIBERS**:
        1.  Select the check box next to the subscriber.
        2.  Click **Delete**. A confirmation message is displayed.
        3.  Click **OK**.
5.  To delete an event:
    1.  In the grid, select the check box next to the event, and then click **Delete**. A confirmation message is displayed.
    2.  Click **OK**.
6.  To delete an event group:
    1.  In the grid, select the check box next to the event group, and then click **Delete**. A confirmation message is displayed.
    2.  Click **OK**.

## Event grid fields

 
| Field | Description |
| --- | --- |
| Event Group | Code that specifies the category of the event. See [Event groups](../configuration.md). |
| Events | Number of events in the event group. |
| Event | A potential action that could occur during a business process in an integrated application, and can be monitored and reported to Event Management. See [Events](../events.md). |
| Recommended Priority | Priority that is specified by the integrated application that sends the event or alert, or set by an Event Management administrator. Users can specify a different Priority for their alerts when they subscribe to the event. Priority is a code that describes the importance of an event or alert. Code that describes the importance of an event or alert.<br>-   • **Informational**: The event or alert is noteworthy but typically requires no action.
<br>-   • **Actionable**: The event or alert requires action.
<br>-   • **Critical**: The event or alert is severe and requires immediate action.
<br > See [Priorities](../alerts.md). |

## Event fields

 
| Field | Description |
| --- | --- |
| Name | Unique identifier for the event. The event name cannot contain spaces or special characters. |
| Group | Event group to associate with the event. You can select an existing group or enter a new group. See [Event groups](../configuration.md). |
| Recommended Priority | Priority that is specified by the integrated application that sends the event or alert, or set by an Event Management administrator. Users can specify a different Priority for their alerts when they subscribe to the event. Priority is a code that describes the importance of an event or alert. Code that describes the importance of an event or alert.<br>-   • **Informational**: The event or alert is noteworthy but typically requires no action.
<br>-   • **Actionable**: The event or alert requires action.
<br>-   • **Critical**: The event or alert is severe and requires immediate action.
<br > See [Priorities](../alerts.md). |
| Acknowledgment Required | If Yes, the event's alerts must be acknowledged.<br > If No, the event's alerts do not require acknowledgment.<br > See [Acknowledgment](../alerts.md). |
| Short Description | Brief description of the event. If this field is not blank, the short description is displayed on pages instead of the event name, so it should be written to help users differentiate between events. If this field is blank, the event name is displayed on pages. |
| Description | Explanation of the event, such as its purpose or function. |
| Primer Lock | If Yes, the event cannot be primed. This setting prevents an integrated application from overwriting the configuration of the event in Event Management. If you have modified the configuration of a pre-configured event in Event Management, then it is suggested that you set the **Primer Lock** field to **Yes**.<br > If No, the event can be primed. This setting enables an integrated application to overwrite the configuration of the event, which is useful if the integrated application sends an updated event. |
| Subject | Text to use as a template for the alert subject. The subject typically provides a short summary of the alert. The subject is used to specify the subject line of the alert email and alert summary on the Event Management Alert Inbox page. The subject is not used for an alert instant message.<br > The subject can contain qualifier fields associated with the event to provide specific information about the alert. For example, "Low Inventory - @prtnum" could resolve to "Low Inventory - Widget01" or "Low Inventory - ComponentA" in an actual alert message subject line. See [Qualifiers](../configuration.md).<br > **Note**: Use @ to preface field names so that those parts of the message are automatically replaced with specific data when the alert notification is sent. |
| Locale | Locale of the **Subject** and **Message** fields.<br > Event Management generates alert text using the **Subject** and **Message** fields with a locale that matches the subscriber's locale. If there is no subject and message combination with a locale that matches the subscriber's locale, Event Management generates the alert subject and message based on the instance's default locale. See [Configure Event Management](system-configuration.md). |
| Message | Text to use as a template for the alert message body. The message typically provides a description with details of the alert that can be used to respond to the alert.<br > The message can contain qualifier fields associated with the event to provide specific information about the alert. For example, "Item Identifier Low Inventory - @prtnum" could resolve to "Low Inventory - Widget01" or "Low Inventory - ComponentA" in an actual alert message body text. See [Qualifiers](../configuration.md).<br > **Note**: Use @ to preface field names so that those parts of the message are automatically replaced with specific data when the alert notification is sent. |
| Hours | Hours part of the time after which to escalate or expire an unacknowledged alert. This value is applicable only when an event's alert must be acknowledged.<br > If the **Event/Command** field is left blank, then the value in the **Hours** field is used to expire the alert; otherwise, the value in the **Hours** field is used to escalate the alert.<br>
**Notes**:

<br>

-   • The numbers entered in the **Hours** and **Minutes** fields are used in combination to specify an entire duration. For example, to escalate or expire an unacknowledged alert after three and one-half hours, in the **Hours** field enter 3, and in the **Minutes** field enter 30.
<br>-   • If both the **Hours** and **Minutes** fields are blank, the alert is not escalated or expired. If both the **Hours** and **Minutes** fields are zero, the alert is escalated or expired immediately.
<br>

 |
| Minutes | Minutes part of the time after which to escalate or expire an unacknowledged alert. This value is applicable only when an event's alert must be acknowledged.<br > If the **Event/Command** field is left blank, then the value in the **Minutes** field is used to expire the alert; otherwise, the value in the **Minutes** field is used to escalate the alert.<br>

**Notes**:

<br>

-   • The numbers entered in the **Hours** and **Minutes** fields are used in combination to specify an entire duration. For example, to escalate or expire an unacknowledged alert after three and one-half hours, in the **Hours** field enter 3, and in the **Minutes** field enter 30.
<br>-   • If both the **Hours** and **Minutes** fields are blank, the alert is not escalated or expired. If both the **Hours** and **Minutes** fields are zero, the alert is escalated or expired immediately.
<br>

 |
| Event/Command | Value that specifies how to perform escalation or expiration of an alert. This value is applicable only when an event's alert must be acknowledged.<br>-   •
    
    **Event**: After the amount of time specified in the **Hours** and **Minutes** fields elapses, if the original event's alert has not been acknowledged, Event Management escalates the alert by using the event specified in the **Event/Command** field to create a follow-up alert.
    
    <br>
    
    **IMPORTANT**: The event specified in the **Event/Command** field must be defined in Event Management; otherwise, the event is assumed to be a command. See [Configure an event](#Configure_an_event). Also, users must subscribe to the escalation event to receive an alert; users subscribed to the original event are not automatically subscribed to the escalation event. See [Subscription](../configuration.md).
    
    <br>
    
    **Note**: The event specified in the **Event/Command** field can be the same as the original event.
    
    <br>
<br>-   • **Command**: After the amount of time specified in the **Hours** and **Minutes** fields elapses, if the original event's alert has not been acknowledged, Event Management runs the command specified in the **Event/Command** field. Valid commands are MOCA commands or SQL statements. When executing the command, Event Management provides the command with the original alert's details, such as event name, qualifiers, and values, for optional use by the command.
<br>-   • **Blank**: After the amount of time specified in the **Hours** and **Minutes** fields elapses, if the original event's alert has not been acknowledged, Event Management expires the alert. |
| Subscriber | Unique identifier of a user who has subscribed to the event. |
| Account | Notification account (or accounts, if more than one is configured for the same alert priority) to which an email or instant message is sent to notify the event subscriber of an alert. See [Notification accounts](../configuration.md). |

## Qualifiers fields

**Notes**:

-   Qualifier fields are the parts of an event that users can select when subscribing to an event to ensure that they receive only the alerts that are relevant to them. See [Qualifiers](../configuration.md). Qualifier fields can be any or all fields that are associated with an event. They can also be used as placeholders in the alert subject and message templates. For example, if the area code field is assigned to the errored location event, then when subscribing to the event, users can specify the areas for which they want to receive errored location alerts.
-   Event Management enables you to determine the standard qualifiers to assign to an event. Event Management users can then select and customize the standard event qualifiers into alert qualifiers to meet their unique, individual notification needs. A standard set of event qualifiers is included with a pre-configured Blue Yonder event. However, an administrator with knowledge of the integrated application's database tables and columns can add qualifiers.

 
| Field | Description |
| --- | --- |
| Field Name | Name of field. The value entered must match the name sent by the integrated application. Valid field names can only contain alphabetical characters and the underscore (\_). |
| Field Type | Data type of field (for example, string). |

## Subscriber fields

 
| Field | Description |
| --- | --- |
| User | Unique identifier of the person subscribed to the event so that the person receives alerts. See [Subscription](../configuration.md). This field is typically display only, but is available when an administrator needs to specify the user for which the administrator is adding a subscription. See [View and manage alert details](find-alert.md), [View and manage event details](find-alert.md), and [Configure an event](#Configure_an_event). |
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

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
