---
title: "Inputs"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/admin/inputs.htm"
source: "/content/admin/inputs.htm"
toc_path:
  - "Administration"
  - "System Administrator"
  - "Configuration"
  - "Variable Configuration"
  - "Inputs"
sections:
  - "Define an input value for a variable configuration"
  - "Delete an input value"
  - "Inputs fields"
images: []
source_sha1: 6446f5af759a20570ea17034b331496011dca849
---
# Inputs

You use the Inputs page to define the input properties of a field, such as minimum and maximum length, and the type of characters allowed in the field.

## Define an input value for a variable configuration

1.  Select **System Administrator > Configuration > ** **Variable Configuration > Inputs**.
2.  Perform one of the following tasks:
    -   To add an input value, from the **Actions** drop-down list, select **Add**.
    -   To copy an input value, in the grid select the check box next to the variable name, and then from the **Actions** drop-down list, select **Copy**.
    -   To modify an input value, in the grid select the check box next to the variable name, and then from the **Actions** drop-down list, select **Edit**.
3.  Enter information in the [Inputs fields](#Inputs_fields).
    
4.  Click **Save**.

## Delete an input value

1.  Select **System Administrator > Configuration > ** **Variable Configuration > Inputs**.
2.  In the grid, select the check box next to the variable name.
3.  From the **Actions** drop-down list, select **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Inputs fields

 
| Field | Description |
| --- | --- |
| **Variable Name** | Code, as defined in Message Catalog, that is used to represent a piece of fixed text (such as a window title, field label, or button label) that is displayed in the user interface. Variable names are used to provide multi-language support (MLS). The implementation of a variable name, such as prtnum, can be configured in multiple ways to support translations or customizations, or to accommodate a specific user interface, such as an RF or mobile device screen. |
| **Form ID** | Unique identifier of a form associated with a client window. |
| **Customization Level** | Value associated with a database entry that determines whether the entry is distributed with the standard application or has been customized for the specific application instance. Data that is distributed with the application is distributed with a customization level of 0 (zero), which is the lowest level. When you define a variable configuration, it is automatically assigned a customization level of 10. When the application framework is determining which database entry to use, it uses the customization level as one of the determining factors. Entries with a higher customization level take precedence over those with a lower customization level. For example, the customization level of attr\_str1 is 0 (zero), but when you configure a custom field for attr\_str1, the new configuration is automatically assigned a customization level of 10, which takes precedence. This field is display only. |
| **Numeric Mask** | Input mask that defines the type of characters allowed to be entered in the field.<br>-   • **Any Character (A)**: Allows any character.
<br>-   • **Alpha/Numeric (H)**: Allows only alphabetic or numeric characters; no symbols.
<br>-   • **Floating Point (F)**: Allows only an integer with a decimal value.
<br>-   • **Integer (I)**: Allows only numeric values.
<br>-   • **ASCII(0-127) (S)**: Allows only ASCII characters 0 to 127; typically used to support meta data. |
| Maximum Length | Maximum number of characters that the application accepts for the field when a value is scanned or typed into the field. If the entered value exceeds the maximum character number, then the application does not accept the value. This field is used only when the **Numeric Mask** field is set to **Any Character (A)** or **ASCII(0-127) (S)**. |
| Left Precision | Maximum number of digits to the left of the decimal point that are allowed. This field is used only when the **Numeric Mask** field is set to **Alpha/Numeric (H)**, **Floating Point (F)**, or **Integer (I)**. |
| Case Conversion | Character case to which the value is automatically converted upon exiting the field. This field is used only when the **Numeric Mask** field is set to **Any Character (A)** or **ASCII(0-127) (S)**.<br>-   • **No Case Conversion (N)**: The value is not converted.
<br>-   • **Force Upper Case (U)**: The value is automatically converted to capital (uppercase) letters.
<br>-   • **Force Lower Case (L)**: The value is automatically converted to small (lowercase) letters. |
| Multiple Line Flag | Indicates that a field supports multiple lines of data. This field is used only when the **Numeric Mask** field is set to **Any Character (A)** or **ASCII(0-127) (S)**. |
| Enabled | Specifies whether the configuration is enabled for the variable name. |
| Auto Mask | Not currently used. |
| Addon ID | Identifier for the component in which the value is used.<br>-   • **3pl**: Third-party logistics component used in a Warehouse Management instance to support the tracking and management of inventory for multiple clients in a single or multi-warehouse environment.
<br>-   • **CUSTOMS**: Customs component used in a Warehouse Management instance to support customs functionality and integration with a duty management application.
<br>-   • **LES**: Global component specifying that the value is available in all SCE installed applications.
<br>-   • **RF**: Radio frequency terminal component specifying that the field is available on RF and mobile device screens displayed in the mobile terminal framework.
<br>-   • **SEAMLES**: Integrator component specifying that the field is only available in Integrator.
<br>-   • **WM**: Warehouse Management component specifying that the field is only available in Warehouse Management. |
| Application ID | Unique identifier of a client window. |
| Locale ID | Identifier for a locale. A locale defines the attributes for a language that affect how information is displayed in the application. |
| Input Mask | Display-only field that contains a combination of the following values:<br>-   • **/INTEGER**: Integer number value
<br>-   • **/FLOAT**: Floating point number
<br>-   • **/POSITIVE**: Specifies a positive number and is combined with /INTEGER or /FLOAT
<br>-   • **/UPPER & LOWER**: Converts characters to upper and lowercase |
| Minimum Length | Minimum number of characters that the application accepts for the field when a value is scanned or typed into the field. If the entered value does not contain enough characters to meet the minimum number, then the application does not accept the value. This field is used only when the **Numeric Mask** field is set to **Any Character (A)** or **ASCII(0-127) (S)**. |
| Right Precision | Maximum number of digits to the right of the decimal point that are allowed. This field is used only when the **Numeric Mask** field is **Alpha/Numeric (H)**, **Floating Point (F)**, or **Integer (I)**. |
| Group Name | Identifier used by Blue Yonder product teams to indicate the product group that was responsible for loading data (in a particular row of a table). For example, standard group names include dcs\_data, mcs\_data, sal\_data, and so on. This field is display only. |
| Force Positive Number | Indicates that the numeric value entered must be a non-negative number; that is, either a positive number (value that is greater than zero) or 0 (zero). If deselected, a negative value (such as -10) is also allowed. This field is used only when the **Numeric Mask** field is set to **Alpha/Numeric (H)**, **Floating Point (F)**, or **Integer (I)**. |
| Display Mask | Not currently used. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
