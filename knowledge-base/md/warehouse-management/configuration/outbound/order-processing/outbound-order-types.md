---
title: "Outbound Order Types"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/outbound_order_types.htm"
source: "/content/outbound_order_types.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Outbound"
  - "Order Processing"
  - "Outbound Order Types"
sections:
  - "Add or modify an outbound order type"
  - "Delete an outbound order type"
images: []
source_sha1: be8de2bf29d8b743bc1ccc52d75cdd499b19f161
---
# Outbound Order Types

An order type is a category used to group orders based on the warehouse processing necessary to fulfill the order. For example, customer orders and distribution orders require different processing, so an order type can be assigned to categorize each order separately.

In the application, order types are used to identify orders for wave (controlled) allocation, to identify orders that are eligible for bulk picking, and to direct orders to specific destinations.

The application provides the following standard order types:

-   **Customer Outbound Orders**: Orders of this type are for a specific customer defined for the warehouse.
-   **Distribution Outbound Order**: Orders of this type require distribution processing. A distribution is a pre-allocation of a warehouse inbound order line to a single store, and it is what connects that inbound order line to an outbound order line.
-   **Vendor (supplier) returns**: Orders of this type are used to return inventory to the vendor that supplied it.

## Add or modify an outbound order type

1.  Select **Configuration > Outbound > Order Processing > Outbound Order Types**.
2.  Perform one of the following tasks:
    -   To add an order type, click **Add**.
    -   To modify an order type, in the grid, click the order type.
    -   To copy an order type, in the grid, select the check box next to the order type, and then click **Copy**.
3.  Enter information in the following fields:
    
     
    | Field | Description |
    | --- | --- |
    | Order Type | Unique name to identify the order type. |
    | Description | Meaningful description that further defines the order type. |
    | Allow Bulk Picking | If Yes, orders that are created using this order type are eligible for bulk picking. A bulk pick is a single pick that satisfies multiple order lines for which the inventory would otherwise have been picked separately. Bulk pick processing allocates matching inventory for multiple order lines together into larger unit of measure (UOM) picks so as to reduce the number of smaller UOM picks required to satisfy the orders.<br > **Note**: If bulk picking is enabled for the order type, the application only attempts to bulk pick orders if the associated customer and client are also enabled for bulk picking.<br > If No, inventory for orders created using this order type are allocated and picking separately. |
    | Allow Shipping of Restricted Products | If Yes, orders that are created using this order type can be fulfilled with inventory from a restricted item lot. The restricted lot status can indicate, for example, a safety issue within a specific lot (such as with food products) or that the inventory requires testing or validation before it can be shipped to an end customer. If an order type is configured to allow the use of restricted inventory, the application first attempts to allocate restricted inventory for orders of that type, and then searches for unrestricted inventory, if needed.<br > If No, orders of this type can only be fulfilled with inventory from an unrestricted item lot. |
    | GS1 Order Type | GS1 order type that corresponds to the Warehouse Management outbound order type. If integrated with Warehouse Management, Connect sends this GS1 order type value in outgoing messages to other systems, and sends the WM inbound order type value in inbound messages. |
    | WM Default | If Yes, then when multiple Warehouse Management order types correspond to the **GS1 Order Type** value, this WM order type is used by default. If integrated with Warehouse Management, Connect sends the GS1 order type value in outgoing messages to other systems, and sends the default WM order type value in inbound messages. |
    
4.  Click **Save**.

## Delete an outbound order type

1.  Select **Configuration > Outbound > Order Processing > Outbound Order Types**.
2.  In the grid, select the check box next to the order type to delete.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
