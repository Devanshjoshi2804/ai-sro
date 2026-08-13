---
title: "Order Consolidation"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/order_consolidation.htm"
source: "/content/order_consolidation.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Outbound"
  - "Order Processing"
  - "Order Consolidation"
sections:
  - "Order consolidation rules"
  - "Configure order consolidation"
  - "Order Consolidation fields"
images: []
source_sha1: a17e9b1324598956ef4c1583be235bb73c132b6b
---
# Order Consolidation

Order consolidation is the process of combining outbound order lines into shipments. This can be done automatically by the application or manually by the shipment planner. You can configure how the application consolidates order lines.

Consolidating orders can reduce the number of shipments needed to complete an order. In addition, when new orders continuously enter the application, there may be opportunities to combine them with existing, unallocated shipments so they can be delivered as a single parcel. You can consolidate orders during shipment planning and wave planning.

## Order consolidation rules

If you configure the application to add new shipment lines to existing unallocated shipments, then during order consolidation the application executes the selected consolidation rules. The consolidation rules are used to determine whether the new shipment line can be added to an existing shipment by matching criteria such as route-to address, carrier, or delivery date.

By default, a list of standard order consolidation rules are provided in a recommended sequence. However, you can change the selection and the sequence in which the rules are executed.

During order consolidation processing, when the application executes the rules, each command takes the results of the previous commands and filters out the shipments in the list that do not match that consolidation rule. For best results, the commands should be listed in a sequence that causes the initial rules to filter out as many shipments as possible. This will limit the list of shipments that the subsequent rules are required to validate and will improve performance.

The following table shows the default configuration of the consolidation rules.

 
| Default sequence | Consolidation rule |
| --- | --- |
| 1 | By route to address |
| 2 | By destination area |
| 3 | By carrier code |
| 4 | By carrier service level |
| 5 | By delivery date |
| 6 | By ship date |
| 7 | By wave flag |
| 8 | By export type |
| 9 | By payment terms |
| 10 | By weight |
| 11 | By ship by (create shipment by date) |
| 12 | By ship to address |

## Configure order consolidation

1.  Select **Configuration > Outbound > Order Processing > Order Consolidation**.
2.  Enter information in the [Order Consolidation fields](#Order_Consolidation_fields).
3.  To select and sequence the rules used to determine which new order lines can be consolidated into existing, unallocated shipments:
    
    **Note**: The **Consolidation Rules** field is only available if the **Allow Consolidation with Existing Shipments** field is set to **Yes**.
    
    1.  Under **CONSOLIDATION SETTINGS**, select **Consolidation Rules**.
        
        **Note**: The default rules are immediately cleared once you select a new rule.
        
    2.  In the **Available** column, select the check box next to the rules to use.
    3.  To reorder the list, in the **Selected Rules** column, select the rule to move, and then drag it to the new location in the list. The list sequence number determines the order in which the application evaluates the consolidation rules.
    4.  Click **Apply**.
4.  Click **Save**.

## Order Consolidation fields

 
| Field | Description |
| --- | --- |
| Order Consolidation | Minimum amount of time that the delivery dates on separate order lines must overlap to be considered for consolidation. Valid time units: d=days; h=hours; m=minutes; s=seconds. Example: 10h means 10 hours. If no time unit is entered, the field defaults to minutes (m).<br > For example, if the window is set to four hours (4h), consider the following three order lines:<br>-   • Order Line 1 - Early Date of 01/01/2014 6:00 A.M., Late Date of 01/01/2014 4:00 P.M.
<br>-   • Order Line 2 - Early Date of 01/01/2014 8:00 A.M., Late Date of 01/01/2014 2:00 P.M.
<br>-   • Order Line 3 - Early Date of 01/01/2014 9:00 A.M., Late Date of 01/01/2014 1:00 P.M.
<br > The overlap between all 3 lines is 4 hours, determined by the latest Early Date and earliest Late Date (9:00 A.M. to 1:00 P.M.). So, if the window is set to 4 hours, all 3 lines could be consolidated together.<br > If the window is set for 6 hours (6h), Line 1 and Line 2 could be consolidated together because they overlap by 6 hours (8:00 A.M. to 2:00 P.M.); however, Line 3 would be left out because the overlap is less than 6 hours between Line 1 and between Line 2. |
| Difference in Shipment Weight | Amount of weight that is used during consolidation to determine whether the application will split an order line or add it to a new shipment. If adding the order line will cause the shipment to exceed its maximum shipment weight, then the weight of the order line is compared to the value defined in the **Difference in Shipment Weight** field.<br > If the weight of the order line is greater than the difference in shipment weight, then the order line is large enough to split. If it is less than the difference in shipment weight, then rather than splitting the order line, the whole order line is added to a new shipment. If the line is split, the package quantity is pro-rated by the available order line weight, and rounded down to accommodate the standard case and split attributes defined for the order line.<br > For example, if the value defined in the **Difference in Shipment Weight** field is 500 lbs, and if adding an order line that weighs 600 lbs would cause the maximum shipment weight to be exceeded, then the order line is split. If adding an order line that weighs 400 lbs would cause the maximum shipment weight to be exceeded, then the order line is added to a new shipment.<br > To change a measurement unit, click the unit next to the field, and select a different unit. |
| Maximum Shipment Weight | Maximum weight allowed for a consolidated shipment. This value is calculated using the gross case weight that is defined for the item footprint. If an order line, added to a shipment, would cause it to exceed the maximum shipment weight, then depending on the difference in shipment weight, the order line is either added to the shipment and the excess split into a new shipment; or the entire order line is added to a new shipment.<br > To change a measurement unit, click the unit next to the field, and select a different unit. |
| Allow Consolidation with Existing Shipments | If Yes, the application attempts to consolidate new shipment lines into existing unallocated shipments (in the Ready status) during shipment planning. If you set this field to Yes, the application executes the consolidation rules to determine the best existing shipment to which each additional shipment line can be added. When this field is set to Yes, the **Consolidation Rules** field becomes available, allowing you to select and sequence the consolidation rules used to determine the best existing shipment to which to add the new shipment line.<br > If No, the application does not attempt to add new shipment lines to existing shipments. |
| Show Shipment Summary | Not currently used. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
