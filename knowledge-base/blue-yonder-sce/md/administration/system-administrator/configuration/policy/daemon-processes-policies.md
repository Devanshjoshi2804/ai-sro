---
title: "Daemon processes policies"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/policies/daemon_processes_policies.htm"
source: "/content/policies/daemon_processes_policies.htm"
toc_path:
  - "Administration"
  - "System Administrator"
  - "Configuration"
  - "Policy"
  - "Daemon processes policies"
sections:
  - "Daemon processes installed policy"
  - "Deferred Execution command policy"
  - "Deferred Execution exit on error policy"
  - "Deferred Execution initial timer policy"
  - "Deferred Execution installed policy"
  - "Deferred Execution timer policy"
images: []
source_sha1: c8ec75f30f8678c16f11f72fd475eb6359015188
---
# Daemon processes policies

The Daemon processes (SALDAEPRC) policies control whether daemon processes are allowed on the application server and how they operate (if allowed). Examples of daemon processes include tasks such as deferred executions, batch processing, and work operations. Each task is defined by the following policies:

-   Command
-   Exit on error
-   Initial timer
-   Installed
-   Execution timer

These policies are described using the Deferred Execution task as an example.

You use Policy Maintenance to maintain Daemon processes policies.

**IMPORTANT**: These policies are global and cannot be overridden by warehouse.

## Daemon processes installed policy

The Daemon processes installed (SALDAEPRC/INSTALLED/INSTALLED) policy determines whether daemon processing is allowed.

**IMPORTANT**: If you disable this policy, daemon processes cannot be run.

You can configure the following DETAILS field for this policy:

-   **Return Number 1**: Specifies whether the policy is enabled. A value of 1 is enabled, 0 is disabled. The policy is enabled by default.

## Deferred Execution command policy

The Deferred Execution command (SALDAEPRC/DEFERRED-EXECUTION/COMMAND) policy determines which command is used to define and execute the Deferred Execution daemon process.

You can configure the following DETAILS field for this policy:

-   **Return String 1**: Must be a valid MOCA server command as defined in Server Command Maintenance in the SCE client. The default value is execute deferred commands.
    
    **Note**: Do not change this value without first consulting with your Blue Yonder project team.
    

## Deferred Execution exit on error policy

The Deferred Execution exit on error (SALDAEPRC/DEFERRED-EXECUTION/EXIT-ON-ERROR) policy determines whether the Deferred Execution daemon process stops operating whenever an error occurs.

You can configure the following DETAILS field for this policy:

-   **Return Number 1**: Specifies whether the daemon process stops operating whenever an error occurs. A value of 1 is enabled, 0 is disabled. When the policy is set to 0, the daemon process operates regardless of errors. The policy is disabled by default.

## Deferred Execution initial timer policy

The Deferred Execution initial timer (SALDAEPRC/DEFERRED-EXECUTION/INITIAL-TIMER-IN-SECONDS) policy determines how long after the application has started that the Deferred Execution daemon process executes for the first time.

You can configure the following DETAILS field for this policy:

-   **Return Number 1**: Integer representing the number of seconds after the application has started that the daemon process executes for the first time. The default value is 0.

Use this policy to manage application resources by limiting the number of daemon processes executing at the same time.

## Deferred Execution installed policy

The Deferred Execution installed (SALDAEPRC/DEFERRED-EXECUTION/INSTALLED) policy determines whether the application allows the Deferred Execution daemon process.

You can configure the following DETAILS field for this policy:

-   **Return Number 1**: Specifies whether the Deferred Execution daemon process is enabled. A value of 1 is enabled, 0 is disabled. This policy is enabled by default.

## Deferred Execution timer policy

The Deferred Execution timer (SALDAEPRC/DEFERRED-EXECUTION/TIMER-LENGTH-IN-SECONDS) policy determines how long the Deferred Execution daemon process is inactive between operations.

You can configure the following DETAILS field for this policy:

-   **Return Number 1**: Integer representing the number of seconds between the time the daemon process completes and when it starts again. The default value is 60.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
