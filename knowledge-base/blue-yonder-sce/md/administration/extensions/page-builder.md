---
title: "Page Builder"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/admin/page_builder.htm"
source: "/content/admin/page_builder.htm"
toc_path:
  - "Administration"
  - "Extensions"
  - "Page Builder"
sections:
  - "Page Builder resources"
  - "Page layout configuration attributes"
  - "Reload APIs"
  - "Export a page that was built using Page Builder"
  - "Import a page that was built using Page Builder"
  - "Delete a page"
  - "Delete a page layout configuration"
images:
  - "/content/resources/images/image621867.png"
  - "/content/resources/images/normal_import_24_15x15.png"
  - "/content/resources/images/image1098457.png"
source_sha1: aec3a00ba36bc8f1ad7a719df1587b477e96a500
---
# Page Builder

You use Page Builder to add a web user interface (UI) page to your web client. The information provided on pages (except the external type page) is sourced using a resource (web service). See [Page Builder resources](#Page_Builder_resources).

A new UI page can be one of the following types:

-   **Grid**: Displays information in a tabular format and optionally provides actions that can be performed. A grid type page can display a single grid layout or a multiple (parent and child) grid layout. See [Grid](page-builder/grid.md).
-   **Chart**: Displays information in a graphical format. See [Chart](page-builder/chart.md).
-   **Dashboard**: Displays selected charts and grids. See [Dashboard](page-builder/dashboard.md).
-   **Form**: Displays the fields related to an action, or when associated with a grid type page, the fields that are used to add or edit entity information for a grid. See [Form](page-builder/form.md).
    
-   **External**: Displays the content of an external URL, such as a webpage or a web-based application. See [External Page](page-builder/external-page.md).

You use the Menu Editor to add a page to a menu and assign roles that can access the page. See [Add or modify a menu](menu-editor.md).

**Note**: When you add a page using Page Builder, you can preview the page. The preview displays the page and related data but is not fully functional. To use the page in the application, you must add the page to a menu.

After a page is added to a menu, you can view the page and define page layout configuration attributes such as the context in which the page is displayed and the properties specific to the page type. See [Page layout configuration attributes](#Page_layout_configuration_attributes).

You can also use Page Builder to export and import pages from one instance to another. See [Export a page that was built using Page Builder](#Export_a_page_that_was_built_using_Page_Builder) and [Import a page that was built using Page Builder](#Import_a_page_that_was_built_using_Page_Builder).

## Page Builder resources

A resource provides information to display on the page and is one of the following types of web services:

-   **Standard web service**: A web service that the application provides and uses. For example, you can configure a page that uses the standard order information web service to display selected order information in a chart format that best meets the reporting needs of your business.
-   **User-defined Java-based web service**: A web service written using the MOCA web service framework.
-   **Configurable web service**: A web service that uses MOCA components, commands, and configuration files. See the information on web services and Configurable Web Services in the _MOCA Developer Guide_.

**Note**: The external page type does not use a web service as a resource, as it displays the content of an external URL.

These web service resources and actions are stored on the application server instance and are accessible as part of the MOCA API metadata. To retrieve the available resources, the portal server instance API Discovery Service polls the application server instance when the portal server instance is restarted, or when a user reloads the APIs in Page Builder. See [Reload APIs](#Reload_APIs).

## Page layout configuration attributes

A page layout configuration defines the layout and attributes of the columns, fields, or widgets (such as a chart or grid) that are displayed on a page. You can define page layout configurations for a grid, form, chart, and dashboard type page. Each page is assigned an extension ID, which is an internal identifier that represents the page and the associated configurations.

You can define the following attributes for a page layout configuration:

-   **Context**: A unique combination of warehouse (site), menu, and client (subsite) in which the configuration takes effect. For example, if you select a context with the values of WMD2, All Menus, and Client A, the attributes and authorizations of that field configuration are used when a user logs in to WMD2 and selects Client A. The configuration is not applied for users who log into WMD1, or who log in to WMD2 without selecting Client A.

If multiple contexts apply to the same user, the most specific context is used. The application uses the following order (first to last) to determine which context is the most specific for a user:

1.  Client (subsite)
2.  Warehouse (site)
3.  Menu

For example, if you have a configuration with context values of All Sites, All Menus, and All Subsites, and a second with WMD1, All Menus, and All Subsites, the second context is applied for users logged in to WMD1.

If a user has access to multiple warehouses (sites), only the context for the selected warehouse applies. In the previous example, if the user logs out of WMD1 and selects WMD2, the application uses the All Sites, All Menus, and All Subsites configuration.

If a user has access to multiple clients (subsites) and selects more than one client at the same time, the application uses a configuration with All Subsites.

-   **Properties**: The appearance of the page elements that include the following settings:
    -   **Chart configuration**:
        -   The navigation links from a chart value to one or more destination pages
    -   **Parent and child grid configuration**:
        -   Whether the layout is horizontal (stacked) or vertical (side by side)
        -   The grid size ratio between the parent and child grids
        -   How each grid is configured. See [Grid configuration](#Grid_configuration).
    -   **Grid configuration**:
        -   The columns that are displayed, how each column is configured, the position of each column in the grid, whether a summary value is displayed for a column, and the navigation links from a column value to one or more destination pages
        -   The actions that are displayed in the **Actions** drop-down list, permission for each action, and configuration of actions that are associated to the selected resource
        -   The message text for the labels on the page to use instead of the distributed message name
        -   The columns to be used as required search criteria to display data in the grid
        -   The default and maximum number of results that display in the grid
        -   Whether data is displayed in the grid when the page is opened
    -   **Form configuration**:
        -   Whether the layout is a 1 or 2 column format
        -   The fields that are displayed and how each field is configured
            
            **Note**: See [Field configuration attributes](field-editor.md).
            
        -   The position of each field on the page
    -   **Dashboard configuration**:
        -   Whether the layout is a 2 or 3 column format
        -   The size of each widget
        -   The widgets that are displayed

## Reload APIs

The **Reload APIs** action runs the API Discovery Service to fetch updated Page Builder metadata (stored on the MOCA application server instance) without having to restart the portal server instance. You can perform this action to load new or updated MOCA web service resources and actions.

**IMPORTANT**: Existing pages may not function correctly if associated resources are updated. Use the Page Builder Resources health check to view discrepancies that exist between existing pages and updated resources.

Page Builder does not automatically update page properties to match an updated resource. For example, if a column is removed from a configurable web service used with a grid type page, the grid will continue to display the column heading and the cells of the removed column would be blank. Or, conversely, if a column is added to the configurable web service, it will not be automatically displayed on the grid. To correct these types of issues, you need to update the page, or in some cases, add a new page and select the updated resource.

1.  Select **Extensions > Page Builder**.
2.  From the **Actions** drop-down list, select **Reload APIs**. A message is displayed asking if you want to reload APIs.
3.  Click **Yes**. A confirmation message is displayed.
4.  Click **OK**.
5.  To view the Page Builder Resources health check, see [View and run health checks](../system-management.md).
6.  Update and save any pages that are affected by the updated resources.

## Export a page that was built using Page Builder

Use Page Builder to export one or more pages from one instance to another. The export process creates a ZIP file that contains a series of folders, YAML files, configuration files, menu data (if the page is associated to a menu), and Configurable Web Service resources (if the page is supported by that type of resource) that support the page. When you initiate the export process, all pages displayed in Page Builder are included in the export file, so to export specific pages, use the filter field to limit the display prior to exporting data.

**Note**: The export process requires a valid connection to the application server instance to export Configurable Web Service resources. If there is no connection to the instance, the resource files are not included in the export file.

1.  Select **Extensions > Page Builder**.

**Note**: The export process includes all pages that are displayed in the grid.

3.  Enter search criteria or select a filter to display the list of pages to export.
4.  Click ![Export](../../../images/resources/images/image621867.png).
5.  Save the file.

## Import a page that was built using Page Builder

Use Page Builder to import one or more pages into an instance. The import process validates the contents of a selected ZIP file, extracts the files, and loads the files onto the portal server and into the database. During this process, both page and menu files are loaded. In addition, depending on the resources used to support the page, the import process copies all YAML files associated to the page into the portal server database, including menu data information, and, if the page uses Configurable Web Service resources, extracts and deploys the resource files to the application server instance.

1.  Copy the ZIP file that contains the data exported from Page Builder to the portal server on which the instance is located.

1.  Select **Extensions > Page Builder**.
    
2.  Click ![Import](../../../images/resources/images/normal_import_24_15x15.png).
3.  Select a ZIP file to import, and then click **Submit**.
4.  If the page is supported by a user-defined Java-based web service, copy the web service files to the application server instance.
5.  Restart the application server instance to which the portal server instance is connected to enable the change.
    
    **Note**: You must restart the application server instance so that the application server discovers the web service resources associated to the imported pages.
    

1.  To view the changes, reload (refresh) the page using the web browser.
    
    **Note**: A reload downloads the webpage with the most current information and updates the cached data.
    

## Delete a page

When you delete a page, the extension ID and page layout configurations are also deleted. If the page is a grid type page, the associated form type page is also deleted.

1.  Select **Extensions > Page Builder**.
2.  In the grid, select the page row (without clicking the title).
3.  From the **Actions** drop-down list, select **Delete**. A confirmation message is displayed.
4.  Click **Yes**. If the page is displayed on a dashboard or menu, an additional confirmation message is displayed. Click **OK**.

## Delete a page layout configuration

**Note**: If a page is displayed on more than one menu in the application, deleting a page layout configuration removes the configuration from all occurrences of the page.

1.  Open the page.
2.  In the page title bar, click ![Extensions settings](../../../images/resources/images/image1098457.png). The Grid, Form, or Dashboard Configuration page is displayed.
3.  Under **Configurations**, select the configuration, and then click **Delete**. A confirmation message is displayed.
4.  Click **Yes**.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
