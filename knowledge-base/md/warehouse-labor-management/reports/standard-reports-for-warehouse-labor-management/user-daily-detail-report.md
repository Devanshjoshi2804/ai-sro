---
title: "User Daily Detail report"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/wlmreports_user_daily_detail_report.htm"
source: "/content/wlmreports_user_daily_detail_report.htm"
toc_path:
  - "Warehouse Labor Management"
  - "Reports"
  - "Standard reports for Warehouse Labor Management"
  - "User Daily Detail report"
sections:
  - "User Daily Detail report fields"
images: []
source_sha1: 0c3fd79dde301eb8d122a6468aac5e5f1957d306
---
# User Daily Detail report

This report chronicles the known activities on a user’s workday. You use this report to view detailed assignment information.

After you select the report, you can provide a description of the report, specify the date range for which information is collected, and enter selection criteria to group or limit the output of the report.

## User Daily Detail report fields

 
| Field | Description |
| --- | --- |
| Group By (1–3) | Grouping level by which the information is organized (for example, by supervisor or user). You can have up to three levels of grouping. |
| Page Break | Indicates whether each grouping value is displayed on a separate page. For example, if **Group By** is Users, you have 10 users, and **Page Break** is True, then the report will generate a minimum of 10 pages with each user's information on a separate page. |
| Threshold | Type of user information to which the threshold applies.<br>-   • **Performance**: Only assignment performance information is included.
<br>-   • **Indirect**: Only time spent on indirect tasks is included.
<br>-   • **Direct hours**: Only time spent on direct tasks is included.
<br>-   • **Total paid hours**: Only paid time for the user's work day is included.
<br>-   • **Unmeasured**: Only time spent on unmeasured tasks is included. |
| Value | Number used for the threshold starting point. For example, if you want to view user performance below 80 percent, then the **Threshold** is Performance, the **Value** is 80 and the **Above/Below** is Below. |
| Above/Below | Indicates whether the report displays the information that is above or below the threshold value. For example, if **Threshold** is Material Handling %, **Value** is 70, and **Above/Below** is set to Above, then only the time spent on material handling over 70 percent will be shown on the report. |
| Date Range | Date range for the information that is included in the report. You can select a date that is relative to today's date (such as Yesterday, Last Week, or Last Year) or you can enter a custom date range. |
| From Date | Starting date for a specific date range. |
| To Date | Ending date for a specific date range. |
| Supervisor | Person to whom a user reports. A supervisor manages and oversees a user's work. You can also use the supervisor's ID for easy user selection in reports, assignments, performance statistics, report cards, and payroll information. |
| Warehouse | Unique identifier associated with the warehouse. In a multi-warehouse environment, you can select the warehouse for which you are authorized. |
| Users | Unique identifier for an individual who will be using the application, either with direct access or through an internet connection. |
| Work Teams | Optional category into which users can be grouped for easy selection in reports, assignments, performance statistics, report cards, and payroll information. |
| Report Group | Optional category into which users can be grouped for easy selection in reports, report cards, and payroll information. |
| User Group | Optional category into which users can be grouped for easy selection in reports, assignments, performance statistics, report cards, and payroll information. |
| Observed | Indicates whether to display assignments that have been observed. |
| Show Payroll Cost | Indicates whether payroll cost information is included in the generated report. Payroll cost is the actual pay rate for the user. |
| Show Quality Error | Indicates whether quality error information is included in the generated report. A quality error is used to identify when the overall inventory status of an item is no longer considered acceptable. |
| Show Expected Performance | Indicates whether expected performance information is included in the generated report. Expected performance is a performance value that a user is held to based on actual performance. Only available if False is selected in the **Show Payroll Cost** field. |
| Subtitle | Additional descriptive information that will be displayed below the title in the generated report. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
