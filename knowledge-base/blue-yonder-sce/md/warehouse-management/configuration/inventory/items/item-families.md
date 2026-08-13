---
title: "Item Families"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/item_families.htm"
source: "/content/item_families.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inventory"
  - "Items"
  - "Item Families"
sections:
  - "Add or modify an item family"
  - "Delete an item family"
  - "Item Family fields"
images: []
source_sha1: 7bf2bb6bdeba1cd935fe6ceeb3f150d294893e78
---
# Item Families

An item family is a group of similar items, typically with the same material handling characteristics.

You can use item families to configure the application to process storage and allocation in the following ways:

-   Store items belonging to the same item family in specific zones or locations in the facility.
-   Allocate or reserve inventory for orders from specific zones based on the item family to which the inventory belongs.

You can also use item families to segregate inventory based on attributes such as temperature requirements, security, hazardous risk, non-standard size, or composition. For example, a warehouse stores wide, flat sheets of plastic, and a storage zone consisting of wide shelves was constructed to hold the sheets of plastic. There are four different items defined for the plastic, each one corresponding to the thickness of the plastic. The warehouse could define an item family of Plastic Sheets, and assign the four items to that family. The warehouse could then define and reserve locations in the storage zone exclusively for the Plastic Sheets item family.

You can also use item families to load pallets of inventory in specific item families in a specific order.

## Add or modify an item family

1.  Select **Configuration > Inventory > Items > Item Families**.
2.  Perform one of the following tasks:
    -   To add an item family, click **Add.**
    -   To modify an item family, in the grid, click the item family.
    -   To copy an item family, select the check box next to the item family, and then click **Copy**.
3.  Enter information in the [Item Family fields](#Item_Family_fields).
4.  Click **Save**.

## Delete an item family

1.  Select **Configuration > Inventory > Items > Item Families**.
2.  In the grid, select the check box of the item family to delete.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Item Family fields

 
| Field | Description |
| --- | --- |
| Item Family | Identifier used to group similar items together. Typically, all of the items within a family have the same material handling characteristics. |
| Description | Text that further describes the item family. |
| Item Family Group | Name used to group similar item families together. Typically, all of the item families within a group have the same material handling characteristics. Item family groups can be used for sorting and reporting purposes, and as criteria, for example, for storage paths and work assignment rules. |
| Break Stop Sequence Code | Name of the method that is used determine whether the stop sequence order for loading this item can be broken, and if so, how it can be broken.<br>-   • **Acceptable to ignore the Stop Sequence Order**: Pallets of the item family are loaded whenever they are ready to be loaded as long as all other pallets that must go on the front of the transport equipment (item families with a Break Stop Sequence Code of Force Break of Stop Sequence to Front of Trailer) have been loaded first.
<br>-   • **Force Break of Stop Sequence to Back of Trailer**: Pallets of the item family are loaded on the back of the transport equipment, regardless of stop sequence order.
<br>-   • **Force Break of Stop Sequence to Front of Trailer**: Pallets of the item family are loaded on the front of the transport equipment, regardless of stop sequence order.
<br>-   • **Respect the Stop Sequence Order**: Pallets of the item family are loaded in stop sequence order.
<br > If you do not specify a Break Stop Sequence Code for the item family, the application directs pallets of inventory in the item family to be loaded before inventory with a break stop sequence code of Force Break of Stop Sequence to Back of Trailer. |
| Pallet Rounding Threshold Percentage for Overshipment | Number representing the percentage of a pallet at and over which the application rounds up the ordered quantity to a full pallet.<br > For example, if the order quantity is 80, the Pallet Rounding Threshold Percentage is 60, and the full pallet quantity is 100, then the application allocates a full pallet, because 80 is greater than 60% of 100.<br > However, if the full pallet quantity is 150, then the application does not round up to the full pallet quantity because 80 is less than 90 (60% of 150). |
| Work Release Sequence | Number that determines the sequence in which locked pick work in the work queue is unlocked and becomes available for a user to perform. The sequence number is in relation to other item families that have a work release sequence defined.<br > The sequence is ordered from the lowest number to the highest (for example 1, 2, 3, and so on). When pick work for an item family is unlocked, it must be picked and deposited to ship staging before the next sequential pick work is unlocked. The base sequence for any item family is defaulted to 999999999 (also the maximum number allowed).<br > This field is only available if outbound work sequencing is enabled and the Work Release Type includes item family. See [Outbound work sequencing](../../outbound/shipping/outbound-staging.md). |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
