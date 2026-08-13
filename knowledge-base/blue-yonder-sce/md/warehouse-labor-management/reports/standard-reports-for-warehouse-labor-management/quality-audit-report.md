---
title: "Quality Audit report"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/wlmreports_quality_audit_report.htm"
source: "/content/wlmreports_quality_audit_report.htm"
toc_path:
  - "Warehouse Labor Management"
  - "Reports"
  - "Standard reports for Warehouse Labor Management"
  - "Quality Audit report"
sections:
  - "Quality Audit report fields"
images: []
source_sha1: d7f4b4cbe521dbe7306edd02faafe4d10d4cebe9
---
# Quality Audit report

This report provides the results of auditing a warehouse for quality errors, including the error rate, sample rate, and projected error count. For example, if a customer receives too many items, the error type will be over (pick) and the audit results will include a cost to remedy the error, the number of items overpicked, and other attributes specified by the report parameters. The sampling rate charted against the error rate helps you determine if you are doing too many or too few quality audits. The optimal sample rate is the rate at which the error rate begins to level off.

After you select the report, you can provide a description of the report, specify the duration of time for which information is collected, and enter selection criteria to group or limit the output of the report.

## Quality Audit report fields

 
| Field | Description |
| --- | --- |
| Group By (1–3) | Grouping level by which the information is organized (for example, by supervisor or user). You can have up to three levels of grouping. |
| Page Break | Indicates whether each grouping value is displayed on a separate page. For example, if **Group By** is Users, you have 10 users, and **Page Break** is True, then the report will generate a minimum of 10 pages with each user's information on a separate page. |
| Charged/UnCharged | Indicates the type of quality error information to which the threshold applies.<br>-   • **Total**: Both charged and uncharged quality error information is included.
<br>-   • **Charged**: Only the quality error information containing charges to the user is included.
<br>-   • **UnCharged**: Only quality error information that does not contain charges to the user is included. |
| Quality Errors | Indicates whether to include quality error information. If you set **Charged/UnCharged** to Total, both charged and uncharged quality error information is included. |
| Quality Error % | Quality performance percent amount used for the threshold. For example, if you want to view charged quality errors above 10 percent, then set the **Charged/UnCharged** to Charged, the **Quality Error %** to 10 and the **Above/Below** to Above. |
| Above/Below | Indicates whether the report displays the information that is above or below the threshold value. For example, if **Threshold** is set to Material Handling %, **Value** is set to 70, and **Above/Below** is set to Above, then only the time spent on material handling over 70 percent will be shown on the report. |
| Duration Count | Number of time periods, specified in the **Duration Period** field, for which to report on quality errors. |
| Duration Period | Time measurement, such as Days, Weeks, or Months, that is used with the value in the **Duration Count** field to specify the time period for which to report on quality errors. |
| Warehouse | Unique identifier associated with the warehouse. In a multi-warehouse environment, you can select the warehouse for which you are authorized. |
| Aisle Area | Unique alphanumeric identifier, one to ten characters in length, for an aisle area. An aisle area is a group of aisles that share the same characteristics. Aisle areas are defined based on the environment and characteristics of the work being performed in the aisles. |
| Aisle Area Desc | Meaningful summary identifying the purpose and use of the aisle area. |
| Supervisors | Person to whom a user reports. A supervisor manages and oversees a user's work. You can also use the supervisor's ID for easy user selection in reports, assignments, performance statistics, report cards, and payroll information. |
| Client | Unique identifier for a client who houses product within a multi-client (third-party logistics) warehouse. The client ID distinguishes one client from another and allows for effective management of activities for multiple clients in one warehouse. In Warehouse Labor Management, the client may be used both for reporting purposes and in the job code mapping process to develop individual job codes by client. |
| Customers | Unique number for the customer. A customer is the end recipient associated with an assignment. In the case of a 3PL, the customer would be the individual or organization to which product is being shipped; whereas the client is the individual or organization for which product is shipped. In Warehouse Labor Management, the customer may be used both for reporting purposes and in the job code mapping process to develop individual job codes by customer. |
| Users | Unique identifier for an individual who will be using the application, either with direct access or through an internet connection. |
| Location ID | Unique identifier assigned to a location. Each location defined in the application has a location ID. A location is a uniquely identified position within an area of the warehouse used to store, stage, or manipulate product. |
| Work Area | Unique alphanumeric identifier, 1 to 40 characters in length, for a work area. A work area defines an area of the warehouse where similar types of operations are performed. Typically, a warehouse is divided into work areas for work management purposes. |
| User Groups | Optional category into which users can be grouped for easy selection in reports, assignments, performance statistics, report cards, and payroll information. |
| Report Groups | Optional category into which users can be grouped for easy selection in reports, report cards, and payroll information. |
| Shift | Defined work period within 24 hours that may include paid and unpaid breaks. |
| Shift Category | Unique name for a group of shifts. |
| Work Teams | Optional category into which users can be grouped for easy selection in reports, assignments, performance statistics, report cards, and payroll information. |
| Work Category | Unique identifier for the work category. A work category is a method of categorizing job information for reporting and statistical purposes. A job code can be assigned to only one work category. |
| Job Codes | Identifier for the job code. A job code represents a standard for a task being performed in your facility, and it is the basic component for an assignment. |
| Job Code Desc | Meaningful summary identifying the purpose and use of the job code. |
| Subtitle | Additional descriptive information that will be displayed below the title in the generated report. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
