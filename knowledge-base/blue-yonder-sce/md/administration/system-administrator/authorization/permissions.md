---
title: "Permissions"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/admin/permissions.htm"
source: "/content/admin/permissions.htm"
toc_path:
  - "Administration"
  - "System Administrator"
  - "Authorization"
  - "Permissions"
sections:
  - "Add a permission"
  - "Delete a field permission"
images: []
source_sha1: 89849227d6551cf70c8a750dd2f6272312c08565
---
# Permissions

A permission is a user-defined label that can be used to associate one or more roles with the authorization to view or edit an extensible field. For example, if you want to allow a role to view a **Quantity** field but not edit the field value, you can create a permission called Quantity, assign the permission to the role, and then assign the permission to the visible permissions (but not the editable permissions) for the **Quantity** field.

To use a permission as a method of providing authorization, perform the following tasks:

1.  Create a user-defined label to represent the permission. See [Add a permission](#Add_a_permission).
2.  Assign the permission to roles that require it. Specifically, you use the Roles page, **Option Types** field to view and assign permissions for the role. See [Add or modify a role](roles.md).
3.  Assign the permission to the field configuration that you want to restrict. Specifically, you use the Field Configuration page **Authorization** tab to assign the permission to either the **Visible Permissions** or **Editable Permissions** field, or to both. See [Add or modify a field configuration](../../extensions/field-editor.md).

## Add a permission

1.  Select **System Administrator > Authorization > Permissions**.
    
2.  Perform one of the following tasks:
    -   To add a permission, click **Add**.
    -   To copy a permission, in the grid, select the check box next to the permission, and then click **Copy**.
3.  In the **Permission Name** field, enter a name for the permission.
4.  Under **Permission Category**, select **Field**.
    
    **Note**: A field permission type is the only permission that can be assigned at this time.
    
5.  Click **Save**.
6.  To assign a permission to roles, continue with [Add or modify a role](roles.md).

## Delete a field permission

If you delete a permission and a user is currently logged into the application using a role that is assigned the permission, the user remains logged in and can complete tasks related to any currently displayed pages. However, the user will not be able to access functionality that was authorized by the deleted permission.

1.  Select **System Administrator > Authorization > Permissions**.
    
2.  In the grid, select the check box next to the permission.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**. The permission is automatically unassigned from any roles to which it was assigned.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
