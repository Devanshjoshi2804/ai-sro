---
title: "RF Devices"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/rf_devices.htm"
source: "/content/rf_devices.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Equipment"
  - "Hardware"
  - "RF Devices"
sections:
  - "Configure RF emulation"
  - "Add or modify an RF device"
  - "Delete an RF device"
  - "Add or modify a vendor for an RF device"
  - "Delete a vendor for an RF device"
  - "Devices fields"
  - "Vendors fields"
images: []
source_sha1: dd42b468db0219c60fbc81a8cfd556915e1fb1a9
---
# RF Devices

An RF device is a terminal (with a keypad and display screen) or Android mobile device that is used to communicate with Warehouse Management, and perform directed and undirected work in the warehouse.

**Notes**: Emulation is an easy way to troubleshoot and test without a live RF or mobile device. To set up an RF emulator, see [Configure RF emulation](#Configure_RF_emulation). To set up a mobile device accessible from web browser, see the _Warehouse Management WMS Mobile Installation Guide_.

When you define an RF device, you define the following attributes:

-   Type and attributes of the terminal, such as the size of the display screen.
-   Vendor and terminal identifier of the RF device
-   Work areas in which the terminal is authorized to perform work, and which the application uses to direct work management activities. By default, all work areas are assigned to the RF device so it is authorized to work in all work areas.
-   Printers, if used, to which the terminal can print labels or reports

For an Android mobile device, the following values are required:

-   **Vendor**: Must match the value of the vendor (-v) property or vendor default value (WEBMTF) provided in the **mtf-mobile-adapter.properties** file for the warehouse.
-   **Terminal**: Serial number of the Android mobile device or a unique value to identify the mobile device.
-   **Terminal Type**: Handheld
-   **Width**: 20
-   **Height**: 16

## Configure RF emulation

For Warehouse Management installations, RF emulation provides access to an RF session from your workstation. With RF emulation you can perform RF functions on the workstation for a selected warehouse.

**IMPORTANT**: RF emulation requires that you have a telnet application installed on the Warehouse Management server.

You must perform the following tasks to set up RF emulation on your workstation after installing a new version or upgrading from an earlier version of Warehouse Management:

1.  Define an RF device. When you configure the RF device, you define the device and terminal names, terminal type, and vendor information.
    
2.  Configure the MTF SERVER task. You use the Console to configure the MTF SERVER task. The MTF SERVER task is distributed with default settings. You must configure the task to reflect your specific installation variables. To configure the MTF SERVER task:
    1.  Select the **Auto Start** check box.
    2.  Select the **Restart on Termination** check box.
    3.  Configure the following MTF SERVER command line arguments:
        
        -   **\-v**: Name of the RF vendor that you defined for the RF device in the web client..
        -   **\-W**: Name of the warehouse to which you want to connect.
        -   **\-a**: Service URL for the Warehouse Management server instance to which the RF terminal connects.
        -   **\-P**: Port number for the RF server. The port number for the RF server is the port number for the server instance that you are configuring, plus 20. In the command line, place the -P argument after the -a argument.
        -   **\-G**: Determines whether the RF form name and the active field name are displayed at the bottom of RF emulator forms. For example, for a wide screen, use -G 39,7; for a narrow screen, use -G 19,15.
        -   **\-j**: Full path to the mtf log configuration file (mtf\_logging.xml) that specifies the logging options that have been enabled.
            
        
        **Example**: -v DEFAULT -W WMD1 -a http://server02:4500/service<br>\-j $MTFDIR/data/mtf\_logging.xml -p 0 -P 4520 -G 39,7
        
3.  Test the access to RF emulation:
    1.  Start or restart the MTF\_SERVER task.
    2.  Start a command prompt and enter the following command: telnet <_MTF Server_> <_MTF Server Port Number_>
        
        **Example**: telnet server02 4520
        
    3.  When you are prompted for a terminal ID, enter the terminal ID that you created for the RF device.
    4.  When you are prompted for a user name and password, enter your credentials.
4.  To enable tracing from the RF device:
    1.  Access the RF Utilities Menu.
    2.  To enable tracing for the Warehouse Management server, select and configure server tracing.
    3.  To enable tracing for the RF terminal session, select and configure device tracing.

## Add or modify an RF device

1.  Select **Configuration > Equipment > ** **Hardware > RF Devices**.
2.  Above the grid, select **Devices**.
3.  Perform one of the following tasks:
    -   To add a new RF device, click **Add**.
    -   To modify an RF device, in the grid, click the RF device.
        
        **Note**: You cannot modify a device that is associated with an active session. The operator must log out of the device before you can save modifications.
        
    -   To copy an RF device, in the grid, select the check box next to the RF device, and then click **Copy**.
4.  Enter information in the [Devices fields](#Devices_fields).
5.  To assign accessible work areas:
    1.  Under **WORK**, click **Work Areas**. The Work Areas page is displayed.
    2.  Under **Available**, select the check box next to the work areas that apply.
    3.  Click **Apply**.
6.  Click **Save**.

## Delete an RF device

You cannot delete a device that is associated with an active session. The operator must log out of the device before you can delete it.

1.  Select **Configuration > Equipment > Hardware > RF Devices**.
2.  Above the grid, click **Devices**.
3.  Select the check box next to the RF device to delete.
4.  Click **Delete**. A confirmation message is displayed.
5.  Click **OK**.

## Add or modify a vendor for an RF device

You cannot modify a vendor that is currently associated with an RF device.

1.  Select **Configuration > Equipment > Hardware > RF Devices**.
2.  Above the grid, select **Vendors**.
3.  Perform one of the following tasks:
    -   To add a new vendor for an RF device, click **Add**.
    -   To modify a vendor for an RF device, in the grid, click the vendor.
    -   To copy a vendor for an RF device, in the grid, select the check box next to the vendor, and then click **Copy**.
4.  Enter information in the [Vendors fields](#Vendors_fields).
5.  Click **Save**.

## Delete a vendor for an RF device

You cannot delete a vendor that is currently associated with an RF device.

1.  Select **Configuration > Equipment > Hardware > RF Devices**.
2.  Above the grid, select **Vendors**.
3.  In the grid, select the check box next to the vendor to delete.
4.  Click **Delete**. A confirmation message is displayed.
5.  Click **OK**.

## Devices fields

 
| Field | Description |
| --- | --- |
| Device Code | Unique identifier for a piece of equipment such as a radio frequency (RF) or mobile device that has access to or communicates with the application. The device code is the display name for the device and represents a logical location during warehouse operations. For example, during picking, an inventory display shows the device code as the location of the inventory until the inventory is deposited. |
| Locale | Unique identifier for the locale in which to display the initial log-in screen to users. After the user logs in, the application supports the display and entry of data in accordance with the user's locale. A locale defines a set of culture-specific components, such as language, time and date formats, currency formats, and a measurement unit system. |
| Device Name | Name that further identifies the device. You can create a name, for example, that includes terms such as Wide or Narrow to identify an RF screen size, or Standard or Touch to identify whether a workstation has a touch screen, or EMUBSmith for an RF emulator used by a user named Bruce Smith. |
| Vendor Name | Name of the vendor that manufactured the RF terminal. For an Android mobile device, the vendor name must match the value in the vendor (-v) property defined in the **mtf-mobile-adapter.properties** file for the warehouse. |
| Terminal | Unique name or identifier that represents the physical RF device (hardware). When setting up RF emulation, for ease of use, it is recommended that you provide a name that matches the RF device. For Android mobile devices, to ensure a unique terminal ID is assigned to each device, it is recommended to configure each device with its hardware serial number as the **Terminal**. If you do not use serial numbers, then ensure that the terminal identifiers are unique and not duplicated.<br > **Note**: Depending on your Android version, the serial number may be stored on your mobile device under **Settings > About** <_Device_> > **Status**. Alternatively, see the device manufacturer's documentation for information on finding the serial number. |
| Terminal Type | Type of terminal that defines the size of the display screen. The size of the display is defined by the values you enter for Height and Width. The default size of a Handheld display is 20 x 16; the default size of a Vehicle display is 40 x 8. For an Android mobile device, set the **Terminal Type** field to Handheld. |
| Width | Maximum number of characters that the width of the RF screen supports. Default is 20 for the Handheld terminal type, and 40 for a Vehicle terminal type. For an Android mobile device, the Terminal Type must be **Handheld** and the **Width** must be 20. |
| Height | Maximum number of lines that the height of the RF screen supports. Default is 16 for Handheld terminal type, and 8 for a Vehicle terminal type. For an Android mobile device, the Terminal Type must be **Handheld** and the **Height** must be 16. |
| Home Work Area | Identifier for the home work area. A work area is a logical division of warehouse space made on the basis of physical layout and access by different types of material handling vehicles, and which consists of a number of work zones. A home work area is the home base for an RF device, mobile device, or voice headset device, which the application uses to direct work.<br > Signing on to a home work area is optional. For example, if an operator is directed to work, the following will occur when that work is complete:<br>-   • If the operator signed on to a home work area, the application will look for new work back in the operator's home work area.
<br>-   • If the operator is not using a home work area, the application will look for more work in the current work area. |
| Report Printer | Name of the printer that will be used to print reports from this device. Only printers that have been configured to print reports are available for selection. |
| Label Printer | Name of the printer that will be used to print labels from this device. Only the label printers that have been set up and configured to work with the application are available for selection. |

## Vendors fields

 
| Field | Description |
| --- | --- |
| RF Vendor Name | Name of the vendor that manufactured the RF terminal. |
| RF Vendor Inquiry | Terminal number inquiry string for the vendor terminal query. |
| RF Vendor Response | Response format for the vendor terminal query. |
| RF Vendor Response Time | Time (in milliseconds) to wait for the terminal to respond with the terminal ID value. If the terminal does not respond within the specified time frame, the user is prompted to enter the terminal ID. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
