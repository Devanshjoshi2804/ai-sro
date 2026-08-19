---
title: "Outbound Note Types"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/outbound_note_types.htm"
source: "/content/outbound_note_types.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Outbound"
  - "Order Processing"
  - "Outbound Note Types"
sections:
  - "Add or modify an outbound note type"
  - "Delete an outbound note type"
images: []
source_sha1: 5abf26342a40447eddee316e6a5f9239b9dcc4ec
---
# Outbound Note Types

An outbound note type is a template that is used to define a set of attributes that are applied to order notes created using the note type. Note types define the points during outbound processing when the notes are made available for viewing. A note type also specifies if the notes are automatically displayed and whether they are printed on a packing list or bill of lading.

For example, you can create one note type for notes that are informational and not critical to complete the outbound processes; for this note type you limit the number of exit points at which the note becomes available and indicate that the note should not be displayed automatically. However, you can also create a note type for notes that are critical and required to be viewed before work continues; for this note type you specify multiple exit points and indicate that the note should be displayed automatically.

You can assign one or more outbound workflow exit points to a note type. See [Outbound workflow exit points](../../work/warehouse-workflows/outbound-workflows.md).

## Add or modify an outbound note type

1.  Select **Configuration > Outbound > Order Processing > Outbound Note Types**.
2.  Perform one of the following tasks:
    -   To add a note type, click **Add**.
    -   To modify a note type, in the grid, click the note type.
    -   To copy a note type, in the grid, select the check box next to the note type, and then click **Copy**.
3.  In the **Note Type** and **Description** fields, enter the values.
4.  To configure the note to be printed on shipping documents, in the **Printing** field, select either or both of the following options:
    -   **Packing List**: Specifies whether order notes are printed on the packing slip for the order with which the note type is associated. Notes for an order print at the top of the packing slip; notes for a specific order line print next to the item number on the packing slip.
    -   **Bill of Lading**: Specifies whether order notes are printed on the bill of lading for the order with which the note type is associated. Notes on a bill of lading print in the Special Instructions section and are limited to 40 characters. If notes exceed 40 characters, they are truncated to fit within the section to keep the integrity of the report layout.
5.  To assign the processing points at which notes are available for viewing:
    1.  Click **Note Type Exit Points**. The Exit Points page is displayed.
    2.  In the **Available Exit Points** column, select the exit points to use.
    3.  To automatically display the note when the exit point occurs, select the **Auto Display** check box. If cleared, notes using this note type are displayed to the operator by request only through a button or a function key. Notes that are displayed automatically can also be viewed by request when the notes become available.
    4.  Click **Apply**.
6.  Click **Save**.

## Delete an outbound note type

1.  Select **Configuration > Outbound > Order Processing > Outbound Note Types**.
2.  In the grid, select the check box next to the note type to delete.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
