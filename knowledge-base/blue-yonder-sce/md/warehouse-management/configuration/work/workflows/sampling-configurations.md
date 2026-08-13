---
title: "Sampling Configurations"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/sampling_configurations.htm"
source: "/content/sampling_configurations.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Work"
  - "Workflows"
  - "Sampling Configurations"
sections:
  - "Add or modify a sampling configuration"
images: []
source_sha1: 7208eb69c0e352e3c50ff08e379c081d9b0a46b4
---
# Sampling Configurations

A sampling configuration defines the rate at which a warehouse workflow is performed on inventory. The rate is a percentage (such as 10, 25, or 50 percent) of a quantity of LPNs. For example, if you define a sampling rate of 25% for the first 200 LPNs that are processed for an inbound shipment, then the application prompts the user to perform the workflow on a random selection of 50 LPNs out of the 200 that are processed.

You can configure multiple sampling rates for a single sampling configuration. For example, you can specify a rate of 100% for the first 5 LPNs, and a rate of 50% for the next 10 LPNs, and a rate of 25% for the remainder of the LPNs that are processed. The following table shows how the example would be configured.

 
| From (number of LPNs) | Rate (%) |
| --- | --- |
| 1 | 100% |
| 6 | 50% |
| 11 | 25% |

**Note**: If a sampling configuration with multiple sampling rates is assigned to an RF operator workflow, the application uses the rate with the highest percentage.

You create sampling configurations to define the rate at which warehouse workflows are performed on inventory that is being processed.

After sampling configurations are created, you can assign a sampling configuration to an inbound, outbound, or RF operator type of workflow.

## Add or modify a sampling configuration

1.  Select **Configuration > Work > Workflows > Sampling Configurations**.
2.  Perform one of the following tasks:
    -   To add a configuration, click **Add**.
    -   To modify a configuration, in the grid, click the name of the configuration.
    -   To copy a configuration, in the grid, select the check box next to the configuration, and click **Copy**.
3.  In the **Name** and **Description** fields, enter the values.
4.  Click **Sampling Rate Configuration**.
    
    **Note**: You can define multiple sampling rates for a single configuration. For example, for the first 50 LPNs you can define a rate of 50%; for the next 50 LPNs, you can define a different rate (such as 20%), and so on.
    
5.  To add or copy a sampling rate:
    1.  To add a sampling rate, click **Add**.
    2.  To copy a sampling rate, in the grid, select the check box next to the rate, and then click **Copy**.
    3.  Enter information in the following fields:
        
        | Field | Description |
        | --- | --- |
        | Number of LPNs | Number of LPNs to sample. |
        | From | Number of the LPN at which the sampling rate takes effect. For example, to start the sampling rate with the first LPN, enter 1; to start with the 20th LPN, enter 20; and so on. |
        | Rate | Percentage of the LPNs to which the workflow should be applied. For example, if you enter 20%, then the workflow is applied to 20% of the number of LPNs associated with the rate. |
        
    4.  Click **Save**.
6.  To modify a sampling rate:
    1.  In the grid, in the **From (No. of LPNs)** column, enter the number of the LPN at which to start the rate, and then press **Enter**.
        
        **Note**: You cannot change the value in To column. The application fills in the To value based on the number you enter in the From column in the next row.
        
    2.  In the **Sample** column, enter the percentage of the LPNs to which the workflow should be applied, and then press **Enter**.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
