---
title: "Inventory Statuses"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/inventory_statuses.htm"
source: "/content/inventory_statuses.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inventory"
  - "Inventory Status"
  - "Inventory Statuses"
sections:
  - "Inventory status uses"
  - "Inventory status changes"
  - "Add or modify an inventory status"
  - "Translate an inventory status"
  - "Delete an inventory status"
images: []
source_sha1: 9ab6cbefd2e4b878a76e188535c71090e9bfdf96
---
# Inventory Statuses

An inventory status is used to define the physical condition, availability, or material handling requirements for the inventory. Every item defined in the warehouse must be assigned an inventory status. You can assign a default inventory status when creating a new item.

Inventory statuses are uniquely defined for your application during the initial setup.

## Inventory status uses

You can apply an inventory status to an LPN of inventory to ensure that the inventory is stored in a distinct location of the warehouse. For example, operators handling inventory identified with a Damaged status can be directed to store that inventory in a Damaged location in the facility.

Applying an inventory status also ensures that inventory identified with different statuses is not stored in the same location. When you define inventory mixing rules to prevent mixing inventory statuses in a location, then the application does not let an operator deposit an LPN of inventory into a location that contains inventory of a different inventory status.

In addition, you can use a unique inventory status to reserve or hold inventory for a specific customer, order line, or purpose. The application only allocates or reserves inventory for an order when that inventory is identified with the same inventory status that was specified on the order line.

**Note**: Typically, orders are created for inventory identified with the default status for your application, such as "Available" or "Shippable".

## Inventory status changes

You can change an inventory status when an item is identified and received into your facility. However, you cannot change the status of inventory in the following situations:

-   Inventory is reserved for an order. To change the status of inventory that is reserved, you must first cancel the reservation or the pick work for that inventory.
-   Inventory is pending or waiting to be put away in a location.
-   The status change violates the inventory aging profile assigned to the inventory.

If you are using aging profiles for date-tracked items, you can still manually change the inventory statuses, but only to a status that is later in the aging progression. The exception to this is when a backwards change coordinates with the application-calculated status. For example, if you manually changed an inventory status from First Quality to Second Quality, you can manually go back to First Quality if the inventory's age is within the window defined for the First Quality status.

## Add or modify an inventory status

1.  Select **Configuration > Inventory > Inventory Status > Inventory Statuses**.
2.  To add an inventory status code:
    1.  Click **Add**.
    2.  Enter information in the following fields:
        
        | Field | Description |
        | --- | --- |
        | Inventory Status | Value that defines the quality or disposition of the inventory. |
        | Description | Description of the inventory status that further defines the inventory status. |
        | Short Description | Brief description of the inventory status. |
        
3.  To reorder the list, in the grid, select the status code to move, and then drag it to the new location in the grid. The grid order determines the order in which the inventory statuses are displayed to the user, such as from a drop-down list field.
4.  To modify a description, in the grid, click the description, and then enter your changes.
5.  Click **Save**.

## Translate an inventory status

You can translate the description and short description of selected rows for use in another locale. You may want to do this if any of your users are associated with a different locale and need to understand the descriptions in the language of their locale.

**IMPORTANT**: The changes you make to the descriptions in a locale are saved and applied to all warehouses in a multi-warehouse environment.

1.  Select **Configuration > Inventory > Inventory Status > Inventory Statuses.**
2.  Perform one of the following tasks:
    -   To translate specific rows, in the grid, select the check box of the rows, and then above the grid, click **Translation**.
    -   To translate all rows, above the grid, click **Translation**.
3.  From the **Destination Locale** drop-down list, select the locale.
4.  In the grid, select a translated description or short description, and then enter the new value.
5.  Click **Save**.

## Delete an inventory status

1.  Select **Configuration > **Inventory > Inventory Status > Inventory Statuses.
2.  In the grid, select the check box next to the inventory status to delete.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
