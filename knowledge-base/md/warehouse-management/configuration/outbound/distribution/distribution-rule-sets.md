---
title: "Distribution Rule Sets"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/distribution_rule_sets.htm"
source: "/content/distribution_rule_sets.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Outbound"
  - "Distribution"
  - "Distribution Rule Sets"
sections:
  - "Distribution rules"
  - "Distribution overage rules"
  - "Quantity distribution options"
  - "UOM Quantity"
  - "Outbound Order Percentage"
  - "Store Ordered Percentage"
  - "Add or modify a rule set"
  - "Rule fields"
images: []
source_sha1: 866119615f326caafcafe03a01d5ef7112a90366
---
# Distribution Rule Sets

A rule set consists of one or more rules that the application uses to distribute inventory from a planned inbound order line to one or more outbound order lines. During distribution processing, the application executes one rule at a time, in sequential order, until distribution of the inventory from the inbound order line is complete.

A rule set is assigned to a distribution type; all of the distributions assigned to the same inbound order line must have the same distribution type. In this way, the same rule set is used to execute the distribution of the inbound inventory to all of the associated outbound order lines.

Each rule in a rule set contains a rule type (method used to distribute inventory) and a list of properties (such as quantity, order percent, and rounding mode) for which you can configure specific values.

You arrange the rules in a rule set in sequential order, according to the order in which you want the application to process the rules, to distribute inventory to multiple customers (distribution orders).

For example, you can ensure that each distribution order receives a fixed amount of inventory before each order is filled to a certain percentage. You can also configure the assignment of inventory so that distribution orders are either filled evenly or are filled in such a way as to avoid any orders being completely shorted in the event of insufficient inventory.

A distribution rule set assigns inventory based on the distribution quantity and does not exceed that quantity. For example, if a rule is configured to assign a fixed 25 cases to each order, but a previous rule in the rule set already allocated 25 cases to the order, then that order would not be subject to this rule because it has already reached the threshold amount for that rule of 25 cases. Similarly, if a distribution order is filled before the rule set finishes executing, that distribution does not receive additional inventory when the remaining rules execute.

The application processes the rules in a rule set once, so a rule set should be configured to fill 100% of the distribution if possible. In the event that a configured rule set does not fill a distribution order completely, there is a default rule in place that ensures 100% of the distribution order is filled if the necessary inventory is available in storage. This default rule sorts orders by priority, early ship date, and then remaining percentage.

## Distribution rules

A distribution rule controls how received inventory is assigned to distributions. A rule can be configured to evenly distribute the same amount to each order, to distribute different amounts to each order based on a percentage of what each store ordered, or to distribute a specific UOM quantity.

When inventory is received for distribution to multiple orders, the application processes the individual rules of distribution rule set sequentially to distribute the inventory to each order. You can arrange the rules to execute in any order you choose to fit the needs of the distribution. You also define the order in which each distribution receives inventory, such as by early ship date to help ensure that those orders are fulfilled on time.

## Distribution overage rules

Distribution overage rules are similar to distribution rules, except that they are assigned to rule sets used specifically for over distributions. Over distributions occur when the amount of inventory received is greater than the expected distribution and storage amount. For example, you may receive more inventory against an inbound order line than what was expected. Instead of storing the inventory you can use the over distribution process to push it out to the distributions associated with that inbound order line. For this process to take place, the inbound order line and the distributions must be configured to allow over distribution (quantities greater than the order quantity).

A distribution overage rule set consists of one or more distribution overage rules that are configured and applied to an over distribution. If you do not have a distribution overage rule set assigned to a distribution type for the distributions and an over distribution occurs, a default rule is executed that defines how the excess inventory is distributed. The default rule assigns one case to each distribution until the excess inventory is gone, and the rule sorts distribution by remaining percentage and then priority.

A distribution overage rule set assigns excess inventory to distributions until the inventory is gone. This means that if after all the rules in the overage rule set have been executed to completion, and there is still excess inventory needing to be over distributed, the default overage rule runs until the excess inventory is gone.

## Quantity distribution options

Distribution rules can be configured to distribute a fixed UOM quantity to each distribution, up to a specified percentage of each distribution’s order quantity, or by the percentage of the distribution’s order quantity in relation to the entire inbound order line quantity.

### UOM Quantity

The UOM quantity method is used to ensure that each distribution associated with the same inbound order line receives a pre-determined amount of inventory. Rules configured around this method are useful for situations in which you want to ensure that each customer receives some portion of inventory to satisfy a minimum demand. For example, if the possibility exists that the distributions may not be filled to 100%, this rule would still ensure that each distribution receives an equal amount of inventory before the application executes the next rule in the rule set.

For example, a simple configuration for this rule gives 25 cases to each distribution by setting the UOM property to cases and the quantity to 25. Each distribution receives 25 cases before the next rule executes. However, a rule configured with this method will not exceed the distribution order quantity. For example, if the rule was set to assign 25 cases, and an outbound order line was for 20, the application would assign only 20 to the distribution.

### Outbound Order Percentage

The outbound order percent method is used to distribute up to a specified percentage of each distribution's order quantity to each distribution associated with the same inbound order line. Rules configured around this method focus on the distribution order quantity instead of a fixed amount of inventory to distribute, and may assign a different quantity to each distribution. This method ensures that each distribution receives the same percentage relative to the original quantity ordered.

For example, a simple configuration of this rule could be an order percentage of 50%. If distribution A was for 100 cases and distribution B was for 1,000 cases, then using this method, the application assigns 50 cases to distribution A and 500 cases to distribution B before executing the next rule in the rule set.

### Store Ordered Percentage

The store ordered percentage method distributes inventory based on the percentage of a distribution's order quantity in relation to the entire distribution quantity on the inbound order line. Distribution rules configured around this method give a proportionate amount of inventory to each distribution associated with the same inbound order line based on the quantities of other distributions for the same inbound order line.

For example, if an inbound order line's total quantity is 1,000 divided between three distributions as shown in the following table, the application calculates the ordered percentage for each distribution and distributes available inventory based on that percentage.

  
| Distribution | Actual<br > ordered quantity | Calculated ordered percentage |
| --- | --- | --- |
| A | 500 | 50% |
| B | 200 | 20% |
| C | 300 | 30% |
| TOTAL | 1,000 | 100% |

When distribution inventory is assigned, each distribution receives the calculated ordered percentage of the available inventory. If a quantity of 400 is received, the following table shows how each distribution is assigned inventory.

  
| Distribution | Calculated ordered percentage | Assigned quantity |
| --- | --- | --- |
| A | 50% | 200 |
| B | 20% | 80 |
| C | 30% | 120 |
| TOTAL | 100% | 400 |

When additional inventory is available and assigned to these distributions, whatever that quantity happens to be (not to exceed the ordered quantity), Distribution A receives 50%, Distribution B receives 20%, and Distribution C receives 30%.

## Add or modify a rule set

1.  Select **Configuration > Outbound > Distribution > Distribution Rule Sets**.
2.  To enable distribution processing and use of rule sets, select **ENABLED**.
3.  Perform one of the following tasks:
    -   To add a rule set, click **Add**.
    -   To modify a rule set, in the grid, click the description of the rule set.
    -   To copy a rule set, in the grid, select the check box next to the description, and then click **Copy**.
4.  In the **Description** field, enter text that describes the rule set.
5.  In the **Rule Set Type** field, select one of the following options:
    -   **Distribution Rule**: The rule set is used to assign expected inventory to distributions. It is not used to process inventory in excess of the expected amount on the inbound order line.
    -   **Distribution Overage Rule**: The rule set is used to assign unexpected inventory from an inbound order line after distribution (outbound order) quantities have already been filled. Create an over distribution for use in situations when you would rather overfill outbound orders than have to store the unexpected inventory for future use.
6.  To configure rules for the rule set:
    1.  Under **RULES**, perform one of the following tasks:
        -   To add a rule, click **Add**.
        -   To modify a rule, in the grid, click the description of the rule.
        -   To copy a rule, in the grid, select the check box next to the description, and then click **Copy**.
    2.  Enter information in the [Rule fields](#Rule_fields).
    3.  To define the order in which the application assigns inventory to distributions associated with the same inbound order line:
        1.  Click **Sort Orders**.
        2.  In the **Available** column, select the distribution attributes that apply.
            
            **Note**: You can sort distributions by any data related to the distribution order; however, the following options are commonly used:
            
            -   **Priority**: Sorts distributions by the processing priority defined on the distribution. Distributions with a higher priority are filled first.
            -   **Remaining %**: Sorts distributions by the percentage remaining needed to complete the distributions. Distributions needing the most inventory in order to reach completion are filled first.
            -   **Early Ship Date**: Sorts distributions by the date they are scheduled to ship. Distributions with an earlier ship date are filled first. For example, if a rule is configured to distribute a fixed number of 25 cases to each distribution and to sort by priority and then early ship date, the application assigns inventory to the distribution with a higher processing priority first, as defined on the distribution. In the event that both distributions have the same priority, the inventory is then assigned by the early ship date, so that distribution with the nearest ship date is filled first.
            
        3.  Click **Apply**.
    4.  Click **Apply**.
7.  Click **Save**.

## Rule fields

 
| Field | Description |
| --- | --- |
| Rule Type | Defines the method by which the application distributes inventory for the rule.<br > For a standard distribution rule (not an overage rule) select one of the following options:<br>-   • **Distribute by UOM Quantity**: Requires you to specify a quantity by UOM that should be distributed. Used to ensure that each distribution associated with the same inbound order line receives a pre-determined amount of inventory.
<br>-   • **Distribute by Order Percentage**: Requires you to specify a percentage of the distribution order. Used to distribute up to a specified percentage of each distribution's order quantity to each distribution associated with the same inbound order line.
<br>-   • **Distribute by Store Ordered Percentage**: Enables the application to distribute inventory based on a percentage of the distribution's order quantity in relation to the entire distribution quantity. Distribution rules configured around this method give a proportionate amount of inventory to each distribution associated with the same inbound order line based on the quantities of other distributions for the same inbound order line.
<br > For an overage distribution rule, select one of the following options:<br>-   • **Distribute Overage Evenly**: Enables the application to distribute the overage evenly to each of the distributions assigned to the same inbound order line. Used to ensure that each of the distributions receives the same amount.
<br>-   • **Distribute Overage by Store Ordered Percentage**: Enables the application to distribute the overage amount to each distribution based on the percentage of the distribution's order quantity in relation to the entire distribution quantity on the inbound order line.
<br>-   • **Distribute Overage by UOM Quantity**: Requires you to specify a quantity by UOM to distribute. Used to distribute a pre-determined amount of the overage inventory to each distribution associated with the same inbound order line. This rule is typically used to complete the distribution of excess inventory by assigning a specific quantity (such as 1 case) to each distribution until the excess inventory is gone.
<br > For examples, see [Quantity distribution options](#Quantity_distribution_options). |
| Quantity | Quantity of inventory that is distributed. Enter the quantity that the distribution (outbound order) receives when the rule is executed.<br > Only available if the **Rule Type** field is set to Distribute by UOM Quantity or Distribute Overage by UOM. |
| Order Percentage | Percentage of inventory that is distributed. Enter the percentage that the distribution (outbound order) receives when the rule is executed.<br > Only available if the **Rule Type** field is set to Distribute by Outbound Order Percentage or Distribute by Store Ordered Percentage. |
| Rounding Mode | Defines how distribution quantities are rounded to the nearest rounding UOM, if at all.<br > **Note**: For the purpose of providing an example for each rounding mode, assume the **Rounding Unit of Measure** field is set to Case, and that there are 10 Eaches in a Case.<br>-   • **Automatic**: Rounds the distributed quantity to the nearest whole rounding UOM by traditional rounding means. For example, if the distributed quantity is supposed to be 54 eaches, the application rounds down to 50, or 5 cases. If the distributed quantity is supposed to be 55 eaches, the application rounds up to 60, or 6 cases.
<br>-   • **None**: Prevents the application from rounding distribution quantities. If a distribution can be satisfied with a quantity of 53, then the application assigns 53 eaches made up of 5 cases and 3 eaches. If this value is selected, breaking UOMs is allowed to fill a distribution.
<br>-   • **Round Down:** Rounds the distributed quantity to the next lowest whole rounding UOM. For example, if a distribution can be satisfied with a quantity of 53 available eaches, the application would assign 50 to the distribution because 50 eaches is the next lowest whole UOM of 5 cases.
<br>-   • **Round Up**: Rounds the distributed quantity to the next highest whole rounding UOM. For example, if a distribution can be satisfied with a quantity of 53 eaches, the application would assign 60 because 60 eaches is the next highest whole UOM of 6 cases.
<br > **IMPORTANT**: If rounding up would cause the application to assign more inventory to a distribution than what is required for the order, the quantity is not rounded up. In the event that case breaking is not allowed to satisfy a distribution quantity, the quantity is rounded down to the next whole rounding UOM. |
| Rounding Unit of Measure | Unit of measure that the application uses as its lowest form of measurement in the event it must round to the nearest UOM as specified in the **Rounding Mode** field. If the rule is configured to round distribution quantities, and a rounding UOM is not specified, then the application uses the case-level UOM. |
| Unit of Measure | Unit of measure (UOM) in which the quantity defined for the rule is distributed. Only available if Distribute by UOM Quantity or Distribute Overage by UOM Quantity is selected for the rule type. For example, if you enter 50 in the **Quantity** field and Case in the **Unit of Measure** field, the rule distributes up to 50 cases to the distribution. |
| Case Breaking Mode | Value that determines whether opening case-level UOMs to remove unit quantities is allowed in order to satisfy a distribution quantity.<br>-   • **Break Case On Remainder**: Only allows opening cases when doing so completes the ordered quantity for the distribution.
<br>-   • **Break Case On Rule**: Always allows opening cases regardless of whether doing so completes the ordered quantity for a distribution.
<br>-   • **Never Break Case**: Does not allow opening cases to remove unit quantities. Instead, the distribution quantity is rounded down to the nearest case quantity. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
