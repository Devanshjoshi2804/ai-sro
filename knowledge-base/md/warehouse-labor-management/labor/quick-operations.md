---
title: "Quick Operations"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/quick_operations_wlm.htm"
source: "/content/quick_operations_wlm.htm"
toc_path:
  - "Warehouse Labor Management"
  - "Labor"
  - "Quick Operations"
sections:
  - "End Shift"
  - "Unmeasured Adjustment"
  - "Unmeasured Assignment"
  - "End a shift"
  - "Add an unmeasured adjustment"
  - "Add an unmeasured assignment"
images: []
source_sha1: 9f56d76c89c54042599f182a9596dcb25fe19853
---
# Quick Operations

You use the Quick Operations pages to end shifts and add unmeasured time adjustments and assignments for one or more users.

## End Shift

You use the End Shift page to end the shift for users that report to you or for all users in the warehouse, depending on your role. A shift is a defined work period that occurs in a 24-hour span that may include paid and unpaid breaks. A shift is assigned to a specific day of the week in a schedule. For example, if a schedule is set up for users working days, and the users work a 40-hour week with 9 hours worked Monday through Thursday and only 4 hours worked Friday, then a shift for a 9-hour day is created and assigned to the schedule Monday through Thursday, and a different shift for a 4-hour day is created and assigned to Friday. If breaks are added to the shift, they are automatically inserted into the assignment that occurs during that time period.

Users must indicate when their shift ends so that the application can calculate the performance for the last assignment of the day. Typically, users end their shift from the User Sign On page. If users forget or are unable to end their shift, you can manually end the shift using the End Shift page. See [End a shift](#End_a_shift).

**Note**: You can also perform shift-based tasks using the Schedule Operations window, which is accessed from the SCE client.

## Unmeasured Adjustment

The Unmeasured Adjustment page enables you to add unmeasured time adjustments for one or more users. Unmeasured time is time from a task that does not have calculated standards, such as performing a clean-up activity, attending a meeting or fixing a machine. You can insert an unmeasured time adjustment into an assignment that has already started. For example, if a user takes a break while an assignment is in progress but does not account for the time, then you can add the unmeasured time adjustment for the user. The unmeasured time is inserted into the assignment that was in progress at the time defined as the adjustment start time.

Your role privilege authorizations determine whether you can view all users in the facility or only those that report to you. If the Unmeasured Time Operations privilege is selected for your role, then you can view and add adjustments for all users. See [Add an unmeasured adjustment](#Add_an_unmeasured_adjustment).

## Unmeasured Assignment

The Unmeasured Assignment page enables you to add unmeasured assignments for one or more users. An assignment represents the basic unit of work that a user performs in your facility. Unmeasured time is time from a task that does not have calculated standards, such as performing a clean-up activity, attending a meeting or fixing a machine. See [Add an unmeasured assignment](#Add_an_unmeasured_assignment).

## End a shift

You can only end a shift for users with assignments that are in the Active status. Once the shift is ended, the assignments are changed to the Complete status, and an ISTOP is recorded with the shift end time.

1.  Select **Labor > Quick Operations > End Shift**.
2.  In the **User ID** field, enter the unique identifier for the user.
    
3.  In the **Stop Time** field, enter the date and time at which the shift ended.
4.  Click **Submit**. A confirmation message is displayed stating that an ISTOP record was created.

## Add an unmeasured adjustment

1.  Select **Labor > Quick Operations > Unmeasured Adjustment**.
2.  Enter information in the following fields:
    
     
    | Field | Description |
    | --- | --- |
    | User ID | Unique identifier for one or more users for which to add the unmeasured adjustment. Valid users are those working on assignments with a start time prior to the **Adj. Start Time**. |
    | Adj. Start Time | Date and time when the unmeasured adjustment should start. |
    | Unmeasured Job Code | Unique identifier for the unmeasured job code for which the adjustment is added. |
    | Adj. Minutes | Number of minutes to be adjusted into the assignment for the unmeasured task, starting at the defined adjustment start time. |
    
3.  Click **Add Adjustment**. A confirmation message is displayed.

## Add an unmeasured assignment

1.  Select **Labor > Quick Operations > Unmeasured Assignment**.
2.  Enter information in the following fields:
    
     
    | Field | Description |
    | --- | --- |
    | Job Code | Unique identifier of the unmeasured job code for the assignment. |
    | Start Time | Date and time when the unmeasured assignment starts. |
    | User ID | Unique identifier for one or more users for which to add the unmeasured assignment. |
    
3.  Click **Add Assignment**. A confirmation message is displayed.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
