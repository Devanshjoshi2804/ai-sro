---
title: "Grid"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/admin/grid.htm"
source: "/content/admin/grid.htm"
toc_path:
  - "Administration"
  - "Extensions"
  - "Page Builder"
  - "Grid"
sections:
  - "Grid column size configuration"
  - "Grid column summary types"
  - "Grid and chart navigation link configuration"
  - "Example: Navigation link"
  - "Ad-hoc filters on the destination page"
  - "Example: Column with derived values"
  - "Parent and child grid configuration"
  - "Batch actions on grid type pages"
  - "Add or modify a grid type page"
  - "Add or modify a grid type page layout configuration"
  - "Add or modify a parent and child grid type page layout configuration"
  - "Context fields"
  - "Message fields"
  - "Bulk Copy fields"
images:
  - "/content/resources/images/image632381.png"
  - "/content/resources/images/image1140974_11x10.png"
  - "/content/resources/images/image524298.png"
  - "/content/resources/images/image1098457.png"
  - "/content/resources/images/image524298.png"
  - "/content/resources/images/image1140974.png"
  - "/content/resources/images/image524298.png"
  - "/content/resources/images/image1098457.png"
source_sha1: f1ee60e130d6b23263aca7245a9863cd8e1de9f7
---
# Grid

A grid type page displays information in a tabular format and optionally provides actions that can be performed on the information, such as adding, copying, editing, and deleting entities. A grid type page can display a single grid or two grids in a parent and child layout, and includes page elements. See [Work with pages](../../../get-started/work-with-pages.md) and [Filters](../../../get-started/filters.md).

When you configure a grid type page, you define the following components:

-   **Resource**: Web service end point that provides the data used on the page. A resource can be one of the distributed resources or a user-defined resource. Before creating a page, you must have a resource to associate with the page.
    
    **Note**: A user-defined resource can be a Java-based web service written using the MOCA web service framework, or a Configurable Web Service that uses MOCA components, commands, and configuration files. See the information on web services and Configurable Web Services in the MOCA Developer Guide.
    

-   **Grid actions**: Optional actions, such as adding (and copying), editing, and deleting entities, that are handled automatically by the page; you do not need to provide additional configuration.
    
    **Note**: When a grid type page is configured to provide Add or Edit actions, the application automatically creates a form type page for use in adding or editing rows in the grid.
    
-   **Child Grid**: Optional configuration that enables a child grid on the grid type page. A child grid requires a title, a separate resource to support the child grid data and associated actions, and resource property mappings to enable loading data in the child grid.
-   **Labeling**: Message text for the labels on the page to use instead of the distributed message name.
    

After you add a grid type page, you must add the page to a menu and assign roles that can access the page. You can then view the page and define page layout configuration attributes, such as columns, actions, and navigation links.

If the page supports add and edit actions, you can also view the associated form type page and define additional page layout configurations.

If the page supports a parent and child layout, you can also define and view a preview of parent and child page layout configuration attributes, such as grid alignment and ratio of parent to child grid size.

## Grid column size configuration

When you add a grid type page, each column in the grid is configured with a minimum width of 150 pixels. If a grid contains several columns, this minimum width may prevent all columns from being displayed, forcing the user to scroll in order to view the entire grid.

You can configure the column size to fit the information that is displayed in the column and make best use of the horizontal page space. Each column can be configured with a minimum width in pixels or a flex percentage value. A flex percentage is a number that indicates a column's relative size in proportion to other columns in the grid and can be used to ensure the grid displays properly regardless of the window size or screen resolution. A flex percentage can be expressed in any proportion, for example to express the ratio 2 to 1 you could also use 100 to 50, or 20 to 10.

You can also use a combination of minimum width and flex percentage values when configuring column sizes. For example, a page includes four columns (A-D) and you configure each column with the following values:

-   **Column A**: Minimum width value of 200
-   **Column B**: Minimum width value of 200
-   **Column C**: Flex percentage value of 2
-   **Column D**: Flex percentage value of 1

When displayed, Columns A and B use 400 pixels. The remaining pixels are divided between Columns C and D in the 2:1 ratio.

## Grid column summary types

Grid type pages support a column summary value, which is displayed at the bottom of the grid. To display a summary value for a column, you select a summary type that corresponds to the data type of the column. A summary type is supported for integer, float, long, double, number, and string data types. The summary value is calculated for the rows that are displayed on the current page.

**Note**: You can adjust the number of rows that are displayed on the page, or use different filtering criteria so that all the data is displayed on one page and included in the summary value.

In grid column configuration, the new **Summary Type** drop-down list field displays one or more of the following summary types, depending on the selected column's data type:

-   **Count**: A count of the results that are displayed in the column.
-   **Sum**: A total of the column values. For example, for a column that displays an each UOM quantity, the summary value displays the total number of eaches.
-   **Min** **and Max**: The lowest and highest values in the column. For example, the highest and lowest performance rating.
-   **Average**: The average of all column values. For example, for a column that displays the number of completed picks per hour, the summary value displays the average number of picks completed per hour.

**Note**: A column with a string data type is limited to the Count summary type. In addition, the **Summary Type** field is not displayed for a column with an object, Boolean, or date data type.

## Grid and chart navigation link configuration

As part of grid and chart type page layout configuration, you can configure navigation links from values displayed in the grid or chart to one or more pages in the application. When a grid or chart contains a navigation link, the user can click a value to display a page, or a list of pages from which to choose.

### Example: Navigation link

You can link grid column values or chart values displayed on a page or dashboard to any page in the application. For example, if a grid type page included an **Item** column, you could select the Inventory page as the destination page for that column. When a user clicks a value in the **Item** column, the Inventory page is displayed.

### Ad-hoc filters on the destination page

When available, you can configure ad-hoc filters to limit the data that is displayed on the destination page. For example, in Page Builder, you create two pages, Items Chart (the source page) and Items Grid (the destination page). You add a navigation link for the **Item** value on Items Chart, and to limit the data displayed on Items Grid, you add an item ad-hoc filter. When a user clicks the item, FLASHLIGHT, on Items Chart, the item=FLASHLIGHT ad-hoc filter is applied to the data that is displayed on Items Grid.

**Note**: The resource that supports chart type pages may have summarized data that does not provide useable values for context navigation. If available, you can select a full data resource for the chart type page and map the summary chart and full data resource parameters to support ad-hoc filtering.

You can configure one or more ad-hoc filters for a destination page by mapping fields between the destination page and the source page. The available fields for the destination page are drop-down lists. The values in a drop-down list represent the available fields from the source page. Selecting a value from a list maps the field between the destination and the source pages. For example, to use an item ad-hoc filter, in the **Item** drop-down list, select **Item**.The field name and the value selected from the field drop-down list must match for the ad-hoc filter to work.

**Note**: If ad-hoc filters are available for a destination page, additional fields are displayed during link configuration. To support ad-hoc filters, a destination page must expose APIs, such as a page created using Page Builder. If the destination page does not expose any APIs, no fields are displayed and you cannot configure ad-hoc filters.

## Example: Column with derived values

You can add a column with derived values to a grid type page by adding JavaScript code that calculates a value based on data for each row contained in the page resource. The following code shows an example of how to retrieve the data from a resource, calculate a value, and then display the value in the column.

**IMPORTANT**: You must have knowledge of JavaScript in order to use the derived values functionality. If the code that you enter in the field is invalid, no value is displayed in the grid.

**Example**: The following table shows customer order data displayed in a Page Builder grid type page.

     
| Name | Status | Delivery | Price | Tax | Discount |
| --- | --- | --- | --- | --- | --- |
| Store01 | Picked | Sat, Oct 10 2020 | 1000 | 110 | 20 |
| Store02 | Shipped | Thu Oct 10 2019 | 5000 | 500 | 30 |
| Store03 | Complete | Wed Oct 10 2018 | 8000 | 1200 | 10 |

Using column configuration, a column is added with JavaScript code that is used to calculate a final price for the order based on the price, tax, and discount values. The following code is added to the **JavaScript for derived column** field:

var data=JSON.parse(getInput()),

price=data.price, tax=data.tax, and discount=data.discount

var finalPrice=(price + tax)-(((price + tax)\*discount)/100);

setResult(finalPrice);

The JavaScript code that is provided in the field is run in a sandbox environment. The sandbox environment uses the following two functions to read grid row data from the page as input and pass back the derived output as the column value:

-   **getInput()**: Provides the JSON object with the column name as the key, and column value for that row as the value. The JSON string provided by this function can be parsed and used in JavaScript code as shown in the example. This function is used by the sandbox environment to read grid row data from the page.
-   **setResult()**: Sets the result back as a string. This function provides the derived value for display in the column. This function is used by the sandbox environment to pass the output of the JavaScript code to be displayed as the column value in the grid.

The following table shows the derived values that are displayed in the Final Price column after you save the column configuration and refresh the browser.

      
| Name | Status | Delivery | Price | Tax | Discount | Final Price |
| --- | --- | --- | --- | --- | --- | --- |
| Store01 | Picked | Sat, Oct 10 2020 | 1000 | 110 | 20 | 888 |
| Store02 | Shipped | Thu Oct 10 2019 | 5000 | 500 | 30 | 3850 |
| Store03 | Complete | Wed Oct 10 2018 | 8000 | 1200 | 10 | 8280 |

## Parent and child grid configuration

As part of adding or modifying a grid type page, you can configure a child grid, which enables both a parent and child grid on the page. You map the child grid resource properties to the parent resource properties so that when you select a row in the parent grid, the related child grid data is displayed.

When you specify a child grid, you define the following components:

-   **Title**: Displayed at the top of the child grid
-   **Resource**: A web service endpoint that provides the data used in the child grid. A grid can be supported by one of the distributed resources or a user-defined resource. See the information on web services and Configurable Web Services in the _MOCA Developer Guide_.
-   **Child property mappings**: A list of child resource properties that can be mapped to the parent resource properties.
    
    **Note**: At least one property must be mapped in order for data to display in the child grid.
    

After a grid type page is added, you can access Parent-Child Grid Configuration to perform the following tasks:

-   Set the page context
-   Set the grid alignment
-   Indicate the ratio of parent to child grid display
-   Access the standard grid configuration attributes for either the parent or child page

**Note**: The auto load option, which you can use to control how data is loaded into a grid, is not available for a child grid. Data is displayed in a child grid when a parent row is selected, based on the mapping defined on the child grid configuration. Aside from the auto load option, the child and parent grid configuration attributes are the same.

## Batch actions on grid type pages

A batch action is a task that a user can perform on multiple rows in a grid type page simultaneously, rather than having a separate action performed for each record. You select multiple rows, and then select the action from the **Actions** drop-down list to display a page on which you perform the action in batch.

The action can be whatever task is needed for the information that is displayed on the page. For example, if a page displays item information, the action may be batch editing field values. If a page displays order information, the action might be batch printing shipping paperwork. Batch actions are defined within a resource that is associated to the grid type page as part of the Configurable Web Services framework, and must be configured in the page attributes to display on the grid type page.

The name of the batch action displayed in the **Actions** drop-down list and the name of the batch action page is based on the definition in the page resource. The batch action page provides the fields needed to complete the action, and standard functions including the ability to display selected records within a batch and the ability to update a single record within the batch.

For example, a grid type page displays customer contact information that is updated frequently. A batch action called Bulk update, is available within the resource that supports the page and is configured to be displayed in the **Actions** drop-down list. You receive notice that a new centralized telephone number has to be updated on multiple contact records. On the page, you select the affected rows, and from the **Actions** drop-down list select the **Bulk update** option. The Bulk Update page is displayed that lists the fields for which values can be changed. Since the telephone number is the same for each record, you enter the number and click **Execute** to change the value for all selected records.

A batch action also supports separately modifying each record within a batch. Consider the previous example. Instead of a centralized number, you receive notice that unique telephone numbers are required for all customer contacts. You select the 10 contacts, select the Bulk update option, and indicate that you do not want to use the same values for each record. For each record, you enter the unique telephone number and execute the batch action. All customer contacts are updated at once.

If one or more actions fails to execute, the Batch Actions Summary Report window displays a list of all actions or the actions that failed (optionally). When you highlight an action in the list, information relating to the selected action is displayed that describes either the completed successful action or attributes of the failed action.

The Batch Action Summary Report window is not displayed if all records in the batch are completed successfully.

**IMPORTANT**: Batch actions must be defined within the resource that is associated to the page. For information on batch actions, see Configurable Web Services in the _MOCA Developer Guide_.

If the grid type page resource supports batch actions, you can configure batch actions using the Grid Configuration page. See [Add or modify a grid type page layout configuration](#Add_or_modify_a_grid_type_page_layout_configuration).

## Add or modify a grid type page

1.  Select **Extensions > Page Builder**.
    

1.  Perform one of the following tasks:
    -   To add a grid, from the **Actions** drop-down list, select **Add Grid**.
    -   To modify a grid, in the grid, click the title.
    -   To copy a grid, in the grid, select the page row (without clicking the title), and then from the **Actions** drop-down list, select **Copy**.
2.  Enter information in the following fields:
    
     
    | Field | Description |
    | --- | --- |
    | **Title** | Text to display at the top of the page. |
    | **Description** | Text that provides additional information about the page, such as its purpose, and why and how it is used. The description is not displayed on the page. |
    | **Select Resource** | Web service end point to use to support the information that is displayed and the automatic actions that are performed on the page. After selecting a resource, the automatic actions are available and selected. |
    
    **Notes**:
    
    -   Only web service-specific actions supported by the resource are available for selection.
    -   When a grid type page is configured to provide Add or Edit actions, the application automatically creates a form page for use in adding or editing rows in the grid.
    

1.  To configure a child grid:
    1.  Click **Child Grid**.
    2.  In the **Title** field, enter the text to display at the top of the child grid.
    3.  In the **Select Resource** field, click ![Lookup](../../../../images/resources/images/image632381.png), and then select the web service end point to use to support the child grid. The child resource properties are displayed as field drop-down lists. The parent resource properties are listed as values in each list.
        
    4.  From a field drop-down list, select a corresponding parent resource property.
        
        **Note**: To load data in the child grid, you must select at least one parent resource property on which you want to filter the data.
        
    5.  Click **Apply**.
2.  If the page is new or you have selected a different resource for an existing page, then click **Save**. The Edit Labels page is displayed.
3.  To define labels:
    1.  If the Edit Labels page is not displayed, click **Labeling**.
    2.  To copy a label:
        1.  In the grid, select the check box next to the name to copy, and then click **Copy**.
        2.  Enter information in the [Message fields](#Message_fields).
        3.  Click **Save**.
    3.  To copy multiple labels:
        1.  In the grid, select the check box next to the names to copy, and then click **Copy**.
        2.  Enter information in the [Bulk copy fields](#Bulk_copy_fields).
        3.  Click **Save**.
    4.  To delete a label, in the grid, select the check box next to the names to delete, and then click **Delete**. A confirmation message is displayed.
    5.  To edit message text for a label, in the grid, click ![Edit](../../../../images/resources/images/image1140974_11x10.png), enter the message text, and click **Save**, or to edit the next label, click **Save & Next**.
4.  Click ![Close](../../../../images/resources/images/image524298.png) to close.
5.  To test the page:
    1.  If the Edit Grid page is not displayed, in the grid, click the grid title.
    2.  Click **Preview**.
    3.  Review the information on the page.
        
        **IMPORTANT**: The data that is displayed on the preview page is real data from the database and any actions that you take affect the database. Make sure that you are working in an environment in which it is safe to add, modify, copy, or delete data (such as a test or development environment).
        
    4.  Perform the available actions, such as adding a new entity.
    5.  Click **Back**.
6.  Click **Save**.
7.  To continue with additional page layout configuration:
    -   To add the page to a menu, see [Add or modify a menu](../menu-editor.md).
    -   To configure a grid type page, see [Add or modify a grid type page layout configuration](#Add_or_modify_a_grid_type_page_layout_configuration).
    -   To configure a form type page, see [Add or modify a form type page layout configuration](form.md).
    -   To configure a parent and child grid type page, see [Add or modify a parent and child grid type page layout configuration](#Add_or_modify_a_parent_and_child_grid_type_page_layout_configuration).

## Add or modify a grid type page layout configuration

You can configure a page that was created using Page Builder and added to a menu. See [Add or modify a menu](../menu-editor.md).

1.  Open the page.
2.  In the page title bar, click ![Extensions settings](../../../../images/resources/images/image1098457.png). The Grid Configuration page is displayed.

1.  Under **Configurations**, perform one of the following tasks:
    -   To add a configuration, click **Add**.
    -   To copy a configuration, select a configuration, and then click **Copy**.
    -   To modify a configuration, select the configuration.
2.  Under **CONTEXT**, enter information in the [Context fields](#Context_fields).
    
    **Note**: Only one unique combination of warehouse, menu, and client can exist per configuration.
    

1.  To define which columns are displayed in the grid and configure the column properties:
    1.  Click **Configure Columns**.
    2.  To include an existing column in the grid, select the check box next to the column.
    3.   To add a column with derived values to the grid:
        1.  From the **Actions** drop-down list, click **Add**.
        2.  Enter a name for the column, and click **Apply**.
            
            **Note**: Spaces and periods are not allowed; however, if you use a capital letter, a space is added when the column name is displayed on the grid. For example, if you want the grid column title to be "Final Price", enter the column name as FinalPrice.
            
        3.  In the **JavaScript for derived column** field, enter code to calculate the value. See [Example: Column with derived values](#Example:_Column_with_derived_values).
    4.  To reorder the selected columns, drag each column to the position you want.
        
    5.  To display a summary value for a column, select the column and then from the **Summary Type** drop-down list, select a type.  See [Grid column summary types](#Grid_column_summary_types).
        
        **Note**: You cannot display a summary value for a column with derived values.
        
    6.  To configure column properties, select the column and enter information in the following fields:
        
        | Field | Description |
        | --- | --- |
        | **Minimum Width** | Number that defines the minimum width of the column in pixels. If left blank, the minimum width is 150 pixels by default. |
        | **Flex Percentage** | Number that indicates a column's relative size in proportion to the other columns in the grid. See [Grid column size configuration](#Grid_column_size_configuration). |
        | **Visible by Default** | If On, the column is displayed on the grid. If Off, the column is hidden but is available from the column's shortcut menu. A user can opt to display the column in the grid. See [Adjust columns in a grid](../../../get-started/grids.md). |
        
    7.  To configure navigation links for a column:
        
        **Note**: You cannot configure a navigation link for a column with derived values.
        
        1.  Select the column, and then click **Configure Link Navigation**.
        2.  Select the check box next to the pages to which the values in the column are linked.
        3.  To reorder the selected pages, drag each page to the position you want.
        4.  To configure ad-hoc filters to limit the data that is displayed on the destination page, from a field drop-down list, select the field from the source page that matches the field on the destination page. For example, if the destination page has an **order** field, then from the **order** drop-down list, select **order** (if it is available from the source page) to filter the results displayed on the destination page by a specific order number. See [Grid and chart navigation link configuration](#Grid_and_chart_navigation_link_configuration).
            
            **Note**: The value selected from the drop-down list must match the label of the drop-down list for an ad-hoc filter to work.
            
        5.  Click **Apply**.
    8.  To remove a column from the grid, either clear the check box for the column under Select Columns, or click ![Close](../../../../images/resources/images/image524298.png) next to the column name.
    9.  Click **Apply**.
2.  To define which actions are displayed in the drop-down list and configure action properties:
    1.  Click **Grid Actions**.
    2.  Select the check box next to the action to include in the grid.
    3.  To reorder the selected actions, drag each action to the position you want.
    4.  To assign permissions for an action, select the action, and then from the **Assigned Permissions** drop-down list, select the roles, privileges, and user-defined permissions for which the action is available.
        
        **Note**: Assigning permissions makes the action visible on the **Actions** drop-down list and allows any role, privilege, and user-defined permission that is selected to perform the action.
        
    5.  To configure actions, select the action, and enter information for the configuration options.
    6.  Click **Apply**.

1.  To define labels:
    1.  Click **Labeling**.
    2.  To copy a label:
        1.  In the grid, select the check box next to the name to copy, and then click **Copy**.
        2.  Enter information in the [Message fields](#Message_fields).
        3.  Click **Save**.
    3.  To copy multiple labels:
        1.  In the grid, select the check box next to the names to copy, and then click **Copy**.
        2.  Enter information in the [Bulk copy fields](#Bulk_copy_fields).
        3.  Click **Save**.
    4.  To delete a label, in the grid, select the check box next to the names to delete, and then click **Delete**. A confirmation message is displayed.
    5.  To edit message text for a label, in the grid, click ![Edit](../../../../images/resources/images/image1140974.png), enter the message text and click **Save**, or to edit the next label, click **Save & Next**.
    6.  When finished, click ![Close](../../../../images/resources/images/image524298.png) to close.

1.  To select the columns to be used as required search criteria in the grid:
    
    **Note**: You cannot use a column with derived values in search criteria.
    
    1.  Click **Filter Field**.
    2.  Select the check box next to the column.
    3.  Click **Select**.
        
        **Note**: The **Auto Load Grid Data** field is automatically set to **No** when one or more columns are selected.
        
2.  To define the number of rows that are displayed per page in the grid:
    
    **Note**: If you do not specify default and maximum page sizes, the page is configured with 50, 100, and 150 displayed rows per page, which provides the user with three display options.
    
    -   In the **Default Page Size** field, enter or select the number of rows per page to display by default on the grid.
    -   In the **Maximum Page Size** field, enter or select the maximum number of rows per page to display on the grid.
3.  To configure the page to open without displaying information in the grid, in the **Auto Load Grid Data** field, select **No**.
    
4.  Click **Save**.

1.  To view the changes, reload (refresh) the page using the web browser.
    
    **Note**: A reload downloads the webpage with the most current information and updates the cached data.
    

## Add or modify a parent and child grid type page layout configuration

You can configure a page that was created using Page Builder and added to a menu. See [Add or modify a menu](../menu-editor.md).

1.  Open the page.
2.  In the page title bar, click ![Extensions settings](../../../../images/resources/images/image1098457.png). The Parent-Child Grid Configuration page is displayed.

1.  Under **Configurations**, perform one of the following tasks:
    -   To add a configuration, click **Add**.
    -   To copy a configuration, select a configuration, and then click **Copy**.
    -   To modify a configuration, select the configuration.
2.  Under **CONTEXT**, enter information in the [Context fields](#Context_fields).
    
    **Note**: Only one unique combination of warehouse, menu, and client can exist per configuration.
    

1.  Under **LAYOUT CONFIGURATION + PREVIEW**, to set the parent-child grid alignment, select one of the following options:
    
    -   **Stacked**: Displays the parent grid above the child grid in a vertical layout.
    -   **Side by Side**: Displays the parent grid to the left of the child grid in a horizontal layout.
2.  To set the grid size ratio of parent grid to the child grid, select one of the following options:
    -   **1:2**: The parent grid is half the size of the child grid.
    -   **1:1**: The parent and child grids are the same size.
    -   **2:1**: The parent grid is twice the size of the child grid.
3.  To configure the parent or child grid:
    1.  Perform one of the following tasks:
        -   To modify a parent grid configuration, click **Parent Grid**.
        -   To modify a child grid configuration, click **Child Grid**.
    2.  Continue with [Add or modify a grid type page layout configuration](#Add_or_modify_a_grid_type_page_layout_configuration).
4.  Click **Save**.

1.  To view the changes, reload (refresh) the page using the web browser.
    
    **Note**: A reload downloads the webpage with the most current information and updates the cached data.
    

## Context fields

 
| Field | Description |
| --- | --- |
| **Extension ID** | Unique internal identifier for an entity (such as a field, action, or page) that is enabled for extensibility. The extension ID identifies the entity, configurations, and if the entity is used within a variety of functions within the application, specific use of the entity in the application. |
| **Site** | Warehouse to which the configuration applies. The combination of site (warehouse), menu, and subsite (client) defines the context in which the configuration takes effect. |
| **Menu** | Application module to which the configuration applies. The combination of site (warehouse), menu, and subsite (client) defines the context in which the configuration takes effect. |
| **Subsite** | Client to which the configuration applies. The combination of site (warehouse), menu, and subsite (client) defines the context in which the configuration takes effect. |

## Message fields

 
| Field | Description |
| --- | --- |
| **Locale** | Locale associated with the message. The message is displayed to users whose locale matches the message's locale. A locale defines a set of culture-specific components, such as language, time and date formats, currency formats, and a measurement unit system. |
| **Message Text** | Text to be displayed in the application. You can include HTML tags, except script-based tags, in this field to format your message. For example, entering "Add <b > Role</b>" in this field displays "Add **Role**". A preview of the message text as it will be displayed is provided in the **Message Preview** field. |
| **Menu** | Application menu associated with the message. The message is only displayed when working in the specified menu. |
| **Site** | Warehouse associated with the message. The message is only displayed when working with the specified warehouse. |
| Subsite | Client associated with the message. The message is only displayed when working with the specified client. |
| Message Preview | A preview of the message entered in the **Message Text** field as it will be displayed in the application. The preview field is especially useful to validate whether any HTML tags that you entered in the **Message Text** field are displayed as expected. This field is display only. |

## Bulk Copy fields

 
| Field | Description |
| --- | --- |
| **Menu** | Application menu associated with the message. The message is only displayed when working in the specified menu. |
| **Locale** | Locale associated with the message. The message is displayed to users whose locale matches the message's locale. A locale defines a set of culture-specific components, such as language, time and date formats, currency formats, and a measurement unit system. |
| **Site** | Warehouse associated with the message. The message is only displayed when working with the specified warehouse. |
| **Subsite** | Client associated with the message. The message is only displayed when working with the specified client. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
