---
title: "System Audit Record"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/admin/system_audit_record.htm"
source: "/content/admin/system_audit_record.htm"
toc_path:
  - "Administration"
  - "System Administrator"
  - "Configuration"
  - "System"
  - "System Audit Record"
sections:
  - "View system audit records"
  - "System Audit Record fields"
images: []
source_sha1: 49f99af64d1e290dc66438a3ba47f95b9c220fbe
---
# System Audit Record

The System Audit Record page displays system audit records for security-related activities that are being tracked, such as log in and out attempts (success and failure), intruder alerts, the expiration of a user's account, and the changing of a user's password.

## View system audit records

1.  Select **System Administrator > Configuration > ** **System > System Audit Record**.
2.  View the information in the [System Audit Record fields](#System_Audit_Record_fields).

## System Audit Record fields

 
| Field | Description |
| --- | --- |
| Application ID | Unique application identifier for the client component that performed the operation being audited. |
| Audit Type | Type of audit record.<br>-   • **I**: An interactive operation, such as a user changing a password.
<br>-   • **A**: User authentication, such as a login attempt. |
| Audit Date | Date and time that the operation was performed. |
| Execute Command | Description of the operation or command that was performed or executed and the resulting status. |
| Rows Affected | Number of database rows affected by the operation or returned to the client. |
| Return Status | Return status of the operation. |
| TCP Address | TCP address of the client from which the operation was performed. In this case, the client is defined as either the SCE client or the server instance to which the web client is connected. |
| User ID | Unique identifier for the individual who performed the operation. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
