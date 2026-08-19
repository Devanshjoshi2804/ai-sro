---
title: "Media"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/get_started/media.htm"
source: "/content/get_started/media.htm"
toc_path:
  - "Get started"
  - "Media"
sections:
  - "Media file association"
  - "Media storage"
  - "Manage a media file association"
  - "Media fields"
images:
  - "/content/resources/images/image602559.png"
  - "/content/resources/images/image602559.png"
  - "/content/resources/images/image602559.png"
  - "/content/resources/images/image1076421.png"
  - "/content/resources/images/image524298_14x14.png"
  - "/content/resources/images/image524298.png"
source_sha1: f72a4fbc75477d2145e9e339dce74cfac63fc808
---
# Media

You can associate a media file with an entity (such as a user or item) to provide visual information about the entity.

The following file categories and media file types are currently supported:

**Note**: Media with an unsupported file type cannot be displayed or downloaded in the application. To add a new file type, contact your Blue Yonder project team.

-   **FILE**
    
    -   .doc
        
        **Note**: You must have Microsoft Word installed to view .doc files.
        
    -   .pdf
        
        **Note**: You must have Adobe Reader installed to view .pdf files.
        
    -   .txt
-   **IMAGE**
    -   .bmp
    -   .gif
    -   .jpg and .jpeg
    -   .png

Media are represented by the following types of views:

-   **Thumbnail**: Miniature representation of a media file that is typically displayed in grids.
-   **Default**: System-sized representation of a media file that is typically displayed in the media tool.
-   **Enlarged**: Magnified representation of a media file that can be displayed from the media tool or when a thumbnail is clicked in a grid.

For the thumbnail and default views, if a media file is not associated with an entity, a placeholder image is displayed. If the media file cannot be displayed (for example, a network error prevents access to the media storage location), the media tool displays, "Image cannot be displayed".

**Note**: Media attributes and behavior (such as the media path and file size) are configured by the SYSTEM-INFORMATION/MEDIA policies in Policy Maintenance.

## Media file association

You can use the following methods to associate a media file with an entity:

-   **Media tool**: The media tool is displayed on pages that enable you to associate a media file with an entity (such as a user or item). Depending on the page, the media tool functions in one of the following modes:
    -   **Display-only**: If a media association exists, the media tool enables you to view the default and enlarged views of the media file. If a media association does not exist, the media tool displays a placeholder image.
    -   **Edit**: If a media association exists, the media tool enables you to view the default and enlarged views of the media file, change the media file associated with the entity, or remove the media file. If a media association does not exist, the media tool enables you to associate a media file with the entity.
-   **Add Media action**: The **Add Media** option is displayed in the **Actions** drop-down list for a selected entity on pages that enable you to associate a media file with an entity. When an entity is associated to a media file, **View Media** is also displayed as an option.

## Media storage

When you associate a media file with an entity, the media file is copied from the original file system (such as your PC or mobile device) to the server's file system where the media file is stored in a subfolder of the primary folder that is specified by the media configuration.

**Note**: The media path is configured by the SYSTEM-INFORMATION/MEDIA/MEDIA-PATH policy in Policy Maintenance.

If the media file is removed from the server storage folder without removing the corresponding media file association (for example, if the media file is manually deleted directly from the server's file system), instead of attempting to display the missing media file, the media tool displays, "Image cannot be displayed".

## Manage a media file association

You can associate a media file with an entity when ![Media settings](../../images/resources/images/image602559.png) is displayed on the media tool, or when an entity is selected and the **Add Media** and **View Media** options are displayed on the **Actions** drop-down list.

1.  To manage a media file association using the media tool:
    1.  Navigate to a page that displays the media tool.
    2.  To associate a media file with the entity:
        1.  Click ![Media settings](../../images/resources/images/image602559.png) **Add image**.
        2.  Click **Browse**, and then navigate to the media file and open it.
    3.  To change the media file associated with the entity:
        1.  Click ![Media settings](../../images/resources/images/image602559.png).
        2.  Click **Change Image**, and then navigate to the media file and open it.
    4.  To remove the media file association, perform one of the following tasks:
        -   If a Remove link is displayed under the image, click **Remove**.
        -   If no link is displayed, use the Media page to remove the image. See [Delete a media file](../administration/system-administrator/configuration/system/media.md).
    5.  Click **Close**.
    6.  To enlarge the view, click ![Enlarge](../../images/resources/images/image1076421.png).
2.  To manage a media file association using the media actions:
    1.  Navigate to a page that contains the media actions.
    2.  Select the check box on the row of the entity.
    3.  To associate a media file with an entity:
        1.  From the **Actions** drop-down list, select **Add Media**. The Add Media page is displayed.
        2.  Enter information in the [Media fields](#Media_fields).
        3.  Click **Save**.
    4.  To view a media file associated with an entity:
        1.  From the **Actions** drop-down list, select **View Media**. The Media page is displayed.
        2.  If the media file is an image, to enlarge the view, click the thumbnail.
        3.  If the media file is a digital document (such as TXT, DOC, or PDF), to download and view the file, click the thumbnail.
            
            **Note**: You must have the associated application installed to open DOC and PDF files.
            
        4.  Click ![Close](../../images/resources/images/image524298_14x14.png).
    5.  To delete a media file associated with an entity:
        1.  From the **Actions** drop-down list, select **View Media**. The Media page is displayed.
        2.  Select the check box next to the media thumbnail.
        3.  From the Actions drop-down list, select **Delete**. A confirmation message is displayed.
        4.  Click **OK**.
        5.  Click ![Close](../../images/resources/images/image524298.png).

## Media fields

 
| Field | Description |
| --- | --- |
| **Title** | User-defined name assigned to the media. Once assigned, this name is used to identify the media in the thumbnail and media display views. You can change this name at any time by modifying the media record. |
|  **Media** | Path to the location where the media file is stored. After a file is saved to the server, the field is blank. To view the default path where media is stored on the application server, view the SYSTEM-INFORMATION/MEDIA/MEDIA-PATH policy in Policy Maintenance. |
|  **Client** | Unique identifier for a client who houses product within a multi-client (third-party logistics) warehouse. The client ID distinguishes one client from another and allows the application to effectively manage product for multiple clients in one warehouse. This field is only displayed in a 3PL environment.<br > **Note**: If you do not select a client, the media is stored in the ALL\_CLIENT\_ID folder in the default media storage location on the server. |
| Tag | Alphanumeric text used to classify the media for search purposes. For example, you can apply a tag of "Assembly" to a media file, and then later retrieve all the files that share the same tag. |
| Original File Name | Original file name of the selected media. |
| File Type | File type of the selected media. If you attempt to add media that exceeds the configured limitations for that file type, you can compress your image. Compression reduces the actual file to the size limits defined in the application policy. As a result, a compressed image may display distorted. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
