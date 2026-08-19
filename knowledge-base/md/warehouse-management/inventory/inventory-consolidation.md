---
title: "Inventory Consolidation"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/inventory_consolidation.htm"
source: "/content/inventory_consolidation.htm"
toc_path:
  - "Warehouse Management"
  - "Inventory"
  - "Inventory Consolidation"
sections:
  - "Consolidation examples"
  - "Add or modify an inventory consolidation rule"
  - "View consolidation candidates"
  - "Consolidate inventory"
  - "Inventory Consolidation Rules fields"
  - "Consolidation Candidates fields"
images: []
source_sha1: 4b827e1b73bb69928915b336cc62e6e5fe2016ec
---
# Inventory Consolidation

Inventory consolidation is the process of moving partial inventory quantities from a source movement zone to a destination movement zone, where the inventory is consolidated in a location. Consolidation can move partial quantities out of or within source zones to utilize space more efficiently. For example, one or more locations in the source zone may contain small quantities of the same item. You can search the source movement zone for consolidation opportunities, and then combine the quantities to a new location in the destination zone. Consolidation potentially creates empty locations in the source zone and utilizes available capacity in partially filled locations in the destination zone.

You use the following pages to configure and perform inventory consolidation: 

-   **Inventory Consolidation Rules**: Used to define criteria for the application to identify inventory consolidation opportunities in a source movement zone. A rule also specifies the destination movement zone in which the inventory must be consolidated. The source and destination movement zones defined for a rule can be different to consolidate inventory across zones, or you can define the same zone as both the source and destination to consolidate inventory within a single zone.
    
    An inventory consolidation rule also specifies the method by which the application searches for inventory to be consolidated, such as by the quantity of eaches or cases. For example, a consolidation rule may specify that any location within the source zone that contains 10 cases or less of an item is a candidate for consolidation in a location in the destination zone.
    
    **Note**: The application does not consider allocated quantities in a location when searching for consolidation candidates. For example, if a location contains a full pallet but half of the pallet quantity is allocated to be picked, then the application only considers the other non-allocated half pallet for consolidation.
    
-   **Consolidation Candidates**: Used to find consolidation candidates and to create directed work to move inventory. A consolidation candidate is a real-time opportunity to consolidate inventory based on the consolidation rule for a source movement zone. After you select the source zone, the application searches the zone for locations with inventory that satisfies the consolidation rule method value, and then you can create directed work inventory moves for the consolidation candidates.
    
    If the destination storage zone is configured to allow mixing (**Mixing Rules** field), then items from multiple locations in the source zone can be consolidated to a single location in the destination zone if no storage mixing restrictions are violated.
    
    The application may select consolidation candidates from one or more locations in the source zone. If locations in the source zone have inventory to be consolidated, the application attempts to find a location in the destination zone that already contains the item. If there is no destination location with the same inventory, then the application searches for an empty location. If there is no empty location but the zone allows mixing, then the application attempts to consolidate the inventory in a mixed location.
    
    **Note**: If a location in the source zone contains committed (allocated) inventory waiting to be picked, the remaining inventory in the location is not considered for consolidation. If a location in the destination zone contains allocated inventory not yet picked, then the location can be considered a destination for consolidation. However, the allocated quantity is included in capacity calculations until it is picked from the location.
    

## Consolidation examples

Assume the following information: 

-   **Item1 footprint**: 10 eaches in a case and 10 cases per pallet (100 eaches per pallet)
-   **Item2 footprint**: 5 eaches in a case and 10 cases per pallet (50 eaches per pallet)
-   **Consolidation rule method**: Pallet percentage value of 50%

The following scenarios explain how the system identifies consolidation candidates based on the previous assumptions:

-   If a location in the source zone contains one full pallet (100 eaches) and a partial pallet with 4 cases (40 eaches) of Item1, then the inventory would not be a consolidation candidate. This is because the total unit quantity in the location is 140, and according to the consolidation rule, the total unit quantity must be 50 eaches or less (50% of full pallet quantity for Item1).
-   If a location in the source zone contained mixed inventory of one full pallet of Item1 and 4 cases of Item2, then only the inventory for Item2 would be considered a consolidation candidate because 20 (4 x 5) is less than 25 (50% of full pallet quantity for Item2). Alternatively, if both Item1 and Item2 quantities are at or below 50% of a full pallet quantity, then the application attempts to consolidate each item to a separate partially filled location in the destination zone that already contains the item. If separate partially filled locations for the items do not exist and there are no empty locations available, then the items may be consolidated to the same location (when the destination zone allows mixing) if no mixing restrictions are violated.
-   If the source and destination zones are the same, and two locations in the zone contain 40 eaches and 45 eaches of Item1, respectively, then the inventory in both locations can be consolidated.

## Add or modify an inventory consolidation rule

1.  Select **Inventory > Inventory Consolidation > Inventory Consolidation Rules**.
2.  Perform one of the following tasks: 
    -   To add a rule, click **Add**.
    -   To modify a rule, in the grid, click the source movement zone.
3.  Enter information in the [Inventory Consolidation Rule fields](#Inventory_consolidation_rule_fields).
4.  Click **Save**.

## View consolidation candidates

1.  Select **Inventory > Inventory Consolidation > Consolidation Candidates**.
2.  From the source movement zone drop-down list, select the source zone in which to search for inventory consolidation candidates. The consolidation opportunities are displayed.
3.  View the information in the [Consolidation Candidates fields](#Consolidation_candidates_fields).

## Consolidate inventory

1.  Select **Inventory > Inventory Consolidation > Consolidation Candidates**.
2.  From the source movement zone drop-down list, select the source zone in which to search for inventory consolidation candidates. The consolidation opportunities are displayed.
3.  In the grid, select the row for the consolidation move for which to create directed work.
    
4.  Click **Create Work**. A confirmation message is displayed.
5.  Click **OK**.

## Inventory Consolidation Rules fields

 
| Field | Description |
| --- | --- |
| Source Movement Zone | Movement zone from which the inventory to be consolidated must be sourced. The application searches for consolidation candidates in the source zone and attempts to find a location in the destination zone in which to consolidate the inventory. Consolidation potentially creates empty locations in the source zone and utilizes available capacity in partially filled locations in the destination zone. |
| Destination Movement Zone | Movement zone to which the inventory must be destined for consolidation. The application searches for consolidation candidates in the source zone and attempts to find a location in the destination zone in which to consolidate the inventory. Consolidation potentially creates empty locations in the source zone and utilizes available capacity in partially filled locations in the destination zone. |
| Consolidation Rule Method | Method by which the application finds inventory consolidation candidates in the source movement zone.<br>-   • **Each Quantity**: The application evaluates the each quantity of an item in a location. If the item quantity is equal to or less than the value defined for **Each Quantity**, then the inventory is a candidate for consolidation. For example, if the **Each Quantity** is 50, then locations in the source movement zone with an item quantity of 50 eaches or less are consolidation candidates.
<br>-   • **Case Quantity**: The application evaluates the case quantity of an item in a location. If the item quantity is equal to or less than the value defined for **Case Quantity**, then the inventory is a candidate for consolidation. For example, if the **Case Quantity** is 20, then locations in the source movement zone with an item quantity of 20 cases or less are consolidation candidates.
<br>-   • **Pallet Percentage**: The application evaluates a percentage of the unit quantity of a full pallet. If the quantity is equal to or less than the value for **Pallet Percentage**, then the inventory is a candidate for consolidation. For example, if the **Pallet Percentage** is 25% and a full pallet of ItemA is 200 eaches, then locations in the source movement zone with an ItemA quantity of 50 eaches or less are consolidation candidates (.25 x 200 = 50).
<br>-   • **Source Command**: The application runs the command in the **Source Command** field to identify inventory consolidation candidates. You can use this method to consolidate inventory from specific locations. |
| Case Quantity | Quantity of cases at or below which the inventory in a location is considered a consolidation candidate. Only available if the **Consolidation Rule Method** is Case Quantity. |
| Each Quantity | Quantity of eaches at or below which the inventory in a location is considered a consolidation candidate. Only available if the **Consolidation Rule Method** is Each Quantity. |
| Pallet Percentage | Percentage of a full pallet at or below which inventory in a location is considered a consolidation candidate. For example, if you enter 50, then when a location contains 50% or less of a full pallet item quantity, the inventory is a candidate for consolidation. Only available when the **Consolidation Rule Method** is Pallet Percentage. |
| Source Command | Command used by the application to identify the location and inventory to be considered as a consolidation candidate. Only available if the **Consolidation Rule Method** is Command. |

## Consolidation Candidates fields

 
| Field | Description |
| --- | --- |
| Source Location | Location in the source zone from which inventory is moved through directed work to the destination zone for consolidation. |
| Item Number | Unique identifier for the item to be consolidated. An item is any specific piece of inventory that is stored or processed within the application. |
| Source Quantity | Quantity of inventory in the source location that satisfies the inventory consolidation rule configured for the source zone. This is the quantity to be moved if directed work is created. |
| Pending Quantity | Quantity of inventory that is pending to the source location through an inventory move, case transfer, or replenishment. |
| Destination Location | Location in the destination zone to which inventory is moved (through replenishment work) for consolidation. |
| Source Movement Zone | Movement zone from which the inventory to be consolidated must be sourced. The application searches for consolidation candidates in the source zone and attempts to find a location in the destination zone in which to consolidate the inventory. Consolidation potentially creates empty locations in the source zone and utilizes available capacity in partially filled locations in the destination zone. |
| Destination Movement Zone | Movement zone to which the inventory must be destined for consolidation. The application searches for consolidation candidates in the source zone and attempts to find a location in the destination zone in which to consolidate the inventory. Consolidation potentially creates empty locations in the source zone and utilizes available capacity in partially filled locations in the destination zone. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
