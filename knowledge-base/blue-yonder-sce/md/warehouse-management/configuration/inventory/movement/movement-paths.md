---
title: "Movement Paths"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/movement_paths.htm"
source: "/content/movement_paths.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inventory"
  - "Movement"
  - "Movement Paths"
sections:
  - "Location reservation"
  - "Add or modify a movement path"
  - "Delete a movement path"
  - "Movement Path fields"
images: []
source_sha1: ba0d67b097c08249092b27357e8806dd255c4742
---
# Movement Paths

A movement path specifies the path that inventory takes from one point to another through your facility. A movement path applies to an LPN level of inventory that is moved from a source zone to a destination zone. A movement path can include a hop, which is an intermediate zone to which inventory is moved (not its final destination). A hop is typically a zone that is set up for special processing or inventory handling.

You define a movement path for the following reasons:

-   Any time you want the application to create work that moves inventory from its source location to a location other than its destination location. For example, movement paths are required when you want inventory to move to a processing zone before moving to its destination zone.
-   To specify a different path for different LPN levels that may exist in a source zone. LPN levels include LPNs (such as pallet), sub-LPNs (such as cases), and detail LPNs (such as eaches).
-   To specify intermediate hops. If multiple hops are configured for the same source zone, destination zone, and LPN level, the application directs the inventory to each intermediate hop in the order defined by the hop sequence.
    
    **Note**: If a movement path is defined for outbound operations, then you should only select intermediate hop (movement) zones that include locations that are not used for ship staging (location type **Ship Staging** field set to No). Movement zones containing ship staging locations are typically defined as the destination of an outbound movement path.
    
    For each hop, you can optionally specify an RF directed move that should be generated automatically when inventory is deposited to the hop location. The RF directed move is added to the work queue at the base priority defined for the operation (or a different priority that you specify), and is used to move inventory to its next location in the path.
    
    You can also specify a move method, which determines how the application allocates a location in relation to the source or destination work zone of the inventory. For example, you can configure the application so that the work zone of the selected location (in the hop zone) is in the same work zone as the final storage location.
    
-   To specify criteria that defines the order, order line, and shipment attributes values that inventory must match in order to be directed to one or more hops.
-   To establish a consistent path that inventory follows through a facility. For example, you may establish a path for cases picked from a case pick location. The path can direct the inventory to a consolidation location for palletizing, then to a processing location for shrink wrapping, and then to shipping.

**Note**: If there are any exceptions to a path that inventory takes in a facility, you can configure movement path criteria. See Movement Path Criteria.

## Location reservation

You can configure the application to determine when and which locations within a movement path are reserved. For each outbound pick method, you can select whether no locations, the first location, or all locations are reserved during pick release. For more information, see [Pick Methods](../../outbound/picking/pick-methods.md).

The application processes the reservation based off the configuration in the following ways:

-   If you choose to reserve no locations during pick release, the application only reserves one location at a time, starting when the inventory is picked. The first deposit location (in the movement zone that follows the source zone) is reserved when the inventory is picked, and each next location is reserved when the inventory is picked up from its current location.
-   If you choose to reserve the first deposit location during pick release, then the movement zone in which the first deposit takes place must have an available location for the picks to release, and locations in the remaining zones defined for the movement path are reserved one at a time when the inventory is picked up from its current location.
-   If you choose to reserve all locations in a path, then the application only releases the picks if all zones in the movement path have an available location at the time of pick release. If you reserve all locations in the path, then when a dock set or dock door is defined on an appointment, the application determines the staging lane by evaluating the priority of the lanes associated with the dock set or door. See [Associate staging lanes and aisles with shipping dock doors](../../outbound/shipping/dock-lane-assignment.md).
    
    **Note**: If a lane is associated to multiple doors in a set, then the application uses the average priority of all lane-to-door associations defined in the dock lane assignment configuration. For example, if the dock set defined on an appointment has 3 doors, and a lane is assigned to each door in the set with priorities of 1, 2, and 3, then the lane priority is 2 for the dock set \[(1 + 2 + 3 = 6) / 3 = 2\]. If another lane is associated to the same doors with the priorities of 1, 1, and 2, then that lane would be evaluated first since its average priority is higher than 2.
    
    If a destination zone and destination lane is defined during wave planning or allocation, the application does not evaluate any other staging lanes associated with the dock set or door. Additionally, if an appointment does not have a dock set or door, or if there is no appointment associated with the group of picks, then priority is not evaluated and location sort rules are used instead.
    
    **Note**: If a pick method is configured to reserve all lanes, during the location reservation phase of pick release, the application searches for staging lanes based on the release group defined on the pick method and by matching resource codes, if enabled. See [Staging location reservation by resource code](../../outbound/picking/pick-release.md).
    

Additionally, if the location type is configured to allow location overrides, then an operator can deposit the inventory to a different location from that which is already reserved, if the new location is within the original movement zone.

**Note**: Operators performing distribution deposit with a voice device cannot utilize the location override functionality.

If there are no locations available in the original zone defined in the movement path, then the operator can deposit the inventory to a pickup and deposit (P&D) location until a location becomes available in the original movement zone. The application creates directed work to move the inventory from a P&D location to the original movement zone.

If a location is available but only has the capacity for a partial quantity, then depending on the RF warning display configuration for the movement zone, a message may be displayed to the operator and a portion of the inventory can be deposited to the original zone. For more information, see [Location Types](../../warehouse/locations/location-types.md) and [Movement Zones](movement-zones.md).

## Add or modify a movement path

1.  Select **Configuration > Inventory > Movement > Movement Paths**.
2.  Perform one of the following tasks:
    -   To add a movement path, click **Add**.
    -   To modify a movement path, in the grid, click the movement path.
    -   To copy a movement path, in the grid, select the check box next to the movement path, and then click **Copy**.
3.  Enter information in the [Movement Path fields](#Movement_Path_fields).
4.  To define a hop and set the hop sequence:
    1.  Click **Hops**. The Hops page is displayed.
        
    2.  In the **Available Zones** column, select the check box next to the zones that apply.
        
        **Note**: If a movement path is defined for outbound operations, then you should only select hop (movement) zones that include locations that are not used for ship staging (location type **Ship Staging** field set to No). Movement zones containing ship staging locations are typically defined as the destination of an outbound movement path.
        
    3.  To assign criteria to a hop, under **Criteria**, select the attributes inventory must have in order to move to the hop-to zone within the movement path.
    4.  To assign a move method to a hop:
        
        **Note**: A hop move method determines how the application allocates a location in relation to the source or destination work zone of the inventory. The move method selection is considered when inventory is being moved to the hop zone for which you configure the method.
        
        1.  Perform one of the following tasks:
            -   To add a move method, click **Optional - Add New**.
            -   To modify a move method, click the existing move method assigned to the hop.
        2.  From the **Move Method** drop-down list, select one of the following options:
            -   **Receiving Staging Lane attached to Dock Door**: The application selects a receiving staging lane associated with the dock door at which the inventory is received.
            -   **Same Zone First Hop**: The application selects a location in the same work zone as the source location from which the product is moving. This can be used, for example, for outbound picking so that the application selects the pickup and deposit location at the end of the aisle from which inventory is picked.
            -   **Same Zone Second Hop**: The application selects a location in the same work zone as the destination location of the inventory. This can be used, for example, for inbound putaway so that the application selects the P&D location at the end of the aisle in which the inventory is stored.
        3.  Click **Save**.
    5.  To set up RF directed move for a hop:
        
        **Note**: If you assign an RF directed move to the hop, then work is added to work queue when inventory is deposited to the hop location. The directed work is used to move inventory from the hop location to its next location in the movement path.
        
        1.  Perform one of the following tasks:
            -   To add an RF directed move, click **Optional - Add New**.
            -   To modify a RF directed move, click the RF directed move operation.
        2.  Enter information in the following fields:
            
            | Field | Description |
            | --- | --- |
            | RF Directed Move Operations | Operation that creates work to move inventory out of the zone. |
            | Override Base Priority | Priority at which the work is added to work queue. If you leave this field blank, then the base priority defined for the operation is used. |
            
        3.  Click **Save**.
        4.  To specify the sequence of the hop in the movement path, drag the zone to the preferred position in the list.
    6.  Click **Apply**.
5.  Click **Save**.

## Delete a movement path

1.  Select **Configuration > Inventory > Movement > Movement Paths**.
2.  In the grid, select the check box next to the movement path to delete.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Movement Path fields

 
| Field | Description |
| --- | --- |
| Movement Path Name | Unique identifier for a movement path. A movement path specifies the path that inventory takes from one point to another through your facility. |
| Source Zone | Movement zone that contains the location from which inventory is initially picked or moved. It represents the first movement zone on the movement path. |
| Destination | Movement zone that contains the final destination location for inventory that was picked or moved. For example, for inventory picked for an outbound order, this could be a zone that contains ship staging locations. |
| LPN Level | LPN level of inventory to which the movement path applies.<br>-   • **LPN**: Typically represents a pallet.
<br>-   • **Sub-LPN**: Typically represents a case.
<br>-   • **Detail LPN**: Typically represents an each or piece.
<br > The units of measure (UOMs) associated with LPN, sub-LPN, and detail LPN levels are defined by the **System Equivalent UOM** field in the item footprint. See [Item Footprint UOM fields](../items/items.md). |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
