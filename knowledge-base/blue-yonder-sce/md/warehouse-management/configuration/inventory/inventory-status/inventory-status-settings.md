---
title: "Inventory Status Settings"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/inventory_status_settings.htm"
source: "/content/inventory_status_settings.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inventory"
  - "Inventory Status"
  - "Inventory Status Settings"
sections:
  - "Configure inventory status settings"
images: []
source_sha1: 4e569278a30270badc6d660751dce0cb55720eed
---
# Inventory Status Settings

You use inventory status settings to configure the following attributes:

-   Restrict inventory status changes by user role. When you enable inventory status change restrictions, the application prevents a user from changing the status of inventory unless the user's role is configured to do so. When you restrict inventory status changes, you specify which roles can perform inventory status change operations and the inventory statuses to and from which the role is allowed to change inventory. The restriction also applies to inventory status changes made to inventory on hold, but does not affect inventory status changes that take place as a result of an aging profile process or an integration transaction.
    
    If inventory status change restrictions is not enabled, then the application does not restrict inventory status changes by role.
    
    **IMPORTANT**: If inventory status change restrictions are enabled, then new roles that are added to the application after restrictions are enabled will not automatically be allowed to perform inventory status changes. To allow those roles to make changes, you must configure each role with the inventory statuses it is allowed to change.
    
-   Select the inventory statuses, by pick zone, that are not eligible for picking. When inventory in a location in the zone changes to an inventory status that is not eligible for picking (such as the Damaged status), the application locks the location by placing it in the Inventory Error status. An inventory status change can occur as a result of a manual change or as a result of an aging profile assigned to date tracked inventory that changes the status automatically.
    
    You may want the application to lock a location, for example, when inventory in a location changes to an inventory status that disallows shipping. When a location is locked, the application prevents inventory activities (such as storage, allocation, and picking) from taking place at the location. Any inventory activity at the location that was defined prior to the location being locked can be completed, but no new activity is created.
    

## Configure inventory status settings

1.  Select **Configuration > Inventory > Inventory Status > Inventory Status Settings**.
2.  To specify which roles can perform inventory status change operations and the inventory statuses to and from which the role is allowed to change inventory:
    1.  Set **Enable Restrictions** to **Yes**. The **Inventory Status Change Permissions** field becomes available so that you can select role restrictions.
    2.  Click **Inventory Status Change Permissions**.
    3.  Perform one of the following tasks:
        -   To add a role restriction, click **Add**.
        -   To modify a role restriction, in the grid, click the role.
        -   To copy a role restriction, in the grid, select the check box next to the role, and then click **Copy**.
    4.  From the **Role** drop-down list, select a role.
    5.  To add a permission:
        1.  Click **Add**.
        2.  Enter information in the following fields:
            
            | Field | Description |
            | --- | --- |
            | From Inventory Status | Inventory status from which the role is allowed to change the status of inventory. |
            | To Inventory Status | Inventory status to which the role is allowed to change the status of inventory. |
            
        3.  Click **Apply**.
    6.  To modify a permission, in the grid, click the row to modify, and then change the field information.
    7.  To delete a permission:
        1.  In the grid, select the check box next to the permission to delete.
        2.  Click **Delete**. A confirmation message is displayed.
        3.  Click **OK**.
3.  To define the inventory statuses that are not eligible for picking, by pick zone:
    1.  Click **Error Locations by Inventory Status**.
    2.  Perform one of the following tasks:
        -   To add an ineligible inventory status for a pick zone, click **Add**.
        -   To modify an ineligible inventory status for a pick zone, in the grid, click the pick zone.
        -   To copy an ineligible inventory status for a pick zone, in the grid, select the check box next to the pick zone, and then click **Copy**.
    3.  From the **Pick Zone** drop-down list, select a pick zone.
    4.  In the **Available** column, select the inventory statuses that are not eligible for picking.
    5.  Click **Apply**.
    6.  To delete a pick zone status configuration:
        1.  In the grid, select the check box next to the pick zone to delete.
        2.  Click **Delete**. A confirmation message is displayed.
        3.  Click **OK**.
4.  Click **Save**.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
