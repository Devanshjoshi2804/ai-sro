---
title: "Manifest Package Operations policies"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/policies/manifest_package_operations_policies.htm"
source: "/content/policies/manifest_package_operations_policies.htm"
toc_path:
  - "Administration"
  - "System Administrator"
  - "Configuration"
  - "Policy"
  - "Manifest Package Operations policies"
sections:
  - "Default minimum weight policy"
  - "Default scan by work reference number policy"
  - "Allow carrier change policy"
  - "Mixed parts default policy"
  - "Workstation <WS-XX> policies"
  - "Workstation <WS-XX> minimum weight policy"
  - "Workstation <WS-XX> scan by work reference number policy"
images: []
source_sha1: 4301c42dc7cda588cf4f751a795fe21fbd26d23b
---
# Manifest Package Operations policies

The Manifest Package Operations (MANPKGOPR) policies determine which options are available on the Manifest Package Operations window in the SCE client. When you configure MANPKGOPR policies, you can specify the following information:

-   **Default settings**: Used to define the minimum acceptable weight and whether a parcel can be identified by a work reference number.
-   **Miscellaneous settings**: Used to define whether carrier changes are permitted and the text that is to be used to describe parcels that contain a mix of different items.
-   **Workstation-specific (<**_WS-XX_**>) settings**: Used to define the minimum acceptable weight and whether a parcel can be identified by a work reference number when the Manifest Package Operations window is started on a specific workstation. If defined, workstation-specific settings are used instead of the default settings.

You use Policy Maintenance or Policy Maintenance - Override to maintain MANPKGOPR policies.

## Default minimum weight policy

The Default minimum weight (MANPKGOPR/DEFAULT/MINIMUM-WEIGHT) policy controls the default settings for the minimum acceptable weight for a parcel. This policy is used for any workstation that does not have a workstation-specific policy configured.

You can configure the following DETAILS fields for this policy:

-   **Return String 1**: Text, as defined on the Measurement Units page in the **Host Measurement Unit Code** field, that represents the measurement unit (MU) for the minimum weight specified in the **Return Float 1** field.
    -   If the **Return String 1** field is blank, Warehouse Management uses LB.
    -   If an invalid MU is specified the **Return String 1** value, then when a user starts Manifest Package Operations, an error is displayed stating that an invalid MU is defined for the minimum weight policy. Manifest Package Operations cannot be started until this error is resolved.
-   **Return Float 1**: Real number (number that can contain a fractional part), such as 2.25, that specifies the minimum weight allowed for a parcel.
    -   If the weight in the **Package Weight** field (entered manually or captured from an integrated weight scale) on the Manifest Package Operations window is less than the minimum weight, then Warehouse Management automatically changes the value to the minimum weight.
    -   If the MU specified in the **Return String 1** field is different from the default weight unit for the user's locale (defined on the Locales page), then Warehouse Management internally converts the minimum weight to the default weight unit before comparing it against the weight in the **Package Weight** field on the Manifest Package Operations window. For example, if you set the minimum weight policy to 1 KG, but the user's locale default weight unit is LB, the minimum weight is converted internally to 2.20462262 LB. If the weight in the **Package Weight** field is 1.5 LB, it is reset to the minimum weight of 2.20462262 LB. Some parcel carriers have minimum weight requirements. Setting this policy to the parcel carrier's minimum acceptable weight enables you to properly manifest parcels with the carrier.

## Default scan by work reference number policy

The Default scan by work reference number (MANPKGOPR/DEFAULT/SCANNING-BY-WORK-REFERENCE) policy controls whether a parcel can be identified by a work reference number when the Manifest Package Operations window is started. This policy is used for any workstation that does not have a workstation-specific policy configured.

You can configure the following DETAILS fields for this policy:

-   **Return Number 1**: Specifies whether the **Work Reference** field will be available on the Manifest Package Operations window. The following values are valid:
    -   **0:** The field is not available. Typically, you use this setting when all or most of your manifesting workstations are used to process individually picked cases.
    -   **1**: The field is available. Typically, you use this setting when all or most of your manifesting workstations are used to process loads of cases so that the user can scan the work reference rather than each individual case.

## Allow carrier change policy

The Allow carrier change (MANPKGOPR/MISCELLANEOUS/ALLOW-CARRIER-CHANGE) policy controls whether carrier changes are permitted (enabled) when manifesting a parcel. When this policy is enabled and the Carriers setting is enabled on the outbound order settings, the **Carrier** and **Service Level** fields are displayed on the Manifest Package Operations window.

You can configure the following DETAILS field for this policy:

-   **Return Number 1**: Specifies whether carrier changes are permitted (enabled). A value of 1 is enabled, 0 is disabled.
    
    **Note**: If you set this value to 1, any such changes that are made do not take effect immediately, but become deferred changes for the shipment to be executed when the shipment is staged.
    

## Mixed parts default policy

The Mixed parts default (MANPKGOPR/MISCELLANEOUS/MIXED-PARTS-DEFAULT) policy specifies the text that describes parcels containing a mix of different items on the Manifest Package Operations window.

You can configure the following DETAILS fields for this policy:

-   **Return String 1**: Mixed Items. Mixed Items is the standard text string that represents the Warehouse Management internal description of a parcel that contains different items. This value is defined in the les\_mls\_cat entry for lbl\_mixed\_part.
    
    **Note**: For more information on les\_mls\_cat entries, contact your Blue Yonder project team.
    
-   **Return String 2**: Text string, such as Assortment, that represents the description for a parcel that contains different items. This value is the description that you want to be displayed on the Manifest Package Operations window instead of the Warehouse Management internal description specified in the **Return String 1** field. You only need to configure this policy setting if you want to specify your own description for a parcel that contains different items. This policy setting only applies to the Manifest Package Operations window.

## Workstation <_WS-XX_> policies

The Workstation (MANPKGOPR/<_WS-XX_>) policies, where <_WS-XX_> is replaced with the name of the manifesting workstation as defined on the Workstations page, control settings when the Manifest Package Operations window is started on a specific workstation. Workstation-specific policies are optional and if not configured, the default policies are used.

**Note**: MANPKGOPR/<_WS-XX_> policies are not distributed. If you want to use them, you must add them.

Workstation-specific policies are useful in situations where you need one or more manifesting workstations to operate differently from the rest of the manifesting workstations. For example, you may have one workstation where you manifest parcels for a specific seldom-used parcel carrier, but all of your other manifesting workstations manifest parcels for your primary parcel carrier.

### Workstation <_WS-XX_> minimum weight policy

The Workstation <_WS-XX_> minimum weight (MANPKGOPR/<_WS-XX_>/MINIMUM-WEIGHT) policy controls a specific workstation's settings for the minimum acceptable weight of a parcel.

You can configure the following DETAILS fields for this policy:

-   **Return String 1**: Text, as defined on the Measurement Units page in the **Host Measurement Unit Code** field, that represents the measurement unit (MU) for the minimum weight specified in the **Return Float 1** field.
    -   If the **Return String 1** field is blank, Warehouse Management uses LB.
    -   If an invalid MU is specified the **Return String 1** value, then when a user starts Manifest Package Operations, an error is displayed stating that an invalid MU is defined for the minimum weight policy. Manifest Package Operations cannot be started until this error is resolved.
-   **Return Float 1**: Real number (number that can contain a fractional part), such as 2.25, that specifies the minimum weight allowed for a parcel.
    -   If the weight in the **Package Weight** field (entered manually or captured from an integrated weight scale) on the Manifest Package Operations window is less than the minimum weight, then Warehouse Management automatically changes the value to the minimum weight.
    -   If the MU specified in the **Return String 1** field is different from the default weight unit for the user's locale (defined on the Locales page), then Warehouse Management internally converts the minimum weight to the default weight unit before comparing it against the weight in the **Package Weight** field on the Manifest Package Operations window. For example, if you set the minimum weight policy to 1 KG, but the user's locale default weight unit is LB, the minimum weight is converted internally to 2.20462262 LB. If the weight in the **Package Weight** field is 1.5 LB, it is reset to the minimum weight of 2.20462262 LB. Some parcel carriers have minimum weight requirements. Setting this policy to the parcel carrier's minimum acceptable weight enables you to properly manifest parcels with the carrier.

### Workstation <_WS-XX_> scan by work reference number policy

The Workstation <_WS-XX_> scan by work reference number (MANPKGOPR/<_WS-XX_>/SCANNING-BY-WORK-REFERNCE) policy controls a specific workstation's settings for whether a parcel can be identified by a work reference number when the Manifest Package Operations window is started.

You can configure the following DETAILS fields for this policy:

-   **Return Number 1**: Specifies whether the **Work Reference** field will be available on the Manifest Package Operations window. The following values are valid:
    -   **0:** The field is not available. Typically, you use this setting when all or most of your manifesting workstations are used to process individually picked cases.
    -   **1**: The field is available. Typically, you use this setting when all or most of your manifesting workstations are used to process loads of cases so that the user can scan the work reference rather than each individual case.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
