---
title: "Code Maintenance-Supervisor"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/admin/code_maintenance-supervisor.htm"
source: "/content/admin/code_maintenance-supervisor.htm"
toc_path:
  - "Administration"
  - "System Administrator"
  - "Configuration"
  - "System"
  - "Code Maintenance-Supervisor"
sections:
  - "Add or modify a code"
  - "Delete a code"
  - "Code Maintenance-Supervisor fields"
images: []
source_sha1: d2c6903704f3cf2c8ba7b13e8a9ae5fc0f34b55b
---
# Code Maintenance-Supervisor

A code is an identifier that represents a value for a specific attribute stored in a column in the application server instance database. You can define code values that match the terminology used in your warehouse for attributes such as appointment types, inventory statuses, and order types.

The following table shows an example of origin code (orgcod) codes values.

   
| Column | Code | Description | Priority |
| --- | --- | --- | --- |
| orgcod | AD | Andorra | 1 |
| orgcod | AE | United Arab Emirates | 2 |
| orgcod | AF | Afghanistan | 3 |
| orgcod | AG | Anitgua Barbuda | 4 |

You use the Code Maintenance-Supervisor page to maintain codes and values.

## Add or modify a code

When you add a code, you define a code value and description that is associated with an existing column.

**IMPORTANT**: If the column that you want to use does not exist in the application database, contact your Blue Yonder project team for assistance.

1.  Select **System Administrator > Configuration > ** **System > Code Maintenance-Supervisor**.
2.  Perform one of the following tasks:
    -   To add a code, from the **Actions** drop-down list, select **Add**.
    -   To copy a code, in the grid select the check box on the row of the code value, and then from the **Actions** drop-down list, select **Copy**.
    -   To modify a code, in the grid select the check box on the row of the code value, and then from the **Actions** drop-down list, select **Edit**.
3.  Enter information in the [Code Maintenance-Supervisor fields](#Code_Maintenance-Supervisor_fields).
4.  Click **Save**. A confirmation message is displayed.
5.  Click **OK**.

## Delete a code

1.  Select **System Administrator > Configuration > ** **System > Code Maintenance-Supervisor**.
2.  In the grid, select the check box on the row of the code value.
3.  From the **Actions** drop-down list, select **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Code Maintenance-Supervisor fields

 
| Field | Description |
| --- | --- |
| Code Value | Unique identifier that represents the value for the code. |
| Description | Description of the code value that is displayed on the user interface in place of the code value; such as in a drop-down list. |
| Required Field | Specifies whether the field (in which the code value is selected) is required. |
| Sort Sequence | Value that determines the sequence of the code value in the column. This value also determines the order in which the code values are displayed to the user. |
| Column | Name of the column in the application server instance database for which the code is being defined. |
| Column Description | Description that is displayed in place of the column on the user interface; it is typically used to identify the field in which the code value is selected. For example, the column description for the column ordtyp is Order Type. |
| Short Description | Brief description of the code value. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
