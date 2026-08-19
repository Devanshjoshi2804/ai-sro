---
title: "Carrier Cross Reference"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/carrier_cross_references.htm"
source: "/content/carrier_cross_references.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Partners"
  - "Carriers"
  - "Carrier Cross Reference"
sections:
  - "Add or modify a carrier cross reference"
  - "Carrier Cross Reference fields"
images: []
source_sha1: ebc761952d647791f568fd51a60a77cd7779d6bc
---
# Carrier Cross Reference

A cross reference is a configuration that associates (maps) a carrier and service level defined in Warehouse Management with a carrier and service level defined in an external system (such as a parcel application integrated through Parcel Handler, a third-party shipping application, or GS1).

**Note**: GS1 has standard required identifiers for all carrier service levels. When Warehouse Management is integrated with a system that utilizes GS1 messaging, the Warehouse Management service levels need to be mapped to the standard GS1 service levels. This mapping allows the Integrator transaction to determine what Warehouse Management service level to assign to any inbound shipment.

To define the association, you select a carrier and service level defined in Warehouse Management. Then you enter the values that are used to represent the same carrier and service level in the external system.

Cross references are required to support communication between Warehouse Management and the external system with regard to carriers and service levels.

**IMPORTANT**: When Warehouse Management is integrated with a parcel application through Parcel Handler, you must configure a cross reference for each of the carriers that you want to use for parcel shipping. The cross referenced carriers should match the carriers defined and enabled in the PARCEL-HANDLER/SERVICE-CONDITIONS/CARRIERLIST policy.

## Add or modify a carrier cross reference

1.  Select **Configuration > Partners > Carriers > Carrier Cross Reference**.
2.  Perform one of the following tasks:
    -   To add a cross reference, click **Add**.
    -   To modify a cross reference, in the grid, click the external system cross reference.
3.  Enter information in the [Carrier Cross Reference fields](#Carrier_Cross_Reference_fields).
4.  Click **Save**.

## Carrier Cross Reference fields

 
| Field | Description |
| --- | --- |
| Carrier | Identifier for a carrier (defined in Warehouse Management) that delivers inbound inventory to the warehouse or outbound shipments to a customer. In the application, a carrier can be associated with a customer, order, inbound shipment, outbound shipment, load, and service levels (such as Ground, Next Day, and Saturday Delivery). |
| Service Level | Identifier for the service and transit time (defined in Warehouse Management) provided by the carrier that transports an order or shipment to the customer. For example, for a parcel carrier it may be used to indicate services such as express, second-day air, or standard delivery. |
| External System Name | Name of the external system (application) that contains carriers and service levels that need to be associated with the Warehouse Management carrier and service levels.<br>-   • If the external system is set to **Parcel** which represents a parcel application (integrated through Parcel Handler), then the cross references for carrier and service level are defined in the **Parcel Manifest Service** field.
<br>-   • If the external system is not set to **Parcel**, then the cross references for carrier and service level are defined in the **External System Carrier** and **External System Service Level** fields, respectively.
<br > **Note**: The external system name can be GS1, with the external system carrier and service levels mapped to the respective standard GS1 carrier and service levels. |
| Parcel Manifest Service | Carrier code and service level. You must enter the value provided by the parcel vendor. The carrier and service level are separated by a pipe character; for example, std.ups.com|STD. This field is only available when the **External System Name** field is set to Parcel. |
| External System Carrier | Name of the carrier defined in the external (third-party) application. The value of this field must match the carrier name that is defined in the external application. This field is only available when the **External System Name** field is set to an external application other than Parcel. |
| External System Service Level | Name of the carrier service level defined in the external (third-party) application. The value of this field must match the service level name that is defined in the external application. This field is only available when the **External System Name** field is set to an external application other than Parcel. |
| Service Title | Name for the service level that you want to be printed on labels. For example, if the carrier service level is an abbreviation (such as GR), you can choose to have the entire word (such as GROUND) printed on the labels. |
| External System Prints Labels | If Yes, then shipping labels are printed by the external system specified in the **External System Name** field.<br > If No, then Warehouse Management prints the required shipping labels. If the **External System Name** field is set to **Parcel** and represents a parcel application (integrated through Parcel Handler), then set this field to No to indicate that Warehouse Management prints the labels. |
| COD Address | Name of the collect on delivery (COD) address. This is the address to which the external system sends payments collected from COD deliveries. An address name represents the location and contact information of an entity (such as a carrier, client, customer, or supplier). The information fields support the entry of an address name, first and last name, address lines, a city, a state or province, a postal code, and a country. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
