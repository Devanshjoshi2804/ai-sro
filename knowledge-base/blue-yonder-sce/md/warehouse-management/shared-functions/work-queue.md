---
title: "Work Queue"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/work_queue.htm"
source: "/content/work_queue.htm"
toc_path:
  - "Warehouse Management"
  - "Shared functions"
  - "Work Queue"
sections:
  - "Ineligible work"
images: []
source_sha1: e4778104b1c8f4d54a56f73632062c9e173846ec
---
# Work Queue

The Work Queue page is accessible from the following modules: **Inventory**, **Outbound Planner**, **Picking**, **Production**, **Receiving**, **Shipping**, or **Yard**.

The work queue displays the work that was requested to be performed in the application, such as to pick inventory, move transport equipment, or perform inventory counts. You use the work queue to view and manage work requests. The details on the work queue page are displayed in the following tabs:

-   **Work**: Displays details for all the work that was requested to be performed in the application
-   **Summary**: Displays a summary of all the work that was requested to be performed in the application

You can view the following types of work and pick details:

-   Directed work is work that is presented to RF and voice operators that select the directed work option on their RF or voice devices. The application determines the appropriate work to offer to the user based on user and equipment permissions, the user's proximity to the work, and the priority of the work in relation to other work.
-   Undirected work is work that is performed by selecting an RF or voice menu option other than Directed Work
-   Details associated with each pick, such as pick status, quantities, and inventory attributes

You can manage directed work requests by performing the following actions:

-   Assign work to a specific user to prevent it from being offered to other users
-   Assign work to a specific role to prevent it from being offered to users that are not assigned to the role
-   Unassign a user or role from a piece of work to allow the work to be offered to other users
-   Change the priority of work to affect the sequence in which the work is offered to eligible users
-   Suspend work to prevent it from being offered to any user
-   Resume work that has been suspend to allow it to be offered to users
-   Unlock work to release work that was released to a Locked status. For example, during the demand replenishment process, replenishment work is typically locked automatically to prevent work from being released until there is room in the location for the replenishment inventory. When room becomes available, the work is typically released automatically.
-   Cancel directed work to change the work to undirected
-   Cancel picks to remove the pick work from the queue
-   View ineligible work to understand the reason why work is not being offered to a logged in user

The following types of work are displayed in the work queue as a single grid row that you can expand to view additional details:

-   Work assignment (a collection of individual picks performed in a single picking tour)
-   Bulk pick (a single pick that satisfies multiple order or work order lines)
-   Carton pick (a collection of picks to be packed into a single carton)

## Ineligible work

You can view ineligible work to determine why directed work is not offered to a particular user (RF or voice operator) that is logged into the application on a particular device. If the application indicates that a user is ineligible for a work request, the work request is not offered to the user until the reasons for ineligible work are resolved. See [View ineligible work](work-queue/procedures-for-work-queue.md).

The following table explains the reasons why a user may be ineligible for work.

 
| Reason | Description |
| --- | --- |
| Assigned to Other Role | The work is assigned to a role to which the user is not assigned. See [Users](../../administration/system-administrator/authorization/users.md). |
| Assigned to Other User | The work is assigned to a different user. You can assign a user to a specific load, a piece or transport equipment, or to a specific work request. See [Manage the work queue](work-queue/procedures-for-work-queue.md). |
| Assigned User Locked | The user is currently working on and locked to an outbound load. Once the outbound load has been completed, the user can perform other directed work. |
| Device/Work Area | The device is not authorized for the work area. See [Add or modify an RF device](../configuration/equipment/hardware/rf-devices.md). |
| Ineligible Work Status | The status of the work is Locked or Suspended. You use the work queue to unlock a locked work request and reset a suspended work request. See [Manage the work queue](work-queue/procedures-for-work-queue.md). |
| Out of Service | The work zone has been placed out of service. You can indicate whether a work zone is in service or out of service. See [Add or modify a work zone](../configuration/work/work/work-zones.md). |
| Same Cycle Count user | The user has performed a count for which the application requires a different user to perform a subsequent count. For example, if one user performed a cycle count that resulted in an audit count, and the audit count type requires a different user, then another user must perform the audit count. See [Add or modify a count type](../configuration/inventory/counting/count-types.md). |
| Unauthorized for Client | The user is not authorized for the client associated with the work. See [Clients](../configuration/partners/clients.md). |
| User/Operation | The user is not authorized to perform the operation. See [Work Operations](../configuration/work/work/work-operations.md). |
| Warehouse Equipment Not Valid for Location | The warehouse equipment is not allowed to perform directed work in the location. The location access group of the equipment must match the location access group of the location. See [Location Access Groups](../configuration/equipment/equipment/location-access-groups.md). |
| Warehouse Equipment Type/Operation | The warehouse equipment is not authorized to perform the operation. See [Work Operations](../configuration/work/work/work-operations.md). |
| Wrong Aisle | The aisle in which the work is located is different from the aisle that the user selected as an assignment filter. The user restricted work requests to a certain aisle based upon an assignment filter. If directed work filters are enabled, assignment filters are displayed when the user signs on to directed work. The user can filter work requests so that only requests for a particular aisle, building, or work zone are received. See [Work RF Settings](../configuration/work/work/work-rf-settings.md). |
| Wrong Building | The building in which the work is located is different from the building that the user selected as an assignment filter. The user restricted work requests to a certain building based upon an assignment filter. If directed work filters are enabled, assignment filters are displayed on the device when the user signs on to directed work. The user can filter work requests so that only requests for a particular aisle, building, or work zone are received. |
| Wrong Work Zone | The work zone in which the work is located is different from the work zone that the user selected as an assignment filter. The user restricted requests to a certain work zone based upon an assignment filter. If directed work filters are enabled, assignment filters are displayed on the device when the user signs on to directed work. The user can filter work requests so that only requests for a particular aisle, building, or work zone are received. |
| Zone Equipment Limits | The number of pieces of equipment currently performing directed work in the work zone has reached the limit defined for the work zone. See [Work Zones](../configuration/work/work/work-zones.md) and [Equipment limits](../configuration/work/work/equipment-limits.md). |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
