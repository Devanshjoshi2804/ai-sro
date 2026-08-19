---
title: "Copy Language Entries"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/copy_language_entries.htm"
source: "/content/copy_language_entries.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Advanced"
  - "Copy Language Entries"
sections:
  - "Copy language entries to a locale"
images: []
source_sha1: a0b0e1f7facbdda3c27e4b317fe211b7be2d6a7e
---
# Copy Language Entries

A language entry is text, such as a field label, menu name, or value in a drop-down list displayed on the application interface. Language entries are associated to a locale so that the text can be displayed in the language of the user's locale.

The copy language entries feature provides the ability to copy text from an existing locale to a locale that does not yet contain language entries. This process is useful when you are adding a new locale for a language that is not supported, so that you can log into the new locale and view text on the application interface.

**Note**: You do not need to copy language entries for supported languages that are distributed with an application installation. You can load supported language data as part of an upgrade of an instance using the installer, or through a manual data load. See the information on language support in the _Warehouse Management Installation Guide_ or the information on loading languages in the _Supply Chain Execution Applications Administrator Guide_.

You copy language entries using the following pages that correspond to database tables in which the language entries are stored:

-   **Description**: Description master (DSCMST) table, which contains text for codes that are either added by the user as application data or provided as distributed data.
-   **Input**: LES variable input (LES\_VAR\_INP) table, which contains text for input values defined by the user as part of variable configurations.
-   **Item Description**: Item description (PRTDSC) table, which contains text for item descriptions.
-   **MLS Catalog**: Message Language Support (MLS) (or message) catalog (LES\_MLS\_CAT) table, which contains text for field labels, screen titles, and user messages provided as distributed data.
-   **System Description**: System description master (SYS\_DSC\_MST) table, which contains text for codes related to SCE client and RF and mobile device menu options, workflow descriptions, and other column values provided as distributed data.
    
    **Note**: The difference between the SYS\_DSC\_MST table and the DSCMST table is that descriptions in the SYS\_DSC\_MST table are rarely created by the user as application data.
    

## Copy language entries to a locale

1.  Select **Configuration > Advanced > Copy Language Entries**, and then select one of the following pages:
    -   Description
    -   MLS Catalog
    -   Input
    -   Item Description
    -   System Description
2.  In the grid, select the row that displays the destination and source locale ID combination. The LANGUAGE DESCRIPTION DETAILS grid displays the available entries in the source locale that do not yet exist in the destination locale.
    

**Note**: The grid displays enabled locale IDs only. If you do not see the locale ID you want, the locale may not be enabled. Use the Locales page to enable it. See [Add or modify a locale](../../../administration/system-administrator/configuration/internationalization/locales.md).

4.  Under **LANGUAGE DESCRIPTION DETAILS**, perform one of the following tasks:
    -   To copy specific rows, select one or more rows.
    -   To copy all rows, and if there are multiple pages in the grid, adjust the display range to increase the number of rows that can be copied, and then select the check box in the column title row to select all displayed rows. See [Adjust pages in a grid](../../../get-started/grids.md).
5.  From the **Actions** menu, select **Copy Locale**. The entries are copied to the destination locale and removed from the LANGUAGE DESCRIPTION DETAILS grid.
6.  If you have additional rows of data to copy in the grid, repeat the process to select the rows and copy the data.
7.  Repeat this procedure for each Copy Language Entries page.
8.  To verify the language entries are copied into the locale, assign the locale to a user, and then log in to the application as that user.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
