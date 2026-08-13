---
title: "Post pick workflow every pick policy"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/policies/post_pick_workflow_every_pick_policy.htm"
source: "/content/policies/post_pick_workflow_every_pick_policy.htm"
toc_path:
  - "Administration"
  - "System Administrator"
  - "Configuration"
  - "Policy"
  - "Post pick workflow every pick policy"
sections: []
images: []
source_sha1: b51defbe71abeee3033d8f74afa265ed1bac07e4
---
# Post pick workflow every pick policy

The Post-pick workflow every pick (LIST-PICKING/MISCELLANEOUS/POSTPICK-WORKFLOW-EVERY-PICK) policy determines whether the Post-Pick outbound workflow exit point occurs once for an entire work assignment or for each pick in a work assignment. If the policy is enabled, then the exit point occurs after every completed pick in a work assignment, meaning that outbound workflows configured for the Post-Pick exit point are triggered after each work assignment pick. If disabled, then the exit point occurs only once per work assignment, even if there are multiple picks.

**Notes**:

-   Only the first inventory move for a unique work reference triggers the exit point. For example, assume there is a pick for 10 cases in a location. If an operator completes the pick in partial quantities, such as two moves of 5 cases, then the exit point only occurs on the first move.
    
-   The post-pick exit point does not apply to replenishment picks, work order picks, and cartonized picks.
    

You use Policy Maintenance to maintain the Post-pick workflow every pick policy.

You can configure the following DETAILS field for this policy:

-   **Return Number 1**: Specifies whether the policy is enabled. A value of 1 is enabled, 0 is disabled. The policy is disabled by default.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
