---
title: "Storage Zones"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/storage_zones.htm"
source: "/content/storage_zones.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inbound"
  - "Storage"
  - "Storage Zones"
sections:
  - "Narrow aisle inventory movement and storage configuration points"
  - "Zone consolidation"
  - "Add or modify a storage zone"
  - "Delete a storage zone"
  - "Consolidate zones"
  - "Storage Zone fields"
images: []
source_sha1: 8704009d13a5d34426bf94bcfc97f2698ddc73ff
---
# Storage Zones

A storage zone represents a group of locations that have the same attributes (consolidation, item mixing, date control, and others) for storing inventory. Any location that is used to store inventory must belong to a storage zone.

Storage locations are typically grouped into zones based on the type of inventory stored there, so that they can be used in directed putaway processing. Directed putaway uses search path rules to find the optimal storage zone for inventory. Therefore, it is useful to organize locations into storage zones based on one or more attributes (item, item family, item family group, client, supplier, handling unit type, LPN level, and so on) of inventory that is stored in the zone.

Storage zones and storage locations are used for the following warehouse processes:

-   **Counting**: Storage zone locations can be included in cycle counts.
-   **Inventory mixing**: Mixing restrictions apply to storage locations, and can be configured for specific storage zones, buildings, and the warehouse.
-   **Movement paths**: Storage zone locations can be included as intermediate stops (hops) on a movement path.
-   **Picking**: Storage zone locations can be included in picking zones for the purpose of inventory allocation, picking, and replenishment.
-   **Putaway**: Storage zones can be specified on search paths used to direct inventory to proper storage locations during putaway.
-   **Staging**: Storage zones can include staging locations for storing inventory temporarily prior to loading.

## Narrow aisle inventory movement and storage configuration points

You can configure the application to achieve an optimal flow of inventory in and out of narrow aisle storage locations. For example, the most efficient flow may be to direct inbound inventory to a pickup and deposit (P&D) location at one end of the aisle. An operator using narrow-aisle material handling equipment can move inventory to locations within the aisle. The operator uses the same equipment to pick outbound inventory and move it to a P&D location at the other end of the aisle. Another operator can use non-specialized equipment to move outbound inventory to its next destination, such as staging.

The following tasks describe the points at which you can configure the application for optimal inventory management in narrow aisle storage locations:

1.  **Work Areas and Work Zones**: You create work areas and work zones for the purpose of work management and enforcement of equipment limits. For example, create a work zone that consists of all the locations on one side of the narrow aisle, create a second work zone for the locations on the other side of the aisle, and then create a work area that consists of only these two work zones. This allows you to configure the application to direct operators to work in their current aisle before being moved to another aisle, and to the side of the aisle in which they are located. See [Work Areas](../../work/work/work-areas.md) and [Work Zones](../../work/work/work-zones.md).
2.  **Equipment limits**: Specify the maximum number of material handling vehicles, by equipment type, allowed in a work area or work zone at one time. The application does not release directed work that exceeds that limit. You assign the narrow aisle (VNA) location access group to the equipment allowed to access locations to which the same location access group is assigned. See [Equipment Limits](../../work/work/equipment-limits.md).
3.  **Movement zones**: Create movement zones for each set of locations to and from which inventory needs to be moved. For example, to ensure that inventory picked up from the left side P&D is deposited to the left side of the aisle, create a movement zone that contains the locations on the left side of the aisle, and another movement zone for the left side P&D location. Movement zones should also be defined for staging and dock locations. See [Movement Zones](../../inventory/movement/movement-zones.md).
4.  **Movement paths**: When you define movement paths, you can specify a P&D movement zone as a hop to which inventory must be deposited during inbound or outbound processing. For example, if special equipment is used within the narrow aisle, then inbound inventory could be deposited to a P&D location so that the equipment can move it to the storage location in the aisle. Similarly, the equipment is used to pick outbound inventory and deposit it to a P&D location, where other equipment can be used to move it to the next destination, such as staging. See [Movement Paths](../../inventory/movement/movement-paths.md).
5.  **Storage zones**: All of the locations within the narrow aisle (not including the P&D locations) could be included in one storage zone. This allows them to share configurations related to how inventory is stored in a narrow aisle. See [Storage Zones](#).
6.  **Pick zones**: All of the locations within the narrow aisle (not including the P&D locations) could be included in one pick zone. This allows them to share configurations related to how inventory is picked in a narrow aisle. See [Pick Zones](../../outbound/allocation/pick-zones.md).
7.  **Locations types**: For narrow aisle P&D locations, use the capacity-tracked P&D location type (**Track Capacity** field is set to Yes) so that the application can evaluate capacity when determining whether to release work. See [Location Types](../../warehouse/locations/location-types.md).
8.  **P&D locations**: For narrow aisle P&D locations, specify location dimensions and maximum weight, and set capacity to be tracked. These configurations allow the application to determine the best location for inventory based on size and weight, and to release allocated picks based on available capacity in the P&D locations. See [Pickup and Deposit Locations](../../warehouse/locations/pickup-and-deposit-locations.md).
9.  **Storage locations**: For narrow aisle storage locations, specify location dimensions and maximum weight. These configurations allow the application to determine the best location for inventory based on size and weight. See [Storage Locations](../../warehouse/locations/storage-locations.md).
10.  **Storage sequence**: You can define the sequence in which the application selects locations to store inventory. The sequence is useful for narrow aisle storage zones, for example, to direct the application to fill all the locations in one aisle before filling the next aisle, or to distribute inventory across multiple aisles. See [Configure storage sequences](../../warehouse/locations/location-sequences.md).
11.  **Work operation**: You can create a narrow aisle storage work operation and apply it where necessary to prevent specialized equipment from leaving the narrow aisle to complete other work. You authorize vehicles for the operation that can perform work in the narrow aisle. All P&D locations that are used for inventory moving into the narrow aisle should be configured to generate work with this operation. The specialized equipment should be authorized for both picking and the narrow aisle storage operations. See [Work Operations](../../work/work/work-operations.md).

## Zone consolidation

You can use the Consolidate action, available from any zone configuration grid, to consolidate zones that share a common configuration into a single (original) zone. You can consolidate the following types of zones: count zones, movement zones, pick zones, storage zones, and work zones. See [Consolidate zones](#Consolidate_zones).

When you select a zone and use the Consolidate action, the application presents a list of zones that have a configuration that matches the selected (original) zone. You can then select one or more of the matching zones to consolidate to the original zone.

During consolidation, the application performs the following tasks:

-   Updates all the configurations and references for the zones that are being consolidated to now use the original zone. For example, if PickZone2 and PickZone3 are consolidated into PickZone1, then the locations assigned to PickZone2 and PickZone3 are reassigned to PickZone1.
-   Removes the consolidated zones and retains the original zone.
-   Displays a progress bar that shows the processing status of the consolidation.
-   When consolidation is complete, displays the list of any remaining consolidation candidates that match the original zone. This allows you to continue consolidating to the original zone.

The same process is available for location types using the location type configuration. See [Location type consolidation](../../warehouse/locations/location-types.md).

## Add or modify a storage zone

1.  Select **Configuration > Inbound > Storage > Storage Zones.**
2.  Perform one of the following tasks:
    -   To add a zone, from the **Actions** drop-down list, select **Add**.
    -   To modify a zone, in the grid, select the storage zone.
3.  Enter information in the [Storage Zone fields](#Storage_Zone_fields).
4.  Click **Layout** or **Next**.
5.  To draw the zone on the warehouse map for the selected building:
    1.  Click **View**, and then select the check box for each option that you want to display on the map.
    2.  Click **Draw**, and then move and size the shape on the page.
6.  Click **Finish**.
    
    **Note**: To assign locations to a storage zone, see the information on modifying multiple locations in [Location configuration process](../../warehouse/locations.md).
    

## Delete a storage zone

1.  Select **Configuration > Inbound > Storage > Storage Zones**.
2.  In the grid, select the check box next to the storage zone to delete.
3.  From the **Actions** drop-down list, select **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Consolidate zones

You use the following procedure to consolidate zones that have the same configurations into a single (original) zone. See [Zone consolidation](#Zone_consolidation).

**Note**: Zones cannot be consolidated if outstanding work references the selected zone.

1.  Perform one of the following tasks:
    -   For count zones, select **Configuration > Inventory > Counting > Count Zones.**
    -   For movement zones, select **Configuration > Inventory > Movement > Movement Zones.**
    -   For pick zones, select **Configuration > Outbound > Allocation > Pick Zones.**
    -   For storage zones, select **Configuration > Inbound > Storage > Storage Zones.**
    -   For work zones, select **Configuration > Work > Work > Work Zones.**
2.  In the grid, select the zone to which duplicate zones will be consolidated. This becomes the original zone that remains after the duplicate zones have been removed. This is also the zone to which references and configurations are reassigned.
3.  From the **Actions** drop-down list, select **Consolidate**. A list of zones that have the same configuration as the original zone are displayed.
4.  In the grid, select the check box next to the zones to consolidate. The selected zones will be removed after consolidation takes place.
5.  Click **Save**. The selected zones are removed, and the Consolidation page displays the remaining zones, if any, that match the original zone.

## Storage Zone fields

 
| Field | Description |
| --- | --- |
| Name | Name of the storage zone. |
| Description | Text that further describes the zone. |
| Building | Name of the building in which the zone resides. |
| Stocking UOM Dimensions | If Yes, then when the application searches for a storage location in the zone for quantities that are less than a pallet, the dimensions of the item’s stocking UOM are used in storage capacity calculations. The stocking UOM is defined in the item configuration, and the dimensions for the stocking UOM are defined in the item footprint configuration. If set to Yes, the stocking UOM dimensions are used regardless of the inventory quantity (full or partial pallet).<br > If No, then for quantities that are less than a pallet, the application uses the item's Case UOM dimensions in storage capacity calculations. For example, if a partial pallet is being stored, the application considers the quantity of cases to be deposited and the number of cases per tier (as defined on the item footprint), and then uses the Case UOM dimensions to determine the dimensions of the partial pallet. If set to No and the quantity is a full pallet, the application uses the Pallet UOM dimensions. |
| Mixing Rules | Defines whether the locations in the zone are used to store a single item at a time, mixed items, or items that are not pickable.<br>-   • **Single Item:** Mixing items is not allowed. The attributes of all inventory in the location must be identical.
<br>-   • **Mixed:** Mixing items is allowed, with the exception of attributes restricted by storage mixing restrictions. See [Storage Mixing Restrictions](storage-mixing-restrictions.md).
<br>-   • **Non-Pickable:** Mixing items is allowed, with the exception of attributes restricted by storage mixing restrictions; however, inventory in the location cannot be picked. Typically this value is used for ship staging or salvage locations. |
| Date Controlled | If Yes, then the application tracks the age of inventory for each date controlled item stored within the zone's locations. This is to ensure that all inventory stored in a location is within the same date window, as defined on the item. If set to Yes, then during the storage process, the application compares the age of the inventory on the LPN to the age of the inventory currently in the location to determine if the LPN fits within the defined date window for mixing inventory of different ages.<br > If No, then the application ignores the age of inventory for date controlled items when attempting to store it in the zone's locations. |
| Proximity | Defines how the application attempts to find a putaway location for inventory that is picked up in the storage zone. This field is only available when Warehouse Labor Management is integrated with Warehouse Management.<br>-   • **Proximity to empty/partially full primary pick location:**<br > The application attempts to put away inventory to an empty or partially-filled storage location that is closest to the item's assigned location, such as its primary pickface location. Select this option, for example, to minimize the travel time required to perform replenishments to the item's assigned location.
<br>-   • **Proximity to current/source location where product is picked up:**<br > The application attempts to put away inventory to an empty or partially-filled storage location closest the location from which the inventory was picked up. Select this option to minimize travel time to the putaway location. |
| Item Class Level Storage | If Yes, then the application considers the item class level for vertical storage when attempting to allocate a storage location in the zone. The item class level determines the level at which an item class can be stored in relation to other item class levels. With item class levels, 1 is the lowest possible level and must not be stored above any other item class level. Item class level 2 can be stored above item class level 1 but must not be stored above higher item class levels; and so on. Item class levels do not refer to specific physical levels of a bay, but instead represent a relative vertical position. Item class levels can be used to direct the storage of item classes in relation to one another, for example, to prevent contamination or the combination of materials that could prove hazardous.<br > For example, assume the application is attempting to allocate a storage location for inventory that belongs to item class level 5. Allocation finds a bay with 4 levels but the third level contains inventory that belongs to item class level 10. Since item class level 5 cannot be stored above item class level 10, the application can direct the inventory to a location only on the first or second level of this bay. If the application directs item class level 5 to the second level in the bay, then first level locations can only be allocated for an item class level 5 or lower, and the fourth level locations can only be allocated for an item class level 10 or higher.<br > If the application attempts to allocate a location for an item class that does not have an item class level assigned, then item class level is not considered for vertical storage.<br > **Note**: If you perform a mass update for locations in a storage zone enabled for item class level storage, then the **Aisle**, **Bay**, and **Level** fields cannot be modified.<br > If No, then the application does not consider item class level when allocating a storage location in the zone. |
| Automatic LPN Consolidation | If Yes, the application automatically consolidates inventory to an existing LPN in the destination location. The moved inventory assumes the attributes of the existing LPN unless the **Consolidate to Source LPN** field is set to Yes. Select Yes for each-pick and case-pick storage zones in which the operator is not required to enter an LPN to move inventory out of locations in the zone. Serialized items are not consolidated.<br>
**Notes**:

<br>

-   • Automatic LPN consolidation can take place if the pick zone is configured to require the operator to scan Sub-LPN Level or Detail LPN Level picks. If the pick zone is configured for LPN Level picks, then consolidation will not take place, even if **Automatic LPN Consolidation** is set to Yes.
<br>-   • If **Automatic LPN Consolidation** is set to Yes, then LPN-level consolidation happens regardless of whether the inventory satisfies the consolidation criteria defined in the inventory movement settings. However, sub-LPN and detail LPN consolidation only happens if the inventory satisfies the consolidation criteria.
<br>-   • The **Automatic LPN Consolidation** field on a storage zone and the **Attachment Strategy** field on a movement zone are mutually exclusive. To avoid unexpected behavior, if a location belongs to a storage zone with this field set to Yes, then the location's movement zone must be configured with the **Attachment Strategy** field set to Never Attach.
<br>

<br > If No, the application does not automatically consolidate inventory to an existing LPN in the destination location. |
| Manual Consolidation During Putaway | If Yes, the zone supports manual consolidation of LPNs. Select Yes if you allow operators to choose the LPN to which they deposit inventory to consolidate the inventory onto an existing LPN.<br > If No, manual consolidation is not allowed. |
| Consolidate to Source LPN | If Yes, then when consolidating a full LPN into this storage zone, the application retains the attributes of the source LPN and applies the source LPN's attributes to the inventory already in the destination location. This field does not apply when consolidating a partial LPN in which case the source inventory assumes the attributes of the LPN already in the destination location.<br > If No, then the inventory being consolidated into this storage zone assumes the attributes of the LPN already in the destination location.<br > This field is only available when the **Automatic LPN Consolidation** field is set to Yes. |
| Deposit Override - Set Location Full | If Yes, then when an operator overrides a deposit location with an override reason that is configured to change the location status to Full, the application allows the status change. Select Yes, for example, in pallet storage zones where the calculated capacity may overstate the amount of inventory a location can hold. This can occur, for example, when a stacking method (such as pyramid or interlock stacking) is used that does not fill the location to the capacity configured for the location but prevents additional inventory from being stored there.<br > If No, the location status is not changed to Full during a deposit location override, even if the override reason that is used is configured to set the location's status to Full. Select No, for example, in each and case storage locations where pallet stacking methods are not used.<br > See [Storage Override Reasons](storage-override-reasons.md). |
| Deposit Override - Set Maximum Location Capacity | If Yes, then when an operator overrides a deposit location with an override reason that is configured to set the location's maximum capacity to its current capacity, the application allows the change. Select Yes, for example, in pallet storage zones where an interlock or pyramid stacking method may be used. Use of these stacking methods can result in filling the location to the point where there is no more room for additional pallets, even though the application calculates that there is room based on the capacity configured for the location.<br > If No, the location's maximum capacity is not changed by an override reason, even if the reason is configured to change it. Select No, for example, in each and case storage locations where pallet stacking methods are not used.<br > See [Storage Override Reasons](storage-override-reasons.md). |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
