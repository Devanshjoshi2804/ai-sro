---
title: "Counts"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/counts.htm"
source: "/content/counts.htm"
toc_path:
  - "Warehouse Management"
  - "Inventory"
  - "Counts"
sections:
  - "Scheduled counts"
  - "Automated ABC counts"
  - "Count batches"
  - "Count templates"
  - "Count and batch status"
images: []
source_sha1: d3c7559e39c3363cad26e9c3ad8028c03180f795
---
# Counts

You use the Counts page to view information on the following tabs:

-   **Scheduled**: Individual counts and batches of counts that have been scheduled or released. When you view scheduled counts, you can perform the following tasks:
    
    -   Schedule additional counts by requesting counts and specifying the date on which they should be performed.
    -   Edit a count batch or add a count to a count batch.
    -   Release counts or count batches so that count work is added to the work queue or count sheets are printed (depending on the count release process).
    -   Cancel counts or count batches that have been released. Cancelling a count deletes the count work from the work queue.
    -   Reset cancelled counts to release count work.
    -   Reopen counts that are completed or in process.
    -   Remove scheduled counts.
    -   Suspend released counts to temporarily prevent count work from being performed.
    -   Resume suspended counts to complete count work.
    -   Cancel a count work, assign a different user, or change work priority.
    -   Complete count batches that have been performed. Completing a count releases a location from a Locked status, and restores it to the status it was in when the original count was scheduled. Completing a count also makes counting information available for count history reports.<br>
    
    See [Procedures for counts](counts/procedures-for-counts.md).
    
-   **Templates**: Reusable configurations that define a cycle count based on attributes such as item, location, range of locations, client (for a 3PL environment), hold type, and inventory status. A template is associated with a schedule that defines how often counts are scheduled or released for the locations or inventory that matches the attributes defined for the count template.
-   **Count Entry**: In-process paper-based cycle counts for which you can enter count results. Depending on whether you are entering summary count or LPN count results, you identify the item and quantity information, along with any other selected count attributes, or the LPNs that were counted. If discrepancies occur, a secondary count (such as an audit count) may be generated, depending on how the count type is configured.
    
    **Note**: If the **Detail Count** field for the count type is set to Yes, then paper-based cycle counts are displayed on the Audit Count page instead of the Count Entry page.
    
-   **Audit Count**: Pending paper-based audit counts. If an audit count is generated as a result of discrepancies that occurred during counting, then an authorized user at a workstation can view the list of pending audit counts and print the sheets to be used for a paper-based audit count.
-   **History**: Counts and batches of counts that have been performed and completed within your facility. This information helps you determine when a count was performed, the quantity counted, the storage location affected, and the user who performed the count.

## Scheduled counts

The application enables you to schedule or release counts by item, location, or range of locations. In a 3PL facility, you can also manually schedule or release counts for a specific client. Counts are scheduled by finding locations based on certain criteria using location, item or inventory attributes and selecting the count type, request type, and scheduled date. You can also schedule ABC counts.

Counts can be scheduled or released manually or automatically (using [templates](#Count_templates)).

## Automated ABC counts

In ABC counting, the application uses the ABC codes and the ABC counting configuration to automatically schedule cycle counts by item, location or client. Items or locations are identified with A, B, or C codes based on factors such as the nature of the items, location movements, and item expense. You assign the counting frequency to ABC codes to determine how many times an item or a location must be counted within the count period. The application then automatically schedules the counts, and a background job (if enabled) automatically releases ABC counts on the count day. The job (maintained in the Console, under Jobs) is disabled by default and has configurable parameters such as Count Type, Release flag, Number of days to look ahead, and Warehouse ID. Based on the configured parameters, the application schedules or releases ABC counts into separate batches by Item, Item and Supplier, Client, and Location and Count Zone. The counts are displayed on the Counts page, and the ABC counts statistics are displayed on the [Inventory Dashboard](dashboard.md).

The format of an application-generated batch number is ABC-MMDDYYYYTTTTTTTT-x, where MMDDYYYYTTTTTTTT is the date and time when the ABC count was scheduled and x is the application-generated sequence.

You can enable ABC counting and configure the counting frequency for ABC codes in the count settings. See [Configure count settings](../configuration/inventory/counting/count-settings.md).

If you select to count by item (or item and supplier), then the application may ignore the daily quota for counts. The daily quota is derived from the number of locations eligible for counting divided by the number of days in the count cycle. For example, if there are 10 locations to be counted in a count period of 5 days, the daily quota is 2. When an item exists across multiple locations, the application creates and releases as many counts as needed to complete the total item count across all locations on the same day. The application processes counting by item this way so that a complete and accurate count for an item does not span multiple days, and any discrepancies with the item can be resolved sooner. For example, if a single item exists in 10 locations and the count period is 5 days, then the daily quota is 2. However, since the count is by item, the application releases all 10 counts on the same day rather than 2 per day for the duration of the count period.

**Note**: The ability to schedule ABC counts by item and supplier is currently not supported.

## Count batches

A count batch is a set of counts that are scheduled or released together. For example, you may want to batch counts for the purpose of assigning the batch to a single operator to perform the count. Alternatively, you could batch counts by aisle, so that work is performed and completed in one aisle at a time.

Every count that you schedule is associated with a batch identifier. You can manually enter a batch identifier when scheduling counts. If a batch identifier is not assigned, the application automatically assigns a unique batch identifier to every count.

## Count templates

A count template is a reusable configuration that defines a count based on location, item, and inventory attributes. The template can be associated with a schedule job that determines when and how often the template is processed. A count template can be used to automatically schedule and release counts using a background schedule job. Processing creates the count requests for the locations and inventory defined by the template.

For example, you can create one template to initiate counts for a hold type that is counted once every 24 hours, and another template to schedule counts for non-held inventory that is counted weekly. The application automatically creates a job (maintained in the Console) to process the count according to the template schedule.

## Count and batch status

Following is the list of count statuses:

-   **Scheduled**: The count has been scheduled, but cannot be performed because it is not yet released.
-   **Released**: The scheduled count has been released, such as to the work queue or printed count sheets, and count work can begin.
-   **Completed**: The count has been performed and completed.
-   **Generated**: The count has been generated.
-   **In Process**: The count work has begun.
-   **Deferred**: The count has been generated, but is deferred (held) until the pick or storage activity pending to the location is complete.
-   **Cancelled**: The count has been cancelled (removed from the work queue).

Following is the list of batch statuses:

-   **Released**: All counts in the batch are in a Released status or contains counts in a combination of Released, Cancelled, In Progress, or Completed statuses.
-   **Partially Released**: One or more of the counts are in a Scheduled status.
-   **Cancelled**: All counts are in a Cancelled status.
-   **Scheduled**: All counts are in a Scheduled status.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
