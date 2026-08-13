---
title: "Host"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/host.htm"
source: "/content/host.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Integration"
  - "Host"
sections: []
images: []
source_sha1: 8fb391b60afe68deb04a827c56ad2ed8b43ebd5c
---
# Host

The host integration supports the configuration of the following transactions:

-   **Location transaction**: Defines the level at which inventory transactions in an area are created and sent to the host. If you choose Summary transactions, you must select an attribute (such as inventory status) and define a host business system location for each attribute value (Available, Damaged, and so on) by which to summarize. Host location transaction configurations are used to automate the process of informing the host of inventory quantity and status changes. 
-   **Movement transaction**: Specifies the movement transaction that is created and sent to the host when inventory is moved into and out of an area. Movement transactions are used to notify the host when inventory moves occur.
-   **Transaction grouping**: Determines how receiving information is summarized and sent to the host in the receiving transaction (INV-RCV). When the value of a selected attribute on one inbound order line matches the value for the same attribute on another inbound order line, the application groups the line information together before sending it to the host.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
