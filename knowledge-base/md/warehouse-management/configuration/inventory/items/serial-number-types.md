---
title: "Serial Number Types"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/serial_number_types.htm"
source: "/content/serial_number_types.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inventory"
  - "Items"
  - "Serial Number Types"
sections:
  - "Serialization types"
  - "Serial number masks"
  - "Add or modify a serial number type"
  - "Delete a serial number type"
  - "Serial Number Type fields"
images: []
source_sha1: e978e6e0acf2c6a79c904f05285ab2e17fe711f3
---
# Serial Number Types

A serial number type defines a kind of serial number, such as an Electronic Serial Number (ESN), International Mobile Equipment Identifier (IMEI), Integrated Circuit Card Identifier (ICCID), and the Security Identity Module (SIM). For each serial number type, you define a serialization mask that defines the expected format of the serial number and is used to validate that a serial number was entered correctly.

You can assign one or more serial number types to an item, which allows you to associate different serial number formats and attributes with the item when it arrives from different suppliers or is tracked for different clients.

A serial number type also determines whether serial numbers that are captured are sent to the host, and the order in which serial number types are displayed to an operator for typing or scanning a serial number.

## Serialization types

A serialization type determines the processes during which serial numbers are captured and verified. You can configure a serialization type for each unique item number or, for a 3PL environment, item client combination. See [Add or modify an item](items.md).

The following serialization types are supported:

-   **Cradle to Grave**: Gives you full visibility and control over serial numbers while the inventory is in the warehouse. Every partial move for an LPN requires a validation of the serial numbers being transferred. In addition, the user will be required to capture a serial number during the following processes:
    -   When identifying product, if an advance shipment notification (ASN) does not exist
    -   When putting away product, if an ASN exists, but does not contain a serial number
    -   At any point in the product's storage life before or after picking when the inventory quantity is changed
    -   Whenever a partial LPN is picked
    -   When manually confirming a pick
-   **Outbound Capture Only**: Only captures serial numbers during outbound processes and usually for customer compliance reasons. Serial numbers will only be captured during picking and after packing. If serial number capture is configured to be delayed until pack station processing, then instead of being captured during picking, serial number capture takes place during pack station operations. Serial numbers are not defaulted when the item client combination is picked or packed but are verified by the serial number mask associated with the serial number type. Unless serial number capture is configured to be delayed until pack station processing, the user is required to capture a serial number whenever they perform RF picking or confirm a pick at a workstation.

## Serial number masks

A serial number mask is a pattern that a serial number must match to be considered valid. During serial number capture, the application uses the serial number mask associated with the serial number type to dynamically validate the serial number as it is being typed or scanned by the user.

The characters in the mask are used to indicate the type of data required. You can use the following characters to define a serial number mask:

-   **&**: Requires a letter in the position.
-   \*: Requires any alphanumeric character in the position.
-   **#**: Requires a number in the position.
-   **@**: Requires a check digit in the position.

You can also include constants in a mask; these are characters that the application automatically appends to a serial number that is entered. For example, if the serial number type always starts with MFG, you can define MFG as a constant so that the user does not have to type it when entering a serial number.

The following table shows a valid serial number for each example mask.

 
| Mask | Valid serial number |
| --- | --- |
| &&&### | ABC123 |
| &#&#&# | A1B2C3 |
| &&\*\*\*\*\*\* | MM123DEF |
| ##\*\*\*\*\*\* | 991A2B3C |

## Add or modify a serial number type

1.  Select **Configuration > Inventory > Items > Serial Number Types**.
2.  Perform one of the following tasks:
    -   To add a serial number type, click **Add.**
    -   To modify a serial number type, in the grid, click the serial number type.
3.  Enter information in the [Serial Number Type fields](#Serial_number_type_fields).
4.  Click **Save**.

## Delete a serial number type

You cannot delete a serial number type that is assigned to an item.

1.  Select **Configuration > Inventory > Items > Serial Number Types**.
2.  In the grid, select the check box of the serial number type to delete.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Serial Number Type fields

 
| Field | Description |
| --- | --- |
| Serial Number Type | Identifier for a specific kind of serial number. A serial number type defines the order in which the operator is prompted to enter serial numbers when multiple types are required for an item, whether serial numbers of this type are reported to the host, and the number mask that is used to verify that a valid serial number has been entered. |
| Description | Text that further describes the serial number type. |
| Sequence | Sequence in which the application displays the serial number types to the operator, when prompting the operator to enter the serial numbers required for an item. |
| Report to Host | If Yes, serial numbers of this type will be sent to the host when they are recorded. Select Yes if you want serial numbers to be included in inventory transactions sent to the host.<br > If No, the application does not send serial numbers of this type to the host. |
| Serial Number Mask | Text string that the application uses to validate captured serial numbers of this type. When an operator enters a serial number, the application uses the serial number mask to determine whether the serial number is valid.<br > Valid values include any letter or number, as well as the following characters:<br>-   • **&**: Requires a letter in the position.
<br>-   • **\***: Requires any alphanumeric character in the position.
<br>-   • **#**: Requires a number in the position.
<br>-   • **@**: Requires a check digit in the position.
<br > For example, WH###&&& is a mask that can be used to validate the following serial number: WH123ABC |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
