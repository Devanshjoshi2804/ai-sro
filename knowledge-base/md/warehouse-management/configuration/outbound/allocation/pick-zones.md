---
title: "Pick Zones"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/pick_zones.htm"
source: "/content/pick_zones.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Outbound"
  - "Allocation"
  - "Pick Zones"
sections:
  - "Allocate to empty process"
  - "Allocate to empty examples"
  - "Zone consolidation"
  - "Add or modify a pick zone"
  - "Delete a pick zone"
  - "Consolidate zones"
  - "Pick Zone fields"
images: []
source_sha1: d7f961d5ce825da14ba3728056e686a176f5a88b
---
# Pick Zones

A pick zone represents a group of locations that share the same attributes for picking, such as the LPN level at which picks can be allocated, the cartonization group to which it belongs, and whether the location supports replacement picks, starter pallets, and pre-inventory allocation. For a location to be considered pickable, it must be assigned to a pick zone.

Each pick zone can represent a different picking configuration. For example, you can define multiple pick zones for a series of bays (shelving units). If the bay is three levels high, each level could be defined as a different pick zone based on the inventory being stored there (such as pallets on one level, cases on another level, and heavy cases on another level).

Pick zones are assigned to allocation search paths to represent the source from which inventory is allocated to fulfill orders. The allocation search path determines the units of measure (UOMs) that can be allocated from a particular zone.

When you configure a pick zone, you define the attributes of the pick zone, the layout of the pick zone (as drawn on a warehouse or building map), and the locations that belong to the pick zone. A location can belong to only one pick zone.

## Allocate to empty process

The allocate to empty process is intended to be used in pick zones that have single-item locations, not pickface locations. This process can be used to override FEFO, FIFO, LEFO, and LIFO allocation of date-tracked inventory, but does not override absolute FEFO, FIFO, LEFO, and LIFO allocation of date-tracked inventory. The allocate to empty options apply to the allocation of an item only, not allocation by other item attributes such as lot and origin code.

Processing takes place according to the following options in the **Allocate to Empty Action** field:

-   **Allocation**: The application automatically sets and maintains a location's allocate to empty sequence, and users cannot change it. When the application sets a location's allocate to empty sequence, the location that is the primary source of allocation for an item will only be reset once the location is empty, even if the allocation that set it is canceled. Using the **Allocation** option also eliminates the possibility of having multiple primary locations. For example, if a location becomes the primary source of allocation for an item, it is the only primary source for the item in the pick zone; but once the location is empty and its allocate to empty sequence is reset, the application will allocate from another location. If you want to be able to designate which location should be second or third in line for allocating a specific item, you should select the **Manual** or **Manual and Allocation** option.
-   **Manual**: The application does not automatically set the allocate to empty sequence, but a user can manually set it for locations in the pick zone. Typically, you would allow manual updates to the allocate to empty sequence for locations in a pick zone if you want to select a specific location that needs to be emptied, or if you want to specify that certain inventory for an item needs to be allocated before other existing inventory. For example, if a specific location needs to be available for storing incoming inventory, you can set its sequence so that the application allocates from that location until it is empty. Similarly, if you want to ensure that a specific lot of an item is allocated immediately, you can set the storage location's allocate to empty sequence so that the application identifies it as the primary source of allocation.
-   **Manual** or **Manual and Allocation**: Both of these options allow you to manually set the allocate to empty sequence for a single location from which you want inventory to be allocated, or you can set the allocate to empty sequence for multiple locations containing the same item. Setting the allocate to empty sequence for multiple locations ensures that the locations are emptied in the order you want.
    
    For example, if there are three locations storing the same item that you want to allocate from until they are empty, you can set each location's allocate to empty sequence. In this scenario, the location with the lowest allocate to empty sequence would be the primary allocation source for the item until the location is empty. Then the application selects the next location for which you set sequence and allocates from the location with the lower (higher priority) sequence.
    

**Note**: If two or more locations have identical allocate to empty sequence numbers, the application evaluates the allocate to empty dates and uses the location that had its allocate to empty sequence set first as the primary allocation source.

## Allocate to empty examples

The following table is an example of three locations containing the same item in a pick zone that allows only manual updates to the allocate to empty sequence, meaning that each allocate to empty sequence is manually set by a user. When the application allocates the item from this pick zone, it begins with LOC-C because it has the lowest sequence. When LOC-C is empty and its sequence is cleared, the application allocates the item from LOC-B until it is empty, and then from LOC-A. After a location’s sequence is cleared and new inventory is stored there, you must manually set its allocate to empty sequence again if you want the location to hold allocation priority over other locations storing the same item in the pick zone.

 
| Location | Allocate to empty sequence |
| --- | --- |
| LOC-A | 800 |
| LOC-B | 700 |
| LOC-C | 600 |

If the locations are in a pick zone where only automatic updates are made to the allocate to empty sequence, you would not be able to specify which locations follow the initial location for allocation. The following table is an example of the application allocating from LOC-C first and setting its allocate to empty sequence to 1000. The sequence is not set for other locations storing the same item so that LOC-C remains the primary source for allocation. However, once LOC-C is empty, the application clears its allocate to empty sequence and determines the next location to allocate from using the allocation search path configurations.

 
| Location | Allocate to empty sequence |
| --- | --- |
| LOC-A | ‑ |
| LOC-B | ‑ |
| LOC-C | 1000 |

## Zone consolidation

You can use the Consolidate action, available from any zone configuration grid, to consolidate zones that share a common configuration into a single (original) zone. You can consolidate the following types of zones: count zones, movement zones, pick zones, storage zones, and work zones. See [Consolidate zones](#Consolidate_zones).

When you select a zone and use the Consolidate action, the application presents a list of zones that have a configuration that matches the selected (original) zone. You can then select one or more of the matching zones to consolidate to the original zone.

During consolidation, the application performs the following tasks:

-   Updates all the configurations and references for the zones that are being consolidated to now use the original zone. For example, if PickZone2 and PickZone3 are consolidated into PickZone1, then the locations assigned to PickZone2 and PickZone3 are reassigned to PickZone1.
-   Removes the consolidated zones and retains the original zone.
-   Displays a progress bar that shows the processing status of the consolidation.
-   When consolidation is complete, displays the list of any remaining consolidation candidates that match the original zone. This allows you to continue consolidating to the original zone.

The same process is available for location types using the location type configuration. See [Location type consolidation](../../warehouse/locations/location-types.md).

## Add or modify a pick zone

1.  Select **Configuration > Outbound > Allocation > Pick Zones**.
2.  Perform one of the following tasks:
    -   To add a pick zone, from the **Actions** drop-down list, select **Add**.
    -   To modify a pick zone, in the grid, click the pick zone.
    -   To copy a pick zone, in the grid, select the check box next to the pick zone, and then from the **Actions** drop-down list, select **Copy**.
3.  Enter information in the [Pick Zone fields](#Pick_Zone_fields).
4.  Click **Layout** or **Next**.
5.  To draw the zone on the warehouse map for the selected building:
    1.  Click **View**, and then select the check box for each option that you want to display on the map.
    2.  Click **Draw**, and then move and size the shape on the page.
6.  Click **Finish**.
    
    **Note**: To assign locations to a pick zone, see the information on modifying multiple locations in [Location configuration process](../../warehouse/locations.md).
    

## Delete a pick zone

1.  Select **Configuration > Outbound > Allocation > Pick Zones**.
2.  In the grid, select the check box next to the pick zone to delete.
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

## Pick Zone fields

 
| Field | Description |
| --- | --- |
| Zone Name | Name for a group of locations that share the same attributes for picking. |
| Description | Text that further describes the zone. |
| Building | Name of the building in which the zone resides. |
| Pre-Inventory Allocation (PIA) | If Yes, locations in the zone are enabled for pre-inventory allocation. Pre-inventory allocation (PIA) is a process in which picks are allocated from a pickface location before the necessary inventory physically exists at that location. With PIA enabled, if a pick location does not have inventory to complete an order, then the application generates demand-based replenishments from reserve storage locations to the pick location, and then generates picks based on the inventory pending to the pick location.<br > If No, then if there is insufficient inventory in the pick location, allocation will be shorted (fail) until the locations are replenished. |
| Allocate to Empty | If Yes, then when the application allocates an item from a location, that location is the primary source for allocating the item until the location is empty. For example, when allocate to empty is enabled, if five pallets of ITEM01 are stored in LOC-A and the application allocates four of them, then when the application needs to allocate ITEM01 again, it will first allocate the one remaining pallet from LOC-A before allocating ITEM01 from another location. If this field is set to Yes, then you define how the allocate to empty sequence is set in the **Allocate to Empty Action** field.<br > If No, the application does not allocate from the location until it is empty. |
| Allocate to Empty Action | Value that determines the method by which the allocate to empty sequence is set for the pick zone. Only available if the **Allocate to Empty** field is set to Yes.<br>-   • **Allocation:** Allocate to empty is enabled and the application automatically sets the allocate to empty sequence for a location. If selected, then when the application allocates an item from a location, that location's allocate to empty sequence is set to 1000 and it becomes the primary location for allocating that item until the location is empty. You cannot manually change the location's allocate to empty sequence but once the location is empty, its allocate to empty sequence is reset until the location is again selected for allocation**.**
<br>-   • **Disabled:** Allocate to empty is not used, and the application allocates inventory based on the allocation search path.
<br>-   • **Manual:** Allocate to empty is enabled but you must manually modify the allocate to empty sequence for a location. If selected, and you want the application to allocate from one location until it is empty before allocating from another location, you must manually modify the location's allocate to empty sequence so that it is earlier sequentially than the other location. Once the location is empty, the allocate to empty sequence is reset.
<br>-   • **Manual and Allocation:** Allocate to empty is enabled and the application automatically sets the allocate to empty sequence for a location. If selected, then when the application allocates an item from a location, that location's allocate to empty sequence is set to 1000 and it becomes the primary location for allocating that item until the location is empty. However, with this option selected, you can also manually change the location's allocate to empty sequence to better suit operational needs. Once the location is empty, its allocate to empty sequence is reset until the location is again selected for allocation. |
| LPN Level Picks | LPN level at which operators must scan picks in the pick zone.<br > **Note**: If the item being picked is tracked at an LPN level that is not selected in this field, operators may still be required to scan an identifier for that LPN level when performing a pick.<br>-   •
    
    **LPN Level**: Operators are required to scan or enter an LPN when removing inventory from the pick zone. Typically, an LPN refers to a pallet.
    
    <br>
    
    **Note**: If **LPN Level** is selected, then automatic consolidation will not take place even if the storage zone is configured for automatic LPN consolidation.
    
    <br>
<br>-   • **Sub-LPN Level**: Operators are required to scan or enter a sub-LPN when removing inventory from the pick zone. Typically, a sub-LPN refers to a case.
<br>-   • **Detail LPN Level**: Operators are required to scan or enter a sub-LPN when removing inventory from the pick zone. Typically, a detail LPN refers to an each or piece. |
| Replace Picks | If Yes, the pick zone supports replacing the source location of an outstanding pick with a source location in receiving to fulfill the pick. This process eliminates the intermediate step for storage by fulfilling a pick with inventory in a receiving location. For example, selecting Yes allows the application to automatically change the source location (typically in a storage area) of an outstanding pick or replenishment to a location in receiving (such as a receiving dock door or production location). This occurs when received inventory can be used to satisfy a pick. By sourcing the pick from receiving, the inventory can be moved directly from receiving to the customer order's destination location.<br > If No, the application does not attempt to automatically change the source location of an outstanding pick with a different source location. |
| Starter Pallet | If Yes, a pick from a location in the pick zone is eligible to be a starter pallet. A starter pallet is the first pallet in a picking tour, and is typically a large quantity base pick (such as a less than full pallet pick) upon which subsequent picks can be placed. See [Starter pallets](../picking/work-assignments.md).<br > If No, picks from the zone are not eligible to be used as starter pallets. |
| Visibility to Work Assignment Picks | If Yes, then when an operator begins a work assignment in the pick zone, the list of picks is displayed to the operator. This allows the operator to perform the picks out of sequence if necessary. This is useful, for example, to support equipment that can pick several layers at a time to build a pallet, because the picks can be completed in reverse order until the equipment is full. This process results in fewer deposits and still builds the pallet in the correct sequence.<br > If No, work assignment picks are displayed one at time for the operator to complete the picks in sequence. |
| Batch Limit | Maximum number of picks sent to the voice device in a single batch. A lower value (minimum of 10) means the device needs to request new batches from the application more often; however, this configuration allows the operator to be informed of picking errors more frequently and address them immediately. A higher value means the device needs to stop picking less often to request a new batch from the application; however, if the application is using one-way messaging, the operator is not informed of picking errors until the current batch is complete.<br > **Note**: You can define this field value in the general voice picking configurations and for a specific pick zone. The pick zone batch limit overrides the value defined in the voice picking configurations.<br > When the number of picks on a device falls to 50% of the configured value, the application sends another batch limit of picks to the device. Therefore, the number of picks currently on a voice device can fluctuate between 50% and 150% of the defined batch limit. For example, if the defined limit is 10, then when there are 5 picks remaining on a device, the application sends 10 more picks so the device has a total of 15 picks.<br > When the application creates a batch and adheres to the configured batch limit, it also considers the next pick in sequence (which would exceed the batch limit) to determine if it can be consolidated with the last pick in the previous batch based on item, location, and pick UOM. For example, assume the batch limit for voice picking is 10. If 11 separate picks exist for Item A from the same location and in the same picking UOM, then instead of sending separate batches to the voice device (one for the first 10 picks and another for the eleventh pick because it exceeds the limit), the application consolidates the quantity of the eleventh pick into the batch with the first 10 picks. The voice operator is then prompted with a single pick quantity to fulfill all 11 picks.<br > **Note**: The application continues to evaluate and consolidate the next pick in sequence until it no longer matches the last pick in the original batch, or until 25 additional picks have been added to the original batch. |
| Pick Validation Batch Size | Number of subsequent picks in a work assignment that the application pre-validates. Pick pre-validation is a process that determines whether inventory is available in a location prior to presenting the pick to an operator.<br > **Note**: You can define this field value in the general voice picking configurations and for a specific pick zone. The pick zone validation batch size overrides the value defined in the voice picking configurations.<br > For example, assume the **Pick Validation Batch Size** is 5. When a voice operator acknowledges a work assignment and is directed to the first pick location, the application pre-validates the first 5 picks. After the operator completes 4 of the picks, there is one pre-validated pick remaining, and the operator is directed to the fifth pick. At the same time, the application pre-validates the next 5 picks in the work assignment.<br > Set this field to a higher number in fast-moving or high-density picking environments to ensure the operator has a higher number of validated picks to complete over a short period of time. Alternatively, set this field to a lower number in slower moving picking environments or to reduce the need to skip or cancel picks that would fail validation. For example, if this field is set to 1 (default value) and the fourth pick requires a replenishment, then there is time for the replenishment to be completed before the application attempts to validate that pick. However, if the field was set to 4, then the fourth pick would fail validation without the replenishment completed, and the pick is subject to the fail action defined on the pick pre-validation scheme associated with the pick method. As another example, pick zones in which a voice device's connection to the application may be inhibited (such as a freezer) could be configured with a higher validation batch to reduce the number of transaction messages that are exchanged.<br > **Note**: This field has no effect if the picked message format between the voice device and application is ODR (outbound data record). The application only pre-validates the **Pick Validation Batch Size** if the message format is LUT (look-up table). If the ODR format is used, the application pre-validates all of the picks issued to the device. |
| Pick Multiple LPNs at Once | If Yes, then when there are multiple LPN-level (pallet) order picks or replenishment picks from the same location, the application groups the pick quantities based on selected criteria, if the equipment limit allows. When the operator is presented with the pick work, prior to acknowledging it, the grouped quantity is displayed on the RF Pickup Product At screen. Upon acknowledging the work, the operator is directed to pick a quantity of 1; however, the operator can continue picking pallets (scanning each one separately) until the grouped quantity has been picked.<br > **Note**: This configuration does not apply to LPN picks in a work assignment.<br > When this field is set to Yes, operators performing full pallet picks in the zone, such as with a fork truck, can perform multiple pallet picks at the same time, without acknowledging each pick separately. The application groups pallet picks with the highest priority first, and the grouped quantity will not exceed the equipment LPN limit.<br > For example, assume there are 4 single-pallet picks from a location that have matching values for the selected grouping criteria, and that the operator's fork truck has a limit of 3 LPNs. When the operator looks for directed work, the application groups 3 LPN picks to reach the equipment limit. That quantity (3) is displayed on the RF device with the source location prior to acknowledging the work. After acknowledgment, the operator can scan 3 LPNs (one by one), rather than picking 1 LPN at a time and requiring the application to look for additional work after each pick. However, the operator is not required to pick the entire grouped quantity, and the picked quantity can be deposited at any time.<br > If you set this field to Yes, then in the column that is displayed, select the check box next to the available criteria that must match for picks for be grouped together.<br > **Note**: If a pallet pick is manually assigned to an operator, the application can still group additional pallet picks that meet the grouping criteria with the initial pick. The operator can then pick the grouped quantity or can pick a lesser quantity.<br > If No, the application does not provide operators with the quantity on the acknowledgment screen; there is no visibility to multiple LPN picks from the same location. Therefore, operators must complete pallet picks individually, even when there are similar picks from the same location. Using the previous example, if this field is set to No, the operator would need to separately pick 3 LPNs (acknowledging each piece of pick work individually) from the same location. |
| Cartonization Group | Name of the cartonization group to which the pick zone belongs. A cartonization group is used to group pick zones from which inventory can be cartonized together. For example, your warehouse may have 10 pick zones in which you want to perform cartonization, but 5 of the pick zones are located close together on the north side of the building while the other 5 pick zones are located close together on the south side of the building. You can define 2 cartonization groups and assign one to the north pick zone and one to the south pick zones, so that product from the north 5 pick zones is cartonized together and product from the south 5 pick zones is cartonized together, separately from the north 5 pick zones. |
| Summary Count Back | If Yes, then when an operator performs a count back task in the pick zone, the system allows the inventory to be counted in summary (without tracking the lot, origin, revision level, or other inventory attributes). For example, if an operator picks less than a full pallet of inventory from a mixed-lot LPN, then when performing the count back, the operator can enter the total quantity of the remaining inventory once instead of counting each lot separately.<br > If No, then the operator must count the inventory for each lot, origin, and revision level separately. For example, if an operator picks less than a full pallet of inventory from a mixed-lot LPN, then when performing the count back, the operator must count and enter the quantity for each lot individually. When the inventory for one lot is confirmed, the operator can count and confirm inventory for the next lot, and so on.<br>
**Notes**:

<br>

-   • Setting this field to No may increase the time it takes an operator to perform the count, because the inventory may need to be physically separated by lot, origin, or revision level prior to performing the count.
<br>-   • If a user is configured to never perform a count back, then this field has no effect for that user, since the counts are never required.
<br>-   • If a user is configured to always perform count back, then this field determines how that user performs the count.
<br>-   • If a user is configured to perform a count back only if the item or location requires it, then this field determines how the count is performed. If neither the location nor item requires count back, then this field has no effect, since a count is not performed.
<br>

For more information on user configurations, see [Define the Warehouse Management Settings for a user](../../../../administration/system-administrator/authorization/users.md).

 |
| Count Back Location Quantity | If Yes, then when an operator completes a pick, the application requires the operator to count back the remaining quantity of the picked item in the entire location. Count back counts are performed only for the locations and items that require it, based on the count settings, and only by authorized users. For example, assume a location contains Item1 on LPN1 and LPN2, and Item2 on LPN3. If an operator picks Item1 from LPN1, then the operator is required to count back the remaining quantity of Item1 on LPN1 and LPN2. The operator does not count back Item2 on LPN3.<br > If No, then the operator is required to count back the remaining quantity of the picked item on the LPN from which it was picked. For example, assume a location contains Item1 on LPN1 and LPN2. If an operator picks Item1 from LPN1, then the operator is required to count back the remaining quantity of Item1 on LPN1. The operator does not count back Item1 on LPN2.<br > **Note**: This field only affects count back quantity if manual and automatic consolidation are disabled for the storage zone. If manual or automatic consolidation are enabled for the storage zone, then the operator is required to count back the entire picked item quantity for the location regardless of this field. See [Count back counts](../../inventory/counting/count-settings.md). |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
