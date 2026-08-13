---
title: "Labor Performance widget"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/labor_performance_widget.htm"
source: "/content/labor_performance_widget.htm"
toc_path:
  - "Warehouse Labor Management"
  - "Labor"
  - "Labor Dashboard"
  - "Labor Performance widget"
sections:
  - "Summary chart"
  - "Grid view"
  - "Monitor labor performance on the dashboard"
  - "Add a user observation"
  - "Labor Performance Summary fields"
  - "Labor Performance Detail fields"
  - "Observation fields"
images:
  - "/content/resources/images/labor_pending_approval.png"
  - "/content/resources/images/image1178162.png"
  - "/content/resources/images/image1178163.png"
  - "/content/resources/images/image1178164.png"
  - "/content/resources/images/labor_addobservation.png"
  - "/content/resources/images/image1182503.png"
  - "/content/resources/images/image1182504.png"
  - "/content/resources/images/image1182340.png"
  - "/content/resources/images/labor_addobservation.png"
  - "/content/resources/images/labor_addobservation.png"
  - "/content/resources/images/image1178163.png"
  - "/content/resources/images/image1178162.png"
  - "/content/resources/images/image1178164.png"
source_sha1: 17f5e7bfe1ed19c510a2a28c27e11226be40868a
---
# Labor Performance widget

You can monitor user performance statistical information at the summary and detail levels using the labor Performance widget. Performance statistics let supervisors (or other authorized users) examine a user’s assignment completion information (such as the goal, measured, unmeasured, direct, and indirect) and the actual performance percentage. The performance information viewed at the detail or the summary level is displayed in hours, minutes, and seconds. The detail level also provides the identifier for the job code.

The Performance widget displays information using a summary chart and a detailed grid view. The chart and the grid view are dynamic in that the information in the grid view changes based on the performance level selected in the chart. You can filter by assignment attributes (such as by job code, user, and shift), and the chart and grid view will display information only relevant to the search. Additionally, the performance widget displays information for the current date, or you can use the date selection tool to view information for a past date.

## Summary chart

The summary chart displays high level performance information for all users that are working (or worked) on an assignment for the selected date range. The information in the chart changes based on whether you apply a filter or execute a search. The chart is divided into the following configurable, color-coded performance levels:

-   Exceptional High
-   Above Expectation
-   Meets Expectation
-   Below Expectation
-   Exceptional Low

**Note**: You define the performance levels in the Warehouse Labor Management, Labor System Configuration/Performance Level Ranges policy.

Each performance level represented in the summary chart displays the number of users that are performing at that level. You can click an area of the chart summary (a performance level) to view detailed information in the grid that relates only to the users at the specific performance level you selected.

The Performance widget quick view at the top of the Labor dashboard displays the number of users in three grouped performance levels from the summary chart: Above (includes Exceptional High and Above Expectation), Meets (includes Meets Expectation), and Below (includes Below Expectation and Exceptional Low).

## Grid view

The grid view of the Performance widget displays detailed information for all users that are working (or worked) on an assignment for the selected date range. The information in the grid view changes based on whether a specific performance level is selected in the summary chart, or if you apply a filter or execute a search.

**Note**: When you expand a row in the grid view, if an employee has logged indirect time and it has not been approved, the pending-approval icon ![Pending Approvals](../../../../images/resources/images/labor_pending_approval.png) is displayed next to the indirect job code. You can click the icon to display the Approvals widget filtered for the specific user and job code, where you can approve, reject, or adjust indirect time. The icon is also an indication that a user's performance is tentative and based on time that has not yet been approved.

The grid view displays the following information:

-   **User**: Unique identifier for a user, and the user's last and first name. Additionally, the user's picture may be displayed.
-   **Performance or Variance**: Indicates whether the goal time for an assignment is being met or exceeded (value of 100 or greater for performance; value of 0 or greater for variance). The value displayed in the parent row for a user is the performance or variance for all of the user's assignments; you can expand a user's row to view the performance or variance for each specific job code.
    
    **Note**: If the Warehouse Labor Management, Labor System Configuration/Enable Variance policy is enabled, variance is displayed. If disabled, performance is displayed.
    
-   **Performance trend icon**: Displayed as an arrow (![Negative Performance Trend](../../../../images/resources/images/image1178162.png) or ![Positive Performance Trend](../../../../images/resources/images/image1178163.png)) that represents the direction in which performance is trending over a defined time frame (such as the previous 2 hours); a horizontal bar (![Neutral Performance Trend](../../../../images/resources/images/image1178164.png)) means there has been no change in performance.
    
    **Note**: You define the trend window (in minutes) in the Warehouse Labor Management, Labor System Configuration/Performance Trend Window policy.
    
-   **Direct minutes**: Number of minutes spent on direct tasks for the assignment, such as picking or loading.
-   **Indirect minutes**: Number of minutes spent on indirect tasks for the assignment, such as changing the battery for an RF device.
-   **Break**: Number of minutes a user spent on break, which is a period of time within a shift in which work is not performed.
-   **Direct report**: Indicates whether the user directly reports to the user that is logged in to the application.
-   **Observation Status**: Status of an observation for the user. An observation can be in the following statuses: Pending, In Process, Observed, Completed.
    
    **Note**: You can create an observation for a user by clicking the ![Add observation](../../../../images/resources/images/labor_addobservation.png) icon in the row for the user. See [Add a user observation](#Add_a_user_observation).
    

## Monitor labor performance on the dashboard

1.  Select **Labor > Dashboard > Performance**.
2.  View the following information in the performance quick view:
    
    **Note**: To display the quick view, click ![Toggle Down](../../../../images/resources/images/image1182503.png); to hide the quick view, click ![Toggle Up](../../../../images/resources/images/image1182504.png).
    
    -   **Above**: Number of users performing at the Exceptional High and Above Expectation performance levels.
    -   **Meets**: Number of users performing at the Meets Expectation performance level.
    -   **Below**: Number of users performing at the Below Expectation and Exceptional Low performance levels.
3.  To limit the information that is displayed, enter search criteria; to view performance information for a previous date, select a date using the date selection tool.
    
    **Note**: It is recommended that date range searches for performance do not exceed a maximum of 31 days to prevent delayed processing times.
    
4.  To view performance summary information:
    1.  If the summary chart is not displayed, click **Summary** to display the chart.
    2.  View the information in the [Labor Performance Summary fields](#Labor_performance_summary_fields).
    3.  To view information for users in a specific performance level, click the area of the chart that correlates to the performance level. The grid view is updated and displays information only relevant to the selected performance level.
        
        **Note**: The displayed name for the chart updates to reflect the performance level selected. For example, if you select the area of the chart for Meets Expectation, the name that is displayed for the chart is changed from Summary to Meets Expectation.
        
5.  To minimize the chart (maximize the grid view), click ![Collapse](../../../../images/resources/images/image1182340.png).
6.  To view detailed performance information:
    1.  In the grid, view information in the [Labor Performance Detail fields](#Labor_performance_detail_fields).
    2.  To view job-specific details for a user, expand the row, and then view the information.
        
        **Note**: The value displayed for a column in the parent row for a user is the cumulative value for all of the user's assignments; you can expand a user's row to view the values for each specific job code.
        

## Add a user observation

1.  Perform one of the following actions:
    -   To add an observation from the Observations widget:
        1.  Select **Labor > Dashboard > Observations**.
        2.  Click **Add**.
        
        **Note**: With search results displayed, you can add an observation for a specific user by clicking ![Add observation](../../../../images/resources/images/labor_addobservation.png), which is displayed in the user's grid row.
        
    -   To add an observation from the Performance widget:
        1.  Select **Labor > Dashboard > Performance**.
        2.  In the grid view, in the row for the user for which you want to create an observation, click ![Add observation](../../../../images/resources/images/labor_addobservation.png).
            
            **Note**: If the icon is displayed in red, that indicates the user's performance is below expectation.
            
2.  Enter information in the [Observation fields](#Observation_fields).
3.  Perform one of the following tasks:
    -   To perform the observation, click **Next**. The Perform page is displayed and the observation's status is updated to In Process. See [Perform a user observation](labor-observations-widget.md).
    -   To leave the observation in a Pending status to be performed later, click **Save and Exit**.

## Labor Performance Summary fields

 
| Field | Description |
| --- | --- |
| Exceptional High | Number (or percentage) of users that are performing within the range configured for the Exceptional High performance level. The number of users in each level is displayed in the designated color-coded pieces in the summary chart. The summary chart key displays the percentage of users that are performing at each specific level, and also the performance ranges that are configured for each level. For example, Exceptional High 5% (121-999).<br > **Note**: You define the performance levels in the Warehouse Labor Management, Labor System Configuration/Performance Level Ranges policy. |
| Above Expectation | Number (or percentage) of users that are performing within the range configured for the Above Expectation performance level. The number of users in each level is displayed in the designated color-coded pieces in the summary chart. The summary chart key (below the chart) displays the percentage of users that are performing at each specific level, and also the performance ranges that are configured for each level. For example, Above Expectation 20% (101-120).<br > **Note**: You define the performance levels in the Warehouse Labor Management, Labor System Configuration/Performance Level Ranges policy. |
| Meets Expectation | Number (or percentage) of users that are performing within the range configured for the Meets Expectation performance level. The number of users in each level is displayed in the designated color-coded pieces in the summary chart. The summary chart key (below the chart) displays the percentage of users that are performing at each specific level, and also the performance ranges that are configured for each level. For example, Meets Expectation 60% (90-100).<br > **Note**: You define the performance levels in the Warehouse Labor Management, Labor System Configuration/Performance Level Ranges policy. |
| Below Expectation | Number (or percentage) of users that are performing within the range configured for the Below Expectation performance level. The number of users in each level is displayed in the designated color-coded pieces in the summary chart. The summary chart key (below the chart) displays the percentage of users that are performing at each specific level, and also the performance ranges that are configured for each level. For example, Below Expectation 10% (80-89).<br > **Note**: You define the performance levels in the Warehouse Labor Management, Labor System Configuration/Performance Level Ranges policy. |
| Exceptional Low | Number (or percentage) of users that are performing within the range configured for the Exceptional Low performance level. The number of users in each level is displayed in the designated color-coded pieces in the summary chart. The summary chart key (below the chart) displays the percentage of users that are performing at each specific level, and also the performance ranges that are configured for each level. For example, Exceptional Low 5% (0-79).<br > **Note**: You define the performance levels in the Warehouse Labor Management, Labor System Configuration/Performance Level Ranges policy. |

## Labor Performance Detail fields

 
| Field | Description |
| --- | --- |
| User | Unique identifier for the user, and the user's last and first name, that is assigned to perform the work. Additionally, the user's picture may be displayed. |
| Performance | Value that represents whether the goal time for an assignment is being met. Performance is calculated based on the number of goal time seconds completed and the number of actual seconds operators have spent on the assignment. Specifically, Performance = (complete goal seconds / complete seconds) x 100.<br > For example, assume an assignment was supposed to take 1 hour (3600 goal time seconds), but the actual amount of time to complete the assignment was 1.25 hours (4500 seconds). Based on these numbers, the application calculates a Performance value of 80 \[(3600 / 4500) x 100 = 80\]. The application rounds decimal values for performance to the nearest whole number. A value of 100 or greater indicates that the goal time is being met or exceeded, whereas a value lower than 100 indicates that the actual work is taking longer than the expected goal time.<br > If a job is unmeasured, a performance value is not displayed. Additionally, performance is not displayed if the Warehouse Labor Management, Labor System Configuration/Enable Variance policy is disabled. |
| Variance | Amount of variance from the baseline percentage against the goal time. The baseline percentage is always 100, so a variance of 0 means that the goal time is being met as expected (100%). However, a variance of -10 indicates that work is being completed at a rate 10% lower than expected; or in other words, that operators are performing at rate of 90% of the expected output relative to the goal time. Alternatively, a variance of 5 indicates that work is being completed 5% faster than expected.<br > This column is only displayed if the Warehouse Labor Management, Labor System Configuration/Enable Variance policy is enabled. |
| Performance trend (icon) | Trend is displayed as an up arrow (![Positive Performance Trend](../../../../images/resources/images/image1178163.png)) or down arrow (![Negative Performance Trend](../../../../images/resources/images/image1178162.png)) to indicate changes in the rate of performance, or a horizontal bar (![Neutral Performance Trend](../../../../images/resources/images/image1178164.png)) to indicate no change. The application calculates trend based on the performance trend window, which defines a period of time for which performance is calculated and then compared to the overall performance of the assignment.<br > **Note**: You define the trend window in the Warehouse Labor Management, Labor System Configuration/Performance Trend Window policy.<br > Specifically, Trend = \[performance during trend window\] - \[overall performance\]. If the difference is a positive value, the trend arrow points upward; if the difference is a negative value, the trend arrow points downward; if there is no difference (the value is zero 0), a horizontal bar indicates no change. For example, assume that the trend window is set at 120 minutes (2 hours), and the overall performance from the start of the assignment to the current time is 95. If the performance over the last 2 hours is 100, then the trend arrow points upward (100 - 95 = 5). |
| Goal Time | Estimated time to complete the assignment based on engineered standards. Goal time estimates are calculated by creating Future Assignments in Warehouse Labor Management. Goal time calculations should be considered estimates because they can change based on multiple factors, such as skipped picks, use of different travel sequences, and transition move travel time. |
| Direct Time | Amount of time spent on direct tasks. A direct task is a work task that can have a cost applied against a specific object. Direct tasks usually refer to tasks that can be attributed to a specific customer or client. Direct tasks can be measured or unmeasured tasks. |
| Indirect Time | Amount of time spent on indirect tasks. An indirect task is a work task that does not have a cost that can be applied against a specific object. Indirect tasks usually refer to management or maintenance time. For example, a battery change for a forklift does not directly relate to a specific client or customer. Indirect tasks can be measured or unmeasured tasks. |
| Break | Amount of time the user spent on break. A break is period of time within a shift in which work is not performed. You can add a break at a specific time and define the length of the break (in minutes) in a shift configuration, and the break value will be displayed in this field at the time it occurs. For example, if a shift is from 8 A.M. to 5 P.M. with a configured break at 12 P.M. for 30 minutes, then the break time would not be displayed in this field at 10 A.M. However, if an assignment has as start time of 11:45 A.M. and an end time of 1:00 P.M., then the application adjusts the assignment to include the break time, which is displayed in this field. You can also add an adjustment for a break to an assignment using Assignment Operations. |
| Direct Report | Indicates whether the user performing the assignment reports directly to the user that is logged in to the application. A check mark is displayed in this field if the user is a direct report. |
| Measured | Amount of time spent on measured tasks for the assignment. A measured task is a work task that has calculated standards. Goal time and performance calculations can be performed for job codes with measured tasks. Measured tasks can be direct or indirect tasks. |
| Unmeasured | Amount of time spent on unmeasured tasks for the assignment. An unmeasured task is a work task that does not have calculated standards. Goal time and performance calculations cannot be performed for job codes with unmeasured tasks. Unmeasured tasks can be direct or indirect tasks. |
| Curve Expectation | Value for the expected performance or variance of a user based on one or more defined learning curves. A learning curve, associated with either a user or a job code, enables you to hold a user to a lower expectation and gradually increase expected performance based on the number of calendar days.<br > **Note**: If the Warehouse Labor Management, Labor System Configuration/Enable Variance policy is enabled, variance is displayed. If disabled, performance is displayed.<br > The curve expectation can be calculated based on one or more learning curves. For example, if a user is working on assignments associated with job codes that are assigned to multiple learning curves, this value is the cumulative expectation derived from all of the defined curves.<br > Total goal time and total expected goal time are used to calculate the curve expectation. Specifically, Curve Expectation = Total Goal Time / Total Expected Goal Time. In this equation, Total Expected Goal Time = (100 x \[Goal Time\]) / \[Expected Performance defined in the learning curve\].<br > For example, assume a user has two assignments, each with a goal time of 3600 seconds (1 hour), and each for a job code associated with a different learning curve expected performance of 75 and 80. The application calculates the curve expectation as 77.<br>-   • Total Goal Time = 3600 x 2 = 7200
<br>-   • Total Expected Goal Time = 4800 + 4500 = 9300
    -   • Assignment 1 expected goal time = (100 x 3600) / 75 = 4800
    <br>-   • Assignment 2 expected goal time = (100 x 3600) / 80 = 4500
    <br>
<br>-   • Curve Expectation = 7200 / 9300 = 77 (rounded to nearest whole number)
<br > **Note**: Learning curves (expected performance) and assignments (goal times) are maintained in Warehouse Labor Management. |
| Status | Current status of the observation.<br>-   • **Pending**: The observation has been created or scheduled but has not been started.
<br>-   • **In Process**: The observation has been started but not fully performed.
<br>-   • **Observed**: The observation has been fully performed but has not been completed.
<br>-   • **Completed**: The observation is complete. |
| Units/Hour | Average number of units processed per hour for all job codes performed by an employee. This value relates to the productivity and performance of an employee when compared to the baseline units per hour for a job code. The specific unit refers to the **Reporting Unit** as defined for the job code, and this value is the average of all units for all job codes an employee performs. The Units Per Hour Calculation policy determines how the application calculates this value, which is either by direct hours (time spent on direct tasks) or by total paid hours (direct or indirect time). For example, if an employee performs 75 case picks in 2 hours and 25 pallet picks in 2 hours, then the units per hour is calculated as 25, the result of \[(75 + 25) / (2 + 2)\]. The **Units/Hour** field is also displayed on the Summary Report and the Daily Details Report. |
| Job Code Units/Hour | Average number of units processed per hour for a single job code, such as 50 cases (picked) per hour. This value relates to the productivity and performance of an employee when compared to the baseline units per hour for a job code. The specific unit refers to the **Reporting Unit** as defined for the job code. The Units Per Hour Calculation policy determines how the application calculates this value, which is either by direct hours (time spent on direct tasks) or by total paid hours (time spent on direct and indirect tasks). For example, if an employee performs 75 case picks in 2 hours, then the units per hour is calculated as 38, the result of (75 / 2) rounded up. The **Job Code Units/Hour** field is also displayed on the Summary Report and the Daily Details Report. |

## Observation fields

 
| Field | Description |
| --- | --- |
| User | Unique identifier and name of the employee to be observed. |
| Observation Supervisor | Name of the supervisor responsible for performing the observation. |
| Job Code | Unique identifier for the job that is to be (or was) observed. Job codes are essentially a representation of all of the tasks being performed in your facility, and are the basic component of an assignment.<br > **Note**: The application does not validate the selected job code for the observation against the job code for the assignment. |
| Template | Identifier for an observation template. A template can include job code specific questions that cover time and pace, preferred methods, safety, and equipment use. User observation templates are maintained in Observation Template Maintenance, available in the SCE client. |
| Due Date | Date by which the scheduled observation should be completed. By default, the application sets the due date to the current date plus 7 days. You can change the date on which an observation is due by updating this value (before the observation is performed), and you can change the default number of days to complete an observation in the SCE client (Labor System Configuration/Days to Complete an Observation policy). |
| Time Frame | Method by which the time period for an observation is defined. When completing an observation, all of the assignments that were completed during the time period are included in performance calculations. However, you can modify the start and stop times of an observation, and the assignments that are included in the observation, after the observation has been performed (but prior to its completion).<br>-   • **Record Time**: Indicates that the supervisor will manually start and stop the timer at the beginning and end of an observation. If you select this value, then on the Perform page of an in-process observation, the supervisor can click **Start Timer** and **Stop Timer** to set the time frame.
<br>-   • **Start Time/Stop Time**: Indicates that the observation will begin and end on the dates and times defined in the **Start Time** and **Stop Time** fields.
<br>-   • **Assignment**: Indicates that the observation is to be performed only during the defined assignment. If you select this value, then the start and stop times cannot be modified. Additionally, if multiple assignments are associated with an assignment number, then the application prompts for additional details to identify the specific assignment. |
| Indicator | Application-generated letter that is used to designate a split or merged assignment. When multiple assignments are associated with the same assignment number, then you can specify an indicator to identify the specific assignment. If the **Indicator** and **Plan Date** fields are available and no values are defined, then all of the assignments associated with the number are included in the observation. |
| Plan Date | Date on which an assignment is scheduled to be performed. If multiple assignments are associated with the same assignment number, then you can specify an indicator or a plan date to identify the specific assignment. If the **Indicator** and **Plan Date** fields are available and no values are defined, then all of the assignments associated with the number are included in the observation. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
