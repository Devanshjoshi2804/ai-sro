---
title: "Policy History"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/policies/policy_history.htm"
source: "/content/policies/policy_history.htm"
toc_path:
  - "Administration"
  - "System Administrator"
  - "Configuration"
  - "Policy"
  - "Policy History"
sections:
  - "View Policy History"
  - "Policy History fields"
images: []
source_sha1: 23eff76ca21094e39d6194c179d70b964e936bbd
---
# Policy History

You can view information about the policies that have been added, changed, and deleted. The history information tells you the policy values before the change, policy values after the change, comments about the change, who made the change, and when the change was made. You can provide search criteria to limit the displayed information to specific policy changes. For example, you can provide a policy code to view all changes made to the related policies.

**Note**: In a multi-warehouse environment, default and current warehouse policy history information is displayed.

## View Policy History

1.  Select **System Administrator > Configuration > Policy > Policy History**.
2.  To filter the results, see [Filter information on a page](../../../../get-started/work-with-filters.md).
3.  View the information in the [Policy History fields](#Policy_History_fields).

## Policy History fields

 
| Field | Description |
| --- | --- |
| **Policy Code** | Code that identifies the functional area or object to which a group of policies applies. For example, policies that define how work orders are processed are located under WORK-ORDER-PROCESSING. |
| **Policy Variable** | Code that identifies a group of policies within a policy code. For example, the WORK-ORDER-PROCESSING/COMMANDS-TO-EXECUTE policy variable defines a series of policies that determine whether or not specified commands are executed at specific points during the work order process. |
| **Policy Value** | Code that identifies a single policy within a policy variable. This value is the identifier for which detail values are configured. For example, the WORK-ORDER-PROCESSING/COMMANDS-TO-EXECUTE/EXEC-AT-ALLOCATE policy value determines if and what command is executed when a work order is allocated. |
| **Warehouse** | Unique ID associated with the warehouse. |
| Sort Sequence | Order in which the policy is applied. If you do not enter a value, the sort sequence is application-generated starting with a value of 0. Use the sort sequence when you define more than one detail row for the same policy value, and you want to specify the order in which the detail rows are applied. |
| Action Type | Type of action taken on a policy.<br>-   • **Delete**: Policy was removed.
<br>-   • **Insert**: Policy was created.
<br>-   • **Update**: Policy was modified. |
| Old Return String 1 | Character string data value that the policy previously looked for when it was implemented. |
| New Return String 1 | Updated character string data value that the policy now looks for when it is implemented. |
| Old Return String 2 | Based on the value in Old Return String 1, additional character string data value that the policy previously looked for when it was implemented. |
| New Return String 2 | Based on the value in New Return String 1, additional updated character string data value that the policy now looks for when it is implemented. |
| Old Return Number 1 | Integer data value that the policy previously looked for when it was implemented. Often used for turning a policy on or off, where 1 equals On and 0 equals Off. |
| New Return Number 1 | Updated integer data value that the policy now looks for when it is implemented. Often used for turning a policy on or off, where 1 equals On and 0 equals Off. |
| Old Return Number 2 | Based on the value in Old Return Number 1, additional integer data value that the policy previously looked for when it was implemented. |
| New Return Number 2 | Based on the value in New Return Number 1, additional updated integer data value that the policy now looks for when it is implemented. |
| Old Return Float 1 | Float (numbers with a decimal fraction) data value that the policy previously looked for when it was implemented. |
| New Return Float 1 | Updated float (numbers with a decimal fraction) data value that the policy now looks for when it is implemented. |
| Old Return Float 2 | Based on the value in Old Return Float 1, additional float data value that the policy previously looked for when it was implemented. |
| New Return Float 2 | Based on the value in New Return Float 1, additional float data value that the policy now looks for when it is implemented. |
| Comment for Change | Text that describes why the change was made to the policy value. |
| Date Last Modified | Date and time the policy was last updated. |
| Last Modified By | User who most recently modified the policy. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
