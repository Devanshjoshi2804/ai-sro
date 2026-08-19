---
title: "Database Archive"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/admin/database_archive.htm"
source: "/content/admin/database_archive.htm"
toc_path:
  - "Administration"
  - "System Administrator"
  - "Configuration"
  - "System"
  - "Database Archive"
sections:
  - "Archiving process"
  - "Simple and complex archiving"
  - "Add or modify a database archive"
  - "Delete a database archive"
  - "Database Archive fields"
  - "Database Archive (Details) fields"
images: []
source_sha1: b38d32d5516b1d15f55434dfae87992d52e17c18
---
# Database Archive

An application's database is typically designed for execution purposes rather than historical record keeping. To keep an application's execution tables lean for performance purposes, you can use database archiving functionality to save historical data in a database archive. For example, you may want to archive the following types of data:

-   Shipment information
-   Planned inbound order information
-   Daily transactions
-   Order activity

## Archiving process

The archiving process is performed in a two-step process that consists of archiving and purging.

1.  **Archiving**: The process by which a user-configurable amount of historical data is copied from a production instance to an archive instance for data reporting and historical purposes.
2.  **Purging**: The process of removing archived data from the production instance to keep production processing times at an optimal level.

**Notes**:

-   These archiving and purging processes manage application server instance (MOCA) database information only. REFS database information is not included in the archiving and purging process.
-   For cloud deployments that use Data Access Service and the cloud storage solution (powered by Snowflake), warehouse data is continuously synched with cloud storage, eliminating the need for a separate archive instance.

For example, you can configure the application to archive dispatched outbound loads every 30 days, and then purge that data from the production instance. In this way it is stored for historical purposes in the archive instance, and removed from the production instance.

Some configuration data is archived but not purged; instead, the archive process is used to update the data in the archive instance, but does not purge it from the production instance. This is called synchronizing the data.

For example, you can configure the application to archive supplier information every 30 days. This is done to synchronize the supplier data in the archive instance. Supplier data is not purged from the production instance because it is required on an ongoing basis for various warehouse operations.

Blue Yonder recommends the following archiving time intervals:

**Note**: These time intervals are recommendations only. You may need to reduce or expand the intervals depending on the volume of data in the production instance. The amount of data retained in the production instance, and the purge and archive schedule should be discussed and agreed upon by you and your Blue Yonder project team.

-   Data older than 30 days is archived
-   Integration transactions older than 7 days are archived

**IMPORTANT**: Blue Yonder project implementation methodology requires archiving and purging to be configured prior to a production instance going live. A project is not transitioned to Customer Support without this configuration.

## Simple and complex archiving

You can perform a simple or a complex database archive.

-   **Simple archive**: A simple archive is characterized by targeting the archival of a single table, such as the Daily Transaction table. The simple archive process, for this example, identifies aged daily transaction entries, archives those entries to the archive instance, and then removes the entries from the production database.
-   **Complex archive**: Complex archives consider a hierarchy of information to archive, determined by a driver table. Processing of a complex archive differs from a simple archive in that a List or Select command is used to find the list of entries from the driver table to process, then the archive details are used to process entries from related tables for each row of the driver table. In addition to the driver table schema, complex archives do not allow for the setting of the Purge, but require an additional purge component to actually remove the data from the production instance.

## Add or modify a database archive

1.  Select **System Administrator > Configuration > ** **System > Database Archive**.
2.  To add or modify a database archive:
    1.  Perform one of the following tasks:
        -   To add a new database archive, from the **Actions** drop-down list, select **Add**.
        -   To copy a database archive, in the grid select the check box next to the archive, and then from the **Actions** drop-down list, select **Copy**.
        -   To modify a database archive, in the grid select the check box next to the archive, and then from the **Actions** drop-down list, select **Edit**.
    2.  Enter information in the [Database Archive fields](#Database_Archive_fields).
    3.  Click **Save**. A confirmation message is displayed.
    4.  Click **OK**.
3.  To add or modify a database table:

1.  Select the check box next to the database archive.
2.  Under **DATABASE ARCHIVE DETAILS**, perform one of the following tasks:
    -   To add a database table, from the **Actions** drop-down list, select **Add**.
    -   To modify a table, in the grid select the check box on the row of the table, and then from the **Actions** drop-down list, select **Edit**.
    -   To copy a table, in the grid select the check box on the row of the table, and then from the **Actions** drop-down list, select **Copy**.
3.  Enter information in the [Database Archive (Details) fields](#Database_Archive_\(Details\)_fields).
4.  Click **Save**. A confirmation message is displayed.
5.  Click **OK**.

5.  To run a database archive:

1.  Select the check box next to the archive, and then from the **Actions** drop-down list, select **Run Archive**. A message states that archiving could take considerable time.
2.  Click **Yes**. Data is copied to the database archive.

7.  To run the database archive in debug mode, select the check box next to the archive, and then from the **Actions** drop-down list, select **Test Archive**. A status file is created with the information that would have been archived if the Run Archive command had been run.
    
    **Note**: The Test Archive option is only available when a file name has been entered in the **Status File** field.
    

## Delete a database archive

1.  Select **System Administrator > Configuration > ** **System > Database Archive**.
2.  Perform one of the following tasks:
    -   To delete a database archive, in the grid, select the check box next to the archive.
    -   To delete a table from a database archive:
        1.  In the grid, select the check box next to the archive.
        2.  Under **DATABASE ARCHIVE DETAILS**, select the check box on the row of the archive table.
3.  From the **Actions** drop-down list, select **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Database Archive fields

 
| Field | Description |
| --- | --- |
| Duplicate Action | Action that will be taken for a duplicate row error, represented by a letter.<br>-   • **E**: Error and Rollback
<br>-   • **I**: Ignore and Continue
<br>-   • **R**: Replace and Continue |
| Archive Table | Name of the database table to add to the database archive. |
| Maximum Rows | Maximum number of rows to process between commits. By default, the components commit changes after each driving table processing cycle. |
| Purge | Indicates that the row being processed should be purged immediately after being archived. This option is only available when performing a simple archive or an archive that has no detail records. |
| Archive Days | Number of days after which records will be archived. |
| Archive Name | Name of the database archive. |
| List Command | A MOCA command or SQL select statement for the database rows to archive. This field includes paging hints with a limit offset of 0 (zero). This code provides pagination for query results to prevent the data from being archived out of order. The result statement should contain any fields that may be needed for sub-archivals. |
| Post Archive Command | Post archive command to be processed after each driving table processing cycle has completed. For a simple archive, this command is invoked for each row that is archived. For a complex archive, this command is invoked for each driving table row that is archived, after a successful archival of the archive details. |
| Status File | Name of the status file that contains informational messages regarding the archive process. If the status file does not exist, it will be created. If the status file exists, additional status messages are added. This column may include a fully qualified file name or simply a file name that will be placed by default into the **$LESDIR/log** directory. |
| Date Column | Name of the source column for the date used to determine record age. |

## Database Archive (Details) fields

 
| Field | Description |
| --- | --- |
| Duplicate Action | Action that will be taken for a duplicate row error, represented by a letter.<br>-   • **E**: Error and Rollback
<br>-   • **I**: Ignore and Continue
<br>-   • **R**: Replace and Continue |
| Archive Table | Name of the database table to add to the database archive. |
| Post Archive Command | Post archive command to be processed after each driving table processing cycle has completed. For a simple archive, this command is invoked for each row that is archived. For a complex archive, this command is invoked for each driving table row that is archived, after a successful archival of the archive details. |
| Archive Name | Name of the database archive. |
| List Command | A MOCA command or SQL select statement for the database rows to archive. This field includes paging hints with a limit offset of 0 (zero). This code provides pagination for query results to prevent the data from being archived out of order. The result statement should contain any fields that may be needed for sub-archivals. |
| Sequence Number | Number that indicates the sequence in which to process the database table. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
