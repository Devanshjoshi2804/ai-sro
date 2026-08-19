---
title: "Location Transaction"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/location_transactions.htm"
source: "/content/location_transactions.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Integration"
  - "Host"
  - "Location Transaction"
sections:
  - "Configure location transactions"
images: []
source_sha1: 82b17a4c0ba505df7c6ec6df1b57b4e87225dcee
---
# Location Transaction

The location transaction configuration enables you to specify the level at which inventory transactions in an area are created and sent to the host. Inventory transactions are typically created at a summary level; however, you can create inventory transactions at a detailed location level.

When transactions are created at the summary level, you must define how you want the transactions summarized. You can summarize transactions by any one of these columns (inventory attributes): inventory status, lot number, origin code, and revision level.

If you specify a summary level for the inventory transactions, then you must define a host location for all of the possible values of the summary column. For example, if the summary column is Inventory Status, then you must define a host location for every area and host location code combination that exists for each of the inventory statuses—available, damaged, hold, unavailable and so on. The host location represents that inventory status in that area at the time of the adjustment. You must define this mapping for every area in which inventory is reported.

Host locations identify the location at which inventory in an area is displayed to the host. When inventory is moved, the application checks to see if the host location of the source storage location is different from the host location of the destination location. If they are the same, the application does not have to send a transaction. If they are different, a transaction is required.

The location transaction configuration is used to automate the process of informing the host of inventory quantity and status changes. The configuration of location transactions is normally performed by the Blue Yonder project team. The host location mapping convention is required, but can be supported through Integrator using a different configuration (HSTACC, or host account). Contact your Blue Yonder project team for assistance.

## Configure location transactions

1.  Select **Configuration > Integration > Host > Location Transaction**.
2.  In the grid, select the area for which you want to define host transactions that are used to report inventory quantity and status changes.
3.  In the **Inventory Reporting Level** field, select the level at which inventory is reported to the host:
    -   **Summary**: Area level.
    -   **Detail**: Location level.
4.  If **Summary** is selected, define the host locations by which to report inventory transactions to the host:
    1.  Perform one of the following tasks:
        -   To add a host location value, click **Add**.
        -   To modify a host location value, in the grid, click the value.
    2.  From the **Attribute** drop-down list, select one of the following attributes by which to report inventory:
        -   **Inventory Status**: Value that defines the quality or disposition of the inventory.
        -   **Lot Number**: Identifier assigned to a quantity of inventory that is uniquely identified during the manufacturing process for tracking an attribute of that inventory, such as its expiration date.
        -   **Origin Code**: Identifier assigned to an item to identify the item's country of origin. It is typically used for export paperwork.
        -   **Revision Level**: Number assigned to an item to differentiate revisions of the same item.
    3.  In the **Value** field, enter a value for the selected attribute.
    4.  In the **Host Location** field, enter the host location that represents the selected attribute value.
    5.  Click **Apply**.
    6.  Repeat this procedure for each possible value of the attribute. For example, if the attribute is Inventory Status, then enter a value and host location for every defined inventory status.
5.  Click **Save**.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
