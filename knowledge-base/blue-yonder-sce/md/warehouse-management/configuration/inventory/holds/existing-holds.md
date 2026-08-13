---
title: "Existing Holds"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/existing_holds.htm"
source: "/content/existing_holds.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inventory"
  - "Holds"
  - "Existing Holds"
sections:
  - "Inbound hold criteria"
  - "Multi-level holds"
  - "Add or modify a hold"
  - "Delete a hold"
  - "Holds fields"
  - "Inbound Hold Criteria fields"
images: []
source_sha1: 477e669cca54327148bedc447c849977b09eaa33
---
# Existing Holds

A hold is an attribute that is applied to inventory without changing the inventory status. For example, if HOLD1 is applied to LPN1, LPN2, and LPN3 for ITEMA, the inventory status can remain as Available without being changed to a Hold status. With HOLD1 applied to the inventory, the hold can be configured to allow the LPNs to be allocated and shipped. For example, for damaged inventory, the hold allows the "held" inventory to have an Available inventory status for shipping to another location, such as for disposal.

A hold can be defined, maintained, and applied manually by a user or automatically through inbound integration transactions. Specifically, the application can receive the Hold Definition Information (HOLD\_DEF\_INB\_IFD) transaction to create, modify, enable, or disable a hold, and the Hold Assignment Information (HOLD\_ASSIGNMENT\_INB\_IFD) transaction to apply or remove a hold from inventory. Hold activity, displayed on the Holds page, identifies the date and time the hold was created and modified, and by whom. The user name SUPER identifies hold activity initiated by an integration transaction.

Holds are warehouse specific. The hold prefix, which is configured for the warehouse, can be used to identify the warehouse in which the hold was created.

A hold type is a category used to group holds that are similar, and typically identifies the purpose of the hold. For example, you can define a Customer Service hold type and an Inventory Control hold type to identify the departments for which the hold was created. There can be more than one hold applied the same LPN (or inventory) at the same time; for example, both HOLD1 and HOLD2 can be applied to LPN01.

You can configure a hold to prevent the status of inventory on hold from being changed. For example, if your facility uses aging profiles, you may want to prevent the status of inventory on hold from being changed automatically as it ages. The hold assigned to inventory can be configured to prevent the inventory from being allocated or shipped, but the hold itself does not change the inventory status.

## Inbound hold criteria

You can define an inbound (future) hold by setting the **Apply to Inbound Inventory** field to Yes, and then defining the criteria for the inventory to which it will be applied. An inbound hold is applied automatically to inventory that matches the criteria when the inventory is identified (such as during receiving, production line receiving, or an inventory adjustment) or, if an area or location is specified, moved to the specified area or location.

For example, if you configure inbound hold criteria for a specific item, lot, and supplier, then when inventory matching the item, lot, and supplier is identified, the hold is applied automatically. In addition, if existing inventory is adjusted (added or modified) to match the item, lot, and supplier (for example, if it was originally identified with the wrong lot), the hold is applied to that inventory as well.

**IMPORTANT**: If you select to apply the hold to inbound inventory, but you do not specify any inbound hold criteria, then the hold will be applied to all inventory that is identified or adjusted.

When configuring inbound hold criteria, you can specify an area or location to limit the locations in which the hold is applied automatically. If you specify an area or location, then the following behavior occurs:

-   The hold is applied to matching inventory that is either identified to, adjusted into, or moved into the specified area or location. If the hold is applied to the inventory, it remains applied when the inventory is moved out of the area or location.
-   The hold is not automatically applied to matching inventory that currently exists in the area or location.
-   The hold is not automatically applied to matching inventory that is identified to, adjusted into, or moved into other areas or locations.

For example, a hold is defined with the following inbound hold criteria:

-   **Item**: ITEM01
-   **Manufacturing Date**: **From** 5/1/2019, **To** 5/31/2019

If a pallet of ITEM01 is received with a manufacturing date of 5/2/2019, the hold is applied. If another pallet of ITEM01 is received with an incorrect date of 4/31/2019, the hold is not applied. After the pallet is put away to a storage location, a user performs an inventory adjustment to correct the manufacturing date to 5/2/2019. Now the inventory matches the hold criteria, and the hold is applied automatically.

As another example, a hold is defined with the following inbound hold criteria:

-   **Item**: ITEM01
-   **Manufacturing Date**: **From** 5/1/2019, **To** 5/31/2019
-   **Area**: Expected Receipts

If a pallet of ITEM01 is received with a manufacturing date of 5/2/2019, the hold is applied. If another pallet of ITEM01 is received with an incorrect date of 4/31/2019, the hold is not applied. After the pallet is put away to a storage location, a user performs an inventory adjustment to correct the manufacturing date to 5/2/2019. However, the hold is not applied.

Since you specified the Expected Receipts area, the hold is applied to matching inventory during receiving, but it is not applied when making inventory attribute changes to existing inventory in other areas of the warehouse, and it is not applied to matching inventory received from a production line.

## Multi-level holds

You can place multiple holds on the same inventory for different reasons, such as to meet multiple processing requirements for the inventory. For example, you can place two holds on the same inventory; the first hold prevents it from being allocated until it is repackaged, and the second hold prevents it from being shipped until it passes a final inspection.

## Add or modify a hold

1.  Select **Configuration > ** **Inventory > Holds > Existing Holds**.
    
    **Note**: You can also add a hold (without modification) on the Holds page in the Inventory module.
    
2.  Perform one of the following tasks:
    -   To add a new hold, click **Add**.
    -   To modify a hold, in the grid, click the hold.
    -   To copy a hold, in the grid, select the check box next to the hold, and then click **Copy**.
3.  Enter information in the [Holds fields](#Holds_fields).
4.  If the **Apply to Inbound Inventory** field is set to **Yes**, then define the criteria for the inventory to which the hold will be automatically applied at the time of receipt:
    1.  Under **INBOUND PROCESSING**, click **Inventory** **Criteria**.
    2.  Enter information in the [Inbound Hold Criteria fields](#Inbound_Hold_Criteria_fields).
    3.  Click **Apply**.
5.  To view information related to activity for the hold, such as when is was created, under **Activity**, view the following fields:
    
     
    | Field | Description |
    | --- | --- |
    | Created By | User who created the hold. |
    | Create Date | Date and time at which the hold was created. |
    | Modified By | User who modified the hold. |
    | Modified Date | Date and time at which the hold was modified. |
    
6.  Click **Save**.

## Delete a hold

You cannot delete a hold when the hold is enabled.

1.  Select **Configuration > Inventory > Holds > Existing Holds**.
2.  In the grid, select the check box next to the hold to delete.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Holds fields

 
| Field | Description |
| --- | --- |
| Enable Hold | If enabled, this hold can be applied to inventory, either through a manual process from a workstation or automatically, if it is configured to be applied to expected inbound inventory.<br > If disabled, the hold is not available for use and cannot be applied to inventory. |
| Source | Prefix applied to the hold number. The hold source is typically site specific, and it distinguishes the holds placed on inventory at one site from holds placed on inventory at another site. This field is display only, and is populated with a value from the warehouse configuration (either the **Default Hold Prefix** or, if that field is blank, the **Warehouse Name**). |
| Hold | Unique identifier for the hold definition. Hold numbers are applied to inventory identifiers to indicate that the inventory is on hold as described in the hold definition. Hold numbers can either be user defined or application generated when hold definitions are created. |
| Notes | Additional information related to the hold. You use this field, for example, to describe the purpose of the hold and when it was created. This field is for informational purposes only; it is not used by any process. |
| Description | Description of the hold that is displayed on the application windows and in reports. |
| Type | Code that defines the category to which this hold belongs. Typically, the hold type identifies the purpose of the hold. The hold type is used only for display and report purposes. |
| Severity | Hold severity categorizes a hold by how serious it is from an operational standpoint. The levels range from 1 to 5, with 1 being the most critical. Setting a severity determines the order in which the hold is displayed on the Inventory dashboard. |
| Inventory Status | If Yes, then at the time a user applies or removes the hold, the user can also change the inventory status.<br > If No, then the application prevents users from changing inventory status when the hold is either applied or removed.<br > **Note**: This field only affects whether a user can change inventory status during the hold application or removal process. This field does not impact whether a status change can be made (manually or automatically) after the hold is applied or removed. |
| Apply to Inbound Inventory | If Yes, then during receiving or identification, the application automatically applies the hold to inventory that matches the inventory criteria defined for the hold. If you select Yes, then you must also select a reason for applying the hold, and define the inventory criteria.<br > If No, the application does not automatically apply the hold to any inventory. |
| Reason | Value that indicates why the hold is being applied. A reason is required whenever a hold is applied to inventory, but this reason is used specifically when the application applies the hold automatically to new inventory. Only available when **Apply to Inbound Inventory** is set to Yes. |
| Allocation | If Yes, then when this hold is applied to inventory, it does not prevent the inventory from being allocated for an order. Select Yes if you allow inventory on hold to be allocated for an order.<br > If No, then when this hold is applied to inventory, it prevents the inventory from being allocated for an order. Select No if you want to prevent the inventory from being used to fulfill an order while the inventory is on hold. |
| Shipping | If Yes, then when this hold is applied to inventory, it does not prevent the inventory from being shipped from the warehouse. Select Yes if you allow inventory on hold to be shipped.<br > If No, then when this hold is applied to inventory, it prevents the inventory from being shipped. Select No if you want prevent the inventory from being shipped to a customer while the inventory is on hold. |
| Movement for RF Outbound Audit | If Yes, inventory placed under this hold during an outbound audit can be moved. Typically, inventory under an audit hold is not allowed to be moved to ensure that it is not loaded until the audit is successfully completed. However, supervisors may require the ability to move and adjust the held inventory while reconciling failed audits. Select Yes to allow the movement of inventory that is under this hold.<br > **Note**: To ensure that only authorized personnel can move held inventory, in addition to selecting Yes, you also must configure the user role options to give certain roles the ability to move inventory under a hold that allows movement. See [Roles](../../../../administration/system-administrator/authorization/roles.md).<br > If No, inventory placed under this hold during an outbound audit cannot be moved, regardless of the role options that are assigned to the operator. |

## Inbound Hold Criteria fields

 
| Field | Description |
| --- | --- |
| Item | Identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). Before the application can effectively store, track, and manipulate inventory, you must assign an item identifier and define the attributes of each item you want to track. When defining an item, you specify information such as how the item is packaged and handled, along with details that define how it should be received, stored, allocated, shipped, counted, and valued (cost information). |
| Item Family | Identifier used to group similar items together. Typically, all of the items within a family have the same material handling characteristics. |
| Inventory ID | Identifier (LPN, sub-LPN, or detail LPN) for the inventory to be placed on hold. |
| Lot | Identifier assigned to a quantity of an item during the manufacturing process for the purpose of tracking an attribute of that item, such as an expiration date. Lots differentiate distinct groups of inventory with the same item number. Items that may require a lot number include pharmaceuticals, fabrics, food, and other products with limited shelf life. Lots are user defined and are not necessarily unique since the same lot number can be applied to different items. However, lot and item combinations must be unique. |
| Supplier Lot Number | Identifier that is an attribute of an item or item and lot combination and is assigned by the item's supplier. A supplier lot number used to uniquely identify and track the inventory to which it is assigned. The supplier lot number is a different attribute than the lot number, which is a manufacturer or production lot number. |
| Revision Level | Identifier that is assigned to an item number to differentiate revisions of the same item number. |
| Customs Consignment ID | Unique identifier assigned to a receipt of bonded inventory. A customs consignment is an application-generated ID number that consists of a prefix (the warehouse ID) plus the next value in the customs consignment ID sequence. For example, if your warehouse ID is WMD1 and the next number in the sequence is 123456, then the customs consignment ID will be WMD1123456.<br > Only displayed if Customs functionality is enabled for the warehouse and the item is configured for customs tracking. |
| Rotation | Unique identifier that the application generates and automatically assigns to bonded inventory during receipt of that inventory into a bonded warehouse. The rotation ID is tracked with the inventory as long as the inventory is in the warehouse. |
| Under Bond | If Yes, then inventory must be bonded in order for the application to apply the hold. Bonded inventory is inventory for which customs duties and excise duties are required and have not yet been paid.<br > If No, then the hold is applied to inventory that is not under bond. |
| Excise Duty Stamp | If Yes, then the inventory requires a duty stamp in order for the application to apply the hold. A duty stamp is a form of tax levied on certain excise items.<br > If No, then the hold is applied to inventory that does not require a duty stamp. |
| Client | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. |
| Origin | Identifier that is assigned to an item to identify the item's place of origin. Typically used for export paperwork. Origins are user defined. |
| Status | Quality status of an item. Inventory statuses are uniquely defined for your application during the initial setup, and they can be used to identify the physical condition and availability of the inventory, or special material handling requirements for the inventory. |
| Manufacturing Date | Range of manufacturing dates of inventory to which the hold should be applied. The range includes both a date and time. The dates and times are stored in the database and displayed in the web client in the original captured time zone, not converted to a different time zone, such as a user preferred time zone. |
| Supplier | Identifier for a supplier. A supplier can be an individual, organization, or another warehouse within your own organization from which you repeatedly receive inventory or handling units. |
| Inbound Shipment | Unique identifier used for inventory tracking for an inbound shipment of inventory. An inbound shipment is a group of orders that are transported to the warehouse together or received together. When inventory arrives at the warehouse on a piece of transport equipment, an inbound shipment represents the contents of the transport equipment; however, one or more inbound shipments can be associated with a piece of transport equipment. |
| Planned Inbound Order | Identifier for a planned inbound order that is associated with a specific supplier. A planned inbound order is an authorization to receive specific inventory and quantities from a supplier. It is used, but not required, to receive inventory into the warehouse. |
| Work Order | Identifier for a work order. A work order is an internal order used to find, allocate, and deliver product to a work-in-process area for assembly or disassembly, conversion, kitting, or repackaging. |
| Work Order Revision | Identifier for one instance of a work order that allows you to use a standard work order multiple times. |
| Area | Identifier for the area in which the hold is applied automatically when matching inventory is identified to, adjusted into, or moved into the area. If you specify an area, the application does not apply the hold automatically to matching inventory that is identified to, adjusted into, or moved into other areas.<br > For example, a hold is defined with the following inbound hold criteria:<br>-   • **Item**: ITEM01
<br>-   • **Manufacturing Date**: **From** 5/1/2019, **To** 5/31/2019
<br>-   • **Area**: Expected Receipts
<br > If a pallet of ITEM01 is received with a date of 5/2/2019, the hold is applied. If another pallet of ITEM01 is received with an incorrect date of 4/31/2019, the hold is not applied. After the second pallet is put away to a storage location, a user performs an inventory adjustment to correct the manufacturing date to 5/2/2019. Now the item and manufacturing date match the criteria, but the hold is not applied because the inventory is not in the Expected Receipts area. |
| Storage Location | Identifier for the location in which the hold is applied automatically when matching inventory is identified to, adjusted into, or moved into the location. If you specify a location, the application does not apply the hold automatically to matching inventory that is identified to, adjusted into, or moved into other locations.<br > For example, if you specify a receiving staging location, then the inbound hold is applied automatically to matching inventory identified in that staging location. It is not applied automatically to matching inventory added to other locations, such as through inventory adjustments or attribute changes. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
