---
title: "Variable Configuration"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/admin/variable_configuration.htm"
source: "/content/admin/variable_configuration.htm"
toc_path:
  - "Administration"
  - "System Administrator"
  - "Configuration"
  - "Variable Configuration"
sections:
  - "Variable names"
  - "Addon IDs"
  - "Custom date formats"
  - "Variable configuration setup tasks"
images: []
source_sha1: f01d0af8bf7dfa55a505c01b0df8e526f83e9fe7
---
# Variable Configuration

A variable configuration is the configuration of a field (such as a text box, list, or check box) that implements a variable name. The configuration defines the field label and other properties, as well as the context in which the configuration takes effect (such as on a specific SCE client window, on all SCE client windows, or on RF or mobile device screens).

You can use the following pages to maintain variable configurations:

-   **Catalog**: Define one or more message catalog entries for a new or existing variable name.
    
    **Note**: Variable names are also maintained on the Message Catalog page. See [Message Catalog](internationalization/message-catalog.md).
    
-   **Config**: Define the basic properties of a variable configuration, such as whether the variable configuration is enabled and visible, field type, and display settings.
-   **Defaults**: Define a default value for a field.
-   **Inputs**: Define the properties of a valid input value, such as maximum number of characters allowed.
-   **Validate**: Define how the data entered into a field is validated, including how often validation occurs and which command is used for validation.
-   **Valid Possibility**: Define a field as a drop-down list with values.
-   **Lookup**: Define a field as a lookup field, in which a user can access a lookup window or menu.

## Variable names

A variable name, as defined on the Catalog page or on Message Catalog, is a code that is used to represent a piece of fixed text (such as an SCE client window title, field label, or button label) that is displayed in the user interface.

Variable names are used to provide multi-language support (MLS). The implementation of a variable name, such as prtnum, can be configured in multiple ways to support translations or customizations, or to accommodate a specific user interface, such as an RF or mobile device screen.

For example, the standard product display text for the variable name prtnum is Item. If your facility refers to items as stock keeping units (SKUs), you can change the display text for prtnum to SKU.

The configuration associated with a variable name defines its properties, such as its appearance, data type, default values, input parameters, validation, valid possibilities, and whether a variable lookup is provided with the control. For example, you may want the reacod (reason code) field to use a different list of valid possibilities depending on the application in which it is displayed. To do this, you would create separate variable configurations for reacod, and select a different lookup ID (list of valid possibilities) for each. The configuration also defines the context (such as on SCE client windows or RF and mobile device screens) in which the variable configuration takes effect. Context is defined by addon ID variables. See [Addon IDs](#Addon_IDs).

## Addon IDs

An addon ID is a code that is used to identify a Blue Yonder component (such as a Blue Yonder application) or group of components (all Blue Yonder applications). An addon ID, when associated with a variable name or user-defined inventory attribute, provides a method for specifying the context in which the variable or attribute configuration takes effect.

For example, if you want the prtnum variable name to be displayed as Item on all SCE client windows in the application, you associate that value with the LES addon ID. If you want it to be displayed as Itm: on RF or mobile device screens, you associate that value with the RF addon ID.

The following table describes the base addon IDs and the context that each represents.

 
| Addon ID | Component |
| --- | --- |
| 3PL | Environments in which third-party logistics functionality is enabled |
| Customs | Environments in which customs functionality is enabled |
| LES | Global to all Blue Yonder components |
| LM | Warehouse Labor Management |
| RF | RF and mobile device screens |
| SEAMLES | Integrator |
| WM | Warehouse Management |

In addition to addon IDs, the following addon ID hook variables may be used, depending on the application policies (SYSTEM- INFORMATION/MISCELLANEOUS/ADDON\_ID\_HOOKS) that are enabled:

-   **Clients**: In a 3PL environment, if the CLIENT\_ID addon ID hook variable is enabled, then you can configure a variable configuration to take effect only with data related to a specific client.
-   **Client Groups**: In a 3PL environment, if the CLIENT\_GRP addon ID hook variable is enabled, then you can configure a variable configuration to take effect only with data related to a specific client group.
-   **Warehouses**: In a multi-warehouse environment, if the Warehouse ID addon ID hook variable is enabled, then you can configure a variable configuration to take effect only in a specific warehouse.
    
    **Note**: If you have Warehouse Management installed, you can use Policy Maintenance to enable addon IDs and addon ID hook variables.
    

Precedence defines which variable configuration is used when multiple variable configurations have been defined for a variable name, each with different addon IDs. Precedence is based on the addon IDs that are enabled in the application using the SYSTEM-INFORMATION/MISCELLANEOUS/ADDON\_ID policy, and the value for Sort Sequence that is defined for each return string (addon ID) in the policy.

For example, variable configurations for client ID fields are enabled and visible but are associated with the 3PL addon ID; therefore, in a standard non-3PL application, the client ID fields are hidden because the 3PL addon ID is not enabled. In a 3PL environment with the 3PL addon ID enabled, the client ID fields are visible (based on user authorization).

When an addon ID is enabled, the variable configuration takes effect, except when multiple addon IDs are enabled, and precedence is given to one variable configuration over another.

The following table provides an example of how the application determines which configuration to use when multiple addon IDs (A, B, and C) are enabled sequentially, and there are conflicting configurations for the same variable name.

**Note**: A weight is given to each addon ID in the application configuration from left to right. The first addon ID is given the highest weight and the last addon ID is given the lowest weight. The weight is a bitwise weight: (2^(n-1), 2^(n-2), ... 2^0, where n is the number of addon IDs. So, since A is the first of 3 addon IDs, the weight is 2^(3-1), or 2^2, which equals 4.

  
| Addon ID Enabled | Weight | Explanation |
| --- | --- | --- |
| LES | 0 | Matches any configuration, but is only used if no other matches occur. |
| A | 4 | Matches the first addon ID, therefore, has more weight than the other two. |
| B | 2 | Matches the second ID. |
| C | 1 | Matches the last ID. |
| A,B | 6 | Weighs more than A alone. |
| A,C | 5 | Would only be used if B did not match. |
| A,B,C | 7 | Would always be used if defined because all the IDs match. |
| B,C | 3 | Would only be used if A did not match. |
| C | 1 | Would only be used if A and B did not match. |
| A,B,C,D | \-1 | Would not be used because D does not exist in the application configuration. |

Based on this example, a variable configuration for a specific variable name that is enabled for A, B, and C is used over another configuration for the same variable name that is enabled for A, B, or C individually. In addition, variable configuration C, the lowest weighted configuration, is only used over another configuration for the same variable name if there are no other configurations defined for A or B, and variable configuration A and D is not used because D does not exist in the application.

## Custom date formats

A custom date format is a configuration that controls how date and time information is displayed for a field (variable name) that uses a date control; these include fields that capture a start date, end date, shipped date, completion date, and so on.

When you configure the display properties of a variable configuration or a user-defined inventory attribute that uses a date control, you can use date format codes to define the format in which the date and time information is displayed. For example, you would use FRMT=yymmdd to specify a two-digit year, a two-digit month, and a two-digit day.

For information on configuring a date format for variable configuration, see [Add or modify a variable configuration](variable-configuration/config.md).

The following table shows how the same date can be displayed in different formats.

 
| Code | Format |
| --- | --- |
| ddddMMMMddyyy | Friday January 15 2021 |
| yyMMdd | 210115 |
| yyddd | 21FRI |
| MMddyyy | 01152021 |

The following table lists the codes that control the format in which date and time is displayed.

 
| Codes | Description |
| --- | --- |
| d | One or two-digit day. One-digit values are not preceded by 0. |
| dd | Two-digit day. One-digit values are preceded by 0. |
| ddd | Three-character day-of-week abbreviation. |
| dddd | Full day-of-week name. |
| h | One or two-digit hour in 12-hour format. One-digit values are not preceded by 0. |
| hh | Two-digit hour in 12-hour format. One-digit values are preceded by 0. |
| H | One or two-digit hour in 24-hour format. One-digit values are not preceded by 0. |
| HH | Two-digit hour in 24-hour format. One-digit values are preceded by 0. |
| m | One or two-digit minute. One-digit values are not preceded by 0. |
| mm | Two-digit minute. One-digit values are preceded by 0. |
| M | One or two-digit month number. One-digit values are not preceded by 0. |
| MM | One or two-digit month number. One-digit values are preceded by 0. |
| MMM | Three-character month abbreviation. |
| MMMM | Full month name. |
| s | One or two-digit seconds. One-digit values are not preceded by 0. |
| ss | One or two-digit seconds. One-digit values are preceded by 0. |
| t | One-letter a.m./p.m. abbreviation (a.m. is displayed as A, p.m. is displayed as P). |
| tt | Two-letter a.m./p.m. abbreviation (a.m. is displayed as AM, p.m. is displayed as PM). |
| w | One or two-digit week number. One-digit values are not preceded by 0. |
| ww | One or two-digit week number. One-digit day values are preceded by 0. |
| y | One-digit year (2021 is displayed as "1"). |
| yy | Last two digits of the year (2021 is displayed as 21). |
| yyy | Full year (2021 is displayed as 2021). |

**Note**: The application calculates the decade for the single-year date code (y) using plus or minus 5 years, depending on whether looking back to arrive at a manufactured date or ahead to arrive at an expiration date.

## Variable configuration setup tasks

A variable configuration can be defined to implement a control, or changes to a control, in the SCE client, and RF and mobile device user interfaces. For example, a variable configuration is used to change the label that is displayed next to a control, or to prevent the control from being displayed. When you define a variable configuration, you can specify the context in which the configuration takes effect; that is, for a specific warehouse, client, client group, user, or role.

You must complete the following tasks to set up and implement a variable configuration:

1.  **Enable the addon IDs that can be used to control the context in which the variable configuration takes effect.**
    
    You use Policy Maintenance to configure the SYSTEM-INFORMATION/MISCELLANEOUS/ADDON\_ID and SYSTEM-INFORMATION/MISCELLANEOUS/ADDON\_ID\_HOOKS policies.
    
2.  **Verify user assignments.**
    
    You use the web client to assign users to roles, warehouses (in a multi-warehouse environment), and clients and client groups (in a 3PL environment). If the user is assigned to multiple warehouses, or is set as an Enterprise user, then the warehouse selected when the user logs in is the one that the application uses to determine the variable configurations. See [Users](../authorization/users.md).
    
3.  **Define the custom variable configurations that you want to implement.**
    
    You use the pages under Variable Configuration to create custom variable configurations.
    

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
