---
title: "Location Audit"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/location_audit.htm"
source: "/content/location_audit.htm"
toc_path:
  - "Warehouse Management"
  - "Inventory"
  - "Location Audit"
sections:
  - "Audit warehouse locations"
  - "Location Audit fields"
images: []
source_sha1: b55ad1081ea35113308857daa99207a4303eaf1f
---
# Location Audit

You use the Location Audit page to selectively perform a data integrity audit on locations throughout the warehouse.

Sometimes, database tables may contain inaccurate data, or information across database tables may not be in sync. For example, incorrect capacity values (quantity, volume, or length) may be recorded in the database for a storage location, which can lead to an error in the location. Alternatively, a location may be configured as not pickable, but the database value for the location is recorded as pickable. To audit such errors, you use the Location Audit page to find problematic locations, so you can resolve the errors to achieve data accuracy.

You can audit the locations based on search criteria, such as storage zone, location range, or aisle. The application then lists the locations that are in error based on the search criteria. While the application looks for these error locations, you can choose to either pause and resume or stop the audit process. After the audit is complete, you can choose to repair the problematic locations, a process in which the application takes the necessary action to fix the data in the database tables.

You can also save search criteria for future use. For example, if you decide to consistently monitor specific locations in a warehouse that have frequent pick cancellations, you can save the search criteria to quickly perform an audit on the locations in the future.

## Audit warehouse locations

1.  Select **Inventory > ** **Location Audit**.
2.  Enter search criteria for the location to audit. For example, enter a location range, zone, or aisle.
3.  Click **Start Audit**.
    
    **Note**: During the audit process, you can pause and resume or stop the audit.
    
4.  Perform one of the following tasks:
    
    -   To repair selected locations, in the grid, select the check box next to the location, and then click **Repair Selected**.
    -   To repair all the locations, click **Repair All**.
5.  View the information in the [Location Audit fields](#Location_audit_fields).

## Location Audit fields

 
| Field | Description |
| --- | --- |
| Location | Unique name for a location within the facility that has problems due to which you cannot perform any operations. |
| Description | Meaningful description of the problem in the location. |
| Action | Action that the application performed to fix the error in the location. |
| Movement Zone | Name of a movement zone. A movement zone represents a group of locations to and from which inventory can be moved. For example, storage locations to which inventory can be deposited and processing locations to which inventory is moved for packing are the types of locations that must be assigned to a movement zone for the application to select those locations for putaway or deposit.<br > Source, hop, and destination locations must be assigned to a movement zone so that a movement path can be defined to use each of those locations. |
| Storage Zone | A storage zone represents a group of locations that have the same attributes (consolidation, item mixing, date control, and others) for storing inventory. |
| Pick Zone | Name of a pick zone. A pick zone represents a group of locations that share the same attributes for picking, such as the LPN level at which picks can be allocated, the cartonization group to which it belongs, and whether the location supports replacement picks and pre-inventory allocation. The search path searches pick zones when attempting to find inventory for allocation. |
| Location Type | Category that is used to group and configure locations that are used for similar purposes, regardless of their proximity to one another. Location type attributes define how the application tracks and processes inventory or transport equipment in the location. |
| Building | Unique identifier for a building. A building is a warehouse entity consisting of one or more areas. Inventory and location information can be reported by building. |
| Work Zone | Name or number that identifies a work zone. A work zone is a logical division of warehouse space made on the basis of physical layout and access by different types of warehouse equipment. A work zone exists inside a work area. |
| Aisle | Identifier for a passageway in the facility where operators and equipment move between racks or blocks of locations, typically to put away or pick inventory. You typically define aisles and then, in the process of defining storage locations, you can assign locations to the aisle in which they are located (a single location can be assigned to only one aisle). |
| Area | Identifier for an area. Areas are used for grouping and sorting locations in the warehouse. For example, an area named STAGING can be used to group ship staging locations; an area named CASEPICK can be used to group case pickface locations. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
