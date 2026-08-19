---
title: "Voice Replenishments"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/voice_replenishments.htm"
source: "/content/voice_replenishments.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inventory"
  - "Replenishments"
  - "Voice Replenishments"
sections:
  - "Configure voice replenishment"
  - "Voice Replenishment Set fields"
images: []
source_sha1: 83fb63562921a4a668b507d682dd3457c74ee5d2
---
# Voice Replenishments

If your facility uses voice devices to move inventory from reserve storage locations to primary pickface locations, then you must configure the voice functionality for replenishments.

You can configure multiple sets of configurations, each for a different region code. When an operator requests a replenishment function using the region code, the voice settings for that region are applied.

For example, you may require operator confirmations for one region, but not for another. New operators can be directed to use the region that requires confirmations, and experienced operators for whom confirmations are not necessary can be directed to use the other region.

You specify one or more work operations, which apply to all replenishment regions, that a voice operator can perform. For voice replenishment you can specify, for example, Case Replenishment (CRP) and Pallet Replenishment (PRP) operations. This association is required so that when the voice operator selects a function, such as replenishment, the application attempts to find directed work for any of the operations associated with that function. If no operation codes are assigned to a voice function, then directed work cannot be retrieved for that function.

## Configure voice replenishment

1.  Select **Configuration > Inventory > Replenishments > Voice Replenishments**.
2.  Select the directed work operations for performing voice replenishment:
    1.  Click **Operation**.
    2.  In the **Available** column, select the check box next to the operations to use.
    3.  Click **Save**.
3.  Under **SETTINGS**, perform one of the following tasks:
    -   To add a voice replenishment set, click **Add**.
    -   To modify a voice replenishment set, in the grid, click the description of the voice replenishment set.
4.  Enter information in the [Voice Replenishment Set fields](#Voice_Replenishment_Set_fields).
5.  Click **Apply**.
6.  To delete a voice replenishment set:
    1.  Under **SETTINGS**, select the check box next to the description of the voice replenishment set to delete.
    2.  Click **Delete**. A confirmation message is displayed.
    3.  Click **OK**.
7.  Click **Save**.

## Voice Replenishment Set fields

 
| Field | Description |
| --- | --- |
| Description | Text that defines the configuration for this region. For example, you may configure one region to require an operator to confirm spoken locations, and another region to disable that requirement. You can then require new operators to use the region that requires the confirmation, while experienced operators can use the region that does not require it. |
| Region | Number that the operator speaks to select this region. A region is an identifier for a group of settings that take effect when a voice operator performs a replenishment function using the region code. (A region is not related to a physical location in the warehouse.)<br > You can configure voice replenishment differently, by region, to accommodate situations that require different settings. For example, a region can be configured for new operators to require more confirmations than a region configured for experience operators. |
| Spoken LPN Length | Number of digits of the LPN, starting from the last digit, that the operator must speak when specifying an LPN.<br > If any number of digits is acceptable, select the **No Length Restriction** check box. Then the operator can speak any number of digits and must typically pause or say "ready" for the voice device to accept the spoken value. |
| Cancel LPN | If Yes, the operator can use the cancel LPN command to cancel the replenishment. If a replenishment is cancelled, the operator is prompted for a cancel reason to determine how the application processes the cancelled replenishment.<br > If No, an operator is not allowed to cancel a replenishment. |
| Capture Pickup Quantity | If Yes, the voice device prompts the operator to speak the pickup quantity, and the operator must confirm the quantity picked up from the replenishment source location.<br > If No, the voice device does not prompt the operator to confirm the quantity that was picked up from the source location. |
| Capture Replenishment Quantity | If Yes, the voice device prompts the operator to speak the quantity of inventory that was replenished, and the operator must confirm the quantity deposited in the replenishment destination location.<br > If No, the voice device does not prompt the operator to confirm the quantity that was deposited. |
| Override Pickup Quantity | If Yes, the operator can override the directed pickup quantity for a replenishment, and pick up a different quantity instead.<br > If No, an operator is not allowed to override the pickup quantity for a replenishment. |
| Override Location | If Yes, the operator can override the replenishment destination location directed by the application, and deposit the inventory to a different location.<br > If No, an operator is not allowed to override the replenishment destination location. |
| Confirm Spoken Location | If Yes, the operator must confirm the spoken location identifier. If set to Yes, the voice device repeats the spoken location digits, and the operator must confirm the digits by saying "yes" or reject the value by saying "no".<br > If No, the device does not repeat the location digits spoken by the operator. Select No if you want to save time by not requiring the confirmation. |
| Spoken Location Length | Number of digits of the location, starting from the last digit, that the operator must speak when specifying the source or destination location.<br > If any number of digits is acceptable, select the **No Length Restriction** check box. Then the operator can speak any number of digits and must typically pause or say "ready" for the voice device to accept the spoken value. |
| Location Check Digit Length | Number of the location check digits, starting from the last digit, that the operator must speak when specifying a location's primary check digit. For example, if location check digits are 5 characters in length, you may require the operator to speak only the last 3 digits to confirm that it is the correct location.<br > If this value is less than 1 or greater than 99, then the operator can speak any number of digits and must typically pause or say "ready" for the voice device to accept the spoken value. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
