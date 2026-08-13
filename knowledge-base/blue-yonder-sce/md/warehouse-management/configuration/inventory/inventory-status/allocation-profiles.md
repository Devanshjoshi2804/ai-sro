---
title: "Allocation Profiles"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/allocation_profiles.htm"
source: "/content/allocation_profiles.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inventory"
  - "Inventory Status"
  - "Allocation Profiles"
sections:
  - "How allocation profiles work"
  - "Add or modify an allocation profile"
  - "Delete an allocation profile"
images: []
source_sha1: de982ef578aa0dbdf8c7c2fbeb16004f4d4c1e19
---
# Allocation Profiles

An allocation profile is a series of inventory statuses that defines the levels of quality at which a customer is willing to accept inventory. When an allocation profile is specified for an order, then the application can select inventory to satisfy that order based on a prioritized list of acceptable inventory statuses rather than a single status. This functionality provides your customers with the ability to define a wider range of acceptable inventory, as well as specify their preference on the quality of the inventory that they are willing to accept.

When you configure an allocation profile, you select the inventory statuses to include, the priority in which they should be allocated, and whether inventory in each status is allowed to be shipped. Allocation profiles can be applied to both date-controlled and non date-controlled inventory.

After allocation profiles are configured, you can assign an allocation profile to an order line, work order line, or bill of materials line.

An allocation profile can also be assigned to a customer or customer type. This is done so that if an allocation profile is not specified on an order line, the application can use the profile specified for the customer or, if not specified for the customer, the customer type. See [Existing Customers](../../partners/customers/existing-customers.md) and [Customer Types](../../partners/customers/customer-types.md).

## How allocation profiles work

The application uses the following process to select inventory based on an allocation profile:

1.  During allocation of shippable orders, the application uses the allocation profile specified for the order line. If not found, it uses the allocation profile specified for the ship-to customer. If not found, it uses the allocation profile defined for the ship-to customer type.
    
    **Note**: During allocation of internal orders, the application uses the allocation profile specified for the work order line or bill of materials line.
    
2.  The application attempts to allocate inventory with the highest status in the profile (defined with a priority of 1). If sufficient inventory does not exist for that status, the application attempts to allocate inventory from each subsequent status in the profile until it has fulfilled the order line.
3.  Allocated inventory is picked and staged.
4.  Prior to shipping, the application checks the status of inventory, and prevents shipping if the inventory status does not allow shipping (based on the allocation profile configuration).

## Add or modify an allocation profile

1.  Select **Configuration > Inventory > Inventory Status > Allocation Profiles**.
2.  Perform one of the following tasks:
    -   To add an allocation profile:
        1.  Click **Add**.
        2.  In the **Name** and **Description** fields, enter the values.
    -   To modify an allocation profile, in the grid, click the profile name.
    -   To copy an allocation profile:
        1.  In the grid, select the check box next to the profile, and then click **Copy**.
        2.  In the **Name** and **Description** fields, enter the values, and then click **Apply**.
        3.  In the grid, click the profile name.
3.  Under **ALLOCATION DETAILS**, configure inventory statuses for the allocation profile:
    1.  Perform one of the following tasks:
        -   To add a new status, click **Add**.
        -   To modify details for a status, in the grid, click the status.
    2.  Enter information in the following fields:
        
        | Field | Description |
        | --- | --- |
        | Allow Shipping | If Yes, inventory with this status can be shipped.<br > If No, inventory with this status cannot be shipped. |
        | Allow Allocation | If Yes, inventory with this status can be allocated.<br > If No, inventory with this status is not considered for allocation. |
        | Inventory Status | Defines the acceptable quality or disposition of the inventory that can be allocated. |
        
    3.  Click **Save**.
    4.  To adjust the priority of the acceptable statuses, in the grid, click and drag the status to a different position. The application evaluates the statuses in the order that they are listed in the grid, starting with priority 1. Priority of 1 is the highest level quality that the customer is willing to accept inventory.
    5.  To delete a status from the grid:
        1.  Select the check box next to the priority, and then click **Delete**. A confirmation message is displayed.
        2.  Click **OK**.
4.  Click **Save**.

## Delete an allocation profile

1.  Select **Configuration > Inventory > Inventory Status > Allocation Profiles**.
2.  In the grid, select the check box next to the profile to delete.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
