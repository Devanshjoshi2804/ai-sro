---
title: "Catalog"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/admin/catalog.htm"
source: "/content/admin/catalog.htm"
toc_path:
  - "Administration"
  - "System Administrator"
  - "Configuration"
  - "Variable Configuration"
  - "Catalog"
sections:
  - "Add or modify a message catalog entry"
  - "Delete a catalog entry"
  - "Catalog fields"
  - "Catalog (Details) fields"
images: []
source_sha1: 59fc756159a981fb8daa243fea712a8f0563fb8b
---
# Catalog

You use the Catalog page to add or modify a variable name, and then maintain catalog entries for a variable name.

**IMPORTANT**: You can add or modify variable configurations for existing variable names, which are those that have been implemented in a Blue Yonder application, such as on a specific SCE client window, form, or RF screen. If you want to add and configure a new variable name, contact your Blue Yonder project team for assistance.

## Add or modify a message catalog entry

1.  Select **System Administrator > Configuration > ** **Variable Configuration > Catalog**.
2.  To add a variable name:

1.  To add a new variable name, from the **Actions** drop-down list, select **Add**.
2.  To copy a variable name, in the grid select the check box next to the variable name, and then from the **Actions** drop-down list, select **Copy**.
3.  Enter information in the [Catalog fields](#Catalog_fields).
4.  Click **Save**.

4.  To add or modify a message catalog entry:
    1.   Select the variable name, and then under **CATALOG DETAILS**, perform one of the following tasks:
        -   To add a message catalog entry, from the **Actions** drop-down list, select **Add**.
        -   To copy a message catalog entry, in the grid select the check box next to the variable name, and then from the **Actions** drop-down list, select **Copy**.
        -   To modify a message catalog entry, in the grid select the check box next to the variable name, and then from the **Actions** drop-down list, select **Edit**.
    2.  Enter information in the [Catalog (Details) fields](#Catalog_\(Details\)_fields).
    3.  Click **Save**.
5.  Continue with [Add or modify a variable configuration](config.md).

## Delete a catalog entry

1.  Select **System Administrator > Configuration > ** **Variable Configuration > Catalog**.
2.  Under **CATALOG DETAILS**, in the grid select the check box next to the variable name.
3.  From the **Actions** drop-down list, select **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Catalog fields

 
| Field | Description |
| --- | --- |
| **Variable Name** | Code, as defined in Message Catalog, that is used to represent a piece of fixed text (such as a window title, field label, or button label) that is displayed in the user interface. Variable names are used to provide multi-language support (MLS). The implementation of a variable name, such as prtnum, can be configured in multiple ways to support translations or customizations, or to accommodate a specific user interface, such as an RF or mobile device screen. |
| **Addon ID** | Identifier for the component in which the value is used.<br>-   • **3pl**: Third-party logistics component used in a Warehouse Management instance to support the tracking and management of inventory for multiple clients in a single or multi-warehouse environment.
<br>-   • **CUSTOMS**: Customs component used in a Warehouse Management instance to support customs functionality and integration with a duty management application.
<br>-   • **LES**: Global component specifying that the value is available in all SCE installed applications.
<br>-   • **RF**: Radio frequency terminal component specifying that the field is available on RF and mobile device screens displayed in the mobile terminal framework.
<br>-   • **SEAMLES**: Integrator component specifying that the field is only available in Integrator.
<br>-   • **WM**: Warehouse Management component specifying that the field is only available in Warehouse Management. |
| **MLS Text** | Description that is displayed in place of the message ID on the SCE client or RF and mobile device user interfaces; for example, as the title of an application window or as the label for a field or control that is displayed on an application window. |
| **Locale ID** | Identifier for a locale. A locale defines the attributes for a language that affect how information is displayed in the application. |

## Catalog (Details) fields

 
| Field | Description |
| --- | --- |
| Variable Name | Code, as defined in Message Catalog, that is used to represent a piece of fixed text (such as a window title, field label, or button label) that is displayed in the user interface. Variable names are used to provide multi-language support (MLS). The implementation of a variable name, such as prtnum, can be configured in multiple ways to support translations or customizations, or to accommodate a specific user interface, such as an RF or mobile device screen. |
| Application ID | Unique identifier of a client window. |
| Product ID | Identifier for the Blue Yonder application with which the message ID is associated. You use "LES" when the message ID is displayed in multiple applications. |
| MLS Text | Description that is displayed in place of the message ID on the SCE client or RF and mobile device user interfaces; for example, as the title of an application window or as the label for a field or control that is displayed on an application window. |
| Group Name | Identifier used by Blue Yonder product teams to indicate the product group that was responsible for loading data (in a particular row of a table). For example, standard group names include dcs\_data, mcs\_data, sal\_data, and so on. This field is display only. |
| Addon ID | Identifier for the component in which the value is used.<br>-   • **3pl**: Third-party logistics component used in a Warehouse Management instance to support the tracking and management of inventory for multiple clients in a single or multi-warehouse environment.
<br>-   • **CUSTOMS**: Customs component used in a Warehouse Management instance to support customs functionality and integration with a duty management application.
<br>-   • **LES**: Global component specifying that the value is available in all SCE installed applications.
<br>-   • **RF**: Radio frequency terminal component specifying that the field is available on RF and mobile device screens displayed in the mobile terminal framework.
<br>-   • **SEAMLES**: Integrator component specifying that the field is only available in Integrator.
<br>-   • **WM**: Warehouse Management component specifying that the field is only available in Warehouse Management. |
| Form ID | Unique identifier of a form associated with a client window. |
| Customization Level | Value associated with a database entry that determines whether the entry is distributed with the standard application or has been customized for the specific application instance. Data that is distributed with the application is distributed with a customization level of 0 (zero), which is the lowest level. When you define a variable configuration, it is automatically assigned a customization level of 10. When the application framework is determining which database entry to use, it uses the customization level as one of the determining factors. Entries with a higher customization level take precedence over those with a lower customization level. For example, the customization level of attr\_str1 is 0 (zero), but when you configure a custom field for attr\_str1, the new configuration is automatically assigned a customization level of 10, which takes precedence. This field is display only. |
| Sort Sequence | Not currently used. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
