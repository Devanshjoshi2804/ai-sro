---
title: "User Sign On"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/user_sign_on_wlm.htm"
source: "/content/user_sign_on_wlm.htm"
toc_path:
  - "Warehouse Labor Management"
  - "Labor"
  - "User Sign On"
sections:
  - "Goal time and performance information"
  - "User Sign On setup and configuration"
  - "User Sign On usage scenario"
  - "Perform a user sign on activity"
  - "Perform a clock punch"
  - "End an assignment and shift"
  - "View performance information"
  - "View your rejected unmeasured time requests"
  - "Daily Details fields"
  - "Overall Performance fields"
  - "Rejected Time fields"
images: []
source_sha1: c2fe46b9a9dff562b7b538adb9d4140d5d87107c
---
# User Sign On

The User Sign On page enables you to perform basic work activities from dedicated web-enabled PCs or terminals in your facility during a short period of time. The User Sign On page is designed to be constantly running on these dedicated PCs or terminals; however, it will remain idle until a user signs on to an activity. After each activity, the sign on page is cleared and ready for the next user to sign on and perform an activity. You can perform the following work activities on the User Sign On page: 

-   **Assignment Sign On**: Sign on to an individual or a team assignment by assignment number. The assignment information is then tracked and used for performance calculations.
-   **Job Code Sign On**: Sign on directly to a job code. The job code sign on is used for performing unmeasured tasks (such as sanitation) or for activity cards.
-   **Activity Card Sign On**: Sign on to an activity card assignment. An activity card is used when you are providing the assignment information (such as the activities performed and the corresponding quantities of units handled). When you sign on to an activity card, an activity card assignment is created by the application without any goal time associated with it. Once the activity card assignment is completed, you must sign back on to the assignment on the User Sign On page and provide the appropriate information (for example, the number of pallets and cases, and if required, the reference ID). You can then sign on to the next job (such as an assignment, job code, activity card, or a team leader) as usual.
-   **Team Leader Sign On**: Sign on to the team leader of a team-led assignment. When you sign on to a team leader, you are automatically signed on to the team assignment to which the team leader signs on until you sign on to another team assignment or until the team leader signs on to a non-team assignment. During sign on, you will enter the team leader's user ID instead of an assignment number or a job code ID. You will then share in the calculated performance for the entire team-led assignment.
-   **Assignment Merge**: If auto-merging is enabled in your facility, then similar assignments will be merged whenever you consecutively sign on to assignments in a specified time frame. When an auto-merge occurs, a message is displayed indicating that the assignments have been merged. If assignments are not auto-merged, then a message is displayed asking you to confirm whether you want to merge the assignments.
-   **Rejected time**: View your unmeasured time requests that were rejected by a supervisor.
    
-   **Shift and Assignment End**: When you end your shift using the User Sign On page, your active assignment (job) is automatically recorded as completed. If applicable, you can use the end shift and assignment function to sign off for breaks (such as lunch). If Time and Incentives functionality is enabled, you can clock out instead of ending the shift.
    
    **Note**: Depending on your facility's configuration, clocking out to end the shift and assignment may not be available.
    
-   **Perform Clock Punches**: If Time and Incentives functionality is enabled, you can perform clock punches (such as clocking in for a shift or break) that are entered directly in the application.

## Goal time and performance information

You can configure whether goal time and performance information is available to users and displayed on the User Sign On page. The level of goal time and performance information that is available to the users is determined by the masking level for the associated job code.

**Note**: You use Job Code Maintenance (accessed from the Warehouse Labor Management SCE client) to specify the masking level for a job code. See the _Supply Chain Execution Help_.

-   **Goal Time**: Displays the expected amount of time to perform the job, the clock time at which the job is expected to finish (for example, 09:30 A.M.), and any expected break times. This information is displayed whenever a user signs on to a job.
    
    **Note**: Goal time information is not available for an activity card or team leader sign on; or for a job containing unmeasured tasks.
    
-   **Last Job Performance**: Displays the statistical performance percentage, the corresponding performance message, and the goal time and actual time information for the previously completed job. This information is displayed whenever a user signs on to a new job.
    
    **Note**: You use the Sign On Client policies (accessed from the Warehouse Labor Management SCE client) to specify the performance percentage amount used to display the above, average, or below performance information, and the message text that is displayed to the users.
    
-   **Daily Details**: Displays the statistical performance percentage, and the total goal time and actual time information for all of the completed jobs for the day. Depending on your application configuration, a performance message can also be displayed based on the user's performance percentage. This information is displayed whenever a user signs on to a job or clicks **Daily Details** after performing a user sign on.
-   **Detailed Performance**: Displays detailed performance information for all of the completed jobs for the current day (and any specified number of previous days). This information is displayed whenever a user clicks **Performance** after performing a user sign on.
    

## User Sign On setup and configuration

You must configure the following policies in the Warehouse Labor Management SCE client:

-   **Sign On Server Configuration**: Used to specify the rules that customize the behavior of the application for User Sign On (for example, whether auto-merge is enabled).
-   **Sign On Client Configuration**: Used to specify the page setup and display settings for User Sign On, and are configured using client-based policies (for example, whether the clock is displayed).

## User Sign On usage scenario

The User Sign On page enables you to perform basic work activities (such as signing on to assignments, punching the clock, and ending a shift). Goal time and performance information is also available on the User Sign On page upon performing specific tasks.

**Note**: Depending on your application configuration and the type of work activity performed, not all of these tasks may be available or may apply.

1.  A user sign on is performed on the User Sign On page. To sign on, you need to enter your user ID, and if required, your password.
2.  If you are using the Time and Incentives functionality, a request for clock punch is indicated. When the request for a clock punch is provided, you can click Yes to record the clock punch directly in the application. This enables you to clock in for the shift or from the break when you start the next work activity. In addition, the clock punch information is displayed.
3.  The job ID for the work that will be performed is required.
    
    **Note**: The job ID can be the assignment number, the job code ID, or the team leader's user ID. When a job ID is entered, User Sign On searches the database for the associated job. The application searches first for an assignment number, then for a job code ID, and then for a user ID. The application prompts you to enter the job ID for the work that will be performed.
    
4.  If auto-merge assignments is enabled, then if you enter several assignment numbers during the sign on process, the application may merge the assignments. This process combines several small assignments (or pieces of an assignment) into a single assignment. When several assignment numbers are entered, the assignment merge confirmation is displayed.
5.  If applicable, you can view the goal time for the job. The goal time information shows the expected amount of time required to complete the job.
    
    **Note**: Goal time information is not available for an activity card or team leader sign on.
    
6.  After the work is completed, you return to the sign on page and perform a user sign on.
7.  If the previous assignment was an activity card, then the key volume indicator (KVI) information for the assignment is required. The activity card sign on is used when you must provide the assignment information, such as activities performed and the corresponding quantities of units handled. After the activity assignment is complete, you can sign on and the request for activity card information is displayed, and then you can enter the information for the work performed. For example, the number of pallets and cases, and if required, the reference ID.
8.  The job ID for the next job is required.
    
    **Note**: You automatically complete the previous job by signing on to a new job.
    
9.  If the next job contains indirect tasks (such as a meeting or training), an additional prompt may be displayed during the job sign on. You must click **Enter** again to confirm the sign on.
    
    **Note**: The Enable Confirm Job policy determines whether users are prompted to confirm the sign on. See the _Supply Chain Execution Help_.
    
10.  The application calculates the performance of the previous assignment.
11.  You can view past assignment performance. The daily performance information is provided for a completed job whenever you sign on to the next job. You can also view the performance for any completed job and a total performance for the day. In addition, you can view this summarized performance information after performing a user sign on.
12.  When the user is done for the day, the user ends the shift and the active assignment from the User Sign On page.
     
     **Note**: Ending a shift does not close the User Sign On page.
     

## Perform a user sign on activity

1.  Select **Labor > User Sign On**.
2.  In the **User ID** field, enter your user name.
3.  If required, in the **Password** field, enter your password.
4.  Click **Sign On**.
5.  If a message is displayed asking if you want to punch in, perform one of the following tasks:
    -   To perform a clock punch:
        1.  Click **Yes**. The clock punch information is displayed.
        2.  View the clock punch information, and then click **Enter**.
        3.  In the **User ID** field, reenter your user name, and then click **Continue**.
    -   To bypass a clock punch, click **No**.
6.  To perform an assignment or job code sign on:
    
    **Note**: If auto-merging is enabled in your facility and you consecutively sign on to multiple assignments in the specified time frame, then a confirmation message is displayed indicating the assignments have been merged. If assignments are not auto-merged, then a message is displayed asking you to confirm whether you want to merge the assignments.
    
    1.  In the **Job Code/User ID/Assignment Number** field, enter the assignment number or job code for the work you are about to do, and then click **Sign On**. A confirmation message is displayed.
    2.  Click **Yes**.
    3.  If the assignment is split and the assignments window is displayed, then select the assignment indicator to sign on to, and then click **Enter**. A confirmation message is displayed.
    4.  Click **Yes**.
7.  To perform a team leader sign on, in the **Job Code/User ID/Assignment Number** field, enter the team leader's user ID, and then click **Sign On**.
8.  To perform an activity card sign on:
    1.  In the **Job Code/User ID/Assignment Number** field, enter the activity card job code, and then click **Sign On**. A confirmation message is displayed.
    2.  Click **Yes**.
    3.  Perform the work. When you are finished, return to the User Sign On page.
    4.  In the **User ID** field, enter your user name, and then click **Continue**. The activity card fields are displayed.
    5.  Enter the required information, such as the number of pallets and the number of cases, and then click **Confirm**. A confirmation message is displayed.
    6.  Click **Yes**. When the **Job Code/User ID/Assignment Number** field is displayed, sign on to the next job.

## Perform a clock punch

Clock punches are only available when the Time and Incentives functionality is enabled in your Warehouse Labor Management instance.

1.  Select **Labor > User Sign On**.
2.  In the **User ID** field, enter your user name.
3.  If required, in the **Password** field, enter your password.
4.  Click **Sign On**.
5.  Perform one of the following tasks:
    -   If this is your first sign on of the day, then when a message is displayed asking if you want to clock in for the shift, click **Yes**.
    -   If this is not your first sign on of the day, then click **Punch In/Out**. The appropriate clock punch is recorded. For example, if your facility separates clock punches for breaks, and you have already clocked in for the shift, then your next clock punch is recorded as a clock out for break.
6.  When the clock punch information is displayed, view the information, and then click **Enter** to clear the User Sign On page.

## End an assignment and shift

The shift and assignment end functionality enables you to end your shift and your active assignment (job) in one step. Use this procedure when you will not be performing another assignment (for example, after the last assignment of the day or if you will be going on a break).

**Note**: Ending an assignment and shift does not close the User Sign On page.

1.  Select **Labor > User Sign On**.
2.  In the **User ID** field, enter your user name.
3.  If required, in the **Password** field, enter your password.
4.  Click **Sign On**.
5.  Click **End Shift**.
6.  If the goal time or performance information is displayed, view the information, and then click **Enter** to clear the User Sign On page.

## View performance information

1.  Select **Labor > User Sign On**.
2.  In the **User ID** field, enter your user name.
3.  If required, in the **Password** field, enter your password.
4.  Click **Sign On**.
5.  To view the detailed information for the completed jobs for the current day, click **Daily Details** and then view the information in the [Daily Details fields](#Daily_details_fields).
6.  To view the summarized performance information for the completed jobs for the current day, click **Performance** and then view the information in the [Overall Performance fields](#Overall_performance_fields).

## View your rejected unmeasured time requests

Note: To view rejected unmeasured time requests for a user as a supervisor, see [View rejected unmeasured time requests](labor-dashboard/labor-approvals-widget.md).

1.  To view your rejected unmeasured time requests:
    
    1.  Select **Labor > User Sign On**.
        
    2.  In the **User ID** field, enter your user name.
        
    3.  If required, in the **Password** field, enter your password.
        
    4.  Click **Sign On**.
        
    5.  If a message is displayed asking if you want to punch in, perform one of the following tasks:
        
        -   To perform a clock punch:
            
            1.  Click **Yes**. The clock punch information is displayed.
                
            2.  View the clock punch information, and then click **Enter**.
                
            3.  In the **User ID** field, reenter your user name, and then click **Continue**.
                
        -   To bypass a clock punch, click **No**.
            
    6.  Click **Rejected Time**.
        
2.  View the information in the [Rejected Time fields](#Rejected_Time_fields).
    

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

## Overall Performance fields

 
| Field | Description |
| --- | --- |
| Goal Time | Estimated time to complete the assignment based on engineered standards. Goal time estimates are calculated by creating Future Assignments in Warehouse Labor Management. Goal time calculations should be considered estimates because they can change based on multiple factors, such as skipped picks, use of different travel sequences, and transition move travel time. |
| Actual Time | Actual amount of time it took to complete the assignment. The application uses this value to calculate user performance. Specifically, performance is calculated based on the number of goal time seconds completed and the number of actual seconds operators have spent on the assignments. |
| Performance | Value that represents whether the goal time for an assignment is being met. Performance is calculated based on the number of goal time seconds completed and the number of actual seconds operators have spent on the assignment. Specifically, Performance = (complete goal seconds / complete seconds) x 100.<br > For example, assume an assignment was supposed to take 1 hour (3600 goal time seconds), but the actual amount of time to complete the assignment was 1.25 hours (4500 seconds). Based on these numbers, the application calculates a Performance value of 80 \[(3600 / 4500) x 100 = 80\]. The application rounds decimal values for performance to the nearest whole number. A value of 100 or greater indicates that the goal time is being met or exceeded, whereas a value lower than 100 indicates that the actual work is taking longer than the expected goal time.<br > If a job is unmeasured, a performance value is not displayed. Additionally, performance is not displayed if the Warehouse Labor Management, Labor System Configuration/Enable Variance policy is disabled. |
| Team Performance | Value (average) that represents whether the goal time for an assignment is being met by the team. The team average is calculated using the performance of all employees that report to the same supervisor. Performance is calculated based on the number of goal time seconds completed and the number of actual seconds operators have spent on the assignment. Specifically, Performance = (complete goal seconds / complete seconds) x 100. |

## Rejected Time fields

 
| Field | Description |
| --- | --- |
| User ID | Unique identifier of the user for whom you want to view rejected unmeasured time requests. |
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
