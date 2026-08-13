---
title: "Pick Labels"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/pick_labels.htm"
source: "/content/pick_labels.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Outbound"
  - "Picking "
  - "Pick Labels"
sections:
  - "Configure pick labels"
  - "Pick Labels fields"
images: []
source_sha1: 4bebcff2609ac2960fcb38476fc8d02579010024
---
# Pick Labels

A pick label is used to facilitate picking by providing a work reference number for users to scan, and can also include a shipping label to be applied to inventory as it is picked.

When you configure the label settings, you specify the printer at which labels are printed, when labels are printed, and whether a label is required for undirected picks. An undirected pick is a pick that the operator selects to perform from the RF Picking menu; a directed pick is a pick that the operator accepts (acknowledges) through RF Directed Work.

## Configure pick labels

1.  Select **Configuration > Outbound > Picking > Pick Labels**.
2.  Enter information in the [Pick Labels fields](#Pick_Labels_fields).
3.  Click **Save**.

## Pick Labels fields

 
| Field | Description |
| --- | --- |
| Print at Release | If Yes, the application prints labels automatically when picks are released, based on the configurations that you defined.<br > If No, labels are not printed automatically at pick release. |
| Label Printer | Name of the default printer that is used to print labels for pick release. The device must be associated with a valid label printer address that has also been defined in the application. |
| Unconfirmed Picks | Maximum number of labels for unconfirmed picks that should existing at any given time. An unconfirmed pick is a pick that has been released but not completed. When this number is reached, the application does not release additional labels until picks are confirmed and the outstanding count drops below the limit. This value can be used to prevent the pick release process from releasing too many labels when a large number of picks have been released but are not yet confirmed (completed). |
| Minimum to Release | Value that represents the minimum number of labels that must accumulate before the picks will be released. For example, if this value is set to 50, picks will not be released until 50 picks are pending release. This is typically used to create larger, more efficient pick batches. If the amount of time the labels have been waiting for release exceeds the value specified for the **Minimum Timing** field, then the labels are released. |
| Minimum Timing | Amount of time (in seconds) that the application waits to accumulate the number of picks specified in the **Minimum to Release** field, before it releases the picks and prints the labels. The pick release process keeps track of time while it is attempting to build a batch of picks to release together. When the amount of time reaches the number of seconds defined here, then the picks are released even if the quantity in the batch is less then the minimum number of labels specified in the **Minimum to Release** field. |
| Label Required | If Yes, then the application prints a label automatically after the RF operator completes an undirected pick. An undirected pick is a pick that the operator selects to perform from the RF Picking menu; a directed pick is a pick that the operator accepts (acknowledges) through RF Directed Work. If the RF operator picks inventory onto more than one LPN and then presses Done, the RF Label LPN screen is displayed asking the operator to scan the last LPN picked and the rest of the LPNs. The application prints a label for each LPN that is scanned. This does not apply to LPNs created using RF Carton Picking or RF Case Confirm.<br > If No, the application does not print a label for an undirected pick. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
