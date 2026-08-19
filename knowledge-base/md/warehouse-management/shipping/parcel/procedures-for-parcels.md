---
title: "Procedures for parcels"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/procedures_for_parcels.htm"
source: "/content/procedures_for_parcels.htm"
toc_path:
  - "Warehouse Management"
  - "Shipping"
  - "Parcel"
  - "Procedures for parcels"
sections:
  - "Release a held parcel"
  - "Void a manifested parcel"
  - "Print a parcel label"
  - "Close a manifest"
  - "Complete shipments associated with a closed manifest"
  - "Print paperwork for a closed manifest"
  - "Resolve a problem parcel shipment"
  - "Change the carrier of a parcel shipment"
  - "Stage a parcel shipment"
  - "View detailed parcel shipment information"
  - "View parcel packages"
  - "View detailed manifest information"
  - "Manifest detail fields"
  - "Parcel Package fields"
  - "Parcel Shipment detail fields"
images: []
source_sha1: ebdaea59f7f9cc711796763bd8017f568162052c
---
# Procedures for parcels

You can perform the following procedures on parcels.

## Release a held parcel

Releasing a held parcel changes its status from Hold to Released to indicate that the parcel can be shipped. When you release a held parcel, Warehouse Management also writes a daily transaction record with the activity "Release Package".

1.  [View parcel packages](#View_parcel_packages).
2.  In the grid, select the check box next to the held parcels to release.
3.  From the **Actions** drop-down list, select **Release Package**. A confirmation message is displayed.
4.  Click **Yes**.
    
    **Note**: If the application cannot release the parcel, the Release Failure window is displayed and shows the reason for the failure.
    
5.  Click **OK**.

## Void a manifested parcel

There may be situations where you need to remove a parcel from a manifest. For example, you discover that another carrier offers a better rate, or that the customer wants to receive the parcel sooner. Voiding a manifested parcel removes it from the currently open shipping manifest for the selected parcel carrier. Voiding also writes a daily transaction record with activity "Void Manifested Package".

You can void a parcel prior to closing the manifest, and if changing the carrier is allowed for the facility and the order line. After voiding a parcel, you can manifest it again. See [Manifest a parcel](../manifesting.md).

1.  [View parcel packages](#View_parcel_packages).
    
    **Note**: You cannot void a parcel associated with a closed (shipped) manifest.
    
2.  In the grid, select the check box next to the manifested parcels to void.
3.  From the **Actions** drop-down list, select **Void Package**. A confirmation message is displayed.
4.  Click **Yes**.
    
    **Note**: If the application cannot cannot void the parcel, the Void Failure window is displayed and shows the reason for the failure.
    

## Print a parcel label

When you print a parcel label, Warehouse Management prints the correct number of labels with the correct formatting for the parcel's carrier and service level.

1.  [View parcel packages](#View_parcel_packages).
2.  In the grid, select the check box next to the parcel for which to print a label.
3.  From the **Actions** drop-down list, select **Print Label**. A confirmation message is displayed.
    
    **Note**: The Actions drop-down list is only displayed for parcels that have not shipped.
    
4.  Click **Yes**.
    
    **Note**: If the application cannot print the parcel label, the Print Failure window is displayed and shows the reason for the failure.
    
5.  Click **OK**.

## Close a manifest

You can close a manifest in any of the following scenarios:

-   The parcel carrier's transport equipment is ready to depart and all manifested parcels are loaded. This is so that the manifest can be communicated to the carrier by the integrated parcel manifesting service (such as a parcel application integrated through Parcel Handler). Transmitting the manifest information gives a carrier advanced notice of the parcels that will be arriving at the sorting facility.
-   The shipment is loaded and parcel carrier's transport equipment has departed. However, the manifest must be closed on the same day the shipment is dispatched. This ensures that the manifest has same number of packages as loaded in the transport equipment.
-   The shipment status is either Staged, Loading, Loaded, or Load Complete.

If shipment processing is not deferred and the host transaction is configured, closing the manifest also notifies the host system that the inventory was shipped.

**Note**: Once a manifest is closed, it cannot be reopened.

1.  Select **Shipping > Parcel > Manifests > Open**.
2.  In the grid, select the check box next to the manifest, or click the manifest.
3.  Click **Close Manifest**. A confirmation message is displayed.
4.  Click **Yes**.
    
    **Note**: If the application cannot close the manifest, the Close Failure window is displayed and shows the reason for the failure.
    
5.  Click **OK**.

## Complete shipments associated with a closed manifest

Typically, parcel shipping is deferred and processed automatically at a later time (instead of during the closing of a manifest). However, you may want to complete the shipments in a closed manifest before the automatic processing occurs to indicate that the parcels have shipped. This is especially useful when you need to send the shipped transactions to the host system before the automatic processing occurs.

When you manually complete shipments in a closed manifest, the application automatically performs the following processing actions:

-   Updates the parcel's manifest status to Shipped
-   Creates all of the necessary shipping structures, such as loads and stops
-   Loads the stops
-   Closes and dispatches the transport equipment
-   Sends transactions, if configured to do so, to the host system to indicate that the parcel has been shipped

1.  Select **Shipping > Parcel > Manifests > Closed**.
2.  In the grid, select the check box next to the manifest, or click the manifest.
3.  From the **Actions** drop-down menu, select **Complete Shipments**. A confirmation message is displayed.
4.  Click **OK**.

## Print paperwork for a closed manifest

1.  Select **Shipping > Parcel > Manifests > Closed**.
2.  In the grid, select the check box next to the manifest, or click the manifest.
3.  From the **Actions** drop-down menu, select **Print Paperwork**. A confirmation message is displayed.
4.  Click **OK**.

## Resolve a problem parcel shipment

You can use this procedure to automatically resolve a problem parcel shipment, meaning that a user does not need to find, void, and re-manifest the parcel associated with a problem shipment. However, some problem shipments cannot be automatically resolved by the application and must be manually resolved by a user.

See [Problem parcel shipments](parcel-concepts.md).

1.  Select **Shipping > Parcel > Manifests > Open**.
2.  In the grid, click the manifest containing problem shipments. The manifest details are displayed.
3.  Select **Problem Shipments**.
4.  In the grid, select the check box next to the shipment to resolve, and then click **Resolve**. Any held packages are automatically removed from the manifest and re-manifested on the carrier's next manifest.

## Change the carrier of a parcel shipment

You can change the carrier and service level for a parcel shipment before the first parcel is manifested. Carrier change is only allowed if all of the orders associated with the shipment have the **Change Carrier** field set to Yes and the **Carriers** field in the outbound order settings is set to Yes.

Changing the carrier and service level is useful, for example, if the original carrier arrives late at the facility or is unable to transport the shipment; or if the carrier is not the most cost-effective choice (at the original service level) to transport the shipment.

If the shipment is already staged and the new carrier and service level is associated with a different staging lane (location) than the old carrier and service level, then you can indicate whether to move the parcels from the old staging location to the new staging location immediately or using the work queue.

1.  Select **Shipping > Parcel**.
2.  Perform one of the following tasks:
    -   To view a list of parcel shipments, select **Shipments**.
    -   To view a list of packages and their associated shipments, select **Packages**.
3.  In the grid, click a shipment. The shipment details are displayed.
4.  From the **Actions** drop-down list, select **Change Carrier**. The Change Carrier window is displayed.
5.  Enter information in the following fields:
    
     
    | Field | Description |
    | --- | --- |
    | Carrier | Identifier for a carrier that delivers inbound inventory to the warehouse or outbound shipments to a customer. This is the identifier that will be displayed to users on the application windows and reports. In the application, a carrier can be associated with a customer, order, inbound shipment, outbound shipment, load, and service levels (such as Ground, Next Day, and Saturday Delivery). |
    | Service Level | Identifier for the service and transit time provided by the carrier that transports an order or shipment to the customer. For example, for a parcel carrier it may be used to indicate services such as express, second-day air, or standard delivery. |
    | System Moves Shipment Immediately | If Yes, then the staged shipment is automatically moved to the new staging lane in the application. This field is relevant if the new carrier and service level is associated with a different staging lane than the lane in which the parcels were originally staged.<br > If No, then directed work is created to move the shipment. |
    
6.  Click **OK**.

## Stage a parcel shipment

A shipment must be fully picked and in a staging lane before it can be staged.

**IMPORTANT**: After you stage a shipment, you no longer have the ability to reallocate any inventory that is missing due to cancelled picks.

1.  Select **Shipping > Parcel**.
2.  Perform one of the following tasks:
    -   To view a list of parcel shipments, select **Shipments**.
    -   To view a list of packages and their associated shipments, select **Packages**.
3.  In the grid, click a shipment. The shipment details are displayed.
4.  From the **Actions** drop-down list, select **Stage Shipment**.
    
    **Note**: If the shipment is successfully staged, there is no confirmation message displayed; instead, the status of the shipment and the progress bars are updated.
    

## View detailed parcel shipment information

1.  Select **Shipping > Parcel**.
2.  Perform one of the following tasks:
    -   To view a list of parcel shipments, select **Shipments**.
    -   To view a list of packages and their associated shipments, select **Packages**.
3.  In the grid, click a shipment. The shipment details are displayed.
4.  View information in the [Parcel Shipment detail fields](#Parcel_shipment_detail_fields).
5.  Select **Orders** and view information in the [Order detail fields](../../outbound-planner/outbound/procedures-for-orders.md).
6.  Select **Picks** and view information in the [Picks detail fields](../../shared-functions/waves-and-picks/procedures-for-picks-and-work-assignments.md).
7.  Select **LPNs** and view information in the [LPN detail field listings](../../shared-functions/inventory/procedures-for-lpns.md).
8.  Select **Shorts** and view information in the [Shorts detail fields](../../outbound-planner/outbound/procedures-for-shorts-and-replenishments.md).
9.  Select **Pending Replens** and view information in the [Pending Replenishments detail fields](../../outbound-planner/outbound/procedures-for-shorts-and-replenishments.md).
10.  Select **Customs** and view information in the [Customs Order fields](../../outbound-planner/outbound/procedures-for-orders.md).
11.  Select **Cross Dock** and view information in the [Cross Dock detail fields](../../outbound-planner/outbound/procedures-for-shorts-and-replenishments.md).

## View parcel packages

1.  Select **Shipping > Parcel**.
2.  To view all parcel packages, select **Packages**.
3.  To view the packages in a specific manifest, select **Manifests**, and then perform one of the following tasks:
    -   To view open manifests (in progress), select **Open**, and then in the grid, click the manifest.
    -   To view manifests that have shipped, select **Closed**, and then in the grid, click the manifest.
4.  View information in the [Parcel Package fields](#Parcel_package_fields).

## View detailed manifest information

1.  Select **Shipping > Parcel > Manifests**.
2.  Perform one of the following tasks:
    -   To view open manifests, select **Open**.
    -   To view closed manifests, select **Closed**.
3.  In the grid, click the manifest. The manifest details are displayed.
4.  View information in the [Manifest detail fields](#Manifest_detail_fields).
5.  In the grid, view information in the [Parcel Package fields](#Parcel_package_fields).

## Manifest detail fields

 
| Field | Description |
| --- | --- |
| Manifest | Internal tracking number assigned and used by the application to uniquely identify a manifest. A manifest list identifies all parcels that are shipped together on the same piece of transport equipment by the parcel carrier. This identifier is blank until the manifest is closed. |
| Carrier | Identifier for a carrier that delivers inbound inventory to the warehouse or outbound shipments to a customer. This is the identifier that will be displayed to users on the application windows and reports. In the application, a carrier can be associated with a customer, order, inbound shipment, outbound shipment, load, and service levels (such as Ground, Next Day, and Saturday Delivery). |
| Service Level | Identifier for the service and transit time provided by the carrier that transports an order or shipment to the customer. For example, for a parcel carrier it may be used to indicate services such as express, second-day air, or standard delivery. |
| Ship Date | Date on which the manifest was or will be shipped. |
| Destination | Staging location in which the parcel shipment is to be staged. For a manifest, if multiple shipments are included and are staged in different lanes, or if a single shipment is in two lanes, then both lanes are displayed (or the text "Many" and the number of lanes). |
| Picked | Percentage of inventory on the parcel shipment that has been picked. For a manifest, this is the percentage of picked inventory for all shipments on the manifest, if more than one is included. Additionally, an X of Y value displays the number of eaches that are picked out of the total number of expected eaches; for example, (50 of 100). |
| Staged | Percentage of inventory on the parcel shipment that has been staged. For a manifest, this is the percentage of staged inventory for all shipments on the manifest, if more than one is included. Additionally, an X of Y value displays the number of eaches that are staged out of the total number of expected eaches; for example, (50 of 100). |

## Parcel Package fields

 
| Field | Description |
| --- | --- |
| Shipment | Unique identifier for a parcel shipment. A parcel shipment consists of one or more parcels. The parcel is the shippable entity, while the parcel shipment is a grouping of parcels that is shipped together to the same destination. Typically, but not always, a parcel shipment only consists of one parcel. |
| Tracking Number | Unique number used by a parcel carrier to track a parcel throughout the delivery process. If a tracking number is displayed in this field when you enter the inventory ID associated with the parcel, it means that the parcel was previously manifested. You can reuse the tracking number, if appropriate; enter a different tracking number; or delete the tracking number (leaving the field blank) to have the parcel application (integrated through Parcel Handler) generate a new tracking number. |
| Package Status | Current condition of the package in the parcel manifesting process.<br>-   • **Released**: The package has been manifested and is ready to ship.
<br>-   • **Hold**: The package has been manifested, but is not yet ready to ship. This status is the result of manifesting a parcel to hold (automatically or manually).
<br>-   • **Closed**: The package is associated with a manifest that has been closed.
<br>-   • **Shipped**: The package has been loaded onto the parcel carrier's transport equipment and has left the facility.
<br>-   • **No selection (blank)**: The package is not manifested. |
| Carrier | Identifier for a carrier that delivers inbound inventory to the warehouse or outbound shipments to a customer. This is the identifier that will be displayed to users on the application windows and reports. In the application, a carrier can be associated with a customer, order, inbound shipment, outbound shipment, load, and service levels (such as Ground, Next Day, and Saturday Delivery). |
| Manifest | Internal tracking number assigned and used by the application to uniquely identify a manifest. A manifest list identifies all parcels that are shipped together on the same piece of transport equipment by the parcel carrier. This identifier is blank until the manifest is closed. |
| Service Level | Identifier for the service and transit time provided by the carrier that transports an order or shipment to the customer. For example, for a parcel carrier it may be used to indicate services such as express, second-day air, or standard delivery. |
| Ship Date | Date on which the manifest was or will be shipped. |
| Picked | Percentage of inventory on the parcel shipment that has been picked. For a manifest, this is the percentage of picked inventory for all shipments on the manifest, if more than one is included. Additionally, an X of Y value displays the number of eaches that are picked out of the total number of expected eaches; for example, (50 of 100). |
| Staged | Percentage of inventory on the parcel shipment that has been staged. For a manifest, this is the percentage of staged inventory for all shipments on the manifest, if more than one is included. Additionally, an X of Y value displays the number of eaches that are staged out of the total number of expected eaches; for example, (50 of 100). |

## Parcel Shipment detail fields

 
| Field | Description |
| --- | --- |
| Shipment | Unique identifier for a parcel shipment. A parcel shipment consists of one or more parcels. The parcel is the shippable entity, while the parcel shipment is a grouping of parcels that is shipped together to the same destination. Typically, but not always, a parcel shipment only consists of one parcel. |
| Status | Status that represents the processing state of the shipment.<br>-   • **Ready**: The shipment has been created or planned and is ready for allocation. Shipments can be created automatically by host download, or manually.
<br>-   • **In-Process**: Inventory for the shipment has been allocated.
<br>-   • **Staged**: The shipment has been staged manually or automatically. A shipment is staged when all inventory for the shipment has been picked and deposited in the ship staging location and is ready to be loaded onto the transport equipment.
<br>-   • **Loading**: At least one pallet, case, or piece of inventory has been deposited onto the transport equipment.
<br>-   • **Loaded**: All inventory for the shipment has been loaded onto the transport equipment.
<br>-   • **Complete**: The transport equipment containing the shipment has been closed and dispatched from the facility.
<br>-   • **Transfer**: Inventory for the shipment is being moved to a different ship staging location.
<br>-   • **Cancelled**: The shipment has been cancelled with a shipped quantity of zero. |
| Manifest | Internal tracking number assigned and used by the application to uniquely identify a manifest. A manifest list identifies all parcels that are shipped together on the same piece of transport equipment by the parcel carrier. This identifier is blank until the manifest is closed. |
| Carrier | Identifier for a carrier that delivers inbound inventory to the warehouse or outbound shipments to a customer. This is the identifier that will be displayed to users on the application windows and reports. In the application, a carrier can be associated with a customer, order, inbound shipment, outbound shipment, load, and service levels (such as Ground, Next Day, and Saturday Delivery). |
| Service Level | Identifier for the service and transit time provided by the carrier that transports an order or shipment to the customer. For example, for a parcel carrier it may be used to indicate services such as express, second-day air, or standard delivery. |
| Picked | Percentage of inventory on the parcel shipment that has been picked. For a manifest, this is the percentage of picked inventory for all shipments on the manifest, if more than one is included. Additionally, an X of Y value displays the number of eaches that are picked out of the total number of expected eaches; for example, (50 of 100). |
| Staged | Percentage of inventory on the parcel shipment that has been staged. For a manifest, this is the percentage of staged inventory for all shipments on the manifest, if more than one is included. Additionally, an X of Y value displays the number of eaches that are staged out of the total number of expected eaches; for example, (50 of 100). |
| Destination | Staging location in which the parcel shipment is to be staged. For a manifest, if multiple shipments are included and are staged in different lanes, or if a single shipment is in two lanes, then both lanes are displayed (or the text "Many" and the number of lanes). |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
