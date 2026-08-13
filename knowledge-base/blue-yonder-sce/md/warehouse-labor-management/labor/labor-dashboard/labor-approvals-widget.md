---
title: "Labor Approvals widget"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/labor_approvals_widget.htm"
source: "/content/labor_approvals_widget.htm"
toc_path:
  - "Warehouse Labor Management"
  - "Labor"
  - "Labor Dashboard"
  - "Labor Approvals widget"
sections:
  - "Approve unmeasured time"
  - "Adjust unmeasured time"
  - "Reject unmeasured time"
  - "Sign on a user to an unmeasured task"
  - "View approval history"
  - "View rejected unmeasured time requests"
  - "Approval History fields"
  - "Daily Details fields"
  - "Rejected Time fields"
images:
  - "/content/resources/images/labor_approve_time.png"
  - "/content/resources/images/labor_adjust_time.png"
  - "/content/resources/images/labor_reject_time.png"
  - "/content/resources/images/labor_approve_time.png"
  - "/content/resources/images/labor_adjust_time.png"
  - "/content/resources/images/labor_reject_time.png"
source_sha1: ae22b550525c9c33b02fa83b897ed4db8e47422d
---
# Labor Approvals widget

You can view and manage unmeasured time approval requests using the labor Approvals widget. Requests for unmeasured time are made when a user signs on to an assignment which has a job code set up as an unmeasured task, and that job code is configured to require approval. Unmeasured tasks are tasks that do not have calculated standards, such as performing clean-up activities, attending meetings, or fixing a machine. The application provides functionality where users can request unmeasured tasks, and then supervisors approve, adjust, or reject the unmeasured time for these requests. You can also manually sign on users to unmeasured time to bypass the typical approval process. This functionality may be used in cases when it is inefficient to have all users sign on before starting a task such as an unplanned clean-up activity. The configuration settings for a job code determine whether a task is unmeasured.

Users can also request unmeasured time on the [Log Indirect Work](../../../warehouse-management/shared-functions/log-indirect-work.md) page. When requests require approval, the user is credited with the time for the unmeasured task and an assignment or adjustment is created in a pending approval state. The user’s supervisor is notified of the pending request, either through an Event Management event or from the dashboard widget; the Approvals widget quick view at the top of the Labor Dashboard displays the number of pending approvals.

**Note**: The Labor System Configuration/Convert Approved Requests to Adjustments policy determines whether pending unmeasured assignment requests will be converted to adjustments upon approval. Converting to an adjustment applies the unmeasured time to the assignment that was in Active status at the start time of the adjustment; not converting keeps the unmeasured time as a separate assignment. See the information on the Convert Approved Requests to Adjustments policy in the _Supply Chain Execution Help_.

The Approvals widget displays the following tags for unmeasured time requests:

-   **ADJ**: The unmeasured time is an adjustment request received through an Integrator transaction from an external system, such as a time-tracking system. Unmeasured time recorded at a workstation or using an RF device is created as an assignment record, and external unmeasured time requests are created as adjustment records.
-   **Active**: The assignment is currently being performed and does not have a stop time. Assignments with this tag cannot be approved and adjusted; however, active unmeasured time can be approved if it is not converted to an adjustment. Assignments with this tag can also be rejected.

In the widget grid, you can expand the row for a user to display each pending unmeasured time request that was submitted. In the row for each request for a user, you can click Daily Details to view detailed assignment information, and the unmeasured time request is highlighted in the daily details grid. You can also click View History to access the approval history by job code for a specific user. Additionally, in the row for each unmeasured time request pending approval, you can use the following icons to perform actions:

-   **Approve** ![Approve](../../../../images/resources/images/labor_approve_time.png): Processes the unmeasured time request and moves it out of the pending state. Depending on the Labor System Configuration/Convert Approved Requests to Adjustments policy setting, the assignment may or may not be automatically converted to an adjustment, or you may be prompted to select whether to convert the assignment to an adjustment. An adjustment applies the duration of the unmeasured time to the assignment that the user was working on at the time of the request. Unmeasured time cannot be converted to an adjustment unless the assignment has a stop time.
-   **Adjust Duration ![Adjust Duration](../../../../images/resources/images/labor_adjust_time.png)** : Enables you to change the duration of the unmeasured time and automatically processes the assignment or adjustment. Unmeasured time cannot be converted to an adjustment unless the assignment has a stop time. If you adjust the time to increase the unmeasured time duration, then the request is approved. If you adjust the time to reduce the unmeasured time duration, you must re-approve the adjusted request.
-   **Reject** ![Reject](../../../../images/resources/images/labor_reject_time.png): Removes the assignment or adjustment and creates a record for the rejected time. You are required to enter a reason for the rejection.

## Approve unmeasured time

1.  Select **Labor > Dashboard > Approvals**.
2.  In the grid, perform one of the following tasks:
    -   Expand the unmeasured time requests for a user, and then in the row for the time to adjust, click ![Approve](../../../../images/resources/images/labor_approve_time.png).
    -   Select the check box for one or more unmeasured time requests, and then from the **Actions** drop-down list, select **Approve**.
3.  If a prompt is displayed asking if you want to convert the assignments to adjustments, perform one of the following tasks:
    
    **Note**: The Labor System Configuration/Convert Approved Requests to Adjustments policy determines whether a prompt is displayed or if pending assignment requests will be automatically converted to adjustments upon approval.
    
    -   To approve and convert the unmeasured time from a standalone assignment to an adjustment for the assignment that was Active when the user signed on to the unmeasured assignment, click **Yes**.
    -   To approve the unmeasured time and retain it as a separate assignment instead of converting it to an adjustment, click **No**.
    -   To exit the approval process, click **Cancel**.
4.  View the confirmation message.

## Adjust unmeasured time

1.  Select **Labor > Dashboard > Approvals**.
2.  In the grid, perform one of the following tasks:
    -   Expand the unmeasured time requests for a user, and then in the row for the time to adjust, click ![Adjust Duration](../../../../images/resources/images/labor_adjust_time.png).
    -   Select the check box for the unmeasured time request, and then from the **Actions** drop-down list, select **Adjust Duration**.
3.  Adjust the time information in the following fields:
    
    **Note**: If the unmeasured time request was created as an adjustment record (ADJ tag) from an external system, then you adjust the **Hours**, **Minutes**, and **Seconds** of the duration instead of the start and stop time. There is no minimum time limit to adhere to when you change the duration of an adjustment record, but the maximum adjusted time cannot be greater than the assignment duration.
    
    | Field | Description |
    | --- | --- |
    | Start Time | Start date and time of the unmeasured assignment. The start time must fall within the Start Time Min and Start Time Max values. The start time minimum is calculated by the start time of the previous assignment plus any adjustment durations for that assignment. The start time maximum is calculated by the stop time of the current assignment minus any adjustment durations for the assignment. |
    | Stop Time | Stop date and time of the unmeasured assignment. The stop time must fall within the Stop Time Min and Stop Time Max values. The stop time minimum is calculated by the start time of the current assignment plus any assignment durations for the assignment. The stop time maximum is calculated by the stop time of the next assignment minus any assignment durations for that assignment. |
    
4.  Click **Approve**, and then view the notification message.

**Note**: If you adjust the time to increase the unmeasured time duration, then the request is approved. If you adjust the time to reduce the unmeasured time duration, you must re-approve the adjusted request.

## Reject unmeasured time

1.  Select **Labor > Dashboard > Approvals**.
2.  In the grid, perform one of the following tasks:
    -   Expand the unmeasured time requests for a user, and then in the row for the time to reject, click ![Reject](../../../../images/resources/images/labor_reject_time.png).
    -   Select the check box for one or more unmeasured time requests, and then from the **Actions** drop-down list, select **Reject**.
3.  In the text box, enter a reason for the unmeasured time rejection, and then click **Reject**.
    
4.  View the confirmation message.

## Sign on a user to an unmeasured task

You can sign on users to unmeasured tasks to bypass the request and approval process.

1.  Select **Labor > Dashboard > Approvals**.
2.  Click **Unmeasured Sign On**.
3.  Enter information in the following fields:
    
     
    | Field | Description |
    | --- | --- |
    | Job Code | Unmeasured job code to which the user is signed on. |
    | Start Time | Date and time at which the unmeasured task is started. |
    | User ID | Identifier for the user to be signed on to the unmeasured task. |
    
4.  Click **Sign On**. A confirmation message is displayed.

## View approval history

1.  Select **Labor > Dashboard > Approvals**.
    
2.  Perform one of the following tasks:
    -   To view approval history for a user displayed in the grid, click **View History** in the row for the user. The Approval History page is displayed.
    -   To open the Approval History page without a user selected, click **View History**, and then in the **User ID** field, enter a user.
3.  To change the date range for which approval history details are displayed, in the **Report Date** field, use the calender tool to select a new date range.
4.  To view detailed information for each unmeasured time request for a specific job code, in the grid, expand the row.
5.  View the information in the [Approval History fields](#Approval_History_fields).
    
    **Note**: In an expanded row, if the status of a request is either Pending or Approved, you can click **Daily Details** in the Summary column to view information for the unmeasured time in context with other tasks performed by the user. See [Daily Details fields](#Daily_details_fields). Alternatively, if the request is Rejected, then the **Summary** column displays the reason for rejection, as entered by the user that rejected the unmeasured time.
    

## View rejected unmeasured time requests

1.  To view the rejected time for users that report to a supervisor:
    
    **Note**: To view your rejected unmeasured time requests, see [View your rejected unmeasured time requests](../user-sign-on.md).
    
    1.  Select **Labor > Dashboard > Approvals**.
        
    2.  Click **Rejected Time**.
        
    3.  Enter the **User ID**.
        
    4.  To view the rejected time for a user that reports to a specific supervisor, in the **User Supervisor** field, enter the supervisor ID.
        
    5.  To specify the date on which a user signed on to an unmeasured task, in the **Plan Date** field, enter the date.
        
    6.  To change the date range for which rejected time details are displayed, in the **Report Date** field, use the calender tool to select a new date range.
        
2.  View the displayed information in the [Rejected Time fields](#Rejected_Time_fields).
    

## Approval History fields

 
| Field | Description |
| --- | --- |
| Job Code | Unique identifier for a job code. A job code represents a standard for a task being performed in your facility, and it is the basic component for an assignment. |
| Pending Count | Number of unmeasured time requests for the job code that are pending approval or rejection. |
| Approved Count | Number of unmeasured time requests that were approved for the job code during the date range specified in the **Report Date** field. |
| Rejected Count | Number of unmeasured time requests that were rejected for the job code during the date range specified in the **Report Date** field. |
| Pending Average / Total Duration | Average time for each pending unmeasured time request for the job code, and the total duration (sum) of time for all pending unmeasured time requests during the date range specified in the **Report Date** field. The average time is calculated by dividing the total duration of pending time for the job code by the number of pending time requests. For example, if the **Pending Count** value is 5, and the **Total Duration** is 1 hour, then the **Pending Average** is 12 minutes (60 / 5 = 12). |
| Approved Average / Total Duration | Average time for each approved unmeasured time request for the job code, and the total duration (sum) of time for all approved time requests during the date range specified in the **Report Date** field. The average time is calculated by dividing the total duration of approved time for the job code by the number of approved time requests. For example, if the **Approved Count** value is 10, and the **Total Duration** is 3 hours, then the **Approved Average** is 18 minutes \[(3 x 60 = 180) / 10 = 18\]. This field displays the following time units: h = hours; m = minutes; s = seconds. |
| Rejected Average / Total Duration | Average time for each rejected unmeasured time request for the job code, and the total duration (sum) of time for all rejected time requests during the date range specified in the **Report Date** field. The average time is calculated by dividing the total duration of rejected time for the job code by the number of rejected time requests. For example, if the **Rejected Count** value is 2, and the **Total Duration** is 3 hours, then the **Approved Average** is 1.5 hours or 90 minutes \[(3 x 60 = 180) / 2 = 90\]. This field displays the following time units: h = hours; m = minutes; s = seconds. |
| Status | Status of the unmeasured time approval request (Pending, Approved, or Rejected). |
| Start Time | Date and time at which the unmeasured task was started. |
| Stop Time | Date and time at which the unmeasured task was completed. |
| Duration | Amount of time a user spent on the unmeasured task. This field displays the following time units: h = hours; m = minutes; s = seconds. |
| Parent Job | Identifier for the parent assignment that was in progress when an unmeasured time adjustment was logged. For example, if an operator is picking but needs to perform a safety check for which an unmeasured time adjustment is required, then the picking assignment is the parent job for the unmeasured time. If the unmeasured time is not an adjustment, and the unmeasured task is an individual assignment, then there is no parent job associated to the unmeasured time. |
| Parent Actual Time | Actual amount of time it took to complete the parent assignment of the unmeasured time adjustment. The application uses this value to calculate the parent job performance. Specifically, performance is calculated based on the number of goal time seconds completed and the number of actual seconds the operator spent on the parent assignment. |
| Parent Performance | Value that represents whether the goal time for the parent assignment was met. Performance is calculated based on the number of goal time seconds completed and the number of actual seconds an operator spends on the assignment. Specifically, Performance = (complete goal seconds / complete seconds) x 100. For example, assume an assignment was supposed to take 1 hour (3600 goal time seconds), but the actual amount of time to complete the assignment was 1.25 hours (4500 seconds). Based on these numbers, the application calculates a Performance value of 80 \[(3600 / 4500) x 100 = 80\]. The application rounds decimal values for performance to the nearest whole number. A value of 100 or greater indicates that the goal time is being met or exceeded, whereas a value lower than 100 indicates that the actual work is taking longer than the expected goal time. |

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

## Rejected Time fields

 
| Field | Description |
| --- | --- |
| User ID | Unique identifier of the user for whom you want to view rejected unmeasured time requests. |
| User Supervisor | Name or User ID of the user's supervisor. |
| Assignment | Unique identifier for an assignment. An assignment represents a basic unit of work that an employee performs in a facility. |
| Plan Date | Plan date for which you want to find rejected unmeasured time requests. The plan date is the date on which work is scheduled to be performed. |
| Indicator | Application-generated letter used to designate a split or merged assignment. When multiple assignments are associated with the same assignment number, then you can specify an indicator to identify the specific assignment. |
| Supervisor ID | Supervisor who rejected the request. |
| Rejected Time | Date and time the unmeasured time request was rejected. |
| Unmeasured Time | Amount of time (hours, minutes, and seconds) spent performing unmeasured tasks for the assignment after the start time or stop time was adjusted. An unmeasured task is a work task that does not have calculated standards, meaning that the application cannot calculate goal time and performance. This value is the adjusted difference (actual time) between the start time and stop time, and it matches the **Original Unmeasured Time** value if no time adjustments are made. |
| Original Unmeasured Time | Amount of time (hours, minutes, and seconds) originally spent performing unmeasured tasks for an assignment. This value is the original difference between the non-adjusted start time and stop time, and it matches the **Unmeasured Time** value if no time adjustments are made. |
| Job Code | Unique identifier for a job code. A job code represents a standard for a task being performed in your facility, and it is the basic component for an assignment. |
| Reason for rejection | Reason the unmeasured time request was rejected. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
