---
title: "Outbound Order Settings"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/outbound_order_settings.htm"
source: "/content/outbound_order_settings.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Outbound"
  - "Order Processing"
  - "Outbound Order Settings"
sections:
  - "Configure order processing settings"
  - "Order Processing Settings fields"
  - "Restricted Order Mass Update fields"
images: []
source_sha1: 0bd793850d817be06384a899bcf0ed29953b6ace
---
# Outbound Order Settings

You use order processing settings to configure the rules for processing outbound orders in your facility. When you configure order processing, you define the following attributes:

-   Whether an increase in the quantity of an order line that has been allocated (status is In Progress) is also added to the shipment. The application automatically adds a new shipment line to the shipment to support that quantity.
-   Restrictions to mass order line updates. This configuration defines the order processing statuses during which mass order line updates are allowed. The following attributes can be changed when mass order line updates are allowed: inventory rotation method, allocation search path group, footprint, allocation rule name, and whether cross-docking is allowed.
-   Whether users are allowed to change the carrier that is assigned to a shipment
-   Whether a reason code is required when an order line is changed or deleted
-   Whether orders are deleted automatically when a shipment is deleted
-   Order line and shipment line attributes that cannot be modified after a shipment has been allocated

## Configure order processing settings

1.  Select **Configuration > Outbound > Order Processing > Outbound Order Settings**.
2.  Enter information in the [Order Processing Settings fields](#Order_Processing_Settings_fields).
3.  To define the restrictions for updating multiple orders at the same time:
    1.  Click **Mass Update**.
    2.  Enter information in the [Restricted Order Mass Update fields](#Restricted_Order_Mass_Update_fields).
    3.  Click **Save**.
4.  To configure reason codes:
    1.  To require users to select a reason whenever they update or delete an order line, in the **Reason Codes** field, select **Yes**.
    2.  Click **Reason Codes**.
    3.  Perform one of the following tasks:
        -   To add a reason code, click **Add**.
        -   To modify a reason code, in the grid, click the reason.
        -   To copy a reason code, in the grid, select the check box next to the reason code, and then click **Copy**.
    4.  Enter information in the following fields:
        
        | Field | Description |
        | --- | --- |
        | Order Change Code | Code that represents the order change reason. To have the application automatically generate a code, select the **System Generated** check box. |
        | Order Change Reason | Name of the order change reason. This is the value that is available for selection when a user needs to select a reason for an order change or deletion. |
        | Customs Order Type | Type of customs order that is used by a duty management application to calculate duties owed for an order. You associate a customs order type with the reason code that is used to identify an inventory adjustment that adds bonded inventory to the warehouse. A customs order type is used to categorize orders that have the same source site type (customs, customs and excise, or non-bonded), destination site type, and destination country type (United Kingdom, member of European Union, or neither). Only available when customs functionality is enabled. |
        | Customs Planned Inbound Order Type | Planned inbound order type that is on the customs paperwork for the transport equipment. You associate a customs planned inbound order type with the reason code that is used to identify an inventory adjustment that deletes bonded inventory from the warehouse. Only available when customs functionality is enabled.<br>-   • **From EU States**: The planned inbound order originated from another country in the European Union (EU), and the current warehouse is in the EU.
        <br>-   • **From Importation**: The planned inbound order originated from a country outside the EU, and the current warehouse is within the EU.
        <br>-   • **Other Sources**: The planned inbound order originated from a source not identified by other receipt types; for example, from an adjustment or production line.
        <br>-   • **Other UK Warehouses**: The planned inbound order originated from another warehouse in the United Kingdom.
        <br>-   • **Gains in Store**: The planned inbound order is for an adjustment in the quantity of existing inventory. |
        
    5.  To select the clients that use the reason code:
        1.  Click **Clients**.
        2.  In the **Available** column, select the check box next to the clients that use the reason code.
    6.  Click **Apply**.
5.  To define order line modification restrictions:
    
    **Note**: Order line modification restrictions are order line attributes that cannot be modified after a shipment has been allocated.
    
    1.  Click **Order Line Modification Restrictions**.
    2.  In the **Available** column, select the check box next to the order line attributes that cannot be modified after a shipment has been allocated.
    3.  Click **Apply**.
6.  To define shipment modification restrictions:
    
    **Note**: Shipment modification restrictions are shipment attributes that cannot be modified after a shipment has been allocated.
    
    1.  Click **Shipment Modification Restrictions**.
    2.  In the **Available** column, select the check box next to the shipment attributes that cannot be modified after a shipment has been allocated.
    3.  Click **Save**.
7.  Click **Apply**.

## Order Processing Settings fields

 
| Field | Description |
| --- | --- |
| Propagate Order Quantity | If Yes, when the quantity of an order line that has been allocated (status is In Progress) is increased, the additional quantity will be added to the shipment and, if necessary, the application will automatically add a new shipment line to the shipment to support that quantity.<br > If No, the additional quantity is not added to the shipment, so the shipment would need to be manually replanned. |
| Partials to Ship | If Yes, the application allows shipments to be shipped even though they contain shipment lines with a staged quantity of 0 (zero) and the order line is configured to disallow partial shipments.<br > If No, then if the order line is configured to disallow partial shipments, the application does not allow partial shipments to be shipped. |
| Carriers | If Yes, then the carrier can be assigned when the order is built into a shipment, when the shipment is allocated, or when the shipment is prepared for shipping.<br > **Note**: Before a carrier change can happen, the **Change Carrier** field on the order must also be set to Yes.<br > If No, then you must define the carrier on the order line and the carrier cannot be changed. |
| Order Processing | Determines whether an order is deleted when a shipment is deleted.<br>-   • **Delete**: The order is deleted when the shipment is deleted.
<br>-   • **Do not delete**: The order is not deleted when the shipment is deleted.
<br>-   • **Confirm before deleting**: When a shipment is deleted, the application displays a message asking the user if the order should also be deleted. This option allows the user to determine whether the order is deleted along with the shipment. |
| Reason Codes | If Yes, users are required to enter a reason code when an order line that has been saved is changed or deleted. If selected, the user is forced to select a reason code before being allowed to save changes to an existing order. The host application can use the reason to determine how to proceed with processing the order.<br > If No, the user is not required to enter a reason code when an order is changed. |

## Restricted Order Mass Update fields

 
| Field | Description |
| --- | --- |
| Unallocated | Orders with a processing status of Unallocated.<br>-   • **Allowed**: Mass order line updates are allowed for orders with a processing status of Unallocated.
<br>-   • **Restricted**: Mass order line updates are not allowed for orders with a processing status of Unallocated.
<br>-   • **Warning**: Mass order line updates are allowed, after user confirmation, for orders with a processing status of Unallocated. |
| Allocated | Orders with a processing status of Allocated.<br>-   • **Allowed**: Mass order line updates are allowed for orders with a processing status of Allocated.
<br>-   • **Restricted**: Mass order line updates are not allowed for orders with a processing status of Allocated.
<br>-   • **Warning**: Mass order line updates are allowed, after user confirmation, for orders with a processing status of Allocated. |
| Picks Released | Orders with a processing status of Picks Released.<br>-   • **Allowed**: Mass order line updates are allowed for orders with a processing status of Picks Released.
<br>-   • **Restricted**: Mass order line updates are not allowed for orders with a processing status of Picks Released.
<br>-   • **Warning**: Mass order line updates are allowed, after user confirmation, for orders with a processing status of Picks Released. |
| Picking Begun | Orders with a processing status of Picking Begun.<br>-   • **Allowed**: Mass order line updates are allowed for orders with a processing status of Picking Begun.
<br>-   • **Restricted**: Mass order line updates are not allowed for orders with a processing status of Picking Begun.
<br>-   • **Warning**: Mass order line updates are allowed, after user confirmation, for orders with a processing status of Picking Begun. |
| Picking Complete | Orders with a processing status of Picking Complete.<br>-   • **Allowed**: Mass order line updates are allowed for orders with a processing status of Picking Complete.
<br>-   • **Restricted**: Mass order line updates are not allowed for orders with a processing status of Picking Complete.
<br>-   • **Warning**: Mass order line updates are allowed, after user confirmation, for orders with a processing status of Picking Complete. |
| Transport Equipment Loading | Orders with a processing status of Transport Equipment Loading.<br>-   • **Allowed**: Mass order line updates are allowed for orders with a processing status of Transport Equipment Loading.
<br>-   • **Restricted**: Mass order line updates are not allowed for orders with a processing status of Transport Equipment Loading.
<br>-   • **Warning**: Mass order line updates are allowed, after user confirmation, for orders with a processing status of Transport Equipment Loading. |
| Transport Equipment Loaded | Orders with a processing status of Transport Equipment Loaded.<br>-   • **Allowed**: Mass order line updates are allowed for orders with a processing status of Transport Equipment Loaded.
<br>-   • **Restricted**: Mass order line updates are not allowed for orders with a processing status of Transport Equipment Loaded.
<br>-   • **Warning**: Mass order line updates are allowed, after user confirmation, for orders with a processing status of Transport Equipment Loaded. |
| Complete | Orders with a processing status of Complete.<br>-   • **Allowed**: Mass order line updates are allowed for orders with a processing status of Complete.
<br>-   • **Restricted**: Mass order line updates are not allowed for orders with a processing status of Complete.
<br>-   • **Warning**: Mass order line updates are allowed, after user confirmation, for orders with a processing status of Complete. |
| Shipment Cancelled | Orders with a processing status of Shipment Cancelled.<br>-   • **Allowed**: Mass order line updates are allowed for orders with a processing status of Shipment Cancelled.
<br>-   • **Restricted**: Mass order line updates are not allowed for orders with a processing status of Shipment Cancelled.
<br>-   • **Warning**: Mass order line updates are allowed, after user confirmation, for orders with a processing status of Shipment Cancelled. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
