---
title: "Replenishment Search Paths"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/replenishment_search_paths.htm"
source: "/content/replenishment_search_paths.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inventory"
  - "Replenishments"
  - "Replenishment Search Paths"
sections:
  - "Configure replenishment search paths"
  - "Search Path Rule fields"
images: []
source_sha1: 5eddb57bc2e777a705debfccc85ac190b2e63806
---
# Replenishment Search Paths

An allocation search path is a configuration that identifies the source zone from which the application should attempt to allocate inventory for a replenishment pick based on the attributes of the required inventory.

The source of the inventory to be allocated is defined in the search path rule by building and pick zone, and the search paths are arranged in order of priority that the application uses to search them. The replenishment search path rules define the following information:

-   LPN level and units of measure (UOMs) at which inventory can be allocated and picked from the zone
-   Pick method used for the replenishment picks
-   Absolute group that is used to limit the number of search paths that are evaluated when searching for inventory that is closest to the required date based on the absolute inventory rotation method specified for replenishing the item
-   Maximum amount that can be allocated from a location in the source zone to satisfy a requested pick quantity

Each search path can also be defined with attribute values that are used to qualify which inventory can be allocated using the search path. For example, you can define a search path to ensure that inventory from a specific pick zone (such as the Freezer) is given priority when allocating inventory for a specific item family (such as Frozen Goods).

A replenishment search path with no attribute values defined is the default path by which the application attempts to allocate any inventory.

A default set of inventory attribute fields are provided, but you can add fields and specify values for each search path as needed.

**Note**: If the warehouse uses a user-defined item hierarchy or if user-defined inventory attributes are enabled, those fields are available for selection. Field descriptions are not provided for user-defined fields.

## Configure replenishment search paths

**Note:** For triggered, top-off, and manual replenishments, the application only considers inventory attributes, such as Item Number, defined in the search path criteria. For demand and emergency replenishments, the application considers both inventory and order attributes, such as Client, defined in the search path criteria. This is because demand and emergency replenishments are generated to fulfill specific orders or work orders, but top-off, triggered, and manual replenishments are generated based on inventory levels in a pick zone.

1.  Select **Configuration > Inventory > Replenishments > Replenishment Search Paths**.

1.  To specify the criteria that can be used to limit search paths to specific inventory:
    
    **Note**: If the warehouse uses a user-defined item hierarchy or if user-defined inventory attributes are enabled, those fields are available for selection. Field descriptions are not provided for user-defined fields.
    
    1.  Above the grid, click **Manage Fields**.
    2.  In the **Available Criteria** column, select the attributes to use.
        
        **Note**: Selected criteria that is in use cannot be removed. Criteria is in use if one or more search paths has a value assigned to the criteria.
        
    3.  Click **Save**.
2.  Perform one of the following tasks:
    -   To add a search path, click **Add**.
    -   To modify a search path, in the grid, click the search path.
    -   To copy a search path, in the grid, select the check box next to the priority, and then click **Copy**.
3.  Enter information in the following fields:
    
     
    | Field | Description |
    | --- | --- |
    | Priority | Position of this search path in the list of search paths. The position determines the priority in which the application evaluates the search path when attempting to allocate inventory. The higher the number the lower the priority (1 is the highest priority, 2 is lower, and so on). |
    | Search Path | Name of the search. The name is displayed in lists that display search paths. For example, a search path can be assigned to an order line, so this is the name that would be selected on the order line. |
    

1.  To specify the criteria that limits the search path to specific inventory:
    1.  To show or hide criteria fields:
        1.  Under **CRITERIA**, click **Manage Fields**.
        2.  In the **Available Criteria** column, select the attributes to use.
        3.  Click **Save**.
    2.  Enter information in the criteria fields.
2.  To define a rule for the search:
    1.  Under **WHERE TO SEARCH**, click **Search Path Rules**.
    2.  Perform one of the following tasks:
        -   To add a rule, click **Add**.
        -   To modify a rule, in the grid, click the pick zone.
        -   To copy a rule, in the grid, select the check box next to the priority, and then click **Copy**.
    3.  Enter information in the [Search Path Rule fields](#Search_Path_Rule_fields).
    4.  To add an absolute group for allocating date-tracked inventory:
        1.  From the **Absolute Group** drop-down list, select **Add New**.
        2.  In the **Name** and **Description** fields, enter the values.
        3.  Click **Save**.
    5.  Click **Apply**.
    6.  On the Search Path Rules page, click **Apply**.
3.  Click **Save**.

## Search Path Rule fields

 
| Field | Description |
| --- | --- |
| Building | Unique identifier for a building. A building is a warehouse entity consisting of one or more areas. Inventory and location information can be reported by building. |
| Priority | Number that determines the priority in which the application evaluates the search path rule in relation to other search path rules when attempting to find inventory. The application begins by evaluating the rule with the highest priority (1), and then moves to the rule with the next highest priority (2), and so on. |
| Pick Zone | Name of a pick zone. A pick zone represents a group of locations that share the same attributes for picking, such as the LPN that can be allocated for replenishment picks. The replenishment search paths search the pick zones when attempting to allocate inventory that is used to fill pick locations. |
| LPN Level | LPN level at which picks can be allocated from locations in the pick zone.<br>-   • **LPN**: Inventory at the full LPN level can be reserved from locations in this zone to satisfy the requirements of an order or replenishment. Typically, an LPN refers to a pallet. When inventory is allocated at the LPN level, operators are required to scan or enter an LPN.
<br>-   • **Sub-LPN**: Inventory at the case level can be reserved from locations in this zone to satisfy the requirements of an order or replenishment.
<br>-   • **Detail LPN**: Inventory at the each (or piece) level can be reserved from locations in this zone to satisfy the requirements of an order or replenishment.
<br>-   • **Any**: Inventory at any LPN level can be reserved from locations in this zone to satisfy the requirements of an order or replenishment. |
| Allocation UOM | Unit of measure that can be picked from a location (using the search path rule) regardless of the quantity that is allocated. For example, you may configure a search path for a pick zone from which pallet quantities can be allocated (as specified by the **Maximum UOM** field), but the allocated quantity can only be picked as cases (as specified by the **Allocation UOM** field).<br > Specify an **Allocation UOM** when you want to specify which UOM is picked from a location (using the search path rule). For example, if you have a sub-LPN pick zone from which you typically pick Layer UOMs, you may want to specify Layer as the **Allocation UOM** to prevent the application from allocating Case UOMs.<br > If you leave this field blank, you allow the application to allocate any UOM from the pick zone that matches the LPN level (LPN, sub-LPN, or Detail LPN) on the search path rule. |
| Maximum UOM | Unit of measure used to limit the quantity that can be allocated from a location (using the search path rule). It allows allocation of a quantity up to but not equal to the next highest UOM on the item footprint. For example, if you specify the Case UOM, then a quantity up to but not equal to the next highest UOM (such as a Layer or Pallet quantity) can be allocated using this path.<br > You use this field to prevent large quantities from being allocated from locations that are typically used to fill smaller orders, such as to prevent pallet quantities from being allocated from each pickfaces. For example, for a pick zone that contains each pickfaces, you may configure two search paths: one path specifies the Each UOM and another path specifies the Case UOM as the **Maximum UOM**. As a result, neither of the search path rules allows the allocation of pallet quantities from a pickface.<br > You can leave this field blank if you do not want to limit the quantity that can be allocated from a location using this search path rule. |
| Threshold Pick | If Yes, inventory allocated using this search path can be a threshold pick. A threshold pick is a pick that contains more inventory than is needed for the order, and from which the unneeded inventory is removed. For example, if a full pallet consists of 10 cases, and an order line requires 9 cases, the operator can be directed to a pallet storage location to pick a full pallet and then remove the unneeded case, rather than pick 9 cases separately from a case pickface. If you set this field to Yes, then the value you select in the **Qualifying UOM** field indicates the level at which a threshold pick is allocated. Threshold picks are not allocated for replenishment picks, even if this field is set to Yes.<br > If No, the application does not allocate a threshold pick to satisfy a request for inventory. Select No to prevent the application from allocating threshold picks, or if the search path is used for allocating replenishments. |
| Location Capacity Pick % | Maximum percentage of a location's capacity, based on the location's capacity code, that can be allocated from a location in the source zone to satisfy a single pick. If a pick exceeds this percentage, the application does not allocate from the location. For example, if a location's capacity code is Each and its capacity is 100 eaches, and the value in this field is 75, a pick that requires 80 eaches (or 80% of the location's capacity) would not be allocated from the location; only a quantity that amounts to 75% or less of the location's capacity would be allocated.<br > This value is generally used to limit the inventory that can be allocated from a pickface in a single pick, such as from a case flow rack, so as not to empty the pickface, which may trigger the a replenishment. Instead, if the quantity exceeds this percentage, the application skips the location and continues searching for inventory. |
| Pick Method | A set of configurations that define how picks are created and released. You can create separate pick methods for outbound picks, which fulfill orders shipped from the warehouse, and for replenishment picks, which restock picking locations in the warehouse. |
| Absolute Group | Name of the absolute group to which the allocation search path is assigned. An absolute group is a collection of allocation search paths used to limit the search paths that are used to find date-tracked inventory for an order line that specifies an absolute inventory rotation method. An absolute inventory rotation method is used to ensure that when fulfilling a request for date-tracked inventory, the application finds the inventory that is closest to the appropriate processing date using first-in first-out (FIFO), first-expired first-out (FEFO), last-in first-out (LIFO), or last-expired first-out (LEFO). |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
