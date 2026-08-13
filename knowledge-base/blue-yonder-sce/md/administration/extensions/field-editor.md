---
title: "Field Editor"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/admin/field_editor.htm"
source: "/content/admin/field_editor.htm"
toc_path:
  - "Administration"
  - "Extensions"
  - "Field Editor"
sections:
  - "Field configuration attributes"
  - "Action authorizations"
  - "Move Options field configuration"
  - "Shortcut keys"
  - "Browser shortcut keys"
  - "Event propagation"
  - "View a field configuration"
  - "View an action authorization"
  - "View an extensible field configuration"
  - "View a field configuration on a form type page"
  - "Add or modify a field configuration"
  - "Delete a field configuration"
  - "Context fields"
  - "Attributes fields"
  - "Message fields"
  - "Bulk Copy fields"
images:
  - "/content/resources/images/image1100232.png"
  - "/content/resources/images/image1098457.png"
  - "/content/resources/images/image1100232.png"
  - "/content/resources/images/image1098457.png"
  - "/content/resources/images/image1100232.png"
  - "/content/resources/images/image1098457.png"
  - "/content/resources/images/image1140974.png"
  - "/content/resources/images/image524298.png"
source_sha1: 1b4193d5c2970a13385f15f2614809e75ac36c5e
---
# Field Editor

You use the Field Editor to view and configure extensible fields in the web client. The Field Editor displays the name, description, reference (an additional 40-character description), and an extension ID (an internal identifier that represents the extensible field and its associated configurations).

**Note**: Not all fields in the application can be configured. The availability of extensible fields depends on what is released in the standard application.

You can configure the following types of fields:

-   **Fields on pages created using Page Builder**: When you add a new form type page, or when a form type page is added by Page Builder in support of a grid type page, all fields can be configured.
-   **Actions**: An action is a task that a user can perform in the web client that is displayed as a button or link on the user interface. Several pages in the application have distributed actions that are extensible and can be configured. See [Action authorizations](#Action_authorizations) and [Shortcut keys](#Shortcut_keys).
-   **Distributed extensible fields**: Several pages in the application have distributed extensible fields. For example, the Move Options field is used when a user at a workstation requests an inventory or transport equipment move. You can control which move option is available to a user by selecting a default value by role. See [Move Options field configuration](#Move_Options_field_configuration). In addition, select fields in other functional areas such as wave planning and item configuration are extensible and can be configured.

From the Field Editor page, you can select a field and access the Field Configuration page to maintain field configurations.

**Note**: You can also access the Field Configuration page from the page, window, **Action** drop-down list, or tag tooltip on which the field or action is displayed. See [View a field configuration on a form type page](#View_a_field_configuration_on_a_form_type_page), [View an action authorization](#View_an_action_authorization), or [View an extensible field configuration](#View_an_extensible_field_configuration).

## Field configuration attributes

A field configuration allows you to define the context and properties for viewing and taking action on a field. A Default configuration exists for each field.

You can define the following attributes for a field configuration:

-   **Context**: A unique combination of warehouse (site), menu, and client (subsite) in which the configuration takes effect. For example, if you select a context with the values of WMD2, All Menus, and Client A, the attributes and authorizations of that field configuration are used when a user logs in to WMD2 and selects Client A. The configuration is not applied for users who log into WMD1, or who log in to WMD2 without selecting Client A.

If multiple contexts apply to the same user, the most specific context is used. The application uses the following order (first to last) to determine which context is the most specific for a user:

1.  Client (subsite)
2.  Warehouse (site)
3.  Menu

For example, if you have a configuration with context values of All Sites, All Menus, and All Subsites, and a second with WMD1, All Menus, and All Subsites, the second context is applied for users logged in to WMD1.

If a user has access to multiple warehouses (sites), only the context for the selected warehouse applies. In the previous example, if the user logs out of WMD1 and selects WMD2, the application uses the All Sites, All Menus, and All Subsites configuration.

If a user has access to multiple clients (subsites) and selects more than one client at the same time, the application uses a configuration with All Subsites.

-   **Properties**: The appearance of the field that can include the following settings:
    -   **Attributes**: The available attributes may include the field label, whether the field is required, the value that is displayed or selected by default, the field type and whether to validate a value against a list of allowed values, and minimum and maximum field lengths.
        
        **Note**: The **Attributes** fields are not enabled for an action authorization.
        
    -   **Authorization**: The visibility and editability of the field. You define the following permissions:
        -   **Visible**: The field is always visible, always hidden, or visible based on permission by selected role, privilege, and custom permission.
            
            **Note**: When accessing the application using the Portal Server Administrator role, a placeholder remains on the page, window, **Actions** drop-down list, and tag tooltip for a hidden field so that you can update the configuration.
            
        -   **Editable**: Editability refers to the user's ability to take action in the field. For example, if the field is a drop-down list, the user action is selecting a value. If the field is an action, the user action is performing the action. The field is always editable, never editable, or editable based on permission by selected role, privilege, and custom permission.
            
            **Notes**:
            
            -   If no roles have visibility permissions, the field is not displayed and you do not need to set additional permissions for editability.
            -   If no roles have editability permissions, depending on the visibility permission level, the field may be displayed, but the user is unable to make a selection.
            

## Action authorizations

An action is a task that a user can perform in the web client. On the user interface, an action can be displayed as a button or as a link on a page, a window, an **Actions** drop-down list, and a tag tooltip. An action authorization is a field configuration of an action that determines the permissions to view and perform the action.

Each action is associated with a privilege. The privilege is assigned to a distributed configuration to provide visible permissions for the action. A role can then be assigned the privilege to view the action. You can assign the privilege to the role using the Roles page. See [Add or modify a role](../system-administrator/authorization/roles.md).

Distributed web client roles are already assigned privileges typically used by the role. For example, Add Inventory is an action that can be performed on the Inventory page, LPN tab. The Add Inventory action authorization includes the following settings:

-   **Visible** field is set to **Permission Based** and the Inventory Adjust privilege is selected.
-   **Editable** field is set to **Always**.

Both the Outbound Planner and Picking Manager roles access the Inventory page, LPNs tab. The Picking Manager role is assigned the Inventory Adjust privilege and can view and perform the Add Inventory action from the **Actions** drop-down list. The Outbound Planner role is not assigned the privilege and the Add Inventory action is hidden.

To view which privileges are assigned to an action, see [View an action authorization](#View_an_action_authorization). To view which privileges are assigned to a role, see View privileges for a role.

**Notes**:

-   Not all actions in the application can be authorized. To view which pages contain actions that can be configured, see [View an action authorization](#View_an_action_authorization).
-   You can also assign the always or never permissions if you want to use a generic authorization.

You maintain action authorizations using the Field Configuration page. Field Configuration is accessible from the gear![Extensions settings](../../../images/resources/images/image1100232.png) icon associated with an extensible action or from the Field Editor.

## Move Options field configuration

The **Move Options** field (also referred to as Move Method) is used when a user at a workstation requests an inventory (including putaway, loading, and unloading) or transport equipment move. The following move options are available:

-   **Add to Work Queue**: Indicates that a work request is sent to the work queue for an RF operator to complete the physical move. With this option, you can also assign the work to a specific user.
-   **Move Immediately**: Indicates that the location is immediately updated in the application, and no work request is sent.

The **Move Options** field is an option button field that provides the move options as selections when a user needs to complete a move.

You can use field configuration to control the selections available to a role. For example, your Receiving Clerk role is not allowed to select the **Move Immediately** option. You configure the Receiving putaway **Move Options** field to display the **Add to Work Queue** option as the default value, and not allow the Receiving Clerk to select **Move Immediately**.

## Shortcut keys

A keyboard shortcut is a special key or combination of keys that executes a specific action on a page. Shortcut keys provide an easier and quicker method of performing an action rather than using the computer mouse.

You can configure shortcut keys for a page that includes distributed, extensible actions (such as the Packing processing page in Warehouse Management) using field extensibility. Shortcut key configuration involves assigning a key or a key combination to the action, and if necessary, restricting how the browser handles default events that are assigned to the shortcut keys.

Keys that can be assigned as a shortcut are listed in the **Keys** drop-down list. The following characters cannot be used as a single key shortcut, but can be combined with another key, such as **Shift+A**, **Ctrl+X**, and so on:

-   **Alt**, **Ctrl**, and **Shift** keys

-   The following symbol keys from the main keyboard: **! @ # $ % ^ & \* ( )**

### Browser shortcut keys

Browsers have default shortcut key configurations. You can identify which shortcut keys are used by a browser by searching for shortcuts in the browser's help. Some of these shortcuts can be overridden by an event propagation configuration, and some shortcuts may be restricted from use. Make sure to test your shortcut configuration to identify whether there is a conflict with a default browser shortcut.

### Event propagation

When you want to use a shortcut key that is already used by a browser (and is not restricted), you can control how the browser responds to the shortcut key using event propagation. Browsers use event propagation to manage how the shortcut key event executes an action on a webpage. Event propagation also controls whether a shortcut key event is "bubbled up" from a nested user interface component to be executed by the browser. The event propagation setting enables you to restrict default browser event handling to ensure your shortcut keys do not conflict with default browser shortcut keys.

**Note**: Distributed actions have an event propagation option assigned by default.

The following event propagation options are available:

-   **Allow All**: Does not change the default browser behavior for the shortcut key (if any), including when a shortcut key is assigned to a nested interface component. If a shortcut key is used by a browser event and the action that you configured, both actions will be executed when the shortcut key is used. For example, if **Ctrl+P** is the browser default shortcut for printing and you assign **Ctrl+P** as the shortcut to the Process action on the Packing page, both actions will be executed.
-   **Prevent Default**: Disables the default browser behavior for the shortcut key (if any) when the Packing page is displayed. Most of the distributed actions are configured with this option to avoid having duplicate actions executed with the same shortcut key.
-   **Stop Propagation**: Stops a shortcut key event on a nested user interface component from being delivered to the browser, so that the browser does not execute the action.
-   **Stop Event**: Combines the Prevent Default and Stop Propagation options. This option stops the nested shortcut key event from being delivered to the browser, and disables the default browser behavior for the shortcut key (when the Packing page is displayed).

## View a field configuration

1.  To view a field configuration using the Field Editor:
    
    1.  Select **Extensions > Field Editor**.
    2.  In the grid, select the field or action, and then click **Configure**.
    
2.  To view a field configuration from the page, window, **Actions** drop-down list, or tag tooltip on which the field or action is displayed:
    
    -   See [View an action authorization](#View_an_action_authorization).
    -   See [View an extensible field configuration](#View_an_extensible_field_configuration).
    -   See [View a field configuration on a form type page](#View_a_field_configuration_on_a_form_type_page).
    

## View an action authorization

1.  Open one of the following pages that contains extensible actions:
    -   Appointments
    -   Door Activity
    -   Inbound Shipments
    -   Inventory
    -   Outbound
    -   Staging
    -   Transport Equipment
    -   Waves and Picks
    -   Work Queue
2.  Navigate to the action.
3.  Perform one of the following tasks:
    -   If you are viewing a page, in the page title bar, click ![Extensions settings](../../../images/resources/images/image1098457.png).
    -   If you are viewing an expanded **Actions** drop-down list, a window, or a tag tooltip, press **Ctrl + Shift + X**.
4.  Click ![Extensions settings](../../../images/resources/images/image1100232.png) next to an action. The Field Configuration page is displayed.
    
    **Note**: When you point to the gear icon, a blue box is displayed outlining the action to indicate that you are accessing the Field Configuration page rather than clicking on the action.
    

## View an extensible field configuration

1.  Access the page that contains the extensible field.
2.  Navigate to the extensible field.
3.  Perform one of the following tasks:
    -   If you are viewing a page, in the page title bar, click ![Extensions settings](../../../images/resources/images/image1098457.png).
    -   If you are viewing a window, press **Ctrl + Shift + X.**
4.  Click ![Extensions settings](../../../images/resources/images/image1100232.png) next to the field name. The Field Configuration page is displayed.

## View a field configuration on a form type page

1.  Perform one of the following tasks:

-   Open a form type page from the menu.
-   Open a form type page associated to a grid, and then from the **Actions** drop-down list, select **Add**.

3.  Click ![Extensions settings](../../../images/resources/images/image1098457.png) displayed on the right in the page title bar. The Form Configuration page is displayed.

1.  Select a configuration.
2.  Under **FIELDS AND LAYOUT**, click the field name. The Field Configuration page is displayed.

## Add or modify a field configuration

**Note**: An extensible field may be displayed more than once in the application (such as the Create New Appointment action that is displayed on the Door Activity, Staging, and Appointments pages). Adding or modifying a field configuration affects all occurrences of that extensible field.

1.  [View a field configuration](#View_a_field_configuration).

1.  Under **Configurations**, perform one of the following tasks:
    -   To add a configuration, click **Add**.
    -   To copy a configuration, select a configuration, and then click **Copy**.
    -   To modify a configuration, select the configuration.
2.  Under **CONTEXT**, enter information in the [Context fields](#Context_fields).
    
    **Note**: Only one unique combination of warehouse, menu, and client can exist per configuration.
    

1.  To define the appearance of the field, under **PROPERTIES**, enter information in the [Attributes fields](#Attributes_fields).
    
    **Note**: The **Attributes** fields are not enabled when modifying an action authorization.
    
2.  To define labels:
    1.  Click **Labeling**.
    2.  To copy a label:
        1.  In the grid, select the check box next to the name to copy, and then click **Copy**.
        2.  Enter information in the [Message fields](#Message_fields).
        3.  Click **Save**.
    3.  To copy multiple labels:
        1.  In the grid, select the check box next to the names to copy, and then click **Copy**.
        2.  Enter information in the [Bulk Copy fields](#Bulk_copy_fields).
        3.  Click **Save**.
    4.  To delete a label, in the grid, select the check box next to the names to delete, and then click **Delete**. A confirmation message is displayed.
    5.  To edit message text for a label, in the grid, click ![Edit](../../../images/resources/images/image1140974.png), enter the message text and click **Save**, or to edit the next label, click **Save & Next**.
    6.  When finished, click ![Close](../../../images/resources/images/image524298.png) to close.

1.  To define visibility, select the **Authorization** tab, and then in the **Visible** field, perform one of the following tasks:
    -   To make the field visible, select **Always**.
    -   To hide the field, select **Never**.
    -   To limit visibility to selected roles, privileges, and custom permissions:
        1.  Select **Permission Based**.
        2.  From the **Visible Permissions** drop-down list, select the roles, privileges, and custom permissions for which the field is made visible.
            
            **Note**: Only the selected roles, and the roles to which the selected privileges and permissions are assigned, will have visibility to the field.
            
2.  To define editability, select the **Authorization** tab, and then in the **Editable** field, perform one of the following tasks:
    -   To make the field editable (a user can select an option or perform an action), select **Always**.
    -   To make the field unavailable for editing, select **Never**.
        
        **Note**: If the field is configured to be hidden, then it is also unavailable for editing.
        
    -   To limit editability to selected roles, privileges, and permissions:
        1.  Select **Permission Based**.
        2.  From the **Editable Permissions** drop-down list, select the roles, privileges, and custom permissions for which the field is made editable.
            
            **Note**: Only the selected roles, and the roles to which the selected privileges and permissions are assigned, will have permission to select an option in the field.
            
3.  To define a keyboard shortcut:
    
    1.  Select the **Keyboard Shortcuts** tab, select the **Keys** tab, and then click **Add**.
    2.  To use **Alt**, **Ctrl**, and **Shift**, select the corresponding check box.
    3.  From the **Key** drop-down list, select a key.
        
        **Note**: The drop-down list displays all available keys. See [Shortcut keys](#Shortcut_keys).
        
    4.  From the **Action** drop-down list, select the action to perform.
    5.  To change the default event propagation setting for the action, select the **Actions** tab, and then for an action, select one of the following options:
        -   **Allow All**: Allows the default browser action (if any) to execute when the shortcut key is used and allows the shortcut key event on a nested user interface component to be delivered to the browser.
        -   **Prevent Default**: Disables the default browser action (if any) from executing when the shortcut key is used.
        -   **Stop Propagation**: Prevents a shortcut key event on a nested user interface component from being delivered to the browser.
        -   **Stop Event**: Combines Prevent Default and Stop Propagation.
4.  Click **Save**.

## Delete a field configuration

**Note**: If an extensible field is used more than once in the application, deleting a field configuration removes it from all occurrences of the extensible field.

1.  Perform one of the following tasks:
    
    -   [View a field configuration](#View_a_field_configuration).
    -   [View an action authorization](#View_an_action_authorization).
    -   [View an extensible field configuration](#View_an_extensible_field_configuration).
    
2.  Under **Configurations**, select the configuration, and then click **Delete**. A confirmation message is displayed.
    
3.  Click **Yes**.
    

## Context fields

 
| Field | Description |
| --- | --- |
| **Extension ID** | Unique internal identifier for an entity (such as a field, action, or page) that is enabled for extensibility. The extension ID identifies the entity, configurations, and if the entity is used within a variety of functions within the application, specific use of the entity in the application. |
| **Site** | Warehouse to which the configuration applies. The combination of site (warehouse), menu, and subsite (client) defines the context in which the configuration takes effect. |
| **Menu** | Application module to which the configuration applies. The combination of site (warehouse), menu, and subsite (client) defines the context in which the configuration takes effect. |
| **Subsite** | Client to which the configuration applies. The combination of site (warehouse), menu, and subsite (client) defines the context in which the configuration takes effect. |

## Attributes fields

 
| Field | Description |
| --- | --- |
| **Required** | If Yes, users are required to enter a value in the field.<br > If No, users are not required to enter a value in the field. |
| **Default** | Value that is displayed in the field when the page is first displayed. The value can be a user-defined entry or a selection from a drop-down list, depending on the field being configured.<br > The **Move Options** field **Default** field either displays a drop-down list with the Add to Work Queue and Move Immediately options, or is a text entry field in which you must enter one of the following default values:<br > **IMPORTANT**: The default values are case sensitive and must be entered exactly as shown.<br>-   • **workQueue**: Indicates that Add to Work Queue is the default selection.
<br>-   • **immediate**: Indicates that Move Immediately is the default selection. |
| **Field Type** | Determines the type of control in which the field is rendered, such as a text box, drop-down list (referred to as a combo box), or lookup field. This attribute is only available when a page is sourced from a Configurable Web Service resource, and the displayed values for the field are configured within the resource and linked actions as either a lookup field or drop-down list field type.<br > The options vary by the type of field specified in the Configurable Web Service:<br>-   • **Lookup field**: Valid field types are **Text Field**, **Combo Box**, and **Lookup Field**
<br>-   • **Drop-down list field**: Valid field types are **Text Field** and **Combo Box** |
| Description Field | Indicates the type of value that is displayed in a lookup or drop-down list (referred to as a combo box) field. The type of value, such as a code value or a short description, is determined by the available indexes that are defined in the Configurable Web Service resource and vary by the field type.<br > For example, if a drop-down list displays data type values, you can specify that those values be displayed as short descriptions, such as Alpha, Integer, and Float, rather than code values, such as A, I, and F. Similarly, for a lookup field type, you can specify the type of value that is displayed for a lookup selection. |
| **Validate Data** | If Yes, a user-entered value is validated against a list of allowed values defined by the Configurable Web Service resource and linked actions that support the page on which the field is being rendered.<br > If No, a user-entered value is not validated against a list of allowed values.<br > **Note**: This field is available when the **Field Type** value is **Text Field**. |
| Minimum Length | Minimum number of characters that the application accepts for the field when a value is scanned or typed into the field. If the entered value does not contain enough characters to meet the minimum number, then the application does not accept the value. This field is used only when the **Numeric Mask** field is set to **Any Character (A)** or **ASCII(0-127) (S)**. |
| Maximum Length | Maximum number of characters that the application accepts for the field when a value is scanned or typed into the field. If the entered value exceeds the maximum character number, then the application does not accept the value. This field is used only when the **Numeric Mask** field is set to **Any Character (A)** or **ASCII(0-127) (S)**. |

## Message fields

 
| Field | Description |
| --- | --- |
| **Locale** | Locale associated with the message. The message is displayed to users whose locale matches the message's locale. A locale defines a set of culture-specific components, such as language, time and date formats, currency formats, and a measurement unit system. |
| **Message Text** | Text to be displayed in the application. You can include HTML tags, except script-based tags, in this field to format your message. For example, entering "Add <b > Role</b>" in this field displays "Add **Role**". A preview of the message text as it will be displayed is provided in the **Message Preview** field. |
| **Menu** | Application menu associated with the message. The message is only displayed when working in the specified menu. |
| **Site** | Warehouse associated with the message. The message is only displayed when working with the specified warehouse. |
| Subsite | Client associated with the message. The message is only displayed when working with the specified client. |
| Message Preview | A preview of the message entered in the **Message Text** field as it will be displayed in the application. The preview field is especially useful to validate whether any HTML tags that you entered in the **Message Text** field are displayed as expected. This field is display only. |

## Bulk Copy fields

 
| Field | Description |
| --- | --- |
| **Menu** | Application menu associated with the message. The message is only displayed when working in the specified menu. |
| **Locale** | Locale associated with the message. The message is displayed to users whose locale matches the message's locale. A locale defines a set of culture-specific components, such as language, time and date formats, currency formats, and a measurement unit system. |
| **Site** | Warehouse associated with the message. The message is only displayed when working with the specified warehouse. |
| **Subsite** | Client associated with the message. The message is only displayed when working with the specified client. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
