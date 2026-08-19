---
title: "Receiving concepts"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/receiving_concepts.htm"
source: "/content/receiving_concepts.htm"
toc_path:
  - "Warehouse Management"
  - "Receiving"
  - "Receiving concepts"
sections:
  - "Advanced shipment notifications"
  - "ASN auto receiving from trusted suppliers"
  - "Auto receiving errors"
  - "Auto receiving setup"
  - "Receive status"
  - "Hot transport equipment"
images: []
source_sha1: 38a163abbbb52299b9e5d28e92610c2fe5b4ee13
---
# Receiving concepts

You use the Receiving module to manage the people, equipment, inventory, and processes that receive inventory into your warehouse. You can make adjustments to inventory, work, inbound shipments, distributions, loads, equipment, and other factors that can improve the productivity and efficiency of warehouse receiving activities.

## Advanced shipment notifications

An advanced shipment notification (ASN) is an Electronic Data Interchange (EDI) document in which the shipper sends notification of a shipment to the recipient electronically before the transport equipment arrives at the facility. The information in the ASN provides general information about the shipment, such as carrier information and the expected time of arrival. It also provides detailed information about the inventory that is being included in the shipment, such as pallet and case license plate numbers (LPNs), item identifiers, footprints, and lot numbers.

If used in your operations, an ASN is typically downloaded from a host system and used by the application to create a planned inbound order and pre-identification inventory details. Inventory received by ASN from a supplier configured as trusted can be stored without having to validate inventory attributes against the ASN, but the LPNs must be scanned to be received. You can also configure ASN auto receiving for trusted suppliers, which immediately receives all of the LPNs on an inbound shipment. See [Trusted suppliers](../configuration/partners/suppliers.md) and [ASN auto receiving from trusted suppliers](#ASN_auto_receiving_from_trusted_suppliers).

Additionally, you can download (and receive from) ASNs from trusted suppliers that contain LPNs with inventory for multiple planned inbound orders. For example, if a trusted supplier performs order consolidation and builds pallets that contain inventory for multiple orders, then when the ASN is downloaded, the application creates the necessary planned inbound orders. An operator can then receive inventory from the ASN against the appropriate planned inbound order. When receiving by ASN from a non-trusted supplier, the operator must verify item information before storing the inventory.

**Note**: The application does not support receiving serialized handling units from an ASN. If handling unit tracking is enabled and a downloaded ASN does not include a handling unit type, then the application uses the default handling unit type associated with the first item to be received from the ASN. If the first item does not have a default type, the operator must enter a handling unit type.  

If your facility tracks items by sub-LPN, the application can be configured to require that operators scan each sub-LPN received against an ASN to process the cases individually. Inventory information is retrieved from the pre-identification inventory details that are created from the ASN. If you do not require that each sub-LPN from a pallet of case-tracked inventory is scanned, then an operator can receive the entire pallet by scanning either a sub-LPN or LPN. See [Configure inbound identification](../configuration/inbound/receiving/inbound-identification.md).

If an ASN that includes distribution information is downloaded, and if cross docking is enabled, the application creates a planned inbound order, as well as the outbound orders and shipments to fulfill the distribution. See [ASN distribution cross docks](../configuration/inbound/cross-docking.md).

## ASN auto receiving from trusted suppliers

Auto receiving is a process in which the application immediately receives all of the LPNs on an inbound shipment and systematically moves them to a receiving staging lane. The physical move of the LPNs can take place before, during, or after auto-receive processing. An inbound shipment is eligible for auto receiving if it is associated with a detailed ASN (with LPN information), and the supplier on every planned inbound order is trusted and enabled for auto receiving. The application displays the **Auto Receive** tag on the shipments that are eligible for auto receiving.

For example, assume an inbound shipment associated with a detailed ASN arrives at the warehouse. When the operator scans the shipment to receive, the application confirms whether all of the inbound orders are from trusted suppliers that are enabled for auto receiving. If so, the operator is prompted with the option to perform auto receiving; when auto-receive processing is done, the operator can complete the inbound shipment. When auto receiving is completed on an RF device, the transport equipment is also closed and dispatched automatically if there are no other inbound shipments on the equipment. When auto receiving is performed on a workstation, such as on the Inbound Shipments page, you can complete the inbound shipment and select from additional transport equipment move options. If any of the suppliers on the inbound shipment are not trusted or not enabled for auto receiving, then the application initiates LPN receiving, which requires the operator to scan each LPN on the inbound shipment.

**Notes**: 

-   You can configure the application to create directed putaway work for auto-received shipments when the transport equipment is closed (**Create Putaway Work During Auto Receiving** field in the Close Inbound Shipment configuration). The **RF Close Auto Create Putaway Work** field has no effect on shipments that are auto-received. If directed work is not created, you must use manual (undirected) putaway to move auto-received inventory from staging to storage.
-   If the **ASN Receiving** field or **ASN Receiving - Items Tracked by Sub-LPN** field is set to Yes in the Inbound Identification configuration, the application overrides the setting during auto receiving. This is because the application immediately receives the entire inbound shipment at once (at the LPN level) without the need to verify any LPN or sub-LPN attributes.
-   The application does not validate item lots during auto receiving.

## Auto receiving errors

When auto receiving is complete, the application displays the number of successfully received LPNs and the number of LPNs that were not received. If an error occurs, you must access the detail view of the shipment (from a workstation) to see the cause of the error and resolve the issue. For example, assume an inbound shipment that meets the requirements for auto receiving arrives at the warehouse with 40 LPNs to receive using an RF device. The following steps describe the process of error handling in this example: 

1.  The operator scans the shipment, selects a staging lane, and confirms to begin auto receiving; the RF device displays a message that auto receiving is in progress.
2.  When auto receiving is complete, the application displays the message, "Auto receiving complete. 35 LPNs received and 5 failed."
3.  At a workstation, access the shipment details (**Receiving > Inbound Shipments**) to view the auto-receive status of Completed with Error.
4.  Click the error status to display a message, such as an item on the LPNs is configured as not receivable.
5.  To resolve this error, you can reconfigure the item as receivable and initiate auto receiving again.
6.  The remaining 5 LPNs are successfully auto received, and the shipment can be put away to storage, cross docked, or distributed.

You can perform auto receiving from the Inbound Shipments page, Staging page, and Door Activity page. See [Auto receive an inbound shipment](inbound-shipments/procedures-for-inbound-shipments.md).

## Auto receiving setup

You must perform the following steps to enable auto receiving of trusted ASNs:

1.  Set the **Auto Receive Trusted ASNs** field to Yes in the identification configurations. See [Configure inbound identification](../configuration/inbound/receiving/inbound-identification.md). 
2.  Set the **Trusted** field and the **Auto Receive Trusted ASNs** field to Yes for a supplier. See [Add or modify a supplier](../configuration/partners/suppliers.md). 
3.  Determine whether putaway work is created by the application (directed) or initiated manually by an operator (undirected) by setting the **Create Putaway Work During Auto Receiving** field. See [Configure close inbound shipments](../configuration/inbound/receiving/close-inbound-shipment.md).

## Receive status

Receive status is an inventory status that identifies the quality level of the inventory received against an inbound order line. A receive status can potentially trigger workflows that have been configured to be performed based on that status. The receive status defined for a planned inbound order line overrides the receive status defined for the supplier, which overrides the receive status defined for the item.

Depending on the receiving identification configuration for the warehouse, users may not be allowed to change the receive status of inventory during the identification process. However, if allowed, and if a user changes the receive status of inventory during identification, the application generates an additional line on the order to show that there is a difference between the expected and actual receive status of the item.

For example, if a quantity of 100 of item TEA is expected with a receive status of Available, and the inventory is identified with a receive status of Quality1, then the order includes the following two lines for the item:

-   TEA with the Available status: shows an expected quantity of 100 and an identified quantity of 0.
-   TEA with the Quality1 status: shows an expected quantity of 0 and an identified and an identified of 100.

## Hot transport equipment

Sometimes there is not enough inventory in the warehouse to fill a shippable outbound order and that order is allocated short. However, if an inbound shipment containing that item is expected to arrive before the outbound order is scheduled to be dispatched, then the inbound shipment is tagged as hot.

Hot transport equipment is any equipment used to transport inventory that can be used to fill a shippable order that was allocated short. The "hot" functionality further enhances cross docking capabilities, and it supports customers who operate in a just-in-time environment. For example, the application can identify which incoming and storage equipment contains inventory for which there are existing orders that have been allocated short. That equipment will be flagged as hot so that you can see which equipment requires a higher priority for processing. You can increase the work queue priority for receiving that item to fulfill the outbound order quicker.

The application determines which transport equipment is hot by comparing the item numbers on expected and storage transport equipment with the item numbers that have been allocated short. The application can be configured to evaluate expected and stored transport equipment for inventory on a regularly scheduled basis. In addition, transport equipment and orders containing hot items are displayed with a Hot tag when you view the activity on the Staging, Door Activity, Appointments, and Inbound Shipments dashboards.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
