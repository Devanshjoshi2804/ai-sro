---
title: "Procedures for inventory issues"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/procedures_for_inventory_issues.htm"
source: "/content/procedures_for_inventory_issues.htm"
toc_path:
  - "Warehouse Management"
  - "Inventory"
  - "Inventory Issues"
  - "Procedures for inventory issues"
sections:
  - "Manage inventory that is not receivable"
  - "Manage inventory that is not pickable"
  - "Manage inventory for not shippable items"
  - "Manage expiring inventory"
  - "Manage locations in error"
  - "Manage mixing violations"
  - "Manage items without a valid storage location"
  - "Manage inventory in override locations"
  - "Manage damaged inventory"
  - "Manage out of sequence inventory"
  - "Inventory issues fields"
  - "Not Receivable fields"
  - "Not Pickable fields"
  - "Not Shippable fields"
  - "Expiring fields"
  - "Locations in Error fields"
  - "Mixing Violations fields"
  - "No Location fields"
  - "Location Overrides fields"
  - "Damaged fields"
  - "Out of Sequence fields"
images: []
source_sha1: e91fac43c035b51e41a666a96ee1eee2ea31a7f3
---
# Procedures for inventory issues

The following procedures can be performed on the issues identified on the Inventory Issues page.

## Manage inventory that is not receivable

For a description of the issue, see [Inventory issue: Not Receivable](../inventory-issues.md).

1.  Select **Inventory > Inventory Issues > Not Receivable**.
2.  View the information in the [Not Receivable fields](#Not_Receivable_fields).
3.  To view additional item details or to perform actions on an item:
    1.  In the grid, click an item, and view the item information. See [View detailed item information](../../shared-functions/inventory/procedures-for-items.md).
    2.  Perform one or more of the following tasks:
        -   To maintain the item, see [Maintain an item](../../shared-functions/inventory/procedures-for-items.md).
        -   To apply a hold to the item, see [Apply a hold to inventory](../holds/procedures-for-holds.md).
        -   To release a hold from the item, see [Release a hold from inventory](../holds/procedures-for-holds.md).
        -   To generate a cycle count for the item, from the **Actions** drop-down list, select **Generate Cycle Count**, and then click **OK**.
        -   To generate a replenishment for the item, from the **Actions** drop-down list, select **Generate Replenishment**, and then click **OK**.

## Manage inventory that is not pickable

For a description of the issue, see [Inventory issue: Not pickable](../inventory-issues.md).

1.  Select **Inventory > Inventory Issues > Not Pickable**.
2.  View the information in the [Not Pickable fields](#Not_Pickable_fields).
3.  To view a location, in the grid, click the location. The location details are displayed.
4.  To perform actions on the location, see [Procedures for locations](../../shared-functions/inventory/procedures-for-locations.md).

## Manage inventory for not shippable items

For a description of the issue, see [Inventory issue: Not shippable](../inventory-issues.md).

1.  Select **Inventory > Inventory Issues > Not Shippable**.
2.  View the information in the [Not Shippable fields](#Not_Shippable_fields).
3.  To view an LPN, in the grid, click the LPN. The LPN details are displayed.
4.  To perform actions on the LPN, see [Procedures for LPNs](../../shared-functions/inventory/procedures-for-lpns.md).

## Manage expiring inventory

For a description of the issue, see [Inventory issue: Expiring](../inventory-issues.md).

1.  Select **Inventory > Inventory Issues > Expiring**.
2.  Select the date range to view.

**Note**: By default, the page displays the inventory that will expire over the next 30 days starting from the current date.

4.  View the information in the [Expiring fields](#Expiring_fields). The grid provides a link to the number of LPNs associated with each item.
5.  To view the LPN details, click the LPN value. To perform actions on the LPN, see [Procedures for LPNs](../../shared-functions/inventory/procedures-for-lpns.md).

## Manage locations in error

For a description of the issue, see [Inventory issue: Locations in error](../inventory-issues.md).

1.  Select **Inventory > Inventory Issues > Locations in Error**.
2.  View the information in the [Locations in Error fields](#Locations_in_Error_fields).
3.  To view a location, in the grid, click the location. The location details are displayed.
4.  To perform actions on the location, see [Procedures for locations](../../shared-functions/inventory/procedures-for-locations.md).

## Manage mixing violations

For a description of the issue, see [Inventory issue: Mixing violations](../inventory-issues.md).

1.  Select **Inventory > Inventory Issues > Mixing Violations.**
2.  View the information in the [Mixing Violations fields](#Mixing_Violations_fields).
3.  To view multiple violations for a location, in the grid, expand the location.
4.  To view a location, in the grid, click the location. To perform actions on the location, see [Procedures for locations](../../shared-functions/inventory/procedures-for-locations.md).

## Manage items without a valid storage location

For a description of the issue, see [Inventory issue: No location](../inventory-issues.md).

1.  Perform one of the following tasks:
    -   Select **Receiving > Receiving Issues > No Location**.
    -   Select **Inventory > Inventory Issues > No Location**.
2.  View information in the [No Location fields](#No_Location_fields).
3.  To initiate putaway for an item:
    1.  In the No Location grid, click the item. The item details are displayed.
    2.  In the LPNs Affected grid, select the check box next to the inventory for which to search for a storage location.
    3.  Click **Storage Location Search**. The search results are displayed. If successful, the Location Search Results window is displayed and shows the location that was found. Directed work is created to move the inventory if there is a defined movement path for the inventory from its current location to the storage location that was found.
4.  To view search results and the storage rules that were used for an LPN:
    1.  In the No Location grid, click an item, and then in the LPNs Affected grid, click an LPN.
    2.  View information in the [Search Results fields](../../receiving/receiving-issues/procedures-for-receiving-issues.md).
    3.  To view the storage zone rules that were applied to find a storage location for the inventory, select **Storage Rules Used**, and view information in the [Storage Rules Used fields](../../receiving/receiving-issues/procedures-for-receiving-issues.md).
    4.  To view additional inventory details, select **Inventory Attributes**, and view information in the [No Location Inventory Attributes fields](../../receiving/receiving-issues/procedures-for-receiving-issues.md).
5.  To view additional item details or to perform actions on an item or LPN:
    1.  In the No Location grid, click an item, and view information in the [LPNs Affected fields](../../receiving/receiving-issues/procedures-for-receiving-issues.md).
    2.  Select **Item**, and view the item information. See [View detailed item information](../../shared-functions/inventory/procedures-for-items.md).
    3.  To perform actions on an item, select **Summary**, and perform one or more of the following tasks:
        -   To maintain the item, see [Maintain an item](../../shared-functions/inventory/procedures-for-items.md).
        -   To apply a hold to the item, see [Apply a hold to inventory](../holds/procedures-for-holds.md).
        -   To release a hold from the item, see [Release a hold from inventory](../holds/procedures-for-holds.md).
        -   To generate a cycle count for the item, from the **Actions** drop-down list, select **Generate Cycle Count**, and then click **OK**.
        -   To generate a replenishment for the item, from the **Actions** drop-down list, select **Generate Replenishment**, and then click **OK**.
    4.  To perform actions on an LPNS, select **LPNs**, and then see [Procedures for LPNs](../../shared-functions/inventory/procedures-for-lpns.md).

## Manage inventory in override locations

For a description of the issue, see [Inventory issue: Location overrides](../inventory-issues.md).

1.  Select **Inventory > Inventory Issues > Location Overrides.**
2.  View the information in the [Location Overrides fields](#Location_Overrides_fields).
3.  To view or modify an item:
    1.  In the grid, click the item.
    2.  To perform actions on the item, see [Procedures for items](../../shared-functions/inventory/procedures-for-items.md).
4.  To view or modify an LPN:
    1.  In the grid, click the LPN.
    2.  To perform actions on the LPN, see [Procedures for LPNs](../../shared-functions/inventory/procedures-for-lpns.md).
5.  To view or modify a location:
    1.  In the grid, click the system location.
    2.  To perform actions on the location, see [Procedures for locations](../../shared-functions/inventory/procedures-for-locations.md).

## Manage damaged inventory

For a description of the issue, see [Inventory issue: Damaged](../inventory-issues.md).

The Damaged display shows the inventory that is currently in damaged status.

1.  Select **Inventory** ** > Inventory Issues > Damaged**.
    
2.  Select the date range to view the list of damaged items.
    
3.  View the information in the [Damaged fields](#Damaged_fields).
    
4.  To view or modify an LPN, in the grid, click the LPN. To perform actions on the LPN, see [Procedures for LPNs](../../shared-functions/inventory/procedures-for-lpns.md).
    

## Manage out of sequence inventory

For a description of the issue, see [Inventory issue: Out of sequence](../inventory-issues.md).

1.  Select **Inventory > Inventory Issues > Out of Sequence**.
2.  View the information in the [Out of Sequence fields](#Out_of_Sequence_fields).
3.  In the grid, click the location in which the inventory to move is stored. The location details are displayed.
4.  Click **LPNs**, and then [Move inventory](../../shared-functions/inventory/procedures-for-lpns.md).

## Inventory issues fields

### Not Receivable fields

 
| Field | Description |
| --- | --- |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Date | Date and time that the user attempted to receive the item. |
| Expected | Quantity of the item expected to be received into the warehouse. |
| Footprint | Name that identifies a footprint, which describes the packaging dimensions and units of measure for the item with which it is associated. |
| Item Family | Identifier used to group similar items together. Typically, all of the items within a family have the same material handling characteristics. |
| Inbound Order | Identifier for an inbound order or planned inbound order that is associated with a specific supplier. |
| Inbound Order Line | Unique identifier for an inbound order line. The order line is the section of an order that provides detailed information about an individual item that the order requests. |
| User | User ID of the person who attempted to receive the item. |

### Not Pickable fields

 
| Field | Description |
| --- | --- |
| Current Location | Location in which the inventory currently resides. |
| Pick Zone | Name of a pick zone. A pick zone represents a group of locations that share the same attributes for picking, such as the LPN level at which picks can be allocated, the cartonization group to which it belongs, and whether the location supports replacement picks and pre-inventory allocation. The search path searches pick zones when attempting to find inventory for allocation. |
| Zone not in Search Path | The **Resolve in Configuration** text in this column indicates that the pick zone is not assigned to an allocation search path rule. This issue prevents the application from allocating inventory from locations assigned to the pick zone. |
| Location Out of Service | The **Resolve in Location** text in this column indicates that the location is either disabled or in an error status, both of which prevent inventory activities such as allocation, picking, and putaway from taking place in the location. |
| Location not Pickable | The **Resolve in Location** text in this column indicates that the storage location is not configured to be a pickable location (the **Pickable** field is set to No). |
| No Pick Zone Assigned | The **Resolve in Configuration** text in this column indicates that the location is not associated with a pick zone. If the location is not associated with a pick zone, it is not included in an allocation search path and the application will not find the location when attempting fulfill an order. |
| UOM Not Pickable | The **Resolve in Configuration** text in this column indicates that the location is associated with a pick zone on an allocation search path rule, but the rule does not support picking inventory in the unit of measure (UOM) that the order requires. |

### Not Shippable fields

 
| Field | Description |
| --- | --- |
| LPN | Unique identifier for inventory. Typically, an LPN refers to a pallet; however, it can refer to inventory received at less than pallet quantity. The LPN is the license plate by which the inventory is tracked in the facility. |
| Departure | Date and time that the transport equipment associated with a load is scheduled to depart from the warehouse. |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Client | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. |
| Location | Unique name for a location within the facility that is used to receive, store, process, or ship inventory. |
| Reason | Reason that the item cannot be shipped. For example, a hold that prevents shipping may be assigned to the item. |

### Expiring fields

 
| Field | Description |
| --- | --- |
| Expiration Date | Date on which the inventory will expire. The expiration date is determined by the aging profile or shelf life assigned to the item configuration. The date is stored in the database and displayed in the web client in the original captured time zone, not converted to a different time zone, such as a user preferred time zone. |
| Received | Date on which the inventory was received into the warehouse. If the inventory was received on multiple dates, then this field displays "Many." |
| Days to Expire | Number of days remaining until the inventory expires, based on the aging profile or shelf life defined in the item configuration. |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Client | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. |
| Quantity | Quantity of inventory that will expire. |
| LPNs | Identifier for an LPN or a value that represents a quantity of LPNs. |
| Locations | Number of locations in which the inventory resides. |
| Aging | Name of the aging profile representing the aging process assigned to the inventory. An aging profile defines the status transitions that automatically occur over time as date-tracked inventory ages. The aging profile can also calculate the expiration date of inventory for this item when it is received (based on the expired status configured for the aging profile). |

### Locations in Error fields

 
| Field | Description |
| --- | --- |
| Location | Unique name for a location within the facility that is used to receive, store, process, or ship inventory. |
| Date | Date and time at which the location was set to the Error status. |
| User | User who set the location to the Error status. |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Quantity | Quantity of inventory residing in the location. |

### Mixing Violations fields

 
| Field | Description |
| --- | --- |
| Location | Unique name for a location within the facility that is used to receive, store, process, or ship inventory. |
| Storage Zone | A storage zone represents a group of locations that have the same attributes (consolidation, item mixing, date control, and others) for storing inventory. |
| Violations | Attribute that represents the type of mixing restriction violation that exists in the location. If more than one violation exists, then a number is displayed. Click the number to display the attributes that violate the mixing restrictions. |
| Client | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. |
| Quantity | Quantity of the item in the location. |
| LPNs | Identifier for an LPN or a value that represents a quantity of LPNs. |

### No Location fields

 
| Field | Description |
| --- | --- |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Received | Quantity of inventory received for the item that does not have any location. |
| Item Footprint | Name that identifies a footprint, which describes the packaging dimensions and units of measure for the item with which it is associated. |
| Item Family | Identifier used to group similar items together. Typically, all of the items within a family have the same material handling characteristics. |
| Supplier | Identifier for a supplier. A supplier can be an individual, organization, or another warehouse within your own organization from which you repeatedly receive inventory or handling units. |
| Inbound Order | Identifier for an inbound order or planned inbound order that is associated with a specific supplier. |
| Location | Location in which the inventory currently resides. |
| Status | Quality status of an item. Defines the quality or disposition of the item. |

### Location Overrides fields

 
| Field | Description |
| --- | --- |
| Item | Unique code that is used to identify inventory. The item description and, for a 3PL environment, the item client ID are also displayed. |
| Date | Date and time at which the operator chose to override the application-directed deposit location and deposited the inventory to a user-selected location. |
| LPN | Unique identifier for inventory. Typically, an LPN refers to a pallet; however, it can refer to inventory received at less than pallet quantity. The LPN is the license plate by which the inventory is tracked in the facility. |
| Quantity | Quantity of inventory on the LPN. |
| User Location | Location to which the user deposited the inventory after overriding the application-directed location. |
| System Location | Location that the application selected for the inventory deposit. |
| User | User who deposited the item. |
| RF User Reason | Code that identifies why the user chose to deposit the LPN in a location other than the application-directed location. |
| Cycle Count | A check mark indicates that a cycle count was generated in the application-selected location. This occurs if the selected reason is configured to generate a cycle count. |

### Damaged fields

 
| Field | Description |
| --- | --- |
| Date | Date and time at which the inventory was set to a damaged status. |
| LPN | Unique identifier for inventory. Typically, an LPN refers to a pallet; however, it can refer to inventory received at less than pallet quantity. The LPN is the license plate by which the inventory is tracked in the facility. |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Quantity | Quantity of inventory on the LPN. |
| Inventory Status | Value that defines the quality or disposition of the inventory. |
| Reason | Reason that the inventory was set to a damaged status during receiving or status change operation. |
| User | User ID, first name, and last name of the person who set the inventory to damaged status. |
| Current Location | Location in which the inventory currently resides. |
| Damaged Location | Location in which the inventory was identified as damaged. |

### Out of Sequence fields

 
| Field | Description |
| --- | --- |
| Location | Unique name for a location within the facility that is used to receive, store, process, or ship inventory. |
| Aisle | Identifier for a passageway in the facility where operators and equipment move between racks or blocks of locations, typically to put away or pick inventory. You typically define aisles and then, in the process of defining storage locations, you can assign locations to the aisle in which they are located (a single location can be assigned to only one aisle). |
| Bay | Identifier used in a location numbering scheme to group locations typically by the type of racking that is present (such as flow racks, floor locations, or shelving), the number of pick levels, and the size or appearance of the racking. |
| Level | Identifier used in a location naming scheme to identify the level in a multilevel rack or storage aisle. |
| Item Class Name | Item class to which the item belongs. An item class is a category that can be used to group items for processing typically based on matching characteristics, such as hazardous or flammable material. You can assign an item class to an item even if inventory for the item exists in the warehouse. See [Item Classes](../../configuration/inventory/items/item-classes.md).<br > **IMPORTANT**: Warehouse Management designation of hazardous materials related to this functionality in no way implies compliance with federal or international regulations pertaining to the storage, processing, and transport of such materials. |
| Item Class Sequence Min | Minimum allowable item class level for inventory to be stored in the location. For example, assume there is a bay with 3 levels of storage. Inventory with an item class level of 2 is stored on the first level, and inventory with item class level 6 is stored on the third level. The second level is empty. With item class levels, a lower class cannot be stored above a higher class. Therefore, **Item Class Sequence Min** for the second level is 2, because it must have the same class level or higher than the inventory below it. The **Item Class Sequence Max** for the second level is 6, so as not to exceed the item class level stored on level 3. |
| Item Class Sequence Max | Maximum allowable item class level for inventory to be stored in the location. For example, assume there is a bay with 3 levels of storage. Inventory with an item class level of 2 is stored on the first level, and inventory with item class level 6 is stored on the third level. The second level is empty. With item class levels, a higher class cannot be stored beneath a lower class. Therefore, the **Item Class Sequence Max** for the second level is 6, so as not to exceed the item class level stored on level 3. The **Item Class Sequence Min** is 2, because inventory on the second level must have the same class level or higher than the inventory below it. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2023 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
