---
title: "Parcel Handler"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/parcel_handler_sec.htm"
source: "/content/parcel_handler_sec.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Outbound"
  - "Shipping "
  - "Parcel Handler"
sections:
  - "Rate shopping"
  - "Pre-cartonization criteria"
  - "Configure Parcel Handler"
  - "Parcel Handler fields"
images: []
source_sha1: 00db7506f1d04e4dac784dc39160817372c254b6
---
# Parcel Handler

Parcel Handler is an application that provides the interface between Warehouse Management and Integrator to support communications between Warehouse Management and a third-party parcel application. The third-party parcel application interfaces with multiple carriers and is responsible for communicating with carriers to arrange for the transportation of parcels. It also generates the labels required to identify each parcel with the selected carrier.

**IMPORTANT**: The Parcel Handler policies must be configured in the Parcel Handler instance. If Warehouse Management and Parcel Handler are installed in the same instance, then Parcel Handler configurations can be defined in the web client on the Parcel Handler configuration page. However, if Warehouse Management and Parcel Handler are installed in separate instances, you must connect to the Parcel Handler client instance to configure these policies. For additional information on Parcel Handler configuration, see the _Warehouse Management Parcel Handler Configuration Guide_.

You use the Parcel Handler configuration page to define the following attributes: 

-   Authentication information for the parcel application that is integrated through Parcel Handler, such as the URL, user name, and password
-   Rate shopping preferences such as whether to rate shop across multiple carriers, and if the third-party parcel application is Centiro, whether rate shopping is based on the lowest price or the shortest lead time
    
-   Carrier list that defines the parcel carrier names for which you want to retrieve service conditions from the parcel application
    

**Note**: Parcel Handler payment terms and package codes used during the manifesting process are configured on the Parcel page. See [Configure parcel](parcel.md).

For additional information on Parcel Handler configuration, see the _Warehouse Management Parcel Handler Configuration Guide_.

## Rate shopping

Rate shopping is used to find the best rate for shipping a parcel package while still delivering it within a specific range of delivery dates.

**Note**: If the parcel application is Centiro, then the **Centiro Rate Shop Priority** field determines whether rate shopping is based on the lowest price or the shortest lead time. See [Configure Parcel Handler](#Configure_Parcel_Handler).

During manifesting, you can obtain rates from the parcel application integrated through Parcel Handler so that you can compare the cost of shipping the parcel at different service levels and, depending on configuration, different carriers. Parcel carrier rates are based on the dimensions and weight of the carton, any insurance value applied to the carton, and the destination. Changing the carrier is only allowed when the parcel is the first one manifested for the shipment, all of the orders associated with the shipment have the **Change Carrier** field set to Yes, and the Outbound Order Settings page has the **Carriers** field set to Yes.

**Note**: The ability perform rate shopping across multiple carriers is only available if the **Rate Shop Multiple Carriers** field is set to Yes. If set to No, then only the rates available for the assigned carrier are displayed. See [Configure Parcel Handler](#Configure_Parcel_Handler).

### Pre-cartonization criteria

The application can be configured to estimate the number and type of containers needed based on which inventory can be put together in the same container. You use the **Pre-Cartonization Criteria** field on the Pick Cartonization page to configure the criteria that determines how the application groups inventory that can be placed into the same container. See [Configure pick cartonization](../picking/pick-cartonization.md).

Inventory with matching values for the selected criteria can be included in the same container. Commonly used values include Carton Group, Ship-to Customer, and Order Number; values such as these are used to ensure that all the inventory in a container is being shipped to the same destination or belongs to the same order.

## Configure Parcel Handler

**Note**: Parcel Handler payment terms and package codes are defined on the Parcel configuration page. See [Configure parcel](parcel.md).

1.  Select **Configuration > Outbound > Shipping > Parcel Handler**.
2.  Enter information in the [Parcel Handler fields](#Parcel_Handler_fields).
3.  To define the carriers for which service conditions are received from the integrated parcel application:
    
    **Note**: Parcel Handler receives the carrier service conditions and parameters according to these carrier names when you run the FETCH-SERVICE-CONDITIONS job. For more information, see the _Warehouse Management Parcel Handler Configuration Guide_.
    
    1.  Under **GENERAL**, click **Service Condition Carrier List**.
    2.  To add a carrier for which to retrieve service conditions, click **Add**, enter the carrier and select **ENABLED**, and then click **Save**.
    3.  To remove a carrier from having their service conditions retrieved, select the check box next to the carrier, and then click **Delete**.
4.  Click **Save**.

## Parcel Handler fields

 
| Field | Description |
| --- | --- |
| Parcel Application URL | URL used to connect to the parcel application that is integrated through Parcel Handler. This is the URL for the third-party parcel application, not the service URL for the Parcel Handler instance. |
| Password | Password used to access the integrated parcel application. |
| Username | User name to access the integrated parcel application. |
| Parcel Application | Application that is integrated with Warehouse Management through Parcel Handler. |
| Centiro Rate Shop Priority | Determines whether carriers and carrier services should be retrieved based on lowest cost or shortest lead time.<br>-   • **Lead Time:** The application retrieves the carriers and carrier service based on shortest lead time.
<br>-   • **Cost**: The application retrieves the carriers and carrier services based on the lowest cost. This is the default value.
<br > **Note**: This configuration is only applicable if Centiro is the third-party parcel application. |
| Maximum Carrier Services | Maximum number of carrier services that should be retrieved by the application from the third-party parcel application during rate shopping. |
| Rate Shop Multiple Carriers | If Yes, then carrier service rates are retrieved from multiple carriers during rate shopping. If rate shopping is enabled, a user can use rate shopping functionality to search carriers and service levels to find the lowest cost for shipping a parcel package in the best transit time, while still delivering it within a specific range of delivery dates.<br > If No, then rate shopping is performed only for the carrier currently assigned to the parcel. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
