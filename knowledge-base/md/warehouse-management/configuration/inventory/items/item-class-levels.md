---
title: "Item Class Levels"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/item_class_levels.htm"
source: "/content/item_class_levels.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inventory"
  - "Items"
  - "Item Class Levels"
sections:
  - "Setup and configuration"
  - "Add or modify an item class level"
images: []
source_sha1: 92a127461a7403e93b6d3276461794692d6c2950
---
# Item Class Levels

An item class level is a configuration that can be used (depending on the storage zone configuration) to determine the level at which an item class can be stored in relation to other item class levels. With item class levels, 1 is the lowest possible level and must not be stored above any other item class level. Item class level 2 can be stored above item class level 1 but must not be stored above higher item class levels; and so on. Item class levels do not refer to specific physical levels of a bay, but instead represent a relative vertical position. Item class levels can be used to direct the storage of item classes in relation to one another, for example, to prevent contamination or the combination of materials that could prove hazardous. An item class can only be associated with one class level. However, you can assign the same class level to multiple item classes that can be stored on the same physical level.

You can change the item class level configurations for inventory already in storage to accommodate certain situations. For example, a warehouse has three item class levels (Chicken-1, Beef-2, Bread-3). If a new item class (Fruit) is introduced that can be stored between levels 2 (Beef) and 3 (Bread), then you can change the class level for Bread from 3 to 4, and then add a class level for the new item class and assign it class level 3. However, manual inventory movement may be required to open new storage opportunities, such as moving class level 4 inventory to a higher physical level so the new class level 3 inventory can be stored between class level 2 and 4.

If the application attempts to allocate a location for an item class that does not have an item class level assigned, then item class level is not considered for vertical storage.

For example, assume a warehouse has the following item class level configurations:

 
| Item Class | Class Level |
| --- | --- |
| BREAD | 8 |
| FRUIT | 6 |
| BEEF | 4 |
| CHICKEN | 2 |

Also assume that the item classes are stored in the same zone, which includes three empty bays of vertical storage three levels high. The following table illustrates the storage zone contents after multiple items are received over a period of time.

   
| Physical Level | Bay 1 | Bay 2 | Bay 2 After Manual Move |
| --- | --- | --- | --- |
| TOP | BREAD |   | BREAD |
| MIDDLE | FRUIT | BREAD | BEEF |
| BOTTOM | CHICKEN | CHICKEN | CHICKEN |

Assume the sequence for allocating a storage location is Bay 1-BOTTOM, Bay 1-MIDDLE, Bay 1-TOP, Bay 2-BOTTOM, Bay 2-MIDDLE, and so on. The placement of the items in the storage zone is a result of the following sequence of events:  

1.  CHICKEN is received. The application checks the first available location, Bay 1 - BOTTOM, and since there is no item class level below it, CHICKEN is stored there.
2.  FRUIT is received. Since FRUIT can be stored above CHICKEN, according to the item class level configurations, FRUIT is stored in Bay 1-MIDDLE.
3.  CHICKEN is received. The application checks the next available location, Bay 1-TOP. Since CHICKEN cannot be stored above FRUIT, the application checks the next location. CHICKEN is stored in Bay 2-BOTTOM.
4.  BREAD is received. The application checks the first available location, Bay 1-TOP. Since BREAD can be stored above both FRUIT and CHICKEN, it is stored in Bay 1-TOP.
5.  BREAD is received. The application checks the next available location, Bay 2-MIDDLE. Since BREAD can be stored above CHICKEN, it is stored in Bay 2-MIDDLE.
6.  BEEF is received. The application checks the next available location, Bay 2-TOP. Since BEEF cannot be stored above BREAD, the application does not find a suitable location, even though there is available capacity in the storage zone.
    
    **Note**: In this scenario, the user must recognize the missed storage opportunity and manually move the BREAD from Bay 2-MIDDLE to Bay 2-TOP. The application can then direct the BEEF to Bay 2-MIDDLE, because BREAD can be stored above BEEF which can be stored above CHICKEN.
    

## Setup and configuration

You must perform the following tasks to enable item class level processing for vertical storage: 

1.  Add item classes. See [Add or modify an item class](item-classes.md).
2.  Assign item classes to items (one item class per item). You can assign an item class to an item even if inventory for the item exists in the warehouse. See [Add or modify an item](items.md).
3.  Assign class levels to item classes. See [Add or modify an item class level](#Add_or_modify_an_item_class_level).
4.  Enable item class level storage for the storage zones in which the item classes are stored. [Add or modify a storage zone](../../inbound/storage/storage-zones.md).

## Add or modify an item class level

You use this procedure to assign a class level to an item class that has already been created. An item class can only be associated with one class level. However, you can assign the same class level to multiple item classes that can be stored on the same physical level.

1.  Select **Configuration > Inventory > Items > Item Class Levels**.
2.  Perform one of the following tasks: 
    -   To add a new item class level, click **Add**.
    -   To modify an item class level, in the grid, click the item class.
3.  Enter information in the following fields:
    
     
    | Field | Description |
    | --- | --- |
    | Item Class | Item class assigned to the class level. An item class is a category that can be used to group items for processing typically based on matching characteristics, such as hazardous or flammable material. |
    | Class Level | Class level that is used to determine the level at which the defined item class can be stored in relation to other item class levels. With item class levels, 1 is the lowest possible level and must not be stored above any other item class level. Item class level 2 can be stored above item class level 1 but must not be stored above higher item class levels; and so on. Item class levels do not refer to specific physical levels of a bay, but instead represent a relative vertical position. A class level can only be assigned to one item class. |
    
4.  Click **Save**.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
