---
title: "Outbound Loading"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/outbound_loading.htm"
source: "/content/outbound_loading.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Outbound"
  - "Shipping "
  - "Outbound Loading"
sections:
  - "PARS number configuration"
  - "Fluid loading"
  - "Configure outbound loading"
  - "Outbound Loading fields"
images:
  - "/content/resources/images/back_wmconfig_22x20.png"
source_sha1: 434a9d739da30e95f2f32eaaf910f618cba26d17
---
# Outbound Loading

Loading is the process of moving picked and staged inventory onto transport equipment for outbound shipment.

## PARS number configuration

When you configure loading, you can select the destination countries that require a Pre-Arrival Review System (PARS) number on loads being shipped on the selected transport mode. A PARS number, typically provided by the host, allows for advance processing by customs before goods arrive. If a PARS number is required and a load does not have one, the application prevents closing the transport equipment.

## Fluid loading

Fluid loading allows picked inventory to be loaded directly onto transport equipment (typically from storage or other pick zone) without being staged.

You can enable fluid loading for a specific building and for the service level and carrier type for each carrier that you want to load in this way.

Even with fluid loading enabled for the building and for the carrier's service level and carrier type, picked inventory must still meet the following requirements before the application will bypass staging and direct the inventory to be deposited from storage directly onto waiting transport equipment:

-   The source location of the picked inventory must be something other than a ship staging location.
-   The destination location of the picked inventory must be a ship staging movement zone or location.
-   The stop sequence defined for the picked inventory must match the current stop for the transport equipment.
-   The load and transport equipment defined for the picked inventory must match the transport equipment that is checked in to a dock door.

## Configure outbound loading

1.  Select **Configuration > Outbound > Shipping > Outbound Loading**.
2.  Enter information in the [Outbound Loading fields](#Outbound_Loading_fields).
3.  To enable fluid loading in buildings:
    1.  Under **FLUID LOADING**, click **Buildings**.
    2.  Under **Available**, select the check box next to the buildings in which you allow fluid loading.
    3.  Click **Apply**.
4.  To enable fluid loading for carrier service levels:
    1.  Under **FLUID LOADING**, click **Carrier Settings**.
    2.  Select the check box next to the carrier service.
    3.  From the **Actions** drop-down list, select **Enable Fluid Loading**.
    4.  Click ![Previous page](../../../../../images/resources/images/back_wmconfig_22x20.png).
5.  To select the criteria that must match for shipments to be consolidated into a single stop:
    1.  Under **PERFORMING THE LOAD**, click **Consolidation Criteria for Stops.**
    2.  Under **Available**, select the check box next to the attributes that must match for shipments to be included on the same stop.
    3.  Click **Apply**.
6.  To select the countries that required a PARS number for one or more transport modes:
    1.  Under **COMPLETING THE LOAD**, click **PARS Number Configuration**.
    2.  Perform one of the following tasks:
        -   To add a PARS number configuration, click **Add**, and then in the **Transport Mode** and **Country** fields, enter the values.
        -   To modify a transport mode, in the grid, click the transport mode, and then in the **Transport Mode** and **Country** fields, enter the values.
    3.  Click **Apply.**
7.  To define the LPN activities that are to be tracked and displayed on the Shipped LPN Activity page, based on the information sent from the host:
    
    **Note**: Even if no LPN activities are defined, the application still displays the information it receives from the host. However, there are no descriptions for the activities; only the code values for the activities received in the host transaction are displayed.
    
    1.  Under **SHIPPED LPN ACTIVITY**, click **LPN Activities**.
    2.  Click **Add**, and then in the **LPN Activity**, **Description**, and **Short Description** fields, enter the information.
        
        **Note**: The value for **Description** is displayed on the Shipped LPN Activity page, whereas the **LPN Activity** field represents the code also used by the host to identify the activity.
        
    3.  To translate the descriptions of LPN activities:
        
        1.  Perform one of the following tasks:
            
            -   To translate specific rows, in the grid, select the check box of the rows, and then above the grid, click **Translation**.
                
            -   To translate all rows, above the grid, click **Translation**.
                
        2.  From the **Destination Locale** drop-down list, select the locale.
            
        3.  In the grid, select a translated description or short description, and then enter the new value.
            
        4.  Click **Save**.
            
    4.  Click **Apply**.
8.  Click **Save**.

## Outbound Loading fields

 
| Field | Description |
| --- | --- |
| Directed Work | If Yes, then once a shipment is staged and associated with a load that is assigned to the transport equipment parked at a dock door, the application will automatically create work to load the equipment.<br > If No, then directed work is not created. Select No if you plan to load transport equipment without the use of an RF device or if RF devices are used to perform loading using undirected work. |
| Completion | Determines how a stop is completed after all loads for a stop are entered on the RF load screen. You may want to manually control stop completion to allow for a quality assurance check, to load additional inventory, or to assign stop seals. Whether you manually complete the stop or prompt the operator to do so can depend on whether you want to assign stop seals or produce additional paperwork. A stop cannot be closed until all expected inventory for the stop has been loaded.<br>-   • **Do not allow operator to complete the stop.** The operator is not prompted to complete stops or enter stop seals; these tasks must be done using a workstation.
<br>-   • **Prompt operator to complete the stop and enter seals.** After all LPNs for the stop are entered on the RF load screen, the operator is prompted to complete the stop and is then prompted for the stop seal.
<br>-   • **Automatically complete the stop and prompt operator to enter seals.** After all LPNs for the stop are entered on the RF load screen, the operator is prompted for the stop seal only, and is not prompted to complete the stop; the stop is completed automatically. |
| Loading Order | Order in which stops are loaded onto transport equipment.<br>-   • **By building first, then in stop order**. When operators load transport equipment and identify the inventory loaded using an RF device, stops are loaded by building. For example, if orders for a load are picked and loaded from different buildings, the inventory in building 1 could be for stops 1, 3, 4, and 6 and the inventory in building 2 could be for stops 2 and 5. By allowing the user to load inventory out of stop order, the inventory from building 1 can be loaded on the transport equipment, and the transport equipment can be moved to building 2 to complete the loading of the remaining stops. In order to do this, the transport equipment needs to be partially unloaded in building 2 so that the inventory in building 2 can be loaded in the correct positions on the trailer.
<br>-   • **In stop order**. When operators load transport equipment, they are directed to load it in stop order regardless of the building in which the inventory for the stops are located. |
| Single Scan Loading | If Yes, the operator is not required to confirm each individual LPN to load it. Instead, when the operator has picked up multiple LPNs to be loaded, the Loading Deposit screen displays "MANY" in the LPN field. When the operator scans the dock location, all the LPNs are loaded at once.<br > If No, the operator is required to confirm each individual LPN to load it. If this field is set to No, then when an operator has picked up multiple LPNs to be loaded, the Loading Deposit screen displays one of the LPNs in the LPN field. When the operator scans the dock location, the LPN is loaded. The Loading Deposit screen then displays the next LPN and dock location. The operator presses Enter to accept the dock location and load the LPN, and then continues to accept the dock location to load each of the remaining LPNs one at a time. The LPN field remains active, allowing the operator to enter a different LPN to load rather than the displayed LPN. |
| LTL Loads | If Yes, a less than truckload (LTL) shipment may be split so that it can be loaded onto different transport equipment. This is useful when an operator is loading transport equipment and realizes that the entire shipment will not fit on the transport equipment.<br > **Note**: Even if you allow users to split LTL shipments, if the **Partial** field is set to No on any order line of a shipment, then the application does not allow the shipment to be split. All order lines for a shipment must have the **Partial** field set to Yes for any of the order lines to be split onto a new shipment.<br > If No, an operators are not allowed to split an LTL shipment. |
| Allow Only GUI | If Yes, then less than truckload (LTL) shipments can only be split using the web client user interface, not an RF device.<br > If No, then shipments on LTL shipments can be split using the web client user interface or an RF device.<br > Only available if **LTL Loads** is set to Yes. |
| Commit During Unloading | If Yes, then the application commits picks and corresponding pick moves to the database individually during the unloading process for a stop. In facilities that routinely unload large stops in this manner, committing the changes during unloading can help eliminate database performance issues for other users while the stop is being unloaded.<br > If No, then the application commits all picks and pick moves in a single transaction after the entire stop has been unloaded.<br > **Note**: The unloading process is initiated on an RF device or by using an API. |
| Delivery Sequence Loading Order | Determines whether inventory should be loaded in ascending or descending order of the delivery numbers and delivery sequence defined for the orders in a stop. For example, assume a stop includes four orders, two with a delivery number of A1 and two with a delivery number of B1. Also assume that the orders for both A1 and B1 have a delivery sequence of 1 and 2. If this field is set to Descending, then the orders are loaded in the following sequence: B1 2, B1 1, A1 2, A1 1. See [Delivery sequence loading](../../../outbound-planner/outbound-planning-concepts.md).<br > **Note**: The delivery sequence loading order defined for a shipment overrides the client value, which overrides the warehouse value. However, if there is no selection (blank) in the Delivery Sequence Loading Order field on a shipment, the value is inherited from the outbound loading settings or, in a 3PL environment, the client configuration.<br>-   • **Ascending**: Operators are directed to load orders from the lowest to the highest value of the delivery number and delivery sequence defined on the orders (for example, 0 to 9 or A to Z).
<br>-   • **Descending**: Operators are directed to load orders from the highest to the lowest value of the delivery number and delivery sequence defined on the orders (for example, 9 to 0 or Z to A).
<br>-   • **Disabled**: The application does not enforce sequence loading, and orders can be loaded in any sequence.
<br > **Note**: To ensure proper loading, all shipments within a stop should have the same delivery sequence loading order. |
| Commit During Loading | If Yes, then when loading an entire stop in one action, the application commits each pick and its corresponding pick moves to the database after each LPN is loaded. In facilities that routinely load large stops in this manner, committing the changes in separate transactions during loading can help eliminate database performance issues for other users while the stop is being loaded.<br > If No, then the application commits picks and pick moves to the database after the entire stop is loaded.<br > **Note**: If pallets are loaded individually, then this field has no effect and pick transactions are committed individually. |
| Automatically Close Transport Equipment | If Yes, the RF Close Transport Equipment screen will not be displayed, and the transport equipment will be closed automatically after all stops are completed (whether using fluid loading or not).<br > If No, the RF Close Transport Equipment screen is displayed for the RF operator to close the transport equipment. |
| Automatically Dispatch Transport Equipment | If Yes, then the application will automatically dispatch the transport equipment after the equipment is closed.<br > If No, then you must manually dispatch the transport equipment. You may want to manually dispatch the equipment manually if you require a supervisor to approve the dispatch. |
| Tractor | If Yes, then when transport equipment is checked out of the yard, it must have an assigned tractor with a status of At Site. If the assigned tractor's status is not At Site or a tractor is not assigned to the transport equipment, you cannot check out the equipment.<br > If No, then transport equipment can be checked out regardless of whether it has an assigned tractor. However, if a tractor is assigned to the transport equipment, it must be in a status of At Site before you can check out the equipment. |
| Ship Load Event Logging Deferred | If Yes, then the execution of the Ship Load event (including the logging of Ship Load transactions) is deferred until post trailer dispatch processing. The transactions are instead saved to a deferred execution database table to be logged at a later time. This helps ensure that trailer dispatch is not delayed while the transactions are logged.<br > If No, then the Ship Load event is immediately sent to the host during trailer dispatch processing. |
| LPN Level | LPN level at which the application logs the initial activity for when inventory is shipped from the warehouse. For example, if LPN is selected, then when an LPN is shipped, the application logs the activity and displays the record on the Shipped LPN Activity page for the purpose of LPN tracking. Select the check box next to each level for which the application should log an activity when inventory is shipped.<br > **Note**: If none of the LPN levels are enabled to be logged by the application when they are shipped, the application can still receive and display subsequent activity information sent from the host. |
| Instance Level Visibility | If Yes, the Shipped LPN Activity page displays LPN activities for all of the warehouses in the instance.<br > If No, the Shipped LPN Activity page only displays LPN activities for the current warehouse.<br>
**Notes**:

<br>

-   • The permissions for a user are taken into account as they relate to client access. For example, if a user is restricted to viewing information only for Client A and the host sends an update for Client B, then the record is not displayed to that user.
<br>-   • The host system is responsible for sending correct warehouse values to the application to be displayed; the application does not validate any of the data that is received through the inbound transaction. If this field is set to No, and if the warehouse identifier is populated incorrectly in the transaction or not at all, then the activity will not be displayed because it does not match the current warehouse. If this field is set to Yes, then all activities are displayed regardless of whether the warehouse identifier in the transaction matches one defined in the application.
<br>

 |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
