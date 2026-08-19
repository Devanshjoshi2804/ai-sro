---
title: "Billing"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/billing.htm"
source: "/content/billing.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Integration"
  - "Billing"
sections:
  - "Configure billing activities"
images: []
source_sha1: d884ece500f9a1e21a96ec1a1e5b3013ab6af78a
---
# Billing

You use the Billing integration page to configure External Billing activities. External Billing is a logistics billing solution used by 3PL providers to record and charge for logistics activities in the warehouse. When integration is enabled and configured, Warehouse Management generates billing transactions for client-related activity and storage events. The billing application uses the transaction data to calculate costs and generate client invoices.

The Billing page is only available if the **External Billing System** field is set to Yes in the General Integration configurations. After you set the **External Billing System** field to Yes, you must exit the application and log in again to be able to access the Billing page. See [Configure general integration](general-integration.md).

## Configure billing activities

1.  Select **Configuration > Integration > Billing**.
    
    **Note**: The Billing page is only available if the **External Billing System** field is set to Yes in the General Integration configurations. After you set the **External Billing System** field to Yes, you must exit the application and log in again to be able to access the Billing page.
    
2.  Perform one of the following tasks:
    -   To add a client configuration, click **Add**.
    -   To modify a client configuration, in the grid, click the client.
3.  Enter information in the following fields:
    
     
    | Field | Description |
    | --- | --- |
    | Client | Name of the client for whom you want to configure data capture for storage and activities. |
    | Storage | If Yes, then in locations enabled for billing, the client's inventory is tracked and reported to the billing application.<br > If No, the client's inventory is not tracked for billing purposes. |
    | Activity | If Yes, the selected activities are tracked and reported to the billing application.<br > If No, activities are not tracked for the client. If you select Yes, then you must also select the activities to track for the client. |
    
4.  To select the activities to track for the client:
    1.  Click **Billing Activities**.
    2.  In the **Available** column, select the check box next to the activities to track.
    3.  Click **Apply**.
5.  Click **Save**.
    
    **Note**: When an external billing system is integrated with Warehouse Management, you can specify which locations to include in billing storage transactions. You do this for each location by setting its **Billing** field to Yes. See [Location configuration process](../warehouse/locations.md).
    

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
