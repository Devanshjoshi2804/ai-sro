---
title: "Voice Counting"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/voice_counting.htm"
source: "/content/voice_counting.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inventory"
  - "Counting"
  - "Voice Counting"
sections:
  - "Configure voice counting"
  - "Voice Counting Set fields"
images: []
source_sha1: 229439589ddc0d088b53cb3003966a39764057da
---
# Voice Counting

If your facility uses voice devices to perform inventory counting operations, then you must configure the voice functionality for counting.

You can configure multiple sets of configurations, each for a different region code. When an operator requests a counting function using the region code, the voice settings for that region are applied.

For example, for one region you provide prioritized directed work to operators, and in another region the operator manually selects the counting task to perform.

You specify one or more work operations, which apply to all counting regions, that a voice operator can perform. For voice counting you can specify, for example, the Cycle Count (CNT), Detail Cycle Count (CNTDTL), and Audit Count (CNTAUD) operations. The association of an operation is required for a region that uses directed work. When the voice operator selects a function, such as counting, the application attempts to find directed work for any of the operations associated with that function. If no operation codes are assigned to a voice function, then directed work cannot be retrieved for that function.

## Configure voice counting

1.  Select **Configuration > Inventory > Counting > Voice Counting**.
2.  Select the directed work operations for performing voice counting:
    1.  Click **Operation**.
    2.  In the **Available** column, select the check box next to the operations that can be performed using a voice device.
    3.  Click **Save**.
3.  Under **SETTINGS**, perform one of the following tasks:
    -   To add a voice counting set, click **Add**.
    -   To modify a voice counting set, in the grid, click the description of the voice counting set.
4.  Enter information in the [Voice Counting Set fields](#Voice_Counting_Set_fields).
5.  Click **Apply**.
6.  To delete a voice counting set:
    1.  Under **SETTINGS**, select the check box next to the description of the voice counting set to delete.
    2.  Click **Delete**. A confirmation message is displayed.
    3.  Click **OK**.
7.  Click **Save.**

## Voice Counting Set fields

 
| Field | Description |
| --- | --- |
| Description | Text that defines the configuration for this region. For example, you may configure one region to use directed work and another region for operators to manually select the tasks to perform. |
| Region | Number that the operator speaks to select this region. A region is an identifier for a group of settings that take effect when a voice operator performs a counting function using the region code. (A region is not related to a physical location in the warehouse.)<br > You can configure voice counting differently, by region, to accommodate situations that require different settings. For example, you can configure a region to use directed work, and specify the operations to use, and then configure another region that does not use directed work. |
| Use Directed Work | If Yes, then the application directs the operator to the location where the cycle count is to be completed. Even if you select Yes, the operator has the option to specify a count location by scanning or speaking the location to complete a manual count in directed mode.<br > If No, then an operator that signs on to a counting function using this region must manually select the location at which to perform a count operation. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
