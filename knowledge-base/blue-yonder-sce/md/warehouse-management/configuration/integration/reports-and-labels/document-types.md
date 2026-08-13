---
title: "Document Types"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/document_types.htm"
source: "/content/document_types.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Integration"
  - "Reports and Labels"
  - "Document Types"
sections:
  - "Add or modify a document type"
  - "Delete a document type"
  - "Document Type fields"
  - "Compliance fields"
  - "Compliance Rule fields"
images: []
source_sha1: 50634c11e9995630c2b5ae0e5d0f16ddaabba977
---
# Document Types

A document type is the configuration for a type of report (such as a bill of lading) or type of label (such as for a pallet or storage location).

The application provides the following standard document types:

-   Bills of lading
-   Carton label
-   Customer carton label
-   Customer ship label (single SKU)
-   Location label
-   Packing slip
-   Pallet label
-   Item label
-   Pick-ship label
-   Shipper's export declaration

## Add or modify a document type

When you create a document type, you can define its attributes and document type criteria (fields that determine the information that is included on the document type).

When you modify a document type, you can also define its format assignments (reports or label formats that use it) and its compliance attributes (how and when each report and label format based on the document type is printed).

1.  Select **Configuration > Integration > Reports and Labels > Document Types**.
2.  Perform one of the following tasks:
    -   To add a document type, click **Add**.
    -   To modify a document type, in the grid, click the document type.
    -   To copy a document type, in the grid, select the check box next to the document type, and then click **Copy**.
3.  Enter information in the [Document Type fields](#Document_Type_fields).
4.  To select the report and label formats to which the document type settings apply:
    
    **Note**: The **Format Assignments** field is only available when modifying a document type.
    
    1.  Under **SETTINGS**, click **Format Assignments**.
    2.  In the **Available** column, select the check box next to the formats that apply.
    3.  Click **Apply**.
5.  To define the fields that must be included on the label and whether a value is required for the field:
    1.  Under **SETTINGS**, click **Document Type Criteria**.
    2.  Perform one of the following tasks:
        -   To add a field, click **Add**.
        -   To modify a field, in the grid, click the argument name.
    3.  Enter information in the following fields:
        
        | Field | Description |
        | --- | --- |
        | Argument Name | Variable name of the field to include on the label. This is the name that the application uses to display a label for the field. For example, stoloc displays the label for the Location field; ship\_id displays the label for the Shipment field. To find an argument name, navigate to the Message Catalog page, and search for the field label using the **MLS Text** field. |
        | Required | If Yes, a value is required for the field. If set to Yes, then if the application cannot retrieve a value for the field, the document will not be produced.<br > If No, a value is not required for the field. |
        
    4.  Click **Apply**.
6.  To add the default units of measure (UOMs) for which the label is printed, and whether a label should be printed for a partial UOM quantity:
    
    **Note**: The **Default Units of Measure** field is only available when the **Print Documents By** field is set to Unit of Measure. The default UOMs apply when no UOMs are defined on the compliance configuration.
    
    1.  Click **Default Units of Measure**.
    2.  Click **Add**.
    3.  From the **Unit of Measure** drop-down list, select a UOM.
    4.  To require a label for partial quantities of the UOM, set the **Partial UOM** field to Yes. For example, if a Case UOM contains 10 eaches, then for a quantity of 15 eaches, one label is printed for the full UOM (10) and one label is printed for the partial quantity of the UOM (5).
    5.  Click **Apply**.
7.  To define how and when each label and report format based on the document type is printed:
    
    **Note**: The **Compliance** field is only available when modifying a document type.
    
    1.  Under **COMPLIANCE**, click **Compliance**.
    2.  To set the precedence by which a configuration is used, click and drag a document format to the preferred position in the list. See [Precedence in compliance](../reports-and-labels.md).
    3.  Perform one of the following tasks:
        -   To add a compliance configuration, click **Add**.
        -   To modify a compliance configuration, in the grid, click the document format.
    4.  Enter information in the [Compliance fields](#Compliance_fields).
    5.  To define the criteria that determines whether the document format is produced:
        
        **Note**: You assign criteria to limit use of the document type to inventory that matches the criteria. For example, you can specify a customer and item family for which the document should be used.
        
        1.  Click **Compliance Rule**.
        2.  In the **Available** column, select the check box next to the criteria that applies.
        3.  In the **Selected** column, enter information in the [Compliance Rule fields](#Compliance_Rule_fields).
        4.  Click **Apply**.
8.  To add the units of measure (UOMs) for which the label is printed, and whether a label should be printed for a partial UOM quantity:
    
    **Note**: The **Units of Measure** field is only available when the **Print Documents By** field (on the document type configuration) is set to Unit of Measure. If you do not specify a UOM, then the application uses the default UOMs defined for the document type.
    
    1.  Click **Units of Measure**.
    2.  Click **Add**.
    3.  From the **Unit of Measure** drop-down list, select a UOM.
    4.  To require a label for partial quantities of the UOM, set the **Partial UOM** field to Yes. For example, if a Case UOM contains 10 eaches, then for a quantity of 15 eaches, one label is printed for the full UOM (10) and one label is printed for the partial quantity of the UOM (5).
    5.  Click **Apply**.
9.  Click **Save**.

## Delete a document type

Some document types are distributed with the standard product. It is recommended that you do not delete the distributed document types.

1.  Select **Configuration > Integration > Reports and Labels > Document Types.**
2.  In the grid, select the check box next to the document type to delete.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Document Type fields

 
| Field | Description |
| --- | --- |
| Document Type | Unique identifier for the document type. The document type is an internal application identifier. The application provides several common document types. If you need to add a new report or label format, instead of adding a new document type, you may only need to modify an existing document type and add the new format. |
| Document Type Category | Category that determines whether the document type is a label or report. |
| Data Command | Server command that retrieves the information to be printed on the report or label for the document type. The application performs this action when the document type is printed. Contact your Blue Yonder project team if you do not know what command to enter. Do not change the command without first consulting your project team. |
| Description | Description of the document type. The description is the text that identifies the document type to users. |
| Break Level | Value that specifies the shipping level at which the document type is printed.<br>-   • **Load**: The document type is printed for the outbound load.
<br>-   • **Stop**: The document type is printed for each stop on the outbound load.
<br>-   • **Shipment**: The document type is printed for each shipment on the outbound load. |
| Billing Required | Reserved for future use. |
| Print Documents By | Packaging level or unit of measure (UOM) for which the document type is printed if an LPN level or UOM is not specified at the time of printing.<br>-   • **LPN Level**: Displays the **Default LPN Levels** field for you to select the packaging levels at which the label is printed. Packaging levels are defined on the item footprint configuration.
<br>-   • **Unit of Measure**: Displays the **Default Units of Measure** field for you to select the UOMs for which the label is printed, and whether it is printed for partial UOMs. UOMs are defined on the item footprint configuration. |
| Default LPN Levels | LPN level for which the label is printed. At the time of printing, if the user does not select an LPN level and if an LPN level was not defined for the label compliance, then the default LPN level is used.<br>-   • **LPN**: Inventory at the full LPN level; typically, a pallet.
<br>-   • **Sub-LPN**: Inventory at the case level.
<br>-   • **Detail LPN**: Inventory at the each (or piece) level.
<br > The **Default LPN Levels** field is only available if the **Print Documents By** field is set to LPN Level. In addition, you cannot change the LPN level if a compliance configuration already exists for the document type. |

## Compliance fields

 
| Field | Description |
| --- | --- |
| Document Format | Label format or report format to which the compliance applies. The document format is a specific report or label format that you want to configure for printing, for example, based on customer preferences or for specific items. For example, if the document type is a bill of lading report, then you can define compliance for the standard bill of lading report and for each custom bill of lading report (such as those designed for specific customers or carriers). |
| Device Source | Method to determine which printer to use to print the document.<br>-   • **Device code for workstation/Device**: Use printer based on workstation or RF device associated with the action that initiated the report or label printing.
<br>-   • **Destination Location**: Use printer based on the destination location of the work.
<br>-   • **Report's default printer**: Use printer based on the report's or label's default printer.
<br>-   • **Source Location**: Use printer based on the source location of the work.
<br>-   • **No selection (blank)**: Use printer based on the report's or label's default printer.
<br > **IMPORTANT**: If you select either the **Report's default printer** or **No selection (blank)** options and the report or label format does not have a default printer configured, then the report or label will not be printed. |
| Locale Type | Field that is used to determine which locale to apply to the report or label. A locale defines the culture-specific attributes displayed or printed on the report or label. Culture-specific attributes include language, time and date formats, currency formats, and measurement unit system.<br > For example, if you ship to a foreign country, you can select to print the shipping documentation based on the locale of the ship-to customer.<br > If you set the **Locale Type** field to Specific Locale, then the **Locale** field is displayed for you to select a locale. If you set the **Locale Type** field to Specific User, then the report is printed in the locale associated with the user who printed the label or report. |
| Locale | Identifier that determines the culture-specific attributes displayed or printed on the report or label. Culture-specific attributes include language, time and date formats, currency formats, and measurement unit system. |
| LPN Levels | LPN level for which the label is printed. The LPN level only applies to label formats. If you leave this field blank, the document prints at the default LPN levels defined for the document type.<br>-   • **LPN**: Inventory at the full LPN level; typically, a pallet.
<br>-   • **Sub-LPN**: Inventory at the case level.
<br>-   • **Detail LPN**: Inventory at the each (or piece) level. |
| Exit Point | Point in the warehouse process at which the application automatically prints the labels or reports. If you want a document format to be printed at multiple exit points, you must create a separate compliance configuration for each exit point. |
| Copies | Number of copies of the label or report to print at the selected exit point. |
| Document Group | Optional user-defined text used to group document formats for the purpose of overriding the precedence of the compliance configurations. See [Document groups](../reports-and-labels.md) and [Precedence in compliance](../reports-and-labels.md).<br > The application does not validate the value that you enter in this field. Be sure to enter the text exactly as it is displayed in other document formats that you want to include in the same group. The value is case-sensitive; for example, the application does not regard BOL, Bol, and bol as the same document group. |

## Compliance Rule fields

 
| Field | Description |
| --- | --- |
| Operator | Operator that is used with a value to qualify the criteria. For example, use "=" to limit the criteria to a specific value, such as Item Family = Apparel.<br>-   • **!=**: Not equal to
<br>-   • **\=**: Equal to
<br>-   •  > : Greater than
<br>-   • **>=**: Greater than or equal to
<br>-   • **<**: Less than
<br>-   • **<=**: Less than or equal to |
| Value | Value for the criteria. The value is used to limit use of the document format to matching inventory. For example, if the criteria is Item Family, you can use the operator and value to indicate the specific item family for which the document is used. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
