---
title: "Config"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/admin/config.htm"
source: "/content/admin/config.htm"
toc_path:
  - "Administration"
  - "System Administrator"
  - "Configuration"
  - "Variable Configuration"
  - "Config"
sections:
  - "Add or modify a variable configuration"
  - "Delete a variable configuration"
  - "Config fields"
images: []
source_sha1: aaf1253688f10366bdbffe4d746c044b9ecfe3f3
---
# Config

You use the Config page to enable and configure the basic properties of a variable configuration.

If you are configuring a date field, you can define a custom date format for displaying date and time information. See [Custom date formats](../variable-configuration.md).

## Add or modify a variable configuration

1.  Select **System Administrator > Configuration > ** **Variable Configuration > Config**.
2.  Perform one of the following tasks:
    -   To add a variable configuration, from the **Actions** drop-down list, select **Add**.
    -   To copy a variable configuration, in the grid select the check box next to the variable name, and then from the **Actions** drop-down list, select **Copy**.
    -   To modify a variable configuration, in the grid select the check box next to the variable name, and then from the **Actions** drop-down list, select **Edit**.
3.  Enter information in the [Config fields](#Config_fields).
    
4.  Click **Save**.
5.  If you configured a field for an SCE client window, reset the cache (from the **Tools** menu, select **Reset Cache**).
    
    **IMPORTANT**: For the field to be displayed on SCE client windows, you must reset the cache on each SCE client workstation that accesses the server instance.
    
6.  If desired, [Define a default value for a variable configuration](defaults.md).

## Delete a variable configuration

1.  Select **System Administrator > Configuration > ** **Variable Configuration > Config**.
2.  In the grid, select the check box next to the variable name.
3.  From the **Actions** drop-down list, select **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Config fields

 
| Field | Description |
| --- | --- |
| Variable Name | Code, as defined in Message Catalog, that is used to represent a piece of fixed text (such as a window title, field label, or button label) that is displayed in the user interface. Variable names are used to provide multi-language support (MLS). The implementation of a variable name, such as prtnum, can be configured in multiple ways to support translations or customizations, or to accommodate a specific user interface, such as an RF or mobile device screen. |
| Form ID | Unique identifier of a form associated with a client window. |
| Customization Level | Value associated with a database entry that determines whether the entry is distributed with the standard application or has been customized for the specific application instance. Data that is distributed with the application is distributed with a customization level of 0 (zero), which is the lowest level. When you define a variable configuration, it is automatically assigned a customization level of 10. When the application framework is determining which database entry to use, it uses the customization level as one of the determining factors. Entries with a higher customization level take precedence over those with a lower customization level. For example, the customization level of attr\_str1 is 0 (zero), but when you configure a custom field for attr\_str1, the new configuration is automatically assigned a customization level of 10, which takes precedence. This field is display only. |
| Display Height (Pixels) | Determines the height of the field in pixels and can only be used if the field accepts height resizing. This value is typically used for resizing larger fields. |
| Enabled | Specifies whether the configuration is enabled for the variable name. |
| Push Context | Indicates that whenever one form flows to another, the field value from the first form is added to the application context. This is used when you want the value to be available to consecutive forms so that it can be used in some way, such as to populate the same field. |
| Addon ID | Identifier for the component in which the value is used.<br>-   • **3pl**: Third-party logistics component used in a Warehouse Management instance to support the tracking and management of inventory for multiple clients in a single or multi-warehouse environment.
<br>-   • **CUSTOMS**: Customs component used in a Warehouse Management instance to support customs functionality and integration with a duty management application.
<br>-   • **LES**: Global component specifying that the value is available in all SCE installed applications.
<br>-   • **RF**: Radio frequency terminal component specifying that the field is available on RF and mobile device screens displayed in the mobile terminal framework.
<br>-   • **SEAMLES**: Integrator component specifying that the field is only available in Integrator.
<br>-   • **WM**: Warehouse Management component specifying that the field is only available in Warehouse Management. |
| Application ID | Unique identifier of a client window. |
| Field Type | Determines the type of field in which the field is rendered, such as Currency or Date and Time. |
| Control Programmatic ID | Class ID of the Active X control that is used when the field is created dynamically (such as VB.TextBox and VB.ComboBox). |
| Control Properties | Determines the format of a custom date field. Use "FRMT=" followed by the date format code. For example, the value FRMT=yyMMdd displays the date using the last two digits of the year, the two-digit month number, and a two-digit day; such as 140115 for January 15, 2014. |
| Display Width (Pixels) | Determines the width of the field in pixels. This value is typically used for resizing larger fields. |
| Visible | Indicates that the field is made visible in the user interface. If this check box is deselected, then even if the field is enabled, it is not displayed on any window or screen. |
| Group Name | Identifier used by Blue Yonder product teams to indicate the product group that was responsible for loading data (in a particular row of a table). For example, standard group names include dcs\_data, mcs\_data, sal\_data, and so on. This field is display only. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
