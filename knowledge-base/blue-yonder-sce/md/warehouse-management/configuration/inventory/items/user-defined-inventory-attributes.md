---
title: "User Defined Inventory Attributes"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/user_defined_inventory_attributes.htm"
source: "/content/user_defined_inventory_attributes.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inventory"
  - "Items"
  - "User Defined Inventory Attributes"
sections:
  - "Examples: User-defined inventory attributes"
  - "Attribute name values"
  - "Enable user-defined inventory attributes"
images: []
source_sha1: 9bd0f8b1421b3b2b7021afe7f06a202f2c3ccddb
---
# User Defined Inventory Attributes

User-defined inventory attributes are optional item attributes that you can enable for use. When an attribute is enabled for use, then you can also enable the attribute to be tracked for individual items. See [Items](items.md).

User-defined attributes can be used in addition to the standard inventory attributes that the application provides.

The user-defined attributes can be represented using different data types (text, an integer, an integer with a decimal point, or a date). All inventory transactions (such as for receiving, moves, replenishments, picking, and transfers) validate the inventory attribute for the items for which the attribute is enabled.

When attributes are enabled and items are configured for attribute tracking, then you can capture and track user-defined attributes throughout the following warehouse processes:

-   Receiving
    -   During the receiving process, an operator can be prompted to verify user-defined attribute values that have been downloaded from the host on the planned inbound order line. For inbound order lines on which the attribute value has not been specified, the receiving operator can be prompted to enter the appropriate information. The processing of advance shipment notifications (ASNs) also supports the verification or entry of the additional attribute information as necessary for specified items. The information captured during the receiving process is tracked for the item throughout all of its movements in the warehouse.
    -   Multiple user-defined inventory attribute values can be received against a single inbound order line.
-   Date Control
    -   If the attribute is a date field, you can define a date window for the item for which the date attribute is tracked. The date window defines the acceptable maximum age difference between the oldest and newest inventory in a single location. This permits mixing multiple dates in a location in storage zones that are configured for date control.
    
    **Note**: To retain data consistency with physical labels, date (dte) type user-defined inventory attributes are not converted to a different time zone when displayed in the web client or stored in the database, but retain their original captured time zone.
    
-   Displays
    -   You can query by and display user-defined attributes that are enabled.
-   Inventory Adjustments
    -   Attribute tracking is maintained during inventory adjustments and transfers.
-   Inventory Attribute Changes
    -   Attribute values can be changed for existing inventory.
-   Inventory Attribute Mixing
    -   You can prevent inventory mixing in a location based on standard and user-defined attributes.
-   Inventory Holds
    -   Inventory can be placed on hold and released based on an attribute value.
-   Inventory Moves
    -   Attribute values can be used as selection criteria to make move requests.
-   Cycle Counting
    -   Cycle counting can be configured to display user-defined attributes for the item and allow the entry of user-defined attribute values during summary counts. Details counts include the user-defined attributes.
    -   Attribute values can be captured during summary and detail cycle counts.
-   Allocation
    -   Allocation rules for attributes on the order line can be downloaded, or defined and maintained manually.
    -   Wildcard values can be used for the attribute to define which attribute values are acceptable, including null.
    -   During standard allocation, the absence of data in an inventory field on an outbound order line means that any value is acceptable. However, you can configure a user-defined attribute so that if the field is null (left blank) on the order line, then only inventory that has that attribute as null can be allocated for the order line.
-   Picking
    -   Validation and modification of user-defined attribute values can take place during the picking process for outbound orders, replenishment orders, and work orders.
    -   RF pick validation can be configured to require confirmation of the attribute value during picking if more than one value for the attribute exists in the pick location.
-   Shipping
    -   Attribute information is tracked during the split load and pack station processes.
-   Reports and Labels
    -   Shipment records and paperwork include the user-defined attribute information for the inventory that has shipped from the warehouse.
    -   Values for user-defined attributes are displayed on labels and in reports.

## Examples: User-defined inventory attributes

The following examples show how user-defined inventory attributes can be used:

-   **Customs tracking**: A facility wants to assign a number, received from customs documentation, to an item, so that the application can track the item by the number and allocate inventory using that attribute.
-   **Serial number tracking**: A facility wants to track serial numbers for kits that are received, so that they can allocate inventory by the serial number. The facility wants to assign the serial number to a user-defined inventory attribute instead of using the standard serial number capture process.
-   **Item family attribute**: A facility wants to track an attribute that is unique to an item family, such as a luminosity code for light bulbs.

## Attribute name values

The name and number of a user-defined inventory attribute represents the type of data (such as text or numeric) and the type of field (such as a Yes/No toggle or drop-down list) that the attribute supports.

The following data types are available for use:

-   String or text (str)
-   Integer or number (int)
-   Floating decimal point (flt)
-   Date (dte)

**Note**: To retain data consistency with physical labels, date (dte) type user-defined inventory attributes are not converted to a different time zone when displayed in the web client or stored in the database, but retain their original captured time zone.

You enable an attribute that matches the type of data that you want to track. For example, for a text value (such as a color), use the "str" attribute; for a date value (such as a certification date), use the "dte" attribute.

After you determine the type of data to track, you must enable all three attributes of the same data type and number. Each attribute serves a different purpose and all three are required. For example, to set up a "str" (string or text-based) attribute, enable the following attributes:

-   **attr\_str1**: When this attribute is enabled, a text box field is added to the item configuration. The text box is labeled with the attribute description. The text box provides a drop-down list that allows a user to configure one of the following options for each item:
    -   **Not Tracked**: The attribute is not tracked for the item. This is the value that is assigned to all items by default, so that you can enable the attribute for specific items to which it applies.
    -   **Tracked - Required**: The attribute is tracked for the item and a value is required. For example, an operator is not allowed to identify or adjust inventory without entering a value for the attribute.
        
    -   **Tracked - Optional**: The attribute is tracked for the item but a value is not required. For example, the field is displayed during inventory identification, but an operator is allowed to identify inventory without entering a value for the attribute.
-   **attr\_str1\_flg**: When this attribute is enabled, the field is made available in the configuration of RF pick validation. Pick validation determines which fields must be entered or confirmed when picking inventory using an RF device.
-   **inv\_attr\_str1**: Defines the type of field that is displayed for the attribute during warehouse processing. This attribute defines, for example, the input properties (such as a text box or drop-down list) of the field and the value that is selected by default for the field. For example, when enabled, the field is displayed during inventory identification to allow an operator to select a value for the attribute.

The following table lists the structure of the attributes that are available and their corresponding data type.

    
| Attributes | Data type | Attr\_<data type> | Attr\_<data type>\_Flg | Inv\_Attr \_<data type> |
| --- | --- | --- | --- | --- |
| Inventory Attribute Text 1–18<br > **Note**: Inventory Attribute Text values are limited to 100 characters. | String: Alphanumeric | attr\_str1 – attr\_str18 | attr\_str1\_flg – attr\_str18\_flg | inv\_attr\_str1 – inv\_attr\_str18 |
| Inventory Attribute Number 1–5 | Integer: Numeric | attr\_int1 – attr\_int5 | attr\_int1\_flg – attr\_int5\_flg | inv\_attr\_int1 – inv\_attr\_int5 |
| Inventory Attribute Decimal 1–3 | Float: Numeric with decimal point | attr\_flt1 – attr\_flt3 | attr\_flt1\_flg – attr\_flt3\_flg | inv\_attr\_flt1 – inv\_attr\_flt3 |
| Inventory Attribute Date 1 and 2 | Date: Calendar date | attr\_dte1 and attr\_dte2 | attr\_dte1\_flg and attr\_dte2\_flg | inv\_attr\_dte1 and inv\_attr\_dte2 |

**IMPORTANT**: Additional configuration may be required to make the attribute visible, to assign a description (field label) to the attribute, and to define the type of data input used to represent the attribute values.

For information on the configuration of user-defined inventory attributes, see the Supply Chain Execution Help. For information on defining the context in which enabled attributes take effect (such as in workstation displays or on RF screens, or only when 3PL or Customs is enabled for the warehouse), see the information on addon IDs and addon ID hook variables, in the Supply Chain Execution Help.

## Enable user-defined inventory attributes

To ensure that an attribute can be configured for an item, available for pick validation, and available for entering a value (such as during inventory identification), you must enable all three attribute names that have the same data type and number. For example, for a text field (string data type), you must enable attr\_str1, attr\_str1\_flg, and inv\_attr\_str1.

**Note**: The description is the label by which the attribute is displayed in the application. The description is assigned in User Defined Inventory Attribute Maintenance window, available in the Supply Chain Execution (SCE) client.

1.  Select **Configuration > Inventory > Items > User Defined Inventory Attributes**.
2.  In the **Available** column, select the check box next to the attributes to enable.
3.  Click **Save**.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
