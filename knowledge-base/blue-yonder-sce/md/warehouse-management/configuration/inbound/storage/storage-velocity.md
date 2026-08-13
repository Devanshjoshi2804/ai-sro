---
title: "Storage Velocity"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/storage_velocity.htm"
source: "/content/storage_velocity.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inbound"
  - "Storage"
  - "Storage Velocity"
sections:
  - "Add or modify a storage velocity"
  - "Delete a storage velocity"
images: []
source_sha1: 8477ebd79f5a1da76bcbb7bf1771a509d7b350c3
---
# Storage Velocity

A velocity is an attribute that indicates the speed at which an item moves in and out of a warehouse. When a location is configured with a velocity, it indicates that items with the same velocity are stored in that location. Velocity on an item is applied manually based on your knowledge of an item's movement, but can be configured to change automatically based on the pick velocity thresholds configured for the velocity recalculation rule. Velocities assist in putting fast moving inventory in more convenient picking locations and using the less convenient locations for slower moving inventory. Velocities for an item or location can be defined using the standard values of Fast, Medium, or Slow, or other terms that you define. If you are unsure which velocity to use, you can configure all locations and items to Fast, and then lower the velocity over time, as needed.

The application uses velocities during the storage selection process. For example, you can configure a search path to ensure that fast moving, high volume inventory is directed to the most efficient pick section in the facility. When material handlers receive an item associated with a fast-moving velocity, the application tries to direct the item to a location defined as fast moving. Depending on the storage zone rule configured, if a fast moving location is not available, then the application uses the next storage rule to find a storage location.

After you configure velocities, you can perform the following tasks:

-   Manually add a velocity to an item
-   Manually add a velocity to a location
-   Configure storage zone rules to match the velocity on the item to the velocity on the location
-   Configure velocity recalculation rules so that the application can automatically assign a velocity to an item

## Add or modify a storage velocity

1.  Select **Configuration > Inbound > Storage > Storage Velocity**.
2.  Perform one of the following tasks:
    -   To add a velocity, click **Add**.
    -   To modify a velocity, in the grid, click the velocity.
    -   To copy a velocity, in the grid, select the check box next to the velocity, and then click **Copy**.
3.  Enter information in the following fields:
    
     
    | Field | Description |
    | --- | --- |
    | Storage Velocity | Identifies the speed at which inventory stored in a location moves in and out of the warehouse. Velocity is used to optimize warehouse space and inventory handling by placing fast moving items in the best locations for quick picking, and slower moving items in the less accessible storage locations. The application accomplishes this by attempting to match the velocity of the item with the velocity of the location when finding a location for storing the item. |
    | Description | Long description of the velocity. This is the value that is available for selection from the Velocity drop-down list when assigning a velocity to an item or location. |
    | Short Description | Brief description of the velocity. If the application is configured to use this description, this is the value that represents the velocity on RF screens. |
    
4.  Click **Save**.

## Delete a storage velocity

1.  Select **Configuration > Inbound > Storage > Storage Velocity**.
2.  In the grid, select the check box next to the velocity to delete.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
