---
title: "Voice Tracing"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/voice_tracing.htm"
source: "/content/voice_tracing.htm"
toc_path:
  - "Warehouse Management"
  - "Picking"
  - "Voice Tracing"
sections:
  - "View voice tracing details"
  - "Start or stop voice tracing"
  - "Voice Tracing fields"
images: []
source_sha1: 410a104816f3e83c4c132aaaa5dd091146a4b00c
---
# Voice Tracing

The Voice Tracing page displays the voice devices that are being used by operators to perform voice operations. You can select a specific device and turn on tracing so the application generates logs for the voice operations performed with the device, such as picking, replenishment, or loading. When operators perform these operations, you may want to check the application's performance, or there may be issues where the application does not respond to certain commands. In such scenarios, the operator can run voice tracing to generate the voice logs to further investigate and identify the underlying issue. The voice logs are generated and archived as a ZIP file in the MOCA console. For details, see the _Supply Chain Execution Applications Console User Guide_.

For example, assume that an operator is performing voice picking, and the application does not respond to the voice command with the deposit information. The operator can run voice tracing to generate the logs to identify the issue.

## View voice tracing details

1.  Select **Picking > Voice Tracing**.
2.  View the information in the [Voice Tracing fields](#Voice_Tracing_fields).

## Start or stop voice tracing

1.  Select **Picking > Voice Tracing**. The Voice Tracing page is displayed.
2.  In the grid, select the device for which you want to start or stop voice tracing.
3.  Perform one of the following tasks:
    -   To start voice tracing, from the **Actions** drop-down list, select **Start Voice Trace**. Voice tracing is enabled for the device.
        
    -   To stop voice tracing, from the **Actions** drop-down list, select **Stop Voice Trace**. The application archives the generated report as a ZIP file in the MOCA console.
        

## Voice Tracing fields

 
| Field | Description |
| --- | --- |
| Trace Enabled | Indicates whether voice tracing is enabled for the voice device. Voice tracing is used to generate reports for voice operations. |
| Device | The voice headset that has access to or communicates with the application. |
| Device Name | Text that further identifies the voice device. |
| Current User | The user who is currently performing voice operations. |
| Last Activity Date | Date and time at which the voice activity was last performed. |
| Current Location | Location in which the voice device is currently in use. |
| Current Work Area | Work area in which the voice device is currently in use. |
| Terminal ID | Unique name or identifier for the voice device. |
| Device Mode | Indicates whether the voice device performs directed or undirected work. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
