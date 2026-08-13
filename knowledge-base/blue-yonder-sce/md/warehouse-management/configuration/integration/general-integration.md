---
title: "General Integration"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/general_integration.htm"
source: "/content/general_integration.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Integration"
  - "General Integration"
sections:
  - "Configure general integration"
images: []
source_sha1: d89cfdddab9f6acf0217dd016be29cccf435308f
---
# General Integration

You use the General settings to enable integration with the following supporting products and functions:

-   **Parcel**: Parcel Handler is an application that provides the interface between Warehouse Management and Integrator for the purpose of supporting communications between Warehouse Management and a third-party parcel application.
    
    Set **Parcel** to Yes if Warehouse Management is integrated with a parcel application through Parcel Handler. In addition, perform the parcel setup tasks. See [Parcel](../outbound/shipping/parcel.md).
    
-   **Slotting**: Slotting enables you to create effective product storage strategies (slotting plans) that minimize travel distances, thereby optimizing material handling and space efficiency. In addition, Slotting enables you to easily modify existing slotting plans and reslot locations to keep your physical layout and product placement strategies current with changing business demands. With Slotting, Warehouse Management can be configured to automatically reslot a pick line based on the waving or allocation of an order set. The inventory shortages for the wave or allocation drives the automatic reslot of the pick line. Slotting must be installed and enabled in Warehouse Management. See the Supply Chain Execution Help.
-   **3PL**: Third-party logistics support is the ability to service multiple clients in a single facility. A common business scenario in the 3PL environment is to offer warehouse services to multiple clients in one warehouse. The 3PL handles incoming receipts, stores product, tracks inventory, and fulfills outgoing orders for its clients. The third-party logistic functionality must be installed during installation of the Warehouse Management. See [Clients](../partners/clients.md).
-   **External Billing System**: External Billing is a logistics billing solution used by 3PL providers to record and charge for logistics activities in the warehouse. When integration is enabled and configured, Warehouse Management generates billing transactions for client-related activity and storage events. The billing application uses the transaction data to calculate costs and generate client invoices.
-   **Full Validation Of Inbound Transactions**: Full validation is performed on certain inbound Integrator transactions to identify and log all errors in a single execution. When full validation is enabled, if the application processes a transaction with one or more errors, it records each error until the entire transaction is validated. If there are multiple errors, you can view and troubleshoot all of them at once before processing the transaction again.<br > See [Integration Errors](../../../administration/system-administrator/integration-errors.md).<br>
    
    **Notes**:
    
    -   Full validation is only performed on certain inbound transactions that impact the ability to ship and receive inventory.
    -   Full validation can eliminate the need to process a transaction multiple times if there are multiple errors since all of the errors can be immediately identified. However, full validation may increase processing time.
    -   The **Full Validation Of Inbound Transactions** field value set at the client level overrides the field value set at the warehouse level.
    -   Custom validations are possible. Contact your Blue Yonder project team for information on custom validations.
    

## Configure general integration

1.  Select **Configuration > Integration > General Integration**.
2.  To integrate with a parcel application through Parcel Handler, set the **Parcel** field to **Yes**.
    
    **Note**: To configure parcel, see [Parcel](../outbound/shipping/parcel.md).
    
3.  To enable installed Slotting functionality, set the **Slotting** field to **Yes**.
4.  To enable installed third-party logistics (3PL) functionality, set the **3PL** field to **Yes**.
5.  To integrate with an external billing system, set the **External Billing System** field to **Yes**.
    
    **Note**: The **External Billing System** field is only available if 3PL is set to **Yes**. To configure clients for activity and storage tracking, see [Configure billing activities](billing.md). Also, when an external billing system is integrated with Warehouse Management, you can specify which locations to include in billing storage transactions. You do this for each location by setting its **Billing** field to **Yes**. See [Locations](../warehouse/locations.md).
    
6.  To enable the application to fully validate certain inbound transaction in their entirety, regardless of whether the transactions include multiple errors, set the **Full Validation Of Inbound Transactions** field to **Yes**.
    
    **Note**: Full validation can eliminate the need to process a transaction multiple times if there are multiple errors since all of the errors can be immediately identified. However, full validation may increase processing time. See [Integration Errors](../../../administration/system-administrator/integration-errors.md) and [General Integration](#General_Integration).
    
    If this field is set to No, then when an error is encountered during inbound transaction processing, the application stops validating the transaction. When full validation is disabled, a transaction may need to be processed multiple times if there are multiple errors.
    
7.  Click **Save**.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
