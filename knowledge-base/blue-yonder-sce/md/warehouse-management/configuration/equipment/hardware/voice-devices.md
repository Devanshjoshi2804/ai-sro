---
title: "Voice Devices"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/voice_devices.htm"
source: "/content/voice_devices.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Equipment"
  - "Hardware"
  - "Voice Devices"
sections:
  - "Add or modify a voice device"
  - "Delete a voice device"
  - "Voice Devices fields"
images: []
source_sha1: a6bcd70f9c7ee1256dbf18aff9b7b4fde7b6092f
---
# Voice Devices

A voice device is an RF device with a headset and microphone that allows users to perform directed and undirected work hands-free, using voice commands rather than keypads. The operations that can be performed by a voice device are defined by the voice configurations in Warehouse Management.

When you add a voice device, you define the following attributes:

-   Work areas in which the device is authorized to perform work, and which the application uses to direct work management activities
-   Printers, if used, to which the device can print labels or reports

## Add or modify a voice device

1.  Select **Configuration > Equipment > Hardware > Voice Devices**.
2.  Perform one of the following tasks:
    -   To add a new voice device, click **Add**.
    -   To modify a voice device, click the voice device.
    -   To copy a voice device, select the check box next to the voice device, and then click **Copy**.
3.  Enter information in the [Voice Devices fields](#Voice_Devices_fields).
4.  To assign accessible work areas:
    1.  Under **WORK**, click **Work Areas**. The Work Areas page is displayed.
    2.  Under **Available**, select the check box next to the work areas that apply.
    3.  Click **Apply**.
5.  Click **Save**.

## Delete a voice device

1.  Select **Configuration > Equipment > Hardware > Voice Devices**.
2.  In the grid, select the check box next to the voice device to delete.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Voice Devices fields

 
| Field | Description |
| --- | --- |
| Device | Name of the voice device. A voice device is an RF device with a headset and microphone that communicates with Warehouse Management and allows users to perform directed and undirected work using voice commands rather than a keypad and display. The Device field is limited to 20 characters. If the voice headset code requires more than 20 characters, enter the code in the Voice Terminal field. |
| Description | Description of the voice device that further defines it. |
| Voice Locale | Unique identifier for a locale. Identifier that determines which language and language attributes (such as currency and measurement units) that will be displayed in the user interface or spoken to the voice operator. The locale is specified when a user logs in. |
| Voice Terminal | Type of voice headset that requires a device code that exceeds 20 characters. To identify a voice headset device, the application uses the value that you specify for Voice Terminal. If this field is blank, then the application uses the value specified for Device. |
| Home Work Area | Identifier for the home work area. A work area is a logical division of warehouse space made on the basis of physical layout and access by different types of material handling vehicles, and which consists of a number of work zones. A home work area is the home base for an RF device, mobile device, or voice headset device, which the application uses to direct work.<br > Signing on to a home work area is optional. For example, if an operator is directed to work, the following will occur when that work is complete:<br>-   • If the operator signed on to a home work area, the application will look for new work back in the operator's home work area.
<br>-   • If the operator is not using a home work area, the application will look for more work in the current work area. |
| Report Printer | Name of the printer that will be used to print reports from this device. Only printers that have been configured to print reports are available for selection. |
| Label Printer | Name of the printer that will be used to print labels from this device. Only the label printers that have been set up and configured to work with the application are available for selection. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
