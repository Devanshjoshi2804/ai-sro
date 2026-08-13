---
title: "Named thread pool policies"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/policies/named_thread_pool_policies.htm"
source: "/content/policies/named_thread_pool_policies.htm"
toc_path:
  - "Administration"
  - "System Administrator"
  - "Configuration"
  - "Policy"
  - "Named thread pool policies"
sections:
  - "Allocate Wave named thread pool policies"
  - "Daily Transaction Writer named thread pool policies"
  - "Order Activity Writer named thread pool policies"
  - "Work Manager named thread pool policies"
images: []
source_sha1: 448e2a8e6b3d7c9e2564d7ed5704218ab95fd2b2
---
# Named thread pool policies

Named thread pool policies are used to execute discrete pieces of work in multiple threads to support application-level use cases, such as the following examples:

-   Work that needs to be performed in a separate thread because it requires a separate transaction
-   Work that needs to be performed in parallel synchronously to improve performance, such as distributing work to multiple threads and then waiting until all threads are completed before proceeding
-   Work that needs to be performed in parallel asynchronously to improve performance, such as executing work in the background

Named thread pools are tracked by the Monitoring and Diagnostics (M&D) probe polling framework.

The following thread pool policy codes are provided in the application:

-   Allocate Wave
-   Daily Transaction Writer
-   Order Activity Writer
-   Work Manager

The following table lists the policy value descriptions used with the NAMED-THREADPOOL policy variables.

 
| Policy Value | Description |
| --- | --- |
| AUTOCOMMIT | Automatically commits or rolls back transactions on its context after thread execution is completed.<br > The **Return Number 1** value specifies whether the policy is enabled. A value of 1 is enabled, 0 is disabled. |
| BOOTSTRAP-MOCA-CONTEXT | Runs a process to configure a MOCA session and server context for any thread execution originated from its thread pool. It does not explicitly roll back or commit a transaction.<br > The **Return Number 1** value specifies whether the policy is enabled. A value of 1 is enabled, 0 is disabled. |
| ENABLED | Determines whether the policy uses named thread pools or the standard thread pool functionality (asynchronous executor).<br > The **Return Number 1** value specifies whether the policy is enabled. A value of 1 is enabled, 0 is disabled. If the policy is disabled, the standard thread pool functionality (asynchronous executor) is used. |
| PROBE-REPORTING-INTERVAL-IN-SECONDS | Time interval (in seconds) to report metrics from this thread pool as probe data to M&D. |
| SIZE | Integer representing the number of threads that can execute a task at one time. |

## Allocate Wave named thread pool policies

The Allocate Wave named thread pool (ALLOCATE-WAVE/NAMED-THREADPOOL) policies define how named thread pools are used to allocate inventory as part of the allocation process. These policies are enabled by default.

The following table lists the ALLOCATE-WAVE/NAMED-THREADPOOL policies and the default policy values.

 
| Policy | Return Number 1 |
| --- | --- |
| ALLOCATE-WAVE/NAMED-THREADPOOL/AUTOCOMMIT | 1 |
| ALLOCATE-WAVE/NAMED-THREADPOOL/BOOTSTRAP-MOCA-CONTEXT | 1 |
| ALLOCATE-WAVE/NAMED-THREADPOOL/ENABLED | 1<br > **Note**: If clustering is enabled and this functionality is disabled (ENABLED = 0), then allocation starts in cluster server mode. |
| ALLOCATE-WAVE/NAMED-THREADPOOL/PROBE-REPORTING-INTERVAL-IN-SECONDS | 300 |
| ALLOCATE-WAVE/NAMED-THREADPOOL/SIZE | 10<br > **Note**:  This policy value can be also be modified on the Post Allocation configuration page. For information on how to determine the optimum number of threads, see [Configure post allocation settings](../../../../warehouse-management/configuration/outbound/allocation/post-allocation.md). |

## Daily Transaction Writer named thread pool policies

The Daily Transaction Writer named thread pool (DLYTRN/NAMED-THREADPOOL) policies define how named thread pools are used to record daily transaction history that is displayed on the Inventory History page. These policies are disabled by default.

The following table lists the DLYTRN/NAMED-THREADPOOL policies and the default policy values.

 
| Policy | Return Number 1 |
| --- | --- |
| DLYTRN/NAMED-THREADPOOL/AUTOCOMMIT | 1 |
| DLYTRN/NAMED-THREADPOOL/BOOTSTRAP-MOCA-CONTEXT | 1 |
| DLYTRN/NAMED-THREADPOOL/ENABLED | 0 |
| DLYTRN/NAMED-THREADPOOL/PROBE-REPORTING-INTERVAL-IN-SECONDS | 300 |
| DLYTRN/NAMED-THREADPOOL/SIZE | 10 |

## Order Activity Writer named thread pool policies

The Order Activity Writer named thread pool (ORDACT/NAMED-THREADPOOL) policies define how named thread pools are used to record order activity that is displayed on the Order Activity page for a selected order. Order Activity Writer writes the order activity log if the parent transaction committed successfully. These policies are disabled by default.

The following table lists the ORDACT/NAMED-THREADPOOL policies and the default policy values.

 
| Policy | Return Number 1 |
| --- | --- |
| ORDACT/NAMED-THREADPOOL/AUTOCOMMIT | 1 |
| ORDACT/NAMED-THREADPOOL/BOOTSTRAP-MOCA-CONTEXT | 1 |
| ORDACT/NAMED-THREADPOOL/ENABLED | 0 |
| ORDACT/NAMED-THREADPOOL/PROBE-REPORTING-INTERVAL-IN-SECONDS | 300 |
| ORDACT/NAMED-THREADPOOL/SIZE | 10 |

## Work Manager named thread pool policies

The Work Manager named thread pool (UPDATE-WORK-QUEUE/NAMED-THREADPOOL) policies define how named thread pools are used to record work queue history that is displayed on the Work Queue page. These policies are disabled by default.

The following table lists the UPDATE-WORK-QUEUE/NAMED-THREADPOOL policies and the default policy values.

 
| Policy | Return Number 1 |
| --- | --- |
| UPDATE-WORK-QUEUE/NAMED-THREADPOOL/AUTOCOMMIT | 1 |
| UPDATE-WORK-QUEUE/NAMED-THREADPOOL/BOOTSTRAP-MOCA-CONTEXT | 1 |
| UPDATE-WORK-QUEUE/NAMED-THREADPOOL/ENABLED | 0 |
| UPDATE-WORK-QUEUE/NAMED-THREADPOOL/PROBE-REPORTING-INTERVAL-IN-SECONDS | 300 |
| UPDATE-WORK-QUEUE/NAMED-THREADPOOL/SIZE | 4 |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
