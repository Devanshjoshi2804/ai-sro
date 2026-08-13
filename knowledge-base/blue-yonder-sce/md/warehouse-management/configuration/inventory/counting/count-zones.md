---
title: "Count Zones"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/count_zones.htm"
source: "/content/count_zones.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inventory"
  - "Counting"
  - "Count Zones"
sections:
  - "Zone consolidation"
  - "Add or modify a count zone"
  - "Delete a count zone"
  - "Consolidate zones"
  - "Count Zone fields"
images: []
source_sha1: 0ad23e75a9db51ef053cdc20bd65fc329cd31d71
---
# Count Zones

A count zone is a method of grouping locations for an inventory count. You may want to group locations into a count zone based on the type of counts that take place (RF or paper-based) and how counts are generated (manually or automatically). For example, a warehouse may have one count zone for piece pick locations and another count zone for pallet pick locations. You could then configure a count release rule for the piece pick count zone to produce pick sheets, and a count release rule for the pallet pick count zone to create directed work.

A count zone can also be used to group locations that should be counted together. For example, you can create a separate count zone for each aisle, and then configure the release rule to group count work by aisle. When the count work is released, an operator is directed to complete all the counts in an aisle. 

The count zone attributes determine whether inventory activity is allowed to take place at locations in the zone for which a count has been scheduled, and the threshold value, which determines minimum unit quantity or percentage of a location's capacity that must remain after a pick or inventory transfer is complete for the application to bypass an immediate count. See [Count Settings](count-settings.md).

## Zone consolidation

You can use the Consolidate action, available from any zone configuration grid, to consolidate zones that share a common configuration into a single (original) zone. You can consolidate the following types of zones: count zones, movement zones, pick zones, storage zones, and work zones. See [Consolidate zones](#Consolidate_zones).

When you select a zone and use the Consolidate action, the application presents a list of zones that have a configuration that matches the selected (original) zone. You can then select one or more of the matching zones to consolidate to the original zone.

During consolidation, the application performs the following tasks:

-   Updates all the configurations and references for the zones that are being consolidated to now use the original zone. For example, if PickZone2 and PickZone3 are consolidated into PickZone1, then the locations assigned to PickZone2 and PickZone3 are reassigned to PickZone1.
-   Removes the consolidated zones and retains the original zone.
-   Displays a progress bar that shows the processing status of the consolidation.
-   When consolidation is complete, displays the list of any remaining consolidation candidates that match the original zone. This allows you to continue consolidating to the original zone.

The same process is available for location types using the location type configuration. See [Location type consolidation](../../warehouse/locations/location-types.md).

## Add or modify a count zone

1.  Select **Configuration > Inventory > Counting > Count Zones**.
2.  Perform one of the following tasks:
    -   To add a new count zone, from the **Actions** drop-down list, select **Add**.
    -   To modify a count zone, in the grid, click the count zone.
    -   To copy a count zone, in the grid, select the check box next to the count zone, and then from the **Actions** drop-down list, select **Copy**.
3.  Enter information in [Count Zone fields](#Count_Zone_fields).
4.  Click **Next**.
5.  To define the boundaries of the count zone on the floor plan:
    1.  Click **Draw**. A boundary box is displayed on the floor plan.
    2.  To move the boundary box, click and drag the center to a new position.
    3.  To adjust the size of the boundary box, click and drag the edges to new positions.
6.  Click **Finish**.

## Delete a count zone

You cannot delete a count zone that contains locations.

1.  Select **Configuration > Inventory > Counting > Count Zones**.
2.  In the grid, select the check box next to the count zone to delete.
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

## Count Zone fields

 
| Field | Description |
| --- | --- |
| Zone Name | Unique identifier for the count zone. |
| Description | Description that further defines the count zone. |
| Building | Name of the building in which the zone resides. |
| RF Cycle Count | If Yes, then cycle counts in the zone are performed on an RF device. RF cycle counts transition through statuses such as Generated, Scheduled, Released, and In Progress. The location being counted remains available for inventory processing (such as picking and putaway) while cycle counts are pending. This is because RF-based counts are performed against real-time information, and the quantity in the location when the count was generated is not relevant at the time the count is performed. If you set this field to Yes, then cycle counts in the zone must be performed on an RF device and are not visible on the Count Entry page.<br > If No, then cycle counts performed in the zone are paper-based. Paper-based counts are generated in an In Progress status, and the location being counted is unavailable for inventory processing until the count is complete. This ensures that the quantity of inventory that was in the location when the count was generated is the same as when the operator performs the count. In the application, the Count in Progress tag is immediately applied to the location when the count is generated. If this field is set to No, then paper-based cycle counts in the zone must be manually entered and completed before the location being counted is available for processing.<br > **Note**: If the **Detail Count** field for the count type is set to No, then paper-based cycle counts are displayed on the Count Entry page. If the **Detail Count** field is set to Yes, then paper-based counts are displayed on the Audit Count page. |
| Count Near Zero | If Yes, the application directs an RF operator to perform a cycle count immediately following a pick or inventory transfer in the count zone if inventory in a location drops below the **Threshold Value**. The picking operator, if authorized for the count near zero operation, is prompted to perform the count. If the picking operator is not authorized, then another operator performs the count. Select Yes if you want to ensure that the inventory level is accurate when it falls below a certain amount.<br > Count near zero functionality can be enabled by item and by count zone. Therefore, a count near zero can be generated for a location if the count zone is enabled for it, even if the item in the location is not configured for count near zero. If you enable count near zero for an item and leave the **Count Near Zero Amount** blank (null), then the application defers to the count zone configuration.<br > Alternatively, if both the item and count zone are enabled for count near zero and have different thresholds, the value defined for the item takes precedence. For example, assume an item's threshold (count near zero amount) is 20 units and a count zone's location threshold is 25 units. After a pick is complete, if the remaining quantity in the location is 22, then a count is not generated because the quantity did not fall below the item's threshold.<br > If No, then the count zone is not enabled for count near zero. However, a count near zero can still be generated for a location in the count zone if the item in the location is enabled for count near zero and the inventory falls below the count threshold for the item. |
| Threshold Value | Minimum unit quantity or percentage of a location's capacity that must remain after a pick or inventory transfer is complete for the application to bypass an immediate count. If the remaining inventory in the location is below the threshold value, the application prompts the operator to perform a count immediately after the pick or transfer. In the first field, enter the value for the unit quantity or percentage. In the second field, select one of the following values:<br>-   • **Unit Quantity**: Indicates that the threshold value represents the stocking unit quantity of the item in the location.
<br>-   • **Percentage**: Indicates that the threshold value represents a percentage of the location's capacity.
<br > For example, if you set the threshold value to 20%, then when the inventory level falls below 20% of a location's capacity, the operator is prompted to perform an inline count following a pick or inventory transfer. If you set this field to zero (0), then a count is generated when the location is empty (remaining unit quantity or percentage of the location's capacity being used is 0).<br > Only available when the **Count Near Zero** is enabled for the count zone.<br > **Note**: If an item and a count zone are enabled for count near zero and have different thresholds, the value defined for the item takes precedence. For example, assume an item's threshold (count near zero amount) is 20 units and a count zone's location threshold is 25 units. After a pick is complete, if the remaining quantity in the location is 22, then a count is not generated because the quantity did not fall below the item's threshold. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
