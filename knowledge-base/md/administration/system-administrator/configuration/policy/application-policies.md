---
title: "Application policies"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/policies/application_policies.htm"
source: "/content/policies/application_policies.htm"
toc_path:
  - "Administration"
  - "System Administrator"
  - "Configuration"
  - "Policy"
  - "Application policies"
sections:
  - "Address validation policy"
  - "Type of addresses to be validated policy"
images: []
source_sha1: 0fa322042756a386bb27efed9dd179fd06e6d2e3
---
# Application policies

You use the Application (APPLICATION) policies to configure application-level settings. These policies are used to determine the behavior of specific applications within your Blue Yonder installation; not the application behavior itself. Typically, the Applications policy group is used for application-level settings for an application that is available across multiple products.

**Note**: Depending on your Blue Yonder installation, an additional Applications policy group is available to group application-level setting policies that affect only a specific product but do not apply to another policy grouping defined for that product.

You use Policy Maintenance to maintain Application policies.

**IMPORTANT**: These policies are global and cannot be overridden by warehouse.

## Address validation policy

You can use the Address validation (APPLICATION/ADDRESS/VALIDATE) policy to specify whether the application will validate addresses against a valid list of country, state, city, and postal code combinations defined in the application. Address validation is used to verify address information whenever a defined address type (such as billing, customer, or carrier) is added or modified in the application and helps to eliminate the problems associated with an incorrect address (for example, if the address information has an invalid postal code for the city that may delay or prevent a shipment from reaching its destination).

**Note**: This policy is functional only for Blue Yonder products version 2006.1 and later.

You can configure the following DETAILS field for this policy:

-   **Return Number 1**: Specifies whether the application validates addresses against a valid list of country, state, city, and postal code combinations. A value of 1 is enabled, 0 is disabled. The policy is disabled by default.

A valid list of country, state, city, and postal code combinations against which addresses can be validated must already be defined in the application. Geographical data files, which provide a complete set of valid country, state, city, and postal code values for the United States or Canada are available during a Blue Yonder installation. You can also manually enter country, state, city, and postal code combinations for other countries using the web client. See [City Postal Codes](../internationalization/city-postal-codes.md).

## Type of addresses to be validated policy

You can use the Type of addresses to be validated (APPLICATION/ADDRESS/VALIDATE-ADRTYP) policy to specify the type of addresses, such as customer or carrier, that are validated in the application whenever an address with this address type is added or modified. The addresses are validated against a valid list of country, state, city, and postal code combinations. This policy is only functional when the Address Validation policy is enabled.

You can configure the following DETAILS fields for this policy:

-   **Return Number 1**: Specifies whether the application validates the associated address type whenever an address with this address type is added or modified. A value of 1 is enabled, 0 is disabled. The policy is disabled by default.
-   **Return String 1**: Parameter representing the type of address, such as customer or carrier, that you want validated in the application whenever an address with this address type is added or modified. The addresses are validated against a valid list of country, state, city, and postal code combinations in the application. The available address types can vary depending on your application configuration.
-   **Sort Sequence**: Order in which the application processes policy details in relation to other details defined for the same policy. The Sort Sequence value is automatically defined by the application when you first define an address type.
    
    **IMPORTANT**: Changing the sequence affects the order in which the application checks for address types and may impact processing behavior (for example, application performance slowdown issues). For more information, contact your Blue Yonder project team.
    

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
