---
title: "Procedures for receiving issues"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/procedures_for_receiving_issues.htm"
source: "/content/procedures_for_receiving_issues.htm"
toc_path:
  - "Warehouse Management"
  - "Receiving"
  - "Receiving Issues"
  - "Procedures for receiving issues"
sections:
  - "Manage unexpected items"
  - "Manage items without a valid storage location"
  - "Manage non-receivable items"
  - "View items deposited in an override location"
  - "Manage items received over the expected quantity"
  - "Manage items received under the expected quantity"
  - "Manage damaged items"
  - "View and resolve distribution exceptions"
  - "View or modify an inbound quality issue"
  - "Add an inbound quality issue using the Receiving Issues page"
  - "Delete an inbound quality issue"
  - "Receiving issues field listings"
  - "Unexpected Items fields"
  - "No Location fields"
  - "Search Results fields"
  - "Storage Rules Used fields"
  - "No Location Inventory Attributes fields"
  - "LPNs Affected fields"
  - "Not Receivable fields"
  - "Location Overrides fields"
  - "Overage fields"
  - "Shortages fields"
  - "Damaged fields"
  - "Distribution Exceptions fields"
  - "Inbound Quality Issue fields"
images:
  - "/content/resources/images/image429922_16x16.png"
  - "/content/resources/images/image430276_16x16.png"
source_sha1: 61c5eabad15f76d1c4ad7ccf1713befb8cd1b88f
---
# Procedures for receiving issues

The following procedures can be performed on the issues identified on the Receiving Issues page.

## Manage unexpected items

For a description of the issue, see [Receiving issues: Not expected](../receiving-issues.md).

1.  Select **Receiving > Receiving Issues > Not Expected**.
2.  View the information in the [Unexpected Items fields](#Unexpected_Items_fields).
3.  To view additional item information:
    1.  In the grid, click an item. The item details page is displayed.
    2.  Click **Footprints**. The footprints configured for the item are displayed.
        
        **Note**: Click ![Expand](../../../../images/resources/images/image429922_16x16.png) or ![Collapse](../../../../images/resources/images/image430276_16x16.png) to show or hide the footprint details.
        
4.  To maintain an item configuration:
    1.  While viewing additional item information, select **Item**, and then click **Maintain item**.
    2.  See [Add or modify an item](../../configuration/inventory/items/items.md).

## Manage items without a valid storage location

For a description of the issue, see [Receiving issues: No location](../receiving-issues.md).

1.  Perform one of the following tasks:
    -   Select **Receiving > Receiving Issues > No Location**.
    -   Select **Inventory > Inventory Issues > No Location**.
2.  View information in the [No Location fields](#No_Location_fields).
3.  To initiate putaway for an item:
    1.  In the No Location grid, click the item. The item details are displayed.
    2.  In the LPNs Affected grid, select the check box next to the inventory for which to search for a storage location.
    3.  Click **Storage Location Search**. The search results are displayed. If successful, the Location Search Results window is displayed and shows the location that was found. Directed work is created to move the inventory if there is a defined movement path for the inventory from its current location to the storage location that was found.
4.  To view search results and the storage rules that were used for an LPN:
    1.  In the No Location grid, click an item, and then in the LPNs Affected grid, click an LPN.
    2.  View information in the [Search Results fields](#Search_Results_fields).
    3.  To view the storage zone rules that were applied to find a storage location for the inventory, select **Storage Rules Used**, and view information in the [Storage Rules Used fields](#Storage_Rules_Used_fields).
    4.  To view additional inventory details, select **Inventory Attributes**, and view information in the [No Location Inventory Attributes fields](#No_Location_Inventory_Attributes_fields).
5.  To view additional item details or to perform actions on an item or LPN:
    1.  In the No Location grid, click an item, and view information in the [LPNs Affected fields](#LPNs_Affected_fields).
    2.  Select **Item**, and view the item information. See [View detailed item information](../../shared-functions/inventory/procedures-for-items.md).
    3.  To perform actions on an item, select **Summary**, and perform one or more of the following tasks:
        -   To maintain the item, see [Maintain an item](../../shared-functions/inventory/procedures-for-items.md).
        -   To apply a hold to the item, see [Apply a hold to inventory](../../inventory/holds/procedures-for-holds.md).
        -   To release a hold from the item, see [Release a hold from inventory](../../inventory/holds/procedures-for-holds.md).
        -   To generate a cycle count for the item, from the **Actions** drop-down list, select **Generate Cycle Count**, and then click **OK**.
        -   To generate a replenishment for the item, from the **Actions** drop-down list, select **Generate Replenishment**, and then click **OK**.
    4.  To perform actions on an LPNS, select **LPNs**, and then see [Procedures for LPNs](../../shared-functions/inventory/procedures-for-lpns.md).

## Manage non-receivable items

For a description of the issue, see [Receiving issues: Not receivable](../receiving-issues.md).

1.  Select **Receiving > Receiving Issues > ** **Not Receivable**.
2.  View information in the [Not Receivable fields](#Not_Receivable_fields).
3.  In the grid, click an item. The item details are displayed.
4.  To view and manage item information:
    1.  Select **Item**. View the item information.
    2.  To modify the item:
        1.  Click **Maintain Item**.
        2.  See [Add or modify an item](../../configuration/inventory/items/items.md).
            
            **Note**: To define an item as receivable, set the **Receivable** field (processing attribute) to Yes.
            
5.  To view item footprint information, select **Footprint**, and view the information.

## View items deposited in an override location

For a description of the issue, see [Receiving issues: Location overrides](../receiving-issues.md).

1.  Select **Receiving > Receiving Issues > Location Overrides**.
2.  View information in the [Location Overrides fields](#Location_Overrides_fields).
3.  In the grid, click an item. The display shows a visual representation of the used capacity in the location, the location attributes, and the contents for both the user-selected location and the application-directed location.
4.  To view recent transactions associated with a location, click **Recent Transactions**.

## Manage items received over the expected quantity

For a description of the issue, see [Receiving issues: Overage](../receiving-issues.md " ").

1.  Select **Receiving > Receiving Issues > ** **Overage**.
2.  View information in the [Overage fields](#Overage_fields).
3.  In the grid, click an item. The item details are displayed.
4.  To view and manage item information:
    1.  Select **Item**. View the item information.
    2.  To modify the item:
        1.  Click **Maintain Item**.
        2.  See [Add or modify an item](../../configuration/inventory/items/items.md).
5.  To view item footprint information, select **Footprint**, and view the information.

## Manage items received under the expected quantity

For a description of the issue, see [Receiving issues: Shortages](../receiving-issues.md).

1.  Select **Receiving > Receiving Issues > Shortages**.
2.  View information in the [Shortages fields](#Shortages_fields).
3.  In the grid, click an item. The item details are displayed.
4.  To view and manage item information:
    1.  Select **Item**. View the item information.
    2.  To modify the item:
        1.  Click **Maintain Item**.
        2.  See [Add or modify an item](../../configuration/inventory/items/items.md).
5.  To view item footprint information, select **Footprint**, and view the information.

## Manage damaged items

For a description of the issue, see [Receiving issues: Damaged](../receiving-issues.md).

1.  Select **Receiving > Receiving Issues > Damaged**.
2.  View information in the [Damaged fields](#Damaged_fields).
3.  In the grid, click an item. The item details are displayed.
4.  To view and manage item information:
    1.  Select **Item**. View the item information.
    2.  To modify the item:
        1.  Click **Maintain Item**.
        2.  See [Add or modify an item](../../configuration/inventory/items/items.md).
5.  To view item footprint information, select **Footprint**, and view the information.

## View and resolve distribution exceptions

For a description of the issue, see [Receiving issues: Distribution exceptions](../receiving-issues.md).

1.  Select **Receiving > Receiving Issues > Distribution Exceptions**.
2.  To view exceptions that you have previously resolved and cleared with the current, unresolved distribution exceptions, select the **Include Resolved** check box; otherwise, clear it to view only unresolved exceptions.
3.  View information in the [Distribution Exceptions fields](#Distribution_Exceptions_fields).
4.  To resolve an exception, in the grid, select the check box next to the LPN, and then click **Resolve Exception**.
    
    **Note**: Resolving a distribution exception does not affect the inventory in any logical way and has no processing effect on the inventory. Resolving exceptions on this window indicates that you resolved the unexpected inventory in the warehouse and want to remove the exception from the display.
    

## View or modify an inbound quality issue

For a description of the issue, see [Receiving issues: Inbound quality](../receiving-issues.md).

1.  Select **Receiving > Receiving Issues > Inbound Quality Issues**, and then enter search criteria, if necessary.
2.  To modify an issue:
    1.  In the grid, click the issue.
    2.  Enter information in the [Inbound Quality Issue fields](#Inbound_Quality_Issue_fields).
    3.  Click **Save**.

## Add an inbound quality issue using the Receiving Issues page

You can add an inbound quality issue using the Receiving Issues page. Alternatively, see [Report an inbound quality issue using the Inbound Shipments page](../inbound-shipments/procedures-for-inbound-shipments.md).

1.  Select **Receiving > Receiving Issues > Inbound Quality Issues**.
2.  Click **Add**.
3.  Enter information in the [Inbound Quality Issue fields](#Inbound_Quality_Issue_fields).
4.  Click **Save**.

## Delete an inbound quality issue

You typically delete an inbound quality issue once the issue has been resolved.

1.  Select **Receiving > Receiving Issues > Inbound Quality Issues**.
2.  To narrow the issues that are displayed, enter search criteria, such as a date, a carrier or supplier, or an inbound order.
3.  In the grid, select the check box next to the issue.
4.  Click **Delete**. A confirmation message is displayed.
5.  Click **OK**.

## Receiving issues field listings

### Unexpected Items fields

 
| Field | Description |
| --- | --- |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Date | Date and time the last action was performed on the order or order line. |
| Quantity | Quantity of the item received into the warehouse. |
| Supplier | Identifier for a supplier. A supplier can be an individual, organization, or another warehouse within your own organization from which you repeatedly receive inventory or handling units. |
| Inbound Order | Identifier for an inbound order or planned inbound order that is associated with a specific supplier. |
| Location | Unique identifier for the location where the item currently resides. |
| User | User who performed the transaction activity. |

### No Location fields

 
| Field | Description |
| --- | --- |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Received | Quantity of inventory received for the item that does not have any location. |
| Item Footprint | Name that identifies a footprint, which describes the packaging dimensions and units of measure for the item with which it is associated. |
| Item Family | Identifier used to group similar items together. Typically, all of the items within a family have the same material handling characteristics. |
| Supplier | Identifier for a supplier. A supplier can be an individual, organization, or another warehouse within your own organization from which you repeatedly receive inventory or handling units. |
| Inbound Order | Identifier for an inbound order or planned inbound order that is associated with a specific supplier. |
| Location | Location in which the inventory currently resides. |
| Status | Quality status of an item. Defines the quality or disposition of the item. |

### Search Results fields

 
| Field | Description |
| --- | --- |
| Building | Building in which the application searched for a valid storage location for the LPN. A building is a warehouse entity consisting of one or more areas. Inventory and location information can be reported by building. |
| Location | Location that was considered, but not selected, by the application for storage of the LPN based on the storage rules that were used. |
| Reason | Reason why a location could not be used to store the LPN. For example, if the height of the LPN is greater than the location's, the value for this field is Height. |
| Comparison | Further explanation of the reason why the location was not selected in relation to the LPN. For example, if the **Reason** is Height, the **Comparison** value could be Pallet Height, indicating the pallet is too large for the storage location. |
| Location Attribute | Attribute of the location that relates to the reason why the application could not store the LPN in the location. This value can be evaluated in conjunction with the values for **Reason**, **Comparison**, and **LPN Attribute**. For example, assume the reason and comparison is Height and Pallet Height, respectively. If the location attribute is 300 and the LPN attribute is 400, that indicates the maximum height for the location is 300 inches, and the actual height of the LPN is 400 inches, and therefore the location could not be used. |
| LPN Attribute | Attribute of the LPN that relates to the reason why the application could not store the LPN in the location. This value can be evaluated in conjunction with the values for **Reason**, **Comparison**, and **Location Attribute**. For example, assume the reason and comparison is Height and Pallet Height, respectively. If the location attribute is 300 and the LPN attribute is 400, that indicates the maximum height for the location is 300 inches, and the actual height of the LPN is 400 inches, and therefore the location could not be used. |

### Storage Rules Used fields

 
| Field | Description |
| --- | --- |
| Sequence | Number that determines the sequence in which the application evaluates the storage zone rule in relation to other storage zone rules assigned to the search path. When evaluating the rules for location selection, the application begins by evaluating the rule with the lowest priority (1), and then moves to the next storage zone rule in sequential order. |
| Warehouse | Unique identifier for the site in which the building for the storage zone rule is located. |
| Building | Building in which the storage zone is located. A building is a warehouse entity consisting of one or more zones. Inventory and location information can be reported by building. |
| Storage Zone | Storage zone for which the storage zone rule is configured and in which the application attempted to find a storage location for the LPN. A storage zone represents a group of locations that have the same attributes (consolidation, item mixing, date control, and others) for storing inventory. |
| Strategy | Storage strategy for the search path that was evaluated by the application in an attempt to find a storage location.<br>-   • **PARTIALS-KEEP-ZONE**: The application searches for a storage location that is partially full and with the same velocity zone as the inventory being stored.
<br>-   • **PARTIALS-BREAK-ZONE**: The application searches for a storage location that is partially full and does not necessarily have the same velocity zone as the inventory being stored.
<br>-   • **EMPTIES-KEEP-ZONE**: The application searches for a storage location that is empty and with the same velocity zone as the inventory being stored.
<br>-   • **EMPTIES-BREAK-ZONE**: The application searches for a storage location that is empty and with the same velocity zone as the inventory being stored.
<br>-   • **MIXED**: The application searches for a partially filled storage location that already contains mixed inventory. The location does not necessarily contain inventory that matches the inventory being stored. |
| Storage Suffix | Suffix for the LPN attribute that is required for the application to store the LPN in the zone to which the storage rule applies.<br>-   • **FUL**: Only full LPNs of inventory, as specified in the storage settings configuration, can be stored in the zone.
<br>-   • **HVY**: Only LPNs considered to be heavy, as specified in the storage settings configuration, can be stored in the zone.
<br>-   • **HLF**: Only half LPNs of inventory, as specified in the storage settings configuration, can be stored in the zone.
<br>-   • **MIX**: Only mixed-item LPNs can be stored in the zone.
<br>-   • **PCS**: Only LPNs assigned the Pieces attribute, as specified in the storage setting configuration, can be stored in the zone. |
| Inventory Status | Status that inventory must have in order to be stored in the zone as required by the storage zone rule. An inventory status defines the quality or disposition of the inventory. |
| Movement Zone | Name of a movement zone. A movement zone represents a group of locations to and from which inventory can be moved. For example, storage locations to which inventory can be deposited and processing locations to which inventory is moved for packing are the types of locations that must be assigned to a movement zone for the application to select those locations for putaway or deposit.<br > Source, hop, and destination locations must be assigned to a movement zone so that a movement path can be defined to use each of those locations. |

### No Location Inventory Attributes fields

 
| Field | Description |
| --- | --- |
| Item Description | Text that describes an item. An item is any specific piece of inventory that is stored or processed within the application. |
| LPN | Unique identifier for inventory. Typically, an LPN refers to a pallet; however, it can refer to inventory received at less than pallet quantity. The LPN is the license plate by which the inventory is tracked in the facility. |
| LPN Quantity | Quantity of the item on the LPN. |
| Status | Quality status of an item. Defines the quality or disposition of the item. |
| Lot Number | Identifier assigned to a quantity of inventory that is uniquely identified during the manufacturing process for the purpose of tracking an attribute of that inventory, such as its expiration date. Lots differentiate distinct groups of inventory that have the same item. Lots are user defined and are not necessarily unique since the same lot can be applied to different items. However, lot and item number combinations must be unique. |
| Origin Code | Identifier assigned to an item to identify the item's country of origin. It is typically used for export paperwork. Origin codes are user defined. |
| Revision Level | Identifier that is assigned to an item number to differentiate revisions of the same item number. |
| Supplier | Identifier for a supplier. A supplier can be an individual, organization, or another warehouse within your own organization from which you repeatedly receive inventory or handling units. |
| Exp Date | Date and time that the inventory will expire. This field defaults to the date calculated by the application based on the manufactured date and aging profile name of the item. |
| FIFO Date | Date used by the application for processing inventory when the first in, first out (FIFO) inventory rotation method is used. FIFO ensures that the oldest inventory is selected first. |
| Mfr Date | Date on which the inventory identified on this LPN was manufactured. This date is the basis for date calculations (such as for aging and shelf life) that the application performs for date-tracked items. For example, this date can be used for first in, first out (FIFO) order processing. |

### LPNs Affected fields

 
| Field | Description |
| --- | --- |
| LPN | Unique identifier for inventory. Typically, an LPN refers to a pallet; however, it can refer to inventory received at less than pallet quantity. The LPN is the license plate by which the inventory is tracked in the facility. |
| LPN Quantity | Quantity of the item on the LPN. |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Description | Text that further describes the item. |
| Location | Unique name for a location within the facility that is used to receive, store, process, or ship inventory. |
| Inbound Order | Identifier for an inbound order or planned inbound order that is associated with a specific supplier. |
| Inbound Order Line | Unique identifier for an inbound order line. The order line is the section of an order that provides detailed information about an individual item that the order requests. |
| Storage Rules Used | Number of storage zone rules that the application processed in attempting to locate a storage location for the inventory. Storage zone rules (associated with a search path) specify the zone to which matching inventory can be directed, criteria for finding an optimal location, and capacity restrictions for the zone. |
| Suggested Reason | Reason why the application was unable to find a suitable storage location for the inventory based on the storage rules. |

### Not Receivable fields

 
| Field | Description |
| --- | --- |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Date | Date and time that the user attempted to receive the item. |
| Expected | Quantity of the item expected to be received into the warehouse. |
| Footprint | Name that identifies a footprint, which describes the packaging dimensions and units of measure for the item with which it is associated. |
| Item Family | Identifier used to group similar items together. Typically, all of the items within a family have the same material handling characteristics. |
| Inbound Order | Identifier for an inbound order or planned inbound order that is associated with a specific supplier. |
| Inbound Order Line | Unique identifier for an inbound order line. The order line is the section of an order that provides detailed information about an individual item that the order requests. |
| User | User ID of the person who attempted to receive the item. |

### Location Overrides fields

 
| Field | Description |
| --- | --- |
| Item | Unique code that is used to identify inventory. The item description and, for a 3PL environment, the item client ID are also displayed. |
| Date | Date and time at which the operator chose to override the application-directed deposit location and deposited the inventory to a user-selected location. |
| LPN | Unique identifier for inventory. Typically, an LPN refers to a pallet; however, it can refer to inventory received at less than pallet quantity. The LPN is the license plate by which the inventory is tracked in the facility. |
| Quantity | Quantity of inventory on the LPN. |
| User Location | Location to which the user deposited the inventory after overriding the application-directed location. |
| System Location | Location that the application selected for the inventory deposit. |
| User | User who deposited the item. |
| RF User Reason | Code that identifies why the user chose to deposit the LPN in a location other than the application-directed location. |
| Cycle Count | A check mark indicates that a cycle count was generated in the application-selected location. This occurs if the selected reason is configured to generate a cycle count. |

### Overage fields

 
| Field | Description |
| --- | --- |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Date | Date and time the last action was performed on the order or order line. |
| Overage | Quantity and percentage of items received over the expected quantity. For example, if the overage quantity is (80 of 200), you received a total of 280 eaches or 80 eaches over your expected quantity of 200. |
| Expected Qty | Quantity of the item expected to be received into the warehouse. |
| Received Qty | Quantity of the item received into the warehouse. |
| Supplier | Identifier for a supplier. A supplier can be an individual, organization, or another warehouse within your own organization from which you repeatedly receive inventory or handling units. |
| Inbound Order | Identifier for an inbound order or planned inbound order that is associated with a specific supplier. |
| Location | Unique identifier for the location where the item currently resides. |
| User | User who performed the transaction activity. |

### Shortages fields

 
| Field | Description |
| --- | --- |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Date | Date and time the last action was performed on the order or order line. |
| Short Quantity | Quantity of inventory received under the expected quantity. For example, if the short quantity is (10 of 190) or "10 ea", you received a total of 180 eaches, or 10 eaches under your expected quantity of 190. |
| Supplier | Identifier for a supplier. A supplier can be an individual, organization, or another warehouse within your own organization from which you repeatedly receive inventory or handling units. |
| Inbound Order | Identifier for an inbound order or planned inbound order that is associated with a specific supplier. |
| Location | Unique identifier for the location where the item currently resides. |
| Closed Inbound Shipment | Identifier for the inbound shipment associated with the inventory that was received short. |

### Damaged fields

 
| Field | Description |
| --- | --- |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Date | Date and time at which the planned inbound order line was last modified (for example, when inventory was received against the line). |
| Damaged | Quantity and percentage of damaged items out of the expected quantity on the planned inbound order line. For example, if the damaged quantity is 15% (15 of 100), you received or expected a total of 100 eaches and 15 of those eaches are damaged. |
| Carrier | Identifier for a carrier that delivers inbound inventory to the warehouse or outbound shipments to a customer. This is the identifier that will be displayed to users on the application windows and reports. In the application, a carrier can be associated with a customer, order, inbound shipment, outbound shipment, load, and service levels (such as Ground, Next Day, and Saturday Delivery). |
| Supplier | Identifier for a supplier. A supplier can be an individual, organization, or another warehouse within your own organization from which you repeatedly receive inventory or handling units. |
| Planned Inbound Order | Identifier for a planned inbound order that is associated with a specific supplier. A planned inbound order is an authorization to receive specific inventory and quantities from a supplier. It is used, but not required, to receive inventory into the warehouse. |
| Load Status | Processing status of the order. |
| User | User ID, first name, and last name of the person who set the inventory to damaged status. |
| Location | Unique identifier for the location where the item currently resides. |
| Status | Quality status of an item. Defines the quality or disposition of the item. |

### Distribution Exceptions fields

 
| Field | Description |
| --- | --- |
| LPN | Unique identifier for the inventory associated with the distribution exception, such as the identifier of missing or excess inventory as a result of a distribution audit. Typically, an LPN refers to a pallet; however, it can refer to inventory received at less than pallet quantity. The LPN is the license plate by which the inventory is tracked in the facility. |
| Item | Unique code that is used to identify inventory. The item description and, for a 3PL environment, the item client ID are also displayed. |
| Exception | Value that describes the reason for the exception. Exceptions occur when there is a discrepancy in the amount of actual residual inventory and the expected residual quantity at the end of the deposit process and the distribution audit fails.<br>-   • **Extra Inventory Remaining**: There is inventory remaining after the distribution assignment is completed.
<br>-   • **Insufficient Inventory Remaining**: The quantity of inventory remaining does not match what the application expects to be remaining.
<br>-   • **Expected Inventory, None Remaining**: The application expects there to be additional inventory and there is none remaining.
<br>-   • **No Expected Inventory, Inventory Remaining**: The application does not expect any additional inventory and there is some remaining. |
| Exception Date | Date and time at which the distribution exception occurred. Exceptions occur when there is a discrepancy in the amount of actual residual inventory and the expected residual quantity at the end of the deposit process and the distribution audit fails. |
| Location | Unique identifier for the location in which the exception inventory is currently stored. |
| Expected Quantity | Quantity of residual inventory that was expected by the application for the distribution audit. |
| Reported Quantity | Quantity of residual inventory that was entered by an operator during the distribution audit. This quantity does not match the application's expected quantity, which caused the distribution exception to occur. |
| Resolved | Indicates that the exception was resolved and cleared from the exceptions display (unless the **Include Resolved** check box is selected). You can manually resolve exceptions in the application after the exception was corrected in the facility, such as through an inventory adjustment or re-receiving excess inventory against the original inbound order line. |

### Inbound Quality Issue fields

 
| Field | Description |
| --- | --- |
| Supplier Issue | Identifier for the type of quality issue that exists for the selected supplier. The issues that are available for selection are defined in inbound configuration. |
| Supplier Quantity | Number of items affected, such as the unit quantity of the item associated with the supplier quality issue. |
| Carrier Issue | Identifier for the type of quality issue that exists for the selected carrier. The issues that are available for selection are defined in inbound configuration. |
| Carrier Quantity | Number of items affected, such as the unit quantity of the item associated with the carrier quality issue. |
| Carrier | Identifier for a carrier that delivers inbound inventory to the warehouse or outbound shipments to a customer. This is the identifier that will be displayed to users on the application windows and reports. In the application, a carrier can be associated with a customer, order, inbound shipment, outbound shipment, load, and service levels (such as Ground, Next Day, and Saturday Delivery). |
| Transport Equipment | Alphanumeric identifier for transport equipment. Transport equipment numbers are not unique, can exist multiple times, and can be associated with various carriers. |
| Supplier | Identifier for a supplier. A supplier can be an individual, organization, or another warehouse within your own organization from which you repeatedly receive inventory or handling units. |
| Inbound Shipment | Unique identifier used for inventory tracking for an inbound shipment of inventory. An inbound shipment is a group of orders that are transported to the warehouse together or received together. When inventory arrives at the warehouse on a piece of transport equipment, an inbound shipment represents the contents of the transport equipment; however, one or more inbound shipments can be associated with a piece of transport equipment. |
| Planned Inbound Order | Identifier for a planned inbound order that is associated with a specific supplier. A planned inbound order is an authorization to receive specific inventory and quantities from a supplier. It is used, but not required, to receive inventory into the warehouse. |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| LPN | Unique identifier for inventory. Typically, an LPN refers to a pallet; however, it can refer to inventory received at less than pallet quantity. The LPN is the license plate by which the inventory is tracked in the facility. |
| Client | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. |
| Report by User | User who reported the quality issue. |
| Last Updated | Date and time at which the quality issue was last updated. |
| Last Updated User | User who most recently updated the quality issue. |
| Issue ID | Unique, application-assigned identifier for the inbound quality issue. |
| Note | Additional information related to the quality issue. You use this field, for example, to provide additional details about the reason for reporting the quality issue. This field is for informational purposes only; it is not used by any process. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2023 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
