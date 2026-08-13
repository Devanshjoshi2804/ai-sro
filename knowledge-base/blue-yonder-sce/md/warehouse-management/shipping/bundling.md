---
title: "Bundling"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/bundling.htm"
source: "/content/bundling.htm"
toc_path:
  - "Warehouse Management"
  - "Shipping"
  - "Bundling"
sections:
  - "Bundling examples"
  - "Bundling and manifesting at the same time"
  - "Bundling first, then manifesting"
  - "Parcel bundling eligibility"
  - "Dimensions of a bundled parcel LPN"
  - "Bundle inventory"
  - "Unbundle inventory"
images: []
source_sha1: 4003ecc013019deee4cf589e6839dceafc515ecb
---
# Bundling

You use the Bundling page to view, select, and bundle or unbundle eligible LPNs. If Warehouse Management is integrated with a parcel application through Parcel Handler, then you can also manifest a bundled parcel.

The Bundling page consists of the following tabs:

-   **Bundle**: Displays the list of picked LPNs that match your search criteria, and that reside in a ship staging location and have no outstanding cartonized picks.
-   **Unbundle**: Displays the list of bundled LPNs that match your search criteria.

You must enter search criteria to retrieve data. In the search field, when you enter a value for an identifier, the application searches for that identifier in LPN, LPN UCC, Sub-LPN, and Sub-LPN UCC fields; you do not have to specify the type of identifier. Search results (such as for a shipment) applicable to both bundled and unbundled inventory are displayed on both tabs.

**Note**: The **Bundle and Manifest** button is only available if Warehouse Management is integrated with a parcel application through Parcel Handler.

## Bundling examples

The following examples illustrate two common scenarios for bundling parcels: bundling and manifesting at the same time; and bundling first, then manifesting later. Each example provides a scenario and an associated standard process.

**IMPORTANT**: For manifesting to take place, Warehouse Management must be integrated with a parcel application through Parcel Handler.

### Bundling and manifesting at the same time

The following process illustrates bundling a group of parcels together and immediately manifesting the resulting bundled parcel LPN. In this example, a user picks the cartons for a single shipment into a physical tote. When all the cartons are picked for the shipment, the user brings the tote to a manifest station. At the manifest station, a user manually determines which parcels can be grouped together and physically bands the parcels together. The user then indicates in the application which parcels have been bundled together and manifests the resulting bundled parcel LPN.

To bundle and manifest at the same time, see [Bundle inventory](#Bundle_inventory).

### Bundling first, then manifesting

The following process illustrates bundling the parcels together and then later manifesting the resulting bundled parcel LPNs. In this example, a user picks the cartons for a single shipment into a physical tote. When all of the cartons are picked for the shipment, the user brings the tote to a manual consolidation ship staging location. In the consolidation location, a user manually determines which parcels can be grouped together and physically bands the parcels together. The user then indicates in the application which parcels have been bundled together. The bundled parcel LPNs are then moved to a manifest station where a user manifests the bundled parcel LPNs.

To bundle parcels, see [Bundle inventory](#Bundle_inventory).

To manifest bundled parcel LPNs, see [Manifest a parcel](manifesting.md).

## Parcel bundling eligibility

To be eligible to be bundled together, parcels must meet the following criteria:

-   Belong to the same outbound shipment
-   Be shipped by a carrier at a service level that permits bundling. To configure a carrier service level for bundling, see [Configure parcel](../configuration/outbound/shipping/parcel.md) or [Add or modify a carrier](../configuration/partners/carriers/existing-carriers.md).
-   Be located in one or more ship staging locations. The newly bundled parcel LPN is created in the ship staging location that you select.
-   Not have any outstanding cartonized picks
-   Have the same attributes as the rest of the parcels in the bundle, as defined by the bundling criteria. To define bundling criteria, see [Configure parcel](../configuration/outbound/shipping/parcel.md).

You cannot add parcels to a bundled parcel LPN that has been manifested. Instead, you must void the bundled parcel LPN from the manifest; then you can modify it by adding a parcel or unbundling it.

## Dimensions of a bundled parcel LPN

The application calculates the default dimensions for a bundled parcel LPN based on a configuration in which the original individual parcels are stacked on top of each other.

-   **Height**: The sum of the height of the original individual parcels. For example, if you have 3 parcels, each 12 inches tall, the default height of the parcel LPN is 36 inches.
-   **Length**: The length of the longest original individual parcel. For example, if you have 3 parcels that are 10 inches, 12 inches, and 24 inches long (respectively), then the default length of the parcel LPN is 24 inches.
-   **Width**: The width of the widest original individual parcel. For example, if you have 3 parcels that are 10 inches, 12 inches, and 18 inches wide (respectively), then the default width of the parcel LPN is 18 inches.

Using the example values, the dimensions of the bundled parcel LPN (consisting of 3 parcels) would be 36 x 24 x 18 inches.

If you manifest the bundled parcel LPN, you can change the dimensions to match the actual dimensions of the bundled parcel LPN.

## Bundle inventory

Use this procedure to group parcels into a bundled parcel LPN or add parcels to an existing bundled parcel LPN.

Parcels cannot be added to a manifested bundled parcel LPN. If you want to add a parcel to a bundled parcel LPN that has been manifested, you must first void the bundled parcel LPN from the manifest. See [Void a manifested parcel](parcel/procedures-for-parcels.md).

Depending on configuration, you may not be allowed to add a manifested parcel to a bundle.

**IMPORTANT**: Parcels can only be bundled if bundling is supported by the parcel shipment's carrier and service level. Manifesting is only available if Warehouse Management is integrated with a parcel application through Parcel Handler.

1.  Select **Shipping > Bundling > Bundle.**
2.  Enter search criteria to display the parcels that are available to bundle.
3.  In the grid, select the parcels that you want to bundle together.
4.  In the **Destination LPN** field, enter an LPN for the bundle.
    
5.  In the **Destination Location**, enter the ship staging location for the bundled parcel LPN.
    
    **Note**: If you add parcels to an existing bundled parcel LPN, then the location of the existing bundled parcel LPN is displayed and cannot be changed. Adding parcels to a bundled parcel LPN does not change the location of the bundled parcel LPN.
    
6.  Perform one of the following tasks:
    -   To bundle the selected inventory, click **Bundle**. The bundled parcel LPN is created and you can view its details on the **Unbundle** tab.
        
        **Note**: If the inventory cannot be bundled, an error message displays the identifier of the first parcel to fail the bundling process.
        
    -   To bundle the inventory and manifest the bundled parcel LPN:
        1.  Click **Bundle and Manifest**. The bundled parcel LPN is created and you can view its details on the **Unbundle** tab. The Manifesting page is displayed.
        2.  Continue with [Manifest a parcel](manifesting.md).

## Unbundle inventory

Unbundling is the process of separating a bundled parcel LPN into separate parcels.

The application does not allow you to unbundle a manifested bundled parcel LPN. Instead, you must first void the bundled parcel LPN from the manifest, and then unbundle it. See [Void a manifested parcel](parcel/procedures-for-parcels.md).

1.  Select **Shipping > Bundling > Unbundle**.
2.  Enter search criteria to display the LPNs that are available to unbundle.
3.  In the grid, select the LPN to unbundle, and then click **Unbundle**. The bundled parcel LPN is removed from the application and the individual parcels are tracked by their original carton number (sub-LPN) under a new application-generated LPN.
    

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
