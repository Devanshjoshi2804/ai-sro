---
title: "Footprints"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/footprints_config.htm"
source: "/content/footprints_config.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inventory"
  - "Items"
  - "Footprints"
sections:
  - "Item footprints"
  - "Add or modify a footprint"
  - "Delete a footprint"
  - "Footprint fields"
  - "Item Footprint UOM fields"
images: []
source_sha1: ffe331514e4d4d1fa4d834f185e093eaa108613e
---
# Footprints - Configuration

A footprint is a code that defines the packaging configuration for an item, including its nesting dimensions, cases per tier, pallet stack height, and default handling unit type. The item footprint also provides the units of measure (UOM) in which the item is packaged, as well as the dimensions and attributes of each UOM.

## Item footprints

An item can be associated with more than one footprint. For example, if an item comes in packaging configurations of 10 cases per pallet and 12 cases per pallet, then two different footprints can be defined for the item to capture both configurations. Each item must be associated with at least one footprint and one footprint must be defined as the default for the item.

The application uses footprint information, along with an item's packaging attributes, during the following processes:

-   **Receiving**: To calculate volume and pallet height. These calculations are used to find a storage location in which the inventory can physically fit.
-   **Cartonization**: To calculate whether the item can fit in an over-pack carton.
-   **Shipment building**: To calculate the volume of a shipment containing the item.

During the receiving process, the default item footprint for the item is displayed for the user to view the packaging levels available for the item. This helps the user enter UOM and quantity information during receiving. The operator can select a different item footprint, or if the application is configured to allow it, the operator can create a new footprint.

You can configure the inbound identification settings to allow operators to create new item footprints using an RF device while receiving, receiving without an order, or performing an inventory adjustment. This functionality allows operators to receive inventory with a case quantity (units per case) that is different from that which already is defined on existing footprints for the item. For example, if the only footprint for an item specifies there are 10 units in each case of inventory, but an operator scans a case of the item that has 15 units, then the operator can create a new footprint (specifying 15 units per case) in order to process the inventory. See [Configure inbound identification](../../inbound/receiving/inbound-identification.md).

**Note**: The application purges a new item footprint that was created on the RF device when no more inventory with that footprint exists in the warehouse.

Footprint information can be received from a host, or it can be manually entered. The following situations are examples of when you will need to manually add a footprint:

-   A new item arrives unexpectedly, and the host has not sent the necessary information
-   The host does not maintain dimensional information about the inventory, and operators must manually measure and enter the footprint code for each new item as it is received
-   An item is received in different size packaging than the packaging in which it is normally received

For more information on adding or modifying a footprint, see [Add or modify a footprint](#Add_or_modify_a_footprint).

## Add or modify a footprint

1.  Perform one of the following tasks:
    -   To add, modify, or copy a footprint for all warehouses in the application, select **Configuration > Inventory > Items > Footprints**.
    -   To add, modify, or copy a footprint specific to the warehouse, select **Inventory** > **Footprints** or configure the footprint from the Item Overrides page.
    -   To add, modify, or copy a footprint for an item from the Items page:
        1.  Select **Configuration** > **Inventory** > **Items** > **Items**.
        2.  In the **Footprint** column, click the footprint associated with the item. The Footprints page is displayed.
        
        **Note**: If an item has more than one footprint, the **Footprint** column displays **Many** (_number of footprints_). Configuring a footprint from the Items page modifies the item footprint for all warehouses in the application. To configure a footprint or check outstanding work for a footprint specific to a warehouse you must access the footprint from the Item Overrides page.
        
    -   To add, modify, or copy a footprint for an item from the Item Overrides page:
        1.  Select **Configuration** > **Inventory** > **Items** > **Item Overrides**.
        2.  In the **Footprint** column, click the footprint associated with the item. The Footprints page is displayed.
        
        **Note**: If an item has more than one footprint, the **Footprint** column displays **Many** (_number of footprints_). Configuring a footprint from the Items Overrides page modifies the item footprint that is overridden for the warehouse.
        
2.  Perform one of the following tasks:
    -   To add a footprint, from **Actions** drop-down list, select **Add**.
    -   To modify a footprint, in the grid, click the footprint.
    
    **Notes**:
    
    -   Only authorized users who have permissions to modify footprints with inventory can modify a footprint if inventory for the item exists in the warehouse.
        
    -   If warehouse-specific values are defined for an item footprint, then updating the item footprint from the Items page does not update the attributes that are overridden for a specific warehouse.
    
    -   To copy a footprint, in the grid, select the check box of the footprint, and then from the **Actions** drop-down list, select **Copy**.
3.  Enter information in the [Footprint fields](#Footprint_fields).
4.  To define UOMs:
    1.  Under **UNITS OF MEASURE**, click **Setup**.
    2.  Perform one of the following tasks:
        -   To add a UOM, click **Add**.
        -   To modify a UOM, in the grid, click the UOM.
        -   To copy a UOM, in the grid, select the check box next to the UOM, and then click **Copy**.
    3.  Enter information in the [Item Footprint UOM fields](#Item_footprint_uom_fields).
    4.  Click **Apply**.
5.  Click **Apply**.

## Delete a footprint

You cannot delete a footprint if it is the default footprint for an item or if inventory for the item exists in the warehouse.

1.  Perform one of the following tasks:
    -   To delete a footprint for all warehouses in the application, select **Configuration > Inventory > Items > Footprints**, then select the check box next to the footprint.
    -   To delete a footprint specific to the warehouse, select **Inventory** > **Footprints**, then select the check box next to the footprint.
    -   To delete a footprint for an item from the Items page:
        1.  Select **Configuration** > **Inventory** > **Items** > **Items**.
        2.  In the **Footprint** column, click the footprint associated with the item. The Footprints page is displayed.
    -   To delete a footprint for an item from the Item Overrides page:
        1.  Select **Configuration** > **Inventory** > **Items** > **Item Overrides**.
        2.  In the **Footprint** column, click the footprint associated with the item. The Footprints page is displayed.
2.  From **Actions** drop-down list, select **Delete**. A confirmation message is displayed.
3.  Click **OK**.

## Footprint fields

 
| Field | Description |
| --- | --- |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Item Client | Name of the client who stores this item in the facility. This field is only displayed in a 3PL environment. |
| Footprint | Name that identifies a footprint, which describes the packaging dimensions and units of measure for the item with which it is associated. |
| Footprint Description | Description that further identifies the footprint. |
| Default Item Footprint | If Yes, the footprint is displayed by default when the item is displayed. One and only one footprint must be defined as the default footprint.<br > If No, this is not the default footprint. |
| Default Handling Unit | Handling unit type that is applied by default (if handling unit tracking is enabled in the warehouse) when a pallet LPN of inventory for the item footprint is received. A handling unit type is group of platforms or containers (such as a pallets or totes) that share the same characteristics such as size and weight as well as whether they are serialized, temporary, and considered a container. The application tracks the on-hand quantity of handling units by type and, for serialized assets, by handling unit LPN. |
| Purge Unused Footprint | If Yes, the footprint is automatically purged from the application when no more inventory with the footprint exists. Select Yes for a footprint that is rarely used, such as one that represents an unusual packaging configuration. This field is automatically set to Yes for a new footprint that is created on a device during receiving.<br > If No, the footprint is not automatically purged when there is no more inventory associated with the footprint. |
| Pallet Stack Height | Maximum number of pallets that can be stacked on top of one another in a location. This value applies when the item footprint is stored in locations configured with a pallet stack height restriction; it does not apply to stacking pallets in transport equipment configured for storage. A value of 0 permits stacking pallets as high as the location capacity allows. |
| Stack Method | Name of the stack method used for stacking pallets in a location. This stack method is used when the pallet level UOM for the item footprint is stored in locations configured with a pallet stack restriction. |
| Cases Per Tier | Number of cases that are typically placed on each tier of a pallet-equivalent UOM for the item footprint. When defining a footprint for which you do not have a layer UOM, you must specify the number of cases that are typically placed on each tier or level of a pallet of inventory. For example, if cases of an item are typically received on pallets that are stacked with 6 cases per level and 3 levels high, totaling 18 cases, the cases per tier would be defined as 6. The application compares the LPN height to the location height to determine if an LPN can fit in a location. |
| Level Units | Number of level units (width) that a pallet-equivalent UOM of this item occupies when deposited to a location associated with a level type. The value you enter here must be considered in relation to other elements of level type configuration, such as the total level units defined for a level type, and how many pallets of this size can be stored on the level. For example, if a level can fit 5 pallets of this size and the level has 10 total level units, then the level unit value for this footprint is 2.<br > If this footprint represents the smallest pallet for the item, the number of level units should be equal to the number of level units in a single location associated with a level type and used to store the item. See [Level units](../../warehouse/locations/level-types.md). |
| Length | Additional length of a single unit of an item when it is stacked inside or on top of other items in the same nesting class. This optional attribute is used by cartonization to fit more inventory into smaller or fewer cartons, thus saving on shipping expenses. |
| Width | Additional width of a single unit of an item when it is stacked inside or on top of other items in the same nesting class. This optional attribute is used by cartonization to fit more inventory into smaller or fewer cartons, thus saving on shipping expenses. |
| Height | Additional height of a single unit of an item when it is stacked inside or on top of other items in the same nesting class. This optional attribute is used by cartonization to fit more inventory into smaller or fewer cartons, thus saving on shipping expenses. |
| Wrap | LPN-level packaging attribute for inventory. LPN packaging attributes are user-defined fields that are used to indicate requirements such as pallet wrapping, use of a slip sheet, and the application of labels on all four sides of a pallet of inventory. |
| Double Wrap | LPN-level packaging attribute for inventory. LPN packaging attributes are user-defined fields that are used to indicate requirements such as pallet wrapping, use of a slip sheet, and the application of labels on all four sides of a pallet of inventory. |
| Label 4 Sides | LPN-level packaging attribute for inventory. LPN packaging attributes are user-defined fields that are used to indicate requirements such as pallet wrapping, use of a slip sheet, and the application of labels on all four sides of a pallet of inventory. |
| Slip Sheet | LPN-level packaging attribute for inventory. LPN packaging attributes are user-defined fields that are used to indicate requirements such as pallet wrapping, use of a slip sheet, and the application of labels on all four sides of a pallet of inventory. |

## Item Footprint UOM fields

 
| Field | Description |
| --- | --- |
| Unit of Measure | Identifier for the packaging level (such as each, inner pack, case, layer, or pallet) at which an item can be received, stocked, tracked, and reported. Units of measure are used in item footprint configurations. |
| Unit Quantity | Number of individual units of the item contained in the unit of measure (UOM). The application automatically updates this value based on the values for UOM Quantity and next UOM. For example, if the configuration has Pallet, Case, and Each UOMs, and there are 10 eaches per Case and 10 cases per Pallet, then the unit quantity for Pallet is 100. |
| System Equivalent UOM | Inventory level at which the application tracks the UOM. The application supports inventory tracking (using license plate numbers) at the following levels: LPN (pallet-equivalent UOM), sub-LPN (case-equivalent UOM), and detail-LPN (unit or each UOM). The case and pallet equivalent settings are required for every footprint. The application automatically defines the smallest UOM on the footprint as the detail-LPN level.<br>-   • **None**: The UOM is not an inner pack, case, or pallet equivalent unit of measure. Select None, for example, if the UOM represents a single unit (each) or a layer.
<br>-   • **PACK EQUIVALENT**: The UOM represents an inner pack. An inner pack is a less-than-case quantity that consists of multiple units (eaches) packaged together. The footprint configuration defines the number of units per pack. It is used, for example, to qualify a quantity on an order or work order by number of units per pack instead of by footprint.
<br>-   • **CASE EQUIVALENT**: The UOM represents a sub-LPN level of inventory.
<br>-   • **LAYER EQUIVALENT**: The UOM represents a single tier (layer) on a pallet of inventory. A layer typically consists of a number of cases. This system equivalent UOM is only used for reporting pick activity when Warehouse Labor Management is integrated with the application.
<br>-   • **PALLET EQUIVALENT**: The UOM represents an LPN level of inventory. Select this option for the largest UOM in the footprint. |
| Receive | If Yes, the unit of measure (UOM) is the default UOM in which the inventory is received, added, or modified during inventory identification. This default UOM can be overridden, if necessary, during inventory identification. For example, if the item is typically received in full pallets but occasionally arrives at the receiving dock as less than a full pallet, the operator can choose a different UOM defined for the footprint to identify the quantity received.<br > If No, this is not the default UOM in which the item is identified. |
| Length | Length of the item footprint UOM. To change a measurement unit, click the unit next to the field, and select a different unit. |
| Width | Width of the item footprint UOM. To change a measurement unit, click the unit next to the field, and select a different unit. |
| Height | Height of the item footprint UOM. To change a measurement unit, click the unit next to the field, and select a different unit. |
| Gross Weight | Weight of the item footprint UOM that includes its packaging. To change a measurement unit, click the unit next to the field, and select a different unit. |
| Net Weight | Weight of the item footprint UOM, excluding the weight of its packaging. To change a measurement unit, click the unit next to the field, and select a different unit. |
| Cartonization | If Yes, indicates that the unit of measure can be cartonized (picked to a carton). Cartonization is an allocation process that determines which picks can be packed together in cartons for shipment, and which size carton should be used. Select Yes if you want to be able to allocate the item in this UOM for picking to a carton. Cartonization is typically enabled for each or piece UOMs that are small enough to fit into the picking and shipping cartons that your facility uses.<br > If No, the UOM will not be considered a candidate for cartonization. Select No, for example, for pallet UOMs and for case UOMs that are too large for a carton. |
| Carton Distribution | If Yes, the UOM must be placed in a carton if it is part of a distribution order. A distribution is a pre-allocation of a warehouse receipt to a single store; it connects a planned inbound order to an outbound order. The application evaluates this attribute during the distribution process; so that for a distribution order, you can require a UOM (even if it is not normally cartonized) to be packed into a shipping carton prior to being combined with other distribution inventory at a distribution deposit location. If inventory for which carton distribution is required is picked to a carton, the application does not direct the operator to pack it into another carton during the distribution process, since it has already been cartonized into the most efficient shipping carton.<br > If No, the application does not attempt to cartonize the UOM when it is part of a distribution order. |
| Bulk Picking | If Yes, indicates that the unit of measure can be aggregated for bulk picking. Bulk pick processing allocates matching inventory for multiple outbound order or work order lines together into larger UOM picks so as to reduce the number of smaller UOM picks required to satisfy the orders. For example, if Case is enabled as the bulk picking UOM on the default item footprint, then during bulk pick processing the application can combine order lines for case quantities of the item into larger bulk picking UOM quantities, such as pallets. The larger bulk picking UOM that is eligible to be the physical pick resulting from combining smaller UOM quantities is defined in Units of Measure. If you select Yes, the when eligible order or work order lines for the item are allocated using bulk pick processing, the application combines order lines for this UOM quantity in order to allocate the inventory at a higher, bulk picking UOM.<br > If No, the application does not combine order lines for the UOM quantity; and instead the order lines are allocated separately. Only available for the default item footprint, and only if bulk picking is enabled for the warehouse. |
| Threshold Percentage | Minimum percentage value of the UOM capacity that a partial UOM must contain to qualify as a threshold pick. Threshold picking is a pick process that is used to satisfy an order for a less than full platform quantity. For example, if a full pallet consists of 10 cases, and an order line requires 9 cases, the operator can be directed to pick a full pallet and then remove the unneeded case, rather than being directed to pick 9 cases separately.<br > Valid values are from 1.000 to 100.000. The smallest UOM must have a value of 100.000. Specify a threshold percentage for the pallet level UOM, if your facility uses threshold picking. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
