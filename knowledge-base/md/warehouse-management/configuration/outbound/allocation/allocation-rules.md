---
title: "Allocation Rules"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/allocation_rules.htm"
source: "/content/allocation_rules.htm"
toc_path:
  - "Warehouse Management"
  - "Configuration"
  - "Outbound"
  - "Allocation"
  - "Allocation Rules"
sections:
  - "Allocation rules processing"
  - "Allocation rule use scenarios"
  - "Delete an allocation rule"
  - "View allocation rules"
images: []
source_sha1: 4f6cbe7043441772afc2cb422c6cfac6bd5af99a
---
# Allocation Rules

An allocation rule is a processing command that specifies the inventory attribute values that are acceptable to fulfill an order line, work order line, or bill of materials (BOM) line. The attributes for which you can specify values for an allocation rule include lot, origin, revision level, manufactured date, expiration date, any user-defined inventory fields and, if customs functionality is installed, customs attributes.

You add and modify allocation rules inline with creating an order line, assembly work order line, disassembly work order, or BOM line. A simple allocation rule consists of a single value for one or more attributes; a complex allocation rule consists of multiple values for one or more attributes. After you create an allocation rule, it is saved in the application and is available for selection when you create or modify another order line, work order line, or BOM line.

If your host system supports it, rule information can be downloaded from the host with the order, work order, or BOM information. A rule can be assigned to multiple order lines. While it is assigned, it cannot be modified; however, you can select an assigned rule, save it with a new rule name, and then make the necessary changes to the new rule.

## Allocation rules processing

The application uses allocation rules during the following processes:

-   Order processing to group order lines based on values defined in allocation rules
-   Work order processing to specify the component items that are used to produce a finished good
-   Disassembly processing to specify which finished good should be allocated and broken down into its components items
-   Cross docking and pick replacement to ensure the picks match the rules selected for the order lines
-   Receiving by comparing the rules associated with replenishments to the planned inbound orders to determine whether a piece of transport equipment is hot
-   Picking to ensure that scanned inventory matches the rule values and, if it does not, disallows the pick
-   Dynamic slotting (if Slotting is installed and enabled in Warehouse Management), to dynamically create temporary allocation rules based on rules associated with replenishments, and delete the temporary rules after the slotting process has been completed

## Allocation rule use scenarios

Allocation rules are used to define inventory attribute values that you want to be included or not included during allocation to fulfill an order line, work order line, or BOM line. These rules provide the ability for you to specify one, multiple, or a range of values or exceptions for one or more specific attributes. The application supports the definition of the following common inventory allocation scenarios:

-   **Multiple values**: You can request inventory from the warehouse that matches multiple values that you define. For example, if an item is tracked by origin, you can specify that the origin must equal CNTRYA or CNTRYB to be acceptable for allocation.
-   **Multiple values for different attributes**: You can request inventory from the warehouse that matches multiple values that you define for various attributes. For example, if an item is tracked by lot and origin, you can specify that the lot for the item must equal LOTA and the origin must equal CNTRYA, CNTRYB, or CNTRYC to be acceptable for allocation.
-   **Multiple exceptions**: You can request inventory from the warehouse that excludes specific values. For example, for a lot-tracked item, you can specify that the lot for the item must not equal LOTA or LOTB to be acceptable for allocation.
-   **Multiple values but limit the number of different values**: You can request inventory from the warehouse that matches any of several values, but does not include more than a specific number of different values. For example, for manufacture or expiration date-controlled items, you can request inventory from the warehouse that meets a range or list of expiration dates that are acceptable to fulfill the order, along with a requirement that no more than two different expiration dates be shipped for the order line. The rule would specify, for example, that the expiration date must be equal to 04/18/21, 04/20/21, or 04/22/21, but must not include more than two different dates (MAX COUNT is 2) to be acceptable for allocation.
-   **Range of values and an exception**: You can request inventory from the warehouse that matches a range of values (such as dates), but does not include one or more specific values. For example, you can specify that the manufacture date for an order line must be later than or equal to the manufacture date specified on the order line, but must not be the manufacture date listed as an exclusion on the order line. The rule would specify, for example, a manufacture date that is greater than or equal to 0919 but must not equal 0926 to be acceptable for allocation.

## Delete an allocation rule

You cannot delete an allocation rule that is assigned to an order line, work order line, or BOM line.

1.  Select **Configuration > Outbound > Allocation > Allocation Rules**.
    
2.  In the top grid, select the allocation rule.
    
3.  From the **Actions** drop-down list, select **Delete**. A confirmation message is displayed.
    
4.  Click **OK**.
    

## View allocation rules

1.  Perform one of the following tasks:
    
    -   Select **Configuration > Outbound > Allocation > Allocation Rules**.
        
    -   Select **Configuration > Outbound > Allocation > >Allocation Rules > Order Line Allocation Rules**.
        
    -   Select **Configuration > Outbound > Allocation > Allocation Rules > Work Order Line Allocation Rules**.
        
    -   Select **Configuration > Outbound > Allocation > Allocation Rules > BOM Allocation Rules**.
        
2.  In the top grid, select an allocation rule.
    
3.  In the bottom grid, view the information related to the allocation rule, order lines, work order lines, or BOM lines.
    

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
