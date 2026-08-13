---
title: "Item Hierarchy Setup"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/item_hierarchy_setup.htm"
source: "/content/item_hierarchy_setup.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inventory"
  - "Items"
  - "Item Hierarchy Setup"
sections:
  - "Example: Item hierarchy"
  - "Set up an item hierarchy"
images: []
source_sha1: be369d1f3e5e873beb1084fce41327ac03b15d61
---
# Item Hierarchy Setup

An item hierarchy represents a hierarchical set of attributes for the items that a facility maintains. It is used to categorize, group, and associate attributes to items so that items can be stored, allocated, and shipped based on those categories and attributes.

The item hierarchy configuration supports up to seven levels. You can assign a name to each level that you use. If you use an item hierarchy, the first level is required and the remaining levels are optional.

You can perform the following tasks related to item hierarchies:

-   Import an item hierarchy for use in the warehouse
-   Enter a description for each level of the hierarchy that you use
-   Assign the first hierarchy level to an item for the purpose of assigning its attributes to the item
-   Use hierarchy level attributes as selection criteria for inbound workflows, storage search paths, work assignments, allocation search paths, replenishment search paths, and resource codes
-   Use hierarchy level attributes as search criteria to find inventory and inbound shipments

**Note**: Hierarchy information can only be added to the application through integration transactions from the host.

## Example: Item hierarchy

The following table illustrates an item hierarchy that represents the way a facility may categorize their inventory.

**Note**: For most implementations, attributes are coded (such as with numeric or alphanumeric values), but for clarity, this example uses descriptive terms.

  
| Level | Name | Example attributes |
| --- | --- | --- |
| Level 1 | Sub-class | Plain, Embroidered, Printed |
| Level 2 | Class | Solid, Patterned, Plaid |
| Level 3 | Segment | Casual, Sports, Designer |
| Level 4 | Model | High End, Moderate, Budget |
| Level 5 | Type | Shirt, Blouse, Dress Shirt |
| Level 6 | Line | Men's, Women's, Children's |
| Level 7 | Category | Clothing, Electronics, Housewares |

The following examples represent how the hierarchy can apply to single items:

-   Clothing - Men's - Dress Shirt - High End- Designer - Solid - Plain
-   Clothing - Children's - Shirt - Budget - Sports - Patterned - Printed
-   Clothing - Women's - Blouse - Moderate - Casual - Plaid - Embroidered

## Set up an item hierarchy

An item hierarchy can consist of up to seven levels. You can enter a description for each level of the item hierarchy that you use. You should start with Level 1 and then define any other levels you want to use. Leave the description blank for the levels that you do not use.

1.  Select **Configuration > Inventory > Items > Item Hierarchy Setup**.
2.  In the grid, under **Column**, click the hierarchy level to define.
3.  In the **Description** field, enter the name of the hierarchy level.
4.  Click **Save**.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
