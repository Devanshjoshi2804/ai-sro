---
title: "Returns concepts"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/returns_concepts.htm"
source: "/content/returns_concepts.htm"
toc_path:
  - "Warehouse Management"
  - "Returns"
  - "Returns concepts"
sections:
  - "Returns"
  - "Returns operations"
  - "Return order statuses"
images: []
source_sha1: 80acab7e8fd16b862c5bbcc2c9c794629cb39f1e
---
# Returns concepts

You use the Returns module to manage the people, equipment, and inventory involved in returns processes. You can make adjustments to inventory, work, orders, and other factors that can improve the productivity and efficiency of warehouse packing activities.

## Returns

A return order is an order that describes inventory that has been returned to the warehouse from a customer. A return order is required to process all returned inventory, whether expected or unexpected.

An expected return is one that is downloaded from the host or created from the original outbound order. For example, if a customer orders an item and wants to return it, the customer either submits a return request (in which case the return order is downloaded from the host) or sends the item back without prior authorization (in which case the return order can be created from the original outbound order).

An unexpected return is the result of inventory being returned to the warehouse without a return order and the original order no longer exists. For example, if an original order was purged from the application and the customer returns the inventory, an unexpected return can be created to process the inventory. In this scenario, a return label may be shipped with the original order; that is, the customer sends a return label back to the warehouse with the inventory. The information from the return label is then used to create a new, unexpected return.

## Returns operations

The Returns module provides the following pages for processing and viewing returns:

-   **Return Processing**: Used to process return orders from a return arrival LPN. During processing, the operator identifies the source (customer), the inventory, the disposition of the inventory, and the requested actions (such as a refund or replacement). When processing is complete, the operator is directed to deposit the completed inventory to a pallet so that it can be taken to its next destination.
-   **Return Orders**: Used to view return orders to determine their status and reference information. While viewing information, you can close a return order.
-   **Return Arrival LPNs**: Used to view the LPNs that contain returned inventory to determine their arrival date, location, reference number, and number of cartons that require processing.

## Return order statuses

A return order (expected or unexpected) transitions through the following statuses:

-   **Open**: The return order was created but no inventory has been processed for the return. The return details can be modified.
-   **In Progress**: The return order was created and at least one item has been processed for the return. The return details can be modified and additional items can be added.
-   **Closed**: All inventory for the return order has been processed and the return was manually closed. The return details cannot be modified and items cannot be added.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
