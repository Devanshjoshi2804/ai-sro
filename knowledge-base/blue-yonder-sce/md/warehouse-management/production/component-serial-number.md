---
title: "Component Serial Number"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/component_serial_number.htm"
source: "/content/component_serial_number.htm"
toc_path:
  - "Warehouse Management"
  - "Production"
  - "Component Serial Number"
sections:
  - "View component serial numbers"
  - "Component Work Order fields"
  - "Component Serial Number fields"
images: []
source_sha1: 0f427b25331e2ae08284d35caec2d122ea3eed4b
---
# Component Serial Number

You can view the serial numbers that have been captured for a work order's component items.

## View component serial numbers

1.  Select **Production > Component Serial Number**.
2.  View the [Component Work Order fields](#Component_work_order_fields).
3.  In the grid, expand a work order, and then view the [Component Serial Number fields](#Component_serial_number_fields).

## Component Work Order fields

 
| Field | Description |
| --- | --- |
| Work Order | Identifier for a work order. A work order is an internal order used to find, allocate, and deliver product to a work-in-process area for assembly or disassembly, conversion, kitting, or repackaging. |
| Component Key | Unique application-assigned identifier for a component item. |
| Item Number | Identifier for the item. |
| Disassembly | Indicates whether the work order is for disassembling a top-level item into component items. If not, the work order is for assembling component items into a top-level item. |
| Item Client | Name of the client who stores this item in the facility. This field is only displayed in a 3PL environment. |
| Lot Number | Identifier assigned to a quantity of inventory that is uniquely identified during the manufacturing process for the purpose of tracking an attribute of that inventory, such as its expiration date. Lots differentiate distinct groups of inventory that have the same item. Lots are user defined and are not necessarily unique since the same lot can be applied to different items. However, lot and item number combinations must be unique. |
| Revision Level | Identifier that is assigned to an item number to differentiate revisions of the same item number. |
| Work Order Revision | Identifier for one instance of a work order that allows you to use a standard work order multiple times. |
| Work Order Type | Unique identifier for the work order type. A work order type is a category into which work orders are grouped based on similar processing characteristics. |
| Sub-LPN | Unique identifier for a case of inventory. |

## Component Serial Number fields

 
| Field | Description |
| --- | --- |
| Work Order | Identifier for a work order. A work order is an internal order used to find, allocate, and deliver product to a work-in-process area for assembly or disassembly, conversion, kitting, or repackaging. |
| Component Key | Unique application-assigned identifier for a component item. |
| Item Number | Identifier for the item. |
| Serial Number | Unique identifier that is used to identify a piece of inventory in the warehouse. The identifier may contain numbers, letters, and check digits as required by the serial number type, and may be captured for an LPN, sub-LPN or detail LPN of inventory. The point at which the serial number is captured is determined by the serialization type assigned to the item. |
| Disassembly | Indicates whether the work order is for disassembling a top-level item into component items. If not, the work order is for assembling component items into a top-level item. |
| Item Client | Name of the client who stores this item in the facility. This field is only displayed in a 3PL environment. |
| Lot Number | Identifier assigned to a quantity of inventory that is uniquely identified during the manufacturing process for the purpose of tracking an attribute of that inventory, such as its expiration date. Lots differentiate distinct groups of inventory that have the same item. Lots are user defined and are not necessarily unique since the same lot can be applied to different items. However, lot and item number combinations must be unique. |
| Revision | Revision level of the component item consumed in an assembly work order. A revision level is a unique identifier that is assigned to an item to differentiate revisions of the same item. Revision levels are user defined. |
| Work Order Revision | Identifier for one instance of a work order that allows you to use a standard work order multiple times. |
| Work Order Type | Unique identifier for the work order type. A work order type is a category into which work orders are grouped based on similar processing characteristics. |
| Sub-LPN | Unique identifier for a case of inventory. |
| Detail LPN | Unique identifier for inventory at the unit or each unit of measure. |
| Unit Quantity | Number of individual units of the item contained in the unit of measure (UOM). The application automatically updates this value based on the values for UOM Quantity and next UOM. For example, if the configuration has Pallet, Case, and Each UOMs, and there are 10 eaches per Case and 10 cases per Pallet, then the unit quantity for Pallet is 100. |
| Origin Code | Origin code of the component items consumed in an assembly work order. An origin code is a unique identifier that is assigned to an item to identify the item's place of origin. Typically used for export paperwork. Origin codes are user defined. |
| Sub-Component Key | Unique application-assigned identifier for a sub-component item. |
| Supplier Number | Unique code that identifies a supplier. A supplier is considered to be any source from which you receive product. For example, a supplier can be an individual, an organization, or another plant within your own organization from which you repeatedly receive product. Only inventory from this supplier can be used for the distribution. |
| Sub-Component | Indicates that the component is consumed as a sub-component of another component item. A value of Yes is displayed if the component is a sub-component item. |
| Inventory Identifiers | Unique inventory identifier, such as an LPN or case identifier. |
| Warehouse ID | Unique ID associated with the warehouse. |
| Production Line | Name of the production line. A production line is an arrangement of machines or sequence of operations (production stations) involved with the assembly or disassembly of top-level item. |
| User ID | Unique identifier of the user who has provided the component tracking details. |
| Serial Number Type | Identifier for a specific kind of serial number. A serial number type defines the order in which the operator is prompted to enter serial numbers when multiple types are required for an item, whether serial numbers of this type are reported to the host, and the number mask that is used to verify that a valid serial number has been entered. |
| Serial Level | The serialization level of the component. |
| Last Modified By | Username of the last person who modified the work order line. |
| Date Last Modified | Date and time indicating when the work order line was last modified. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
