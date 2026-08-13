---
title: "Work RF Settings"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/work_rf_settings.htm"
source: "/content/work_rf_settings.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Work"
  - "Work"
  - "Work RF Settings"
sections:
  - "Configure work RF settings"
  - "Work RF Settings fields"
images: []
source_sha1: a61d2150f6df9b735fa975a12f91dac4f4db73da
---
# Work RF Settings

You can configure the attributes and behavior for directed work operations for warehouse equipment. For example, you can configure attributes for radio frequency (RF) terminals. These settings apply to both vehicle-mounted and portable warehouse equipment, and some also apply to voice terminals. You can configure the following attributes:

-   General settings that define how a starting location is determined for an operator during the login process, and whether the operator must enter a filter value to obtain directed work
-   Whether the application includes warehouse equipment that is performing undirected work when calculating the maximum number of warehouse equipment allowed in a work zone at the same time
-   Timer settings for the warehouse equipment. For example, the amount of time the application looks for directed work before logging the operator out.

## Configure work RF settings

1.  Select **Configuration > Work > Work > Work RF Settings**.
2.  Enter information in the [Work RF Settings fields](#Work_RF_Settings_fields).
3.  Click **Save**.

## Work RF Settings fields

 
| Field | Description |
| --- | --- |
| Start Location | If Yes, an operator is required to enter their current location during the RF login process. The application uses the start location as a determining factor when locating directed work for the operator.<br > If No, then during the RF login process, the application uses the location specified in the **Default Start Location** field. If no location is specified in that field, then an operator is required to enter their current location. |
| Default Start Location | Location that is used as the default start location for an operator during the RF login process. This field is only available if the **Start Location** field is set to No. The application uses the start location as a determining factor when locating directed work for the operator. |
| Directed Work Filter | If Yes, the operator is prompted to filter for the location in which the directed work is to be performed. When the operator selects RF Directed Work, the application requires the operator to specify an additional work filter (building, aisle, or work zone). Then the application locates directed work based on the filter value. Selecting Yes saves processing time when there are potentially many locations in which directed work could be performed.<br > If No, the operator is not prompted to enter a filter value to obtain directed work. |
| Work Area Associations | If Yes, then the system finds directed work for RF and voice operators based on work area associations. A work area association is a configuration that defines the sequence in which the system searches selected work areas to find directed work. With work area associations, the system considers the association between work areas (typically based on proximity) over work priority, while still following the absolute and delta priorities defined for the home and current work areas. Enable the use of work area associations if you want to reduce travel by limiting the work areas to which an operator is directed to perform work.<br > **Note**: If you set this field to Yes, then you must also enable work area associations for specific warehouse equipment types. See [Work Area Associations](work-area-associations.md).<br > If No, then work area associations are not considered when the system attempts to find work for an operator. |
| Allow Work Operation Override | If Yes, then you allow the base work operations for which an operator is authorized to be temporarily overridden. A work operation override limits the directed work presented to an operator. For example, if there is an increase in receiving work that requires additional resources to complete, but operators are being directed to perform work for a different operation, then a manager can select the receiving work operation as an override for specific operators. The operators with the override are only authorized to perform the receiving work operation, and the rest of their base work operations are temporarily unauthorized. Work operation overrides are valid until the operator logs out of the device or changes warehouse equipment type. See [Work Operation Override](../../../shared-functions/work-operation-override.md).<br > If No, then work operation overrides are not allowed. |
| Calculations | If Yes, the application includes warehouse equipment that is performing directed work as well as warehouse equipment that is performing undirected work when calculating the maximum number of warehouse equipment allowed in the work zone.<br > If No, only warehouse equipment performing work is included in the calculation. The value for maximum warehouse equipment is defined for each work zone and for each warehouse equipment type. |
| Look For Work Duration | Amount of time that the application looks for directed work before the RF operator is automatically logged out of the application in conjunction with the Loop Duration setting. For example, if this field is set to 5m, and Loop Duration is set to 5s, then the application looks for work every 5 seconds and stops after 5 minutes if no work is found. At that point, the message "Timeout Looking for Work – Press Enter" is displayed, and upon pressing Enter, the user is logged out. |
| Loop Duration | Amount of time that the application waits before looking for work again if the application does not find work for the RF operator. |
| Short Timer Duration | Amount of time that the RF Tools Menu or any undirected menu can remain displayed without a key being pressed before the RF Undirected Menu is displayed. |
| Timer Duration | Amount of time that an RF directed work screen can remain displayed without a key being pressed before the RF operator is automatically logged out. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
