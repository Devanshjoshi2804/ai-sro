---
title: "Inventory Settings"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/inventory_settings.htm"
source: "/content/inventory_settings.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inventory"
  - "Inventory Settings"
sections:
  - "Recovery of lost inventory"
  - "Configure inventory settings"
  - "Inventory Settings fields"
images: []
source_sha1: 97d82728a683d24fe36d9ec77be9d28b1681c125
---
# Inventory Settings

Inventory settings are used to specify the following attributes:

-   Whether the details of a hold are automatically displayed when inventory is scanned
-   Whether an operator is allowed to update lost or misplaced inventory to its current physical location
-   Whether the application displays an inventory summary screen when the operator performs an inventory query. The operator can access inventory details from the summary screen.
-   Whether the application requires an identifier (an item or location) when the operator performs an inventory query
-   The maximum number of rows displayed when the operator performs an inventory query
-   The minimum and maximum number of characters that the application accepts when an LPN is entered on a device or workstation during inbound identification and during picking
-   The catch quantity attributes when receiving or shipping LPNs or sub-LPNs, such as, extreme tolerance limits, allow cancellation of the catch quantity capture, and so on. The operator can be prompted to capture catch quantity, and the application verifies the normal and extreme tolerance limits in the following scenarios:
    -   Receiving:
        -   Receive and add inventory
        -   Adjust inventory
    -   Shipping:
        -   Picking
        -   Before loading
        -   Capture catch quantity at the LPN or sub-LPN level, if configured, during picking or before loading

## Recovery of lost inventory

Recovery of lost inventory can take place when the RF operator is performing a pick or count and selects inventory that the application shows as being in one of the following locations:

-   A lost location. This is the location to which inventory is moved when it is adjusted out of a location. If the **Recover from Lost Location** field is set to Yes, the operator can recover the inventory to its current physical location if it was adjusted out of a location during an audit count. However, inventory that was adjusted out of a location using a workstation or the RF Inventory Adjust screen cannot be recovered using this functionality.
-   A location different from where the inventory is physically located. This can occur when someone physically moves the inventory without changing its location in the application. If the **Recover from Storage Location** field is set to Yes, the operator can recover the inventory to its current physical location.

The recovery process prompts the operator to confirm the contents of the LPN with what the application expects. If the content matches, the operator can update the location of the inventory to its current physical location and then continue with the pick or the count.

Recovery is available for inventory that is in a four-wall or lost location, and that is not picked or ASN inventory. The application does not validate mixing restrictions when updating the inventory's location.

## Configure inventory settings

1.  Select **Configuration > Inventory > Inventory Settings**.
2.  Enter information in the [Inventory Settings fields](#Inventory_Settings_fields).
3.  To select the attributes by which the inventory displayed on the RF inventory summary screen is grouped:
    1.  Click **RF Summary Display**.
    2.  In the **Available** column, select the check box next to the attributes that apply.
    3.  Click **Apply**.
4.  Click **Save**.

## Inventory Settings fields

 
| Field | Description |
| --- | --- |
| RF Hold Details | If Yes, the details of a hold are automatically displayed when the RF operator scans inventory that is on hold.<br > If No, hold details are not automatically displayed. |
| Lot Parsing | If Yes, then when a lot number is entered during receiving, the application retrieves the manufactured or expiration date embedded in the lot number. For example, when an operator receives lot-tracked inventory and enters the lot number for an item, the application analyzes the lot number and populates the manufactured date and expiration date (as applicable) from the information embedded in the lot number. If this field is set to Yes, then lot parsing only takes place if the lot number is based on a valid lot format (assigned to the item) that is configured for date parsing.<br > If No, the application does not parse dates from lot numbers. |
| Recover from Lost Location | If Yes, then an operator that is performing a pick or count can recover inventory that the application shows (logically) as being in a lost location. The recovery process prompts the operator to confirm the contents of the LPN with what the application expects. If the content matches, the operator can update the location of the inventory to its current physical location and then continue with the pick or the count. If the content does not match, the location of the inventory cannot be updated to the current location.<br > If No, then for an inventory discrepancy during a pick, the application is typically configured to generate a count; for an inventory discrepancy during a count, the application is typically configured to generate an audit count. |
| Recover from Storage Location | If Yes, then an operator that is performing a pick or count can recover inventory that the application shows as being in a different physical location than where the pick or count is taking place. The recovery process prompts the operator to confirm the contents of the LPN with what the application expects. If the content matches, the operator can update the location of the inventory to its current physical location and then continue with the pick or the count.<br > If No, then for an inventory discrepancy during a pick, the application is typically configured to generate a count for both the current location and the physical location of the inventory; for an inventory discrepancy during a count, the application is typically configured to generate an audit count. |
| Enable Inventory Summary Display | If Yes, the RF operator is presented with an inventory summary display when the operator performs an inventory query. You also select the inventory attributes by which the display of inventory in a location is grouped (summarized).<br > When the RF operator performs an inventory query, the Inventory Query screen lets the operator enter selection criteria, and flow to the next screen. If the Inventory Summary Display screen is enabled, then the Inventory Summary Display screen is displayed and shows the quantity of inventory in each location summarized by the fields configured for display. For example, if Lot Number is assigned to be displayed, the screen displays a record that shows the item and item client (for a 3PL environment), and the quantity of inventory in a location that has the same lot number. The next record shows the quantity of inventory for the next lot, and so on. Following the inventory summary of the last record, the Inventory Display screen is displayed showing inventory details.<br > If No, the Inventory Summary Display screen is not display; instead, the Inventory Display screen shows the storage location, item, and all of the inventory details for one record.<br > In both instances, a page number on the RF screen indicates how many records were retrieved matching the selection criteria that was entered. The operator can scroll through the records, or page back and forth between records. |
| Minimum Length | Minimum number of characters that the application accepts when an LPN is entered on a device or workstation during inbound identification and during picking. If the entered value falls outside of the range (for example, if a larger number is scanned into the LPN field), then the application does not accept that value. The **Minimum Length** and **Maximum Length** fields can be used to help prevent the application from accepting other values, such as a UPC or location, instead of an LPN. |
| Maximum Length | Maximum number of characters that the application accepts when an LPN is entered on a device or workstation during inbound identification and during picking. If the entered value falls outside of the range (for example, if a larger number is scanned into the LPN field), then the application does not accept that value. The **Minimum Length** and **Maximum Length** fields can be used to help prevent the application from accepting other values, such as a UPC or location, instead of an LPN. |
| Inventory or Item Number | If Yes, RF operators are required to enter or scan either an item or location when performing a query on the RF Inventory Display screen.<br > If No, the operator is still required to enter at least one value on the RF Inventory Display screen before performing a query. Regardless of whether this field is set to Yes or No, the maximum number of results that are displayed is dependent on the value in the **Maximum Rows** field. |
| Maximum Rows | Maximum number of rows displayed when an RF operator performs an inventory query. |
| Minimum Extreme Tolerance (%) | Percentage of catch quantity below an item's defined minimum catch quantity that is deemed to be within tolerance. The application calculates catch quantity limits based on an item's configuration, but this value overrides the minimum tolerance and allows you to accept a lower value that would otherwise not be acceptable. For example, if an item's minimum catch quantity is 100, but the extreme minimum tolerance for a warehouse is 15 (15%), then whenever the warehouse captures catch quantity for the item, the application accepts a minimum value of 85.<br > **Note**: In a 3PL environment, the client configuration for this field overrides the warehouse level configuration. |
| Maximum Extreme Tolerance (%) | Percentage of catch quantity above an item's defined maximum catch quantity that is deemed to be within tolerance. The application calculates catch quantity limits based on an item's configuration, but this value overrides the maximum tolerance and allows you to accept a higher value that would otherwise not be acceptable. For example, if an item's maximum catch quantity is 100, but the extreme maximum tolerance for a warehouse is 15 (15%), then whenever the warehouse captures catch quantity for the item, the application accepts a maximum value of 115.<br > **Note**: In a 3PL environment, the client configuration for this field overrides the warehouse level configuration. |
| Suppress Out of Tolerance Prompt | If Yes, the application does not prompt the operator to recapture the catch quantity when the catch quantity of inventory is beyond its normal tolerance limits and within the extreme tolerance limits for the client. The application accepts the entered catch quantity for the inventory. For example, if an item's maximum catch quantity is 100, but the extreme maximum tolerance for the warehouse is 15 (15%), then whenever the application captures catch quantity for the item and warehouse within a value of 115, the application does not prompt the RF operator to recapture the catch quantity.<br > If No, the application prompts the operator to recapture the catch quantity when the catch quantity of inventory is beyond its normal tolerance limits and within the extreme tolerance limits for the client.<br > If the captured catch quantity is beyond the minimum or maximum extreme tolerance limit, the application does not allow the operator to proceed further and prompts the operator to recapture the catch quantity irrespective of the value of **Suppress Out of Tolerance Prompt**.<br > **Note**: In a 3PL environment, the client configuration for this field overrides the warehouse level configuration. |
| Delay Capture Until Loading | If Yes, the application does not prompt the operator to capture catch quantity at picking. Instead, the application requires the operator to capture catch quantity before loading. The application does not allow an operator to load inventory if the catch quantity is required but has not been captured. If you set this field to Yes, an operator can capture the catch quantity for an LPN or sub-LPN using directed or undirected work, depending on the following configurations:<br>-   • If the **Require Sub-LPN Capture** field is Yes, and if catch-tracked inventory is deposited to a location type with the **Create Sub-LPN Catch Work on Deposit** field set to Yes, then the application creates directed work for the capture. If the inventory is not deposited to a location type enabled for creating directed capture work, then an operator must capture catch quantity using the undirected RF menu option.
<br>-   • If the **Require Sub-LPN Capture** field is No, then the option to create directed capture work upon deposit is disabled, and an operator must capture the capture catch quantity using the undirected RF menu option before loading.
<br > If No, the application prompts the operator to capture the catch quantity of inventory when picking a full or partial pallet.<br > **Note**: In a 3PL environment, the client configuration for this field overrides the warehouse level configuration. |
| Require Sub-LPN Capture | If Yes, the operator is required to capture the catch quantity of each sub-LPN during shipping (while picking or before loading). If you set this field to Yes, the point at which the operator captures the sub-LPN catch quantity depends on whether delayed capture is enabled (**Delay Capture Until Loading** field).<br > **Note**: If a work assignment is picked to a sub-LPN, the individual case information (including catch quantity) is no longer retained. Therefore, the application does not prompt for sub-LPN capture if a work assignment is picked to a sub-LPN, even if this field is set to Yes. See [Work assignments picked to sub-LPNs](../outbound/picking/work-assignments.md).<br > If No, the operator is not required to capture the catch quantity of each sub-LPN during shipping; however, LPN catch quantity may still be required.<br > **Note**: In a 3PL environment, the client configuration for this field overrides the warehouse level configuration. |
| Allow Cancel Capture | If Yes, then when prompted to capture the catch quantity of inventory either during picking or before loading, the operator can cancel the capture request. If an operator cancels the catch quantity capture for an LPN or for a sub-LPN on an LPN, then the application will not prompt for a capture of the LPN again.<br > If No, then the operator is required to capture the catch quantity of inventory when prompted by the application; the operator cannot cancel the prompt.<br > **Note**: In a 3PL environment, the client configuration for this field overrides the warehouse level configuration. |
| Require Out of Tolerance Approval | If Yes, the application requires an approval, such as from a supervisor, for inventory that is outside of its normal tolerance but within the defined extreme tolerance limits. Inventory that is outside its normal tolerance but within the extreme limits is displayed with the **Tolerance** tag and must be approved (or adjusted) before it can be loaded and shipped. The application calculates catch quantity limits based on an item's configuration, and the values specified in **Minimum Extreme Tolerance (%)** or **Maximum Extreme Tolerance (%)**. For example, if the minimum tolerance limit is 100, the minimum extreme tolerance limit is 85, and the captured catch quantity is 90, the application tags inventory as out of tolerance and prompts for a supervisor approval.<br > If No, the application does not require an approval to ship inventory even if the catch quantity is outside the normal tolerance limits but within the configured extreme tolerance limits.<br > **Note**: In a 3PL environment, the client configuration for this field overrides the warehouse level configuration. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
