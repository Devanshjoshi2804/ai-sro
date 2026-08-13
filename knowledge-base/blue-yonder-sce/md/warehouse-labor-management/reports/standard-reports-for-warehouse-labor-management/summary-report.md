---
title: "Summary report"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/wlmreports_summary_report.htm"
source: "/content/wlmreports_summary_report.htm"
toc_path:
  - "Warehouse Labor Management"
  - "Reports"
  - "Standard reports for Warehouse Labor Management"
  - "Summary report"
sections:
  - "Summary report fields"
images: []
source_sha1: 4a96655a28cfa67d930d41ec4a9ba65d0dbe3c34
---
# Summary report

This report chronicles the work activities in your facility. You use this report to view summarized assignment information. In addition, all report details provide grand total levels.

After you select the report, you can provide a description of the report, specify the date range for which information is collected, and enter selection criteria to group or limit the output of the report.

## Summary report fields

 
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
| Reference ID | Unique identifier used to reference the assignment information for the day. |
| Route # | Number that indicates a specific sequential routing order for an assignment through your facility. |
| User Defined 1-4 | User defined information, as specified in the User Defined 1-4 fields, for an assignment. |
| Warehouse | Unique identifier associated with the warehouse. In a multi-warehouse environment, you can select the warehouse for which you are authorized. |
| Aisle Area | Unique alphanumeric identifier, one to ten characters in length, for an aisle area. An aisle area is a group of aisles that share the same characteristics. Aisle areas are defined based on the environment and characteristics of the work being performed in the aisles. |
| Aisle Area Desc | Meaningful summary identifying the purpose and use of the aisle area. |
| Supervisors | Person to whom a user reports. A supervisor manages and oversees a user's work. You can also use the supervisor's ID for easy user selection in reports, assignments, performance statistics, report cards, and payroll information. |
| Client | Unique identifier for a client who houses product within a multi-client (third-party logistics) warehouse. The client ID distinguishes one client from another and allows for effective management of activities for multiple clients in one warehouse. In Warehouse Labor Management, the client may be used both for reporting purposes and in the job code mapping process to develop individual job codes by client. |
| Customers | Unique number for the customer. A customer is the end recipient associated with an assignment. In the case of a 3PL, the customer would be the individual or organization to which product is being shipped; whereas the client is the individual or organization for which product is shipped. In Warehouse Labor Management, the customer may be used both for reporting purposes and in the job code mapping process to develop individual job codes by customer. |
| Users | Unique identifier for an individual who will be using the application, either with direct access or through an internet connection. |
| Work Area | Unique alphanumeric identifier, 1 to 40 characters in length, for a work area. A work area defines an area of the warehouse where similar types of operations are performed. Typically, a warehouse is divided into work areas for work management purposes. |
| User Groups | Optional category into which users can be grouped for easy selection in reports, assignments, performance statistics, report cards, and payroll information. |
| Report Groups | Optional category into which users can be grouped for easy selection in reports, report cards, and payroll information. |
| Shift | Defined work period within 24 hours that may include paid and unpaid breaks. |
| Shift Category | Unique name for a group of shifts. |
| Work Teams | Optional category into which users can be grouped for easy selection in reports, assignments, performance statistics, report cards, and payroll information. |
| Work Category | Unique identifier for the work category. A work category is a method of categorizing job information for reporting and statistical purposes. A job code can be assigned to only one work category. |
| Job Codes | Identifier for the job code. A job code represents a standard for a task being performed in your facility, and it is the basic component for an assignment. |
| Job Code Desc | Meaningful summary identifying the purpose and use of the job code. |
| Observed | Indicates whether to display assignments that have been observed. |
| Show Blended Cost | Indicates whether blended cost information is included in the generated report. Blended cost is an estimated rate for the user. |
| Show Payroll Cost | Indicates whether payroll cost information is included in the generated report. Payroll cost is the actual pay rate for the user. |
| Show Quality Error | Indicates whether quality error information is included in the generated report. A quality error is used to identify when the overall inventory status of an item is no longer considered acceptable. |
| Show Clock Punch | Indicates whether clock punch information is included in the generated report. A clock punch is a record marking (or indicating) a starting or ending date and time for a user. Only available if you are using Time and Incentives functionality. |
| Show Expected Performance | Indicates whether expected performance information is included in the generated report. Expected performance is a performance value that a user is held to based on actual performance. Only available if False is selected in the **Show Payroll Cost** field. |
| Show Utilization % | Indicates whether utilization percentage is included in the generated report. Utilization % is the percentage of paid time a user spends on direct work (value-added activity). |
| Subtitle | Additional descriptive information that will be displayed below the title in the generated report. |
| Baseline Performance | Value for performance data (direct and indirect) to compare against actual values. |
| Baseline Indirect % | Value for the percentage of time spent on indirect tasks to compare against actual values. |
| Show Graph | Indicates whether a bar graph containing the report information is also included in the generated report. |
| Baseline Unmeasured % | Value for the percentage of time spent on unmeasured task times to compare against actual values. |
| Baseline Units/Hr | Value for units per hour to compare against actual values. |
| Baseline Cost/Unit | Value for cost per unit to compare against actual values. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
