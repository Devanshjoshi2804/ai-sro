---
title: "System Security policies"
url: "https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/policies/system_security_policies.htm"
source: "/content/policies/system_security_policies.htm"
toc_path:
  - "Administration"
  - "System Administrator"
  - "Configuration"
  - "Policy"
  - "System Security policies"
sections:
  - "Always enforce password format check policy"
  - "Case insensitive passwords policy"
  - "Default password policy"
  - "Digital signatures policy"
  - "Disable account after password expiration policy"
  - "Format rules progression policy"
  - "History check parameters policy"
  - "LDAP authorization policy"
  - "Max failed login attempts policy"
  - "Maximum length check parameters policy"
  - "Minimum length check parameters policy"
  - "Password expiration time policy"
  - "Password expiration warning policy"
  - "Revoke user session on password change policy"
images: []
source_sha1: 4ae2389de033a89dffcee36ea8b7563d733f4a29
---
# System Security policies

You use the System Security (SYSTEM-SECURITY) policies to configure settings for system-level security control including digital signatures, LDAP authorization, the maximum number of log in attempts available to a user, and whether to expire a user's session when the password on a user account is changed.

In addition, the System Security policies specify rules for password formats, such as minimum length, whether to always enforce password format requirements, and operations associated with password aging, such as the number of days a password is valid.

You use Policy Maintenance to maintain System Security policies.

**IMPORTANT**: These policies are global and cannot be overridden by warehouse.

## Always enforce password format check policy

The Always enforce password format check (SYSTEM-SECURITY/PASSWORD-FORMAT/FORCE-PASSWORD-FORMAT-CHECK) policy determines whether new passwords, modified passwords, and default passwords used when copying users must meet the rules defined in the Format Rules Progression policy.

You can configure the following DETAILS field for this policy:

-   **Return Number 1**: Specifies whether the policy is enabled. A value of 1 is enabled, 0 is disabled. The policy is enabled by default.

## Case insensitive passwords policy

The Case insensitive passwords (SYSTEM-SECURITY/PASSWORD-FORMAT/CASE-INSENSITIVE) policy converts all characters that a user enters for a password to uppercase letters, eliminating the need to match upper and lowercase letters when entering a password. For example, when the policy is enabled a user can enter **Password** or **password** and both are converted to **PASSWORD**. When this policy is disabled, passwords are case sensitive.

You can configure the following DETAILS field for this policy:

-   **Return Number 1**: Specifies whether the policy is enabled. A value of 1 is enabled, 0 is disabled. The policy is disabled by default.
    
    **IMPORTANT**: It is recommended that you do not change this policy value after passwords are stored in the production database as doing so can prevent users from accessing the application. If you are required to update this policy in a production environment, ensure that the users have the ability to access the application after the policy is updated. For example, you can update user accounts with a temporary password, and then configure user accounts to change the password on next login to a value that meets the criterion of the updated policy. See [Add or modify a user](../../authorization/users.md).
    

## Default password policy

The Default password (SYSTEM-SECURITY/PASSWORD-FORMAT/DEFAULT-PASSWORD) policy specifies a password to use when copying users. When a default password is specified, the password is displayed as asterisks in the **Password** field on the Copy Users page.

You can configure the following DETAILS field for this policy:

-   **Return String 1**: Default password.
    
    **Note**: If the Always enforce password format check policy is enabled, then the default password must meet the criteria defined in the Password Format Rules Progression policy.
    

## Digital signatures policy

The Digital signatures (SYSTEM-SECURITY/USER-SECURITY/SIGNATURE\_EXPIRATION\_TIME) policy defines the number of minutes prior to password expiration that a login message is displayed. A password is used as a digital authorization (a "digital signature") for an operation. For example, if you require a digital signature when changing lot numbers, users are prompted to re-enter their passwords when starting the task, and if they have not completed the task prior to the digital signature expiration time, users are prompted to re-enter their passwords.

You can configure the following DETAILS field for this policy:

-   **Return Number 1**: Number of minutes a user's password is valid. The default value is 3.

## Disable account after password expiration policy

The Disable account after password expiration (SYSTEM-SECURITY/PASSWORD-AGING/DISABLE-INTERVAL DAYS) policy determines the number of days following a user's password expiration that an account will remain active.

You can configure the following DETAILS field for this policy:

-   **Return Number 1**: Integer representing the number of days following password expiration that an account will remain active. If the password is not updated within the assigned number of days, the account will be disabled. The default value is 120.

## Format rules progression policy

The Format rules progression (SYSTEM-SECURITY/PASSWORD-FORMAT/EXECUTE-SYNTAX) policy defines a list of commands or rules that are used to validate the complexity of a password. Commands are defined as policy details and may require related policy definitions to be enabled or disabled for the command to execute. For example, the check minimum password length command requires the Minimum length check parameters policy have a minimum length value.

**Note**: This policy defines which rules are used and in what order. The Always enforce password format check policy enables this policy.

When a password is added or modified, all enabled commands are executed in the priority indicated. If any of the commands fail, the password is rejected.

You can configure the following DETAILS fields for this policy:

-   **Return Number 1**: Specifies whether the command is enabled. A value of 1 is enabled, 0 is disabled.
-   **Return String 1**: Command to be executed. The following commands are the default values:
    -   **check password character types**: Verifies that the password contains at least one character from three of the following classes:
        -   Uppercase alpha characters \[A-Z\]
        -   Lowercase alpha characters \[a-z\]
        -   Numeric digits \[0-9\]
        -   Non-alphanumeric characters such as spaces or punctuation
            
            **Note**: This command requires the Case Insensitive Passwords policy be disabled.
            
    -   **check password maximum length**: Verifies the password length does not exceed the value defined in the Maximum Length Check Parameters policy.
    -   **check password minimum length**: Verifies the password length based on the value defined in the Minimum Length Check Parameters policy.
    -   **check password history**: Verifies the password has not been repeated within a given time frame as indicated by the values in the History Check Parameters policy.
-   **Sort Sequence**: Order in which the application processes policy details in relation to other details defined for the same policy.

## History check parameters policy

The History check parameters (SYSTEM-SECURITY/PASSWORD-FORMAT/HISTORY-CHECK) policy defines how often a user can repeat a password by checking an updated password against passwords previously used within a given time period. This policy is used by the Format rules progression policy check password history command, which must be enabled for this parameter to have any effect.

You can configure the following DETAILS fields for this policy:

-   **Return Number 1**: Number of past passwords that are checked against a new password. The default value is 6.
-   **Return Number 2**: Number of days back to check for password repeats. The default value is 356.

## LDAP authorization policy

The LDAP authorization (SYSTEM-SECURITY/LDAP-AUTHORIZATION/ENABLED) policy determines whether the SCE client window is enabled to use the Lightweight Directory Access Protocol (LDAP) authentication method. LDAP is an authentication type that relies on an LDAP server to verify a user's identity.

You can configure the following DETAILS field for this policy:

-   **Return Number 1**: Specifies whether the policy is enabled. A value of 1 is enabled, 0 is disabled. When enabled and LDAP authentication is configured, LDAP authentication can be used in place of native authentication for user access. This policy is disabled by default.

## Max failed login attempts policy

The Max failed login attempts (SYSTEM-SECURITY/PASSWORD-AGING/MAX-FAILED-LOGIN-ATTEMPTS) policy determines the number of failed login attempts a user is allowed before the user account is set to an inactive status. A user is unable to log in until the user account is updated to an active status.

You can configure the following DETAILS field for this policy:

-   **Return Number 1**: Number of login attempts a user is given prior to the user account status being changed to inactive. The default value is 0.

## Maximum length check parameters policy

The Maximum length check parameters (SYSTEM-SECURITY/PASSWORD-FORMAT/MAXIMUM-LENGTH) policy defines the maximum number of characters allowed in a password. This policy is used by the Format rules progression policy check password maximum length command, which must be enabled for this parameter to have any effect.

You can configure the following DETAILS field for this policy:

-   **Maximum Length**: Maximum number of characters allowed in the password. There is no default value.

## Minimum length check parameters policy

The Minimum length check parameters (SYSTEM-SECURITY/PASSWORD-FORMAT/MINIMUM-LENGTH) policy defines the minimum number of characters required in a password. This policy is used by the Format Rules Progression policy check password minimum length command, which must be enabled for this parameter to have any effect.

You can configure the following DETAILS field for this policy:

-   **Return Number 1**: Minimum number of characters required in the password. The default value is 8.

## Password expiration time policy

The Password expiration time (SYSTEM-SECURITY/PASSWORD-AGING/EXPIRE-INTERVAL-DAYS) policy determines the number of days that a user's password is valid.

You can configure the following DETAILS field for this policy:

-   **Return Number 1**: Number of days a user's password is valid. The default value is 90.

## Password expiration warning policy

The Password expiration warning (SYSTEM-SECURITY/PASSWORD-AGING/EXPIRE-WARNING-DAYS) policy determines the number of days prior to password expiration that a warning message will be displayed.

You can configure the following DETAILS field for this policy:

-   **Return Number 1**: Number of days prior to password expiration that the expiration warning message will be displayed. The default value is 7.

**Note**: If the password is not updated within an assigned number of days, the account will be disabled.

## Revoke user session on password change policy

The Revoke user session on password change (SYSTEM-SECURITY/PASSWORD-AGING/REVOKE-USER-SESSION-ON-PWD-CHANGE) policy determines whether an SCE client session is expired when the password associated with the user account is changed. When a session expires, the user is logged out of the application. To resume the session, the user must log in using the new password.

You can configure the following DETAILS field for this policy:

-   **Return Number 1**: Specifies whether the policy is enabled. A value of 1 is enabled, 0 is disabled. The policy is enabled by default.

Supply Chain Execution Web Applications 2022.1.0.0 Help | Last updated: 31 May 2024

© 2014-2024 Blue Yonder Group, Inc. All rights reserved. [Legal notice](https://bf56-kms-wms-web-np2.jdadelivers.com/web/help/content/legal_notice.htm)

Contact: [Customer Support](https://success.blueyonder.com/ "Blue Yonder Customer Support") | [Services](https://blueyonder.com/services "Blue Yonder Services")
