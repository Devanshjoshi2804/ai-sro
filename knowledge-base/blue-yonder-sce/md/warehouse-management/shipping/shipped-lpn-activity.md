---
title: "Shipped LPN Activity"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/shipped_lpn_activity.htm"
source: "/content/shipped_lpn_activity.htm"
toc_path:
  - "Warehouse Management"
  - "Shipping"
  - "Shipped LPN Activity"
sections:
  - "View shipped LPN activity"
  - "Shipped LPN Activity fields"
images: []
source_sha1: ae8e42a182d0160f77c8edba87dbc718b200fa7e
---
# Shipped LPN Activity

You use the Shipped LPN Activity page to view inventory that was shipped from one or all of the warehouses in an instance, based on configured LPN levels. The page displays additional activity updates that are sent from the host system, such as when inventory was delivered, signed for, or returned. You can also view both the shipped LPN as well as its associated parent LPN details. For example, if tracking is enabled for sub-LPNs, then the shipped LPN and sub-LPN values are the same, and the LPN value represents the LPN that contains the sub-LPN.

When inventory is shipped from the warehouse, the application logs the Shipped activity at each LPN level that is enabled for shipped activity tracking. The host system then sends LPN activity information back to the application through the Shipped LPN Activity Integrator transaction (SHIPPED\_LPN\_ACTIVITY\_INB\_IFD). The activity information received from the host is not regulated and can include data for any LPN levels, whereas the application logs the initial activity only at the defined LPN levels.

You can define the following characteristics for the Shipped LPN Activity page based on your operational requirements:

-   The LPN levels at which the initial Shipped activity is logged by the application (LPN, sub-LPN, and detail LPN)
    
    **Note**: If none of the LPN levels are enabled to be logged by the application when they are shipped, the application can still receive and display subsequent activity information sent from the host.
    
-   Whether the displayed activity is for the current warehouse or for all warehouses in an instance (multi-instance support is not available)
-   The LPN activities for which an update is displayed on this page, based on the information sent from the host
    
    **Note**: If the host sends an activity for which there is no corresponding code in the application, the data in the transaction is still displayed, but there is no activity description displayed.
    

The inbound transaction must include both the client and customer for the application to process the transaction and display the shipped LPN activity. Additionally, the permissions for a user are taken into account as they relate to client access. For example, if a user is restricted to viewing information only for Client A and the host sends an update for Client B, then the record is not displayed to that user.

**Note**: The host system is responsible for sending the correct data to be displayed including the client, customer, warehouse, and a defined LPN activity code. The application does not validate any of the data that is received through the inbound transaction against the actual shipment values.

You can archive and purge shipped LPN activity records according to a job schedule, which is defined in the Console, under Jobs.

## View shipped LPN activity

1.  Select **Shipping > Shipped LPN Activity**.
2.  To limit the records that are displayed, enter a date or date range, or enter search criteria.
3.  View information in the [Shipped LPN Activity fields](#Shipped_LPN_Activity_fields).

## Shipped LPN Activity fields

 
| Field | Description |
| --- | --- |
| Event Date | Date on which the LPN activity occurred. Event dates for inventory being shipped from the warehouse are populated by the application, and subsequent event dates (such as for delivery or returns) are sent from the host system and displayed in this field. |
| Shipped LPN Activity | Activity that was performed on a shipped LPN, sub-LPN, or detail LPN. LPN activities are configurable and represent processing actions that take place throughout the shipment and delivery of inventory, such as Shipped, Delivered, or Signed. |
| Shipped LPN | Unique identifier for inventory that has shipped from the warehouse. This identifier is typically an LPN, sub-LPN, or detail LPN, based on the LPN level you have configured for shipped LPN tracking.<br > For example, if the application is configured for sub-LPNs, then an activity is logged whenever a sub-LPN is shipped, and this identifier represents the sub-LPN. However, if both LPNs and sub-LPNs are tracked, then this field displays the identifier to which the LPN activity relates. |
| LPN Level | LPN level of the identifier in the **Shipped LPN** field, such as LPN, sub-LPN, or detail LPN. |
| Warehouse | Unique identifier for the site from which an LPN was shipped, or the site that needs to be referenced in the transaction (such as when an LPN is delivered, the sending warehouse should be referenced to know the LPN arrived). The application must be configured for instance level (multi-warehouse) tracking of shipped LPNs before activities that reference other facilities are displayed, such as inventory being shipped from another warehouse in the instance.<br > **Note**: While this value should be a warehouse defined in the application, the host system is responsible for sending the correct data to be displayed. The application does not validate any of the data that is received through the inbound transaction against the actual shipment values. If the application is configured to display activities for only the current warehouse, and if the warehouse identifier is populated incorrectly in the transaction or not at all, then the activity will not be displayed unless the configuration is changed to show instance-wide data. |
| Ship From | Identifier for the facility, distributor, or organization from which the LPN was shipped. When an LPN is initially shipped and the application logs an activity, the Ship From value is the warehouse. An LPN can have multiple records with different Ship From values depending on whether the LPN requires intermediate stops before its destination. However, subsequent values are only received from the host and displayed by the application; the application does not validate any of the data that is received. |
| Route To | Identifier for the distributor or organization to which the LPN is initially sent before arriving at its destination. The route-to and ship-to are the same if the LPN does not require an initial stop. |
| Ship To | Customer to whom the LPN is to be shipped, as originally defined on the order. If multiple customers are associated with an LPN, a separate record is displayed for each customer.<br > **Note**: The host system is responsible for sending the correct data to be displayed, including the customer name. The application does not validate any of the data that is received through the inbound transaction against the actual shipment values. |
| Insert Date | Date and time at which the LPN activity record was processed and displayed in the application. |
| Client | Unique identifier for the client associated with the ship-to customer defined on the order. If multiple clients are associated with an LPN, a separate record is displayed for each client.<br > **Note**: The host system is responsible for sending the correct data to be displayed, including the client name. The application does not validate any of the data that is received through the inbound transaction against the actual shipment values. |
| LPN | Unique identifier for inventory. Typically, an LPN refers to a pallet; however, it can refer to inventory received at less than pallet quantity. The LPN is the license plate by which the inventory is tracked in the facility. |
| Sub-LPN | Unique identifier for a case of inventory. |
| Detail LPN | Unique identifier for inventory at the unit or each unit of measure. |
| LPN UCC | Uniform Code Council (UCC) standard inventory identification number for the LPN. |
| Sub-LPN UCC | Uniform Code Council (UCC) standard inventory identification number for the sub-LPN. |
| Tracking Number | Unique identifier used by a parcel carrier to track a parcel throughout the delivery process. |
| Handling Unit | Unique identifier for a handling unit that is tracked as an individual as well as collectively by handling unit type. A handling unit is an object (such as a pallet, tote, or a piece of transport equipment) that has value and that you want to track either individually or collectively.<br > The identifier in this field refers to the handling unit for the LPN level that is being tracked. For example, if the application is configured to log the shipped LPN activity only for sub-LPNs, and handling units are tracked at the LPN level, then no value is displayed in this field. To see handling units for LPNs and sub-LPNs, then both LPN levels must be selected for shipped LPN activity tracking in the outbound loading configuration. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
