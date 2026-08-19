---
title: "Outbound Customs"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/outbound_customs.htm"
source: "/content/outbound_customs.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Outbound"
  - "Shipping "
  - "Outbound Customs"
sections:
  - "Customs order types"
  - "Holds on customs consignment inventory"
  - "Allocation of bonded inventory"
  - "Hold on outbound inventory"
  - "Configure outbound customs"
  - "Customs Order Type Rules fields"
images: []
source_sha1: 04e93ff8c056adadf3c0643b8e27e4793c1d8819
---
# Outbound Customs

Outbound customs settings define how the application processes the shipment of bonded inventory.

## Customs order types

You can configure the customs order types that are assigned by default to an outbound order based on the selected site type for the warehouse and the destination. The duty management application uses customs order types to determine whether fees and taxes must be paid when bonded inventory is shipped.

**Note**: Customs functionality is used to manage bonded inventory. See [Bonded inventory](../../inbound/receiving/inbound-customs.md).

The customs duty that is paid on shipped inventory is country specific and is determined by the destination country of the shipment. For example, for inventory shipping from a warehouse, consider the following scenarios:

-   The order destination is within the country of origin and the customs order type is duty free. Therefore, the application should be configured to allocate duty-free inventory first. If there is no duty-free inventory, then bonded inventory can be used. For the purpose of customs declaration and release, the bonded and duty-free inventory can be included in the same shipping container.
-   The order destination is outside the country of origin and the customs order type is bonded. Therefore, the application should be configured to allocate inventory that is under bond. When there is no bonded inventory left, then duty-free inventory can be used. For the purpose of customs declaration and release, the bonded and duty free inventory should not be packed in the same shipping container. This is done because there are more rules that have to be followed to declare and release the bonded inventory.

You can configure a customs order type to allow or prevent mixing of bonded and duty free inventory in the same shipping container. When mixing is not allowed, then during packing, the application creates additional shipping containers as needed to ensure that bonded inventory is not packed in the same container as duty-free inventory.

## Holds on customs consignment inventory

When bonded inventory is received into the warehouse, it must not be shipped until its associated customs consignment has been successfully processed in the duty management application.

You can prevent bonded inventory from being allocated or shipped until the customs consignment has been processed by placing a hold on the inventory at the time the inventory is received. This can be done automatically by setting up a future hold (using the Customs Hold hold type) for all inventory that is under bond, or for inventory that matches certain criteria, such as a customs consignment or rotation ID.

When inventory that matches the hold definition is received, the hold is applied to it automatically. When the duty management application finishes processing a completed consignment, the custom holds are automatically removed from the inventory. If the duty management application fails to process a completed consignment, the custom holds are not removed from the affected inventory.

## Allocation of bonded inventory

A bonded warehouse contains inventory that is liable to excise and customs duties. The following process shows how components can be configured to support the allocation of appropriate inventory for orders shipped from a bonded warehouse:

-   Outbound orders
    -   The application assigns a customs order type to an outbound order based on the location of the warehouse (source) and customer (destination) of the order. The configuration of customs order types and rules determines how the application assigns a customs order type. The user can change the assigned order type. Outbound order lines can be configured to require under bond or duty stamp inventory, or inventory for a specific rotation ID. In addition, the allocation rules (simple or complex) assigned to the order line can also be based on those customs attributes.
-   Allocation search paths
    -   Search paths can be configured to find inventory that is under bond or to which a duty stamp has been applied. A customs order type can be assigned to a search path to indicate the type of order for which the search path is used.
    -   Search paths can be sequenced, for example, to first search pick zones where bonded inventory is stored, before searching elsewhere.

## Hold on outbound inventory

The shipping process for bonded inventory supports the tracking of the customs consignments and rotation identifiers. Through the configuration of a workflow at a specific exit point in the shipping process—picking, ship staging, transport equipment close, or dispatch—bonded inventory can be placed on Customs hold automatically. When processing by the duty management application is complete, the hold is automatically removed.

## Configure outbound customs

1.  Select **Configuration > Outbound > Shipping > Outbound Customs**.
2.  To define customs order types:
    
    **IMPORTANT**: The customs order types defined in Warehouse Management must match those defined in the integrated duty management application.
    
    1.  Click **Customs Order Types**.
    2.  Perform one of the following tasks:
        -   To add a customs order type, click **Add**.
        -   To modify a customs order type, in the grid, click the customs order type.
    3.  Enter information in the following fields:
        
         
        | Field | Description |
        | --- | --- |
        | Customers Order Type | Name of the order type used for customs processing. The name must match a customs order type defined in the duty management application. |
        | Description | Text that further describes the customs order type. |
        | Allow Mixing | If Yes, then the application allows packing bonded and duty-free in the same shipping container. Select Yes, for example, if the customs order type is used for destinations within the country of origin.<br > If No, then the application prevents packing bonded and duty-free inventory in the same shipping container. Instead, it creates additional shipping containers automatically for packing bonded and duty-free inventory in separate containers. Select No, for example, if the customs order type is used for destinations outside the country of origin and you want to keep bonded and duty-free inventory separate for the purpose of customs processing. |
        
    4.  Click **Apply**.
3.  To define the rules used to assign a customs order type to an outbound order:
    1.  Click **Customs Order Type Rules**.
    2.  Perform one of the following tasks:
        -   To add a rule, click **Add**.
        -   To modify a rule, in the grid, click the customs site type.
    3.  Enter information in the [Customs Order Type Rules fields](#Customs_Order_Type_Rules_fields).
    4.  To add, modify, or delete a site type or country type:
    
    -   For a customs site type, click **Maintain Customs Site Type**.
    -   For a destination site type, click **Maintain Destination Site Type**.
    -   For a country type, click **Maintain Customs Country Type**. 
    
    1.  Perform one of the following tasks:
        -   To add a type, click **Add**, and then in the **Customs Site Type**, **Description**, and **Short Description** fields, enter the values.
        -   To modify a type, in the grid, click the **Description** and **Short Description** fields, enter the values.
        -   To delete a type:
            1.  In the grid, select the check box next to the type to delete.
            2.  Click **Delete**. A confirmation message is displayed.
            3.  Click **Save**.
    2.  To define the sequence in which the type is applied, in the grid, click a row and drag it to the preferred position in the grid.
    3.  To translate a type:
        1.  Perform one of the following tasks:
            -   To translate specific rows, in the grid, select the check box of the rows, and then above the grid, click **Translation**.
            -   To translate all rows, above the grid, click **Translation**.
        2.  From the **Destination Locale** drop-down list, select the locale.
        3.  In the grid, select a translated description or short description, and then enter the new value.
        4.  Click **Save**.
    
    6.   Select the customs order types that can be assigned to an order based on the rule:
        1.  Perform one of the following tasks:
            -   To add an order type, click **Add,** and then from the **Customs Order Type** drop-down list, select the customs order type.
            -   To modify an order type, click the description.
        2.  To indicate that the customs order type is assigned by default to orders that have a source and destination matching this rule, set the **Default** field to Yes.
        3.  Click **Apply**.
    7.  To remove an order type from the list:
        1.  In the grid, select the check box next to the order type to remove.
        2.  Click **Delete**. A confirmation message is displayed.
        3.  Click **OK**.
4.  Click **Save**.

## Customs Order Type Rules fields

 
| Field | Description |
| --- | --- |
| Customs Site Type | Customs site type assigned to the address of the warehouse from which the outbound order is shipped. The site type indicates whether the warehouse is bonded, and if it is bonded, the type of bonded warehouse.<br>-   • **Customs**: The address is a bonded warehouse that contains inventory for which customs duties must be paid. Customs duties are assessed against goods (other than alcoholic beverages and tobacco products) that have been imported from the European Union (EU).
<br>-   • **Customs and Excise**: The address is a bonded warehouse that contains inventory for which both customs and excise duties must be paid. Excise duties are assessed against goods such as alcoholic beverages and tobacco products.
<br>-   • **No selection (blank)**: The address is not a bonded warehouse and only duty paid items can be received.
<br > Only available if the customs functionality is enabled. |
| Destination Site Type | Customs site type assigned to the address of the destination (customer) to which the outbound order is shipped. The site type indicates whether the warehouse is bonded, and if it is bonded, the type of bonded warehouse.<br>-   • **Customs**: The address is a bonded warehouse that contains inventory for which customs duties must be paid. Customs duties are assessed against goods (other than alcoholic beverages and tobacco products) that have been imported from the European Union (EU).
<br>-   • **Customs and Excise**: The address is a bonded warehouse that contains inventory for which both customs and excise duties must be paid. Excise duties are assessed against goods such as alcoholic beverages and tobacco products.
<br>-   • **No selection (blank)**: The address is not a bonded warehouse and only duty paid items can be received. |
| Customs Country Type | Country type assigned to the address of the destination (customer) to which the order is to be shipped. The country type is used to determine the type of customs and duties required by the country.<br>-   • **EU**: The country is a member of the European Union, but is not part of the United Kingdom.
<br>-   • **UK**: The country is a part of the United Kingdom. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
