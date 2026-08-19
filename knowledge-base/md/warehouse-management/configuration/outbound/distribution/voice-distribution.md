---
title: "Voice Distribution"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/voice_distribution.htm"
source: "/content/voice_distribution.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Outbound"
  - "Distribution"
  - "Voice Distribution"
sections:
  - "Configure voice distribution"
  - "Voice Distribution Set fields"
images: []
source_sha1: 0f8551c96a952fdac4c8035bbd3d0d668929bc35
---
# Voice Distribution

If your facility uses voice devices to deposit inventory to distribution or customer (store) locations, then you must configure the voice functionality for distribution.

You can configure multiple sets of configurations, each for a different region code. When an operator requests a distribution function using the region code, the voice settings for that region are applied.

For example, for one region you may limit the maximum number of LPNs per assignment to 1, and for another region you may set the limit at 4. An operator using a hand truck signs on to region 1, and an operator using a fork truck signs on to region 4. As another example, you may require operator confirmations for one region, but not for another. New operators can be directed to use the region that requires confirmations, and experienced operators from whom confirmations are not necessary can be directed to use the other region.

You specify one or more work operations, which apply to all distribution regions, that a voice operator can perform. For voice distribution you can specify, for example, the Distribution Transfer (DSTTRN) operation. This association is required so that when the voice operator selects a function, such as distribution, the application attempts to find directed work for any of the operations associated with that function. If no operation codes are assigned to a voice function, then directed work cannot be retrieved for that function.

## Configure voice distribution

1.  Select **Configuration > Outbound > Distribution > Voice Distributions**.
2.  Under **GENERAL**, select the directed work operations for performing voice distribution:
    1.  Click **Operation**.
    2.  In the **Available** column, select the check box next to the operations to use.
    3.  Click **Apply**.
3.  Under **SETTINGS**, perform one of the following tasks:
    -   To add a voice distribution set, click **Add**.
    -   To modify a voice distribution set, in the grid, click the description of the voice distribution set.
    -   To copy a voice distribution set, in the grid, select the check box next to the description, and then click **Copy**.
4.  Enter information in the [Voice Distribution Set fields](#Voice_Distribution_Set_fields).
5.  To delete a voice distribution set:
    1.  Under **SETTINGS**, select the check box next to the description of the voice distribution set to delete.
    2.  Click **Delete**. A confirmation message is displayed.
    3.  Click **Apply**.
6.  Click **Save.**

## Voice Distribution Set fields

 
| Field | Description |
| --- | --- |
| Description | Text that defines the configuration for this region. For example, you may configure one region to require an operator to confirm spoken locations, and another region to disable that requirement. You can then require new operators to use the region that requires the confirmation, while experienced operators can use the region that does not require it. |
| Region Number | Number that the operator speaks to select this region. A region is an identifier for a group of settings that take effect when a voice operator performs a distribution function using the region code. (A region is not related to a physical location in the warehouse.)<br > You can configure voice distribution differently, by region, to accommodate situations that require different settings. For example, a region can be configured for new operators to require more confirmations than a region configured for experience operators. Regions may also be configured differently (for example, the maximum LPNs per assignment) for use with different types of equipment. |
| Directed Work | If Yes, then the application directs the operator to the location of the LPNs that need to be distributed.<br > If No, then an operator that signs on to a distribution function using this region must manually select the location at which to pick up the distribution LPNs. |
| Directed Work Filters | If Yes, the operator is prompted to filter for the location in which the directed work is to be performed. When the operator selects the distribution function using this region, the operator must specify an additional work filter (building, aisle, or work zone). The application locates directed work that can be performed in the locations. Select Yes to save processing time when there are potentially many locations at which directed work could be performed.<br > If No, the operator is not prompted to enter a filter value to obtain directed work.<br > Only available if **Directed Work** is set to Yes. |
| Maximum LPNs per Assignment | Maximum number of LPNs an operator can pick up at one time. If this value is less than 1 or greater than 99, then the voice device allows the operator to request 1 LPN to pick up. |
| Assignment Passing | If Yes, an operator can pass the current assignment to another operator. Operators may need to pass an assignment for a number of reasons; for example, their shift may be over or they are limited to working in one work area and need to pass the work to a user in the next work area.<br > If No, an operator is not allowed to pass the current assignment to another operator. |
| Over Distributing | If Yes, an operator is allowed to deposit more inventory to a distribution location than the quantity that the application specified.<br > If No, operators are not allowed to deposit additional inventory to the distribution location to which the application directed them. Instead, any additional inventory is processed as either expected or unexpected residual inventory. |
| Signoff During Assignments | If Yes, an operator can speak "sign off" to sign off of a voice device while an assignment is in progress. However, if there is inventory on the device, the operator is prompted to deposit the inventory prior to being signed off. If labels are required for the picked inventory, they are printed prior to deposit.<br > **Note**: The application does not require an operator to deposit inventory prior to sign off for cluster picking and bulk cluster picking; instead, the device prompts the operator to deposit the inventory when the operator signs on again.<br > If No, an operator is not allowed to sign off of a directed work assignment that is in progress. |
| Skip Aisle | If Yes, an operator can speak "skip aisle" to bypass an aisle during a distribution assignment. The operator is directed back to the skipped location at the end of the assignment, and at that time the operator is not allowed to skip the aisle. If the **Repick Skips** field is set to Yes, the operator can return to the skipped aisle at any time.<br > If No, operators are not allowed to bypass an aisle to which they were directed. |
| Repick Skips | If Yes, operators can speak "repick skips" to return to a skipped location at any time during their assignment.<br > If No, operators cannot choose to return to a location that was bypassed at any time during their assignment.<br > If a location is skipped, the operator is directed back to the skipped location at the end of the assignment. At that time, the operator is not allowed to skip the location. |
| Skip Slot | If Yes, an operator can speak "skip slot" to bypass a location during a distribution assignment. The operator is directed back to the skipped location at the end of the assignment, and at that time the operator is not allowed to skip the location. If the **Repick Skips** field is set to Yes, the operator can return to the skipped location at any time.<br > **Note**: In this context, a "slot" is a location.<br > If No, operators are not allowed to bypass a location during a distribution assignment. |
| Multiple Open Containers | If Yes, multiple containers can be open simultaneously at a single deposit location.<br > If No, the operator is only allowed to have one container open at a distribution deposit location. Once the container is completed and closed, a new container can be opened for deposit. |
| System Generates Container ID | If Yes, the application generates a container ID automatically when an operator opens a new container at a distribution location.<br > If No, the operator is prompted to enter a container ID when opening a new container. |
| Validate Containers | If Yes, then during a distribution deposit, the operator must speak the container ID so the application can validate that it is the correct container for the deposit.<br > If No, then during a distribution deposit, the operator is only prompted for the container ID if there are multiple open containers in the location. Select No if you do not require the operator to confirm the container when there is only one open container in a location. |
| Validate Container Length | Number of digits, starting with the last digit in the container ID, that the operator must speak to confirm a container. For example, if container IDs are 8 characters in length, then you may require the operator to speak only the last 4 digits of the ID to confirm that it is correct container.<br > If any number of digits is acceptable, enter 0 (zero). Then the operator can speak any number of digits and must typically pause or say "ready" for the voice device to accept the spoken value.<br > Only available when the **Validate Containers** field is set to Yes. |
| Expected Residual Location | Location where expected residuals are taken after the assignment is complete. An expected residual occurs when excess inventory exists after the distribution deposit process is complete. When an operator moves inventory through a distribution deposit area, it is possible that not all of the inventory is needed for the outbound orders. At the completion of the deposit process, an audit runs on any additional inventory. If the amount of excess inventory matches the expected amount of excess and the audit is successful, the inventory is considered residual and it is directed to this storage location through putaway. |
| Pickup and Deposit Location | Temporary holding location for distribution inventory that is being handled by operators using this region's configurations. This location is typically used for depositing a distribution temporarily so that it can be picked up and completed later by the same or another operator. |
| Unexpected Residual Location | Location where unexpected residuals are taken after the assignment is complete. If no location is specified, unexpected residuals are taken to the expected residual location.<br > Unexpected residuals occur when there is unplanned excess inventory at the end of the deposit process. As a result, the operator is directed to deposit the unplanned inventory to this exception location. A user must determine what the issue is and then gather information on how to resolve it. Once resolved, the operator can clear the exception and move the inventory out of the unexpected residual location. You can view distribution exceptions on the Receiving Issues page in the Receiving module. |
| Confirm Spoken Location | If Yes, the operator must confirm the spoken location identifier. If set to Yes, the voice device repeats the spoken location digits, and the operator must confirm the digits by saying "yes" or reject the value by saying "no".<br > If No, the device does not repeat the location digits spoken by the operator. Select No if you want to save time by not requiring the confirmation. |
| Confirm Spoken Location Length | Number of digits of the location, starting from the last digit, that the operator must speak to confirm a location. For example, if location IDs are 8 characters in length, you may require the operator to speak only the last 4 digits to confirm that it is the correct location.<br > If any number of digits is acceptable, enter 0 (zero). Then the operator can speak any number of digits and must typically pause or say "ready" for the voice device to accept the spoken value.<br > Only available when the **Confirm Spoken Location** field is set to Yes. |
| Location Check Digit Length | Number of the location check digits, starting from the last digit, that the operator must speak when specifying a location's primary check digit. For example, if location check digits are 5 characters in length, you may require the operator to speak only the last 3 digits to confirm that it is the correct location.<br > If this value is less than 1 or greater than 99, then the operator can speak any number of digits and must typically pause or say "ready" for the voice device to accept the spoken value. |
| Confirm Spoken LPN | If Yes, the operator must confirm the spoken LPN when closing a container. If set to Yes, the voice device repeats the spoken LPN, and the operator must confirm the value by saying "yes" or reject the value by saying "no".<br > If No, the device does not repeat the LPN spoken by the operator when closing a container. Select No if you want to save time by not requiring the confirmation. |
| Confirm Spoken LPN Length | Number of digits of the LPN, starting from the last digit in the LPN, that the operator must speak to specify an LPN. For example, if LPNs are 8 characters in length, you may require the operator to speak only the last 4 digits to confirm that it is the correct LPN.<br > If any number of digits is acceptable, enter 0 (zero). Then the operator can speak any number of digits and must typically pause or say "ready" for the voice device to accept the spoken value.<br > Only available when the **Confirm Spoken LPN** field is set to Yes. |
| Use LUT Status Updates | If Yes, the application sends two-way message status updates. If set to Yes, the application sends status updates using the lookup table (LUT) format. When using LUT, the device sends a message and waits for the application to receive the message before continuing the work.<br > If No, the application sends status updates using the outbound data record (ODR) format. The ODR format lets the device confirm that the application received the message while continuing the work. |
| Print Exception Labels | If Yes, an exception label is printed automatically for residual inventory when there is unexpected residual inventory remaining after an assignment is complete.<br > If No, an exception label is not printed automatically. |
| Allow Ready Confirmations | If Yes, an operator can speak "Ready" to confirm the deposit of a full LPN to a distribution location.<br > If No, an operator is prompted to confirm the deposit of a full LPN by speaking the LPN or location, if required to do so. |
| Print Residual Labels | If Yes, a label is printed automatically for residual inventory when there is expected residual inventory remaining after an assignment is complete.<br > If No, a residual label is not printed automatically. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
