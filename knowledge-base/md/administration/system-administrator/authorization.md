---
title: "Authorization"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/admin/authorization.htm"
source: "/content/admin/authorization.htm"
toc_path:
  - "Administration"
  - "System Administrator"
  - "Authorization"
sections:
  - "Setup tasks for web client authorization"
  - "Maintain users and roles based on installation configuration"
images: []
source_sha1: 2cf5e7fff133fda5cc69c0010f01ec652fca6da7
---
# Authorization

Authorization is the process of allowing an authenticated user access to the appropriate functionality available from an application. In the Supply Chain Execution (SCE) web client, authorization is managed by maintaining a list of roles, with each role mapped to a list of functions. Authorizing a user involves assigning the System User role (for working in the web client user interface) and other roles appropriate for the tasks they need to perform in the application to the user. Most roles are mapped to menus to provide navigation to the pages required to complete tasks within the application.

## Setup tasks for web client authorization

To support user authorization in the web client, perform the following setup tasks:

1.  **Identify your installation configuration**. If your installation includes more than one application in the web client, the process to maintain users and roles varies depending on the installation configuration. To identify the process that is appropriate for your configuration, see [Maintain users and roles based on installation configuration](#Maintain_users_and_roles_based_on_installation_configuration).
2.  **Maintain roles**. Perform the following tasks:
    -   **Determine if the roles exist in the application**. Each application provides distributed web client role configurations aligned to functional areas in the application. See [Distributed web client roles](authorization/roles.md).
    -   **Add roles**. Add any roles needed to address the tasks and authorization required by your users. See [Add or modify a role](authorization/roles.md).
3.  **Maintain role menu assignments**. Roles are assigned to menus to provide navigation to the functionality.
    -   **Determine if roles are assigned to a menu**. If you are using distributed web client roles, most roles are assigned to distributed web client menus. You can view menus and role assignments using the Menu Editor. See [View a menu](../extensions/menu-editor.md).
    -   **Assign a role to a menu**. If you add a new role, use a distributed web client role that is not assigned to a menu, or copy and modify a distributed role, then you must add the role to a menu, using the Menu Editor. To assign a role to a menu, or to add a new menu, see [Add or modify a menu](../extensions/menu-editor.md).
        
        **Note**: The Menu Editor is part of the Extensions functionality. To view and manage menus, your user account must be assigned to the Portal Server Administrator role.
        
4.  **Maintain users and assign roles**. After roles exist in the application, you can assign roles to users to provide user access to the application functionality. See [Add or modify a user](authorization/users.md).
    
    **IMPORTANT**:
    
    -   All web client users must be assigned to the System User role. The role is distributed with the application and authorizes a user to work in the web client user interface.
    -   All API users must be assigned to the Base API role. This role is distributed with the application and authorizes a user to make basic API requests.
    -   For efficient system performance, do not assign more than 25 roles to a single user. The application validates user authorization for each web client role option. Exceeding this number of assigned roles can cause errors when the system tries to validate user permissions.
    

## Maintain users and roles based on installation configuration

The following applications require a portal server installation: Warehouse Management, Event Management, and Warehouse Labor Management production instances. If your portal server installation supports more than one application, the process to maintain users and roles varies depending on the installation configuration.

-   **Multiple applications, combined instance**: If you have installed multiple applications in the same instance, then you can maintain users and roles through the web client. You have a combined instance if you use one URL to access and view menus, pages, users, and roles in the web client for both applications, such as Warehouse Management and Event Management.
-   **Multiple applications, separate instances**: If you have multiple applications installed in separate instances, each with their own portal server instance, then you can maintain users and roles using each application's web client. You have separate instances if you use two different URLs to access the applications.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
