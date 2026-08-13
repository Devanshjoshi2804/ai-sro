---
title: "Receiving"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/receiving_config.htm"
source: "/content/receiving_config.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inbound"
  - "Receiving"
sections:
  - "Automated directed receiving"
  - "Automated directed receiving setup"
images: []
source_sha1: e23df71d5bbd51d4ed838fc85f9118b7fa528c36
---
# Receiving - Configuration

Receiving is the process of identifying inventory from an external source into your warehouse so that it can be tracked, processed, stored, and shipped. Receiving may be initiated in any of the following scenarios:

-   After inventory arrives at the warehouse with or without transport equipment
-   From transport equipment at a dock door
-   From a receiving staging location
-   Without an associated planned inbound order or other documentation

You use receiving configurations to define the attributes and behavior of the receiving processes supported by the application.

## Automated directed receiving

Automated directed receiving is the process by which the application automatically creates directed receiving work to a hold status in the work queue, and at the appropriate time (such as after passing any required transport equipment safety checks) releases the receiving work and makes it available to the most appropriate RF operator, based on priority, proximity, and permissions. See [Work Operations](../work/work/work-operations.md).

The application can be configured to automatically create and add directed receiving work to the work queue whenever receiving transport equipment is checked in (or when an inbound shipment is assigned to a staging lane), equipment is moved to a dock door for unloading, or an inbound shipment is unloaded from transport equipment. If directed receiving work for an inbound shipment is created when the transport equipment is checked in, and the inbound shipment is unloaded, its receiving location is updated from the dock door to the receive staging location where the inbound shipment resides.

See [Automated directed receiving setup](#Automated_directed_receiving_setup) below.

The directed work for the inbound shipment can be performed by only one operator. Other operators can assist with receiving the transport equipment by performing receipts in undirected mode. If a specific operator or role is manually assigned to a piece of directed receiving work, then that specific operator (or an operator assigned to the designated role) is always the most appropriate operator to sign on to the directed receiving work.

If you do not want to use automated directed receiving, you can manually assign receiving work to users.

Automated directed receiving work is specified using the configurable workflow functionality; therefore, it is highly flexible and can be configured to meet your facility's business processes.

## Automated directed receiving setup

Before you can use the automated directed receiving functionality, you must configure the application to create receiving work. If transport equipment safety checks are required, then the receiving work is released after successful completion of the safety check.

Set up automated directed receiving using one of the following sets of tasks:

-   If transport equipment does not require a safety check or you receive inventory from an inbound shipment (without transport equipment), perform the following tasks:
    1.  Enable the CRE-RCV-WRK (Create Receiving Work) background warehouse workflow. See [Background Workflows](../work/warehouse-workflows/background-workflows.md).
    2.  Select one of the following exit points to specify the point during processing at which the receiving work is created:
        -   **Master Receipt Check In**: Occurs when the transport equipment or inbound shipment is checked in.
        -   **Transport Equipment to Dock Door**: Occurs when the transport equipment is moved to a dock door.
        -   **Master Receipt Unload**: Occurs when an inbound shipment is unloaded from transport equipment to a receiving staging location.
-   If transport equipment requires a safety check, perform the following tasks:
    1.  Add an action to the master workflow used to perform trailer safety checks (such as PERFORM-TRLR-SAF-CHK, SAFETY-CHK-IMMEDIATE, or SAFETY-CHK-DEFERRED). See [Instruction and workflow actions](../work/workflows/master-workflows.md).
        
        **IMPORTANT**: Do not overwrite the existing Pass action for the workflow; instead, add a new action. Adding a new action causes receiving work to be created only when a safety check passes.
        
        The following list shows how to configure an action to create receiving work:
        
        -   **Result**: Pass
        -   **Action**: Run MOCA
        -   **Command**: create directed receiving work where trlr\_id = @trlr\_id and wh\_id = @wh\_id
    2.  Enable the warehouse workflow for the transport equipment safety check that you configured to create receiving work.
    3.  Specify the exit point at which the transport equipment safety check should take place.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
