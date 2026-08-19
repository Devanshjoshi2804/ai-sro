---
title: "Quality errors"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/quality_errors.htm"
source: "/content/quality_errors.htm"
toc_path:
  - "Warehouse Labor Management"
  - "Labor"
  - "Labor Assignments"
  - "Quality errors"
sections:
  - "Log or modify a quality error"
  - "Unresolve a quality error"
  - "Quality Error fields"
images: []
source_sha1: 05cf1b30ed133437bb0b1c28d402d8975cfe1572
---
# Quality errors

A quality error occurs when inventory being shipped from your warehouse is no longer considered acceptable to the customer. Typical examples of quality errors include a customer receiving a damaged or incorrect (mispicked) item, or an incorrect quantity of an item that they ordered.

Resolved quality errors are applied to the associated discrete record to calculate cost and performance details. The quality error information collected can be used when assessing cost and profitability, and when measuring employee performance.

## Log or modify a quality error

An assignment must be completed before you can log a quality error.

1.  Select **Labor > Labor Assignments**.
2.  On the Search pane, enter criteria for the assignment, and then click **Search**.
3.  In the Assignments grid, select the assignment for which to log a quality error.
4.  On the Assignment details pane, select the **Quality Error** tab.
5.  From the **Actions** drop-down list, select **Log Quality Error**.
6.  Enter information in the [Quality Error fields](#Quality_error_fields).
7.  Click **Save**.

## Unresolve a quality error

You can unresolve a quality error to change quality reporting information for errors that have previously been recorded in the application. When a previously resolved error is unresolved, the charges applied to the discrete task are removed until the error is resolved again. You can resolve quality errors in the SCE client.

1.  Select **Labor > Labor Assignments**.
2.  On the Search pane, enter criteria for the assignment, and then click **Search**.
3.  In the Assignments grid, select the assignment for which to log a quality error.
4.  On the Assignment details pane, select the **Quality Error** tab.
5.  In the grid, select the quality error to unresolve.
6.  From the **Actions** drop-down list, select **Unresolve Quality Error**. A confirmation message is displayed.
7.  Click **Yes**.

## Quality Error fields

 
| Field | Description |
| --- | --- |
| Seq Number | Integer that defines a specific sequence number in the assignment in which the error occurred. Only displayed for discrete assignments. |
| Error Item Number | Identifier for the item that was actually picked (in error). |
| Item Number | Number representing the stock keeping unit (SKU) or label that should have been picked for the quality error that is being logged. Only displayed for discrete assignments. |
| Quality Error Type | Category into which a quality error is grouped. Typically, the **Quality Error Type** is the reason for the quality error, such as damaged, mispick, or short. |
| Quality Error Source | Origin of the quality error, such as from the customer, store, or an internal audit. |
| Quantity | Quantity amount associated with the quality error. For example, if the **Quality Error Type** value is Short, and the **Quantity** value is 3, then three units of the expected quantity of an item are missing. |
| Cost | Cost for resolving the quality error. |
| Driver | Name of the driver who delivered or picked up the transport equipment associated with the quality error. |
| Quality Error Comment | Comments related to the quality error. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
