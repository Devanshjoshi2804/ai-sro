---
title: "Measurement Units"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/admin/measurement_units.htm"
source: "/content/admin/measurement_units.htm"
toc_path:
  - "Administration"
  - "System Administrator"
  - "Configuration"
  - "Internationalization"
  - "Measurement Units"
sections:
  - "Measurement unit categories"
  - "Measurement unit conversion"
  - "Measurement unit type defaults"
  - "Measurement unit system"
  - "Add or modify a measurement unit"
  - "Delete a measurement unit"
  - "Measurement Units fields"
images: []
source_sha1: c52e41f94fbeacd951437ff6886059ebbcbcd323
---
# Measurement Units

A measurement unit is a standard used for determining quantity, capacity, or dimension. For example, an inch is a standard measurement unit representing a linear distance, and multiple inches can be used to express linear distance greater than an inch. Measurement units are used to quantify the following measurements:

-   Area
-   Distance
-   Linear
-   Mass (weight)
-   Temperature
-   Velocity
-   Volume

The application provides measurement units in the International System of Measurements (Metric) and the United States System of Measurement systems. The Metric system includes units such as centimeter, meter, gram, and kilogram, among others; the U.S. system includes units such as inch, foot, pound, and ton, among others.

## Measurement unit categories

A measurement unit category is used to classify a measurement unit type by size (small, medium, and large) and kind (area, distance, linear, mass, temperature, and volumetric). A measurement unit category is used in the configuration of unit of measure type fields that are displayed. The measurement unit category limits the list of values available for the user to select. For example, you can configure a field that captures the length of a carton with the Small Linear Measurement category, so that the user can select from units such as inches, centimeters, decimeters, and millimeters. You can also configure a field that captures distance from one city to another with the Distance Measurement category, so that the user can select from units such as miles and kilometers.

Each category is associated with a system measurement unit. The system measurement unit is the measurement unit to which values in this category are converted for storage in the database and for communication with the host. A system measurement unit is defined for each type of measure (area, distance, linear, mass, temperature, and volume) in the System Units (SYS-MU) policies. The following table describes the different measurement unit categories and the associated base unit used for conversion.

   
| Measurement unit category | System measurement unit | Use | Examples |
| --- | --- | --- | --- |
| Small Linear Measurement | Inch | Measurement of straight line distances | Centimeter, millimeter, and decimeter |
| Medium Linear Measurement | Inch | Measurement of straight line distances | Foot, meter, and yard |
| Distance Measurement | Mile | Measurement of straight line distances | Mile and kilometer |
| Small Area Measurement | Square Inch | Measurement of a surface or piece of land | Square centimeter, square millimeter, and square decimeter |
| Medium Area Measurement | Square Inch | Measurement of a surface or piece of land | Square foot, square meter, and square yard |
| Large Area Measurement | Square Mile | Measurement of a surface or piece of land | Square mile and square kilometer |
| Small Volumetric Measurement | Cubic Inch | Measurement of space occupied by a three-dimensional object or region | Cubic centimeter, cubic millimeter, and cubic decimeter |
| Medium Volumetric Measurement | Cubic Inch | Measurement of space occupied by a three-dimensional object or region | Cubic foot, cubic meter, and cubic yard |
| Large Volumetric Measurement | Cubic Mile | Measurement of space occupied by a three-dimensional object or region | Cubic mile and cubic kilometer |
| Small Mass (Weight) Measurement | Ounce | Measurement of the heaviness of an object | Gram and ounce |
| Medium Mass (Weight) Measurement | Ounce | Measurement of the heaviness of an object | Kilogram and pound |
| Large Mass (Weight) Measurement | Ounce | Measurement of the heaviness of an object | Long and short ton, hundredweight, and tonne |
| Temperature Measurement | Celsius | The intensity of heat present in an object or space as expressed in a comparative scale and shown by a thermometer | Celsius, fahrenheit, and kelvin |

## Measurement unit conversion

In the application, fields that are configured with a field type of Unit of Measure are displayed in the default measurement unit type defined for the measurement unit category of the field. This relationship is defined in Measurement Units. You select a measurement unit system for a locale that provides the default measurement unit types that can be displayed for each measurement unit category.

Measurement unit values are converted when the following situations occur:

-   **A user selects a unit from a unit of measure field drop-down list**. For example, if the measurement unit category of the field is Small Linear Measurement and the default unit type is Inch, the value for the field is displayed in inches. The user can view the value for that field in one of the other units defined for the Small Linear Measurement category displayed in the drop-down list. The Small Linear Measurement category includes units from both the International System of Measurements (Metric) and the United States System of Measurements. If a user is viewing a value of 1 in. and selects cm, the application converts and displays the value in 2.54 cm. This selection is not saved. When the user views that same field in a new session, the value is displayed in the default value of inch.
-   **The default unit types defined for the locale belong to a different measurement unit system than the unit types defined for storing values in the database**. For example, if the locale is configured with the International System of Measurements (Metric), and the system measurement units (saved in the SYS-MU policies) belong to the United States System of Measurements, a conversion is required to display the values. Using the example of the Small Linear Measurement, the default unit type defined on the locale is centimeter and the system measurement unit is inch. When a user enters a value in a field, such as 2.54 cm, the value is converted to and saved in the database as 1 in. When the user views that same field in a new session, the stored value of 1 in. is retrieved and converted to 2.54 cm for the displayed value.

The measurement unit conversion calculation is based on details defined in Measurement Units including the measurement unit category, system measurement unit, and conversion factors.

The following table shows the conversions of four small linear measurement units that use inch as the system measurement unit.

 
| Measurement unit type | Conversion |
| --- | --- |
| Inch | 1 inch = 1 inch |
| Decimeter | 1 decimeter = 3.9370078 inches |
| Centimeter | 1 centimeter = 0.3937008 inch |
| Millimeter | 1 millimeter = 0.03937008 inch |

**IMPORTANT**: This conversion calculation is for display purposes only. Values are stored in the database in the system measurement unit.

## Measurement unit type defaults

Once measurement units are defined, you can define a measurement unit default for each measurement unit category for each locale. This is the measurement unit in which values are displayed (by default).

For example, for the US\_ENGLISH locale, you can select the United States System of Measurement and define inch as the measurement unit default for the Small Linear Measurement category. For the FRENCH locale, you can select the International System of Measurements (Metric), and define decimeter as the measurement unit type default for the Small Linear Measurement category.

You use the **Units** tab in Locale Maintenance to define measurement unit defaults.

**IMPORTANT**: Locale Maintenance is an SCE client window. For changes made in Locale Maintenance to take effect, you must exit the client and then log in again.

## Measurement unit system

The application provides the International System of Measurements (Metric), and United States System of Measurements measurement unit systems. In the application, one measurement unit system is assigned to each locale. The measurement unit system and the default units assigned on the **Units** tab in Locale Maintenance determine the measurement unit type that is displayed throughout your Blue Yonder  application.

For example, the United States System of Measurement is assigned to the US\_ENGLISH locale. Fields displaying linear measurement values are displayed in the default units defined for the U.S. system, such as inches and feet. If you change the measurement unit system of the locale to the International System of Measurements (Metric), the values displayed on the user interface are the default units defined for the metric system, such as centimeters and meters.

You use the **Locales page** to assign a measurement unit system to a locale.

## Add or modify a measurement unit

1.  Select **System Administrator > Configuration > ** **Internationalization > Measurement Units**.
2.  Perform one of the following tasks:

-   To add a measurement unit, from the **Actions** drop-down list, select **Add**.
-   To copy a measurement unit, in the grid select the check box on the row of the measurement unit, and then from the **Actions** drop-down list, select **Copy**.
-   To modify a measurement unit, in the grid select the check box on the row of the measurement unit, and then from the **Actions** drop-down list, select **Edit**.

4.  Enter information in the [Measurement Units fields](#Measurement_Units_fields).
5.  Click **Save**. A confirmation message is displayed.
6.  Click **OK**.
    

## Delete a measurement unit

1.  Select **System Administrator > Configuration > ** **Internationalization > Measurement Units**.
2.  In the grid, select the check box on the row of the measurement unit.
3.  From the **Actions** drop-down list, select **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Measurement Units fields

 
| Field | Description |
| --- | --- |
| Measurement Unit Types | Name of the type of measurement unit. |
| **Measurement Unit Short Description** | Standard abbreviation for the measurement unit. |
| **Measurement Unit Description** | Meaningful description of the measurement unit type. |
| **Measurement Unit System** | Value that represents the system to which the measurement unit belongs.<br>-   • **International System of Measurements (Metric) (M)**: The measurement unit belongs to the metric system, which includes units such as meters and centimeters.
<br>-   • **United States System of Measurements (U)**: The measurement unit belongs to the U.S. system, which includes units such as yards and inches. |
| Measurement Unit Categories | Value that groups the measurement unit type based on size and kind of measurement, such as small, medium, and large area, volumetric, or mass measurements. A category is used, in the configuration of a field in an application, to limit the selection of measurement units to a list relevant to what is being measured, such as inches and decimeters for a carton length field, and miles and kilometers for a distance field. |
| Unit Category's System Measurement Unit | Measurement unit to which the values for this kind of measurement are converted, if necessary, and stored in the database. This value is defined by the System Units (SYS-MU) policies, which let you configure each kind of measurement (area, distance, linear, temperature, volume, and weight) with a measurement unit type. |
| Conversion Factor Numerator | Value that, when divided by the conversion factor denominator, is equivalent to one unit of the unit category's system measurement unit. For example, if you are maintaining a unit type of foot and the unit category's system measurement unit is inch, the conversion numerator should be 12, because there are 12 inches in 1 foot. |
| Conversion Factor Denominator | Value that, when divided into the conversion factor numerator, equals the numerical value that is equivalent to one unit of the defined unit category's system measurement unit. For example, if you are maintaining a unit type of foot and the unit category's system measurement unit is inch, this value is 1 because there are 12 inches in 1 foot. This value should be saved as 1 to avoid unexpected results. When the application processes the equation, the numerator is divided by 1, therefore, maintaining its original value. |
| Enabled | Specifies whether the measurement unit type is available for use in your application. |
| Display Precision | Value that specifies the number of decimal places to which the measurement value is rounded. All measurements displayed as this unit type are displayed only as the rounded value. A value of -1 in this field specifies that the measurement value is not rounded. Rounding values to the specified display precision only affects the display of the value; the actual full decimal point value is stored in the database. |
| Host Measurement Unit Code | Code for the measurement unit type that the application uses in transactions to and from the host. This value is not available for selection in your application; it only used to represent this measurement unit to a host system. |
| UN/CEFACT Code | Common code value used by the United Nations Centre for Trade Facilitation (UN/CEFACT) for the measurement unit type. |
| Absolute Group | An identifier used by Blue Yonder product teams to indicate the product group that was responsible for loading data (in a particular row of a table). Standard group names include dcs\_data, mcs\_data, and sal\_data. This field is display only. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
