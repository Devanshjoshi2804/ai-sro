---
title: "Policy Maintenance"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/policies/policy_maintenance.htm"
source: "/content/policies/policy_maintenance.htm"
toc_path:
  - "Administration"
  - "System Administrator"
  - "Configuration"
  - "Policy"
  - "Policy Maintenance"
sections:
  - "Add or modify a policy"
  - "Policy Maintenance fields"
  - "Policy Maintenance (Details) fields"
images: []
source_sha1: 6ab10d4887e8fc12a8feec0377dfd20f1486fe2c
---
# Policy Maintenance

The Policy Maintenance and Policy Maintenance-Override pages display the following policy information:

-   **Policy Code**: Top-level identifier for the functional area or object to which a group of policies applies. For example, the SYSTEM-SECURITY policy codes specify settings for system-level security control, such as rules for user password formats.
-   **Policy Variable**: Second-level identifier for a group of policies within a policy code. For example, the SYSTEM-SECURITY/PASSWORD-FORMAT policies define the level of complexity for user passwords, such as character type and length requirements.
-   **Policy Value**: Third-level identifier for a single policy within a policy variable. This value is the identifier for which detail values are configured. For example, the SYSTEM-SECURITY/PASSWORD-FORMAT/MAXIMUM-LENGTH policy represents the maximum number of characters allowed in a password.

When you select a policy code in the grid, policy value details are displayed in the DETAILS grid.

## Add or modify a policy

**Note**: In a multi-warhouse environment, any policies that you add using Policy Maintenance are policies that can be overridden for a specific warehouse.

1.  Select **System Administrator > Configuration > Policy > Policy Maintenance**.
2.  To add a policy, from the **Actions** drop-down list, select **Add**.
3.  Enter information in the [Policy Maintenance fields](#Policy_Maintenance_fields).
    
4.  Click **Save**.
    
5.  To view policy details, in the grid, select check box for the policy. The values are displayed in the DETAILS grid.
    
    **Note**: A policy value is only displayed once in the grid; however, if the policy value has multiple detail records, the total number of rows on the grid pagination toolbar includes the number of details.
    
6.  To edit policy details:
    1.  In the grid, select the check box next to the policy.
    2.  Under **DETAILS**, perform one of the following tasks:
        -   To add new details, from the **Actions** drop-down list, select **Add**.
        -   To modify details, in the grid, select the check box next to the row, and then from the **Actions** drop-down list, select **Edit**.
    3.  Enter information in the [Policy Maintenance (Details) fields](#Policy_Maintenance_\(Details\)_fields).
    4.  Click **Save**. A confirmation message is displayed.
    5.  Click **OK**.

## Policy Maintenance fields

 
| Field | Description |
| --- | --- |
| Policy Code | Code that identifies the functional area or object to which a group of policies applies. For example, policies that define how work orders are processed are located under WORK-ORDER-PROCESSING. |
| Policy Variable | Code that identifies a group of policies within a policy code. For example, the WORK-ORDER-PROCESSING/COMMANDS-TO-EXECUTE policy variable defines a series of policies that determine whether or not specified commands are executed at specific points during the work order process. |
| Policy Value | Code that identifies a single policy within a policy variable. This value is the identifier for which detail values are configured. For example, the WORK-ORDER-PROCESSING/COMMANDS-TO-EXECUTE/EXEC-AT-ALLOCATE policy value determines if and what command is executed when a work order is allocated. |
| Comments | Description of the purpose of the policy or functional area to which the policy is related, and information about how the policy is used. |

## Policy Maintenance (Details) fields

 
| Field | Description |
| --- | --- |
| Sort Sequence | Order in which the policy is applied. If you do not enter a value, the sort sequence is application-generated starting with a value of 0. Use the sort sequence when you define more than one detail row for the same policy value, and you want to specify the order in which the detail rows are applied. |
| Return String 1 | Character string data value that the policy looks for when it is implemented. |
| Return String 2 | Based on the value in Return String 1, additional character string data value that the policy looks for when it is implemented. |
| Return Number 1 | Integer data value that the policy looks for when it is implemented. Often used for turning a policy on or off, where 1 equals On and 0 equals Off. |
| Return Number 2 | Based on the value in Return Number 1, additional integer data value that the policy looks for when it is implemented. |
| Return Float 1 | Float (numbers with a decimal fraction) data value that the policy looks for when it is implemented. |
| Return Float 2 | Based on the value in Return Float 1, additional float data value that the policy looks for when it is implemented. |
| Comments | Description of the policy value and information about how the policy value is used. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
