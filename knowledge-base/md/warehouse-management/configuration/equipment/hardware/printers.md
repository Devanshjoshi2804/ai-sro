---
title: "Printers"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/printers.htm"
source: "/content/printers.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Equipment"
  - "Hardware"
  - "Printers"
sections:
  - "Add or modify a printer"
  - "Delete a printer"
  - "Printers fields"
images: []
source_sha1: 50bd82c4b6a77c55a42135c066162dbb5f8891c4
---
# Printers

Printers are used to print documents such as reports, and carton, picking, and shipping labels.

-   To print reports, you must have Warehouse Reporting integrated with the application, and you must define one or more report (typically postscript) printers. When report printers are defined, they are available for selection when printing reports.
-   To print labels, you must define the local and network printers on the application server (or remote server), and then define them in Warehouse Management. When label printers are defined, they are available for selection when printing labels.

You can assign a printer to a location so that when printing takes place at the location as a result of a workflow action, paperwork is directed to the assigned printer by default.

## Add or modify a printer

1.  Select **Configuration > Equipment > ** **Hardware > Printers**.
2.  Perform one of the following tasks:
    -   To add a new printer, click **Add**.
    -   To modify a printer, in the grid, click the printer.
    -   To copy a printer, in the grid, select the check box next to the printer, and then click **Copy**.
3.  Enter information in the [Printers fields](#Printers_fields).
4.  To assign the printer to locations:
    
    **Note**: You can assign a printer to a location so that when printing takes place at the location as a result of a workflow action, paperwork is directed to the assigned printer by default.
    
    1.  Click **Printer Location Assignments**.
    2.  To add a printer assignment:
        1.  Click **Add**.
        2.  Enter search criteria to find locations.
        3.  In the grid, select the check box next to the locations that apply.
        4.  Below the grid, from the **Assign As** drop-down list, select the type of printer that is assigned to the location.
        5.  Click **Apply**.
    3.  To delete a printer assignment:
        1.  In the grid, select the check box next to the location.
        2.  Click **Delete**. A confirmation message is displayed.
        3.  Click **OK**.
5.  Click **Save**.

## Delete a printer

1.  Select **Configuration > Equipment > ** **Hardware > Printers**.
2.  In the grid, select the check box next to the printer to delete.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Printers fields

 
| Field | Description |
| --- | --- |
| Printer Network Address | Name of the printer that has been defined on the network, or the printer's internet protocol (IP) address on the network. You can typically obtain the printer IP address from the printer's setup menu or documentation. |
| Printer Type | Name that describes the type of printer. The printer type can represent the kind of printer (such as Postscript or Label) or the manufacturer and model (such as Zebra 170XI). The printer type helps users select the correct printer from a list of printers when attempting to print labels and reports. |
| Printer Language | Determines the printer language in which labels are generated using the printer.<br>-   •
    
    **ZPL**: Labels are generated using Zebra Programming Language (ZPL).
    
    <br>
<br>-   •
    
    **DPL**: Labels are generated using Datamax Programming Language (DPL).
    
    <br>
<br > If no value is selected, ZPL is used by default. |
| Use Print Queue | If Yes, the application uses the print queue located on a remote server. Select Yes if the printer is located on a remote server (such as the instance server). You must enter the location of the print queue in the Print Queue Location field. A print queue is a representation of a physical printer that is used to display active print jobs and their status.<br > If No, the application uses the local print queue. Select No if the printer is local (connected to the server). If the printer is local, the application uses the name of the printer to find the local print queue. |
| Print Queue Location | Location of the print queue on the remote server. Enter the subdirectory in which print jobs (files that have been submitted to be printed) are stored until they are output to the printer. For example, if the directory is $LESDIR/labels, then the subdirectory could be a name that represents the printer type, such as "Zebra" or "Intermec". |
| Printer Description | Meaningful description that further identifies the printer. For example, Printer in the shipping office. |
| Printer Status | Defines the status of the printer.<br>-   • **Connected**: Indicates that the printer is connected and available for use.
<br>-   • **Disconnected**: Indicates that the printer is disconnected and not available for use.
<br>-   • **Rerouted**: Indicates that jobs sent to this printer should be rerouted to another printer. When selected, you must specify the printer to which the print jobs are sent. |
| Route To Printer | Name of the printer to which to print jobs are sent, when the value for **Printer Status** is **Rerouted**. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
