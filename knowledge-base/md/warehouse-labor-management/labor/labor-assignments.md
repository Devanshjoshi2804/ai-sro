---
title: "Labor Assignments"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/labor_assignments.htm"
source: "/content/labor_assignments.htm"
toc_path:
  - "Warehouse Labor Management"
  - "Labor"
  - "Labor Assignments"
sections:
  - "Add an assignment"
  - "Delete an assignment"
  - "Assign a user to an assignment"
  - "Unassign a user from an assignment"
  - "Change the times for an assignment"
  - "Split an assignment"
  - "View or modify general assignment details"
  - "View or modify summary assignment details"
  - "View discrete assignment details"
  - "Assignment fields"
  - "General tab fields"
  - "Discrete Details tab fields"
images:
  - "/content/resources/images/image1076720.png"
  - "/content/resources/images/image1076719.png"
source_sha1: e8f5cf18d0e4a15b779e431411aba6fbf8e098b7
---
# Labor Assignments

The Assignments page provides visibility to the direct and indirect assignments that are active, complete, or not yet started. An assignment represents the basic unit of work that a user performs in your facility. Assignment information is typically downloaded from the host, however, you can add, modify, or delete assignments on the Assignments page. This page is also intended for supervisors to fix assignments or insert unmeasured time for users.

The Assignments page is divided into the following panes:

**Note**: You can show and hide the panes by clicking ![Expand/Collapse](../../../images/resources/images/image1076720.png) and ![Expand/Collapse](../../../images/resources/images/image1076719.png).

-   **Search (left)**: Search fields into which you can enter criteria to view specific assignments. You can search for assignments based on job code, report date, user, and work category, among other attributes.
-   **Assignments grid (center)**: The assignments that match the search criteria. When you select an assignment in the grid, the details are displayed on the assignment details pane (right). You can add new assignments or delete existing assignments on the Assignments pane. Assignments may be displayed with tags in the Assignment column for status (Future, Complete, or Active) and the Job Code column for work type (Direct or Indirect).
-   **Assignment details (right)**: Information associated with the assignment selected in the Assignments grid (center). You can split an assignment, change the start and end time for an assignment, or assign (and unassign) a user to an assignment. The following tabs are available on this pane to view or modify assignment information: 
    -   **General**: General assignment information that you can modify.
    -   **Adjustments**: Assignment adjustments that you can add, modify, delete, approve, and reject.
    -   **Summary**: Summarized assignment information that you can modify, such as product totals and key volume indicator (KVI) details.
    -   **Discrete Details**: Discrete details for the assignment. There are no actions available on this tab.
    -   **Quality Error**: Reported assignment quality errors. You can log new quality errors against the assignment, change existing errors, or unresolve an error to update its details.

## Add an assignment

1.  Select **Labor > Labor Assignments**.
2.  From the **Actions** drop-down list, select **Add Assignment**.
3.  Enter information in the [Assignment fields](#Assignment_fields).
4.  Click **Save**.

## Delete an assignment

1.  Select **Labor > Labor Assignments**.
2.  On the Search pane, enter criteria for the assignment, and then click **Search**.
3.  In the Assignments grid, select the assignment to delete.
4.  From the **Actions** drop-down list, select **Delete**. A confirmation message is displayed.
5.  Click **Yes**.

## Assign a user to an assignment

1.  Select **Labor > Labor Assignments**.
2.  On the Search pane, enter criteria for the assignment, and then click **Search**.
3.  In the Assignments grid, select the assignment.
4.  On the Assignment details pane, click **Assign User**.
5.  In the **User ID** field, enter the user you want to assign to the assignment.
6.  In the **Start Time** field, enter the date and time at which the assignment should be started.
7.  Click **Assign User**.

## Unassign a user from an assignment

1.  Select **Labor > Labor Assignments**.
2.  On the Search pane, enter criteria for the assignment, and then click **Search**.
3.  In the Assignments grid, select the assignment.
4.  On the Assignment details pane, click **Unassign User**. A confirmation message is displayed.
5.  Click **Unassign User**.

## [](labor-assignments/quality-errors.md)Change the times for an assignment

1.  Select **Labor > Labor Assignments**.
2.  On the Search pane, enter criteria for the assignment, and then click **Search**.
3.  In the Assignments grid, select the assignment.
4.  On the Assignments details pane, click **Change Times**.
5.  In the **Start Time** field, enter the date and time at which the assignment should be started.
6.  In the **Stop Time** field, enter the date and time at which the assignment was completed.
    
7.  Click **Change Times**.

## Split an assignment

Assignments can be split when they contain more tasks or quantities than one user can perform. When you split an assignment and define the number of splits, new goal times for user performance are calculated and will be greater than or equal to the goal time of the original assignment. In addition, when you split an assignment that is in Active or Complete status, the newly created split assignments are displayed as future assignments.

1.  Select **Labor > Labor Assignments**.
    
2.  On the Search pane, enter criteria for the assignment, and then click **Search**.
    
3.  In the Assignments grid, select the assignment.
    
4.  On the Assignment details pane, click **Split**.
    
5.  In the **No. of Splits** field, enter the number of times to split the assignment.
    
6.  To preview the split assignment KVI details, click **Calculate**.
    
7.  Click **Split**.
    

## View or modify general assignment details

1.  Select **Labor > Labor Assignments**.
2.  On the Search pane, enter criteria for the assignment, and then click **Search**.
3.  In the Assignments grid, select the assignment.
4.  On the Assignment details pane, select the **General** tab.
5.  View or enter information in the [General tab fields](#General_tab_fields).
6.  If you modified the general details for the assignment, click **Save**.

## View or modify summary assignment details

1.  Select **Labor > Labor Assignments**.
2.  On the Search pane, enter criteria for the assignment, and then click **Search**.
3.  In the Assignments grid, select the assignment.
4.  On the Assignment details pane, select the **Summary** tab.
5.  View or enter information in the following fields:
    
     
    | Field | Description |
    | --- | --- |
    | Total Cube | Total cubic volume of all of the pieces on this assignment. |
    | Total Weight | Total weight of all of the pieces on this assignment. |
    | Shipping Units | Number of shipping units for this assignment. |
    | KVI Details | Key volume indicator (KVI) values (for example, pallets, cases, and eaches) with their associated quantities for the assignment. The KVI information is specific to the job code associated with the assignment; however, you can override the quantity information as needed for the assignment. |
    
6.  If you modified summary details, click **Save**.

## View discrete assignment details

1.  Select **Labor > Labor Assignments**.
2.  On the Search pane, enter criteria for the assignment, and then click **Search**.
3.  In the Assignments grid, select the assignment for which to view discrete details.
4.  On the Assignment details pane, select the **Discrete Details** tab.
5.  View the information in the [Discrete Details tab fields](#Discrete_Detail_tab_fields).

## Assignment fields

 
| Field | Description |
| --- | --- |
| Assignment | Unique identifier for an assignment. An assignment represents a basic unit of work that an employee performs in a facility. |
| Plan Date | Date on which an assignment is scheduled to be performed. If multiple assignments are associated with the same assignment number, then you can specify an indicator or a plan date to identify the specific assignment. |
| Job Code | Unique identifier for a job code. A job code represents a standard for a task being performed in your facility, and it is the basic component for an assignment. You cannot select an activity card job code for a new assignment. |
| Reference ID | Unique identifier used to reference this assignment information for the day. |
| Client ID | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. |
| Customer | Name used to identify a business to whom you ship inventory. Each customer has a profile that is used to define how their inventory is handled, how their orders are processed, and how their inventory is shipped. |
| Route # | Number that indicates a specific sequential routing order for the assignment through your facility. |
| Machine ID | Unique alphanumeric identifier for a machine. A machine is a gas- or electric battery-powered material handling unit used for picking, depositing, or transporting product within a warehouse. |
| Total Cube | Total cubic volume of all of the pieces on this assignment. |
| Total Weight | Total weight of all of the pieces on this assignment. |
| Shipping Units | Number of shipping units for this assignment. |
| User Defined 1-4 | User defined information for an assignment. |
| Aisle Area ID | Unique identifier for an aisle area. |
| KVI Details | Key volume indicator (KVI) values (for example, pallets, cases, and eaches) with their associated quantities for the assignment. The KVI information is specific to the job code associated with the assignment; however, you can override the quantity information as needed for the assignment. |

## General tab fields

 
| Field | Description |
| --- | --- |
| Work Category | Unique identifier for the work category. A work category is a method of categorizing job information for reporting and statistical purposes. A job code can be assigned to only one work category. You can use this field as search criteria to find assignments in a specific category. |
| Team Type | Parameter used to identify team reporting assignments. You can use this field as search criteria to find assignments of a specific type, such as Team or Individual. |
| Learning Curve | Name of the learning curve applied to the assignment. A learning curve gradually increases the expected performance for a user against the standard. This is commonly used for new employees or employees that are cross training in new departments. |
| Job Code | Unique identifier for a job code. A job code represents a standard for a task being performed in your facility, and it is the basic component for an assignment. You cannot select an activity card job code for a new assignment. |
| Reference ID | Unique identifier used to reference this assignment information for the day. |
| Client ID | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. |
| Customer | Name used to identify a business to whom you ship inventory. Each customer has a profile that is used to define how their inventory is handled, how their orders are processed, and how their inventory is shipped. |
| Route # | Number that indicates a specific sequential routing order for the assignment through your facility. |
| Machine ID | Unique alphanumeric identifier for a machine. A machine is a gas- or electric battery-powered material handling unit used for picking, depositing, or transporting product within a warehouse. |
| User Defined 1-4 | User defined information for an assignment. |
| Aisle Area ID | Unique identifier for an aisle area. |
| Shift ID | Name of the shift associated with this assignment. A shift is a defined work period within 24 hours that may include paid and unpaid breaks. You can use this field as search criteria for finding assignments. |
| User | Unique identifier for the user assigned to the assignment. |
| Supervisor | User ID and name of the supervisor to whom the user assigned to the assignment reports. A supervisor manages and oversees a user's work. |
| Work Team | Name that identifies a work team. A work team is an optional category into which users can be grouped for easy selection throughout the application, such as in reports, assignments, performance statistics, report cards, and payroll information. |
| User Group | Name that identifies a user group to which the user belongs. A user group is used to categorize users for easy selection in reports, assignments, performance statistics, report cards, and payroll information. |
| Plan Date | Date on which an assignment is scheduled to be performed. If multiple assignments are associated with the same assignment number, then you can specify an indicator or a plan date to identify the specific assignment. |
| Start Time | Actual start date and time of active or completed assignments. |
| Stop Time | Actual end date and time of active or completed assignments. |
| Indicator | Application-generated letter used to designate a split or merged assignment. When multiple assignments are associated with the same assignment number, then you can specify an indicator to identify the specific assignment. |

## Discrete Details tab fields

 
| Field | Description |
| --- | --- |
| Seq # | Application-generated number that defines the order of the discrete details for the assignment. |
| Location | Unique name for a location within the facility that is used to receive, store, process, or ship inventory. |
| Grab Factor | Number of cases that are regularly obtained or placed in a single motion for the assignment. The application uses the grab factor to determine the number of time measurement units (TMUs) that are allotted when a user handles a specific case type. |
| Shipping Units | Number of shipping units for this assignment. |
| Units of Measure | Quantity of the UOM associated with the discrete detail activity. The quantity is displayed in one of the following UOM columns: **Pallet**, **Layer**, **Case**, **Inner**, and **Each**. For example, if the value in the **\# Case** field is 5 and the type of activity is Obtain, then 5 cases were picked for the discrete detail. |
| Item # | Unique identifier of the item for this discrete detail. Typically, this is the stock keeping unit (SKU) or label that is displayed on a pick sheet. Only displayed when the detail activity type is Obtain or Place. |
| Item Desc | Description of the item associated with this discrete detail. This information also is displayed on the pick sheet or label. Only displayed when the assignment detail activity type is Obtain or Place. |
| Con License | Identifier of the container (for example, pallet or tote) where the product for the task is to be placed. |
| Cube | Unit volume of the UOM (for example, pallet or case). This is the cube of the picked UOM, not the shipping unit or total picked amount. Only displayed when the detail activity type is Obtain or Place. |
| Weight | Unit weight of the UOM (for example, pallet or case). This is the weight of the picked UOM, not the shipping unit or total picked amount. Only displayed when the detail activity type is Obtain or Place. |
| Machine ID | Unique alphanumeric identifier for a machine. A machine is a gas- or electric battery-powered material handling unit used for picking, depositing, or transporting product within a warehouse. |
| Activity type | Type of activity performed for the discrete detail, such as Obtain or Place. |
| Aisle Area ID | Unique identifier for an aisle area. |
| Work Type ID | Identifier for the work type for the discrete detail. A work type is a category within the application that is used to represent a basic type of work (for example, selection or putaway) performed in a facility. A work type can be mapped (associated) to a job code to identify different job-related activities within the facility. |
| Travel Distance | Distance, in inches, between the starting and ending locations. Inches are the default measurement unit; your configuration may be different. |
| Travel TMUs | Distance, in time measurement units (TMUs), between the starting and ending locations. TMUs are the default measurement unit; your configuration may be different. |
| Trans # | Transaction number. |
| Special 1-5 | Special handling information for an assignment. A special handling rule defines a task that is only required for a specific time frame or condition. When calculating the goal time for an assignment, the application will take into account the additional assignment time required to complete the special handling. For example, you might need a special handling rule to account for the extra time required to pack specific items in ice during the summer months when heat conditions would otherwise cause these items to spoil or melt before reaching their destination. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
