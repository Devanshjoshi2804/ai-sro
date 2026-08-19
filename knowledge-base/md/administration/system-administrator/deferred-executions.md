---
title: "Deferred Executions"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/admin/deferred_executions.htm"
source: "/content/admin/deferred_executions.htm"
toc_path:
  - "Administration"
  - "System Administrator"
  - "Deferred Executions"
sections:
  - "Rerun a failed deferred command"
  - "Deferred Execution fields"
images: []
source_sha1: 36b7b140964b98307f6eb5eab088cce6586ce61c
---
# Deferred Executions

Deferred execution enhances application performance and allows users to continue working in the application while a command is running rather than waiting for the application to complete a command or task before resuming work. Commands are run in the application either manually or according to a scheduled job. A job is a command that is configured to run in the background while the application server instance is operating.

You use the Deferred Executions page to view the deferred commands in the application and to rerun the commands that the application failed to process successfully. You can also view the execution status of the commands.

For example, assume a command is configured to print a shipping report and labels after a pallet is deposited in a location for shrink wrapping. After the pick operator deposits the picked pallet to the shrink wrapper location, instead of waiting until the report and labels print, a deferred command runs to allow the operator to deposit the pallet and continue to work on the next pick task.

The deferred command to print the required paperwork and labels runs and is displayed on the Deferred Executions page. If there is a processing error when the application runs the deferred command, then it remains displayed, allowing the user to manually rerun the failed command after troubleshooting the issue.

**Note**: The Deferred Executions page was created using Page Builder; therefore, users assigned to the Portal Server Administrator role can configure the page layout and properties. See [Page layout configuration attributes](../extensions/page-builder.md) and [Add or modify a grid type page layout configuration](../extensions/page-builder/grid.md).

## Rerun a failed deferred command

1.  Select **System Administrator > Deferred Executions**.
2.  View information in the [Deferred Execution fields](#Deferred_Execution_fields).
3.  To rerun the deferred command, in the grid, select the command, and then from the **Actions** drop-down list, select **Retry Execution**. The application reruns the command and updates the **Execution Date** and **Modified User ID**.

## Deferred Execution fields

 
| Field | Description |
| --- | --- |
| **Execution ID** | Unique number that identifies the deferred command. |
| **Added Date** | Date and time on which the command was deferred. |
| **Deferred Command** | Command that is planned to process later. |
| **Deferred Date** | Scheduled date and time to rerun the command. |
| **Execution Date** | Date and time at which the command was last processed. |
| Execution Status | The processing status returned by the application after rerunning a command. If the Execution Status is zero (0), then the command was run successfully. If the Execution Status is a value greater than zero and the deferred date is before or equal to the application time, then the command failed, and you should rerun the command. If the command failed and the deferred date is later than the application time, then you should rerun the command before the scheduled deferred date and time. |
| Affected Rows | The number of rows that are affected when you run the command. If the value is zero, then no operations are performed. |
| Execution Type | The type of command which helps is identifying why and when the command was run. |
| Key Value | Brief description of the command that was run. |
| Modified Date | Date and time on which the command was rerun. |
| Modified User ID | The user ID of the person who reran the command. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
