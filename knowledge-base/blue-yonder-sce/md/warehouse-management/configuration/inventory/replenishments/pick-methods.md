---
title: "Pick Methods"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/pick_methods_replen.htm"
source: "/content/pick_methods_replen.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inventory"
  - "Replenishments"
  - "Pick Methods"
sections:
  - "Add or modify a replenishment pick method"
  - "Delete a replenishment pick method"
  - "Replenishment Pick Method fields"
  - "Release Rule fields"
images: []
source_sha1: a7f4116fc23df71097ae43bddd280dfd352cfe17
---
# Pick Methods - Configuration

A pick method is a required attribute of an allocation search path. A pick method is a configuration that defines the type of pick that is created when inventory on the search path is allocated for a pick or replenishment, and how that pick is released (such as, whether the application creates directed work that is added to the work queue or produces a pick sheet for paper-based picking).

Each pick method is defined by a name, description, and a pick pre-validation scheme. See [Pick Pre-Validation Scheme](../../outbound/picking/pick-pre-validation-scheme.md).

To each pick method you add one or more release rules, as required, to release the work in your facility. For example, you may configure the release rules for different types of picks (standard, carton, threshold, bulk, and bulk threshold) and different types of replenishments (top-off, triggered, emergency, and manual).

A release rule is defined by the following attributes:

-   Action that occurs when the pick is released, such as to create work for an RF operator to perform or produce a pick sheet for paper-based picking.
-   Operation (for actions that create work) that is used to perform the work, such as Pallet Pick or Case Pick. You can also adjust the priority of the operation so that it is released to a position higher or lower in the work queue.
-   Work groupings (for actions that create work) that direct the application to group pieces of work together that have similar attributes that you select.
-   Destination rules that override the release rule for picks that have a destination in a specific movement zone. The application uses the normal release rule configuration except when a pick is destined to a movement zone for which a specific destination release rule is configured.
-   Priority that determines position in the work queue. The base priority can be overridden, increased, or decreased by a specified value at the time of allocation.
    

After you create a pick method, you can assign it to the allocation search path that should use it. See [Allocation Search Paths](../../outbound/allocation/allocation-search-paths.md) or [Replenishment Search Paths](replenishment-search-paths.md).

## Add or modify a replenishment pick method

There are typically only two pick methods used for replenishments: pallet replenishment and case replenishment.

1.  Select **Configuration > Inventory > Replenishments > Pick Methods**.
2.  Perform one of the follow tasks:
    -   To add a pick method, click **Add**.
        
        **Note**: The two commonly used pick methods for replenishments are pallet replenishment and case replenishment. If new pick method is required, it is typically set up by Customer Support because it requires additional technical configuration. Before adding a new pick method, contact your Blue Yonder project team.
        
    -   To modify a pick method, in the grid, click the pick method name.
3.  Enter information in the [Replenishment Pick Method fields](#Replenishment_Pick_Method_fields).
4.  Configure release rules for the pick method:
    1.  Under **RELEASE RULES**, click the type of replenishment work for which you want to configure the release rules.
    2.  Enter information in the [Release Rule fields](#Release_Rule_fields).
    3.  To define the attributes that must match for individual pieces of work to be grouped into a single task:
        1.  Click **Work Groupings**.
        2.  Select the check box for the attributes that must match.
        3.  Click **Save**.
            
            **Note**: The work groupings can limit the performance of the action you specified for the release rule by grouping individual pieces of work into one piece of work. For example, if you select Create Directed Work as the action for the release rule, and then select Operation and Destination Location as the work grouping attributes, the application groups the work for replenishment picks that have the same operation and destination location.
            
    4.  To add or modify a destination rule:
        
        **Note**: A destination rule overrides the pick method and defines a different release action for a specific zone.
        
        1.  Click **Destination Rules**.
        2.  Perform one of the following tasks:
            -   To add a destination rule, click **Add**.
            -   To modify a destination rule, select the rule to modify.
        3.  Enter information in the [Release Rule fields](#Release_Rule_fields).
        4.  To define the attributes that must match for individual pieces of work to be grouped into a single task when the destination rule is used, click **Work Groupings**, select the check box for the attributes that must match, and click **Save**.
        5.  Click **Save.**
    5.  Click **Save**.
    6.  Repeat the necessary steps to define release rules for the remaining work types.
    7.  Click **Save**.

## Delete a replenishment pick method

1.  Select **Configuration > Inventory > Replenishments > Pick Methods**.
2.  In the grid, select the check box next to the pick method to delete.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Replenishment Pick Method fields

 
| Field | Description |
| --- | --- |
| Method Name | Name of the pick method. A pick method is a set of configuration options that define how replenishment work is created and released. A Pallet Replen is used to move full pallets to a defined pick location; a Case Replen is used to move cases to a defined pick location. |
| Description | Text that further describes the pick method. |
| Pre-Validation Scheme | Name of a configuration that determines what occurs when a pick fails pre-validation. Pick pre-validation is a process that determines whether inventory is available in a location prior to displaying the pick to an operator. Using a pre-validation scheme can help prevent an operator from being directed to a location that either no longer contains available inventory for the pick or which is locked from picking.<br > After you have created a pick pre-validation scheme, you must assign the scheme to a pick method for the type of pick to which it applies. Assigning a pre-validation scheme to a pick method determines how the application handles pre-validation for the each pick method. |
| Work Assignments | If Yes, then picks that are allocated using the pick method can be built into work assignments. A work assignment is a picking process by which the application combines individual picks into a list (work assignment) that an operator can perform in one picking tour, moving from one pick location to another until the list is complete.<br > If No, then picks are not added to work assignments. |
| Prompt for Specific Case | If Yes, when an operator performs a replenishment pick generated using this pick method, the application prompts the operator with the specific sub-LPN to pick. If you select Yes, the application assigns specific sub-LPNs to the replenishment picks on the work assignment at the time the picks are performed. The application tracks the inventory for each completed pick on the replenishment work assignment and applies picked quantities across the assignment, if necessary. For example, if a single pick of a mixed-item case satisfies two replenishment picks on the work assignment, both picks are updated and considered complete.<br > If No, the application does not prompt the operator with the specific sub-LPN to pick. If you select No, the operator is only prompted with location, item, and quantity information for a pick, and is not directed to pick a specific case. |
| Allow Mix Case | If Yes, then for detail level replenishments using this pick method, the application can allocate a full mixed item sub-LPN to satisfy the detail-LPN picks. The mixed sub-LPN is picked to a location from which the detail LPNs needed for replenishment can be removed. If you select Yes, the application also considers the composition of the inventory in single- and mixed-item cases when locations are being sorted for replenishment allocation. Locations with single-item cases are used for allocation first, and then the application considers the locations with mixed-item cases, if necessary.<br > **Note**: When the application sorts locations to allocate single-item partial cases over mixed-item partial cases, this sorting only valid for replenishment allocation and can override other sorting configurations in place. For example, the application does not respect the defined rotation method, such as FIFO, for detail-level replenishments of date-tracked inventory.<br > If No, the application directs the operator to pick only the specific item from the mixed-item case. If you select No, the application still considers locations with mixed item cases, however, locations with single-item cases are not necessarily prioritized over mixed-item cases. |

## Release Rule fields

 
| Field | Description |
| --- | --- |
| Destination | Storage zone that contains the final destination location for the replenishment inventory. |
| Action | Action that the application performs to release the replenishment:<br>-   • **Create Work**: Releases the pick as undirected work.
<br>-   • **Produce Shipment Label**: Prints a pick label that includes the information for the pick work.
<br>-   • **Create Directed Work**: Creates a directed work request for the pick, which is added to the work queue so that an RF operator can perform it. |
| Operation | Work operation that identifies the type of directed work that is created, such as a pallet replenishment or case replenishment. |
| Priority | Priority at which work initially enters the work queue. It is the priority at which a work request is created. Priority is used, for example, to assign a higher priority to pallet and case replenishment work to fill pick locations than to pallet or case pick work to fulfill orders.<br>-   • **Use base priority**: The value for the operation's base priority at the time of allocation is used when work is created. The base priority is the current priority that is defined for the operation.
<br>-   • **Override base priority**: The operation's base priority is overridden at the time of allocation for the selected zone with the number specified in the **Value** field. For example, you may consider your case replenishments coming out of your flow racks more important than your case replenishments coming out of your floor zone.
<br>-   • **Increase priority from base priority**: The operation's base priority is increased at the time of allocation by the number specified in the **Value** field.
<br>-   • **Decrease priority from base priority**: The operation's base priority is decreased at the time of allocation by the number specified in the **Value** field. |
| Value | Value that is applied against the base priority of the operation. Depending on what is selected for **Priority**, the value either replaces the base priority, or it is added to or subtracted from the base priority to result in a new priority. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
