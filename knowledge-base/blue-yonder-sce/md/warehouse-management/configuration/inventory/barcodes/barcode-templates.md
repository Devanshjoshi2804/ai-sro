---
title: "Barcode Templates"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/barcode_templates.htm"
source: "/content/barcode_templates.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inventory"
  - "Barcodes"
  - "Barcode Templates"
sections:
  - "Barcodes with multiple serial numbers"
  - "Template settings"
  - "Add or modify a barcode template"
  - "Delete a barcode template"
  - "Barcode Template fields"
  - "Barcode Template Settings fields"
images: []
source_sha1: d1f5299d67cf9f70304f8c01911edb1201661ae9
---
# Barcode Templates

A barcode template is a configuration that defines the type and location of data that is contained in barcodes that are based on the template. The application uses the template during warehouse processing to extract data from a barcode (such as those attached to an item, shipping container, or location) and populate displayed fields with that data.

The use of barcode templates simplifies warehouse processes and provides reliable data entry. For example, while advance shipment notifications (ASNs) describe the details of an inbound shipment, there are times when the ASN details do not match the actual inventory that was shipped. If a barcode template has been set up for the supplier, then during receiving, the operator can scan the barcodes attached to shipping containers to populate the fields on the receiving screens. This process updates any existing information that was inaccurate.

You can assign a barcode template to each supplier from whom you receive inventory labeled with barcodes that are based on the template. A barcode template can be assigned to multiple suppliers, but a supplier can be assigned only one barcode template.

## Barcodes with multiple serial numbers

The application supports the parsing of barcodes (such as 2D barcodes) that contain more than one serial number. For example, for a serialized item quantity of three, if the barcode provides all three serial numbers, the packing operator can obtain the required values with a single scan.

**Note**: Support for multiple serial numbers in a barcode is limited to pack station processing and is not available during other processes.

To enable parsing of these barcodes, you must configure a template for the AIM symbology used in the barcode. The template defines the type and location of data that is contained in barcodes that use the template. You can define one template for each AIM symbology identifier as the default template. The default template is used when the application cannot determine what barcode template to use.

The AIM symbology identifier is a prefix that identifies the symbology from which the barcode data is parsed. For example, it can identify a type of 2D barcode, such as PD417, GS1 DataMatrix, or GS1 QR. If the application cannot determine what template to use, it will use the default for the prefix provided by the barcode reader.

**Note**: The Association for Automatic Identification and Mobility (AIM) is a standards organization responsible for defining the AIM symbology identifiers.

The following configurations are required to support 2D barcode processing:

-   Capturing of serial numbers must be delayed until inventory is at the pack station
-   Since the AIM identifier is not stored in the barcode data, this feature requires that the barcode reader be configured to pass in the AIM identifier.
-   Multiple serial number barcodes that use GS1 must adhere to the GS1 standards when sending multiple serial numbers in GS1 DataMatrix or GS1QR symbologies.
-   Multiple serial number barcodes that do not use GS1 must contain a delimiter between each serial number to signify the end of a serial number and start of another. The delimiter must be the same throughout the barcode.

## Template settings

The template settings for a barcode define the data structure that the application uses to extract data from a barcode.

Each application ID identifies the location and content of a piece of information (typically an inventory attribute or location) that is contained in the barcode. It specifies the length of the expected value, the date format (for date information), and the number of digits after the decimal point (for fractional values).

You can define as many application IDs as you need to identify the type and location of data contained in the barcode. All possible data fields that the supplier includes in the barcode should be defined. This allows the maximum data extraction to occur when the operator scans the barcode.

The structure of a barcode template is typically obtained from the supplier.

For each template, an application ID can only be associated with one field; however, one field can be mapped to multiple application IDs. For example, Supplier X uses the application ID 101 for the Item field. If Supplier Y wants to use 201 as the ID for the Item field, you can create a second application ID for the Item field on the same template. If you do this, the application will recognize both 101 and 201 as the Item field. However, if Supplier Y wants to use ID 101 for the Serial Number field while Supplier X is using it for Item, you must create separate barcode templates for each supplier.

**Note**: An application ID can be added to a template without mapping it to a field so that it can still be scanned. This is used when a supplier includes data in the barcode that you do not use.

## Add or modify a barcode template

1.  Select **Configuration > Inventory > Barcodes > Barcode Templates**.
2.  Perform one of the following tasks:
    -   To add a barcode template, click **Add**.
    -   To modify a barcode template, in the grid, click the template name.
    -   To copy a barcode template, in the grid, select the check box next to the template name, and then click **Copy**.
3.  Enter information in the [Barcode Template fields](#Barcode_Template_fields).
4.  To assign the template to a supplier:
    
    **Note**: If a template is currently assigned to a supplier, selecting it here updates the template assignment to the one that you select.
    
    1.  Under **DEFINITION**, click **Suppliers**.
    2.  In the **Available** column, select the check box next to the suppliers that use the template.
    3.  Click **Apply**.
5.  To add or modify the barcode data structure:
    1.  Under **TEMPLATE SETTINGS**, perform one of the following tasks:
        -   To add an application ID, click **Add**.
        -   To modify an application ID, in the grid, click the application ID.
        -   To copy an application ID, in the grid, select the check box next to the application ID, and then click **Copy**.
    2.  Enter information in the [Barcode Template Settings fields](#Barcode_Template_Settings_fields).
    3.  Click **Apply**.
6.  To delete an application ID:
    1.  Under **TEMPLATE SETTINGS**, in the grid, select the check box next to the application ID to delete.
    2.  Click **Delete**. A confirmation message is displayed.
    3.  Click **OK**.
7.  Click **Save**.

## Delete a barcode template

You cannot delete a barcode that is assigned to a supplier.

1.  Select **Configuration > Inventory > Barcodes > Barcode Templates**.
2.  In the grid, select the check box next to the template to delete.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Barcode Template fields

 
| Field | Description |
| --- | --- |
| Barcode Template | Identifier for a bar code template. A bar code template is used to parse data from supplier-provided inventory barcodes for tracking purposes. A bar code template contains one or more bar code applications and can be associated with one or more suppliers. A bar code application defines the data structure (application ID, field name, length, date format, and decimal value) that the application uses to extract data from a supplier's bar code.<br > Bar code templates are used to simplify the receiving process to ensure inventory attributes are accurate when received from the supplier. Based on an agreed upon bar code format between you and your supplier, certain inventory attributes are contained in bar codes placed on the shipping container. During receiving, when the bar code is scanned (or entered), this information populates the fields on the receiving screens and updates any existing information that is inaccurate. |
| Description | Text that further describes the barcode template. |
| AIM Symbology Identifier | AIM symbology identifier (SI) is a three-character string consisting of an SI indicator, symbology identification, and a modifier character. This value identifies the symbology to use for parsing data from a barcode. For example, the value **\]d2** represents GSI DataMatrix (a 2D barcode symbology).<br > **Note**: The Association for Automatic Identification and Mobility (AIM) is a standards organization responsible for defining the AIM symbology identifiers.<br > When an operator scans a barcode, if the reader passes an AIM as a prefix to the data, the application uses the corresponding template to parse the data.<br > You can configure one default template for each AIM symbology identifier. This allows the application to determine a barcode symbology for a scanned barcode, and use the appropriate template to parse it. |
| Default Template | If Yes, this template is used by default for barcodes that the application does not recognize. You can configure one default template. However, if you use AIM symbology identifiers, you can also configure one default template for each AIM symbology identifier. The AIM symbology identifier identifies the barcode symbology used in the barcode.<br > If No, the template is not a default template. |

## Barcode Template Settings fields

 
| Field | Description |
| --- | --- |
| Application ID | Unique identifier for a piece of data (typically an inventory attribute) contained in a barcode based on the template. An application ID must be six characters or less, and the first two characters cannot be the same as another application ID in the same template. For example, if you define a valid application ID of 001, and attempt to define a second as 002. The application will not accept this because the parsing command cannot distinguish the difference. An application ID of 02, however, would be acceptable.<br > Do not use the application ID of 00 with any other application IDs on a barcode. |
| Field | Inventory attribute that is extracted from the barcode and displayed during receiving or product identification. One field can be mapped to multiple application IDs, but each application ID can be mapped to only one field. |
| Length | Number of characters allowed for the specified field. The length of the field is specified to indicate the location of the data in the barcode. For a template that contains multiple application IDs, the application determines the position of data based on the length of each field included in the template. |
| Date Format | Format (for example, YYMMDD) in which you want a date field to be populated. Only available if Manufactured Date or Expiration Date is selected as the field. |
| Decimal Places | Number of digits that a field with a fractional value allows after a decimal. Only available when Catch Quantity is selected as the field. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
