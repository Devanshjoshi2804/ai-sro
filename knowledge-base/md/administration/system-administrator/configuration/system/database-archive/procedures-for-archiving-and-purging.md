---
title: "Procedures for archiving and purging"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/admin/procedures_for_archiving_and_purging.htm"
source: "/content/admin/procedures_for_archiving_and_purging.htm"
toc_path:
  - "Administration"
  - "System Administrator"
  - "Configuration"
  - "System"
  - "Database Archive"
  - "Procedures for archiving and purging"
sections:
  - "Prerequisite tasks for remote archiving"
  - "Configure archiving attributes"
  - "Configure the jobs for archiving and purging"
  - "Test archives and purges"
  - "Standard Warehouse Management database archives"
images: []
source_sha1: 1ba73fd76ae7750301682941c8397b94f02b795d
---
# Procedures for archiving and purging

You can use the following archiving methods:

-   **Remote instance archive**: Archive remotely into an instance that is identical to the production instance. When you archive remotely, all SCE client-based custom data driven applications (DDAs) and reports, as well as all SCE client-based standard product DDAs and reports work without modification or duplication. Blue Yonder recommends archiving to a remote instance for an on-premises deployment.
-   **Local production instance archive**: When you archive locally, all production instance data that meets the customer-defined archiving criteria is moved to a set of duplicate tables in the same production instance. The duplicate tables must be manually created and have a prefix (such as ARC\_) to designate them as the archive tables.
    
    **IMPORTANT**: If you archive locally, any DDAs or reports that are used to retrieve data must be modified or duplicated to retrieve data from the ARC\_ tables. If you want to archive locally, be sure to discuss the implications with your Blue Yonder project team.
    
-   **DAAS archive**: There is no separately archived data as warehouse data is continuously synched with cloud storage (powered by Snowflake), eliminating the need for a separate archive. Data will continue to be purged from production using the archiving and purging jobs. This option is valid only for cloud customers configured to use Data Access Service and enhanced cloud storage.
    

## Prerequisite tasks for remote archiving

Before you configure remote archiving, complete the following prerequisite tasks in the order listed:

1.  **Install a new instance of your application to serve as the archive instance**.

This archive instance must be an exact copy of the production instance, including all reports, database changes, data driven applications (DDAs), and server commands. The archive instance must be maintained like the production instance so that existing product reports and DDAs can be used to gather data from the archive instance, and the archive instance is kept current with customizations and product updates.

3.  **Export the production database, and import it into the archive instance**.

This is done to ensure that all database changes in the production instance exist in the archive instance. This is a standard database administrator activity. If you need help with this procedure, contact your Blue Yonder project team.

5.  **Purge transaction data from the archive instance**.

This step is done to ensure that your archive instance is clear of all transaction data. If you need help with this procedure, contact your Blue Yonder project team.

## Configure archiving attributes

You use Policy Maintenance to configure archiving attributes.

**IMPORTANT**: To use any archiving method, you must enable archiving using the Archive system installed (ARCHIVE-SYSTEM/INSTALLED/INSTALLED) policy. See [Archive system policies](../../policy/archive-system-policies.md).

## Configure the jobs for archiving and purging

You use the Console to create or configure the jobs that are used to archive or purge data automatically on a regular basis. The schedule for each job determines when and how the job is executed. For information on maintaining and scheduling jobs, see the Supply Chain Execution Applications Console User Guide.

**IMPORTANT**: Some archiving, purging, and synchronization jobs are provided with the standard product. However, to avoid running unnecessary jobs, you should determine your requirements and then enable and configure only the required jobs.

You use the following process to configure jobs for archiving and purging:

1.  Log into the Console, and then access the Jobs page.
2.  Define and configure jobs. You can add jobs for each of the existing database archives, depending on your application requirements. You use the following command for jobs used to archive production data:
    
    archive production data where arc\_nam = '<_Name of Archive_>'
    
    For example: archive production data where arc\_nam = 'BILL-OF-MATERIALS'
    
    **Note**: Database archives are defined on the Database Archive page. See [Database Archive](../database-archive.md).
    
3.  Define a schedule for each job using the following guidelines:

-   Configure different jobs to be run each day so that an excessively large amount of data does not need to be archived and purged on any one day.
-   Configure the jobs to be run during off hours since archiving and purging can be a resource intensive process.
-   Stagger the start times of the jobs so that you can extend processing over a period of time. Archive and purge jobs can be configured to run in any order.

## Test archives and purges

You can perform tests on archive instances.

**Perform a simple archive and purge**

You can test the archive instance using a simple archive and purge.

**Note**: The procedure tests archiving and purging of the OBSOLETE-APPOINTMENT archive (APPT table) using a sysdate value of 30.

1.  In the archive instance, truncate the APPT table in the OBSOLETE-APPOINTMENT archive:
    1.  Start the SCE client and log in to the archive instance.
    2.  Start Server Command Operations.
    3.  In the command field, enter the command to truncate the table; for example: \[truncate table APPT\]
    4.  Click **Execute**.
2.  In the production instance, determine how many table rows to archive and purge:
    1.  Start the SCE client and log in to the production instance.
    2.  Start Server Command Operations.
    3.  In the command field, enter the command to display the number of table rows for a specific number of days; for example:
        
        \[select count( \* ) from appt where end\_dte < sysdate - 30\]
        
    4.  Click **Execute**. The number of rows is displayed.
    5.  To reduce the number of returned rows, rerun the command changing the sysdate (number of days) value until you reach a manageable number.
    6.  Record the number of rows returned and the sysdate value used.
3.  In the production instance, update and run the OBSOLETE-APPOINTMENT archive:
    1.  Start a web browser for the application's web-based functionality and log in to the instance.
    2.  Select **System Administrator > Configuration > System > Database Archive**.
    3.  Select the check box next to the OBSOLETE-APPOINTMENT archive, and then from the **Actions** drop-down list, select **Edit**.
    
    **Note**: The OBSOLETE-APPOINTMENT archive is configured to purge the data.
    
    5.  In the **List Command** field, locate and update the sysdate value.
    6.  Click Apply.
    7.  From the **Actions** drop-down list, select **Run Archive**. A message states that archiving could take considerable time.
    8.  Click **Yes**. Data is copied to the database archive.
4.  When the archive and purge is complete, in the archive instance, verify that the rows were archived:
    1.  In Server Command Operations, in the command field, enter the command to display the number of table rows; for example: \[select count( \* ) from appt\]
    2.  Click **Execute**. The number of rows should match the number previously recorded.
5.  In the production instance, verify that the rows were purged:
    1.  In Server Command Operations, in the command field, enter the command to find the rows using the same sysdate value passed to the list command from the production instance; for example:
        
        \[select count( \* ) from appt where trndte < sysdate - 30\]
        
    2.  Click **Execute**. No rows should be returned.
        
        **Note**: If rows are returned, verify that the date and time of the rows are outside the retention days defined.
        

**Perform a standard archive and purge**

You can test a standard product archive.

**Note**: The procedure tests the STDPRD-PARTS archive (PRTMST table).

1.  In the archive instance, determine the number of records in the PRTMST table:

1.  Start the SCE client and log in to the archive instance.
2.  Start Server Command Operations.
3.  In the command field, enter the command to find table records; for example:
    
    \[select count( \* ) from prtmst\]
    
4.  Click **Execute**.
5.  Record the number of returned records.

3.  In the production instance, add data and start the archive:

1.  In the web client, add a new item named TESTITEM. See [Add or modify an item](../../../../../warehouse-management/configuration/inventory/items/items.md).
2.  Select **System Administrator > Configuration > System > Database Archive.**
3.  In the grid, select the check box next to the STDPRD-PARTS archive, and the from the **Actions** drop-down list, click **Run Archive**. The archiving process begins and runs for a period of time based on the number of records being archived.

5.  When the archive is complete, in the archive instance, verify that the records were archived:

1.  In Server Command Operations, in the command field, enter the command to find table records; for example: \[select count( \* ) from prtmst\]
2.  Click **Execute**. The number of records returned should be one higher than the number recorded.
3.  Start a web browser for the application's web-based functionality and log in to the instance.
4.  Verify that TESTITEM exists in the archive instance.

**Perform a complex archive and purge**

You can test the archive instance using a complex archive and purge of multiple tables.

**Note**: The procedure tests archiving and purging of the DISPATCHED-TRAILERS archive (CAR\_MOVE table) using the 30 days old value.

1.  In the archive instance, identify the tables included in the archive:
    1.  In the web client, select **System Administrator > Configuration > System > Database Archive**.
    2.  In the grid, select the DISPATCHED-TRAILERS archive.
    3.  View the list of tables under **DATABASE ARCHIVE DETAILS**.
2.  In the archive instance, truncate all the tables in the DISPATCHED-TRAILERS archive:

1.  Start the SCE client, and log into the archive instance.
2.  Start Server Command Operations.
3.  In the command field, enter the commands to truncate the tables in the list; for example: \[truncate table TRLR\]
4.  Click **Execute**.

4.  In the production instance, determine how many table rows to archive:

1.  Start the SCE client, and log into the production instance.
2.  Start Server Command Operations.
3.  In the command field, enter a command to display the number of table rows; for example:
    
    \[select count(car\_move.car\_move\_id) from car\_move, trlr where car\_move.trlr\_id = trlr.trlr\_id and trlr.trlr\_cod = 'SHIP' and trlr.dispatch\_dte < sysdate - 30 and not exists (select 'x' from shipment, stop where shipment.stop\_id = stop.stop\_id and stop.car\_move\_id = car\_move.car\_move\_id and shipment.shpsts not in ('C','B'))\]
    
    **Note**: The command only returns loads that are completed and the date of completion is older than the sysdate value (number of days) specified in the command.
    
4.  Click **Execute**. The number of rows is displayed.
5.  To reduce the number of returned rows, rerun the command changing the sysdate value until you reach a manageable number.
6.  Record the number of returned rows and the sysdate value used.

6.  In the production instance, run the DISPATCHED\_TRAILERS archive:

1.  In Database Archive, in the grid select the check box next to the DISPATCHED-TRAILERS archive.
2.  From the **Actions** menu, select **Edit**.
3.  In the **List Command** field, and modify the list command for the DISPATCHED-TRAILERS archive to use the updated sysdate value.
4.  Select the **Purge** check box.
5.  Click **Apply**.
6.  From the **Actions** drop-down list, click **Run Archive**. The archiving process begins and runs for a period of time based on the number of rows being archived and purged.

8.  When the archive and purge is complete, in the archive instance, check that the rows were archived from the tables:

1.  In Server Command Operations, in the command field, enter the command to display the number of table rows; for example:\[select count( \* ) from car\_move\]
2.  Click **Execute**. The number of rows returned should match the number previously recorded.

10.  In the production instance, verify that the rows were purged:

1.  In Server Command Operations, in the command field, enter the command to find the rows using the same days old value passed to the list command from the production instance; for example: ﻿
    
    \[select count(car\_move.car\_move\_id) from car\_move, trlr where car\_move.trlr\_id = trlr.trlr\_id and trlr.trlr\_cod = 'SHIP' and not exists (select 'x' from shipment, stop where shipment.stop\_id = stop.stop\_id and stop.car\_move\_id = car\_move.car\_move\_id and shipment.shpsts not in ('C','B'))\]
    
2.  Click **Execute**. No rows should be returned.
    
    **Note**: If rows are returned, verify that the date and time of the rows are outside the retention days defined.
    

12.  Check additional tables to verify that rows exist in the archive instance and the rows were purged from the production instance.

## Standard Warehouse Management database archives

The following table describes the standard database archives distributed with Warehouse Management.

**Note**: You can view the tables associated with each archive and maintain database archive configurations using the Database Archive page. See [Database Archive](../database-archive.md).

 
| Archive name | Data included in archive |
| --- | --- |
| ADJUSTMENT-HISTORY | History of transaction information related to inventory adjustments, such as a status change and the reason for the change. |
| ARCHIVE-SYS-AUDITS | Security-related activities and changes made by users within a Blue Yonder product. |
| ASYNC-RESOURCE | Logical groups of asynchronous command executions. |
| BILL-OF-MATERIALS | Items that define a template for creating work orders. |
| BILL-TRAN | Billing transaction data for chargeable activities that is captured in Warehouse Management when integrated with an external billing system. |
| CANCELLED-ORDERS | Outbound orders that have been cancelled. |
| CANCELLED-SHIPMENTS | Shipments that have been cancelled. |
| CANCELLED-SHORTS | Orders and items that were allocated short and for which short allocation was cancelled. |
| CNFRM\_INV\_SERV | Inbound and outbound workflows that have been confirmed. |
| CNFRM-BCK-SERV | Background workflows that have been confirmed. |
| CNFRM-NONINV-SERV | Transport equipment, warehouse equipment, and assembly non-inventory workflows that have been confirmed. |
| DAILY-ACTIVITY | Activities tracked by just item. |
| DAILY-TRAN | Daily transactions that are recorded. |
| DEFERRED-EXEC | Command executions run outside of user processing. |
| DISPATCHED-RCV-TRUCK | Receiving transport equipment that has been dispatched. |
| DISPATCHED-STANDALONE-TRACTOR | Dispatched tractors that are not associated with transport equipment. |
| DISPATCHED-TRAILERS | Loads that have been dispatched. |
| DOM-CUSTOMERS | Customers that were added as a result of orders downloaded from a distributed order model (DOM) application. |
| INVENTORY-ACTIVITY | Activities recorded for inventory; for example inventory that was adjusted, shipped, received, consumed for a work order, or received from a work order. |
| INVENTORY-SNAPSHOT | Historical inventory snapshots that exist in the application. |
| LMS-ACTIVITY | Labor activities recorded for a user in a warehouse that is integrated with Warehouse Labor Management. |
| OBSOLETE-APPOINTMENT | Obsolete (unused or old) appointments that can be defined in the web client. |
| ORDER-ACTIVITY | Activity against an outbound order; for example, the addition and deletion of shipment and order lines, shipment allocation and loading, assignment of shipments to stops, and pick activity. |
| OUTBOUND-AUDIT-HISTORY | History of user entries recorded while performing RF outbound audits of picked inventory. |
| OUTBOUND-SERVICE-<br > ORDER | Workflow entries for outbound orders. |
| OUTBOUND-SERVICE-<br > ORDER-LINE | Workflow entries for outbound order lines. |
| PACKOUT-ACTIVITY | Pack station and outbound audit activity. |
| PICK-SUMMARY-BY-HOUR | Hourly pick summary information for pending (allocated) and completed pallet (LPN level), case (sub-LPN level), and quantity (other-UOMs) picks. |
| RCVTRK-WRKORDER-CLSD | Completed inbound shipment information related to closed work orders. |
| RECEIVING-HISTORY | History of inventory that was received, reverse received, including the state in which it was received before consolidation, inventory movement, adjustments, and so on. Includes inventory identifiers, attributes, order information, and other tracking information. |
| RETURNSPROCOPR-<br > ARCHIVE | Returns that have been processed. |
| SHIPPED-LPN-ACTIVITY | Shipped LPN activity logged or received by the application. |
| STDPRD-ADDRESSES | Addresses defined in the application. |
| STDPRD-AREAS | Areas defined in the application. |
| STDPRD-BILL-OF-<br > MATERIALS | Bills of materials (BOMs) defined in the application. |
| STDPRD-BUILDINGS | Buildings defined in the application. |
| STDPRD-CANCELED-RPL-PICKS | Cancelled picks for replenishments. |
| STDPRD-CANCELLED-<br > COUNTS | Cancelled counts. |
| STDPRD-CARRIERS | Carriers defined in the application. |
| STDPRD-CARTONS | Cartons defined in the application. |
| STDPRD-CNTZON | Count zones defined in the application. |
| STDPRD-COMMODITY | Commodities defined in the application. |
| STDPRD-COUNT-HISTORY | Details of counts that have been performed and completed within your facility. The history information tells you when a count was performed, the quantity counted, the storage location and the user who performed the count. |
| STDPRD-CUSTOMERS | Customers defined in the application. |
| STDPRD-DESCRIPTIONS | Descriptions for entries throughout the application; for example codes and order types. |
| STDPRD-DISTRO\_EXCP | Distribution exceptions that occur when excess inventory is left over after the completion of a distribution deposit process. |
| STDPRD-DSPTCHED-ORPHAN- TRLRS | Dispatched transport equipment that is not associated with an inbound shipment or outbound load. |
| STDPRD-EXCP\_HRS\_SET | Time frame on specific dates during which dock doors are available for scheduling. |
| STDPRD-FOOTPRINTS | Item footprints defined in the application. |
| STDPRD-GEODATA | Geographical location data. |
| STDPRD-HOLD-HISTORY | History of all inventory placed on or released from a specific hold. |
| STDPRD-HRS\_OPR\_SET | Time frame for a day of the week during which dock doors are available for scheduling. |
| STDPRD-INVENTORY-SERVICE | Inventory workflow results and affected inventory. |
| STDPRD-ITEM-VELOCITY | Item velocity information including item quantities that result from velocity type and item velocity policy settings. |
| STDPRD-LOC\_TYPE | Location type defined in the application. |
| STDPRD-LOCATIONS | Locations defined in the application. |
| STDPRD-LOTS | Lots defined in the application. |
| STDPRD-MANCNTCNTHST | Manual count history. |
| STDPRD-<br > MANCNTRFINVADJHST | Inventory adjustment history. |
| STDPRD-MOV\_ZONE | Movement zones defined in the application. |
| STDPRD-PARTS | Items defined in the application. |
| STDPRD-PCK\_ZONE | Pick zones defined in the application. |
| STDPRD-RECUR-SCHED | Recurring schedule entries with start and end date. |
| STDPRD-RIMSTS\_CLSD | Inbound shipments that have been closed. |
| STDPRD-SERVICE-INS-MST | Workflow instruction data. |
| STDPRD-SERVICE-MST | Warehouse workflow data. |
| STDPRD-SERVICE-RATE | Workflow sampling rate data. |
| STDPRD-STO\_ZONE | Storage zone locations and attributes. |
| STDPRD-SUPPLIERS | Supplier information. |
| STDPRD-TRNSP\_MODE | Transport modes define in the application. |
| STDPRD-USER\_RECOUNT | Cycle count recount entries. |
| STDPRD-WAREHOUSE | Warehouses defined in the application. |
| TEMP-ADDRESS | Temporary addresses defined in the application. |
| TEMP-CUSTOMER | Temporary customers defined in the application. |
| TRACTOR-ACTIVITY | Historical information related to tractor activity; for example tractors that have been created, checked in, changed, assigned and unassigned to transport equipment, and dispatched. |
| TRLR-ACTIVITY | Historical information related to transport equipment activity in your yard; for example transport equipment that has been created, checked in, changed, moved, audited, and renamed. |
| WCS-DISCREPANCY | Inventory discrepancies between the Warehouse Control System and Warehouse Management. |
| WORK-HISTORY | History of the work that has been handled by the work queue. This log gives you information about the type of work, the status of the work queue entry (such as pending, completed, or deleted), who acknowledged the work and who was the last user to modify the work queue entry. |
| WORK-ORDERS | Work orders defined in the application. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
