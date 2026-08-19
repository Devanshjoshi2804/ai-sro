---
title: "Defaults"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/admin/defaults.htm"
source: "/content/admin/defaults.htm"
toc_path:
  - "Administration"
  - "System Administrator"
  - "Configuration"
  - "Variable Configuration"
  - "Defaults"
sections:
  - "Define a default value for a variable configuration"
  - "Delete a default value"
  - "Defaults fields"
images: []
source_sha1: 2f2fa454faee1ab6aa38acb9f403165d76756e56
---
# Defaults

You use the Defaults page to enable and configure a default value to populate a variable name field automatically. You use a default value when you want a certain value to be displayed in the field by default when the field is available for selection.

## Define a default value for a variable configuration

1.  Select **System Administrator > Configuration > ** **Variable Configuration > Defaults**.
2.  Perform one of the following tasks:
    -   To add a default value, from the **Actions** drop-down list, select **Add**.
    -   To modify a default value, in the grid select the check box next to the variable name, and then from the **Actions** drop-down list, select **Edit**.
    -   To copy a default value, in the grid select the check box next to the variable name, and then from the **Actions** drop-down list, select **Copy**.
3.  Enter information in the [Defaults fields](#Defaults_fields).
    
4.  Click **Save**.

## Delete a default value

1.  Select **System Administrator > Configuration > ** **Variable Configuration > Defaults**.
2.  In the grid, select the check box next to the variable name.
3.  From the **Actions** drop-down list, select **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Defaults fields

 
| Field | Description |
| --- | --- |
| Variable Name | Code, as defined in Message Catalog, that is used to represent a piece of fixed text (such as a window title, field label, or button label) that is displayed in the user interface. Variable names are used to provide multi-language support (MLS). The implementation of a variable name, such as prtnum, can be configured in multiple ways to support translations or customizations, or to accommodate a specific user interface, such as an RF or mobile device screen. |
| Form ID | Unique identifier of a form associated with a client window. |
| Customization Level | Value associated with a database entry that determines whether the entry is distributed with the standard application or has been customized for the specific application instance. Data that is distributed with the application is distributed with a customization level of 0 (zero), which is the lowest level. When you define a variable configuration, it is automatically assigned a customization level of 10. When the application framework is determining which database entry to use, it uses the customization level as one of the determining factors. Entries with a higher customization level take precedence over those with a lower customization level. For example, the customization level of attr\_str1 is 0 (zero), but when you configure a custom field for attr\_str1, the new configuration is automatically assigned a customization level of 10, which takes precedence. This field is display only. |
| Enabled | Specifies whether the configuration is enabled for the variable name. |
| Character Value | Character (text) string consisting of letters and numbers. This value is used when the **Default Type** field value is set to **Alpha (A)**, and the **Default Value Client Function** field is blank. |
| Float Value | Numeric data with a decimal point. This value is used when the **Default Type** field value is set to **Float (F)**, and the **Default Value Client Function** field is blank. |
| Default Value Client Function | Client function command that is used to populate the default value. This field is not used when the **Default Type** field is set to **Component**.<br>-   • **DATE/TIME**: Sets the value to the current server date and time; the following rounding options are also available:
    -   • **DATE/TIME (D)**: Rounded to the nearest day
    <br>-   • **DATE/TIME (H)**: Rounded to the nearest hour
    <br>-   • **DATE/TIME (M)**: Rounded to the nearest minute
    <br>-   • **DATE/TIME (S)**: Rounded to the nearest second
    <br>
<br>-   • **Get Context Value (CNTXTVAR)**: Sets the value in the field to the value available on context for the variable name.
<br>-   • **Environment Variable Value (ENVVAR)**: Sets the value in the field to the value available on the server environment for the variable name. |
| Default Value Command | MOCA command used to populate the default value for the field. This field is displayed only when the **Default Type** field is set to **Component**. |
| Addon ID | Identifier for the component in which the value is used.<br>-   • **3pl**: Third-party logistics component used in a Warehouse Management instance to support the tracking and management of inventory for multiple clients in a single or multi-warehouse environment.
<br>-   • **CUSTOMS**: Customs component used in a Warehouse Management instance to support customs functionality and integration with a duty management application.
<br>-   • **LES**: Global component specifying that the value is available in all SCE installed applications.
<br>-   • **RF**: Radio frequency terminal component specifying that the field is available on RF and mobile device screens displayed in the mobile terminal framework.
<br>-   • **SEAMLES**: Integrator component specifying that the field is only available in Integrator.
<br>-   • **WM**: Warehouse Management component specifying that the field is only available in Warehouse Management. |
| Application ID | Unique identifier of a client window. |
| Default Type | Type of data for which you want to define a default.<br>-   • **Alpha (A)**: Character (text) string consisting of letters and numbers.
<br>-   • **Integer (I)** : Numeric data without a decimal point.
<br>-   • **Float (F)**: Numeric data with a decimal point.
<br>-   • **Date/Time (D)**: Date and time value.
<br>-   • **Component (C)**: Executes a MOCA command to populate the field with a default value.
<br > If you select the **Alpha **(A)**, **Integer (I)**, or **Float (F)** default types, then you have the option to either enter a value in the corresponding value field, or select an option from the **Default Value Client Function** drop-down list.<br > If you select the **Date/Time (D)** default type, then you have the option to either enter (or select) a date and time in the **Date Value** fields, or select an option from the **Default Value Client Function drop-down list. |
| Constant | Indicates that the default value is a constant. This means that the field is populated with the default value whenever the field is cleared. If this check box is deselected, then the field is populated with the default value only when the SetDefaults command is called, such as when a new record is added. |
| Integer Value | Numeric data without a decimal point. This value is used when the **Default Type** field is set to **Integer (I)**, and the **Default Value Client Function** field is blank. |
| Date Value | Date and time values. These values are used when the **Default Type** is set to **Date/Time (D)**, and the **Default Value Client Function** field is blank. |
| Field Name | Variable name that contains the value that should be retrieved from context or the server environment. This field is used only when the **Default Value Client Function** field is set to **Get Context Value (CNTXTVAR)** or **Get Environment Variable Value (ENVVAR)**. |
| Group Name | Identifier used by Blue Yonder product teams to indicate the product group that was responsible for loading data (in a particular row of a table). For example, standard group names include dcs\_data, mcs\_data, sal\_data, and so on. This field is display only. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
