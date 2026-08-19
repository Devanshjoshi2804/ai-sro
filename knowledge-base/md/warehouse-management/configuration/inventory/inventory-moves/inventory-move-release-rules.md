---
title: "Inventory Move Release Rules"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/inventory_move_release_rules.htm"
source: "/content/inventory_move_release_rules.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inventory"
  - "Inventory Moves"
  - "Inventory Move Release Rules"
sections:
  - "Release rules for stock transfers"
  - "Configure inventory move release rules"
  - "Inventory Move Release Rule fields"
images: []
source_sha1: 08713c651bd16bbe72203fe124e9cb2491101343
---
# Inventory Move Release Rules

Inventory move release rules define the action the application performs to release work for stock transfers. The application creates a work request for the stock transfer, which is added to the work queue so that an RF operator can perform it.

## Release rules for stock transfers

Release rules define how the application releases directed work for stock transfers based on the LPN level of the inventory being transferred. You can also define whether transfers for similar inventory can be grouped together into a single work request.

A stock transfer is used to move inventory from one location to another. The following are typical reasons for performing a stock transfer:

-   To consolidate inventory. For example, if you have three locations that are partially filled with identical inventory, you can perform stock transfers to move all the inventory into one location.
-   To move inventory into a different pick location. For example, as the season approaches, you may want to move seasonal or promotional inventory to a more accessible picking location.

## Configure inventory move release rules

1.  Select **Configuration > Inventory > Inventory Moves > Inventory Move Release Rules**.
2.  Under **RELEASE RULES**, select the LPN level for which you want to configure a release rule:
    -   **LPN Release Rule**
    -   **Sub-LPN Release Rule**
    -   **Detail-LPN Release Rule**
3.  Enter information in the [Inventory Move Release Rule fields](#Inventory_Move_Release_Rule_fields).
4.  To select the attributes that must match for individual pieces of work to be grouped into a single task:
    1.  Click **Work Groupings**.
    2.  In the **Available** column, select the check box next to the attributes that must match.
    3.  Click **Apply**.
        
        **Note**: The work groupings can limit the performance of the action you specified for the release rule by grouping individual pieces of work into one piece of work. For example, if you select Create Work as the action for the release rule, and then select Item and Work Zone as the work groupings, the application will only produce on one stock transfer for all LPNs that are of the same item and that are located in the same work zone.
        
5.  Click **Apply**.
6.  Click **Save**.

## Inventory Move Release Rule fields

 
| Field | Description |
| --- | --- |
| Action | Action that the application performs to release the transfer. The application creates a work request for the stock transfer, which is added to the work queue so that an RF operator can perform it. |
| Operation | Work operation that identifies the type of directed work that is created, such as Transfer. |
| Priority | Priority at which work initially enters the work queue. It is the priority at which a work request is created.<br>-   • **Use base priority set on work operations**: The value for the operation's base priority is used when work is created. The base priority is the current priority that is defined for the operation.
<br>-   • **Override base priority**: The operation's base priority is overridden when the work is created with the number specified in the **Value** field.
<br>-   • **Increase priority from base priority**: The operation's base priority is increased when the work is created by the number specified in the **Value** field.
<br>-   • **Decrease priority from base priority**: The operation's base priority is decreased when the work is created by the number specified in the **Value** field. |
| Value | Value that is applied against the base priority of the operation. Depending on what is selected for **Priority**, the value either replaces the base priority, or it is added to or subtracted from the base priority to result in a new priority. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
