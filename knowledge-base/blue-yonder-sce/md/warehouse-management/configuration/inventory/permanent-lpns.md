---
title: "Permanent LPNs"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/permanent_lpns.htm"
source: "/content/permanent_lpns.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inventory"
  - "Permanent LPNs"
sections:
  - "Add or modify a permanent LPN"
  - "Delete a permanent LPN"
images: []
source_sha1: e31b3bebd5000eacc15586499af86dc27c7c0c3c
---
# Permanent LPNs

A permanent LPN is a location used to hold inventory before it is moved to a final putaway location. Permanent LPNs primarily serve as temporary storage locations for inventory that has yet to be moved to a final putaway location. This enables you to track inventory at each stage as it moves throughout your facility.

For example, you can assign a permanent LPN to a pallet that is kept next to a receiving dock door. Cases that are placed on this pallet as you receive them can be tracked to this location. This can decrease the time it takes to locate a specific case that contains items needed to complete a work order. This case can be split from the LPN that you are receiving and then cross-docked to the appropriate location to complete the work order. The normal receiving, storage, and picking procedures can be bypassed.

## Add or modify a permanent LPN

You can add or modify a permanent LPN location to hold inventory before it is moved to a final putaway location.

1.  Select **Configuration > Inventory > Permanent LPNs**.
2.  Perform one of the following tasks:

-   To add a permanent LPN, from the **Actions** drop-down list, select **Add**.
-   To add a permanent LPN using the copy feature, select the check box next to the LPN, and then from the **Actions** drop-down list, select **Copy**.
-   To modify a permanent LPN, select the check box next to the LPN, and then from the **Actions** drop-down list, select **Edit**.

4.  Enter information in the following fields:
    
     
    | Field | Description |
    | --- | --- |
    | LPN | Identifier for the permanent LPN. |
    | Warehouse ID | Identifier for the warehouse in which the permanent LPN is used and stored. |
    | Storage Location | Storage location for the permanent LPN. |
    | Home Location | Location in your facility to which a permanent LPN is returned once it is empty or no longer in use. For example, if a cart is used to carry inventory to a putaway location, you can specify the home location of the cart; that is, where the cart is to be returned when the putaway task is complete. |
    | Moveable LPN | Indicates that the permanent LPN can be moved across the facility and transferred to another location. If deselected, indicates that although eaches and cases can be transferred out of the LPN to another location, the permanent LPN itself cannot be transferred to another location or LPN. |
    
5.  Click **Save**.

## Delete a permanent LPN

You cannot delete permanent LPN locations that are currently in use; that is, any locations that contain inventory or to which inventory is pending.

1.  Select **Configuration > Inventory > Permanent LPNs**.
2.  In the grid, select the check box next to the permanent LPN.
3.  From the **Actions** drop-down list, select **Delete**. A confirmation message is displayed.
4.  Click **Yes**.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
