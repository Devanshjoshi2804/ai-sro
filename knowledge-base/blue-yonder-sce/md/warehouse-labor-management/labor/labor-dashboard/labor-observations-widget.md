---
title: "Labor Observations widget"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/labor_observations_widget.htm"
source: "/content/labor_observations_widget.htm"
toc_path:
  - "Warehouse Labor Management"
  - "Labor"
  - "Labor Dashboard"
  - "Labor Observations widget"
sections:
  - "User observations"
  - "Add a user observation"
  - "Perform a user observation"
  - "Edit a user observation"
  - "Delete a user observation"
  - "Complete or reopen a user observation"
  - "View user observation details"
  - "Observation fields"
  - "Observation Summary fields"
  - "Observation Details fields"
images:
  - "/content/resources/images/labor_pending_small.png"
  - "/content/resources/images/laborobvs_in_process.png"
  - "/content/resources/images/laborobvs_observed.png"
  - "/content/resources/images/labor_pastdueobvs.png"
  - "/content/resources/images/labor_addobservation.png"
  - "/content/resources/images/labor_addobservation.png"
source_sha1: 9b2a2724111adddd7c73874ede9729f9e3337f3a
---
# Labor Observations widget

You can create, perform, and complete user observations using the labor Observations widget. An observation is the act of a supervisor physically watching an employee (user) do normal job functions (one or more assignments) for a certain length of time, and then answering the questions posed on the user observation template. The user observation information is a key element for assessing and successfully improving quality, safety, and productivity.

When you first access the Observations widget, you must enter search criteria or select a quick filter to view observation information. Using the quick filter, you can view all observations, or you can filter by status (Pending, In Process, Observed, or Complete). Additionally, you can view only the observations that need supervisor action, which include those that are Pending, In Process, and Observed.

The Observations widget quick view at the top of the Labor dashboard displays a numerical value next to the following icons to represent the number of observations in a particular status:

-   ![Pending: Due Today / Past Due](../../../../images/resources/images/labor_pending_small.png) **Pending**: Number of observations that have been created or scheduled but have not yet been started. The number of pending observations displayed in the quick view represent observations that are due on the current date and those that are past due.
-   ![In Process](../../../../images/resources/images/laborobvs_in_process.png) **In Process**: Number of observations that have been started but not fully performed.
-   ![Observed](../../../../images/resources/images/laborobvs_observed.png) **Observed**: Number of observations that have been fully performed but not completed. Observations in this status require electronic signatures to be completed.

The grid view displays information for each user at a summary level and a detail level. The summary row for a user indicates the number of observations in each status, and allows you to create an observation for that user. You can expand a user's row to view more detailed information related to each observation, such as the associated job code, dates on which it was created and is due, and the template that is being used for the observation. Past due observations are marked with an icon (![Past Due](../../../../images/resources/images/labor_pastdueobvs.png)), and the due date value is displayed in red italicized text.

When you create and perform an observation, the observation widget transitions through the following pages: 

-   **Details**: The Details page is displayed first and contains general information about the observation, such as the user, job code, due date, and time frame. If you save and exit from the Details page, the observation remains in a Pending status. If you continue to the next page, Perform, the status of the observation changes to In Process.
-   **Perform**: The Perform page is populated based on the observation template, which is maintained in Observation Template Maintenance. This page contains the questions that must be answered, either by the user or the supervisor, during the observation. If you save and exit from the Perform page, the Observation remains in an In Process status. If you continue to the next page, Summary, the status of the observation changes to Observed.
-   **Summary**: The Summary page displays the details of the finished observation, including performance statistics (goal time, actual time, and performance rating). Since an observation can be performed for a specific assignment or during a time period in which multiple assignments are completed, you can indicate which assignments are included in the performance calculations. If you save and exit from the Summary page, the observation remains in an Observed status. If you complete the electronic signatures and finish the observation, its status changes to Complete.

## User observations

A user observation is the act of a supervisor physically watching an employee (user) do normal job functions (one or more assignments) for a certain length of time, and then answering the questions posed on the user observation template. The user observation information is a key element for assessing and successfully improving quality, safety, and productivity.

**Note**: You can create templates to use for recording user observations. The templates can include job code specific questions that cover time and pace, Preferred Methods, safety, and equipment use. User observation templates are maintained in Observation Template Maintenance, available in the SCE client.

You can set up user observations to be scheduled automatically or through a conditional, trigger-based event, using the SCE client. For example, you can set a user observation to automatically occur for new users every four weeks or you can set a user observation to occur when some criteria, such as low performance, is met. See the information on user observation scheduling in the _Supply Chain Execution Help_.

When user observations are automatically scheduled, the application generates a list of pending user observations on a regular schedule. You can view, create, and perform pending user observations using the Observations widget in the web client. An observation can be performed during a specific assignment, or during a specific time period that may contain multiple assignments. Prior to completing the observation, you can indicate which assignments that were scheduled to be performed during the time frame are included in the performance calculation.

Only one scheduled observation can exist for the same user, job code, template, and due date. For example, if a user observation is pending and another is created for the same user with an identical job code and template, the due date must be different than the first observation.

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
    -   To perform the observation, click **Next**. The Perform page is displayed and the observation's status is updated to In Process. See [Perform a user observation](#Perform_a_user_observation).
    -   To leave the observation in a Pending status to be performed later, click **Save and Exit**.

## Perform a user observation

1.  Select **Labor > Dashboard > Observations**.
2.  Enter search criteria or select a quick filter to view the observation to perform.
3.  In the grid, expand the row for the user. The existing observations for the user are displayed.
4.  In the **Status** column for the observation you want to perform, click the observation status.
    
    **Note**: Observations that have yet to be performed are in either Pending status or In Process status. If you select a pending observation, the Details page is displayed, and you must click **Next** to advance to the Perform page. If you select an in-process observation, the Perform page is displayed initially.
    
5.  If the observation's time frame value is set to Record Time, then click **Start Timer** to begin recording the time during which the observation is performed.
    
    **Note**: When you click **Start Timer**, the current time is set as the Start Time value for the observation; clicking **Stop Timer** sets the Stop Time value. You can reset the timer (which sets a new Start Time value) by clicking **Start Timer** again.
    
6.  Perform the observation by following the sections on the Perform page, asking the questions that are displayed, and entering answers and comments as necessary. The observation template determines the content that is displayed while performing an observation.
7.  Perform one of the following tasks:
    -   To leave the observation in an In Process status to be finished later, click **Save and Exit**. If you used the timer to perform the observation, the Stop Time is recorded when you save and exit.
    -   To finish the observation, which changes its status to Observed, click **Next**. The Summary page is displayed. See [Complete or reopen a user observation](#Complete_or_reopen_a_user_observation).
        
        **Note**: If the manual timer is used and you do not click **Stop Timer** before advancing to the Summary tab, the application automatically sets the Stop Time value to the time at which you clicked **Next**.
        

## Edit a user observation

1.  Select **Labor > Dashboard > Observations**.
2.  Enter search criteria or select a quick filter to view the observation to edit.
3.  In the grid, expand the row of the user, and then perform one of the following tasks:
    -   Select the check box for the observation, and then click **Edit**.
        
        **Note**: To make updates to multiple observations, select the check box for each observation to edit; selecting the check box for a user automatically selects all of the user's observations. Completed observations are not included in the observation mass update.
        
    -   In the **Status** column for the observation, click the observation status.
        
4.  Enter information in the [Observation fields](#Observation_fields).
    
    **Note**: Some fields may not be displayed or available to update, depending on the status of the observation.
    
5.  Perform one of the following tasks:
    -   If you completed the update on the Observation Mass Update page:
        1.  Click **Apply**. The results of the mass update are displayed.
        2.  Click **OK**.
    -   If you completed the update on the Details, Perform, or Summary page (depending on the status of the observation), then click **Save and Exit**.
        
    -   If you completed the update on the Details, Perform, or Summary page and want to continue performing the observation, click **Next**. See [Perform a user observation](#Perform_a_user_observation). If the observation is Observed, then you can also complete the observation. See [Complete or reopen an observation](#Complete_or_reopen_a_user_observation).

## Delete a user observation

1.  Select **Labor > Dashboard > Observations**.
2.  Enter search criteria or select a quick filter to view the observation to delete.
3.  In the grid, expand the row of the user, and then select the check box for the observation to delete.
    
    **Note**: You can select multiple observations to delete, or you can delete all of a user's observations by selecting the check box for the user.
    
4.  Click **Delete**. A confirmation message is displayed.
5.  Click **OK**.

## Complete or reopen a user observation

1.  Select **Labor > Dashboard > Observations**.
2.  Enter search criteria or select a quick filter to view the observation to complete.
3.  In the grid, expand the row of the user.
4.  To complete an observation:
    1.  In the **Status** column, in the row for the observation, click **Observed**. The Summary page is displayed.
        
        **Note**: Observations in a Pending or In Process status must be performed before they can be closed.
        
    2.  View the information in the [Observation Summary fields](#Observation_summary_fields).
    3.  To change the time frame in which the observation was performed, update the information in the **Start Time** and **End Time** fields.
        
        **Note**: If the observation was created for a specific assignment (instead of a period of time), then you cannot update the start and end times. However, you can update the assignment.
        
    4.  To view or change the assignments that are included in the observation performance calculations:
        
        **Note**: The assignments that are available to be included in the observation performance calculations is dependent on the defined time frame or assignment number. If there are multiple assignment with the same number and no indicator or plan date is specified, then all assignments associated with the number are included in the observation.
        
        1.  Click **View/Modify Assignments**.
        2.  In the grid, deselect the check box next to each assignment to exclude from the observation; or select the check box next to each assignment to include in the observation.
        3.  Click **Calculate** and view the performance statistics.
        4.  Click **Save**.
    5.  Review the observation details as necessary.
    6.  Electronically sign the observation:
        
        **Note**: If signatures are disabled, then encryption setup is not complete. Contact your System Administrator.
        
        1.  Click the **Employee** signature line, complete the signature, and then click **OK**.
        2.  Click the **Supervisor** signature line, complete the signature, and then click **OK**.
            
        3.  Click **Complete**. A confirmation message is displayed.
        4.  Click **Yes**.
            
5.  To reopen an observation:
    1.  In the **Status** column, in the row for the observation, click **Complete**. The Summary page is displayed.
    2.  Click **Reopen**. A confirmation message is displayed.
    3.  Click **Yes**.

## View user observation details

1.  Select **Labor > Dashboard > Observations**.
2.  Enter search criteria or select a quick filter to view observations.
3.  In the grid, expand the row for the user. The existing observations for the user are displayed.
4.  View information in the [Observation Details fields](#Observation_details_fields).

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

## Observation Summary fields

 
| Field | Description |
| --- | --- |
| User | Unique identifier and name of the employee to be observed. |
| Job Code | Unique identifier for the job that is to be (or was) observed. Job codes are essentially a representation of all of the tasks being performed in your facility, and are the basic component of an assignment.<br > **Note**: The application does not validate the selected job code for the observation against the job code for the assignment. |
| Observation Supervisor | Name of the supervisor responsible for performing the observation. |
| Created Date | Date and time at which the observation was created or automatically scheduled. |
| Due Date | Date and time by which the observation must be completed. |
| Template | Identifier for an observation template. A template can include job code specific questions that cover time and pace, preferred methods, safety, and equipment use. User observation templates are maintained in Observation Template Maintenance, available in the SCE client. |
| Completed Date | Date and time at which the observation was completed by the supervisor. This is the date and time when the observation's status transitioned to Complete. |
| Assignment | Number of the assignment during which the observation is performed. If multiple assignments are associated with the same assignment number, such as when an assignment is split, then you can specify an indicator or a plan date to identify the specific assignment. If the **Indicator** and **Plan Date** fields are available and no values are defined, then all of the assignments associated with the number are included in the observation. |
| Indicator | Application-generated letter that is used to designate a split or merged assignment. When multiple assignments are associated with the same assignment number, then you can specify an indicator to identify the specific assignment. If the **Indicator** and **Plan Date** fields are available and no values are defined, then all of the assignments associated with the number are included in the observation. |
| Plan Date | Date on which an assignment is scheduled to be performed. If multiple assignments are associated with the same assignment number, then you can specify an indicator or a plan date to identify the specific assignment. If the **Indicator** and **Plan Date** fields are available and no values are defined, then all of the assignments associated with the number are included in the observation. |
| Goal Time | Estimated time to complete the assignments included in the observation based on engineered standards. Goal time calculations should be considered estimates because they can change based on multiple factors, such as skipped picks, use of different travel sequences, and transition move travel time. |
| Actual Time | Actual amount of time it took to complete the assignments included in the observation. The application uses this value to calculate user performance. Specifically, performance is calculated based on the number of goal time seconds completed and the number of actual seconds operators have spent on the assignments.<br > If you modify the assignments included in the observation, the actual time (as well as the performance) is recalculated based on the selected assignments. |
| Performance | Value that represents whether the goal time for the selected assignments is being met. Performance is calculated based on the number of goal time seconds completed and the number of actual seconds operators have spent on the assignments. Specifically, Performance = (complete goal seconds / complete seconds) x 100.<br > For example, assume an assignment was supposed to take 1 hour (3600 goal time seconds), but the actual amount of time to complete the assignment was 1.25 hours (4500 seconds). Based on these numbers, the application calculates a Performance value of 80 \[(3600 / 4500) x 100 = 80\]. The application rounds decimal values for performance to the nearest whole number. A value of 100 or greater indicates that the goal time is being met or exceeded, whereas a value lower than 100 indicates that the actual work is taking longer than the expected goal time.<br > If you modify the assignments that are included in the observation, the performance is recalculated based on the selected assignments. |

## Observation Details fields

 
| Field | Description |
| --- | --- |
| User | Unique identifier and name of the employee to be observed. |
| User Supervisor | Name or User ID of the user's supervisor. |
| Observation Supervisor | Name of the supervisor responsible for performing the observation. |
| Pending | Number of observations for the user that are in Pending status, regardless of due date. Pending observations have been created or scheduled but have not yet been started. |
| In Process | Number of observations for the user with a status of In Process. In-process observations have been started but are not fully performed. |
| Observed | Number of observations for the user that are in Observed status. Observations in this status have been fully performed but have not been completed. |
| Completed | Number of observations for the user in a Completed status. |
| Status | Current status of the observation.<br>-   • **Pending**: The observation has been created or scheduled but has not been started.
<br>-   • **In Process**: The observation has been started but not fully performed.
<br>-   • **Observed**: The observation has been fully performed but has not been completed.
<br>-   • **Completed**: The observation is complete. |
| Job Code | Unique identifier for the job that is to be (or was) observed. Job codes are essentially a representation of all of the tasks being performed in your facility, and are the basic component of an assignment.<br > **Note**: The application does not validate the selected job code for the observation against the job code for the assignment. |
| Created Date | Date and time at which the observation was created or automatically scheduled. |
| Due Date | Date and time by which the observation must be completed. |
| Completed Date | Date and time at which the observation was completed by the supervisor. This is the date and time when the observation's status transitioned to Complete. |
| Template | Identifier for an observation template. A template can include job code specific questions that cover time and pace, preferred methods, safety, and equipment use. User observation templates are maintained in Observation Template Maintenance, available in the SCE client. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
