---
title: "Handling unit slots setup tasks"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/handling_unit_slots_setup_tasks.htm"
source: "/content/handling_unit_slots_setup_tasks.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inventory"
  - "LPN Handling"
  - "Handling unit slots setup tasks"
sections: []
images: []
source_sha1: 2567d49d20fd51423177cd0d9fcb57437a03620c
---
# Handling unit slots setup tasks

If you want the application to direct work assignment picks to separate handling units (such as totes) that are transported by another (primary) handling unit (such as a trolley), you can define handling unit slots for the primary handling unit type.

To set up handling unit slots for a primary handling unit type:

1.  Define handling unit settings. Enable handling unit tracking for either the Inventory or Picking Container category. See [Handling unit categories](../lpn-handling.md).
2.  Define a handling unit type (such as a tote) that represents a slot on a primary handling unit.
    
    1.  Define its handling unit category as either Inventory or Picking Container. For tracking to take place, the handling unit category must be enabled for use under handling unit settings.
    2.  Enable the Container attribute to indicate that the handling unit type can contain inventory and that it has edges that stand up around the inventory.
    3.  Enable it for work assignments.
    4.  Define its capacity.
        
    
    Do not add handling unit slots to this handling unit type, because this is the handling unit slot that can be added to a primary handling unit type.
    
3.  Define the primary handling unit type.
    1.  Define its handling unit category as either Inventory or Picking Container. For tracking to take place, the handling unit category must be enabled for use under handling unit settings.
    2.  Enable it for work assignments.
    3.  Define its capacity. The capacity must be greater than cumulative capacity of the slots defined for the primary handling unit type.
    4.  Define its handling unit slots. For example, if the primary handling unit is a trolley that contains 6 totes, then when defining handling unit slots, add the Tote handling unit type and specify 6 slots (such as 1 through 6). The application uses the slot code, based on the configuration of the work assignment rule, to direct the operator to place a pick quantity into a specific slot.
4.  Configure a work assignment rule for the slot. See [Work Assignments](../../outbound/picking/work-assignments.md).
    1.  Configure the rule to not assign slots by setting the **Assign Slot** field to No. This field should be set to No for the slot rule, but set to Yes for the primary handling unit rule.
    2.  Configure the rule to include pick tasks on existing work assignments to ensure that the application considers as many same-item picks together as possible.
    3.  Define the criteria that determines how the application builds the work assignment:
        -   Selection criteria determines which picks are eligible to be included in work assignments using this rule, such as a particular item family
        -   Grouping criteria determines which picks can be included on the same work assignment, such as by order number
        -   Sequence criteria determines the order in which picks are sorted before being added to a work assignment, such as by item number
    4.  Define the capacity of the work assignment by the slot handling unit type.
5.  Configure a work assignment rule for the primary handling unit that contains the slots.
    1.  Configure the rule to assign slot numbers to picks by setting the **Assign**Slot field to Yes. This field should be set to Yes for the primary handling unit rule, but set to No for the slot rule.
    2.  Define the selection criteria to include the all the picks that meet the criteria defined by the slot work assignment rule. For example, if you created a slot work assignment rule called TOTE1 Rule, then configure the rule for the primary handling unit as follows: Field Name = Pick List Rule Name; Value = TOTE1 Rule.
    3.  Configure the work assignment grouping and sequence criteria with the same values that you defined for the slot work assignment rule.
    4.  Define the capacity of the work assignment by the primary handling unit type (such as the trolley), and then define a group break value that limits the contents of the list to the number of slots. For example, if the trolley contains 6 totes with one order per tote, then configure the group break for the trolley as follows: Break Value = Count; Group Break Field = Orders; Maximum Quantity = 6.
6.  Create a work assignment rule group that includes the work assignment rule for the primary handling unit type and the work assignment rule for the slot. A work assignment rule group enables you to run a number of work assignment rules together in order so that the results of first rule are considered when the second rule is running, and so on. For the rule group, arrange the sequence of the work assignment rules so that the slot rule is executed first, and then the primary handling unit rule. When the rule group is executed, the application creates a single work assignment that directs the operator to pick quantities to the individual slots on the primary handling unit.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
