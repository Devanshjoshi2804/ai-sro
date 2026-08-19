---
title: "Barcode Settings"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/barcode_settings.htm"
source: "/content/barcode_settings.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inventory"
  - "Barcodes"
  - "Barcode Settings"
sections:
  - "Configure barcode settings"
  - "Barcode Settings fields"
images: []
source_sha1: c40473c7316ca11cd6037e8c97dc83c83a304427
---
# Barcode Settings

Barcode settings include configurations that define how the application stores and processes data parsed from a GS1 barcode. Specifically, you can configure how the application processes the following standard GS1 barcode elements:

-   **SSCC prefix**: The serial shipping container code (SSCC) received from a supplier, which is often used as the LPN, can be either 18 digits or 20 digits (18 digits plus a prefix of 00). You can configure the format in which you want the application to store SSCCs, so that when you receive an advanced shipment notification (ASN), the application determines whether the prefix needs to be added or removed.
-   **Separator character**: When a barcode includes variable-length data, the GS1 standard FNC1 character is used as a separator to indicate the end of the variable-length attribute value. However, since the FNC1 character is only recognized by the scanning device, you must select a separator character (such as a comma or pipe) that the application will use in place of the FNC1 character to parse data values from the barcode.

**Note**: If your warehouse supports GS1-128 barcodes, the scanning devices must be configured to retrieve the initial FNC1 character from a barcode and pass it to the application to signify that the barcode conforms to GS1 standards.

## Configure barcode settings

1.  Select **Configuration > Inventory > Barcodes > Barcode Settings**.
2.  Enter information in the [Barcode Settings fields](#Barcode_settings_fields).
3.  Click **Save**.

## Barcode Settings fields

 
| Field | Description |
| --- | --- |
| SSCC Prefix | If Yes, the application processes and stores serial shipping container codes (SSCC) with the prefix of 00. The SSCC received from a supplier, which is often used as the LPN, can be either 18 digits or 20 digits (18 digits plus a prefix of 00). When you receive an advanced shipment notification (ASN), the application determines whether the prefix needs to be added or removed based on this configuration. For example, if you select Yes and receive an SSCC from a supplier that does not use the prefix, then the first two digits (00) are added by the application.<br > If No, the application stores SSCCs without the prefix. For example, if you select No and receive an SSCC from a supplier that uses the prefix, then the first two digits (00) are removed by the application. |
| Variable Length Separator Characters(s) | Character used by the application in place of the FNC1 (Function Code 1) character when it is included in a barcode as a separator character. All GS1 barcodes begin with the FNC1 character to indicate that the barcode follows GS1 standards. Any additional occurrences of the FNC1 character in a barcode are used as separators to indicate the end of variable-length attribute values that are included in the barcode. However, the FNC1 character is only recognized by the scanning device and must be translated into a character that can be processed by the application.<br > **Note**: If your warehouse supports GS1-128 barcodes, the scanning devices must be configured to retrieve the initial FNC1 character from a barcode and pass it to the application to signify that the barcode conforms to GS1 standards.<br > For example, you may select the pipe character (|) as the Variable Length Separator. When a barcode includes variable-length attribute values, the barcode is read by the scanner, processed by the application, and displayed to the user in the following formats:<br>-   • **Barcode scan**: FNC1(240)paperFNC1(10)414OMFNC1(422)DKFNC1(20)1
<br>-   • **Processed by the application**: 240paper|10414OM|422DK|201
<br>-   • **Displayed to the user**:
    -   • **Item**: Paper
    <br>-   • **Lot Number**: 414OM
    <br>-   • **Origin Code**: DK
    <br>-   • **Revision Level**: 1
    <br>
<br > **Note**: Different barcode scanners may require different separator characters. Separate each variable length separator with a comma. The default value is the pipe character (|). |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
