---
title: "Label Formats"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/label_formats.htm"
source: "/content/label_formats.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Integration"
  - "Reports and Labels"
  - "Label Formats"
sections:
  - "Add or modify a label format"
  - "Delete a label format"
images: []
source_sha1: 2998f0d0bec3df3f2530de52caaca15b800f4d1a
---
# Label Formats

A label format is a specific instance of a label document type. For example, for a pallet label document type, you may have the following label formats:

-   Customer-specific formats for customers that have specific requirements
-   Item-specific formats for items that have specific requirements
-   Generic warehouse format that is used by default when no other specific format applies

After you define label formats, in a multi-warehouse environment, you can select which formats to make available in the current warehouse.

## Add or modify a label format

You use the Global tab to define all of the label formats. After the formats are defined, you use the tab for the current warehouse to make the label formats available for use in the current warehouse.

1.  Select **Configuration > Integration > Reports and Labels > Label Formats**.
2.  Perform one of the following tasks:
    -   To define a label format, above the grid, select **Global**.
    -   To make an existing label format available for use in the current warehouse, above the grid, select the current warehouse.
3.  Perform one of the following tasks:
    -   To add a label format, click **Add**.
    -   To modify a label format, in the grid, click the label format.
4.  Enter information in the following fields:
    
     
    | Field | Description |
    | --- | --- |
    | Label Format | Unique identifier for the label format. This identifier must match the name (label ID) of the label as specified in Label Designer. For example, if you create a label for pallet building with the label identifier **pallbl**, then the value in this field should be pallbl. Label Designer is the default label service for Warehouse Management. See [Label Designer overview](label-designer-overview.md).<br > If Label Designer is disabled (LABEL-EDITOR policy removed), then this identifier must match the name of the file that contains the label configuration information, without the file extension. For example, if the file name is palletlabel.pof, then the value in this field should be palletlabel. For more information on custom label configuration files, contact your Blue Yonder project team.<br > **Note**: The value for the **Description** field, rather than the label format identifier, is used during warehouse processing when the label format is displayed to users. |
    | Description | Meaningful description of the label format. This description, rather than the label format identifier, is used during warehouse processing when the label format is displayed to users. |
    | Data Command | MOCA data command that generates the label. For example, if you want the pallet build label to be generated during the pallet build process, then the value in **Data Command** field should be pallbl datacmd.<br > **Note**: This field is only valid if Label Designer is enabled. |
    | Default Printer | Default printer used to print the report or label. If, at the time of printing, the user does not specify a printer, then printing takes place at the default printer. |
    
5.  Click **Save**.

## Delete a label format

1.  Select **Configuration > Integration > Reports and Labels > Label Formats**.
2.  To delete a label format from the current warehouse:
    1.  Above the grid, select the current warehouse.
    2.  In the grid, select the check box next to the label format to delete.
    3.  Click **Delete**. A confirmation message is displayed.
    4.  Click **OK**.
3.  To delete a global label format:
    
    **Note**: You cannot delete a global label format that has been added to a warehouse. When you delete a global label format, it is no longer available to be added to a warehouse.
    
    1.  Above the grid, select **Global**.
    2.  In the grid, select the check box next to the label format to delete.
    3.  Click **Delete**. A confirmation message is displayed.
    4.  Click **OK**.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
