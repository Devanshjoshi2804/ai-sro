---
title: "Currency"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/admin/currency.htm"
source: "/content/admin/currency.htm"
toc_path:
  - "Administration"
  - "System Administrator"
  - "Configuration"
  - "Internationalization"
  - "Currency"
sections:
  - "Add or modify a currency"
  - "Delete a currency or conversion rate"
  - "Currency fields"
images: []
source_sha1: 3cef8f3e3e00a2f5f829a6a85640a03ebe7e5bee
---
# Currency

Currency defines the type of money that is used in a particular country or territory (as identified by an ISO-4217 code). A currency is associated with each locale. Currencies are used during data entry of monetary values; for example, when a user enters a cost value (such as 10), the user can select a currency to qualify the value.

You can also define a conversion (exchange) rate to support the conversion of values from one currency to another. If a user enters a cost value in one currency, then if a conversion rate is available, a user associated with another locale can view the cost value converted to their currency.

You use the Currency page to define currency information for the different currency types with which you work.

## Add or modify a currency

1.  Select **System Administrator > Configuration > ** **Internationalization > Currency**.
2.  To add or modify a currency:
    1.  Perform one of the following tasks:
        -   To add a new currency, from the **Actions** drop-down list, select **Add**.
        -   To copy a currency, in the grid select the check box on the row of the currency, and then from the **Actions** drop-down list, select **Copy**.
        -   To modify a currency, in the grid select the check box on the row of the currency, and then from the **Actions** drop-down list, select **Edit**.
    2.  Enter information in the [Currency fields](#Currency_fields).
    3.  Click **Save**. A confirmation message is displayed.
    4.  Click **OK**.
3.  To add or modify a conversion rate:
    1.  Select the check box next to the currency for which to add the rate.
    2.  Under **CONVERSION RATES**, perform one of the following tasks:
        -   To add a new conversion rate, from the **Actions** drop-down list, select **Add**.
        -    To copy a conversion rate, in the grid select the check box next to the rate, and then from the **Actions** drop-down list, select **Copy**.
        -    To modify a conversion rate, in the grid select the check box next to the rate, and then from the **Actions** drop-down list, select **Edit**.
    3.  In the **Conversion Rate** field, enter the rate.
    4.  In the **Effective Date** field, select the date and time the conversion rate is valid.
    5.  In the **Destination Currency Code** field, select the currency to which the source currency is converted using the specified rate.
    6.  Click **Save**. A confirmation message is displayed.
    7.  Click **OK**.

## Delete a currency or conversion rate

1.  Select **System Administrator > Configuration > ** **Internationalization > Currency**.
2.  Perform one of the following tasks:
    -   To delete a currency, in the grid, select the check box on the row of the currency.
    -   To delete a conversion rate:
        1.  In the grid, select the check box on the row of the currency.
        2.  Under **CONVERSION RATES**, select the check box next to the conversion rate.
3.  From the **Actions** drop-down list, select **Delete**. A confirmation message is displayed.
4.  Click **OK**.

## Currency fields

 
| Field | Description |
| --- | --- |
| **Currency Code** | Unique identifier that represents a currency. The value is the alphabetic portion of the ISO 4217 currency code. For example, the U.S. dollar is represented by the code USD. |
| **Description** | Description of the currency and the full ISO 4217 three-letter alphabetic code and three-digit numeric code that represents the currency. For example, USA dollar (USD, 840). |
| **No. of digits after decimal** | Number of digits that are displayed to the right of the currency decimal point (separator). |
| Currency Decimal Point | Character used to indicate the decimal separator. |
| Currency Grouping Character | Character used as the digit grouping separator. For example, a comma is used for the U. S. dollar to indicate the thousands place (1,000.00). |
| Currency Grouping Style | Number of digits that are grouped between each separator for the digits that display to the left of the decimal separator. A three-digit grouping (or thousands place) is commonly used. However, some currencies may use only two digits. |
| Currency Symbol | Symbol used to represent a currency, such as the U.S. dollar sign ($), Euro (€), or Japanese yen (¥). |
| Positive Currency Format | Format that represents how a positive value is displayed in the currency. For example, ($n), where $ is the currency symbol and n represents the value. |
| Negative Currency Format | Format that represents how a negative value is displayed in the currency. For example, ($n), where $ is the currency symbol and n represents the value. |
| Enabled | Specifies whether the currency is available for use in the application. |
| Group Name | Identifier used by Blue Yonder product teams to indicate the product group that was responsible for loading data (in a particular row of a table). For example, standard group names include dcs\_data, mcs\_data, sal\_data, and so on. This field is display only. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
