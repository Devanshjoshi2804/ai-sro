---
title: "Label Designer overview"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/label_designer_overview.htm"
source: "/content/label_designer_overview.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Integration"
  - "Reports and Labels"
  - "Label Designer overview"
sections: []
images: []
source_sha1: 38fa6fc1cb3de878d6d7db02dfecdf34a6761e9e
---
# Label Designer overview

Label Designer is a standalone cloud-based application that is part of the Blue Yonder Azure services. It is the default label service for Warehouse Management and provides an interface from which users can manage labels without relying on a third-party service or license.

Label Designer offers centralized label design and management with version control and increased efficiency through label standardization. The application provides a label form designer, cloud-based centralized housing of label forms, and configurable print execution during various warehouse processes. During label generation, the application populates labels with real-time information from Warehouse Management using RESTful API-based data services or MOCA commands.

**Note**: For on-premises customers, Label Designer uses local file system storage and does not operate on the cloud platform. Labels in an on-premises environment are populated using MOCA commands.

Specifically, you use Label Designer to perform the following tasks:

-   Create and design customer compliant labels using a variety of barcode, text, and graphic controls
    
-   Define custom API fields to add to a label
    
-   Import and export label designs and templates
    
-   Import Zebra Programming Language (ZPL) label files to be converted to the Label Designer data model
    
-   Generate print-ready ZPL and Datamax Programming Language (DPL) labels
    

**Notes**: 

-   For Blue Yonder Cloud customers, Label Designer is enabled by default through the LABEL-EDITOR policy. The policy must be updated to include the Label Designer service URL. Contact Blue Yonder Services for assistance in setting up the Label Designer cloud-based instance.
    
-   For on-premises customers, the service URL is not required, but the LABEL-SERVICE daemon task must be started in the Console. If the task definition is updated to use a port other than the default, the LABEL-EDTIOR policy must also be updated.
    
-   To disable Label Designer functionality in Warehouse Management, you must delete the LABEL-EDITOR policy using Policy Maintenance.
    

To configure Warehouse Management to use the labels created in Label Designer, you must complete the following tasks:

1.  Create a label format with the following attributes to match each label created in Label Designer:
    
    -   **Label Format**: Label ID as specified in Label Designer. For example, if you create a label for pallet building with the label identifier **pallbl**, then the value in the **Label Format** field should be pallbl.
        
    -   **Data Command**: MOCA data command that generates the label. For example, if you want the pallet build label to be generated during the pallet build process, then the value in **Data Command** field should be pallbl datacmd.
        
    
    See [Label Formats](label-formats.md).
    
2.  For each printer, select the language in which labels are produced. If you do not select a value in the **Printer Language** field, the default language (ZPL) is used to print labels. See [Printers](../../equipment/hardware/printers.md).
    

See the information on label creation in the _Label Designer User Guide_.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
