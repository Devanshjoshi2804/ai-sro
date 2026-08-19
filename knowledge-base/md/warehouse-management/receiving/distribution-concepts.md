---
title: "Distribution concepts"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/distribution_concepts.htm"
source: "/content/distribution_concepts.htm"
toc_path:
  - "Warehouse Management"
  - "Receiving"
  - "Distribution concepts"
sections:
  - "Flow-through distribution processing"
  - "Over distribution"
  - "Distribution deposit"
  - "Distribution deposit process"
  - "Residual inventory and exceptions"
  - "Distribution shortages"
  - "Customers and put-to-grid locations"
  - "Flow-through distribution process"
images: []
source_sha1: c51a3b7762155440c3cca5ee0dc5f587b70416e6
---
# Distribution concepts

Distributions manage how received inventory is allocated within a warehouse. You can make adjustments to distribution processes that can improve the productivity and efficiency of warehouse receiving activities.

## Flow-through distribution processing

The application uses flow-through distribution processing to provide a highly automated and efficient method of receiving inventory from a supplier and shipping the same inventory to a customer without placing the inventory in storage locations. The method reduces movements, keeps each customer's inventory organized and separated at all times, and respects the static schedule of customers and routes.

A distribution is a pre-allocation of a warehouse receipt to a customer. This process pushes inventory from receiving out to one or more customers, in contrast to an order which pulls inventory from the warehouse to the customer. A distribution usually involves new merchandise that you want to ship out in appropriate amounts to appropriate customers, in contrast to an order which usually involves existing inventory that the customer needs so that they can restock their shelves.

For example, consider a warehouse that expects to receive an inbound order line of 100 units of a new popular DVD. The warehouse needs to distribute that inventory to one large store and two small stores, by shipping 50 units to the large store and 25 units to each of the small stores. The user in the warehouse can create a distribution so that when the inventory is received, an outbound order and order lines will be automatically created to ship the inventory to the selected stores.

The distribution process also identifies whether incoming inventory is a distribution candidate. Incoming transport equipment may include some inventory that is meant for a distribution and some that is not. Instead of holding all of the incoming inventory until the distribution occurs, the application splits the inventory based on its distribution candidacy. Inventory that is a candidate for distribution is held until the distribution occurs; non-distribution inventory is available for putaway immediately after receiving. Distribution quantities are assigned to customers according to configurable rules and rule sets.

**Note**: All distributions tied to an inbound order line must be filled to 100% before any of that inventory is considered for storage.

An inbound order line can be associated with multiple distributions; if it is, the application uses the distribution type configuration to determine how the inventory is distributed to multiple customers. See [Distribution Types](../configuration/outbound/distribution/distribution-types.md).

An outbound order can be associated with multiple distributions but each outbound order line can be associated with only one distribution. You can configure the distribution to automatically create a new outbound order, or you can associate the distribution with an existing outbound order. Each time you create a distribution for an existing outbound order, a new outbound order line is added to the outbound order, so that the application creates one shipment for multiple distributions from multiple inbound order lines that are intended for the same customer.

## Over distribution

An over distribution is a distribution of inventory over and above the amount of the store order. This can occur when the amount of the inventory that arrives at the warehouse is greater than what was expected on the inbound order line. If your distribution and inbound order are configured to allow distribution overages, the additional inventory can be distributed to stores even though the outbound orders have been filled. When unplanned inventory is received you may have to over distribute to the stores instead of holding the inventory as stock.

For example, you have a planned inbound order line that for 150 cases of shoes from which 100 cases will be immediately distributed and 50 will be stock quantity. When the inventory arrives, you receive 160 cases of shoes, 10 over the planned quantity. Depending on how the application is configured, the extra 10 cases are either distributed with the original 100 cases, or placed with the stock quantity for a total of 60 cases. If the extra 10 cases are pushed out with the original distribution quantity of 100 cases, then an over distribution occurs and the customer receives 110 cases.

Over distributions follow different rules than normal distributions. If there are multiple customers that you must over distribute to, you configure a rule to define how the excess inventory is assigned to the customers.

In order to allow an over distribution, you must perform the following tasks:

-   Configure the distribution to allow over distribution (set **Over Distribute** field to Yes). See [Add or modify a distribution from an inbound order line](inbound-shipments/procedures-for-inbound-shipments.md).
-   Configure the inbound order lines associated with the distribution to specify the ones for which you want to distribute overages (set **Distribute Overage** field to Yes). See [Add or modify an inbound order line](inbound-shipments/procedures-for-inbound-shipments.md).
    
    **Note**: Over distributions can only occur if both the inbound order line and the customer allow over distribution. Configuring over distribution at the inbound order level indicates that if excess inventory is received for that inbound order line, you can assign it to stores that allow over distribution. Configuring over distribution at the distribution level indicates that the customer associated with the distribution accepts over distributed inventory that comes from the inbound order line on the distribution.
    

## Distribution deposit

Distribution deposit is a process in which picked inventory being distributed to multiple stores is directed to separate locations, one for each store, and then consolidated for shipment according to configurations. With this process you can choose the designated locations for consolidation and the UOMs that must be consolidated into a carton before being placed on a pallet.

Distribution deposit is similar to the put-to-store process in that both processes put inventory in a location to combine for a particular store before being actually shipped to the store. However, a distribution location contains inventory that is destined for a specific store, the outbound shipment has been planned, and the inventory is released and picked. All of the inventory in a distribution location is part of an active shipment and ships together on the same transport equipment. A put-to-store location contains inventory that has not yet been planned to a shipment or released for picking. Inventory placed in a put-to-store location is held for a store until it is ready for shipment, at which time it is released and picked. Put-to-store inventory in a single location can also be shipped at different times and on different transport equipment instead of all being planned to one shipment as in the case of distribution locations.

## Distribution deposit process

During the distribution deposit process, the application directs the operator through the distribution locations in a logical order, based on travel sequence, until all inventory planned for distribution has been placed in the distribution locations. The distribution pallets or cartons remain in the distribution location until they are closed and directed to move out of the location to a staging zone or to be loaded onto waiting transport equipment. Pallet LPNs and carton LPNs are considered closed when no additional inventory can be added to the existing LPN. Closing a pallet LPN or carton LPN is completed either manually on an RF device by the operator working in the distribution zone, or automatically by the application when the final pick for a shipment is deposited. See [Distribution setup](../configuration/outbound/distribution.md).

If the RF device is configured to do so, when the operator is directed to a location for deposit, the application looks for an existing, uncompleted LPN on which to deposit the inventory. At this point, the operator has the following options:

-   Deposit the entire quantity to an existing LPN
-   Deposit a partial quantity to the existing LPN and close it. The remaining quantity is either deposited to another existing LPN or a new partial LPN is created.
-   Choose not to deposit any quantity to the existing LPN, and instead create a new partial LPN from the deposited inventory
-   Skip the location and return to it later
-   Exit the distribution deposit and receive a prompt in an undirected deposit screen to drop the inventory for another operator to resume later

When the operator completes the final deposit for a shipment, the containers are closed either manually or automatically, depending on how the application is configured. After the containers for a shipment are closed, a configuration for the location type determines which one of the following actions takes place:

-   The RF Shipment Complete screen is displayed, and the containers are automatically transferred to the operator's RF device for depositing to the next location in the movement path.
-   The RF Shipment Complete screen is not displayed, and the application creates directed work to move the containers to the next location in the movement path.

After the operator completes the deposit work, a configuration determines whether the operator must perform an audit to verify the quantity of the residual inventory (which could be zero). If an audit is required, the operator enters the quantity and the application compares the entered residual quantity against the expected residual quantity. If the quantities match, the audit passes and the operator is directed to place the residual inventory in a storage location determined by putaway; if the residual quantity is zero, then the operator can begin another task. If the residual inventory does not match the quantity expected by the application, the audit fails and the inventory is directed to an exception location where it can be determined what caused the discrepancy in the residual inventory.

If you do not require audits, then after the distribution deposit process is complete, any residual inventory is returned to storage.

## Residual inventory and exceptions

Residual inventory is planned excess inventory that exists after the distribution deposit process is complete. When an operator moves inventory through distribution deposit locations, it is possible that not all of the inventory is needed for the outbound orders. At the completion of the distribution deposit process, depending on the configuration for the movement zone, the operator may be required complete an audit. If the amount of excess inventory matches the expected amount of excess and the audit is successful, the inventory is considered residual and it is directed to a storage location through putaway.

Exceptions occur when there is a discrepancy in the amount of actual residual inventory and the expected residual quantity at the end of the deposit process and the audit fails. In this case, the operator is directed to deposit the unplanned inventory into an unexpected exceptions location. A user must determine what the issue is and then gather information on how to resolve it. When resolved, the operator can clear the exception and move the inventory out of the unexpected exception location. See [View and resolve distribution exceptions](receiving-issues/procedures-for-receiving-issues.md).

**Note**: For voice device operators, the configuration of unexpected exception locations determines whether the operator is asked to count the quantities of each excess item and speak them into the voice device.

## Distribution shortages

Distribution shortage allocations are generated when there is not enough inventory to fill distribution orders from the expected received quantity. Shortages can happen for a number of reasons, but the result is that one or more distribution orders will not be filled to 100%. In an attempt to ensure that orders for a distribution are not shipped short, you can configure the distribution and the outbound order line to allocate inventory from storage to fill a distribution order.

Shortages are determined when an inbound shipment is closed. At that point, the application validates the distributions against the shipment to identify any shortages and if shortages exist, then a new outbound order line is created for the shortage quantity. If the original distribution is allocated, the application assigns the new order line to the same shipment as the original distribution and then allocates it. If the original distribution is not allocated, the application still assigns the order line to the same shipment but does not allocate the inventory. If there is no shipment planned for the distribution, the application only creates the new order line. The application associates the new outbound order line with the original distribution so that when shipment planning or allocation takes place the new order line is included.

You can indicate whether a distribution is eligible for allocation from storage by setting the **Allocate From Storage for Shorts** field to Yes on the outbound order line. See [Add or modify a distribution from an inbound order line](inbound-shipments/procedures-for-inbound-shipments.md) and [Add or modify an order line](../outbound-planner/outbound/procedures-for-orders.md).

## Customers and put-to-grid locations

A customer is a retail establishment that sells merchandise to the end consumer. In the application, a customer has a facility with a static address to which the warehouse ships inventory on a route or static schedule.

Put-to-grid locations are warehouse locations that are defined for each customer, and are designed to hold inventory for flow-through distributions that have been received but have not yet been allocated for the customer. For each put-to-grid location, you can specify the following configurations:

-   The LPN levels that can be stored in the location (LPN, sub-LPN, and detail LPN).
-   Types of inventory that can be stored in a specific put-to-grid location based on any attribute of the distribution or customer. This is useful, for example, when you want to keep inventory separate by department for ease in stocking at the customer facility. A default location can be defined to hold inventory that does not have the special attributes.

As inventory is moved into put-to-grid locations that are configured for manual consolidation, an operator can manually consolidate case-level and detail-level inventory onto pallets. For example, in a case put-to-grid location, users can manually build the cases into a pallet and then manually transfer the pallet from the case put-to-grid location to the pallet put-to-grid location. Then when the distribution is allocated, the operator can be directed to transfer an entire pallet LPN to the customer's ship staging location instead of having to do multiple case or each transfers.

## Flow-through distribution process

The following steps describe flow-through distribution processing:

**Note**: You allocate distributions in a wave by using the ORD-STORE-SELECTION wave rule. See [Allocate a wave](../shared-functions/waves-and-picks/procedures-for-waves.md).

1.  Create a distribution for the appropriate planned inbound order line. For each order line, you can create a separate distribution for each customer. See [Add or modify a distribution from an inbound order line](inbound-shipments/procedures-for-inbound-shipments.md).
    
    For example, if you have 3 planned inbound order lines that you want to distribute to 20 customers, you create 60 distributions (3 distributions for each of the 20 customers). When the distributions are created, the application automatically creates the outbound orders and order lines for each distribution. In addition, if routes have been created, then when distributions are allocated, the application automatically creates the stops and loads for the resulting shipments.
    
2.  Receive inventory for the planned inbound order line into the warehouse. When inventory for a flow-through distribution is identified into the warehouse, the inventory is associated with distributions in priority order. When the priority of multiple distributions is the same, the application associates full pallets and full cases to applicable distributions before partial pallets or eaches. The application prompts the operator through splitting the inventory at the case and each level if there are multiple next locations on the movement paths of a pallet's inventory.
3.  If distributions have been allocated, then, as directed by the application, cross-dock to ship staging locations defined for the customers associated with the distributions. Put away eaches, as directed by the application, to put-to-grid detail locations. Split the LPNs as directed by the application.
4.  If distributions have not been allocated, then, as directed by the application, put away the inventory to the put-to-grid locations defined for the customers. Split the LPNs as directed by the application.
5.  As applicable, in put-to-grid detail LPN and sub-LPN locations, build eaches and cases onto pallets and move the pallets to put-to-grid LPN locations.
6.  After a distribution is allocated, any inventory waiting in put-to-grid locations is allocated and moved to the ship staging locations defined for the customers.
7.  Load the inventory onto the transport equipment.
8.  If all the inventory does not fit, then split the shipment.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
