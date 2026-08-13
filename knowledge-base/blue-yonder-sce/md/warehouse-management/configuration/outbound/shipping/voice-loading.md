---
title: "Voice Loading"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/voice_loading.htm"
source: "/content/voice_loading.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Outbound"
  - "Shipping "
  - "Voice Loading"
sections:
  - "Configure voice loading"
  - "Voice Loading Set fields"
images: []
source_sha1: e23179514a38359763e137955ef3e427caf761f5
---
# Voice Loading

If your facility uses voice devices to move inventory from ship staging locations onto transport equipment, then you must configure the voice functionality for loading.

You can configure multiple sets of configurations, each for a different region code. When an operator requests a loading function using the region code, the voice settings for that region are applied.

For example, for one region you provide prioritized directed work to operators, and in another region the operator manually selects the loading task to perform. As another example, you may require operator confirmations for one region, but not for another. New operators can be directed to use the region that requires confirmations, and experienced operators for whom confirmations are not necessary can be directed to use the other region.

You specify one or more work operations, which apply to all loading regions, that a voice operator can perform. For voice loading you can specify, for example, the Load Shipping Trailers (LOD) operation. This association is required so that when the voice operator selects a function, such as loading, the application attempts to find directed work for any of the operations associated with that function. If no operation codes are assigned to a voice function, then directed work cannot be retrieved for that function.

## Configure voice loading

1.  Select **Configuration > Outbound > Shipping > Voice Loading**.
2.  Select the directed work operations that can be used to perform voice loading:
    1.  Click **Operation**.
    2.  In the **Available Operations** column, select the check box next to the operations that apply.
    3.  Click **Apply**.
3.  Under **SETTINGS**, perform one of the following tasks:
    -   To add a voice loading set, click **Add**.
    -   To modify a voice loading set, in the grid, click the description of the voice loading set.
4.  Enter information in the [Voice Loading Set fields](#Voice_Loading_Set_fields).
5.  To delete a voice loading set:
    1.  Under **SETTINGS**, select the check box next to the description of the voice loading set to delete.
    2.  Click **Delete**. A confirmation message is displayed.
    3.  Click **OK**.
6.  Click **Save**.

## Voice Loading Set fields

 
| Field | Description |
| --- | --- |
| Description | Text that defines the configuration for this region. For example, you may configure one region to use directed work and another region for operators to manually select the tasks to perform. |
| Region | Number that the operator speaks to select this region. A region is an identifier for a group of settings that take effect when a voice operator performs a loading function using the region code. (A region is not related to a physical location in the warehouse.)<br > You can configure voice loading differently, by region, to accommodate situations that require different settings. For example, you can configure a region to use directed work, and specify the operations to use, and then configure another region that does not use directed work. |
| Use Directed Work | If Yes, then the application directs the operator to the location where the loading operation begins. Even if you select Yes, the operator has the option to specify a location by scanning or speaking the location to complete manual loading in directed mode.<br > If No, then an operator that signs on to a loading function using this region must manually select the location at which to begin the loading operation. |
| Spoken LPN Length | Number of digits of the LPN, starting from the last digit, that the operator must speak when specifying an LPN.<br > For example, if LPNs in your facility typically consist of 8 digits, then to save time, you may require that the operator speak only the last 4 digits of the LPN.<br > If this value is less than 1 or greater than 99, then the operator can speak any number of digits and must typically pause or say "ready" for the voice device to accept the spoken value. |
| Capture Transport Equipment ID | If Yes, the voice device prompts the operator to speak the identifier of the transport equipment to load. Select Yes if you want the operator to confirm the transport equipment identifier.<br > If No, the application does not prompt the operator to confirm the identifier of the transport equipment. Select No if you want to save time by not requiring the confirmation. |
| Spoken Transport Equipment Length | Number of digits of the transport equipment identifier, starting from the last digit, that the operator must speak when specifying the transport equipment to load.<br > For example, if transport equipment identifiers in your facility typically consist of 8 digits, then to save time, you may require that the operator speak only the last 4 digits of the identifier.<br > If this value is less than 1 or greater than 99, then the operator can speak any number of digits and must typically pause or say "ready" for the voice device to accept the spoken value. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
