---
title: "Valid Possibility"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/admin/valid_possibility.htm"
source: "/content/admin/valid_possibility.htm"
toc_path:
  - "Administration"
  - "System Administrator"
  - "Configuration"
  - "Variable Configuration"
  - "Valid Possibility"
sections:
  - "Define valid possibilities for a variable configuration"
  - "Delete a valid possibility configuration"
  - "Valid Possibility fields"
images: []
source_sha1: 262ce19d38d371a9378f2436aa652df449856e06
---
# Valid Possibility

You use the **Valid Possibility** page to configure a variable name with a field that displays a list of valid values from which a user can select. This configuration is useful in the following examples:

-   When a field uses codes to indicate status, such as A or D for Available or Damaged.
-   When a field uses codes to indicate type or size, such as Small, Medium, and Large.
-   When a field uses codes to describe a numeric field with a limited set of states, such as 1 for Class 100 and 2 for Class 200.
    
    **Note**: Values for codes are defined in Code Maintenance-Supervisor.
    

## Define valid possibilities for a variable configuration

1.  Select **System Administrator > Configuration > ** **Variable Configuration > Valid Possibility**.
2.  Perform one of the following tasks:
    -   To add a valid possibility configuration, from the **Actions** drop-down list, select **Add**.
    -   To copy a valid possibility configuration, in the grid select the check box next to the variable name, and then from the **Actions** drop-down list, select **Copy**.
    -   To modify a valid possibility configuration, in the grid select the check box next to the variable name, and then from the **Actions** drop-down list, select **Edit**.
3.  Enter information in the [Valid Possibility fields](#Valid_Possibility_fields).
    
4.  Click **Save**.

## Delete a valid possibility configuration

1.  Select **System Administrator > Configuration > ** **Variable Configuration > Valid Possibility**.
2.  In the grid, select the check box next to the variable name.
3.  From the **Actions** drop-down list, select **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Valid Possibility fields

 
| Field | Description |
| --- | --- |
| **Variable Name** | Code, as defined in Message Catalog, that is used to represent a piece of fixed text (such as a window title, field label, or button label) that is displayed in the user interface. Variable names are used to provide multi-language support (MLS). The implementation of a variable name, such as prtnum, can be configured in multiple ways to support translations or customizations, or to accommodate a specific user interface, such as an RF or mobile device screen. |
| **Form ID** | Unique identifier of a form associated with a client window. |
| **Customization Level** | Value associated with a database entry that determines whether the entry is distributed with the standard application or has been customized for the specific application instance. Data that is distributed with the application is distributed with a customization level of 0 (zero), which is the lowest level. When you define a variable configuration, it is automatically assigned a customization level of 10. When the application framework is determining which database entry to use, it uses the customization level as one of the determining factors. Entries with a higher customization level take precedence over those with a lower customization level. For example, the customization level of attr\_str1 is 0 (zero), but when you configure a custom field for attr\_str1, the new configuration is automatically assigned a customization level of 10, which takes precedence. This field is display only. |
| **Enabled** | Specifies whether the configuration is enabled for the variable name. |
| Add Null Row | Indicates that a blank row is placed at the top of the list of valid possibilities. Select this check box to enable a user to leave the field blank (no selection). If deselected, one of the valid possibilities populates the field. |
| Code Column | Column name, as defined in Code Maintenance-Supervisor, that provides the actual value of the field. If the lookup command is "list code descriptions for...", then the **Code Column** should be "codval". |
| Sort Columns | Column name, as defined in Code Maintenance-Supervisor, by which the list of valid possibilities is sorted. |
| Group Name | Identifier used by Blue Yonder product teams to indicate the product group that was responsible for loading data (in a particular row of a table). For example, standard group names include dcs\_data, mcs\_data, sal\_data, and so on. This field is display only. |
| Application ID | Unique identifier of a client window. |
| Addon ID | Identifier for the component in which the value is used.<br>-   • **3pl**: Third-party logistics component used in a Warehouse Management instance to support the tracking and management of inventory for multiple clients in a single or multi-warehouse environment.
<br>-   • **CUSTOMS**: Customs component used in a Warehouse Management instance to support customs functionality and integration with a duty management application.
<br>-   • **LES**: Global component specifying that the value is available in all SCE installed applications.
<br>-   • **RF**: Radio frequency terminal component specifying that the field is available on RF and mobile device screens displayed in the mobile terminal framework.
<br>-   • **SEAMLES**: Integrator component specifying that the field is only available in Integrator.
<br>-   • **WM**: Warehouse Management component specifying that the field is only available in Warehouse Management. |
| Lookup ID | Identifier for a lookup ID that provides the lookup command. Lookup IDs are defined outside of the web client and must be loaded into the instance. |
| Disable Combo w/Single Row | Indicates that when the lookup command returns a single row, the single row is selected and the field becomes unavailable for data entry. |
| Allow Editing in Query Mode | Indicates that when the field is displayed in query mode, it allows the entry of free-form text while the form on which it is displayed is in query mode. Select this check box if you want to enable users to specify criteria in the field, such as a wildcard value, when the field is used in query mode. |
| Description Column | Column name, as defined in Code Maintenance-Supervisor, that provides the description of the code value. If the lookup command is "list code descriptions for...", then the **Description Column** should be "lngdsc" or "short\_dsc" depending on whether you want to use the long or short description for the column. |
| Grid Lookup Columns | Column name (or comma-separated list of column names), as defined in Code Maintenance-Supervisor, that you want to be displayed when the field displays with a lookup in an editable grid. For example, if you want the lookup to provide both the code value and its description, you would specify those two columns. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
