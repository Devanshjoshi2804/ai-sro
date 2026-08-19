---
title: "Reporting policies"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/policies/reporting_policy_data.htm"
source: "/content/policies/reporting_policy_data.htm"
toc_path:
  - "Administration"
  - "System Administrator"
  - "Configuration"
  - "Policy"
  - "Reporting policies"
sections:
  - "Max pages policies"
  - "Max pages settings enabled policy"
  - "Time-out duration millis policy"
  - "Time-out settings enabled policy"
images: []
source_sha1: c5c7ff2851a9a82f59c5438943fa8ccc855bac45
---
# Reporting policies

The Reporting (REPORTING) policies control the following report generation limits:

-   **Maximum pages enabled for a report**: You can set a page limit when generating a report. When a report exceeds the maximum number of pages, an error message is displayed and the report generation is terminated. You can then enter information in the report criteria fields to reduce the page count and regenerate the report. This configuration prevents long delays when generating reports that can affect overall application performance.
-   **Duration**: You can limit the time available for a report to generate. When report generation exceeds the time limit, an error message is displayed and the report generation is terminated. You can then enter information in the report criteria fields to reduce the report size and regenerate the report. This configuration prevents communication errors when generating reports that can affect overall application performance.

You use Policy Maintenance or Policy Maintenance - Override to maintain Reporting policies.

## Max pages policies

The Max pages (REPORTING/MAX-PAGES/DEFAULT, <_Standard Report_>) policies set the maximum number of pages for a report. The DEFAULT policy value indicates that the policy applies to all reports. Separate polices exist for each standard report, such as the All Employees Report (REPORTING/MAX-PAGES/Std-AllEmployees).

To configure a policy for a specific report, add a new policy that specifies the report name as the policy value.

**Note**: A report-specific policy takes precedence over the default policy.

You can configure the following DETAILS field for this policy:

-   **Return Number 1**: Maximum number of pages. The default value is 500, which is the maximum value that can be set for this field.

The maximum number of pages can also be configured in the report jrxml file (located on the application server instance in the **:\\JDA\\<**_Instance Name_**>\\REPORTING\\reports** directory) using the net.sf.jasperreports.governor.max.pages property. If this value is set in both the report jrxml file property and the policy code values, the lowest value is used. If no values are set in either policies or in the jrxml file, a default value of 500 is used.

## Max pages settings enabled policy

The Max pages settings enabled (REPORTING/MAX-PAGES-SETTINGS-ENABLED/DEFAULT) policy enables the use of a maximum number of pages value for a report. The DEFAULT value indicates that the policy applies to all reports.

To configure a policy for a specific report, add a new policy that specifies the report name as the policy value.

**Note**: A report-specific policy takes precedence over the default policy.

You can configure the following DETAILS field for this policy:

-   **Return Number 1**: Specifies whether the policy is enabled. A value of 1 is enabled, 0 is disabled. The policy is enabled by default.

## Time-out duration millis policy

The Time-out duration millis (REPORTING/TIME-OUT-DURATION-MILLIS/DEFAULT) policy sets the maximum timeout value in milliseconds for report generation. The DEFAULT value indicates that the policy applies to all reports.

You can configure the following DETAILS field for this policy:

-   **Return Number 1**: Maximum timeout value. The default value is 300000.

You can also configure report timeout using the timeout-duration-millis key value located in the REPORTING section of the MOCA registry. The default value is 300000. If this value is set in both the registry and the policy code values, the lowest value is used. If the policies are not configured, the application uses the value from the registry. If no values are set in the policies or registry, a default value of 300000 is used.

## Time-out settings enabled policy

The Time-out settings enabled (REPORTING/TIME-OUT-SETTINGS-ENABLED/DEFAULT) policy enables the use of a timeout value for report generation. The DEFAULT value indicates that the policy applies to all reports.

You can configure the following DETAILS field for this policy:

-   **Return Number 1**: Specifies whether the policy is enabled. A value of 1 is enabled, 0 is disabled. The policy is enabled by default.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
