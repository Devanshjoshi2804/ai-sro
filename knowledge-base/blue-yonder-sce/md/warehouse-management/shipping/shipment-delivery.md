---
title: "Shipment Delivery"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/shipment_delivery.htm"
source: "/content/shipment_delivery.htm"
toc_path:
  - "Warehouse Management"
  - "Shipping"
  - "Shipment Delivery"
sections:
  - "Shipment delivery confirmation process"
  - "View and confirm delivered shipments"
  - "Shipment Delivery fields"
  - "Shipment fields"
  - "Order fields"
  - "LPN Delivery fields"
images: []
source_sha1: 3e3b64070a1a1300b29ae89c01ddf8861105cde9
---
# Shipment Delivery

The Shipment Delivery page provides visibility to shipped inventory that has been delivered to customers, and the order line quantities and LPNs reported by the customer as having been received.

You can select to view confirmed or unconfirmed shipments. For each shipment, you can view order details that show the shipped quantity and customer confirmed quantity for each order line, or for LPN-tracked shipments, you can view the delivery date for each LPN on the shipment. This information is provided through an inbound transaction that also supplies, if applicable, the reason for an order line quantity discrepancy or LPN discrepancy, which relates to the LPN disposition rather than the quantity.

**Notes**:

-   For LPN-tracked shipments, the shipment delivery date is set to the most recent LPN delivery date. For example, if a shipment has 2 confirmed LPNs and its delivery date is set to the most recent LPN date, then if a third LPN confirmation is received, the shipment's delivery date is updated to reflect the latest LPN. Additionally, LPN-tracked shipments do not have discrepancy reasons defined at the order line level.
-   For shipments tracked by sub-LPN or detail LPN, if a reason is provided at the LPN level (either by the customer or a warehouse user), the reason is applied to its sub-LPNs and detail LPNs, regardless of whether they are confirmed (have a delivery date specified). Additionally, the parent LPN delivery date is not set until all sub-LPNs or detail LPNs are confirmed as delivered without discrepancies.

When the display shows that order lines or LPNs for a shipment have been delivered (received by the customer site), then you can view the information to determine whether discrepancies exist between what was shipped and what was received. For LPN-tracked shipments, when proof of delivery for an LPN is received, the full LPN quantity is updated on the order line and shipment.

For unconfirmed, non-LPN tracked shipments, you can change the customer confirmed quantity, add or modify the discrepancy reason for an order line, and then confirm the shipment.

For unconfirmed, LPN-tracked shipments, you cannot update order line quantities, but you can add or modify an LPN discrepancy reason, and then confirm the shipment. To confirm an LPN-tracked shipment, each LPN must have either a delivery date (confirming proof of delivery for non discrepant LPNs) or a reason (for discrepant LPNs without a delivery date).

After a shipment has been confirmed, no further changes can be made to the reason on an order line or LPN or to the customer-received quantity for an order line.

## Shipment delivery confirmation process

For non-LPN tracked shipments, the shipment delivery confirmation process compares the shipped quantity against the quantity that a customer reported as received (customer confirmed quantity) for the purpose of determining whether discrepancies exist.

For LPN-tracked shipments, the process confirms the delivery of each LPN on a shipment by ensuring it has a delivery date. LPN quantities are not confirmed, and a discrepancy exists when a full LPN is not received. An LPN is discrepant if it has a delivery date and a reason provided as to the disposition of the received LPN (such as damaged inventory), or if it has no delivery date or reason provided (indicating it was never received).

The following steps describe the shipment delivery confirmation process:

1.  An inbound transaction from the host informs the application of the quantities that the customer received against a shipment and its shipment lines. This transaction updates the original order line with the quantities received and, if applicable, the discrepancy reason provided by the customer. For LPN-tracked shipments, the transaction includes proof of delivery confirmation for the LPNs, sub-LPNs, and detail LPNs on a shipment (depending on the LPN level). When proof of delivery for an LPN is received, the full LPN quantity is updated on the order line and shipment. This process provides visibility to received quantities on the original order line. Discrepancy reasons indicate the reason that a discrepancy occurred; for example, an item was missing, damaged, or incorrect.
    
    **Note**: A list of standard reasons is distributed. Customers must use the reasons that are defined in the application.
    
2.  When the inbound transaction is processed, the following actions take place:
    -   If the shipped quantity matches the customer confirmed quantity for each order line on the shipment, the application automatically completes the delivery confirmation for the shipment. For LPN-level tracking and delivery confirmation, when the receipt of a shipped LPN is confirmed, the LPN ID and delivery date are updated in the application; if all of the LPNs for a shipment are confirmed without discrepancy, the shipment is automatically confirmed.
    -   If there is a discrepancy between the shipped quantity and customer confirmed quantity for any order line, or if an LPN is discrepant (meaning that it is not confirmed as received and has no delivery date) on an LPN-tracked shipment, the following actions take place:
        -   The application does not complete the delivery confirmation. Instead, a user must enter a discrepancy reason (if not already provided by the customer) for each discrepant order line or LPN. For shipments not tracked by LPN, if necessary, the user can adjust the customer confirmed quantity. The user can then process the delivery confirmation. This step is typically concluded after the user investigates and, if necessary, resolves any shipping delivery issues that occurred.
        -   If enabled and configured to occur, the application sends an Event Management alert to notify interested parties that a discrepancy occurred between the shipped quantity and the customer confirmed quantity. For LPN-tracked shipments, an alert is sent whenever an inbound transaction is received for an LPN that includes a reason (indicating a discrepancy exists between the shipped LPNs and customer confirmed LPNs due to the disposition of the inventory). An alert is not sent when a user manually updates or adds a reason to an LPN using the Shipment Delivery page.

## View and confirm delivered shipments

You can view the shipments that have been delivered to customers. For shipments that contain discrepancies (either between the shipped quantity and the customer confirmed quantity for an order line, or between the shipped LPNs and customer confirmed LPNs), you can complete the shipment delivery confirmation.

**Note**: To confirm an LPN-tracked shipment, each LPN must have either a delivery date (confirming proof of delivery for non discrepant LPNs) or a reason (for discrepant LPNs without a delivery date). Additionally, if you are confirming an LPN-tracked shipment, then you cannot update order line quantities; alternatively, if confirming a shipment that is not LPN-tracked, the LPN view is disabled, and you can only update and confirm order line quantities.

1.  Select **Shipping > Shipment Delivery**.
2.  To confirm shipment delivery information without modifying order lines or LPNs:
    1.  In the grid, select the check box next to the shipments to confirm.
    2.  Click **Confirm Shipment**. A confirmation message is displayed.
    3.  Click **OK**.
3.  To view, update, and confirm shipment delivery information:
    1.  Select **Not Confirmed**. See [Shipment Delivery fields](#Shipment_Delivery_fields).
    2.  In the grid, click the shipment. See [Shipment fields](#Shipment_fields).
    3.  Perform one of the following tasks:
        
        **Note**: Changes are not allowed to shipments for which delivery has already been confirmed.
        
        -   To view, update, and confirm delivery of a non-LPN tracked shipment:
            1.  Select **Orders**. See [Order fields](#Order_fields).
            2.  To change the customer confirmed quantity for an order line:
                1.  In the grid, select the check box next to the order line.
                2.  From the **Actions** drop-down list, select **Change Customer Confirmed Quantity**.
                3.  Enter the quantity that the customer received for the order line, and then click **Save**.
            3.  To change the discrepancy reason:
                1.  In the grid, select the check box next to the order line.
                2.  From the **Actions** drop-down list, select **Change Reason**.
                3.  From the drop-down list, select the reason for the discrepancy, and then click **Save**.
        -   To view, update, and confirm delivery of an LPN-tracked shipment:
            1.  Select **LPNs**, and then in the LPN grid, select **Delivery**. See [LPN Delivery fields](#LPN_Delivery_fields).
            2.  To change the discrepancy reason for an LPN:
                1.  In the grid, select the check box next to the LPN.
                    
                    **Note**: For shipments tracked by sub-LPN or detail LPN, you can expand the parent LPN to view delivery information or change the discrepancy reason for each child LPN. If you change the reason at the LPN level, the reason for all sub-LPNs or detail LPNs are also changed, regardless of whether they are confirmed (have a delivery date).
                    
                2.  Click **Change Reason**.
                3.  From the drop-down list, select the reason for the discrepancy, and then click **Save**.
    4.  To confirm the shipment delivery information, click **Confirm Shipment**, and then click **OK**.
4.  To view confirmed shipments, click **Confirmed**. See [Shipment Delivery fields](#Shipment_Delivery_fields).

## Shipment Delivery fields

 
| Field | Description |
| --- | --- |
| Shipment | Unique identifier for an outbound shipment. A shipment is a group of orders or order lines that are allocated together and shipped to the same location. |
| Carrier | Identifier for a carrier that delivers inbound inventory to the warehouse or outbound shipments to a customer. This is the identifier that will be displayed to users on the application windows and reports. In the application, a carrier can be associated with a customer, order, inbound shipment, outbound shipment, load, and service levels (such as Ground, Next Day, and Saturday Delivery). |
| Ship To Address | Address name for the customer to whom the order was shipped. |
| Delivery Date | Date on which the shipment was delivered to the customer. |

## Shipment fields

 
| Field | Description |
| --- | --- |
| Carrier | Identifier for a carrier that delivers inbound inventory to the warehouse or outbound shipments to a customer. This is the identifier that will be displayed to users on the application windows and reports. In the application, a carrier can be associated with a customer, order, inbound shipment, outbound shipment, load, and service levels (such as Ground, Next Day, and Saturday Delivery). |
| Load | Unique identifier for a load. A load is one or more shipments grouped together into one or more stops that are shipped on a single piece of transport equipment. |
| Transport Equipment | Alphanumeric identifier for transport equipment. Transport equipment numbers are not unique, can exist multiple times, and can be associated with various carriers. |
| Delivery Date | Date on which the shipment was delivered to the customer. |
| Driver | Name of the driver who delivered or picked up the transport equipment. |
| Shipment Delivery Confirmed | If Yes, shipment delivery has been confirmed. The application confirms shipment delivery automatically if the customer reports that all inventory for the shipment has been received. If a discrepancy occurs between the shipped quantity and the customer confirmed quantity, then a user must complete the delivery confirmation.<br > If No, shipment delivery has not been confirmed. If a discrepancy occurred between the shipped quantity and the customer confirmed quantity, then a user must manually confirm the shipment. This is typically done after the user has accounted for all inventory on the shipment between the warehouse (shipper) and the customer. |

## Order fields

 
| Field | Description |
| --- | --- |
| Order Line | Unique number that identifies the order line. The number corresponds to the line's position on the order. The first order line is automatically assigned a line number of 0001. Additional order lines are then automatically numbered sequentially, beginning with 0002. |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Shipped Quantity | Quantity of the item on the order line that was shipped to the customer. |
| Customer Confirmed Quantity | Quantity of the item on the order line that the customer received. An inbound transaction from the host supplies the quantity that the customer received against each shipment line. This transaction updates the original order line with the quantities received and, if applicable, the discrepancy reason provided by the customer. |
| Discrepant Quantity | Difference, if any, between the shipped quantity and the customer confirmed quantity for the order line. |
| Reason | Value that represents the reason for the discrepancy between the quantity that was shipped to the customer and the quantity the customer reported as received. For LPN-tracked shipments, this is the reason that a full LPN was not confirmed as received by the customer; or if it was received, the reason can indicate the disposition of the LPN (such as damaged inventory). For example, reasons can include Damaged Part, Incorrect Receipt, Incorrect Pick, and Missing Item. The proof of delivery transaction from the host can include the discrepancy reason provided by the customer if it matches one of the reasons defined in the application.<br > **Note**: A list of standard reasons is distributed. Customers must use the reasons that are defined in the application. |
| User | User who performed the transaction activity. |
| Date Modified | Last date on which the order line information was updated. |

## LPN Delivery fields

 
| Field | Description |
| --- | --- |
| LPN | Unique identifier for inventory. Typically, an LPN refers to a pallet; however, it can refer to inventory received at less than pallet quantity. The LPN is the license plate by which the inventory is tracked in the facility. |
| Delivery Date | Date on which the LPN was delivered to the customer. Delivery dates reflect the time zone used in the web client, which can be either the default system time zone or a user preferred time zone. |
| Reason | Value that represents the reason for the discrepancy between the quantity that was shipped to the customer and the quantity the customer reported as received. For LPN-tracked shipments, this is the reason that a full LPN was not confirmed as received by the customer; or if it was received, the reason can indicate the disposition of the LPN (such as damaged inventory). For example, reasons can include Damaged Part, Incorrect Receipt, Incorrect Pick, and Missing Item. The proof of delivery transaction from the host can include the discrepancy reason provided by the customer if it matches one of the reasons defined in the application.<br > **Note**: A list of standard reasons is distributed. Customers must use the reasons that are defined in the application. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
