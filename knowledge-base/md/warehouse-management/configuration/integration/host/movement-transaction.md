---
title: "Movement Transaction"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/movement_transactions.htm"
source: "/content/movement_transactions.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Integration"
  - "Host"
  - "Movement Transaction"
sections:
  - "Add or modify a movement transaction"
  - "Movement Transaction fields"
images: []
source_sha1: 2837f75994b30d8c8d510051af8f2bfb432756af
---
# Movement Transaction

The movement transaction configuration enables you to specify which transaction to send to the host for each movement to and from an area. The application uses the source area and destination area to define the movement-generated host transaction.

When a move occurs, a transaction is generated using the transaction that you specified. A value of **Any Area** specified for either the source or destination indicates that any area is valid. Multiple host transactions can be generated from one movement by creating multiple entries with different sequence numbers.

## Add or modify a movement transaction

1.  Select **Configuration > Integration > Host > Movement Transaction**.
2.  Perform one of the following tasks:
    -   To add a movement transaction, click **Add**.
    -   To modify a movement transaction, in the grid, click the transaction.
    -   To copy a movement transaction, in the grid, select the check box next to the transaction, and then click **Copy**.
3.  Enter information in the [Movement Transaction fields](#Movement_Transaction_fields).
4.  Click **Save**.

## Movement Transaction fields

 
| Field | Description |
| --- | --- |
| Source Area | Area in which the transaction activity began, such as the area from which inventory was moved. |
| Destination Area | Area in which the transaction activity ended, such as the area to which inventory was moved. |
| Sequence | Number that defines the order in which this transaction is generated when multiple transactions are generated from a single inventory move. |
| Host System | Host application to which the transaction will be sent. |
| Events | Identifier for the event that will be generated. |
| Send To Host | If Yes, when the transaction is generated, it is automatically sent to the host.<br > If No, the transaction is generated but is not automatically sent to the host. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
