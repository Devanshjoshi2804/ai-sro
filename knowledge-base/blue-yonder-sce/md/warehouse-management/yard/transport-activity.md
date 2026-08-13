---
title: "Transport Activity"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/transport_activity.htm"
source: "/content/transport_activity.htm"
toc_path:
  - "Warehouse Management"
  - "Yard"
  - "Transport Activity"
sections:
  - "View transport equipment activity"
  - "View tractor activity"
  - "Transport Equipment Activity fields"
  - "Tractor Activity fields"
images: []
source_sha1: b86721ecd4ff8603b2ecd6901625577d7d0ecc7b
---
# Transport Activity

You use the Transport Activity page to view the history details of transport equipment and tractor activity. When you first access the page, you enter the date range and time duration for which to search completed transactions. You can also filter the transactions by more specific criteria; for example, you can enter a transport equipment or tractor identifier to view the activity that has been performed on the equipment or tractor, such as it being checked in, at the site, moved, or checked out.

You can search activity history using the following criteria:

-   Equipment identifier
-   Tractor
-   Activity
-   Carrier
-   Equipment type
-   Equipment status
-   Tractor status
-   Yard or door location
-   Load

## View transport equipment activity

1.  Select **Yard > Transport Activity**.
2.  Select **Transport Equipment**.
3.  In the **Search** fields, enter the date and time by which to limit the displayed activity. By default, activities that occurred within the last 24 hours are displayed.
4.  Click **Go**.
5.  View the information in the [Transport Equipment Activity fields](#Transport_Equipment_activity_fields).

## View tractor activity

1.  Select **Yard > Transport Activity**.
2.  Select **Tractors**.
3.  In the **Search** fields, enter the date and time by which to limit the displayed activity. By default, activities that occurred within the last 24 hours are displayed.
4.  Click **Go**.
5.  View the information in the [Transport Activity fields](#Tractor_activity_fields).

## Transport Equipment Activity fields

 
| Field | Description |
| --- | --- |
| Equipment | Alphanumeric identifier for transport equipment. Transport equipment numbers are not unique, can exist multiple times, and can be associated with various carriers. |
| Date | Date and time on which the activity was completed on the transport equipment. |
| User | User who performed the activity on the transport equipment. |
| Activity | Identifier for the activity that was performed on the transport equipment by a user or RF operator. For example, when equipment is checked in, "Transport Equipment Checked In" is the displayed activity. |
| Carrier | Identifier for a carrier that delivers inbound inventory to the warehouse or outbound shipments to a customer. This is the identifier that will be displayed to users on the application windows and reports. In the application, a carrier can be associated with a customer, order, inbound shipment, outbound shipment, load, and service levels (such as Ground, Next Day, and Saturday Delivery). |
| Equipment Type | Type of equipment on which the activity was performed. For example, an ocean container or refrigerated trailer. |
| Equipment Status | Current status of the transport equipment, such as Checked In, Open For Shipping, or Dispatched. |
| Yard Location | Current location of the transport equipment in the yard. This location is either a yard location or a door location. A yard location is an outdoor space in which transport equipment can be stored or parked until it is either moved to a dock door or checked out. A door location is an opening on the dock where transport equipment can be parked for the purpose of loading or unloading. |
| Load | Unique identifier for a load. A load is one or more shipments grouped together into one or more stops that are shipped on a single piece of transport equipment. |

## Tractor Activity fields

 
| Field | Description |
| --- | --- |
| Date | Date and time on which the activity was completed on the transport equipment. |
| User | User who performed the activity on the tractor. |
| Tractor | Alphanumeric identifier for a tractor. Vehicles used to haul the transport equipment, such as tractors, rail engines, and ships, are referred to as tractors. Tractor numbers are not unique, can exist multiple times, and can be associated with various carriers. |
| Carrier | Identifier for a carrier that delivers inbound inventory to the warehouse or outbound shipments to a customer. This is the identifier that will be displayed to users on the application windows and reports. In the application, a carrier can be associated with a customer, order, inbound shipment, outbound shipment, load, and service levels (such as Ground, Next Day, and Saturday Delivery). |
| Activity | Identifier for the activity that was performed on the transport equipment by a user or RF operator. For example, when equipment is checked in, "Transport Equipment Checked In" is the displayed activity. |
| Tractor Status | Current status of the tractor. A status can be assigned to standalone tractors or those assigned to shipping, receiving, or storage transport equipment.<br>-   • **Expected**: The tractor is expected to arrive at the facility, or has arrived at the facility, but has not yet been checked in.
<br>-   • **At Site**: The tractor is checked in to the yard.
<br>-   • **Dispatched**: The tractor has been checked out of the yard and is no longer tracked by the application. |
| Transport Equipment | Alphanumeric identifier for transport equipment. Transport equipment numbers are not unique, can exist multiple times, and can be associated with various carriers. |
| Location | Current location of the tractor in the yard. This location is either a yard location or a door location. A yard location is an outdoor space in which transport equipment can be stored or parked until it is either moved to a dock door or checked out. A door location is an opening on the dock where transport equipment can be parked for the purpose of loading or unloading. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
