---
title: "Labor tab"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/labor_tab_picking.htm"
source: "/content/labor_tab_picking.htm"
toc_path:
  - "Warehouse Management"
  - "Picking"
  - "Dashboard"
  - "Labor tab"
sections:
  - "Setup when integrating with Warehouse Mangement"
  - "Planning profile"
  - "Actuals and Planning mode"
  - "Monitor labor productivity on the dashboard"
  - "Edit a labor planning profile"
  - "Labor Productivity fields"
  - "Planning Profile fields"
images:
  - "/content/resources/images/image1178162.png"
  - "/content/resources/images/image1178163.png"
  - "/content/resources/images/image1178164.png"
  - "/content/resources/images/image1182503.png"
  - "/content/resources/images/image1182504.png"
  - "/content/resources/images/image1178163.png"
  - "/content/resources/images/image1178162.png"
  - "/content/resources/images/image1178164.png"
source_sha1: b44520ecad249626931fe08c1982938cc211a200
---
# Labor tab - Picking

You can monitor labor productivity and workload progression statistics using the labor Productivity widget. The Productivity widget is available on the Picking and Outbound Planner dashboard (Labor tab) in Warehouse Management, and also on the Labor dashboard, which is available in a standalone Warehouse Labor Management instance or those integrated with Warehouse Management. The widget displays information based on the criteria associated with a planning profile.

A planning profile is a configuration that defines the search criteria for displaying workload progression statistics and planning information. Planning profiles are created in Warehouse Labor Management and can be edited through the Productivity widget in Warehouse Management.

**Note**: When you view productivity on the Picking and Outbound Planner dashboard (Labor tab), only activities that are supported by goal time functionality (picking, putaway, and replenishments, with some exceptions) can be displayed. When goal time functionality is enabled, assignments for those activities are created in Warehouse Labor Management with a status of Future and are used in goal and performance calculations. Goal time exceptions are listed in the Labor Goal Time field description. See [Warehouse Labor Management fields](../../configuration/integration/warehouse-labor-management.md).

The Productivity widget displays the following information:

-   **Performance or Variance**: Indicates whether the goal time for an assignment is being met or exceeded (value of 100 or greater for performance; value of 0 or greater for variance).
    
    **Note**: If the Warehouse Labor Management, Labor System Configuration/Enable Variance policy is enabled, variance is displayed. If disabled, performance is displayed.
    
-   **Performance trend icon**: Displayed as an arrow (![Negative Performance Trend](../../../../images/resources/images/image1178162.png) or ![Positive Performance Trend](../../../../images/resources/images/image1178163.png)) that represents the direction in which performance is trending over a defined time frame (such as the previous 2 hours); a horizontal bar (![Neutral Performance Trend](../../../../images/resources/images/image1178164.png)) means there has been no change in performance.
    
    **Note**: You define the trend window (in minutes) in the Warehouse Labor Management, Labor System Configuration/Performance Trend Window policy.
    
-   **Have**: Number of operators assigned to the work. The span of time required to complete the work is based on this value.
-   **Need**: Number of operators needed to complete the work before the end time of the planning profile.
-   **Capacity**: Amount of time (in hours) that is either in excess of what is needed (positive) or insufficient for what is needed (negative) to finish the work on time. See [Actuals and Planning mode](#Actuals_and_Planning_mode).

## Setup when integrating with Warehouse Mangement

The Productivity widget is available in standalone instances of Warehouse Labor Management without any additional setup. However, you must complete the following tasks for the Labor tab to be displayed and populated with information on the Picking and Outbound Planner dashboards. See [Labor Dashboard](../../../warehouse-labor-management/labor/labor-dashboard.md).

1.  Ensure that Warehouse Management is integrated with Warehouse Labor Management in a single instance. Also, ensure that the portal server installation that supports the combined instance includes both Warehouse Management and Warehouse Labor Management. See the Warehouse Management and Warehouse Labor Management Integration Guide.
2.  In Warehouse Management, configure Warehouse Labor Management attributes. See [Configure Warehouse Labor Management integration](../../configuration/integration/warehouse-labor-management.md).
    -   Enable Warehouse Labor Management functionality in Warehouse Management.
    -   Set the **Labor Goal Time** field in Warehouse Management to Yes.

## Planning profile

A planning profile is a configuration that defines the search criteria for displaying workload progression statistics and planning information. The method by which workload progression statistics are grouped and displayed on the Productivity widget is determined by the planning profile configuration.

Specifically, the first column displays the identifiers associated with the first **Group By** value defined in the profile. In the grid, you click an identifier to drill down to the identifiers for the next **Group By** value.

-   For example, if the identifier associated with the **Group By 1** field for the selected planning profile is Job Code, then on the Productivity widget, the column name is Job Code. Each row then represents the workload progression for a specific job code.
-   If the identifier associated with the **Group By 2** field for the same planning profile is Work Area, then on the Productivity widget, a user can click a job code to display the workload progression for the job code by work areas (the column name changes to Work Area).
-   If the identifier associated with the **Group By 3** field for the same planning profile is Customer, then on the Productivity widget, a user can click a work area to display the workload progression for the job code-specific work area by customer (the column name changes to Customer).

In this way, the labor supervisor can drill down to understand where operators are spending time and which tasks are getting delayed.

Additionally, in chart view, the planning profile's start time (or the current time, if the start time has passed) and end time are displayed in the chart's heading row.

## Actuals and Planning mode

The Productivity widget displays workload progression statistics in Actuals mode (real time) or Planning mode (simulation). The widget is accessible on the Labor Supervisor page or on the Labor tab of the Shipping and Outbound Planner dashboards.

-   **Actuals**: In Actuals mode, the widget displays read-only information for the current day using either a chart view (default) or grid view.
    
    -   **Chart**: In chart view, visual indicators (a red or green bar) identify the span of time required to complete an assignment and whether it will be completed on time. You can click an identifier to view more granular information for the work, depending on the number of levels defined in the planning profile.<br>
        
        For example, if the value in the Have column is equal to or greater than the value in the Need column, the span of time is displayed in green and ends at or before the profile end time. In a message indicates that there are no active users, it means the work was completed and there are no operators currently working on it. If a message indicates that work was not started, it means the work was not completed, and there are no operators currently working on it.
        
    -   **Grid**: In grid view, workload progression statistics are displayed as numerical data only, and you cannot navigate to different levels of information.
        
-   **Planning**: In Planning mode, you can modify the values in the Have column for the purpose of visualizing different completion times. You can also change the date or the completion time to forecast future labor assignments. Changes made in Planning mode have no effect on Actuals; they are for simulation purposes only. Based on your changes, the application updates the span of time needed to complete the work. For example, assume 2 assignments exist, one of which has too many operators and the other has too few. Prior to reassigning operators, you can simulate results by updating the number in the Have column (or adjusting the end time) until both assignments are projected to be completed prior to the end time defined in the planning profile.
    

## Monitor labor productivity on the dashboard

1.  Perform one of the following tasks:
    -   Select **Labor > Dashboard > Productivity**.
        
        **Note**: To display the quick view for productivity at the top of the dashboard, which shows overall performance, click ![Expand](../../../../images/resources/images/image1182503.png); to hide the quick view, click ![Collapse](../../../../images/resources/images/image1182504.png).
        
    -   Select **Outbound Planner > Dashboard > Labor**.
    -   Select **Picking > Dashboard > Labor**.
2.  From the **Planning Profile** drop-down list, select the planning profile to be used by the application for displaying workload progression statistics.
    
    **Note**: To set a profile that is displayed by default for the current user, after selecting the profile, click **Set as Default**.
    
3.  View information in the [Labor Productivity fields](#Labor_productivity_fields).
4.  To simulate completion times based on the number of assigned operators:
    
    **Note**: Changes made in Planning mode have no effect on Actuals; they are for simulation only.
    
    1.  Click **View Planning**.
    2.  To change the end time of the planning profile, from the **Complete By** drop-down list, select a new time.
    3.  To forecast productivity for a future date, use the date selection tool to select the date.
    4.  In the **Have** column, enter the number of operators to assign, and view the simulated completion times.
        
        **Note**: In Planning mode, the value in parentheses next to the Have column name represents the number of operators available to assign; a negative number means you have assigned more operators than you have. The values below the Have column name represent the number of operators assigned and the number of operators available to assign. For example, assume the column title is Have (-1) 11/10. This means that you have assigned 11 operators, but you only have 10. The (-1) value indicates that you have assigned an operator that you do not currently have.
        

## Edit a labor planning profile

1.  Perform one of the following tasks:
    -   Select **Labor > Dashboard > Productivity**.
    -   Select **Outbound Planner > Dashboard > ** **Labor**.
    -   Select **Picking > Dashboard > ** **Labor**.
2.  From the **Planning Profile** drop-down list, select the planning profile to edit.
3.  Click **Edit**.
4.  Enter information in the [Planning Profile fields](#Planning_profile_fields).
5.  To maintain advanced filters:
    
    **Note**: An advanced filter configuration defines workload grouping criteria values for the planning profile. Workload grouping criteria values are used to filter the amount of statistical and planning information that is displayed (for example, for a particular job code or customer).
    
    1.  Perform one of the following tasks:
        -   To add a filter, from the **Actions** drop-down list, select **Add Advanced Filter**.
        -   To modify a filter, in the grid, click the value in the **Field** column.
    2.  From the **Field** drop-down list, select the workload grouping criteria for which to define values.
    3.  Perform one of the following tasks:
        -   To select a range of workload grouping criteria values, select **Select by Range** and then enter information in the **From** and **To** fields.
            
            **Note**: The fields represent the first and last values in a range of values for the workload grouping filter. For example, if you have aisle areas defined in sequence, then these values can be the first and last aisle areas in the range for which you want to view statistics and planning information.
            
        -   To select specific criteria values, select **Specific Selections**, and then in the grid, select the rows for the values by which to filter the workload grouping category.
    4.  Click **Save**.
6.  Click **Save**.

## Labor Productivity fields

 
| Field | Description |
| --- | --- |
| Performance | Value that represents whether the goal time for an assignment is being met. Performance is calculated based on the number of goal time seconds completed and the number of actual seconds operators have spent on the assignment. Specifically, Performance = (complete goal seconds / complete seconds) x 100.<br > For example, assume an assignment was supposed to take 1 hour (3600 goal time seconds), but the actual amount of time to complete the assignment was 1.25 hours (4500 seconds). Based on these numbers, the application calculates a Performance value of 80 \[(3600 / 4500) x 100 = 80\]. The application rounds decimal values for performance to the nearest whole number. A value of 100 or greater indicates that the goal time is being met or exceeded, whereas a value lower than 100 indicates that the actual work is taking longer than the expected goal time.<br > If a job is unmeasured, a performance value is not displayed. Additionally, performance is not displayed if the Warehouse Labor Management, Labor System Configuration/Enable Variance policy is disabled. |
| Variance | Amount of variance from the baseline percentage against the goal time. The baseline percentage is always 100, so a variance of 0 means that the goal time is being met as expected (100%). However, a variance of -10 indicates that work is being completed at a rate 10% lower than expected; or in other words, that operators are performing at rate of 90% of the expected output relative to the goal time. Alternatively, a variance of 5 indicates that work is being completed 5% faster than expected.<br > This column is only displayed if the Warehouse Labor Management, Labor System Configuration/Enable Variance policy is enabled. |
| Performance trend (icon) | Trend is displayed as an up arrow (![Positive Performance Trend](../../../../images/resources/images/image1178163.png)) or down arrow (![Negative Performance Trend](../../../../images/resources/images/image1178162.png)) to indicate changes in the rate of performance, or a horizontal bar (![Neutral Performance Trend](../../../../images/resources/images/image1178164.png)) to indicate no change. The application calculates trend based on the performance trend window, which defines a period of time for which performance is calculated and then compared to the overall performance of the assignment.<br > **Note**: You define the trend window in the Warehouse Labor Management, Labor System Configuration/Performance Trend Window policy.<br > Specifically, Trend = \[performance during trend window\] - \[overall performance\]. If the difference is a positive value, the trend arrow points upward; if the difference is a negative value, the trend arrow points downward; if there is no difference (the value is zero 0), a horizontal bar indicates no change. For example, assume that the trend window is set at 120 minutes (2 hours), and the overall performance from the start of the assignment to the current time is 95. If the performance over the last 2 hours is 100, then the trend arrow points upward (100 - 95 = 5). |
| Have | Number of active operators currently working on the assignment. A value is displayed in each assignment row, and the column heading value equals the sum of all active operators (sum of all values in the Have column) across all assignments for the planning profile.<br > In Planning mode, the value in parentheses next to the Have column name represents the number of operators available to assign; a negative number means you have assigned more operators than you have available. The values below the Have column name represent the number of operators assigned and the number of operators available to assign. For example, assume the column title is Have (-1) 11/10. This means that you have assigned 11 operators, but you only have 10. The (-1) value indicates that you have assigned an operator that you do not currently have. |
| Need | Number of operators needed to complete the assignment by the planning profile's end time. This value is calculated by the application using the number of goal time hours for the assignment, the number of hours defined in the profile, and the allotted break time. Specifically, Need = goal time / (profile hours - break time). For example, assume the goal time for an assignment is 16 hours, the profile's start to end time is 9 hours, and the profile break time is 60 minutes. Based on these values, the application calculates a Need quantity of 2, as a result of 16 / (9 - 1). The application rounds decimal values for this field to one decimal. For example, a calculated need of 1.485 is rounded and displayed as 1.5. |
| Capacity (hrs) | Number of hours for an assignment that are available to reassign (positive, displayed in green) or need to be accounted for (negative, displayed in red). The application calculates capacity based on the end time of the selected profile, the calculated completion time of the assignment, and the number active operators on the assignment. Specifically, Capacity = \[(profile end time - completion time) x (Have)\]. For example, assume the profile end time is 5 P.M., the calculated completion time of the assignment is 6 P.M., and there are currently 2 active operators (Have column). Based on these values, the capacity shortage is -2 \[(5 - 6) x 2 = -2\], which means you must account for 2 hours of labor in order to complete the assignment on time. Alternatively, if the end time is 5 P.M. and the calculated completion time is 2 P.M. with 2 active operators, then you have a capacity overage of 6 hours to reassign to other assignments as needed \[(5 - 2) x 2 = 6\].<br > The column heading value for capacity represents the collective capacity across all assignments for the profile. Using the aforementioned examples, the heading value for the two assignments is 4 hours (-2 + 6 = 4). If an assignment is not started or has no active operators, then the capacity is displayed as a negative value, which represents the number of hours needed to complete the assignment by the end time of the planning profile. |

## Planning Profile fields

 
| Field | Description |
| --- | --- |
| Start Time | Anticipated start time to determine available labor resources. |
| Complete by Time | Anticipated end time to determine available labor resources. |
| Break Minutes Calculation Mode | Type of break minutes used to calculate statistical information.<br>-   •
    
    **Use Break Minutes**: The number entered in the **Break Minutes** field is used.
    
    <br>
<br>-   •
    
    **Use Shift**: The number of break minutes from the shift that is selected in the **Shift** field is used.
    
    <br> |
| Break Minutes | Total number of minutes allotted for breaks. Only available when **Break Minutes Calculation Mode** is set to Use Break Minutes. |
| Shift | Name that identifies a shift. A shift is a defined work period within 24 hours that may include paid and unpaid breaks. Only available when **Break Minutes Calculation Mode** is set to Use Shift. |
| Group By 1 - Group By 3 | Workload grouping by which the information will be organized (for example, by job code or customer). You can have up to three levels of grouping. Only applicable when the planning profile is used for viewing workload progression statistics. |
| Report Date at Start of Shift | Indicates that for shifts crossing midnight, the shift start date will be used as the report date. The setting for this field will override the settings for schedules referenced when viewing workload progression statistical information. Only applicable when the planning profile is used for viewing workload progression statistics. |
| Include Prior Dates | Indicates that the application will include future assignments with a plan date prior to the report date. Only applicable when the planning profile is used for viewing workload progression statistics. |
| Days to Include | Number of days prior to the report date for which the application will look for and include future assignments. Only applicable when the planning profile is used for viewing workload progression statistics and when the **Include Prior Dates** check box is selected. |
| Performance Percentage | Type of performance percentage used to calculate the statistical information. Only applicable when the planning profile is used for viewing workload progression statistics.<br>-   • **Use Current**: The current performance percentage will be used.
<br>-   • **Use Job Code**: The job code performance percentage (**Statistics Percent** field) value will be used.
<br>-   • **Use Report Card**: The report card performance percentage value will be used.
<br>-   • **User-Entered Values**: The number entered in the **Value** field will be used.
<br > Performance percentage and unmeasured percentage are used to calculate the number of workload seconds (time to complete the work). Specifically, Workload Seconds = \[Performance Seconds\] / \[1 - (Unmeasured Percentage / 100)\]. In this equation, Performance Seconds = \[goal time seconds\] x (100 / Performance percentage).<br > For example, assume the goal time for an assignment is 3600 seconds (1 hour), and the planning profile is configured with a performance percentage of 80 and an unmeasured percentage of 50. The application calculates the workload as 9000 seconds.<br>-   • Performance seconds = 3600 x (100 / 80) = 4500
<br>-   • Workload seconds = 4500 / \[1 - (50 / 100)\] = 9000
<br > The time required to complete the assignment in the selected planning profile is 2.5 hours \[(9000 / 60) / 60\].<br > A higher performance percentage means the number of workload seconds (time to complete the work) is reduced; a higher unmeasured percentage means an increase in the number of workload seconds. |
| Unmeasured Percentage | Type of unmeasured percentage information used to calculate the statistical information.<br>-   • **Use Current**: The current unmeasured task value will be used.
<br>-   • **Use Job Code**: The job code unmeasured percentage (**Statistics Percent** field) value will be used.
<br>-   • **Use Report Card**: The report card performance percentage value will be used.
<br>-   • **User-Entered Values**: The number entered in the **Value** field will be used.
<br > Performance percentage and unmeasured percentage are used to calculate the number of workload seconds (time to complete the work). Specifically, Workload Seconds = \[Performance Seconds\] / \[1 - (Unmeasured Percentage / 100)\]. In this equation, Performance Seconds = \[goal time seconds\] x (100 / Performance percentage).<br > For example, assume the goal time for an assignment is 3600 seconds (1 hour), and the planning profile is configured with a performance percentage of 80 and an unmeasured percentage of 50. The application calculates the workload as 9000 seconds.<br>-   • Performance seconds = 3600 x (100 / 80) = 4500
<br>-   • Workload seconds = 4500 / \[1 - (50 / 100)\] = 9000
<br > The time required to complete the assignment in the selected planning profile is 2.5 hours \[(9000 / 60) / 60\].<br > A higher performance percentage means the number of workload seconds (time to complete the work) is reduced; a higher unmeasured percentage means an increase in the number of workload seconds. |
| Value | Performance percentage or unmeasured percentage that will be used when calculating the statistical information. Only available when **Performance Percentage** is set to User Entered Values or **Unmeasured Percentage** is set to User Entered Values. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
