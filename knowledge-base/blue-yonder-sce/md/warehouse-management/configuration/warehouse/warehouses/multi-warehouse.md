---
title: "Multi-warehouse"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/multi-warehouse.htm"
source: "/content/multi-warehouse.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Warehouse"
  - "Warehouses"
  - "Multi-warehouse"
sections:
  - "Support multiple warehouses in one instance"
  - "Multiple warehouses in one instance versus multiple instances"
  - "Work in a warehouse"
  - "How multi-warehouse affects each area of Warehouse Management"
  - "Date and time data"
  - "Warehouses"
  - "RF devices"
  - "Receiving and putaway"
  - "Inventory management"
  - "Order management"
  - "Allocation"
  - "Replenishments"
  - "Picking"
  - "Shipping"
  - "Work orders"
  - "Cross-docking"
  - "Work management"
  - "Yard management"
  - "Cycle counting"
  - "Host transactions"
  - "Warehouse Labor Management"
  - "Slotting"
  - "Campus reporting"
  - "Translated warehouse"
  - "Change the warehouse for outbound orders"
  - "Redirected planned inbound orders"
  - "Outbound transactions"
  - "Set up and configure a multi-warehouse environment"
  - "Configure shipping between warehouses"
images: []
source_sha1: 046f1db712e8cdb3eb382e32b4df96987607bc04
---
# Multi-warehouse

The application can be configured to support multiple warehouses within one instance or within multiple instances. Multi-warehouse configurations define warehouse work, campus reporting, shipping, and other attributes for processes performed within Warehouse Management and its integrations.

## Support multiple warehouses in one instance

For facilities with multiple warehouses under the same business ownership, the following single instance configurations are supported:

-   Campus installs: Facilities with multiple buildings located in one physical location, often with a shared yard or inventory.
    
-   Hub and spoke: Facilities that have many smaller warehouses supporting or supported by a larger main facility. Examples include retailers with forward distribution centers (DC) or manufacturers that use several satellite warehouses to support a main DC.
    

In these multi-warehouse configurations, each facility can have its own unique processing rules and configuration, while reducing the hardware requirements and administrative overhead that would be required for separate instances.

The supported configurations of a multi-warehouse environment are different for cloud and on-premises deployments of Warehouse Management. The configurations described in this topic apply directly to cloud installations to provide optimal service levels.

**Note**: Contact your Blue Yonder project team to configure a multi-warehouse environment with a cloud deployment.

The same guidelines and configurations are recommended for on-premises deployments, but alternative patterns are supported.

## Multiple warehouses in one instance versus multiple instances

The following table lists some of the differences between configuring multiple warehouses in one instance of Warehouse Management versus configuring multiple instances of Warehouse Management (one for each warehouse).

 
| Multi-warehouse | Multi-instance |
| --- | --- |
| Individual facilities are small in size or processing needs and support a larger distribution center. | Individual facilities are large in size or processing needs. |
| IT staff is in one central location. | IT staff may be required in each location. |
| Single database is needed to support data for all locations. | Separate database is needed for each location. |
| Warehouse Management updates and customizations only need to be applied to one production instance. | Warehouse Management updates and customizations must be applied to multiple production instances. |
| Only one set of MOCA-based processes, such as background tasks. | Separate sets of MOCA-based processes, such as background tasks. |
| All date and time information is stored in the default system time zone of the single server, which is recommended to be the time zone of the main facility.<br > **Note**: A multi-warehouse instance can only have one time zone associated with it. This means that all warehouses must be configured to use the default system time zone, even if they are not physically located in that time zone. | All date and time information is stored in the time zone of each facility's server instance. |
| Certain configuration information, such as customers, suppliers, items, and settings, can be shared across warehouses; item attributes can be overridden at the individual warehouse level. | Configuration information is specific to each instance, even though it might be the same for all warehouses. |

## Work in a warehouse

A user's authorization is limited to one or more warehouses. Users can only maintain and view data, and perform tasks in their current warehouse—even if they are authorized for multiple warehouses. The warehouse name that is displayed in the application is the warehouse in which a user is currently working.

When users log in, if they are authorized for more than one warehouse, they can select the warehouse in which they want to work. To work in a different warehouse, the user must log in to the other warehouse. If users are only authorized for one warehouse, they do not have the option to select a different warehouse.

## How multi-warehouse affects each area of Warehouse Management

A multi-warehouse configuration affects the following areas of Warehouse Management.

### Date and time data

Date and time data is displayed on pages in the web client and reports using the default system time zone or a preferred time zone.

The default system time zone is the time zone used for all date and time information stored within the application instance as part of a user session. For information on time zone configuration, see the _Warehouse Management Time Zone Configuration Guide_.

**Note**: A multi-warehouse instance can only have one time zone associated with it. This means that all warehouses must be configured to use the default system time zone, even if they are not physically located in that time zone.

### Warehouses

In a Warehouse Management instance, the same aisle, zone, building, location, work area, and work zone can exist in multiple warehouses, but each has a warehouse-specific definition.

### RF devices

A radio frequency (RF) device is assigned a code that is warehouse specific and limits the RF device to data and operations associated with a specific warehouse.

**Note**: An authorized user can reconfigure an RF device for another warehouse.

### Receiving and putaway

-   **Planned inbound orders and inbound shipments**: Warehouse specific, but can exist in multiple warehouses.
-   **Receiving and storage configurations**: Warehouse specific.
-   **Inbound quality and item configuration**: Warehouse specific and configured at the warehouse level.
-   **Returns**: Warehouse specific, and can only be processed in the current warehouse; although the same return number can exist in multiple warehouses.
-   **Transport equipment**: Outbound from one warehouse and later inbound at another warehouse.
-   **Suppliers**: Not warehouse specific.

### Inventory management

-   **Item information**: Shared by all warehouses. Item attributes, however, can be overridden at the warehouse level. When an override occurs, the modified item record becomes warehouse specific.
-   **Inventory identifiers (LPN, sub-LPN, or detail LPN)**: Unique, and can exist in only one warehouse at a time.
-   **Holds**: Warehouse specific, but can exist in multiple warehouses.

### Order management

-   **Outbound orders, order activity, order displays, and order reports**: Warehouse specific. Portions of the same order can exist in more than one warehouse.
-   **Customers and wave rules**: Not warehouse specific.

### Allocation

Allocation follows warehouse-specific policies for the current warehouse, and looks for inventory in locations associated with the warehouse in which the orders, work orders, and replenishments exist.

### Replenishments

-   **Replenishments**: Generated for all warehouses or a single warehouse.
-   **Triggered and top-off replenishments**: Generated for the current warehouse.
-   **Emergency replenishments**: Generated for the warehouse to which the order that they are replenishing belongs.
-   **Replenishment rules**: Warehouse specific.
-   **Replenishment displays and reports**: Apply to the current warehouse.

### Picking

-   **Pallet building, order overpack, and order consolidation**: Occurs in the warehouse in which the inventory exists.
-   **Picking**: Warehouse specific.
-   **Picking reports and displays:** Applies to the current warehouse.
-   **Pick cancel codes and label formats**: Not warehouse specific.

### Shipping

-   **Outbound shipments**: Warehouse specific and cannot be duplicated across warehouses. All orders assigned to a shipment must belong to the same warehouse.
-   **Shipping reports**: Apply to the current warehouse.
-   **Shipping between warehouses**: When a shipment is sent from one warehouse to another warehouse in the same Warehouse Management instance, an advance shipment notice (ASN) is generated that can be used as a planned inbound order ASN by the receiving application. For more information on configuring shipping between warehouses, see [Configure shipping between warehouses](#Configure_shipping_between_warehouses).

### Work orders

-   **Bill of material (BOM)**: Warehouse specific. The same BOM number can exist in more than one warehouse, but represents a different BOM in each warehouse.
-   **Production lines, work orders, work order configurations, work order management reports, and transactions**: Warehouse specific.
-   **Production line inventory and return-to-stock inventory**: Put away to locations in the same warehouse as the production line.

### Cross-docking

-   **Cross-docking configuration**: Warehouse specific.
-   **Cross-docking displays**: Apply to the current warehouse.

### Work management

-   **Work management functionality**: Supported on an application level and a warehouse-specific level. Every warehouse in the Warehouse Management instance can use the application-level configuration for work operations. However, a warehouse-specific configuration can also be defined to specify such attributes as base priority and escalation timing.
-   **User operation access**: Defined at the application level.
-   **Warehouse equipment operation access:** Warehouse specific. The application retrieves and assigns work that matches the warehouse of the device that is requesting the work.
-   **Creation of work**: Consolidated by warehouse; a work request does not span multiple warehouses. When a work request is completed and removed from the application, a work history record is generated and tracked by warehouse.
-   **RF operators**: Access work areas that exist in the warehouse to which they are logged in, and for which the RF device is authorized.

### Yard management

-   **Dock calendars and appointments**: Warehouse specific.
-   **Transport equipment activity**: Tracked by warehouse.
-   **Carrier codes and transport equipment**: Not warehouse specific.

### Cycle counting

-   **Cycle count calendar**: Warehouse specific, as are functions associated with generating and deleting cycle counts, and performing cycle and audit counts.
-   **Cycle count request:** Not allowed to span multiple warehouses (for example, to count a specific item in all warehouses). In addition, cycle and audit count work is not combined across warehouses.
-   **Cycle count settings**: Can be warehouse specific.
-   **Count history**: Tracked by warehouse.

### Host transactions

Inbound and outbound transactions support the use of warehouse IDs. In a multi-warehouse environment, a warehouse ID is required for warehouse-specific inbound transactions such as for outbound order, planned inbound order, and inventory downloads. In a single warehouse environment, a warehouse ID is not required for inbound transactions.

### Warehouse Labor Management

When Warehouse Management is integrated with Warehouse Labor Management, multiple warehouses on the same instance can each communicate with their own instance of Warehouse Labor Management.

### Slotting

When Slotting is installed and enabled in Warehouse Management, the interface supports identifying warehouse-specific locations.

## Campus reporting

Campus reporting allows you to configure, in a multi-warehouse environment, which warehouses are visible to the host. When transactions are sent to a host application, they can be sent as if they originated from a different warehouse. Also, outbound orders, shipments, and planned inbound orders downloaded from the host are directed to a single warehouse, but can be redirected to the warehouse that should fulfill the processing.

### Translated warehouse

For each warehouse, you can define which warehouse is visible to the host. This is called the translated warehouse. Use of a translated warehouse is optional, and only applies in a multi-warehouse environment.

You specify a translated warehouse, for example, if your host system requires communications to take place to and from a single warehouse, instead of from multiple warehouses. It is also useful if the host downloads outbound orders, shipments, and inbound orders that are meant to be fulfilled by more than one warehouse.

All transactions from the warehouse to the host that specify a warehouse contain the name of the translated warehouse. As a result, they appear to originate from the translated warehouse instead of the warehouse in which the activities occurred.

All inbound orders, outbound orders, and shipments for warehouses are downloaded from the host to the translated warehouse. They can then be redirected to the warehouse that should fulfill the processing.

A client can be associated with one or more warehouses, including the translated warehouse.

### Change the warehouse for outbound orders

Orders sent from the host are directed to the translated warehouse. You can redirect orders, if necessary, to any warehouse associated with the translated warehouse that should fulfill the orders. If you select an order to redirect that is tied to an outbound shipment, Warehouse Management automatically selects all of the other orders on the same shipment to be redirected to the same warehouse. Once an order has been allocated, it can no longer be redirected.

### Redirected planned inbound orders

Planned inbound orders sent from the host are directed to the translated warehouse. You can redirect planned inbound orders, if necessary, to any warehouse associated with the translated warehouse that should receive the inventory. If you select a planned inbound order to redirect, Warehouse Management automatically selects the remaining planned inbound orders on the transport equipment to be redirected to the same warehouse. Once transport equipment has been checked in or any inventory created by a planned inbound order advanced shipment notification (ASN) has been deposited, the associated inbound order can no longer be redirected. See the Warehouse Management topics in the Supply Chain Execution Help.

### Outbound transactions

In a multi-warehouse environment, all outbound transactions from Warehouse Management to the host that specify a warehouse contain the translated warehouse identifier, and are displayed to the host to have originated from the translated warehouse.

## Set up and configure a multi-warehouse environment

Before you can start using a single instance of Warehouse Management for multiple warehouses, you must complete the following setup tasks:

**Note**: Your Warehouse Management instance should be provisioned (cloud) or installed (on-premises) prior to starting this procedure. All post-installation or upgrade tasks should also be complete.

1.  Define each warehouse. See [Add or modify a warehouse](../warehouses.md).

**Note**: The **Time Zone** field is informational only. The time zone of all warehouses in an instance is set by the default system time zone.

3.  Configure each warehouse's unique processing needs as you would for a single warehouse environment.
4.  Configure each user's access to one or more warehouses.
5.  If you are shipping inventory between warehouses, then [configure shipping between warehouses](#Configure_shipping_between_warehouses).

## Configure shipping between warehouses

To support shipments between warehouses, you must complete the following tasks.

**Note**: This feature is supported in both multiple and non-multiple warehouse environments. It also sends an ASN directly to a customer who is set up to receive it.

1.  **Configure Integrator.**
    -   The Integrator instance of the sending system must be configured to have a system for each of the receiving systems that receive an ASN. Each of the receiving systems must be properly configured with the host and port of the system's instance. In a multi-warehouse scenario where all of the receiving warehouses are sharing the same instance, it is valid to have a single Integrator system for all of the warehouses. In this configuration, the sending system is the same as the receiving system.
    -   Add each of the receiving systems as a receiving system for the SHIP\_LOAD\_OUB\_IFD interface document. Add the BLOCK\_INTER\_WAREHOUSE\_IFD\_SEG blocking algorithm to the system for the IFD and set it to block when T is returned.
2.  **Configure customers.**
    -   Each warehouse that is receiving shipments (ASNs) from another warehouse, must be defined as a customer for the shipping warehouse (sending system). This is the customer to which the order is being shipped. The actual customer identifier that is assigned is not important. However, it is important to set the **ASN System** field to the Integrator system (as defined previously when configuring Integrator) for this warehouse.
    -   In a multi-warehouse scenario where the sending system and receiving system are sharing the same instance, it is important to set the **Tracking** field to Yes (on the customer configuration). This ensures that the inventory is moved out of the sending warehouse so that it can be received into the receiving warehouse.
    -   Assign an address to the customer. This address must have an identifier that exactly matches the warehouse identifier of the receiving system or warehouse. This value is used to populate the **Warehouse ID** field in the ASN.
3.  **Configure outbound orders in the shipping warehouses.**
    -   An order that is destined for another warehouse, must have a ship-to customer defined. This ship-to customer must be the warehouse (defined by a customer configuration) so that the ASN can be mapped to the correct Integrator system and the **Warehouse ID** field can be correctly populated on the ASN.
4.  **Configure planned inbound orders in the receiving warehouses.**
    -   The planned inbound order's supplier number must be the shipper's warehouse ID.
    -   The planned inbound order's inbound order type must either be the customer PO type or the order type on the shipper's order.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
