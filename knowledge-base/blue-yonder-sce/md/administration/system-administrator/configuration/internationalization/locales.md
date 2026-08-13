---
title: "Locales"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/admin/locales.htm"
source: "/content/admin/locales.htm"
toc_path:
  - "Administration"
  - "System Administrator"
  - "Configuration"
  - "Internationalization"
  - "Locales"
sections:
  - "Locale IDs"
  - "Add or modify a locale"
  - "Delete a locale or locale parameters"
  - "Locale fields"
  - "Locale (Params) fields"
images: []
source_sha1: 9f7479518fc9ba1e7ee1c84d5fd517b42e94f01d
---
# Locales

A locale defines attributes for a language that affect how information is displayed in the application. When you set up a locale, you provide the following attributes:

-   Locale ID
-   Oracle national language support (NLS) settings
-   Operating system locale IDs
-   Linear, volume, and weight measurement units
-   True, false, and toggle keyboard character values
-   Number, currency, and date and time formats
-   Voice language code

## Locale IDs

Internationalization refers to the application's ability to operate in different languages and regions of the world. This includes displaying text in the appropriate language, and managing culture-specific features such as address formats, dimensions, dates, and times.

All of the application's configurable language attributes are defined in locales, which are uniquely identified by a locale ID.

All application users have a unique user configuration, which includes their locale ID. When a user logs in, the application determines the user's locale ID, and then displays the attributes that are appropriate for the user's language and territory.

You use the Locales page to set up and maintain locales.

## Add or modify a locale

1.  Select **System Administrator > Configuration > ** **Internationalization > Locales**.
2.  Perform one of the following tasks:
    -   To add a locale, from the **Actions** drop-down list, select **Add**.
    -   To copy a locale, in the grid select the check box next to the locale ID, and then from the **Actions** drop-down list, select **Copy**.
    -   To modify a locale, in the grid select the check box next to the locale ID, and then from the **Actions** drop-down list, select **Edit**.
3.  Enter information in the [Locale fields](#Locale_fields).
4.  Click **Save**. A confirmation message is displayed.
5.  Click **OK**.
6.  To add or modify locale parameters:
    1.  In the grid, select the check box next to the locale ID for which to add parameters.
    2.  Under **LOCALE PARAMS**, perform one of the following tasks:
        -   To add new parameters, from the **Actions** drop-down list, select **Add**.
        -    To modify parameters, in the grid select the check box next to the locale ID, and then from the **Actions** drop-down list, select **Edit**.
    3.  Enter information in the [Locale (Params) fields](#Locale_\(Params\)_fields).
    4.  Click **Save**. A confirmation message is displayed.
    5.  Click **OK**.

## Delete a locale or locale parameters

1.  Select **System Administrator > Configuration > ** **Internationalization > Locales**.
2.  Perform one of the following tasks:
    -   To delete a locale ID, in the grid, select the check box next to the locale ID.
    -   To delete locale parameters for a locale ID:
        1.  In the grid, select the check box next to the locale ID.
        2.  Under **LOCALE PARAMS**, select the check box next to the locale ID.
3.  From the **Actions** drop-down list, select **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Locale fields

 
| Field | Description |
| --- | --- |
| Locale ID | Identifier for a locale. A locale defines the attributes for a language that affect how information is displayed in the application. |
| Description | Meaningful description of the locale. |
| NLS\_LANGUAGE Setting | The Oracle national language support (NLS) language for the application server instance database, such as AMERICAN or SPANISH. See the information on the NLS\_LANGUAGE parameter in the [Oracle documentation](https://docs.oracle.com/cd/B28359_01/server.111/b28298/ch3globenv.htm#i1006575). |
| NLS\_SORT Setting | The Oracle national language support (NLS) sorting approach used for the application server instance database, such as BINARY or a linguistic sort name. See the information on the NLS\_SORT parameter in the [Oracle documentation](https://docs.oracle.com/cd/B28359_01/server.111/b28298/ch3globenv.htm#i1006575). |
| Unix Server Locale | The Linux server locale. The POSIX locale, also referred to as the C locale, is the Linux default locale value. |
| MS-Windows Client LCID | Language Code Identifier (LCID) used by the Microsoft Windows client. See the information on LCIDs in the [Microsoft documentation](https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-lcid/db95f4c3-1470-422c-af4a-5bb161b2f848). |
| Voice Language Code | A 5-digit value that represents a language and country, for example, EN\_US for English\_United States and ES\_ES for Spanish\_Spain. The voice language code is defined as part of the hardware settings used for voice device configurations. |
| Group Name | Identifier used by Blue Yonder product teams to indicate the product group that was responsible for loading data (in a particular row of a table). For example, standard group names include dcs\_data, mcs\_data, sal\_data, and so on. This field is display only. |
| Country Name | Name or code name of the country. |
| Short Description | Brief description of the locale. |
| NLS\_TERRITORY Setting | The Oracle national language support (NLS) territory for the application server instance database, such as FRANCE or MEXICO. See the information on the NLS\_TERRITORY parameter in the [Oracle documentation](https://docs.oracle.com/cd/B28359_01/server.111/b28298/ch3globenv.htm#i1006575). |
| Measurement Unit System | Measurement unit system assigned to the locale. The measurement unit system determines the measurement unit type that is displayed throughout your Blue Yonder application.<br>-   • **M**: International System of Measurements (Metric), which includes units such as meters and centimeters.
<br>-   • **U**: United States System of Measurements, which includes units such as yards and inches. |
| RF Server Locale | The MTF server locale. The POSIX locale, also referred to as the C locale, is the MTF server locale default value. |
| MS-Windows Server LCID | The Language Code Identifier (LCID) used by the Microsoft Windows server. See the information on LCIDs in the [Microsoft documentation](https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-lcid/db95f4c3-1470-422c-af4a-5bb161b2f848). |
| Enabled | Specifies whether the locale is available for use in your application. |

## Locale (Params) fields

 
| Field | Description |
| --- | --- |
| Locale ID | Identifier for a locale. A locale defines the attributes for a language that affect how information is displayed in the application. |
| True-Keyboard Char | Keyboard character used to indicate a yes (true) response in the RF or mobile device screen. |
| Grouping Character | Character used as the digit grouping separator. Digital grouping is used, for example, to separate thousands from hundreds. For example, 1,000,000. |
| Decimal Point | Character used to indicate the decimal separator. |
| Short Date Pattern | Format for short date fields, where the following standard formats are used:<br>-   • M/d/yyyy
<br>-   • MM/dd/yyyy
<br>-   • M/d/yy
<br>-   • MM/dd/yy
<br>-   • d/M/yy
<br>-   • dd/MM/yyyy
<br>-   • d/M/yy
<br>-   • dd/MM/yy
<br > Where:<br>-   • **d**: One-digit or two-digit day number.
<br>-   •
    
    **dd**: Two-digit day number. A single-digit day value is preceded by a 0.
    
    <br>
<br>-   • **M**: One-digit or two-digit month number.
<br>-   • **MM**: Two-digit month number. A single-digit month value is preceded by a 0.
<br>-   • **yy**: Last two digits of the year (2021 is displayed as **21**).
<br>-   •
    
    **yyyy**: Full year (2021 is displayed as **2021**).
    
    <br> |
| Short Time Pattern | Format for short time fields, where the following standard formats are used:<br>-   • h:mm tt
<br>-   • H:mm
<br > Where:<br>-   •
    
    **h**: One-digit or two-digit hour in a 12-hour format.
    
    <br>
<br>-   • **H**: One-digit or two-digit hour in a 24-hour format.
<br>-   •
    
    **mm**: Two-digit minute. Single-digit values are preceded by a 0.
    
    <br>
<br>-   •
    
    **tt**: Two-letter A.M. or P.M. abbreviation (A.M. is displayed as **AM**).
    
    <br> |
| AM Symbol | Characters used to indicate that a time is before noon, such as AM, when time is displayed in a 12-hour format. |
| Time Separator | Character used to separate time values. |
| First Day of Week | Value that indicates the first day of the week.<br>-   • **0**: The first day of week is specified by the default system settings.
<br>-   • **1**: Sunday
<br>-   • **2**: Monday
<br>-   • **3**: Tuesday
<br>-   • **4**: Wednesday
<br>-   • **5**: Thursday
<br>-   • **6**: Friday
<br>-   • **7**: Saturday |
| Positive Sign Position | Format of a positive currency value as indicated by one of the following options:<br>-   • **0**: Parentheses surround the quantity and the currency symbol.
<br>-   • **1**: The positive sign precedes the quantity and the currency symbol.
<br>-   • **2**: The positive sign succeeds the quantity and the currency symbol.
<br>-   • **3**: The positive sign immediately precedes the currency symbol.
<br>-   • **4**: The positive sign immediately succeeds the currency symbol.
<br > **Note**: Values 1 through 4 require that the **Positive Sign** field contain a value. |
| **Positive Sign** | Character used to indicate a positive number. |
| **Month Display Type** | Value that indicates if a month is displayed in the application using numbers (N) or letters . |
| False-Keyboard Char | Keyboard character used to indicate a no (false) response in the RF or mobile device screen. |
| Grouping Style | Defines the number of digits used in digital grouping. Digital grouping is used to group numeric values to the left of the decimal point, for example, to separate thousands from hundreds. For example, 1,000,000 has a **Grouping Style** value of 3. |
| Currency Code | Unique identifier that represents a currency. The value is the alphabetic portion of the ISO 4217 currency code. For example, the U.S. dollar is represented by the code USD. |
| Long Date Pattern | Format for long date fields, where the following standard formats are used:<br>-   • dddd, MMMM, dd, yyyy
<br>-   • MMMM dd, yyyy
<br>-   • ddd,MMM dd, yyyy
<br>-   • MMM dd, yyy
<br>-   • dddd, dd MMMM, yyyy
<br>-   • dd MMMM, yyyy
<br>-   • ddd, dd MMM, yyyy
<br>-   • dd MMM, yyyy
<br > Where:<br>-   •
    
    **dd**: Two-digit day number. A single-digit day value is preceded by a 0.
    
    <br>
<br>-   • **ddd**: Three character day-of-the-week abbreviation.
<br>-   • **dddd**: The full day-of the-week name.
<br>-   • **MMM**: The three-character month abbreviation.
<br>-   • **MMMM**: The full month name.
<br>-   •
    
    **yyyy**: Full year (2021 is displayed as **2021**).
    
    <br> |
| Long Time Pattern | Format for long time fields, where the following standard formats are used:<br>-   • h:mm:ss tt
<br>-   • H:mm:ss
<br > Where:<br>-   • **h**: The one-digit or two-digit hour in a 12-hour format.
<br>-   • **H**: The one-digit or two-digit hour in a 24-hour format.
<br>-   •
    
    **mm**: Two-digit minute. Single-digit values are preceded by a 0.
    
    <br>
<br>-   • **ss**: The two-digit seconds. Single-digit values are preceded by a 0.
<br>-   •
    
    **tt**: Two-letter A.M. or P.M. abbreviation (A.M. is displayed as **AM**).
    
    <br> |
| PM Symbol | Characters used to indicate that a time is after noon, such as PM, when time is displayed in a 12-hour format. |
| Date Separation Character | Character used to separate date values. |
| Calendar Week Rule | Value that indicates the day of the year when the first week of the year starts.<br>-   • **0**: The first week of the year starts on the first day of the year and ends before the following designated first day of the week.
<br>-   • **1**: The first week of the year starts on the first occurrence of the designated first day of the week on or after the first day of the year.
<br>-   • **2**: The first week of the year is the first week with four or more days before the designated first day of the week. |
| Negative Sign Position | Format of a negative currency value as indicated by one of the following options:<br>-   • **0**: Parentheses surround the quantity and the currency symbol.
<br>-   • **1**: The negative sign precedes the quantity and the currency symbol.
<br>-   • **2**: The negative sign succeeds the quantity and the currency symbol.
<br>-   • **3**: The negative sign immediately precedes the currency symbol.
<br>-   • **4**: The negative sign immediately succeeds the currency symbol.
<br > **Note**: Values 1 through 4 require that the **Negative Sign** field contain a value. |
| Negative Sign | Character used to indicate a negative number. |
| Group Name | Identifier used by Blue Yonder product teams to indicate the product group that was responsible for loading data (in a particular row of a table). For example, standard group names include dcs\_data, mcs\_data, sal\_data, and so on. This field is display only. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
