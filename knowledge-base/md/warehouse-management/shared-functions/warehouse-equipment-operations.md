---
title: "Warehouse Equipment Operations"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/warehouse_equipment_operations.htm"
source: "/content/warehouse_equipment_operations.htm"
toc_path:
  - "Warehouse Management"
  - "Shared functions"
  - "Warehouse Equipment Operations"
sections:
  - "Lock or unlock warehouse equipment"
images: []
source_sha1: 1e00db79d117d553621c3cf06f52d8031fd9f6f6
---
# Warehouse Equipment Operations

The Warehouse Equipment Operations page is accessible from the following modules: **Picking**, **Receiving**, or **Shipping**.

You use this page to view operational details of the warehouse equipment that is defined for warehouse equipment types configured with the **Capture Warehouse Equipment** field set to Yes. You can view information such as the warehouse equipment ID, its status (Idle, Locked, or Active), and the current user of the warehouse equipment with the date and time the user logged in. Additionally, if the warehouse equipment is locked and unlocked, then the page displays the date and time the equipment was locked or unlocked and the user that performed the action.

If the Perform Equipment Safety Check workflow (PERFORM-EQP-SAF-CHK) is configured and enabled, then the application automatically locks warehouse equipment that fails the safety check. You can use the Warehouse Equipment Operations page to manually unlock the equipment so it can be used in warehouse operations, and you can manually lock warehouse equipment to ensure that no operators can log in using the equipment. See [Warehouse Equipment Workflows](../configuration/work/warehouse-workflows/warehouse-equipment-workflows.md).

## Lock or unlock warehouse equipment

You can lock warehouse equipment that is in an Idle status. Active equipment cannot be locked.

1.  View the Warehouse Equipment Operations page.
    
    1.  Select one of the following modules: **Picking**, **Receiving**, or **Shipping**.
    2.  Select **Warehouse Equipment Operations**.
    
2.  In the grid, select the check box next to the warehouse equipment to lock or unlock.
3.  Perform one of the following tasks: 
    -   To lock the warehouse equipment, from the **Actions** drop-down menu, select **Lock**. The status of the equipment changes to Locked.
    -   To unlock the warehouse equipment, from the **Actions** drop-down menu, select **Unlock**. The status of the equipment changes to Idle.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
