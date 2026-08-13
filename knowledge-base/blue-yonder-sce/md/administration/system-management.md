---
title: "System Management"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/admin/system_management.htm"
source: "/content/admin/system_management.htm"
toc_path:
  - "Administration"
  - "System Management"
sections:
  - "Portal server instance configuration files"
  - "View and run health checks"
  - "Download a support file"
  - "View instance details"
images:
  - "/content/resources/images/image569280.png"
  - "/content/resources/images/image524298.png"
  - "/content/resources/images/image524298.png"
source_sha1: 4aae0fdb8fa6a3b7be887aae10ca861e4d321d53
---
# System Management

You use the System Management Monitor page to view the state of a portal server instance and configuration information for all portal server nodes connected to the network. This page displays your installation configuration.

The Monitor page displays the following links:

-   **Health Checks**: **<_Number and status of checks that were run_>**: Displays a list of portal server framework health checks. A health check is a test that assesses an application's state, configuration, or data, such as whether page resources exist and are being returned by the Page Builder Discoverability API. You can view a list of the health checks that were run when the page was initially opened and read details about each health check, such as status and possible reasons why a health check may fail.
-   **Download Support Zip**: Downloads the portal server support ZIP file. A support file is a compressed folder that contains files that can help you identify and resolve system issues during troubleshooting.

The Monitor page also displays all portal server instance connections to other nodes in a network diagram. A node is a single installed instance that may be combined on a network with other nodes to make up a cluster. The diagram includes the following node types, represented in boxes:

-   **Portal**: Represents a portal server instance. In a clustered configuration, multiple portal server instances are displayed and numbered sequentially. When you select a portal node, the instance URL and a **More...** link are displayed. The **More...** link provides access to the Node Details - Portal page on which you can view configuration and environment details of the selected portal server instance and its server.
-   **App Server**: Represents an application server instance. Each application server instance is connected to a separate portal server instance, as indicated in the diagram by a line. When you select an App Server node, the status of the instance, the instance URL, and the applications available to the instance (configured in the rpweb file) are displayed.
-   **Proxy/LB**: Represents a proxy server or load balancer. Each portal server instance within a clustered configuration is connected to the same proxy server or load balancer, as indicated in the diagram by a line. When you select a proxy/LB node, the proxy server or load balancer URL is displayed.
    
    **Note**: If there are multiple Proxy/LB boxes in the diagram, one or more of the portal server instance rpweb files may have an incorrect URL for the proxy server or load balancer, set in the rpweb file as the server.baseURL value. To view the rpweb file, see [View instance details](#View_instance_details).
    

## Portal server instance configuration files

The Monitor page network diagram provides access to all portal server instances connected on the network. After selecting an instance, you gain read-only visibility to configuration files stored in the instance's **rpweb\\settings** folder. The following files provide helpful information for an Administrator to understand the portal server instance configuration:

**Note**: The **available-libsource.properties**, **dev-modes.xml**, and **test-modes.xml** files may also be displayed on this page, but are for internal use only.

-   **cache.properties**: Defines the configuration for in-memory caches.
-   **default-settings.xml**: Defines the configuration for the portal server instance including default values, all available configuration settings, and descriptions and examples for different use cases for the settings.
    
    **IMPORTANT**: Do not modify the default-settings file as this file is overwritten during upgrades. Any changes required to the portal server instance configuration should be made in the rpweb file.
    
-   **hikari.properties**: Provides information that can be helpful in monitoring the database connections managed within HikariCP, a Java Database Connectivity (JDBC) connection pool.
-   **jetty.properties**: Defines the configuration for Jetty properties, provides suggested settings (such as indicating the number of threads available to handle requests), and includes a link to Jetty documentation.
-   **logging-db-v1.xml**: Defines the configuration for the portal server instance's database logging as part of installation or upgrade tasks that use db command line tools, such as `db all`.
-   **logging-v1.xml**: Defines the configuration for the portal server instance's runtime logging and can include the following types of logging components:
    -   **Loggers**: Define which log events are sent to specific appenders, and what severity level the log event is assigned, such as DEBUG, WARN, ERROR, INFO, or OFF.
        
        **Note**: A severity level of OFF indicates that no events will be logged.
        
    -   **Appenders**: Define how log events look, to which output messages are sent, and how the output is handled (such as allowing a rolling file or limiting the file size).
    -   **Filters**: Determine if or how a log event should be published.
-   **management.properties**: Defines the configuration related to Java Management Extensions (JMX) including whether to include portal server instance monitoring within Java monitoring and diagnostics.
    
-   **modes.xml**: Defines the configuration for Java components and HTTP request paths.
-   **rpweb.xml**: Defines the instance-specific configurations required for the portal server instance to start, such as connections and site names specific to the instance. Settings in this file supersede those in the default-settings file. For example, values that you enter during the installation process, such as the instance name and port number, are saved in this file. You can also update settings that affect the web client display, such the how the navigation bar is displayed and the row height display for a grid. For information about updating the rpweb file and the available configuration options, see the _Supply Chain Execution Applications Administrator Guide_.
    

## View and run health checks

The first time that you open the Monitor page, the application automatically runs health checks and a summary of the results are displayed in the Health Checks link. You can view additional information about the health checks or use the page refresh tool to update the health checks results.

1.  Select **System Management > Monitor**.
2.  To run the health checks, click ![Refresh](../../images/resources/images/image569280.png). The health checks are run and the Health Checks summary is updated.
3.  To view a list of all the health checks that were run:
    1.  Click **Health Checks**. The Health Checks page is displayed.
    2.  When finished, click ![Close](../../images/resources/images/image524298.png).

## Download a support file

You can download a support file from the Monitor page. The support ZIP file includes folders and files that provide information about the portal server instance, and if the instance is part of a clustered configuration, all nodes within the cluster. See the support files information in the _Supply Chain Execution Applications Administrator Guide_.

1.  Select **System Management > Monitor**.
2.  Click **Download Support Zip**. The file is downloaded to the default download location of the computer on which the web client is running.

## View instance details

You can view detailed information about any node displayed on the Monitor page network diagram.

1.  Select **System Management > Monitor**.
2.  To view information for a portal server instance, click the **Portal** node, and then click **More...** The Node Details - Portal page is displayed.
    
    1.  To view instance configuration settings, under the **Configuration** tab, click a file name. The contents of the file are displayed on the page.
    
    **Note**: For descriptions of the files, see [Portal server instance configuration files](#Portal_server_instance_configuration_files).
    
    3.  To view information about the physical server on which the instance resides and other instance environment details, click the **Environment** tab and perform one or more of the following actions:
        -   To view a list of all environment variables that are set on the server, click **Environment Variables**.
        -   To view a list of the Java properties for the Java Virtual Machine on which the portal server instance is running, click **Java Properties**.
        -   To view information about the server, such as operating system information, CPU details, percentage of disk space used, and memory usage, click **System Information**.
        -   To identify current use of heap memory and delete any unused objects, click **System Information**, and then click **Run Garbage Collection**.
    4.  When finished, click ![Close](../../images/resources/images/image524298.png).
3.  To view information for an application server instance, click the **App Server** node. The instance status, the instance URL, and the applications available to the instance are displayed.
4.  To view the proxy server or load balancer URL, click the **Proxy/URL** node.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
