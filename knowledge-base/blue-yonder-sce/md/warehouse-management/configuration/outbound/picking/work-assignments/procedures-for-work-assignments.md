---
title: "Procedures for work assignments"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/procedures_for_work_assignment_configuration.htm"
source: "/content/procedures_for_work_assignment_configuration.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Outbound"
  - "Picking "
  - "Work Assignments"
  - "Procedures for work assignments"
sections:
  - "Configure work assignments"
  - "Add or modify an item family set sequence"
  - "Reset an item family set sequence"
  - "Add or modify work assignment rules"
  - "Mass copy and update work assignment rules"
  - "Configure work assignment rule groups"
  - "Work Assignment fields"
  - "Item Family Set Sequence fields"
  - "Work Assignment Rules fields"
  - "Work Assignment Rule Group fields"
  - "Break Value fields"
images: []
source_sha1: f580c0548af0352aba95d7608e1ee943f73b0b1f
---
# Procedures for work assignments

When you configure work assignments, you define settings for starter pallets, work assignment rules, and order sequence processing.

## Configure work assignments

1.  Select **Configuration > Outbound > Picking > Work Assignments**.
2.  Enter information in the [Work Assignment fields](#Work_Assignment_fields).
3.  To define the pick zones that are eligible for starter pallets:
    1.  Click **Pick Zones Eligible for Starter Pallets**.
    2.  In the **Available Pick Zones** column, select the check box next to the pick zones eligible for starter pallets.
    3.  Click **Apply**.
4.  To define criteria that determines the sequence in which starter pallets are chosen to be included in a work assignment:
    1.  Click **Sequencing**.
    2.  To select criteria from displayed entities:
        1.  If the advanced query is displayed, click **Simple**.
        2.  If the available entities are not displayed, click **Show Available**.
        3.  In the **Available** grid, select the entities that you want to use as criteria.
        4.  Click **Add selected**. The entities are added to the **Selected** grid.
        5.  To remove criteria, in the **Selected** grid, select the criteria to remove, and click **Remove selected**.
        6.  To reorder the criteria, in the **Selected** grid, click a row, and then click the up or down arrow to move the selected criteria. The application applies the criteria in sequential order according to how it is displayed in the grid.
    3.  To enter criteria using database entities, click **Advanced**, and then enter the column and field name, using a period to separate the column and field. Multiple column and field entries must be separated by a comma and space.
        
        You can use operators like IS NULL or IS NOT NULL to build an advanced query. For example, <column name>.<field name > IS NOT NULL, <column name>.< field name>.
        
    4.  Click **Save**.
5.  To define work assignment rules, see [Add or modify work assignment rules](#Add_or_modify_work_assignment_rules).
6.  To select the pick zones in which operators should not be prompted to enter a pick quantity when the pick quantity is 1:
    
    **Note**: You use this configuration to relieve the operator from having to enter a pick quantity when the pick quantity is 1 unit. Operators will still be prompted to enter the quantity for pick quantities greater than 1.
    
    1.  Under **WORK ASSIGNMENTS**, click **Disable Quantity Field for Pick Quantity of 1**.
    2.  In the **Available Pick Zones** column, select the check box next to the pick zones that apply.
    3.  Click **Apply**.
7.  To define a work assignment rule reference to override work assignment rules for shipment:
    1.  Under **WORK ASSIGNMENTS**, click **Work Assignment Rule References**.
    2.  In the grid, click **Add**. The Add New Work Assignment Rule Reference window is displayed.
    3.  Enter the **Work Assignment Rule Reference** name, **Description**, and **Short Description**.
    4.  Click **Apply**.
    5.  To modify a work assignment rule reference, in the grid, click and modify the description.
8.  To select the item families for which work assignment picks are not released until all handling unit slots are reserved:
    
    **Note**: You use this configuration for order sequence processing. When you have a work assignment rule for a handling unit (parent) that is defined for an item family set sequence, you can prevent releasing the picks for work assignment until picks have been planned to all of the slots on the handling unit.
    
    1.  Under **ORDER SEQUENCE PROCESSING**, click **Prevent Release By Item Family Until Handling Unit Is Fully Utilized**.
    2.  In the **Available** column, select the check box next to the item families that apply.
    3.  Click **Apply**.
9.  To select the movement zones in which automatically shipping takes place for carriers that allow it:
    
    **Note**: Automatic shipping is a process by which a staged shipment is systematically loaded, closed, shipped, and dispatched automatically. Automatic shipping will not take place if the carrier is not enabled to allow it.
    
    1.  Under **ORDER SEQUENCE PROCESSING**, click **Automatically Ship Shipments by Zone**.
    2.  In the **Available** column, select the check box next to the movement zones that apply.
    3.  Click **Apply**.
10.  To select the carriers that allow automatic shipping:
     
     **Note**: If a carrier is enabled for automatic shipping, then shipping takes place automatically when all inventory for the shipment has been staged to a movement zone that is enabled for automatic shipping. If the carrier is enabled for automatic shipping, but the zone is not enabled for it, then an operator can still auto-ship the shipment when the shipment is fully staged.
     
     1.  Under **ORDER SEQUENCE PROCESSING**, click **Carriers that Allow** **Automatic Shipping.**
     2.  In the **Available** column, select the check box next to the carriers that apply.
     3.  Click **Apply**.
11.  To define the item family sequence sets for order sequence processing:
     1.  Under **ORDER SEQUENCE PROCESSING**, click **Item Family Set Sequence**. See [Add or modify an item family set sequence](#Add_or_modify_an_item_family_set_sequence).
12.  Click **Save**.

## Add or modify an item family set sequence

1.  Select **Configuration > Outbound > Picking > Work Assignments**.
2.  Under **ORDER SEQUENCE PROCESSING**, click **Item Family Set Sequence**.
3.  To add or modify a set sequence, perform one of the following tasks:
    -   To add a set sequence, from the **Actions** drop-down list, select **Create Set Sequence**.
    -   To modify a set sequence, in the grid, select the check box next to the set sequence, and then from the **Actions** drop-down list, select **Modify Set Sequence**.
4.  Enter information in the [Item Family Set Sequence fields](#Item_Family_Set_Sequence_fields).
5.  Click **Next**.
6.  In the **Available** column, select the check box next to the item families to include in the set.
7.  Click **Next**.
8.  Review item family set sequence information. The current sequence is set to the first possible sequence. For example, if the **Sequence Length** was set to 000, the current sequence is 001.
9.  Click **Finish**.

## Reset an item family set sequence

You can reset an item family set sequence to its first sequence value. For example, if the **Sequence Length** field is 000 and the **Current Sequence** is greater than 001 (such as 099), then resetting the set sequence changes the value to 001.

1.  Select **Configuration > Outbound > Picking > Work Assignments**.
2.  Under **ORDER SEQUENCE PROCESSING**, click **Item Family Set Sequence**.
3.  In the grid, select the check box next to the item family set, and then from the **Actions** drop-down list, select **Reset Set Sequence**. A confirmation message is displayed.
4.  Click **Yes**. The sequence value is changed to the first possible sequence.

## Add or modify work assignment rules

You can add or modify work assignment rules. To copy and update multiple rules at the same time, see [Mass copy and update work assignment rules](#Mass_copy_and_update_work_assignment_rules). To add rules to a group, see [Configure work assignment rule groups](#Configure_work_assignment_rule_groups).

1.  Select **Configuration > Outbound > Picking > Work Assignments**.
2.  Under **WORK ASSIGNMENTS**, click **Work Assignment Rules**.
3.  In the Rules grid, perform one of the following tasks:
    -   To add a rule, from the **Actions** drop-down list, select **Add**.
    -   To modify a rule, click the rule.
    -   To copy a rule, select the check box next to the rule, and then from the **Actions** drop-down list, select **Copy**.
4.  Enter information in the [Work Assignment Rules fields](#Work_Assignment_Rule_fields).
5.  To define the order in which picks are listed on a work assignment:
    1.  Click **Pick Order**.
    2.  To select criteria from displayed entities:
        1.  If the advanced query is displayed, click **Simple**.
        2.  If the available entities are not displayed, click **Show Available**.
        3.  In the **Available** grid, select the entities that you want to use as criteria.
        4.  Click **Add selected**. The entities are added to the **Selected** grid.
        5.  To remove criteria, in the **Selected** grid, select the criteria to remove, and click **Remove selected**.
        6.  To reorder the criteria, in the **Selected** grid, click a row, and then click the up or down arrow to move the selected criteria. The application applies the criteria in sequential order according to how it is displayed in the grid.
    3.  To enter criteria using database entities, click **Advanced**, and then enter the column and field name, using a period to separate the column and field. Multiple column and field entries must be separated by a comma and space.
        
        You can use operators like IS NULL or IS NOT NULL to build an advanced query. For example, <column name>.<field name > IS NOT NULL, <column name>.< field name>.
        
    4.  Click **Save**.
6.  To define the criteria that determines which picks are included in work assignments using this rule:
    1.  Click **Selection Criteria**.
    2.  Under **Criteria Definition**, click **Expression**.
    3.  Select an entity that has the attribute to use, such as **Outbound Order**.
    4.  Select the attribute to use, such as **Ship-To Customer**.
    5.  Select the qualifier to use, such as "**\=**".
    6.  Select the value to use, such as **CustomerA** (the name of the shipping address for the order).
    7.  To add additional expressions:
        1.  Select the mathematical argument used to evaluate multiple rows of criteria (expressions):
            -   **Or**: Must match either group of the defined criteria.
            -   **And**: Must match both groups of the defined criteria.
            -   **(**: Opening argument used to group criteria together.
            -   **)**: Closing argument used to group criteria together.
                
                **Note**: Other operators that represent a combination of these arguments, such as ")And(" are also available. The operator determines how the application evaluates the criteria. For example, if you have two criteria lines connected with the operator "And", that means the inventory must match both attributes to meet the criteria. If the two lines are connected with the operator "Or", the inventory only has to match one of the field values to meet the criteria.
                
        2.  Click **Expression**, and define its criteria.
    8.  Click **Apply**.
7.  To define the criteria that determines which picks can be included in the same work assignment:
    1.  Click **Criteria Grouping**.
    2.  To select criteria from displayed entries:
        1.  If the advanced query is displayed, click **Simple**.
        2.  If the available entities are not displayed, click **Show Available**.
        3.  In the **Available** grid, select the entities that you want to use as criteria.
        4.  Click **Add selected**. The entities are added to the **Selected** grid.
        5.  To remove criteria, in the **Selected** grid, select the criteria, and then click **Remove selected**.
        6.  To reorder the criteria, in the **Selected** grid, click a row, and then click the up or down arrow to move the selected criteria. The application applies the criteria in sequential order according to how it is displayed in the grid.
    3.  To enter criteria using database entities, click **Advanced**, and then enter the column and field name, using a period to separate the column and field name. Multiple column and field entries must be separated by a comma and space.
        
        You can use operators like IS NULL or IS NOT NULL to build an advanced query. For example, <column name>.<field name > IS NOT NULL, <column name>.<field name>.
        
    4.  Click **Save**.
8.  To define the criteria that determines the order in which selected picks are sorted before being added to a work assignment:
    1.  Click **Criteria Sequence**.
    2.  In the **Available** column, select the check box next to the fields by which to sort picks.
    3.  In the **Selected** column, from the **Sort Order** drop-down list, select the order by which to sort the picks.
    4.  To change the sequence in which the application evaluates the criteria, in the **Selected** column, click the row and drag it to the preferred position.
    5.  Click **Apply**.
9.  To define the criteria that determines the capacity of a work assignment:
    
    1.  Click **Break Value**.
    2.  Click **Add**.
    3.  Enter information in the [Break Value fields](#Break_value_fields).
        
    4.  Click **Apply**.
    5.  To delete a break value:
        1.  Select the check box next to the break value and then click **Delete**. A confirmation message is displayed.
        2.  Click **OK**.
10.  Click **Save**.

## Mass copy and update work assignment rules

You can add multiple new work assignment rules based on one or more existing rules. Each new rule is based on a selected item family, item family set, or handling unit type.

For example, you can define a work assignment rule with the configuration you want for order sequence processing. Then you can copy the rule and select the item families, item family sets, or handling unit types for which new rules are created.

1.  Select **Outbound > Picking > Work Assignments**.
2.  Click **Work Assignment Rules** > **Rules**.
3.  From the **Actions** drop-down list, select **Copy Sequence Rule**.
4.  Enter filter criteria to display the rules to copy.
5.  Click **Next**.
6.  From the **Field** drop-down list, select one of the following options:
    -   **Item Family**: A group of related or similar items.
    -   **Item Family Set**: A group of item families that can be picked together for sequenced orders.
    -   **Handling Unit Type**: A type of handling unit, such as a pallet, tote, stillage, trolley, or slot on a stillage or trolley.
7.  In the **Available Attributes** column, select the check box next to the attributes that apply. A new work assignment rule will be created for each of the selected attributes and for each of the selected work assignment rules.
8.  Click **Next**.
9.  Review the list of work assignment rules that have been created.
    
    **Note**: The new rule is named after the copied rule but includes the selected attribute name.
    
10.  Click **Finish**.

## Configure work assignment rule groups

1.  Select **Configuration > Outbound > Picking > Work Assignments**.
2.  Click **Work Assignment Rules**.
3.  To add rules to an existing group:
    1.  Above the grid, click **Rules**.
    2.  In the grid, select the check box next to the rules.
    3.  From the **Actions** drop-down list, select **Add to Existing Group**.
    4.  From the **Name** drop-down list, select the group.
    5.  Click **Save**.
4.  To add rules to a new group:
    1.  Above the grid, click **Rules**.
    2.  In the grid, select the check box next to the rules.
    3.  From the **Actions** drop-down list, select **Create New Group**.
    4.  In the **Name** and **Description** fields, enter the values.
    5.  Click **Save**.
5.  To add or modify a group:
    1.  Above the grid, click **Groups**.
    2.  Perform one of the following tasks:
        -   To add a group, click **Add**.
        -   To modify a group, in the grid, click the work assignment group.
    3.  Enter information in the [Work Assignment Rule Group fields](#Work_Assignment_Rule_Group_fields).
    4.  In the **Available** column, select the check box for the work assignment rules.
    5.  To arrange the sequence that the application executes the rules, in the **Selected** column, click the row and then drag it to the correct position.
    6.  Click **Save**.

## Work Assignment fields

 
| Field | Description |
| --- | --- |
| Maximum When Not Specified | Value that determines the default maximum number of starter pallets that can be included in a single work assignment for the transport equipment handling unit. A starter pallet is a major quantity base pick that is used to begin a less than full pallet picking tour. This value is used if there is no transport equipment associated with the shipment or if there is no maximum value associated with the transport equipment handling unit. The maximum number of starter pallets is typically configured to correspond to the number of floor spots on the transport equipment. Set this value to zero or blank if you do not want to limit the number of starter pallets on a work assignment. |
| Full Pallets | If Yes, then full pallets can be used as starter pallets to which additional picks can be added. You may want to allow full pallet picks to be starter pallets and allow additional picked inventory to be placed on top if your common storage pallet height is shorter (when filled with inventory) than the pallet height wanted for shipping.<br > If No, then full pallets cannot be used as starter pallets and operators are not directed to pick additional inventory to full pallets. |
| RF Pick Display | Value that determines which work assignment picks are displayed to the operator. In pick zones that are configured to provide visibility to work assignment picks, the application displays the list of picks when an operator starts a pick work assignment. Visibility to work assignment picks allows the operator to perform the picks out of sequence, which may be necessary to accommodate certain types of picking equipment.<br>-   • **Display All Picks**: Displays all of the picks in the work assignment.
<br>-   • **Display Picks by Source Pick Zone**: Displays only the picks in the work assignment that are sourced from the pick zone in which the operator is currently working. |
| Confirm Destination LPN | If Yes, then when an operator is performing multiple work assignments that are picked to the same destination LPN, the application prompts the operator to confirm the destination LPN after each pick. For example, if an operator performs two work assignments at once, but enters the same LPN as the destination for each assignment, then the operator must confirm the destination LPN after completing each pick. Select Yes to ensure operators are picking work assignments to the correct destination LPN; however, this will increase the time it takes to complete work assignments that are picked to one LPN.<br > If No, then the application does not prompt the operator for the destination LPN when multiple work assignments are picked to the same destination LPN.<br>
**Notes**: 

<br>

-   • If there are multiple destination LPNs for a consolidated pick, such as when picking multiple work assignments that allow consolidation, then the application always prompts the operator for the destination LPN, regardless of this configuration.
<br>-   • This field does not affect operators picking a single work assignment.
<br>

 |
| Reset Planned Order Sequence | Value that indicates the start of the Planned Order Sequence sequential numbering scheme. You use this value to reset the Planned Order Sequence so that previous Planned Order Sequence values can be reused.<br > For example, if the reset value is 001 and the current planned order sequence value is 099, then if the next order is downloaded with a planned order sequence value of 001, then that order can be planned into the slot after the slot planned with sequence value 099.<br > A planned order sequence value is populated on orders downloaded by the host. This value is required for order sequence processing to ensure that orders are allocated, picked, and shipped in the sequential order required by the customer. |
| Shipping Date Option | Date that Warehouse Labor Management uses to derive the cut-off time and close time for the work assignment.<br > Cut-off time is the point at which new picks can no longer be added to the work assignment. Cutoff time is calculated using the closest shipping or delivery date of all order lines on the work assignment plus the estimated picking time for the work assignment and the travel time from last pick's source location to the staging location.<br > Close time is the point at which the application closes the work assignment. When a handling unit is closed, the following actions take place:<br>-   • The application allows the operator to complete the current pick (for a non-slotted handling unit) or the picks for the current slot (for a slotted handling unit). This is used to maintain the integrity and sequence of the slot before closing the handling unit.
<br>-   • The application cuts remaining picks from the work assignment and automatically plans them to a new work assignment.
<br>-   •
    
    If any pick for a slot cannot be completed in time for the ship date, all the picks for the slot will be cancelled.
    
    <br>
    
    **Note**: Picks for a slot are always handled together. If picking for a slot has started, the application does not close the handling unit until remaining picks for the same slot are all picked. If any pick for a slot needs to be cancelled because of insufficient time, then all picks for the same slot are cancelled.
    
    <br>
<br > A cut-off and close time can be defined manually, for example, if Warehouse Labor Management is not integrated or if a user wants to override it. See [Order Sequence Processing](../../../../picking/order-sequence-processing.md). |
| Order Sequence Loading | Order in which master handling unit LPNs are manually loaded onto transport equipment based on item family set sequence. If there are multiple handling units for the item family set, the Order Sequence Loading field determines the order in which the LPNs are loaded on the transport equipment. The order is determined by the item family set sequence assigned to the LPN.<br>-   • **Sequence**: LPNs for the same item family set are loaded in item family set sequence order. For example, if the item family set sequence is 001, 002, and 003, then the LPNs must be loaded in the following order: 001, 002, and 003.
<br>-   • **Reverse Sequence**: LPNs for the same item family set are loaded in reverse order of the item family set sequence. For example, if the item family set sequence is 001, 002, and 003, then the LPNs must be loaded in the following order: 003, 002, and 001. |

## Item Family Set Sequence fields

 
| Field | Description |
| --- | --- |
| Sequence Set Name | Name of the item family set. An item family set is a group of item families that you want to be able to assign to the same work assignment rule for picking sequenced orders to a master handling unit. |
| Sequence Set Description | Text that further describes the item family set. |
| Sequence Length | One or more zeros, which represent the number of characters used to specify the sequence. For example, enter 000 to specify a 3-digit sequence number; enter 00000 to specify a 5-digit sequence number. |
| Mass Create | If Yes, a sequence set is created for and assigned to each selected item family. A number is appended to each item family set name to differentiate the item family sets from one another.<br > If No, only one sequence set is created, and it is assigned to the item family set.<br > The **Mass Create** field is not available when modifying a set sequence. |

## Work Assignment Rules fields

 
| Field | Description |
| --- | --- |
| Name | Name of the work assignment rule. A work assignment rule is a reusable, named configuration that can be used individually or in combination with other work assignment rules (as a work assignment rule group) to generate a work assignment, or multiple work assignments if the number of available picks exceeds the capacity of a single work assignment. A work assignment rule defines how pick tasks are evaluated for inclusion in work assignments generated by the rule, as well as how the picks are sorted prior to inclusion in a work assignment, and grouped within individual work assignments. |
| Description | Text that further describes the work assignment rule. |
| Type | Type of picks that are included in the work assignment.<br>-   • **Outbound Order**: Only picks allocated to fulfill an outbound order are included in the work assignment.
<br>-   • **Replenishment**: Only picks allocated to fulfill a replenishment are included in the work assignment.
<br>-   • **Work Order**: Only picks allocated to fulfill a work order are included in the work assignment.
<br > The criteria available for section (such as for pick order, selection, grouping, sequence, and breaking) for the work assignment is limited to criteria that matches the type of picks that can included on the work assignment. |
| Client | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. |
| Release Action | Action used to release the pick work for the work assignment.<br>-   • **Create Work**: Generates directed work for the work queue.
<br>-   •
    
    **Produce Pick List Report**: Generates a report that can be printed and given to an operator for performing the picks for the work assignment.
    
    <br>
    
    **Note**: If you select this option, you must also add the **gen\_usr\_id** environment variable to the Pick Release Manager job (PICK-RELEASE-MANAGER). Jobs are maintained in the Console, under Jobs.
    
    <br>
<br>-   • **Produce Sequenced Handling Unit Documents**: Generates a Master Handling Unit Label report for a master handling unit and labels for the slots on the handling unit when a work assignment is released. This option can be assigned to the work assignment rule for a master handling unit that is used to pick sequenced orders to slots on the handling unit. |
| Pick to LPN Level | LPN level to which work assignments created from this rule are picked.<br>-   • **LPN (Pallet)**: Work assignments created from this rule are picked to an LPN; operators must scan an LPN as the To ID prior to starting an assignment. The application tracks the inventory by the LPN to which it is picked, and retains any individual case IDs and case-level serialization previously associated with the inventory.
<br>-   •
    
    **Sub-LPN (Case)**: Work assignments created from this rule are picked to a sub-LPN. If selected, when an operator scans the To ID prior to starting a work assignment, the ID is processed as a sub-LPN (even if an LPN is scanned). The application tracks the inventory by the sub-LPN to which it is picked; however, individual case IDs are not retained, and case-level serialization is not tracked if multiple cases are picked to the sub-LPN. When an operator scans the physical sub-LPN as the To ID, the application automatically generates an LPN identifier to associate with the physical sub-LPN. Therefore, each work assignment (and its picked inventory) is associated with a unique sub-LPN (user defined) and a unique LPN (application defined). The application also tracks the sub handling unit type for each sub-LPN scanned as the To ID, if applicable. This is useful for work assignments that contain case or each picks being sent to the same customer.
    
    <br>
    
    See [Work assignments picked to sub-LPNs](../work-assignments.md).
    
    <br>
<br>
**Notes**:

<br>

-   • Carton picks are excluded from work assignments built with a rule configured to pick to the sub-LPN level.
<br>-   • If the **Require Sub-LPN Capture** inventory settings configuration is set to Yes for the warehouse or client (in a 3PL environment), then the application tracks the case identifier and respective catch quantity. However, if a work assignment is picked to a sub-LPN, the individual case information (including catch quantity) is no longer retained. Therefore, the application does not prompt for sub-LPN capture if a work assignment is picked to a sub-LPN.
<br>-   •
    
    Voice devices do not support tracking handling units. Therefore, when a voice operator picks a work assignment to an LPN or sub-LPN, the application does not track any associated handling unit or sub handling unit type.
    
    <br>
<br>

 |
| Operation | Work operation that identifies the type of directed work that is created for the work assignment. Select an operation if you selected **Create Work** in the **Release Action** field. |
| Force to Pick Up Previous LPNs | If Yes, an operator who resumes an incomplete work assignment is directed to pick up the previously picked inventory. Select Yes to ensure that the remaining picks are picked to the original LPN.<br > If No, an operator who resumes an incomplete work assignment is not directed to pick up the previously picked inventory. |
| Drop at Work Zone Change | If Yes, then during picking for a work assignment, the operator is notified when all of the picks in the current work zone are complete. Select Yes, for example, to notify the operator so that the operator can choose to deposit the work assignment to a pickup and deposit location where it can be picked up by another operator in the work zone of the next pick.<br > If No, then the operator is not notified when the picks in the current work zone are complete. |
| Assign Slot | If Yes, the application assigns a slot number to each pick that is generated by a slot work assignment rule. Select Yes for a master work assignment rule that is processed in conjunction with a slot work assignment rule. In this configuration, the two rules are added to a rule group so that the application processes the slot rule and then the master rule. With the **Assign Slot** field set to Yes for the master rule, the application assigns a slot number to each pick based on the slot rule from which it was processed.<br > If handling unit types are specified for the work assignment rule, then picks are assigned slot numbers based upon one of the following configurations:<br>-   • The handling unit type specified in the GROUP BREAK area of the slot work assignment rule
<br>-   • The handling unit types associated with the slots of the handling unit type specified in GROUP BREAK area for the master work assignment rule
<br > To assign slots without handling units, see [Work assignment setup for picking to slots](../work-assignments.md). To assign slots based on handling unit configurations, see [Handling unit slots setup tasks](../../../inventory/lpn-handling/handling-unit-slots-setup-tasks.md).<br > If No, the work assignment rule does not assign a slot number to each pick. Select No for work assignments that are not picked to slots, or for a slot work assignment rule that is processed with a master work assignment rule. |
| To Previous Operator After Inline Replenishment | If Yes, then if an operator sets down an incomplete work assignment to perform an in-line replenishment, the same operator is directed to resume the same work assignment upon completing the in-line replenishment. An in-line replenishment is a replenishment performed by a picking operator during a work assignment when the specified location does not have the pick quantity available. Select Yes to ensure that the operator who stops working on a work assignment to complete an in-line replenishment is also directed to resume the work assignment when the replenishment is complete.<br > If No, then any authorized picking operator may resume the work assignment interrupted by an in-line replenishment. |
| Prevent Pick Consolidation | If Yes, the application does not consolidate picks for the same item (same attributes and source location) during picking. If multiple orders contain picks for the same item, setting this field to Yes ensures that the application will not consolidate picks across multiple orders for the same work assignment.<br > This configuration is useful for rules used to build work assignments for sequenced orders. Sequenced orders are used for picking and shipping inventory in the same item family set sequence for multiple orders in a sequenced fashion, typically in the order in which the items are required in a production line. For example, assume there are 4 each picks (2 for item A and 2 for item B) meant to be picked in alternating order (1A, 1B, 1A, 1B). If this field is set to Yes, the application directs the operator to pick the items in order sequence instead of consolidating the picks into 2 picks of 2 eaches (2A, 2B).<br > **Note**: Preventing pick consolidation is especially useful if operators pick sequenced orders to non-slotted handling units. In this case, preventing pick consolidation retains the pick and deposit sequence of stacked items. However, if operators pick sequenced orders to slotted handling units, the deposit sequence is kept regardless of this configuration because each pick has an assigned slot. Since the deposit sequence to slotted handling units is enforced even if picks are grouped, preventing consolidation in this case may lead to increased travel time for pickers with no difference in the result.<br > If No, the application does not prevent pick consolidation, meaning that multiple picks for the same item may be consolidated into a single pick. |
| Pick Tasks on Existing Work Assignments | If Yes, then the application can build new work assignments using pick tasks that are already built into an existing work assignment. For example, assume the application builds a new work assignment using a rule with this field set to Yes. If there are picks on existing work assignments that meet the rule criteria for the new assignment, the application removes the picks from the existing work assignment and adds them to the new work assignment.<br > **Note**: When this field is set to Yes, any existing work assignment that has not been acknowledged may be downsized by the application, and possibly deleted altogether, if the removed picks were the last picks in the assignment. However, if all of the existing eligible picks to be removed are included in a trolley work assignment (picking to slots), the application does not remove them from the existing assignment.<br > If No, then the application cannot remove picks on existing work assignments for new assignments. |
| Fill Work Assignment with Similar Picks First | Determines if and how the application prioritizes sorting similar picks to fill a single work assignment until a new work assignment is needed (based on the group break value for the rule).<br>-   • **Item Number**: Picks are prioritized by item first, and then other defined sequence criteria are applied. For example, assume the criteria sequence for a rule is defined by pick zone first. If you select Items in this field, the application instead groups all of the picks for the same item first, and then sorts them by pick zone before adding them to the work assignment.
<br>-   • **Order Number**: Picks are prioritized by order first, and then other defined sequence criteria are applied.
<br>-   • **No Selection (blank)**: The application does not attempt to fill work assignments with similar picks first.
<br > If you select a value for this field, and if the capacity for the current work assignment is reached, additional picks for the same item or order may be added to a new work assignment that includes picks for additional items or orders based on the selection criteria. However, the application attempts to ensure that the same item or order is only included in one split work assignment. For example, assume the value of this field is Items, and that Item A must be split across two work assignments due to capacity. One of the work assignments contains only picks for Item A, and the other includes the remaining picks for Item A and any other eligible picks that meet the selection criteria, if there is available capacity.<br > If you select a value for this field and the **Pick Tasks on Existing Work Assignments** field is set to Yes, the application may split an item or order to more than one mixed work assignment in certain scenarios. It is recommended that if you select a value for this field, then the **Pick Tasks on Existing Work Assignments** field should be set to No to avoid unexpected behavior.<br > Similarly, if you select a value for this field, then the **Split Pick Tasks Across Assignments** field should be set to No.<br > It is also recommended that if you select a value for this field, the **Assign Picks to Existing Assignment** field should be set to Never to ensure that picks are not added to or removed from an existing work assignment that contains similar picks. |
| Assign Picks To Existing Assignment | Determines whether and when the application is allowed to add picks to an existing work assignment.<br>-   • **Always**: The application can assign picks to the work assignment at any time, including after acknowledgment, as long as the work assignment is not complete.
<br>-   • **Before In Progress**: The application can assign picks after the work assignment has been created, but not after an operator acknowledges (signs on to) the directed work to perform the work assignment.
<br>-   • **Never**: Prevents the application from assigning additional picks to an existing, generated work assignment, even during the first run of pick release.
<br>-   • **Single**: The application can only assign picks to the work assignment during the first run of pick release. For example, if a group of picks is released and List 1 is created using a rule with this field set to Single, then while the application is still evaluating the initial group of picks to build into additional work assignments, eligible picks can be added to List 1 until all picks in the group have been evaluated. If more picks are released, then the application does not consider assigning additional picks to List 1. |
| Split Pick Tasks Across Assignments | If Yes, then during the generation of work assignments, if a single pick exceeds the available capacity of a work assignment, the application splits the pick across two work assignments. For example, if a pick quantity is 10 but the work assignment capacity can only allow 3, then with this field set to Yes, a pick quantity of 3 is added to the first assignment and the pick for the remaining 7 is added to another work assignment. The application splits pick tasks based on the picking UOM to ensure that all split quantities are pickable.<br > If this is set to Yes, then **Fill Work Assignment with Similar Picks First** must be blank to fill work assignments to maximum capacity. For example, if **Fill Work Assignment with Similar Picks First** is set to Orders, then new work assignments will be created for orders that exceed the capacity of the existing work assignment (leaving available capacity).<br > If No, then if a pick exceeds the available capacity of a work assignment, the pick is not split and instead must be added as a single pick to a work assignment with available capacity for the original pick quantity. |
| Max Starter Pallets Per Assignment | Maximum number of starter pallets that can be included in a single work assignment. A starter pallet is a major quantity base pick that is used to begin a less than full pallet picking tour. Set this value to zero or blank if you do not want to limit the number of starter pallets in a work assignment. The value you specify here overrides the value set for the **Maximum When Not Specified** field on the work assignment. |
| Handling Unit Type | Handling unit type that is required for work assignments generated using this rule. If you specify a handling unit type and also define group break values, the application uses the value that represents the lowest capacity. For example, if the handling unit type supports a maximum weight of 500, but you specify a group break value to be a maximum weight of 450, the application limits the work assignment to 450. If a handling unit type is specified on the order line, the application uses that handling unit type and does not assign the picks for that order line to a work assignment that uses a different handling unit type. |
| Max Handling Units Per Assignment | Maximum number of handling units that can be included in a work assignment created with the rule. If you select a value from the **Handling Unit Type** drop-down list, then the maximum number of handling units defines the capacity of the work assignment based on the maximum volume or weight (if lower than the break value) for the handling unit type.<br > For example, if the handling unit type Pallet has a maximum volume of 10,000 cubic inches, and the maximum number of handling units per assignment for the rule is 2, then the maximum capacity of a work assignment is 20,000 cubic inches (2 x 10,000). However, if you specify a handling unit type and also define group break values, the application uses the value that represents the lowest capacity. Therefore, if the break value for the rule is 8 cubic feet (13,824 cubic inches), then the application uses the break value maximum for work assignments created with the rule because it is a lower capacity than the volume of 2 pallets (20,000 cubic inches). Alternatively, if the break value is greater than 20,000 cubic inches, then the handling unit capacity is used instead.<br>

**Notes**:

<br>

-   • If you enter a value greater than 1, then the **Assign Picks To Existing Assignment** field should be set to Never.  
<br>-   • When processing work assignments with multiple handling units, the application does not re-plan picks based on pick cancellations or skipped picks. For example, if a pick for the first handling unit is cancelled, the application would not move any picks destined for the second handling unit to the first handling unit. Similarly, if a pick is skipped on the first handling unit, the application will not move the skipped pick to the second handling unit.
<br>-   • Labels are only printed for handling units to which inventory has been picked. Labels are not printed for empty handling units.
<br>

 |

## Work Assignment Rule Group fields

 
| Field | Description |
| --- | --- |
| Enable Work Assignment Group | If Enabled, the work assignment rule group is enabled for use. A work assignment rule group must be enabled to make it available for selection when creating work assignments either manually or automatically.<br > If Disabled, the work assignment rule group is not available for selection when creating a work assignment. |
| Name | Name of the work assignment rule group. A work assignment rule group is a set of work assignment rules that you want the application to run sequentially when creating work assignments based on the rule group. |
| Description | Description that further defines the work assignment rule group. |
| Client | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. |

## Break Value fields

 
| Field | Description |
| --- | --- |
| Group Break Function | Attribute used to define the capacity of a work assignment.<br>-   • **Count**: Defines capacity by the quantity of the attribute selected in the **Group Break Field** and **Maximum Quantity** fields. For example, you can restrict a work assignment to a single item or to a maximum number of cartons.
<br>-   • **Volume**: Defines capacity by a cubic volume, the values for which you enter in the **Maximum Volume** and **Volume Threshold** fields. You can also enter a value for **Maximum Pick Weight** to specify the maximum weight of picks that can be added to a work assignment after the volume threshold has been met. Volume calculations depend on the accuracy of item footprint information.
<br>-   • **Weight**: Defines capacity by weight, which you enter in the **Maximum Weight** field.
<br>-   • **Pick Quantity**: Defines capacity by the unit quantity, which you enter in the **Maximum Pick Quantity** field. See [Work assignment rule break values](../work-assignments.md). |
| Group Break Field | Entity by which the capacity of a work assignment is determined, such as the maximum number of orders allowed. The value in the **Maximum Quantity** field determines how many can be included in a work assignment. For example, if this field is set to Items and the **Maximum Quantity** field is set to 5, then work assignments built using the work assignment rule cannot include more than 5 items. This field is only available if the **Group Break Function** field is set to **Count**. |
| Maximum Quantity | Value that determines the maximum quantity for a work assignment; the **Group Break Field** value determines the entity for which the max quantity applies. For example, if the **Group Break Field** is set to Items and the value of this field is 5, then work assignments built using the work assignment rule cannot include more than 5 items. This field is only available when the **Group Break Function** field is set to **Count**. |
| Maximum Volume | Maximum cubic volume of inventory to include on a work assignment. The volume of the inventory is derived from the dimensions specified for the item footprint UOMs of the picked inventory. This field is only available if the **Group Break Function** field is set to **Volume**.<br > **Note**: If you specify a handling unit type for the work assignment rule and also define group break values, the application uses the value that represents the lowest capacity. For example, if the selected handling unit type has a maximum of 5,000 cubic inches and the maximum volume break value is 5 cubic feet (8,640 cubic inches), then the application uses the handling unit type capacity instead of the break value maximum for work assignments created with the rule. |
| Minimum Volume | Minimum volume of inventory that is required to create a work assignment with the rule. The volume of the inventory is derived from the dimensions specified for the item footprint UOMs of the picked inventory. For example, you can set a higher minimum volume to exclude case picks but allow full layer picks. Only available if the **Group Break Function** field is set to **Volume**. |
| Volume Threshold | Value that defines the cubic volume of the work assignment, at or above which you want to restrict the weight of each subsequent pick added to the work assignment. The value by which subsequent picks are restricted is defined in the **Maximum Pick Weight** field. A volume threshold is used to avoid adding heavy picks to the end of a work assignment. This field is only available if the **Group Break Function** field is set to **Volume**. |
| Maximum Pick Weight | Maximum weight of a pick that can be added to a work assignment after the value specified for **Volume Threshold** has been met. This field is used to limit the weight of picks that are added to the end of a work assignment. This field is only available if the **Group Break Function** field is set to **Volume**. |
| Maximum Weight | Maximum amount of weight allowed for a work assignment. The weight of the inventory is derived from the weight specified for the item footprint UOMs of the picked inventory. Only available if the **Group Break Function** field is set to **Weight**.<br > **Note**: If you specify a handling unit type for the work assignment rule and also define group break value by weight, the application uses the value that represents the lowest capacity. For example, if the selected handling unit type has a maximum weight of 400 pounds and the maximum weight break value is 500 pounds, then the application uses the handling unit type capacity instead of the break value maximum for work assignments created with the rule. |
| Minimum Weight | Minimum amount of inventory by weight that is required to create a work assignment with the rule. The weight of the inventory is derived from the weight specified for the item footprint UOMs of the picked inventory. Only available if the **Group Break Function** field is set to **Weight**. |
| Maximum Pick Quantity | Maximum unit quantity that is allowed for a work assignment. This value is typically used to limit a work assignment for a slot to the number of pieces that the slot can hold. Only available if the **Group Break Function** field is set to **Pick Quantity**. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
