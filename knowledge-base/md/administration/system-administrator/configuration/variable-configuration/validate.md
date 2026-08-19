---
title: "Validate"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/admin/validate.htm"
source: "/content/admin/validate.htm"
toc_path:
  - "Administration"
  - "System Administrator"
  - "Configuration"
  - "Variable Configuration"
  - "Validate"
sections:
  - "Define a validation for a variable configuration"
  - "Delete a validation"
  - "Validate fields"
images: []
source_sha1: 4a1abedfc67700195c7c8910ef0d926d6ee3d691
---
# Validate

You use the Validate page to configure a variable name with a server command that is executed automatically when focus leaves the field. The server command validates the data entry.

Validation only occurs when there is a value in the field (it is not blank), the validate configuration is enabled and the data entry took place during the specified validation mode (for example, during the creation of a new record, or editing of an existing record). The return status of the command determines whether the data entry is valid. If the status is OK, the validation command has successfully validated the input value and it is acceptable. If the return status is not OK, the validation command failed indicating that the input value is not acceptable.

## Define a validation for a variable configuration

1.  Select **System Administrator > Configuration > ** **Variable Configuration > Validate**.
2.  Perform one of the following tasks:
    -   To add a validation, from the **Actions** drop-down list, select **Add**.
    -   To copy a validation, in the grid select the check box next to the variable name, and then from the **Actions** drop-down list, select **Copy**.
    -   To modify a validation, in the grid select the check box next to the variable name, and then from the **Actions** drop-down list, select **Edit**.
3.  Enter information in the [Validate fields](#Validate_fields).
    
4.  Click **Save**.

## Delete a validation

1.  Select **System Administrator > Configuration > ** **Variable Configuration > Validate**.
2.  In the grid, select the check box next to the variable name.
3.  From the **Actions** drop-down list, select **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Validate fields

 
| Field | Description |
| --- | --- |
| **Variable Name** | Code, as defined in Message Catalog, that is used to represent a piece of fixed text (such as a window title, field label, or button label) that is displayed in the user interface. Variable names are used to provide multi-language support (MLS). The implementation of a variable name, such as prtnum, can be configured in multiple ways to support translations or customizations, or to accommodate a specific user interface, such as an RF or mobile device screen. |
| **Form ID** | Unique identifier of a form associated with a client window. |
| **Customization Level** | Value associated with a database entry that determines whether the entry is distributed with the standard application or has been customized for the specific application instance. Data that is distributed with the application is distributed with a customization level of 0 (zero), which is the lowest level. When you define a variable configuration, it is automatically assigned a customization level of 10. When the application framework is determining which database entry to use, it uses the customization level as one of the determining factors. Entries with a higher customization level take precedence over those with a lower customization level. For example, the customization level of attr\_str1 is 0 (zero), but when you configure a custom field for attr\_str1, the new configuration is automatically assigned a customization level of 10, which takes precedence. This field is display only. |
| **Enabled** | Specifies whether the configuration is enabled for the variable name. |
| Validate Command | MOCA command that is executed when focus leaves the control. This command is executed when there is a value in the field (it is not blank), the validate configuration is enabled and the data entry took place during the specified validation mode. |
| Group Name | Identifier used by Blue Yonder product teams to indicate the product group that was responsible for loading data (in a particular row of a table). For example, standard group names include dcs\_data, mcs\_data, sal\_data, and so on. This field is display only. |
| Addon ID | Identifier for the component in which the value is used.<br>-   • **3pl**: Third-party logistics component used in a Warehouse Management instance to support the tracking and management of inventory for multiple clients in a single or multi-warehouse environment.
<br>-   • **CUSTOMS**: Customs component used in a Warehouse Management instance to support customs functionality and integration with a duty management application.
<br>-   • **LES**: Global component specifying that the value is available in all SCE installed applications.
<br>-   • **RF**: Radio frequency terminal component specifying that the field is available on RF and mobile device screens displayed in the mobile terminal framework.
<br>-   • **SEAMLES**: Integrator component specifying that the field is only available in Integrator.
<br>-   • **WM**: Warehouse Management component specifying that the field is only available in Warehouse Management. |
| Application ID | Unique identifier of a client window. |
| Validate Mode | Client input mode during which the validate command is executed when focus leaves the control and the field is not blank.<br>-   • **Always Enabled (A)**: Executes during all client input modes.
<br>-   • **Criteria Only (C)**: Executes when entering search criteria for a query.
<br>-   • **Edit Existing Record (E)**: Executes when editing an existing record, but not during the creation of a new record.
<br>-   • **Edit or New Record (I)**: Executes when editing an existing record and during the creation of a new record.
<br>-   • **New Record (N)**: Executes during the creation of a new record, but not when editing an existing record.
<br>-   • **No selection (blank)**: Validation is not performed. |
| Return Fields Flag | Indicates that the validate command returns data, the validation causes fields to be populated with the returned data. |
| Return Fields | Column name or a comma-separated list of column names that specifies which field to return from the command. For a validation command, the **Return Fields Flag** must also be selected the return to take place. For a lookup command, multiple columns can be returned and any number of these columns can be returned to the calling form. Aliasing can be done by using name=alias. This field is used only when the **Return Fields Flag** check box is selected. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
