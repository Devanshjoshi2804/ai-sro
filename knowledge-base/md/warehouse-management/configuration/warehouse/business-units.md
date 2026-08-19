---
title: "Business Units"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/business_units.htm"
source: "/content/business_units.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Warehouse"
  - "Business Units"
sections:
  - "Add or modify a business unit"
  - "Delete a business unit"
images: []
source_sha1: 08587059b1c0ad8cbfdaff76ac0f208404bf8470
---
# Business Units

A business unit is an entity used to group areas and items for which a subset of operations exist within a specific building of a warehouse. A business unit is not limited to physical locations or structures; and instead, it groups multiple warehouse entities together that can span multiple areas and items.

When you create a business unit, you define the building in which the business unit resides, and then you can assign the business unit to one or more items and areas. The following list describes the relationships between business units and buildings, items, and areas:

-   A business unit can only be associated with one building.
    
-   Each building can be associated with multiple business units.
    
-   A business unit can be assigned to one or more items and areas.
    
-   Each item and area can only be associated with one business unit.
    

**Note**: Business unit configuration is not required. However, if you choose to utilize this functionality, then it is suggested that you associate all defined areas and items to a business unit.

For example, assume a refrigerated building of a warehouse is divided into multiple areas based on temperature, which restricts the items that are stored in each area. The entire refrigerated building of the warehouse may have one supervisor; however, each different temperature zone (one or more areas) may be managed by a different user with a different team. In this scenario, separate business units can be created for each individual temperature zone. If there is a business unit for FROZEN and another for REFRIGERATED, then you can assign each business unit to the appropriate areas within the building and the appropriate items in each area.

You can filter data in the application using the business unit as part of the search criteria. This provides a more efficient method of displaying relevant data that is specific to a business unit instead of filtering by buildings, areas, and items.

**Note**: Depending on the data you are viewing in the application, the business unit filter is applied based on location/area or item. If the page you are viewing contains non-logical location information, then the business unit filter is applied using the associated areas. If the page does not have location information, then the filter is applied using the associated items. For example, if you are viewing expiring inventory on the inventory dashboard, then the business unit filter displays data for all locations in the areas assigned to the business unit. Alternatively, if you are viewing inventory that is not receivable, then the business unit filter displays data for the items assigned to the business unit.

## Add or modify a business unit

1.  Select **Configuration > Warehouse > Business Units**.
    
2.  Perform one of the following tasks: 
    
    -   To add a business unit, click **Add**.
        
    -   To modify a business unit, click it.
        
3.  Enter information in the following fields: 
    

 
| Field | Description |
| --- | --- |
| **Business Unit** | Name of the business unit. A business unit is an entity used to group areas and items for which a subset of operations exist within a specific building of a warehouse. |
| Description | Meaningful description of the business unit. |
| **Building** | Unique identifier for the building in which the business unit resides. A building is a warehouse entity consisting of one or more areas. Inventory and location information can be reported by building. |

5.  Click **Save**.
    

## Delete a business unit

You can delete a business unit only if there are no items or areas associated with it.

1.  Select **Configuration > Warehouse > Business Units**.
    
2.  In the grid, select the check box next to the business unit.
    
3.  Click **Delete**. A confirmation message is displayed.
    
4.  Click **OK**.
    

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
