---
title: "Count Release Rules"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/count_release_rules.htm"
source: "/content/count_release_rules.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inventory"
  - "Counting"
  - "Count Release Rules"
sections:
  - "Modify a count release rule"
  - "Count Release Rule fields"
  - "Count Zone Settings fields"
images: []
source_sha1: f50f3c3ab7771ff984cfd5ea180b65154ffa5699
---
# Count Release Rules

A count release rule is a configuration for a count type that determines the release action that takes place when a count for the type is generated. A release action can send count work to the work queue for RF directed counting or print counts on paper to hand to counting staff who will record the counts on paper and then manually enter the count results into the application. A count release rule also determines the attributes by which individual counts can be grouped, such as by count zone, item, or aisle. You may want to group counts by aisle, for example, so that a single operator would complete all of the counts in the same aisle.

In a facility that uses RF directed work, release rules are typically configured to create work, which releases directed work that is added to the work queue. An RF operator can sign on to the directed work to complete it.

If the release rule creates work, you can override the base priority at which the work enters the work queue. The override is used to create the directed work at a higher or lower priority depending on how quickly you want the work to be completed.

In a facility that uses paper-based counting, release rules are typically configured to generate count or audit sheets that can be printed. Counters use the count or audit sheets to record the results in each location. The results are then manually entered into the application.

A release rule configuration is applied, by default, to every count zone in which counts are released. However, for each release rule, you can override the settings for one or more count zones. For example, if the release rule is configured to create work, you can define an override for a count zone where eaches are picked to produce count sheets instead. In this scenario, when a cycle count is performed, directed work will be created when the count occurs in any zone except for the zone that contains the each pick locations, in which case a paper count will be performed.

Similarly, if the release rule is configured to group individual counts, for example, by aisle, you can configure an override for a count zone in which individual counts are grouped by both aisle and item.

The application provides a count release rule for each count type, so that by default an action occurs when a count for that count type is generated.

## Modify a count release rule

By default, the application provides a release rule for each count type, which you can modify according to your facility requirements. You cannot add or delete release rules.

1.  Select **Configuration > Inventory > Counting > Count Release Rules**.
2.  In the grid, click the count type to modify.
3.  Enter information in the [Count Release Rule fields](#Count_Release_Rule_fields).
4.  To select the attributes by which the application groups individual counts:
    1.  Under **GENERAL**, select **Count Grouping**.
    2.  In the **Available** column, select the check box next to the attributes to use.
    3.  Click **Apply**.
5.  To override the release rule settings for a specific count zone:
    
    **Note**: The **Override Settings by Count Zone** field is only available after you save changes to the rule.
    
    1.  Under **SETTINGS BY COUNT ZONE**, select **Override Settings by Count Zone**.
    2.  Perform one of the following tasks:
        -   To add an override, click **Add**.
        -   To modify an override, in the grid, click the count zone.
        -   To copy an override, in the grid, select the check box next to the count zone, and then click **Copy**.
    3.  Enter information [Count Zone Settings fields](#Count_Zone_Settings_fields).
    4.  To select the attributes by which the application groups individual counts:
        1.  Select **Count Grouping**.
        2.  In the **Available** column, select the check box next to the attributes to use.
        3.  Click **Apply**.
    5.  Click **Apply**.
6.  Click **Save**.

## Count Release Rule fields

 
| Field | Description |
| --- | --- |
| Action | Action the application performs for the release rule when a count is generated.<br>-   • **Produce Audit Sheet**: The application generates an audit sheet for you to print. This action is recommended when you are configuring a Count Audit count type and you do not want to create directed work for the audit.
<br>-   • **Produce Count Sheet**: The application generates a count sheet for you to print. This action is recommended when you are configuring a Cycle Count count type and you do not want to create directed work for the cycle count.
<br>-   • **Create Work**: The application creates count work (defined by the operation code configured for the count type) and sends it to the work queue. |
| Additional Arguments | Command line argument used to further define the action you want the application to perform after releasing the count. Contact your Blue Yonder project team if you would like to define additional arguments for the release rule. |
| Override Work Priority | If Yes, the **All Zones Priority** field becomes available for you to define the base priority for the work that is released to the work queue for the count type associated with the release rule. The base priority is the priority at which work enters the work queue.<br > If No, the application uses the base priority defined for the work operation associated with the count type for the release rule.<br > This field is only used if the selected action creates directed work. |
| All Zones Priority | Value that determines the base priority in which work is released to the work queue. The value defined for **All Zones Priority** overrides the base priority defined for the work operation for the count type associated with the release rule. For example, if the Count Audit count type is configured to use the Count Audit operation, and that operation is configured with a base priority of 2, you can override that priority with a higher or lower priority, depending on how quickly you want the work to be completed.<br > The priority you define applies to all count zones unless an exception is defined for a specific count zone.<br > Only available when the **Override Work Priority** field is set to Yes. |

## Count Zone Settings fields

 
| Field | Description |
| --- | --- |
| Count Zone | Unique identifier for the count zone to which this override applies. A count zone is a method of grouping locations for an inventory count. |
| Action | Action the application performs for the release rule when a count is generated.<br>-   • **Produce Audit Sheet**: The application generates an audit sheet for you to print. This action is recommended when you are configuring a Count Audit count type and you do not want to create directed work for the audit.
<br>-   • **Produce Count Sheet**: The application generates a count sheet for you to print. This action is recommended when you are configuring a Cycle Count count type and you do not want to create directed work for the cycle count.
<br>-   • **Create Work**: The application creates count work (defined by the operation code configured for the count type) and sends it to the work queue. |
| Additional Arguments | Command line argument used to further define the action you want the application to perform after releasing the count. Contact your Blue Yonder project team if you would like to define additional arguments for the release rule. |
| Override Priority | If Yes, the **Zone Override Priority** field becomes available for you to define the base priority for work that is released to the work queue for the count type associated with the release rule. The base priority is the priority at which work enters the work queue.<br > If No, the application uses the base priority defined for the work operation associated with the count type for the release rule.<br > This field is only used if the selected action creates directed work. |
| Zone Override Priority | Value that determines the base priority in which work is released to the work queue for work done in the specific count zone you define. The value defined for **Zone Override Priority** overrides the default base priority and, if defined, the override priority you defined for all count zones. For example, the Cycle Count count type is configured to use the Cycle Count operation, and the operation is configured with a base priority of 40. If you override that value with a priority of 30 for all zones and you define a priority of 10 for a count zone that contains each pick locations, then when a cycle count is generated, the counts in the zone that contains each pick locations will be counted before the cycle counts located in other zones.<br > Only available when the **Override Priority** field is set to Yes. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
