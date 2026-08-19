---
title: "Procedures for holds"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/procedures_for_holds.htm"
source: "/content/procedures_for_holds.htm"
toc_path:
  - "Warehouse Management"
  - "Inventory"
  - "Holds"
  - "Procedures for holds"
sections:
  - "Add a hold"
  - "Enable a hold"
  - "Disable a hold"
  - "Apply a hold to inventory"
  - "Release a hold from inventory"
  - "Holds fields"
  - "Inbound Hold Criteria fields"
images: []
source_sha1: 8cee436d88ca7caae407663bec0ce63cf3f0fc9c
---
# Procedures for holds

You can perform the following procedures on holds.

## Add a hold

You can create a new hold definition.

1.  Select **Inventory** > **Holds**.
2.  On the **Active Holds** tab, from the **Actions** drop-down list, select **Add Hold**.
3.  Enter information in the [Holds fields](#Holds_fields).

**Note**: Hold definitions are differentiated based on the hold type and severity.

5.  If the **Apply to Inbound Inventory** field is set to **Yes**, then define the criteria for the inventory to which the hold will be automatically applied at the time of receipt:
    1.  Under **INBOUND PROCESSING**, click **Inventory Criteria**.
    2.  Enter information in the [Inbound Hold Criteria fields](#Inbound_Hold_Criteria_fields).
    3.  Click **Apply**.
6.  Click **Save**. The **Hold** tag is displayed for the items and LPNs in the Items and LPNs view when a hold is applied to inventory.

## Enable a hold

You can enable hold definitions on the Disabled Holds tab. Enabled holds are displayed on the Active Holds tab.

1.  Select **Inventory** > **Holds**.
2.  Select **Disabled Holds**.
3.  In the grid, select the hold to enable.
4.  From the **Actions** drop-down list, select **Enable Hold**. A confirmation message is displayed.
5.  Click **OK**.

## Disable a hold

You cannot disable a hold that is associated with inventory, or an inbound or outbound order.

1.  Select **Inventory** > **Holds**.
2.  On the **Active Holds** tab, select the hold to disable.
3.  From the **Actions** drop-down list, select **Disable Hold**. A confirmation message is displayed.
4.  Click **OK**.

## Apply a hold to inventory

You can apply one or more holds to the same inventory. When you apply a hold to an item, all of the inventory for that item is held, regardless of the LPN on which the inventory is located. When you apply a hold to inventory on a specific LPN, only the inventory on that LPN is held.

You can also apply a hold to an item or inventory in a location by viewing the detailed information for a location or item (on the Summary tab). See [View detailed LPN information](../../shared-functions/inventory/procedures-for-lpns.md) and [View detailed item information](../../shared-functions/inventory/procedures-for-items.md).

1.  Perform one of the following tasks:
    -   View the Inventory page, select **On-Site**, and then perform one of the following tasks:
        
        1.  Select one of the following modules: **Inventory**, **Outbound Planner**, **Picking**, **Production**, **Receiving**, or **Shipping**.
        2.  Select **Inventory**.
        
        -   To apply a hold to an item, select **Items**, and then in the grid, select the check box next to the item.
        -   To apply a hold to inventory on a specific LPN, select **LPNs**, and then in the grid, select the check box next to the LPN.
        -   To apply a hold to inventory in a specific location:
            1.  Select **Locations**.
            2.  In the grid, click the location. The location details are displayed.
            3.  Perform one of the following tasks:
                -   To apply a hold to an item in the location, select **Items**, and then in the grid, select the check box next to the item.
                -   To apply a hold to an LPN in the location, select **LPNs**, and then in the grid, select the check box next to the LPN.
    -   View a grid with a link for a location, click the location, and then select one of the following: **Items** or **LPNs**.
    -   View a grid with a link for an item, and then click the item.
2.  From the **Actions** drop-down list, select **Apply Hold**. The Apply Hold page is displayed with a list of existing hold definitions.
3.  To add a hold definition:
    1.  Click **Add Hold**.
    2.  Enter information in the [Holds fields](#Holds_fields).
    3.  If the **Apply to Inbound Inventory** field is set to Yes, then define the criteria for the inventory to which the hold will be automatically applied at the time of receipt:
        1.  Under **INBOUND PROCESSING**, click **Inventory Criteria**.
        2.  Enter information in the [Inbound Hold Criteria fields](#Inbound_Hold_Criteria_fields).
        3.  Click **Apply**.
    4.  Click **Save**.
4.  In the grid, select the hold to apply, and then click **Apply**. The Apply Hold window is displayed.
5.  Enter information in the following fields:
    
     
    | Field | Description |
    | --- | --- |
    | Change Inventory Status | Status to which the held inventory is changed. This field is only displayed if the **Inventory Status** field on the hold configuration is set to Yes. |
    | Change Only Certain Statuses | Indicates that the status for certain held inventory is to be changed based on its current status. If selected, then for each inventory status, in the **To Inventory Status** column, select the status to apply to the inventory. For example, you may only want to update the status for inventory that has an Available status, while keeping the remaining held inventory in its current status. This field is only displayed if the **Inventory Status** field on the hold configuration is set to Yes. |
    | Reason | Value that indicates why the hold is being applied. A reason is required whenever a hold is applied to inventory. |
    
6.  Click **OK**. A confirmation message is displayed.

**Note**: If the application was unable to apply the hold, then a list of the LPNs is displayed with the reason the hold could not be applied.

8.  Click **OK**.

## Release a hold from inventory

You can release a hold to remove the hold from the inventory.

1.  Perform one of the following tasks:
    -   View the Inventory page, select **On-Site**, and then perform one of the following tasks:
        
        1.  Select one of the following modules: **Inventory**, **Outbound Planner**, **Picking**, **Production**, **Receiving**, or **Shipping**.
        2.  Select **Inventory**.
        
        -   To release a hold from an item, select **Items**, and then in the grid, select the check box next to the item.
        -   To release a hold from inventory on a specific LPN, select **LPNs**, and then in the grid, select the check box next to the LPN.
        -   To release a hold from inventory in a specific location:
            1.  Select **Locations**.
            2.  In the grid, click the location. The location details are displayed.
            3.  Perform one of the following tasks:
                -   To release a hold to an item in the location, select **Items**, and then in the grid, select the check box next to the item.
                -   To release a hold to an LPN in the location, select **LPNs**, and then in the grid, select the check box next to the LPN.
    -   Select **Inventory > Holds**, and then perform the following tasks:
        1.  Select **Active Holds**.
        2.  Click a hold, and then select **LPNs**.
        3.  In the grid, select the check box next to the LPN, or click the LPN.
        
        **Note**: To release all inventory under an active hold, instead of selecting **LPNs**, select **Summary** and then from the **Actions** drop-down list, select **Release All Inventory**. The Release Hold page is displayed.
        
    -   View a grid with a link for a location, click the location, and then select one of the following: **Items** or **LPNs**.
    -   View a grid with a link for an item, and then click the item.
2.  From the **Actions** drop-down list, select **Release Hold**. The Release Hold page is displayed.
3.  Select the hold to release, and click **Apply**. The Release Hold window displays.
4.  Enter information in the following fields:
    
     
    | Field | Description |
    | --- | --- |
    | Change Inventory Status | Status to which the held inventory is changed. This field is only displayed if the **Inventory Status** field on the hold configuration is set to Yes. |
    | Change Only Certain Statuses | Indicates that the status for certain held inventory is to be changed based on its current status. If selected, then for each inventory status, in the **To Inventory Status** column, select the status to apply to the inventory. For example, you may only want to update the status for inventory that has an Available status, while keeping the remaining held inventory in its current status. This field is only displayed if the **Inventory Status** field on the hold configuration is set to Yes. |
    | Reason | Value that indicates why the hold is being applied. A reason is required whenever a hold is applied to inventory. |
    
5.  Click **OK**. A confirmation message is displayed.
6.  Click **OK**.

## Holds fields

 
| Field | Description |
| --- | --- |
| Enable Hold | If enabled, this hold can be applied to inventory, either through a manual process from a workstation or automatically, if it is configured to be applied to expected inbound inventory.<br > If disabled, the hold is not available for use and cannot be applied to inventory. If you create a hold with this field disabled, the hold is created in the **Disabled Holds** tab. |
| Source | Prefix applied to the hold number. The hold source is typically site specific, and it distinguishes the holds placed on inventory at one site from holds placed on inventory at another site. This field is display only, and is populated with a value from the warehouse configuration (either the **Default Hold Prefix** or, if that field is blank, the **Warehouse Name**). |
| Hold | Unique identifier for the hold definition. Hold numbers are applied to inventory identifiers to indicate that the inventory is on hold as described in the hold definition. Hold numbers can either be user defined or application generated when hold definitions are created. |
| Notes | Additional information related to the hold. You use this field, for example, to describe the purpose of the hold and when it was created. This field is for informational purposes only; it is not used by any process. |
| Description | Description of the hold that is displayed on the application windows and in reports. |
| Type | Code that defines the category to which this hold belongs. Typically, the hold type identifies the purpose of the hold. The hold type is used only for display and report purposes. |
| Severity | Hold severity categorizes a hold by how serious it is from an operational standpoint. The levels range from 1 to 5, with 1 being the most critical. Setting a severity determines the order in which the hold is displayed on the Inventory dashboard. |
| Reason | Value that indicates why the hold is being applied. A reason is required whenever a hold is applied to inventory, but this reason is used specifically when the application applies the hold automatically to new inventory. Only available when **Apply to Inbound Inventory** is set to Yes. |
| Inventory Status | If Yes, then at the time a user applies or removes the hold, the user can also change the inventory status.<br > If No, then the application prevents users from changing inventory status when the hold is either applied or removed.<br > **Note**: This field only affects whether a user can change inventory status during the hold application or removal process. This field does not impact whether a status change can be made (manually or automatically) after the hold is applied or removed. |
| Apply to Inbound Inventory | If Yes, then during receiving or identification, the application automatically applies the hold to inventory that matches the inventory criteria defined for the hold. If you select Yes, then you must also select a reason for applying the hold, and define the inventory criteria.<br > If No, the application does not automatically apply the hold to any inventory. |
| Allocation | If Yes, then when this hold is applied to inventory, it does not prevent the inventory from being allocated for an order. Select Yes if you allow inventory on hold to be allocated for an order.<br > If No, then when this hold is applied to inventory, it prevents the inventory from being allocated for an order. Select No if you want to prevent the inventory from being used to fulfill an order while the inventory is on hold. |
| Shipping | If Yes, then when this hold is applied to inventory, it does not prevent the inventory from being shipped from the warehouse. Select Yes if you allow inventory on hold to be shipped.<br > If No, then when this hold is applied to inventory, it prevents the inventory from being shipped. Select No if you want prevent the inventory from being shipped to a customer while the inventory is on hold. |
| Movement for RF Outbound Audit | If Yes, inventory placed under this hold during an outbound audit can be moved. Typically, inventory under an audit hold is not allowed to be moved to ensure that it is not loaded until the audit is successfully completed. However, supervisors may require the ability to move and adjust the held inventory while reconciling failed audits. Select Yes to allow the movement of inventory that is under this hold.<br > **Note**: To ensure that only authorized personnel can move held inventory, in addition to selecting Yes, you also must configure the user role options to give certain roles the ability to move inventory under a hold that allows movement. See [Roles](../../../administration/system-administrator/authorization/roles.md).<br > If No, inventory placed under this hold during an outbound audit cannot be moved, regardless of the role options that are assigned to the operator. |

## Inbound Hold Criteria fields

 
| Field | Description |
| --- | --- |
| Item | Unique identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). |
| Item Family | Identifier used to group similar items together. Typically, all of the items within a family have the same material handling characteristics. |
| Inventory ID | Identifier (LPN, sub-LPN, or detail LPN) for the inventory to be placed on hold. |
| Lot Number | Identifier assigned to a quantity of inventory that is uniquely identified during the manufacturing process for the purpose of tracking an attribute of that inventory, such as its expiration date. Lots differentiate distinct groups of inventory that have the same item. Lots are user defined and are not necessarily unique since the same lot can be applied to different items. However, lot and item number combinations must be unique. |
| Supplier Lot Number | Identifier that is an attribute of an item or item and lot combination and is assigned by the item's supplier. A supplier lot number used to uniquely identify and track the inventory to which it is assigned. The supplier lot number is a different attribute than the lot number, which is a manufacturer or production lot number. |
| Revision Level | Identifier that is assigned to an item number to differentiate revisions of the same item number. |
| Consignment ID | Unique identifier assigned to a receipt of bonded inventory. A customs consignment is an application-generated ID number that consists of a prefix (the warehouse ID) plus the next value in the customs consignment ID sequence. For example, if your warehouse ID is WMD1 and the next number in the sequence is 123456, then the customs consignment ID will be WMD1123456.<br > Only displayed if Customs functionality is enabled for the warehouse and the item is configured for customs tracking. |
| Rotation | Unique identifier that the application generates and automatically assigns to bonded inventory during receipt of that inventory into a bonded warehouse. The rotation ID is tracked with the inventory as long as the inventory is in the warehouse. |
| Client | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. |
| Origin | Identifier assigned to an item to identify the item's country of origin. It is typically used for export paperwork. Origin codes are user defined. |
| Status | Quality status of an item. Inventory statuses are uniquely defined for your application during the initial setup, and they can be used to identify the physical condition and availability of the inventory, or special material handling requirements for the inventory. |
| Manufacturing Date | Range of manufacturing dates of inventory to which the hold should be applied. The range includes both a date and time. The dates and times are stored in the database and displayed in the web client in the original captured time zone, not converted to a different time zone, such as a user preferred time zone. |
| Supplier | Identifier for a supplier. A supplier can be an individual, organization, or another warehouse within your own organization from which you repeatedly receive inventory or handling units. |
| Inbound Shipment | Unique identifier used for inventory tracking for an inbound shipment of inventory. An inbound shipment is a group of orders that are transported to the warehouse together or received together. When inventory arrives at the warehouse on a piece of transport equipment, an inbound shipment represents the contents of the transport equipment; however, one or more inbound shipments can be associated with a piece of transport equipment. |
| Planned Inbound Order | Identifier for a planned inbound order that is associated with a specific supplier. A planned inbound order is an authorization to receive specific inventory and quantities from a supplier. It is used, but not required, to receive inventory into the warehouse. |
| Work Order Number | Identifier for a work order. A work order is an internal order used to find, allocate, and deliver product to a work-in-process area for assembly or disassembly, conversion, kitting, or repackaging. |
| Work Order Revision | Identifier for one instance of a work order that allows you to use a standard work order multiple times. |
| Area | Identifier for an area. Areas are used for grouping and sorting locations in the warehouse. For example, an area named STAGING can be used to group ship staging locations; an area named CASEPICK can be used to group case pickface locations. |
| Storage Location | Name for a location within a warehouse used to store inventory and from which inventory can be picked. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
