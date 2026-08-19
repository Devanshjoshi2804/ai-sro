---
title: "Counting"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/counting.htm"
source: "/content/counting.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inventory"
  - "Counting"
sections:
  - "Count by LPN"
images: []
source_sha1: b3c834b6b960b1e25611d3595c162b1b24b1e11a
---
# Counting

To configure the application for counting operations, perform the following tasks:

1.  **Set up count types**.
    
    A count type is a configuration that determines how a count is processed; for example, whether it is a detail or summary count, or generates an audit count if a discrepancy occurs. The application provides the standard count types that you can use or modify. New count types are not typically added. If you require new count types, consult with your Blue Yonder project team. See [Count Types](counting/count-types.md).
    
2.  **Set up count zones**.
    
    A count zone is a method of grouping locations for an inventory count. You can create one count zone that includes all the locations that you want to be counted. Alternatively, you may want to group locations into a count zone based on the type of counts that take place (RF or paper-based) and how counts are generated (manually or automatically). Every location that needs to be counted must belong to a count zone. See [Count Zones](counting/count-zones.md).
    
3.  **Configure count settings**.
    
    You use count settings to define the general settings that apply to all count types, ABC counts based on count period and ABC count frequency on an item or location, audit counts, manual counts, count near zero counts, and count back counts. You also define the actions available to a user for sending count results and inventory adjustments related to a count to the host (for paper-based counts and audits). See [Count Settings](counting/count-settings.md).
    
4.  **Configure count release rules**.
    
    A count release rule determines the action that takes place when the application generates a count. The rule can be configured, for example, to release directed work to the work queue (for counters using an RF device) or to produce a printed count sheet; both of which direct the counter to count the inventory in a location. See [Count Release Rules](counting/count-release-rules.md).
    
5.  **Configure voice counting**.
    
    If your facility uses a voice recognition application to perform inventory counting, select the work operation and type of work (directed or undirected) that can be performed using a voice device for each region in your warehouse. See [Voice Counting](counting/voice-counting.md).
    

## Count by LPN

Count by LPN is a cycle counting option that allows the counter to scan the LPNs in a location to perform the count, without entering any other information such as item and quantity. This configuration is useful for locations in which only an LPN is required to confirm a count.

The LPN that can be scanned is determined by level at which LPNs in the location are tracked:

-   For detail level tracking, the detail LPN must be scanned to record the detail as counted
-   For sub-LPN level tracking, the detail or case LPN must be scanned to record the entire case as counted
-   For LPN level tracking, the detail, case, or pallet LPN must be scanned to record the entire pallet as counted

The count by LPN can result in a discrepancy for any of the following reasons:

-   The application does not recognize the LPN (LPN has not been identified into the application)
-   The LPN is in the wrong location
-   One or more expected LPNs were not scanned

When you configure count by LPN, you define the following attributes:

-   Count zones in which count by LPN can be performed. To each count zone that supports count by LPN, you must assign the LPN level at which count by LPN can be performed.
-   Count types that are used to perform count by LPN. To each count type that supports count by LPN, you must assigned the LPN Cycle Count work operation.
    
    See [Configure count settings](counting/count-settings.md).
    

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
