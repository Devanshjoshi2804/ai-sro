---
title: "Manifesting"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/manifesting.htm"
source: "/content/manifesting.htm"
toc_path:
  - "Warehouse Management"
  - "Shipping"
  - "Manifesting"
sections:
  - "Manifest a parcel"
  - "Required Manifest fields"
  - "Carrier Manifest fields"
  - "Value Added Services Manifest fields"
  - "Payment Processing Manifest fields"
  - "International Manifest fields"
images: []
source_sha1: a89cc8a7f1ca0205004d8d2e3b508b32fbd0d754
---
# Manifesting

The Manifesting page is accessible from the following module: **Shipping**.

You use this page to manifest a parcel package, which is the process of assigning a tracking number and rate to a parcel, and assigning the parcel to the current manifest list for the carrier. A parcel is a small package that contains inventory and is to be shipped, using a parcel carrier, to a customer. If an open manifest does not exist for the carrier, the integrated instance of Parcel creates, opens, and assigns a unique identifier to the manifest.

When you first access the Manifest page, you must enter an inventory identifier (or in some scenarios, a work reference number) for the parcel you want to manifest. You can then define additional manifesting attributes on the following tabs:

-   Required
-   Carrier
-   Value Added Services
-   Payment Processing
-   International

For more information on the process of manifesting a parcel, see [Parcel concepts](parcel/parcel-concepts.md).

## Manifest a parcel

You can use the following procedure to manually manifest a parcel. For more information, see the [Manifesting](parcel/parcel-concepts.md) parcel concept.

1.  View the Manifesting page.
    
    1.  Select the **Shipping** module.
    2.  Select **Manifesting**.
    
2.  Perform one of the following tasks:
    -   If the parcel has already been manifested at least once, then in the **Tracking** field, enter or scan the tracking number.
    -   If the parcel is a bundled parcel LPN, then in the **Identifier** field, enter or scan the LPN or any one of the sub-LPNs.
    -   If the parcel is a mixed item carton, then in the **Identifier** field, enter or scan the carton number or sub-LPN.
    -   If the parcel is a serialized item, then in the **Identifier** field, enter or scan the serial number.
    -   If the parcel is a case pick, then in the **Identifier** field, enter or scan the sub-LPN.
3.  Press **Tab**. The parcel attributes are displayed.
    
    **Note**: Some fields may not be available for modification while manifesting a parcel, but may be available for modification on the order or shipment.
    
4.  In the **Tracking** field, perform one of the following tasks:
    -   To allow the parcel application to assign a tracking number to the parcel, leave the field blank.
    -   To manually assign a tracking number to the parcel, enter or scan the tracking number (for example, from the parcel carrier's pre-printed tracking label).
    -   To reuse a tracking number (if allowed), and if the correct number is not already displayed, then enter or scan the tracking number.
        
        **Note**: Reusing a tracking number is useful when the original tracking number was not used for some reason (for example, the original parcel could not be shipped as originally manifested and needed to be voided and re-manifested later), and you want to reuse the tracking number so that it is not wasted.
        
5.  To update the package weight for a parcel, perform one of the following tasks on the **Required** tab:
    -   If a scale is integrated, make sure the parcel is on the scale, and then click **Get Weight**.
    -   If a scale is not integrated, in the **Package Weight** field, enter the weight of the parcel.
6.  To change the carrier or service level, perform one or more of the following tasks on the **Required** tab:
    -   To change the carrier, in the **Carrier** field, enter a different carrier. As a result of changing the carrier, different service levels and payment terms may become available for selection.
        
        **Notes**:
        
        -   Changing the carrier is only allowed when the parcel is the first one being manifested for the shipment and the parcel order is configured to allow carrier changes.
        -   Changing the carrier almost always results in a need to also change the service level.
        
    -   To change the service level, from the **Service Level** drop-down list, select the new service level. As a result of changing the service level, different payment terms may become available for selection.
7.  To rate shop for a parcel package:
    
    **Notes**:
    
    -   You can rate shop for a parcel package only if the parcel is not manifested; you cannot rate shop for an entire parcel shipment. If you need to change a manifested parcel, you can void the manifest, and then make the changes while remanifesting the parcel. See [Void a manifested parcel](parcel/procedures-for-parcels.md).
    -   Parcel carrier rates are based on the service level, dimensions, and weight of the parcel, any insurance value applied to the parcel, the destination, and the selected carrier. See [Rate shopping for a parcel](parcel/parcel-concepts.md).
    
    1.  Click **Rate Shop**. The available service level and rates for the selected carrier are displayed.
        
        **Note**: The **Delivery Date** is calculated based on the specified **Ship Date** on the **Required** tab and the service level for the carrier.
        
    2.  Perform one of the following tasks:
        -   To change to a new service level, in the grid, select the row for the service level and rate, and then click **Select**.
        -   To keep the current service level and rate, click **Cancel**.
8.  Perform one or more of the following tasks:
    -   Select **Required** and enter or view information in the [Required Manifest fields](#Required_manifest_fields).
    -   Select **Carrier** and enter or view information the [Carrier Manifest fields](#Carrier_manifest_fields).
    -   Select **Value Added Services** and enter or view information in the [Value Added Services Manifest fields](#Value_Added_Services_manifest_fields).
    -   Select **Payment Processing** and enter or view information in the [Payment Processing Manifest fields](#Payment_Processing_manifest_fields).
    -   If the parcel is an international package, select **International** and enter or view information in the [International Manifest fields](#International_manifest_fields).
9.  To clear the Manifesting page and restart the process, click **Reset**.
10.  To print a parcel label, click **Print Label**. A parcel must be manifested in order to print the parcel label.
11.  To void the package, click **Void**. A parcel must be manifested before it can be voided.
12.  Click **Manifest**.
     
     **Note**: If the parcel is successfully manifested, no confirmation message is displayed.
     
13.  If Warehouse Management has been configured to automatically print the parcel shipping and tracking label at manifest, then pick up the label from the printer and affix it to the manifested parcel.

## Required Manifest fields

 
| Field | Description |
| --- | --- |
| Package Status | Current condition of the package in the parcel manifesting process.<br>-   • **Released**: The package has been manifested and is ready to ship.
<br>-   • **Hold**: The package has been manifested, but is not yet ready to ship. This status is the result of manifesting a parcel to hold (automatically or manually).
<br>-   • **Closed**: The package is associated with a manifest that has been closed.
<br>-   • **Shipped**: The package has been loaded onto the parcel carrier's transport equipment and has left the facility.
<br>-   • **No selection (blank)**: The package is not manifested. |
| Identifier | Unique name or code associated with the parcel to manifest. If a bar code scanner is available for the workstation, you can scan the inventory identifier and it is displayed in this field. You can enter an LPN or LPN UCC for a bundled parcel LPN, sub-LPN, sub-LPN UCC, serial number for a serialized item, carton number for a mixed item carton, or item (when using the Work Reference field). |
| Manifest to Hold Status | If Yes, then the parcel's manifest status is Hold and cannot be shipped. Held parcels can be rated and manifested, but manifests with held parcels cannot be shipped or closed until the held parcels are either released or split from the shipment (if shipment splitting is permitted). Holding parcels is especially useful when you are pre-manifesting parcel shipments to hold so that you can print the manifest label at allocation to apply to inventory during picking.<br > If No, indicates that the parcel's manifest status is Released and can be shipped. |
| Work Reference | Unique identifier for a piece of work. A value in this field is useful as search criteria for finding parcels with inventory that has been allocated, but not yet picked. Only available if scanning by work reference is enabled and if the package is a warehouse parcel (not a manual parcel). |
| Ship Date | Date on which the manifest was or will be shipped. |
| Package Weight | Weight of the parcel. If a value is displayed, it can represent the weight of the parcel based on the gross weight defined for the parcel's item; and for a mixed item carton, this weight can include the weight of the carton. If a weight scale is integrated with Warehouse Management, the value can represent the weight from the scale. Alternatively, the value can represent the value for the minimum weight configuration defined for the workstation or the facility. |
| Carrier | Code that identifies the carrier that is expected to deliver the parcel to a customer. This carrier identifier is used for internal processing. If carrier changes are permitted, you can change the carrier for the first parcel to be manifested for a shipment. |
| Service Level | Identifier for the service and transit time provided by the carrier that transports an order or shipment to the customer. For example, for a parcel carrier it may be used to indicate services such as express, second-day air, or standard delivery. |
| Carton Name | Value that represents the parcel's carton. A carton is a corrugated box or container of any size that serves as packaging for inventory. For warehouse parcels, a carton code is displayed if the parcel represents a mixed item carton. When a carton code is selected, the dimensions defined for the carton are displayed in the Length, Height, and Width fields. |
| Package Code | Carrier-specific standard packaging material, such as a carrier's rolled up document tube, as defined for the carrier and service level in the integrated Parcel instance. Parcel uses this code to recognize that the inventory is being shipped in the carrier's special packaging thus providing the proper shipping rate (often discounted). |
| Length | Length of the parcel. If you have a value in the Carton Name field, then the length of the carton (as defined in the carton configurations) is displayed; otherwise, for warehouse parcels, the length of the case (as defined for the item footprint) is displayed. |
| Width | Width of the parcel. If you have a value in the **Carton Name** field, then the width of the carton (as defined in the carton configurations) is displayed; otherwise, for warehouse parcels, the width of the case (as defined for the item footprint) is displayed. |
| Height | Height of the parcel. If you have a value in the **Carton Name** field, then the height of the carton (as defined in the carton configurations) is displayed; otherwise, for warehouse parcels, the height of the case (as defined for the item footprint) is displayed. |
| Ship-To Customer | Customer to whom the parcel is to be shipped. |
| Ship-To Address | Address to which the parcel is to be shipped. |

## Carrier Manifest fields

 
| Field | Description |
| --- | --- |
| Freight Class | Standardized code, ranging from 50 to 500, that classifies the kind of freight being carried. Freight class is used as the product basis in the over-the-road industry. (STCC is the other basis and is used by the rail industry.) The higher the freight class, the more carriers charge to transport it. Factors such as value, density, and hazardous nature influence the freight class. |
| Booking Number | Number for the advance reservation or confirmation made in the FedEx booking system for a shipment being tendered to FedEx by a shipper. |

## Value Added Services Manifest fields

 
| Field | Description |
| --- | --- |
| Service Options | Value-added services that can be assigned to the parcel such as Collect on Delivery or Hold for Pickup. Depending on the selected options, additional parameters may be displayed for which values can be defined (for a non-warehouse parcel). For example, a collect on delivery (COD) service option may have parameters for the COD amount and COD payment terms. Parameters are retrieved from the integrated Parcel instance along with the service options to which the parameters apply. |
| Service Type | For international shipments, defines the type of service that is used by the carrier.<br>-   • **Airport to Airport**: The facility drops off the package at the airport. Then, the carrier transports the package to the airport in the destination country. Finally, the customer (or broker) picks up the package at the destination airport.
<br>-   • **Airport to Door**: The facility drops off the package at the airport where the carrier takes over and transports the package to the actual ship-to address in the destination country.
<br>-   • **Door to Airport**: The carrier picks up the package from the facility and then transports the package to the airport in the destination country. Then, the customer (or broker) picks up the package at the destination airport.
<br>-   • **Door to Door**: The carrier picks up the package from the facility and then transports the package to the actual ship-to address in the destination country. |
| Package Value | Monetary value of the parcel. A value is only needed when the parcel requires insurance coverage in addition to the parcel carrier's automatic insurance coverage, which typically covers parcels valued at less than 100 U.S. dollars. Shipping rates are adjusted to reflect the added insurance coverage. |
| Dry Ice Weight | Weight of the dry ice that is packed in the parcel. If the parcel does not contain dry ice as packaging material, leave this field blank. |

## Payment Processing Manifest fields

 
| Field | Description |
| --- | --- |
| Payment Terms | Method (such as pre-paid or third party) by which delivery charges are to be paid. Valid values are either the carrier-specific payment terms retrieved from the integrated Parcel instance, or the generic payment terms defined in the Parcel integration configurations. For a warehouse parcel, payment terms are displayed if they were defined for the order line. |
| Account Number | Unique number that identifies the account that the consignee has established with the carrier. This is the account number that the carrier bills for the parcel's delivery charges. For a warehouse parcel, Warehouse Management displays the account number defined for the bill-to customer and carrier. |
| COD Payment Terms | Method (such as currency, check, or money order) by which collect on delivery (COD) payments must be made. Valid values are user-defined. |
| COD Indicator Type | Value that indicates the type of collect on delivery (COD), if any, that will be required for the order.<br>-   • **Electronic**: COD is collected using an electronic form of payment.
<br>-   • **None**: The carrier does not require that you specify the type of COD.
<br>-   • **Regular**: COD is collected as a check or cash. |
| Signature Required | If Yes, then you require the shipper to obtain a signature at delivery.<br > If No, then you do not want a recipient to sign for the package, and you are releasing the shipper from obtaining a signature (shipper release). |
| Bill Freight | If Yes, then the freight costs for a collect on delivery (COD) shipment are paid by the recipient. The freight charges are added to the COD amount.<br > If No, then the freight charges are not paid by the recipient; the shipper pays. |
| Bill Consignee | If Yes, then the delivery charges for the shipment are billed to the consignee.<br > If No, then the consignee is not billed for delivery charges. |

## International Manifest fields

 
| Field | Description |
| --- | --- |
| Broker Address | Address for the broker to which the parcel is to be shipped. A broker is a person or entity that buys and sells goods for other persons or entities. |
| AES Number | Unique internal transaction number (ITN) that is generated by the Automated Export System (AES) administered by the United States Census Bureau's Foreign Trade division. An ITN is required for shipping non-exempt shipments out of the United States and is obtained by using one of the AESDirect products. If the shipment is exempt, leave this field blank. |
| AES Type | Value that indicates how you have filed or will file the shipment with the Automated Export System (AES).<br>-   • **Pre-shipment**: You filed before the shipment shipped, which requires an AES internal transaction number (ITN) and an acceptance date.
<br>-   • **Post-shipment**: You will file after the shipment is shipped, but before the shipment arrived at customs, which does not require an AES ITN.
<br>-   • **Server down**: You attempted to file, but the AES server was down. |
| AES Accepted Date | Date and time that the international shipment was accepted by the Automated Export System (AES) and an internal transaction number (ITN) was given. A value is only required if the value for **AES Type** is **Pre-Shipment**. |
| Customs Clearance | For international shipments, if Yes, indicates that parcels will be sent directly to customs for clearance.<br > If No, then customs clearance is not required. |
| FTSR Number | Foreign Trade Statistics Regulations (FTSR) number (an Automated Export System \[AES\] exemption citation). This is the number of the section or provision in the FTSR where the particular exemption is provided (for example, 30.55h). Warehouse Management passes the information to a parcel application (integrated through Parcel Handler), but does not receive the information from the parcel application. Required for shipments out of the United States that are exempt (the AES Number field is blank).<br > A value is only required if the AES Number field is blank. |
| Export Type | Value that a parcel carrier has defined for itself to be used for international shipment documentation and manifesting international packages. The valid values are provided by the integrated Parcel instance. If you need to change the export type after manifesting a parcel for a shipment, you must void the parcels associated with the shipment, change the export type, and then re-manifest the shipment's parcels with the new export type. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
