---
title: "Item Override Config"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/item_override_configuration.htm"
source: "/content/item_override_configuration.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inventory"
  - "Items"
  - "Item Override Config"
sections:
  - "Select the item attributes that can be overridden by warehouse"
images: []
source_sha1: a1857ca9214050ae14907c634b8f02d27a847a5e
---
# Item Override Config

In a multi-warehouse environment, the item attribute values specified for master items apply to all of the warehouses unless specifically overridden for a particular warehouse.

If you allow warehouse-specific item configurations, you can select which item attributes can be overridden for a specific warehouse. See [Select the item attributes that can be overridden by warehouse](#Select_the_item_attributes_that_can_be_overridden_by_warehouse).

If warehouse-specific item configurations are allowed for selected attributes, then users can update items in the current warehouse with values that are different from the master item for one or more of the available attributes. See [Override item attributes for the current warehouse](item-overrides.md).

**IMPORTANT**: If warehouse-specific values are defined for an item, then updating the master item does not update the attributes that are overridden for a specific warehouse.

## Select the item attributes that can be overridden by warehouse

1.  Select **Configuration > Inventory > Items > Item Override Config**.
2.  Under **Available Attributes**, select the check box next to the item attributes that you allow users to override for a specific warehouse.
3.  Click **Save**.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
