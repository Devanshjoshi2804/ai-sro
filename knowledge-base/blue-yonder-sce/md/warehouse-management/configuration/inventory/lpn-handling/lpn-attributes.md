---
title: "LPN Attributes"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/lpn_attributes.htm"
source: "/content/lpn_attributes.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inventory"
  - "LPN Handling"
  - "LPN Attributes"
sections:
  - "Configure LPN attributes"
images: []
source_sha1: 6d234bd7989409aa2b14340d0de108cae9adedf7
---
# LPN Attributes

An LPN attribute is a user-defined, LPN-level packaging requirement that is assigned to support the preferences of a customer, customer type, or supplier. For example, if a customer requires that pallets of inventory be wrapped and labeled on all four sides, LPN attributes for wrapping and labeling can be specified on the customer's order lines. During order processing, the application prompts operators to perform or verify the attributes prior to shipping.

LPN attributes typically represent processes that can be applied or performed by warehouse personnel. This is different from an inventory attribute, such as a lot, that cannot be physically changed.

Enabling an LPN attribute makes it available to be displayed or selected in the following situations:

-   During product identification and inventory attribute change operations where the LPN attributes can be applied to inventory that is being received, identified, or changed
-   During picking to prompt the operator to pick inventory that matches the LPN attribute requirement
-   On an order line, where you can specify whether the LPN attributes are required or not allowed for inventory on the order line
-   During configuration of the following entities:
    -   **Suppliers**: You can specify receiving default values for LPN attributes by supplier, supplier item, and supplier item footprint.
    -   **Customers**: You can specify by customer the LPN attribute requirements for shipped inventory.
    -   **Customer types**: You can specify by customer type the LPN attribute requirements for shipped inventory.

## Configure LPN attributes

You can provide a user-defined label and device label for up to five LPN attributes.

1.  Select **Configuration > Inventory > LPN Handling > LPN Attributes**.
2.  In the grid, enter information in the following fields:
    
     
    | Field | Description |
    | --- | --- |
    | Label | Name for the attribute that is displayed on workstation windows. |
    | Device Label | Name for the attribute that is displayed on RF device screens. |
    | Enabled | If Yes, the attribute is available for use and selection during warehouse configuration and processing. If No, the attribute is not displayed on either workstation windows or RF screens. Select No if you do not want to use an attribute. |
    
3.  Click **Save**. A confirmation message is displayed.
4.  Click **OK**.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
