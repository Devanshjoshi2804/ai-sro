---
title: "Pick Methods"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/pick_methods.htm"
source: "/content/pick_methods.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Outbound"
  - "Picking "
  - "Pick Methods"
sections:
  - "In-line replenishments"
  - "Add or modify a pick method"
  - "Delete a pick method"
  - "Pick Method fields"
  - "Release Rules fields"
images: []
source_sha1: e127f1c8e6d3fb6bac6779dc9d771ad7fc89cada
---
# Pick Methods

A pick method is a required attribute of an allocation search path. A pick method is a configuration that defines the type of pick that is created when inventory on the search path is allocated for a pick or replenishment, and how that pick is released (such as, whether the application creates directed work that is added to the work queue or produces a pick sheet for paper-based picking).

Each pick method is defined by a name, description, and a pick pre-validation scheme. See [Pick Pre-Validation Scheme](pick-pre-validation-scheme.md).

To each pick method you add one or more release rules, as required, to release the work in your facility. For example, you may configure the release rules for different types of picks (standard, carton, threshold, bulk, and bulk threshold) and different types of replenishments (top-off, triggered, emergency, and manual).

A release rule is defined by the following attributes:

-   Action that occurs when the pick is released, such as to create work for an RF operator to perform or produce a pick sheet for paper-based picking.
-   Operation (for actions that create work) that is used to perform the work, such as Pallet Pick or Case Pick. You can also adjust the priority of the operation so that it is released to a position higher or lower in the work queue.
-   Work groupings (for actions that create work) that direct the application to group pieces of work together that have similar attributes that you select.
-   Destination rules that override the release rule for picks that have a destination in a specific movement zone. The application uses the normal release rule configuration except when a pick is destined to a movement zone for which a specific destination release rule is configured.
-   Priority that determines position in the work queue. The base priority can be overridden, increased, or decreased by a specified value at the time of allocation.
    

After you create a pick method, you can assign it to the allocation search path that should use it. See [Allocation Search Paths](../allocation/allocation-search-paths.md) or [Replenishment Search Paths](../../inventory/replenishments/replenishment-search-paths.md).

## In-line replenishments

An in-line replenishment is a replenishment performed by a picking operator while picking a work assignment when the specified location does not have the pick quantity available. For example, if an operator arrives at a location to complete picks from a list and there is not enough inventory available, the operator can set down the completed pick work and immediately complete a replenishment to the location. Once the replenishment is complete, the operator can resume the work assignment and complete the rest of the picks. If an operator arrives at a location where a replenishment is already in process, the operator has the option of waiting for the replenishment instead of having to skip or cancel the pick.

In-line replenishments can be enabled by setting the **Replenish While Picking** field to Yes for a pick method.

You can also configure a work assignment rule to specify whether the work assignment must be resumed by the original operator who set down the picks to complete the in-line replenishment. See [Work assignment rules](work-assignments.md).

## Add or modify a pick method

1.  Select **Configuration > Outbound > Picking > Pick Methods**.
2.  Perform one of the following tasks:
    -   To add a pick method, click **Add**.
    -   To modify a pick method, in the grid, click the pick method name.
3.  Enter information in the [Pick Method fields](#Pick_Method_fields).
4.  Configure release rules for the pick method:
    1.  Under **RELEASE RULES**, click the type of pick work for which you want to configure the release rules.
    2.  Enter information in the [Release Rules fields](#Release_Rule_fields).
    3.  To define the attributes that determine how work is grouped, click **Work Groupings**, select the check box for the attributes that must match, and click **Save**.
        
        **Note**: The work groupings can limit the performance of the action you specified for the release rule by grouping individual pieces of work into one piece of work. For example, if you select PRODUCE WORK ASSIGNMENT as the action for the release rule, and then select Operation Code and Cartonization Group as the work groupings, the application will only produce on one work assignment for all picks that are of the same type of operation and that have the same cartonization group.
        
    4.  To add or modify a destination rule:
        
        **Note**: A destination rule is a separate release rule that is used instead of the normal release rule when the pick's destination movement zone is that which you specify in the destination rule.
        
        1.  Click **Destination Rules**.
        2.  Perform one of the following tasks:
            -   To add a new destination rule, click **Add**.
            -   To modify an existing destination rule, select the rule you want to modify.
        3.  Enter information in the [Release Rules fields](#Release_Rule_fields).
        4.  To define the attributes that must match for individual pieces of work to be grouped into a single task when the destination rule is used, click **Work Groupings**, select the check box for the attributes that must match, and click **Apply**.
        5.  Click **Save**
        6.  Repeat the necessary steps to define additional destination rules for the pick work type.
        7.  Click **Apply**.
    5.  Click **Save**.
        
5.  Click **Save**.

## Delete a pick method

1.  Select **Configuration > Outbound > Picking > Pick Methods**.
2.  In the grid, select the check box next to the pick method to delete.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Pick Method fields

 
| Field | Description |
| --- | --- |
| Method Name | Name of the pick method. A pick method is a set of configuration options that define how picks are created and released. You can create separate pick methods for outbound picks, which fulfill orders shipped from the warehouse, and for replenishment picks, which restock picking locations in the warehouse. |
| Description | Text that further describes the pick method. |
| Pre-validation Scheme | Name of a configuration that determines what occurs when a pick fails pre-validation. Pick pre-validation is a process that determines whether inventory is available in a location prior to displaying the pick to an operator. Using a pre-validation scheme can help prevent an operator from being directed to a location that either no longer contains available inventory for the pick or which is locked from picking.<br > After you have created a pick pre-validation scheme, you must assign the scheme to a pick method for the type of pick to which it applies. Assigning a pre-validation scheme to a pick method determines how the application handles pre-validation for the each pick method. |
| Reserve During Pick Release | Determines which locations in the movement zones defined for a movement path are reserved during pick release when the application uses this pick method.<br>-   • **All**: During pick release, a location is reserved in all of the defined movement zones for a movement path. If selected, then the application only releases the picks if all zones in the movement path have an available location at the time of pick release; if not, the application does not release the picks until a location is available in all defined movement path zones.
<br>-   • **First**: Only the first deposit location (in the movement zone that follows the source zone) is reserved during pick release. Each subsequent location in the remaining movement path zones is only reserved when the operator picks up the inventory from its current location. If selected, and if there are no locations available in the first movement zone that follows the source zone, then the application does not release the picks. If a location is available and the picks release, but there is not a location available in the next zone in the movement path, then the operator can deposit the picks to a P&D location until a location is available in the next movement zone.
<br>-   • **None**: No locations in the movement zones defined for a movement path are reserved during pick release. The first deposit location (in the movement zone that follows the source zone) is reserved when the operator picks the inventory, and each subsequent location in the remaining movement path zones is only reserved when the operator picks up the inventory from its current location. If selected, the application always releases the picks, regardless of whether there are available locations in the movement path zones. If the next zone in the movement path is full, the operator can deposit the picks to a pickup and deposit (P&D) location until a location is available in the next movement zone. |
| Work Assignments | If Yes, then picks that are allocated using the pick method can be built into work assignments. A work assignment is a picking process by which the application combines individual picks into a list (work assignment) that an operator can perform in one picking tour, moving from one pick location to another until the list is complete.<br > If No, then picks are not added to work assignments. |
| Cartonization | If Yes, picks that are allocated using the pick method are subject to cartonization. Cartonization is the process of determining which items are to be packed together in a container and which size container is to be used.<br > If No, picks are not cartonized. |
| Replenish While Picking | If Yes, an operator completing picks that were allocated using the pick method is allowed to perform an in-line replenishment. An in-line replenishment is a replenishment performed by a picking operator when the specified location does not have the pick quantity available. For example, if an operator arrives at a location to complete picks and there is not enough inventory available, the operator can set down the completed pick work and immediately complete a replenishment to the location.<br > If No, the operator is not directed to perform in-line replenishments when performing picks. |

## Release Rules fields

 
| Field | Description |
| --- | --- |
| Destination | Movement zone that contains the final destination location for inventory that was picked. For example, for inventory picked for an outbound order, this could be a zone that contains ship staging locations. |
| Action | Action that the application performs to release the pick:<br>-   • **CREATE DIRECTED WORK:** Creates a directed work request for the pick, which is added to the work queue so that an RF operator can perform it.
<br>-   • **CREATE PICKS**: Releases the pick as undirected work.
<br>-   • **CREATE WORK FOR PM PRE MANIFEST PACKAGE**: Creates a work queue entry for a case pick or kit pick, and manifests the parcel package.
<br>-   • **PROCESS PM PRE MANIFEST PACKAGE**: Creates a work queue entry for a case pick or kit pick, manifests the parcel package, and prints a manifest label with pick information and parcel package information.
<br>-   •
    
    **CREATE LABEL FILE FOR PM PREMANIFEST PACKAGE**: Manifests the parcel package and prints a manifest label with pick information and parcel package information.
    
    <br>
<br>-   • **PRODUCE PICK LIST**: Produces a report that displays the pick information. An operator uses the report to perform paper-based picking.
<br>-   • **PRODUCE SHIPMENT LABEL**: Prints a pick label that includes the information for the pick work. |
| Operation | Work operation that identifies the type of work that is created, such as piece pick, case pick, kit pick, list pick, pallet pick, or replenishment pick. |
| Priority | Priority at which work initially enters the work queue. It is the priority at which a work request is created. Priority is used, for example, to assign a higher priority to pallet and case replenishment work to fill pick locations than to pallet or case pick work to fulfill orders.<br>-   • **Use base priority**: The value for the operation's base priority at the time of allocation is used when work is created. The base priority is the current priority that is defined for the operation.
<br>-   • **Override base priority**: The operation's base priority is overridden at the time of allocation for the selected zone with the number specified in the **Value** field. For example, you may consider your case replenishments coming out of your flow racks more important than your case replenishments coming out of your floor zone.
<br>-   • **Increase priority from base priority**: The operation's base priority is increased at the time of allocation by the number specified in the **Value** field.
<br>-   • **Decrease priority from base priority**: The operation's base priority is decreased at the time of allocation by the number specified in the **Value** field. |
| Value | Value that is applied against the base priority of the operation. Depending on what is selected for **Priority**, the value either replaces the base priority, or it is added to or subtracted from the base priority to result in a new priority. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
