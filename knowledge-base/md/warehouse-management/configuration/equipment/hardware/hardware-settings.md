---
title: "Hardware Settings"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/hardware_settings.htm"
source: "/content/hardware_settings.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Equipment"
  - "Hardware"
  - "Hardware Settings"
sections:
  - "RF session recovery and timeout"
  - "Configure hardware settings"
images: []
source_sha1: 033b06f71cc23cfc2db01be44c53ed35070bf183
---
# Hardware Settings

Hardware settings determine the configuration of RF devices. You use the Hardware Settings pages to enable automatic RF session recovery, and when not enabled, to set the recovery timeout. You also enable whether an operator can be logged in to more than one RF device at a time.

## RF session recovery and timeout

Session recovery, when enabled, recovers an operator's RF session when a connection is temporarily lost without requiring the operator to log back in. For example, if the RF device is moved to a warehouse location that is outside the range of the wireless network and the connection is lost, then when the device is moved back into range, the session can be resumed without requiring the operator to log in.

If session recovery is not enabled, you can specify a recovery timeout value. This value defines the number of seconds following the disconnection of an RF session, during which the session can be resumed; if greater time elapses, the operator is required to log in and start a new session. Disabling session recovery is useful to ensure operators are properly logging in and out of their devices, especially when an RF device is shared between operators on different shifts.

When setting a recovery timeout value, consider that if the device disconnects, and attempts to reconnect within the specified time frame, the operator is not required to log in again. For example, if one operator does not properly log off a device and leaves for the day, and another operator picks up that same device after the recovery time has lapsed, the new operator must log into a new session. But if the recovery timeout period has not elapsed, then the new operator can resume the session that belonged to the previous operator.

## Configure hardware settings

1.  Select **Configuration > Equipment > Hardware > Hardware Settings**.
2.  Enter information in the following fields:
    
     
    | Field | Description |
    | --- | --- |
    | Enable Session Recovery | If Yes, then RF sessions are automatically restored if there is a disconnect with the MTF server.<br > If No, then RF sessions are not restored automatically. |
    | Recover Timeout | Number of seconds following a disconnect with the MTF server during which the session can be resumed without the operator having to log in. The **Recovery Timeout** field is only available when the **Enable Session Recovery** field is set to No |
    | Single RF Login | If Yes, then an operator can only be logged in to one RF device at a time. If set to Yes, when an operator attempts to log in to an RF device, the application verifies whether the operator is currently logged in to another device. If so, then the application prevents the operator from logging in to the second device.<br > If No, then during a log in attempt, the application does not verify whether an operator is already logged in to another RF device, and the operator can be logged in to multiple RF devices simultaneously. |
    
3.  Enter the language code that is used for each available locale:
    
    **Note**: The language code is 5-digit value that represents a language and country, for example, en\_US for English\_United States and es\_ES for Spanish\_Spain. Refer to your voice device documentation for the list of support languages and language codes.
    
    1.  Under **VOICE SETTINGS**, in the **Language Code** grid, find the locale to configure.
    2.  In the **Language Code** column, enter the value that represents the language to use for the selected locale.
4.  Click **Save**.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
