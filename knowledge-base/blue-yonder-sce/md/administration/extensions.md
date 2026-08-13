---
title: "Extensions"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/admin/extensions.htm"
source: "/content/admin/extensions.htm"
toc_path:
  - "Administration"
  - "Extensions"
sections:
  - "Extensions data and data priority"
images:
  - "/content/resources/images/image1100232.png"
  - "/content/resources/images/image1100232.png"
  - "/content/resources/images/image1098457_13x13.png"
source_sha1: f145b96536e7599f0fe2b521b4ba159ec3bc7a99
---
# Extensions

An extension is a configuration of a distributed entity, such as a message or field, that results in an entity that meets your unique business needs. While the application has been designed and implemented to provide a variety of features and functions, your business may want to view or act on information in a way that is not provided by the standard application. Instead of relying on custom code to provide non-standard functionality, you can extend the following distributed entities in the web client:

-   **Actions**: You can add an action authorization, which is a field configuration of an action, using the Field Configuration page. Field Configuration is accessible from the gear ![Extensions settings](../../images/resources/images/image1100232.png) icon associated with an extensible action. The action can be provided as a button or a link on a window, a page, an **Actions** drop-down list, or a tag tooltip. See [Action authorizations](extensions/field-editor.md).
-   **Database tables**: You can add user-defined columns to standard database tables distributed with the application using the Column Editor. This functionality is intended for use in test or development environments. See [Column Editor](extensions/column-editor.md).
-   **Fields**: You can define the attributes and properties for a field using the Field Configuration page. Field Configuration is accessible from the Field Editor, or by using the gear ![Extensions settings](../../images/resources/images/image1100232.png) icon associated with an extensible field. See [Field Editor](extensions/field-editor.md).
-   **Menus**: You can build or modify a menu to provide role-based accessibility to pages using the Menu Editor. See [Menu Editor](extensions/menu-editor.md).
-   **Messages**: You can modify message text to match your preferred business terminology using the Message Editor. See [Message Editor](extensions/message-editor.md).
-   **Pages**: You can add and configure page types (such as grid, chart, or form) using Page Builder. Additional page layout configuration is accessible from a page using the gear ![Extensions settings](../../images/resources/images/image1098457_13x13.png) icon. See [Page Builder](extensions/page-builder.md).

Extensions data is stored in the portal server database and is assigned a priority level to ensure that the right data is displayed when you log into the web client, and to preserve extended data when the instance is upgraded. See [Extensions data and data priority](#Extensions_data_and_data_priority).

**Note**: User-defined columns created using the Column Editor are stored in the application server database and are not assigned a priority level.

To view and manage extensions, your user account must be assigned to the Portal Server Administrator role.

## Extensions data and data priority

Extensions data is stored in the portal server database, and managed from the portal server (also referred to as REFS \[External Facing Services\]), which is installed in a separate instance from the application server. Portal server provides the functionality to view, work with, and extend application data using the web client. After making changes in the web client, you can export extensions data for the purpose of importing it into another portal server instance.

**Note**: You can export extensions data created using the Field Editor, Message Editor, Menu Editor, and Page Builder. Extensions data created using the Column Editor is stored in the application server database, and is exported using a different process. See [Column Editor](extensions/column-editor.md).

The extensions data export process produces a series of YAML files. YAML is a human readable file format used to export and import data into the portal server database.

When you export the data, the application creates a ZIP file that contains the YAML files organized into several folders.

**Note**: In Page Builder, when you export a page supported by Configurable Web Service resources, the ZIP file also includes the resources.

Extensions data is saved into the following folders:

-   **customer**: This folder contains files with changes made using the web client.
-   **services**: This folder contains files that a Blue Yonder Services or a Value Added Reseller has previously added to the portal server database.

During the export process, application folders (such as **wm**, **refs**, and **mcs**) may also be created that contain YAML files that are distributed with the standard application.

The application assigns a priority to standard and modified application data so that the right data is displayed when you log into the web client. The priority value determines the level of the data that should be used from the database. The following priority levels are assigned:

-   Data that is distributed with standard applications is assigned a value in the low priority range starting with 1
-   Data that is associated with services modifications is assigned a higher priority value and is given priority over standard application data
-   Data that is added using the web client is assigned the highest priority value

Priority values are used to preserve extended data when an application instance is upgraded or enhanced, ensuring that changes made in the web client are prioritized over distributed application data.

**Note**: When you export a Page Builder page, you can then import the page, menu data, and Configurable Web Service resource files into another instance using the web client. See [Import a page that was built using Page Builder](extensions/page-builder.md).

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
