---
title: "Inventory Adjustment Settings"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/inventory_adjustment_settings.htm"
source: "/content/inventory_adjustment_settings.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inventory"
  - "Inventory Adjustments"
  - "Inventory Adjustment Settings"
sections:
  - "Configure inventory adjustment settings"
  - "Inventory Adjustment Settings fields"
images: []
source_sha1: bf76578da7caae7ef9be72db4cb821cf5892085b
---
# Inventory Adjustment Settings

Inventory adjustment settings determine how inventory adjustments are performed.

## Configure inventory adjustment settings

You can configure inventory adjustment settings for the current warehouse.

You can also select the fields by which adjustment quantities are grouped in transactions that are sent (played) to the host. For example, you can group adjustments by item, by inventory status, or by the user who performed the adjustment.

1.  Select **Configuration > Inventory > Inventory Adjustment Settings**.
2.  Enter information in the [Inventory Adjustment Settings fields](#Inventory_Adjustment_Settings_fields).
3.  To specify the attributes that must be summarized on inventory adjustments:
    1.  Under **PLAYING ADJUSTMENTS TO HOST**, click **Adjustment Attribute Summary**. The Inventory Adjustment Attribute Summaries page is displayed.
    2.  In the **Available** column, select the check box next to the attributes to use.
        
        **Note**: Select only those attributes that you want the application to send to the host as part of the grouped transaction summary. If you do not select any attributes, then all of the attributes are sent to the host by default.
        
    3.  Click **Apply**.
4.  Click **Save**.

## Inventory Adjustment Settings fields

 
| Field | Description |
| --- | --- |
| Reasons | If Yes, the user is required to provide a reason when performing or approving an adjustment.<br > If No, the user does not need to enter a reason when performing or approving an adjustment. |
| Location Error on Preference Violation | If Yes, then when an item is assigned to a location and a different item is added to the location through an inventory adjustment, the application sets the location to Error status. An item is assigned to a location through a location preference rule, which prevents the application from directing other items to the location for putaway.<br > If No, then when an item is added to a location through an inventory adjustment, the application does not consider the location's assigned item when it resets the location's status after an adjustment. If you set this field to No, it is possible for an item other than the assigned item to be added to a location. |
| Play Adjustment To Host | Determines when inventory adjustments are sent (played) to the host.<br>-   • **Send individually**: Adjustments are sent to the host as they are completed.
<br>-   • **Send when complete**: Adjustments are sent to the host in one transaction when they are all completed.
<br > You use the Transactions page in the Inventory module to view adjustment sessions and send them to the host. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
