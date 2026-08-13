---
title: "RF Outbound Audit Settings"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/rf_outbound_audit_settings.htm"
source: "/content/rf_outbound_audit_settings.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Outbound"
  - "RF Outbound Audit Settings"
sections:
  - "Setup"
  - "Configure RF outbound audit settings"
  - "RF Outbound Audit Settings fields"
images: []
source_sha1: ba0fbb0631ecd5660b670c5ca1b0a0ed9035a388
---
# RF Outbound Audit Settings

An outbound audit is a process that is performed by an RF operator to validate that the inventory picked for a shipment matches the expected inventory.

Audits can be performed on LPNs, orders, shipments, stops, or completed work assignments using both directed and undirected work. Audits are also performed by location, so if an audited shipment has inventory on two LPNs in two different locations, two pieces of work are created. You can audit or re-audit a shipment anytime after all the inventory for a shipment is picked but before loading begins.

For a single audit, many audit detail records may be created based on the number of different inventory attributes to be validated. For example, assume that the only attributes to be validated for an audit are item and lot. If the audited inventory is a single item and lot combination, only one detail record is created. However, if the inventory is a single item but from two different lots, then two detail records are created to account for both lots. Conversely, if the application is not configured to audit the lot, only a single detail record is created.

The operator must enter the item attributes blindly when performing an audit; attribute values are not auto-populated when an LPN is entered for audit.

**Note**: Inventory quantity is always validated at the end of an audit; however, if cartons or slots on a handling unit are being audited, the quantity is validated after each slot or carton.

The operator also has the ability to skip an entire LPN (or a carton or slot, when applicable) during an audit. When a LPN is skipped (or the audit for an LPN is complete), the application prompts the user for the next identifier. If there are no other LPNs to audit, the operator can complete the audit and a supervisor must investigate any skipped inventory.

Inventory under audit is automatically placed on hold to prevent it from being moved by an operator. The hold is automatically removed upon the successful completion of an audit. Failed audits must be manually reconciled by a supervisor, which may include removing a hold.

After a set of attributes for an item are validated, the application creates a history record for the item and attributes combination. These records are viewable in the Shipping application as shipping issues; this information gives you visibility to completed and pending audits, and can aid in resolving audit discrepancies.

### Setup

You must configure the following attributes to set up the outbound audit process:

1.  Configure the following RF outbound audit attributes:
    
    -   The movement zones in which a directed audit is automatically created when all picks for a shipment are completed and deposited to a zone
        
        **Note**: Undirected audits can be performed on any picked inventory regardless of whether the zone is configured to support directed audits.
        
    -   The default inventory attributes that operators must enter while performing an audit
    -   In a 3PL environment, the override attributes that operators must enter when auditing inventory for a specific client
    -   Whether operators must enter the quantity in a UOM that is smaller than the pallet-equivalent UOM when an LPN under audit contains identical inventory
    -   Whether audit discrepancy errors are displayed to operators immediately after an incorrect audit of a detail record or at the end of the entire audit
        
    -   Whether the alternate item UOM is populated when the auditor scans an alternate item.
        
    -   Whether the application prompts for an LPN when an operator performs an audit on a work assignment.
        
    
    See [Configure RF outbound audit settings](#Configure_RF_outbound_audit_settings).
    
2.  Define the outbound audit hold, and whether the hold allows the movement and adjustment of inventory that is under audit. See [Add or modify a hold](../inventory/holds/existing-holds.md).
3.  Define the following user role options:
    
    1.  Whether a role has permission to perform outbound audits (MTF - Outbound Audit).
    2.  Whether a role has permission to move inventory that is under an audit hold that allows movement (Remove RF Outbound Audit Hold).
        
        **Note**: Users with this permission also have access to the RF Remove Audit Hold screen, which allows them to manually remove a hold from inventory that failed an audit.
        
    
    See [Authorization](../../../administration/system-administrator/authorization.md).
    

## Configure RF outbound audit settings

1.  Select **Configuration > Outbound > RF Outbound Audit Settings**.
2.  Enter information in the [RF Outbound Audit Settings fields](#RF_Outbound_Audit_Settings_fields).
3.  Define the default inventory attributes that must be confirmed during an audit:
    1.  Click **Configure Default Audit Attributes**.
    2.  In the **Available** column, select the check box next to the attributes that operators must enter while performing an audit.
    3.  Click **Apply**.
4.  In a 3PL environment, to define the client override audit attributes:
    1.  Click **Override Audit Attributes by Client**.
    2.  Perform one of the following tasks:
        -   To add a client audit configuration, click **Add**, and then from the **Client** drop-down list, select a client.
        -   To modify a client audit configuration, in the grid, click the client.
    3.  In the **Available** column, select the check box next to the attributes that operators must enter while performing an audit on inventory for the client.
    4.  Click **Apply**.
5.  In a 3PL environment, select the clients for which an audit discrepancy error is immediately displayed to an operator:
    1.  Click **Audit Discrepancy Error**.
    2.  In the **Available** column, select the check box next to the clients for which an error is immediately displayed when an operator enters an incorrect attribute value.
        
        **Note**: For clients in the **Available** column, operators are prompted with discrepancy errors when the entire audit is complete.
        
    3.  Click **Apply**.
6.  In a 3PL environment, select the clients for which an operator is required to enter the audit quantity in a UOM that is smaller than the pallet-equivalent UOM if the inventory on a pallet LPN is identical:
    
    **Note**: This configuration prevents operators from entering a quantity of 1 if the inventory on a pallet is identical. Instead, the audit quantity must be entered in a lower UOM, such as cases.
    
    1.  Click **Prevent Pallet UOM Quantity for Clients**.
    2.  In the **Available** column, select the check box next to the clients for which the maximum UOM cannot be used when entering the audit quantity.
    3.  Click **Apply**.
7.  Specify the movement zones in which directed audits are automatically created when all picks for a shipment are completed and deposited to the zone:
    
    **Note**: Undirected audits can be performed on any picked inventory in any movement zone, regardless of this configuration.
    
    1.  Select **Movement Zone Configuration**.
    2.  In the **Available** column, select the check box next to the movement zones that apply.
    3.  Click **Apply**.
8.  In a 3PL environment, select the clients for which an audit discrepancy error is immediately displayed to an operator:
    1.  Click **Audit Discrepancy Error**.
    2.  In the **Available** column, select the check box next to the clients for which an error is immediately displayed when an operator enters an incorrect attribute value.
        
        **Note**: For clients in the **Available** column, operators are prompted with discrepancy errors when the entire audit is complete.
        
    3.  Click **Apply**.
9.  Click **Save**.

## RF Outbound Audit Settings fields

 
| Field | Description |
| --- | --- |
| Audit Discrepancy Error | If Yes, when a discrepancy occurs during the audit of a detail record, an error message is immediately displayed before the operator can audit the next detail record. Each detail record includes the inventory for shipment with identical attribute values. A discrepancy occurs when the attribute value entered by the operator is different from what the application expected.<br > For example, if a shipment with three LPNs is being audited and each LPN contains the same item but from different lots (three detail records), then if the operator enters an incorrect value for the first LPN, the error is displayed to the operator before moving to the second LPN.<br > **Note**: Audits can be completed despite the errors; the supervisor has visibility to the audit and can correct errors as needed.<br > If No, the audit discrepancy error is not displayed to the operator until the entire audit is finished (all detail records are complete). For example, if a shipment with three detail records is being audited and the operator enters an incorrect value for the first record, the error is not displayed until all three records have been audited.<br > **Note**: Regardless of this configuration, when quantities are validated and the entered quantity is less than the expected quantity, an error is only displayed after the entire audit is complete (and if the quantities still do not match). However, if the quantity is greater than expected, the error is immediately displayed. |
| Prevent Pallet UOM Quantity | If Yes, when an operator performs an audit on a pallet LPN that contains identical inventory (single detail record), the quantity must be entered in a UOM that is smaller than the pallet-equivalent UOM to prevent a quantity of 1 from being entered. For example, assume a full pallet holds 10 cases. If an audited pallet contains 8 cases of identical inventory, the operator could enter a pallet quantity of 1, even though the LPN is not a full pallet. To prevent this scenario, select Yes to ensure that the operator cannot enter the pallet-equivalent UOM quantity and instead must enter the case quantity of 8.<br > If No, operators can enter inventory quantities using the pallet-equivalent UOM for an LPN of identical inventory under audit. Select No if you do not require smaller UOM (more granular) quantities to be recorded for a pallet LPN under audit. With this option selected, operators may save time by not having to count smaller UOM quantities on a pallet LPN. |
| Ignore LPNs on Work Assignments | If Yes, then when an operator performs an audit on a work assignment, the application prompts for item, item attribute, and quantity information, but does not prompt for an LPN. When set to Yes, after an operator enters a work assignment ID, the application displays the item attributes to audit. When the operator enters item data, the application validates the attributes and picked quantity against the entire work assignment quantity (all LPNs combined) instead of what was expected for a specific LPN. For example, if a work assignment has an expected quantity of 10 on LPN1 and an expected quantity of 10 on LPN2, then when performing the audit, the operator can enter a quantity of 20 (expected combined quantity) without confirming a specific LPN. If there are multiple items on an LPN, then a quantity must be entered for each item.<br > **Note**: If you set this field to Yes and want to audit slots on a trolley, you must scan the master trolley LPN as the entity to audit so you can then enter the slots. If you scan the work assignment associated to the trolley being audited, the application bypasses the opportunity to enter the slots and the entire trolley is audited together.<br > If No, then the application prompts for an LPN, and then for the item, item attributes, and quantity that was picked to the LPN. If set to No, the operator must enter the information for each LPN. |
| Populate Alternate Item UOM | If Yes, then when an auditor scans an alternate item that has been configured with a UOM, the application populates the UOM field. The auditor can override the populated UOM. If no UOM is set for the alternate item, or if the auditor scans the master item, then the UOM field is not populated.<br > The application requires that a UOM is entered for RF outbound audits. Therefore, if there is no UOM defined for the alternate item, or if the auditor scans the master item, then the UOM must be manually entered.<br > If No, then the UOM field is not populated, and the auditor must enter the UOM value. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
