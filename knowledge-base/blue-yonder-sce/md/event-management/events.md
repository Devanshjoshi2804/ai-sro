---
title: "Events"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/em/events.htm"
source: "/content/em/events.htm"
toc_path:
  - "Event Management"
  - "Events"
sections:
  - "Task flow"
images: []
source_sha1: 2aba7a5ffa1cecefe8b48f0b04e2294a2bf79f5d
---
# Events

An Event Management event is a potential action that could occur during a business process in an integrated application, and can be monitored and reported to Event Management. For example, the business process of canceling a pick in Warehouse Management can potentially trigger the Event Management event, WMD-CANCEL-PICK. The integrated application can be any application that can send event and alert information to Event Management in the Event Management XML format and call the Event Management XML processing command.

Several Supply Chain Execution (SCE) applications can be configured to send events and alerts to Event Management.

Before Event Management can process events and alerts, the events must be defined using one or more of the following methods:

-   The integrated application sends the event definition to Event Management (known as priming the event). This is the preferred method. For Blue Yonder SCE applications, see the _Event Management Configuration Guide_.
-   An administrator manually configures the event definition in Event Management. See [Configure an event](administration/event-configuration.md).
-   Event Management can attempt to configure an event definition when it receives an unknown event. See [Configure Event Management](administration/system-configuration.md) and the **Prime Unknown EMS Events** field in the [System Configuration fields](administration/system-configuration.md) to prime unknown events.

One business process action can result in zero, one, or more alerts. If there are no subscribers to an event when the corresponding business process action occurs, Event Management does not send any alert notifications. If the event has one or more subscribers, Event Management sends an alert and alert notification to each subscriber. Each individual alert and alert notification specifies the subscriber's chosen priority and acknowledgment status, if acknowledgment is required. See [Alerts](alerts.md) and [Subscription](configuration.md).

## Task flow

Typically, you perform the following sequence of tasks in Event Management.

1.  If an administrator has not already done so and you have access to the Configuration page, configure your user preferences. See [Configuration](configuration.md).
    
    **Note**: After completing the initial configuration, additional configuration changes are typically only performed on an as-needed basis.
    
    1.  Subscribe to the events for which you want to receive alerts and alert notifications, and optionally personalize them (for example, by assigning a different priority or specifying qualifiers to control the alerts and alert notifications that Event Management delivers). See [Configure event subscriptions](configuration.md).
    2.  Specify the email, instant messaging, or both types of accounts that Event Management will use to deliver alert notifications. See [Configure notification accounts](configuration.md). (Alerts are always added to a subscriber’s Alert Inbox page.)
2.  View alerts actively or passively. When viewing alerts actively, you select **Event Management > Alert Inbox**. You view alerts passively by receiving an email or instant message with the alert notification. See [View and manage alerts](alerts.md).
3.  View more information on an alert or mark it as read. See [View and manage alerts](alerts.md).
4.  If an alert requires acknowledgment, acknowledge the alert. See [View and manage alerts](alerts.md). Make sure you perform any tasks associated with your unique business process before or after acknowledging the alert in Event Management.
5.  When finished with an alert that you do not need to keep, delete the alert. See [View and manage alerts](alerts.md).
6.  To suspend alert and alert notification receipt for all subscribed events (for example, while on vacation), set the out of office feature on. This suspends receiving alerts and alert notifications, or forwards alerts and alert notifications to another user. To begin receiving alerts and alert notifications again for all subscribed events, set the out of office feature off. See [Set the out of office feature on or off](configuration.md).
7.  To suspend alert and alert notification receipt for one or more (but not all) subscribed events, disable the subscription. See [Configure event subscriptions](configuration.md).

Administrators can perform additional tasks. See [Administration](administration.md).

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
