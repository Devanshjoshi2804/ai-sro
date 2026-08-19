---
title: "Trace view options policies"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/policies/trace_view_options_policies.htm"
source: "/content/policies/trace_view_options_policies.htm"
toc_path:
  - "Administration"
  - "System Administrator"
  - "Configuration"
  - "Policy"
  - "Trace view options policies"
sections:
  - "Accepted statuses policy"
  - "Auto expand tree policy"
  - "Flag time policy"
images: []
source_sha1: 57a9246e9a7fdac2db93bb2373e5da53897de16c
---
# Trace view options policies

The Trace view options (TRACE-VIEW-OPTIONS) policies control the appearance and operation of the Trace Analyzer in the SCE client. Trace Analyzer is used to organize and summarize the large amount of information contained in trace files for easy analysis.

You use Policy Maintenance or Policy Maintenance - Override to maintain Trace View Options policies.

## Accepted statuses policy

The Accepted statuses (TRACE-VIEW-OPTIONS/LES/ACCEPTED-STATUSES) policy indicates error message values that are not displayed in red text in the tree structure. Error message values are displayed in red text that is not listed in the policy details will be displayed in red text.

You can configure the following DETAILS field for this policy:

-   **Return Number 1**: Error status value, such as -1403.

## Auto expand tree policy

The Auto expand tree (TRACE-VIEW-OPTIONS/LES/AUTO-EXPAND-TREE) policy configures whether the Command Profiler tree structure is expanded when the Command Profiler is loaded.

You can configure the following DETAILS field for this policy:

-   **Return Number 1**: Determines the display of the tree structure. The following values are valid:
    -   **0**: Tree is not expanded when the tree loaded.
    -   **1**: Tree is expanded when the tree is loaded.

## Flag time policy

The Flag time (TRACE-VIEW-OPTIONS/LES/FLAG-TIME) policy sets a time threshold within which a command must execute or else it is displayed in bold in the tree.

You can configure the following DETAILS field for this policy:

-   **Return Number 1**: Integer value in milliseconds, representing the minimum length of time a command must take to execute in order to be displayed in bold in the tree. Commands that take less time are not displayed in bold.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
