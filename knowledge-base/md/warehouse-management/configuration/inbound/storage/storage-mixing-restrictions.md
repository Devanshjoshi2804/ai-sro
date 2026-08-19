---
title: "Storage Mixing Restrictions"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/storage_mixing_restrictions.htm"
source: "/content/storage_mixing_restrictions.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inbound"
  - "Storage"
  - "Storage Mixing Restrictions"
sections:
  - "Precedence"
  - "Handling unit types"
  - "Configure storage mixing restrictions"
images: []
source_sha1: c797750bc121855731d30ecaf31d511988cd1bfb
---
# Storage Mixing Restrictions

An inventory mixing restriction is a configuration that specifies the item and inventory attributes for which different values that cannot be mixed in a location.

Warehouse, building, and zone-level mixing restrictions only take effect in pickable locations (as defined by the configuration of a storage zone). The application validates these mixing restrictions at the time of putaway, and does not direct putaway to a location that would violate applicable restrictions. For example, a mixing restriction can prevent storing items with different lot numbers or handling unit types in the same location.

-   Warehouse-level mixing restrictions apply to all pickable locations in the warehouse, except those for which building or zone restrictions are defined.
-   Building-level mixing restrictions apply to all pickable locations in the building, except those for which zone restrictions are defined.
-   Zone-level mixing restrictions apply to all pickable locations within the zone.

**Note**: Warehouse, building, and zone-level mixing restrictions are not compounded. The restrictions defined for a zone override those defined for a building and warehouse; the restrictions for a building override those defined for the warehouse.

LPN-level mixing restrictions only take effect on non-picked inventory in locations that are configured to validate inventory mixing (as defined by the configuration of the location type). The application validates LPN-level restrictions during deposit, and does not allow a deposit that would violate the LPN-level restrictions. For example, if you restrict item families on an LPN, then if the operator attempts to transfer a case to an LPN that contains a different item family, the application does not allow the deposit. In addition, the application would not allow the deposit of an LPN that contains more than one item family. For a 3PL environment, client-specific LPN-level restrictions override those defined for the warehouse.

You can define separate LPN mixing restrictions for picked inventory. See [LPN Mixing Restrictions](../../outbound/shipping/lpn-mixing-restrictions.md).

## Precedence

LPN-level inventory mixing restrictions defined for non-picked inventory are always applied during the deposit of non-picked inventory to locations configured (by location type) to validate inventory mixing.

Warehouse, building, and zone inventory mixing restrictions only apply to the putaway of inventory to pickable locations. These restrictions are not compounded. Instead, zone restrictions override those defined for the building and warehouse; and building restrictions override those defined for the warehouse.

The following table is an example of a mixing restriction configuration.

 
| Level | Restriction |
| --- | --- |
| Storage Zone A | Item family |
| Storage Zone B | None |
| Storage Zone C | None |
| Building 001 | Lot |
| Building 002 | None |
| Warehouse WMD1 | Inventory status |

For this example:

-   Storage Zones A and B are located in Building 001
-   Storage Zone C is located in Building 002
-   Buildings 001 and 002 are both located in Warehouse WMD1

Based on the example values, the application prevents mixing in the following locations:

-   Storage Zone A = Prevents mixing item families (zone restriction overrides building and warehouse restrictions)
-   Storage Zone B = Prevents mixing lots (building restriction overrides warehouse restriction; no restriction for zone)
-   Storage Zone C = Prevents mixing inventory statuses (warehouse restriction applies because there is no restriction for building or zone)

## Handling unit types

You can prevent the mixing of serialized and non-serialized handling unit types regardless of the inventory stored on the handling units.

The restriction prevents mixing handling unit types in the same location at the same time, even if the inventory on the handling units is allowed to be mixed. For example, use this restriction for locations that can support different handling unit types, but not multiple types at the same time.

## Configure storage mixing restrictions

1.  Select **Configuration > Inbound > Storage > Storage Mixing Restrictions**.
2.  To configure mixing restrictions for the current warehouse:
    1.  Select **Warehouse**.
    2.  In the **Attribute** column, select the check box next to the attributes that apply. The selections are displayed in the **Warehouse Inventory** column.
    3.  Click **Save**.
3.  To configure mixing restrictions for a building:
    1.  Select **Building**.
    2.  From the **Available in** drop-down list, select a building.
    3.  In the **Attribute** column, select the check box next to the attributes that apply. The selections are displayed in the **Building Inventory** column.
    4.  Click **Save**.
4.  To configure mixing restrictions for a storage zone:
    1.  Select **Storage Zone**.
    2.  From the **Available in** drop-down list, select a storage zone.
    3.  In the **Attribute** column, select the check box next to the attributes that apply. The selections are displayed in the **Storage Zone Inventory** column.
    4.  Click **Save**.
5.  To configure mixing restrictions for LPNs:
    1.  Select **LPN**.
    2.  Perform one of the following tasks:
        -   For a non-3PL environment, in **Attribute** column, select the check box next to the attributes that apply. The selections are displayed in the **LPN Inventory** column.
        -   For a 3PL environment, configure client-specific LPN mixing restrictions:
            1.  Perform one of the following tasks:
                -   To add a client, click **Add**, and then from the **Client** drop-down list, select a client.
                    
                    **Note**: To define warehouse default restrictions, from the **Client** drop-down list, select Default. Client-specific restrictions take precedence over warehouse default restrictions.
                    
                -   To modify a client, in the grid, select the client.
                -   To copy a client, in the grid, select the check box next to the client, click **Copy**, and then from the **Client** drop-down list, select a client.
            2.  In the **Attribute** column, select the check box next to the attributes that apply. The selections are displayed in the **LPN Inventory** column.
    3.  Click **Apply**.
6.  Click **Save**.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
