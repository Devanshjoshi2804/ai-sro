---
title: "Parcel concepts"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/parcel_concepts.htm"
source: "/content/parcel_concepts.htm"
toc_path:
  - "Warehouse Management"
  - "Shipping"
  - "Parcel"
  - "Parcel concepts"
sections:
  - "Parcel manifesting service"
  - "Parcel processing task flow"
  - "Problem parcel shipments"
  - "Manifesting"
  - "LTL manifesting"
  - "Manifesting process"
  - "Manifest lists"
  - "Open manifests"
  - "Carrier and service level assignments during manifesting"
  - "Rate shopping for a parcel"
  - "Parcel weight"
  - "Weight and manifest to hold processing"
  - "Weight calculation (no weight scale)"
  - "Parcel manifest statuses"
  - "Warehouse versus non-warehouse parcels"
images: []
source_sha1: 268ecc2fb0bfd577e028995eef0be7103a832289
---
# Parcel concepts

A parcel is a small package that contains inventory and is to be shipped, using a parcel carrier, to a customer. In Warehouse Management, a parcel can be a sub-LPN, case, kit, carton, or non-Warehouse Management package (such as a business office parcel or an employee's personal parcel). A parcel can also be a LPN, if it is a bundled parcel LPN. Each parcel or bundled parcel LPN is assigned a unique carrier-specific tracking number that can be used to track the parcel in the carrier's system or in Warehouse Management. See [Bundling](../../configuration/outbound/shipping/parcel.md).

A parcel shipment consists of one or more parcels. The parcel is the shippable entity, while the parcel shipment is a grouping of parcels that are shipped together to the same destination. Typically, but not always, a parcel shipment only consists of one parcel. Therefore, the terms parcel, small package, and parcel shipment are sometimes used interchangeably.

## Parcel manifesting service

A parcel manifesting service is a parcel application integrated through Parcel Handler that provides parcel manifesting functionality (such as rating, manifesting, carrier compliance, and carrier communication) to Warehouse Management.

**IMPORTANT**: To perform parcel processing, Warehouse Management must be integrated with a parcel application through Parcel Handler. See the _Warehouse Management Parcel Handler Configuration Guide_.

The following table lists the functional responsibilities and interactions of Warehouse Management and the parcel application integrated through Parcel Handler.

  
| Area | Warehouse Management | Parcel application |
| --- | --- | --- |
| Functional responsibilities | Warehouse Management provides the following functionality:<br>-   • Inventory, outbound order, and outbound shipment management
<br>-   • Inventory allocation and picking for orders
<br>-   • Cartonization
<br>-   • Packing
<br>-   • Bundling
<br>-   • Loading and shipping of parcels | The parcel application provides the following functionality:<br>-   •
    
    Up-to-date rating
    
    <br>
<br>-   •
    
    Manifesting
    
    <br>
<br>-   •
    
    Enforcement of compliance with all carrier and service level requirements, such as the following details:
    
    <br>
    -   •
        
        Shipping labels
        
        <br>
    <br>-   •
        
        Package dimensions
        
        <br>
    <br>-   •
        
        Weights
        
        <br>
    <br>-   •
        
        Shipping dates
        
        <br>
    <br>-   •
        
        International shipping requirements and paperwork
        
        <br>
    <br>-   •
        
        Hazardous goods shipping
        
        <br>
    <br>
<br>-   •
    
    Electronic communication with the carrier
    
    <br> |
| Interactions | Sends the following requests to the parcel application:<br>-   • Manifest a parcel
<br>-   • Rate shopping
<br>-   • Close a manifest | Generates the following responses to requests from Warehouse Management:<br>-   • Adds a parcel to a manifest
<br>-   • Calculates shipping costs
<br>-   • Assigns a tracking number
<br>-   • Provides current status of the manifest
<br>-   • Assigns a manifest number |

## Parcel processing task flow

The following tasks are typically performed when manifesting and shipping parcels.

1.  Manually create parcel orders in Warehouse Management or download parcel orders from your host system. You use the Outbound Planner module to create and maintain orders.
    
2.  Manually plan the parcel orders into one or more waves; if you do not manually create a shipment for a parcel order, the application automatically creates a shipment when a wave is allocated. You can also download parcel shipments from your host application. You use the Outbound Planner or Picking module to manually plan orders into waves (or to create shipments).
3.  Allocate and pick inventory for the parcel shipment. You use the Outbound Planner or Picking module to allocate inventory for a wave.
    
    If configured to do so, the application may manifest the associated parcels to hold and print parcel picking and shipping labels at allocation. You can attach the labels to the case or carton as it is being picked, and skip the manual manifesting step later in this task flow. See [Pre-manifesting and manifest to hold](../../configuration/outbound/shipping/parcel.md).
    
    Depending on your configuration, the picked items are deposited at the following locations:
    
    -   A pack station so that the items can be packed into shipping containers
    -   A bundling station so that cartons can be banded or taped together to save on shipping costs
    -   A parcel manifesting station, if manual manifesting is required
    -   Ship staging

See [Bundling](../../configuration/outbound/shipping/parcel.md) and for parcel manifesting, see [Manifesting](#Manifesting).

5.  Monitor the shipment progress. See [View detailed parcel shipment information](procedures-for-parcels.md).
    
    You can also view the following information:
    
    -   Pick work that was created for the shipment and the pick work that still exists for the shipment that has not been confirmed
    -   Inventory that has been picked for the shipment
    -   Current location of any inventory that has been picked for the shipment
    -   Inventory that has arrived in the ship staging lane

See [View parcel packages](procedures-for-parcels.md) and [View detailed manifest information](procedures-for-parcels.md).

7.  If necessary, bundle parcels. You can bundle parcels into a bundled parcel LPN or unbundle parcels from a bundled parcel LPN. See [Bundling](../bundling.md).
8.  If manifesting an international parcel, follow your business rules for acquiring Automated Export System (AES) information. You use the Outbound Planner or Shipping module to enter the AES information after you have acquired it. See [Add or modify a shipment](../../outbound-planner/outbound/procedures-for-shipments.md) or [Manifest a parcel](../manifesting.md).
9.  Perform parcel manifesting tasks.
    1.  If not already done automatically, manually manifest the packages in the parcel shipment.
        
        You use the Manifest page to manually manifest a parcel. You can also search for better shipping rates (rate shopping) while manually manifesting a parcel. See [Manifest a parcel](../manifesting.md).
        
        If the parcel has been pre-manifested, then you do not need to manually manifest the parcel.
        
        When manifesting, you may be prompted to perform workflows. You may be required to complete one or more workflows before the application manifests the parcel.
        
    2.  If necessary, print or reprint shipping and tracking labels for a parcel shipment. See [Print a parcel label](procedures-for-parcels.md).
    3.  If necessary, remove (void) parcels from a manifest that are no longer going to ship as part of the manifest. See [Void a manifested parcel](procedures-for-parcels.md).
    4.  If not configured to be done automatically, release any parcels that were pre-manifested to hold. See [Release a held parcel](procedures-for-parcels.md).
10.  Perform parcel shipping tasks.
     1.  If desired, perform one or more of the following tasks:
         -   Change the carrier for a parcel shipment, if permitted by configuration settings. See [Change the carrier of a parcel shipment](procedures-for-parcels.md).
         -   View notes, if any, about the parcel shipment.
         -   Search for better shipping rates for the parcel shipment (rate shop).
             
     2.  Physically load the parcels on the parcel carrier's transport equipment.
     3.  Close and print the manifest. Closing the manifest list for the carrier notifies the application that all parcels have been loaded onto the transport equipment. See [Close a manifest](procedures-for-parcels.md).
         
         Before closing the manifest, you must resolve any problem shipments. See [Problem parcel shipments](#Problem_parcel_shipments).
         
     4.  If necessary, reprint the carrier paperwork for a closed manifest. See [Print paperwork for a closed manifest](procedures-for-parcels.md).
     5.  If necessary, manually complete the shipments associated with a closed manifest. See [Complete shipments associated with a closed manifest](procedures-for-parcels.md).

## Problem parcel shipments

A problem shipment is a shipment that has not been staged and has non-manifested parcels, outstanding picks, replenishments, cross docks, or held parcels. Manifests with problem shipments cannot be closed. Problem shipments can be resolved manually or automatically during the manifest close process. However, some problem shipments cannot be automatically resolved by Warehouse Management and must be manually resolved by a user. Automatic resolution of a problem shipment means that a user does not need to find, void, and re-manifest the parcel associated with a problem shipment.

See [Resolve a problem parcel shipment](procedures-for-parcels.md).

The following table lists the causes of problem shipments and how to resolve them.

   
| Type | Description | Automatic resolution | Manual resolution |
| --- | --- | --- | --- |
| Not staged | The parcel shipment has not yet been staged. | None. Must be resolved manually. | Stage the shipment. See [Stage a parcel shipment](procedures-for-parcels.md). If the shipment is not ready to stage, then you must complete other tasks first, such as picking the inventory for the shipment, manifesting the parcel for the shipment, and depositing the parcel in the parcel staging location. |
| Non-manifested parcels | One or more of the parcels associated with the shipment have not been manifested. This typically occurs for shipments with multiple parcels. | For multi-parcel shipments, Warehouse Management can only resolve shipments whose carrier permits the parcel numbering information (package X of Y labeling) to be incorrect, and permits the shipment to be shipped out across different days (splitting a multi-parcel shipment). | Manifest the parcels or split the shipment. If the carrier does not support incorrect X of Y parcel numbering, then you also need to reprint the parcel shipping and tracking label. See [Manifest a parcel](../manifesting.md) and [Print a parcel label](procedures-for-parcels.md). |
| Outstanding picks, replenishments, or cross docks | There are outstanding picks, replenishments, or cross docks for the shipment. This typically occurs for shipments with multiple parcels. Some of the parcels have been manifested, but other parcels have outstanding picks, replenishments, or cross docks. | None. Must be resolved manually. | Complete or cancel the picks, replenishments, or cross docks. If you complete the picks, replenishments, or cross docks, you also need to manifest the parcel associated with the picked inventory. If you cancel the picks, replenishments, or cross docks, you also need to split the shipment. See [Manifest a parcel](../manifesting.md). |
| Held parcels | One or more of the parcels associated with the shipment were manifested to hold. This occurs for both single-parcel and multi-parcel shipments. | If resolved automatically, the held parcels are moved to the following day's manifest when it is opened.<br > For multi-parcel shipments with held parcels, Warehouse Management can only resolve shipments whose carrier permits the parcel numbering information (package X of Y labeling) to be incorrect, and permits the shipment to be shipped out across different days (splitting a multi-parcel shipment).<br > **IMPORTANT**: International problem shipments must be resolved manually. | You need to either release the held manifested parcels, or you need to void them and then re-manifest them later. If the carrier does not support incorrect X of Y parcel numbering, then you also need to reprint the parcel shipping or tracking label. See [Release a held parcel](procedures-for-parcels.md), [Void a manifested parcel](procedures-for-parcels.md), and [Print a parcel label](procedures-for-parcels.md). |

## Manifesting

A manifest is a contract between the warehouse and a third-party parcel carrier. The manifest lists all the parcels that are shipped together on the same day and on the same piece of transport equipment by the parcel carrier. The route-to address is used as the destination for the manifest.

Manifesting is the process of assigning a tracking number and rate to a parcel, and assigning the parcel to the current manifest list for the parcel carrier.

For facilities that ship many parcels, manifesting in Warehouse Management is typically configured to be performed automatically (see [Pre-manifesting and manifest to hold](../../configuration/outbound/shipping/parcel.md)). However, for facilities that ship only a few parcels, or to handle exception conditions where a parcel cannot be automatically manifested, you can also manually manifest parcels using the Manifesting page (see [Manifest a parcel](../manifesting.md)) or the RF Parcel Manifest function.

When you manifest a parcel, all of the appropriate parcel information is sent to the parcel application integrated through Parcel Handler. The parcel application verifies that the selections for the parcel (such as service options) are valid based on the carrier and service level, and then either manifests the parcel or returns an error indicating the reason the parcel cannot be manifested.

### LTL manifesting

In addition to manifesting a parcel for a parcel carrier, you can also manifest a full LPN for an LTL (less than truckload) carrier. Similar to parcel manifesting, after the inventory identifier for the LPN is entered or scanned on the Manifesting page, you have the ability to modify dimensions, rate shop, print labels, or void a manifested LPN.

**Note**: You can also manifest a non-LTL package as an LPN if it is a bundled parcel LPN.

## Manifesting process

When you manifest a parcel, the parcel application integrated through Parcel Handler performs the following tasks:

-   Assigns a carrier-specific tracking number to the parcel.
-   Applies a rate or cost to the parcel for shipping it with the selected carrier, using the selected service level.
-   Assigns the parcel to the selected carrier's open manifest. If no open manifest exists for the carrier, a new manifest is automatically created for the current date.
    
    **Notes**:
    
    -   During manifesting, multi-piece held packages are added to the manifest; but a single-piece held package is not added to a manifest until the package is released.
    -   The actual manifest number is created for the carrier when the manifest is closed. Prior to the manifest being closed, the released parcels for a carrier get added to a manifest, which is identified on the Parcel page, **Manifests** tab with a Warehouse Management-generated number. When the manifest is closed, the parcel application updates Warehouse Management with the actual manifest number for the carrier.
    
    The manifest is typically left open so that parcels using the same carrier and service level can be added to it throughout the day. At any given time, multiple manifests can be open, containing multiple parcels, to be shipped with different carriers. If a manifest contains an urgent parcel, you can close the manifest manually so that the carrier knows it is available for pickup.
    

When the manifest is closed (from the Parcel page, **Manifests** tab), the parcels become the responsibility of the carrier to be picked up and delivered.

## Manifest lists

When a parcel is manifested and an open manifest list (manifest) exists for the carrier, the parcel is automatically assigned to the carrier’s manifest. When an open manifest does not exist for the carrier, the parcel application creates, opens, and assigns a unique identifier to the manifest. The parcel is then automatically assigned to the newly opened manifest.

### Open manifests

Only one manifest can be open for each carrier for a given day. If you close a manifest for a carrier, and then on the same day manifest an additional parcel for that carrier, the integrated parcel application opens a new manifest for the carrier for the same day. (You cannot reopen a manifest.) This results in two manifests for the same carrier on the same day, but only one of the manifests is open.

If you do not close a manifest, parcels that are manifested on a different day are not added to the open manifest. Instead, the integrated parcel application opens a new manifest for the carrier on the new day without automatically closing the previous manifest. For example, yesterday you manifested several parcels for carrier A and they were added to carrier A's open manifest. However, you did not close the manifest. Today, the first parcel that you manifest for carrier A results in the parcel application opening a new manifest for carrier A. Today's first parcel is then added to the newly opened manifest. This results in two open manifests for the same carrier, but on different days.

## Carrier and service level assignments during manifesting

The carrier and service level assignments depend on the following parcel information:

-   **First parcel**: When manifesting the first parcel in a shipment, you can change the carrier and service level if permitted to do so by configuration and order line settings.
-   **Additional parcels**: When manifesting additional parcels in a shipment, you cannot change the carrier or service level. All parcels in a shipment must be manifested with the same carrier and service level. If you need to change the carrier or service level after manifesting one or more parcels for a shipment, you must void all of the parcels that have already been manifested for the shipment, and then manifest the parcels again with the updated carrier or service level (if carrier changes are permitted).

## Rate shopping for a parcel

Rate shopping is the process of searching for the lowest cost or shortest lead time for shipping a parcel package, while still meeting the required delivery date.

Once you identify a parcel on the Manifesting page, you can click **Rate Shop** to have Warehouse Management request rates from the parcel application integrated through Parcel Handler. Warehouse Management displays the list of rates based on the selected carrier so that you can compare the cost of shipping the parcel with various carrier service levels.

Depending on the configuration of Parcel Handler, rate shopping can be performed for a selected carrier or across all carriers. Additionally, if the third-party parcel application is Centiro, then rate shopping can be prioritized by either lead time or cost. See [Configure Parcel Handler](../../configuration/outbound/shipping/parcel-handler.md).

Parcel carrier rates are based on the dimensions and weight of the carton, any insurance value applied to the carton, and the destination. Rates can be displayed at any time, but changing the carrier is only allowed when the parcel is the first one being manifested for the shipment and the order is configured to allow carrier changes.

See [Manifest a parcel](../manifesting.md).

**Note**: You cannot change the carrier or service level for a manifested parcel. To make changes to a manifested parcel, you must void the parcel (which removes it from the manifest), and then make the changes while manifesting the parcel again. See [Void a manifested parcel](procedures-for-parcels.md).

## Parcel weight

Warehouse Management can be used in conjunction with an integrated weight scale to provide an accurate weight for parcels. When interfacing with a weight scale, the operator places the parcel on the scale, clicks a button in Warehouse Management during manifesting, and Warehouse Management copies the weight from the scale into the manifest information for that parcel. Contact Blue Yonder for a list of supported weight scales.

### Weight and manifest to hold processing

If the shipping weight of the parcel is estimated when it is manifested to hold, you can update the weight to the actual weight before releasing the parcel. Your Blue Yonder project team can also configure an integrated weight scale to automatically capture the actual weight before releasing the parcel; for example, when the parcel is moved over the weight scale by a conveyor.

### Weight calculation (no weight scale)

If a weight scale is not used, Warehouse Management calculates the weight of the carton from the weight assigned to the parcel's contents footprint configurations.

## Parcel manifest statuses

After being manifested, a parcel passes through several manifesting statuses. You can use the parcel's manifest status to monitor the parcel's current condition. In some cases, a parcel may not have a manifest status. This occurs when the parcel is not manifested, either because it has never been manifested, or it has been removed from a manifest (by voiding the parcel). In both cases, no manifest information, and therefore, no manifest status, exists for the parcel.

The following list describes the parcel manifest statuses:

-   **Released**: The parcel has been manifested and is ready to ship. If a released parcel is removed from a manifest, Warehouse Management deletes the associated manifest information and, consequently, the parcel no longer has a manifest status. When a released parcel's manifest is closed, the parcel's status changes to Closed.
-   **Hold**: The parcel has been manifested, but is not yet ready to ship. This status is the result of manifesting a parcel to hold (automatically or manually). If a held parcel is removed from a manifest, Warehouse Management deletes the associated manifest information and, consequently, the parcel no longer has a manifest status. If a held parcel is released (automatically or manually), then the parcel's status changes to Released. If a held parcel is removed from a manifest during problem shipment resolution (performed by clicking Resolve on the Problem Shipments tab on the Manifests page), then the parcel's status changes to Void.
-   **Void**: The parcel has been voided; or the parcel was automatically removed from a manifest during problem shipment resolution (performed by clicking **Resolve** on the **Problem Shipments** tab while viewing detailed manifest information). Parcels with a void status are not displayed in the application.
-   **Closed**: The parcel is associated with a manifest that has been closed. When the closed parcel is shipped (automatically or manually), the parcel's status changes to Shipped.
-   **Shipped**: The parcel has been loaded onto the parcel carrier's transport equipment and has left the facility. If enabled, transactions have been sent to the host system to indicate that the parcel has been shipped.

## Warehouse versus non-warehouse parcels

You can use the parcel manifesting functionality to manifest and ship the following types of parcels:

-   **Warehouse parcels**: A case, carton, or bundled LPN that has been allocated, picked, and assigned to a parcel carrier.
-   **Non-warehouse parcels**: A package that has arrived at the shipping dock from a source outside of Warehouse Management. No order, shipment, or inventory is attached to a non-warehouse parcel. This kind of parcel is also known as a manual parcel (because you select the **Manual** check box on the Manifest Package Operations window). You can use Manifest Package Operations to manifest non-warehouse parcels. For example, it is not unusual for warehouse facilities to be asked to ship parcels for other departments in the company, or for personal reasons. You can use Warehouse Management to manually identify the carton and manifest it to be shipped with a parcel carrier. When manifesting a non-warehouse parcel, you need the following information:
    -   Dimensions and weight of the parcel
    -   Name and address of the person or organization to which the parcel is to be shipped
    -   Carrier and service level to use for shipping the parcel

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
