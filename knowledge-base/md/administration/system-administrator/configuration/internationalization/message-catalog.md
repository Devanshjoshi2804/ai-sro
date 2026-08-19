---
title: "Message Catalog"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/admin/message_catalog.htm"
source: "/content/admin/message_catalog.htm"
toc_path:
  - "Administration"
  - "System Administrator"
  - "Configuration"
  - "Internationalization"
  - "Message Catalog"
sections:
  - "Add or modify a message catalog entry"
  - "Delete a message catalog entry"
  - "Message Catalog fields"
images: []
source_sha1: 883a8f580f727c05ed967b32c65c850c00506762
---
# Message Catalog

All text displayed in the application is maintained in the message catalog. The catalog is a database table that stores the English source text, along with any alternative (customized or translated) text that may be created.

The message catalog provides the following text:

-   All of the fixed text presented to the user including window titles, labels, drop-down lists, buttons, pull-down menus, error messages, and informational messages
-   The text that is most appropriate for the following items:
    -   Display device (for example, RF wide or narrow form)
    -   Language identified in the user’s locale ID
-   The titles, headers, labels, and other text for generating reports

Each piece of source text in the message catalog is defined using a message ID. The message ID is a unique identifier that is associated with a description (the text that is displayed in the application in place of the message ID) and other attributes that determine where it is used (such as on a specific application window or form).

Message IDs are used to implement translations and customizations. For example, the standard description for the message ID "prtnum" is "Item Number." If a customer refers to items as SKUs, the project team can change the description of prtnum to "SKU", so that wherever a prtnum field displays, it is labeled "SKU" on the user interface.

You use Message Catalog to maintain the message catalog.

## Add or modify a message catalog entry

1.  Select **System Administrator > Configuration > ** **Internationalization > Message Catalog**.
2.  Perform one of the following tasks:
    -   To add a new message catalog entry, from the **Actions** drop-down list, select **Add**.
    -   To copy a message catalog entry, in the grid select the check box on the row of the message ID, and then from the **Actions** drop-down list, select **Copy**.
    -   To modify a message catalog entry, in the grid select the check box on the row of the message ID, and then from the **Actions** drop-down list, select **Edit**.
3.  Enter information in the [Message Catalog fields](#Message_Catalog_fields).
4.  Click **Save**. A confirmation message is displayed.
5.  Click **OK**.

## Delete a message catalog entry

1.  Select **System Administrator > Configuration > ** **Internationalization > Message Catalog**.

1.  In the grid, select the check box on the row of the message ID.
2.  From the **Actions** drop-down list, select **Delete**. A confirmation message is displayed.
3.  Click **OK**.

## Message Catalog fields

 
| Field | Description |
| --- | --- |
| Message ID | Unique identifier that represents a piece of source text in the message catalog. Each message ID is associated with a description (the text that is displayed in the application in place of the message ID), and other attributes that determine where it is used. Message IDs are used to support translations and customizations. |
| Application ID | Unique identifier for a Blue Yonder application. |
| Product ID | Identifier for the Blue Yonder application with which the message ID is associated. You use "LES" when the message ID is displayed in multiple applications. |
| Sort Sequence | Not currently used. |
| Variation | User-defined value that associates the message ID with a variation, such as one of the several different sizes of RF screens. |
| MLS Text | Description that is displayed in place of the message ID on the SCE client or RF and mobile device user interfaces; for example, as the title of an application window or as the label for a field or control that is displayed on an application window. |
| Form ID | Unique identifier for a specific form. |
| Locale ID | Identifier for a locale. A locale defines the attributes for a language that affect how information is displayed in the application. |
| Absolute Group | An identifier used by Blue Yonder product teams to indicate the product group that was responsible for loading data (in a particular row of a table). Standard group names include dcs\_data, mcs\_data, and sal\_data. This field is display only. |
| Customization Level | Value that differentiates customized data from standard data. Standard data is distributed with a customization level of 0 (zero). Customized data is assigned a higher customization level, usually in increments of 10. The MCS framework uses the customization level to determine which database entry to use and, as a result, takes the entry with the highest customization level. This field is display only. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
