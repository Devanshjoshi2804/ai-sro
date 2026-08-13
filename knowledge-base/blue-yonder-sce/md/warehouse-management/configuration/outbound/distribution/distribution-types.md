---
title: "Distribution Types"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/distribution_types.htm"
source: "/content/distribution_types.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Outbound"
  - "Distribution"
  - "Distribution Types"
sections:
  - "Add or modify a distribution type"
  - "Distribution Type fields"
images: []
source_sha1: 50acd5f475221d131ef9830ab37ac53886c2188c
---
# Distribution Types

A distribution type is a category that defines the processing attributes of a distribution. It defines the point at which the distribution is processed, whether the distribution requires transportation planning, whether operators are allowed to negatively adjust an open inbound order line, and the LPN levels that must be moved to customer storage locations after being assigned to a distribution.

All of the distributions associated with a single inbound order line must have the same distribution type, so that the timing, rule sets, and attributes are applied the same way when the expected inventory arrives.

You can configure multiple distribution types for use in different situations. For example, you may want to assign inventory differently based on the customers involved or the inventory being distributed, or you may want the distribution to be processed at a certain time depending on the supplier from which the inventory was shipped.

A distribution type also identifies the rule sets (normal and overage) that are used to distribute the inventory. Each rule set consists of individual rules that are executed in sequence to assign inventory to each distribution associated with the inbound order line.

## Add or modify a distribution type

1.  Select **Configuration > Outbound > Distribution > Distribution Types**.
2.  Perform one of the following tasks:
    -   To add a distribution type, click **Add**.
    -   To modify a distribution type, in the grid, click the description.
    -   To copy a distribution type, in the grid, select the check box next to the name, and then click **Copy**.
3.  Enter information in the [Distribution Type fields](#Distribution_Type_fields).
4.  Click **Save**.

## Distribution Type fields

 
| Field | Description |
| --- | --- |
| Description | Name of the distribution type that is used for identification and when assigning it to a distribution. A distribution type is a category that is used to define a set of attributes that can be applied to a distribution. |
| Rule Set | Name of the rule set that is used when the distribution to which the distribution type is assigned is processed. A rule set is a set of rules that determine the amount of inventory that is assigned to the distribution from an inbound order line. |
| Adjust Open Receipt | If Yes, operators can reduce the quantity on an inbound order line that is associated with distributions in the event there is an inventory shortage. Select Yes if you allow the operator to adjust the inbound order line (expected quantity) to match the actual quantity received.<br > If No, operators are not allowed to reduce the inbound order line quantity. If you select No, then if the actual received quantity is less than the expected quantity, the quantities will not match. |
| Timing | Specific point in the receiving process at which the application starts processing the distribution.<br>-   • **Identify**: Distribution processing begins when the inventory is identified either on the transport equipment or from LPN level ASN information received from the host.
<br>-   • **Master Receipt Close**: Distribution processing begins when the inbound shipment is closed.
<br>-   • **Receive**: Distribution processing begins when the inventory is physically received from either the transport equipment or receiving staging location. |
| Overage Rule Set | Name of the rule set that is processed to distribute additional unexpected inventory from an inbound order line to the distribution. An over distribution is a distribution over and above the amount of the outbound order. For an over distribution to take place, the distribution and the inbound order line must be configured to allow the distribution overage. |
| TMS Planning | If Yes, outbound orders must be planned into shipments and loads by a transportation management system.<br > If No, outbound orders can be planned into shipments using Warehouse Management. |
| TM Lead Time | Number of hours estimated between the time distribution inventory arrives at the warehouse and the time the inbound order line is processed to completion. This value, which represents the time allowed for processing the inbound order line, is added to the expected date on the distribution's inbound order. If that total time is earlier than the order's early ship date, then the early ship date is sent to the transportation management system (TMS); otherwise, the order is planned immediately. TM lead time is used prevent the TMS from planning the order before the inventory is fully received. |
| LPN Levels | LPN levels that must be moved to the customer's storage location when identified as part of a distribution.<br > For example, if you select LPN, then when a pallet is received for a distribution, it must be moved to the customer's storage location. Moving an LPN to the customer's storage location allows operators to combine it with other inventory to be shipped to the same customer. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
