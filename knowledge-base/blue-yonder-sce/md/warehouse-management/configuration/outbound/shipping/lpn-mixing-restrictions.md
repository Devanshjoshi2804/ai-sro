---
title: "LPN Mixing Restrictions"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/lpn_mixing_restrictions.htm"
source: "/content/lpn_mixing_restrictions.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Outbound"
  - "Shipping "
  - "LPN Mixing Restrictions"
sections:
  - "Configure LPN mixing restrictions"
images: []
source_sha1: dd55e9f71e8ea410a2aa934bfff665c20f6b179c
---
# LPN Mixing Restrictions

An LPN mixing restriction is a configuration that specifies the attributes of picked inventory that cannot be mixed on an LPN. LPN-level mixing restrictions only take effect in locations (based on location type) that are enabled to validate inventory mixing. For example, to prevent mixed-shipment LPNs from being deposited to a staging location, you can enable the staging location type to validate inventory mixing, and then specify Shipment as an LPN mixing restriction.

You can define LPN mixing restrictions based on item, inventory, order, and shipment attributes (such as item family, lot, expiration date, customer, shipment, or load). For a 3PL environment, client-specific LPN-level restrictions override those defined for the warehouse.

Validation takes place when picked inventory is moved to a location or to an LPN within a location that is configured to validate inventory mixing on LPNs. If the deposit would violate a restriction, the application presents a message and does not allow the operator to deposit the inventory to that location.

To define mixing restrictions for non-picked inventory, see [Storage Mixing Restrictions](../../inbound/storage/storage-mixing-restrictions.md).

## Configure LPN mixing restrictions

1.  Select **Configuration > Outbound > Shipping > LPN Mixing Restrictions**.
2.  Perform one of the following tasks:
    -   In a non-3PL environment, to configure mixing restrictions for an LPN, in the **Available** column, select the check box next to the attributes that should not be mixed on an LPN in a location configured to validate inventory mixing.
    -   In a 3PL environment, to configure mixing restrictions for an LPN:
        1.  Perform one of the following tasks:
            -   To add a client, click **Add**, and then from the **Client** drop-down list, select a client.
                
                **Note**: To define warehouse default restrictions, from the **Client** drop-down list, select Default. Client-specific restrictions override the warehouse default restrictions.
                
            -   To modify a client, in the grid, select the client.
            -   To copy a client configuration, in the grid, select the check box next to the client, click **Copy,** and then from the **Client** drop-down list, select the client.
        2.  In the **Available** column, select the check box next to the attributes for which different values are not allowed on the same LPN, when the LPN is in a location configured to validate inventory mixing.
        3.  Click **Apply**.
3.  Click **Save**.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
