---
title: "Inbound Pallet Build"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/inbound_pallet_build.htm"
source: "/content/inbound_pallet_build.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inbound"
  - "Receiving"
  - "Inbound Pallet Build"
sections:
  - "Inbound pallet building process flow"
  - "Inbound pallet building setup"
  - "Add or modify an inbound pallet build configuration"
  - "Delete an inbound pallet build configuration"
  - "Inbound Pallet Build fields"
images: []
source_sha1: 5a50956d1a76b0799930ea03dde66062a6815622
---
# Inbound Pallet Build

Inbound pallet building is a process in which inventory that is tracked by LPN or sub-LPN (such as pallets and cases) is consolidated onto pallets during the receiving identification process. The application directs the operator to perform inbound pallet building when the identified inventory matches the criteria defined in a pallet build configuration. The pallet build configuration specifies the movement zone that contains the locations to which inventory is directed for pallet building.

A pallet position configuration defines the positions available in each pallet build location. See [Outbound Staging](../../outbound/shipping/outbound-staging.md).

You can group pallet build configurations by the following putaway types: cross docking, distributions, replacement picks, and storage.

During inventory identification, the application uses the first pallet build configuration that the inventory matches to direct pallet building. For example, if pallet build criteria specifies an inventory status of Inspection, then when the operator identifies inventory in an Inspection status, the application directs the operator to a pallet build location and position. When a new pallet is started in a position, the application prints a label for it (if configured to do so).

After inventory is deposited to a pallet position, the resource code, specified in the pallet build configuration, reserves the position for matching inventory. This prevents mixing inventory on a pallet. For example, if a different item was received in the Inspection status, the application would direct the operator to a different position (pallet) in the location.

A single pallet is built in each position until the pallet is full. When the pallet is full, then if configured to do so, the application creates directed work to move the pallet to its next location as defined by the movement path.

## Inbound pallet building process flow

The following steps describe the inbound pallet building process:

1.  An RF operator selects the Receiving option from the RF Receiving menu.
2.  The operator scans a receiving door, inbound shipment, or inbound order.
3.  To receive inventory from an ASN, the operator scans an inventory identifier, and the application validates the inventory.
4.  To receive inventory without an ASN, the operator scans an item.
5.  The application determines the LPN level at which the item is tracked and displays the appropriate receiving screen.
6.  The operator identifies the sub-LPNs or LPNs of the item (unless the attributes are provided by the ASN), and then presses Done.
7.  On the Putaway screen, the operator selects Directed putaway.
8.  If the inventory matches criteria in an existing pallet build configuration, the following process takes place:
    1.  The Inbound Pallet Build screen is displayed, directing the operator to a pallet build location, and then a pallet position. The location is in the pallet build movement zone defined in the pallet build configuration. At this point, the operator can continue with the pallet build, or bypass it and perform putaway without building a pallet.
    2.  The operator takes the inventory to the pallet build location and position, and deposits the inventory to the pallet in that position.
        
        If no pallet was started in that position, the operator enters the destination LPN and deposits the inventory. At this point, a pallet label is printed if configured to do so by an inbound workflow.
        
        During the pallet building process, the operator can start a new pallet, split inventory to a different existing pallet, or override a suggested pallet position.
        
    3.  When inventory is deposited to a pallet position, the application sets the resource code for the position. The resource code reserves the position for inventory that matches the resource code. For example, if the resource code specified in the pallet build configuration is Item, then only inventory with the same item number as the inventory in the location is allowed to be added to the pallet position.
    4.  If the pallet build configuration specifies a pallet volume or uses the full pallet UOM quantity, then the application notifies the operator when a pallet is full. Otherwise, the operator can indicate that the pallet is full.
    5.  If a work operation has been assigned to the movement path for the inbound pallet build movement zone, then the application creates directed work for an operator to pick up the full pallet and move it to its destination location. Otherwise, an operator uses undirected work to move the full pallet to its next destination.
9.  If no inventory matches the criteria, then the operator is directed to perform putaway.

## Inbound pallet building setup

To configure the application for pallet building during receiving, perform the following tasks:

1.  **Configure location types.** Define a processing location type for receiving pallet building. When you define the location type, select the Processing category, and set the following attributes to Yes: **Tracks Capacity** and **Four Wall Inventory**.
    
    However, you must set the **Start Processing** field (available when creating a location type) and the **Processing** field (available when modifying a location type) to No. Setting these fields to No allows unpicked inventory to be deposited to the processing location. See [Location Types](../../warehouse/locations/location-types.md).
    
2.  **Configure locations**. Create processing locations using the pallet build location type. See [Processing Locations](../../warehouse/locations/processing-locations.md).
3.  **Configure pallet positions**. Define one or more pallet positions for each pallet building location. A single pallet can be built in each pallet position. See [Outbound Staging](../../outbound/shipping/outbound-staging.md).
4.  **Configure movement zones**.
    
    -   Create a movement zone that includes the pallet building locations. For the movement zone, set the **Allow Pallet Build** field to Yes.
    -   You also need to know which movement zone includes the source locations from which receiving takes place. If you receive inventory from transport equipment, use the movement zone that contains the dock doors. If your process is to unload inventory before receiving it (so that the transport equipment can depart), then use the movement zone that contains the staging lanes from which you receive the inventory.
        
    
    See [Movement Zones](../../inventory/movement/movement-zones.md).
    
5.  **Configure the work operation for pallet build**. If you want the application to create directed work automatically to move full pallets to their next destination, perform the following tasks:
    1.  Create a work operation or configure an existing work operation (for example, the PALBLD work operation) for creating directed work. See [Work Operations](../../work/work/work-operations.md).
    2.  Assign the operation to the pallet build movement zone.
6.  **Configure movement paths**. Configure a movement path for each of the pallet build movement zones. The movement path specifies the path that inventory takes out of the pallet build movement zone to its next destination. See [Movement Paths](../../inventory/movement/movement-paths.md).
7.  **Define inbound pallet build configurations**. An inbound pallet building configuration specifies the following attributes:
    
    -   The putaway type for the inventory, which specifies the purpose of the inventory, such as whether it is used to satisfy a cross dock, distribution, or pick replacement, or instead directed to storage
    -   Source movement zone from which the inventory is received, such as the movement zone that contains dock doors or receiving staging lanes
    -   The pallet build movement zone, which contains the locations in which the pallets are built; pallet positions must be defined for locations in the zone
    -   The resource code that is used to reserve the position for matching inventory after the first deposit is made
    -   Selections (optional) for **Pallet Volume** and **Use Pallet UOM Quantity**, which are used to determine when the pallet is full; if both fields are left blank, the operator is allowed to deposit any quantity of inventory before specifying that the pallet is full
    -   The criteria that is used to determine what inventory should be directed to a pallet build location in the zone
        
    
    See [Inbound Pallet Build](#Inbound_Pallet_Build).
    
8.  **Configure an inbound work flow.** You can configure an inbound workflow to print a pallet label when the operator starts to build a pallet. For this workflow, use the Start Pallet Build exit point. See [Inbound Workflows](../../work/warehouse-workflows/inbound-workflows.md).

## Add or modify an inbound pallet build configuration

1.  Select **Configuration > Inbound > Receiving > Inbound Pallet Build**.
2.  Perform one of the following tasks:
    -   To add a pallet build configuration, click **Add**.
    -   To modify a pallet build configuration, in the grid, click the putaway type.
3.  Enter information in the [Inbound Pallet Build fields](#Inbound_Pallet_Build_fields).
4.  To select the values used to reserve a pallet position for matching inventory:
    
    **Note**: The resource code takes effect after inventory is deposited to a pallet position. For example, if the resource code is Item, then the item number of the deposited inventory becomes the resource code value. Only inventory matching the resource code value can be added to the position after the initial deposit. The resource code value is cleared when the position is emptied.
    
    1.  Click **Receiving Resource Code**.
    2.  From the **Criteria Table** drop-down list, select the entity that contains the fields you want to use to reserve a pallet position. For example, to reserve the position by an item attribute, select Item.
    3.  In the **Available** column, select the check box next to the fields that apply.
    4.  Click **Apply**.
5.  To select the criteria used to determine which inventory is directed to an inbound pallet building location:
    1.  Under **CRITERIA**, click **Pallet Build Criteria**.
    2.  Under **Criteria Definition**, click **Expression**.
    3.  Select a table name that has the attribute to use, such as **Inventory Detail**.
    4.  Select the field name to use, such as **Inventory Status**.
    5.  Select the qualifier to use, such as "**\=**".
    6.  Select the value to use, such as **Inspect** (the name of the inventory status).
    7.  To add additional expressions:
        1.  Select the mathematical argument used to evaluate multiple rows of criteria (expressions):
            -   **Or**: Must match either group of the defined criteria.
            -   **And**: Must match both groups of the defined criteria.
            -   **(**: Opening argument used to group criteria together.
            -   **)**: Closing argument used to group criteria together.
                
                **Note**: Other operators that represent a combination of these arguments, such as ")And(" are also available. The operator determines how the application evaluates the criteria. For example, if you have two criteria lines connected with the operator "And", that means the inventory must match both attributes to meet the criteria. If the two lines are connected with the operator "Or", the inventory only has to match one of the field values to meet the criteria.
                
        2.  Click **Expression**, and define its criteria.
    8.  Click **Apply**.
6.  Click **Save**.

## Delete an inbound pallet build configuration

1.  Select **Configuration > Inbound > Receiving > Inbound Pallet Build**.
2.  In the grid, select the check box next to the putaway type to delete.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Inbound Pallet Build fields

 
| Field | Description |
| --- | --- |
| Putaway Type | Groups pallet build configurations by how the inventory is used.<br>-   • **Distribution**: A process that is used to split pallets of inventory, if necessary, and move inventory from receiving to a customer’s shipment staging location, put-to-store location, distribution location, or hop location, if configured to do so.
<br>-   • **Cross Dock**: A process that splits pallets of inventory, if necessary, and moves inventory from receiving to a specified staging location to satisfy an outbound order.
<br>-   • **Pick Replacement**: A process that replaces the source location of an outstanding pick or replenishment with the receiving location to which inbound inventory has been identified.
<br>-   • **Storage**: The standard putaway process that uses the storage search path configuration to direct inventory to an appropriate storage location. |
| Source Movement Zone | Movement zone that contains the locations from which the inbound inventory is being received, such as receiving dock doors or receiving staging locations. |
| Pallet Build Movement Zone | Movement zone in which the locations used for pallet building are located. |
| Pallet Volume | Maximum volume for the pallet being built. If you enter a value, then the application uses this value to determine when the pallet is full. If the **Use Full Pallet UOM Quantity** field is set to Yes, the application uses the least of the two values (the pallet UOM quantity as defined on the item footprint or the pallet volume) to determine when the pallet is full.<br > If the **Pallet Volume** field is left blank and the **Use Full Pallet UOM Quantity** field is set to No, then the application allows unlimited quantity to be built on the pallet, and the operator is responsible for indicating that the pallet is full. |
| Use Full Pallet UOM Quantity | If Yes, the application uses the pallet UOM quantity to determine when a pallet is full. The pallet UOM quantity is defined on the item footprint. If there are multiple items on the pallet, the application uses the value for largest pallet UOM quantity.<br > However, if a value is defined for **Pallet Volume**, and the **Use Full Pallet UOM Quantity** field is set to Yes, then the application uses the least of the two values to determine when the pallet is full.<br > If No, the application does not use the pallet UOM quantity to determine when a pallet is full. If this field is set to No and the **Pallet Volume** field is left blank, then the application allows an unlimited quantity to be built on the pallet, and the operator is responsible for indicating that the pallet is full. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
