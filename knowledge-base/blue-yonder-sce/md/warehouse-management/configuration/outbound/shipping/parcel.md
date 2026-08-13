---
title: "Parcel"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/parcel_config.htm"
source: "/content/parcel_config.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Outbound"
  - "Shipping "
  - "Parcel"
sections:
  - "Parcel setup tasks"
  - "Bundling"
  - "Setup and configuration"
  - "Rate shopping"
  - "Pre-cartonization criteria"
  - "Shipper rules"
  - "Purpose of parcel shipper rules"
  - "How parcel shipper rules are evaluated"
  - "Shipper rule examples"
  - "Parcel Handler payment terms and payment codes"
  - "Parcel address validation and carrier selection"
  - "Address validation configuration"
  - "Carrier selection configuration"
  - "Processing"
  - "Error handling and reallocation"
  - "Setup"
  - "Pre-manifesting and manifest to hold"
  - "Parcel processing scenarios"
  - "Set up pre-manifesting"
  - "Set up automatic release of parcels"
  - "Set up automatic close of parcel shipments"
  - "Configure parcel"
  - "Parcel fields"
  - "Parcel Handler Payment Terms fields"
  - "Parcel Handler Package Codes fields"
images: []
source_sha1: dba14e214eccb63596b62dc5ed409262e61fbd43
---
# Parcel - Configuration

Parcel processing is the act of preparing and shipping outbound orders using a small package (parcel) carrier. A parcel carrier typically prefers to handle individual smaller packages (typically weighing less than 150 pounds), but some parcel carriers offer heavy parcel services as well. This differs from less-than-truckload (LTL) carriers that typically want shipments to be packaged as large as possible such as by pallet.

Parcel processing functionality enables you to prepare parcel orders for shipping but relies on an integrated parcel manifesting service to provide parcel manifesting functionality. Warehouse Management provides item, order, and shipment information, and order processing functionality; the parcel application provides rating, manifesting, carrier compliance, and carrier communication functionality.

Configure the parcel settings if Warehouse Management is integrated with a parcel application through Parcel Handler.

## Parcel setup tasks

You must configure parcel processing if Warehouse Management is integrated with a parcel application (through Parcel Handler).

The following information must be obtained from the third-party parcel vendor before you configure parcel processing:

**Note**: For required configurations that are performed outside the web client, see the _Warehouse Management Parcel Handler Configuration Guide_.

-   **Carriers and service levels**: Used to configure parcel carriers and service levels. Once carrier and service levels are configured, carrier cross reference should be definedUsed to configure the carrier cross references and to define the Parcel Handler carrier list in the Warehouse Management web client. These configurations provide visibility in Warehouse Management to the carriers and service levels that are available for shipping parcels.
-   **Parcel Handler payment terms and Parcel Handler package codes**: Used to configure the carriers' payment terms and package codes in the Warehouse Management web client. The payment terms and package codes that are available for carriers from the parcel vendor must be added to Warehouse Management.
-   **Shipper IDs**: Used to configure the shipper rules in the Warehouse Management web client. A shipper ID, obtained from the parcel vendor, identifies the entity and address (location) from which a parcel is shipped. Shipper rules are used for manifesting and rating a parcel shipment.

Perform the following tasks to configure parcel processing:

1.  Enable the Parcel integration in Warehouse Management. See [Configure general integration](../../integration/general-integration.md).
2.  Configure parcel processing.
    
    -   **Bundling**: Select the carriers and service levels that allow bundling, the criteria that must match for parcels to be bundled together, and whether you allow users to select a parcel for bundling that has already been manifested (the application voids the parcel from the manifest prior to adding the parcel to a bundle).
    -   **Manifesting**: Define the rules by which a shipper ID is selected for manifesting packages.
        
        **IMPORTANT**: For the **Shipper ID** field, the value must match the value provided by the parcel vendor.
        
    -   **Customer-specific data fields**: For a customer, select from inventory, customer, and order attributes to provide additional information on labels and in notifications to the carrier.
        
    -   **Address validation and carrier selection**: Define the order types for which a shipment's route-to address is validated by the integrated parcel application, and whether to prevent allocation of shipments until parcel address validation and carrier selection are successful. See [Parcel address validation and carrier selection](#Parcel_address_validation_and_carrier_selection).
    
    See [Configure parcel](#Configure_parcel).
    
3.  Configure carrier cross references to match the carriers provided by the parcel application integrated through Parcel Handler. For each carrier and service level, configure the following fields:
    
    -   For the **External System Name** field, select **Parcel**.
    -   For the **Parcel Manifest Service** field, enter the carrier code and service level received from Parcel. The carrier and service level are separated by a pipe character; for example, std.ups.com|STD.
        
        **IMPORTANT**: For the **Parcel Manifest Service** field, the value must match the value provided by the parcel vendor.
        
    
    See [Add or modify a carrier cross reference](../../partners/carriers/carrier-cross-reference.md).
    
4.  Configure parcel carriers. For each parcel carrier, the service level must have a transport mode that is configured for shipping parcels. See [Add or modify a carrier](../../partners/carriers/existing-carriers.md).
5.  Configure Parcel Handler attributes. See [Parcel Handler](parcel-handler.md).
    
    **Note**: After you define the carrier list, verify that the carrier service conditions and service parameters can be assigned to orders and order lines. Carrier-specific service conditions and service parameters are supplied by the parcel vendor. Therefore, to understand these values, contact the parcel vendor. If the conditions and parameters are not available, then confirm the carrier cross reference and carrier list configurations are correct, and ensure the FETCH-SERVICE-CONDITIONS job is enabled.
    
6.  To have manifested, staged parcel shipments closed automatically, see [Set up automatic close of parcel shipments](#Set_up_automatic_close_of_parcel_shipments).
7.  To configure carrier (bill-to) accounts for customers that order parcel shipments, see the information on adding a carrier account in [Add or modify a customer](../../partners/customers/existing-customers.md). You can assign an account number to each customer and carrier combination.

## Bundling

Bundling is the process of combining (such as by taping or banding together) two or more small parcels to create one large parcel (called a bundled parcel LPN). Bundling is typically done when it costs less to ship one large parcel than it does to ship several small parcels.

When bundling parcels, you can identify the bundled parcel by entering a new LPN, scanning an LPN from a pre-printed barcode label, or assigning an application-generated LPN to the bundle. The application tracks the bundled parcel LPN, as well as the sub-LPNs (or sub-LPN UCCs) of the individual parcels in the bundle.

Unbundling is the process of disbanding a bundled parcel LPN into its original individual parcels. When you do this, the bundled parcel LPN is removed from the application and the individual parcels are tracked by their original carton number (sub-LPN) on a new application-generated LPN.

If Warehouse Management is integrated with a parcel application through Parcel Handler, you can bundle and manifest at the same time, or bundle first and then manifest (see [Bundling examples](../../../shipping/bundling.md)). When a bundled parcel LPN is manifested, it is listed on the manifest as a single parcel identifier, which has a single tracking number, internal tracking number, weight, and freight rate.

**Note**: You use the **Shipping > Bundling** page to perform bundling and unbundling procedures. See [Bundling](../../../shipping/bundling.md).

### Setup and configuration

You must perform the following tasks to be able to bundle individual parcels for shipping:

1.  Configure the carrier service levels that allow bundling. See [Configure parcel](#Configure_parcel) or [Add or modify a carrier](../../partners/carriers/existing-carriers.md).
2.  Select the criteria that must match for parcels to be bundled together. See [Configure parcel](#Configure_parcel).
3.  If Warehouse Management is integrated with a parcel application (through Parcel Handler) and you want to manifest parcels and bundled parcel LPNs, then you must configure parcel processing. See [Parcel setup tasks](#Parcel_setup_tasks).
    
    You can also configure the application to allow manifested parcels to be added to a bundled parcel LPN. If bundling manifested parcels is allowed, the application automatically voids the parcel from its original manifest before adding it to the bundled parcel LPN. See [Configure parcel](#Configure_parcel).
    

## Rate shopping

Rate shopping is used to find the best rate for shipping a parcel package while still delivering it within a specific range of delivery dates.

**Note**: If the parcel application is Centiro, then the **Centiro Rate Shop Priority** field determines whether rate shopping is based on the lowest price or the shortest lead time. See [Configure Parcel Handler](parcel-handler.md).

During manifesting, you can obtain rates from the parcel application integrated through Parcel Handler so that you can compare the cost of shipping the parcel at different service levels and, depending on configuration, different carriers. Parcel carrier rates are based on the dimensions and weight of the carton, any insurance value applied to the carton, and the destination. Changing the carrier is only allowed when the parcel is the first one manifested for the shipment, all of the orders associated with the shipment have the **Change Carrier** field set to Yes, and the Outbound Order Settings page has the **Carriers** field set to Yes.

**Note**: The ability perform rate shopping across multiple carriers is only available if the **Rate Shop Multiple Carriers** field is set to Yes. If set to No, then only the rates available for the assigned carrier are displayed. See [Configure Parcel Handler](parcel-handler.md).

### Pre-cartonization criteria

The application can be configured to estimate the number and type of containers needed based on which inventory can be put together in the same container. You use the **Pre-Cartonization Criteria** field on the Pick Cartonization page to configure the criteria that determines how the application groups inventory that can be placed into the same container. See [Configure pick cartonization](../picking/pick-cartonization.md).

Inventory with matching values for the selected criteria can be included in the same container. Commonly used values include Carton Group, Ship-to Customer, and Order Number; values such as these are used to ensure that all the inventory in a container is being shipped to the same destination or belongs to the same order.

## Shipper rules

A parcel shipper rule is a set of attributes (building or client) that the application evaluates to select a shipper ID to automatically apply to a parcel during rating and manifesting. The shipper ID represents the entity and address (location) from which a parcel is shipped. While the warehouse is the physical entity shipping parcels, for rating and manifesting purposes, individual buildings or clients can also be considered the shipping entity. Warehouse Management uses the shipper ID to indicate which parcel carrier shipper account (and, therefore, which set of rates) is to be used for manifesting and rating a parcel shipment.

**IMPORTANT**: Shipper IDs are provided by the parcel vendor, and must be added to shipper rules exactly as provided.

### Purpose of parcel shipper rules

A warehouse or its clients (for a third party logistics \[3PL\] facility) may have negotiated different rates with different parcel carriers depending on certain attributes of a shipment. The warehouse wants the appropriate shipper ID to be communicated to the parcel carrier for each parcel shipment so that the appropriate rates are applied during rating and manifesting. For example, for some clients, the warehouse's negotiated rates are better than the client's own negotiated rates, so the clients want to ship under the warehouse's shipper ID to get the better rates. Other clients may have negotiated better rates with the parcel carriers, and would like to ship using the client's shipper ID to get the client's better rates.

### How parcel shipper rules are evaluated

Parcel shipper rules are evaluated based on their arrangement in the Shipper Rules grid. The parcel shipper rule listed at the top of the grid is evaluated first and the rest are evaluated in order (top to bottom) until a rule matches. Therefore, it is recommended that you create a default rule that is only configured with a shipper ID and place it at the bottom of the Shipper Rules grid. However, if you will be manually manifesting parcels (non-warehouse parcels), you need to set up a default rule. Since no other attributes are associated with a non-warehouse parcel, it will rate and manifest with the shipper ID defined for the parcel shipper rule that is set up for the warehouse.

## Shipper rule examples

The following list provides examples of parcel shipper rules:

-   **Client-specific**: A warehouse sets up a general shipper ID. The warehouse has a client, CLIENTA, with its own shipper ID, SHIPPER01. Each parcel rated or manifested for the warehouse uses the general shipper ID, except for parcels that are rated or manifested for CLIENTA. Parcels for CLIENTA are rated or manifested using shipper ID, SHIPPER01.
-   **Building-specific**: A warehouse has negotiated different rates for the warehouse's three buildings. Parcels rated or manifested from BLDG1 use shipper ID, SHIPPER1. Parcels rated or manifested from BLDG2 use shipper ID, SHIPPER2. Parcels rated or manifested from BLDG3 use shipper ID, SHIPPER3.
-   **Multiple attributes**: Parcel shipper rules have been configured for warehouse WMD1 as described in the following table.
    
       
    | Rule | Shipper | Client | Building |
    | --- | --- | --- | --- |
    | 1 | SHIPPER4 | CLIENTB | BLDG3 |
    | 2 | SHIPPER3 | CLIENTA | ANY |
    | 3 | SHIPPER2 | ANY | BLDG2 |
    | 4 | SHIPPER1 | ANY | ANY |
    

The following parcel shipments are rated and manifested using a shipper ID as determined by the appropriate parcel shipper rule:

-   SHIPMENT1 is being rated and manifested from BLDG2 for CLIENTB in WMD1.
    -   Does not match the first rule, since it is rated and manifested from a different building
    -   Does not match the second rule because it is for a different client
    -   Matches the third rule since it is being rated and manifested from BLDG2 in warehouse WMD1. The shipper ID for SHIPMENT1 will be SHIPPER2.
-   SHIPMENT2 is being rated and manifested from BLDG2 for CLIENTA in WMD1.
    -   Does not match the first rule since its building and client are different
    -   Matches the second rule, since it is for CLIENTA and in warehouse WMD1. The shipper ID for SHIPMENT2 will be SHIPPER3.
-   SHIPMENT3 is being rated and manifested from BLDG1 for CLIENTB in WMD1.
    -   Does not match the first rule since it is being rated and manifested from BLDG1
    -   Does not match the second rule since it is for CLIENTB
    -   Does not match the third rule since it is being rated and manifested from BLDG1
    -   Matches the fourth and last rule since it is being rated and manifested from within warehouse WMD1. The shipper ID for SHIPMENT3 will be SHIPPER1. Note that the last rule is configured to act as a default rule.

## Parcel Handler payment terms and payment codes

Parcel Handler payment terms specify how parcel shipping charges are paid (such as collect on delivery, prepaid, or bill recipient). A carrier-specific payment term is a payment term that a parcel carrier has defined for itself. When shipping parcels using a parcel carrier, you must use one of the carrier's payment term values; otherwise, the payment term is rejected and the parcel is not manifested.

Parcel Handler package codes specify the types of packaging (such as envelope, package, box, tube, or custom package) that a carrier supports. Package codes are carrier specific and are used to ensure that the proper shipping rate is applied based on the packaging that is used.

When Warehouse Management is integrated with Parcel Handler, a default set of Parcel Handler payment terms and package codes is provided in the standard product. However, you must obtain the carrier-specific payment terms and package codes that are required for your installation from the parcel vendor, and if any of them are not included in the default set, you must manually add them to Warehouse Management.

You can enter the **Parcel Handler Payment Terms** and **Parcel Handler Package Codes** fields on the Parcel configuration page. Alternatively, you can enter data directly to the database using a script or insert statements. See the _Warehouse Management Parcel Handler Configuration Guide_.

**IMPORTANT**: Do not use the **Payment Terms** field to define payment terms for a parcel application integrated through Parcel Handler. Only data entered for **Parcel Handler Payment Terms** is available for selection on order lines and during manifesting when Warehouse Management is integrated with a parcel application through Parcel Handler. Data for **Parcel Handler Package Codes** is available for selection during manifesting.

The **Payment Terms** field is not currently used.

**Note**: When automatically creating shipments, Warehouse Management does not consolidate shipment lines that have different payment terms.

## Parcel address validation and carrier selection

When Warehouse Management is integrated with a parcel application through Parcel Handler, you can configure the application to validate a shipment's route-to address with the parcel application prior to allocation, and to select a carrier if required. This configuration is used to reduce manifesting errors due to an incorrect or incomplete address, and to select the lowest-cost (or shortest lead time, depending on configuration) carrier and service level (if the shipment was created without a carrier).

### Address validation configuration

You can select specific order types for which the application sends address validation to a parcel application. When a shipment is created or downloaded with one of the selected order types, then the application can prevent allocation of the shipment until address validation and carrier selection is successful, if configured to do so.

### Carrier selection configuration

Carrier selection through a parcel application is configured by defining a selection rule with the carrier and service level set to Parcel. Since carrier selection rules are considered in sequence, you can prioritize the Parcel rule to run first, or you can lower its priority to ensure that it is used only after other rules are considered and no carrier is found. For example, assume you have three carrier selection rules in the following sequence: Carrier 1, Carrier 2, and Parcel. When a shipment is created or downloaded without a carrier, the application attempts to find matching criteria for Carrier 1 and then Carrier 2, if the first rule was unsuccessful. If neither are successful, then the third rule (Parcel) is executed and the application sends rate shopping and carrier selection to the integrated parcel application.

If Event Management is installed, you can enable an event so that information is sent to Event Management whenever parcel validation fails.

### Processing

During address validation and carrier selection processing, the application applies a tag to the shipment and wave, if applicable. The parcel validation tag displays one of the following statuses: Pending Parcel, In Progress Parcel, and Failed Parcel. If multiple shipments in a wave have different parcel validation tags, only one tag is displayed for the wave. If one shipment fails validation, then Failed Parcel is displayed for the wave; if no shipments fail validation but some are pending and some are in progress, then the In Progress Parcel tag is displayed.

**Note**: You can view the parcel tags on pages that display shipments and waves; such as the Waves and Picks page, and Outbound page. See [View waves](../../../shared-functions/waves-and-picks/procedures-for-waves.md) and [View shipments](../../../outbound-planner/outbound/procedures-for-shipments.md).

Address validation and carrier selection are configured separately but function cooperatively. Depending on the shipment details, carrier selection or address validation may not be required. For example, when a shipment is created or downloaded with an order type configured for address validation, the application confirms whether a carrier and service level are defined on the shipment, and then performs one of the following tasks: 

-   If a carrier and service level are defined on the shipment, then the application sends the route-to address to the parcel application through Parcel Handler for validation.
    -   If validation is successful, normal processing (allocation, picking, and manifesting) can resume.
    -   If validation fails, the application determines whether to prevent allocation based on the parcel configuration (**Prevent Allocation on Failure** field).
-   If a carrier and service level are not defined on the shipment, then the application selects a carrier using the configured carrier selection rules.
    -   If you configure a selection rule with the carrier and service level set to Parcel, then the application will send carrier selection to the parcel application. If carrier selection fails, the application determines whether to prevent allocation based on the parcel configuration (**Prevent Allocation on Failure** field).
        
        **Note**: Carrier selection for a shipment can be sent to parcel regardless of whether the shipment has an order type selected for address validation. Alternatively, if a carrier is selected using a non-parcel rule, then the shipment can still be sent to parcel for address validation if it contains an order type enabled for validation.
        
    -   If carrier selection through the parcel application fails, the application does not consider any additional selection rules.

**Notes**: 

-   If the weight of the shipment exceeds the maximum weight or volume restrictions on the carrier service level, then parcel validation will fail.
-   If a shipment is created without shipment lines (orders), validation does not occur until the first order is added.

After address validation is complete, if you change the carrier, service level, or the route-to address, then the application re-validates the address with the parcel application. Once a wave is successfully allocated, the application no longer validates carrier selection or the route-to address with the parcel application.

### Error handling and reallocation

When an error occurs during address validation or carrier selection, regardless of whether the shipment was prevented from allocation, the issue must be resolved to avoid errors during manifesting. However, for shipments that were not allocated due to a parcel validation error, an automatic allocation method can be configured to ensure that the previously failed shipment is auto allocated after the error is resolved.

If an error occurs, you can view the details of the shipment to see the cause of the error (**Parcel Error** field). This message is populated directly from the parcel application. See [View shipments](../../../outbound-planner/outbound/procedures-for-shipments.md).

For example, assume the route-to address of a customer is incorrect and causes address validation to fail. After the error is resolved and you save the changes, the application identifies any unallocated shipments (status of Ready) associated with the updated route-to address that also have a parcel validation status. The application resets the parcel validation status of the shipments to Ready, and then performs re-validation by sending the address to the parcel application again.

When validation is successful, the application selects the shipment for auto allocation, if configured to do so. You can configure the auto allocation method criteria to specifically search for shipments that were prevented from being allocated due to failed parcel validation. Typical auto allocation methods are configured to run based on a certain event (as scheduled or on download); however, you set the method for failed parcel validation to always run. This setting ensures that as soon as the error is resolved and parcel validation is successful, the application can allocate the shipment without waiting for any additional action or manual allocation.

### Setup

You must complete the following tasks to set up parcel address validation and carrier selection:

1.  Perform the required parcel setup tasks. See [Parcel setup tasks](#Parcel_setup_tasks).
2.  On the Parcel page, perform the following tasks: 
    
    1.  Select the order types for which a shipment's route-to address is validated by the integrated parcel application through Parcel Handler. A shipment's address is validated if at least one order type on the shipment is enabled.
        
    2.  Select whether to prevent allocation of shipments until parcel validation and carrier selection is successful (**Prevent Allocation on Failure** field). If enabled, shipments that are pending validation, in the process of being validated, or that fail validation are prevented from allocation. In a 3PL environment, select the clients that prevent allocation until parcel validation is successful.
        
    
    See [Configure parcel](#Configure_parcel).
    
3.  Configure a carrier selection rule for sending carrier selection to the integrated parcel application. The rule must include the following values: 
    
    -   **Carrier**: Parcel
    -   **Service**Level: Parcel
    
    **Note**: Only carriers for which you have configured a carrier cross reference can be selected by the integrated parcel application. See [Carrier Cross Reference](../../partners/carriers/carrier-cross-reference.md).
    
    See [Configure carrier selection rules](carrier-selection.md).
    
4.  If the application is integrated with Event Management, then to receive an alert whenever a shipment fails address validation or carrier selection, set the **Parcel Validations** field to Yes in the Event Management integration configuration. See [Configure Event Management integration](../../integration/event-management.md).
5.  Configure an automatic allocation method for the shipments that failed address validation or carrier selection. Define the method with the following attributes to ensure that shipments that failed validation are selected for auto allocation when the error is resolved: 
    
    -   **Always Run**: Yes
    -   **Criteria Definition** with the following values: 
        -   **Entity**: Parcel Shipment Activity
        -   **Column**: Allocation Prevented
        -   **Value**: 1
    
    See [Configure automatic allocation settings](../allocation/automatic-allocation.md).
    

## Pre-manifesting and manifest to hold

Pre-manifesting is an automatic process that manifests a parcel to hold during pick release. With this process you can configure pick release to print a picking label and a shipping label at the same time. This process eliminates the need to manifest parcels and print shipping labels after picking.

**Note**: If you do not manifest to hold, then you typically manifest parcels after picking and packing, and before or during staging.

Manifest to hold is the process of manually manifesting a parcel to a hold status. That means the parcel is not released for shipping.

**Note**: A single-piece held package is not added to a manifest until it is released. Only multi-piece held packages are added to the manifest.

When a parcel is pre-manifested or manifested to hold, you can print the shipping label and apply the label to the picking or shipping carton. However, since the parcel is not released for shipping, you can still make adjustments to the package attributes, such as its weight.

A manifest cannot be closed when it has held packages. Therefore, you must resolve the problem shipment (either release or void the parcel) before closing the manifest.

You use one of the following methods to manifest parcels to hold:

**IMPORTANT**: Pre-manifesting is not supported for parcels assigned to LTL carriers.

-   **Automatic** **(pre-manifesting)**: You can configure the pick release rules for the Carton Pick pick method and optionally for a specific zone (typically for small package staging) to manifest the package to hold. This process takes place at the time of pick release. See [Set up pre-manifesting](#Set_up_pre-manifesting).
-   **Manual**: After inventory has been picked, you can use the Manifesting page to manifest a parcel to hold (set the **Manifest to Hold** field to Yes). This method is useful in exception situations where a parcel could not be or was not manifested to hold automatically. For example, you can manually manifest a parcel to hold and then deposit it with the automatically manifested parcels, so that your normal business process can be applied to the manually manifested parcel.

On the Parcel page, **Packages** tab, you can view parcels that have been manifested to hold (package status is Hold). The parcel remains in this status until it is manually or automatically released for shipping, or voided from the manifest.

-   To configure Warehouse Management to automatically release held parcels when the shipment is staged, see [Set up automatic release of parcels](#Set_up_automatic_release_of_parcels).
-   To release held parcels manually, see [Release a held parcel](../../../shipping/parcel/procedures-for-parcels.md).

## Parcel processing scenarios

**How to have an order line processed as a parcel**

Parcel processing is supported when Warehouse Management is integrated with a parcel application through Parcel Handler.

A parcel shipment can consist of one or more packages (depending on the carrier configuration) that are shipped together on a parcel carrier.

When an order line is processed as a parcel, the inventory that is released for picking or picked is displayed on the Parcel page, **Packages** tab. The parcel can be manifested from the Manifesting page (if not already pre-manifested during pick release).

For an order line to be processed as a parcel, it must have the following attributes:

-   Have a parcel carrier and service level assigned:
    -   The carrier's service level must be configured with a transport mode that is configured for parcel shipping. See [Existing Carriers](../../partners/carriers/existing-carriers.md).
    -   The carrier and service level must have a carrier cross reference configured for the parcel application. See [Carrier Cross Reference](../../partners/carriers/carrier-cross-reference.md).
-   Be manifested either during pick release or after picking:
    -   Automatic manifesting occurs when the pick release rule is configured for pre-manifesting. See [Pre-manifesting and manifest to hold](#Pre-manifesting_and_manifest_to_hold).
    -   You can manually manifest the parcel using the Manifesting page. See [Manifest a parcel](../../../shipping/manifesting.md).

The order line can also include carrier-specific payment terms and package codes.

**Single-parcel and multi-parcel shipments**

A configuration on the parcel carrier service level determines whether a parcel shipment is limited to one parcel or can consist of multiple parcels.

When a shipment consists of multiple parcels, each parcel can be added to the same manifest. The resulting labels will include the package number of the shipment; for example, 1 of 3, 2 of 3, and 3 of 3.

For information on forcing single-parcel shipments for a carrier service level, see [Service Level fields](../../partners/carriers/existing-carriers.md).

**Parcel processing at the pack station**

At a pack station, you use the Packing page to process and complete single-parcel shipments (one shipping container per shipment) or multi-parcel shipments (multiple shipping containers per shipment).

**Note**: A multi-parcel shipment consists of multiple parcels that together have the same shipment and manifest, but each parcel has a different tracking number. For multi-parcel shipments, the package number is printed on the label, such as 1 of 3, 2 of 3, and 3 of 3.

**Manifesting**

You can configure a pack station workstation to display the Manifesting page automatically when the operator completes a shipping container. After the operator manifests the package, the operator can resume packing. See [Manifest at pack station](../../../packing/packing-concepts.md).

**Note**: If the packing operator does not have permission to view the Manifesting page, then manifesting must be done later by an authorized user.

For automatic manifesting, you can configure the Manifest the Packed Shipping Container Automatically (MNFST-SHP-CTN) master and background workflows to manifest the shipping container when it is closed.

**Note**: If the workstation is configured to display the Manifesting page, then the MNFST-SHP-CTN workflows should not be configured for automatic manifesting.

Labels are created by the parcel application integrated through Parcel Handler. The content of the labels is governed by the carrier assigned to the manifest. The sender address on the label is the Warehouse Management account address (as defined by the shipper ID configuration).

You can print labels for parcels at the following processing points:

-   Pre-manifesting
    -   If the application is configured for automatic pre-manifesting, then the release rule configured for the pick defines whether labels are printed automatically when allocated picks are released. See [Set up pre-manifesting](#Set_up_pre-manifesting).
        
        Parcel labels printed at the time of pick release contain both the pick and the parcel package information.
        
-   Pack station processing
    -   When a shipping container is closed, the packing operator (if authorized) can access the Manifesting page to print parcel labels.
        
    -   For automatic label printing, you can configure the Label Manifest Carton (MNFST-CTN) master and outbound workflows to print parcel labels for the shipping container when it is closed.
-   Staging
    -   From the Parcel page, **Packages** tab, you can print labels for manifested parcels.
-   Manifest closing
    -   After the manifest is closed, paperwork (a summary of the carrier services and shipments) can be printed, and labels can be reprinted as needed.

**Label printing**

You can print parcel labels from the Manifesting page.

For automatic label printing, you can configure the Label Manifest Carton (MNFST-CTN) master and outbound workflows to print parcel labels for the shipping container when it is closed.

**Manual and automatic label printing for parcels**

Labels are created by the parcel application integrated through Parcel Handler. The content of the labels is governed by the carrier assigned to the manifest. The sender address on the label is the Warehouse Management account address (as defined by the shipper ID configuration).

You can print labels for parcels at the following processing points:

-   Pre-manifesting
    -   If the application is configured for automatic pre-manifesting, then the release rule configured for the pick defines whether labels are printed automatically when allocated picks are released. See [Set up pre-manifesting](#Set_up_pre-manifesting).
        
        Parcel labels printed at the time of pick release contain both the pick and the parcel package information.
        
-   Pack station processing
    -   When a shipping container is closed, the packing operator (if authorized) can access the Manifesting page to print parcel labels.
        
    -   For automatic label printing, you can configure the Label Manifest Carton (MNFST-CTN) master and outbound workflows to print parcel labels for the shipping container when it is closed.
-   Staging
    -   From the Parcel page, **Packages** tab, you can print labels for manifested parcels.
-   Manifest closing
    -   After the manifest is closed, paperwork (a summary of the carrier services and shipments) can be printed, and labels can be reprinted as needed.

## Set up pre-manifesting

To set up pre-manifesting to occur at the time of pick release, you must configure the release rule for the pick that is used to release the parcel picks. See [Pick Methods](../picking/pick-methods.md).

The following example shows how to configure the Carton Pick pick method for pre-manifesting.

1.  Select **Configuration > Outbound > Picking > Pick Methods**.
2.  In the grid, click the **Carton Pick** pick method. The Carton Pick pick method is displayed.
3.  Under **RELEASE RULES**, click **Carton Pick**. The Carton Pick Release Rules page is displayed.
4.  Click **Destination Rules**. The Carton Pick Destination Rules page is displayed.
5.  Add a destination rule for the parcel staging zone:
    1.  Click **Add**.
    2.  From the **Destination** drop-down list, select the zone (such as small package staging) in which parcel shipments are staged.
    3.  From the **Action** drop-down list, select one of the following commands to manifest the parcels destined for the zone:
        -   **CREATE WORK FOR PM PRE MANIFEST PACKAGE**: Creates the work in the work queue for the carton pick, and manifests the parcel.
        -   **PROCESS PM PRE MANIFEST PACKAGE**: Creates the work in the work queue for the carton pick, manifests the parcel, and prints the label that contains both the pick and the parcel shipping information.
            
            **IMPORTANT**: Labels must be set up before picks are allocated. If a label is required but is not set up, then pick release fails.
            
        -   **PRODUCE LABEL FOR PM PRE MANIFEST PACKAGE**: Manifests the parcel and prints the label that contains both the pick and the parcel shipping information. Does not create a work queue entry.
    4.  Click **Save**.
6.  Click **Save**.

## Set up automatic release of parcels

You can use a background workflow to automatically release parcels to the carrier for parcel pickup. The background workflow automatically runs the command (defined in the master workflow) to release the manifested packages when they are deposited to a shipment staging location (exit point defined in the background workflow).

To release parcels automatically using a background workflow:

1.  Create a master workflow (or use RELEASE-PM-SHIP-PKG) with the following attributes:
    
    **Note**: See [Add or modify a master workflow](../../work/workflows/master-workflows.md).
    
    -   **Type**: Background
    -   **User Instructions**:
        -   **Confirmation**: Do not confirm.
        -   **Discontinue Workflow On Fail**: No
        -   **Instruction Action**:
            -   **Result**: Pass
            -   **Action**: Run MOCA
            -   **Command**: release pm packages for shipment where @\*
2.  Create a background workflow (or use RELEASE-PM-SHIP-PKG) with the following attributes:
    
    **Note**: See [Add or modify a background workflow](../../work/warehouse-workflows/background-workflows.md).
    
    -   Enabled
    -   **Master Workflow**: RELEASE-PM-SHIP-PKG
    -   **Exit Point**: Shipment Stage

## Set up automatic close of parcel shipments

You can configure the application to automatically close (complete) parcel shipments that have been manifested and staged. This process automatically moves a parcel shipment from the Staged to Load Complete status after all of the shipment's parcels have been manifested and staged for the required wait time, and are in the manifest status specified for the parcel carrier.

**Note**: Parcel processing is supported for carriers with a transport mode configured for shipping parcels, and only when Warehouse Management is integrated with a parcel application through Parcel Handler.

Perform the following tasks to set up auto-closing of parcel shipments:

1.  Schedule the Automatically Close Parcel Shipments job (AUTO-CLOSE-PARCEL) to run at timed intervals. This job, when it runs, performs auto-load and close processing on qualifying parcel shipments. For information on scheduling jobs using the Console, see the _Supply Chain Execution Applications Console User Guide_.
2.  Configure each parcel carrier to which auto-closing applies. You must enable the auto-close functionality, define the wait time after staging that shipments can be closed, and select the manifest status (such as Released or Closed) that parcels must have to qualify for auto-closing. See [Add or modify a carrier](../../partners/carriers/existing-carriers.md).

## Configure parcel

1.  Select **Configuration > Outbound > Shipping > Parcel**.
2.  Enter information in the [Parcel fields](#Parcel_fields).
3.  To define the carrier and service levels at which bundling during manifesting is allowed:
    
    **Note**: This configuration is usually dependent on the warehouse terms of agreement with the carrier and whether the carrier allows bundling at certain service levels.
    
    1.  Under **BUNDLING**, click **Carriers Allowing Bundling**.
    2.  In the **Available** column, select the check box next to the carrier and service levels that apply.
    3.  Click **Apply**.
4.  To define the criteria that must match for packages to be bundled together:
    1.  Under **BUNDLING**, click **Bundling Criteria**.
    2.  In the **Available** column, select the check box next to the attributes that apply.
    3.  Click **Apply**.
5.  To define shipper rules provided by the parcel vendor:
    
    1.  Under **MANIFESTING**, click **Shipper Rules**.
        
    2.  Perform one of the following tasks:
        -   To add a shipper rule, click **Add**.
        -   To copy a shipper rule, in the grid, select the check box next to the rule, and then click **Copy**.
    3.  Enter information in the following fields:
        
         
        | Field | Description |
        | --- | --- |
        | Shipper | Identifier that represents the entity and address (location) from which a parcel is shipped. The Shipper is a value provided by the parcel vendor and configured in Warehouse Management. See [Shipper rules](#Shipper_rules). |
        | Building | Unique identifier for a building. A building is a warehouse entity consisting of one or more areas. Inventory and location information can be reported by building. |
        | Client | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. |
        
    4.  Click **Save**.
    5.  To arrange the sequence that shipper rules are evaluated, in the grid, click a row and then drag it to the preferred position.
    6.  Click **Apply**.
6.  To add the Parcel Handler payment terms provided by the parcel vendor:
    
    **IMPORTANT**: Use the Parcel Handler Payment Terms field to enter payment terms provided by the parcel vendor. The Payment Terms field is not currently used.
    
    1.  Under **MANIFESTING**, click **Parcel Handler Payment Terms**.
    2.  Perform one of the following tasks:
        
        -   To add a payment term, click **Add**.
        -   To copy a payment term, in the grid, select the check box next to the payment term, and then click **Copy**.
    3.  Enter information in the [Parcel Handler Payment Terms fields](#Parcel_handler_payment_terms_fields).
    4.  Click **Save**.
7.  To add the package codes provided by the parcel vendor:
    
    1.  Under **MANIFESTING**, click **Parcel Handler Package Codes**.
    2.  Perform one of the following tasks:
        
        -   To add a package code, click **Add**.
        -   To copy a package code, in the grid select the check box next to the package code, and then click **Copy**.
    3.  Enter information in the [Parcel Handler Package Codes fields](#Parcel_handler_package_codes_fields).
    4.  Click **Save**.
8.  To define customer-specific data fields:
    1.  Under **MANIFESTING**, click **Customer-Specific Data Fields**.
    2.  Perform one of the following tasks:
        -   To add a field, click **Add**.
        -   To modify a field, in the grid, click the customer.
        -   To copy a field, in the grid, select the check box next to the customer, and then click **Copy**.
    3.  Enter information in the following fields:
        
        | Field | Description |
        | --- | --- |
        | Customer | Customer to whom inventory is shipped, and to whom the user field configuration applies. To define a configuration that applies to all customers, select **Default**. The application applies the default configuration if no customer-specific configuration exists for the customer. |
        | Client | Unique identifier for a client who houses inventory within a multi-client (third-party logistics) warehouse. The client identifier distinguishes one client from another so that the application can effectively manage inventory and activities for multiple clients in the same warehouse. |
        | Field 1 - Field 4 | Field that you want to be populated and sent to the parcel application during manifesting. Fields related to pick work assignments, customers, and orders are available for selection. The value for the selected field prints on the shipping label or is sent to the carrier, or both. For example, a customer may require the order number to be printed on the shipping label for receiving purposes at the receiving site, or that the account number is sent to the carrier for COD shipments so that it can be reported back when payment is sent from carrier to shipper. |
        
    4.  Click **Save**.
    5.  Click **Apply**.
9.  To define the order types for which a shipment's route-to address is validated:
    
    **Note**: When a shipment that includes a selected order type is created, and a carrier and service level is set on the shipment (either at creation or through a non-parcel selection rule), the application sends the shipment's route-to address to the integrated parcel application for validation with the shipment's carrier. See [Parcel address validation and carrier selection](#Parcel_address_validation_and_carrier_selection).
    
    1.  Under **ADDRESS VALIDATION AND CARRIER SELECTION**, click **Order Types**.
    2.  In the **Available** column, select the check box next to each order type enabled for address validation.
    3.  Click **Apply**.
10.  In a 3PL environment, to define the clients that prevent allocation until address validation and carrier selection are successful: 
     1.  Under **ADDRESS VALIDATION AND CARRIER SELECTION**, click **Clients**.
     2.  In the **Available** column, select the check box next to each client.
     3.  Click **Apply**.
11.  Click **Save**.

## Parcel fields

 
| Field | Description |
| --- | --- |
| Parcel Service | Service URL for the Parcel Handler instance that you want to integrate with Warehouse Management. The URL includes the host name, port number, and a constant value (service). The required format for the URL is http://<Host Name>:<Port Number>/service. For example, http://myserver:4000/service.<br > If Parcel Handler is installed in the same instance as Warehouse Management, then the Parcel Handler URL will be the same as the Warehouse Management URL. |
| Default Country | Value that is used as the country code if no country is defined in the shipment's route-to address. Defining a default country is useful if you have addresses that are in the same country, but the country codes are blank; for example, because the host application from which you download address information does not specify the country. |
| Parcel Shipment Paperwork | Determines which application will print the shipping paperwork.<br>-   • **WM**: Select if you are using a parcel application integrated through Parcel Handler.
<br>-   • **Parcel**: Not currently used. |
| Multi-Package Shipments | Determines when the parcel application will rate packages for a multi-package shipment.<br>-   • **Each package**: Select if you are using a parcel application integrated through Parcel Handler.
<br>-   • **After final package**: Not currently used. |
| Bundle After Manifesting | If Yes, the application allows you to add a manifested parcel to a new or existing bundled parcel LPN. During the process, the application automatically voids the parcel from the manifest before adding it to the bundled parcel LPN.<br > If No, the application does not allow you to bundle packages that have been manifested. |
| Allow Pre Manifesting | Not currently used. |
| Use Delivery Date | Not currently used. |
| Manifest Before Staging | Not currently used. |
| Prevent Allocation on Failure | If Yes, then the application prevents the allocation of any shipment with a parcel validation status of Pending, In Progress, or Failed. Parcel address validation and carrier selection is useful to prevent manifesting errors due to an incorrect or incomplete address, and to ensure the lowest-cost carrier and service level is selected (if the shipment is created without a carrier). Select Yes to ensure that parcel validation of a shipment's route-to address and carrier selection must be completed successfully before the application will allocate the shipment.<br > If No, then the application will not prevent the allocation of shipments that are pending validation, are in the process of being validated, or have failed validation.<br > See [Parcel address validation and carrier selection](#Parcel_address_validation_and_carrier_selection). |

## Parcel Handler Payment Terms fields

 
| Field | Description |
| --- | --- |
| Third Party Parcel System | Third-party parcel application (integrated through Parcel Handler). |
| Payment Code | Carrier-specific code for the payment term. A payment term specifies how parcel shipping charges are paid (such as collect on delivery, prepaid, or bill recipient). |
| Carrier Code | Unique code that is used to identify the carrier. A carrier delivers inbound inventory to the warehouse or outbound shipments to a customer. |
| Description | Text that defines the payment term. |
| Short Description | Brief description of the payment term. |

## Parcel Handler Package Codes fields

 
| Field | Description |
| --- | --- |
| Third Party Parcel System | Third-party parcel application (integrated through Parcel Handler). |
| Package Code | Unique identifier for the package. A package code specifies the type of packaging (such as envelope, package, box, tube, or custom package) that a carrier supports. Package codes are carrier specific and are used to ensure that the proper shipping rate is applied based on the packaging that is used. |
| Carrier Code | Unique code that is used to identify the carrier. A carrier delivers inbound inventory to the warehouse or outbound shipments to a customer. |
| Description | Text that defines the package code. |
| Short Description | Brief description of the package code. |

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2023 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
