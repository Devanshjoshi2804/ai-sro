---
title: "Storage Settings"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/storage_settings.htm"
source: "/content/storage_settings.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inbound"
  - "Storage"
  - "Storage Settings"
sections:
  - "LPN Composition"
  - "Example: Full LPN"
  - "Example: Half LPN"
  - "Example: Heavy LPN"
  - "Example: Pieces"
  - "Configure storage settings"
  - "Storage Settings fields"
images: []
source_sha1: e59d8eef5262bd269d457029f8bf225cac8e00ca
---
# Storage Settings

You can configure the attributes and behavior for depositing inventory, and define the attributes that can be used in search path configurations. Specifically, you can configure the following storage settings:

-   Deposit sequence in which the LPNs are displayed to an RF operator
-   Movement zones in which the application automatically deposits picked inventory
-   Movement zones in which the operator can deposit all the sub-LPNs or detail LPNs on an LPN at once to the same location, without having to confirm each one
-   LPN composition attributes. These attributes can be defined for use on a storage search path (including location preference rules) to limit the path to inventory that matches the attribute values.

## LPN Composition

The LPN composition attributes are values that can be assigned to a storage search path or location preference rule to limit use of the path or rule to inventory that matches the attribute.

### Example: Full LPN

The value for Full LPN defines the percentage of an LPN that represents a full LPN. The LPN is physically full when it contains the quantity defined for the pallet-equivalent UOM on the item footprint. You can specify a value less than 100 percent to represent a full LPN for the purpose of storing the inventory.

For example, for an item footprint defined by 1 each, 10 eaches per case, 10 cases (100 eaches) per pallet, the following calculations apply:

-   If Full LPN = 100%, then if there are 10 cases on the LPN, the application uses the search path to which this attribute is assigned.
-   If Full LPN = 90%, then if there are at least 9 cases on the LPN, the application uses the search path to which this attribute is assigned.
-   If Full LPN = 90%, then if there are less than 9 cases on the LPN, the application does not use the search path to which this attribute is assigned.

### Example: Half LPN

The value for Half LPN defines the percentage that qualifies a partial pallet LPN for storage in a search path or location preference rule that uses this attribute. An LPN that contains an amount equal to or greater than the value for Half LPN, but less than the value for Full LPN, represents a half pallet.

**Note**: The LPN is physically full when it contains the quantity defined for the pallet-equivalent UOM on the item footprint.

For example, for an item footprint defined by 1 each, 10 eaches per case, 10 cases (100 eaches) per pallet, the following calculation applies:

-   If Full LPN = 90% and Half LPN = 50%, then if an LPN contains at least 50 eaches but less than 90 eaches, the application uses the search path to which this attribute is assigned.

### Example: Heavy LPN

The value for Heavy LPN defines the weight at which an LPN is considered heavy. If the weight of an LPN is equal to or greater than the value for Heavy LPN, then the application uses the search path to which this attribute is assigned.

For example, if Heavy LPN is set to 50 pounds, then for an item footprint where 1 case = 10 pounds and 1 pallet = 100 pounds (10 cases), the following calculations apply:

-   If the LPN contains 5 or more cases of the item (50 pounds or more), the application can use the search path to which this attribute applies.
-   If the LPN contains less than 5 cases of the item, the application does not use the search path to which this attribute applies.

### Example: Pieces

The value for Pieces defines a minimum unit quantity. An LPN that contains a quantity equal to or greater than the value for Pieces qualifies for storage in a search path or location preference rule that uses this attribute.

For example, if the value for Pieces is set to 200, then the following calculations apply:

-   If an LPN contains 200 or more eaches, the application can use the search path to which this attribute applies.
-   If the LPN contains less than 200 eaches, the application does not use the search path to which the attribute applies.

## Configure storage settings

1.  Select **Configuration > Inbound > Storage > Storage Settings**.
2.  Enter information in the [Storage Settings fields](#Storage_Settings_fields).
3.  To select the zones in which the application automatically deposits picked inventory:
    
    **Note**: If a zone is assigned to allow auto-deposit, then when an RF operator exits out of picking, the operator is not required to scan the deposit location; instead, the LPNs are automatically deposited. For example, you may configure a zone that contains conveyor locations to be auto deposit zones, so that when carton picks are complete, cartons are automatically deposited to the conveyor.
    
    1.  Click **Auto Deposit Movement Zones**.
    2.  In the **Available** column, select the check box next to the zones that apply.
    3.  Click **Apply**.
4.  To select the movement zones in which the operator can deposit all the sub-LPNs or detail LPNs on an LPN at once to the same location, without having to confirm each one:
    
    **Note**: In the selected movement zones, if all the inventory on an LPN is going to the same location, an operator can deposit all the sub-LPNs or detail LPNs at once. If any of the sub-LPNs or detail LPNs are destined for a different location, then the operator must confirm each sub-LPN or detail LPN to deposit it.
    
    1.  Click **Confirm Sub/Detail LPN Deposits Once**.
    2.  In the **Available** column, select the check box next to the zones that apply.
    3.  Click **Apply**.
5.  To set the deposit sequence in which LPNs are displayed to an RF operator for deposit when moving multiple LPNs at the same time:
    
    **Note**: The deposit sequence is only valid if the **Force Inventory Deposit Visibility** field is set to Yes. The deposit sequence can be based, for example, on the order in which LPNs were picked up (last LPN picked up is the first to be deposited).
    
    1.  Click **Deposit Sequence**.
    2.  To select criteria from displayed entities:
        1.  If the advanced query is displayed, click **Simple**.
        2.  If the available entities are not displayed, click **Show Available**.
        3.  In the **Available** grid, select the entities that you want to use as criteria.
        4.  Click **Add selected**. The entities are added to the **Selected** grid.
        5.  To remove criteria, in the **Selected** grid, select the criteria to remove, and click **Remove selected**.
        6.  To reorder the criteria, in the **Selected** grid, click a row, and then click the up or down arrow to move the selected criteria. The application applies the criteria in sequential order according to how it is displayed in the grid.
    3.  To enter criteria using database entities, click **Advanced**, and then enter the column and field name, using a period to separate the column and field. Multiple column and field entries must be separated by a comma and space.
        
        You can use operators like IS NULL or IS NOT NULL to build an advanced query. For example, <column name>.<field name > IS NOT NULL, <column name>.< field name>.
        
    4.  Click **Apply**.
6.  To specify the inventory attributes that must match on a mixed-item LPN for the LPN to be stored in a location:
    
    **Note**: A mixed-item LPN is an LPN that contains different items or the same item with different attributes. If the inventory attribute values match the selected inventory attributes, then the mixed-item LPN can be stored in a mixed-item location. If they do not match, the items are stored separately. This option is only available if the **Mixed LPN** field is set to No.
    
    1.  Click **Inventory Attributes for Mixed LPN**.
    2.  In the **Available** column, select the check box next to the inventory attributes that must match.
    3.  Click **Apply**.
7.  Click **Save**.

## Storage Settings fields

 
| Field | Description |
| --- | --- |
| Force Inventory Deposit Visibility | If Yes, during inventory deposit, when multiple LPNs exist on an operator's RF device, a deposit screen is displayed listing the deposit location and pallet position for each of the LPNs. The RF operator can scan or select an LPN from the list and deposit it. This lets the operator choose the next best LPN to deposit based on the deposit sequence. If there is only one LPN on the RF device, then the standard deposit screen is displayed.<br > If No, the operator is not able to select which LPN to deposit. |
| Allow Location Entry on Override | If Yes, then during a deposit location override, the operator can select a new location for the inventory deposit. If the operator does not enter a location, the operator is directed to a location selected by the application.<br > If No, then during a deposit location override, the operator is directed to a location selected by the application and does not have the option to select a different location. |
| Full LPN | Percentage at which an LPN is considered a full LPN for the purpose of storage. The Full LPN attribute can be assigned to a storage search path to indicate that the path is used for LPNs that match this attribute.<br > An LPN is physically full when it contains the quantity defined by the item footprint for the pallet equivalent UOM. If you require LPNs to be completely full to be considered full LPNs, then enter 100%.<br > Select a value less than 100 if you allow partial LPNs, such as those that contain 90% of the full quantity for the UOM, to be considered full LPNs for storage on the search path. |
| Half LPN | Percentage at which an LPN is considered a half LPN. The Half LPN attribute can be assigned to a storage search path to indicate that the path is used for LPNs that match this attribute.<br > An LPN is physically full when it contains the quantity defined by the item footprint for the pallet equivalent UOM.<br > A half LPN is an LPN that has a quantity equal to or greater than what is defined for **Half LPN** and less than what is defined for **Full LPN**. For example, enter 50% to store LPNs that have a quantity of at least 50% but less than the percentage defined for a full LPN. |
| Heavy LPN | Minimum weight of an LPN for it to be considered heavy for storage purposes. To change a measurement unit, click the unit next to the field, and select a different unit.<br > The **Heavy LPN** attribute can be assigned to a storage search path to indicate that the path is used for LPNs that match this attribute. An LPN that is equal to or greater than this value is considered for storage in a search path that uses this attribute. This option is typically used to direct heavy LPNs to floor or lower rack locations. |
| Pieces | Minimum number of pieces on an LPN for the LPN to be considered for storage using this attribute. The **Pieces** attribute can be assigned to a storage search path to indicate that it is used for LPNs that match this attribute. This attribute is typically used to direct LPNs that contain a unit quantity equal to or greater than this value to a piece storage location. |
| Mixed LPN | If Yes, then items on a mixed-item LPN are stored in separate locations. Select Yes if you want to store inventory on a mixed LPN separately, so that each item is deposited to a separate location.<br > If No, then a mixed-item LPN can be stored in a single location. The application stores the mixed LPN in a single location if doing so does not violate mixing restrictions and if the selected attributes match, as defined by the **Inventory Attributes for Mixed LPN** field. |
| Check for Partial Sub-LPNs | If Yes, then during putaway, the application checks the LPN to determine whether it contains partial case quantities and, if so, uses a storage path that contains this attribute. The full case quantity is defined by the configuration of the item footprint case-equivalent UOM. For example, if a case UOM has 10 eaches per case, and the LPN contains 100 eaches, then the application determines that there are no partial LPNs. However, if a case UOM has 10 eaches per case, and the LPN contains 95 eaches, then the application determines that there is one partial LPN and uses a storage search path that supports this configuration.<br > If No, the application does not check the LPN to determine whether it contains partial case quantities. |
| Consigned Inventory | If Yes, the application determines whether any inventory on an LPN is consigned inventory before attempting to find a storage search path for the LPN. Consigned inventory is inventory that belongs to the supplier; in other words, ownership of the inventory has not yet been transferred from the supplier to the warehouse. Select Yes if you want this check to be performed on inventory prior to storing it.<br > If No, the application does not determine whether inventory on an LPN contains consigned inventory before attempting to find a storage path for the LPN. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
