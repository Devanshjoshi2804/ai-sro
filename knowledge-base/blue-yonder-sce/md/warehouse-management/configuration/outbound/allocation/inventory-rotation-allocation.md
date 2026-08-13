---
title: "Inventory rotation allocation "
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/inventory_rotation_allocation_.htm"
source: "/content/inventory_rotation_allocation_.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Outbound"
  - "Allocation"
  - "Inventory rotation allocation "
sections:
  - "Inventory rotation methods"
  - "Inventory rotation allocation processing"
  - "Inventory must match inventory rotation method"
  - "Continue to allocate inventory beyond best date"
  - "Example: Not enough best-date inventory to match rotation method"
  - "Date-based inventory rotation method processing"
  - "Date-based absolute inventory rotation method processing"
  - "Location attribute inventory rotation method processing"
  - "Inventory rotation allocation processing examples"
  - "Outbound date window"
  - "Date window calculations"
  - "Movement zones for absolute inventory rotation allocation"
  - "Inventory rotation allocation processing setup"
images: []
source_sha1: e04a13f03c43f10d54bbb718da849118dd20121f
---
# Inventory rotation allocation

Inventory rotation allocation is a process that allocation uses to find and allocate inventory for an order based on an inventory rotation method and the received, manufactured, or expiration date of inventory. The inventory rotation method determines the sequence in which allocation evaluates available inventory for allocation.

If an order or work order line does not use an inventory rotation method, such as first-expired, first-out (FEFO), allocation processing follows the sequence of allocation search paths, and it allocates the first inventory that it finds that matches the required attributes on the order or work order line.

If the order or work order line uses an inventory rotation method that is not absolute, such as FEFO, allocation follows the sequence of allocation search paths to find a zone that contains the inventory, and then from that zone it allocates the inventory closest to the processing date defined by the inventory rotation method.

If the order or work order line uses an absolute inventory rotation method, such as absolute FEFO, and absolute groups are not defined, allocation searches all of the appropriate search paths until it finds the inventory that is closest to the appropriate processing date. If absolute groups are defined, it searches the sequence of absolute groups until it finds matching inventory within an absolute group, and then it allocates from within that group the inventory closest to the appropriate processing date. Movement zones not associated with a shipping or replenishment allocation search path can also be included in the search for inventory closest to the processing date. See [Movement zones for absolute inventory rotation allocation](#Movement_zones_for_absolute_inventory_rotation_allocation).

## Inventory rotation methods

An inventory rotation method determines the order in which the application chooses available inventory for allocation and replenishment.

Allocation for an order or work order follows the sequence of allocation search paths and, if appropriate, absolute groups, if they are defined for search paths. Replenishments follow the sequence of replenishment search paths.

**IMPORTANT**: The regular and absolute FEFO and LEFO methods of inventory rotation are only supported for date-tracked inventory that is assigned to an aging profile with an **Expired** status defined.

The application supports the following default inventory rotation methods:

-   **FIFO-ORDER-BY**: First-in, first-out. The oldest inventory, based on received date, is selected first from the first search path that contains matching inventory.
-   **FIFO-ORDER-BY-ABSOLUTE**: The oldest inventory, based on received date, is selected first based on a search of all search paths or, if absolute groups are defined, from the first absolute group that contains matching inventory.
-   **LIFO-ORDER-BY**: Last-in, first-out. The newest inventory, based on received date, is selected first from the first search path that contains matching inventory.
-   **LIFO-ORDER-BY-ABSOLUTE**: The newest inventory, based on received date, is selected first based on a search of all search paths or, if absolute groups are defined, from the first absolute group that contains matching inventory.
-   **FEFO-ORDER-BY**: First-expiration, first-out. The first inventory to expire, based on expiration date, is selected first from the first search path that contains matching inventory.
-   **FEFO-ORDER-BY-ABSOLUTE**: The first inventory to expire, based on expiration date, is selected first based on a search of all search paths or, if absolute groups are defined, from the first absolute group that contains matching inventory.
-   **LEFO-ORDER-BY**: Last-expiration, first-out. The last inventory to expire, based on expiration date, is selected first from the first search path that contains matching inventory.
-   **LEFO-ORDER-BY-ABSOLUTE**: The last inventory to expire, based on expiration date, is selected first based on a search of all search paths or, if absolute groups are defined, from the first absolute group that contains matching inventory.
-   **LOCATION-ORDER-BY**: Locations are ordered within an pick zone (maintaining the search path order) by the location attributes specified for the **Location Sort** configuration in the inventory selection settings.

**Note**: The **Inventory in Location Sort** configuration is not an inventory rotation method, but is an additional sorting method applied after allocation to ensure the consumption of proper inventory during picking. LPNs of inventory within a location are ordered by the attributes specified by the **Inventory in Location Sort** configuration in the inventory selection settings.

## Inventory rotation allocation processing

Inventory rotation allocation processing is an allocation process that is directed by an inventory rotation method. An inventory rotation method determines the order in which allocation chooses available inventory to fulfill an order or replenishment. For inventory rotation methods, allocation searches for inventory according to the sequence of allocation or replenishment search paths. For absolute inventory rotation methods, allocation ignores the search path sequence but can be limited to search paths defined by absolute groups.

If an inventory rotation method is specified at any of the following levels, the application uses the one with the highest precedence. The precedence is defined from highest to lowest in the following order:

**Note**: Inventory rotation methods defined at a lower precedence (except the default method) are automatically copied to the order line or work order line when the line is created. For example, if an order line is created for a date-tracked item with a rotation method defined, the rotation method is copied from the item to the order line, and then the application uses the order line rotation method during allocation.

-   Order line or work order line
-   Customer item
-   Item
-   Customer (ship to)
-   Customer type
-   Client
-   Default rotation method
    -   For order allocations, defined by the allocation inventory selection configuration
    -   For replenishments, defined by the replenishment settings configuration

After inventory has been allocated from a location using a date-based inventory rotation method, the application directs the picker to pick the best inventory available in that location. The operator can pick any inventory that is within the date window of the best inventory available.

## Inventory must match inventory rotation method

Allocation attempts to fulfill a request for inventory (such as an order line) with inventory closest to the processing date based on the inventory rotation method associated with the request. The inventory rotation method configuration determines what takes place when the application finds an insufficient quantity of best-date inventory or when the best-date inventory cannot be allocated. Best-date inventory may not be eligible for allocation if the unit of measure (UOM) does not match the UOM of the request, for example.

You use the **Inventory Must Match Inventory Rotation Method** field to specify whether the application must allocate inventory for an order line that matches the best date as determined by the inventory rotation method.

If you set this field to Yes, then for order lines that require the inventory rotation method, the application must allocate inventory that matches the best date as determined by the inventory rotation method. If no quantity of best-date inventory can be allocated, then the entire order line is shorted. When there is not enough best-date inventory to fulfill the request, the **Continue to Allocate Inventory Beyond Best Date** field, which becomes available when the **Inventory Must Match Inventory Rotation Method** field is set to Yes, determines whether the application shorts the remaining quantity or attempts to allocate inventory using the next best date. See [Continue to allocate inventory beyond best date](#Continue_to_allocate_inventory_beyond_best_date).

If you set this field to No, then when the available inventory (based on the best date for the inventory rotation method) is not enough to fulfill the order line or the best-date inventory cannot be allocated, the application attempts to fulfill the remaining quantity with the next closest date based on the inventory rotation method until the order line is fulfilled. If the application cannot allocate the required quantity after considering all dates for the inventory rotation method, then the order line is shorted.

You can access both the **Inventory Must Match Rotation Method** and **Continue to Allocate Inventory Beyond Best Date** fields when configuring **Location Sort** for an absolute rotation method. See [Configure allocation inventory selection settings](allocation-inventory-selection.md).

### Continue to allocate inventory beyond best date

When the **Inventory Must Match Inventory Rotation Method** field is set to Yes, you use the **Continue to Allocate Inventory Beyond Best Date** field to specify whether the application attempts to allocate inventory with the next best date if there is not enough best-date inventory available to fulfill an order line.

If you set this field to Yes, then when the application has allocated all available best-date inventory for an order line based on the inventory rotation method and there is unfulfilled quantity, the application continues to allocate inventory with the next best date to fulfill the order line. The application continues searching for the next best date until the order line is fully allocated or the next best-date inventory is unavailable. If the application cannot allocate the required quantity after considering all dates for the inventory rotation method, then the order line is shorted. The application only continues to allocate beyond the best date for an order line if a partial quantity of best-date inventory is allocated; if no best-date inventory is able to be allocated, then the entire order line is shorted.

**Note**: If this field is set to Yes and an order line does not allow case splitting, the application's behavior when encountering a partial case of best-date inventory is determined by the **Ignore Partial Cases for Strict Absolute Date Allocation** field in the allocation inventory selection configuration. If the **Ignore Partial Cases for Strict Absolute Date Allocation** field is set to Yes, then the application allocates any full cases with the same date as the partial case, skips the partial case, and continues to allocate the next best-date inventory. If the **Ignore Partial Cases for Strict Absolute Date Allocation** field is set to No, then the application allocates any full cases with the same date as the partial case, but the remaining quantity for the order line is shorted.

If you set this field to No, then the application does not allocate inventory beyond the best date for an order line based on the inventory rotation method. For example, if the application can only allocate 10 eaches of best-date inventory for an order line requiring 20 eaches, then the remaining 10 eaches are shorted, even if there is available inventory with the next best date. This field is set to No by default.

### Example: Not enough best-date inventory to match rotation method

For example, an order line requires 20 eaches of ITEM-A with an inventory rotation method of first-expired, first-out (FEFO). When the order line is allocated, the application finds the first-expired inventory, but there are only 10 eaches with that expiration date available for allocation.

-   If the **Inventory Must Match Inventory Rotation Method** field is set to Yes and the **Continue to Allocate Inventory Beyond Best Date** field is set to No, the application allocates the 10 eaches with the oldest expiration date and shorts the remaining quantity (10 eaches).
-   If the **Inventory Must Match Inventory Rotation Method** field is set to Yes and the **Continue to Allocate Inventory Beyond Best Date** field is set to Yes, the application allocates the 10 eaches with the oldest expiration date and then continues to allocate inventory from the next oldest expiration date to fulfill the order line until the order line quantity is fulfilled. If the inventory with the next oldest expiration date cannot be allocated, then the application shorts the remaining quantity.
-   If the **Inventory Must Match Inventory Rotation Method** field is set to No, the application searches for inventory with the next oldest expiration date to fulfill the rest of the quantity needed by the order line, and continues searching the next oldest expiration dates until the order line quantity is fulfilled.

## Date-based inventory rotation method processing

When using a date-based inventory rotation method (FEFO-ORDER-BY, FIFO-ORDER-BY, LEFO-ORDER-BY, and LIFO-ORDER-BY), the application searches for inventory by search path sequence. When it finds a pick zone that contains the inventory, then the inventory closest to the preferred processing date is reserved, even when this inventory spans multiple locations in the zone. A location may contain inventory that has different dates, so the application determines the amount of inventory available for each date. After the inventory for a date has been allocated, the application considers inventory in all of the locations in a zone to determine the next date to allocate. This logic only considers pick zones in which the unit of measure (UOM) is valid for picking.

Date-based inventory rotation methods are typically used by companies that have items that have a longer shelf life; therefore, shipping inventory based on the priority of the search path is acceptable.

For example, if the order is for ITEM01 and the inventory rotation method is first-in, first-out (FIFO-ORDER-BY), then the application finds the first pick zone that contains ITEM01 and allocates the oldest inventory based on its received date that matches all of the required attributes on the order line.

## Date-based absolute inventory rotation method processing

When using an absolute date-based inventory rotation method (FEFO-ORDER-BY-ABSOLUTE, FIFO-ORDER-BY-ABSOLUTE, LEFO-ORDER-BY-ABSOLUTE, and LIFO-ORDER-BY-ABSOLUTE), the application searches in one of the following ways, depending on whether absolute groups have been defined:

-   If absolute groups are not defined, the application searches all search paths for inventory that is closest to the preferred processing date, even when this inventory spans multiple pick zones and locations. A location may contain inventory that has different dates, so the application determines the amount of inventory for each date. After the inventory for the preferred date is allocated, the application considers all other search paths to determine the next date to allocate. This logic only considers pick zones in which the UOM is valid for picking.
-   If absolute groups are defined, the application searches each absolute group, in sequence, until it finds matching inventory, and then it allocates inventory that is closest to the preferred processing date within that absolute group. If sufficient inventory is not found, the application searches the next sequential absolute group.

**Note**: If the **Inventory Must Match Inventory Rotation Method** field is set to Yes, then the application must allocate inventory for an order line that matches the best date as determined by the inventory rotation method. If no quantity of best-date inventory can be allocated, then the entire order line is shorted. However, if a partial quantity of best-date inventory can be allocated, then the **Continue to Allocate Inventory Beyond Best Date** field determines whether the application shorts the remaining quantity or attempts to allocate inventory using the next best date. If the **Inventory Must Match Inventory Rotation Method** field is set to No, then the application can allocate inventory with the next closest date. See [Inventory must match inventory rotation method](#Inventory_must_match_inventory_rotation_method).

Absolute date-based inventory rotation methods are typically used by companies that have items that have a very short shelf life; therefore, shipping the oldest inventory is critical to prevent it from expiring in the warehouse.

For example, if the order is for ITEM01 and the absolute first-in, first-out (FIFO-ORDER-BY-ABSOLUTE) inventory rotation method is selected, the application searches in one of the following ways:

-   The application searches all search paths until it finds the oldest inventory for ITEM01 based on its received date that matches all of the required attributes on the order line.
-   The application searches each absolute group in sequence until it finds ITEM01, and then allocates the oldest inventory for ITEM01 based on its received date that matches all of the required attributes on the order line.

## Location attribute inventory rotation method processing

When using the location attribute inventory rotation method (**Location Order By**), the application searches for inventory by allocation search path sequence and then in the order defined by the location attributes specified in the **Location Order By** configuration.

## Inventory rotation allocation processing examples

**Example: Allocating in absolute date order with absolute groups**

For allocation search paths set to search GROUP1, then GROUP2, then GROUP3, the following table provides an example of the absolute date processing order in which the application would search for allocatable inventory using ABSOLUTE-FEFO-ORDER-BY.

  
| Group | Search path | Inventory |
| --- | --- | --- |
| GROUP1 | Pick Zones 4, 6, and 8 | Expires May 5, May 12, and May 16 |
| GROUP2 | Pick Zones 3, 5, and 7 | Expires May 1 and May 2 |
| GROUP3 | Pick Zones 9 and 10 | Expires April 30, May 3, and May 4 |

The inventory expiring on May 5 in GROUP1 would be allocated first because the application stops searching other absolute groups when it finds inventory in an absolute group. If there is insufficient inventory that expires on May 5, it uses the inventory expiring on May 12 and then on May 16 in that same group. If additional inventory is still needed, the application allocates the inventory expiring on May 1 from GROUP2, and so on.

**Note**: The example assumes that the inventory rotation method does not require all inventory on the order line to match the best date found. Instead, allocation will continue searching for the remaining inventory required to fulfill the order line. See [Inventory must match inventory rotation method](#Inventory_must_match_inventory_rotation_method).

**Example: Allocating in absolute date order without absolute groups**

For allocation search paths set to search Pick Zone 1, 2, and then 3, the following table provides an example of the absolute date processing order in which the application would search for allocatable inventory using ABSOLUTE-FEFO-ORDER-BY.

 
| Search path | Inventory |
| --- | --- |
| Pick Zone 1 | Expires May 12 |
| Pick Zone 2 | Expires April 30 |
| Pick Zone 3 | Expires May 5 |

The inventory expiring on April 30 would be allocated first, and then the inventory expiring on May 5, because for absolute date processing the application allocates the inventory that expires first, regardless of search path sequence.

**Note**: The example assumes that the inventory rotation method does not require all inventory on the order line to match the best date found. Instead, allocation will continue searching for the remaining inventory required to fulfill the order line. See [Inventory must match inventory rotation method](#Inventory_must_match_inventory_rotation_method).

**Example: Allocating in search path order**

For search paths set to search Pick Zone 1, 2, and then 3, the following table provides an example of the allocation search path order in which the application would search for allocatable inventory using FEFO-ORDER-BY.

 
| Search Path | Inventory |
| --- | --- |
| Pick Zone 1 | Expires May 12 |
| Pick Zone 2 | Expires April 30 |
| Pick Zone 3 | Expires May 5 |

The inventory expiring on May 12 would be allocated instead of the inventory expiring on April 30, because the application allocates the first inventory that it finds based on search path sequence.

**Example: Allocating locations**

When using absolute date processing, after selecting a pick zone, allocation sorts the locations to determine the one from which to allocate inventory. The following table provides a sample scenario.

  
| Search path | Location | Inventory |
| --- | --- | --- |
| Pick Zone 1 | LOC1A | 4 cases that expire April 30 |
| LOC2B | 4 cases that expire May 12 |
| Pick Zone 2 | LOC2A | 2 cases that expire May 5 |

If the order quantity is for 7 cases, then using ABSOLUTE-FEFO-ORDER-BY, the application would allocate 4 cases from LOC1A, 2 cases from LOC2A, and 1 case from LOC1B.

**Note**: The example assumes that the inventory rotation method does not require all inventory on the order line to match the best date found. Instead, allocation will continue searching for the remaining inventory required to fulfill the order line. See [Inventory must match inventory rotation method](#Inventory_must_match_inventory_rotation_method).

**Example: Allocating a specific pallet**

When using absolute date processing, if a location contains mixed expiration dates, the application allocates the specific pallet of inventory using FEFO that is closest to expiring. The following table provides a sample scenario.

  
| Location | LPN | Inventory |
| --- | --- | --- |
| LOCA | LPN100 | Expires May 5 |
| LPN101 | Expires April 30 |

The application allocates LPN101 and directs the operator to pick it.

## Outbound date window

An outbound date window is an amount of time in relation to inventory’s received date or expiration date during which inventory is considered the same age for allocation when one of the FEFO/FIFO/LEFO/LIFO or absolute FEFO/FIFO/LEFO/LIFO inventory rotation methods is selected.

An outbound date window can be defined for an order line, work order line, disassembly work order, bill of material (BOM) line, disassembly BOM, customer item, customer, customer type, item, client, allocation (default value for order allocations), and replenishment (default value for replenishment allocations). The application uses the date window defined for an entity based on the defined order of precedence. See [Allocation Inventory Selection](allocation-inventory-selection.md).

**IMPORTANT**: The **Enable Outbound Date Window** field in the allocation inventory selection configuration must be set to Yes for the outbound date window to take effect.

To enhance the efficiency of inventory rotation allocation processing, you can define a window of time (in minutes, hours, or days) in which inventory of different ages is considered the same age for allocation even if inventory that is closer to or matches the exact expiration or receiving date is available.

For example, if an outbound date window is defined, then the application processes allocation and picking in the following ways:

-   The application allocates inventory within the window from a single location, even if inventory closer to the preferred processing date exists in another location.
-   If an order line requires a full pallet, the application allocates a full pallet of inventory with expiration or receiving dates that fall within the configured window, even if partial pallets with expiration or receiving dates closer to the preferred processing date are available.
-   If a location contains inventory with different expiration dates, the application allows operators to pick inventory from the location, as long as the expiration dates for the inventory fall within the configured window. This process eliminates having to search for and pick inventory with a specific expiration date.

### Date window calculations

The following examples explain how the application calculates the outbound date window (time) for choosing inventory during allocation:

-   For FEFO and absolute FEFO, the time is added to the earliest expiration date. For example, if the earliest expiration date is 8 A.M. on January 15 and the date window is three days, then inventory that expires up to 8 A.M. on January 18 is considered the same date for processing.
-   For FIFO and absolute FIFO, the time is added to the earliest received date. For example, if the earliest received date is 8 A.M. on January 15 and the date window is three days, then inventory that was received up to 8 A.M. on January 18 is considered the same date for processing.
-   For LEFO and absolute LEFO, the time is subtracted from the latest expiration date. For example, if the latest expiration date is 8 A.M. on January 15 and the date window is three days, then inventory that expires up to 8 A.M. on January 12 is considered the same date for processing.
-   For LIFO and absolute LIFO, the time is subtracted from the latest received date. For example, if the latest received date is 8 A.M. on January 15 and the date window is three days, then inventory that was received up to 8 A.M. on January 12 is considered the same date for processing.

## Movement zones for absolute inventory rotation allocation

The application supports the ability to fulfill order lines with the first inventory to expire and to ensure that the oldest inventory is shipped prior to newer inventory. The application supports these requirements by providing absolute inventory rotation methods, such as absolute first-expired, first-out (absolute FEFO) or absolute first-in, first-out (absolute FIFO). Inventory rotation methods can be assigned to order lines, items, customers, and customer types as well as allocation and replenishment processing. During allocation, the application attempts to fulfill a request for an absolute inventory rotation method by searching all appropriate search paths or absolute groups to find the inventory that is closest to the preferred processing date.

You can expand the search for inventory to satisfy an absolute inventory rotation method to locations that do not belong to an allocation search path. You do this through the configuration of movement zones for absolute inventory rotation method allocation, using the **Non Allocation Search Path Zones for Absolute** field. This configuration enables you to select, for the warehouse or by client, the movement zones to include in the search.

The following types of movement zones can be selected:

-   A movement zone that is not assigned to a shipping or replenishment allocation search path. During the allocation of an order or replenishment pick, the application checks for better inventory from this zone before allocating inventory from a shipping or replenishment allocation search path.
-   A movement zone that is not assigned to a shipping allocation search path, but is assigned to a replenishment allocation search path. The application checks for better inventory from this zone before allocating inventory from a shipping allocation search path, but not before allocating replenishments. The reason is that the zone is already assigned to a replenishment search path.

You can select movement zones, for example, that contain pickup and deposit (P&D) locations, pallet build locations, or RF devices. If allocation finds better inventory in one of these movement zones, it generates a short allocation until the inventory can be moved to a pick location to fulfill the request.

Replenishment processing also considers inventory in the selected movement zones when fulfilling requests based on an absolute inventory rotation method. The following processes take place when non-search path movement zones are configured for consideration:

-   Allocation includes reserve inventory (residing in a movement zone configured for consideration) in its search to find inventory closest to the preferred processing date. If preferred inventory is found in reserve storage, then instead of using available inventory in a pickface, the application attempts to replenish a pickface with the preferred inventory to fulfill the request.
-   The application does not use excess inventory from a pallet replenishment that does not match the rotation method on the order line. Following a replenishment, the application evaluates the inventory that was deposited to the pickface. If multiple orders require the inventory, but the inventory cannot be used for an order line with an absolute inventory rotation method, then the application generates another replenishment for inventory that matches the date requirement.
-   The application considers the inventory rotation method and inventory available before generating picks and replenishments. For example, during the process of fulfilling a triggered replenishment, the inventory required for an order is deposited to a P&D location in a zone configured for consideration. If that inventory is the best match for the date required by the order line (based on absolute inventory rotation method), the application generates a short allocation instead of fulfilling the order line with the next best inventory that is already in a pickable location. The short allocation is fulfilled when the better inventory is moved to a pickable location.
-   If an absolute inventory rotation method is required for replenishments, then the application considers (in addition to storage locations) inventory in movement zones configured for consideration. This can include inventory, for example, that has yet to be put away (in P&D locations) as well as inventory in transit (on an RF device). For example, a top-off replenishment fails if the application finds inventory closer to the required date is in one of the selected movement zones.

During order allocation, the application also evaluates inventory that has been allocated to a replenishment pick. When an absolute inventory rotation method is required for an order line, allocation considers inventory that has been committed to existing replenishment picks before allocating inventory from an allocation search path. If the replenishment inventory is closer to the preferred processing date, then a short allocation is generated with a reason indicating that the preferred inventory is committed to a replenishment pick.

Whenever the application calculates the best date, it only considers inventory that is an exact match for allocation. For example, if inventory for LotA is closest to the preferred processing date, but allocation is searching for LotB, then it will not consider inventory for LotA.

When an allocation or replenishment fails because inventory is found outside of an allocation search path (in one of the movement zones configured for consideration), one of following reasons is displayed for short allocation or failed replenishment:

-   Older/New Inventory Outside of Search Path
-   Older/Newer Inventory Committed to Replenishment Pick

Allocation can take place when the inventory is moved to a pickable location.

## Inventory rotation allocation processing setup

You must perform the following tasks to configure inventory rotation allocation processing for allocating inventory for order lines, work order lines, and replenishments.

1.  Define the allocation inventory selection settings.
    
    -   Select how inventory is evaluated during allocation.
    -   Enable and define a default outbound date window.
        
        **IMPORTANT**: If you set the **Enable Outbound Date Window** field to No, then even though you may have outbound date windows defined at several levels, they have no effect on application processing.
        
    -   Define the precedence that determines which outbound date window is used if it is defined at several levels. The precedence determines the order in which the application enforces the outbound date window when allocating order lines for which a FEFO/FIFO/LEFO/LIFO or absolute FEFO/FIFO/LEFO/LIFO inventory rotation method has been selected. It determines, for example, whether the value on the order line overrides the value for the customer item, whether the value for the customer item overrides the value for the customer, and so on.
        
        **Note**: The precedence that determines which inventory rotation method is used is not configurable. See [Inventory rotation allocation processing](#Inventory_rotation_allocation_processing).
        
        The application considers the outbound date window and the inventory rotation method separately, so if there is a value defined for one but not the other at a certain level, the application moves to the next level in order of precedence to locate the missing value. For example, if the top two levels in order of precedence are Order Line and Customer Item, respectively, the application would consider the values defined for the order line first. If the order line specified an outbound date window but no inventory rotation method, the application would use the outbound date window at the order line level, and then use the rotation method defined at the next level in order of precedence.
        
    -   Configure the location sort, which defines the sequence in which allocation chooses available inventory for allocation.
    -   To include non-search path movement zones during the allocation of inventory using an absolute inventory rotation method, select the zones to search. For example, you can select movement zones that contain pickup and deposit (P&D) locations or pallet build locations. If the application finds inventory in one of the movement zones, it generates a short allocation until the inventory can be moved to a pickable location. Non-search path movement zones also apply to the allocation of replenishments. See [Movement zones for absolute inventory rotation allocation](#Movement_zones_for_absolute_inventory_rotation_allocation).
    
    See [Allocation Inventory Selection](allocation-inventory-selection.md).
    
2.  Configure the inventory rotation method and outbound date window for each of the levels to which it should be applied.
    
    **IMPORTANT**: The regular and absolute FEFO and LEFO methods of inventory rotation are only supported for date-tracked inventory that is assigned to an aging profile with an **Expired** status defined.
    
    -   **Order line**: Values are defined on the order line.
    -   **Work order line**: Values are defined on the work order line.
    -   **Work orders**: Values for disassembly work orders are defined on the work order.
    -   **Bill of materials (BOM) detail**: Values are defined on the bill of material detail.
    -   **Bill of materials**: Values for disassembly BOMs are defined on the bill of material.
    -   **Customer item and customer**: Values are defined in the customer configuration. See [Existing Customers](../../partners/customers/existing-customers.md).
    -   **Customer type**: Values are defined in the customer type configuration. See [Customer Types](../../partners/customers/customer-types.md).
    -   **Item**: Values are defined in the item configuration. See [Items](../../inventory/items/items.md).
    -   **Client**: Values are defined in the client configuration. See [Clients](../../partners/clients.md).
    -   **Allocation Configuration**: Values are defined in the allocation inventory selection configuration. These values are used if a value is not specified for any of the other levels. See [Allocation Inventory Selection](allocation-inventory-selection.md).
3.  Configure replenishments for inventory rotation allocation processing.
    
    You use the replenishment settings configuration to define the default inventory rotation method for replenishments, which is used for replenishment allocation only if an inventory rotation method is not defined at any other level. You can also specify an outbound date window, which is used based on the pre-defined order of precedence. See [Replenishment Settings](../../inventory/replenishments/replenishment-settings.md).
    

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
