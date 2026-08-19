---
title: "Item Classes"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/item_classes.htm"
source: "/content/item_classes.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inventory"
  - "Items"
  - "Item Classes"
sections:
  - "Add or modify an item class"
images: []
source_sha1: ec9947335a320429558bb869ff8786e7c7f29371
---
# Item Classes

An item class is a category you can create to group items for processing typically based on matching characteristics, such as hazardous or flammable material. When you create an item class, you assign a class name and a description, and then you can assign the item class to specific items in the warehouse. You can use the item class attribute as criteria for various processes.

**IMPORTANT**: Warehouse Management designation of hazardous materials related to this functionality in no way implies compliance with federal or international regulations pertaining to the storage, processing, and transport of such materials.

Specifically, you can use the item class attribute in the following warehouse processes: 

-   Configure the **Criteria Type** for an inbound, outbound, production, or background workflow with an item class. For example, you can create an inbound workflow for the FLAMMABLE item class so that whenever items in that class are received, the operator is prompted to perform a safety check. See [Warehouse Workflows](../../work/warehouse-workflows.md).
-   Configure storage and replenishment search paths with an item class. For example, assume a warehouse has storage zones for different item classes, such as TOXIC and FLAMMABLE, and that the classes must be stored in separate zones. You can configure one storage search path with the item class TOXIC as criteria and another search path with the item class FLAMMABLE. When items in either class are received in the source zone, the appropriate search path directs the items to the storage zone in their respective search path. See [Storage Search Paths](../../inbound/storage/storage-search-paths.md) and [Replenishment Search Paths](../replenishments/replenishment-search-paths.md).
-   Create a location preference rule using item class as one of the **Storage Options**. For example, assume two item classes, such as COMBUSTIBLE and FLAMMABLE, are stored in the same zone, but the FLAMMABLE class must always be stored in a specific range of locations with no other items. You can create a location preference rule that specifies the item class (**Storage Options** = Item Class; **Item Class** = FLAMMABLE) and the range of locations where only inventory in that class can be stored. A location preference rule can be used in conjunction with a storage search path; when a FLAMMABLE item is received, the storage search path for the class directs the inventory to the correct storage zone, and the location preference rule directs the FLAMMABLE inventory to the acceptable locations in the zone. See [Location Preference Rules](../../inbound/storage/location-preference-rules.md).
-   Configure allocation search paths for finding items by class. When you configure search paths, you can select one item class per search path, and you can then configure the search path rule with the pick zone for that class, and the LPN level and pick method used to pick that item class. See [Allocation Search Paths](../../outbound/allocation/allocation-search-paths.md).
-   Add work assignment rules using the item class in the following configurations. See [Work assignment rules](../../outbound/picking/work-assignments.md).
    -   **Selection Criteria**: Define the item class in the criteria expression, which determines which picks are included in a work assignment. For example, set the **Entity** to Item, **Column** to Item Class, and the define the specific item class as the **Value**.
    -   **Criteria Sequence**: Select Item Class from the available criteria sequence fields, which determines the order in which selected picks are sorted before being added to a work assignment. To define a specific sort order for item classes, you can name the item classes with a prefix used to sort in alphanumeric order. For example, assume there are three item classes that you want to sort in a specific order before they are added to a work assignment. You can name the item classes H1-FLAMMABLE, H2-COMBUSTIBLE, and H3-TOXIC, and then when you select Item Class as an attribute and sort in ascending order, the application sorts by the item classes by prefixes H1, H2, and H3 (rather than alphabetically COMBUSTIBLE, FLAMMABLE, TOXIC).
    -   **Pick Order**: Select Item Class from the available criteria sequence fields, which determines the order in which selected picks are listed on a work assignment. Similar to criteria sequence, if you name item classes with sequenced prefixes to accommodate sorting for certain processes, the application will use the ascending or descending prefix order rather than the names of the item classes without prefixes.
    -   **Break Value**: Define the capacity of a work assignment by the number of item classes the assignment can include. For example, set **Group Break Function** to Count, **Group Break Field** to Item Class, and then define the maximum quantity of classes allowed on a single work assignment.
-   Select Item Class as an outbound LPN mixing restriction to prevent mixed-class LPNs from being deposited in location types enabled to validate inventory mixing. See [LPN Mixing Restrictions](../../outbound/shipping/lpn-mixing-restrictions.md).
-   Select Item Class as an attribute for storage mixing restrictions to prevent mixing item classes within a pickable location as defined by warehouse, building, and storage zone. See [Storage Mixing Restrictions](../../inbound/storage/storage-mixing-restrictions.md).
-   Configure item class levels to determine the level at which an item class can be stored in relation to other item class levels. See [Item Class Levels](item-class-levels.md).

**Note**: The hazardous designation for an item (**Hazardous Material** field) and a configured item class for hazardous material that is assigned to an item are not associated with each other. The **Hazardous Material** field is an indicator that the item should be treated as hazardous, but it does not impact processing unless the attribute is used as criteria in configurations such as a storage search path or work assignment rules. If the **Hazardous Material** field for an item is set to Yes, the Hazardous tag is also applied (on application pages) to LPNs, orders, and shipments that contain the item. Similarly, the item class assigned to an item can be used in warehouse processing configurations, but has no effect on whether the Hazardous tag is displayed.

You can use the hazardous material designation for an item and item classes together to achieve certain processing results. For example, assume there is one storage zone for all hazardous material, but you still want to create location preference rules and enforce vertical storage restrictions based on item class. In this scenario, you can use the **Hazardous Material** field as criteria for a storage search path so all inventory designated as hazardous is directed to the same storage zone. Once in the zone, additional configurations, such as location preference rules or item class levels, can be used to enforce specific storage requirements for different item classes within the hazardous storage zone.

## Add or modify an item class

You are not allowed to delete an item class if there are items assigned to the class, or if the item class is used in the definition of a storage search path.

1.  Select **Configuration > Inventory > Items > Item Classes**.
2.  Perform one of the following tasks: 
    -   To add a new item class, click **Add**.
    -   To modify an item class, in the grid, click the item class.
3.  In the **Item Class** field, enter a name for the item class.
4.  In the **Description** field, enter a description that further defines the item class.
5.  Click **Save**.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
