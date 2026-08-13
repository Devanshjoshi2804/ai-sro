---
title: "Item Lots"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/item_lots.htm"
source: "/content/item_lots.htm"
toc_path:
  - "Warehouse Management"
  - "Inventory"
  - "Item Lots"
sections:
  - "Add or modify an item lot"
  - "Delete an item lot"
  - "Item Lot fields"
images: []
source_sha1: edeb07dc6ce15e84ce6c37922566bbc084669fe6
---
# Item Lots

A lot is a batch (quantity) of an item uniquely identified by a lot number during the manufacturing process for the purpose of tracking that batch of inventory. An item lot represents an item and lot combination that has been identified into the warehouse or that you expect to receive. Before items can be effectively stored, tracked, and manipulated, every item within the facility must be assigned a unique item number, and its attributes must be defined.

You can add or modify an item and lot combination. You can also view the item and lot combinations that have been pre-defined for expected inventory or are associated with inventory that has been identified into the warehouse. In a 3PL environment, if you have multiple item clients defined for an item, you can create the same item and lot combination for each client.

When lot validation is enabled, the application validates lots that are entered during receiving and inventory identification to determine whether the lot either exists in the warehouse or has been pre-defined as an item lot combination. If the lot does not exist or has not been pre-defined, the user is not allowed to create or identify the inventory. This validation helps control receiving of lot-tracked items.

A lot status defines whether an item lot is restricted or unrestricted. Item lots that are restricted can be used to fulfill outbound orders only if the order type allows shipping restricted products. Item lots that are restricted can be allocated for work orders only if the work order allows restricted lots.

You can define the manufactured date and expiring date for the item lot while adding or modifying the item lot. On enabling the auto calculate manufactured and expiring dates option, the application automatically updates the manufactured date when the expiration date is modified, or updates the expiration date when the manufactured date is modified. This is only applicable if the item is associated with an aging profile. This option is useful if you know the expiration date of the item lot, but you do not know the manufactured date.

## Add or modify an item lot

1.  Select **Inventory > Item Lots**.
2.  Perform one of the following tasks:
    -   To add an item lot, from the **Actions** drop-down list select **Add**.
    -   To modify an item lot, in the grid, select the lot, and then from the **Actions** drop-down list, select **Modify**.
    
    **Note**: When you modify an item, you cannot modify the lot or item value.
    
    -   To copy an item lot, in the grid, select the lot, and from the **Actions** drop-down list, select **Copy**.
3.  Enter information in the [Item Lot fields](#Item_lot_fields).
4.  Click **Save**.

## Delete an item lot

You cannot delete an item lot that is currently associated with inventory in your warehouse.

1.  Select **Inventory** > **Item Lots**.
2.  In the grid, select an item lot, and then from the **Actions** drop-down list, select **Delete**. A confirmation message is displayed.
3.  Click **OK**.

## Item Lot fields

 
| Field | Description |
| --- | --- |
| Lot | Identifier assigned to a quantity of inventory that is uniquely identified during the manufacturing process for the purpose of tracking an attribute of that inventory, such as its expiration date. Lots differentiate distinct groups of inventory that have the same item number. Lots are user defined and are not necessarily unique since the same lot can be applied to different items. However, lot and item combinations must be unique. |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Item Client | Name of the client who stores this item in the facility. This field is only displayed in a 3PL environment. |
| Supplier Lot | Identifier that is an attribute of an item or item and lot combination and is assigned by the item's supplier. A supplier lot is used to uniquely identify and track the inventory to which it is assigned. The supplier lot is a different attribute than the lot, which is a manufacturer or production lot number. In a 3PL environment, if you configured the application to auto populate the supplier lot during inventory identification for a client, this is the supplier lot that is applied to inventory during receiving if an inventory status is not specified on the planned inbound order or ASN. |
| Default Inventory Status | Status of the inventory that defines its quality or disposition. This is the inventory status that is applied to inventory during receiving if an inventory status is not specified on the planned inbound order or advanced shipment notification (ASN). |
| Lot Status | Status of the item lot. A lot status identifies whether inventory from a specific item lot is restricted or unrestricted. This field is only available if you configured the item to have shipping restrictions based on its lot.<br>-   • **Restricted**: Inventory from this item lot is restricted and can only be shipped if the order type is configured to allow shipping of restricted items. Inventory from restricted item lots can only be allocated for work orders that are configured to allow restricted lots. The restricted lot status can be used to indicate, for example, a safety issue within a specific lot (such as with food products) or that the inventory requires testing or validation before it can be shipped to an end customer.
<br>-   • **Unrestricted**: Inventory from this item lot has no restrictions and can be allocated and shipped for any order type or work order.
<br > If an unrestricted item lot is allocated for an order that only allows unrestricted inventory, then the application prevents any further processing of the inventory if the lot status changes. For example, assume that unrestricted inventory has been picked and staged for an unrestricted order type. If the lot status for the staged inventory is changed to restricted, when an operator attempts to load the inventory, an error message is displayed on the operator's device indicating that the inventory is restricted cannot be loaded. |
| Manufactured Date | Date and time that the inventory in this lot was manufactured. Only available if the item is configured to be tracked by manufactured date. If an aging profile is assigned to the item, then if you update the manufactured date, the application updates the expiring date based on the aging profile. The expiring and manufactured dates and times are stored in the database and displayed in the web client in the original captured time zone, not converted to a different time zone, such as a user preferred time zone. |
| Expiring Date | Date and time that the inventory in this lot will expire. Only available if the item is configured to be tracked by expiring date. If an aging profile is assigned to the item, then if you update the expiring date, the application updates the manufactured date based on the aging profile. The expiring and manufactured dates and times are stored in the database and displayed in the web client in the original captured time zone, not converted to a different time zone, such as a user preferred time zone. |
| Auto Calculate Manufactured and Expiring Dates | If Yes, and you have entered either the manufactured or expiring date, then the application automatically calculates the other date based on the item's aging profile. For example, if you enter a value in the **Manufactured Date** field and then set this field to Yes, the application calculates the value in the **Expiring Date** field. To recalculate a date, you must set this field to No, make changes to one of the date fields, and then set this field to Yes again.<br > If No, the application does not automatically calculate the manufactured or expiring date. If you enter a date, set this field to Yes, and then back to No, it has no effect on the date calculation that was processed when the field was previously set to Yes.<br > **Note**: The value of this field is not saved to the database, because its purpose is to initiate a one-time calculation of the item lot dates. The default value for this field is No. If you set it to Yes to calculate dates, then when you save and exit the item lot configuration, the field automatically resets to No. However, the calculated manufactured and expiring dates are saved for the item lot. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
