---
title: "Integration Errors"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/admin/integration_errors.htm"
source: "/content/admin/integration_errors.htm"
toc_path:
  - "Administration"
  - "System Administrator"
  - "Integration Errors"
sections:
  - "Reprocess an integration transaction"
  - "Integration Errors fields"
images:
  - "/content/resources/images/image569280.png"
source_sha1: 2ae826af7cae0224517e38e0af7c8326f0ba9312
---
# Integration Errors

You use the Integration Errors page to view the failed inbound transactions and to reprocess them when the transaction errors have been resolved. The integration transactions can be processed in one of the following ways:

-   Process and fully validate the transaction to display all the related errors of the transaction as one record, regardless of how many errors were logged. For example, assume the application receives a transaction with three errors. If full validation is enabled, the application processes the transaction and records all three errors in a single validation instead of stopping when the first error is encountered. You can enable full validation in the general integration configuration. See [General Integration](../../warehouse-management/configuration/integration/general-integration.md).
    
    **Note**: Full validation can eliminate the need to process a transaction multiple times if there are multiple errors since all of the errors can be immediately identified. However, full validation may increase processing time.
    
    **IMPORTANT**: Full validation is only performed on the following inbound transactions that impact the ability to ship and receive inventory:
    
    -   APPT\_INB\_IFD
    -   CANONICAL\_TRANSPORT\_LOAD
    -   CUST\_ADDR\_INB\_IFD
    -   HOLD\_ASSIGNMENT\_INB\_IFD
    -   HOLD\_DEF\_INB\_IFD
    -   ORDER
    -   ORDER\_INB\_IFD
    -   PART\_INB\_IFD
    -   PART\_LOT\_INB\_IFD
    -   PARTFOOT\_INB\_IFD
    -   PRTLOT\_INVSTS\_IFD
    -   RA\_INB\_IFD
    -   RCPT\_INB\_IFD
    -   SHIPORD\_INB\_IFD
    -   TRAFFIC\_PLAN\_INB\_IFD
    -   WO\_INB\_IFD
    
    For more information on inbound transactions, see Warehouse Management Integration Transactions Overview.
    

-   Process and validate the transaction to display the first error encountered. If a transaction includes multiple errors, then after the first error is resolved, reprocess the transaction to identify the second error so it can be resolved, and so on.

You can purge integration transaction error records according to a job schedule (PURGE-TRN-ERR-INFO), which is defined in the Blue Yonder Console, under Jobs.

**Note**: Custom validations are possible. Contact your Blue Yonder project team for information on custom validations.

## Reprocess an integration transaction

You can only view and reprocess the transaction errors associated with clients for which you are authorized. For example, if you are authorized for clients A and B, but not client C, you cannot see or reprocess the transaction errors for client C.

1.  Select **System Administrator > Integration Errors**.
2.  To view the transactions based on date or date range, use the calendar selection tool to select the time frame.
3.  View information in the [Integration Errors fields](#Integration_Errors_fields).
4.  To view the validation error messages associated with a transaction, expand the transaction.
5.  To reprocess transactions, select the check box next to one or more transactions.
6.  Perform one of the following tasks:
    -   To reprocess a transaction without the Integrator and MOCA trace logs, from the **Actions** drop-down list, select **Reprocess**.
    -   To reprocess a transaction with the Integrator and MOCA trace logs, from the **Actions** drop-down list, select **Reprocess with Trace**.
7.  Click **OK**.
8.  To view whether reprocessing was successful, click ![Refresh](../../../images/resources/images/image569280.png) to refresh the page. If the transaction is no longer displayed, reprocessing was successful.

**Note**: If the **Full Validation Of Inbound Transactions** is set to **No**, meaning that the application stops validation after encountering the first error, then reprocessing may have been successful for the original error. The transaction may be displayed again because there are multiple errors in the transaction that must be resolved one at a time. See [General Integration](../../warehouse-management/configuration/integration/general-integration.md).

## Integration Errors fields

 
| Field | Description |
| --- | --- |
| Download | Unique application-generated identifier for the initial download process of an inbound transaction. The download identifier remains constant when you reprocess the transaction in error. |
| Transaction | Application-generated number for the failed inbound transaction. When a transaction fails, the transaction number is incremented by 1 from the last transaction number that was logged.<br > For example, assume that you reprocess a failed transaction with a transaction number of 10 (the previous failed transaction number was 9). If the most recent failed transaction is 14, then when you reprocess the transaction (and if it fails again), the transaction number is 15. |
| Transaction Name | Name of the inbound transaction. The inbound root tag in the IFD is displayed as the transaction name. For example, ORDER\_INB\_IFD. |
| Transaction Version | Version of the inbound transaction. |
| Date-Time | Date and time when the transaction failed. |
| Message | Information about the error. Each transaction can have multiple errors, and each error message provides details of why the transaction failed. For example, "Invalid Inbound Load - TRKNUM-30005." |
| Client | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. |
| Segment | Interface File Definition (IFD) segment of the inbound transaction in which the error was encountered. An IFD is the method in which integration transactions are sent, and a segment of an inbound IFD represents a portion of the entire data set for the IFD. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
