---
title: "Processing Location Reservation"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/processing_location_reservation.htm"
source: "/content/processing_location_reservation.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inventory"
  - "Movement"
  - "Processing Location Reservation"
sections:
  - "Receiving, shipping, and processing resource codes"
  - "Resource types"
  - "Configure processing location resource codes"
images: []
source_sha1: 7bd186faef0c4b73f32d204f0405b0daa8e044dc
---
# Processing Location Reservation

Processing locations can be reserved to ensure that inventory that should be together is organized in the same location. For each movement zone, configure how the application should reserve processing locations by configuring the resource type. A resource type is an identifier that specifies the type of resource the application uses to set a resource code for a location

## Receiving, shipping, and processing resource codes

Receiving resource codes for a location are set when a location is assigned for inbound inventory; this occurs during putaway after inventory has been identified. For example, if the resource variable is set to be the LPN against which the inventory is received, then after the inventory is received and directed to a location, that location's receiving resource code is set to the LPN. Only inventory received for that specific LPN is allowed to be placed in the location until the location is emptied.

Shipping resource codes for a location are set during inventory allocation when the ship staging location is assigned for the outbound inventory. For example, if the resource variable is set to be the carrier, then when a shipment is assigned to a location, the location is set to the carrier associated with the outbound inventory. Thereafter, only inventory scheduled to be shipped by that specific carrier is allowed to be placed in the location.

Processing resource codes for a location are set when the location is assigned for deposit. The deposit process involves placing picked or cross-docked inventory for multiple orders into separate locations. For example, if the resource variable is set to be the item family, then the resource code is set to the item family to which the inventory belongs.

You can configure location types to automatically clear the resource codes for shipping and processing locations. However, for warehouses that want processing or ship staging locations reserved even after the location is emptied (such as for the same customer or for inventory in a specific item family) the location type can be configured to not clear the location, meaning the resource code is retained.

## Resource types

A resource type is a method by which a deposit location in a staging or processing movement zone is reserved for specific inventory. The application uses the resource type to obtain a resource code for a location, which identifies the inventory allowed in the location. The following resource types are available for use in location reservation processing:

-   **Command**: The resource code is generated based on the results of running the command specified as the resource variable. The command must be defined in the application and must accept a work reference; the published value from the command is used as the resource code. For example, if inventory is moving through the zone, the application runs the specified command and uses the result as the resource code.
-   **Derived**: The resource code is derived from a column name (field) on the pick work, shipment, shipment header, outbound order, and outbound order header tables. The resource code can be assigned to a location when inventory is allocated or when it is being moved from one zone in the movement path to the next, depending on the configuration for the outbound pick method. After a location is assigned a code, only inventory that has the same value (such as a specific carrier) is deposited to the location until the the location is emptied of all inventory and is released either manually or automatically. If you select a derived resource type, you select one or more resource variables from a list that includes column names (fields) from the aforementioned tables. For example, if you select Derived as the resource type and you select Carrier as the resource variable, the application will set the location's resource code to the carrier that is responsible for shipping the inventory.
-   **Unrestricted**: The resource code specifies that any inventory can be mixed in the location until the location capacity is reached. The application does not match the resource code value to an inventory attribute value in order to assign inventory to the location; all inventory can be routed to a location with an unrestricted resource code.
-   **Generate**: The resource code value is an application-generated value based on the control number that you select as the resource variable.
-   **Location Assigned**: The resource code specifies the location within a zone to which all inventory is directed regardless of the location's capacity. For example, if inventory is moving through a zone where staging takes place, the resource variable you specify is the location within the zone where you want the inventory placed. For received items, the assigned resource variable for the zone is the location where inbound inventory is placed. For picked inventory, the resource code is set upon allocation, and the location is also assigned to the pick move for inventory moving through the zone for distribution or shipment. The outbound inventory moving through the zone would be directed to the specified location.

## Configure processing location resource codes

1.  Select **Configuration > Inventory > Movement > Processing Location Reservation**.
2.  In the grid, click the movement zone for which you want to define location reservation.
3.  To reserve locations using the returned value of a server command:
    1.  From the **Resource Type** drop-down list, select **Command**.
    2.  In the **Reserve by Command** field, enter the command.
4.  To reserve locations using a value derived from an attribute associated with the inventory:
    1.  From the **Resource Type** drop-down list, select **Derived**.
    2.  To select the attributes by which to reserve locations:
        1.  Click **Derived Resource Variables**.
        2.  In the **Available Attributes** column, select the check box next to the attributes that must match for inventory to be allowed in the locations.
        3.  Click **Apply**.
    3.  To assign attribute values to locations:
        1.  Click **Assign Values to Locations**.
        2.  In the grid next to the location, click the attribute column, and enter a value.
        3.  Click **Apply**.
5.  To reserve locations using a control number:
    1.  From the **Resource Type** drop-down list, select **Generate**.
    2.  From the **Control Number Description** drop-down list, select a control number.
6.  To reserve a single location to which all inventory should be directed when moved into this zone.
    1.  From the **Resource Type** drop-down list, select **Location Assigned**.
    2.  In the **Reserve By Location** field, enter the location.
7.  To allow all inventory to be deposited in any location in the zone (no restrictions), from the **Resource Type** drop-down list, select **Unrestricted**.
8.  Click **Save**.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
