---
title: "Pick Verification"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/pick_verification.htm"
source: "/content/pick_verification.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Outbound"
  - "Picking "
  - "Pick Verification"
sections:
  - "Pick verification defaults"
  - "Deduction sequencing"
  - "Configure pick verification"
  - "Override fields"
  - "Deduction Sequence fields"
images: []
source_sha1: f106f022511fe19f2cb05d65a410ab431926226a
---
# Pick Verification

Pick verification is the process by which the application prompts the operator, during picking, to confirm the attributes of picked inventory. The application requires certain attributes to be verified by default. See [Pick verification defaults](#Pick_verification_defaults).

However, you can define overrides to the pick verification defaults by LPN level and work type for the following entities:

-   **Pick zones**: The overrides apply to picks performed in the selected pick zone.
-   **Order types**: The overrides apply to picks for the selected order type.
-   **User roles**: The overrides apply to picks performed by a user assigned to the selected role.

When a pick is performed, the application first considers the pick zone configuration; then, if an order type or role configuration applies, the application combines the configurations to determine if verification is needed. If an attribute is set to Always in any of the configurations that apply, it takes priority and verification for that attribute is required. If Always is not selected, the option to Never verify an attribute overrides the pick verification defaults.

If pick verification is not configured for an order type, zone, or role, then when an operator completes a pick, the application updates the inventory in the location based on the default or configured deduction sequence and not necessarily on the inventory that was physically picked. See [Deduction sequencing](#Deduction_sequencing).

**Note**: Pick verification configurations also apply to voice picking. However, you can configure whether the application uses full verification or only the pick zone verification configuration. See [Configure voice picking](voice-picking.md).

## Pick verification defaults

By default, the application requires an operator to confirm the following inventory attributes when performing a pick:

-   LPN, for full LPN picks
-   Quantity, for sub-LPN and detail picks
-   Item, for sub-LPN and detail picks
-   Lot, for lot-tracked items
-   Origin, for items tracked by origin
-   Revision level, for items tracked by revision level
-   Catch quantity, when picking a full LPN of an item configured for Catch on Receiving or Catch on Shipping
-   Catch quantity, when picking a partial LPN of an item configured for Catch on Shipping
-   User-defined inventory attribute, for items tracked by the user-defined inventory attribute
-   Rotation, for bonded inventory tracked by a rotation identifier. Only available if Customs is enabled for the warehouse.

If the pick verification flag for an application-required (default) attribute is set to Never and an operator picks inventory from a location that has mixed attribute values, the application selects the first value in alphanumeric order to decrement inventory. For example, if pick verification is not enabled for lot and you have Lot 100, Lot 200, and Lot 300 of Item A in a location, then if the operator is directed to pick Item A, the operator is not prompted to verify which lot was selected. The application would decrement the inventory details for Lot 100, then Lot 200, and Lot 300 as inventory is depleted (even though the operator may have actually picked from Lot 300 at the location).

## Deduction sequencing

A deduction sequence is used to identify the order in which inventory is deducted from a location as the result of a pick (order or replenishment) that does not require pick verification. If pick verification is not configured for an order type, zone, or role, then when an operator completes a pick, the application updates the inventory in the location based on the deduction sequence and not necessarily on the inventory that was physically picked.

The deduction sequence for an order type overrides the sequence for a zone, which overrides the sequence for a role. If a user is assigned to multiple roles with conflicting deduction sequences, then the application sorts the roles alphanumerically and uses the deduction sequence of the first role. If a pick is associated with multiple order types, then the application sorts the order types alphanumerically and uses the sequence of the first order type.

**IMPORTANT**: Pick deduction sequencing should not be used in conjunction with the following areas of functionality: catch quantity capture, inventory serialization, inventory rotation allocation, allocation profiles, and allocation rules (defined in Allocation Rule Maintenance). If your warehouse uses any of this functionality, it is highly recommended that you enable and configure pick verification to avoid unexpected processing behavior.

For example, assume that pick verification is not required for an order type, pick zone, or role. Also assume that a location contains ITEM1 from Lot 1 and Lot 2, and that the deduction sequence for the order type is prioritized by lot with an ascending sort order. When an operator completes a pick for ITEM1 from the location, the application removes the item quantity from Lot 1 first, followed by Lot 2. However, without pick verification, the inventory that is physically picked may differ from the inventory that is deducted in the application. This means that while the application deducted a quantity of ITEM1 Lot 1, the operator could have picked ITEM 1 Lot 2 with no validation.

**IMPORTANT**: Using a deduction sequence configuration in place of pick verification may result in inventory inaccuracies that can span counting, outbound transactions, recalls, reports, and labels. Additional efforts may be required to rectify inaccuracies, such as an increase in inventory adjustments. It is recommended to use pick verification; only use deduction sequencing when all of the risks have been assessed.

If pick verification is not required and there is no deduction sequence configuration, then the application deducts inventory from the pick location using the following default sequence (in ascending order):

1.  Item Client
2.  Revision Level
3.  Supplier
4.  Lot Number
5.  Supplier Lot Number
6.  Origin Code
7.  Inventory Status
8.  Units Per Case
9.  Units Per Pack
10.  Shipment Line ID
11.  Physical Piece
12.  Distribution ID
13.  Manufactured Date
14.  Expiration Date
15.  Return ID
16.  Under Bond

For example, using the default sequence, if all inventory in the location has the same item client, revision level, and supplier, but different lot numbers, then picked inventory quantities are deducted by lot number in ascending order of the lot numbers in the location.

## Configure pick verification

1.  Select **Configuration > Outbound > Picking > Pick Verification**.
2.  Enter information in the following fields:
    
     
    | Field | Description |
    | --- | --- |
    | Confirmation for Threshold Pick | If Yes, the operator is directed to confirm the quantity that was actually picked for a threshold pick. A threshold pick is an overpick performed by picking a higher UOM (such as a pallet) instead of multiple lower UOMs (such as cases) when the quantity required is slightly less than the higher UOM. (The threshold percentage that defines when a threshold pick can be performed is specified on the item footprint UOM.) For example, when an order line requires slightly less than a full pallet, the operator is directed to pick a full pallet rather than multiple cases; the quantity not needed for the order line is removed from the full pallet to be returned to storage.<br > If No, the operator is not prompted to confirm actual picked quantities for a threshold pick.<br > **Note**: It is recommended that the **Confirmation for Threshold Pick** field be set to Yes so that the application is notified that a quantity different from the required quantity was picked. |
    | Display Inventory Attributes | If Yes, then the application displays to the operator the item attributes (such as lot, revision level, and origin) in the location, if they are known and if the inventory is tracked by these attributes. When this field is set to Yes, the application populates attribute values that must be verified so the operator does not have to enter the information. The following pick verification configurations can affect whether and how attributes are displayed:<br>-   • If pick verification for the attribute is required (either by default or when the pick verification override is set to Always), then the item attribute value is displayed prior to verifying the pick. If the pick location contains inventory with multiple values for an attribute, the application displays "Many" as the field value. The operator then verifies the specific attribute value of the picked inventory in a second field for the attribute, separate from the display field that is populated with the value (Many).
    <br>-   • If pick verification for the attribute is not required, then the item attribute field is displayed without a value.
    <br > If No, then if the item is tracked by certain attributes and pick verification is required, the operator must enter the attribute values in the pick fields. If verification is not required, then the item attribute fields are not displayed. |
    | Destination LPN | If Yes, the operator can enter the pick information and the destination LPN or location on a single RF screen. Selecting Yes may increase the speed at which the task is performed but may also increase the risk of an inaccurate entry for the destination because the operator must enter it during pickup.<br > If No, the operator is prompted for the destination LPN or location on a second RF screen. Selecting No may reduce the speed at which the task is performed but may also increase the accuracy of the destination entry because the operator receives a separate prompt after completing the pickup. |
    
3.  To configure a pick verification override:
    1.  Perform one of the following tasks:
        -   To configure overrides by pick zone, click **RF Pick Validation by Zone**.
        -   To configure overrides by outbound order type, click **RF Pick Validation by Order Type**.
        -   To configure overrides by user role, click **RF Pick Validation by Role**.
    2.  Perform one of the following tasks:
        -   To add an override, click **Add.**
        -   To modify an override, in the grid, click the pick zone, order type, or role.
        -   To copy an override, in the grid, select the check box next to the pick zone, order type, or role, and then click **Copy**.
    3.  Enter information in the [Override fields](#Override_fields).
    4.  For each inventory attribute, perform one of the following tasks:
        -   To always prompt the operator to confirm the attribute if inventory is tracked by it, select **Always**.
        -   To never prompt the operator to confirm the attribute, even if inventory is tracked by it, select **Never**.
        -   To prompt the operator to confirm the attribute based on the default settings, select **Default**. For the default values, see [Pick verification defaults](#Pick_verification_defaults).
    5.  Click **Apply**.
4.  To configure a deduction sequence:
    
    **Note**: A deduction sequence is used to identify the order in which inventory is deducted from a location as the result of a pick that does not require pick verification. See [Deduction sequencing](#Deduction_sequencing).
    
    1.  Perform one of the following tasks:
        -   To configure deduction sequencing by pick zone, click **RF Pick Deduction Sequence by Zone**.
        -   To configure deduction sequencing by order type, click **Deduction Sequence by Order Type**.
        -   To configure deduction sequencing by role, click **Deduction Sequence by Role**.
    2.  Perform one of the following tasks:
        -   To add a sequence, click **Add**.
        -   To modify a sequence, in the grid, click the zone, order type, or role.
        -   To copy a sequence, in the grid, select the check box next to the pick zone, order type, or role, and then click **Copy**.
    3.  Enter information in the [Deduction Sequence fields](#Deduction_Sequence_fields).
    4.  In the **Available** column, select the check box next to each attribute by which inventory in the location is deducted for a pick. If available entities are not displayed, click **Show Available**.
    5.  To change the sequence in which an attribute is considered for deduction, in the **Selected** column, select a row and drag it to the preferred position.
    6.  To change the sort order of a selected attribute, from the **Sort Order** drop-down list, select **Ascending** or **Descending**.
    7.  Click **Apply**.
5.  Click **Save**.

## Override fields

 
| Field | Description |
| --- | --- |
| Pick Zone | Name of a pick zone. A pick zone represents a group of locations that share the same attributes for picking, such as the LPN level at which picks can be allocated, the cartonization group to which it belongs, and whether the location supports replacement picks and pre-inventory allocation. The search path searches pick zones when attempting to find inventory for allocation. |
| Role | Category used to group menu options for the purpose of maintaining user authorizations. Roles are assigned to the appropriate user accounts to control the tasks users are authorized to perform. |
| Order Type | Name of an order type. An order type is a category that is used to group orders based on the warehouse processing necessary to fulfill the order. For example, customer orders and distribution orders require different processing by the application, and so an order type can be assigned to categorize each order separately. The application uses order types, for example, to identify orders that are eligible for bulk picking, or to direct orders to specific destination locations. |
| Work Type | Type of pick work to which the verification override applies.<br>-   • **Bulk Pick**: Work type used to perform bulk picks.
<br>-   • **Demand Replenishment**: Replenishment work type generated when pre-inventory allocation is enabled and a pick location does not have inventory to complete an order. The application generates demand-based replenishments from reserve storage locations to the pick locations, and then generates picks based on the inventory pending to the pick locations.
<br>-   • **Emergency Replenishment**: Replenishment work type generated automatically when there is insufficient inventory in a pick zone to satisfy a shipment line.
<br>-   • **Kit**: Work type used to pick component items to fill a work order.
<br>-   • **Manual Replenishment**: Replenishment work type initiated by an operator for a specific location.
<br>-   • **Pick**: Work type used to pick inventory to fill an order.
<br>-   • **Replenishment**: Work type used to fill a pickface location with inventory from a storage location.
<br>-   • **Stage Transfer**: Pick work generated to transfer inventory typically from a cross docking location to a staging lane.
<br>-   • **Top-off Replenishment**: Replenishment work type generated automatically at timed intervals.
<br>-   • **Triggered Replenishment**: Replenishment work type generated automatically when an item in a zone or a location has dropped below a user-defined level. |
| LPN Level | Packaging level to which the override applies:<br>-   • **Detail LPN**: Applies to each (piece) picks.
<br>-   • **LPN**: Applies to pallet picks.
<br>-   • **Sub-LPN**: Applies to case picks. |

## Deduction Sequence fields

 
| Field | Description |
| --- | --- |
| Pick Zone | Name of a pick zone. A pick zone represents a group of locations that share the same attributes for picking, such as the LPN level at which picks can be allocated, the cartonization group to which it belongs, and whether the location supports replacement picks and pre-inventory allocation. The search path searches pick zones when attempting to find inventory for allocation. |
| Role | Category used to group menu options for the purpose of maintaining user authorizations. Roles are assigned to the appropriate user accounts to control the tasks users are authorized to perform. |
| Order Type | Name of an order type. An order type is a category that is used to group orders based on the warehouse processing necessary to fulfill the order. For example, customer orders and distribution orders require different processing by the application, and so an order type can be assigned to categorize each order separately. The application uses order types, for example, to identify orders that are eligible for bulk picking, or to direct orders to specific destination locations. |
| Work Type | Type of pick work to which the deduction sequence applies.<br>-   • **Bulk Pick**: Work type used to perform bulk picks.
<br>-   • **Demand Replenishment**: Replenishment work type generated when pre-inventory allocation is enabled and a pick location does not have inventory to complete an order. The application generates demand-based replenishments from reserve storage locations to the pick locations, and then generates picks based on the inventory pending to the pick locations.
<br>-   • **Emergency Replenishment**: Replenishment work type generated automatically when there is insufficient inventory in a pick zone to satisfy a shipment line.
<br>-   • **Kit**: Work type used to pick component items to fill a work order.
<br>-   • **Manual Replenishment**: Replenishment work type initiated by an operator for a specific location.
<br>-   • **Pick**: Work type used to pick inventory to fill an order.
<br>-   • **Replenishment**: Work type used to fill a pickface location with inventory from a storage location.
<br>-   • **Stage Transfer**: Pick work generated to transfer inventory typically from a cross docking location to a staging lane.
<br>-   • **Top Off Replenishment**: Replenishment work type generated automatically at timed intervals.
<br>-   • **Triggered Replenishment**: Replenishment work type generated automatically when an item in a zone or a location has dropped below a user-defined level. |
| LPN Level | Packaging level to which the deduction sequence applies:<br>-   • **Detail LPN:** Applies to each (piece) picks.
<br>-   • **LPN**: Applies to pallet picks.
<br>-   • **Sub-LPN**: Applies to case picks. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
