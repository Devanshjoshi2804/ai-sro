---
title: "Roles"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/admin/roles.htm"
source: "/content/admin/roles.htm"
toc_path:
  - "Administration"
  - "System Administrator"
  - "Authorization"
  - "Roles"
sections:
  - "Roles and role assignments"
  - "Option types"
  - "Distributed web client roles"
  - "Add or modify a role"
  - "View privileges for a role"
  - "Delete a role"
  - "Role fields"
images: []
source_sha1: 5098282651285c681146e361f3eb823c466b0953
---
# Roles

A role is a category used to assign selected options (such as privileges, reports, and web services) to one or more users. A role is also assigned to the menus that provide navigation for the functionality assigned to the role. You assign a role to users as part of application-based role management to control the web client functionality to which the users have access. See [Setup tasks for web client authorization](../authorization.md).

You maintain roles and assign users to roles using the Roles page; however, depending on your installation configuration, the process may vary. See [Maintain users and roles based on installation configuration](../authorization.md).

Several roles are distributed with the web client that provide authorization for distributed web services aligned to web client functionality. See [Distributed web client roles](#Distributed_web_client_roles).

You maintain roles and assign users to roles using the Roles page. You maintain menu assignments using the Menu Editor. You can also assign roles to users using the Users page.

## Roles and role assignments

Roles are organized in a hierarchical structure that uses parent and child relationships to control a user's ability to assign roles to other users. This structure restricts the ability of a user to assign authorizations to other users, which helps to ensure that users are not given authorization they should not have.

When you create a role, you can assign a parent role to it, which defines its position in the hierarchy. Only the roles to which you are assigned are available for selection as parent roles. This restriction ensures that you can only create a role at a level in the hierarchy that is lower than or equal to your highest assigned role level. Similarly, when assigning a role to another user, you are only allowed to assign a role at a level in the hierarchy that is lower than (but not equal to) your highest assigned role level. However, if you are assigned to the Super role, you can assign any role, including the Super role, to another user.

For example, if a user is assigned to the role Shipping Supervisor, and this role is the highest role to which that user is assigned, that user can create a child role, such as Shipping Clerk, and assign it the parent role of Shipping Supervisor. The shipping supervisor can assign the Shipping Clerk role to another user, but cannot assign the Shipping Supervisor role to another user. Only a user with the role that is the parent for the Shipping Supervisor role is authorized to assign the Shipping Supervisor role.

## Option types

An option type is a category used to group related options such as privileges, directed work, RF operations, and reports. For example, you use the Privileges option type to assign the privileges used to provide role-based permissions for actions.

In order for a role to be useful, options must be assigned to it. You use the **Option Types** drop-down list on the Roles page to maintain the options that are assigned to a role.

The following option types are standard for role configuration:

-   **Custom Permissions**: List of user-defined labels available and associated with specific fields. Permissions are used to limit access to certain functionality through their assignment to roles and extensible fields. See [Permissions](permissions.md).
    
    **IMPORTANT**: The permissions displayed on the Roles page apply to the web client only.
    
-   **API Permissions**: List of permissions available and associated with API methods and endpoints. Permissions are used to limit access to retrieve or modify application information with API requests. For example, View permissions use GET methods, and Create permissions use POST methods.
-   **Directed Operation**: List of the work operations available in the web client. A work operation is a defined activity within the facility usually performed by an operator using a device such as an RF terminal or voice headset. Directed work is a defined activity (such as receiving, picking, counting, or loading transport equipment) performed by an RF operator, who signs on to an RF device and selects the Directed Work option. If work is available, the window displays a piece of directed work to the operator, based on the priority of the work in the work queue, and the permissions and proximity of the operator. You use this option type to limit specific directed work operations to specific roles.
-   **Privileges**: List of actions available in the web client. Privileges are used to limit access to certain functionality through their assignment to roles and actions.
    
    **IMPORTANT**: The privileges displayed on the Roles page apply to the web client only. The privileges displayed on the Role Maintenance window within the SCE client are different and apply only to the SCE client.
    
-   **Reports**: List of the reports available. A report provides a display of information related to the subject of the report, such as status or process tracking information.
-   **RF Screens**: List of RF screens available. RF screens are delivered in the mobile terminal framework (MTF) and displayed on hardware, such as RF terminals, that support the MTF.
    
    **Note**: If your application does not include the RF Screens option type, this list of options may be displayed under the Operations option type.
    
-   **Web Service**: List of pages previously available for a legacy Web application. Starting with the 2021.1.0.0 release, support for the legacy Web application (installed as Web Enablement) ended, and these pages are no longer used.
    

## Distributed web client roles

Distributed web client roles are role configurations that align to functional areas in the application. Many of the distributed roles are also assigned to the appropriate menus to provide navigation to the related functionality.

The following roles are distributed in the web client to provide access to specific functions:

-   **Portal Server Administrator**: Distributed with each portal server instance to align to Extensions-related functionality and navigation.
    
    **Note**: Your user account must have the Portal Server Administrator role assigned to manage role and menu assignment.
    
-   **Warehouse Management functional roles**: Distributed with Warehouse Management to align and access functional areas in the application, such as shipping and receiving. The distributed web client roles are configured with options, such as privileges to provide permissions for actions, and are assigned to the menus that provide navigation to the role-related functionality. Examples of distributed Warehouse Management roles include Inventory Control, Outbound Planner, and Shipping Clerk.
-   **API roles**: Distributed with Warehouse Management to authorize users to retrieve or modify application information through requests sent to API endpoints. These roles contain default sets of permissions that are associated with API modules, which represent functional areas within the application. Examples of API roles include Allocation (API), Receiving Manager (API), and Inventory Manager (API).<br>

**Note**: The API Admin role is used for maintaining APIs with administrative tasks such as making requests, clearing caches, and deploying or updating APIs.

Administrative and user roles are distributed with each web client without assigned menus and are configured with web service role options to provide authorization for working in the web client user interface. Examples of distributed administrative and user roles include System Administrator and System User.

**IMPORTANT**:

-   All web client users must be assigned to the System User role. The role is distributed with the application and authorizes a user to work in the web client user interface.
-   All API users must be assigned to the Base API role. This role is distributed with the application and authorizes a user to make basic API requests.
-   For efficient system performance, do not assign more than 25 roles to a single user. The application validates user authorization for each web client role option. Exceeding this number of assigned roles can cause errors when the system tries to validate user permissions.

You can view the distributed web client roles using the Roles page. You can use the Menu Editor to add or modify the groups and pages that are displayed in the navigation bar for one or more roles.

## Add or modify a role

If you are adding a new role, you must be logged in to the application with a user account that is assigned a role authorized to create the role you want. For example, if you are completing the initial setup of web client roles for your application, log in as a super user.

**IMPORTANT**: It is highly recommended that you do not modify a distributed web client role. These roles provide recommended configurations related to functionality and are already assigned to the menus required for navigation. You can copy a role to simplify your configuration tasks or refer to the distributed roles during application configuration. See [Distributed web client roles](#Distributed_web_client_roles).

1.  Select **System Administrator > Authorization > Roles**.
    
2.  Perform one of the following tasks:
    -   To add a role, click **Add**.
    -   To modify a role, in the gird, click the role.
    -   To copy a role, in the grid, select the check box next to the role, and then click **Copy**.
3.  Enter information in the [Role fields](#Role_fields).
4.  To assign users to this role:
    1.  Click **Users**.
    2.  In the **Available Users** column, select the check box next to the users to assign.
    3.  To make the role available for you to assign to a menu in the Menu Editor, select the check box next to the user with which you are logged in.
        
        **IMPORTANT**: To be able to assign a role to a menu, your user account must be assigned to the role.
        
    4.  Click **Apply**.
5.  To assign options to the role:
    1.  Under **AUTHORIZATIONS**, from the **Option Types** drop-down list, select an [option type](#Option_types). The available and selected options for that option type are displayed.
    2.  In the **Available Options** column, select the check box next to the options to assign.
    3.  Continue to select option types from the **Option Types** drop-down list, and then select options to assign to the role.
6.  Click **Save**. A confirmation message is displayed.
7.  Click **OK**.
8.  To assign a role to a menu:
    1.  Click **Manage Menus**. The Menu Editor is displayed.
    2.  Continue with [Add or modify a menu](../../extensions/menu-editor.md).

## View privileges for a role

A role can be assigned a privilege that provides permission for an action. Some distributed web client roles, such as the Warehouse Management Inventory Manager role, are assigned actions. See [Action authorizations](../../extensions/field-editor.md). You can view the privileges assigned to a role using the Roles page.

1.  Select **System Administrator > Authorization > Roles**.
    
2.  In the grid, click a role.
    
3.  Under **AUTHORIZATIONS**, from the **Option Types** drop-down list, select **Privileges**. The selected privileges are displayed.

## Delete a role

**Note**: It recommended that you do not delete a distributed role. These roles provide recommended configurations related to functionality and can be used for reference during application configuration.

1.  Select **System Administrator > Authorization > Roles**.
    
2.  In the grid, select the check box next to the role.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**. The role is automatically unassigned from any users to which it was assigned.
    
    **Note**: If you delete a role and an assigned user is currently logged into the application, the user remains logged in and can complete tasks related to any currently displayed pages. However, the user will not be able to access additional functionality that is only authorized for the deleted role.
    

## Role fields

 
| Field | Description |
| --- | --- |
| **Role** | Identifier of the role. A role is a category used to assign selected options (such as privileges, reports, and directed operations) to one or more users. |
| **Parent Role** | Role ID that is assigned as the parent role for the role identified in the **Role** field (the child role). Role assignment is controlled by a hierarchical structure that uses parent and child relationships. In order for a role to be available for selection, it must be assigned to a parent role. |
| **Description** | Text that further describes the role. The description should identify the purpose of this role and distinguish it from other roles in the application. |
| **Enabled** | If Yes, the role is enabled for use in the application.<br > If No, the role is not enabled for use in the application. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
