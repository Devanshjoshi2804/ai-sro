---
title: "Lookup"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/admin/lookup.htm"
source: "/content/admin/lookup.htm"
toc_path:
  - "Administration"
  - "System Administrator"
  - "Configuration"
  - "Variable Configuration"
  - "Lookup"
sections:
  - "Define a variable lookup for a variable configuration"
  - "Delete a variable lookup"
  - "Lookup fields"
images: []
source_sha1: 8bc20a13d056c42938c866b46180558b8e5e481c
---
# Lookup

You use the **Lookup** page to configure a variable name with a lookup icon next to the field to enable the user to search for valid values. If configured for the RF addon ID, this configuration provides the F2 lookup function for the field on RF and mobile device screens. You use a variable lookup instead of a valid possibilities list when the list of valid values is too long to be efficiently displayed in a combo (list) box. For example, the **Item** field provides a lookup icon because there are typically many items; however, the **Warehouse** field provides a list of valid possibilities because there are typically only a few warehouses defined.

The lookup icon provides access to a Lookup window on the SCE client, which can provide additional fields by which the user can search to limit the display of valid values.

## Define a variable lookup for a variable configuration

1.  Select **System Administrator > Configuration > ** **Variable Configuration > Lookup**.
2.  Perform one of the following tasks:
    -   To add a variable lookup, from the **Actions** drop-down list, select **Add**.
    -   To copy a variable lookup, in the grid select the check box next to the variable name, and then from the **Actions** drop-down list, select **Copy**.
    -   To modify a variable lookup, in the grid select the check box next to the variable name, and then from the **Actions** drop-down list, select **Edit**.
3.  Enter information in the [Lookup fields](#Lookup_fields).
    
4.  Click **Save**.

## Delete a variable lookup

1.  Select **System Administrator > Configuration > ** **Variable Configuration > Lookup**.
2.  In the grid, select the check box next to the variable name.
3.  From the **Actions** drop-down list, select **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Lookup fields

 
| Field | Description |
| --- | --- |
| **Variable Name** | Code, as defined in Message Catalog, that is used to represent a piece of fixed text (such as a window title, field label, or button label) that is displayed in the user interface. Variable names are used to provide multi-language support (MLS). The implementation of a variable name, such as prtnum, can be configured in multiple ways to support translations or customizations, or to accommodate a specific user interface, such as an RF or mobile device screen. |
| **Form ID** | Unique identifier of a form associated with a client window. |
| **Customization Level** | Value associated with a database entry that determines whether the entry is distributed with the standard application or has been customized for the specific application instance. Data that is distributed with the application is distributed with a customization level of 0 (zero), which is the lowest level. When you define a variable configuration, it is automatically assigned a customization level of 10. When the application framework is determining which database entry to use, it uses the customization level as one of the determining factors. Entries with a higher customization level take precedence over those with a lower customization level. For example, the customization level of attr\_str1 is 0 (zero), but when you configure a custom field for attr\_str1, the new configuration is automatically assigned a customization level of 10, which takes precedence. This field is display only. |
| **Enabled** | Specifies whether the configuration is enabled for the variable name. |
| Input Fields | Column name (or comma-separated list of column names) that specifies which values to pass to the Lookup window from the calling form. These column names do not define the fields on the Lookup window, only which values, if any, to populate on the Lookup window. Aliasing can be done by using name=alias. |
| Application ID | Unique identifier of a client window. |
| Addon ID | Identifier for the component in which the value is used.<br>-   • **3pl**: Third-party logistics component used in a Warehouse Management instance to support the tracking and management of inventory for multiple clients in a single or multi-warehouse environment.
<br>-   • **CUSTOMS**: Customs component used in a Warehouse Management instance to support customs functionality and integration with a duty management application.
<br>-   • **LES**: Global component specifying that the value is available in all SCE installed applications.
<br>-   • **RF**: Radio frequency terminal component specifying that the field is available on RF and mobile device screens displayed in the mobile terminal framework.
<br>-   • **SEAMLES**: Integrator component specifying that the field is only available in Integrator.
<br>-   • **WM**: Warehouse Management component specifying that the field is only available in Warehouse Management. |
| Lookup ID | Identifier for a lookup ID that provides the lookup command. Lookup IDs are defined outside of the web client and must be loaded into the instance. |
| Allow Multiple Row Select | Indicates that the user is enabled to select multiple rows from the Lookup window to populate the field on the calling form. |
| Return Fields | Column name or a comma-separated list of column names that specifies which field to return from the command. For a validation command, the **Return Fields Flag** must also be selected the return to take place. For a lookup command, multiple columns can be returned and any number of these columns can be returned to the calling form. Aliasing can be done by using name=alias. |
| Group Name | Identifier used by Blue Yonder product teams to indicate the product group that was responsible for loading data (in a particular row of a table). For example, standard group names include dcs\_data, mcs\_data, sal\_data, and so on. This field is display only. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
