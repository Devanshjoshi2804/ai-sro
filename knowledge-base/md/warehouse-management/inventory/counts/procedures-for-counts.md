---
title: "Procedures for counts"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/procedures_for_counts.htm"
source: "/content/procedures_for_counts.htm"
toc_path:
  - "Warehouse Management"
  - "Inventory"
  - "Counts"
  - "Procedures for counts"
sections:
  - "View counts and batches"
  - "Schedule a count"
  - "Release a count or batch"
  - "Remove a count or batch"
  - "Cancel a count or batch"
  - "Reset a count"
  - "Reopen a count"
  - "Edit a batch"
  - "Complete a batch"
  - "Add count to a batch"
  - "Manage count work"
  - "Enter paper-based count results"
  - "Perform a paper-based audit count"
  - "View audit counts and print a count sheet"
  - "View count history"
  - "Add or modify a count template"
  - "Delete a count template"
  - "Counts field listings"
  - "Schedule Count Criteria fields"
  - "Schedule fields"
  - "Template fields"
  - "Scheduled Counts fields"
  - "Scheduled Batches fields"
  - "Counts History fields"
  - "Batches History fields"
images: []
source_sha1: 20b168836c69f1ac808917523c70c701af3da803
---
# Procedures for counts

The following procedures can be performed on counts.

## View counts and batches

The counts and batches views allow you to view all counts and batches in different statuses.

1.  Select **Inventory > Counts**.
2.  Select the **Scheduled** tab.
3.  Select the **Counts** tab. The Counts grid is displayed with all counts that are scheduled, released, suspended, or cancelled.
4.  View the information in the [Scheduled Counts fields](#Schedule_Counts_fields).

**Note**: Use Quick Filters to limit the display to ABC Counts, Scheduled, Released, or Suspended counts.

6.  To view the work queue entry for a pending work request:
    1.  In the **Work ID** column, click the work ID.
    2.  Select **Inventory > Counts** to return to the Scheduled Counts display.
7.  Select the **Batches** tab. The Batches grid is displayed.

**Note**: By default, the Batches grid displays batches with counts for more than one location. Clear the filter to view all batches that are scheduled, released or cancelled.

9.  View the information in the [Scheduled Batches fields](#Scheduled_Batches_fields).
10.  In the grid, click the batch. Counts at each of the locations in the batch are displayed in the batch view.

## Schedule a count

You can manually schedule a count or release the count to the work queue. You can save the schedule count criteria as a template.

1.  Select **Inventory > Counts**.
2.  Select the **Scheduled** tab, and then select the **Counts** tab.
3.  From the **Actions** drop-down list, select **Schedule Count**. The Schedule Count page is displayed.
4.  In the **Criteria** column, enter the criteria in the [Schedule Count Criteria fields](#Schedule_Counts_Criteria_fields).

**Note**: You enter criteria to find the locations and items to count.

6.  Click **Find Locations**. The locations that contain inventory matching the selected attributes are displayed.
7.  Click **Next**.
8.  Enter information in the [Schedule fields](#Schedule_fields).
9.  If you select to save the schedule count as a template, enter information in the [Template fields](#Template_fields).
10.  Click **Save** to schedule the count, or click **Save and Release** to release the count. A confirmation message is displayed.
11.  Click **OK**.

## Release a count or batch

You can release scheduled counts for the count work to begin. Only counts in the Scheduled status can be released. You can also release a count batch. You can release a batch if one or more counts are in the Scheduled status, or if the batch is in the Scheduled or Partially Released status. For example, if a batch contains two counts, you can release the batch if any of the counts is in the Scheduled status.

1.  Select **Inventory > Counts**.
2.  Select the **Scheduled** tab.
3.  To release a count:
    1.  Select the **Counts** tab. The Counts grid is displayed.
    2.  In the grid, select the check box next to the counts to release.
    3.  From the **Actions** drop-down list, select **Release Count**. The Release Counts window is displayed.
    4.  Select one of the following options to release the count:
        -   **Release to Current Batch**: Releases the count to the same batch in which the count was scheduled.
        -   **Release to Batch Name**: Releases the count to the batch name that you provide. In the field, enter the name of the batch.
    5.  Click **OK**.
4.  To release a batch:
    1.  Select the **Batches** tab. The Batches grid is displayed.
    2.  In the grid, select the batch row to release.
    3.  From the **Actions** drop-down list, select **Release Batch**. A confirmation message is displayed.
    4.  Click **OK**.

## Remove a count or batch

You can remove a scheduled count if the count does not need to be released or performed. Only counts in the Scheduled status can be removed. You can remove a batch only if all counts in that batch are in the Scheduled status. When you remove a count, the count is removed permanently from the Counts grid. When you remove a batch, the batch is removed permanently from the Batches grid and all counts associated with the batch are removed permanently from the Counts grid.

1.  Select **Inventory > Counts**.
2.  Select **Scheduled**. The Counts grid is displayed.
3.  To remove a count:
    1.  Select the **Counts** tab. The Counts grid is displayed.
    2.  In the grid, select the check box next to the counts to remove.
    3.  From the **Actions** drop-down list, select **Remove Count**. A confirmation message is displayed.
    4.  Click **OK**.
4.  To remove a batch:
    1.  Select the **Batches** tab. The Batches grid is displayed.
    2.  In the grid, select the batch row to remove.
    3.  From the **Actions** drop-down list, select **Remove Batch**. A confirmation message is displayed.
    4.  Click **OK**.

## Cancel a count or batch

You can cancel an RF count before the count work begins or while it is in progress, and is in the Acknowledged, Released, Generated, or Deferred status. You can cancel an RF count batch only when all the counts in the batch are in one of the aforementioned statuses.

You can cancel a paper-based count or count batch any time before the count is completed. Paper-based counts are generated in an In Process status.

When you cancel a count, the counts are displayed in the Counts grid in the Cancelled status and the count work is deleted from the work queue. When you cancel a batch, the batch and the associated counts are displayed in the Batches and Counts grid in the Cancelled status. When you cancel a count batch that is in progress, no credit is given for counts that have been performed. When all counts in a batch are cancelled, the progress bar in the Completed column for the batch in the Batches tab is 100% and you can complete the batch. For completing a batch, see [Complete a batch](#Complete_a_batch).

1.  Select **Inventory > Counts**.
2.  Select **Scheduled**. The Counts grid is displayed.
3.  To cancel a count:
    1.  Select the **Counts** tab. The Counts grid is displayed.
    2.  In the grid, select the check box next to the counts to cancel.
    3.  From the **Action** drop-down list, select **Cancel Count**. A confirmation message is displayed.
    4.  Click **Yes**. A confirmation message is displayed with the number of counts cancelled successfully and counts that could not be cancelled.
    5.  Click **OK**.
4.  To cancel a batch:
    1.  Select the **Batches** tab. The Batches grid is displayed.
    2.  In the grid, select the batch row to cancel.
    3.  From the **Action** drop-down list, select **Cancel Batch**. A confirmation message is displayed.
    4.  Click **Yes**. A confirmation message is displayed.
    5.  Click **OK**.

## Reset a count

You can reset a cancelled count to its previous status (Released, Generated, or Deferred). Only counts in the Cancelled status can be reset. There is no option to reset a cancelled batch. The batch is reset to its previous status (Released, Generated, or Deferred) when you reset all counts associated with a batch.

1.  Select **Inventory > Counts > Scheduled**.
2.  Select the **Counts** tab. The Counts grid is displayed.
3.  In the grid, select the check box next to the counts to reset.
4.  From the **Action** drop-down list, select **Reset** **Count**. A confirmation message is displayed.
5.  Click **OK**.

## Reopen a count

You can reopen counts that are in the Completed or In Progress status to restart and complete the count work. When you reopen a count, the count is released to be completed again.

1.  Select **Inventory > Counts > Scheduled**.
2.  Select the **Counts** tab. The Counts grid is displayed.
3.  In the grid, select the check box next to the counts to cancel.
4.  From the **Action** drop-down list, select **Reopen** **Count**. A confirmation message is displayed.
5.  Click **OK**.

## Edit a batch

When you edit a batch, the existing Scheduled locations (counts) are displayed on the Criteria page. You can enter new criteria to add new counts or update only the Schedule details. You can update the count type, request type, schedule date and time on the Schedule page.

1.  Select **Inventory > Counts > Scheduled**.
2.  Select the **Batches** tab. The Batches grid is displayed.
3.  In the grid, select the batch row to edit.
4.  From the **Actions** drop-down list, select **Edit Batch**. The Edit Batch page is displayed.
5.  Enter the criteria in the [Scheduled Counts fields](#Schedule_Counts_fields).
6.  Click **Find Locations**. The locations that contain inventory matching the selected attributes are displayed.
7.  Click **Next**.
8.  Enter information in the [Schedule fields](#Schedule_fields).
9.  Click **Save** to schedule the count or click **Save and Release** to release the count. A confirmation message is displayed.
10.  Click **OK**.

## Complete a batch

Completing a batch is a daily task that is performed after counts are released and the actual counting work has been performed. Completing a batch releases the location from the Locked status, and restores it to the status it was in before it was locked. When the batch is completed, the application generates a count history and, if appropriate, sends transactions to the host. A batch can be completed only when all the counts in that batch are either completed or cancelled. The completion percentage is displayed as a progress bar for the batches in the Batches grid. The completion percentage is 100% when all counts in that batch are either completed or cancelled.

1.  Select **Inventory > Counts > Scheduled.**
2.  Select the **Batches** tab. The Batches grid is displayed.
3.  In the grid, select the batch to complete.
4.  From the **Actions** drop-down list, select **Complete Batch**. A confirmation message is displayed.
5.  Click **OK**.

## Add count to a batch

Add count is similar to schedule count. You can add one or more counts to an existing batch, and modify the schedule fields from the Batch view. Count requests for the newly added counts will be created based on the schedule defined for the batch.

1.  Select **Inventory > Counts > ** **Scheduled**.
2.  Select the **Batches** tab. The Batches grid is displayed.
3.  In the grid, click the batch to open the Batch view. The status of counts at each of the locations in the count batch is displayed.
4.  From the **Actions** drop-down list, select **Add Count**. The Add Count page is displayed.
5.  Enter the criteria in the [Scheduled Counts fields](#Schedule_Counts_fields).
6.  Click **Find Locations**. The locations that contain inventory matching the selected attributes are displayed.
7.  Click **Next**.
8.  Enter information in the [Schedule fields](#Schedule_fields).
9.  Click **Save** to schedule the count or click **Save and Release** to release the count. A confirmation message is displayed.
10.  Click **OK**.

## Manage count work

Released counts are added to the work queue with a unique work ID. You can open the work queue for the count by clicking the work ID to perform additional work queue operations. You can also perform the following work queue operations from the Counts tab.

1.  Select **Inventory > Counts > Scheduled**.
2.  Select the **Counts** tab. The Counts grid is displayed.
3.  To suspend directed work:
    1.  In the grid, select the check box next to the count to suspend work.
    2.  From the **Actions** drop-down list, select **Suspend Work**. A confirmation message is displayed.
    3.  Click **OK**. The work status is changed to Suspended.
4.  To resume suspended directed work:
    1.  In the grid, select the check box next to the count to resume work.
    2.  From the **Actions** drop-down list, select **Resume Work**. A confirmation message is displayed.
    3.  Click **OK**. The work status is changed to Pending.
5.  To cancel directed work:
    
    **Note**: When you cancel the directed work for a count, the work remains in the queue as undirected work.
    
    1.  In the grid, select the check box next to the count to cancel work.
    2.  From the **Actions** drop-down list, select **Cancel Work**. A confirmation message is displayed.
    3.  Click **Yes**. The work status is cleared.
6.  To assign directed work to a specific user:
    
    **Note**: If the work is already assigned to a user role, this operation overrides it and assigns it to the selected user.
    
    1.  In the grid, select the check box next to the count to assign work.
    2.  From the **Actions** drop-down list, select **Assign User**.
    3.  In the **Assign User** grid, select a user. If a user is currently logged into a workstation or device, a check mark is displayed in the **Logged In** column for the user.
    4.  Click **Select**. A confirmation message is displayed.
    5.  Click **OK**.
7.  To change the priority of work:
    
    **Note**: The value for Priority is green if the value is higher than the base priority defined for the work operation. The base priority represents the priority at which work enters the work queue. Priority can be escalated manually by a user or automatically by the application. See [Priority escalation processes](../../configuration/work/work/work-operations.md).
    
    1.  In the grid, select the check box next to the count to change work priority.
    2.  From the **Actions** drop-down list, select **Change Priority**.
    3.  Under **Enter Priority Level**, enter a value in the text box.
    4.  Click **Save**.

## Enter paper-based count results

When you enter count results you identify the following information, depending on the count:

-   For summary counts, identify the item, quantity, and unit of measure that was counted, in addition to any count attributes configured in the count settings
-   For LPN counts, identify the LPNs that were counted

If discrepancies occur, a secondary count (such as an audit count) may be generated, depending on how the count type is configured. See [Perform a paper-based audit count](#Perform_a_paper_based_audit_count).

1.  Select **Inventory > Counts > Count Entry**.
2.  In the grid, select the row for the location for which to enter count results, and then click **Perform Count Entry**.
3.  If items are displayed, perform a summary count:
    
    **Note**: If the **Expected Quantity** field for the count zone of a location is set to Yes, then the item quantities are displayed.
    
    1.  To add an unexpected item to a location:
        1.  Click **Add**.
        2.  In the **Item** field, enter the item that you counted.
        3.  In the **Quantity** field, enter the quantity of the item that you counted.
        4.  From the **UOM** drop-down list, select the unit of measure that you counted, such as Case. The total each quantity is calculated and displayed.
            
            **Note**: You can enter a quantity and UOM multiple times instead of calculating the total number of eaches in the location. For example, if you see 3 cases (that contain 10 eaches) and a partial case with 7 eaches, you can count the 3 cases and then count the 7 eaches instead of calculating and entering 37 eaches. To accomplish this, you have to add two records, one for each UOM.
            
        5.  To enter a catch quantity, in the **Catch Quantity** field, enter the total catch quantity for the item that you counted.
        6.  Click **Save**.
        7.  If the information you entered does not match the inventory records but a retry is allowed, then when prompted, click **Yes** and re-enter the quantity, or click **No** to accept the value that does not match.
            
            **Note**: If the quantity does not match, then depending on how the count type is configured, the application may automatically schedule a secondary count, such as a recount or audit count, for the location.
            
        8.  Repeat for each item counted in the location.
    2.  To modify an item count in the location:
        1.  Select the row for the item, and then click **Modify**.
        2.  Modify the inventory details as necessary, and then click **Save**.
    3.  To delete an item count from the location, select the row for the item, and then click **Delete**.
4.  To perform a count by LPN:
    1.  Click **Add**.
    2.  In the **Inventory ID** field, enter the LPN to be counted, and then click **OK**.
    3.  If the information you entered does not match the inventory records but a retry is allowed, then when prompted, click **Yes** and re-enter the LPN, or click **No** to accept the value that does not match.
        
        **Note**: If an invalid identifier is entered, then depending on how the count type is configured, the application may automatically schedule a secondary count, such as a recount or audit count, for the location.
        
    4.  To remove an LPN from the count results, select the check box next to the LPN, and then click **Delete**.
5.  When you have entered or confirmed all of the counts for the location, click **Complete Count**.
6.  If the location is empty, and you did not add any inventory to the count results, then when a message is displayed asking you to confirm the empty location, click **Yes**.
7.  When a message is displayed stating that the location will be reset and asks if you are done counting the location, click **Yes**. A confirmation message is displayed.
8.  Click **OK**.

## Perform a paper-based audit count 

1.  Select **Inventory > Counts > Audit Counts**.
2.  In the grid, select the row for the audit count location, and then click **Perform Count Audit**. The expected inventory details for the location are displayed.
3.  To add inventory to the audit count location: 
    
    **Note**: You can add inventory that is unidentified or identified and not expected in the location.
    
    1.  From the **Actions** drop-down list, select **Add Inventory**. The Add Inventory window is displayed.
    2.  Enter information in the [Add Inventory fields](../../shared-functions/inventory/procedures-for-lpns.md).
    3.  Click **Next**.
    
    **Note**: If serial number or catch quantity capture is not required for the item, and if the item is tracked at the LPN level and you are entering a quantity of 1, then the application processes the inventory. If you did not enter an LPN, an identifier is automatically generated.
    
    5.  If the Number Capture window is displayed, perform the following tasks:
        1.  Under **Quantity**, perform one of the following tasks:
            -   To automatically generate the identifiers, click **Generate LPNs**.
            -   To enter a range of identifiers, click **Enter a range**, then enter a starting and ending value, and then press **Tab**.
            -   To enter individual identifiers, in the text box, enter the first identifier and then press **Enter**. Repeat this process until you have entered the required number of identifiers.
        2.  If the inventory is serialized and requires serial number capturing, then under **Serial Numbers**, enter a serial number for each LPN that requires it.
        
        **Note**: To enter a range of serial numbers, click **Enter Range**, then enter the range of numbers to apply to the inventory, and then press **Tab**.
        
        4.  If the inventory is catch tracked and requires a catch quantity, under **Catch Quantity**, enter a value for each LPN that requires it.
        5.  Click **Finish**.
4.  To remove inventory from the audit count location:
    
    **Note**: When you remove inventory, it is deleted from the application and not available for use in the warehouse.
    
    1.  In the grid, select the row for the LPN.
    2.  From the **Actions** drop-down list, select **Remove Inventory**. The Remove Inventory window is displayed.
    3.  Enter information in the [Remove Inventory fields](../../shared-functions/inventory/procedures-for-lpns.md).
    4.  Click **Save**.
5.  To adjust inventory quantity in the audit count location:
    1.  In the grid, select the row for the LPN.
    2.  From the **Actions** drop-down list, select **Adjust Inventory**.
    3.  Enter information in the [Adjust Inventory fields](../../shared-functions/inventory/procedures-for-lpns.md).
    4.  Click **Finish**.
6.  When you are finished entering or confirming audit count results, click **Complete Count**. The location is reset to the status it was in prior to the initial count.
    
    **Note**: The location remains in a locked status if there is a pending inventory adjustment approval.
    
7.  If the adjustment transactions are not automatically sent to the host, then to manually send transactions, see [Send or delete inventory adjustment transactions](../adjustments.md).

## View audit counts and print a count sheet

If an audit count is generated as a result of discrepancies that occurred during counting, then you can view the list of pending audit counts and print the sheets to be used for a paper-based audit count.

**Note**: Pending audit counts are displayed if the release rule for the audit count is configured to produce an audit sheet. If the release rule is configured to create directed work, then the audit count work is sent to the work queue and an audit count sheet is not listed on the Audit Counts page.

1.  Select **Inventory > Counts > Audit Counts**.  
2.  View the information in the Audit Count fields.
3.  To print an audit count sheet, in the grid, select the row for the audit count, and then click **Print Audit Sheet**.
4.  From the **Printer** drop-down list, select the printer, and then enter the number of copies.
5.  Click **Print**.

## View count history

You can view the details of counts and batches that have been completed. When a count or batch is completed, the application generates a count history and, if configured to do so, sends transactions for any adjustments that resulted from the counting process to the host.

1.  Select **Inventory > Counts > History**.
2.  To view the count history, select the **Counts** tab. The Counts grid is displayed. View the information in the [Counts History fields](#Counts_History_fields).
3.  To view the batch history:
    1.  Select the **Batches** tab. The Batches grid is displayed. View the information in the [Batches History fields](#Batches_History_fields).
    2.  To view the details of a count batch, in the grid, click the count batch. The status of counts at each of the locations in the count batch is displayed.

## Add or modify a count template

1.  Select **Inventory > Counts > Templates**.
2.  Perform one of the following tasks:
    -   To add a template, click **Add**.
    -   To modify a template, in the grid, click the template.
    -   To copy a template, in the grid, select the check box next to the template, and then click **Copy**.
3.  Enter information in the [Template fields](#Template_fields).
4.  Click **Save**.

## Delete a count template

1.  Select **Inventory > Counts > Templates**.
2.  In the grid, select the check box next to the template to delete.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Counts field listings

### Schedule Count Criteria fields

 
| Field | Description |
| --- | --- |
| Template | A reusable configuration that defines a cycle count based on location, item, or inventory attributes. See [Count templates](../counts.md). |
| Request Count By | Method by which you want to request the cycle count. This value determines which fields are required for the count.<br>-   • **Client ID**: In a 3PL environment, requires a defined client.
<br>-   • **Item**: Requires a defined item.
<br>-   • **Location**: Requires either a beginning or an end location.
<br>-   • **Location and Client ID**: Requires a defined location and in a 3PL environment, requires a defined client.
<br>-   • **Location and Item**: Requires a defined location and an item number.
<br>-   • **Location Range**: Requires a beginning and an end location. |
| Starting Location | Identifier for the first location in the location range. |
| Ending Location | Identifier for the last location in the location range. |
| Aisle | Identifier for a passageway in the facility where operators and equipment move between racks or blocks of locations, typically to put away or pick inventory. You typically define aisles and then, in the process of defining storage locations, you can assign locations to the aisle in which they are located (a single location can be assigned to only one aisle). |
| Count Zone | Name of a count zone. A count zone is a method of grouping locations for an inventory count. You may want to group locations into a count zone based on the type of counts that take place (RF or paper-based) and how counts are generated (manually or automatically). |
| Client | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Pick Zone | Name of a pick zone. A pick zone represents a group of locations that share the same attributes for picking, such as the LPN level at which picks can be allocated, the cartonization group to which it belongs, and whether the location supports replacement picks and pre-inventory allocation. The search path searches pick zones when attempting to find inventory for allocation. |
| Work Zone | Name or number that identifies a work zone. A work zone is a logical division of warehouse space made on the basis of physical layout and access by different types of warehouse equipment. A work zone exists inside a work area. |
| Location Status | Current status of a location: Full, Partially Full, Empty, Inventory Error, or Locked. |
| Location Velocity | Identifies the speed at which inventory stored in a location moves in and out of the warehouse. Velocity is used to optimize warehouse space and inventory handling by placing fast moving items in the best locations for quick picking, and slower moving items in the less accessible storage locations. The application accomplishes this by attempting to match the velocity of the item with the velocity of the location when finding a location for storing the item. |
| Department | Identifier for a department within the customer's facility. A department can be specified for a customer type, customer, order, order line, distribution, and item. It can be used to group information for the purpose of sorting and searching data, consolidating distribution inventory in customer-specific storage locations, and to help customers direct inventory to the proper department when it arrives at their facility. |
| Item Family | Identifier used to group similar items together. Typically, all of the items within a family have the same material handling characteristics. |
| Inventory Status | Value that defines the quality or disposition of the inventory. |
| Lot | Identifier assigned to a quantity of inventory that is uniquely identified during the manufacturing process for the purpose of tracking an attribute of that inventory. |
| Country of Origin | Identifier assigned to an item to identify the item's country of origin. It is typically used for export paperwork. |
| Revision | Identifier that is assigned to an item number to differentiate revisions of the same item number. |
| Item Velocity | Identifies the speed at which inventory stored in a location moves in and out of the warehouse. Velocity is used to optimize warehouse space and inventory handling by placing fast moving items in the best locations for quick picking, and slower moving items in the less accessible storage locations. The application accomplishes this by attempting to match the velocity of the item with the velocity of the location when finding a location for storing the item. |
| Hold Type | The hold type that identifies the purpose of the hold. |
| Hold Reason | Value that indicates why the hold was applied. |
| Manufacturing Date | Date on which the inventory to be included in the count was manufactured. The date is stored in the database and displayed in the web client in the original captured time zone, not converted to a different time zone, such as a user preferred time zone. This date is the basis for date calculations (such as for aging and shelf life) that the application performs for date-tracked items. For example, this date can be used for first in, first out (FIFO) order processing. |
| Expiration Date | Date on which the inventory will expire. The expiration date is determined by the aging profile or shelf life assigned to the item configuration. The date is stored in the database and displayed in the web client in the original captured time zone, not converted to a different time zone, such as a user preferred time zone. |

### Schedule fields

 
| Field | Description |
| --- | --- |
| Batch | Batch identifier for the counts. See [Count batches](../counts.md). |
| Count Type | Name of a type of inventory count. The attributes of a count type determine how the application processes the count. |
| Request Type | Type of count request.<br>-   • **Inventory Error**: Based on the status of the location being in error.
<br>-   • **Pick to Zero**: Based on a location being picked to a zero quantity.
<br>-   • **User Generated**: Manually requested by a user. |
| Scheduled Date | The date and time at which the count is scheduled to be performed. |
| Save as Template | If Yes, displays the fields to save the schedule count criteria as a template.<br > If No, hides the template fields. |

### Template fields

 
| Field | Description |
| --- | --- |
| Template | Identifier for a count template. A count template is a reusable configuration that defines a cycle count based on location, item, or inventory attributes. |
| Count Type | Name of a type of inventory count. The attributes of a count type determine how the application processes the count. |
| Job Enabled | If Yes, enables the scheduled job settings for the template. The scheduled job determines when and how often the template is processed to create count requests for the defined locations and inventory.<br > If No, disables the scheduled job settings for the template. If this field is set to No, counts are not automatically generated for the template. |
| Job Type | Determines the intervals at which the job is processed for the template.<br>-   • **Timer based**: Indicates that this job will run at set intervals in seconds. When you select this option, the **Seconds** field is displayed.
<br>-   • **Schedule based**: Indicates that this job will run at intervals defined by a recurring schedule (cron expression). When you select this option, the **Schedule based** field is displayed. |
| Seconds | Time in seconds for a timer-based job. For example, if you enter 600, then the job will run every 10 minutes. Only displayed when you select the **Timer based** job type. |
| Schedule based | Quartz-style schedule expression, which is a string of six or seven fields separated by spaces. The fields indicate when a job will run. For example, the expression, 0 15 10 L \* ? , indicates that a job will run at 10:15 A.M. on the last day of every month. Only displayed when you select the **Schedule based** job type.<br > **Note**: You can define the count template schedule using the **Cron Builder**. You define the schedule expression by selecting the values in the **Minutes**, **Hours**, **Day of Month**, **Month**, **Day of Week**, and **Year** tabs. The application generates a schedule expression based on the inputs provided in the Cron Builder.<br > **Allowed Values**:<br>-   • Seconds: 0-59 and \* / , -
<br>-   • Minutes: 0-59 and \* / , -
<br>-   • Hours: 0-23 and \* / , -
<br>-   • Day of Month: 1-31 and \* / , - ? L W C
<br>-   • Month: 1-12 or JAN-DEC and \* / , -
<br>-   • Day of Week: 1-7 or SUN-SAT and \* / , - ? L C #
<br>-   • Year (Optional): 1970-2099 and \* / , -
<br > **Special Characters**:<br>-   •
    
    \[\*\] - Expression will match all values
    
    <br>
    
    Example: "\* \* \* \* \* ? 2010" - Execute every second in the year 2010
    
    <br>
<br>-   •
    
    \[/\] - Used to describe increments
    
    <br>
    
    Example: "10/15 \* \* \* \* ?" - Execute every 15 seconds starting at 10 seconds
    
    <br>
<br>-   •
    
    \[,\] - Used to separate items in a list
    
    <br>
    
    Example: "0 0 0 1,15 \* ?" - Execute every 1st and 15th of the month at midnight
    
    <br>
<br>-   •
    
    \[-\] - Used to define a range
    
    <br>
    
    Example: "0 0 0 ? \* MON-WED" - Execute at midnight Monday through Wednesday
    
    <br>
<br>-   •
    
    \[?\] - Used to omit specification for day of week or month
    
    <br>
    
    Example: "0 0 0 1 \* ?" - Execute at midnight on the first of the month regardless of day of week
    
    <br>
<br>-   •
    
    \[L\] - Stands for "last"
    
    <br>
    
    Example: "0 0 0 L \* ?" - Execute at midnight on the last day of the month
    
    <br>
    
    "0 0 0 ? \* 6L" - Execute at midnight on the last Friday of the month
    
    <br>
<br>-   •
    
    \[#\] - Used to specify the occurrence of a day in a month
    
    <br>
    
    Example: "0 0 0 ? \* SUN#3" - Execute on the third Sunday of the month at midnight
    
    <br>
<br>-   •
    
    \[W\] - Denotes the nearest weekday
    
    <br>
    
    Example: "0 0 0 15W \* ?" - Execute on the weekday nearest to the 15th at midnight
    
    <br>
    
    "0 0 0 LW \* ?" - Execute on the weekday nearest to the end of the month at midnight
    
    <br> |
| Release Automatically | If Yes, then when the template is processed, the count requests will be created and released automatically.<br > If No, then when the template is processed, count requests will be created, but must be released manually to perform the count work (that is, to the work queue or to printed count sheets). |

### Scheduled Counts fields

 
| Field | Description |
| --- | --- |
| Count Status | Status of the scheduled count.<br>-   • **Scheduled**: The count has been scheduled.
<br>-   • **Released**: The scheduled count has been has been released to the work queue or count sheets have been printed.
<br>-   • **Generated**: The count is generated.
<br>-   • **In Process**: The count work has been acknowledged by a user but has not been completed.
<br>-   • **Deferred**: The count has been generated, but is deferred until the pick or storage activity pending to the location is completed.
<br>-   • **Cancelled**: The count work has been deleted from the work queue.
<br>-   • **Completed**: The counts have been performed and completed. |
| Count Type | Name of a type of inventory count. The attributes of a count type determine how the application processes the count. |
| Location | Location at which the inventory count took place. |
| Work ID | Unique application-assigned identifier for a piece of work in the work queue. |
| Work Status | Current status of the work.<br>-   • **Undirected**: The work is undirected; this means that a user can perform it from a workstation, or an RF operator can perform it using an undirected work menu option. Undirected work is not available to be performed through the RF Directed Work menu option.
<br>-   • **Pending**: The directed work has been allocated and released to the queue. Work in this status will be offered to an operator through the RF Directed Work function, based on permissions, priority, and proximity.
<br>-   • **Waiting**: The directed work is assigned to an operator, but the operator has not acknowledged it yet.
<br>-   • **Acknowledged**: The directed work has been acknowledged (accepted) by an operator.
<br>-   • **Suspended**: The directed work is temporarily suspended, indicating that the application will not offer it an operator through the RF Directed Work function.
<br>-   • **Locked**: The directed work is locked and is not released until the application finds an available pickface location. This status is used with the demand replenishment operation (PIARPL) to prevent work from being released until there is room in the location for the replenishment inventory. |
| Operation | Work operation that identifies the type of directed work that was created to perform the count. |
| Priority | Number that represents the priority of the count work in the work queue. Priority is defined for a work operation and represents the position of the count work in the work queue in relation to work of other priorities. A value of "1" is the highest priority. |
| User | User who performed the count. |
| Item | Item that was counted. |
| Original Quantity | Quantity of the item that the application expected in the location prior to the count taking place. |
| Request Type | Type of count request.<br>-   • **Inventory Error**: Based on the status of the location being in error.
<br>-   • **Pick to Zero**: Based on a location being picked to a zero quantity.
<br>-   • **User Generated**: Manually requested by a user. |
| Generation Code | Code that identifies how a cycle count was generated.<br>-   • **INV**: Count is generated by item. The user has selected an item from an application-generated list of counts.
<br>-   • **LST**: Count is generated by location. The user has selected a location or range of locations from an application-generated list of counts.
<br>-   • **CLI**: Count is generated by client. The user has selected a client from an application-generated list of counts.
<br>-   • **MAN**: Manually requested count, which is generated manually by a user. The count mode depends on what attribute was entered on the request. If an item was entered, the count mode is by item; if a location was entered, the count mode is by location; if an item and location were entered, the count mode is none; if an inventory identifier (such as an LPN, sub-LPN, or detail LPN) was entered, the count mode is by inventory identifier; if an item client was entered, the count mode is by client.
<br>-   • **PHY**: Physical inventory count, which generates cycle counts for every location type in the facility configured as four-wall inventory.
<br>-   • **INL**: Count near zero count, which is generated when the quantity in a location falls below a specified threshold during RF picking.
<br>-   • **CTB**: Count back count, which is generated (if enabled) when an operator picks inventory from a location. |
| Count Quantity | Quantity of the item that was counted. |
| Batch | Batch identifier for the counts. See [Count batches](../counts.md). |
| Group | Identifier for a group of counts. |
| Display Original Quantity | Quantity of the item that the application expected in the location prior to the count taking place. |
| Display Count Quantity | Quantity of the item that was counted. |
| Inventory Identifiers | Unique inventory identifier, such as an LPN or case identifier. |

### Scheduled Batches fields

 
| Field | Description |
| --- | --- |
| Batch Status | The status of the batches based on the count statuses:<br>-   • **Released**: All counts in the batch are in a Released status or contains counts in a combination of Released, Cancelled, In Progress, or Completed statuses.
<br>-   • **Partially Released**: One or more of the counts are in a Scheduled status.
<br>-   • **Cancelled**: All counts are in a Cancelled status.
<br>-   • **Scheduled**: All counts are in a Scheduled status. |
| Batch | Batch identifier for the counts. See [Count batches](../counts.md). |
| Locations | Number of locations that are included in the count work. |
| Items | Number of items that are included in the count work. |
| Count Type | Name of a type of inventory count. The attributes of a count type determine how the application processes the count. |
| Completed | A progress bar that displays the completion percentage of the batch. The completion percentage is 100% when all counts in that batch are either completed or cancelled. |
| Inaccurate | Number of completed counts that resulted in a discrepancy between the original (expected) quantity and the count quantity. |

### Counts History fields

 
| Field | Description |
| --- | --- |
| Completed Date | Date on which the count was performed. |
| Location | Location at which the inventory count took place. |
| Count Type | Name of a type of inventory count. The attributes of a count type determine how the application processes the count. |
| User | User who performed the count. |
| Item | Item that was counted. |
| Original Quantity | Quantity of the item that the application expected in the location prior to the count taking place. |
| Count Quantity | Quantity of the item that was counted. |
| Display Original Quantity | Quantity of the item that the application expected in the location prior to the count taking place. |
| Display Count Quantity | Quantity of the item that was counted. |
| Discrepancy | The difference between the Original Quantity and Count Quantity. |
| Generation Code | Code that identifies how a cycle count was generated.<br>-   • **INV**: Count is generated by item. The user has selected an item from an application-generated list of counts.
<br>-   • **LST**: Count is generated by location. The user has selected a location or range of locations from an application-generated list of counts.
<br>-   • **CLI**: Count is generated by client. The user has selected a client from an application-generated list of counts.
<br>-   • **MAN**: Manually requested count, which is generated manually by a user. The count mode depends on what attribute was entered on the request. If an item was entered, the count mode is by item; if a location was entered, the count mode is by location; if an item and location were entered, the count mode is none; if an inventory identifier (such as an LPN, sub-LPN, or detail LPN) was entered, the count mode is by inventory identifier; if an item client was entered, the count mode is by client.
<br>-   • **PHY**: Physical inventory count, which generates cycle counts for every location type in the facility configured as four-wall inventory.
<br>-   • **INL**: Count near zero count, which is generated when the quantity in a location falls below a specified threshold during RF picking.
<br>-   • **CTB**: Count back count, which is generated (if enabled) when an operator picks inventory from a location. |
| Batch | Batch identifier for the counts. See [Count batches](../counts.md). |
| Inventory Identifiers | Unique inventory identifier, such as an LPN or case identifier. |

### Batches History fields

 
| Field | Description |
| --- | --- |
| Completed Date | Date on which the count was performed. |
| Batch | Batch identifier for the counts. See [Count batches](../counts.md). |
| Locations | Number of locations that are included in the count work. |
| Items | Number of items that are included in the count work. |
| Count Type | Name of a type of inventory count. The attributes of a count type determine how the application processes the count. |
| Inaccurate | Number of completed counts that resulted in a discrepancy between the original (expected) quantity and the count quantity. The value of the discrepancy is displayed in the Gain/Loss column. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2023 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
