---
title: "External Page"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/admin/external_page.htm"
source: "/content/admin/external_page.htm"
toc_path:
  - "Administration"
  - "Extensions"
  - "Page Builder"
  - "External Page"
sections:
  - "Add or modify an external type page"
images: []
source_sha1: 846ef48bbe883f89d9991ce0ba4ccd4e09f78659
---
# External Page

An external type page displays a webpage within a frame on the page, (referred to as an iframe) to provide access to content that resides outside of the web client.

When you configure an external type page, you define the following components:

-   **URL**: URL to a webpage, such as a single webpage or a web-based application.
    
    **Note**: The server on which the portal server instance is installed, or the portal server instance itself, may be configured with security restrictions (such as content security policies or protocol restrictions) that prevent content from being displayed in an embedded iframe. A system administrator may need to update the server security settings or the portal server instance configuration settings to allow external content to be displayed within the web client.
    
-   **URL Parameters**: Values included in the URL other than the base protocol, host domain, and path. In the event that a URL contains additional values, Page Builder parses and removes the additional parameters to create a simplified URL. For example, the application converts **https://mycompany.corp/1?mykey=myvalue&destination=%2F&pageId=9945#Content** to **https://mycompany.corp/1**. The remaining parameters are displayed in the URL Parameter list.

After you add an external type page, you must add the page to a menu and assign roles that can access the page. You can then view the page.

## Add or modify an external type page

1.  Select **Extensions > Page Builder**.
2.  Perform one of the following tasks:
    -   To add an external page, from the **Actions** drop-down list, select **Add External Page**.
    -   To modify an external page, in the grid, click the title.
    -   To copy an external page, in the grid, select the page row (without clicking the title), and then from the **Actions** drop-down list, select **Copy**.
3.  Enter information in the following fields:
    
     
    | Field | Description |
    | --- | --- |
    |  **Title** | Text to display at the top of the page. |
    | **Description** | Text that provides additional information about the page, such as its purpose, and why and how it is used. The description is not displayed on the page. |
    
4.  In the **URL** field, enter the URL of the webpage to be displayed.
    
    **Note**: When a URL is entered containing multiple parameters, Page Builder parses the data and updates the URL field with a simplified URL. The simplified URL consists of the base protocol, host domain, and path. The remaining values and fragments formerly within the URL are displayed under the URL Parameters section.
    
5.  To test the page:
    1.  Click **Preview**.
        
        **Note**: If the page is not displayed, the server on which the portal server instance is installed, or the portal server instance itself, may be configured with security restrictions. Contact a system administrator to update the server security settings or the portal server instance configuration settings to allow external content to be displayed within the web client.
        
    2.  Review the information on the page.
    3.  Click **Back**.
6.  Click **Save**.
7.  To add the page to a menu, see [Add or modify a menu](../menu-editor.md).

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
