---
title: "Archive system policies"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/policies/archive_system_policies.htm"
source: "/content/policies/archive_system_policies.htm"
toc_path:
  - "Administration"
  - "System Administrator"
  - "Configuration"
  - "Policy"
  - "Archive system policies"
sections:
  - "Archive system installed policy"
  - "Local archive policy"
  - "Remote host policy"
  - "Source name policy"
  - "Table prefix policy"
images: []
source_sha1: b6b227f5480a95ba3fad1745b25f73256385345c
---
# Archive system policies

The Archive system (ARCHIVE-SYSTEM) policies control whether the application data is archived, and if so, how the archived data is stored. Archived data can be stored on the local server or on an archival instance on a remote server.

**Note**: Cloud deployments using Snowflake cloud storage do not require a separate archive.

You use Policy Maintenance to maintain Archive system policies.

**IMPORTANT**: These policies are global and cannot be overridden by warehouse.

## Archive system installed policy

The Archive system installed (ARCHIVE-SYSTEM/INSTALLED/INSTALLED) policy determines whether this application allows the archiving and purging of data. Archiving refers to the replication of data from a production instance to an archival instance. Purging is the process of removing archived data from the production instance to keep production processing times at an optimal level.

You can configure the following DETAILS field for this policy:

-   **Return Number 1**: Specifies whether the policy is enabled. A value of 1 is enabled, 0 is disabled. The policy is disabled by default.

## Local archive policy

The Local archive (ARCHIVE-SYSTEM/MISCELLANEOUS/LOCAL-ARCHIVE) policy determines how archived data is stored.

You can configure the following DETAILS field for this policy:

-   **Return Number 1**: Specifies the method used to store archived data. The following values are valid:
    -   **0**: Indicates remote archive. The archived data is stored on a remote server. The remote server is specified using the REMOTE-HOST policy value. This option is valid for both on-premises and cloud deployments and is the default value.
        
    -   **1**: Indicates local archive. The archived data is stored within the instance. This option is valid for both on-premises and cloud deployments.
        
    -   **2**: Indicates DAAS archive. There is no separately archived data as warehouse data is continuously synched with cloud storage (powered by Snowflake), eliminating the need for a separate archive. This option is valid only for cloud deployments configured to use Data Access Service and enhanced cloud storage. Data will continue to be purged from production using the archiving and purging and purging only jobs.
        

## Remote host policy

The Remote host (ARCHIVE-SYSTEM/MISCELLANEOUS/REMOTE-HOST) policy specifies the service URL of the remote instance to which the archived data is stored. This policy is functional only when the Archive system installed policy is enabled, and the Archive to local system policy is disabled.

You can configure the following DETAILS field for this policy:

-   **Return String 1**: Service URL for the remote instance to which the archived data is stored. Use the following format for the service URL: http://<Host Name>:<Port>/service

## Source name policy

The Source name (ARCHIVE-SYSTEM/MISCELLANEOUS/SOURCE-NAME) policy determines the name of the instance used as the source from which the data is archived. This policy is functional only when the Archive system installed policy is enabled.

**Note**: This data source is typically your production (working) instance.

You can configure the following DETAILS field for this policy:

-   **Return String 1**: Name of the source instance from which the data is archived. The default value is MCHUGH.

## Table prefix policy

The Table prefix (ARCHIVE-SYSTEM/MISCELLANEOUS/TABLE-PREFIX) policy determines the prefix used to designate the table to which the archived data is stored. This policy is functional only when the Archive system installed policy is enabled.

You can configure the following DETAILS field for this policy:

-   **Return String 1**: Prefix applied to the table to which the archived data is stored. The default value is arc\_.
    
    **Note**: Archiving only takes place between two database tables, either on the same database or on different ones. For example, you might want to archive your ORD table entries to a table called arc\_ORD. The prefix would be configured as arc\_.
    

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
