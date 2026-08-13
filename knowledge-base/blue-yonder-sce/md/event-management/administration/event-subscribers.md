---
title: "Event subscribers"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/em/event_subscribers.htm"
source: "/content/em/event_subscribers.htm"
toc_path:
  - "Event Management"
  - "Administration"
  - "Event subscribers"
sections:
  - "View and manage event subscribers"
  - "Event Subscribers fields"
  - "Subscriber fields"
images: []
source_sha1: 65a877aafaa6a1722e269d7a495e4d8e07ee8b29
---
# Event subscribers

Event Management users can only view their own event subscriptions on the Event Subscription page. However, as an administrative Event Management user, the Event Subscribers page enables you to view all or a subset of the event subscriptions that currently exist in the application. The page also enables you to modify the event subscriptions to resolve subscription issues.

## View and manage event subscribers

1.  Select **Event Management > Administration > Event Subscribers**.
2.  To limit the list of event subscribers that is displayed, enter search criteria or select a filter. See [Filters](../../get-started/filters.md).
3.  View information in the [Event Subscribers fields](#Event_Subscribers_fields).
4.  To modify an event subscription:
    1.  In the grid, click the event name.
    2.  Enter information in the [Subscriber fields](#Subscriber_fields).
    3.  To add a qualifier, under **QUALIFIERS**, enter information in the fields, and then click **Add**.
    4.  To delete a qualifier:
        1.  In the grid, select the check box next to the qualifier, and then click **Delete**. A confirmation message is displayed.
        2.  Click **OK**.
    5.  Click **Save**.

## Event Subscribers fields

 
| Field | Description |
| --- | --- |
| Event Name | Brief description or unique identifier for the event. This field displays the **Short Description** configured for the event, if it is not blank; otherwise, this field displays the **Name** configured for the event. See [Configure an event](event-configuration.md). |
| Group Name | Code that specifies the category of the event. See [Event groups](../configuration.md). |
| User | Unique identifier of the user that is subscribed to the event. |
| Priority | Code that describes the importance of an event or alert.<br>-   • **Informational**: The event or alert is noteworthy but typically requires no action.
<br>-   • **Actionable**: The event or alert requires action.
<br>-   • **Critical**: The event or alert is severe and requires immediate action.
<br > See [Priorities](../alerts.md). |
| Enabled | Indicates whether the event subscription is active and sending alerts. See [Subscription](../configuration.md). |

## Subscriber fields

 
| Field | Description |
| --- | --- |
| User | Unique identifier of the person subscribed to the event so that the person receives alerts. See [Subscription](../configuration.md). This field is typically display only, but is available when an administrator needs to specify the user for which the administrator is adding a subscription. See [View and manage alert details](find-alert.md), [View and manage event details](find-alert.md), and [Configure an event](event-configuration.md). |
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
