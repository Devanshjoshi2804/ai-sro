---
title: "Labor Dashboard"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/labor_dashboard.htm"
source: "/content/labor_dashboard.htm"
toc_path:
  - "Warehouse Labor Management"
  - "Labor"
  - "Labor Dashboard"
sections:
  - "Setup when integrating with Warehouse Management"
images:
  - "/content/resources/images/image1182503.png"
  - "/content/resources/images/image1182504.png"
  - "/content/resources/images/labor_pending_small.png"
  - "/content/resources/images/laborobvs_in_process.png"
  - "/content/resources/images/laborobvs_observed.png"
source_sha1: de40dbee94e350ee5027aea8ddfd74eb659ddc2e
---
# Labor Dashboard

You use the Labor Dashboard to monitor labor productivity and performance statistics. The dashboard includes widgets you can use to view this information and also has a quick view for each widget at the top of the page. To display the quick view, click ![Toggle (Expand)](../../../images/resources/images/image1182503.png). To hide the quick view, click ![Toggle (Collapse)](../../../images/resources/images/image1182504.png).

The Labor Dashboard widgets display the following information:

-   **Productivity**: You can monitor labor productivity and workload progression statistics. When you access the dashboard, the Productivity quick view displays the overall performance (or variance) and associated trend icon for all active assignments. See [Labor Productivity widget](labor-dashboard/labor-productivity-widget.md).
-   **Performance**: You can monitor user performance statistical information at the summary and detail levels. The performance quick view displays the number of users that are performing above, at, or below expectation. See [Labor Performance widget](labor-dashboard/labor-performance-widget.md).
-   **Observations**: You can create, perform, and complete user observations. The Observations quick view displays the number of observations that are pending ![Pending: Due Today / Past Due](../../../images/resources/images/labor_pending_small.png), in process ![In Process](../../../images/resources/images/laborobvs_in_process.png), and complete ![Observed](../../../images/resources/images/laborobvs_observed.png). See [Labor Observations widget](labor-dashboard/labor-observations-widget.md).
-   **Approvals**: You can view and manage unmeasured time approval requests using the Labor Approvals widget. See [Labor Approvals widget](labor-dashboard/labor-approvals-widget.md).

## Setup when integrating with Warehouse Management

The Labor Dashboard is available in standalone instances of Warehouse Labor Management without any additional setup. However, when integrating Warehouse Labor Management with Warehouse Management, you must complete the following tasks for the application to display information on the Labor Dashboard.

1.  Ensure that Warehouse Management is integrated with Warehouse Labor Management in a single instance. Also, ensure that the portal server installation that supports the combined instance includes both Warehouse Management and Warehouse Labor Management. See the Warehouse Labor Management Installation Guide.
2.  In Warehouse Management, configure Warehouse Labor Management attributes. See [Configure Warehouse Labor Management integration](../../warehouse-management/configuration/integration/warehouse-labor-management.md).
    -   Enable Warehouse Labor Management functionality in Warehouse Management.
    -   Set the **Labor Goal Time** field in Warehouse Management to Yes.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
