---
title: "Replenishment of mixed-item cases"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/replenishment_of_mixed-item_cases.htm"
source: "/content/replenishment_of_mixed-item_cases.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inventory"
  - "Replenishments"
  - "Replenishment of mixed-item cases"
sections:
  - "Setup"
images: []
source_sha1: ddb585fe67114c2b829e0542545968582ad27b31
---
# Replenishment of mixed-item cases

When the application allocates detail level (each) inventory for a replenishment from a mixed-item case, you can determine which of the following methods is used:

-   The application allocates only the detail LPNs from the mixed-item case, meaning that the operator picks only the detail quantity that is needed from the sub-LPN.
-   The application allocates the full mixed-item case, which is then moved to a location where the detail LPNs for replenishment are removed from the sub-LPN.

If the application is configured to allocate full mixed-item cases for replenishments, the composition of the inventory in single-item and mixed-item cases is considered when locations are being sorted for replenishment allocation. Locations with single-item cases are used for allocation first, and then the application considers the locations with mixed-item cases, if necessary.

**Note**: When the application sorts locations to allocate single-item cases over mixed-item cases, this sorting is only valid for replenishment allocation and can override other sorting configurations in place. For example, the application does not respect the defined rotation method, such as FIFO, for detail-level replenishments of date-tracked inventory.

If the application is configured to allocate full mixed-item cases and to group replenishment picks together in a work assignment, specific sub-LPNs are assigned to the replenishment picks on the work assignment at the time the picks are performed. The application prompts the picking operator with the specific sub-LPN to pick. The application tracks the inventory for each completed pick on the replenishment work assignment and applies picked quantities across the assignment, if necessary. For example, if a single pick of a mixed-item case satisfies two replenishment picks on the work assignment, both picks are updated and considered complete.

## Setup

You must complete the following setup tasks for the application to allocate full mixed-item cases for detail-level replenishments:

1.  Configure the replenishment search path to consider sub-LPN replenishments before considering detail LPN replenishments. To do this, define a search path that contains a search path rule for sub-LPNs at a higher priority that the search path rule for detail LPNs. See [Replenishment Search Paths](replenishment-search-paths.md).
2.  Configure a replenishment work assignment rule to group replenishment picks by pick zone or source location. See Work assignments overview.
3.  Configure the following attributes for the replenishment pick method:
    
    -   Configure the replenishment pick method to allow work assignment picking.
    -   Set the **Allow Mixed Case** field to Yes. This indicates that full mixed-item cases can be allocated for detail-level replenishments.
    -   Indicate whether the application should prompt the operator with the specific sub-LPN to pick for a replenishment.
        
    
    See [Pick Methods](pick-methods.md).
    

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
