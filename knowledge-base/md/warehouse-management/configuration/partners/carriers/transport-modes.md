---
title: "Transport Modes"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/transport_modes.htm"
source: "/content/transport_modes.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Partners"
  - "Carriers"
  - "Transport Modes"
sections:
  - "Add or modify a transport mode"
  - "Delete a transport mode"
  - "Transport Mode fields"
images: []
source_sha1: 435a488d2661302ee8b30b00f3926c30b9c9999b
---
# Transport Modes

A transport mode is a definition of how freight is to be transported from one location to another. When you define a transport mode, you specify the following attributes:

-   Type of transport to be used, such as full truckload, less than truckload, or small package (parcel).
-   Whether the mode is for a shipment that is less-than-truckload (LTL) and is shipped direct with no stop-off deliveries along the way. This is not necessarily a small package (parcel) mode.
-   Maximum number of operators that are allowed to perform directed or undirected work (such as picking, transferring, staging, or loading) for a load at the same time
-   Whether an operator that is performing work for a load is allowed to perform work for other loads while pending work exists for the load to which they are currently assigned
-   Whether inventory belonging to a selected UOM will be included in optimal dock door calculations. See [Optimal outbound dock door](../../outbound/shipping.md).

The application supplies the following pre-defined transport modes:

-   Full truckload (T)
-   Less than truckload (L)
-   Small package parcel (S)

Generally, the pre-defined transport modes describe the typical means by which freight is transported.

## Add or modify a transport mode

1.  Select **Configuration > Partners > Carriers > Transport Modes**.
2.  Perform one of the following tasks:
    -   To add a new transport mode, click **Add**.
    -   To modify a transport mode, in the grid, click the transport mode.
3.  Enter information in the [Transport Mode fields](#Transport_Mode_fields).
4.  To configure the transport mode settings specific to the current warehouse:
    1.  Set the **Enable Transport Mode in Warehouse** field to **Enabled**.
    2.  Enter information in the following fields:
        
        | Field | Description |
        | --- | --- |
        | Lock User | If Yes, then a user who is performing work (such as picking, transferring, staging, or loading) for the outbound load is not allowed to perform work for other loads until there is no longer any pending work for this load.<br > If No, then a user performing work on this load can perform work for other loads while there is pending work for this load. |
        | Maximum Users | Maximum number of users who are allowed to perform directed and undirected work for the load. For example, if this value is 1, then if one user is performing work (such as picking) for the load, then no other users can perform work (such as picking, transferring, staging, or loading) for the load. If this value is 0, then there is no limit to the number of users who can perform work for the load. |
        | Bill of Lading Break Level | Default level at which a bill of lading (BOL) is provided when a master BOL is required. For example, if the transport mode typically carries multiple stops, selecting the Stop level ensures that the paperwork includes a BOL for each stop. If the break level is Load, or left blank, then a shipment or stop bill of lading is not included. |
        
    3.  To define the units of measure (UOMs) used to determine an optimal dock door for transport equipment:
        1.  Perform one of the following tasks:
            -   To define a new UOM, click **Add**.
            -   To modify a UOM, click the UOM.
        2.  Enter information in the following fields:
            
            | Field | Description |
            | --- | --- |
            | Units of Measure | Packaging level at which an item is received, added, counted, or modified. |
            | Include in Optimal Dock Door Calculation | If Yes, the selected UOM is considered in optimal dock door calculations. The application uses optimal dock door calculations to recommend the best dock door at which to park transport equipment for loading.<br > If No, the UOM is not considered in optimal dock door calculations. |
            
    4.  Click **Apply**.
5.  Click **Save**.

## Delete a transport mode

1.  Select **Configuration > Partners > Carriers > Transport Modes**.
2.  In the grid, select the check box next to the transport mode to delete.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Transport Mode fields

 
| Field | Description |
| --- | --- |
| Transport Mode | Name of the transport mode used to ship inventory. |
| Description | Description of the transport mode. This text is displayed when the user assigns a transport mode on various application windows. |
| Parcel | If Yes, the transport mode is for shipping parcels or small packages.<br > If No, the transport mode is not for shipping parcels or small packages. |
| Direct | If Yes, the transport mode is for a shipment that is shipped direct with no stop-off deliveries on the way.<br > If No, the transport mode is not for shipments that are shipped direct with no stop-off deliveries on the way. |
| Pallet Building | Rule that determines the attributes that must be the same for inventory to be consolidated on the same pallet during pallet build operations. Pallet building is a process in which cases or repack cartons are consolidated after picking to create a new pallet. For example, if the rule is based on the shipment, then when an operator attempts to build a pallet, the application verifies that each case on the pallet is part of the same shipment. Alternatively, if the rule is based on staging lane, then inventory from different shipments can be added to the same pallet as long as the destination staging location is the same.<br > The options that are available are defined in shipping staging configuration. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
