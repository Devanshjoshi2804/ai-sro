---
title: "Break Stop Sequence"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/break_stop_sequence.htm"
source: "/content/break_stop_sequence.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Outbound"
  - "Shipping "
  - "Break Stop Sequence"
sections:
  - "Examples: When to break stop sequence"
  - "Break stop sequence scenarios"
  - "Add or modify a break stop sequence code"
  - "Delete a break stop sequence code"
images: []
source_sha1: 34bf5e4a0d2497a22da894c14f1783dfe73136a5
---
# Break Stop Sequence

A break stop sequence code defines whether the stop sequence is respected when loading inventory on transport equipment. For example, it may be necessary to break the stop sequence in order to load inventory of the same item family together, even though the inventory is assigned to different stops. The break stop sequence code assigned to an item family determines how inventory for an item family is loaded with respect to stop sequence. See [Add or modify an item family](../../inventory/items/item-families.md).

**Note**: If you do not specify a break stop sequence code for a particular item family, the application defaults to Respect the Stop Sequence Order (RSPCT) for that inventory.

However, if a load has the **Ignore Stop Sequence** field set to Yes, then the inventory for all of its stops can be loaded in any sequence. This setting overrides break stop sequence codes that would otherwise apply to inventory on the load. See [Add a load](../../../outbound-planner/outbound/procedures-for-loads.md).

You can use standard break stop sequence codes to achieve the following results:

-   Force inventory to be loaded out of stop sequence at the front of the trailer.
-   Force inventory to be loaded out of stop sequence at the end of the trailer.
-   Force inventory to respect the stop sequence.
-   Ignore stop sequence order and allow inventory to be loaded immediately, as long as the other inventory is loaded, according to its break stop sequence code.

### Examples: When to break stop sequence

In the grocery industry, frozen goods may be stored in a separate building from dry goods. If multiple stops on a load require both frozen and dry goods, the trailer stops at building A to load the frozen goods first, and then goes to building B to load the dry goods. In this scenario, it may be necessary to break the stop sequence loading for the frozen goods, but maintain the stop sequence for dry goods.

In other industries, it may be necessary to load bulky material (such has heavy pipes) at the end of the trailer. In those cases, it may be necessary to break the stop sequence order for the bulky material, but maintain the stop sequence order for all other inventory.

### Break stop sequence scenarios

The following scenarios explain how the application handles the different break stop sequence codes when loading inventory on a trailer:

-   If the break stop sequence code is set to **Force Break of Stop Sequence to Front of Trailer (FBFRONT)**, then this inventory is loaded first.
-   If the break stop sequence code is set to **Acceptable to ignore the Stop Sequence Order (IGNR)**, then this inventory can be loaded after loading inventory that has an FBFRONT code.
-   If the break stop sequence code is set to **Respect the Stop Sequence Order (RSPCT)**, then you can load inventory for the lowest uncompleted stop sequence after loading inventory that has an FBFRONT code.
-   If the break stop sequence code is set to **Force Break of Stop Sequence to Back of Trailer (FBBACK)**, then you can load the inventory after loading inventory that has any other break stop sequence code.
-   If the break stop sequence code is set to a user-defined code, such as FBSECOND or FBTHIRD, then you can load the inventory in the order defined for the code (Sequence Number).
-   If the inventory's item family has no break stop sequence code defined, then it must be loaded before inventory with a break stop sequence code of FBBACK.
-   If an LPN contains multiple item families that have different break stop sequence codes, then you must split the LPN manually, and then load the inventory according to its break stop sequence codes.

## Add or modify a break stop sequence code

**IMPORTANT**: You cannot modify the following break stop sequence codes: IGNR, RSPCT, FBBACK, or FBFRONT.

1.  Select **Configuration > Outbound > Shipping > Break Stop Sequence**.
2.  Perform one of the following tasks:
    -   To add a break stop sequence code, from the **Actions** drop-down list, select **Add**.
    -   To modify a break stop sequence code, in the grid, select the check box next to the break stop sequence code to modify.
        
        **Note**: Some fields may not be available for modification.
        
3.  Enter information in the following fields:
    
     
    | Field | Description |
    | --- | --- |
    | Break Stop Sequence Code | Unique identifier for the break stop sequence code, such as FBSECOND or FBTHIRD. |
    | Description | Meaningful description for the break stop sequence code to explain the purpose of breaking the stop sequence order when loading a trailer. This description is displayed on the application windows when referring to this break stop sequence. |
    | Sequence Number | Number to represent the order in which you want the application to apply this break stop sequence code as compared to the other break stop sequence codes. For example, if you want the break stop sequence code to force inventory to be loaded after the FBFRONT inventory, enter 2. If you already have a break stop sequence code to force inventory to be loaded after the FBFRONT inventory and you want to define a break stop sequence code to force inventory to be loaded after that one, then enter 3. |
    
4.  Click **Save**. A confirmation message is displayed.
5.  Click **OK**.

## Delete a break stop sequence code

**IMPORTANT**: You cannot delete the following break stop sequence codes: IGNR, RSPCT, FBBACK, or FBFRONT. You also cannot delete a break stop sequence code that is currently associated with an item family.

1.  Select **Configuration > Outbound > Shipping > Break Stop Sequence**.
2.  In the grid, select the check box next to the break stop sequence code to delete.
3.  From the **Actions** drop-down list, select **Delete**. A confirmation message is displayed.
4.  Click **OK**.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
