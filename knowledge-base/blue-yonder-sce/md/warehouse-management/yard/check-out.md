---
title: "Check Out "
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/check_out_.htm"
source: "/content/check_out_.htm"
toc_path:
  - "Warehouse Management"
  - "Yard"
  - "Check Out "
sections:
  - "Check out transport equipment"
  - "Check Out fields"
images: []
source_sha1: 1356f18a2dd515c9f8f51614aa84d906ac8d1257
---
# Check Out

You use the Check Out page to check out transport equipment (and the assigned tractor, if applicable) that has already been closed. When equipment is checked out, it is no longer tracked by the application, and if there is inventory on the equipment, it is no longer considered four-wall inventory. Transport equipment must be in a Closed status in order to be checked out. If you attempt to check out equipment that is not closed but meets the criteria to be closed, the application automatically closes the equipment prior to check out.

When you first access the Check Out page, you must enter criteria related to the equipment (for example, a transport equipment number, load, or location), or you can scan paperwork associated with the equipment.

## Check out transport equipment

You can also perform this procedure on [shipping or storage equipment](../shared-functions/staging/procedures-for-staging.md) and [receiving equipment](../shared-functions/staging/procedures-for-staging.md) on other application pages. If you check out transport equipment with an assigned tractor, the tractor is also checked out and its status is updated to Dispatched.

**Note**: If the **Tractor** field in the outbound loading configuration is set to Yes, then you must first have a tractor assigned to the transport equipment before the equipment can be checked out. See [Associate a tractor with transport equipment](../shared-functions/transport-equipment/procedures-for-transport-equipment.md).

1.  Select **Yard > Check Out**.
2.  Enter criteria associated to the transport equipment to check out.
3.  In the grid, select the row of the transport equipment.
4.  Enter information in the [Check Out fields](#Check_Out_fields).
5.  If a bill of lading (BOL) exists, then to print BOL paperwork, click **Print BOL**.
6.  Click **Check Out Equipment**. A confirmation message is displayed.
7.  Click **OK**.

## Check Out fields

 
| Field | Description |
| --- | --- |
| Tractor Reference | Optional internal alphanumeric reference number assigned to tractor when it is checked in to the facility. |
| Equipment Seals | Identifying number that is displayed on the seal or tag used to close and check out shipping transport equipment. These fields are not editable. |
| Tractor | Number of the tractor that is pulling the transport equipment. |
| Tractor Carrier | Identifier for a carrier that delivers inbound inventory to the warehouse or outbound shipments to a customer. In the application, a carrier can be associated with a customer, order, inbound shipment, outbound shipment, load, and service levels (such as Ground, Next Day, and Saturday Delivery). |
| Driver | Name of the driver who delivered or picked up the transport equipment. |
| Driver License | Driver license number for the transport equipment driver. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
