---
title: "Work Operation Override"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/work_operation_override.htm"
source: "/content/work_operation_override.htm"
toc_path:
  - "Warehouse Management"
  - "Shared functions"
  - "Work Operation Override"
sections:
  - "Override work operations for a user"
  - "Work Operation Override fields"
images: []
source_sha1: ae356b62dac64078d5a5834d74aecae52f091f77
---
# Work Operation Override

The Work Operation Override page is accessible from the following modules: **Picking**, **Receiving**, or **Shipping**.

A work operation override is a temporary update to a user's authorized work operations that limits the directed work presented to the user. You use the Work Operation Override page to select the work operations that are temporarily authorized; work operations that are typically authorized but not selected are not presented to the user. For example, if there is an increase in receiving work that requires additional resources to complete, but operators are being directed to perform work for a different operation, then you can select the receiving work operation as an override. The operators for whom you select the override are only authorized to perform the receiving work operation, and the rest of their base work operations are temporarily unauthorized.

**Note**: Work operation overrides only take effect if the **Allow Work Operation Override** field is set to Yes. See [Configure work RF settings](../configuration/work/work/work-rf-settings.md).

The Work Operation Override page displays a record for each operator that is currently logged in to an RF, mobile, or voice device. For each operator, the application displays the warehouse equipment type in use, current work area, the operation being performed, the number of base operations the operator can perform, and the number of work operation overrides. If the number of overrides is 0 (zero), then the operator can perform all available base work operations for which the equipment type and operator are authorized. If the number of overrides is greater than 0, then the operator is restricted to performing work only for the selected work operations.

When you click the number of operation overrides in the grid, the application displays a column of the available work operations for which the operator and warehouse equipment type are authorized. If you select the check box for a work operation in the Available column, it is moved to the Selected column, meaning that the operator is only authorized to performed the selected work operation. Work operation overrides are valid until the operator logs out of the device or changes warehouse equipment type, at which time the number of overrides automatically resets to 0.

## Override work operations for a user

1.  View the Work Operation Override page.
    
    1.  Select one of the following modules: **Picking**, **Receiving**, or **Shipping**.
    2.  Select **Work Operation Override**.
    
2.  View the information in the [Work Operation Override fields](#Work_operation_override_fields).
    
3.  In the row for the user for whom you want to add overrides, click the **Override Operations** value.
    
4.  In the **Available** column, select the check box next to each override work operation.
    
    **Note**: The Available column displays the work operations that are authorized for both the user and the warehouse equipment type. When you select and save one or more work operation overrides, the user is only presented work for the selected operations. The application temporarily suspends authorization for the deselected work operations until the user logs out of the device or changes warehouse equipment type.
    
5.  Click **Save**. The **Override Operations** value displays the number of work operation overrides selected for the operator.
    

## Work Operation Override fields

 
| Field | Description |
| --- | --- |
| User | Unique identifier for an individual who uses the application. |
| Device | Unique identifier for a piece of equipment such as a radio frequency (RF) or mobile device that has access to or communicates with the application. The device code is the display name for the device and represents a logical location during warehouse operations. For example, during picking, an inventory display shows the device code as the location of the inventory until the inventory is deposited. |
| Equipment Type | Type of warehouse equipment the operator is currently using. Warehouse equipment refers to the material handling vehicles that an operator uses to perform directed work and other warehouse operations. For example, a fork truck, crane, or handheld terminal. |
| Base Operations | Number of work operations the user is authorized to perform using the current warehouse equipment type, based on the work operation configurations. A work operation is a defined activity within the facility usually performed by an operator using a device such as an RF terminal or voice headset. The number of base operations a user can perform depends on the operations authorized for the warehouse equipment type in use. |
| Override Operations | Number of work operation overrides for the user. If the number of overrides is 0 (zero), then the operator can perform all available base work operations for which they are authorized. If the number of overrides is greater than 0, then the operator can perform all available base work operations for which the equipment type and operator are authorized. The number of overrides automatically resets to 0 when the operator logs out of the device or changes warehouse equipment or equipment type. |
| Current Work Area | Work area in which the user is currently performing work. If the user is not performing work, then this is the work area the user selected during the login process, if applicable. |
| Current Work Zone | Work zone in which the user is currently performing work. If the user is not performing work, then this is the work zone the user selected during the login process, if applicable. |
| Current Location | Location in which the RF or mobile device is currently in use. |
| Current Operation | Work operation the user is currently performing. If the user is not performing work, then this field is blank. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
