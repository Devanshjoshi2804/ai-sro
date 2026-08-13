---
title: "People"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/people_labor_section.htm"
source: "/content/people_labor_section.htm"
toc_path:
  - "Warehouse Labor Management"
  - "Labor"
  - "People"
sections:
  - "Employee Details"
  - "View summarized employee information"
  - "View detailed employee information"
  - "Daily Details fields"
  - "Employee Summary fields"
  - "Total Hours fields"
  - "Utilization fields"
  - "Overall Performance fields"
images:
  - "/content/resources/images/labor_home_24x24.png"
  - "/content/resources/images/laborobvs_in_process.png"
  - "/content/resources/images/labor_milestone_19x18.png"
  - "/content/resources/images/labor_home_25x25.png"
  - "/content/resources/images/expand_widget.png"
  - "/content/resources/images/expand_widget.png"
  - "/content/resources/images/labor_milestone_19x18.png"
  - "/content/resources/images/laborobvs_in_process.png"
  - "/content/resources/images/image1178163.png"
  - "/content/resources/images/image1178162.png"
  - "/content/resources/images/image1178164.png"
source_sha1: 75f174c1c0e95c2f9b010f1f572a3d27f5176c0c
---
# People

You use the following People pages to access and view labor information for one or more employees: 

-   **All Employees**: List of all employees and a summarized view of their performance, as well as each employee's supervisor.
-   **My Direct Reports**: List of employees that report to the same supervisor (the user that is currently logged in).
-   **Employee Details**: A warehouse employee's statistical utilization information and comparative performance analysis. The Employee Details page provides a collection of color-coded widgets that are useful for researching and evaluating an employee's assignment completion data for a specific period of time.
    

## Employee Details

You can use the Employee Details page to view statistical utilization information and comparative performance analysis for a warehouse employee. The Employee Details page provides a collection of color-coded widgets that are useful for researching and evaluating an employee's assignment completion data for a specific period of time.

**Note**: If you are viewing another employee's details, you can go to your personal details page by selecting **My Details** ![My Details](../../../images/resources/images/labor_home_24x24.png).

When you first access the detail page for an employee, the default date range is set to the previous 2 weeks (14 days). You can change the date range, and the filter through which the range is displayed is automatically adjusted (such as days, weeks, or months). The widgets can display a maximum of 14 days, at which point the range is displayed in weeks. For example, if you select a date range of 21 days, the range is converted and displayed as 3 weeks. The number for each displayed week relates to its yearly week number; for example, W2 refers to the second week of the year in January, and W50 refers to a week in December. If you select a date range that exceeds 31 days, then the range is converted and displayed in months. The maximum search range that can be displayed is 366 days (12 months).

**Note**: An asterisk (\*) is displayed next to a week or a month that is not complete (based on the date range selection). For example, if you select a date range of 5 full months and 1 partial month (such as January 1 to June 15), an asterisk is displayed next to June because the data does not represent the entire month.

The Employee Details page includes the following widgets:

-   **Overall Utilization**: Displays a column chart that compares the employee's performance and utilization. While performance is based on an assignment's goal time and the actual completion time, utilization refers to the percentage of paid time an employee spends on direct work (value-added activities). A higher utilization percentage indicates an effective use of the employee's time. When utilization is combined with performance, you can determine if there is a correlation between the values. For example, an employee may have a high performance value, but if that is associated with low utilization, the performance may be inflated due to a high volume of indirect (measured and unmeasured) work.
    
    **Note**: If an employee has only performed unmeasured indirect work for a data point in the chart, then the performance column is displayed as an outline at 100%. This is only to indicate that no measured work was performed; performance cannot be calculated for unmeasured tasks. Additionally, if the employee does not perform any direct work (measured or unmeasured), then utilization percentage is not displayed for the data point.
    
    You can select a data point in the column chart to view additional details such as the employee's goal time, actual time, indirect minutes, and break minutes for the time period. If the date range filter on the Employee Detail page is set to Days, then you can also view the Daily Details window.
    
    **Note**: The Daily Details window is accessible from the Total Hours and Performance widgets, in addition to the Overall Utilization widget.
    
    The Daily Details window contains a circle chart that displays the amount of time (as a percent of the employee's total time for the day) spent on work associated with different job codes. Additionally, the grid on the Daily Details window lists all of the tasks performed by the employee for that day in chronological order. You can view the start time and stop time of each task, as well as the assignment number, goal time, and performance rating, among other details. If an adjustment was added to an assignment, in the row for the assignment, the application displays an **ADJ** tag. An adjustment is the amount of unmeasured time, such as for a break or meeting, that is deducted from the assignment's actual time to more accurately reflect the actual work performance for the assignment.
    
-   **Total Hours**: Displays a column chart that divides the employee's hours into the following time categories: Measured Direct, Measured Indirect, Unmeasured Direct, and Unmeasured Indirect. This information correlates to the employee's utilization; the widget provides greater detail about the direct and indirect tasks used to calculate the percentage of time spent on value-added activities. A direct task can have a cost applied against a specific object, such as a client or customer; an indirect task does not have a cost that can be applied, such as maintenance time. A measured task has standards, so goal time and performance can be calculated; an unmeasured task does not have standards, so performance cannot be calculated.
    
    You can expand the Total Hours widget to view the detailed information for a specific data point in the column chart. In addition to the column chart, the expanded widget includes a circle chart, displayed in the lower left, with the total time breakdown over the four time categories for the date range. A second circle chart, displayed in the lower right of the expanded widget, shows the breakdown of measured direct tasks, by default. If you select a specific data point in the column chart, then the circle charts are updated to show the time breakdown for the selection. Additionally, if you select a time category in the Total circle chart (lower left), such as Unmeasured Direct, then the second circle chart is updated to show the breakdown of unmeasured direct tasks, such as cycle counting or returns processing. Each circle chart includes the percentage of the employee's total time spent on each task, as well as the actual hours, minutes, and seconds.
    
-   **Overall Performance**: Displays an area chart that compares the employee's performance (in blue) and the team's average performance (in gray). The team average is calculated using the performance of all employees that report to the same supervisor. You can use this information, for example, to determine if a low performing employee is an exception, or whether the rest of the team is also performing at a low level, which may indicate a different issue. Additionally, the chart displays an icon for each completed employee observation (![In Process](../../../images/resources/images/laborobvs_in_process.png)) and each milestone that was met (![Milestone](../../../images/resources/images/labor_milestone_19x18.png)). When you select an observation or milestone, additional information about the event is displayed, such as the milestone type or the observation template.
-   **Performance by**: Displays a bar chart that compares the employee's performance and the team's average performance, filtered by criteria, such as by job code or client. The Performance by widget is color-coded to include the performance levels associated with the performance scores that are displayed.

## View summarized employee information

1.  Perform one of the following tasks:
    -   To view the employees that report directly to you, select **Labor > People > My Direct Reports**.
        
    -   To view all employees, select **Labor > People > All Employees**.
2.  View information in the [Employee Summary fields](#Employee_summary_fields).
3.  To view detailed information for an employee, select the employee.

## View detailed employee information

1.  Perform one of the following tasks:
    -   Select **Labor > People > All Employees**, and then select an employee.
    -   Select **Labor > People > My Direct Reports**, and then select an employee.
    -   Select **Labor > People > Employee Details**.
        
        **Note**: Use this path to view the most recently accessed employee detail page or your own detail page. If you are viewing another employee's details, you can go to your personal details page by selecting **My Details** ![My Details](../../../images/resources/images/labor_home_25x25.png).
        
    -   Select **Labor > Dashboard**, and then in the **Performance** or **Observations** widget, select an employee.
2.  To change the date range for which employee information is displayed, use the date selection tool to select a new range.  
    
    **Note**: The widgets on the Employee Details page display a maximum of 14 days. For example, if you select a date range of 21 days, the range is converted and displayed as 3 weeks. The number for each displayed week relates to its yearly week number; for example, W2 refers to the second week of the year in January, and W50 refers to a week in December. If you select a date range that exceeds 31 days, then the range is converted and displayed in months. The maximum search range that can be displayed is 366 days (12 months). An asterisk (\*) is displayed next to a week or a month that is not complete (based on the date range selection).
    
    For more information, see [Employee Details](#Employee_Details_page).
    
3.  View the employee's utilization: 
    1.  In the **Overall Utilization** widget, view the following information:
        -   **Performance**: Value that represents whether the goal time for an assignment is being met. This is the employee's cumulative performance for the selected date range. Performance is calculated based on the number of goal time seconds completed and the number of actual seconds operators have spent on the assignment. Specifically, Performance = (complete goal seconds / complete seconds) x 100.
        -   **Utilization**: Value that represents the percentage of paid time the employee spends on direct tasks (value-added activities). This is the employee's cumulative utilization for the selected date range. A higher utilization percentage indicates an effective use of the employee's time. Specifically, Utilization = (direct time) / (direct time + indirect time) x 100. Paid breaks are included as part of the indirect time in utilization, whereas unpaid breaks are not included.
    2.  To view additional utilization details:
        1.  Expand ![Expand](../../../images/resources/images/expand_widget.png) the **Overall Utilization** widget.
        2.  In the column chart, select the column for a specific data point, and then view the information in the [Utilization fields](#Utilization_fields).
        3.  If the date range is displayed in days, then to view a breakdown of the amount of time spent on different job codes for the day, select **Daily Details**.
            
            **Note**: The Daily Details window contains a circle chart that displays the amount of time (as a percent of the employee's total time for the day) spent on work associated with different job codes. Additionally, the grid on the Daily Details window lists all of the tasks performed by the employee for that day in chronological order.
            
        4.  View the information in the [Daily Details fields](#Daily_details_fields).
4.  View the employee's hourly breakdown of time:
    1.  In the **Total Hours** widget, view the information in the [Total Hours fields](#Total_hours_fields).
    2.  To view additional details of the time:
        1.  Expand ![Expand](../../../images/resources/images/expand_widget.png) the **Total Hours** widget.
        2.  To view details for a specific data point, select the column.
            
            **Note**: If the date range is displayed in days, then to view a breakdown of the amount of time spent on different job codes for the day, select **Daily Details**. View the information in the [Daily Details fields](#Daily_details_fields).
            
        3.  In the **Total** circle chart, view the time breakdown for the entire date range (by percentage, hours, minutes, and seconds).
            
            **Note**: A second circle chart, displayed in the lower right of the expanded widget, shows the breakdown of measured direct tasks, by default.
            
        4.  To view the detail for a specific data point, select a column in the column chart. The circle charts are updated to show the time breakdown for the selection.
        5.  To view a job code breakdown for a specific time category, in the **Total** circle chart, select a category. The second circle chart is updated to display the job codes within the category to which the employee logged time.
5.  View the employee's performance:
    1.  In the **Overall Performance** widget, view the employee's performance (in blue) as it relates to the team's average performance (in gray). The team average is calculated using the performance of all employees that report to the same supervisor.
    2.  To view additional performance details for a data point, select the point and view the information in the [Overall Performance fields](#Overall_performance_fields).
        
        **Note**: If the date range is displayed in days, then to view a breakdown of the amount of time spent on different job codes for the day, select **Daily Details**. View the information in the [Daily Details fields](#Daily_details_fields).
        
    3.  To view a completed milestone, select ![Milestone](../../../images/resources/images/labor_milestone_19x18.png), and then view the following information: 
        -   **Type**: Value that defines the type of milestone, such as Certification or Training.
        -   **Subtype**: Value that identifies the specific milestone subtype, such as Forklift Training.
        -   **Date**: Date on which the employee completed the milestone.
    4.  To view a complete observation, select ![In Process](../../../images/resources/images/laborobvs_in_process.png), and then view the following information: 
        -   **Template**: Identifier for an observation template. A template can include job code specific questions that cover time and pace, preferred methods, safety, and equipment use.
        -   **Completion Date**: Date on which the observation was completed.
        -   **Performance**: Value that represents whether the goal time for the selected assignments in the completed observation was met. Performance is calculated based on the number of goal time seconds completed and the number of actual seconds operators have spent on the assignments. Specifically, Performance = (complete goal seconds / complete seconds) x 100.
6.  View the employee's performance filtered by criteria:
    1.  In the **Performance by** widget, from the drop-down list, select the category by which to display the employee's performance compared to the team's average performance (in gray).
    2.  View the performance information in the bar chart.
        
        **Note**: The performance rating for the employee and the team is displayed next to each respective bar; the chart key displays the designated color-coded performance levels. You define the performance levels in the Warehouse Labor Management, Labor System Configuration/Performance Level Ranges policy.
        

## Daily Details fields

 
| Field | Description |
| --- | --- |
| Performance | Value that represents whether the goal time for an assignment is being met. Performance is calculated based on the number of goal time seconds completed and the number of actual seconds operators have spent on the assignment. Specifically, Performance = (complete goal seconds / complete seconds) x 100.<br > For example, assume an assignment was supposed to take 1 hour (3600 goal time seconds), but the actual amount of time to complete the assignment was 1.25 hours (4500 seconds). Based on these numbers, the application calculates a Performance value of 80 \[(3600 / 4500) x 100 = 80\]. The application rounds decimal values for performance to the nearest whole number. A value of 100 or greater indicates that the goal time is being met or exceeded, whereas a value lower than 100 indicates that the actual work is taking longer than the expected goal time.<br > If a job is unmeasured, a performance value is not displayed. Additionally, performance is not displayed if the Warehouse Labor Management, Labor System Configuration/Enable Variance policy is disabled. |
| Total Time | Total amount of time (hours, minutes, and seconds) the employee spent on all tasks for the selected date. This includes all time from when the employee signs in to start the shift until the employee signs out at the end of the shift. The total time includes all measured and unmeasured tasks, and all direct and indirect tasks. A direct task can have a cost applied against a specific object, such as a client or customer; an indirect task does not have a cost that can be applied, such as maintenance time. A measured task has standards, so goal time and performance can be calculated; an unmeasured task does not have standards, so performance cannot be calculated. |
| Total Direct | Total amount of time (hours, minutes, and seconds) the employee spent on direct tasks for the selected date. A direct task is a work task that can have a cost applied against a specific object. Direct tasks usually refer to tasks that can be attributed to a specific customer or client. Direct tasks can be measured or unmeasured tasks. |
| Total Indirect | Total amount of time (hours, minutes, and seconds) the employee spent on indirect tasks for the selected date. An indirect task does not have a cost that can be applied against a specific object. Indirect tasks usually refer to management or maintenance time. For example, a battery change for a forklift does not directly relate to a specific client or customer. Indirect tasks can be measured or unmeasured tasks. |
| Total Break | Total amount of time (hours, minutes, and seconds) the employee spent on break for the selected date. A break is a period of time within a shift in which work is not performed. When a break is added to a shift, it eliminates the need for an employee to sign off of an assignment and its time is subtracted from the amount of time available to complete the work. |
| Assignments | Total number of assignments completed by the employee on the selected date. An assignment represents a basic unit of work that an employee performs in your facility. |
| Start Time | Actual start time for an assignment. The assignment must be in Active or Complete status for this value to be displayed. |
| Stop Time | Actual end time for an assignment. The assignment must be in Complete status for this value to be displayed. |
| Assignment | Unique identifier for an assignment. An assignment represents a basic unit of work that an employee performs in a facility. |
| Job Code | Unique identifier for a job code. A job code represents a standard for a task being performed in your facility, and it is the basic component for an assignment. |
| Goal Time | Estimated time to complete the assignment based on engineered standards. Goal time estimates are calculated by creating Future Assignments in Warehouse Labor Management. Goal time calculations should be considered estimates because they can change based on multiple factors, such as skipped picks, use of different travel sequences, and transition move travel time. |
| Actual Time | Actual amount of time it took to complete the assignment. The application uses this value to calculate user performance. Specifically, performance is calculated based on the number of goal time seconds completed and the number of actual seconds operators have spent on the assignments. |
| Direct Time | Amount of time spent on direct tasks. A direct task is a work task that can have a cost applied against a specific object. Direct tasks usually refer to tasks that can be attributed to a specific customer or client. Direct tasks can be measured or unmeasured tasks. |
| Indirect Time | Amount of time spent on indirect tasks. An indirect task is a work task that does not have a cost that can be applied against a specific object. Indirect tasks usually refer to management or maintenance time. For example, a battery change for a forklift does not directly relate to a specific client or customer. Indirect tasks can be measured or unmeasured tasks. |
| Break | Amount of time the employee spent on break. A break is a period of time within a shift in which work is not performed. When a break is added to a shift, it eliminates the need for an employee to sign off of an assignment and its time is subtracted from the amount of time available to complete the work. |

## Employee Summary fields

 
| Field | Description |
| --- | --- |
| Name | Name (Last, First) of the warehouse employee. Each warehouse employee is associated with an authorized user account; the employee's user ID is displayed after the name. |
| Supervisor | Name and user ID of the supervisor to whom the employee reports. A supervisor manages and oversees the employee's work. Only displayed when viewing all employees instead of direct reports. |
| Performance trend (icon) | Trend is displayed as an up arrow (![Positive Performance Trend](../../../images/resources/images/image1178163.png)) or down arrow (![Negative Performance Trend](../../../images/resources/images/image1178162.png)) to indicate changes in the rate of performance, or a horizontal bar (![Neutral Performance Trend](../../../images/resources/images/image1178164.png)) to indicate no change. The application calculates trend based on the performance trend window, which defines a period of time for which performance is calculated and then compared to the overall performance of the assignment.<br > **Note**: You define the trend window in the Warehouse Labor Management, Labor System Configuration/Performance Trend Window policy.<br > Specifically, Trend = \[performance during trend window\] - \[overall performance\]. If the difference is a positive value, the trend arrow points upward; if the difference is a negative value, the trend arrow points downward; if there is no difference (the value is zero 0), a horizontal bar indicates no change. For example, assume that the trend window is set at 120 minutes (2 hours), and the overall performance from the start of the assignment to the current time is 95. If the performance over the last 2 hours is 100, then the trend arrow points upward (100 - 95 = 5). |
| Performance | Value that represents whether the goal time for an assignment is being met. Performance is calculated based on the number of goal time seconds completed and the number of actual seconds operators have spent on the assignment. Specifically, Performance = (complete goal seconds / complete seconds) x 100.<br > For example, assume an assignment was supposed to take 1 hour (3600 goal time seconds), but the actual amount of time to complete the assignment was 1.25 hours (4500 seconds). Based on these numbers, the application calculates a Performance value of 80 \[(3600 / 4500) x 100 = 80\]. The application rounds decimal values for performance to the nearest whole number. A value of 100 or greater indicates that the goal time is being met or exceeded, whereas a value lower than 100 indicates that the actual work is taking longer than the expected goal time.<br > If a job is unmeasured, a performance value is not displayed. Additionally, performance is not displayed if the Warehouse Labor Management, Labor System Configuration/Enable Variance policy is disabled. |
| Direct Time | Amount of time spent on direct tasks. A direct task is a work task that can have a cost applied against a specific object. Direct tasks usually refer to tasks that can be attributed to a specific customer or client. Direct tasks can be measured or unmeasured tasks. |
| Indirect Time | Amount of time spent on indirect tasks. An indirect task is a work task that does not have a cost that can be applied against a specific object. Indirect tasks usually refer to management or maintenance time. For example, a battery change for a forklift does not directly relate to a specific client or customer. Indirect tasks can be measured or unmeasured tasks. |

## Total Hours fields

 
| Field | Description |
| --- | --- |
| Measured Direct | Amount of time spent on work tasks that have calculated standards and that can have a cost applied against a specific object. Goal time and performance calculations can be performed for job codes with measured tasks. Direct tasks usually refer to tasks that can be attributed to a specific customer or client. |
| Measured Indirect | Amount of time spent on work tasks that have calculated standards and that do not have a cost that can be applied against a specific object. Goal time and performance calculations can be performed for job codes with measured tasks. Indirect tasks usually refer to management or maintenance time. For example, a battery change for a forklift does not directly relate to a specific client or customer. |
| Unmeasured Direct | Amount of time spent on work tasks that do not have calculated standards and that can have a cost applied against a specific object. Goal time and performance calculations cannot be performed for job codes with unmeasured tasks. Direct tasks usually refer to tasks that can be attributed to a specific customer or client. |
| Unmeasured Indirect | Amount of time spent on work tasks that do not have calculated standards and that do not have a cost that can be applied against a specific object. Goal time and performance calculations cannot be performed for job codes with unmeasured tasks. Indirect tasks usually refer to management or maintenance time. For example, a battery change for a forklift does not directly relate to a specific client or customer. |

## Utilization fields

 
| Field | Description |
| --- | --- |
| Total Time | Total amount of time (hours, minutes, and seconds) the employee spent on all tasks for the selected date. This includes all time from when the employee signs in to start the shift until the employee signs out at the end of the shift. The total time includes all measured and unmeasured tasks, and all direct and indirect tasks. A direct task can have a cost applied against a specific object, such as a client or customer; an indirect task does not have a cost that can be applied, such as maintenance time. A measured task has standards, so goal time and performance can be calculated; an unmeasured task does not have standards, so performance cannot be calculated. |
| Goal Time | Estimated time to complete the assignment based on engineered standards. Goal time estimates are calculated by creating Future Assignments in Warehouse Labor Management. Goal time calculations should be considered estimates because they can change based on multiple factors, such as skipped picks, use of different travel sequences, and transition move travel time. |
| Actual Time | Actual amount of time it took to complete the assignment. The application uses this value to calculate user performance. Specifically, performance is calculated based on the number of goal time seconds completed and the number of actual seconds operators have spent on the assignments. |
| Performance | Value that represents whether the goal time for an assignment is being met. Performance is calculated based on the number of goal time seconds completed and the number of actual seconds operators have spent on the assignment. Specifically, Performance = (complete goal seconds / complete seconds) x 100.<br > For example, assume an assignment was supposed to take 1 hour (3600 goal time seconds), but the actual amount of time to complete the assignment was 1.25 hours (4500 seconds). Based on these numbers, the application calculates a Performance value of 80 \[(3600 / 4500) x 100 = 80\]. The application rounds decimal values for performance to the nearest whole number. A value of 100 or greater indicates that the goal time is being met or exceeded, whereas a value lower than 100 indicates that the actual work is taking longer than the expected goal time.<br > If a job is unmeasured, a performance value is not displayed. Additionally, performance is not displayed if the Warehouse Labor Management, Labor System Configuration/Enable Variance policy is disabled. |
| Utilization | Value that represents the percentage of paid time the employee spent on direct tasks (value-added activities). This is the employee's utilization for the selected date. A higher utilization percentage indicates an effective use of the employee's time. Specifically, Utilization = (direct time) / (direct time + indirect time) x 100. The application includes both unmeasured and measured time when calculating utilization.<br > For example, assume an employee spends 360 minutes (6 hours) on direct tasks, such as picking, putaway, and loading; also assume 120 minutes (2 hours) were spent on indirect tasks, such as safety checks and equipment cleaning. Based on these numbers, the application calculates the employee's utilization is 75% \[(360) / (360 + 120) x 100 = 75\]. |

## Overall Performance fields

 
| Field | Description |
| --- | --- |
| Goal Time | Estimated time to complete the assignment based on engineered standards. Goal time estimates are calculated by creating Future Assignments in Warehouse Labor Management. Goal time calculations should be considered estimates because they can change based on multiple factors, such as skipped picks, use of different travel sequences, and transition move travel time. |
| Actual Time | Actual amount of time it took to complete the assignment. The application uses this value to calculate user performance. Specifically, performance is calculated based on the number of goal time seconds completed and the number of actual seconds operators have spent on the assignments. |
| Performance | Value that represents whether the goal time for an assignment is being met. Performance is calculated based on the number of goal time seconds completed and the number of actual seconds operators have spent on the assignment. Specifically, Performance = (complete goal seconds / complete seconds) x 100.<br > For example, assume an assignment was supposed to take 1 hour (3600 goal time seconds), but the actual amount of time to complete the assignment was 1.25 hours (4500 seconds). Based on these numbers, the application calculates a Performance value of 80 \[(3600 / 4500) x 100 = 80\]. The application rounds decimal values for performance to the nearest whole number. A value of 100 or greater indicates that the goal time is being met or exceeded, whereas a value lower than 100 indicates that the actual work is taking longer than the expected goal time.<br > If a job is unmeasured, a performance value is not displayed. Additionally, performance is not displayed if the Warehouse Labor Management, Labor System Configuration/Enable Variance policy is disabled. |
| Team Performance | Value (average) that represents whether the goal time for an assignment is being met by the team. The team average is calculated using the performance of all employees that report to the same supervisor. Performance is calculated based on the number of goal time seconds completed and the number of actual seconds operators have spent on the assignment. Specifically, Performance = (complete goal seconds / complete seconds) x 100. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
