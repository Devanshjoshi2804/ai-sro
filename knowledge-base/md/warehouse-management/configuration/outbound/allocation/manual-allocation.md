---
title: "Manual Allocation"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/manual_allocation.htm"
source: "/content/manual_allocation.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Outbound"
  - "Allocation"
  - "Manual Allocation"
sections:
  - "Order destination selection"
  - "Wave rules"
  - "Pre-defined wave rules"
  - "Configure manual allocation"
  - "Manual Allocation fields"
  - "Destination fields"
  - "Wave Rule fields"
images: []
source_sha1: b282b597bd7cbd241315c7c5dcbeab646bb453b8
---
# Manual Allocation

Manual allocation is a process that a user performs using the Outbound Planner or Picking module.

When you configure the settings for manual allocation, you define the following attributes:

-   Default ship staging movement zone that is applied to picked inventory to direct it to its final destination before being loaded onto transport equipment. The application uses the following order of precedence to determine the final destination:
    1.  Destination zone or location specified on the order line
    2.  Destination zone or location specified during shipment allocation
    3.  Ship staging movement zone or location specified by the configuration of order type, carrier, or item family
    4.  Default ship staging movement zone
-   The attributes and behavior of the Shipment Allocation Operations window, such as the information that can be displayed and whether carrier changes are allowed to be made during allocation.
    
    The application uses the following order of precedence to determine the carrier:
    
    1.  Order line
    2.  Carrier specified during allocation
    3.  Carrier specified after staging
-   How often the information on the Wave Operations window is refreshed, and the wave rules that are used to display orders and shipments that can be grouped for allocation. See [Wave rules](#Wave_rules).

## Order destination selection

During allocation, the application determines the destination movement zone or location to which picked inventory should be deposited.

Allocation attempts to use the destination that is defined on the order line, but if one is not defined, it attempts to use the destination selected during shipment allocation.

If a destination is not specified on the order line or during shipment allocation, then the application attempts to use a destination based on the settings defined for manual allocation. You configure manual allocation settings to direct the application to find a destination based on one of the following entities:

-   Order type that is specified on an order. This option is used to direct certain types of orders to a destination separate from other types of orders. An order type is user-defined category assigned to an order. See [Outbound Order Types](../order-processing/outbound-order-types.md).
-   Order type and carrier. This option is used to direct a certain type of order to different destinations based on the carrier assigned to the order line.
-   Carrier that is specified on the order line. This option is used to define destinations based on carrier. For example, orders destined for truckload (TL) or less than truckload (LTL) carriers may be routed to a standard shipping dock, while orders for parcel carriers are routed to a parcel processing zone where cartons are manifested and prepared for parcel shipping.
-   Item family that is specified on the order line. This option is used to direct picks to a destination based on item family. For example, frozen inventory may need to be routed to a staging lane with freezers, while dry inventory can be routed to any other staging lane. An item family is a user-defined category assigned to an item. See [Item Families](../../inventory/items/item-families.md).

## Wave rules

Wave rules are methods for manually selecting orders or shipments for a wave—they define how picking waves are planned. Wave rules are also used in the automatic planning and allocation of unplanned orders when configured with an automatic allocation method. See [Automatic allocation of unplanned orders](automatic-allocation.md).

A wave rule consists of the following components:

-   **Summary Command**: The server command that tells the application how to display the wave summary results. You can preview the shipments or orders that will be selected for the wave, as well as adjust the selection criteria to pick different orders or shipments than the ones originally chosen. For example, if you use the STD-ORDERSELECTION rule to plan a wave, once you enter the selection criteria you will be able to see the orders that will be included with the wave. This enables you to determine whether the selection criteria should be further modified to change the set of orders before actually processing the wave.
-   **Cancel Command**: The server command that tells the application what to do when a user cancels a wave. Wave cancellation needs to take into account the different cancel processing needs of each wave rule. For example, for a wave rule based on orders, the wave planning process automatically creates shipments for the orders planned into the wave. If such a wave is cancelled, not only does the wave itself need to be cancelled, but the underlying shipments that may have been created as part of the wave planning process are removed from the wave. To identify unique wave cancellation needs, the application keeps track of the wave rule used when planning the wave. The wave cancellation process looks at the rule used to plan the wave, and uses the associated cancel command to cancel the wave. If a shipment is in a wave and the wave is cancelled, the shipment remains but is not in a wave anymore.
-   **Fields**: The fields that can be used as selection criteria to group orders or shipments into a wave. For each parameter, you select one of the following types of data entry used to enter a value for the field:
    -   **List**: Lets the user type multiple values for the parameter separated by commas. For example, for the Ship-To Customer, you might want to select orders from more than one customer for the wave.
    -   **Normal**: Lets the user type, look up, or select an option from a list as the user normally would in other areas of the application.
    -   **Range**: Lets the user enter a beginning value and an ending value for the parameter. For example, for the Late Ship Date parameter, the user could enter a beginning date in the From Late Ship Date field and an ending date in the To Late Ship Date field.
-   **Actions**: The server commands that actually create the wave from the orders or shipments that the user has selected.
    
    If you know the application's server commands or how to create your own commands, you can add your own wave rules. If you know the application's database fields, you can add parameters to the existing wave rules. Otherwise, you can contact your Blue Yonder project team for more information on customizing your wave processing.
    

## Pre-defined wave rules

The application provides the following pre-defined wave rules:

-   **STD-DESTSELECTION**: Plans a wave by letting you enter destination criteria. Shipments matching the criteria are then planned into the wave. This wave rule is especially beneficial for facilities where it may be necessary to require two or more staging lanes for inventory to a single transport equipment because distinct item families (such as frozen, refrigerated, and dry goods) may require different staging lanes. Grouping picks by destination enables you to control the allocation and release of waves based on the amount of room at the dock door so that you can move all inventory for one transport equipment through the facility at the same time instead of distributing picks across multiple transport equipment.
-   **STD-ORDERSELECTION**: Plans a wave by letting you enter order line criteria. The selected order lines are then planned into shipments using the application's automatic shipment planning feature and based on your automatic shipment planning configuration settings. After creating shipments, the application assigns them to the wave.
-   **STD-PLANWAVE**: Plans a wave based on a wave set that is defined for the shipment. Orders must already be planned into shipments. This wave rule is especially beneficial to facilities that plan their waves in their host. The host can then set the Wave Set field on the shipment and communicate it to Warehouse Management.
    
    This rule is typically used when the wave set is consistent every week or every day. For example, every Monday morning you ship to 10 stores. The wave set is created and the host sends down this set of orders for the 10 stores in this wave set or the order planner manually plans these orders into a wave.
    
-   **STD-SHIPSELECTION**: Plans a wave by letting you enter shipment criteria. Shipments matching the criteria are then planned into the wave. This wave rule is especially beneficial to facilities that use a separate transportation management application, to plan orders into shipments.

## Configure manual allocation

1.  Select **Configuration > Outbound > Allocation > Manual Allocation**.
2.  Enter information in the [Manual Allocation fields](#Manual_Allocation_fields).
3.  To define a ship staging movement zone or location by order type, carrier, or item family:
    
    **Note**: The application uses this configuration when a destination is not specified on the order line or during shipment allocation or, if one has been specified, it is not available for use.
    
    1.  Under **ORDER DESTINATIONS**, from the **Select Type** drop-down list, select the entity to configure. A button is displayed for you to select destinations based on the selected entity.
    2.  Click **Order Type**, **Carrier**, or **Item Family**.
        
        **Note**: To specify a destination by order type and carrier, select **Order Type**. When you add or modify an order type, set the **Derive from carrier default destination** field to Yes. This indicates that the destination specified by the assigned carrier is used for the order type.
        
    3.  Perform one of the following tasks:
        -   To add a configuration, click **Add**.
        -   To modify a configuration, in the grid, click the order type, carrier, or item family.
    4.  Enter information in the [Destination fields](#Destination_fields).
    5.  Click **Apply**.
4.  To define rules for wave processing:
    
    **Note**: Wave rules are used during wave planning to find orders or shipments that match the selected rule and then group them for allocation. A standard set of wave rules is distributed. New rules are typically added by your Blue Yonder project team.
    
    1.  Click **Wave Rules**.
    2.  Perform one of the following tasks:
        -   To add wave rule, click **Add**.
        -   To modify a wave rule, in the grid, click the rule.
        -   To copy a wave rule, in the grid, select the check box next to the rule, and then click **Copy**.
    3.  Enter information in the [Wave Rule fields](#Wave_Rule_fields).
    4.  To define the selection criteria for building orders and shipments into a wave:
        1.  Click **Manage Fields**.
        2.  Perform one of the following tasks:
            -   To add a field, click **Add**.
            -   To modify a field, in the grid, click the field.
        3.  Enter information in the following fields:
            
            | Field | Description |
            | --- | --- |
            | Field | Fields that can be used as selection criteria to group orders or shipments into a wave. For each parameter, you can define how you want to let users enter the values for the selection criteria. |
            | Type | Method by which a user enters a value for the field.<br>-   • **List**: User can enter multiple values for the parameter separated by commas. For example, for the Ship-To Customer, you might want to select orders from more than one customer for the wave.
            <br>-   • **Normal**: User can type, look up, or select an option from a list as the user normally would in other areas of the application.
            <br>-   • **Range**: User can enter a beginning value and an ending value for the parameter. For example, for the Late Ship Date parameter, the user could enter a beginning date in the From Late Ship Date field and an ending date in the To Late Ship Date field. |
            
        4.  Click **Apply**.
    5.  To select the actions (commands) used to create the wave from the selected orders and shipments:
        1.  Click **Actions**.
        2.  To add an action, click **Add**, enter the action, and then click **Apply**.
        3.  To delete an action:
            1.  In the grid, select the check box next to the action.
            2.  Click **Delete**. A confirmation message is displayed.
            3.  Click **OK**.
5.  Click **Save**.

## Manual Allocation fields

 
| Field | Description |
| --- | --- |
| Default Ship Staging Zone | Ship staging movement zone to which picked inventory is directed when a destination has not been defined elsewhere or, if it has been defined, it is not available for use. The application attempts to find a destination movement zone or location for picked inventory in the following order of precedence:<br>-   • Destination zone or location defined on the order line
<br>-   • Destination zone or location defined during shipment allocation
<br>-   •
    
    Ship staging movement zone or location defined by the configuration of the **Override Default Ship Staging Zone** fields on the allocation Manual settings page. This configuration specifies a destination based on one of the following entities:
    
    <br>
    -   • Order type assigned to the order
    <br>-   • Order type and assigned carrier
    <br>-   • Assigned carrier
    <br>-   • Item family assigned to the inventory on the order line
    <br>
<br>-   • Destination specified in the **Default Ship Staging Zone** field. |
| Select Type | Type of entity for which you want to specify a default destination (ship staging movement zone or location) for picked inventory. The application uses this configuration only if a destination was not specified on the order line or during shipment allocation. If the application cannot find a destination based on this configuration, then it uses the destination specified in the **Default Ship Staging Zone** field.<br>-   •
    
    **By Order Type**: Used to directed certain types of orders to a destination separate from other types of orders. An order type is user-defined category assigned to an order. See [Outbound Order Types](../order-processing/outbound-order-types.md).
    
    <br>
    
    If you select **By Order Type**, then when configuring the default destination, you can derive the destination based on the carrier assigned to the order line for the selected order type.
    
    <br>
<br>-   • **By Carrier**: Used to define destinations based on the carrier assigned to the order line. For example, orders destined for truckload (TL) or less than truckload (LTL) carriers may be routed to a standard shipping dock, while orders for parcel carriers are routed to a parcel processing zone where cartons are manifested and prepared for parcel shipping.
<br>-   • **By Item Family**: Used to define destinations based on the item family of the inventory specified on the order line. For example, frozen inventory may need to be routed to a staging lane with freezers, while dry inventory can be routed to any other staging lane. An item family is a user-defined category assigned to an item. See [Item Families](../../inventory/items/item-families.md). |
| Use Pallet Estimate | If Yes, an estimate of pallet picks, volume, and number is displayed while planning a wave.<br > If No, the estimate of pallet picks is not displayed during wave planning. |
| Allow Destination Change | If Yes, users can change the destination zone for a shipment prior to allocating the shipment.<br > If No, users do not have the option to change the destination zone for a shipment during allocation. |
| View Order Notes | If Yes, you can view order notes after a wave is allocated. The orders and order lines that can be viewed are those configured to be displayed during allocation operations.<br > If No, order notes are not available after allocation. |
| Show Allocation Summary | If Yes, the allocation summary is displayed when allocation of a wave is complete. Select Yes to display the summary automatically following allocation<br > If No, the allocation summary is not displayed automatically following allocation. You may want to select No if your site performs numerous allocations and you want avoid having to view the summary for each one. |
| Allow Carrier Override | If Yes, users are allowed to change the assigned carrier when allocating a shipment.<br > If No, users are not allowed to change an assigned carrier during allocation operations. |
| Warn On Carrier Change | If Yes, then during shipment allocation operations, if the user changes the carrier assigned on the order line, a message is displayed asking the user to confirm the change.<br > If No, then users are not prompted to confirm a carrier change that is made during shipment allocation. |
| Apply Carrier Code to Unspecified | If Yes, users can specify a carrier prior to allocating a wave for shipments that do not have an assigned carrier.<br > If No, then during shipment allocation, users cannot specify a carrier for shipments that that do not have an assigned carrier. This field is typically set to No when a transportation management system (TMS) is used. The TMS plans the best carrier to use and does not allow the warehouse to override it. Without TMS, it may be a transportation group of users in the warehouse doing the planning of which orders go on which transport equipment and carriers. Once they do this manually planning, they do not want the order planner to change during allocation. |
| Refresh Timer | Time duration, in seconds, that indicates how often the application updates the status of the wave processing on the Wave Operations window. When the timer expires, the application refreshes the status of the displayed waves, for example, by updating a wave from a status of In Progress to Complete. If the value is 0, the window is not refreshed automatically, but can be refreshed manually. If the **Refresh Timer** field is blank, the default is 60. |
| Enable Allocation as a Service | If Yes, then Allocation as a Service is enabled to process inventory allocation for the warehouse for waves (outbound shipments) and replenishments. Allocation as a Service is a cloud-native service that is deployed outside of Warehouse Management and does not require the processing resources of the application instance. If enabled, the allocation process is separated from warehouse processing to ensure that allocation does not hinder performance and productivity in other functional areas of the application.<br > Allocation as a Service communicates with the application through public network APIs, which enables you to allocate orders using warehouse automation solutions. Enabling Allocation as a Service can increase allocation performance by automatically scaling computing resources based on the volume of orders to be allocated. As order volume increases, computing resources are automatically consumed to accommodate the rise in demand; as order volume decreases, computing resources are released.<br > **IMPORTANT**: Allocation as a Service should only be enabled for Blue Yonder Cloud customers. Contact Blue Yonder Services before changing the value of this field. If you set this field to Yes without a valid **Allocation Service URL**, then allocation errors will occur.<br > **Note**: If Allocation as a Service is enabled, then the number of allocation threads defined in the post allocation configuration is invalid. This is because Allocation as a Service processes allocation outside of the application and does not use the allocation threads.<br > If No, then Allocation as a Service is disabled, and inventory is allocated through traditional allocation processing in the application. |
| Allocation Service URL | Service URL for the Allocation as a Service instance to integrate with Warehouse Management for processing inventory allocation. If **Enable Allocation as a Service** is set to Yes, then a URL value must also be defined. Contact Blue Yonder Services for assistance with defining the service URL. |

## Destination fields

 
| Field | Description |
| --- | --- |
| Order Type | Name of an order type. An order type is a category that is used to group orders based on the warehouse processing necessary to fulfill the order. For example, customer orders and distribution orders require different processing by the application, and so an order type can be assigned to categorize each order separately. The application uses order types, for example, to identify orders that are eligible for bulk picking, or to direct orders to specific destination locations. |
| Derive from carrier default destination | If Yes, then for orders of this type, the destination is obtained based on the assigned carrier. When you set this field to Yes, the **Ship Staging Movement Zone** and **Ship Staging Location** fields become unavailable. In addition, when you apply the change, a check mark is added to the grid in the By Carrier column for this order type. Then, you can use the **Carrier** button on the Manual settings page to define the destination based on the assigned carrier.<br > If No, then you can select the default destination for the order type using the **Ship Staging Movement Zone** and **Ship Staging Location** fields.<br > This field is only available when setting a destination by order type. |
| Carrier | Identifier for a carrier that delivers inbound inventory to the warehouse or outbound shipments to a customer. This is the identifier that will be displayed to users on the application windows and reports. In the application, a carrier can be associated with a customer, order, inbound shipment, outbound shipment, load, and service levels (such as Ground, Next Day, and Saturday Delivery). |
| Item Family | Identifier used to group similar items together. Typically, all of the items within a family have the same material handling characteristics. |
| Ship Staging Movement Zone | Movement zone for staging picked inventory. This is the final destination to which outbound inventory is directed after being picked. |
| Ship Staging Location | Location for staging picked inventory. This is the final destination location to which outbound inventory is directed after being picked. |

## Wave Rule fields

 
| Field | Description |
| --- | --- |
| Wave Rule Name | Name of the wave rule. A wave rule is a method for selecting orders or shipments for a wave. |
| Description | Text that further describes the wave rule. |
| Summary Action | Server command that tells the application how to display the results in the Pre-Plan Summary window of Wave Operations. The Pre-Plan Summary window enables you to preview the shipments or orders that will be selected for the wave, and if desired, adjust the selection criteria to pick different orders or shipments than the ones originally chosen. For example, if you use the STD-ORDERSELECTION rule to plan a wave, once you enter the selection criteria you will be able to see the orders that will be included with the wave. This enables you to determine whether the selection criteria should be further modified to modify the set of orders before actually processing the wave. |
| Cancel Action | The server command that tells the application what to do when a user cancels a wave. Wave cancellation needs to take into account the different cancel processing needs of each wave rule. For example, for a wave rule based on orders, the wave planning process automatically creates shipments for the orders planned into the wave. If such a wave is cancelled, not only does the wave itself need to be cancelled, but the underlying shipments that may have been created as part of the wave planning process are removed from the wave. To identify unique wave cancellation needs, the application keeps track of the wave rule used when planning the wave. The wave cancellation process looks at the rule used to plan the wave, and uses the associated cancel command to cancel the wave. If a shipment is in a wave and the wave is cancelled, the shipment remains but is not in a wave anymore. |
| Change Carrier Level | Level at which a user can change the carrier assigned to a shipment during wave planning and processing.<br>-   • **Order**: Carrier can be changed for an order line before it is planned into a shipment. Select this option for rules used to display order lines for planning into waves, if you allow the carrier to be changed.
<br>-   • **Shipment**: Carrier can be changed for a shipment line. Select this option for rules used to display shipment lines for planning into waves, if you allow the carrier to be changed. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
