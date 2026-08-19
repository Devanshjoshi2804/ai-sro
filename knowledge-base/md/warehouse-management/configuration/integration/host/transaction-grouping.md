---
title: "Transaction Grouping"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/transaction_grouping.htm"
source: "/content/transaction_grouping.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Integration"
  - "Host"
  - "Transaction Grouping"
sections:
  - "Configure transaction grouping"
images: []
source_sha1: 2877c9ad1d81538d73fb929c27988852a7671320
---
# Transaction Grouping

You configure inventory transaction groupings to determine how receiving information is summarized and sent to the host in the receiving transaction (INV-RCV). When the value of a selected attribute on one inbound order line matches the value for the same attribute on another inbound order line, the application groups the line information together before sending it to the host.

For example, assume there are two planned inbound order lines that require the same item with the same origin code, except that one line specifies Lot A and the other specifies Lot B. If Origin Code is the only attribute selected in the transaction grouping configuration, then when the two lines are received, the application groups the line information in the summary segment of the receiving transaction. However, if Origin Code and Lot Number are selected attributes, then the line information is not grouped because the lot values do not match.

The available attributes represent inventory attributes that can be used for grouping. If you do not select attributes, the application groups lines (by default) by Revision Level, Origin Code, and Lot Status.

## Configure transaction grouping

1.  Select **Configuration > Integration > Host > Transaction Grouping**.
2.  In the **Available** column, select the check box next to the attributes that apply.
3.  Click **Save**.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
