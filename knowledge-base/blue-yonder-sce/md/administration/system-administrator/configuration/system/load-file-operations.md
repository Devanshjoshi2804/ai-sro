---
title: "Load File Operations"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/admin/load_file_operations.htm"
source: "/content/admin/load_file_operations.htm"
toc_path:
  - "Administration"
  - "System Administrator"
  - "Configuration"
  - "System"
  - "Load File Operations"
sections:
  - "Perform load file operations"
images: []
source_sha1: 064cdef3526b6f9e8cb01f908894af33af8cb2e1
---
# Load File Operations

You can manually load data from a CSV file into an application database using Load File Operations. Using this process, you can quickly add a large amount of information to your database at one time, instead of adding each individual piece of information using the web client or host transaction download. This method is especially useful if you have already added the information to one of your other third-party applications that enables you to export information to a CSV file.

Load File Operations uses the logic in an associated control file to determine whether data is being added or updated, and enables you to load data into a database from CSV files that are located on a local client workstation or the application server.

**IMPORTANT**: The location of the control file is determined by a policy (SYSTEM-INFORMATION/PRODUCT-LAYERS/DATA-PATHS) that enables you to specify the folders in which control files are located for the database tables.

When you use Load File Operations to load data, the data is added or updated; it is not deleted. For example, if a record exists in the database, but not in the CSV file, when the CSV file is loaded, the record is not removed from the database. If you need to manually remove records from the database, you must do so using SQL commands.

The following examples represent scenarios in which Load File Operations is used:

-   You have a new group of users (such as a large group of seasonal employees), and you export the user data from your human resources (HR) or payroll application to an appropriately formatted CSV file. You can then import the user data into the LES\_USR\_ATH table instead of manually adding each new user into the web client.
-   You have or can generate an appropriately formatted CSV file that contains a new set of application data. You can import the application data into the PRTMST table instead of using the web client to manually add each new item.
-   You have or can generate an appropriately formatted CSV file that contains location data, such as for an expanded or relabeled warehouse. You can import the location data into the LOCMST table instead of using the web client to manually add or modify each new or relabeled location.

A valid CSV file is a text file in which the first line of information specifies the columns (field names) in a table, and each of the following lines defines a set of values (a record) in the table. Each line uses a delimiter, such as a comma (,), to separate the different types of values on each line of the file. Each line (record) in the file (after the first line) must represent a potential row in the database table, and each value on each line must correspond to a value in a column in the database table.

There are several methods for determining the column names for a particular database table to use in constructing the first line of your CSV file (and the resulting order of field values for the lines that follow the first line). For example, you can use the Table Definition window in the SCE client, or have your database administrator look up the information for you using the interface of the supporting database (such as Oracle or SQL Server). The CSV file can be stored on and loaded from the application server or one of the client workstations that are used to access the application.

**Note**: You can use the Table Definition window in the SCE client to view the layout of a table into which you want to load a file. Table Definition also enables you to view a table’s column attributes, such as names, descriptions, and data types.

## Perform load file operations

You can load data into a database from CSV files that are located on a local client workstation or the application server.

**IMPORTANT**: Loading data into a database, if done improperly, can result in unexpected application behavior. It is suggested that you back up your data before attempting this procedure.

1.  Select **System Administrator > Configuration > System > ** **Load File Operations**.
    
    **Note**: If you use the filter field to locate a table, then you must enter an exact table name. Unlike filter fields on other web client pages that allow wildcard characters, this filter field only supports an exact search.
    
2.  In the grid, click the table name.
    
    **Note**: The control file associated with the table is displayed in the **Control File** field. The control file is the path to and name of the file that provides the logic that directs the loading of the information from the data file (specified in the **File Name** field) into the database table (specified in the **Table Name** field). A control file is required to load data.
    
3.  To load a data file from the client workstation:
    1.  From the **Data File Location** drop-down list, select **Client**.
    2.  Perform one of the following tasks:
        -   In the **File Name** field, enter the folder and name of the file. The file name is the path to and name of the data file that contains the information that you want to load into the database table.
        -   Click **Browse**, and then on the File Name window, select the file to load, and click **Ok**.
            
            **Note**: You can only load one file at a time.
            
4.  To load a data file from the application server:
    1.  From the **Data File Location** drop-down list, select **Server.**
    2.  From the **Product Dir** drop-down list, select the directory in which the file is located, such as LESDIR.
    3.  In the **File Name** field, enter the name of the file.
        
        **Note**: You can only load one file at a time.
        
5.  In the **Field Delimiter** field, enter the symbol that separates the values in the file that you are loading into the database table.
6.  Click **Load File**. The file loading process begins and may take several seconds or minutes depending on the size of your file. A confirmation message is displayed.
7.  Click **OK**.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
