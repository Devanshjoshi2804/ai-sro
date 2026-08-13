---
title: "Log Indirect Work"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/log_indirect_work.htm"
source: "/content/log_indirect_work.htm"
toc_path:
  - "Warehouse Management"
  - "Shared functions"
  - "Log Indirect Work"
sections:
  - "Log indirect work to a work activity"
images: []
source_sha1: 5ee6bc2ea501db549ac62a7c0d7bbf85ec727ca8
---
# Log Indirect Work

The Log Indirect Work page is accessible from the following modules: **Inventory**, **Outbound Planner**, **Packing**, **Picking**, **Production**, **Receiving**, **Returns**, or **Shipping**.

Indirect work is a labor task that is not directly related to processes that move items through the warehouse (such as receiving, inventory moves, order fulfillment, and so on) or a specific client. Indirect work does not have a cost that can be applied against a client or customer. Examples of indirect work include equipment maintenance, cleaning, safety checks, or breaks. The time spent on each indirect work is logged and shared with the Warehouse Labor Management (WLM) application based on the configured activity codes. See [Configure Warehouse Labor Management integration](../configuration/integration/warehouse-labor-management.md).

**Note**: For Warehouse Management (WM) to record and send indirect work information to WLM, a WM activity must be enabled and associated with a work type that is defined in WLM. See [Work Activities](../configuration/work/work/work-activities.md) and [Mapping to work types and discrete procedures](../configuration/work/work/work-activities.md).

The application calculates the duration of indirect work based on the start time of the indirect work (time at which the user manually logs the work) and the start time of the next logged activity (direct or indirect work). The time at which the operator performs the next task in the application, such as picking inventory, is the end time for the indirect work.

**Note**: You must log the indirect work prior to starting the task. The Log Indirect Work page is displayed if Warehouse Labor Management is integrated and enabled for the warehouse.

For example, assume a forklift operator picking a work assignment needs to change the forklift battery, and the operator logs the start of the indirect work at 3:00 P.M. If the operator takes 15 minutes to change the battery and does not start the next pick (obtain task) until 3:20 P.M., then the actual amount of time logged against the indirect work task is 20 minutes.

If the operator begins an inventory counting task (instead of an obtain task) after logging the start of indirect work, then the indirect work end time is recorded as the start time of the count work. However the count work is not logged until the count is completed.

## Log indirect work to a work activity

Indirect work represents a work activity that is not directly related to processes that move items through the warehouse.

**Note**: Warehouse Labor Management (WLM) must be integrated with Warehouse Management (WM) and enabled to log indirect work, and you must log the indirect work prior to starting the task.

For WM to record and send indirect work information to WLM, a WM activity must be enabled and associated with a work type that is defined in WLM. See [Work Activities](../configuration/work/work/work-activities.md) and [Mapping to work types and discrete procedures](../configuration/work/work/work-activities.md).

1.  View the Log Indirect Work page.
    
    1.  Select one of the following modules: **Inventory**, **Outbound Planner**, **Packing**, **Picking**, **Production**, **Receiving**, **Returns**, or **Shipping**.
    2.  Select **Log Indirect Work**.
    
2.  Select the indirect work.
3.  Click **Log**.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
