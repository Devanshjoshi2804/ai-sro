---
title: "Receiving Handling Units Display"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/receiving_handling_unit_display.htm"
source: "/content/receiving_handling_unit_display.htm"
toc_path:
  - "Warehouse Management"
  - "Receiving"
  - "Receiving Handling Units Display"
sections:
  - "View received handling units"
  - "Receiving Handling Units Display fields"
images: []
source_sha1: f05956460b4e31f3f20b51b31722368353a4e50d
---
# Receiving Handling Units Display

You use the Receiving Handling Units Display pages to view serialized and non-serialized handling units that have been received from an inbound shipment. Handling units that contain inventory and empty handling units are displayed if inventory handling unit tracking is enabled. See [Handling unit categories](../configuration/inventory/lpn-handling.md) and [Configure handling unit settings](../configuration/inventory/lpn-handling/handling-unit-settings.md).

## View received handling units

1.  Perform one of the following tasks: 
    -   To view received serialized handling units, select **Receiving > Receiving Handling Units Display Serialized**.
    -   To view non-serialized handling units, select **Receiving > Receiving Handling Units Display Non-Serialized**.
2.  Enter search criteria or select a filter.
3.  View the information in the [Receiving Handling Units Display fields](#Receiving_handling_unit_display_fields).

## Receiving Handling Units Display fields

 
| Field | Description |
| --- | --- |
| Inbound Shipment ID | Unique identifier used for inventory tracking for an inbound shipment of inventory. An inbound shipment is a group of orders that are transported to the warehouse together or received together. When inventory arrives at the warehouse on a piece of transport equipment, an inbound shipment represents the contents of the transport equipment; however, one or more inbound shipments can be associated with a piece of transport equipment. |
| Client ID | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. |
| Supplier Number | Unique code that identifies a supplier. A supplier is considered to be any source from which you receive product. For example, a supplier can be an individual, an organization, or another plant within your own organization from which you repeatedly receive product. |
| Planned Inbound Order Number | Identifier for a planned inbound order that is associated with a specific supplier. A planned inbound order is an authorization to receive specific inventory and quantities from a supplier. It is used, but not required, to receive inventory into the warehouse. |
| Handling Unit Type | Category that classifies a group of handling units (for example, pallets, totes, transport equipment, or vehicles) that share the same characteristics such as size and weight, as well as whether they are serialized, temporary, or considered a container. The application tracks the on-hand quantity of handling units by type and, for serialized handling units, by handling unit identifier. |
| Handling Unit Status | Current condition of the handling unit, such as active or inactive. This value is only used for reporting purposes. |
| Quantity | Quantity of the handling unit type to be received against the planned inbound order. |
| On-Hand Quantity | Quantity of the handling unit type that is currently in storage. |
| Empty | Indicates whether the handling unit currently contains inventory. |
| Warranty Date | Date and time that the warranty of the individual handling unit expires. Enter a date or click the calendar to select a date from the display. |
| Manufacturer ID | Name of the company that produced the individual handling unit. |
| Model | Alphanumeric model number for the individual handling unit. Manufacturers use model numbers to differentiate similar products. |
| Purchase Date | Date and time that the individual handling unit was purchased. Enter a date or click the calendar to select a date from the display. |
| Location | Location in the warehouse in which the handling unit is stored. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
