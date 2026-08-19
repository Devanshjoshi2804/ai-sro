---
title: "Discrete Procedure report"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/wlmreports_discrete_procedure_report.htm"
source: "/content/wlmreports_discrete_procedure_report.htm"
toc_path:
  - "Warehouse Labor Management"
  - "Reports"
  - "Standard reports for Warehouse Labor Management"
  - "Discrete Procedure report"
sections:
  - "Discrete Procedure report fields"
images: []
source_sha1: f064ea50c573c3a74c287e37ad6ba58676f1b6aa
---
# Discrete Procedure report

This report is used to view the discrete procedures and their total repetition quantity, which is the number of times that a discrete procedure was performed, for assignments in your facility. For example, a call center can be configured so that a discrete procedure represents updating a customer’s information. The call center can run this report for a specific time frame and determine whether this procedure was performed and, if so, how often.

After you select the report, you can provide a description of the report, specify the date range for which information is collected, and enter selection criteria to group and limit the output of the report.

## Discrete Procedure report fields

 
| Field | Description |
| --- | --- |
| Group By (1–3) | Grouping level by which the information is organized (for example, by supervisor or user). You can have up to three levels of grouping. |
| From Date | Starting date for a specific date range. |
| To Date | Ending date for a specific date range. |
| Date Range | Date range for the information that is included in the report. You can select a date that is relative to today's date (such as Yesterday, Last Week, or Last Year) or you can enter a custom date range. |
| Warehouse | Unique identifier associated with the warehouse. In a multi-warehouse environment, you can select the warehouse for which you are authorized. |
| Page Break | Indicates whether each grouping value is displayed on a separate page. For example, if **Group By** is Users, you have 10 users, and **Page Break** is True, then the report will generate a minimum of 10 pages with each user's information on a separate page. |
| Aisle Area | Unique alphanumeric identifier, one to ten characters in length, for an aisle area. An aisle area is a group of aisles that share the same characteristics. Aisle areas are defined based on the environment and characteristics of the work being performed in the aisles. |
| Aisle Area Desc | Meaningful summary identifying the purpose and use of the aisle area. |
| Client | Unique identifier for a client who houses product within a multi-client (third-party logistics) warehouse. The client ID distinguishes one client from another and allows for effective management of activities for multiple clients in one warehouse. In Warehouse Labor Management, the client may be used both for reporting purposes and in the job code mapping process to develop individual job codes by client. |
| Customer | Unique number for the customer. A customer is the end recipient associated with an assignment. In the case of a 3PL, the customer would be the individual or organization to which product is being shipped; whereas the client is the individual or organization for which product is shipped. In Warehouse Labor Management, the customer may be used both for reporting purposes and in the job code mapping process to develop individual job codes by customer. |
| Supervisor | Person to whom a user reports. A supervisor manages and oversees a user's work. You can also use the supervisor's ID for easy user selection in reports, assignments, performance statistics, report cards, and payroll information. |
| User ID | Unique identifier of the user. A user is an individual who will be using the application, either with direct access or through an internet connection. |
| Work Area | Unique alphanumeric identifier, 1 to 40 characters in length, for a work area. A work area defines an area of the warehouse where similar types of operations are performed. Typically, a warehouse is divided into work areas for work management purposes. |
| User Group | Optional category into which users can be grouped for easy selection in reports, assignments, performance statistics, report cards, and payroll information. |
| Report Groups | Optional category into which users can be grouped for easy selection in reports, report cards, and payroll information. |
| Shift Category | Unique name for a group of shifts. |
| Shift | Name that identifies a shift. A shift is a defined work period within 24 hours that may include paid and unpaid breaks. |
| Work Teams | Optional category into which users can be grouped for easy selection in reports, assignments, performance statistics, report cards, and payroll information. |
| Work Category | Unique identifier for the work category. A work category is a method of categorizing job information for reporting and statistical purposes. A job code can be assigned to only one work category. |
| Job Codes | Identifier for the job code. A job code represents a standard for a task being performed in your facility, and it is the basic component for an assignment. |
| Job Code Desc | Meaningful summary identifying the purpose and use of the job code. |
| Procedure ID | Unique identifier for the discrete procedure. A discrete procedure is a group of sequenced procedure-based tasks (such as for call center operations, machine setup, or value-added services). |
| Procedure Desc | Meaningful summary identifying the purpose and use of the discrete procedure. |
| Show Blended Cost | Indicates whether blended cost information is included in the generated report. Blended cost is an estimated rate for the user. |
| Show Payroll Cost | Indicates whether payroll cost information is included in the generated report. Payroll cost is the actual pay rate for the user. |
| Show Quality Error | Indicates whether quality error information is included in the generated report. A quality error is used to identify when the overall inventory status of an item is no longer considered acceptable. |
| Show Graph | Indicates whether a bar graph containing the report information is also included in the generated report. |
| Show Clock Punch | Indicates whether clock punch information is included in the generated report. A clock punch is a record marking (or indicating) a starting or ending date and time for a user. Only available if you are using Time and Incentives functionality. |
| Subtitle | Additional descriptive information that will be displayed below the title in the generated report. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
