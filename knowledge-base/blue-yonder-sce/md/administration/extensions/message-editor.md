---
title: "Message Editor"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/admin/message_editor.htm"
source: "/content/admin/message_editor.htm"
toc_path:
  - "Administration"
  - "Extensions"
  - "Message Editor"
sections:
  - "Message types"
  - "Message hierarchy"
  - "Message identifiers"
  - "Modify message text"
  - "Copy a message"
  - "Copy multiple messages"
  - "Delete a message"
  - "Message fields"
  - "Bulk Copy fields"
images:
  - "/content/resources/images/image598345.png"
  - "/content/resources/images/image598345.png"
source_sha1: a032f80e63aa239c4b13b54c0dd738ed28be9f3a
---
# Message Editor

You use the Message Editor to manage messages. A message represents a text string that is displayed on the web user interface (UI), such as a page title, task, button label, field label, and notification text. Messages are stored separately from the rest of the application's code so that they can be translated and extended (configuring a distributed entity to meet your unique business needs). Messages enable you to modify the displayed text to match your preferred business terminology, for example, referring to inventory in a warehouse as SKUs instead of Items.

**Example**: You want to modify all applicable messages from Item to SKU. To accomplish this, you would perform the following tasks on the Message Editor:

1.  Use a filter to limit the messages returned to those containing the word Item.
2.  Modify the first message listed by replacing Item with SKU.
3.  Save the change and modify the next message.
4.  Continue to replace Item with SKU for each message.

**Note**: There may be instances in which a message displayed on a specific web UI page is not available in the Message Editor. Some web UI messages and all server-side messages that are displayed on Supply Chain Execution (SCE) client windows, RF and mobile devices, and reports are maintained using Message Catalog. See [Message Catalog](../system-administrator/configuration/internationalization/message-catalog.md).

## Message types

A message is one of the following types:

-   **Distributed**: A message provided with the standard application and framework that cannot be modified or deleted.
-   **Extension**: A message added by a user with extensibility permissions or by consulting services and displays a check mark in the **Extension** column of the grid on the Message Editor. Extension messages are added by copying or modifying a distributed message. When an extension message is created, the corresponding distributed message is no longer displayed in the grid. A corresponding distributed message matches the name, namespace, locale, menu, site or warehouse, and subsite or client of the extension message. If all extension messages that were created by copying or editing a distributed message are deleted, the corresponding distributed message is again displayed in the grid.

## Message hierarchy

When more than one message applies to a user interface element, the application uses the following order (from first to last) to determine the message that is displayed:

1.  User-specified message (extension)
2.  Services-specified message (extension)
3.  Product-specified message (distributed)
4.  Framework-specified message (distributed)

Messages can be further extended by specifying one or more optional attributes, such as warehouse (site) and client (subsite), so that the message is only displayed when the attribute matches. However, when working with multiple warehouses or clients, the application reverts to the most relevant message (user-specific, services-specific, product-specific, or framework-specific) that is not associated with an attribute. For example, if the distributed message Item is extended to be SKU for Client A and Part for Client B, then when only Client A is associated with the message, SKU is displayed, and when only Client B is associated with the message, Part is displayed. However, if both Client A and Client B can be associated with the message, Item (the distributed message) is displayed.

## Message identifiers

Each message is internally identified by the following fields:

-   **Name**: Unique internal identifier within a namespace that represents a message. The message's message text is displayed in the application instead of the namespace and name, unless there is an issue loading the message.
-   **Namespace**: Unique internal identifier that specifies the scope or context of a name and is used to logically group related names. A name is unique within a namespace but can be reused in a different namespace. The namespace is internally associated with libraries, menus, and pages.

The name and namespace are informational; you should not need to use or specify them.

## Modify message text

If you are modifying a distributed message, the application uses the different message text to automatically create an extension message based on the distributed message. Otherwise, the application updates the message text of the extension message that you are modifying.

1.  Select **Extensions > Message Editor**.

1.  To limit the list of messages that is displayed, enter search criteria or select a filter. See [Filters](../../get-started/filters.md).

3.  In the message's row, click ![Edit](../../../images/resources/images/image598345.png).
4.  In the **Message Text** field, enter text to be displayed in the application. You can include HTML tags, except script-based tags, in this field to format your message. For example, entering "Add <b > Role</b>" in this field displays "Add **Role**". A preview of the message text as it will be displayed is provided in the **Message Preview** field.
    

1.  Click **Save**, or to save and modify the message text in the next row, click **Save & Next**.

## Copy a message

1.  Select **Extensions > Message Editor**.

1.  To limit the list of messages that is displayed, enter search criteria or select a filter. See [Filters](../../get-started/filters.md).

3.  Select the check box next to the message, and then click **Copy**.
4.  Enter information in the [Message fields](#Message_fields).
5.  Click **Save**. A check mark is displayed in the **Extension** column in the grid.

## Copy multiple messages

You can add multiple messages at the same time.

1.  Select **Extensions > Message Editor**.

1.  To limit the list of messages that is displayed, enter search criteria or select a filter. See [Filters](../../get-started/filters.md).

1.  In the grid, select the check boxes next to the messages to copy.
    
    **Note**: In the grid, press and hold **Shift** to select consecutive values or press and hold **Ctrl** to select nonconsecutive values.
    
2.  Click **Copy**. The Bulk Copy window is displayed.
3.  To make the same modification to multiple messages:
    1.  Select the check boxes next to the messages.
    2.  Above the grid, enter information in the [Bulk Copy fields](#Bulk_copy_fields).
    3.  Click **Save**.
4.  To modify an individual message:
    1.  In the message's row, click ![Edit](../../../images/resources/images/image598345.png).
    2.  Enter information in one or more of the [Message fields](#Message_fields).
    3.  Click **Save**, or to save and modify the message text in the next row, click **Save & Next**.
        

## Delete a message

You can only delete extension messages. Deleting all of the extension messages that were based off of the same distributed message reinstates the use of the distributed message.

1.  Select **Extensions > Message Editor**.

1.  To limit the list of messages that is displayed, enter search criteria or select a filter. See [Filters](../../get-started/filters.md).

1.  Select the check box next to the message.
2.  Click **Delete**. A confirmation message is displayed.
3.  Click **Yes**. If a results message is displayed, click **OK**.

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
