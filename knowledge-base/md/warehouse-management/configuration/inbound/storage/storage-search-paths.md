---
title: "Storage Search Paths"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/storage_search_paths.htm"
source: "/content/storage_search_paths.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inbound"
  - "Storage"
  - "Storage Search Paths"
sections:
  - "Storage search path setup"
  - "Storage zone selection process"
  - "Location utilization percentage"
  - "Example: Prioritizing zones based on quantity"
  - "Manage available search path criteria"
  - "Add or modify a storage search path"
  - "Delete a storage search path"
  - "Storage Search Path fields"
  - "Storage Zone Rule fields"
images: []
source_sha1: c706d83a5910d390e11d3a9cecb52579a81a2490
---
# Storage Search Paths

A search path is a configuration that is used to specify the storage zone to which inventory should be directed during putaway. A search path can be restricted to inventory coming from a specific source movement zone, and to inventory that matches specific criteria (such as item, item family, inventory status, and handling unit type) defined for the search path.

Storage zone rules (associated with a search path) specify the zone to which matching inventory can be directed, criteria for finding an optimal location, and capacity restrictions for the zone.

The application processes search paths in order of priority. When it finds a path that matches the inventory to be put away, it searches the path's storage zone rules in sequential order to find an optimal location.

## Storage search path setup

You use the following steps to configure the application to automatically direct inventory to a storage location following receiving or inventory identification:

1.  Configure the storage building sequence. A storage building sequence identifies, for a building, the sequence in which the application attempts to store inventory that is received into the building. Typically the building in which the inventory is received or identified is first in the sequence. If the application cannot find a storage location for the inventory in the first building, it attempts to find a location in the next sequential building.
2.  Optionally, configure location preference rules. A location preference rule specifies a location or range of locations, rather than a storage zone, to which specific inventory should be directed during putaway.
3.  Optionally, select additional inventory or item attributes for use in search path configurations. If the criteria that you want to use for directing inventory to a storage zone is not available, you can add the fields to the criteria selection page prior to configuring storage search paths.
4.  Configure storage search paths. A storage search path has two components:
    -   Inventory criteria, such as item family and inventory status, that defines the inventory that can be stored using the path.
    -   One or more rules that identify the storage zones to which the inventory should be directed. Each rule is configured with location selection criteria, and zone and aisle capacity restrictions that the application uses to find an optimal location within the zone.

## Storage zone selection process

The application performs the following steps to select a storage location for received or identified inventory:

1.  Evaluates the location preference rule, if any, to determine if there is a match for the inventory. If there is a match, then the application directs putaway to the location and does not continue to search the storage search paths.
2.  Uses the following process to evaluate storage search paths:
    1.  Evaluates search paths in priority order to find a path that matches the inventory.
    2.  Evaluates the path's storage zone rules in sequential order with the following exceptions:
        -   If a building sequence has been defined, the application searches for storage zones located in the first building in the sequence. If a location is not found, it searches for storage zones in the next sequential building; and so on.
        -   Zones in which the inventory quantity is below the minimum inventory level are evaluated first, regardless of sequence order.
        -   Zones in which the inventory quantity is greater than the maximum inventory level are evaluated last, regardless of sequence order.
        -   Zones that contain more LPNs of an item than the value specified for maximum LPNs per aisle are only attempted after every other rule has been evaluated.
    3.  Finds a location based on the location selection criteria defined for the rule.
3.  If a suitable location is found, the application directs putaway to the location. If a suitable location is not found, the operator is directed to select a location manually.

## Location utilization percentage

The utilization percentage for a location determines the percentage of a location's capacity that inventory must fill before it can be stored in the location. When using location utilization percentage, you can configure multiple storage zone rules for the same storage zone with different utilization percentages that the application considers in sequence. For example, assume two similar rules are created for the same zone, with the only difference being the first rule has a **Location Utilization Percentage** of 75%, and the second rule is 50%. If the application attempts to allocate a location based on the first rule but cannot find a location that the inventory will fill to at least 75%, then a second attempt is made to allocate a location that the inventory will fill to at least 50%.

If Warehouse Labor Management is integrated and you set a **Proximity** value for a storage zone, then the application first sorts the locations in the zone according the proximity value before applying the remaining conditions in the storage zone rules. For example, if you define that the inventory should be stored in locations that are closest to the primary pick location for the item, the application sorts by proximity to the pick location and then evaluates the conditions on the search path.

If **Last Location**, **Mixed Location**, or **Match Velocity** is set to Yes on the allocation rule, the application first finds locations according to the configurations, (as well as the **Location Status** - Empty or Partially Full), but the utilization percentage still must be met before inventory can be stored. If you always want to use last location, then the utilization percentage should not be defined.

A lower percentage can lead to high-capacity locations being used for smaller pallets, which may limit the available storage capacity for larger pallets. Alternatively, a higher percentage requires that larger pallets are stored in the zone so that locations do not remain unallocated due to putaway quantities not satisfying the utilization percentage.

The percentage applies to a single putaway quantity. Another putaway attempt in a partially full location will consider the existing inventory before calculating the utilization percentage. For example, if the location utilization percentage is set to 75% and the location currently is 25% occupied, then additional inventory to be put away must occupy at least 50% of the total capacity so that the total quantity in the location meets the utilization percentage.

## Example: Prioritizing zones based on quantity

In the following example, the application compares the quantity of an item in each zone that can be used to store the item to the minimum and maximum level values.

    
| Storage zone rule sequence | Current quantity | Minimum level | Maximum level | Actual putaway sequence |
| --- | --- | --- | --- | --- |
| Each Pickface | 140 | 100 | 500 | Bins |
| Bins | 10 | 50 | 100 | Each Pickface |
| Case Pickface | 250 | 200 | 1000 | Case Pickface |
| Rack Storage | 1300 | 0 | 0 | Rack Storage |
| Tunnel Storage | 800 | 400 | 600 | Bulk Storage |
| Bulk Storage | 600 | 0 | 0 | Tunnel Storage |

The result is that the application uses the actual putaway sequence for the following reasons:

-   The Bins zone is a higher priority than the Each Pickface because its quantity of 10 is less than its minimum level of 50, and the Each Pickface is already above its minimum level.
-   The Tunnel Storage zone is a lower priority than the Bulk Storage zone because its quantity of 800 is greater than its maximum level, and Bulk Storage had no maximum level specified.

## Manage available search path criteria

You can specify the criteria that is made available for use in a search path. For example, you may want to add Item Family to your criteria so that you can configure a storage path that directs a particular item family to a specific storage zone.

**Note**: If the warehouse uses an item hierarchy or if user-defined inventory attributes have been enabled, those fields are also displayed for selection.

1.  Select **Configuration > Inbound > Storage > Storage Search Paths**.
2.  Above the grid, click **Manage fields**.
3.  To make criteria available for use, in the **Available** column, select the check box next to the criteria. A check mark in the **In Use** column indicates that the criteria is currently used in a search path configuration.
4.  To make criteria unavailable for use, deselect the check box next to the criteria.
    
    **Note**: You cannot deselect criteria that is currently in use.
    
5.  Click **Save**.

## Add or modify a storage search path

1.  Select **Configuration > Inbound > Storage > Storage Search Paths**.
2.  Perform one of the following tasks:
    -   To add a search path, click **Add**.
    -   To modify a search path, in the grid, click the search path name.
    -   To copy a search path, in the grid, select the check box next to the search path, and then click **Copy**.
3.  Enter information in the [Storage Search Path fields](#Storage_Search_Path_fields).
    
    **Note**: If the warehouse uses a user-defined item hierarchy or if user-defined inventory attributes are enabled, those fields are available for selection. Field descriptions are not provided for user-defined fields.
    
4.  To add inventory criteria:
    1.  Click **Manage Fields**.
    2.  In the **Available** column, select the check box next to the criteria. A check mark in the **In Use** column indicates that the criteria is currently used in a search path configuration.
        
        **Note**: You cannot deselect criteria that is currently in use.
        
    3.  Click **Save**.
5.  Define and prioritize the rules for finding a storage zone and location:
    1.  Click **Zone Rules**. The Storage Zone Rules page is displayed.
    2.  Perform one of the following tasks:
        -   To add a storage zone rule, click **Add**.
        -   To modify a storage zone rule, in the grid, click the storage zone.
        -   To copy a storage zone rule, in the grid, select the check box next to the storage zone, and then click **Copy**.
    3.  Enter information in the [Storage Zone Rule fields](#Storage_Zone_Rule_fields).
    4.  To select the units of measure (UOMs) that can be stored in the zone:
        1.  Click **Manage units of measure for this zone**.
        2.  Select the check box next to the UOMs that can be stored in the zone.
        3.  Click **Save**.
    5.  Click **Apply**.
    6.  To delete a storage zone rule:
        1.  In the grid, select the check box next to the storage zone rule to delete.
        2.  Click **Delete**. A confirmation message is displayed.
        3.  Click **OK**.
6.  Click **Save**.

## Delete a storage search path

1.  Select **Configuration > Inbound > Storage > Storage Search Paths**.
2.  In the grid, select the check box next to the search path name to delete.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Storage Search Path fields

 
| Field | Description |
| --- | --- |
| Priority | Number that determines the priority in which the application evaluates in the storage search path in relation to other search paths when attempting to find a putaway location for inventory. The application begins by evaluating the path with the lowest priority (1), and then moves to the search path with the next highest priority. |
| Search Path Name | Name for the search path. It is helpful to provide a name that briefly describes the inventory for which the search path was created. |
| Item Client | Name of the client who stores this item in the facility. This field is only displayed in a 3PL environment. |
| Item | Identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). Before the application can effectively store, track, and manipulate inventory, you must assign an item identifier and define the attributes of each item you want to track. When defining an item, you specify information such as how the item is packaged and handled, along with details that define how it should be received, stored, allocated, shipped, counted, and valued (cost information). |
| Item Family | Identifier used to group similar items together. Typically, all of the items within a family have the same material handling characteristics. |
| Supplier | Identifier for a supplier. A supplier can be an individual, organization, or another warehouse within your own organization from which you repeatedly receive inventory or handling units. |
| Handling Unit Type | Category that classifies a group of handling units (for example, pallets, totes, transport equipment, or vehicles) that share the same characteristics such as size and weight, as well as whether they are serialized, temporary, or considered a container. The application tracks the on-hand quantity of handling units by type and, for serialized handling units, by handling unit identifier. |
| Receiving Movement Zone | Movement zone in which the inventory to be put away was received or identified. |
| LPN Composition | Identifier that describes the inventory's physical composition. The application uses this value to direct inventory with a matching value to locations specified by the search path rule.<br > For example, you can direct inventory that meets the criteria for Heavy to floor-level pick locations. The values for physical composition are defined by the LPN composition attributes. See [Configure storage settings](storage-settings.md). |
| Inventory Status | Value that defines the quality or disposition of the inventory. |
| Consigned | If Yes, the supplier has retained ownership of the inventory that was received or identified into the warehouse. If consignment is tracked, ownership remains with the supplier until a certain point during warehouse processing, at which time ownership of the inventory is automatically transferred to the warehouse. Consignment tracking is configured by supplier.<br > If No, ownership of the inventory is automatically transferred to the warehouse when it is received or identified.<br > If No Preference, then the search path can be used for inventory that is consigned or not consigned. |
| Held | If Yes, the path is used for inventory to which a hold has been applied. A hold is an attribute of inventory independent of the inventory status associated with that inventory. A hold can indicate that inventory is not available for use or distribution. Optionally, a hold can be configured to allow inventory to which the hold is applied to be shipped.<br > If No, the path is not used for inventory to which a hold has been applied.<br > If No Preference, then the search path can be used for inventory either on hold or not on hold. |
| Customs Item Type | Category that defines the type of customs tracking that is required for the item. Only displayed if Customs functionality is enabled.<br>-   • **Customs**: Customs duties need to be paid for the item. Available if the address for the warehouse is designated as a Customs site type.
<br>-   • **Excise**: Excise duties need to be paid for the item; customs duties may also be required. Available if the address for the warehouse is designated as a Customs and Excise site type.
<br>-   • **No selection (blank)**: Inventory for the item is not bonded. |
| Item Family Group | Name used to group similar item families together. Typically, all of the item families within a group have the same material handling characteristics. Item family groups can be used for sorting and reporting purposes, and as criteria, for example, for storage paths and work assignment rules. |
| ABC Code | Code that the application refers to during the cycle counting process to categorize item numbers and storage locations to determine how often inventory needs to be counted in a single period. ABC code only applies to locations when the application is configured to automatically generate inventory counts by location. The values for ABC codes are defined in inventory count settings. |
| Aging Profile | Name of the aging profile representing the aging process assigned to this item. An inventory aging profile is a configuration that defines a series of inventory statuses, each of which is associated with an age, such as 2 hours, 10 days, or 4 weeks. You assign an aging profile to a date-tracked item when you want the application to automatically update the inventory status of inventory for the item as it ages in the warehouse.<br > Included in the aging profile is the option to define an "Expired" status. The application uses the age of the "Expired" status to calculate the expiration date of an item that is tracked by its expiration date. An aging profile is required if the item is date-tracked by both manufactured date and expiration date. This field only available if the item requires this attribute.  |
| Color | User-defined value for the color of the item. Enter a value if you want to track, report on, or search for inventory based on this attribute. For example, this value can be displayed in inventory and item reports, and can be used to find matching inventory for the purpose of applying a hold or performing an inventory status change operation. |
| Customs VAT Code | Code for the value added tax (VAT) for the item. A customs VAT is charged on goods and some services that are imported from countries outside the European Unit (EU) and brought into the United Kingdom (UK) from other EU countries. It is also charged on most goods and services that VAT-registered businesses provide in the UK.<br>-   • **Standard**: The standard customs VAT rate is charged for this item.
<br>-   • **Zero**: No customs VAT is charged for this item. |
| Origin Code | Identifier assigned to an item to identify the item's country of origin. It is typically used for export paperwork. Origin codes are user defined. |
| Department | Identifier for a department within the customer's facility. A department can be specified for a customer type, customer, order, order line, distribution, and item. It can be used to group information for the purpose of sorting and searching data, consolidating distribution inventory in customer-specific storage locations, and to help customers direct inventory to the proper department when it arrives at their facility. |
| Fit | User-defined value for the fit of the item. Enter a value if you want to track, report on, or search for inventory based on this attribute. For example, this value can be displayed in inventory and item reports, and can be used to find matching inventory for the purpose of applying a hold or performing an inventory status change operation. |
| Duty Stamp Tracked | If Yes, the item requires a duty stamp. Select Yes if the value for **Customs Item Type** is **Excise** and the item contains over 30% alcohol by volume in containers that are 35 cubic liters or larger.<br > If No, the item does not require a duty stamp.<br > Only available if the value for **Customs Item Type** on the order is **Excise**. |
| Item Type | User-defined code that you can use to group similar items. This value is not used in warehouse processing, but can be displayed in shipped history reports. |
| Size | User-defined value for the size of the item. Enter a value if you want to track, report on, or search for inventory based on this attribute. For example, this value can be displayed in inventory and item reports, and can be used to find matching inventory for the purpose of applying a hold or performing an inventory status change operation. |
| Style | User-defined value for the style of the item. Enter a value if you want to track, report on, or search for inventory based on this attribute. For example, this value can be displayed in inventory and item reports, and can be used to find matching inventory for the purpose of applying a hold or performing an inventory status change operation. |
| Velocity | Identifies the speed at which inventory stored in a location moves in and out of the warehouse. Velocity is used to optimize warehouse space and inventory handling by placing fast moving items in the best locations for quick picking, and slower moving items in the less accessible storage locations. The application accomplishes this by attempting to match the velocity of the item with the velocity of the location when finding a location for storing the item. |
| Weight Class | Value (such as Heavy, Medium, or Light) that represents the relative weight of the item. |
| WIP Supply Item | If Yes, then the item is used in work order processing as a component in a top-level item; however, it is not allocated, picked, or delivered to a production staging location, line, or station. Instead, a supply item is typically stored in or near the production area (such as in a non-inventory tracked work-in-process supply locations) and is used by multiple production lines and top-level items. Cellophane and other wrapping materials are examples of supply items. Supply items are charged to a work order, either by specifying them in a bill of material (BOM) used to create the work order, or by specifying them when the work order is closed.<br > If No, the item is not a supply item. |

## Storage Zone Rule fields

 
| Field | Description |
| --- | --- |
| Sequence | Number that determines the sequence in which the application evaluates the storage zone rule in relation to other storage zone rules assigned to the search path. When evaluating the rules for location selection, the application begins by evaluating the rule with the lowest priority (1), and then moves to the next storage zone rule in sequential order. |
| Building | Building in which the storage zone is located. A building is a warehouse entity consisting of one or more zones. Inventory and location information can be reported by building. |
| Storage Zone | A storage zone represents a group of locations that have the same attributes (consolidation, item mixing, date control, and others) for storing inventory. |
| Last Location | If Yes, the application attempts to select the last location to which identical inventory was stored. When the last location reaches capacity, inventory is directed to a new location, based on the next sequential applicable storage zone rule, and that becomes the new last location for the item. If, during putaway to the last location, an operator overrides the putaway location, then the location to which the operator deposits the inventory becomes the new last location for the item. Additionally, if new inventory to be stored in an item's last location violates mixing rules, or the last location is a piece of transport equipment used for storage that has been dispatched or converted to shipping transport equipment, the application finds a different location, which becomes the item's new last location. The last location for an item is cleared when the location is emptied and there is no pending inventory to the location.<br > If No, the application does not attempt to find the last location to which identical inventory was deposited. |
| Location Status | Identifies the type of location to which inventory should be directed first.<br>-   • **Empty**: Find and fill empty locations first, before attempting to fill partially filled locations. Select this option, for example, if you want to store fast-moving items in multiple locations so that multiple operators do not have to access the same location to pick the item.
<br>-   • **Partially Full**: Find and fill locations that contain inventory first, before attempting to fill empty locations. Select this option, for example, if space is limited and you want to consolidate inventory if possible. |
| Mixed Location | If Yes, the application attempts to find a partially filled location that already contains mixed inventory. The partially-filled, mixed-inventory location does not need to contain inventory that matches the inventory being put away.<br > If No, the application does not attempt to find a partially filled mixed location first and instead searches for an empty location, or a location that only contains the inventory that is being put away. |
| Match Velocity | If Yes, the application attempts to find a location with a velocity setting that is the same as or lower then the item being put away. Select this option if you want to avoid placing low velocity items in higher velocity locations.<br > If No, the application does not attempt to match the velocity of the item with the velocity of the location. |
| Location Utilization Percentage | Percentage of a location's capacity that inventory must fill before it can be stored in the location. If the inventory for a single putaway quantity does not fill the location to at least the defined percentage, then the application looks for another location according to the storage zone rules.<br > **Note**: Location utilization percentage is only applicable to locations in the storage zone with a capacity code of Pallet or Volume. If the location capacity code is Pallet, then the utilization percentage is based on the height of the location. If the location capacity code is Volume, then the utilization percentage is based on the volume of the location.<br > For example, assume the **Location Utilization Percentage** is 75, the capacity code for a location is Pallet, and the location height is 72 inches. In order for the application to allocate the location to store a pallet, in addition to satisfying the other storage zone rule criteria, the pallet must be at least 54 inches tall (.75 x 72 = 54), which fills the location to 75%. If the pallet is less than 54 inches tall, then it does not meet the utilization percentage, and the application searches for another location. Location utilization is useful to ensure that smaller pallets (in height or volume) are not stored in locations that could be more efficiently used for larger pallets.<br > The height and volume of a full pallet is determined by the item's footprint (pallet dimensions). For partial pallets, the application calculates the pallet height by using the height of a case, the number of cases on the pallet, and the number of cases per tier (as defined in the footprint). If a pallet has mixed items, the application calculates the pallet height based on the tallest case and number of tiers. Similarly, when calculating utilization by volume for a mixed-item pallet, the application uses the largest case volume and number of tiers.<br>
**Notes**: 

<br>

-   •
    
    If an item has an assigned location as defined in the location preference rules, then utilization percentage is not considered because storage search paths are not used.
    
    <br>
<br>-   •
    
    Location utilization should not be used in locations where pallets are stacked vertically. Storage zone rules for zones with locations that utilize pallet stack height and vertical stacking methods should have a **Location Utilization Percentage** of 0 (zero) or null (blank).
    
    <br>
<br>-   •
    
    If **Last Location** is set to Yes and you want to ensure that the last location is always used when there is available capacity, then do not define a location utilization percentage. If you do, then the inventory must satisfy the utilization percentage before it can be stored in the last location.
    
    <br>
<br>

<br > For more information, see [Location utilization percentage](#Location_utilization_percentage). |
| Zone Inventory Level - Minimum | Minimum level of inventory based on pallet quantity (as defined by the pallet equivalent UOM on the item footprint) that must remain in the zone. Warehouse Management will keep inventory in the zone at or above this level. Warehouse Management considers the unit (or each) quantity on a pallet when calculating inventory levels.<br > For example, if the minimum level is 1 pallet, and 1 pallet equivalent UOM of inventory that meets the search path criteria contains 10 eaches, then the minimum quantity is 10 eaches, even if it resides on multiple partial pallets (such as 4 on one pallet and 6 on another). |
| Zone Inventory Level - Maximum | Maximum level of inventory based on pallet quantity (as defined by the pallet equivalent UOM on the item footprint) that can reside in the zone. Warehouse Management will keep inventory in the zone at or below this level. Warehouse Management considers the unit (or each) quantity on a pallet when calculating inventory levels.<br > If a pallet equivalent UOM of inventory that meets the search path criteria contains 100 eaches, and you define the maximum value as 5, then the application attempts to keep inventory in this storage zone at or below 500 eaches.<br > For example, assume a pallet equivalent UOM of an item contains 100 eaches, and the maximum inventory level for the zone is set as 2 (2 pallets = 200 eaches). If 1 full pallet and 1 partial pallet with a quantity of 50 (150 eaches total) are already stored in the zone, and if a third pallet with a partial quantity equal to or less than 50 eaches is being stored, then Warehouse Management evaluates the zone in sequence. However, if the third pallet has a unit quantity greater than 50 eaches, the application evaluates the zone last to avoid exceeding the zone maximum inventory level, if possible.<br > If location level capacity is found in a zone that is over its maximum inventory level, additional inventory can still be stored in the zone. However, zones in which the inventory quantity is greater than the maximum level are evaluated last, regardless of sequence order. If a building sequence has been defined, the application does not evaluate the second building unless there are no available locations in the search path zones in the first building. |
| Use Item in Inventory Level Calculation (Zone) | If Yes, then if a specific item is not already specified on the search path, the application uses the current search item for the calculation of pallet quantity for the zone, using the pallet equivalent UOM defined on the item footprint.<br > This means that a search path is not needed for every individual item.<br > If No, then if an item is not specified on the search path, the application uses the criteria on the search path to calculate pallet quantity for the zone. |
| Aisle Inventory Level - Maximum | Maximum level of inventory based on pallet quantity (as defined by the pallet equivalent UOM on the item footprint) that can be stored in a single aisle of the storage zone. Warehouse Management will keep inventory in an aisle at or below this level. Warehouse Management considers the unit (or each) quantity on a pallet when calculating inventory levels.<br > If a pallet equivalent UOM of inventory that meets the search path criteria contains 100 eaches, and you define the maximum value as 10, then inventory in an aisle in this zone is kept at or below 1000 eaches.<br > For example, assume a pallet equivalent UOM of a certain item contains 100 eaches and the maximum inventory level for the aisle is set as 10 (10 pallets =1000 eaches). If 9 full pallets and 1 pallet with a quantity of 50 (950 eaches total) are already stored in the aisle, then Warehouse Management allows another pallet to be stored in the same aisle as long as its unit quantity is equal to or less than 50 eaches. However, if the pallet has a unit quantity greater than 50 eaches, it could not be stored in the same aisle because it exceeds the maximum level of 1000 eaches (or 10 full pallet quantities). |
| Use Item in Inventory Level Calculation (Aisle) | If Yes, then if a specific item is not already specified on the search path, the application uses the current search item for the calculation of pallet quantity for the aisle, using the pallet equivalent UOM defined on the item footprint.<br > This means that a search path is not needed for every individual item.<br > If No, then if an item is not specified on the search path, the application uses the criteria on the search path to calculate pallet quantity for the aisle. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
