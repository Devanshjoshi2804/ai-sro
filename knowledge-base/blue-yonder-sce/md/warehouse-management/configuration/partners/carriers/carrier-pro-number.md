---
title: "Carrier PRO Number"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/carrier_pro_numbers.htm"
source: "/content/carrier_pro_numbers.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Partners"
  - "Carriers"
  - "Carrier PRO Number"
sections:
  - "Carrier PRO number setup"
  - "Add or modify a carrier PRO number generation scheme"
  - "Delete a carrier PRO number generation scheme"
  - "Carrier PRO Number fields"
  - "Carrier PRO Number Block fields"
images:
  - "/content/resources/images/image942438.png"
source_sha1: 0f8678191bcf698a9d2d2b833ed86909537187d8
---
# Carrier PRO Number

A progressive rotating order (PRO) number is a carrier-required identifier that the application automatically assigns to a shipment. It identifies the location at which a shipment originated and is used by the carrier for most correspondence regarding the shipment.

Blocks of carrier PRO numbers are provided by the carrier, typically through a download to the application or other communication process. To use these numbers, you must define a PRO number generation scheme for each carrier that provides the numbers.

The PRO number generation scheme defines the format in which the application generates a PRO number for a shipment. The format includes the following components:

-   **Prefix**: Code that typically represents the shipper's location.
-   **Sequence number**: Next sequential number from the block of numbers provided by the carrier.
-   **Check digit**: An application-generated number that is appended to the end of the PRO number. Use of a check digit reduces errors caused by invalid data entry.

After you define the PRO number generation scheme, you can configure the application to automatically check for and assign carrier PRO numbers to shipments by carrier.

## Carrier PRO number setup

The automatic assignment of a carrier PRO number to a shipment is accomplished through the use of a background workflow that is configured to execute either when allocating inventory or staging a shipment. When the workflow executes, it determines whether a PRO number has been assigned to the shipment and, if one has not been assigned, it generates a new PRO number based on the PRO number configuration scheme defined for the shipper and carrier combination. The application automatically assigns the PRO number to the shipment at the load, stop, or shipment level, based on the configuration of shipping paperwork.

The following steps describe how to configure the application to automatically check for and, if required, add the next sequential carrier PRO number to the appropriate shipping documentation.

1.  Define the carrier PRO number configuration scheme for the carrier. The configuration defines the format of the PRO number and the sequence in which the numbers (provided by the carrier) are assigned. See [Add or modify a carrier PRO number generation scheme](#Add_or_modify_a_carrier_PRO_number_generation_scheme).
2.  Enable the ASSIGN-CAR-PRO-NUM background warehouse workflow and configure it to execute at either the Allocate Inventory or Shipment Stage exit points. Remove the unused exit point. See [Add or modify a background workflow](../../work/warehouse-workflows/background-workflows.md).
3.  Configure shipping paperwork by selecting the level (load, shipment, or stop) at which paperwork is required for the shipment. This is the document level to which application automatically assigns the carrier PRO number, if one is not already associated with the shipment. See [Configure outbound paperwork](../../outbound/shipping/outbound-paperwork.md).

## Add or modify a carrier PRO number generation scheme

1.  Select **Configuration > Partners > Carriers > Carrier PRO Number**.
2.  Perform one of the following tasks:
    -   To add a new generation scheme, click **Add**.
    -   To modify a generation scheme, in the grid, select the carrier.
    -   To copy a generation scheme, in the grid, select the check box next to the scheme, and then click **Copy**.
3.  Enter information in the [Carrier PRO Number fields](#Carrier_PRO_Number_fields).
4.  To define a block of PRO numbers for the generation scheme:
    1.  Click **Blocks**.
    2.  Perform one of the following tasks:
        -   To add a block of numbers, click **Add**.
        -   To modify a block of numbers, in the grid, select the row to modify.
    3.  Enter information in the [Carrier PRO Number Block fields](#Carrier_PRO_Number_Block_fields).
    4.  Click **Apply**.
    5.  To delete a block of numbers:
        1.  In the grid, select the row to delete.
        2.  Click **Delete**. A confirmation message is displayed.
        3.  Click **OK**.
    6.  Click ![Previous page](../../../../../images/resources/images/image942438.png).
5.  Click **Save**.

## Delete a carrier PRO number generation scheme

1.  Select **Configuration > Partners > Carriers > Carrier PRO Number**.
2.  In the grid, select the check box next to the PRO number generation scheme.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **Yes**.

## Carrier PRO Number fields

 
| Field | Description |
| --- | --- |
| Carrier | Identifier for the carrier that provided the blocks of sequence numbers used in the PRO number generation scheme. This is typically the carrier that is used to transport the shipments to which the PRO numbers are assigned. |
| Carrier Facility Address | Name and address information for the facility from which inventory is shipped and for which the PRO numbers are generated for the carrier. An address name represents the location and contact information of an entity (such as a carrier, client, customer, or supplier). The information fields support the entry of an address name, first and last name, address lines, a city, a state or province, a postal code, and a country. |
| Check Digit Method | Name of the check digit calculation method that you want the application to use for the carrier PRO number generation scheme. A check digit calculation method appends an algorithmically generated check digit to the PRO number. The purpose of the check digit is to guard against errors caused by incorrect transcription of a PRO number, and helps protect against invalid data entry. |
| Prefix | User-defined alphanumeric prefix for the carrier PRO number format. The prefix value typically represents a facility name or postal code that indicates the point of origin of the shipment being tracked. This value acts as a starting point for carriers in determining the location from which the shipment originated. |
| Number Length | Maximum number of characters in the sequence number portion of the carrier PRO number format. When the carrier PRO number is generated, the application replaces these characters with a number from the block of sequence numbers provided by the carrier. The length of the start and end numbers that you enter for a block of sequence numbers must match the value defined for this field. |
| Separator | Character used to separate the PRO number prefix, sequence number, and check digit in the carrier PRO number format. For example, enter a hyphen (-) in this field to achieve the following format: NNN-######-C |
| Format | User-defined format for a carrier PRO number. For example, in the format NNN-#####-C<br>-   • NNN represents the prefix
<br>-   • ##### represents the sequence number from the block of numbers received from the carrier
<br>-   • C represents the check digit calculated from the selected check digit method
<br > The prefix and check digit portion of the format are not required. This field is display only. |
| Next Value | Next carrier PRO number value to be generated as part of the carrier PRO number generation scheme. This value is display only, and includes the next sequential number that will be used from the block of numbers provided by the carrier. |

## Carrier PRO Number Block fields

 
| Field | Description |
| --- | --- |
| Sort sequence | Sequence in which you want the blocks of carrier PRO numbers to be used. When all of the numbers in a block have been used, the application starts to use the numbers in the next sequential block. To change the sort sequence, in the grid, click and drag the blocks into sequential order; as a result, the application automatically updates the sequence numbers. |
| Block Start | First number in the range of numbers that can be used by the PRO number generation scheme. This is the first number in the block of sequence numbers provided by the carrier. The length of this number must match the length defined in the **Number Length** field. |
| Block End | Last number in the range of numbers that can be used by the PRO number generation scheme. This is the last number in the block of sequence numbers provided by the carrier. The length of this number must match the length defined in the **Number Length** field. When last number in a block is used, the application starts using the next block of sequence numbers, if available, based on the sort sequence assigned to the block. |
| Increment By | Number by which the application increments a sequence number to obtain the next number to use when generating a new carrier PRO number.<br > For example, if you have a range of numbers from 1000 to 2000 that are incremented by 1, the application uses the following numbers: 1000, 1001, 1002, and so on. If you increment by 2, the application uses the following numbers: 1000, 1002, 1004, and so on. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
