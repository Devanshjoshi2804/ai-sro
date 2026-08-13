---
title: "Labels policies"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/policies/labels_policies.htm"
source: "/content/policies/labels_policies.htm"
toc_path:
  - "Administration"
  - "System Administrator"
  - "Configuration"
  - "Policy"
  - "Labels policies"
sections:
  - "Paths configuration output path policy"
  - "Paths configuration search path policy"
images: []
source_sha1: 6e9bceafec7d10dfc3091e1f6727eb70c21e436d
---
# Labels policies

The Labels policies control label printing for your application.

You use Policy Maintenance to maintain Labels policies.

**IMPORTANT**: These policies are global and cannot be overridden by warehouse.

## Paths configuration output path policy

The Paths configuration output path (SYSTEM-INFORMATION/REPORTS/LABELS-PATH) policy determines the location of the label output files.

You can configure the following DETAILS fields for this policy:

-   **Return String 1**: Fully qualified path location for the label output files. The default value is **$LESDIR\\labels**.
-   **Sort Sequence**: Order in which the application processes policy details in relation to other details defined for the same policy.

## Paths configuration search path policy

The Paths configuration search path (SYSTEM-INFORMATION/REPORTS/REPORTS-PATH) policy determines the fully qualified search path for the printer object files from which label files are generated.

You can configure the following DETAILS fields for this policy:

-   **Return String 1**: Fully qualified path location for the printer object files from which label files will be generated. The default value is **$LESDIR\\reports**.
-   **Sort Sequence**: Order in which the application processes policy details in relation to other details defined for the same policy.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
