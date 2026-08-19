---
title: "Over Receiving"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/over_receiving.htm"
source: "/content/over_receiving.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inbound"
  - "Receiving"
  - "Over Receiving"
sections:
  - "Configure over receiving"
  - "Over Receiving fields"
images: []
source_sha1: ca938763baca9c15c9f0b0c8d2fee60bee362644
---
# Over Receiving

Over receiving is the process of receiving more than the expected quantity on an inbound order or inbound shipment line. When you configure over receiving, you specify the following attributes:

-   Whether over receiving is allowed. This is the default setting for the warehouse. It is configured by setting a threshold value that limits over receiving to a specific quantity or cost, or to a percentage of the total expected quantity. A threshold value of zero indicates that over receiving is not allowed.

**Note**: If an item is attribute tracked, such as by lot, and the scanned attribute value does not match the attribute value specified on the order line, then the inventory will not be over-received, but instead is treated as unexpected. If unexpected items are not allowed, then the item cannot be received.

-   Overrides to the default threshold for specific suppliers, items, and clients. During receiving, the application uses the following order of precedence to determine which threshold to apply: item, client, supplier, and warehouse default.
-   Threshold by which the application calculates the maximum over-receipt quantity for catch-enabled items. The threshold can be defined by a specific percentage or amount above the expected catch quantity. A catch quantity is a quantity that is represented in catch unit measurements, which are variable weights or sizes of inventory that may exist within the same material handling (stocking) unit. For example, catch units may be tracked in term of pounds, ounces, or grams.
-   Roles that are allowed to perform over receiving above the defined thresholds. This type of over receiving can only be performed using a workstation, not an RF device. When a user in an authorized role attempts to over receive inventory above the defined threshold, the application displays a message giving the user the option to cancel the over receipt; however, the user can acknowledge the message and continue with the over receipt.
-   Whether an RF operator is notified each time the operator attempts to identify a quantity greater than the expected quantity.

## Configure over receiving

1.  Select **Configuration > Inbound > Receiving > Over Receiving**.
2.  Enter information in the [Over Receiving fields](#Over_receiving_fields).
3.  To define an override limit for a specific client (only available in a 3PL environment):
    1.  Under **OVERRIDE SETTINGS**, click **Clients**:
    2.  In the **Available** column, select the check box next to the client.
    3.  To add a limiting method and value to override the default limiting method and value:
        1.  In the **Selected** column, click **Add Limit**.
        2.  Select the limiting type, and then enter the limiting value.
        3.  Click **Apply**.
    4.  Click **Apply**.
4.  To define an override limit for a specific supplier or item:
    1.  Under **OVERRIDE SETTINGS**, click **Supplier**s or **Item**s.
    2.  Click **Add**.
    3.  Enter the supplier or item, select the limiting type, and then enter the limiting value.
    4.  Click **Apply**.
5.  To define the user roles authorized to over receive inventory above the thresholds:
    1.  Under **OVERRIDE SETTINGS**, click **Roles**.
    2.  In the **Available** column, select the check box next to the roles to use.
    3.  Click **Apply**.
6.  Click **Save**.

## Over Receiving fields

 
| Field | Description |
| --- | --- |
| How to Calculate | Indicates where the application looks for the expected quantities on which to check for over receipt amounts.<br>-   • **Inbound Shipment Line**: Acceptable over receive value cannot be more than what is defined on the inbound shipment line, if one exists.
<br>-   • **Inbound Order Line**: Acceptable over receive value is based on the expected value on the inbound order line.
<br>-   • **Both**: Acceptable over receive value is the lesser of the two (inbound shipment line or inbound order line).
<br > **Note**: You configure when the application checks for over receiving (at identify, at receiving, or both) in Policy Maintenance. |
| Limiting | Default method and value by which the application calculates the default maximum over receiving quantity for a specific item. The field in which you enter a value represents either a monetary amount, percent, or unit quantity, depending on the limiting type that you select.<br>-   • **Cost**: The application calculates the additional items based on the unit cost per item. For example, if the **Limiting** value is $200, and the unit cost for the item is $10, then users can receive an additional quantity of 20 items ($10 x 20=$200). However, if the **Limiting** value is less than the expected cost value, then the user is not allowed to over receive. For example, if the **Limiting** value is $100 and the expected cost value is $500 ($10 unit cost x 50 expected quantity), then users can only receive the expected quantity (50 items). Limiting by cost is not recommended in the value of the items that you receive varies; for example, you receive both high cost and low cost items.
<br>-   • **Percentage**: The application calculates the additional items as a percentage of the total expected quantity and adds the result. For example, if the **Limiting** value is 10% and the expected quantity is 600, then users can receive an additional quantity of 60 (10% x 600).
<br>-   • **Quantity**: The application adds the additional quantity as a straight unit quantity to the expected quantity. For example, if the **Limiting** value is 100 and the expected quantity is 500, then users can receive up to 600 units (100 + 500). |
| Limiting Catch Quantity | Method and value by which the application calculates the maximum over receiving quantity for a catch-enabled item. The field in which you enter a value represents either a percent or catch unit quantity, depending on the limiting type that you select. The catch unit type (measurement unit, such as pounds or grams) and the catch unit weight are configured in the item's master data. See [Items](../../inventory/items/items.md).<br>-   • **Percentage**: The application calculates the additional catch quantity as a percentage of the total expected catch quantity and adds the result. For example, if the **Limiting Catch Quantity** value is 10% and the expected quantity is 100 pounds, then users can receive up to 110 pounds.
<br>-   • **Quantity**: The application adds the additional number of catch-enabled items as a straight unit quantity to the expected quantity. For example, if the **Limiting Catch Quantity** value is 100 and the expected quantity is 500 pounds, then users can receive up to 600 pounds (100 + 500). |
| RF Over Receive Warning | If Yes, each time the operator identifies a quantity greater than the expected quantity, a message is displayed asking the operator to confirm the quantity. Select Yes if you want to require the operator to confirm that a quantity greater than what was expected is correct.<br > If No, the operator is not prompted to confirm quantities received over the expected quantity unless the quantity exceeds the limits that you have defined. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
