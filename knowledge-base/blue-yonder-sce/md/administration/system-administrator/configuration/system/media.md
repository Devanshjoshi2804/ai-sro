---
title: "Media"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/admin/media_config.htm"
source: "/content/admin/media_config.htm"
toc_path:
  - "Administration"
  - "System Administrator"
  - "Configuration"
  - "System"
  - "Media"
sections:
  - "Media thumbnails"
  - "Add or modify a media file"
  - "Delete a media file"
  - "Media fields"
images: []
source_sha1: 82a125ad8dfd5bb8924202b25a41239894616fad
---
# Media

You can add, store, and retrieve media (such as image and digital document files) based on applicable policies, as well as any client access restrictions that are placed on the media in a 3PL environment.

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

## Media thumbnails

A media thumbnail is a miniature representation of a media file. The maximum size of the thumbnail that is displayed is configurable.

Thumbnails enable you to navigate through and identify media files without consuming valuable application resources required to download the full version of each file. When you locate a thumbnail for a file that you want to view, depending on the context, you can click or double-click the thumbnail to display or play the full version of the selected file.

Thumbnails differ depending on the media that they represent. Thumbnails display in the following ways:

-   Image files are displayed as smaller versions of the full image file. You can click these images to display the full-sized image.
-   Digital document files are displayed as a default image intended to represent a PDF. You can click these images to open the PDF in a browser or Adobe Reader.
-   Text files are displayed as a configurable default image to represent the text file. You can click this image to download the file.

The maximum size of thumbnail images and the default thumbnail images for text files are set by policies.

Thumbnail images are created and stored on the server in the same directory as the full image. The file name of the thumbnail is <mediafilename>\_T, where <mediafilename > is the original file name of the image that the thumbnail represents. For example, a thumbnail created for a media file named "trailer.jpg" would be saved as "trailer\_T.jpg" and stored in the same directory as the image that it represents.

## Add or modify a media file

You use this procedure to maintain the media for your application. In a 3PL environment, the Media page displays all media files that are available for clients authorized for the logged-in user. In a non-3PL environment, the Media page displays all media files available for use.

After you have added media files, you can use Media to view, modify the attributes of, and delete media files when necessary.

**Note**: To associate a media file with an entity, see [Manage a media file association](../../../../get-started/media.md).

1.  Select **System Administrator > Configuration > ** **System > Media**.
2.  Perform one of the following tasks:

-   To add a media file, from the **Actions** drop-down list, select **Add**.
-   To modify the attributes of a media file, in the grid click the media ID.
-   To display or download a media file, in the grid click the media thumbnail. See [Media thumbnails](#Media_thumbnails).

4.  Enter information into the [Media fields](#Media_fields).
    
5.  Click **Save**. A confirmation message is displayed.
6.  Click **OK**.

## Delete a media file

**Note**: If you delete a media file that is currently being used (that is, it is associated with a record), the association is removed also.

1.  Select **System Administrator > Configuration > ** **System > Media**.
2.  In the grid, select the check box on the row of the media file.
3.  From the **Actions** drop-down list, select **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Media fields

 
| Field | Description |
| --- | --- |
| Title | User-defined name assigned to the media. Once assigned, this name is used to identify the media in the thumbnail and media display views. You can change this name at any time by modifying the media record. |
| Media | Path to the location where the media file is stored. After a file is saved to the server, the field is blank. To view the default path where media is stored on the application server, view the SYSTEM-INFORMATION/MEDIA/MEDIA-PATH policy in Policy Maintenance. |
| Client | Unique identifier for a client who houses product within a multi-client (third-party logistics) warehouse. The client ID distinguishes one client from another and allows the application to effectively manage product for multiple clients in one warehouse. This field is only displayed in a 3PL environment.<br > **Note**: If you do not select a client, the media is stored in the ALL\_CLIENT\_ID folder in the default media storage location on the server. |
| Tag | Alphanumeric text used to classify the media for search purposes. For example, you can apply a tag of "Assembly" to a media file, and then later retrieve all the files that share the same tag. |
| Original File Name | Original file name of the selected media. |
| File Type | File type of the selected media. If you attempt to add media that exceeds the configured limitations for that file type, you can compress your image. Compression reduces the actual file to the size limits defined in the application policy. As a result, a compressed image may display distorted. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
