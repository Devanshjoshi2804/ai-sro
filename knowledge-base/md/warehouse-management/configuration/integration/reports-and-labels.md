---
title: "Reports and Labels"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/reports_and_labels.htm"
source: "/content/reports_and_labels.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Integration"
  - "Reports and Labels"
sections:
  - "Compliance"
  - "Precedence in compliance"
  - "Document groups"
  - "Printing location"
images: []
source_sha1: e4dad5ee5130a22bb559dfe113f5ca057791750c
---
# Reports and Labels

A report is a document populated with data defined by the report format. For example, a receiving report can document the inventory statuses and quantities that were received during a specific date range. A report is typically printed to a file so that it can be displayed at a workstation, but it can also be printed to a physical printer.

A label is a document populated with data defined by a label format. For example, a pallet label provides the license plate number (LPN) for a pallet. A carton label can identify the contents and customer for whom the carton was packed.

You can configure the application to automatically print the correct type and number of labels and reports at the printer of your choosing and at specific points in the warehouse process.

For each report and label that you want to be printed automatically, you must configure a document type and then configure compliance for the document type, which determines when and how the label or report is printed. For example, to provide labels and reports for outbound orders you can configure printing to occur at the following points:

-   When a shipment is staged, the customer's case labels and pallet labels are automatically printed along with the carrier's bill of lading.
-   When a package is manifested, the customer's packing list is automatically printed.

A document type configuration can be limited by attribute values so that it applies, for example, to a specific customer, carrier, client, or item.

## Compliance

A compliance configuration defines how and when a report or label format is printed. A report or label format is a specific instance of a document type. For example, for a bill of lading (BOL) document type, you may have a standard label format as well as label formats that are specific to a customer or carrier. Therefore, you can add a compliance configuration to the BOL document type, and then specify the format to which the configuration applies.

The compliance configuration also defines the point at which the document is printed, the language (locale) in which it is printed, and the number of copies that are printed.

The application is not distributed with customer compliant labels, but the exiting labels can be used as templates for creating compliant labels. The application does not verify whether labels are compliant with customer requirements, so labels must be manually verified for compliance.

## Precedence in compliance

Precedence defines the priority of a compliance configuration for a document type. It determines which label format or report should be printed instead of another label format or report of the same document type.

For example, for a case label document type, you may have a format defined for customer A and another for item 99. If an order is for customer A and item 99, the application uses the sequence of document formats to determine which one to print (the customer A case label or the item 99 case label).

As another example, you may define a sequence for bill of ladings (BOLs) to print a carrier-specific BOL, if one exists; and if not, the standard warehouse BOL.

You set precedence by arranging the list of document formats on the Compliance page, when configuring compliance for a specific document type. See [Add or modify a document type](reports-and-labels/document-types.md).

Precedence can be overridden by assigning document formats to a document group.

## Document groups

A document group is an attribute of a compliance configuration that enables you to define a text string that groups label formats or reports so that all label formats or reports of the same document type in the same document group are printed at the same time (instead of one taking precedence over the others). For example, if the customer A and item 99 case label formats both have the same document group, then both case labels print, regardless of precedence.

## Printing location

You can configure a label format or report to print at a particular printer based on the following attributes:

-   Destination location. For example, a bill of lading can be printed at the ship staging location when a shipment is staged.
-   Source location. For example, labels for picked inventory can be printed at a printer near the picking location.
-   Default printer assigned to the compliance configuration
-   Printer assigned to the workstation or RF device at which the action was performed that caused the report or label to print

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
