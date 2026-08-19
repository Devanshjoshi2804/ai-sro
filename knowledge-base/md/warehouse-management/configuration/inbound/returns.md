---
title: "Returns"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/returns_config.htm"
source: "/content/returns_config.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inbound"
  - "Returns"
sections:
  - "Configure returns"
  - "Returns fields"
images:
  - "/content/resources/images/image430894.png"
  - "/content/resources/images/image430894.png"
  - "/content/resources/images/image430894.png"
  - "/content/resources/images/image430894.png"
source_sha1: f03efe5102e1bc7c3b4b6faded9a475e56d90fd0
---
# Returns - Configuration

Returns processing is the method by which inventory is identified back into the warehouse after being returned to the warehouse from a customer.

When you configure returns processing, you specify the following attributes:

-   Whether to enable the RF returns arrival process. This process requires the receiving operator to record the arrival of a return LPN, and then move the LPN to a returns processing location.
-   Whether users can process returns for which a return order and original order does not exist
-   Whether users can create a new return order based on an original order
-   Whether users can add unexpected items to an existing return order
-   Whether a value is required for both the Carrier and Shipment Reference fields for any new return that is created from an original order
-   The values that are available for selection during returns processing for the following attributes:
    -   Reasons that indicate why the item was returned; for example, Damaged or Wrong Size
    -   Conditions that indicate the state of the returned item; for example, Like New or Defective
    -   Actions that should be taken (based on the customer's request); for example, No Replacement, Replacement Requested, or Refund Requested. The application does not create orders for replacement items based on the selected action; instead, this information is sent to the host where a replacement order can be created.
    -   Inventory status rules that determine the default inventory status that is assigned to returned inventory based on rule criteria. The criteria for a status rule includes an attribute and attribute value; if returned inventory matches the attribute criteria for a rule, the status defined in the rule is assigned to the inventory. The returns processing operator can override the default status that is assigned to inventory based on these rules.

## Configure returns

1.  Select **Configuration > Inbound > Returns**.
2.  Enter information in the [Returns fields](#Returns_fields).
3.  To add or modify a return reason:
    1.  Click **Reasons**. The Reasons page is displayed.
    2.  Perform one of the following tasks:
        -   To add a return reason, click **Add**.
        -   To modify a return reason, in the grid, click the reason.
        -   To copy a return reason, in the grid, select the check box next to the reason, and then click **Copy**.
    3.  Enter information in the following fields:
        
        | Field | Description |
        | --- | --- |
        | Reason | Value that describes why the item was returned to the warehouse from the customer. The values available for selection are based on what has been configured for the client or warehouse. |
        | Description | Text that further describes the return reason. |
        | Client | Client for which this reason is a valid selection when processing returns. |
        
    4.  Click **Save**.
    5.  To change the sequence in which a return reason is displayed to a user that is processing a return, drag the reason to the preferred position in the list. The sequence numbers are automatically updated.
    6.  Click ![Previous page](../../../../images/resources/images/image430894.png).
4.  To add or modify a return condition:
    1.  Click **Conditions**. The Conditions page is displayed.
    2.  Perform one of the following tasks:
        -   To add a return condition, click **Add**.
        -   To modify a return condition, in the grid, click the condition.
        -   To copy a return condition, in the grid, select the check box next to the condition, and then click **Copy**.
    3.  Enter information in the following fields:
        
        | Field | Description |
        | --- | --- |
        | Condition | Value that describes the state of the item, especially with regard to its appearance, quality, or working order. The values available for selection are based on what has been configured for the client or warehouse. |
        | Description | Text that further describes the return condition. |
        | Client | Client for which this condition is a valid selection when processing returns. |
        
    4.  Click **Save**.
    5.  To change the sequence in which a return condition is displayed to a user processing a return, drag the condition to the preferred position in the list. The sequence numbers are automatically updated.
    6.  Click ![Previous page](../../../../images/resources/images/image430894.png).
5.  To add or modify a return action:
    1.  Click **Actions**. The Actions page is displayed.
    2.  Perform one of the following tasks:
        -   To add a return action, click **Add**.
        -   To modify a return action, in the grid, click the action.
        -   To copy a return action, in the grid, select the check box next to the action, and then click **Copy**.
    3.  Enter information in the following fields:
        
        | Field | Description |
        | --- | --- |
        | Action | Value that describes the action to be performed as a result of the item being returned. The action is typically in compliance with the customer request associated with the return order. The values available for selection are based on what has been configured for the client or warehouse. |
        | Description | Text that further describes the return action. |
        | Client | Client for which this action is a valid selection when processing returns. |
        
    4.  Click **Save**.
    5.  To change the sequence in which a return action is displayed to a user processing a return, drag the action to the preferred position in the list. The sequence numbers are automatically updated.
    6.  Click ![Previous page](../../../../images/resources/images/image430894.png).
6.  To add or modify a return inventory status rule:
    1.  Click **Inventory Status Rules**. The Inventory Status Rules page is displayed.
    2.  Perform one of the following tasks:
        -   To add a return status rule, click **Add**.
        -   To modify a return status rule, in the grid, click the description.
        -   To copy a return status rule, in the grid, select the check box of the rule, and then click **Copy**.
    3.  Enter information in the following fields:
        
        | Field | Description |
        | --- | --- |
        | Description | Text that describes the return inventory status rule. |
        | Status | Inventory status that is assigned to the return inventory that matches the criteria for the rule. |
        
    4.  To add rule criteria:
        1.  Under **CRITERIA**, click **Add**.
        2.  From the **Attribute** drop down, select the attribute to define, and then enter an attribute value. The application assigns the inventory status to return inventory that matches the defined attribute values.
        3.  Click **Save**.
    5.  Click **Save**.
    6.  To change the sequence in which a status is displayed to a user processing a return for inventory that matches the rule criteria, drag the status rule to the preferred position in the list. The sequence numbers are automatically updated.
    7.  Click ![Previous page](../../../../images/resources/images/image430894.png).
7.  Click **Save**.

## Returns fields

 
| Field | Description |
| --- | --- |
| Returns Arrival | If Yes, operators can use the RF Return Arrival screen to record the arrival of returned inventory so the LPN is tracked until the returns on the LPN are processed. When returned inventory arrives at the warehouse during receiving, the operator can scan or enter the LPN (which is required), and other optional attributes if necessary. The application then directs the operator to move the LPN to a returns location where each individual return can be processed by a workstation user. During this process, the operator enters the arrival LPN from which returns are being processed. When the LPN is empty, the operator can change the arrival LPN to process the next pallet of returns.<br > You can search and view return LPNs that have arrived but have not been completely processed in Return Arrival Display. Select Yes if you want to track the arrival and location of return inventory pallets until they are processed by a user at a returns workstation.<br > If No, LPNs of return inventory are not tracked and operators are not required to record the arrival of returned inventory. Instead, the returns are handled outside of the application until the individual returns on an LPN are processed at a returns location. |
| Allow Unexpected Returns | If Yes, users can create an unexpected return to process inventory when a return is not received from the host, or when there is no record of an original order from which the return can be created.<br > If No, users cannot process returns that are unexpected. |
| Allow Returns Using Original Order | If Yes, users can create a return from the original order, meaning that the return details, such as customer and item information, are populated from the original order line for the inventory being returned. Original orders are available until they are purged from the application.<br > If No, users cannot create returns from original orders. |
| Allow Unexpected Returned Items | If Yes, users that process returns can add unexpected items to a return. For example, assume a return exists and there are two items expected, but when the user opens the container, a third item is discovered that was not expected. If you select Yes, the user can add a new line to the return for the unexpected item, and it can be processed into the warehouse. Select Yes if your warehouse does not require a return authorization and you want to be able to process any items that are returned.<br > If No, users can only process returns for items that are expected. |
| 'Carrier' and 'Shipment Reference' Required | If Yes, then during returns processing, if the operator creates a return order based on the original outbound order used to ship the inventory to the customer, the operator is required to enter the carrier and shipment reference for the original order. The carrier is the name of the carrier that delivered the order to the customer. The shipment reference is the tracking number assigned to the order, such as the parcel tracking number or bill of lading.<br > If No, then the returns operator is not required to provide a carrier and shipment reference when creating a new return order based on an original order. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
