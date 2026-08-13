---
title: "Aging Profiles"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/aging_profiles.htm"
source: "/content/aging_profiles.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Inventory"
  - "Inventory Status"
  - "Aging Profiles"
sections:
  - "Age calculation"
  - "Expiration date validation"
  - "Add or modify an aging profile"
  - "Delete an aging profile"
  - "Aging Profile fields"
  - "Aging Profile Detail fields"
images: []
source_sha1: 4a036c3b828b92b030af25db8b307f74461a54a4
---
# Aging Profiles

An inventory aging profile is a configuration that defines a series of inventory statuses, each of which is associated with an age, such as 2 hours, 10 days, or 4 weeks. You assign an aging profile to a date-tracked item if you want the application to automatically update the status of inventory for the item as it ages in the warehouse. For example, it can be useful for perishable commodities such as food, beverages, pharmaceuticals, and other items that deteriorate as they age.

The aging profile includes an option to define an expired status. The application uses the age of the expired status to calculate the expiration date of an item that is tracked by its expiration date.

If an aging profile is assigned to an item, then when the item is received into the warehouse, the operator enters the manufactured or expiration date, and the aging process starts in accordance with the item's aging profile.

**Note**: To retain data consistency with physical labels, user-defined inventory attributes, manufactured date fields, and expiration date fields are not converted to a different time zone when displayed in the web client or stored in the database, but retain their original captured time zone. For example, if a user views inventory that was received in a different time zone, the expiration date and manufactured date are displayed in the original time zone.

If the background job for executing the aging process is enabled, it is executed automatically to determine whether the inventory status needs to be updated; the job schedule can be configured to execute on any timely basis.

If an item is tracked by its manufactured date or expiration date, then an aging profile is optional. If it is tracked by both its manufactured and expiration dates, then either an aging profile or a shelf life is required. For more information on date-tracked items, see [Date controlled inventory](../items/items.md).

### Age calculation

Depending on the method of aging you assign to a profile (manufactured date or expiration date), the inventory statuses defined in the aging details of the profile must be configured in the correct sequence. For a profile that ages by manufactured date, the statuses advance forward from available to expired. For a profile that ages by expiration date, the statuses are sequenced in reverse from expiration to available.

The following table is an example of the aging details of a profile that calculates status by manufactured date. The application considers the product's manufactured date and then calculates forward, so the inventory status changes from Available to Short Date 3 days after the manufactured date, and the inventory expires 5 days after it was manufactured.

   
| Status | Age | Unit of Time | Age Calculation |
| --- | --- | --- | --- |
| Available | 0 | Days | Manufacture Date |
| Short Date | 3 | Days | Manufacture Date |
| Expired | 5 | Days | Manufacture Date |

The following table is an example of the aging details of a profile that calculates status by expiration date. The application considers the product's expiration date and then calculates backwards, so the inventory status changes from Available to Salvaged 3 days prior to the expiration date.

   
| Status | Age | Unit of Time | Age Calculation |
| --- | --- | --- | --- |
| Expired | 0 | Days | Expiration Date |
| Salvaged | 3 | Days | Expiration Date |
| Available | 5 | Days | Expiration Date |

### Expiration date validation

You can configure an aging profile so that the item to which the profile is assigned is validated against the defined minimum and maximum time allowed before expiration. The minimum and maximum time you define is generally based on the characteristics of the item to which the aging profile is assigned. For example, for items that are easily perishable, the minimum amount of time before expiration may be greater so as to allow ample time for the item to be processed out of the warehouse before it expires.

Expiration date validation can take place while receiving inbound orders or customer returns (inbound order type is Customer Return), or during both processes, depending on the aging profile configuration. Additionally, the item must be tracked by expiration date or by manufactured date and expiration date (**Date Code** for the item is set to Expiration Date or Both).

The following table is an example of the expiration date validation settings for an aging profile.

    
| Validate Expiration Date During Receiving | Validate Expiration Date During Returns | Minimum Time Before Expiration | Maximum Time Before Expiration | Unit of Time |
| --- | --- | --- | --- | --- |
| Stop | Warn | 10 | 30 | Days |

Based on this information, the following assumptions can be made for items with this profile: 

-   The application validates expiration dates when the item is received and returned, and allows uninterrupted processing if the item expires between 10 and 30 days from the current date.
-   The application stops receiving the item if it is less than 10 days or more than 30 days from expiration. The operator can enter an expiration date that is within the defined range and can continue receiving.
-   While receiving a customer return order (inbound order type is Customer Return), the application warns the operator when an item is outside the defined range. The operator can continue processing the return with the entered expiration date, or the operator can stop processing, enter an expiration date that is within the defined range, and then continue receiving the return order.

## Add or modify an aging profile

For each aging profile you must assign an age of zero (0) to the first inventory status. This is typically the status that is assigned to inventory when it is received into the warehouse. You must also define an inventory status that indicates the inventory is expired (by selecting the Expired check box for that status).

1.  Select **Configuration > Inventory > Inventory Status > Aging Profiles**.
2.  Perform one of the following tasks:
    -   To add an aging profile, click **Add**.
    -   To modify an aging profile, in the grid, click the profile name.
    -   To copy a profile, in the grid, select the check box next to the profile, and then click **Copy**.
3.  Enter information in the [Aging Profile fields](#Aging_Profile_fields).
4.  Under **AGING DETAILS**, configure inventory statuses for the aging profile:
    1.  Perform one of the following tasks:
        -   To add a status, click **Add**.
        -   To modify a status, in the grid, click the status.
    2.  Enter information in the [Aging Profile Detail fields](#Aging_Profile_Detail_fields).
    3.  Click **Apply**.
    4.  To delete a status from the aging profile:
        1.  In the grid, select the check box next to the status, and then click **Delete**. A confirmation message is displayed.
        2.  Click **OK**.
5.  Click **Save**.

## Delete an aging profile

1.  Select **Configuration > Inventory > Inventory Status > Aging Profiles**.
2.  In the grid, select the check box next to the profile to delete.
3.  Click **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Aging Profile fields

 
| Field | Description |
| --- | --- |
| Description | Description of the aging profile. |
| Name | Name of the aging profile. This is the value you select when assigning an aging profile to an item. |
| Minimum Time Before Expiration | Minimum amount of time prior to an item’s expiration date that the item can be received or returned without the application warning the operator or stopping the process. For example, assume this field value is 10, the **Unit of Time** field is Days, and an expiration date-tracked item is received. If the item is set to expire less than 10 days from the current date, then the application either warns the operator or stops receiving, depending on the value selected in the **Validate Expiration Date During Receiving** field.<br > **Note**: This field value applies to receiving inbound orders and customer returns (inbound order type is Customer Return). However, if the **Validate Expiration Date During Receiving** field or **Validate Expiration Date During Returns** field is left blank (null), then validation does not take place during the respective process. |
| Maximum Time Before Expiration | Maximum amount of time prior to an item’s expiration date that the item can be received or returned without the application warning the operator or stopping the process. For example, assume this field value is 40, the **Unit of Time** field is Days, and an expiration date-tracked item that is received. If the item is set to expire more than 40 days from the current date, then the application either warns the operator or stops receiving, depending on the value selected in the **Validate Expiration Date During Receiving** field.<br > **Note**: This field value applies to receiving inbound orders and customer returns (inbound order type is Customer Return). However, if the **Validate Expiration Date During Receiving** field or **Validate Expiration Date During Returns** field is left blank (null), then validation does not take place during the respective process. |
| Unit of Time | Time measurement unit for the numbers in the **Minimum Time Before Expiration** and **Maximum Time Before Expiration** fields. |
| Validate Expiration Date During Receiving | Determines if the application validates an item's expiration date during receiving, and if so, how the application responds to an expiration date outside of the defined range. The range is defined by the **Minimum Time Before Expiration** and **Maximum Time Before Expiration** fields. For example, if the minimum is 5 days and the maximum is 20 days, then an item that expires in 7 days is within the defined range. However, if the item expires in 21 days, then the item is outside the defined range, and depending on this field, the application may require additional action from the user.<br > **Note**: Expiration date validation is only applicable to items that are date-tracked by expiration date (**Date Code** field for the item is set to Expiration Date or Both).<br>-   • **Warning**: The application validates an item's expiration date during receiving and prompts the operator with a warning when an item is outside the defined range. The operator can continue receiving with the entered expiration date, or the operator can stop receiving, enter an expiration date that is within the defined range, and then continue receiving.
<br>-   • **Error**: The application validates an item's expiration date during receiving, prompts the operator with a message when an item is outside the defined range, and stops the receiving process. When this occurs, the device cursor is positioned in the **Expiration Date** field. The operator can enter an expiration date that is within the defined range, and continue receiving.
<br>-   • **Blank**: The application does not validate the expiration date during receiving. |
| Validate Expiration Date During Returns | Determines if the application validates an item's expiration date while receiving a customer return (inbound order type is Customer Return), and if so, how the application responds to an expiration date outside the defined range. The range is defined by the **Minimum Time Before Expiration** and **Maximum Time Before Expiration** fields. For example, if the minimum is 5 days and the maximum is 20 days, then an item that expires in 7 days is within the defined range. However, if the item expires in 21 days, then the item is outside the defined range, and depending on this field, the application may require additional action from the user.<br > **Note**: Expiration date validation is only applicable to items that are date-tracked by expiration date (**Date Code** field for the item is set to Expiration Date or Both).<br>-   • **Warning**: The application validates an item's expiration date when a customer return order is received, and prompts the operator with a warning when an item is outside the defined range. The operator can continue receiving the return order with the entered expiration date, or the operator can stop processing, enter an expiration date that is within the defined range, and continue receiving the return order.
<br>-   • **Error**: The application validates an item's expiration date when a customer return order is received, prompts the operator with a message when an item is outside the defined range, and stops the receiving process. When this occurs, the device cursor is positioned in the **Expiration Date** field. The operator can enter an expiration date that is within the defined range, and continue receiving the return order.
<br>-   • **Blank**: The application does not validate the expiration date when a customer return order is received. |

## Aging Profile Detail fields

 
| Field | Description |
| --- | --- |
| Status | Quality status of an item. Defines the quality or disposition of the item. |
| Age | Age for the unit of measurement selected from the Unit of Time drop-down list. The Age and Unit of Time indicate the age that inventory must reach before the Status is applied. |
| Unit of Time | Time measurement unit for the number in the Age field. The Age and Unit of Time indicate the age that inventory must reach before the Status is applied. |
| Age Calculation | Determines how the application calculates the date on which the inventory status change is made.<br>-   •
    
    **From the manufactured date forward**: Indicates that the time value defined for the status is the amount of time that has passed since the inventory was manufactured. Therefore, the time is added to the manufactured date to arrive at the date that the inventory status changes. For example, if the aging detail is configured to change the inventory to the Inspect status at an age of 10 days, then the change takes place 10 days after the manufactured date.
    
    <br>
    
    This option is displayed as **Manufacture Date** in the AGING DETAILS grid.
    
    <br>
<br>-   •
    
    **From the expiration date backward**: Indicates that the time value defined for the status is the amount of time remaining until the inventory expires. Therefore, the time is subtracted from the expiration date to arrive at the date that the inventory status changes. For example, if the aging detail is configured to change the inventory to the Inspect status at an age of 10 days, then the change takes place 10 days prior to the expiration date.
    
    <br>
    
    This option is displayed as **Expiration Date** in the AGING DETAILS grid.
    
    <br> |
| Expire Inventory | If Yes, the application considers inventory to be expired when it reaches this status in the aging process. You must define one and only one aging detail with this status. The application uses the age of the expired status to calculate the inventory's expiration date.<br > **Note**: If this field is set to Yes and the aging profile is assigned to an item with the **Date Code** field set to Both, then when an operator receives the item and enters a manufactured or expiration date, the application calculates the other date based on the aging profile. For example, if an operator enters the manufactured date, then the application calculates the expiration date and prompts the operator to accept or adjust the date.<br > If No, this status is not used to indicate that inventory is expired. |
| Scrap Inventory | If Yes, the application considers the inventory to be scrap (unusable) when it reaches this status in the aging process.<br > If No, the inventory is not considered to be unusable when it reaches this status. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
