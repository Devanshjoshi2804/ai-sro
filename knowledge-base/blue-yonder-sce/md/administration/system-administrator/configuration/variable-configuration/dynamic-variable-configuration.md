---
title: "Dynamic Variable Configuration"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/admin/dynamic_variable_configuration.htm"
source: "/content/admin/dynamic_variable_configuration.htm"
toc_path:
  - "Administration"
  - "System Administrator"
  - "Configuration"
  - "Variable Configuration"
  - "Dynamic Variable Configuration"
sections:
  - "Add or modify a dynamic variable configuration"
  - "Delete a dynamic variable configuration"
  - "Dynamic variable configuration fields"
images: []
source_sha1: bd474243d8b60843c1f3c7df3522bc4b85d69085
---
# Dynamic Variable Configuration

A dynamic variable configuration is a custom configuration of a field or button on a specific SCE client window or an RF or mobile device form. Custom configurations use both MOCA commands and values of other fields on the form to control whether the field or button is enabled or disabled and visible or hidden.

## Add or modify a dynamic variable configuration

1.  Select **System Administrator > Configuration > ** **Variable Configuration > Dynamic Variable Configuration**.
2.  Perform one of the following tasks:
    -   To add a dynamic variable configuration, from the **Actions** drop-down list, select **Add**.
    -   To modify a dynamic variable configuration, in the grid select the check box next to the configuration name, and then from the **Actions** drop-down list, select **Edit**.
    -   To copy a dynamic variable configuration, in the grid select the check box next to the configuration name, and then from the **Actions** drop-down list, select **Copy**.
3.  Enter information in the [Dynamic variable configuration fields](#Dynamic_variable_configuration_fields).
    
4.  Click **Save**.
5.  If you configured a field for an SCE client window, reset the cache (from the **Tools** menu, select **Reset Cache**).
    
    **IMPORTANT**: For the field to be displayed on SCE client windows, you must reset the cache on each SCE client workstation that accesses the server instance.
    

## Delete a dynamic variable configuration

1.  Select **System Administrator > Configuration > ** **Variable Configuration > Dynamic Variable Configuration**.
2.  In the grid, select the check box next to the dynamic configuration ID.
3.  From the **Actions** drop-down list, select **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Dynamic variable configuration fields

 
| Field | Description |
| --- | --- |
| **Addon ID** | Identifier for the component in which the value is used.<br>-   • **3pl**: Third-party logistics component used in a Warehouse Management instance to support the tracking and management of inventory for multiple clients in a single or multi-warehouse environment.
<br>-   • **CUSTOMS**: Customs component used in a Warehouse Management instance to support customs functionality and integration with a duty management application.
<br>-   • **LES**: Global component specifying that the value is available in all SCE installed applications.
<br>-   • **RF**: Radio frequency terminal component specifying that the field is available on RF and mobile device screens displayed in the mobile terminal framework.
<br>-   • **SEAMLES**: Integrator component specifying that the field is only available in Integrator.
<br>-   • **WM**: Warehouse Management component specifying that the field is only available in Warehouse Management. |
| **Customization Level** | Value that differentiates customized data from standard data. Standard data is distributed with a customization level of 0 (zero). Customized data is assigned a higher customization level, usually in increments of 10. The MCS framework uses the customization level to determine which database entry to use and, as a result, takes the entry with the highest customization level. This field is display only. |
| **Form ID** | Unique identifier for a specific form. |
| **Input Mode** | Client input mode during which the dynamic variable configuration is executed.<br>-   • **Always Enabled (A**): Executes during all client input modes.
<br>-   • **Criteria Only (C)**: Executes when entering search criteria for a query.
<br>-   • **Disabled (D)**: Never executes.
<br>-   • **Edit Existing Record (E)**: Executes when editing an existing record, but not during the creation of a new record.
<br>-   • **Edit or New Record (I)**: Executes when editing an existing record and during the creation of a new record.
<br>-   • **New Record (N)**: Executes when adding a new record only (not when editing a record). |
| MLS Text | Description that is displayed in place of the message ID on the SCE client or RF and mobile device user interfaces; for example, as the title of an application window or as the label for a field or control that is displayed on an application window. |
| Date Last Modified | Date and time the dynamic variable configuration was last updated. |
| Application ID | Unique identifier of a client window. |
| Dynamic Configuration ID | Unique identifier for the dynamic variable configuration. |
| Group Name | Identifier used by Blue Yonder product teams to indicate the product group that was responsible for loading data (in a particular row of a table). For example, standard group names include dcs\_data, mcs\_data, sal\_data, and so on. This field is display only. |
| Les Command ID | The LES Command ID of the MOCA command in the les\_cmd table. |
| Last Modified By | User who most recently modified the dynamic variable configuration. |
| Variable Name List | Variable name of a single field or a list of comma-separated variable names of multiple fields that affect the dynamic variable configuration. These variables are the variables whose change or lost focus events will cause the dynamic variable configuration command to be run. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
