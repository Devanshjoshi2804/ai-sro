---
title: "Form"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/admin/form.htm"
source: "/content/admin/form.htm"
toc_path:
  - "Administration"
  - "Extensions"
  - "Page Builder"
  - "Form"
sections:
  - "Add or modify a form type page"
  - "Add or modify a form type page layout configuration"
  - "Context fields"
images:
  - "/content/resources/images/image1140974.png"
  - "/content/resources/images/image524298.png"
  - "/content/resources/images/image1098457.png"
  - "/content/resources/images/image1130427.png"
  - "/content/resources/images/image1130428.png"
source_sha1: ea5ed7e6d09fcd2157c674085da879df52387e01
---
# Form

A form type page displays fields used to support a single action, such printing a label. When you configure a form type page, you define the following components:

-   **Action**: Web service endpoint that provides the data used on the page. An action can be part of a resource, or a standalone web service, and can be distributed or user defined.
    
    **Note**: A user-defined action can be a Configurable Web Service that uses MOCA components, commands, and configuration files. See the information on Configurable Web Services in the MOCA Developer Guide.
    
-   **Labeling**: Message text for the labels on the page to use instead of the distributed message name.
    

After you add a form type page, you must add the page to a menu and assign roles that can access the page. You can then view the page and define page layout configuration attributes, such as the layout and field configuration.

**Note**: Page Builder also adds form type pages to support the add and edit actions of a grid type page; however, the form type page that is associated with the grid type page cannot be added to a menu and is removed when the grid type page is deleted.

## Add or modify a form type page

1.  Select **Extensions > Page Builder**.
    

1.  Perform one of the following tasks:
    -   To add a form, from the **Actions** drop-down list, select **Add Form**.
    -   To modify a form, in the grid, click the title.
    -   To copy a form, in the grid, select the page row (without clicking the title), and then from the **Actions** drop-down list, select **Copy**.
2.  Enter information in the following fields:
    
     
    | Field | Description |
    | --- | --- |
    | **Title** | Text to display at the top of the page. |
    | **Description** | Text that provides additional information about the page, such as its purpose, and why and how it is used. The description is not displayed on the page. |
    | **Select Action** | Web service end point to use to support the action that is performed on the page. |
    

1.  If the page is new or you have selected a different action for an existing page, then click **Save**. The Edit Labels page is displayed.
2.  To define labels:
    1.  If the Edit Labels page is not displayed, click **Labeling**.
    2.  To copy a label:
        1.  In the grid, select the check box next to the name to copy, and then click **Copy**.
        2.  Enter information in the [Message fields](../message-editor.md).
        3.  Click **Save**.
    3.  To copy multiple labels:
        1.  In the grid, select the check box next to the names to copy, and then click **Copy**.
        2.  Enter information in the [Bulk copy fields](../message-editor.md).
        3.  Click **Save**.
    4.  To delete a label, in the grid, select the check box next to the names to delete, and then click **Delete**. A confirmation message is displayed.
    5.  To edit message text for a label, in the grid, click ![Edit](../../../../images/resources/images/image1140974.png), enter the message text, and click **Save**, or to edit the next label, click **Save & Next**.
3.  Click ![Close](../../../../images/resources/images/image524298.png) to close.
4.  To test the page:
    1.  If the Edit Form page is not displayed, in the grid, click the form title.
    2.  Click **Preview**.
    3.  Review the information on the page.
        
        **IMPORTANT**: The data that is displayed on the preview page is real data from the database and any actions that you take affect the database. Make sure that you are working in an environment in which it is safe to add, modify, copy, or delete data (such as a test or development environment).
        
    4.  Perform the available action.
    5.  Click **Back**.
5.  Click **Save**.
6.  To continue with additional page layout configuration:
    -   To add the page to a menu, see [Add or modify a menu](../menu-editor.md).
    -   To configure the page, see [Add or modify a form type page layout configuration](#Add_or_modify_a_form_type_page_layout_configuration).

## Add or modify a form type page layout configuration

You can configure a page that was created using Page Builder and added to a menu. See [Add or modify a menu](../menu-editor.md).

1.  Perform one of the following tasks:

-   Open a form type page from the menu.
-   Open a form type page associated to a grid, and then from the **Actions** drop-down list, select **Add**.

3.  Click ![Extensions settings](../../../../images/resources/images/image1098457.png) displayed on the right in the page title bar. The Form Configuration page is displayed.

1.  Under **Configurations**, perform one of the following tasks:
    -   To add a configuration, click **Add**.
    -   To copy a configuration, select a configuration, and then click **Copy**.
    -   To modify a configuration, select the configuration.
2.  Under **CONTEXT**, enter information in the [Context fields](#Context_fields).
    
    **Note**: Only one unique combination of warehouse, menu, and client can exist per configuration.
    

1.  To select the page layout, under **FIELDS AND LAYOUT** perform one of the following tasks:
    -   For a single-column layout, click ![Single-column layout](../../../../images/resources/images/image1130427.png).
    -   For a two-column layout, click ![Two-column layout](../../../../images/resources/images/image1130428.png).
2.  To arrange how the fields are displayed on the page, drag a field into a position you want.
3.  Click **Save**.
4.  To add a field configuration, click a field name, and then continue with [Add or modify a field configuration](../field-editor.md).
    
    **Note**: A blue field name indicates that a field configuration is applied.
    

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
