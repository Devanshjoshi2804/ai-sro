---
title: "Areas"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/areas.htm"
source: "/content/areas.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Warehouse"
  - "Areas"
sections:
  - "Add or modify an area"
  - "Delete an area"
images: []
source_sha1: 9448ecb2a53e130c6dcecf0befe9cb5477f104c8
---
# Areas

An area is a collection of locations in a building, used for grouping and sorting the locations in the warehouse. For example, an area named STAGING can be used to group ship staging locations; an area named CASEPICK can be used to group case pickface locations.

Locations in the warehouse must be assigned to an area. You can view the number of locations contained in an area when you view the area grid view.

## Add or modify an area

1.  Select **Configuration > Warehouse > Areas**.
2.  Select **Grid View**.
    
    **Note**: You can also add or modify an area using the **Map View**.
    
3.  Perform one of the following tasks:
    -   To add an area, click **Add**.
    -   To modify an area, in the grid, click the area name.
    -   To copy an area, in the grid, select the check box next to the area name, and then click **Copy**.
        
        **Note**: The copy function is only available in the **Grid View**.
        
4.  Enter information in the following fields:
    
     
    | Field | Description |
    | --- | --- |
    | **Enter a name for the area** | Name of the area. |
    | **Enter a description for the area** | Description of the area. |
    | **Enter the location designated for lost inventory in this area** | Location to which the application logically moves inventory that was missing as a result of an RF inventory adjustment for a count discrepancy. The move takes place for items for which an inventory adjustment is not allowed. This field is only available when modifying an area. See [Lost location for count discrepancies](../inventory/counting/count-settings.md). |
    | **Select the building where the area resides** | Building in which the area is located. |
    | Select the business unit where the area resides | Name of the business unit to which the area belongs. A business unit is an entity used to group areas and items for which a subset of operations exist within a specific building of a warehouse. See [Business Units](business-units.md). |
    
5.  To filter the map display, click **View**, and then select the entities to display.
6.  To define the area in the warehouse:
    1.  Click **Draw**. The area automatically is displayed on the floor plan.
    2.  Size and drag the area box on the map.
7.  Click **Save**.

## Delete an area

You cannot delete an area to which locations are assigned.

1.  Select **Configuration > Warehouse > Areas**.
2.  Click **Grid View**.
3.  In the grid, select the check box next to the area to delete.
4.  Click **Delete**. A confirmation message is displayed.
5.  Click **OK**.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
