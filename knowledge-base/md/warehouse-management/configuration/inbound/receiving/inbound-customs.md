---
title: "Inbound Customs"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/inbound_customs.htm"
source: "/content/inbound_customs.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inbound"
  - "Receiving"
  - "Inbound Customs"
sections:
  - "Bonded inventory"
  - "Customs consignments"
  - "When to create a customs consignment"
  - "Auto-create consignments"
  - "Auto-complete consignments"
  - "Bonded inventory rotation IDs"
  - "Configure inbound customs"
  - "Receiving Customs fields"
  - "Default Consignment Configuration fields"
images: []
source_sha1: 054ce9e14ba04ebe868545e3443564944db770ec
---
# Inbound Customs

Inbound customs settings define how the application processes the receipt of bonded inventory.

## Bonded inventory

Bonded inventory is inventory for which customs duties and excise duties are required and have not yet been paid. This inventory is managed in a bonded warehouse, where it is received and stored pending its re-export, or release on assessment and payment of import duties, taxes, and other charges.

A bonded warehouse may hold goods liable to the following duty types:

-   **Excise duty**: Tax on specific types of products, such as alcoholic beverages and tobacco. The rates for excise taxes are set by the national government and are different in each European Union (EU) member state.
-   **Customs duty**: Tax on products imported into the EU. It is usually a percentage of the overall value of a product including costs such as freight and insurance. Rates for this tax are set on an EU-wide basis. When products are cleared (duty paid) in one EU country, they are considered duty free when circulated to other member states.

A bonded warehouse requires strict control over bonded inventory, including the ability to track inventory by certain customs attributes and provide the required customs documentation. If customs functionality is enabled for the warehouse, then the application supports the receipt, capture, and maintenance of all necessary information for bonded inventory and provides that information to an integrated duty management application.

## Customs consignments

A customs consignment is set of customs-related information that is associated with a specific planned inbound order or an assembly-type work order of bonded inventory. In a 3PL environment, if the planned inbound order contains lines for different clients, then a consignment must be created for each client on the order and associated with the order lines for that client.

A customs consignment is required for all bonded inventory that is identified into a customs-enabled warehouse. The application uses consignment information to report the receipt of bonded inventory to an integrated instance of a duty management application. After all of the inventory associated with a planned inbound order is identified into the warehouse, the customs consignment for the order can be completed, which sends the order to a duty management application for processing.

## When to create a customs consignment

A customs consignment can be created manually before receiving starts. You assign the customs consignment to a planned inbound order or to an assembly work order. A customs consignment can also be created manually during the receiving process, if your application configuration allows it, using a workstation or RF device. Using this method, the consignment is associated with the planned inbound order or order line during receiving.

If configured to do so, the application can also automatically create consignment information whenever a customs type is specified on a planned inbound order, on a work order, or on an item listed on an order. See [Configure inbound customs](#Configure_inbound_customs).

## Auto-create consignments

You can configure the clients for which the application automatically creates consignment information when a customs type is specified on a planned inbound order, a work order, or an item listed on an order. If you enable this feature, you can define the default values that the application uses to create the customs consignment.

## Auto-complete consignments

You can configure the application to automatically complete a customs consignment when all of the inventory for the consignment is identified. When a consignment is completed, data can be immediately sent to a duty management application for processing so the inventory can be made available to fulfill outbound orders. By using auto-complete consignment functionality, you do not have to wait for the consignment to be manually completed or for the inbound shipment to be closed.

For example, if an inbound shipment contains bonded inventory and free inventory (no consignment needed), a consignment is automatically completed when an operator has identified all of the expected inventory for the consignment, regardless of whether there is other inventory on the inbound shipment that needs to be received.

The auto-complete consignment functionality does not apply when a consignment is over-received or under-received. If auto-complete is enabled and an operator attempts to over receive inventory for a consignment, the operator is prompted with an error and can attempt to receive the correct quantity again. If the quantity identified for a consignment is short, the application does not complete the consignment and no data is sent to the duty management application; instead, the consignment can be completed manually, or the application automatically completes it when the inbound shipment is closed.

## Bonded inventory rotation IDs

A bonded inventory rotation ID is a unique, application-generated identifier that is automatically assigned to bonded inventory when it is received into the warehouse. The rotation ID is tracked as an attribute of inventory as long as the inventory is in the warehouse. A unique rotation identifier is associated with a single bonded item on an inbound shipment when the item is received into the warehouse.

Valid values include numerals from 000000 to 999999 and alpha characters from AAAAAA to ZZZZZZ. The application increments each decimal place 0-9 and then A-Z before increasing to the next decimal place according to the base 36 numbering system.

The format of a rotation ID is YY/X000zzz:

-   YY = The last two digits of the current year. For example, YY = 16 for the year 2016.
-   X = Value that indicates whether the inventory is under bond. If X = 0, the inventory is under bond.
-   000aaa = A 6-character alphanumeric identifier. This is the value that is generated automatically based on the minimum and maximum values that are specified for the warehouse.

The application uses the following process to determine the rotation ID to assign to inventory:

1.  If a planned inbound order line is created with the same customs consignment, planned inbound order number, planned inbound order line number, item, batch, and expiration date, and all other attributes are identical other than the quantity for inventory already received on the same day, then the rotation number is the same for both pieces of inventory. This applies to all custom planned inbound order types.
2.  If blind receiving is performed for bonded inventory, the user is required to enter a planned inbound order number. If the planned inbound order matches a previous planned inbound order on the same day with the same planned inbound order line number, then the rotation number is taken from the older inventory.
3.  If no matches are found for steps 1 or 2 of this process, then the application determines whether there is an existing rotation ID that can be used that matches the inventory.
4.  If no matches are found for steps 1 through 3, then the application generates a new rotation ID.

## Configure inbound customs

1.  Select **Configuration > Inbound > Receiving > Inbound Customs**.
2.  Enter information in the [Receiving Customs fields](#Customs_fields).
    
    **Note**: **Auto Create Customs Consignment**, **Customs Type Required on Inbound Order Lines**, and **Customs Type Required on Work Orders** display as Yes/No fields in a non-3PL environment.
    
3.  For a 3PL environment, to select the clients for which consignments are created automatically for inbound order lines and work orders that have a customs type specified:
    1.  Click **Auto Create Customs Consignment**.
    2.  In the **Available** column, select the check box next to the clients that apply.
    3.  If you want consignments to be created automatically for a client, set the **Enabled** field to Yes.
    4.  Click **Apply**.
4.  For a 3PL environment, to specify the clients that require a customs type on inbound order lines:
    1.  Click **Customs Type Required on Inbound Order Lines**.
    2.  In the **Available** column, select the check box next to the clients that apply.
    3.  If the selected client requires a customs type on inbound order lines, set the **Enabled** field to Yes.
    4.  Click **Apply**.
5.  To define the default attributes of a customs consignment that is created automatically for inventory received from specific suppliers:
    1.  Click **Default Consignment Configuration for Suppliers**.
    2.  Perform one of the following tasks:
        -   To add a default consignment configuration, click **Add.**
        -   To modify a default consignment configuration, in the grid, click the client or supplier.
        -   To copy a default consignment configuration, in the grid, select the check box next to the client or supplier, and then click **Copy**.
    3.  Enter information in the [Default Consignment Configuration fields](#Default_Consignment_Configuration_fields).
        
        **Note**: The clients list displays only in a 3PL environment. In a non-3PL environment only the list of available suppliers display. When you select **Inbound Order** as **Default Type**, and then select a client, the available supplier list refreshes to show the suppliers associated with that client. If you select **All Clients**, then the available supplier list displays all suppliers with the associated clients. Each client can be associated with multiple suppliers.
        
    4.  To select the suppliers that use the default consignment configuration:
        1.  Click **Supplier**.
        2.  In the **Available** column, select the check box next to the suppliers that apply.
        3.  Click **Apply**.
    5.  Click **Apply**.
6.  For a 3PL environment, to select the clients that require a customs type on assembly-type work orders:
    1.  Click **Customs Type Required on Work Orders**.
    2.  In the **Available** column, select the clients.
    3.  If the selected client requires a customs type on assembly-type work orders, set the **Enabled** field to Yes.
    4.  Click **Apply**.
7.  To select the suppliers for which a customs consignment should be automatically closed when all of the consignment inventory has been identified:
    1.  Click **Auto Close Consignment**.
    2.  Perform one of the following tasks:
        -   To add a client or supplier, click **Add.**
        -   To modify a client or supplier, in the grid, click the client or supplier.
    3.  From the **Client** drop-down list, select the client.
        
        **Note**: The clients list is displayed only in a 3PL environment. In a non-3PL environment only the list of available suppliers is displayed. When you select a client, the available supplier list refreshes to show the suppliers associated with that client. If you select **All Clients**, then the available supplier list displays all suppliers with the associated clients. Each client can be associated with multiple suppliers.
        
    4.  In the **Available** column, select the check box next to the suppliers that apply.
    5.  If the selected supplier requires customs consignments to automatically close when all of the consignment inventory has been identified, set the **Enabled** field to Yes.
    6.  Click **Apply**.
        
        **Note**: In the grid, a check mark indicates that auto-close consignment is enabled for the supplier.
        
8.  Click **Save**.

## Receiving Customs fields

 
| Field | Description |
| --- | --- |
| Enable Customs | If Enabled, customs processing is enabled for the warehouse.<br > If Disabled, customs processing is not enabled for the warehouse. You can still configure customs settings, but they will not take effect unless this field is set to Enabled. |
| Allow Putaway Before Duty Management Processing Is Complete | If Yes, then users are allowed to put away inventory before a confirmation that processing of the consignment has been completed has been received from an integrated duty management application. When a customs consignment is complete, it is sent to the duty management application for processing. When the inventory associated with the customs consignment is successfully processed by the duty management application, the status of the consignment changes from Complete to Duty Processed. Set this field to Yes if you allow inventory to be put away in spite of the consignment's processing status. If you use a duty hold and you put the inventory away, the hold remains on the inventory until it is released by the duty management application.<br > If No, putaway of inventory for a consignment is automatically held until a confirmation is received from the duty management application indicating that processing of the consignments has completed. |
| Allow Customs Consignment Creation at Receipt | If Yes, users are allowed to create a customs consignment during receiving. When this field is set to Yes, then during receiving the user is prompted to enter the customs consignment information for bonded inventory.<br > If No, the customs consignment must be created manually before inventory is received. |
| 16.3 Format for UCR Required | If Yes, the value for a unique consignment reference (UCR) must be entered in the 16.3 format. The UCR is specified for a customs consignment when the customs inbound order type for the consignment is From Importation. If this field is set to Yes, then the value for UCR must be 16.3, which consists of 12 alphanumeric characters, a dot (.), and then 3 numeric characters.<br > If No, the UCR can be in any other format except 16.3. |
| Auto Create Customs Consignment | If Yes, the application automatically creates consignment information when a customs type is specified on a planned inbound order, a work order, or an item listed on an order. You can define the default values that the application uses to create the customs consignment using **Default Consignment Configuration for Suppliers**.<br > If No, you must create customs consignment manually before receiving starts. |
| Customs Type Required on Inbound Order Lines | If Yes, the application requires a customs type specified on a planned inbound order line during receiving. You can configure the client for which the application requires a customs type specified on a planned inbound order or order line. If no customs type is specified (Customs, Excise, or Free) on the order or order line, the user will not be able to complete receiving. Defining a customs type on a planned inbound order overrides the customs type defined for the items.<br > If No, the application does not require a customs type specified on a planned inbound order line during receiving. |
| Customs Type Required on Work Orders | If Yes, the application requires a customs type specified on a work order when processing begins. You can configure the client for which the application requires a customs type to be defined on a work order for assembly work orders. If no customs type is specified (Customs, Excise, or Free) on the work order, the operator will not be able to start processing. Defining a customs type on a work order overrides the customs type defined for the component items.<br > If No, the application does not require a customs type specified on a work order when processing begins. |
| Minimum | Six-character alphanumeric value that represents the lowest value at which a rotation identifier can be created for this warehouse. A unique rotation identifier is associated with a single bonded item on an inbound shipment when the item is received into the warehouse. The range that you define using the **Minimum** and **Maximum** fields is the range that is used for one year; when a new year begins, the application starts with the minimum value again. Valid values include numerals from 000000 to 999999 and alpha characters from AAAAAA to ZZZZZZ. As the application creates new values, it increments each decimal place 0-9 and then A-Z before increasing the next decimal place, otherwise known as the base 36 system. |
| Maximum | Six-character alphanumeric value that represents the highest value at which a rotation identifier can be created for this warehouse. A unique rotation identifier is associated with a single bonded item on an inbound shipment when the item is received into the warehouse. The range that you define using the **Minimum** and **Maximum** fields is the range that is used for one year; when a new year begins, the application starts with the minimum value again. Valid values include numerals from 000000 to 999999 and alpha characters from AAAAAA to ZZZZZZ. As the application creates new values, it increments each decimal place 0-9 and then A-Z before increasing the next decimal place, otherwise known as the base 36 system. Only displayed if customs functionality is enabled for the warehouse. |

## Default Consignment Configuration fields

 
| Field | Description |
| --- | --- |
| Default Type | Type of order to which the consignment configuration applies.<br>-   • **Work Order**: Production work order used to assemble a top-level item. If you select Work Order, then all clients and suppliers are selected by default.
<br>-   • **Inbound Order**: Planned inbound orders received from an external source. |
| Client | Identifier for the client associated with the default consignment configuration. When inventory is received from the specified supplier for the client selected in this field, the application applies the default configuration attributes to the customs consignment. |
| Supplier | Identifier for a supplier. A supplier can be an individual, organization, or another warehouse within your own organization from which you repeatedly receive inventory or handling units. |
| Custom Inbound Order Type | Inbound order type that is on the customs paperwork for the transport equipment.<br>-   • **From EU States**: The order originated from another country in the European Union (EU), and the current warehouse is in the EU.
<br>-   • **From Importation**: The order originated from a country outside the EU, and the current warehouse is within the EU.
<br>-   • **Gains in Store**: The order is for an adjustment in the quantity of existing inventory.
<br>-   • **Other Sources**: The order originated from a source not identified by other inbound order types; for example, from an adjustment or production line.
<br>-   • **Other UK Warehouses**: The order originated from another warehouse in the United Kingdom. |
| CWC | Country Whence Consigned. Country from which the goods were initially dispatched to the importing country without any commercial transaction occurring in intermediate countries. |
| Originator | Identifier of the entity (such as the manufacturing plant) that, by contract with a carrier, consigns or sends goods with the carrier, or has them conveyed by a carrier. |
| Customs Status | Status of the customs consignment:<br>-   • **Complete**: Receiving has been completed in Warehouse Management, and the consignment has been sent to a duty management application for processing.
<br>-   • **Duty Processed**: The consignment was successfully processed by a duty management application.
<br>-   • **Pending**: The consignment has not completed receiving in Warehouse Management and therefore has not been sent to a duty management application for processing. |
| Originator Reference | Identifier, such as production reference number, provided by the originator. |
| From SFD if CFSP Entry Done | Unique consignment reference (UCR). An identifier obtained from the Simplified Frontier Declaration (SFD) form and required if a Customs Freight Simplified Procedures (CFSP) entry was done. If the customs configuration requires the 16.3 format, then you must enter the UCR in a format of 12 alphanumeric characters with a dot, and then 3 numeric characters; otherwise, the UCR can be any other format except 16.3 (including blank). |
| Note Text | Additional status information or special instructions related to the consignment. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
