---
title: "Voice Putaway"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/voice_putaway.htm"
source: "/content/voice_putaway.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inbound"
  - "Storage"
  - "Voice Putaway"
sections:
  - "Configure voice putaway"
  - "Voice Putaway Set fields"
images: []
source_sha1: 7937c686b616044b5b6e3982ea1dd778584b01d7
---
# Voice Putaway

If your facility uses voice devices to move (put away) received or identified inventory into storage locations, then you must configure the voice functionality for putaway.

You can configure multiple sets of configurations, each for a different region code. When an operator requests a putaway function using the region code, the voice settings for that region are applied.

For example, for one region you may limit the maximum number of LPNs per assignment to 1, and for another region you may set the limit at 4. An operator using a hand truck signs on to region 1, and an operator using a fork truck signs on to region 4. As another example, you may require operator confirmations for one region, but not for another. New operators can be directed to use the region that requires confirmations, and experienced operators for whom confirmations are not necessary can be directed to use the other region.

You specify one or more work operations, which apply to all putaway regions, that a voice operator can perform. For voice putaway you can specify, for example, the Store (STO) operation. This association is required so that when the voice operator selects a function, such as putaway, the application attempts to find directed work for any of the operations associated with that function.

In undirected mode, after selecting a region and entering a starting location, an operator can either scan or speak an LPN that is in that location to start the putaway process. The user will either be directed to a putaway location by the application or, if the configuration allows it, manually choose the putaway location for the LPN.

## Configure voice putaway

1.  Select **Configuration > Inbound > Storage > Voice Putaway**.
2.  Select the directed work operations for performing voice putaway:
    1.  Click **Operation**.
    2.  In the **Available** column, select the check box next to the operations that can be used to perform putaway using a voice device.
    3.  Click **Save**.
3.  Under **SETTINGS**, perform one of the following tasks:
    -   To add a voice putaway set, click **Add**.
    -   To modify a voice putaway set, in the grid, click the description of the voice putaway set.
    -   To copy a voice putaway set, in the grid, select the check box next to the description, and then click **Copy**.
4.  Enter information in the [Voice Putaway Set fields](#Voice_Putaway_Set_fields).
5.  To delete a voice putaway set:
    1.  Under **SETTINGS**, select the check box next to the description of the voice putaway set to delete.
    2.  Click **Delete**. A confirmation message is displayed.
    3.  Click **OK**.
6.  Click **Save.**

## Voice Putaway Set fields

 
| Field | Description |
| --- | --- |
| Description | Text that defines the configuration for this region. For example, you may configure one to require an operator to confirm spoken LPNs and locations, and another region to disable that requirement. You can then require new operators to use the region that requires the confirmation, while experienced operators can use the region that does not require it. |
| Region | Number that the operator speaks to select this region. A region is an identifier for a group of settings that take effect when a voice operator performs a putaway function using the region code. (A region is not related to a physical location in the warehouse.)<br > You can configure voice putaway differently, by region, to accommodate situations that require different settings. For example, a region can be configured for new operators to require more confirmations than a region configured for experience operators. Regions may also be configured differently (for example, the maximum LPNs per assignment) for use with different types of equipment. |
| Max LPN per Assignment | Maximum number of LPNs an operator can pick up at one time. If this value is less than 1 or greater than 99, then the voice device allows the operator to request 1 LPN to pick up. |
| Use Directed Work | If Yes, then the application directs the operator to the source location of the putaway work.<br > If No, then an operator that signs on to a putaway function using this region must manually select the location at which to begin the putaway operation. |
| Confirm Spoken LPNs and Locations | If Yes, the operator must confirm the spoken LPN and location digit values. If selected, the voice device repeats the spoken LPN and location digits, and the operator must confirm the digits by saying "yes" or reject the value by saying "no".<br > If No, the device does not repeat the LPN and location digits spoken by the operator. Select No if you want to save time by not requiring the confirmation. |
| Voice Spoken LPN Length | Number of digits of the LPN, starting from the last digit, that the voice device speaks to the operator whenever the device speaks the LPN during putaway. For example, if LPNs in your facility typically consist of 8 digits, then to save time, you may require that the device speak only the last 4 digits of the LPN to the operator. If this value is less than 1 or greater than 99, the voice device speaks all the digits of the LPN. |
| Spoken LPN Length | Number of digits of the LPN, starting from the last digit, that the operator must speak when specifying an LPN.<br > For example, if LPNs in your facility typically consist of 8 digits, then to save time, you may require that the operator speak only the last 4 digits of the LPN.<br > If this value is less than 1 or greater than 99, then the operator can speak any number of digits and must typically pause or say "ready" for the voice device to accept the spoken value. |
| Spoken Location Length | Number of digits of the location, starting from the last digit, that the operator must speak when specifying the source or destination location.<br > For example, if locations in your facility typically consist of 8 digits, then to save time, you may require that the operator speak only the last 4 digits of the location.<br > If this value is less than 1 or greater than 99, then the operator can speak any number of digits and must typically pause or say "ready" for the voice device to accept the spoken value. |
| Capture Pickup Quantity | If Yes, the voice device prompts the operator to speak the quantity of inventory that was picked up for putaway. Select Yes if you want the operator to confirm the quantity that was picked up.<br > If No, the application does not prompt the operator to confirm the quantity that was picked up. Select No if you want to save time by not requiring the confirmation. |
| Capture Putaway Quantity | If Yes, the voice device prompts the operator to speak the quantity of inventory that was put away in a location. Select Yes if you want the operator to confirm the quantity that was deposited.<br > If No, the application does not prompt the operator to confirm the quantity that was deposited to the directed location. Select No if you want to save time by not requiring the confirmation. |
| Override Put Location | If Yes, the operator can override the putaway location to which the inventory is being directed with a different location.<br > If No, the operator is not allowed to deposit the inventory to a location other than the directed putaway location. |
| Location Check Digit Length | Number of the location check digits, starting from the last digit, that the operator must speak when specifying a location's primary check digit. For example, if location check digits are 5 characters in length, you may require the operator to speak only the last 3 digits to confirm that it is the correct location.<br > If this value is less than 1 or greater than 99, then the operator can speak any number of digits and must typically pause or say "ready" for the voice device to accept the spoken value. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
