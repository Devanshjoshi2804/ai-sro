---
title: "Allocation"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/allocation.htm"
source: "/content/allocation.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Outbound"
  - "Allocation"
sections: []
images: []
source_sha1: 33f532618e5dfb49087d793d5a29dd4acc4e1640
---
# Allocation

Allocation is the process of locating inventory for an order. Another process, pick release, releases the work to the staff.

Allocation configurations determine how various aspects of the allocation process function to ensure that inventory selection is performed effectively in your facility. For allocation to take place, you must configure the following allocation options:

-   **Pick zones**: Used to represent a group of locations that share the same attributes for picking, such as the LPN level at which picks can be allocated, the cartonization group to which it belongs, and whether the location supports replacement picks, starter pallets, and pre-inventory allocation.
-   **Allocation building sequence**: Used to control picking access and hierarchy. You can define the sequence of buildings in which the application attempts to find inventory to fulfill orders processed from the building.
-   **Allocation search paths**: Used to identify a list of pick zones from which the application should attempt to allocate inventory for a pick based on the attributes of the required inventory.
-   **Manual allocation**: Process that a user performs using the Outbound Planner module or Picking module.
-   **Automatic allocation**: Process by which the application determines when to automatically allocate and what orders/shipments to automatically allocate. This option is often used in warehouses that have a consistent shipping schedule. For example, every Monday morning they ship to Stores 101, 102, and 103, and every Monday afternoon they ship to Stores 201, 202, and 203. They schedule automatically because they do the same allocation of orders consistently every week.
-   **Allocation inventory selection**: Process by which the application finds inventory, including date tracked inventory, to fill an outbound order line.
-   **Post allocation**: Used to configure the actions that take place prior to pick release after an allocation has been attempted.
-   **Allocation rules**: Used to specify acceptable inventory attribute values to fulfill lines.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
