---
title: "Policy Maintenance - Override"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/policies/policy_maintenance_-_override.htm"
source: "/content/policies/policy_maintenance_-_override.htm"
toc_path:
  - "Administration"
  - "System Administrator"
  - "Configuration"
  - "Policy"
  - "Policy Maintenance - Override"
sections:
  - "Override a policy"
  - "Policy Maintenance - Override fields"
  - "Policy Maintenance - Override (Details) fields"
images: []
source_sha1: 84ebcfc3193c05c41e10df39f1e06bcca773d946
---
# Policy Maintenance - Override

In a multi-warehouse environment, you can use Policy Maintenance - Override to add or override a policy for the current warehouse. The Policy Maintenance - Override page displays policies that can be (or are currently) overridden for the current warehouse and warehouse-specific policies.

**Note**: If you try to override a policy that cannot be overridden for the current warehouse, then an error message is displayed.

A "1" in the Override column indicates that an override is in effect for the current warehouse.

**Note**: When you add a warehouse-specific policy, the **Override** value is set to 1 by default.

To remove a policy override (reinstate the default warehouse value), delete the warehouse-specific policy.

## Override a policy

1.  Select **System Administrator > Configuration > Policy > **Policy Maintenance - Override.
2.  To add a warehouse-specific policy, from the **Actions** drop-down list, select **Add**.
3.  Enter information in the [Policy Maintenance - Override fields](#Policy_Maintenance_-_Override_fields).
    
4.  Click **Save**.
    
5.  To override a policy value, in the grid, select the policy (with an **Override** value of 0), and then from the **Actions** drop-down list, select **Override**.
    

**Note**: If you select a policy that is already overridden, then an error message is displayed.

7.  To edit policy details:
    1.  In the grid, select the check box next to the policy.
    2.  Under **DETAILS**, perform one of the following tasks:
        -   To add new details, from the **Actions** drop-down list, select **Add**.
        -   To modify details, in the grid, select the check box next to the data, and then from the **Actions** drop-down list, select **Edit**.
    3.  Enter information in the [Policy Maintenance - Override (Details) fields](#Policy_Maintenance_-_Override_\(Details\)_fields).
    4.  Click **Save**. A confirmation message is displayed.
8.  Click **OK**.
9.  To remove a policy override:
    1.  In the grid, select the policy, and then from the **Actions** drop-down list, select **Delete**.
    2.  In the **Comments** field, enter a comment, and then click **Execute**.

## Policy Maintenance - Override fields

 
| Field | Description |
| --- | --- |
| Policy Code | Code that identifies the functional area or object to which a group of policies applies. For example, policies that define how work orders are processed are located under WORK-ORDER-PROCESSING. |
| Policy Variable | Code that identifies a group of policies within a policy code. For example, the WORK-ORDER-PROCESSING/COMMANDS-TO-EXECUTE policy variable defines a series of policies that determine whether or not specified commands are executed at specific points during the work order process. |
| Policy Value | Code that identifies a single policy within a policy variable. This value is the identifier for which detail values are configured. For example, the WORK-ORDER-PROCESSING/COMMANDS-TO-EXECUTE/EXEC-AT-ALLOCATE policy value determines if and what command is executed when a work order is allocated. |
| Comments | Description of the purpose of the policy or functional area to which the policy is related, and information about how the policy is used. |

## Policy Maintenance - Override (Details) fields

 
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
