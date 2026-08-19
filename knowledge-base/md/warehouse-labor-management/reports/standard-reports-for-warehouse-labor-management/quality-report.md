---
title: "Quality report"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/wlmreports_quality_report.htm"
source: "/content/wlmreports_quality_report.htm"
toc_path:
  - "Warehouse Labor Management"
  - "Reports"
  - "Standard reports for Warehouse Labor Management"
  - "Quality report"
sections:
  - "Quality report fields"
images: []
source_sha1: 9a985c3d726aa003d9017eb1b081fb34e97953e0
---
# Quality report

This report is used to identify quality errors for your facility. For example, you can use the report results to determine which areas have a high number of errors, or which item is frequently picked in error.

After you select the report, you can provide a description of the report, specify the date range for which information is collected, and enter selection criteria to group or limit the output of the report.

## Quality report fields

 
| Field | Description |
| --- | --- |
| Group By (1–3) | Grouping level by which the information is organized (for example, by supervisor or user). You can have up to three levels of grouping. |
| Page Break | Indicates whether each grouping value is displayed on a separate page. For example, if **Group By** is Users, you have 10 users, and **Page Break** is True, then the report will generate a minimum of 10 pages with each user's information on a separate page. |
| Charged/UnCharged | Indicates the type of quality error information to which the threshold applies.<br>-   • **Total**: Both charged and uncharged quality error information is included.
<br>-   • **Charged**: Only the quality error information containing charges to the user is included.
<br>-   • **UnCharged**: Only quality error information that does not contain charges to the user is included. |
| Quality Error % | Quality performance percent amount used for the threshold. For example, if you want to view charged quality errors above 10 percent, then the **Charged/UnCharged** is Charged, the **Quality Error %** is 10 and the **Above/Below** is Above. |
| Above/Below | Indicates whether the report displays the information that is above or below the threshold value. For example, if **Threshold** is Material Handling %, **Value** is 70, and **Above/Below** is set to Above, then only the time spent on material handling over 70 percent will be shown on the report. |
| Date Range | Date range for the information that is included in the report. You can select a date that is relative to today's date (such as Yesterday, Last Week, or Last Year) or you can enter a custom date range. |
| From Date | Starting date for a specific date range. |
| To Date | Ending date for a specific date range. |
| Warehouse | Unique identifier associated with the warehouse. In a multi-warehouse environment, you can select the warehouse for which you are authorized. |
| Item # | Number representing the stock keeping unit (SKU) or label for the item that should have been picked. |
| Error Item # | Item number for the item that was picked in error. |
| Driver | Identifier of the driver who delivered or picked up a truck associated with a quality error. |
| Reference ID | Unique identifier used to reference the assignment information for the day. |
| Route # | Number that indicates a specific sequential routing order for an assignment through your facility. |
| Unresolved | Indicates whether quality errors not tied to an assignment are included in the generated report. |
| User Defined 1-4 | User defined information, as specified in the User Defined 1-4 fields, for an assignment. |
| Quality Error Source | Represents the origin of a quality error. |
| Quality Error Type | Represents the category into which a quality error is grouped. Typically, the quality error type is the reason for the quality error. |
| Supervisor | Person to whom a user reports. A supervisor manages and oversees a user's work. You can also use the supervisor's ID for easy user selection in reports, assignments, performance statistics, report cards, and payroll information. |
| Client | Unique identifier for a client who houses product within a multi-client (third-party logistics) warehouse. The client ID distinguishes one client from another and allows for effective management of activities for multiple clients in one warehouse. In Warehouse Labor Management, the client may be used both for reporting purposes and in the job code mapping process to develop individual job codes by client. |
| Customers | Unique number for the customer. A customer is the end recipient associated with an assignment. In the case of a 3PL, the customer would be the individual or organization to which product is being shipped; whereas the client is the individual or organization for which product is shipped. In Warehouse Labor Management, the customer may be used both for reporting purposes and in the job code mapping process to develop individual job codes by customer. |
| Users | Unique identifier for an individual who will be using the application, either with direct access or through an internet connection. |
| Location ID | Unique identifier assigned to a location. Each location defined in the application has a location ID. A location is a uniquely identified position within an area of the warehouse used to store, stage, or manipulate product. |
| Work Area | Unique alphanumeric identifier, 1 to 40 characters in length, for a work area. A work area defines an area of the warehouse where similar types of operations are performed. Typically, a warehouse is divided into work areas for work management purposes. |
| User Group | Optional category into which users can be grouped for easy selection in reports, assignments, performance statistics, report cards, and payroll information. |
| Aisle Area | Unique alphanumeric identifier, one to ten characters in length, for an aisle area. An aisle area is a group of aisles that share the same characteristics. Aisle areas are defined based on the environment and characteristics of the work being performed in the aisles. |
| Aisle Area Desc | Meaningful summary identifying the purpose and use of the aisle area. |
| Shift | Defined work period within 24 hours that may include paid and unpaid breaks. |
| Shift Category | Unique name for a group of shifts. |
| Work Team | Optional category into which users can be grouped for easy selection in reports, assignments, performance statistics, report cards, and payroll information. |
| Work Category | Unique identifier for the work category. A work category is a method of categorizing job information for reporting and statistical purposes. A job code can be assigned to only one work category. |
| Job Codes | Identifier for the job code. A job code represents a standard for a task being performed in your facility, and it is the basic component for an assignment. |
| Job Code Desc | Meaningful summary identifying the purpose and use of the job code. |
| Report Group | Optional category into which users can be grouped for easy selection in reports, report cards, and payroll information. |
| Subtitle | Additional descriptive information that will be displayed below the title in the generated report. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
