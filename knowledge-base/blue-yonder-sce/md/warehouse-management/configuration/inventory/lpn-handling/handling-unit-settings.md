---
title: "Handling Unit Settings"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/handling_unit_settings.htm"
source: "/content/handling_unit_settings.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inventory"
  - "LPN Handling"
  - "Handling Unit Settings"
sections:
  - "Configure handling unit settings"
  - "Handling Unit Settings fields"
images: []
source_sha1: eb6bd66fe480f8207d6039c89114c4f27a3bf326
---
# Handling Unit Settings

The handling unit settings let you enable and configure the handling unit category that determines the level at which handling units are tracked for the warehouse.

## Configure handling unit settings

1.  Select **Configuration > Inventory > LPN Handling > Handling Unit Settings**.
2.  Enter information in the [Handling Unit Settings fields](#Handling_Unit_Settings_fields).
3.  To add or modify features:
    
    **Note**: The **Transport Equipment** field must be set to Yes in order to define features.
    
    1.  Under **TRANSPORT EQUIPMENT**, select **Features**.
    2.  Perform one of the following tasks:
        -   To add a feature, click **Add**.
        -   To modify a feature, in the grid, select the feature.
    3.  In the **Feature** and **Description** fields, enter the values.
    4.  Click **Apply**.
4.  Click **Save**

## Handling Unit Settings fields

 
| Field | Description |
| --- | --- |
| Inventory | If Yes, the Inventory category is enabled, which means the application supports receiving, tracking, moving, shipping, and transferring serialized and non-serialized inventory handling units that have been defined in the warehouse. Inventory handling units (such as pallets, totes, and carts) can contain inventory, and can be tracked collectively by type or individually by a unique identifier. See [Handling unit categories](../lpn-handling.md).<br > If No, the application does not support the use or tracking of inventory handling units throughout warehouse processes. However, if the **Inventory** field is set to No but the **Picking Container** field is set to Yes, then the application is enabled to track handling units that are used during picking work assignments. |
| Remove Handling Unit When Receiving Unit is Reversed | If the application is configured to allow reverse receiving, then you can reverse the receipt of an empty handling unit. Setting this field determines whether or not the license plate number (LPN) for the handling unit is removed from the application when the receipt of the handling unit is reversed. However, when inventory associated with a handling unit is reversed, and the application is configured to remove the reserved LPN, the associated handling unit is also removed. See [Reverse receiving overview](../../inbound/receiving/reverse-receiving.md).<br > If Yes, when a user performs reverse receiving on an empty handling unit, the application deletes the handling unit from the application. Select Yes if you want to be able to re-receive the handling unit using the same LPN label.<br > If No, when a user performs reverse receiving on an empty handling unit, the handling unit remains in the application. If you select No, the user cannot re-identify the handling unit using the same handling unit LPN label. If the same LPN is scanned again during receiving, a message is displayed to the operator notifying them that the LPN already exists in the application.<br > This field is only available if the **Inventory** field is set to Yes. |
| Track Handling Unit for Sub-LPN | If Yes, then during receiving or inventory identification, the application prompts the user for the handling unit type and, for serialized handling units, the handling unit ID for both the LPN and sub-LPN of inventory; however, the user is not required to enter a sub (child) handling unit. Select Yes if you want the application to track handling units that are received into the facility with sub-LPNs of inventory.<br > If No, then in the same scenario the user is only prompted for the handling unit associated with the LPN of inventory. Select No if you do not want the application to track handling units associated with sub-LPNs of inventory.<br > This field is only available if the **Inventory** field is set to Yes. |
| Transport Equipment | If Yes, the Transport Equipment category is enabled, which means the application tracks transport equipment handling units. Each handling unit that is configured as transport equipment is defined as serialized and tracked as an individual.<br > If No, the application does not track transport equipment handling units and does not prompt for or display handling unit information for transport equipment. |
| Picking Container | If Yes, the Picking Container category is enabled, which means the application tracks serialized and non-serialized handling units during the process of picking work assignments. With this level of tracking enabled, the application only prompts for and tracks handling units that are used during picking work assignments. For example, you may want to track handling units such as trolleys, cages, or totes that are used during picking work assignments to move items within the warehouse, especially if these handling units are pre-labeled with identifiers. Select Yes (and set the **Inventory** field to No) if you want to track handling units during picking work assignments, but not during receiving, shipping, and other inventory movement operations. However, if the **Inventory** field is set to Yes, then all functionality associated with the picking container category is also enabled.<br > If No, the Picking Container category is not enabled, which means the application does not track handling units during picking work assignments unless the Inventory category is enabled (the **Inventory** field is set to Yes). |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
