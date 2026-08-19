---
title: "System Information policies"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/policies/system_information_policies.htm"
source: "/content/policies/system_information_policies.htm"
toc_path:
  - "Administration"
  - "System Administrator"
  - "Configuration"
  - "Policy"
  - "System Information policies"
sections:
  - "Client update enabled policy"
  - "Client update search paths policy"
  - "Client-side application hooks policies"
  - "Dashboard settings policy"
  - "Default User Order policy"
  - "Description invalidation rate policy"
  - "Directory purges policy"
  - "License expiration warning policy"
  - "Product layer data path policy"
  - "MOCA reports path policy"
  - "System default customization level policy"
images: []
source_sha1: 79f6636be50ae0adec621246787f2f0f635ef56c
---
# System Information policies

The System Information (SYSTEM-INFORMATION) policies control the configuration, security, and client functionality used in the Blue Yonder framework. Some System Information polices are product-specific, such as for the Warehouse Management framework, and are explained in topics for that product.

You use Policy Maintenance to maintain System Information policies.

**IMPORTANT**: These policies are global and cannot be overridden by warehouse, unless otherwise noted.

## Client update enabled policy

The Client update enabled (SYSTEM-INFORMATION/CLIENT-UPDATE/ENABLED) policy determines whether updated SCE clients (.ocx files) will be automatically downloaded to the client PCs and from which directory on the server they will be downloaded.

You can configure the following DETAILS field for this policy:

-   **Return Number 1**: Specifies whether the policy is enabled. A value of 1 is enabled, 0 is disabled. The policy is disabled by default.

## Client update search paths policy

The Client update search paths (SYSTEM-INFORMATION/CLIENT-UPDATE/UPDATE-PATH) policy determines the directory path on the server from which updated SCE client will be downloaded.

Typically, there are multiple paths identified to accommodate the different directories in which client applications are filed. For example, %SALDIR% and %MCSDIR% are valid entries. When you identify multiple paths, indicate the sequence ito apply the policies.

You can configure the following DETAILS fields for this policy:

-   **Return String 1**: Name representing the complete path to the directory on the server from which the updated clients will be downloaded. The default value is **$MCSDIR\\downloads\\forms**.
-   **Sort Sequence**: Order in which the application processes policy details in relation to other details defined for the same policy.

## Client-side application hooks policies

The Client-side application hooks (SYSTEM-INFORMATION/CLIENT-HOOKS/<_Hook event_>) policies determines which events within the framework will trigger the application to execute client application hooks. Client application hooks are ActiveX objects that the MCS framework can call by name to customize an application. Any in-process ActiveX server can be used as a hook. A hook event is the type of hook that will trigger the application to execute the client-side hooks.

Separate policies are available for the following hook events:

-   AFTER-LOGIN
-   AFTER-LOGOUT
-   BEFORE-LOGIN
-   BEFORE-LOGOUT

You can configure the following DETAILS fields for these policies:

-   **Return String 1**: Class ID, or name of the ActiveX library (global unique identifier) that the MCS framework creates to execute the hook event. When the framework locates an application hook, it will create the Object GUID.
-   **Return String 2**: Name of the function as it is displayed in the ActiveX library that is represented by the Object GUID.

## Dashboard settings policy

The Dashboard settings (SYSTEM-INFORMATION/DASH/DASH-SETTINGS) policy enables you to control whether dashboards are enabled for the SCE client and whether they will be displayed to users on application startup.

You can configure the following DETAILS fields for this policy:

-   **Return Number 1**: Specifies whether the dashboard is displayed to all users who log into the application. A value of 1 is enabled, 0 is disabled. The policy is disabled by default.
-   **Return Number 2**: Specifies whether dashboard functionality is enabled in the application. When dashboards are enabled, users will be able to view dashboards for which they are authorized. A value of 1 is enabled, 0 is disabled. The policy is enabled by default.
    
    **Note**: Once users log in, if the dashboard functionality is enabled, they can change their user preferences to show or hide the dashboard.
    

## Default User Order policy

The Default User Order (SYSTEM-INFORMATION/MISCELLANEOUS/DEFAULT-USER-ORDER) policy determines how user display text is sorted and displayed as part of an address configuration. This value is used when address information is displayed in documents, reports, and on web client pages (such as the **User Display** field on the Address page).

You can configure the following DETAILS field for this policy:

-   **Return String 1**: You can select one of the following values:
    -   **User ID**: User's identities will be sorted and displayed in the user display field in the following order: user ID, last name, first name. This is the default.
    -   **Last Name**: User's identities will be sorted and displayed in the user display field in the following order: last name, first name, user ID.

## Description invalidation rate policy

The Description invalidation rate (SYSTEM-INFORMATION/MISCELLANEOUS/DESCRIPTION-INVALIDATION-RATE) policy data value enables you to modify the time interval associated with the MCS description cache invalidation requests threaded monitor. The threaded monitor tracks and holds cache invalidation request processing until the last invalidation request is received for a cache type, and the time interval has passed.

For example, when items are loaded into the database with updated footprint codes, the requests to invalidate the footprint code cache descriptions are held until all items in the batch are loaded and the time interval expires. Then the invalidation occurs, and the MCS description footprint code cache is refreshed.

You can configure the following DETAILS field for this policy:

-   **Return Number 1**: Number of milliseconds the threaded monitor waits following the last invalidation request for a MCS description cache type. When the time expires, the invalidation occurs. The default value is 10000.

## Directory purges policy

The Directory purges (SYSTEM-INFORMATION/MISCELLANEOUS/PURGE-PARAMETERS-DIR) policy determines the directories, the file patterns, and the retention hours and days for any files that need periodic cleanup.

You can configure the following DETAILS fields for this policy:

-   **Return String 1**: Fully qualified path of the files to be purged.
-   **Return String 2**: Characters representing the naming convention of the files to be purged.
-   **Return Number 1**: Number of days the files will be retained.
-   **Return Float 1**: Whole or decimal number representing the number of hours the files will be retained, such as 1 or 2.5. If you specify retention hours, then you must enter a value (0 or more) in the **Return Number 1** field for retention days.
-   **Sort Sequence**: Order in which the application processes policy details in relation to other details defined for the same policy.

## License expiration warning policy

The License Expiration Warning (SYSTEM-INFORMATION/LICENSE/EXPIRATION-WARNING-IN DAYS) policy determines the number of days prior to the expiration of your Blue Yonder software license that a warning message will be displayed. Your Blue Yonder software license gives you permission to install and use Blue Yonder applications until a specified expiration date. The warning message gives you time to renew your Blue Yonder software license before you are no longer permitted to use the associated Blue Yonder applications.

You can configure the following DETAILS field for this policy:

-   **Return Number 1**: Number of days prior to software license expiration that the expiration warning message will be displayed. The default value is 14.

## Product layer data path policy

The Product layer data path (SYSTEM-INFORMATION/PRODUCT-LAYERS/DATA-PATH) policy defines a standard folder or folders for each Blue Yonder product in which the control files are located for manually loading data into product-specific database tables using Load File Operations. The control files are used by the Load File Operations page to provide the logic that directs the loading of the information in a comma-separated value (.csv) data file into a database table. See [Load File Operations](../system/load-file-operations.md).

You can also add policy details to define custom folders in which control files are located. An example of when you might want to add a policy is when you have added a custom table to your Blue Yonder database and you want to load data into the custom table from a comma-separated value (.csv) file using Load File Operations. To do this, you must also create a control file that specifies how to load the .csv file, and add a policy detail that defines the folder on the application server in which the custom control file is located. For more information on creating control files for loading data files using Load File Operations, review the contents of the standard control files or contact your Blue Yonder project team.

**Note**: You can add policy details to the Product layer data path policy in Policy Maintenance or Policy Maintenance - Override.

When adding policy details, you can configure the following DETAILS fields:

-   **Sort Sequence**: Order in which the application processes policy details in relation to other details defined for the same policy. Specifically, for this policy, the sort sequence specifies the order in which the folders on the application server are to be searched to find control files for loading comma-separated value (.csv) files into database tables using Load File Operations.

-   **Return String 1**: Folder on the application server in which the control files are located. Path environment variables, such as $LESDIR, can be used instead of typing out the entire absolute path name of the folder. When the folder is actually used, the environment variable is replaced with the path name. For more information on path environment variables, consult your operating system (such as Windows or Linux) documentation.

The following table lists the standard Product layer data path policy values plus an example of an additional custom value (c:\\custom\_control\_files).

**IMPORTANT**: Do not delete or change the standard values. Doing so can result in unexpected application behavior.

      
| Sort Sequence | Return String 1 | Return String 2 | Return Number 1 | Return Number 2 | Return Float 1 | Return Float 2 |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | $MOCADIR\\db\\data\\load\\base\\safetoload\\ | (null) | 0 | 0 | 0 | 0 |
| 1 | $MOCADIR\\db\\data\\load\\base\\bootstraponly\\ | (null) | 0 | 0 | 0 | 0 |
| 2 | $MCSDIR\\db\\data\\load\\base\\safetoload\\ | (null) | 0 | 0 | 0 | 0 |
| 3 | $MCSDIR\\db\\data\\load\\base\\bootstraponly\\ | (null) | 0 | 0 | 0 | 0 |
| 4 | $SALDIR\\db\\data\\load\\<br > base\\safetoload\\ | (null) | 0 | 0 | 0 | 0 |
| 5 | $SALDIR\\db\\data\\load\\<br > base\\bootstraponly\\ | (null) | 0 | 0 | 0 | 0 |
| 6 | $LESDIR\\db\\data\\load\\<br > base\\safetoload\\ | (null) | 0 | 0 | 0 | 0 |
| 7 | $LESDIR\\db\\data\\load\\<br > base\\bootstraponly\\ | (null) | 0 | 0 | 0 | 0 |
| 8 | c:\\custom\_control\_files\\ | (null) | 0 | 0 | 0 | 0 |

## MOCA reports path policy

The MOCA reports path (SYSTEM-INFORMATION/REPORTS/MOCA-REPORTS-PATH) policy defines the search path for the MOCA Reports server functionality. The server searches these paths to find a specified report based on the sort sequence and stops searching after it finds the specified report.

**Note**: Server side environment variables can be used to define a search path, such as **$SALDIR\\reports**.

You can configure the following DETAILS fields for this policy:

-   **Return String 1**: Name representing the fully qualified path of the location for which the application will search for reports. The default value is **$LESDIR\\reports**.
-   **Sort Sequence**: Integer representing the application-generated order in which the policy will be applied.

## System default customization level policy

The System default customization level (SYSTEM-INFORMATION/CUSTOMIZATION-LEVEL/DEFAULT) policy determines the default customization level used. You can customize Blue Yonder application data. Customized data is kept separately using a customization level. The customization level is a higher number than the base data, and protects the base data from changes.

You can configure the following DETAILS field for this policy:

-   **Return Number 1**: Customization level for the customized data that you want to use. Typically, 0 represents the default Blue Yonder data, 10 represents customized project data, 20 represents customized value added reseller (VAR) data, and 30 represents customized site data. The default value is 10.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
