---
title: "Bulk Picking"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/bulk_picking.htm"
source: "/content/bulk_picking.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Outbound"
  - "Picking "
  - "Bulk Picking"
sections:
  - "Bulk picking setup"
  - "Example: Bulk picking"
  - "Bulk picking use scenarios"
  - "Bulk picking deposit"
  - "Configure bulk picking"
images: []
source_sha1: 23c641de8d237e1ca8be67077b975cc932047e16
---
# Bulk Picking

A bulk pick is a single pick that satisfies multiple order or work order lines for which the inventory would otherwise have been picked separately. Bulk pick processing allocates matching inventory for multiple order or work order lines together into larger unit of measure (UOM) picks so as to reduce the number of smaller UOM picks required to satisfy the orders. For the application to allocate bulk picks, the order or work order lines must have the same item and item footprint, as well as identical values for any other order, work order, shipment, or customer attributes that you specify.

For example, assume that three different orders are planned into multiple shipments, but the inventory needed to satisfy those orders is identical. If each order required 5 cases and 15 cases made up a pallet, then instead of allocating the shipments separately and creating multiple case picks, using bulk picking, the application would allocate the shipment lines together to create a single pallet pick. Once the pallet pick is complete, an operator breaks down the pallet and deposits each shipment quantity to a specified location.

When a warehouse, customer, and order type or work order type are configured to allow bulk picking, the application combines the line quantities of eligible orders or work orders for bulk pick opportunities at the time of allocation. However, if necessary, you can disable bulk pick processing at the time of allocation.

For example, assume that 20 cases from multiple shipments are eligible to be combined into a single pallet bulk pick, which the application would process upon allocating the shipments. However, prior to completing allocation, you identify an excess amount of pick work is scheduled to be performed in the pallet pick location, but the case pick location has the capacity for more pick work. Instead of allocating the inventory as a bulk pick and waiting for the work to be completed in the pallet location, you can disable bulk picking during shipping allocation or during work order processing, so the order or work order lines are allocated separately and can be immediately picked as cases in the case pick area.

## Bulk picking setup

You must perform the following tasks to enable bulk pick processing:

1.  Configure bulk picking for the warehouse. Enable bulk picking for the warehouse and, for a 3PL environment, for individual clients. You also select the bulk pick unit of measure, the order and work attributes that must match for lines to be combined in a bulk pick, the sequence in which the application processes the lines, and how residual inventory is returned to storage. See [Configure bulk picking](#Configure_bulk_picking).
2.  Enable bulk picking for specific customers, orders, and work orders. Enable bulk picking for customers, orders, and work orders. For bulk pick processing to take place, the customer and either the order or work order must be enabled for bulk picking.
    1.  Enable bulk pick processing for customer types. Customers created with these customer types, by default, are enabled for bulk pick processing; however, you can disable bulk pick processing for specific customers created with this customer type. See [Customer Types](../../partners/customers/customer-types.md).
    2.  Enable bulk pick processing for specific customers. Orders for these customers, by default, are eligible for bulk pick processing at the time of allocation. See [Existing Customers](../../partners/customers/existing-customers.md).
    3.  Enable bulk pick processing for order types. Orders that are created using these order types are eligible for bulk pick processing, if the warehouse and customer are also enabled for bulk picking. Eligibility is determined at allocation. See [Outbound Order Types](../order-processing/outbound-order-types.md).
    4.  Enable bulk pick processing for work order types. Work orders created using these work order type are eligible for bulk pick processing if the warehouse and customer are also enabled for bulk picking. Eligibility is determined at allocation. See [Work Order Types](../../production/work-order-types.md).
3.  Enable bulk picking for each unit of measure (UOM), at the warehouse level, in which you want bulk picks allocated. The UOMs enabled are the highest level at which a bulk pick can be performed. For example, if you enable Pallet as a bulk picking UOM and if Case is enabled as the bulk picking UOM on the default item footprint, then during bulk pick processing the application can combine order lines for case quantities of the item into larger bulk picking UOM quantities, such as pallets. See [Units of Measure](../../inventory/units-of-measure.md).
    
    UOMs configured at the warehouse level automatically update the UOMs selected for bulk pick processing. However, any changes make on the bulk pick processing configuration do not affect the warehouse level configuration.
    
4.  Enable bulk picking for an item footprint UOM that you want to allow to be combined into bulk picks. Enable the item footprint UOMs that you want to allow to be combined into bulk picks. For example, if you enable the Case UOM on an item footprint, indicates that the UOM can be aggregated (combined) for bulk picking. See [Items](../../inventory/items/items.md).
5.  Define a bulk picking release rule. The release rule is defined for individual pick methods and can be configured so that the application creates and releases work for bulk picks. See [Pick Methods](pick-methods.md). After you define the bulk pick release rule for the pick method, the pick method can be added to an allocation search path. See [Replenishment Search Paths](../../inventory/replenishments/replenishment-search-paths.md).
6.  Configure a consolidation area and locations to which bulk picks are deposited. Bulk picked inventory is directed to separate deposit locations, one for each shipment or work order associated with the bulk pick. The deposited inventory is eventually consolidated with the remaining picks for the shipment or work order. See [Areas](../../warehouse/areas.md) and [Location configuration process](../../warehouse/locations.md).
7.  Configure a movement zone that contains locations configured for consolidation. Create a movement zone that contains locations to which bulk picks are deposited and consolidated into complete shipments or work orders. This movement zone can be configured as a hop to zone in an outbound movement path. See [Movement Zones](../../inventory/movement/movement-zones.md).
8.  Configure an outbound movement path for bulk picks. The source zone is the movement zone that contains the locations at which bulk picks take place. The hop is the movement zone that contains the consolidation locations at which bulk picks are deposited and sorted into shipments. The destination movement zone contains the destination locations for the inventory (such as ship staging or production staging).
    
    If you want the application to create directed work to move the inventory out of the hop zone, you need to configure an RF directed move for the hop zone. The work is created immediately when an LPN is deposited to a location in the hop zone. If a directed move is not configured for the hop zone, then operators use undirected work to move the inventory out of the hope zone. See [Movement Paths](../../inventory/movement/movement-paths.md).
    

## Example: Bulk picking

The following is an example of how the application processes a bulk picking opportunity when combining the shipments for three separate orders.

**Assumptions**:

-   Pallet is the only bulk picking UOM configured for the warehouse. The bulk picking UOM is the UOM to which smaller eligible item footprint UOMs can be combined for a bulk pick.
-   Each order type and customer associated with the orders is enabled for bulk picking.
-   Item footprint configuration
    
    The following table displays the item footprint information for item SHIRT. Since bulk picking is enabled for the Each and Case UOM, the application can combine both UOM quantities on the shipment lines and attempt to reach the Pallet quantity.
    
       
    | Item | UOM | Unit quantity | Allow bulk picking |
    | --- | --- | --- | --- |
    | SHIRT | Each | 1 | Yes |
    | Case | 2 | Yes |
    | Pallet | 100 | No |
    

**Orders in shipment batch**:

The following table displays order information for three separate orders being allocated as a part of the same shipment batch. Each order is part of an order type that is enabled for bulk picking.

  
| Order | Item | Quantity |
| --- | --- | --- |
| Ord1 | SHIRT | 80 |
| Ord2 | SHIRT | 80 |
| Ord3 | SHIRT | 46 |

**Results**:

The application combines the quantities of the orders for a total of 206 units. After considering the bulk picking configurations, the application creates 2 bulk pallet picks to satisfy 200 units and 3 case picks to satisfy the remaining 6 units.

## Bulk picking use scenarios

**Quantity sort**

When the application processes bulk picks, it uses the quantity sort configuration to determine which line quantities are added together first to form bulk picks. The application assigns order or work order line quantities to bulk picks starting with either the smallest or largest quantities first, depending on the configuration.

For example, the application is processing the order lines in the following table using bulk picking. The bulk pick UOM is Pallet and there are 20 cases to a pallet.

 
| Order line | Case quantity |
| --- | --- |
| ORD1 | 10 |
| ORD2 | 5 |
| ORD3 | 5 |
| ORD4 | 5 |
| ORD5 | 5 |
| ORD6 | 3 |
| ORD7 | 2 |

If you configure the application to sort by the largest quantities first, then the application groups ORD1, ORD2, and ORD3 (because their total quantity equals one pallet) into a bulk pallet pick. The remaining four order line quantities would be picked separately, and the bulk pick breakdown would include three deposits (one for ORD1, ORD2, and ORD3).

If you configure the application to sort by the smallest quantities first, then the application groups ORD7, ORD6, ORD5, ORD4, and ORD3 (because their total quantity equals one pallet) into a bulk pallet pick. The remaining two order line quantities would be picked separately, and the bulk pick breakdown would include five deposits (one for ORD7, ORD6, ORD5, ORD4, and ORD3).

**Return to storage**

When the application allocates inventory and creates a pick work assignment, it is possible that a threshold pick is generated depending on the quantity needed for an order and the threshold percentage in the item footprint configurations. For bulk picking, the application utilizes the threshold configuration and may generate a full pallet pick when the entire full pallet quantity is not needed. When this occurs, the residual inventory must be returned to a case storage location. The application directs the operator to return excess inventory from a threshold bulk pick to storage either immediately following the threshold pick or after the rest of the picks have been deposited.

-   **Immediately following picking**: Residual inventory is returned to storage before the operator deposits the rest of the picks. For example, if this option is selected, for a pallet bulk pick in which one case is excess due to a threshold pick, the operator is directed to deposit the single case in an appropriate storage location before being directed to deposit the rest of the picks in the breakdown location.
-   **After breakdown**: Residual inventory is returned to storage after the operator deposits the rest of the picks in the breakdown location. For example, if this option is selected, then for a pallet bulk pick in which one case is excess due to a threshold pick, the operator is directed to deposit each of the picks to its appropriate breakdown location and then deposit the excess case to an appropriate storage location.

## Bulk picking deposit

Bulk picking deposit is a process in which bulk picked inventory is directed to separate deposit locations, one for each shipment associated with the bulk pick, and then consolidated with the rest of picks for the shipment according to application configurations. All of the inventory in a bulk picking deposit location is shipped together. Because distribution deposit and bulk picking deposit are the same process, a location that is set up for cross-dock distribution deposit can also be used for bulk picking deposit.

During the bulk picking deposit process, the application directs the operator to the deposit locations in a logical order, based on travel sequence, until all the inventory planned for a shipment has been placed in the deposit location. The bulk picked LPNs remain in the deposit locations until they are closed and directed to a staging area or to be loaded directed on transport equipment. LPNs are considered closed when no additional inventory can be added to the existing LPN. Closing an LPN is completed on the RF device by the operator working in the location.

If configured to do so, when the operator is directed to a deposit location, the application directs the operator to an existing, uncompleted LPN on which to deposit the inventory. At this point, the operator has the following options:

-   Deposit the entire quantity to an existing LPN.
-   Deposit a partial quantity to the existing LPN and close it. The remaining quantity is either deposited to another existing LPN or a new partial LPN is created.
-   Choose not to deposit any quantity to the existing LPN, and instead create a new partial LPN from the deposited inventory.
-   Skip the location and return to it later.
-   Stage the LPN in a pickup and deposit location for another operator to resume the process later.

A bulk pick can contain inventory with mixed attributes. During the deposit process, if a bulk pick contains mixed attributes, the application prompts the operator for the attribute values. This is done for mixed LPNs so that the application can track exactly which inventory is being included on each shipment. Similarly, if the inventory is serial number tracked or requires the operator to enter a catch weight, the application prompts the operator for that information before completing a deposit.

After the operator completes the deposits for a bulk pick, an audit is performed to determine if there is any residual inventory. During the application-generated audit, the operator is required to enter whether there is residual inventory on the LPN when the deposit work is completed. If there is residual inventory, the operator enters the quantity and the application compares the entered residual quantity against the expected residual quantity. If the quantities match, the audit passes and the operator is directed to place the residual inventory in a storage location determined by putaway. If the residual inventory does not match the quantity expected by the application, the audit fails and the inventory is directed to an exception location where it can be determined what caused the discrepancy in the residual inventory.

## Configure bulk picking

1.  Select **Configuration > Outbound > Picking > Bulk Picking**.
2.  Enter information in the following fields:
    
     
    | Field | Description |
    | --- | --- |
    | Enable Bulk Picking | If Enabled, bulk pick processing is enabled for the warehouse. Bulk picking is a process in which the application attempts to group multiple order or work order lines of the same item and allocate them together as a larger UOM pick. If enabled, the application evaluates bulk picking configurations for eligible order and work order lines before allocating the inventory.<br > If Disabled, the application does not attempt allocate order or work order lines together for bulk picks. |
    | Quantity Sort | The sequence in which eligible order or work order lines are assigned to bulk picks is based on line quantities, so that the application assigns lines to bulk picks in sequential order starting with either the smallest quantities or the largest quantities. See [Bulk picking use scenarios](#Bulk_picking_use_scenarios).<br>-   • **Largest quantity first**: Assigning the largest quantities first may result in a smaller number of lines being included in a bulk pick, but results in fewer breakdown deposits.
    <br>-   • **Smallest quantity first**: Assigning the smallest quantities first may result in fewer trips to pickfaces, but results in more breakdown deposits since a larger number of lines are included. |
    | Return to Storage | Determines when the application returns threshold bulk picked inventory to storage. See [Bulk picking use scenarios](#Bulk_picking_use_scenarios).<br>-   • **Immediately following picking**: Excess inventory is returned to storage before the operator deposits the rest of the picks. Select this option if the residual inventory is stored in a location that is close to the bulk pick zone and your breakdown location is farther away; in this instance, this option may reduce travel time.
    <br>-   • **After breakdown**: Excess inventory is returned to storage after the operator deposits the rest of the picks. Select this option if you want to ensure that each shipment receives the required quantity so that in the event of a discrepancy the residual inventory would be affected instead of the distributed inventory. Additionally, select this option if the warehouse equipment used for bulk picking is not allowed in the zone in which the residual inventory is stored. |
    
3.  To select the clients that allow bulk picking:
    1.  Under **ENABLEMENT**, click **Clients**.
    2.  In the **Available Clients** column, select the check box next to the clients that apply.
    3.  Click **Save**.
4.  To select the UOMs in which bulk picks can be allocated:
    1.  Under **BUILDING THE PICK**, click **Units of Measure**.
        
        **Note**: Available units of measure are those that have been configured and enabled for the warehouse. See [Units of Measure](../../inventory/units-of-measure.md).
        
    2.  In the **Available Unit of Measure** column, select the check box next to the UOMs that apply.
    3.  Click **Save**.
5.  To define the criteria on an order or work order that is required to match for picks to be combined into a bulk pick:
    1.  Under **BUILDING THE PICK,** click one of the following buttons:
        -   **Order Attributes**.
        -   **Work Order Attributes**.
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
6.  Click **Save**.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
