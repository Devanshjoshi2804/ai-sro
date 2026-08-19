---
title: "System configuration"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/em/system_configuration.htm"
source: "/content/em/system_configuration.htm"
toc_path:
  - "Event Management"
  - "Administration"
  - "System configuration"
sections:
  - "Duplicate alerts"
  - "Default event limits"
  - "Configure Event Management"
  - "System Configuration fields"
  - "Limit fields"
images: []
source_sha1: a21222f0cd70cd99c598ef50253f9c33672f20d9
---
# System configuration

You can use the System Configuration page to define email and SMTP details to ensure that alerts are sent effectively, select a default locale, and set default event limits.

## Duplicate alerts

A duplicate alert is an alert that meets the Event Management criteria for being similar enough to a previous alert to be considered the same alert. Event Management only checks for duplicate alerts if the **Check Duplicate Events** field is set to **Yes**. (See [Configure Event Management](#Configure_Event_Management) and [System Configuration fields](#System_Configuration_fields).) Checking for duplicate alerts prevents Event Management from processing, and subscribers' accounts from receiving, an excessive number of alert notifications for the same alert.

When configured to check for duplicate alerts, Event Management first determines whether the event name, key value, source system, and client of a new alert matches an older alert. If so, Event Management uses one of the following additional criteria to determine that the new alert is a duplicate:

-   The alert requires acknowledgment
-   The alert does not require acknowledgment, but the alert status is SENT or PENDING
-   The alert has been escalated (alert status is ESCALATED)

When checking for duplicate alerts, Event Management does not send alert notifications for a duplicate alert to subscribers or add the alert to their Alert Inbox page. Instead, the duplicate count of the original alert is increased by one.

## Default event limits

A default event limit is a specification of the number of alerts of a certain type that are allowed in a specified time frame (rate limit). During periodic checking, once a default event limit has been reached, new alerts are held instead of being processed and sent to subscribers. See [Held alerts](held-alerts.md).

Event Management can simultaneously receive multiple alerts from multiple sources. While this robust design provides you with optimal notification capabilities, the potentially large number of alerts can consume an extensive amount of processing resources and can quickly fill users' mailboxes with email messages. To prevent this, you can limit the rate of incoming alerts and, consequently, the number of alerts being processed at one time.

Event Management supports the following types of default event limits:

-   **System (priority based)**: Event Management distributes the following system default event limits:
    
    -   **PRIORITY1**: 101 informational alerts can be raised in a 10-minute duration before the limit is exceeded.
    -   **PRIORITY2**: 101 actionable alerts can be raised in a 10-minute duration before the limit is exceeded.
    -   **PRIORITY3**: 101 critical alerts can be raised in a 10-minute duration before the limit is exceeded.
    
    For each system default event limit, you can change the distributed **Number of Events Per Interval** and **Time Interval in Minutes** values to better fit your specific business needs.
    
-   **Manual (event based)**: You can create default event limits for specific events.

Event management checks for default event limit violations on a periodic basis. However, after a default event limit is exceeded, Event Management checks for default event limit violations after every new alert. Once the default event limits are no longer exceeded, Event Management stops checking after every new alert and only checks on the periodic basis.

**Note**: The number of alerts at which Event Management checks for default event limit violations is defined by the value in the **Interactions Before Limit Check** field. See [Configure Event Management](#Configure_Event_Management) and [System Configuration fields](#System_Configuration_fields).

Once Event Management starts holding alerts, it continues to place all new alerts on hold. For system default event limits, this behavior continues until Event Management performs another check for limit violations. If the limit is no longer exceeded, Event Management automatically releases the alerts that were held because of a system default event limit. However, for manual default event limits, Event Management continues holding alerts until you manually release or delete the alerts. See [View and manage held alerts](held-alerts.md).

Event Management provides the EMS-EVENT-LIMIT event that can be used to notify subscribers that a default event limit was exceeded.

## Configure Event Management

1.  Select **Event Management > Administration > System Configuration**.
2.  Enter information in the [System Configuration fields](#System_Configuration_fields).
3.  To maintain default event limits, under **DEFAULT EVENT LIMITS**:
    1.  In the **Interactions Before Limit Check** field, enter the number of alerts at which Event Management checks for default event limit violations. For example, if this field is set to 51, then when alert number 51 is received, Event Management checks the default event limits. If a limit is exceeded, Event Management checks for default event limit violations for every new alert until the limit is no longer exceeded. However, if the limit is not exceeded, Event Management does not check again for default event limit violations until alert number 102 is received (another 51 alerts). This process continues as Event Management receives new alerts. See [Default event limits](#Default_event_limits).
        
    2.  Click **Set default event limits**.
    3.  Perform one of the following tasks:
        -   To add a default event limit, click **Add Limit**.
        -   To edit a default event limit, in the grid, click the **Sort Sequence** link.
    4.  Enter information in the [Limit fields](#Limit_fields).
    5.  Click **Save**.
    6.  To delete a default event limit:
        1.  In the grid, select the check box next to the default event limit and click **Delete**. A confirmation message is displayed.
        2.  Click **OK**.
4.  Click **Save**.

## System Configuration fields

 
| Field | Description |
| --- | --- |
| Host Email | Email address of the host Event Management system (for example, [\[email protected\]](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/em/cdn-cgi/l/email-protection)). This address is used as the sender on alert email messages. |
| Host Name | Fully qualified domain name or IP address of the server on which the electronic mail system is installed. |
| SMTP Username | User name for SMTP authentication. This field is required if the electronic mail server through which emails are sent from Event Management is configured to use SMTP authentication. |
| SMTP Password | Password for SMTP user name. This field is required if the electronic mail server through which emails are sent from Event Management is configured to use SMTP authentication. |
| EMS SMTP Port | Number of the port that the electronic mail server uses to send and receive email messages. See your electronic mail server's documentation. |
| Prime Unknown EMS Events | If Yes, Event Management attempts to create an event for an alert that does not match any of the current Event Management events. See [Events](../events.md).<br > If No, Event Management does not attempt to create an event, and the unknown alert is rejected. |
| Source System | Default source system for Event Management events and alerts; for example, SAL. Source system is a qualifier field for every event and alert. See [Qualifiers](../configuration.md). If the integrated application does not specify the source system for its event, the value specified in this field is used. See [Configure an event](event-configuration.md). |
| Default Locale | Locale to use as the default for the Event Management instance. The default locale is used to determine the language to use for alerts and event descriptions whenever the integrated application does not specify a locale in its event.<br > An event can be configured with messages for additional locales. See [Configure an event](event-configuration.md). |
| Check Duplicate Events | If Yes, Event Management checks for duplicate alerts. If the alert is a duplicate, Event Management increases the duplicate count of the original alert by one instead of adding the alert to each subscriber’s Alert Inbox page and sending a new alert notification.<br > If No, Event Management does not check for duplicate alerts. Event Management always sends alert notifications to subscribers even if the alert is a duplicate of a previous alert.<br > See [Duplicate alerts](#Duplicate_alerts). |
| Login | Instant messaging login identifier that Event Management is to use when communicating with the instant messaging service; for example, to send an instant message alert notification. |
| Password | Instant messaging password for the user identifier specified in the **Login** field. |
| Lead Message | Standard text to send at the beginning of each alert instant message. The alert message then follows the lead message. |
| Interactions Before Limit Check | Number of alerts at which Event Management checks for default event limit violations. For example, if this field is set to 51, then when alert number 51 is received, Event Management checks the default event limits. If a limit is exceeded, Event Management checks for default event limit violations for every new alert until the limit is no longer exceeded. However, if the limit is not exceeded, Event Management does not check again for default event limit violations until alert number 102 is received (another 51 alerts). This process continues as Event Management receives new alerts. See [Default event limits](held-alerts.md). |

## Limit fields

**Note**: The following fields are used to specify the default event limits (number of alerts per time frame for a specific priority or event) to apply to the alerts that Event Management receives. After a default event limit is reached, Event Management holds new alerts. See [Default event limits](#Default_event_limits) and [Held alerts](held-alerts.md).

 
| Field | Description |
| --- | --- |
| Sort Sequence | Order in which to apply the default event limit. |
| Raised Events | Name of the event to which the default event limit applies or one of the system default event limits (PRIORITY1, PRIORITY2, and PRIORITY3). See [Default event limits](held-alerts.md). |
| Number of Events Per Interval | Number of alerts to use with the value in the **Time Interval in Minutes** field to define the rate limit. |
| Time Interval in Minutes | Number of minutes to use with the value specified in the **Number of Events Per Interval** field to define the rate limit. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
