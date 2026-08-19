---
title: "Users"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/admin/users.htm"
source: "/content/admin/users.htm"
toc_path:
  - "Administration"
  - "System Administrator"
  - "Authorization"
  - "Users"
sections:
  - "User authentication"
  - "Add or modify a user"
  - "Define the Warehouse Management settings for a user"
  - "Delete a user"
  - "User fields"
  - "Address fields"
images: []
source_sha1: 8d73714d8d23da1d9a8270000d2c13b0b3bd0063
---
# Users

A user is someone who accesses the application. Every user must be identified in the application with a user account and assigned to one or more roles. When a user logs in, the application builds a list of the functions that the user can access based on the user account settings. Any changes made to the available roles for a user account do not take effect until the next time the user logs in.

You use the Users page to maintain users, including the settings used to provide user authentication and authorization.

-   For user authentication, you define authentication settings to provide access to the web client, SCE client, and RF and mobile devices. See [User authentication](#User_authentication).
-   For user authorization, you assign roles to users to control the web client functionality to which each user has access. In addition, the System User role must be assigned to each user that you want to authorize to work in the web client. See [Setup tasks for web client authorization](../authorization.md).

Depending on your installation configuration, the process to maintain users and roles may vary. See [Maintain users and roles based on installation configuration](../authorization.md).

## User authentication

User authentication is the process of validating the identity of a user for access to an SCE application. The SCE applications support the following types of user authentication:

-   **Application based**: Relies on the SCE application to validate the identity of a user using a password stored in a database. This method is also referred to as internal or native authentication, as it provides authentication in the application using passwords stored in the application database.
-   **Lightweight Directory Access Protocol (LDAP) based**: Relies on an external LDAP server to validate the identity of a user. This method is an external authentication method that provides access through configuration on the application server instance.
-   **OpenID Connect (OIDC) based**: Relies on a customer's external Identity Provider (IdP) using OIDC to validate the identity of a user. When configured as an external authentication method, OIDC authenticates a user for a portal server or classic web client, an SCE client, a WMS Mobile device, public APIs, and the gRPC server. This method can be combined with application-based authentication so that a user can use the same user account to also access the application through an RF device.
-   **PingFederate based**: Relies on a PingFederate integration with a customer's external IdP to validate the identity of a user. When configured as an external authentication method, PingFederate authenticates a user for the portal server web client only. This method can be combined with application-based authentication so that a user can use the same user account to also access the application through an SCE client, classic web client, and RF and WMS Mobile devices.

For information about configuring SCE application or portal server instances to support LDAP, OIDC, or PingFederate-based authentication, see the _Supply Chain Execution Applications Administrator Guide_.

## Add or modify a user

1.  Select **System Administrator > Authorization > Users**.
    
2.  Perform one of the following tasks:
    -   To add a user, click **Add**.
    -   To modify a user, in the grid, click the user.
    -   To copy a user, in the grid, select the check box next to the user, and then click **Copy**.
3.  Enter information in the [User fields](#User_fields).
4.  To maintain the user's address information:
    1.  Click **Address**.
    2.  Enter information in the [Address fields](#Address_fields).
    3.  Click **Apply**.
5.  To assign the user to one or more roles:
    
    **Notes**:
    
    -   A role defines the options to which the user has access. If the user is not assigned to a role, the user would have not have access to any functionality.
    -   A super user can assign all roles to other users. Only a super user can assign roles to another super user. A non-super user can assign roles to another user if all of the user's role options are available to the non-super user. For example, a user A can assign roles to another user B if all roles assigned to user B are assignable by user A. If user B has some roles assigned by another user C that cannot be assigned by user A, then user A cannot assign any roles to user B, and the option to assign roles is disabled.
    
    1.  Click **Roles**.
    2.  In the **Available Roles** column, select the check box next to the roles that apply.
        
        **IMPORTANT**:
        
        -   All web client users must be assigned to the System User role. The role is distributed with the application and authorizes a user to work in the web client user interface.
        -   All API users must be assigned to the Base API role. This role is distributed with the application and authorizes a user to make basic API requests.
        -   For efficient system performance, do not assign more than 25 roles to a single user. The application validates user authorization for each web client role option. Exceeding this number of assigned roles can cause errors when the system tries to validate user permissions.
        
    3.  Click **Apply**.
6.  To add or modify the user's Profile Picture image, see [Manage a media file association](../../../get-started/media.md).
7.  To specify the client groups to which the user has access:
    
    **Note**: When you specify one or more client groups, the user's access is limited only to those selected clients.
    
    1.  Click **Client Groups**.
    2.  In the **Available Client Groups** column, select the check box next to the client groups that apply.
    3.  Click **Apply**.
8.  To define Warehouse Management settings, see [Define the Warehouse Management settings for a user](#Define_the_Warehouse_Management_settings_for_a_user).
9.  Click **Save**.

## Define the Warehouse Management settings for a user

You use the Warehouse Settings page (accessed from the **Warehouse Management** button on the Users page) to maintain user account settings that are specific to Warehouse Management users. Specifically, you can define general warehouse settings, including whether count back is required for the user, whether to set or change a password for a voice device, which warehouses the user has permission to access, and which work operations the user has permission to perform.

1.  To select the user for which you want to define or modify warehouse management authorization:
    1.  Select **System Administrator > Authorization > Users**.
        
    2.  In the grid, click the user.
2.  Click **Warehouse Management**.
3.  To specify general warehouse settings:
    1.  Select the **General** tab.
    2.  Enter information in the following fields:
        
        | Field | Description |
        | --- | --- |
        | **Count Back Enable Code** | Count back setting that is applied to the user account. Count back is a picking verification task that requires an operator to capture the quantity of inventory that is left behind on the pallet or in the location in addition to the quantity of inventory being picked. This task applies when the operator is picking less than a full pallet from a location. If the remaining quantity the operator enters does not match the expected quantity, a count is generated. If the operator is authorized to do the count, the application prompts the operator to complete the count. Otherwise, the operator must wait for a supervisor to resolve the discrepancy using an audit count.<br>-   • **Perform count back if item or location requires**: The user is only prompted to perform a count back when picking an item or from a location that requires a count back.
        <br>-   • **Always perform count back**: The user is always prompted to perform a count back when picking, regardless of whether the item or location requires it.
        <br>-   • **Never perform count back**: The user is never prompted to perform a count back when picking, regardless of whether the item or location requires it. |
        | **Set/Change Voice Pin** | If Yes, the user's personal identification number (PIN) password to log in to a voice device is set to the value entered in the **Password** field. Setting this field to Yes enables the **Password** field.<br > If No, the PIN password is set to the password defined on the user account.<br > **Note**: The voice system cannot validate complex passwords. If you select No and the user password includes both upper and lower case letters, special characters, or is lengthy, the system cannot validate the user. In cases where the user password is complex, select Yes to assign a simple voice PIN password. |
        |  **Password** | A numerical value that the user can speak to log in to a voice device. The password must be 10 characters or less and only use numbers 0 to 9. Available if **Set/Change Voice Pin** is set to Yes. |
        
    3.  Click **Apply**.
4.  To specify which warehouses the user can access:
    1.  Select the **User Warehouse** tab.
        
    2.  To grant a user permission access to all available warehouses, set the **Enterprise User** field to Yes.
    3.  To select warehouses the user has permission to access:
        1.  Set the **Enterprise User** field to No.
        2.  In the **Available Warehouses** column, select the check box next to the warehouses that apply.
        3.  To select the warehouse that is displayed when the user logs in to the application, in the **Selected Warehouses** column, select the **Set Default Warehouse** option next to the warehouse name.
        4.  Click **Apply**. A confirmation message is displayed.
        5.  Click **OK**.
5.  To specify the work operations the users has permission to perform:
    1.  Select the **Authorized Directed Work** tab.
    2.  In the **Available Operations** column, select the check box next to the work operations that apply. A work operation is a defined work activity (such as receiving, picking, or counting) performed by an operator using an RF or voice device.
    3.  Click **Apply**. A confirmation message is displayed.
    4.  Click **OK**.
6.  Navigate to the previously viewed User page clicking the <User Name > link in the navigation trail, and then click **Save**.
    
    **IMPORTANT**: If you do not click **Save** on the User page, the changes are not saved.
    

## Delete a user

Deleting a user removes the user information from the database. If access to functionality is required at a later date, the user must be added again. As an alternative, you can temporarily disable a user's access to functionality by updating the user's status to inactive.

1.  Select **System Administrator > Authorization > Users**.
    
2.  Select the check box next to the user.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## User fields

 
| Field | Description |
| --- | --- |
| **User** | Unique identifier for an individual who uses the application. |
| **Login** | Alternate identifier that can be used when logging in to the application in place of the identifier specified in the **User** field. You use this field to provide a shorter or more personal ID for a user to enter. The login is displayed on the user interface and in reports in place of the user ID.<br > The login is also used for PingFederate-based authentication as an attribute on the customer's IdP user account. |
| **Business Analysis for Warehouse User** | Identifier that authenticates the user’s access to Warehouse Management data that is displayed on Business Analysis for Warehouse dashboards. This field is required for all Business Analysis for Warehouse users.<br>-   • If separate Lightweight Directory Access Protocol (LDAP) servers are used by Warehouse Management and Business Analysis for Warehouse, or if Warehouse Management does not use an LDAP server, the identifier must be the same as the user's IBM Cognos user ID used to access Business Analysis for Warehouse.
<br>-   • If Warehouse Management and Business Analysis for Warehouse use the same LDAP server, the identifier must be the same as the user's identifier specified in the LDAP server configuration. |
| **Honorific** | Title, such as Mr., Mrs., or Dr., of the user. |
| First Name | First name of the user. |
| Last Name | Last name of the user. |
| Locale | Identifier that determines which language and language attributes (such as date and time formats) apply to the user and are displayed on the user interface and in reports. The locale for a user and a warehouse address (including locale) are required attributes, and the application displays content based on the user's locale configuration. |
| Client | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse.<br > **Note**: You specify one or more clients to restrict the client information to which the user has access. |
| Super User | If Yes, the user is identified as a super user. A super user has more privileges than other users to perform operations such as adding, copying, or deleting other super users. The appropriate roles must still be assigned to the user to access the application and menus. For example, a super user can access the System Administrator menu only if the Super role is assigned. A super user can log in to the application only if a role is assigned. This field is available only to a super user.<br > If No, the user is not identified as a super user.<br > **Note**: If the Super role is selected for a user and this field is set to No, then the user can access the System Administrator menu and perform operations other than adding, copying, or deleting another super user. |
| Profile Picture | Media tool that displays the image that is associated with the entity. If an image has not been associated with the entity, a default image is displayed. You can view an enlarged version of the image and, depending on the settings, you can add, change, or remove the associated image file. See [Manage a media file association](../../../get-started/media.md). |
| Account Status | Current status of the user. This field determines the user's ability to access the application.<br>-   • **Active**: User account that has access to the application.
<br>-   • **Inactive**: User account that is temporarily disabled.
<br>-   • **Expired**: User account that has expired as configured by the date in the **Expiration Date** field. |
| Account Expiration | If Yes, the user’s access to the application expires on the date specified in the **Expiration Date** field. On the expiration date, the user can no longer successfully log in to the application.<br > If No, the user's access to the application does not expire. |
| Expiration Date | Date on which the user's access to the application is set to expire so that the user can no longer successfully log in. This field is only available if the **Account Expiration** field is set to Yes. |
| External Authentication | If Yes, the application only validates the user's ability to access the working environment using an external method, such as a Lightweight Directory Access Protocol (LDAP), OpenID Connect (OIDC), or PingFederate authentication.<br > If this field is set to Yes, the **Password Expiration**, **Reset Password on Next Login**, **Password**, and **Confirm Password** are not available because they are not required when external authentication is enabled.<br>
**Notes**:

<br>

-   • OIDC authentication does not provide user access through an RF device.
<br>-   • PingFederate authentication only provides user access through a portal server web client.
<br>

<br > If No, the application validates the user's ability to access the working environment using a password. OIDC or PingFederate authentication can also be defined to separately authenticate a user. |
| Password Expiration | If Yes, the user's password expires on regularly scheduled intervals. Select Yes to force the user to change the password on a regular basis.<br > If No, the user's password does not expire.<br > This field is not available when the **External Authentication** field is set to Yes. |
| Reset Password on Next Login | If Yes, the user must change the password for the account the next time the user logs in to the application.<br > If No, the user is not required to change the password the next time the user logs in to the application.<br > This field is not available when the **External Authentication** field is set to Yes. |
| Password | User-maintained code that the user enters to gain access to the application. Available when creating a new user account and the **External Authentication** field is set to No. |
| Confirm Password | User-maintained code that was entered into the **Password** field is re-entered in this field. Available when creating a new user account and the **External Authentication** field is set to No. |
| OpenID Connect Subject | External identifier used to authenticate this user with an OpenID Connect provider. This value must match the subject claim in the OpenID Connect provider identity token. This field is required if an OpenID Connect provider is integrated with the application to manage this user's authentication for access through the portal server or classic web client, SCE client, or WMS Mobile device. |
| Authorization Group | Not currently used. |

## Address fields

 
| Field | Description |
| --- | --- |
| **Address Line 1** | Line one for the address. This is the physical address information (such as house, building or PO box numbers, street names, or suite or floor numbers). |
| **Address Line 2** | Line two for the address. |
| **Address Line 3** | Line three for the address. |
| **Country** | Name or code name of the country. |
| State | State for the address. |
| City | City for the address. |
| Postal Code | Postal code for the address. |
| Region | Geographical region within the country for the address. This information is optional. |
| Address District | Postal district for the address. This information is typically used outside of the United States. |
| Residential Address | If Yes, the address represents a residence.<br > If No, the address does not represent a residence. |
| Temporary | If Yes, the address is temporary.<br > If No, the address is permanent. |
| P.O. Box Address | If Yes, the address is a post office box.<br > If No, the address is a physical address. |
| Phone | Phone number, including area and country code (if applicable), of the individual or organization associated with the address. |
| Fax | Facsimile number, including area and country code (if applicable), of the individual or organization associated with the address. |
| Web Address | URL for the internet site of the individual or organization associated with the address. |
| Email Address | Address at which the individual or organization associated with the address receives electronic mail. For example: [\[email protected\]](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/admin/cdn-cgi/l/email-protection) |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
