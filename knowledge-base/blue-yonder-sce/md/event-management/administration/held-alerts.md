---
title: "Held alerts"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/em/held_alerts.htm"
source: "/content/em/held_alerts.htm"
toc_path:
  - "Event Management"
  - "Administration"
  - "Held alerts"
sections:
  - "Default event limits"
  - "View and manage held alerts"
  - "Held Alerts fields"
images: []
source_sha1: 555ab2c2ea472de21e073d600a0dee9183c78caf
---
# Held alerts

A held alert is an alert that is received after a default event limit is exceeded. Held alerts are not processed and are not delivered to subscribers. Instead, held alerts are stored separately in Event Management. You can use the Held Alerts page to view, release for delivery to the subscriber, and delete held alerts. See [View and manage held alerts](#View_and_manage_held_alerts).

Once a system default event limit is no longer exceeded, Event Management automatically releases the alerts that were held because of a system default event limit. However, for manual default event limits, Event Management continues holding alerts until you manually release or delete the alerts.

## Default event limits

A default event limit is a specification of the number of alerts of a certain type that are allowed in a specified time frame (rate limit). During periodic checking, once a default event limit has been reached, new alerts are held instead of being processed and sent to subscribers.

Event Management can simultaneously receive multiple alerts from multiple sources. While this robust design provides you with optimal notification capabilities, the potentially large number of alerts can consume an extensive amount of processing resources and can quickly fill users' mailboxes with email messages. To prevent this, you can limit the rate of incoming alerts and, consequently, the number of alerts being processed at one time.

Event Management supports the following types of default event limits:

-   **System (priority based)**: Event Management distributes the following system default event limits:
    
    -   **PRIORITY1**: 101 informational alerts can be raised in a 10-minute duration before the limit is exceeded.
    -   **PRIORITY2**: 101 actionable alerts can be raised in a 10-minute duration before the limit is exceeded.
    -   **PRIORITY3**: 101 critical alerts can be raised in a 10-minute duration before the limit is exceeded.
    
    For each system default event limit, you can change the distributed **Number of Events Per Interval** and **Time Interval in Minutes** values to better fit your specific business needs.
    
-   **Manual (event based)**: You can create default event limits for specific events.

Event management checks for default event limit violations on a periodic basis. However, after a default event limit is exceeded, Event Management checks for default event limit violations after every new alert. Once the default event limits are no longer exceeded, Event Management stops checking after every new alert and only checks on the periodic basis.

**Note**: The number of alerts at which Event Management checks for default event limit violations is defined by the value in the **Interactions Before Limit Check** field. See [Configure Event Management](system-configuration.md) and [System Configuration fields](system-configuration.md).

Once Event Management starts holding alerts, it continues to place all new alerts on hold. For system default event limits, this behavior continues until Event Management performs another check for limit violations. If the limit is no longer exceeded, Event Management automatically releases the alerts that were held because of a system default event limit. However, for manual default event limits, Event Management continues holding alerts until you manually release or delete the alerts. See [View and manage held alerts](#View_and_manage_held_alerts).

Event Management provides the EMS-EVENT-LIMIT event that can be used to notify subscribers that a default event limit was exceeded.

## View and manage held alerts

In addition to releasing and deleting held alerts, you can use the Held Alerts page to view the [Held Alerts fields](#Held_Alerts_fields).

1.  Select **Event Management > Administration > Held Alerts**.
2.  To release a held alert, in the grid, select the check box next to the alert, and click **Release**. The alert is sent to subscribers.
3.  To delete a held alert, in the grid, select the check box next to the alert, and click **Delete**. The alert is marked as cancelled and is removed from the application.

## Held Alerts fields

 
| Field | Description |
| --- | --- |
| Alert ID | Unique identifier for an alert. You can use the Alert ID during troubleshooting to match an alert to its corresponding database row or trace file contents. |
| Event Name | Name of the event that corresponds to the alert. An event is a potential action that could occur during a business process in an integrated application, and can be monitored and reported to Event Management. See [Events](../events.md). |
| Priority | Code that describes the importance of an event or alert.<br>-   • **Informational**: The event or alert is noteworthy but typically requires no action.
<br>-   • **Actionable**: The event or alert requires action.
<br>-   • **Critical**: The event or alert is severe and requires immediate action.
<br > See [Priorities](../alerts.md). |
| Duplicate Count | Number of times the same alert has been sent from the integrated application to the Event Management instance. See [Duplicate alerts](system-configuration.md). |
| Source System | Code for the integrated application that sent the alert. |
| Added Date | Date and time that the alert was created in Event Management (not the date and time that the alert occurred in the integrated application). |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
