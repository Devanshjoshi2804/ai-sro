---
title: "Serial Communication"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/serial_communications_configurations.htm"
source: "/content/serial_communications_configurations.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Outbound"
  - "Packing"
  - "Serial Communication"
sections:
  - "Example"
  - "Add or modify a serial communication configuration"
  - "Delete a serial communication configuration"
  - "Serial Communication fields"
images: []
source_sha1: d2f7583df53b743b6e4e89241c532dda0cb647ae
---
# Serial Communication

A serial communication configuration is a set of attributes, such as parity, baud rate, and port, that specifies how information is transferred to and from a serial device. A serial device, such as a serial bar code scanner, is a device that transmits information one bit at a time in sequence using one data stream. This is as opposed to parallel devices, such as parallel printers, that transmit several bits of information at the same time using multiple data streams. A serial device is physically connected to a serial port of a PC.

In the application, a serial communication configuration is used to represent a group of serial devices that all share the exact same communication attributes. You define one serial communication configuration for each group of serial devices, instead of defining each serial device separately, which could be repetitive since they share the same attributes. A serial communication configuration is also associated with each workstation device that is connected to a serial device that is represented by the serial communication configuration. This enables the application to properly interact with your physical serial devices; for example, to read a bar code and use the incoming data, such as the item number, to fill in a field on the window. For more information on devices, see [RF Devices](../../equipment/hardware/rf-devices.md).

### Example

The following example explains how you can use and configure serial device communication configurations with multiple bar code scanners that are not the same.

If you are using 20 bar code scanners in your facility and 16 have the same communication attributes (for example, simple scanners), and 4 have a different set of shared communication attributes (for example, a more expensive, specialized scanner), then you would create 2 serial communication configurations—1 for the group of 16 scanners and 1 for the group of 4 scanners. Then, for each of the 16 workstations to which you have physically connected the simple scanners, you associate the workstation device with the simple scanner's serial communication configuration. For each of the 4 workstations to which you have physically connected the specialized scanners, you associate the workstation device with the specialized scanner's serial communication configuration.

After physically attaching a serial bar code scanner to a pack station and completing the configuration, the application automatically captures and displays the information retrieved from the bar code in the appropriate fields.

## Add or modify a serial communication configuration

You can add a new serial communication configuration or change the attributes of an existing serial communication configuration for a group of serial devices that share the same serial communication attributes.

1.  Select **Configuration > Outbound > Packing > Serial Communication**.
2.  Perform one of the following tasks in the top grid:

-   To add a serial communication, from the **Actions** drop-down list, select **Add**.
-   To modify a serial communication, select the check box next to the configuration, and then from the **Actions** drop-down list, select **Edit**.
-   To copy a serial communication, select the check box next to the configuration, and then from the **Actions** drop-down list, select **Copy**.

4.  Enter information in the [Serial Communications fields](#Serial_Communications_fields).
    
5.  Click **Save**.
6.  To add a device to a serial communication configuration:
    1.  In the top grid, select the check box next to the configuration.
    2.  In the Devices (bottom) grid, from the **Actions** drop-down list, select **Add**.
    3.  In the **Device Code** field, enter the unique identifier for a piece of equipment such as a radio frequency terminal or mobile device that has access to or communicates with the application. The device code is the display name for the device and represents a logical location during warehouse operations.
        
        **Note**: The **Serial Communication ID** and **Warehouse** field values are populated based on the selected serial communication configuration.
        
    4.  Click **Save**.

## Delete a serial communication configuration

You cannot delete a serial communication configuration that is currently assigned to a device.

1.  Select **Configuration > Outbound > Packing > Serial Communication**.
2.  In the top grid, select the check box next to the configuration to delete.
3.  From the **Actions** drop-down list, select **Delete** . A confirmation message is displayed.
4.  Click **Yes**.

## Serial Communication fields

 
| Field | Description |
| --- | --- |
| Baud Rate | Speed of data transfer (number of signaling changes per second) for the group of serial devices represented by the serial communication configuration. This information is typically found in your serial device's user manual. |
| Serial Communication ID | Unique alphanumeric code that identifies a serial communication configuration and differentiates it from other serial communication configurations in the application. A serial communication configuration is a set of attributes, such as parity, baud rate and port, that specifies how information is transferred to and from a serial device. A serial device, such as a serial bar code scanner, is a device that transmits information one bit at a time in sequence using one data stream. |
| Description | Meaningful description that further explains the serial communication configuration. This is the text that is displayed on the application windows when referring to this serial communication configuration. |
| Serial Communication Type ID | Code that identifies the kind of serial device that the serial communication configuration represents.<br>-   • **Scanner**: A piece of equipment that reads printed bar codes (groups of multi-width lines and spaces that encode one or more pieces of information) and converts them to text (letters, numbers, or symbols).
<br > You can use Code Maintenance-Supervisor to define additional serial communication type values using the ser\_dev\_typ column. |
| Barcode Scanner Delay Time | Number representing the time interval, in milliseconds, to ignore reads after a scan. Delay time is the length of time to wait before reading the next bar code. This helps prevent misreads from repeated scans, such as can occur if an item is held too long in front of the scanner or is held in a certain way that produces repeated scans. This information is typically found in your serial device's user manual; otherwise, it is suggested that you use 100. After setting this value, you would only need to change it if you were getting bad reads from the scanner, such as increasing the time to prevent double scans. Only available if **Scanner** is selected from the **Serial Communication Type ID** list. |
| Barcode Scanner Wait Time | Number representing the time interval, in milliseconds, to wait for a full message from the bar code scanner represented by the serial communication configuration. Wait time is the length of time that it takes to read data from the scanner. This information is typically found in your serial device's user manual; otherwise, it is suggested that you use 50. After setting this value, you would only need to change it if you were getting bad reads from the scanner, such as only receiving the first part of the bar code information. Only available if **Scanner** is selected from the **Serial Communication Type ID** list. |
| Parity | Type of parity error check used by the group of serial devices represented by the serial communication configuration. The parity error check is used for detecting errors in a single transmission unit (defined in the **Data Bits** field). This information is typically found in your serial device's user manual. In parity error detection, an extra bit, known as the parity bit, is added to the end of a group of transmitted bits.<br>-   • **Even**: The parity bit is set to 1 if the number of 1's in the communication stream plus 1 results in an even number; otherwise, it is set to 0.
<br>-   • **Odd**: The parity bit is set to 1 if the number of 1's in the communication stream plus 1 results in an odd number; otherwise, it is set to 0.
<br>-   • **Space**: The parity bit is always set to 0, but it is not used.
<br>-   • **Mark**: The parity bit is always set to 1, but it is not used.
<br>-   • **None**: No parity bit is sent. Error detection may instead be handled by the communication protocol.
<br > You can use Code Maintenance-Supervisor to define additional parity values using the parity column. |
| Data Bits | Number of bits representing actual data, such as 7 or 8, that the group of serial devices, represented by the serial communication configuration, transmits in one unit of transmission. This information is typically found in your serial device's user manual. |
| Stop Bits | Number of bits used by the group of serial devices represented by the serial communication configuration to indicate the end of a unit of transmission. This information is typically found in your serial device's user manual. Slower devices typically use more stop bits.<br>-   • **1**: One stop bit is used.
<br>-   • **1.5**: One and one half stop bits are used.
<br>-   • **2**: Two stop bits are used.
<br > You can use Code Maintenance-Supervisor to define additional stop bit values using the stopbits column. |
| Port | Name of the connector to which the serial device represented by the serial communication configuration is physically connected and through which the data will be transmitted. For example, on a Windows-based workstation, this value might be COM1; on a LINUX-based workstation, this value might be /dev/tty\*. |
| Barcode Scanner Encoding | Standard text format used for the information received from the scanner represented by the serial communication configuration. This information is typically found in your serial device's user manual. Depending on the bar code scanner, you might be able to configure the hardware to use different bar code scanner encodings. Only available if Scanner is selected from the Serial Communication Type ID list.<br>-   • **ASCII**: American Standard Code for Information Interchange format for coding individual characters on a computer. ASCII uses a string of 7 or 8 binary digits to represent each character in a character set, such as English.
<br>-   • **UNICODE**: Computer coding format that uses a variable string of up to 16 binary digits to represent each character in a character set. UNICODE can represent more characters than ASCII and is often used to represent character sets, such as Chinese, that have more characters than English.
<br>-   • **UTF-32**: 32 bit Unicode Transformation Format is a Unicode computer coding format that uses exactly 32 binary digits to represent each character in a character set.
<br>-   • **UTF-7**: 7 bit Unicode Transformation Format is a Unicode computer coding format that uses a variable string of up to 7 binary digits to represent each character in a character set.
<br>-   • **UTF-8**: 8 bit Unicode Transformation Format is a Unicode computer coding format that uses one to four strings of 8 binary digits to represent each character in a character set. UTF-8 can represent every character in the Unicode character set and is compatible with ASCII.
<br > You can use Code Maintenance-Supervisor to define additional encoding values using the scanner\_encoding column. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
