---
title: "Reverse Receiving"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/reverse_receiving.htm"
source: "/content/reverse_receiving.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inbound"
  - "Receiving"
  - "Reverse Receiving"
sections:
  - "Configure reverse receiving"
  - "Reverse Receiving fields"
images: []
source_sha1: 221d9aecb17fc1cf87ea5b019174f040579522c6
---
# Reverse Receiving

Reverse receiving is the process of removing an LPN or quantity of inventory from the application after the inventory is identified and received into the warehouse. This process can be used, for example, if inventory was identified incorrectly with a wrong item, lot, or quantity during receiving. This process, if enabled, is only allowed when inventory is received into a physical location in the warehouse, such as a storage or staging location, or a location reserved for damaged inventory.

If reverse receiving is enabled, a user can choose to reverse inventory for an LPN (pallet), sub-LPN (case), or detail-LPN (each or piece). As a result of this process, the received quantity that is reversed is based on the identifier that the user selected. This means, for example, that a sub-LPN can be reversed from a full pallet LPN.

When you configure reverse receiving, you specify the following attributes:

-   Whether reverse receiving is enabled. If reverse receiving is not enabled, receiving inaccuracies can be corrected using inventory adjustment operations.
-   Whether the LPN that identifies the inventory is deleted from the application. If the LPN is deleted, then the user can scan the same LPN label again when receiving the same inventory with the correct information. If the LPN is not deleted, then the user must re-label the inventory with a new LPN to identify the inventory.
-   The action that occurs when an LPN is reversed. The action determines whether the reversal takes the inventory out of the four-wall location in which it is currently residing. If inventory is moved out of the four-wall location, then it is no longer tracked as residing in the warehouse.
    
    The action also determines whether the quantity of the LPN that is reversed is decremented from the order line used to receive it.
    
    **Note**: It is recommended that the inventory be removed from the four-wall location and decremented from the order line so that, if needed, it can be received again correctly.
    

If a handling unit is associated with the inventory that is reversed, the handling unit is automatically removed along with the inventory. However, the application supports receiving empty handling units, and so the reverse receiving process can also be used to reverse the receipt of empty handling units. In association with this process, you can configure the application to delete the handling unit from the application when the receipt of an empty handling is reversed. See [LPN Handling](../../inventory/lpn-handling.md).

## Configure reverse receiving

1.  Select **Configuration > Inbound > Receiving > Reverse Receiving**.
2.  Enter information in the [Reverse Receiving fields](#Reverse_receiving_fields).
    
3.  Click **Save**.

## Reverse Receiving fields

 
| Field | Description |
| --- | --- |
| Allow Reverse Receiving After Close | If Yes, a user can perform reverse receiving after the inbound shipment has been closed.<br > If No, reverse receiving cannot be performed after the inbound shipment has been closed.<br > **Note**: Typically, when an inbound shipment is closed, a transaction is sent to the host on what was received. If the inbound shipment is reopened and an LPN is reversed, then when the same inbound shipment is closed the second time, the receiving information is sent to the host again. Some host applications cannot process closing the same inbound shipment twice. |
| Delete LPN | If Yes, when a user performs reverse receiving, the LPN is removed from the application. Select Yes if you want to be able to re-receive the inventory using the same LPN label.<br > If No, when a user performs reverse receiving, the LPN remains in the application. If you select No, the user cannot re-identify the inventory using the same LPN label. If the same LPN is scanned again during receiving, a message is displayed to the operator notifying them that the LPN already exists in the application. |
| Reverse Receipt Action | Determines the action the application takes when an LPN is reversed.<br>-   • **Move LPN out of 4 wall location and decrement received quantity on inbound order line (recommended)**: This option deletes the inventory quantity from the location and from the order line on which it was received.
<br>-   • **Move LPN out of 4 wall location and do not change received quantity on inbound order line**: This option deletes the inventory quantity from the location, but does not change the quantity on the order line.
<br>-   •
    
    **Do not move LPN out of 4 wall and decrement received quantity on inbound order line**: This option records the inventory quantity as physically existing in the four-wall location; however, it deletes the quantity from the order line.
    
    <br>
    
    **Note**: Inventory in a four-wall location is included in inventory summaries that are sent to the host.
    
    <br> |
| Defer Receipt Reversals | If Yes, then when an operator reverses a receipt, the application defers sending the Receipt Reversals transaction to the host. The transaction is instead saved to a deferred execution database table. For example, if this field is set to Yes, then after inventory has been identified, received into the warehouse, and removed using the reverse receipt, the application stores the transaction in the database until it is purged.<br > If No, then the Receipt Reversals transaction is immediately sent to the host after a receipt is reversed. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
