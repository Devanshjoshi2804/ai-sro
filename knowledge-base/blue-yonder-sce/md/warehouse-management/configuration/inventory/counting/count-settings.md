---
title: "Count Settings"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/count_settings.htm"
source: "/content/count_settings.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inventory"
  - "Counting"
  - "Count Settings"
sections:
  - "Count days and exceptions"
  - "Count back counts"
  - "Automated ABC counts"
  - "Lost location for count discrepancies"
  - "Configure count settings"
  - "Count Settings fields"
images:
  - "/content/resources/images/image895478_12x11.png"
  - "/content/resources/images/image942307.png"
source_sha1: 5f349d9498d68f3fff73044cd8b2d0c26313ab4d
---
# Count Settings

Count settings are used to define how the application prompts for and processes inventory counts. You use count settings to configure the following attributes:

-   **General**
    -   Item and location attributes that must be captured during a summary count:
        -   The standard is for the operator to enter the item and the quantity of that item in the location. The operator is also required to enter any additional item or location attributes configured for the zone or client (3PL), if they are required for the item. For example, if the Lot attribute is set, the operator is required to enter the lot if the item in the location is lot tracked. If the item in the location is not lot tracked, then the operator is not required to enter a lot since it does not exist on the item.
        -   The requirements for inventory attributes can be set at three levels: required for all locations, overridden by count zone, and overridden by client (in a 3PL environment).
        -   The requirements for location attributes apply to all countable locations.
    -   Indicate whether the expected item is displayed to the user during a count. If it is not displayed, then the operator must enter the item.
    -   Count discrepancies for which a secondary count is not generated. If an inventory count reveals a discrepancy that is less than or equal to the threshold value, a secondary (audit) count is not generated. The threshold is used to prevent generating a secondary count for minor discrepancies.
-   **ABC counting**
    -   Count days per period
    -   Type of ABC counts that are scheduled on the selected count days. ABC counts can be scheduled by item, item and supplier, location, or client.
    -   Number of times per period that each code is counted. For example, if A Code is set to 30 and the Count Days Per Cycle is 30, then the application would put the A items on a list to count every day.
        
        If the type of ABC count is by item or by item and supplier, then the client-specific ABC counts (times per period), if any, override the standard ABC code times per period.
        
        If the type of ABC count is by item and supplier, then the supplier-specific ABC counts (times per period), if any, override the standard ABC code times per period.
        
        **Note**: When both client-specific and supplier-specific ABC counts exist, the application uses the ABC count with the highest setting for times per period.
        
    -   Calendar or count days that define how a count period is determined.
-   **Paper-based cycle and audit counts**
    -   Indicate whether the expected quantity for the item is populated as the count quantity on the Count Entry page.
-   **Reasons for count adjustments**
    -   List of reasons from which an operator can select when performing an inventory adjustment based on a count discrepancy.
-   **Count near zero counts**
    -   Count zones and items for which a count is generated when inventory falls below a selected threshold amount. You can select users authorized to perform count near zero counts and UOMs that are available during count near zero for a pick zone. The application prompts the operator to confirm count quantities in the UOMs that are common between the pick zone and item footprint, or only the UOMs defined on the item footprint, if there are no common UOMs.
-   **Count backs**
    -   Items, locations, or pickable UOMs for which a user is prompted to count the quantity that remains in a location or on an LPN, after a pick is performed. All users are required to perform the count back during picking if the item or location requires it. However, you can override this setting for individual users.
    -   Pick zones in which the operator is required to count back the remaining quantity of the picked item in the entire location. For example, assume a location contains Item1 on LPN1 and LPN2, and Item2 on LPN3. If an authorized operator picks Item1 from LPN1, then the operator is required to count back the remaining quantity of Item1 on LPN1 and LPN2. The operator does not count back Item2 on LPN3. You can also enable this functionality on the pick zone configuration page. This functionality only affects count back quantity if manual and automatic consolidation are disabled for the storage zone. If manual or automatic consolidation are enabled for the storage zone, then the operator is required to count back the entire picked item quantity for the location regardless of this field.

## Count days and exceptions

If the count period is defined by count days, you can define the standard days on which counts can be scheduled.

Count days are days on which cycle counts can be performed. The cycle counting process uses the count days to schedule cycle counts for the warehouse.

An exception is used to define a specific date on which the setting for a count is reversed. For example, if your standard count days are Monday, Wednesday and Friday, but you know that during a specific week you need to count on Thursday, you can add that date as an exception; the application will process that day as a count day instead of its default value of a non-counting day.

**Note**: Exception days must be defined for each new calendar year as they do not carry over from the previous year.

## Count back counts

Count back is a standard count type provided with the application.

When you configure the application to prompt operators to perform a count back, you define the following attributes:

-   The items for which a count back is required.
-   The locations for which a count back is required.
-   The pickable units of measure (UOM) for which the application prompts the operator to count back in specific pick zones.
-   The users that are required to perform count backs if the item or location requires it. By default, all users that are authorized to perform count backs are required to perform them if the item or location requires it; however, you can override the default for individual users.
-   Whether an Event Management notification is sent when a count back results in an inventory discrepancy. See [Configure count settings](#Configure_count_settings).
-   When an operator performs a count back, the consolidation setting defined for the storage zone determines the quantity required for the count back.
    -   If LPN consolidation is disabled, then based on the pick zone configuration, the operator must enter either the quantity remaining on the LPN from which the inventory was picked, or the remaining quantity of the picked item in the entire location. The **Count Back Location Quantity** field for a pick zone determines which quantity is required. For example, assume a location contains Item1 on LPN1 and LPN2, and Item2 on LPN3. If count back by location is enabled and an operator picks Item1 from LPN1, then the operator is required to count back the remaining quantity of Item1 on LPN1 and LPN2.
        
        Also, the quantity remaining must be entered in a UOM that is less than the UOM from which the inventory was picked. For example, if a pallet contains 10 cases and an operator picks 2 cases from the pallet, then for a count back the operator can enter the remaining quantity as 8 cases, or the equivalent of 8 cases in any other UOM that is smaller than the pallet UOM.
        
        Consolidation is disabled for a storage zone when the **Automatic LPN Consolidation** and **Manual Consolidation During Putaway** fields are set to **No**.
        
    -   If LPN consolidation is enabled, an operator must enter the quantity remaining in the location from which they picked. For example, if a location contains 2 pallets (10 cases each), and an operator picks two cases, then for a count back the operator must enter the quantity remaining in the location; such as 18 cases.
        
        Consolidation is enabled for a storage zone when either the **Automatic LPN Consolidation** or **Manual Consolidation During Putaway** field is set to **Yes**.
        
    -   The **Manual Consolidation During Putaway** field must be set to **Yes** to perform the count back for the pallet UOM. See [Add or modify a storage zone](../../inbound/storage/storage-zones.md).

## Automated ABC counts

In ABC counting, the application uses the ABC codes and the ABC counting configuration to automatically schedule cycle counts by item, location or client. Items or locations are identified with A, B, or C codes based on factors such as the nature of the items, location movements, and item expense. You assign the counting frequency to ABC codes to determine how many times an item or a location must be counted within the count period. The application then automatically schedules the counts, and a background job (if enabled) automatically releases ABC counts on the count day. The job (maintained in the Console, under Jobs) is disabled by default and has configurable parameters such as Count Type, Release flag, Number of days to look ahead, and Warehouse ID. Based on the configured parameters, the application schedules or releases ABC counts into separate batches by Item, Item and Supplier, Client, and Location and Count Zone. The counts are displayed on the Counts page, and the ABC counts statistics are displayed on the [Inventory Dashboard](../../../inventory/dashboard.md).

The format of an application-generated batch number is ABC-MMDDYYYYTTTTTTTT-x, where MMDDYYYYTTTTTTTT is the date and time when the ABC count was scheduled and x is the application-generated sequence.

You can enable ABC counting and configure the counting frequency for ABC codes in the count settings. See [Configure count settings](#Configure_count_settings).

If you select to count by item (or item and supplier), then the application may ignore the daily quota for counts. The daily quota is derived from the number of locations eligible for counting divided by the number of days in the count cycle. For example, if there are 10 locations to be counted in a count period of 5 days, the daily quota is 2. When an item exists across multiple locations, the application creates and releases as many counts as needed to complete the total item count across all locations on the same day. The application processes counting by item this way so that a complete and accurate count for an item does not span multiple days, and any discrepancies with the item can be resolved sooner. For example, if a single item exists in 10 locations and the count period is 5 days, then the daily quota is 2. However, since the count is by item, the application releases all 10 counts on the same day rather than 2 per day for the duration of the count period.

**Note**: The ability to schedule ABC counts by item and supplier is currently not supported.

## Lost location for count discrepancies

When a count reveals a discrepancy between the actual (user-reported) and logical (expected) inventory quantities, the application performs the following process:

1.  If the item supports adjustments, then when a variance occurs, the count is completed and the adjustment is recorded.
    
    -   If the counted (physical) quantity is less than the expected quantity, then the application creates the discrepant inventory (logically) and moves it to the permanent adjustment location (PERM-ADJ-LOC).
        
    -   If the adjusted quantity is greater than the adjustment threshold, then the adjustment is first sent for adjustment approval before the count is completed.
        

**Notes**:

-   An item supports adjustments if the **Supports Inventory Adjustment** field is set to Yes on the item configuration.
    
-   If the application is configured to allow automatic inventory adjustments and no secondary count is generated, then inventory is sent (logically) to the lost location. See [Automatic inventory adjustments](../inventory-adjustments.md).
    

3.  If the item does not support adjustments, then during RF inventory adjustments performed as a result of a count discrepancy, the following processing takes place:
    
    **Note**: The following processes only take place during RF inventory adjustments performed as a result of a count discrepancy. For other types of inventory adjustments (RF and workstation), the application displays an error if a user attempts to adjust an item that does not support adjustments.
    
    -   If the counted (physical) quantity is greater than the expected quantity, regardless of the adjustment threshold, the operator is allowed to decrease (adjust) the counted quantity to match the expected quantity. For example, if the counted quantity is 7 cases and the expected quantity is 5 cases, the operator can change the counted quantity to 5, and then perform the manual process of physically removing 2 cases from the location or LPN and finding a proper location for the inventory. No inventory adjustment is recorded.
    -   If the counted quantity is less than the expected quantity, regardless of the adjustment threshold, then the application creates the discrepant inventory (logically) and moves it to the lost location defined for the area. If a lost location was not defined for the area, the quantity is moved to the application-assigned lost location, which is the permanent count adjustment location (PERM-CNT-LOC), from which inventory cannot be recovered. For example, if the counted quantity is 5 cases and the expected quantity is 7 cases, then 2 cases are moved (logically) to the lost location. No inventory adjustment is recorded.
        
        When the inventory is moved to the lost location, a background workflow (Inventory Adjust Status Change) changes the logical inventory to a hold status.
        

The logical inventory remains in the lost location until the operator finds the actual inventory or uses another process to reconcile the difference. See [Recovery of lost inventory](../inventory-settings.md).

## Configure count settings

1.  Select **Configuration > Inventory > Counting > Count Settings**.
2.  Enter information in the [Count Settings fields](#Count_Settings_fields).
3.  To require inventory attributes to be captured during a summary count:
    
    **Note**: An operator is required to confirm default inventory attributes during a summary count, unless they are overridden for a count zone. If no attributes are selected, the operator is only required to confirm the item and quantity.
    
    1.  Click **Default Inventory Attributes**.
    2.  In the **Available** column, select the check box next to the attributes to use.
    3.  Click **Apply**.
4.  To specify inventory attributes for a count zone:
    1.  Click **Override Inventory Attributes by Zone**.
    2.  Perform one of the following tasks:
        -   To add a count zone, click **Add**.
        -   To modify attributes for a count zone, in the grid, click the count zone.
        -   To copy a count zone configuration, in the grid, select the check box next to the count zone, and then click **Copy**.
    3.  From the **Count Zone** drop-down list, select a count zone.
    4.  In the **Available** column, select the attributes that need to be confirmed along with the item and quantity for counts that take place within the zone.
        
        **Note**: The attributes that you select will be required instead of the default inventory attributes, if any, that were configured.
        
    5.  Click **Apply**.
5.  To specify inventory attributes for a client:
    
    **Note**: The **Override Inventory Attributes by Client** button is available only when the **Type of ABC Count** field is set to **By Item** or **By Item and Supplier**.
    
    1.  Click **Override Inventory Attributes by Client**.
    2.  Perform one of the following tasks:
        -   To add a client, click **Add**.
        -   To modify attributes for a client, in the grid, click the client.
        -   To copy a client configuration, in the grid, select the check box next to the client, and then click **Copy**.
    3.  From the **Client** drop-down list, select a client.
    4.  In the **Available** column, select the attributes that need to be confirmed along with the item and quantity for counts that take place for the client.
        
        **Note**: The attributes that you select will be required instead of the default inventory attributes, if any, that were configured.
        
    5.  Click **Apply**.
6.  To configure client count display settings:
    
    **Note**: The **Override Count Display Settings by Client** button is available only when the **Type of ABC Count** field is set to **By Item** or **By Item and Supplier**.
    
    1.  Click **Override Count Display Settings by Client**.
    2.  Perform one of the following tasks:
        -   To add display settings for a client, click **Add**, and then from the **Client** drop-down list, select a client.
        -   To modify display settings for a client, in the grid, click the client.
        -   To copy a client count display setting, in the grid, select the check box next to the client, and then click **Copy**.
    3.  Enter information for the count display settings. See [Count Settings fields](#Count_Settings_fields).
    4.  Click **Apply**.
7.  To enable count types for count by LPN counting:
    
    **Note**: Count by LPN is an operation in which the cycle count is performed by entering or scanning LPNs, and without entering any other information such as item and quantity. See [Count by LPN](../counting.md).
    
    1.  Enable the count types that can be used to perform count by LPN:
        1.  Click **Types Using Count by LPN**.
        2.  In the **Available** column, select the count types to use.
        3.  In the **Selected** column, in the **LPN Count Operation** column, select the work operation used to perform the count. The application provides the LPN Cycle Count operation, by default, for this purpose.
        4.  Click **Apply**.
    2.  Enable the count zones in which you allow count by LPN:
        1.  Click **Zones Using Count by LPN**.
        2.  In the **Available** column, select the count zones to use.
        3.  In the **Selected** column, in the **LPN Level** column, select level at which counts can be performed by scanning an LPN.
        4.  Click **Apply**.
8.  To specify the dates on which count days are reversed:
    
    **Note**: An exception reverses the count day selection. For example, if Monday is selected as a count day, an exception for a date that falls on a Monday indicates counting is not performed on that date. If Monday is not selected as a count day, an exception for a date that falls on a Monday indicates counting is performed on that date. The application does not allow you to configure exceptions until changes to selected count days are saved.
    
    1.  To save changes to selected count days, click **Save**.
    2.  To manage exceptions to count days:
        1.  Under **Count Days**, click **Exceptions**.
        2.  To add an exception, on the calendar, select the dates on which the day configuration is reversed. The selected dates are highlighted in red.
        3.  To remove an exception, perform one of the following tasks:
            -   On the calendar, click the exception.
            -   Under **Exception Dates**, click ![Delete](../../../../../images/resources/images/image895478_12x11.png) next to the exception to be deleted.
        4.  Click ![Close](../../../../../images/resources/images/image942307.png).
9.  To configure client-specific ABC counts:
    
    **Note**: The **Client ABC Counts** button is only available when the **Type of ABC Count** field is set to **By Item** or **By Item and Supplier**.
    
    1.  Click **Client ABC Counts**.
    2.  Perform one of the following tasks:
        -   To add a client configuration, click **Add**, and then from the **Client** drop-down list, select a client.
        -   To modify a client configuration, in the grid, click the client.
        -   To copy a client configuration, in the grid, select the check box next to the client, and then click **Copy**.
    3.  Enter information for the client ABC counts. See [Count Settings fields](#Count_Settings_fields).
    4.  Click **Apply**.
10.  To configure supplier-specific ABC counts:
     
     **Note**: The **Supplier ABC Counts** button is only available when the **Type of ABC Count** field is set to **By Item and Supplier**.
     
     1.  Click **Supplier ABC Counts**.
     2.  Perform one of the following tasks:
         -   To add a supplier configuration, click **Add**, and then from the **Supplier** drop-down list, select a supplier.
         -   To modify a supplier configuration, in the grid, click the supplier.
         -   To copy a supplier configuration, in the grid, select the check box next to the supplier, and then click **Copy**.
     3.  Enter information for the supplier ABC counts. See [Count Settings fields](#Count_Settings_fields).
     4.  Click **Apply**.
11.  To define reasons for adjusting inventory for a discrepant count:
     1.  Under **AUDIT COUNTS**, click **Reason for Count Adjustment**.
     2.  Perform one of the following tasks:
         -   To add a reason, click **Add**.
         -   To modify a reason, in the grid, click the reason.
         -   To copy a reason, in the grid, select the check box next to the reason, and then click **Copy**.
     3.  Perform one of the following tasks:
         -   In the **Count Adjustment Code** field, enter a code.
         -   To have the application provide a code, select the **System Generated** check box.
     4.  In the **Count Adjustment Reason** field, enter a name for the reason.
     5.  Select the clients for whom the reason can be used:
         1.  Click **Clients**.
         2.  In the **Available** column, select the check box next to the clients to use.
         3.  Click **Apply**.
     6.  Click **Apply.**
12.  To define reasons for requesting a manual count:
     1.  Under **MANUAL COUNTS**, click **Reason for Request**.
     2.  To add a reason:
         1.  Click **Add**.
         2.  In the **Reason**, **Description**, and **Short Description** fields, enter the values.
         3.  Click **Apply**.
     3.  To modify the descriptions for a reason:
         1.  In the grid, click the description and change it.
         2.  Click **Apply**.
     4.  To translate a reason:
         1.  Perform one of the following tasks:
             -   To translate specific rows, in the grid, select the check box of the rows, and then above the grid, click **Translation**.
             -   To translate all rows, above the grid, click **Translation**.
         2.  From the **Destination Locale** drop-down list, select the locale.
         3.  In the grid, select a translated description or short description, and then enter the new value.
         4.  Click **Save**.
13.  Under **COUNT NEAR ZERO**, configure the zones and thresholds for which an operator is required to perform a count if inventory falls below the threshold after picking or after an inventory transfer from a location:
     1.  Select the count zones to enable for count near zero counts:
         1.  Click **Count Zone.**
         2.  In the **Available** column, select the check box next to the count zones to use.
         3.  In the **Location Threshold** and **Unit of Measure** fields, enter the quantity and select the type of threshold below which the operator is prompted to complete a count near zero count.
         4.  Click **Apply**.
     2.  Select the items to enable for count near zero counts:
         1.  Click **Items**.
         2.  Perform one of the following tasks:
             -   To add an item, click **Add**.
             -   To copy an item's settings, in the grid, select the check box next to the item, and then click **Copy**.
         3.  In the **Item** field, select an item.
         4.  In the **Threshold Quantity** field, select the quantity at or below which the operator is prompted to complete a count near zero count.
         5.  Click **Apply**, and then click **Apply**.
     3.  Select the UOMs (by pick zone) for which operators are prompted to confirm the quantity during a count near zero:
         
         1.  Click **Units of Measure**.
         2.  Perform one of the following tasks:
             -   To add UOMs for a pick zone, click **Add**.
             -   To edit UOMs for a pick zone, in the grid, click the pick zone.
         3.  In the **Pick Zone** field, select a pick zone.
         
         **Note**: The pick zone cannot be changed when editing the UOMs for the pick zone.
         
         5.  In the **Available UOMs** column, select the check box next to the UOM.
         6.  Click **Apply**.
     4.  In the **Minimum Hours** field, enter the amount of time that must elapse before a count near zero count is generated for the same location in which a count near zero was already performed.
     5.  Select the users who are authorized to perform count near zero counts:
         1.  Click **Authorized Users**.
         2.  In the **Available** column, select the check box next to the users to authorize.
         3.  Click **Apply**.
14.  Under **COUNT BACKS**, configure the settings that determine when a user is required to count the amount of inventory remaining in a location following a pick:
     1.  Select the locations that require a count back to be performed:
         1.  Click **Locations**.
         2.  In the **Available** column, select the check box next to the locations to use.
         3.  Click **Apply**.
     2.  Select the items that require a count back to be performed:
         1.  Click **Items**.
         2.  In the **Available** column, select the check box next to the items to use.
         3.  Click **Apply**.
     3.  Select the users that are not required to perform count backs. By default, all users are required to perform a count back if a location or item requires it.
         1.  Click **Users**.
         2.  To add a user override:
             1.  In the grid, click **Add**.
             2.  In the **User** field, enter the user.
             3.  In the **When to Count Back** field, select the option that applies.
             4.  Click **Apply**.
         3.  To delete a user override:
             1.  In the grid, select the user, and then click **Delete**. A confirmation message is displayed.
             2.  Click **OK**.
         4.  Click **Apply**.
     4.  Select the UOMs that require a count back.
         
         1.  Click **Units of Measure**. The Count UOMs page is displayed.
         2.  Click **Add**.
         3.  From the **Pick Zone** drop-down list, select the pick zone for which you want to configure count back UOMs.
         4.  In the **Available UOMs** column, select the check box next to the UOM.
         5.  Click **Apply**.
         6.  Click **Save**.
         
         **Notes**:
         
         -   The **Manual Consolidation During Putaway** field must be set to **Yes** to perform the count back for the pallet UOM. For details, see [Add or modify a storage zone](../../inbound/storage/storage-zones.md).
         -   If there are no common UOMs between the item footprint and pick zone, then the application prompts for all UOMs defined on the item footprint.
         
     5.  Select the pick zones in which operators must count back the entire location quantity of the picked item, instead of counting only the remaining quantity on the LPN from which the item was picked.
         
         **Note**: This functionality only affects count back quantity if manual and automatic consolidation are disabled for the storage zone. If manual or automatic consolidation are enabled for the storage zone, then the operator is required to count back the entire picked item quantity for the location regardless of this field.
         
         1.  Click **Count Back Location Quantity**.
         2.  In the **Available** column, select the check box next to the pick zones in which you require a location count back of the picked item.
         3.  Click **Apply**.
15.  Click **Save**.

## Count Settings fields

 
| Field | Description |
| --- | --- |
| Allow Catch Quantities | If Yes, during counting, the operator is required to enter the catch quantity (such as weight) as well as the unit quantity for inventory that is tracked by catch quantity. Select Yes if you store items that are tracked by catch quantity and you want these values verified during inventory counts. A catch quantity is a quantity that is represented in catch unit measurements, which are variable weights or sizes of inventory that may exist within the same material handling (stock keeping) unit.<br > If No, during counting, the operator is not required to enter a catch quantity (such as weight) for inventory that is tracked by catch quantity. |
| Audit Count Generation Limit | Percentage of a catch quantity discrepancy that is allowed. If a cycle count for a location results in a discrepancy greater than this value between the expected and counted catch quantity, then an audit count is generated automatically. This value is used to prevent minimal (acceptable) discrepancies from generating audit counts.<br > If a catch quantity discrepancy falls within the limit, then an automatic inventory adjustment takes place to update the expected catch quantity to the counter's catch quantity. |
| Location Attributes | Attribute of a location that the operator must confirm when performing a cycle count at a location. You can enter up to three attributes, such as Verification Code (locvrc) or Aisle (aisle\_id) to provide an additional level of verification that the operator is performing the count at the correct location. |
| Single Item Locations | Defines the information that is displayed to the operator or printed on the count sheet for counts that are generated for locations in which the storage zone is configured to allow single items. Only one item is allowed to be stored a single-item location; mixing of inventory (different items) is not allowed.<br>-   •
    
    **Enter Item & Quantity (Blind)**: The operator is directed to the location to count, but the expected item is not displayed to the operator or printed on count sheets. The operator enters the item and quantity in the location. Not showing the item to the counter may take more time but forces the operator to enter the item rather than accepting the displayed value as correct.
    
    <br>
    
    If you select this option, you can also select one or both of the following options:
    
    <br>
    -   • **Do not show item if detail count**: Indicates that for detail counts, the application does not display (or include on count sheets) the expected items in the location. A detail count requires the operator to scan an LPN in the location, and then enter the item and quantity on the LPN. If another LPN is in the same location, the operator scans the next LPN and enters the item and quantity; and so on.
    <br>-   • **Do not show item if summary count**: Indicates that for summary counts, the application does not display (or include on count sheets) the expected items in the location. The summary count requires the operator to enter the item and the total quantity in the location.
    <br>
<br>-   • **Enter Quantity Only (Prompted)**: The operator is directed to the location to count, and the item in the location is displayed to the operator or printed on the count sheet. The operator confirms that the item is in the location and enters the quantity for each item that the application expects in the location. Showing the item to the counter may save time, but if there is a different item in the location, the operator enters 0 for the quantity and then has to enter the correct item with the quantity. Prompted is typically used in warehouses that do not have item barcodes to scan during counting.
<br > **Note**: Prompted means the application displays the item to the counter. Blind means no item displays and the counter must enter the item. The counter always has to enter the counted quantity no matter if prompted or blind is used. |
| Mixed Item Locations | Defines the information that is displayed to the operator or printed on the count sheet for counts that are generated for locations in which the storage zone is configured to allow mixed (different) items to be stored in a location in the zone.<br>-   •
    
    **Enter Item & Quantity (Blind)**: The operator is directed to the location to count, but the expected item is not displayed to the operator or printed on count sheets. The operator enters the item and quantity in the location. Not showing the item to the counter may take more time but forces the operator to enter the item rather than accepting the displayed value as correct.
    
    <br>
    
    If you select this option, you can also select one or both of the following options:
    
    <br>
    -   • **Do not show item if detail count**: Indicates that for detail counts, the application does not display (or include on count sheets) the expected items in the location. A detail count requires the operator to scan an LPN in the location, and then enter the item and quantity on the LPN. If another LPN is in the same location, the operator scans the next LPN and enters the item and quantity; and so on.
    <br>-   • **Do not show item if summary count**: Indicates that for summary counts, the application does not display (or include on count sheets) the expected items in the location. The summary count requires the operator to enter the item and the total quantity in the location.
    <br>
<br>-   • **Enter Quantity Only (Prompted)**: The operator is directed to the location to count, and the item in the location is displayed to the operator or printed on the count sheet. The operator confirms that the item is in the location and enters the quantity for each item that the application expects in the location. Showing the item to the counter may save time, but if there is a different item in the location, the operator enters 0 for the quantity and then has to enter the correct item with the quantity. Prompted is typically used in warehouses that do not have item barcodes to scan during counting.
<br > **Note**: Prompted means the application displays the item to the counter. Blind means no item displays and the counter must enter the item. The counter always has to enter the counted quantity no matter if prompted or blind is used. |
| Auto-Complete | If Yes, then in storage zones configured for single-item storage, the application automatically completes the count when the operator indicates that a count is finished, typically by selecting Done. Select this option if you want to eliminate the need for counters to complete the count in the Complete Cycle Count screen.<br > If No, then in single-item storage zones, when an operator indicates that a count is finished, the Complete Cycle Count screen is displayed, requiring the operator to confirm that the count is complete. |
| Enable ABC Counting | If Yes, the application uses the ABC counting configuration to automatically schedule cycle counts for inventory based on the ABC code assigned to an item, location, or client. You assign one of the ABC codes to the clients, items, and locations that you want to be counted on a regular basis. The application automatically schedules the counts based on the assigned ABC codes. The counts are displayed on the Counts page in the Inventory module.<br > If No, the ABC counting configurations are not enabled, and the application does not attempt to schedule counts based on ABC codes, regardless of whether they are assigned to items, locations, and clients. |
| Initial Start Date for ABC Counts | Date on which the application should begin scheduling ABC counts, based on the configuration of the ABC codes and count days calendar. Enter a date or click the calendar to select a date from the display. When this initial date is set, you are not required to update it again at the beginning of a new cycle count period. |
| Type of ABC Count | Determines the type of ABC counts that are scheduled on the selected count days.<br>-   •
    
    **By Item**: When a cycle count is scheduled for an item, all count zones in which the item is stored are counted in the cycle count period based on the ABC frequency setting for the item.
    
    <br>
    
    **Note**: If you select to count by item (or item and supplier), then the application may ignore the daily quota for counts. The daily quota is derived from the number of locations eligible for counting divided by the number of days in the count cycle. When an item exists across multiple locations, the application creates and releases as many counts as needed to complete the total item count across all locations on the same day. The application processes counting by item this way so that a complete and accurate count for an item does not span multiple days, and any discrepancies with the item can be resolved sooner.
    
    <br>
<br>-   • **By Item and Supplier**: When a cycle count is scheduled for an item and supplier, all items are counted in the cycle count period based on the ABC frequency setting for the supplier.
<br>-   • **By Location**: When a cycle count is scheduled by location, counts are scheduled for every countable location in the warehouse, whether the location has inventory in it (based on the ABC frequency of the item) or the location is empty (based on the ABC frequency of the location). Select this option to ensure all locations are counted whether they have inventory in them or not. For example, if an operator moves inventory into a location without scanning the location barcode during the deposit, that the counter catches the inventory in the location during counting since the application considers this location empty.
<br>-   • **By Client**: When cycle counting is performed by client, then all count zone locations that contain the client's inventory are counted. |
| Count Days Per Cycle | Number of count days within a count period. A count period is the number of days it takes to schedule all of the ABC counts that must be performed at least once per period. For example, if you define a count period as 30 days. Then if your A code must be counted 3 times per period, the application schedules A counts every 10 days. If your B code must be counted 2 times per period, the application schedules B counts every 15 days. If your C code must be counted once per period, the application schedules C counts every 30 days. |
| Minimum Days Per Cycle | Minimum number of count days that are required in count period. This value limits the number count days that can be removed from a count cycle as a result of exceptions that are added to the configuration. |
| Period Day Interpretation | Determines how the application calculates a count period.<br>-   • **Countable**: A count period consists of count days (defined under **Count Days**), except for any dates marked as exceptions (defined under **Exceptions**). For example, if you select Countable, and then select Monday through Friday as count days, then a 30-day count period represents 30 weekdays.
<br>-   • **Calendar**: A count period consists of every day in the week, regardless of the days on which counts actually take place (count days). For example, if you select Calendar, then a 30-day count period represents 30 days including Saturdays and Sundays, regardless of which count days are selected. |
| Count Days | Days on which cycle counts are performed. This configuration is used in determining which days are included in a count period. For example, if you set **Period Day Interpretation** to Count Days, and then select Monday, Wednesday, and Friday as count days, then the days in a count period consist of only Mondays, Wednesdays, and Fridays.<br > You use the **Exceptions** field to select the dates on which exceptions to the count days occur. For example, you can select as an exception a holiday that falls on a day of the week that is set as a count day. |
| Work Days | Reserved for future use. |
| Times per Period | Number of times per count period that you want to count items or locations to which the ABC code has been assigned.<br > Use the ABC codes in the following ways:<br>-   • **A code**: Use for the items or locations that must be counted more frequently than other codes.
<br>-   • **B code**: Use for items and locations that must be counted less frequently than A codes, but more frequently than C codes.
<br>-   • **C code**: Use for items or locations that must be counted less frequently than other codes.
<br > A count period is defined by a number of count days or calendar days, depending on the configuration of the **Period Day Interpretation** field. |
| Expected Quantity | If Yes, then when a user enters paper-based count results at a workstation, the expected quantity for the item is populated as the count quantity on the Count Entry page. If this field is set to Yes, the user can quickly confirm the count quantity without having to manually enter the quantity. If there is a discrepancy between the counted quantity and the original quantity, the user can modify the value before completing the count.<br > If No, then the expected quantity is not displayed on the Count Entry page, and the user must enter the item quantity from the count sheet. |
| Minimum Hours | Minimum number of hours that must elapse following a count near zero count before another count near zero count can be generated for the same location. This value is used to ensure that operators are not prompted to perform count near zero counts repeatedly for the same location. For example, in a location that contains fast-moving inventory, inventory levels can be depleted many times a day to below the count near zero thresholds. |
| Send Alert | If Yes, then Event Management sends an alert to users that are configured in Event Management to be notified of count backs for which a discrepancy has been logged. An alert is only sent if Event Management is integrated with Warehouse Management.<br > If No, then Event Management does not send an alert when a discrepancy is logged as a result of a count back. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
