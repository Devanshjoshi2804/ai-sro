---
title: "Column Editor"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/admin/column_editor.htm"
source: "/content/admin/column_editor.htm"
toc_path:
  - "Administration"
  - "Extensions"
  - "Column Editor"
sections:
  - "Column Compatibility value"
  - "Add or modify a column"
  - "Generate a creation script"
  - "Delete a column"
  - "Column Editor fields"
images: []
source_sha1: c846558a8aea51d0f39fb3577e591ad0efae5d42
---
# Column Editor

You use the Column Editor to extend standard database tables distributed in the application by adding user-defined columns. When you add a new column, you create a column definition and select the tables to which the column should be applied.

After you add a column to a table, the column does not contain any data. You can add data to the column with a method such as a user-defined MOCA command, a task or job, or an Integrator transaction.

To migrate the changes to another instance, you can generate a creation script that includes individual SQL scripts for each column definition. See [Generate a creation script](#Generate_a_creation_script).

**IMPORTANT**: The Column Editor is intended for use in a test or development instance where the instance can be stopped and restarted for the changes to take effect, and where the data and command changes related to the user-defined column are maintained and tested. Column Editor is not intended for use in a production instance.

## Column Compatibility value

When adding a user-defined column to a database table, you are required to select a Compatibility value as an attribute. The Compatibility value identifies how data types are defined and converted between a web client (as part of a Configurable Web Service \[CWS\] or RESTful web service) and the MOCA application server.

All information transmitted in a web request is sent as a string (character) data type. For columns that require data types other than string, such as integer, Boolean, and date, data type handling is required to ensure the data is accurately transmitted between the web client and the MOCA application server. The application handles data type definition and conversion for all web client functionality within the web services layer using International Organization for Standardization (ISO) standard data type definitions. Using the ISO standards allows for improved and consistent communication between the MOCA application server and external web clients. For example, the date data type is defined and converted using the ISO-8601 standard, which requires both date and time zone values.

There may be situations in which you need to control how a column’s data type is handled. For this reason, the following Compatibility values are available to provide flexibility with data type handling:

-   The current Compatibility value (which is the highest value) indicates that the application applies the ISO standard data type handling for the column. You must select the highest value if you are adding a column that supports web client functionality such as Page Builder.
    
    **Note**: It is recommended that whenever possible, you use the default Compatibility value to ensure that data types are defined and converted consistently and for use in the web client.
    
-   A lower Compatibility value, such as 1, indicates that the application does not apply the ISO standards data type handling for the column. You should select this value if you are adding a column that is supported by a previously developed web service that relies on legacy MOCA data type handling.
    
    **Note**: If you select a lower Compatibility value, data may display inconsistently for date and Boolean data types. For more information about the compatibility of column data that is defined and converted by MOCA data type handling, see the MOCA Developer Guide.
    

## Add or modify a column

1.  Select **Extensions > Column Editor**.

1.  Perform one of the following tasks:
    -   To add a column, from the **Actions** drop-down list, select **Add**.
    -   To modify a column, in the grid, select the column, and then from the **Actions** drop-down list, select **Modify**.
2.  Enter information in the [Column Editor fields](#Column_Editor_fields).
    
    **Note**: When modifying a column, only the **Column Description** and **Compatibility** fields can be modified.
    
3.  To apply the column to tables:
    1.  Under **APPLIED TABLES**, in the filter field, enter search criteria to display the tables you want.
    2.  Select the check box next to the tables that apply.
    3.  Click **Save**.
        
        **Note**: New columns will not be populated with data by default. You can add data to the column with a method such as a user-defined MOCA command, a task or job, or an Integrator transaction.
        
4.  To remove the column from tables to which it is applied:
    
    **IMPORTANT**: Removing a column from a table results in data loss and possible errors. All data that was stored in the column is deleted. Any command that directly (select vc\_Column\_Name) or indirectly (select \*) references the column may cease to function.
    
    1.  Under **APPLIED TABLES**, in the filter field, enter search criteria to display the tables you want.
    2.  Deselect the check box next to the tables from which the column should be removed.
    3.  Click **Save**. A confirmation message is displayed.
    4.  Click **OK**.
5.  Restart the instance.

## Generate a creation script

You use the **Generate Creation Script** action from the Column Editor Actions drop-down list to extract all the user-defined column definitions from one application instance for the purpose of migrating the changes to another instance of the same application. A ZIP file is created that contains separate individual SQL scripts for each column definition. These scripts include SQL to create the column definition and apply the column to all of the tables to which the column was applied in the instance.

When extracted, the SQL script files can be included as an input to a rollout to update an instance. If you are producing a rollout or performing a migration and do not need to include all of the columns, you can choose the scripts that you want to include.

**Note**: The creation script only copies new user-defined column definitions into an instance. It does not modify or remove user-defined columns that already exist. Modifying a user-defined column that exists in an instance is not possible without manual intervention. You must manually remove the existing column from the target instance before you can use the script to copy the modified column to the target instance.

1.  Select **Extensions > Column Editor**.

2.  From the **Actions** drop-down list, select **Generate Creation Script**. The Save As window is displayed.
3.  Save the file.

## Delete a column

Deleting a column removes the column definition and removes the column from any tables to which it was applied. You can only delete one column definition at a time.

**IMPORTANT**: Removing a column from a table results in data loss and possible errors. All data that was stored in the column is deleted. Any command that directly ("select vc\__Column\_Name_") or indirectly ("select \*") references the column may cease to function.

1.  Select **Extensions > Column Editor**.

2.  In the grid, select the column.
3.  From the **Actions** drop-down list, select **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Column Editor fields

 
| Field | Description |
| --- | --- |
| **Column Name** | Unique identifier for the column. The name must be in lowercase characters and include a prefix that identifies the value set in the **Extension Type** field.<br > **Note**: A column name includes a uc\_ or vc\_ prefix to indicate the column is not distributed with the standard application. |
| **Column Description** | Text that further describes the column. |
| **Extension Type** | Indicates that the column is a user-defined extension to the standard application table and the type of implementer that added the column. A prefix is added to the column name to indicate the column is added by one of the following implementers:<br>-   • **Customer**: uc\_ is the prefix used to indicate a customer added the column.
<br>-   • **Blue Yonder or Value Added Reseller**: vc\_ is the prefix used to indicate that a Blue Yonder project team or value added reseller added the column. |
| **Compatibility** | Number that identifies the type of data type handling used. The current Compatibility value (which is the highest value) indicates that the application applies ISO standard data type handling for the column. The current value is provided by default and is required if the column is to be used to support web client functionality.<br > If the column is supported by an existing web service that requires alternate data handling, such as legacy MOCA data handling, you can change the value to a previous version, such as from 2 to 1. See [Column Compatibility value](#Column_Compatibility_value).<br > User-defined columns that were previously defined without a Compatibility value are considered version 1 (the lowest value). |
| Data Type | Type of data (Boolean, DateTime, Double, Integer, and String) that is supported in the column. |
| Length | Maximum number of characters allowed for a valid data entry in the column. Only displayed when the **Data Type** value is set to **Double**, **Integer**, or **String.** |
| Precision | Maximum number of digits that are allowed after the decimal point. This field is displayed only when the **Data Type** field is set to **Double**. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
