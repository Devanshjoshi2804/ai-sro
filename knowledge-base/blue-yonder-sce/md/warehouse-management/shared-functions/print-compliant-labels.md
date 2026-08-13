---
title: "Print Compliant Labels"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/print_compliant_label_section.htm"
source: "/content/print_compliant_label_section.htm"
toc_path:
  - "Warehouse Management"
  - "Shared functions"
  - "Print Compliant Labels"
sections:
  - "Print compliant labels"
images: []
source_sha1: 4f089f66d544ab9242157fb1123029cc516394ab
---
# Print Compliant Labels

The Print Compliant Labels page is accessible from the following modules: **Inventory, Packing, Picking, Receiving**, or **Shipping**.

You use this page when you want to manually reprint a compliant label. For example, you can reprint a compliant label if an existing label is damaged or not printed correctly at the exit point. Compliance configuration for labels enables you to select which labels (and the quantity) to print at specific exit points in the warehouse. For more information on compliance configuration, see [Compliance](../configuration/integration/reports-and-labels.md).

To reprint labels using a specific label format, document type, printer, local, and other criteria, use [Reprint an LPN label](inventory/procedures-for-lpns.md).

## Print compliant labels

1.  Perform one of the following tasks:
    
    -   To print from the Print Compliant Labels page:
        1.  Select one of the following modules: **Inventory**, **Packing**, **Picking**, **Receiving**, or **Shipping**.
        2.  Select **Print Compliant Labels**.
    -   To print from the LPN grid view:
        1.  [View LPNs](inventory/procedures-for-lpns.md).
        2.  In the grid, select the check box next to the LPN, sub-LPN, or-detail-LPN; or click the LPN to display the LPN details.
        3.  From the **Actions** drop-down list, select **Print Compliant Labels**.
    
2.  Enter information in the following fields:
    
     
    | Field | Description |
    | --- | --- |
    | LPN or Location | Enter the inventory identifier, such as LPN or location. |
    | Exit Point | Point in the warehouse process at which the report or label has been configured to automatically print. A list of labels that match the compliance configurations is displayed.<br > **Note**: The exit point and label formats are configured when modifying a document type. For more information, see [Add or modify a document type](../configuration/integration/reports-and-labels/document-types.md). |
    
3.  Select the check box for the required label formats.
    
4.  Select a printer at which the labels should be printed.
    
    **Note**: If a default printer is configured in [Label Formats](../configuration/integration/reports-and-labels/label-formats.md), the configured printer is displayed in the **Printer** field.
    
5.  Enter the number of copies.
    
6.  Click **Print**. The print status is displayed.
    
7.  Click **OK**.
    

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
