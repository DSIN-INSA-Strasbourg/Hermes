<!--
Hermes : Change Data Capture (CDC) tool from any source(s) to any target
Copyright (C) 2023 INSA Strasbourg

This file is part of Hermes.

Hermes is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Hermes is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Hermes. If not, see <https://www.gnu.org/licenses/>.
-->

# `usersgroups_adwinrm` client plugin

{{% notice style="warning" title="pywinrm is very slow" %}}
As pywinrm spawn a new terminal and a new Powershell instance each time you run a command, it is really slow.  
This plugin is kept just in case, but you **really** should consider using `usersgroups_adpypsrp` client plugin instead when possible : it is more than 20 times faster (!).  
The configuration is similar on both plugin (excepted `hermes-client-usersgroups_adwinrm.WinRM`).
{{% /notice %}}

## Description

This client will handle Users, Groups and UserPasswords events, and store data into an Active Directory through Powershell commands across pywinrm.

The settings list `standardAttributes` contains available cmdlet parameters used for Users ([`New-ADUser`](https://learn.microsoft.com/en-us/powershell/module/activedirectory/new-aduser) / [`Set-ADUser`](https://learn.microsoft.com/en-us/powershell/module/activedirectory/set-aduser)) and Groups ([`New-ADGroup`](https://learn.microsoft.com/en-us/powershell/module/activedirectory/new-adgroup) / [`Set-ADGroup`](https://learn.microsoft.com/en-us/powershell/module/activedirectory/set-adgroup)).
The settings list `otherAttributes` may contains available LDAP display name (`ldapDisplayName`) attributes to manage those that are not represented by cmdlet parameters for Users and Groups.

The local Datamodel keys MUST exist in `standardAttributes` or `otherAttributes`, and will be used as cmdlet parameters with associated values, allowing to handle every AD attributes.

The `GroupMembers` will only associate a `User` with a `Group`, and can't handle nested groups.

To avoid security issues and corner cases with trashbin, a complex random password is set when user is created. This unknown password will be overwritten by next `UserPassword` event of the `User`. This avoids having an enabled account with no password.

The trashbin will only disable the account.

## Configuration

Nothing to configure for the plugin.

```yaml
hermes-client-usersgroups_adwinrm:
  WinRM:  # For options details, you may look at https://github.com/diyan/pywinrm/#run-process-with-low-level-api-with-domain-user-disabling-https-cert-validation
    # MANDATORY : AD server URI and port
    host: radon1.in.insa-strasbourg.fr
    port: 5986
    # MANDATORY : AD server credentials
    login: administrator
    password: "s3cReT_p4s5w0rD"
    # Default : validate. Set 'ignore' to disable
    server_cert_validation: ignore

  AD_domain:
    # MANDATORY : AD domain name and DN
    name: in.insa-strasbourg.fr
    dn: DC=in,DC=insa-strasbourg,DC=fr
    # MANDATORY : OUs where Users and Groups will be stored
    users_ou: OU=INSA,OU=People,DC=in,DC=insa-strasbourg,DC=fr
    groups_ou: OU=INSA,OU=Groups,DC=in,DC=insa-strasbourg,DC=fr

  # Defines cmdlet parameters that can be set, and the valid type of the associated value
  # You really should set it as is.
  standardAttributes:
    Users:
      AccountExpirationDate: "<DateTime>"
      AccountNotDelegated: "<Boolean>"
      AllowReversiblePasswordEncryption: "<Boolean>"
      AuthenticationPolicy: "<ADAuthenticationPolicy>"
      AuthenticationPolicySilo: "<ADAuthenticationPolicySilo>"
      AuthType: "<ADAuthType>"
      CannotChangePassword: "<Boolean>"
      ChangePasswordAtLogon: "<Boolean>"
      City: "<String>"
      Company: "<String>"
      CompoundIdentitySupported: "<Boolean>"
      Country: "<String>"
      # Credential: "<PSCredential>" # Useless : Specifies the user account credentials to use to perform this task
      Department: "<String>"
      Description: "<String>"
      DisplayName: "<String>"
      Division: "<String>"
      EmailAddress: "<String>"
      EmployeeID: "<String>"
      EmployeeNumber: "<String>"
      Enabled: "<Boolean>"
      Fax: "<String>"
      GivenName: "<String>"
      HomeDirectory: "<String>"
      HomeDrive: "<String>"
      HomePage: "<String>"
      HomePhone: "<String>"
      KerberosEncryptionType: "<ADKerberosEncryptionType>"
      LogonWorkstations: "<String>"
      Manager: "<ADUser>"
      MobilePhone: "<String>"
      Office: "<String>"
      OfficePhone: "<String>"
      Organization: "<String>"
      OtherName: "<String>"
      PasswordNeverExpires: "<Boolean>"
      PasswordNotRequired: "<Boolean>"
      POBox: "<String>"
      PostalCode: "<String>"
      # PrincipalsAllowedToDelegateToAccount: "<ADPrincipal[]>" # Won't be set
      ProfilePath: "<String>"
      SamAccountName: "<String>"
      ScriptPath: "<String>"
      # Server: "<String>" # Useless : Specifies the Active Directory Domain Services instance to connect to
      SmartcardLogonRequired: "<Boolean>"
      State: "<String>"
      StreetAddress: "<String>"
      Surname: "<String>"
      Title: "<String>"
      # TrustedForDelegation: "<Boolean>" # Won't be set
      UserPrincipalName: "<String>"

    Groups:
      AuthType: "<ADAuthType>"
      # Credential: "<PSCredential>" # Useless : Specifies the user account credentials to use to perform this task
      Description: "<String>"
      DisplayName: "<String>"
      GroupCategory: "<ADGroupCategory>"
      GroupScope: "<ADGroupScope>"
      HomePage: "<String>"
      ManagedBy: "<ADPrincipal>"
      SamAccountName: "<String>"
      # Server: "<String>" # Useless : Specifies the Active Directory Domain Services instance to connect to

  # Defines LDAP display name (ldapDisplayName) to handle, that are not handled with standardAttributes.
  # You can set your desired values. The values below are just here for example.
  otherAttributes:
    Users:
      otherMobile: "<String[]>"
      otherTelephone: "<String[]>"
      url: "<String[]>"
```

## Datamodel

The following data types may be set up :

- `Users` : requires the attribute `SamAccountName` to be set
- `UserPasswords` : obviously require `Users`, and requires the following attribute names `user_pkey` corresponding to the primary keys of `Users`, and the attribute `password`. All other attributes will be ignored
- `Groups` : requires the attribute `SamAccountName` to be set
- `GroupsMembers` : obviously require `Users` and `Groups`, and requires the following attribute names `user_pkey` `group_pkey` corresponding to the primary keys of `Users` and `Groups`. All other attributes will be ignored

```yaml
  datamodel:
    Users:
      hermesType: your_server_Users_type_name
      attrsmapping:
        user_pkey: user_primary_key_on_server
        SamAccountName: login_on_server
        UserPrincipalName: "{{ login_on_server ~ '@YOU.AD.DOMAIN.TLD' }}"
        # Not mandatory, only for example :
        MobilePhone: "{{ (mobile | default([None]))[0] }}" # <String>
        otherMobile: "{{ (mobile | default([]))[1:]  }}" # <String[]>
        # ...

    UserPasswords:
      hermesType: your_server_UserPasswords_type_name
      attrsmapping:
        user_pkey: user_primary_key_on_server
        password: cleartext_password_on_server
        # ...

    Groups:
      hermesType: your_server_Groups_type_name
      attrsmapping:
        group_pkey: group_primary_key_on_server
        SamAccountName: group_name_on_server
        # ...

    GroupsMembers:
      hermesType: your_server_GroupsMembers_type_name
      attrsmapping:
        user_pkey: user_primary_key_on_server
        group_pkey: group_primary_key_on_server
        # ...
```
