---
title: "Host measurement unit policies"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/policies/host_measurement_unit_policies.htm"
source: "/content/policies/host_measurement_unit_policies.htm"
toc_path:
  - "Administration"
  - "System Administrator"
  - "Configuration"
  - "Policy"
  - "Host measurement unit policies"
sections:
  - "Host area measurement unit policy"
  - "Host linear measurement unit policy"
  - "Host mass measurement unit policy"
  - "Host temperature measurement unit policy"
  - "Host volumetric measurement unit policy"
images: []
source_sha1: 98a67b39b6ec3b9183ee5e9fc2c72b866b964a87
---
# Host measurement unit policies

The Host measurement unit policies define the measurement units that your Blue Yonder application expects to receive from another Blue Yonder application or host system. You only need to set these policies when the measurement units you expect from an external application are different from those defined in the application's System units policies.

Once you set the Host measurement unit policies, the following conversions will take place:

-   For inbound transactions, measurement units received from Integrator are converted to the measurement units that are defined in the System units policies.
-   For outbound transactions, measurement units sent to Integrator are converted to the measurement units that are defined in the Host measurement units policies.

The following measurement unit categories are available:

-   Area
-   Linear (length)
-   Mass (weight)
-   Temperature
-   Volumetric

**Note**: The measurement unit specified on the Locales page in the web client determines the measurement unit type that is displayed throughout your Blue Yonder application. See [Locales](../internationalization/locales.md).

You use Policy Maintenance or Policy Maintenance - Override to maintain Host measurement units policies.

## Host area measurement unit policy

The Host area measurement unit (HOST-MU/DEFAULT/AREA) policy determines the measurement unit for area that you expect from the selected Integrator application. When the measurement unit for area is received from Integrator, it is converted to the measurement unit that is defined for the System units/area measurement (SYS-MU/AREA/DEFAULT) policy. When your application sends a measurement for area, it is converted to the measurement unit that Integrator uses, as defined by the Host area measurement unit policy.

You can configure the following DETAILS fields for this policy:

-   **Return String 1**: Variable name of the area measurement unit field that is included in the integration transactions from Integrator. A measurement unit field is a field that displays a value that must be qualified by a measurement unit, such as (for area measurements) square inches or square meters.
    -   If you select a specific measurement unit field name, the setting in the **Return String 2** field applies to that field name only.
    -   If you select DEFAULT, the setting in the **Return String 2** field applies to all area measurement unit field names.
-   **Return String 2**: The measurement unit you expect from the selected system, which is converted to the measurement unit for area defined by the System units/area measurement policy.

## Host linear measurement unit policy

The Host linear measurement unit (HOST-MU/DEFAULT/LINEAR) policy determines the measurement unit for length that you expect from the Integrator. When the measurement unit for length is received from Integrator, it is converted to the measurement unit that is defined for the System units/linear measurement (SYS-MU/LINEAR/DEFAULT) policy. When your application sends a measurement for length, it is converted to the measurement unit that Integrator uses, as defined by the Host linear measurement unit policy.

You can configure the following DETAILS fields for this policy:

-   **Return String 1**: Variable name of the linear measurement unit field that is included in the integration transactions from Integrator. A measurement unit field is a field that displays a value that must be qualified by a measurement unit, such as (for linear measurements) inches or meters.
    -   If you select a specific measurement unit field name, the setting in the **Return String 2** field applies to that field name only.
    -   If you select DEFAULT, the setting in the **Return String 2** field applies to all linear measurement unit field names.
-   **Return String 2**: The measurement unit you expect from the selected system, which is converted to the measurement unit for linear defined by the System units/linear measurement policy.

## Host mass measurement unit policy

The Host mass measurement unit (HOST-MU/DEFAULT/MASS) policy determines the measurement unit for weight that you expect from Integrator. When the measurement unit for weight is received from Integrator, it is converted to the measurement unit that is defined for the System units/weight measurement (SYS-MU/MASS/DEFAULT) policy. When your application sends a measurement for weight, it is converted to the measurement unit that Integrator uses, as defined by the Host mass measurement unit policy.

You can configure the following DETAILS fields for this policy:

-   **Return String 1**: Variable name of the mass measurement unit field that is included in the integration transactions from Integrator. A measurement unit field is a field that displays a value that must be qualified by a measurement unit, such as (for mass measurements) ounce or pound.
    -   If you select a specific measurement unit field name, the setting in the **Return String 2** field applies to that field name only.
    -   If you select DEFAULT, the setting in the **Return String 2** field applies to all area measurement unit field names.
-   **Return String 2**: The measurement unit you expect from the selected system, which is converted to the measurement unit for mass defined by the System units/mass measurement policy.

## Host temperature measurement unit policy

The Host temperature measurement unit (HOST-MU/DEFAULT/TEMPERATURE) policy determines the measurement unit for temperature that you expect from the selected Integrator system. When the measurement unit for temperature is received from the Integrator system, it is converted to the measurement unit that is defined for the System units/temperature measurement (SYS-MU/TEMPERATURE/DEFAULT) policy. When your system sends a measurement for temperature, it is converted to the measurement unit that the Integrator system uses, as defined by the Host temperature measurement unit policy.

You can configure the following DETAILS fields for this policy:

-   **Return String 1**: Variable name of the temperature measurement unit field that is included in the integration transactions from Integrator. A measurement unit field is a field that displays a value that must be qualified by a measurement unit, such as (for temperature measurements) Fahrenheit or Celsius.
    -   If you select a specific measurement unit field name, the setting in the **Return String 2** field applies to that field name only.
    -   If you select DEFAULT, the setting in the **Return String 2** field applies to all temperature measurement unit field names.
-   **Return String 2**: The measurement unit you expect from the selected system, which is converted to the measurement unit for area defined by the System units/temperature measurement policy.

## Host volumetric measurement unit policy

The Host volumetric measurement unit (HOST-MU/DEFAULT/VOLUME) policy determines the measurement unit for volume that you expect from the selected Integrator system. When the measurement unit for volume is received from the Integrator system, it is converted to the measurement unit that is defined for the System units/volume measurement (SYS-MU/VOLUME/DEFAULT) policy. When your application sends a measurement for volume, it is converted to the measurement unit that the Integrator system uses, as defined by the Host volumetric measurement unit policy.

You can configure the following DETAILS fields for this policy:

-   **Return String 1**: Variable name of the volume measurement unit field that is included in the integration transactions from Integrator. A measurement unit field is a field that displays a value that must be qualified by a measurement unit, such as (for volume measurements) cubic inches or cubic meters.
    -   If you select a specific measurement unit field name, the setting in the **Return String 2** field applies to that field name only.
    -   If you select DEFAULT, the setting in the **Return String 2** field applies to all volume measurement unit field names.
-   **Return String 2**: The measurement unit you expect from the selected system, which is converted to the measurement unit for area defined by the System units/volume measurement policy.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
