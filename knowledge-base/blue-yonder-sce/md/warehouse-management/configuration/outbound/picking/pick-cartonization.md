---
title: "Pick Cartonization"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/pick_cartonization.htm"
source: "/content/pick_cartonization.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Outbound"
  - "Picking "
  - "Pick Cartonization"
sections:
  - "Automatic cartonization"
  - "Picking cartonization"
  - "Shipping cartonization"
  - "Pack station cartonization"
  - "Cartonization calculation methods"
  - "Manual cartonization"
  - "Cartons"
  - "Repack class"
  - "Carton routing groups"
  - "Example"
  - "Setup"
  - "Cartonization setup and configuration"
  - "Configure pick cartonization"
  - "Pick Cartonization fields"
  - "Cartons fields"
images: []
source_sha1: 5c54cb61d0addc255e7023f83e74aad8ba6e9ddd
---
# Pick Cartonization

Cartonization is the process of determining which items are to be packed together in a container and which size container is to be used. The application supports the following types of cartonization:

-   **Automatic cartonization**: The application determines the type of carton to use. The application supports automatic cartonization for picking, shipping, and pack station to determine the type of carton to use for each respective process.
-   **Manual cartonization**: The operator determines the type of carton to use.

You can configure the application to automatically perform picking cartonization, shipping cartonization, both picking and shipping cartonization, or no automatic cartonization.

**Note**: To utilize cartonization and for cartonization to efficiently optimize cartons, you must first configure the item footprints with accurate dimensions and weight.

## Automatic cartonization

Automatic cartonization takes place during pick release, prior to picking or packing.

Automatic cartonization considers the following information:

-   Only those units of measure (UOMs) that can be cartonized, as defined by the item footprint configuration
-   The repack classes that are defined for the item or customer
-   Only those pick zones for which a cartonization group or packaging levels have been defined for cartonization

During automatic cartonization, the application selects the picks to be processed and then follows the selected processing method to determine which picks will fit into which carton. It also finds the smallest carton that can contain the designated picks (based on the cartonization method) and assigns a carton ID (for picking cartonization) or shipping container ID (for shipping cartonization) to the carton.

### Picking cartonization

Picking cartonization is an automatic cartonization process that determines which type of carton to use as the picking container for certain pick work, and which piece and case picks are picked to the same picking container.

Picking cartonization is typically used in the following situations:

-   Operators pick product directly to the final shipping container, such as a box. This cartonization process does not use pack station processing for packing inventory, but may use it to print labels and paperwork for the packed shipping containers.
-   Picks are grouped and directed to a standard picking container, such as a reusable tote. This cartonization process typically uses pack station processing for packing inventory into shipping containers and for printing labels and paperwork for the packed shipping containers.

Picking cartonization uses only cartons that are configured for picking.

### Shipping cartonization

Shipping cartonization is an automatic cartonization process that determines which type of carton to use as the shipping container for packing the contents of a picking container into a shipping container at the pack station.

Shipping cartonization is typically used when you want the application to determine, during pack station processing, which type of carton to use for packing and shipment, so that picks are grouped in advance of the pick release process. For example, a facility that uses automation to route picked inventory to a pack station uses shipping cartonization to group pick work so that the conveyor directs all picked inventory for the same shipping container to the same pack station.

Shipping cartonization uses only cartons that are configured for shipping.

### Pack station cartonization

Pack station cartonization is an automatic cartonization process that determines which type of carton to use as the shipping container for picked inventory that has been deposited to a pack station.

Pack station cartonization performs the automatic cartonization process on the inventory in the picking container at the pack station for an individual shipment. The results are used to guide the packing operator by prompting the operator to pack, for example, Carton1, then Carton2, and so on.

Pack station cartonization uses only cartons that are configured for pack station processing.

## Cartonization calculation methods

You can configure the application to use one of the following methods for performing automatic cartonization:

**Note**: If the **Pick to Box** field is set to Yes for an item, then during cartonization, the box or carton footprint will be considered instead of the item footprint.

-   **Volume**: This method uses volume-based calculations. The list of possible cartons is selected and sorted in sequence by descending volume. Volume is calculated as (length) x (width) x (height) x (fill percentage). The fill percentage for a carton is determined by the **Maximum Carton** and **Maximum Last Carton** fields. After a carton is processed, and cartonization attempts to downsize into a better fit carton, the actual item and footprint dimensions (length, width, and height) are used to ensure that the item will fit into the carton in some orientation.
    
    For example, if the item is 16 x 12 x 3 and the carton is 17 x 16 x 6, the item will fit into the carton. However, if the carton is 17 x 10 x 6, the item will not fit dimensionally in any orientation. Each item is checked individually; therefore, if each item will fit in some orientation and the combined volume of the items does not exceed the capacity of the carton, the carton will be used.
    
-   **Complex**: This method also uses volume-based calculations (as described for the Volume method), including checking the item dimensions (length, width, and height) to ensure carton dimensions are not exceeded. After a carton passes through the volume-based calculations, the application performs additional calculations when the carton type is downsized. Complex cartonization takes place after the application determines the contents of the carton. The additional calculations validate whether the picks will fit into a smaller carton by using different possibilities of orientation and placement. Only after finding a successful packing combination will the application select a smaller carton.
    
    For example, assume the application is performing cartonization on 4 picks, and there are carton types A, B, and C, with A being the largest and C the smallest. First, the application determines how many of the picks can fit into the largest carton based on volume and weight. If pick 1, 2, and 3 can fit into carton A, but pick 4 does not fit, then the application attempts to downsize the carton for the first three picks. This is the only time that complex cartonziation is performed. During this process, the application attempts to fit pick 1, 2, and 3 into carton B by calculating different orientation and placement combinations for the items. If the application finds a successful packing combination, it selects carton B, and then attempts to downsize to carton C.
    
    Depending on the number of items in the carton, the number of iterations can quickly grow into the millions. For performance reasons, you must configure the maximum number of iterations that can occur. Contact your Blue Yonder project team to determine an appropriate value for your configuration. Even though not every mathematically possible solution is considered, the Complex method provides a successful packing combination based on the random sampling.
    

## Manual cartonization

Manual cartonization is the process of picking pieces, and delivering those pieces to a pack station for further processing. Picking may be directed by a label or pick sheet, or assigned through directed work. When picking for an order or shipment is complete, the picked inventory is directed to the pack station for repacking into a shipping container.

At the pack station, the operator selects the type of carton to use as the shipping container and identifies which pieces are packed into it. Completed shipping containers are typically moved to a consolidation or shipment staging location for further processing.

## Cartons

A carton is a container for inventory that is used during picking and packing operations. For example, you can pick inventory to a carton so that the carton can be shipped when picking is complete, or you can pack picked inventory to a shipping carton so that the carton can be shipped when packing is complete.

You define different types of cartons so that the application can select the most appropriate carton during the automatic cartonization process. The application selects the optimal carton for the picked or packed inventory based on carton attributes, such as size, weight, capacity, and purpose.

The following types of cartons are used exclusively during pack station processing:

**Note**: The application does not consider the following types of cartons for use during cartonization processing.

-   **Generic Carton Type**: This is a standard carton type provided in the application; you cannot add or delete the generic carton type; however, you can configure its dimensions. The generic carton type is used, for example, when a packing operator needs to process a full case (carton) or box without packing it into a shipping container. The packing operator can override the suggested carton type with the generic carton, add or edit its dimensions to match the full case, and process the inventory without packing it to a shipping container. As another example, if the suggested carton is not available and the operator needs to use a different carton that has no pre-defined dimensions, the operator can use the generic carton type to process the inventory.
-   **Pallet Type**: This carton attribute defines a physical pallet as a carton. Cartons of this type are used exclusively in pack station processing when an operator needs to process inventory, such as a full case (carton) or box, without packing it to a shipping carton. The packing operator can override the suggested carton with a pallet carton type and process the inventory to the pallet. Upon completion of the pallet, the operator can edit the dimensions to enter the number of boxes that were packed to the pallet.

## Repack class

Repack classes are optional attributes that you can apply to items and cartons, or to items, customers, and cartons. Repack classes help to ensure that specialty products or products with unique packaging or customer requirements are packaged into suitable cartons for shipping. The following situations are examples where you would use repack classes:

-   Packing heavy items into sturdier boxes
-   Packing frozen food into an insulated container for customers located far away, but use a regular container for customers located close enough that the frozen food will not thaw
-   For a 3PL environment, packing client A's items into client A's cartons and client B's items into client B's cartons

During cartonization, the application looks for a matching repack class on the item, customer, and carton. If a repack class is not defined for the customer, then the application looks for a matching repack class on the item and carton. If a matching repack class is found, then the application selects the appropriate shipping carton. If multiple matching repack classes are found, then the first matching repack class with the highest priority sequence (as defined for the item) is used. The following is an example of how the application looks for a carton based on the repack classes:

-   If the item has no assigned repack classes, then the application selects the largest carton without an associated repack class.
-   If the item has one assigned repack class and no customer repack class, then the application selects the largest carton with a repack class that matches the item.
-   If the item has more than one assigned repack class and no customer repack class, then the application finds the cartons with a repack class that matches one defined for the item, and then selects the largest carton with the highest priority matching repack class (as defined for the item).
-   If the item has one assigned repack class that matches the customer repack class, then the application selects the largest carton with a repack class that matches the item and customer.
-   If the item and the customer each have more than one assigned repack class, the application finds the cartons with a repack class that matches a class defined for both the item and customer, and then selects the largest carton with the highest priority matching repack class (as defined for the item).

**Note**: If the customer requirement policy is not enabled (INSTALLED), the application ignores any defined customer repack classes and only considers the item and carton repack classes. You can configure the CUSTOMER-REQUIREMNT-PROCESSING/INSTALLED policy in [Policy Maintenance](../../../../administration/system-administrator/configuration/policy/policy-maintenance.md).

## Carton routing groups

A carton routing group specifies one or more carton types or a number of carton types (such as less than 3 or more than 6) that are grouped together for processing. For example, if certain pack stations in the warehouse operate more efficiently (higher throughput) based on the carton types or number of carton types that pass through it, then you can create a carton routing group that can be used to direct shipments that require certain carton types to specific pack stations.

If carton routing groups are enabled for the warehouse or a client, then when a shipment is created with at least one order type enabled for carton routing, the application performs precartonization to determine the carton type for the inventory on each order line. If the carton type requirements match the criteria defined for a carton routing group, the application assigns the carton routing group to the shipment. A carton routing group can be used as criteria on a movement path to direct the shipment to, for example, a particular pack station. A carton routing group can also be used as an attribute in building a work assignment to group order lines for picking.

### Example 

For this example, assume SHIP01 is created and the application determines that carton types CT1 and CT2 are required for cartonization.

Consider the following carton routing group configurations: 

   
| Carton Routing Group | Entity | Column | Value |
| --- | --- | --- | --- |
| CRG1 | Carton | Carton Type | \= CT1, CT2 |
| CRG2 | Carton | Number of Carton Types | > 2 |

Consider the following work assignment rule configurations: 

   
| Rule Configuration | Entity | Column | Value |
| --- | --- | --- | --- |
| Selection Criteria | Shipment | Carton Routing Group | \= CRG1 OR CRG2 |
| Criteria Grouping | **Carton Routing Group** criteria is selected |

Consider the following movement path criteria:

   
| Criteria | Entity | Column | Value |
| --- | --- | --- | --- |
| CRT01 | Shipment | Carton Routing Group | CRG1 |
| CRT02 | Shipment | Carton Routing Group | CRG2 |

Consider the following movement paths and associated hop criteria: 

    
| Source zone | Destination zone | Hop sequence | Hop | Criteria |
| --- | --- | --- | --- | --- |
| SA1 | DA1 | 1 | HOP1 | CRT01 |
| SA1 | DA1 | 2 | HOP2 | CRT02 |
| SA1 | DA1 | 3 | HOP3 | n/a |

Assumptions

The following assumptions can be made with this information: 

-   The application assigns carton routing group CRG1 to SHIP01 based on the need for carton types CT1 and CT2. Carton routing group CRG2 does not apply because the number of carton types needed for the shipment is not greater than 2.
-   A work assignment for the shipment is created from the work assignment rule above because the shipment's carton routing group meets the criteria of being CRG1. The selected Carton Routing Group criteria grouping ensures that the work assignment can only have picks for 1 carton routing group.
-   Inventory for SHIP01 meets the movement path criteria CRT01 based on the shipment's carton routing group CRG1.
-   Inventory for SHIP01 follows hop sequence 1, stopping at HOP1, based on the movement path criteria CRT01.

### Setup

You must perform the following tasks to use carton routing groups: 

1.  Configure automatic cartonization. See [Cartonization setup and configuration](#Cartonization_setup_and_configuration).
2.  Configure the following carton routing group attributes: 
    
    -   Enable carton routing groups for the warehouse, or in a 3PL environment, select the clients for which carton routing groups are enabled.
    -   Select the order types for which carton routing groups are enabled.
    -   Define the carton routing group rules that determine the attributes of the carton routing groups.
        
    
    See [Configure pick cartonization](#Configure_pick_cartonization).
    
3.  To build work assignments based on carton routing groups, add work assignment rules:
    
    -   Define selection criteria that includes the carton routing group column and value for the shipment entity.
    -   To indicate that a work assignment can only contain picks for shipments of the same carton routing group, select the Carton Routing Group check box in the criteria grouping configuration.
        
    
    See [Add or modify work assignment rules](work-assignments/procedures-for-work-assignments.md).
    
4.  Add movement path criteria that includes the Carton Routing Group column and the specific carton routing group value for the shipment entity. See Add or modify movement path criteria.
5.  Assign the movement path criteria to a movement path hop. See [Add or modify a movement path](../../inventory/movement/movement-paths.md).

## Cartonization setup and configuration

You must perform the following tasks to set up and configure automatic cartonization.

1.  Configure cartonization. When you configure cartonization you enable the application to perform automatic cartonization, and you define the following attributes:
    
    **Note**: The following configurations are required for picking cartonization, and as noted for shipping and pack station cartonization.
    
    -   Repack classes that restrict the assignment of inventory to a specific class of cartons. See [Repack class](#Repack_class). (Also used for shipping cartonization.)
    -   Cartons that can be used for cartonization processing. Carton attributes define the size and use of the carton, and the types of cartonization to which it can be automatically assigned. (Also required for shipping and pack station cartonization.) See [Configure pick cartonization](#Configure_pick_cartonization).
    -   Attributes that define how eligible picks are grouped and sequenced for cartonization
    -   Attributes that define grouping for pre-cartonization estimation in support of parcel rating
    -   Attributes that define grouping during actual cartonization
    -   Attributes that define which qualified picks can be placed into the same carton
    -   How sensitive-item cartons are selected for items that are configured for being picked to a box before being placed in a carton with other items
    -   The cartonization method used for determining how much inventory can be placed into each carton
    -   Attributes that determine how RF carton picking takes place
    -   Whether carton routing groups are used to direct shipments to a hop on a movement path (such as to a pack station) based on carton type. See [Carton routing groups](#Carton_routing_groups).
    
    See [Configure pick cartonization](#Configure_pick_cartonization).
    
2.  Configure items for cartonization. Define the following attributes to enable items for cartonization:
    
    **Note**: The following configurations are required for picking cartonization, and as noted for shipping and pack station cartonization.
    
    -   Units of measure (UOMs) to cartonize. For each item to cartonize, you use the item footprint configuration to set up UOMs, and to enable cartonization for the UOMs (such as eaches) that can be cartonized. The item footprint also defines the size and weight of the UOM, which are used in cartonization processing. (Also required for shipping and pack station cartonization.) See [Item footprints](../../inventory/items/footprints.md).
    -   Whether the item must be placed in a box before being placed into a carton with other items. You use the item processing configuration to enable the **Pick to Box** field. This attribute is used during picking cartonization to direct the operator to place the item in a carton configured as a sensitive item carton, before packing the item into a carton with other items.
    -   Repack classes. This attribute is used for picking and shipping cartonization. An item will only be directed to cartons that have a matching repack class. If no repack class is defined for the item, it will be directed to a carton that has no repack class defined. See [Repack class](#Repack_class).
    -   Nesting dimensions and nesting class codes. If an item is able to be nested, you use the item footprint configuration to define the nesting dimensions. If an item can be nested with other items, you use the item configuration to define the nesting class code. These attributes are used during cartonization processing to assign cartons or split nested structures based on their stacked dimensions. (Also used for shipping and pack station cartonization.) See [Nesting for cartonization](../../inventory/items/items.md).
    
    See [Items](../../inventory/items/items.md).
    
3.  Configure pick zones. For the pick zones in which you store the item UOMs that have been enabled for cartonization, define the following attributes:
    
    **Note**: The following configurations are required for picking cartonization.
    
    -   Select the LPN level at which picks are allowed in a pick zone. For example, if the Each UOM is enabled for cartonization, then set the LPN level to Detail LPN to allow the Each UOM to be picked from the zone.
    -   Optionally, select a cartonization group for the pick zone. A cartonization group is used to group pick zones from which inventory can be cartonized together. For example, your warehouse may have 10 pick zones in which you want to perform cartonization, but 5 of the pick zones are located close together on the north side of the building while the other 5 pick zones are located close together on the south side of the building. You can define 2 cartonization groups and assign one to the north pick zones and one to the south pick zones, so that inventory from the 5 north pick zones is cartonized together and inventory from the 5 south pick zones is cartonized together, separately from the north pick zones.
    
    See [Pick Zones](../allocation/pick-zones.md).
    
4.  Configure pick methods.
    
    **Note**: The following configuration is required for picking cartonization.
    
    A pick method defines the types of picks that are created and released. After the pick method is defined, you assign the pick method to the allocation search path rules used to allocate carton picks. See [Pick Methods](pick-methods.md).
    
5.  Configure allocation search paths.
    
    **Note**: The following configurations are required for picking cartonization.
    
    An allocation search path defines the source zone from which inventory is allocated for a pick, based on the attributes of the required inventory. For each search path that you want to use to allocate the item UOMs that are configured for cartonization, configure a search path rule with the following attributes:
    
    -   Select the pick zone in which you store item UOMs enabled for cartonization.
    -   Select the LPN level at which picks can be allocated from the pick zone to a level that matches the item UOMs to cartonize. For example, if you cartonize Each UOMs, then select the Detail LPN level, or select Any to allow allocation at any level.
    -   Ensure that the value for the **Allocation UOM** field does not prevent allocating the item UOM to cartonize. For example, if you cartonize Each UOMs, then set **Allocation UOM** to Each or leave it blank.
    -   Select a pick method that creates and releases carton picks from the pick zone.
    
    See [Allocation Search Paths](../allocation/allocation-search-paths.md).
    
6.  Configure shipping cartonization.
    
    **Note**: The following configurations are required for shipping cartonization.
    
    If you want the application to automatically cartonize picked inventory into appropriate shipping containers, perform the following tasks:
    
    -   Configure shipping cartonization. See [Outbound Cartonization](../shipping/outbound-cartonization.md).
    -   Enable automatic carton numbering for the workstation so that the application assigns the shipping container number; otherwise, the operator assigns it, typically by scanning a generic label. See [Workstations](../../equipment/hardware/workstations.md).
    -   For each carrier service level used to transport shipping containers, specify the shipping cartonization thresholds for weight, volume, and value thresholds for each carrier and service level. See [Existing Carriers](../../partners/carriers/existing-carriers.md).
7.  Configure pack station cartonization.
    
    **Note**: The following configurations are required for pack station cartonization.
    
    If you want the application to determine which picks are to be packed together in cartons for a shipment, then configure the following cartonization attributes for pack station:
    
    -   Enable automatic cartonization, which evaluates the picked inventory at the pack station and determines which inventory is to be packed into which shipping carton.
    -   Define whether the pack station operator is allowed to pack an item into a shipping carton if doing so violates the separation of items based on the break-on values.
    -   Define the break-on value (such as shipment ID) that determines when a new shipping carton is started even though there is room for more inventory in the current carton.
    -   Define the order-by value (such as weight) that controls the order in which picks will be considered for adding to a carton.
    -   Define whether you want the application to parse the carton type and if so, specify the command used to parse the shipping container code.
    
    See [Settings and Pack Station](../packing/settings-and-pack-station.md).
    
8.  Configure handling unit types. If your warehouse tracks inventory handling units, you can select the types of cartons that can be picked to the handling unit during a work assignment. See [Handling Unit Types](../../inventory/lpn-handling/handling-unit-types.md).
9.  Configure processing for Carton Confirmation Operations. If you will be using Carton Configuration Operations to confirm picks to a carton, then configure the following attributes:
    
    -   Define the workstations that are used to perform Carton Confirmation Operations. When users process cartons in Carton Confirmation Operations, the application creates a temporary location based on the workstation when processing a carton. See [Workstations](../../equipment/hardware/workstations.md).
    -   Use Policy Maintenance to configure the carton confirmation operations (CTNCNFOPR) policies that determine how inventory is processed using Carton Confirmation Operations.

## Configure pick cartonization

1.  Select **Configuration > Outbound > Picking > Pick Cartonization**.
2.  Enter information in the [Pick Cartonization fields](#Pick_Cartonization_fields).
3.  To define repack classes:
    1.  Under **CARTON SPECIFICATIONS**, click **Repack Class Definition**.
    2.  Perform one of the following tasks:
        -   To add a repack class, click **Add**.
        -   To modify a repack class, in the grid, click the description of the repack class.
    3.  Enter information in the following fields:
        
        | Field | Description |
        | --- | --- |
        | Repack Class | Code that represents the value for the repack class. Repack classes are optional attributes that you can apply to ensure that your products are packaged into suitable cartons for shipping. |
        | Description | Long description of the repack class. This is the value that represents the repack class, for example, in a drop-down list. |
        | Short Description | Brief description of the repack class. This is the value that represents the repack class on RF screens. |
        
    4.  Click **Apply**.
    5.  To adjust the sequence in which the application evaluates the repack class, in the grid, click and drag the repack class to the preferred position.
    6.  To translate the name and description of repack classes:
        1.  Perform one of the following tasks:
            -   To translate specific rows, in the grid, select the check box of the rows, and then above the grid, click **Translation**.
            -   To translate all rows, above the grid, click **Translation**.
        2.  From the **Destination Locale** drop-down list, select the locale.
        3.  In the grid, select a translated description or short description, and then enter the new value.
        4.  Click **Save**.
4.  To define cartons:
    1.  Under **CARTON SPECIFICATIONS**, click **Carton Definition**.
    2.  Perform one of the following tasks:
        -   To add a new carton, click **Add**.
        -   To modify a carton, in the grid, click the carton name.
        -   To copy a carton, in the grid, select the check box next to the carton, and then click **Copy**.
    3.  Enter information in the [Cartons fields](#Cartons_fields).
    4.  To assign or unassign repack classes for the carton:
        1.  Click **Repack Classes**.
        2.  In the **Available Repack Classes** column, select the check box for the repack classes to assign.
        3.  Click **Apply**.
    5.  Click **Save**.
5.  To enable processing by carton routing group for clients in a 3PL environment:
    1.  Under **CARTON ROUTING GROUPS**, click **Clients**.
    2.  In the **Available Clients** column, select the check box next to each client.
    3.  Click **Apply**.
6.  To define a carton routing group:
    1.  Under **CARTON ROUTING GROUPS**, click **Carton Routing Group Rules**.
    2.  Perform one of the following tasks:
        -   To add a carton routing group, click **Add**.
        -   To create a carton routing group from an existing group, select the check box next to the group, and then click **Copy**.
    3.  Enter information in the following fields:
        
        | Field | Description |
        | --- | --- |
        | Group Name | Name of the carton routing group. A carton routing group specifies one or more carton types or a number of carton types (such as less than 3 or more than 6) that are grouped together for processing. |
        | Description | Meaningful description of the carton routing group. |
        | Sequence Number | Sequence in which the application considers the carton routing group rule when attempting to assign a group to a shipment. The lower a sequence number, the higher its priority, with 1 being the highest. When the application matches a carton routing group with a shipment, the remaining rules with a higher sequence are no longer considered. |
        
    4.  To define the criteria of the group that determines which carton types (or the number of carton types) are included in the carton routing group:
        1.  Under **Criteria Definition**, click **Expression**.
        2.  Select the **Carton** entity.
        3.  Select the **Carton Type** column or the **Number of Carton Types** column.
        4.  Select the qualifier to use, such as "**\=**".
        5.  Select the value to use, such as a specific carton type or the number of carton types allowed.
        6.  To add additional expressions:
            1.  Select the mathematical argument used to evaluate multiple rows of criteria.
                -   **OR**: Must match either group of the defined criteria.
                -   **AND**: Must match both groups of the defined criteria.
                -   **(**: Opening argument used to group criteria together.
                -   **)**: Closing argument used to group criteria together.
                    
                    **Note**: Other operators that represent a combination of these arguments, such as ")AND(" are also available. The operator determines how the application evaluates the criteria. For example, if you have two criteria lines connected with the operator AND, that means the shipment must match both attributes to meet the criteria. If the two lines are connected with the operator OR, the shipment only has to match one of the field values to meet the criteria.
                    
            2.  Click **Expression**, and define its criteria.
    5.  Click **Save**.
7.  To select the order types for which carton routing groups are enabled:
    1.  Under **CARTON ROUTING GROUPS**, click **Order Type**.
    2.  In the **Available** column, select the check box next to each order type.
    3.  Click **Apply**.
8.  To define the criteria that is used to group eligible picks for cartonization:
    1.  Under **CARTON ASSIGNMENTS**, click **Grouping Picks**.
    2.  To select criteria from displayed entities:
        1.  If the advanced query is displayed, click **Simple**.
        2.  If the available entities are not displayed, click **Show Available**.
        3.  In the **Available** grid, select the entities that you want to use as criteria.
        4.  Click **Add selected**. The entities are added to the **Selected** grid.
        5.  To remove criteria, in the **Selected** grid, select the criteria to remove, and click **Remove selected**.
        6.  To reorder the criteria, in the **Selected** grid, click a row, and then click the up or down arrow to move the selected criteria. The application applies the criteria in sequential order according to how it is displayed in the grid.
    3.  To enter criteria using database entities, click **Advanced**, and then enter the column and field name, using a period to separate the column and field. Multiple column and field entries must be separated by a comma and space.
        
        You can use operators like IS NULL or IS NOT NULL to build an advanced query. For example, <_column name_>.<_field name_> IS NOT NULL, <_column name_>.< _field name_>.
        
    4.  Click **Apply**.
9.  To define criteria that is used to determine the sequence in which picks are considered for cartonization:
    1.  Under **CARTON ASSIGNMENTS**, click **Sequencing**.
    2.  To select criteria from displayed entities:
        1.  If the advanced query is displayed, click **Simple**.
        2.  If the available entities are not displayed, click **Show Available**.
        3.  In the **Available** grid, select the entities that you want to use as criteria.
        4.  Click **Add selected**. The entities are added to the **Selected** grid.
        5.  To remove criteria, in the **Selected** grid, select the criteria to remove, and click **Remove selected**.
        6.  To reorder the criteria, in the **Selected** grid, click a row, and then click the up or down arrow to move the selected criteria. The application applies the criteria in sequential order according to how it is displayed in the grid.
    3.  To enter criteria using database entities, click **Advanced**, and then enter the column and field name, using a period to separate the column and field. Multiple column and field entries must be separated by a comma and space.
        
        You can use operators like IS NULL or IS NOT NULL to build an advanced query. For example, <_column__name_>.<_field name_> IS NOT NULL, <_column__name_>.<_field name_>.
        
    4.  Click **Save**.
10.  To define the criteria that is used to match picks for placement into the same carton during a picking work assignment:
     1.  Under **CARTON ASSIGNMENTS**, click **Pick Cartonization Rules**.
     2.  Under **Criteria Definition**:
         1.  Click **Expression**.
         2.  Select an entity that has the attribute to use, such as **Customer**.
         3.  Select the attribute to use, such as **Store Type**.
         4.  Select the qualifier to use, such as "=".
         5.  Select the value to use, such as **Chain Store**.
         6.  Click **Apply**.
         7.  To add additional expressions:
             1.  Select the mathematical argument used to evaluate multiple rows of criteria.
                 -   **OR**: Must match either group of the defined criteria.
                 -   **AND**: Must match both groups of the defined criteria.
                 -   **(**: Opening argument used to group criteria together.
                 -   **)**: Closing argument used to group criteria together.
                     
                     **Note**: Other operators that represent a combination of these arguments, such as ")AND(" are also available. The operator determines how the application evaluates the criteria. For example, if you have two criteria lines connected with the operator AND, that means the inventory must match both attributes to meet the criteria. If the two lines are connected with the operator OR, the inventory only has to match one of the field values to meet the criteria.
                     
             2.  Click **Expression**, and define its criteria.
             3.  Click **Apply**.
11.  To be able to obtain pre-cartonization estimates for rating parcels:
     
     **Note**: This setting is used to obtain pre-cartonization estimates for rating parcels and is only used when Warehouse Management is integrated with a parcel application through Parcel Handler. See [Rate shopping](../shipping/parcel-handler.md).
     
     1.  Under **CARTON ASSIGNMENTS**, click **Pre-Cartonization Criteria**.
     2.  To select criteria from displayed entities:
         1.  If the advanced query is displayed, click **Simple**.
         2.  If the available entities are not displayed, click **Show Available**.
         3.  In the **Available** grid, select the entities that you want to use as criteria.
         4.  Click **Add Selected**. The entities are added to the **Selected** grid.
         5.  To remove criteria, in the **Selected** grid, select the criteria to remove, and click **Remove selected**.
         6.  To reorder the criteria, in the **Selected** grid, click a row, and then click the up or down arrow to move the selected criteria. The application applies the criteria in sequential order according to how it is displayed in the grid.
     3.  To enter criteria using database entities, click **Advanced**, and then enter the column and field name, using a period to separate the column and field. Multiple column and field entries must be separated by a pipe character (||) and space.
         
         You can use operators like IS NULL or IS NOT NULL to build an advanced query. For example, <_column name_>.<_field name_> IS NOT NULL || <_column name_>.< _field name_>.
         
     4.  Click **Apply**.
12.  To define the criteria to group inventory into a picking container:
     1.  Under **CARTON ASSIGNMENTS**, click **Cartonization Criteria**.
     2.  To select criteria from displayed entities:
         1.  If the advanced query is displayed, click **Simple**.
         2.  If the available entities are not displayed, click **Show Available**.
         3.  In the **Available** grid, select the entities that you want to use as criteria.
         4.  Click **Add Selected**. The entities are added to the **Selected** grid.
         5.  To remove criteria, in the **Selected** grid, select the criteria to remove, and click **Remove selected**.
         6.  To reorder the criteria, in the **Selected** grid, click a row, and then click the up or down arrow to move the selected criteria. The application applies the criteria in sequential order according to how it is displayed in the grid.
     3.  To enter criteria using database entities, click **Advanced**, and then enter the column and field name, using a period to separate the column and field. Multiple column and field entries must be separated by a pipe character (||) and space.
         
         You can use operators like IS NULL or IS NOT NULL to build an advanced query. For example, <_column name_>.<_field name_> IS NOT NULL || <_column name_>.< _field name_>.
         
     4.  Click **Apply**.
13.  Click **Save**.

## Pick Cartonization fields

 
| Field | Description |
| --- | --- |
| Enable Cartonization | If Enabled, picking cartonization is enabled for the warehouse. Cartonization is the process by which the application determines which items are to be packed together in a container and which size container is to be used. Picking cartonization is typically used when operators pick product directly to the final shipping container.<br > If Disabled, the application does not create cartonized picks during allocation and pick release. |
| Enable Carton Routing Groups | If Yes, then processing by carton routing group is enabled for the warehouse. A carton routing group specifies one or more carton types or a number of carton types (such as less than 3 or more than 6) that are grouped together for processing. For example, if certain pack stations in the warehouse operate more efficiently (higher throughput) based on the carton types or number of carton types that pass through it, then you can create a carton routing group that can be used to direct shipments that require certain carton types to specific pack stations. See [Carton routing groups](#Carton_routing_groups).<br > If No, then carton routing groups are not enabled. |
| Splitting Picks | If Yes, a pick quantity can be split and deposited into multiple picking containers when processing multiple containers for any single shipment.<br > If No, the entire pick quantity must be deposited to one picking container. If you use the complex cartonization method, then splitting is allowed regardless of this value. |
| Sensitive Item Carton | If Yes, an item that is configured as Pick to Box needs to be picked to a sensitive item carton (box) before being cartonized into a shipping carton. It is used, for example, to pack a fragile item in a protective box before packing the item in a container with other items, or to pack one or more small items in a box so that the items do not get lost in the shipping container. During cartonization, the footprint of the carton will be considered instead of the footprint of the item. Therefore, you should also assign a repack class to the item that is same as the repack class assigned for the sensitive item carton.<br > If No, sensitive item cartons will not be considered during pick cartonization. |
| Grouping | Value that represents the maximum number of sensitive item cartons that can be packed into a single picking container. If no value is defined, then the number of sensitive item cartons is subject to the weight, volume, and other limiting criteria defined for the picking container.<br > Only available if **Sensitive Item Carton** is set to Yes. |
| LPN Level | LPN level at which an item configured for Pick to Box can be picked to a carton that has been configured for sensitive items.<br>-   • **LPN**: Typically a full pallet pick.
<br>-   • **Sub-LPN**: Typically a case pick.
<br>-   • **Detail LPN**: Typically an each pick.
<br > Only available if **Sensitive Item Carton** is set to Yes. |
| Cartonization Method | The cartonization method that determines how the application performs automatic cartonization processing.<br>-   • **Volume**: Cartonization is based on a calculated volume. The application sorts the list of possible cartons in a descending volume sequence. Volume is calculated as (length x width x height x fill percentage). The actual item and footprint dimensions are used to ensure that the item will fit into the carton in some orientation. Each item is checked individually, therefore, if each item will fit in some orientation, and the combined volume of the items does not exceed the capacity of the carton, the carton will be used.
<br>-   •
    
    **Complex**: Cartonization is based on volume and additional calculations. This method also uses volume-based calculations (as described for the Volume method), but after a carton passes through the volume-based method, the application performs additional calculations when the carton type is downsized. Complex cartonization takes place after the application determines the contents of the carton; the additional calculations validate whether the picks will fit into a smaller carton by using different possibilities of orientation and placement. Only after finding a successful packing combination will the application select a smaller carton.
    
    <br>
    
    Depending on the number of items in the carton, the number of iterations can quickly grow into the millions. For performance reasons, you must configure the maximum number of iterations that can occur. Even though not every mathematically possible solution is considered, the Complex method provides a successful packing combination based on the random sampling.
    
    <br> |
| Maximum Iterations | Value limits the number of iterations the application performs during complex cartonization processing. You use this limit to avoid a significant decrease in the application performance. The default value is 750000. Contact your Blue Yonder project team before changing the default value.<br > Only available if the **Cartonization Method** is **Complex**. |
| Popup Iterations | Value that represents the percentage of popup iterations to decrement if the abandonment limit is reached during complex cartonization. This value is used for performance reasons to accomplish a sampling of possible solutions rather than processing every possible solution. The default value is 50.0. Contact your Blue Yonder project team before changing the default value.<br > Only available if the **Cartonization Method** is **Complex**. |
| Cancel Pick Release | If Yes, the application will not release picks for a shipment when a cartonization error occurs. A cartonization error occurs when the dimensions or weight of an item that is being cartonized exceeds the limits that are defined for the largest available carton enabled for cartonization and in its repack class. If an error occurs, the application prevents pick release for all picks in the wave or shipment in which the cartonization error occurred, and the picks are set to an Error status. Picks that trigger a cartonization error can either be cancelled and the remaining picks for an order or wave can be reset to a Pending status; or the cartonization error can be resolved, and all picks can be reset to a Pending status.<br > If No, the application will release the pick regardless of whether the item can fit in the largest available carton. If the item exceeds carton limits, the application will select the largest available carton enabled for cartonization by default. |
| Abandonment | Value for the maximum number of iterations that are performed during complex cartonization before a specific packing pattern is abandoned. This value is used for performance reasons to direct the application to stop processing a possible solution set after a number of unsuccessful attempts, and move on to a different possible cartonization solution. When the application stops an iteration, the abandonment limit is decremented by the value for **Popup Iterations** (for example, by 50 percent), and processing continues. The default is 2000.<br > Only available if the **Cartonization Method** is **Complex**. |
| Work Reference Verification | If Yes, during RF carton picking or case confirm, the Ref (work reference) field is enabled on the RF Pickup screen and a work reference number is displayed.<br > If No, the work reference number is displayed but the Ref field is not enabled, which relieves the RF operator from having to enter through this field (saving a keystroke) and prevents the operator from inadvertently scanning an LPN into this field. |
| Destination Carton Identifier | Value that determines whether the application displays the application-generated carton number or the UCC label number for the destination carton on RF screens during carton picking.<br>-   • **UCC Label Number**: The UCC number is displayed on the operator's RF device during carton picking.
<br>-   • **Carton Number**: The application-generated carton number is displayed on the operator's RF device during carton picking. |
| Work Zone Restriction | If Yes, operators can perform carton picks outside their designated work zone. A work zone is a designated area in a work area and is typically defined as a group of locations that are in the same general vicinity. For example, an entire narrow-aisle area can be considered a single work area, and each aisle can be set up as a separate work zone.<br > If No, operators perform carton picks in their designated work zone and then deposit the cartons to a valid pickup and deposit (P&D) location so that they can be completed by another operator in another work zone. |
| RF Forms | If Yes, the **RF Form Name** field becomes available so that you can specify the name of the custom RF screen that is displayed when an RF operator completes that last pick of a cartonized series of picks.<br > If No, then when the operator has completed the last pick of a cartonized series of picks, a message is displayed stating that the picking for the case is complete. |
| RF Form Name | Name of the custom RF screen that is displayed when the RF operator has completed the last pick of a cartonized series of picks. The screen should be one that was created specifically for this situation.<br > Only available if the **RF Forms** field is set to Yes. |

## Cartons fields

 
| Field | Description |
| --- | --- |
| Carton Name | Name that identifies the carton. A carton is a corrugated box or container of any size that serves as packaging for an item. Each type of carton is defined by a configuration that defines what the carton can hold and how the carton is used. |
| Sensitive Item | If Yes, the carton is used for items that are configured to be picked to sensitive item cartons (pick to box items). These items, when picked at a specified LPN level, are first picked to a sensitive item carton before being packed into another carton for shipping.<br > If No, the carton is not used for items that are configured for Pick to Box. |
| Description | Description of the carton. Descriptions let you further define the carton. For example, if a carton's name is B1, the description might be "Box Size 1" or "Box 15L x 15W x 15H". |
| Labels | Determines the point at which labels are printed.<br>-   • **Before picking**: The carton has pre-printed labels. Select this option is selected to indicates that labels are printed prior to the time of picking.
<br>-   • **At the start of picking**: The carton does not have pre-printed labels. Select this option to indicate that labels need to be printed at the time of picking. |
| Pallet Type Carton | If Yes, the carton is a physical pallet, not a box. A carton of this type is available for use only during pack station processing. It is typically used to process inventory that has been picked as a full case or box, and does not require over-packing to a shipping carton. Instead, the operator can pack the cases or boxes directly to the pallet. The application does not consider the pallet carton type for any other cartonization process. The fields related to cartonization processing are not available for this carton type.<br > If No, the carton is not a physical pallet. |
| Length | Length of the inside of the carton. |
| Width | Width of the inside of the carton. |
| Height | Height of the inside of the carton. |
| Weight | Weight of the carton. |
| Max Weight | Maximum weight of inventory that the carton can accommodate. |
| Maximum Carton | Value representing the percentage of the carton that will be filled during cartonization. The fill percentage is calculated as (volume of the item or items) / (total volume of the carton) x 100%. For example, if the carton volume is 1000 and the item volume is 490, then the fill percentage is 490 / 1000 x 100 = 49%. The fill percentage compensates for possible item footprint errors and also allows for packing material to be added to the carton. For example, if you enter 80, then the application will only fill the carton up to 80% of its capacity (volume), leaving 20% of available carton capacity. |
| Work Assignments | If Yes, when this carton is included in a picking work assignment, and the application determines that there is available space in the carton, the application adds additional case or each picks to the work assignment to fill the available space in the carton. This attribute only applies to work assignments that have a break value based on Volume.<br > If No, the application will not add additional picks to the work assignment in order to fill available space in the carton. |
| Maximum Last Carton | Value representing the percentage of the last carton that will be filled during cartonization. The fill percentage is calculated as (volume of the item or items) / (total volume of the carton) x 100%. For example, if the carton volume is 1000 and the item volume is 490, then the fill percentage is 490 / 1000 x 100 = 49%. Generally, this value is greater than the maximum carton percentage. When packing the final items you can exceed the default fill percentage for the last carton without having to package items in a new carton. For example, if you enter 90, then the application will only fill the last carton up to 90% of its capacity (volume), leaving 10% of available carton capacity. |
| Picking | If Yes, the carton is considered for use by the automatic picking cartonization process. The application performs the automatic picking cartonization process by selecting the best carton type and directing the operator to use it during picking.<br > If No, the carton is not used by the automatic picking cartonization process. |
| Shipping | If Yes, the carton is considered for use by the automatic shipping cartonization process. The application performs the automatic shipping cartonization process by selecting the best carton type and directing the packing operator to use it when packing picked inventory into a shipping container during pack station processing.<br > If No, the carton is not used by the automatic shipping cartonization process. |
| Pack Station | If Yes, the carton can be used for pack station processing during which an operator manually packs the carton with picked inventory. Pack station processing can automatically determine the best carton to be used for the inventory at the pack station. During this process, the application will only select from the list of cartons that are supported for the pack station process.<br > If No, the carton is not used for pack station processing. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
