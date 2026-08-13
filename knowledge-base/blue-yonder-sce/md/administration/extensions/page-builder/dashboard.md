---
title: "Dashboard"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/admin/dashboard.htm"
source: "/content/admin/dashboard.htm"
toc_path:
  - "Administration"
  - "Extensions"
  - "Page Builder"
  - "Dashboard"
sections:
  - "Add or modify a dashboard type page"
  - "Add or modify a dashboard type page layout configuration"
  - "Context fields"
images:
  - "/content/resources/images/image1098457.png"
  - "/content/resources/images/image1139491.png"
  - "/content/resources/images/image1139492.png"
source_sha1: adba118bf595e1e8c76d2d1ba0c9aecace6e007b
---
# Dashboard

A dashboard type page displays selected charts and grids to provide a summary view of information. While viewing a dashboard selected from a menu, users can expand a chart or grid to enlarge the view.

When you add or modify a dashboard type page, you select existing grid and chart type pages to add to the dashboard and define their placement in a 2-column layout. The top chart or grid in the list is displayed in the upper left corner of the dashboard. Each subsequent item is placed in a left-to-right, by top-to-bottom sequence.

After you add a dashboard type page, you must add the page to a menu and assign roles that can access the page. You can then view the page and define additional page layout configurations.

## Add or modify a dashboard type page

1.  Select **Extensions > Page Builder**.
2.  Perform one of the following tasks:
    -   To add a dashboard, from the **Actions** drop-down list, select **Add Dashboard**.
    -   To modify a dashboard, in the grid, click the title.
    -   To copy a dashboard, in the grid, select the page row (without clicking the title), and then from the **Actions** drop-down list, select **Copy**.
3.  Enter information in the following fields:
    
     
    | Field | Description |
    | --- | --- |
    | **Title** | Text to display at the top of the page. |
    | **Description** | Text that provides additional information about the page, such as its purpose, and why and how it is used. The description is not displayed on the page. |
    
4.  In the **Choose pages for the dashboard** drop-down list, select the chart and grid pages to display on the dashboard. The selected pages are displayed below the field.
    
    **Note**: The pages that you select are the only pages that can be added to the configurations for this dashboard.
    
5.  To test the page:
    1.  Click **Preview**.
    2.  Review the information on the page.
    3.  Click **Back**.
6.  Click **Save**.
7.  To continue with additional page layout configuration:
    -   To add the page to a menu, see [Add or modify a menu](../menu-editor.md).
    -   To configure the page, see [Add or modify a dashboard type page layout configuration](#Add_or_modify_a_dashboard_type_page_layout_configuration).

## Add or modify a dashboard type page layout configuration

You can configure a page that was created using Page Builder and added to a menu. See [Add or modify a menu](../menu-editor.md).

1.  Open the page.
2.  In the page title bar, click ![Extensions settings](../../../../images/resources/images/image1098457.png). The Dashboard Configuration page is displayed.

1.  Under **Configurations**, perform one of the following tasks:
    -   To add a configuration, click **Add**.
    -   To copy a configuration, select a configuration, and then click **Copy**.
    -   To modify a configuration, select the configuration.
2.  Under **CONTEXT**, enter information in the [Context fields](#Context_fields).
    
    **Note**: Only one unique combination of warehouse, menu, and client can exist per configuration.
    

1.  To select the dashboard layout, under **DASHBOARD ITEMS**, perform one of the following tasks:
    
    **IMPORTANT**: Changing the number of columns on the dashboard layout removes all selected widgets.
    
    -   For a two column layout, click **2**.
    -   For a three column layout, click **3**.
2.  To select an area larger than one cell in which to insert a chart or grid, click the adjacent cells to highlight them.
    
    **Note**: To reset cell selection, click ![Reset](../../../../images/resources/images/image1139491.png).
    
3.  To insert a chart or grid:
    1.  Click ![Add](../../../../images/resources/images/image1139492.png).
    2.  Click the chart or grid, and then click **Select**.
4.  To move a chart or grid on the dashboard layout, click it and when an outline is displayed, drag it to the new position.
5.  Click **Save**.

1.  To view the changes, reload (refresh) the page using the web browser.
    
    **Note**: A reload downloads the webpage with the most current information and updates the cached data.
    

## Context fields

 
| Field | Description |
| --- | --- |
| **Extension ID** | Unique internal identifier for an entity (such as a field, action, or page) that is enabled for extensibility. The extension ID identifies the entity, configurations, and if the entity is used within a variety of functions within the application, specific use of the entity in the application. |
| **Site** | Warehouse to which the configuration applies. The combination of site (warehouse), menu, and subsite (client) defines the context in which the configuration takes effect. |
| **Menu** | Application module to which the configuration applies. The combination of site (warehouse), menu, and subsite (client) defines the context in which the configuration takes effect. |
| **Subsite** | Client to which the configuration applies. The combination of site (warehouse), menu, and subsite (client) defines the context in which the configuration takes effect. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
