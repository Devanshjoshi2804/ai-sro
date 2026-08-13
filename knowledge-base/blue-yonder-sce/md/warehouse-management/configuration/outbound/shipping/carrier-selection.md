---
title: "Carrier Selection"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/carrier_selection.htm"
source: "/content/carrier_selection.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Outbound"
  - "Shipping "
  - "Carrier Selection"
sections:
  - "Carrier selection setup"
  - "Carrier selection rule scenario"
  - "Automatic carrier selection process"
  - "Configure carrier selection rules"
  - "Selection Rule fields"
images: []
source_sha1: 366928c5c6219fa480b8f1e006353add8604e4f3
---
# Carrier Selection

Carrier selection is an automatic process in which the application assigns a carrier to a shipment based on the attributes of the shipment. If selection rules are enabled, the automatic assignment of a carrier to a shipment takes place at the time the shipment is created, if it is created without a carrier.

The assignment is based on the application's search of selection rules in sequential order to find a rule with selection criteria that matches the shipment attributes. The assignment is made when it finds a rule that matches a carrier to a shipment.

The attributes of a selection rule can include item family, order type, ship-to customer, weight or volume of the shipment, quantity of pallets, cases, or eaches in the shipment, and destination location attributes (country, region, postal code, and postal range). You can add other attributes as needed to configure the rules.

If the application is integrated with a parcel application through Parcel Handler, you can configure a rule for retrieving a carrier from the integrated parcel application. See [Parcel address validation and carrier selection](parcel.md).

## Carrier selection setup

The following tasks are required to configure automatic carrier selection:

1.  Configure selection rules.
    
    1.  Enable the carrier selection rules if you want the automatic process to take place.
    2.  Enable additional fields (attributes) for selection criteria, if needed. Attributes associated with the shipment, order, items, and address can be enabled for use.
    3.  Add or modify selection rules.
    4.  Arrange the selection rules in the sequence that you want the application to search them for attributes that match the shipment that needs a carrier.
        
    
    See [Configure carrier selection rules](#Configure_carrier_selection_rules).
    
2.  Enable the Execute Carrier Matrix (EXEC-CAR-MTX) background workflow that executes the automatic carrier selection process using the GET CARRIER CODE PREFERENCE command at the time a shipment is created. See [Background Workflows](../../work/warehouse-workflows/background-workflows.md).
    
    **Note**: If the Execute Carrier Matrix background workflow is enabled, then the GET CARRIER CODE PREFERENCE command is executed at shipment creation through wave planning only if the Shipment Created exit point is selected. However, if a user manually creates a shipment and assigns an order line to it, then the GET CARRIER CODE PREFERENCE command is executed regardless of whether the Shipment Created exit point is selected.
    

## Carrier selection rule scenario

The following example shows how the application processes selection rules to find a carrier and service level to transport a shipment with matching attributes.

**Example**: A shipment has the following attributes:

-   Ship-to postal code: 23005
-   Weight: 100 pounds

The following table shows the selection rules that have been defined.

     
| Sequence | Carrier | Carrier service level | From postal code | To postal code | Net weight |
| --- | --- | --- | --- | --- | --- |
| 1 | UPS | Ground | 21000 | 22000 | 175 |
| 2 | UPS | Express | 23000 | 24000 | 175 |
| 3 | FEDEX | Ground | 23000 | 24000 | 0 |

The application evaluates the selection rules in sequential order to determine which rule matches the ship-to postal code and weight of the shipment that needs to be transported.

As a result, it selects the second rule (UPS Express), because the rule matches the ship-to postal code value and is within the net weight of the shipment. The third rule is also a match, but was not chosen because the second rule was a match.

## Automatic carrier selection process

The application performs the following steps to select a carrier and service level for a shipments when the application has been configured to perform automatic carrier selection.

1.  When a shipment is created, a background workflow triggers the execution of the GET CARRIER CODE PREFERENCE command. The Execute Carrier Matrix (EXEC-CAR-MTX) background workflow is configured to execute at the time shipment is created (Shipment Created exit point).
    
    **Note**: If the Execute Carrier Matrix background workflow is enabled, but the Shipment Created exit point is not selected, then the GET CARRIER CODE PREFERENCE command is not executed when a shipment is created through wave planning. However, if a user manually creates a shipment and assigns an order line to it, then the GET CARRIER CODE PREFERENCE command is executed regardless of whether the Shipment Created exit point is selected.
    
2.  The application evaluates the carrier selection rules against the attributes of the shipment, searching each rule in sequential order (starting with 1) until a matching entry is found.
3.  If a carrier group is assigned to the shipment, then the application only evaluates selection rules for carriers that belong to the carrier group. The values associated with the shipment must either match or fall within the limits defined by the selection rule. For example, if a selection rule has a value for Item Family, that item family must be on the shipment; if it has a value for Net Weight, then the net weight of the shipment must be less than or equal to the value on the selection rule.
4.  The application updates the entity specified in the workflow instruction action command with the carrier code and service level from the matching selection rule. For example, if you want the carrier to be updated on the shipment, the instruction action configuration for the EXEC-CAR-MTX workflow would include the following values:
    
    -   **Result** \= Pass
    -   **Action** \= Run MOCA
    -   **Command** \= get carrier code preference where prcmod = 'U' and ship\_id = @ship\_id and wh\_id = @wh\_id
    
    Alternatively, if you want the carrier updated on the carrier lines, you would use the following command:
    
    get carrier code preference where prcmod = 'U' and ordlin = @ordlin and wh\_id = @wh\_id
    

## Configure carrier selection rules

1.  Select **Configuration > Outbound > Shipping > Carrier Selection**.
2.  To enable the application to automatically assign a carrier to a shipment that does not have one, set the **Enable Selection Rules** field to **ENABLED**.
    
    **Note**: In addition to enabling the selection rules, the Execute Carrier Matrix (EXEC-CAR-MTX) background workflow must also be enabled for the automatic carrier selection process to take place.
    
3.  To enable fields for use in the selection rules:
    
    **Note**: Fields from the order, order line, shipment, and shipment line can be enabled.
    
    1.  Click **Choose Available Fields**.
    2.  In the **Available** column, select the check box next to the fields to use.
    3.  Click **Apply**.
4.  To view selection rules, perform one or more of the following tasks:
    -   To view inventory attributes, select **General**.
    -   To view weight and volume threshold quantities, select **Measures**.
    -   To view pallet, case, pack, and piece threshold quantities, select **Counts**.
    -   To view destination location attributes, select **Location**.
5.  To add or modify a selection rule:
    1.  Perform one of the following tasks:
        -   To add a selection rule, in the grid, click **Add**.
        -   To modify a selection rule, in the grid, click the sequence number.
        -   To copy a selection rule, in the grid, select the check box next to the sequence, and then click **Copy**.
    2.  Enter information into the [Selection Rule fields](#Selection_Rule_fields). Only the fields enabled for selection rules are available for use.
    3.  Click **Save**.
6.  To change the sequence of the rules, drag the rule to the preferred position in the list. The sequence numbers are automatically updated.
7.  To delete a selection rule:
    1.  In the grid, select the check box next to the rule to delete.
    2.  Click **Delete**. A confirmation message is displayed.
    3.  Click **OK**.

## Selection Rule fields

 
| Field | Description |
| --- | --- |
| Sequence | Number that defines the order in which the selection rule is evaluated to determine whether it matches a shipment that requires a carrier assignment. The application searches the list of rules in sequential order, starting with 1, until it finds a selection rule that matches the shipment information. |
| Carrier | Identifier for a carrier that delivers inbound inventory to the warehouse or outbound shipments to a customer. This is the identifier that will be displayed to users on the application windows and reports. In the application, a carrier can be associated with a customer, order, inbound shipment, outbound shipment, load, and service levels (such as Ground, Next Day, and Saturday Delivery). |
| Service Level | Identifier for the service and transit time provided by the carrier that transports an order or shipment to the customer. For example, for a parcel carrier it may be used to indicate services such as express, second-day air, or standard delivery. |
| Cost | Value that represents the cost of inventory that is being shipped. The cost is based on the value assigned to each item represented by the inventory on the shipment. |
| Item Family | Identifier used to group similar items together. Typically, all of the items within a family have the same material handling characteristics. |
| Order Type | Name of an order type. An order type is a category that is used to group orders based on the warehouse processing necessary to fulfill the order. For example, customer orders and distribution orders require different processing by the application, and so an order type can be assigned to categorize each order separately. The application uses order types, for example, to identify orders that are eligible for bulk picking, or to direct orders to specific destination locations. |
| Ship-To Customer | Name and address for the customer to whom the order must be shipped. |
| Cubic Volume | Total cubic volume of the inventory on the shipment. It represents the amount of space, measured in cubic units, that the inventory occupies. |
| Gross Weight | Weight of the inventory on the shipment that includes its packaging and the containers on which it is shipped. |
| Maximum Girth | Maximum circumference allowed for the total amount of inventory on the shipment. |
| Net Weight | Weight of the inventory on the shipment, excluding the weight of the containers or handling units on which it is shipped. |
| Cases (est.) | Maximum number of cases allowed on the shipment. The number of cases per shipment can be obtained during shipment planning, and represents an estimate of the number of case picks that the shipment requires. |
| Packs (est.) | Maximum number of inner packs allowed on the shipment. The number of inner packs per shipment is an estimate of the number of inner-pack picks that the shipment requires. |
| Pallet (est.) | Maximum number of pallets allowed on the shipment. The number of pallets per shipment can be obtained during shipment planning, and represents an estimate of the number of pallet picks that the shipment requires. |
| Pieces (est.) | Maximum number of pieces allowed on the shipment. The number of pieces per shipment can be obtained during shipment planning, and represents an estimate of the number of piece picks the shipment requires. |
| Country | Country for the ship-to customer specified on the order. |
| Postal Code | Postal code associated with the ship-to address of the shipment. |
| Region | Postal region associated with the ship-to address of the shipment. |
| Client | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. |
| COD | Not currently used. |
| Currency | Identifier for the currency in which the monetary value is saved. |
| Department | Identifier for a department within the customer's facility. A department can be specified for a customer type, customer, order, order line, distribution, and item. It can be used to group information for the purpose of sorting and searching data, consolidating distribution inventory in customer-specific storage locations, and to help customers direct inventory to the proper department when it arrives at their facility. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
