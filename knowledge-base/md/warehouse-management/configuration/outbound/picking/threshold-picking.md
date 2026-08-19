---
title: "Threshold picking"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/threshold_picking.htm"
source: "/content/threshold_picking.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Outbound"
  - "Picking "
  - "Threshold picking"
sections:
  - "Threshold picking setup"
  - "Example: Single pick threshold pick"
  - "Example: Starter pallet for a work assignment"
images: []
source_sha1: f1aed1b502764fddab86add676058dae468d823e
---
# Threshold picking

Threshold picking is a pick process that is used to satisfy an order for a less than full pallet (LPN) quantity. For a threshold pick, the operator is typically directed to pick more than the order line quantity when that quantity is a defined percentage less than the next higher UOM. For example, if a full pallet consists of 10 cases, and an order line requires 9 cases, the operator can be directed to a pallet storage location to pick a full pallet and then remove the unneeded case, rather than being directed to pick 9 cases separately from a case pickface. The unneeded inventory is removed to a new LPN and put away to a suitable storage location or pickface, or left in a pickup and deposit (P&D) location for another operator to put away.

When allocating for an order line quantity that qualifies for a threshold pick, the application generates the threshold pick (for example, a pallet) and then allocates the required inventory (for example, 9 cases) against the threshold pick. The unneeded case that was not allocated for the pick is available to be used for another order.

Threshold picking can be used for the following reasons:

-   Reduces overall picking time for a work assignment pick
-   Eliminates the need for the operator to obtain a platform (handling unit) to pick to
-   Reduces the number of cases that need to be handled for the case pick
-   Eliminates having to define a pick-to identifier at the start of a work assignment
-   Reduces the need for replenishments to the pickface because threshold picks are sourced from storage locations
-   Consumes partial pallets in the warehouse
-   Provides a stable base on which subsequent picks can be placed

## Threshold picking setup

The following steps are the tasks that you must perform to configure the application to allocate threshold picks:

1.  Configure items for threshold picking:
    
    -   Configure item footprint with a threshold percentage. For each item that you want to enable for threshold picking, you must configure the item footprint by defining the threshold percentage for the unit of measure (UOM) that should be picked instead of the lower UOM. Typically, a threshold percentage is defined for the pallet UOM.
        
        For example, if you set the threshold percentage for the Pallet UOM to 75%, and the quantity allocated falls between 75% and 100% of a pallet, the operator may be directed to perform a pallet pick for the item. Quantities not needed for the pick are left at the location moved to an appropriate partial pallet location according to the storage search path configurations.
        
    -   Configure the item threshold pick variance. Threshold pick variance is the amount of variance that a pick can be over or under the required pick quantity. If an operator picks a quantity greater than or less than that which is required for the pick, and the quantity exceeds the threshold pick variance, then a message is displayed asking the operator to acknowledge that the pick is over or under the allowed variance. A value of zero means a message is always displayed when a pick does not match the required pick quantity; a value of 100 means that a message is never displayed.
        
        If threshold picking is enabled for the item footprint, then it is recommended to set the threshold pick variance percentage to a value that accommodates a full pallet quantity. For example, if the threshold percentage (indicated on the item footprint) is set to 75%, and a standard full pallet for the item is 100, the application attempts to generate a threshold pick when the order line quantity for the item is between 75 and 99. If the order line quantity is 75 and the pick variance percentage is 34%, then a message is displayed if the operator attempts to pick less than 50 or greater than 101 units (34% of 75 = 25.5; 75 - 25.5 = 49.5; 75 + 25.5 = 100.5). So, in this example, the message would not be displayed to the operator when picking a full pallet quantity of 100 to satisfy an order quantity of 75.
        
    
    See [Items](../../inventory/items/items.md).
    
2.  Configure the allocation search path for the pick zone. Configure a search path rule for each pick zone in which you allow threshold picking by setting the **Threshold Pick** field to Yes.
    
    You must also configure the search path to allow a pick quantity to be allocated in the UOM required for a threshold pick (such as Pallet UOM). See [Configure allocation search paths for order picks](../allocation/allocation-search-paths.md).
    
3.  Configure the UOMs to be pickable. For all of the pick zones in which you want to generate threshold picks, you must select the LPN level that can be picked. For example, for a pallet pick zone, you could select the LPN and sub-LPN levels. See [Pick Zones](../allocation/pick-zones.md).
4.  Configure the RF to prompt for pick quantity confirmation. For a threshold pick, it is recommended that you configure the application to force the operator to enter the quantity for the LPN that is being picked for a threshold pick. Ordinarily, the operator may not be required to enter a quantity when picking an LPN, but this should be required for a threshold pick in order to confirm that a quantity different from the required quantity was picked. See [Pick Settings](pick-settings.md).
5.  Configure a pick method. A pick method is used to define the type of pick that is created when inventory is allocated and released for picking. For each of the pick methods that you want to use for threshold picking (such those that support case picks), you must configure the threshold pick release rules to create work using the Threshold Pick work operation. See [Pick Methods](pick-methods.md).
6.  Configure work operations. For the Threshold Picking operations, select the users and equipment that are authorized to perform the operation. See [Work Operations](../../work/work/work-operations.md).

## Example: Single pick threshold pick

The following process illustrates a single pick threshold pick. In this example, when the order is allocated, the operator is directed to a pallet storage location to pick a pallet, to remove 1 case from it, and to use the 9-case pallet to fulfill the pick. Storage location search (putaway process) finds an appropriate storage location for the 1 case. The operator is then directed to deposit the 1 case in the new application-defined location, and to deposit the pallet of 90 units (9 cases) to the staging area for shipment.

For this example, the following values are defined for threshold picking:

-   Pallet = 100 units
-   Case = 10 units
-   Threshold percentage = 75%
-   Order quantity = 90 units (9 cases)

The following process takes place for generating and performing the threshold pick:

1.  To generate the threshold pick, the user performs the following tasks:
    1.  Allocate an order.
    2.  View the details of the allocation to confirm that a threshold pick was allocated.
2.  To perform the threshold pick, the RF operator performs the following tasks:
    1.  Select the menu and option for picking.
    2.  When prompted, enter the work reference number for the threshold pick.
    3.  Go to the location of the pick and then on the threshold pick screen, scan the LPN.
    4.  If the inventory falls outside of the threshold pick variance, type **Y** to pick it up anyway.
    5.  Enter the total quantity on the LPN that is being picked. For this example, the operator enters 10 cases.
    6.  On the threshold split screen, enter a new LPN for the 1 case that will be split off of the pallet.
    7.  From the deposit screen, view the deposit location for the partial pallet quantity and deliver that 1 case to the location. Alternatively the operator can scan a P&D location and deposit the case there for someone else to move.
    8.  On the next product deposit screen, view the deposit location for the LPN that was required to fulfill the order and deliver the LPN to that location.

## Example: Starter pallet for a work assignment

The following process illustrates a threshold pick that serves as a starter pallet for a list pick. For more information, see [Starter pallets](work-assignments.md).

When picking for a work assignment, a starter pallet can provide a solid base on which subsequent picks for the assignment can be placed. The starter pallet can be a threshold pick, or the two features (starter pallet and threshold pick) can be implemented separately.

For this example, the starter pallet is a threshold pick. When the operator signs on to directed work, the operator is directed to a pallet storage location to pick a pallet, to remove unneeded cases from the pallet, and then to use the rest of the pick as a base platform on which to deposit other picks.

To perform the threshold pick, the RF operator performs the following actions:

1.  Sign on to directed work.
2.  When presented with a product pickup screen, enter the work assignment ID.
3.  Go to the location of the first pick (a starter pallet pick), and then on the threshold pick screen, enter the LPN number.
4.  If the inventory falls outside of the threshold pick variance, type **Y** to pick it up anyway.
5.  Enter the total quantity on the pallet that is being picked.
6.  On the threshold split screen, enter a new LPN number for the case that is being removed from the pallet.
7.  On the product deposit screen, view the deposit location for the partial pallet quantity, and deliver that 1 case to the location. Alternatively the operator can scan a P&D location and deposit the case there for someone else to move.
8.  When the product pickup screen is displayed, continue with the next pick in the assignment. The pick-to LPN the LPN of the starter pallet that was the first pick.
9.  When the warehouse equipment is full or the work assignment is complete, the operator deposits the LPN to destination location for the order.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
