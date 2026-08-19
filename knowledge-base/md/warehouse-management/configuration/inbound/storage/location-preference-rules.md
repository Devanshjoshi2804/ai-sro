---
title: "Location Preference Rules"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/location_preference_rules.htm"
source: "/content/location_preference_rules.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inbound"
  - "Storage"
  - "Location Preference Rules"
sections:
  - "Add or modify a location preference rule"
  - "Delete a location preference rule"
  - "Location Preference Rules fields"
images: []
source_sha1: 1e05dfa139f8df9f5511d8450c8ebf7dfaa8593f
---
# Location Preference Rules

A location preference rule is an optional configuration that is used to specify a location or range of locations to which specific inventory should be directed during putaway. A location preference rule can be restricted to inventory matching one or more of the following attributes: client, item, item family, item class, supplier, handling unit, or LPN attribute. LPN attributes are defined in storage settings. See [Storage Settings](storage-settings.md).

**Note**: You use location preference rules only if there is specific inventory that you want to direct to specific locations. Otherwise, it is more efficient to define a storage search path that directs specific inventory to a zone, and allow the application to find an available location.

When received inventory is ready to be put away, the operator can choose directed putaway to have the application select a storage location. For directed putaway, the application first uses the location preference rule to find a location and, if one is not found, it uses the storage zone search paths. If it still does not find a suitable location, it displays a message to the operator. For undirected putaway, the application does not attempt to find a storage location; instead, the operator selects a location manually.

You can configure multiple location preference rules and place them in sequential order; the application searches them in order until a suitable location is found. When a preference rule includes a range of locations that spans multiple areas, the application sorts the locations by the travel sequence within each separate area. For example, if the locations in a range are in two different areas, the application does not consider the travel sequence for all the locations together. Instead, locations in one area are sorted separately from locations in the other area. To search for locations by area sequence, you must configure multiple preference rules, each including the locations in a single area, and then sort the rules in the sequence by which the areas should be searched.

If you want to reserve locations for specific inventory, you can assign an item or item family to the locations in a rule. For example, if you create a location preference rule for the item family FLAMMABLE for locations 1CS101 through 1CS120 and select the Assign check box, then during directed putaway, the application does not direct any other item family to those locations, even if the locations are empty. If the Assigned Location check box is not selected and the locations become empty, the application could direct another item family to this same set of locations.

## Add or modify a location preference rule

1.  Select **Configuration > Inbound > Storage > Location Preference Rules**.
2.  Perform one of the following tasks:
    -   To add a location preference rule, click **Add**.
    -   To modify a location preference rule, in the grid, click the sequence number associated with the rule.
    -   To copy a location preference rule, in the grid, select the check box next to the sequence number associated with the rule, and then click **Copy**.
3.  Enter information in the [Location Preference Rules fields](#Location_Preference_Rules_fields).
4.  Click **Save**.

## Delete a location preference rule

1.  Select **Configuration > Inbound > Storage > Location Preference Rules**.
2.  In the grid, select the check box next to the sequence number associated with the rule to delete.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Location Preference Rules fields

 
| Field | Description |
| --- | --- |
| Storage Options | Value used to define the criteria that the application uses to evaluate whether inventory should be directed to the location or range of locations. You can use this field to create a location preference rule that is specific to an item, item family, item class, handling unit type, client, or supplier. |
| Sequence Number | Number that defines the sequence in which the application processes the list of location preference rules to find an appropriate location or range of locations for the inventory to be put away. The application evaluates the rules in sequential order (starting with 1), and stops processing when it finds a matching location. |
| LPN Attribute | Identifier that describes the inventory's physical composition. The application uses this value to direct inventory with a matching value to locations specified by the location preference rule.<br > For example, you can direct inventory that meets the criteria for Heavy to floor-level pick locations. The values for physical composition are defined by the LPN composition attributes. See [Configure storage settings](storage-settings.md). |
| Begin Location | First location in the range of locations to which the application will attempt to direct inventory that matches the criteria on the location preference rule. |
| End Location | Last location in the range of locations to which the application will attempt to direct inventory that matches the criteria on the location preference rule. To limit the search path to a single location, enter the same location specified for **Begin Location**. |
| Assigned Location | Indicates that the defined item number, item family, supplier, or client is assigned to the specified location or range of locations in the location preference rule. Assigning one of these storage options to a location or range of locations reserves the location exclusively for inventory that matches that criteria. |
| Item | Identifier for an item. An item is any specific piece of inventory that is stored or processed within the application. Items can be raw materials, packaging materials, in-process materials, supplies, and finished goods. In some warehouses, items are called stock keeping units (SKUs). Before the application can effectively store, track, and manipulate inventory, you must assign an item identifier and define the attributes of each item you want to track. When defining an item, you specify information such as how the item is packaged and handled, along with details that define how it should be received, stored, allocated, shipped, counted, and valued (cost information). Only displayed when you select Item in the **Storage Options** field. |
| Item Family | Identifier used to group similar items together. Typically, all of the items within a family have the same material handling characteristics. Only displayed when you select Item Family in the **Storage Options** field. |
| Client | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another and enables the application effectively manage activity for multiple clients in one warehouse. Only displayed in a 3PL environment when you select Supplier or Client in the **Storage Options** field. |
| Supplier | Unique code that identifies a supplier. A supplier is a provider who supplies goods or services. Only displayed when you select Supplier in the **Storage Options** field. |
| Handling Unit | Identifier for a handling unit type. A handling unit type is a group of handling units (such as pallets, totes, or equipment) that share the same characteristics such as size and weight as well as whether they are serialized, temporary, or considered a container. Only displayed when you select Handling Unit Type in the **Storage Options** field. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
