---
title: "City Postal Codes"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/admin/city_postal_codes.htm"
source: "/content/admin/city_postal_codes.htm"
toc_path:
  - "Administration"
  - "System Administrator"
  - "Configuration"
  - "Internationalization"
  - "City Postal Codes"
sections:
  - "Add or modify a city postal code"
  - "Delete a city postal code"
  - "City Postal Code fields"
images: []
source_sha1: 03510298f7d4829761871c7abc9476a2df752688
---
# City Postal Codes

A city postal code is a valid country, state, city, and postal code combination that can be used for an address in the application. Geographical data files, which provide a complete set of valid country, state, city, and postal code values for the United States and Canada are available to load during a Blue Yonder installation. For other countries, you can enter city postal codes manually using the City Postal Code page.

If a valid city postal code becomes invalid as a result of loading updated geographical data, the **Invalid Flag** check box is automatically selected for the city postal code. In addition, the **Invalid Date** field displays the date on which the city postal code became invalid.

## Add or modify a city postal code

1.  Select **System Administrator > Configuration > ** **Internationalization > City Postal Codes**.
2.  Perform one of the following tasks:
    -   To add a new city postal code, from the **Actions** drop-down list, select **Add**.
    -   To copy a city postal code, in the grid select the check box on the row of the postal code, and then from the **Actions** drop-down list, select **Copy**.
    -   To modify a city postal code, in the grid select the check box on the row of the postal code, and then from the **Actions** drop-down list, select **Edit**.
3.  Enter information in the [City Postal Code fields](#City_Postal_Code_fields).
4.  Click **Save**. A confirmation message is displayed.
5.  Click **OK**.

## Delete a city postal code

1.  Select **System Administrator > Configuration > ** **Internationalization > City Postal Codes**.
2.  In the grid, select the check box on the row of the postal code.
3.  From the **Actions** drop-down list, select **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## City Postal Code fields

 
| Field | Description |
| --- | --- |
| **Country Name** | Name or code name of the country. |
| **City** | City for the postal code. |
| **Latitude** | Line of latitude for the postal code. Type the latitude in decimal format (for example, 40.269 and -75.317). This value is informational only. |
| **GMT Offset** | Positive or negative number indicating the difference in hours or fractional hours between the time zone and the Greenwich Mean Time/Coordinated Universal Time (GMT/UTC) time zone. |
| Invalid Flag | Specifies whether the city postal code definition is invalid. A city postal code definition can become invalid when updated geographical information is imported. |
| Absolute Group | An identifier used by Blue Yonder product teams to indicate the product group that was responsible for loading data (in a particular row of a table). Standard group names include dcs\_data, mcs\_data, and sal\_data. This field is display only. |
| State | State for the postal code. |
| Postal Code | Postal code value. |
| Longitude | Line of longitude for the postal code. Type the longitude in decimal format (for example, 40.269 and -75.317). This value is informational only. |
| Invalid Date | Date and time on which the city postal code definition became invalid. |
| Daylight Savings | Specifies whether this city postal code definition is a location that observes daylight savings time. |
| Custom Level | Value that differentiates customized data from standard data. Standard data is distributed with a customization level of 0 (zero). Customized data is assigned a higher customization level, usually in increments of 10. The MCS framework uses the customization level to determine which database entry to use and, as a result, takes the entry with the highest customization level. This field is display only. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
