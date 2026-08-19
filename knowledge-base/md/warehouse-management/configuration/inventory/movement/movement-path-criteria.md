---
title: "Movement Path Criteria"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/movement_path_criteria.htm"
source: "/content/movement_path_criteria.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inventory"
  - "Movement"
  - "Movement Path Criteria"
sections:
  - "Add or modify movement path criteria"
  - "Delete a movement path criteria"
images: []
source_sha1: 2f609f401fb2aa9aadfb9a947fa8ae5decdd3881
---
# Movement Path Criteria

Movement path criteria is a rule that defines one or more item, shipment, order, or order line attribute values associated with the inventory.

After a criteria definition is created, it can be assigned to a hop (intermediate stop) in a movement path to specify the attributes that inventory must have in order to be directed from a source zone to the hop. Only inventory that matches the criteria is directed to the hop to which the criteria is assigned.

If inventory from the movement path's source zone does not match the criteria for any hop in the movement path, it is directed to the destination zone. If a movement path has a hop to which no criteria is assigned, then all inventory from the source zone is directed to the hop. If a storage movement path has a hop with criteria that includes outbound attributes, then the hop is ignored and the inventory is directed to the destination zone.

The following example illustrates the configuration of movement path criteria and how it is used in a movement path. The following table shows an example of two criteria: CRT01, which specifies a value for a carrier (UPS); and CRT02, which specifies a value for a client (ClientA).

   
| Criteria | Category | Attribute | Value |
| --- | --- | --- | --- |
| CRT01 | Shipment | Carrier | UPS |
| CRT02 | Order Line | Client | ClientA |

The following table shows each criteria assigned to a hop (HOP1 or HOP2) in a movement path. Based on this assignment, inventory is processed in the following ways:

-   Inventory from source zone SA1 that is associated with UPS, but not ClientA, is directed to HOP1 and then to HOP3.
-   Inventory from source zone SA1 that is associated with ClientA, but not UPS, is directed to HOP2 and then to HOP3.
-   Inventory from source zone SA1 that is associated with both UPS and ClientA is directed to HOP1, to HOP2 and then to HOP3.
-   Inventory from source zone SA1 that is associated with neither UPS or ClientA is directed to HOP3.

**Note**: If criteria was assigned to each hop, and inventory from the source zone did not match the criteria in any hop sequence, the inventory would be directed to the destination zone directly.

    
| Source zone | Destination zone | Hop sequence | Hop | Criteria |
| --- | --- | --- | --- | --- |
| SA1 | DA1 | 1 | HOP1 | CRT01 |
| SA1 | DA1 | 2 | HOP2 | CRT02 |
| SA1 | DA1 | 3 | HOP3 | n/a |

## Add or modify movement path criteria

1.  Select **Configuration > Inventory > Movement > Movement Path Criteria**.
2.  Perform one of the following tasks:
    -   To add movement path criteria, click **Add**.
    -   To modify movement path criteria, in the grid, click the movement path criteria.
    -   To copy movement path criteria, in the grid, select the check box next to the movement path criteria, and then click **Copy**.
3.  Enter information in the following fields:
    
     
    | Field | Description |
    | --- | --- |
    | Criteria | Identifier or name of the criteria definition. |
    | Description | Meaningful description for the criteria. The description assists the user in identifying the criteria when they assign it to a hop. |
    
4.  To define the criteria that is used for the movement path:
    1.  Under **Criteria Definition**, click **Expression**.
    2.  Select an entity that has the attribute to use, such as **Shipment**.
    3.  Select the attribute to use, such as **Warehouse**.
    4.  Select the qualifier to use, such as "**\=**".
    5.  Select the value to use, such as **WMD1** (the name of the warehouse).
    6.  To add additional rows of criteria:
        1.  Select the mathematical argument used to evaluate multiple rows of criteria.
            -   **Or**: Must match either group of the defined criteria.
            -   **And**: Must match both groups of the defined criteria.
            -   **(**: Opening argument used to group criteria together.
            -   **)**: Closing argument used to group criteria together.
                
                **Note**: Other operators that represent a combination of these arguments, such as ")And(" are also available. The operator determines how the application evaluates the criteria. For example, if you have two criteria lines connected with the operator "And", that means the inventory must match both attributes to meet the criteria. If the two lines are connected with the operator "Or", the inventory only has to match one of the field values to meet the criteria.
                
        2.  Click **Expression**, and define its criteria.
5.  Click **Save**.

## Delete a movement path criteria

1.  Select **Configuration > Inventory > Movement > Movement Path Criteria**.
2.  In the grid, select the check box next to the movement path criteria to delete.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
