---
title: "Workstations"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/workstations.htm"
source: "/content/workstations.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Equipment"
  - "Hardware"
  - "Workstations"
sections:
  - "Add or modify a workstation"
  - "Delete a workstation"
  - "Workstations fields"
images: []
source_sha1: fbf8955b3ac548f611a35fec694af157fc99d144
---
# Workstations

A workstation consists of a keyboard and monitor that communicates with the application and is used to perform display, maintenance, and operational tasks (other than directed work). When you add a workstation, you define the following attributes:

-   Whether the application displays a confirmation message when an operator changes the carton type
-   Field to which the cursor moves after a carton is processed
-   Whether the workstation has a touch screen display (used in pack station processing)
-   Printers, if used, to which the workstation can print labels or reports
-   Identifier of the weight scale and barcode scanner, if used, that are connected to the workstation. These components are used in pack station processing.
-   Attributes specific to workstations used for production line work order processing
-   Attributes specific to workstations used for outbound processing (such as packing or auditing shipping cartons)

## Add or modify a workstation

1.  Select **Configuration > Equipment > Hardware > Workstations**.
2.  Perform one of the following tasks:
    -   To add a new workstation, click **Add**.
    -   To modify a workstation, in the grid, click the workstation.
    -   To copy a workstation, in the grid, select the check box next to the workstation, and then click **Copy**.
3.  Enter information in the [Workstations fields](#Workstations_fields).
4.  To select the movement zones (associated with the packing workstation) in which shipping containers can be consolidated after packing:
    
    **Notes**:
    
    -   A consolidation movement zone can be associated with multiple workstations to allow multiple workstations to consolidate shipping containers to the same pallet LPNs.
    -   Available movement zones are those with locations that have pallet positions defined.
    -   This field is only available if the **Consolidate at Pack Station** field is set to Yes.
    
    1.  Under **OUTBOUND PROCESSING**, click **Pack Station Consolidation Movement Zones**.
    2.  In the **Available** column, select the check box next to the destination movement zones in which shipping containers should be consolidated at the pack station.
    3.  Click **Apply**.
5.  Click **Save**.

## Delete a workstation

1.  Select **Configuration > Equipment > ** **Hardware > Workstations**.
2.  In the grid, select the check box next to the workstation to delete.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Workstations fields

 
| Field | Description |
| --- | --- |
| Workstation ID | Identifier for a workstation. Typically the identifier of the workstation is the same as that used to identify the workstation on your computer network. |
| Touchscreen | If Yes, indicates that the workstation operates in touch screen mode for windows that are designed for that purpose. In windows that support touch selections, a user can tap areas on the screen (typically using a finger) to scroll through values and select buttons. Application windows are displayed differently in touch screen mode; for example, buttons and scroll bars are larger to make using the touch screen easier. Touch screens are typically used for pack station operations.<br > If No, indicates that you do not want to use touch screen mode at the workstation. |
| Description | Description that further defines the workstation. For example, the description can be used to identify the location of the workstation or whether it is a standard or touch screen. |
| Movement Zone | Name of a movement zone. A movement zone represents a group of locations to and from which inventory can be moved. For example, storage locations to which inventory can be deposited and processing locations to which inventory is moved for packing are the types of locations that must be assigned to a movement zone for the application to select those locations for putaway or deposit.<br > Source, hop, and destination locations must be assigned to a movement zone so that a movement path can be defined to use each of those locations. |
| Report Printer | Name of the printer that will be used to print reports from this device. Only printers that have been configured to print reports are available for selection. |
| Label Printer | Name of the printer that will be used to print labels from this device. Only the label printers that have been set up and configured to work with the application are available for selection. |
| Scale Type | Server command that supports communication between the workstation and a specific type of weight scale. A weight scale is typically used during pack station processing to enter or confirm the weight of a packed shipping container. The application supports the following scale configurations:<br > **Note**: If the scale that you want to use is not listed, contact Customer Support.<br>-   • **Adam Protocol**
<br>-   • **Fairbanks Protocol**
<br>-   • **NCI Protocol**
<br>-   • **Toledo Protocol** |
| Scale Network Address | Network address of the scale that is used to connect the scale to the workstation. The application supports a network interface between the workstation and the scale. |
| Scale Port Number | Port number of the scale that is used to connect the scale to the workstation. |
| Scanner | Identifier of the serial communication configuration that represents the barcode scanner that is or will be attached to the workstation. This is the scanner that the pack station will use to read barcodes. Serial communication configurations are defined on the Serial Communications configuration page. |
| Production Line | Name of the location that identifies the workstation's position on a production line. |
| Processing with Workstation | If Yes, the workstation is used for outbound processing such as packing picked inventory into shipping containers.<br > If No, the workstation is not used for outbound processing. |
| Processing Movement Zone | Name of the movement zone in which this workstation is located. This is the movement zone in which the outbound processing (packing or auditing of shipping containers) is performed using the workstation. The workstation can perform outbound processing only in the processing zone to which it is assigned. If no processing movement zone is selected, then the workstation can perform outbound processing in any of the movement zones configured for outbound processing.<br > The **Processing Movement Zone** field is only available when the **Processing with Workstation** field is set to Yes. |
| Exception Handling Location | Location to which picked inventory containers are directed when errors (such as missing inventory, unexpected inventory or the wrong quantity of inventory) are encountered during pack station processing. The location is displayed as the default special handling location during packing operations. If you do not specify a special handling location for the workstation, then the application uses the default special handling location specified for pack station processing. If you do not specify a special handling location for the device and a default one is not provided, then the packing operator selects a location during packing.<br > The **Exception Handling Location** field is only available when the **Processing with Workstation** field is set to Yes. |
| Allowed Scans | Type of identifier that can be used to initiate processing during packing operations at the workstation.<br>-   • **Location**: Processing can be initiated by entering the location that contains the picked inventory that needs to be packed. You may want to scan locations if you have small shelf locations set up at the pack station, pickers deposit inventory into one side of the shelf location, and the packing operator scans the shelf location ID while removing the inventory from the other side of the shelf to the shipping container.
<br>-   • **LPN**: Processing can be initiated by entering the LPN (such as a pallet LPN) that contains the picked inventory that needs to be packed.
<br>-   • **Sub-LPN**: Processing can be initiated by entering the sub-LPN (such as for a case or a tote) that contains the picked inventory that needs to be packed or audited. You may also want to use sub-LPN identifiers if the packing operator receives cartons from a conveyor.
<br > The **Allowed Scans** field is only available when the **Processing with Workstation** field is set to Yes. |
| Consolidate at Pack Station | If Yes, then after packing inventory to a non-pallet shipping container, the packing operator is directed to deposit the container onto a pallet if the next move for the container is the consolidation zone configured for the pack station. If you set this field to Yes, then use the **Pack Station Consolidation Movement Zones** field to select the consolidation movement zones associated with the pack station.<br > If No, then after packing inventory to a shipping container, the operator is directed to deposit the container to the processing destination zone. |
| Manifest at Pack Station | If **Yes**, then when a shipping container is completed at the pack station, the Manifesting page is displayed for the packing operator to manually manifest the parcel. The application populates the **Identifier** field on the Manifesting page with the shipping container ID, and the operator can perform manifesting operations such as rate shopping and, if allowed, carrier change. After a parcel is manifested, the Packing page is displayed for the operator to resume packing operations. Set this field to **Yes** to allow packing operators to manifest shipping containers in-line with packing operations. However, if the packing operator does not have permission to view the Manifesting page, then the page is not displayed. See [Manifest at pack station](../../../packing/packing-concepts.md).<br>
**Notes**:

<br>

-   • If the **Manifest at Pack Station** field is set to Yes, then the Manifest Shipping Container background workflow should be disabled.
<br>-   • If the **Manifest at Pack Station** and **Consolidate at Pack Station** fields are set to Yes, then the packing operator must first manifest the container before consolidating the container onto a pallet.
<br>

<br > If No, then the Manifesting page is not automatically displayed when a shipping container is completed at the pack station.<br > **Note**: Manifesting functionality is only available when Warehouse Management is integrated with a parcel application through Parcel Handler. |
| Suppress Carton Type Change Confirmation | If Yes, then when a packing operator changes the carton type during pack station operations, the application suppresses the confirmation message so the operator does not have to acknowledge the message and confirm the carton selection. This is useful for workstations that process large quantities of single-line, single-item orders (such as e-commerce orders) where reduced user interaction can increase packing efficiency. For example, if a packing operator scans a picking container and changes the carton type selected by the application, then the message is not displayed and the operator can continue packing operations without confirming the new carton selection.<br > **Note**: If you select Yes and a packing operator changes the carton type to the generic carton, the confirmation message is not displayed but the operator is still required to enter the carton dimensions. If the pallet carton type is used, the operator cannot change the carton type, and the confirmation message is displayed regardless of this field.<br > If No, then the application displays the carton type change confirmation message and the packing operator must accept or reject the confirmation message which determines if the application changes the carton type. |
| Next Field | Field to which the cursor on the Packing page moves after a carton is processed. Select a value to bypass fields for which a value is automatically populated or not required. This is useful for workstations that process large quantities of single-line, single-item orders (such as e-commerce orders) where reduced user interaction can increase packing efficiency. For example, if the **Capture Required** field is set to Yes, meaning that the packing operator is required to capture the weight of a packed shipping container, then you could select Actual Weight as the next field so the operator does not have to manually position the cursor in that field. Alternatively, if the weight is already populated through the use of an integrated weight scale, then you can select Carton Type as the next field so the packing operator can expedite carton type confirmation after the carton is processed. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
