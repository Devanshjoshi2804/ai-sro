---
title: "Reports"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/admin/reports.htm"
source: "/content/admin/reports.htm"
toc_path:
  - "Administration"
  - "System Administrator"
  - "Reports/labels"
  - "Reports"
sections:
  - "Digital signatures"
  - "Add or modify a report configuration"
  - "Delete a report configuration"
  - "General fields"
  - "Add Signature fields"
images: []
source_sha1: 14ab210394ebe6e50116122e66beedd016ecc49d
---
# Reports - Administration

The application provides a standard set of reports that you can run to view information about the status of activities within your facility.

When you work with reports, you can perform the following tasks:

-   Maintain report configurations and their attributes. See [Add or modify a report configuration](#Add_or_modify_a_report_configuration).
-   Print, preview, bookmark, or export reports. See [Operations](operations.md).
-   Print or preview archived reports. See [Archive](archive.md).

The application can be integrated with a certified third-party digital signature capture application. See [Digital signatures](#Digital_signatures).

## Digital signatures

A digital signature is a signature that is placed on a digital document, such as a bill of lading, and stored as part of the document. You use a digital signature to manage your documents with signatures without having to print and file a hard copy of the document.

**IMPORTANT**: Support for capturing digital signatures requires a third-party digital signature capture application to be integrated with your Blue Yonder application. The third-party application must handle capturing and merging the digital signature with the document, as well as the storage and retrieval of the documents to which digital signatures have been added.

Reports that are submitted for a digital signature are generated as PDF documents so that the digital signature capture application can add the captured digital signature. An associated XML file is also generated; this file contains the signature attributes. The XML file serves as the interface with the digital signature capture application. The digital signature capture application parses the XML file and adds the signature to the PDF document based on the configuration defined for the placement of the signature on the report. The digital signature file path to which the PDF and XML files are generated and stored is configured in the SYSTEM-INFORMATION/REPORTS/DIGITAL-SIGNATURE-FILE-PATH policy in Policy Maintenance.

You use the Reports page to enable a report for a digital signature capture and to configure the placement of the signature on the report.

**Note**: Digital signatures cannot be viewed in your Blue Yonder application but can be viewed in the third-party digital signature capture application and in the PDF files.

## Add or modify a report configuration

You can define options for a report configuration.

**Note**: You use Report Operations to view or print a report that is generated using a report configuration.

1.  Select **System Administrator > Reports/labels > Reports**.
    

1.  Perform one of the following tasks:
    -   To add a report configuration, click **Add**.
    -   To modify a report configuration, in the grid, click the report configuration.
2.  Enter information in the [General fields](#General_fields).
3.  To enable Event Management to log an event for this report:
    1.  Under **EVENT MANAGEMENT**, set the **Send Alert** field to Yes.
    2.  In the **Event** field, enter the name of the Event Management event to log when the report is generated.
        
        **Note**: It is suggested that you set up an event name for all report configurations. If the event does not exist, Event Management will create a new event the first time the report is generated. Event Management users with appropriate access can subscribe to the Event Management event for the report and receive an email notification with the report attached, when the report is generated. The event must be enabled in the application, and is only available if Warehouse Management is integrated with Event Management.
        
4.  To require a digital signature for this report:
    1.  Under **SIGNATURE**, set the **Send for Digital Signature** field to Yes.
    2.  Perform one of the following tasks:
        -   To add a digital signature, click **Add**.
        -   To modify a digital signature, in the grid, click the signature.
    3.  Enter information in the [Add Signature fields](#Add_Signature_fields).
    4.  Click **Save**.
5.  Click **Save**.

## Delete a report configuration

You can delete a report configuration. After a report configuration is deleted, it no longer is available on the Operations page to select when viewing or printing reports.

**IMPORTANT**: It is highly recommended that you do not delete reports that are distributed with the application. Reports that are distributed with the application use a "Std-" prefix.

1.  Select **System Administrator > Reports/labels > Reports**.
    
2.  Select the check box next to the report configuration. You can select more than one report configuration.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## General fields

 
| Field | Description |
| --- | --- |
| **Report** | A unique identifier for the report. Standard report configurations that are distributed with the application are named with a "Std-" prefix. It is recommended that you use the following naming conventions:<br>-   • If you are a Blue Yonder customer, begin the report name with "USR-".
<br>-   • If you are a Blue Yonder associate, begin the report name with "VAR-". |
| **Description** | Text that further describes the report. |
| **Functional Area** | An identifier for specific functionality within the application to which the report applies. For example, Inbound Operations, Inventory, or Picking.<br > **Note**: A functional area value is required when you enable Event Management alerts for the report. |
| **Default Printer** | Default printer used to print the report or label. If, at the time of printing, the user does not specify a printer, then printing takes place at the default printer. |
| Product | Name of the Blue Yonder application that uses the report. |
| Report Layout File | Name of the file that defines the layout for the report.<br > **IMPORTANT**: The report name must include .jrxml as the file extension.<br>-   • **Upload**: The user can browse for and select a file to be uploaded to the reporting server.
<br>-   • **Choose an Existing File:** The user can select a file that has been previously uploaded to the reporting server. |
| Days to Keep | The default number of days to store a generated report in the archive.<br > **IMPORTANT**: If the value is 0, the generated report will not be archived. |

## Add Signature fields

 
| Field | Description |
| --- | --- |
| **Signature** | Unique identifier for this signature position on the report. |
| **Description** | Text that further describes the signature; for example Shipper Signature. |
| **Page** | Page on which the signature is displayed.<br>-   • **All Pages**: Signature is displayed on every page of the report.
<br>-   • **First Page**: Signature is displayed on the first page of the report only.
<br>-   • **Last Page**: Signature is displayed on the last page of the report only. |
| **Signature Width** | Width of the area (in inches) in which the signature is displayed. |
| Signature Height | Height of the area (in inches) in which the signature is displayed. |
| Signature Top | Distance from the top margin (in inches) to the area where the signature is displayed. |
| Signature Left | Distance from the left side margin (in inches) to the area where the signature is displayed. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
