---
title: "Shipment Mass Update"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/shipment_mass_update.htm"
source: "/content/shipment_mass_update.htm"
toc_path:
  - "Warehouse Management"
  - "Shared functions"
  - "Shipment Mass Update"
sections:
  - "Perform shipment mass update"
  - "Shipment Mass Update fields"
images: []
source_sha1: 5673f45c726ffe4bbf44359be2bf7dba85cdeebd
---
# Shipment Mass Update

The Shipment Mass Update page is accessible from the following modules: **Outbound Planner**, **Picking**, or **Shipping**.

You use the Shipment Mass Update page to change shipment attributes for multiple shipments at the same time. The Shipment Mass Update page provides you with many options for locating the shipments that you want to change. For example, if you know the carrier that is currently applied to the shipments, you specify the carrier to locate the shipments.

**Note**: No restrictions are applied to shipment mass update, and you can perform shipment mass update before and after allocation.

## Perform shipment mass update

You can query for shipments that you want to change, and then for multiple selected shipments, update the attribute values in one process instead of having to change the attribute for each individual shipment.

**Note**: No restrictions are applied to shipment mass update, and you can perform shipment mass update before and after allocation.

1.  View the Shipment Mass Update page.
    
    1.  Select one of the following modules: **Outbound Planner**, **Picking**, or **Shipping**.
    2.  Select **Shipment Mass Update**.
    
2.  In the filter, enter search criteria to select the shipments to update.
3.  Click **Update Shipments**. The Update Shipments window is displayed.
4.  To manage additional fields that are available for mass update:
    1.  Click **Manage**. The Shipment Update Fields window is displayed.
    2.  To add fields for mass update, in the **Available** column, select the check box next to each field.
    3.  To remove fields from mass update, in the **Available** column, deselect the check box next to each field.
    4.  Click **Save**.
5.  On the Update Shipments window, select the check box next to each attribute you want to update, and then enter information in the applicable [Shipment Mass Update fields](#Shipment_mass_update_fields).
6.  Click **Save**.

After a mass update is processed, you can view the results to determine whether the action was successful. If an updated value is not applicable to one or more shipments, a failure message is displayed. For example, a shipment cannot be updated to Saturday delivery if the shipment has a carrier that does not provide Saturday delivery.

## Shipment Mass Update fields

 
| Field | Description |
| --- | --- |
| Route to Address | Name and address of the distributor or organization to which the shipment is initially sent. The route-to address and ship-to address are the same if the shipment does not require an initial stop. |
| Host Client | Unique name or code that identifies the client's host application. |
| Host External ID | Alternate identifier for the route-to address information. This identifier is typically sent from the host, and it is used to reconcile address information with the information contained in the host application. |
| Carrier | Identifier for a carrier that delivers inbound inventory to the warehouse or outbound shipments to a customer. This is the identifier that will be displayed to users on the application windows and reports. In the application, a carrier can be associated with a customer, order, inbound shipment, outbound shipment, load, and service levels (such as Ground, Next Day, and Saturday Delivery). |
| Service Level | Identifier for the service and transit time provided by the carrier that transports an order or shipment to the customer. For example, for a parcel carrier it may be used to indicate services such as express, second-day air, or standard delivery. |
| Carrier Group | Code that identifies a group of carriers, one of which is expected to transport an order or a shipment to the customer. This is the required carrier group unless the order is configured to allow a carrier to be assigned after the order is created. |
| Document Number | Unique number that identifies the paperwork associated with shipping inventory. Document numbers are applied at the outbound load, stop, or shipment level. |
| Booking Number | Number for the advance reservation or confirmation made in the FedEx booking system for a shipment being tendered to FedEx by a shipper. |
| PRO Number | Progressive routing order (PRO) number assigned to a load, shipment, or stop. A PRO number is assigned as a reference to a shipment for a carrier, and is used by the carrier for most correspondence in relation to tracking the shipment. |
| Freight Code | Code that is used in shipping paperwork to determine who takes financial responsibility for the shipment.<br>-   • **FOB Destination**: Seller takes responsibility for the goods while in transit.
<br>-   • **FOB Source**: Buyer takes responsibility for the goods while in transit. |
| Release Remaining Lines | Used for cross docking purposes.<br > If Yes, then the pick work for the order lines in the shipment that are not marked for cross docking is released as usual.<br > If No, then the pick work created for the order lines in the shipment that are not marked for cross docking is held until the inventory that is marked for cross docking is received and allocated. |
| Wave Set | Optional shipment attribute that identifies a group of shipments that you want to include in a particular wave. A wave is a method of combining orders or shipments into logical sets (such as all shipments that are scheduled to ship tomorrow on a particular carrier) to achieve efficient picking for release and fulfillment. |
| Saturday Delivery | If Yes, then the carrier delivers shipments on Saturday, if required.<br > If No, then the carrier does not deliver on Saturday. |
| Freight Rate | Charge for transporting goods per unit, such as per pound or per package. |
| Freight Charge | Single-character value that indicates the shipment should have a freight charge at the defined freight rate. |
| Early Ship Date | First day of the outbound shipment range. The shipment range identifies a series of dates on which an outbound order line must be shipped. The application uses both delivery and ship dates to consolidate order lines into shipments, depending on the values defined for order consolidation. |
| Early Delivery Date | First day of the delivery range. The delivery range identifies a series of expected delivery dates for the outbound order line. The application uses both delivery and ship dates to consolidate order lines into outbound shipments, depending on the values defined for order consolidation. |
| Late Ship Date | Last day of the outbound shipment range. To define a single shipment date, enter the first day of the shipment range. The application uses both delivery and ship dates to consolidate order lines into shipments, depending on the values defined for order consolidation. |
| Late Delivery Date | Last day of the delivery range. To define a single delivery date, enter the first day of the delivery range. The application uses both delivery and ship dates to consolidate outbound order lines into outbound shipments, depending on the values defined for order consolidation. |
| AES Number | Unique internal transaction number (ITN) that is generated by the Automated Export System (AES) administered by the United States Census Bureau's Foreign Trade division. An ITN is required for shipping non-exempt shipments out of the United States and is obtained by using one of the AESDirect products. If the shipment is exempt, leave this field blank. |
| AES Type | Value that indicates how you have filed or will file the shipment with the Automated Export System (AES).<br>-   • **Pre-shipment**: You filed before the shipment shipped, which requires an AES internal transaction number (ITN) and an acceptance date.
<br>-   • **Post-shipment**: You will file after the shipment is shipped, but before the shipment arrived at customs, which does not require an AES ITN.
<br>-   • **Server down**: You attempted to file, but the AES server was down. |
| AES Accepted Date | Date and time that the international shipment was accepted by the Automated Export System (AES) and an internal transaction number (ITN) was given. A value is only required if the value for **AES Type** is **Pre-Shipment**. |
| FTSR Number | Foreign Trade Statistics Regulations (FTSR) number (an Automated Export System \[AES\] exemption citation). This is the number of the section or provision in the FTSR where the particular exemption is provided (for example, 30.55h). Warehouse Management passes the information to a parcel application (integrated through Parcel Handler), but does not receive the information from the parcel application. Required for shipments out of the United States that are exempt (the AES Number field is blank).<br > A value is only required if the AES Number field is blank. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
