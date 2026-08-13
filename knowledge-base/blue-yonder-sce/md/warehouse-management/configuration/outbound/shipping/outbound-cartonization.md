---
title: "Outbound Cartonization"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/cartonization.htm"
source: "/content/cartonization.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Outbound"
  - "Shipping "
  - "Outbound Cartonization"
sections:
  - "Configure shipping cartonization"
images: []
source_sha1: 243aa06792c16a6903c15611b32543138eca7cf7
---
# Outbound Cartonization

Shipping cartonization is the process by which the application sorts and groups picks, and determines which picks can be added to the same shipping container. Shipping cartonization is typically used when you want the application to determine, during pack station processing, which type of carton to use for packing and shipment, so that picks are grouped in advance of the pick release process. For example, a facility that uses automation to route picked inventory to a pack station uses shipping cartonization to group pick work so that the conveyor directs all picked inventory for the same shipping container to the same pack station.

When you configure shipping cartonization, you define the following attributes:

-   Whether automatic shipping cartonization is enabled.
-   The attributes that must match for picked inventory to be grouped together for cartonization processing. These values determine what picked inventory is eligible for shipping cartonization.
-   The attributes that determine the order in which picked inventory is processed into a shipping container. These values determine the sequence in which eligible picked inventory is processed into cartons.
-   The attributes you want the application to use to determine when to stop grouping product into one shipping container and start grouping product into a new shipping container when the value changes for actual cartonization. These values determine which picked inventory, from the sequential list of eligible inventory, is directed to the same container.
-   The LPN level at which the shipping container is tracked after packing. When a shipping container is consolidated to an LPN, it is no longer tracked by its shipping container identifier unless this configuration is set to Sub-LPN.

## Configure shipping cartonization

1.  Select **Configuration > Outbound > Shipping > Cartonization**.
2.  To enable shipping cartonization, set the **Enable Shipping Cartonization** field to **Enabled**.
3.  To define the attributes that attributes that must have matching values for picks to be added to the same shipping container:
    1.  Click **Pick Cartonization Rules**.
    2.  To select criteria from displayed entities:
        1.  If the advanced query is displayed, click **Simple**.
        2.  If the available entities are not displayed, click **Show Available**.
        3.  In the **Available** grid, select the entities that you want to use as criteria.
        4.  Click **Add selected**. The entities are added to the **Selected** grid.
        5.  To remove criteria, in the **Selected** grid, select the criteria to remove, and click **Remove selected**.
        6.  To reorder the criteria, in the **Selected** grid, click a row, and then click the up or down arrow to move the selected criteria. The application applies the criteria in sequential order according to how it is displayed in the grid.
    3.  To enter criteria using database entities, click **Advanced**, and then enter the column and field name, using a period to separate the column and field. Multiple column and field entries must be separated by a comma and space.
        
        You can use operators like IS NULL or IS NOT NULL to build an advanced query. For example, <column name>.<field name > IS NOT NULL, <column name>.< field name>.
        
    4.  Click **Save**.
4.  To define the attributes that determine the sequence in which eligible picks are processed for cartonization:
    1.  Click **Sequencing**.
    2.  To select criteria from displayed entities:
        1.  If the advanced query is displayed, click **Simple**.
        2.  If the available entities are not displayed, click **Show Available**.
        3.  In the **Available** grid, select the entities that you want to use as criteria.
        4.  Click **Add selected**. The entities are added to the **Selected** grid.
        5.  To remove criteria, in the **Selected** grid, select the criteria to remove, and click **Remove selected**.
        6.  To reorder the criteria, in the **Selected** grid, click a row, and then click the up or down arrow to move the selected criteria. The application applies the criteria in sequential order according to how it is displayed in the grid.
    3.  To enter criteria using database entities, click **Advanced**, and then enter the column and field name, using a period to separate the column and field. Multiple column and field entries must be separated by a comma and space.
        
        You can use operators like IS NULL or IS NOT NULL to build an advanced query. For example, <column name>.<field name > IS NOT NULL, <column name>.< field name>.
        
    4.  Click **Save**.
5.  To define the attributes that determine which sets of picks are considered during a single processing cycle for a work reference:
    
    **Note**: For example, select **Shipment** to process all picks for the same shipment together.
    
    1.  Click **Grouping Picks**.
    2.  To select criteria from displayed entities:
        1.  If the advanced query is displayed, click **Simple**.
        2.  If the available entities are not displayed, click **Show Available**.
        3.  In the **Available** grid, select the entities that you want to use as criteria.
        4.  Click **Add selected**. The entities are added to the **Selected** grid.
        5.  To remove criteria, in the **Selected** grid, select the criteria to remove, and click **Remove selected**.
        6.  To reorder the criteria, in the **Selected** grid, click a row, and then click the up or down arrow to move the selected criteria. The application applies the criteria in sequential order according to how it is displayed in the grid.
    3.  To enter criteria using database entities, click **Advanced**, and then enter the column and field name, using a period to separate the column and field. Multiple column and field entries must be separated by a comma and space.
        
        You can use operators like IS NULL or IS NOT NULL to build an advanced query. For example, <column name>.<field name > IS NOT NULL, <column name>.< field name>.
        
    4.  Click **Save**.
6.  In the **Shipping Container LPN Level** field, select one of the following levels:
    
    **Note**: This configuration does not apply to pallet type shipping containers based on the pallet carton type.
    
    -   **LPN**: Select LPN if you use shipping cartonization but you do not use pallet building after packing. If this field is set to LPN, then after packing when the shipping container is deposited to a location, it is still tracked by its LPN.If this field is set to LPN and you use pallet building after packing, then when the shipping container is deposited to an LPN, the container is merged onto the pallet LPN, and the original shipping container identifier is removed from the application.
    -   **Sub-LPN**: Select Sub-LPN if you use shipping cartonization and pallet building, and you want to retain the shipping container identifier. If this field is set to Sub-LPN, then when the shipping container is deposited to an LPN (for pallet building), the shipping container is still tracked as a uniquely identifiable sub-LPN.
        
        To use pallet building at the pack station with cartonization, the **Shipping Container LPN Level** field must be set to Sub-LPN.
        
7.  Click **Save**.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
