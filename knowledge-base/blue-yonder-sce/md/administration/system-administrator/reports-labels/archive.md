---
title: "Archive"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/admin/archive.htm"
source: "/content/admin/archive.htm"
toc_path:
  - "Administration"
  - "System Administrator"
  - "Reports/labels"
  - "Archive"
sections:
  - "Print an archived report"
  - "Preview an archived report"
  - "Print fields"
images:
  - "/content/resources/images/image1139573_16x20.png"
  - "/content/resources/images/image1139575_17x20.png"
  - "/content/resources/images/image1139616_19x20.png"
  - "/content/resources/images/image1139577_19x20.png"
  - "/content/resources/images/image1139618_19x20.png"
  - "/content/resources/images/image1139581_21x20.png"
  - "/content/resources/images/image1139583_22x20.png"
source_sha1: b0bc1fdd0a51187673249bbab094d4ba0c0ad6a3
---
# Archive

A generated report is archived if a value is specified in the Days to Keep field for the report. The report expires after being stored for the specified number of days.

**Note**: The Purge Reports job, configured in the Console, purges expired reports on a regularly scheduled basis. See the Supply Chain Execution Applications Console User Guide.

When you work with report archives, you can perform the following tasks:

-   View the archive details of a report, such as its file name, user who generated the report, the date and time that the report was generated, and the purge status of the expired reports.
-   View an archived report.
-   Print an archived report.

## Print an archived report

1.  Select **System Administrator > Reports/labels > Archive**.
2.  In the grid, select a report.

1.  From the **Actions** drop-down list, select **Print**.
2.  Enter information in the [Print fields](#Print_fields).
3.  Click **Print**. A confirmation message is displayed.
4.  Click **OK**.

## Preview an archived report

1.  Select **System Administrator > Reports/labels > Archive**.
2.  In the grid, select a report.

3.  From the **Actions** drop-down list, select **Preview**.

1.  To use the PDF toolbar options, point to the title of the report until the PDF toolbar is displayed, and then perform any of the following tasks:
    -   To view a different page of the PDF, select the current page number, and enter a different page number.
    -   To turn the display clockwise, click **Rotate Clockwise** ![Rotate](../../../../images/resources/images/image1139573_16x20.png).
    -   To download the PDF, click **Download** ![Download](../../../../images/resources/images/image1139575_17x20.png).
    -   To print the PDF, click **Print** ![Print](../../../../images/resources/images/image1139616_19x20.png), select the destination and pages to print, and then click **Save** or **Print**.
    -   To display a full page, click **Fit to page** ![Fit to page](../../../../images/resources/images/image1139577_19x20.png).
    -   To display the full width of a page, click **Fit to width** ![Fit to width](../../../../images/resources/images/image1139618_19x20.png).
    -   To enlarge the display, click **Zoom in** ![Zoom in](../../../../images/resources/images/image1139581_21x20.png).
    -   To reduce the display, click **Zoom out** ![Zoom out](../../../../images/resources/images/image1139583_22x20.png).

1.  To print the report and then close the report window:
    1.  Enter information in the [Print fields](#Print_fields).
    2.  Click **Print**. A confirmation message is displayed.
    3.  Click **OK**.
2.  To close the report window without printing the report, click **Cancel**.

## Print fields

 
| Field | Description |
| --- | --- |
| **Printer** | Device to use to print the report. This field is required if you are printing a physical copy of the report. |
| **Copies** | Number of copies of the report to print. |
| **Print Report and Send for Digital Signature** | If Yes, the report will be both printed and sent (electronically) to the digital signature capture application.<br > This field is only available if this instance is integrated with a third-party digital signature capture application, and the selected report is enabled and configured for capturing digital signatures. See [Digital signatures](reports.md). |
| **Send for Digital Signature** | If Yes, the report will be sent (electronically) to the digital signature capture application.<br > This field is only available if this instance is integrated with a third-party digital signature capture application, and the selected report is enabled and configured for capturing digital signatures. See [Digital signatures](reports.md). |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
