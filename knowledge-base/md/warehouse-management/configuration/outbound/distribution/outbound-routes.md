---
title: "Outbound Routes"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/outbound_routes.htm"
source: "/content/outbound_routes.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Outbound"
  - "Distribution"
  - "Outbound Routes"
sections:
  - "Add or modify an outbound route"
  - "Outbound Routes fields"
images: []
source_sha1: b6f1b921c9d1eb35d2e8db130f719c39787efad2
---
# Outbound Routes

A route is a static schedule that defines the start and end times that inventory for one or more customers will be picked up from a warehouse for delivery to one or more stops.

For example, a centralized warehouse may have one route for three customers that are in the same geographic region. Shipments for the route are picked up from the warehouse starting at 9:00 A.M. and ending at 10:00 A.M. every Wednesday. The inventory is then delivered to the three different stops.

If routes are defined, then when you allocate distributions, the application automatically creates the loads and stops for the resulting shipments. If routes are not defined, then you must manually assign the distribution shipments to loads and stops.

## Add or modify an outbound route

1.  Select **Configuration > Outbound > Distribution > Outbound Routes**.
2.  Perform one of the following tasks:
    -   To add a route, click **Add**.
    -   To modify a route, in the grid, click the route.
    -   To copy a route, in the grid, select the check box next to the route, and then click **Copy**.
3.  Enter information in the [Outbound Routes fields](#Outbound_route_fields).
4.  To define the stops along the route:
    
    **Note**: A stop is defined by a customer configuration, which is associated with address information. A customer can represent a distribution center, store, or other shipping destination.
    
    1.  Under **STOPS**, click **Route Stops**.
    2.  To add a stop:
        1.  Click **Add**. The Select a Customer window is displayed.
        2.  Select a customer, and then click **Select**. For a 3PL environment, you select a customer and client combination.
    3.  To delete a stop:
        1.  In the grid, select the check box next to the stop, and then click **Delete**. A confirmation message is displayed.
        2.  Click **OK**.
    4.  To arrange the sequence of the stops, in the grid, click the row and then drag it to the preferred position.
    5.  Click **Apply**.
5.  Click **Save**.

## Outbound Routes fields

 
| Field | Description |
| --- | --- |
| Route Name | Name of the route. A route is a static schedule that defines the start and end times that inventory for one or more customers will be picked up from a warehouse for delivery to one or more stops. |
| Carrier | Identifier for a carrier that delivers inbound inventory to the warehouse or outbound shipments to a customer. This is the identifier that will be displayed to users on the application windows and reports. In the application, a carrier can be associated with a customer, order, inbound shipment, outbound shipment, load, and service levels (such as Ground, Next Day, and Saturday Delivery). |
| Carrier Service Level | Shipping option offered by the carrier relating to the duration and cost of shipping inventory, such as overnight or two-day shipping. |
| Advanced Allocation | If Yes, the application automatically allocates the distribution orders in advance of the scheduled loading start day and time. Select Yes if you want to save time by having the application to automatically allocate the distribution order in advance of loading so that it can be picked and staged prior to the loading start time. If **Advanced Allocation** is set to Yes, you must enter a number of hours in the **Allocation Prior to Shipping** field.<br > If No, automatic allocation does not take place based on the scheduled loading start day and time. |
| Allocation Prior to Shipping | Number of hours in advance of the scheduled loading start day and time that you want the application to automatically allocate the distribution order. Only available if **Advanced Allocation** is set to Yes. |
| Loading Start Day | Day of the week that loading for the route can begin. |
| Loading Start Time | Time of day that loading for the route can begin. |
| Loading End Day | Day of the week that loading for the route must be completed. |
| Loading End Time | Time of day that loading for the route must be completed so that the transport equipment can be dispatched. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
