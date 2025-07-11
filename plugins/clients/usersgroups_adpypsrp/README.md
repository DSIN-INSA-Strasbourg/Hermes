<!--
Hermes : Change Data Capture (CDC) tool from any source(s) to any target
Copyright (C) 2023, 2024, 2025 INSA Strasbourg

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

# `usersgroups_adpypsrp` client plugin

## Description

This client will handle Users, Groups and UserPasswords events, and store data into an Active Directory through Powershell commands across pypsrp.

The settings list `standardAttributes` contains available cmdlet parameters used for Users ([`New-ADUser`](https://learn.microsoft.com/en-us/powershell/module/activedirectory/new-aduser) / [`Set-ADUser`](https://learn.microsoft.com/en-us/powershell/module/activedirectory/set-aduser)) and Groups ([`New-ADGroup`](https://learn.microsoft.com/en-us/powershell/module/activedirectory/new-adgroup) / [`Set-ADGroup`](https://learn.microsoft.com/en-us/powershell/module/activedirectory/set-adgroup)).
The settings list `otherAttributes` may contains available LDAP display name (`ldapDisplayName`) attributes to manage those that are not represented by cmdlet parameters for Users and Groups.

The local Datamodel keys MUST exist in `standardAttributes` or `otherAttributes`, and will be used as cmdlet parameters with associated values, allowing to handle every AD attributes.

The `GroupsMembers` will only associate a `User` with a `Group`.
The `SubGroupsMembers` will only associate a `Group` with a `Group`, allowing to handle nested groups.

To avoid security issues and corner cases with trashbin, a complex random password is set when user is created. This unknown password will be overwritten by the next `UserPassword` event of the `User`. This avoids having an enabled account with no password.

The trashbin will only disable the account.

## Configuration

```yaml
hermes-client-usersgroups_adpypsrp:
  WinRM:  # For options details, you may look at https://pypi.org/project/pypsrp/ - "Connection"
    # MANDATORY: AD server URI and port
    host: radon1.in.insa-strasbourg.fr
    port: 5986
    # MANDATORY: AD server credentials
    login: administrator
    password: "s3cReT_p4s5w0rD"
    # Default: true
    ssl: true
    # Default: true
    ssl_cert_validation: false
    # Default: true
    credssp_disable_tlsv1_2: true
    # Default: "auto". Valid values are [auto, always, never]
    encryption: always
    # Default: "wsman"
    path: "wsman"
    # Default: "negotiate". Valid values are [basic, certificate, negotiate, ntlm, kerberos, credssp]
    auth: kerberos
    # Default: "WSMAN". Override the service part of the calculated SPN used when authenticating the server.
    # This is only valid if negotiate auth negotiated Kerberos or kerberos was explicitly set.
    # If you obtain an error "Server not found in Kerberos database", you may try to set HTTP here.
    negotiate_service: WSMAN

  AD_domain:
    # MANDATORY: AD domain name and DN
    name: in.insa-strasbourg.fr
    dn: DC=in,DC=insa-strasbourg,DC=fr
    # MANDATORY: OUs where Users and Groups will be stored
    users_ou: OU=INSA,OU=People,DC=in,DC=insa-strasbourg,DC=fr
    groups_ou: OU=INSA,OU=Groups,DC=in,DC=insa-strasbourg,DC=fr

  # Optional, allows to force each user to be added to the specified group list.
  # Group membership is only added when the user is created: any change to this parameter's value
  # will only impact users created subsequently
  Users_mandatory_groups:
    - MandatoryGroup1
    - MandatoryGroup2

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
      # Credential: "<PSCredential>" # Useless: Specifies the user account credentials to use to perform this task
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
      # Server: "<String>" # Useless: Specifies the Active Directory Domain Services instance to connect to
      SmartcardLogonRequired: "<Boolean>"
      State: "<String>"
      StreetAddress: "<String>"
      Surname: "<String>"
      Title: "<String>"
      # TrustedForDelegation: "<Boolean>" # Won't be set
      UserPrincipalName: "<String>"

    Groups:
      AuthType: "<ADAuthType>"
      # Credential: "<PSCredential>" # Useless: Specifies the user account credentials to use to perform this task
      Description: "<String>"
      DisplayName: "<String>"
      GroupCategory: "<ADGroupCategory>"
      GroupScope: "<ADGroupScope>"
      HomePage: "<String>"
      ManagedBy: "<ADPrincipal>"
      SamAccountName: "<String>"
      # Server: "<String>" # Useless: Specifies the Active Directory Domain Services instance to connect to

  # Defines LDAP display name (ldapDisplayName) to handle, that are not handled with standardAttributes.
  # You can set your desired values. The values below are just here for example.
  otherAttributes:
    Users:
      otherMobile: "<String[]>"
      otherTelephone: "<String[]>"
      url: "<String[]>"

  # Optional random password generation settings. Default: values specified below
  # Random password is generated to initialize a user whose password is not yet available,
  # or when the user password is removed but the user still exists
  random_passwords:
    # Password length
    length: 32
    # If true, the generated password may contains some upper case letters
    with_upper_letters: true
    # The generated password will contain at least this number of upper case letters
    minimum_number_of_upper_letters: 1
    # If true, the generated password may contains some lower case letters
    with_lower_letters: true
    # The generated password will contain at least this number of lower case letters
    minimum_number_of_lower_letters: 1
    # If true, the generated password may contains some numbers
    with_numbers: true
    # The generated password will contain at least this number of numbers
    minimum_number_of_numbers: 1
    # If true, the generated password may contains some special chars
    with_special_chars: true
    # The generated password will contain at least this number of special chars
    minimum_number_of_special_chars: 1
    # If true, the generated password won't contains the chars specified in 'ambigous_chars_dictionary'
    avoid_ambigous_chars: false
    # The dictionary of ambigous chars (case sensitive) that may be forbidden in password, even if some are present in other dictionnaries
    ambigous_chars_dictionary: "lIO01"
    # The dictionary of letters (case unsensitive) allowed in password
    letters_dictionary: "abcdefghijklmnopqrstuvwxyz"
    # The dictionary of special chars allowed in password
    special_chars_dictionary: "!@#$%^&*"
```

## Datamodel

The following data types may be set up:

- `Users`: requires the attribute `SamAccountName` to be set
- `UserPasswords`: obviously requires `Users`, and requires the attribute `user_pkey` corresponding to the primary keys of `Users`, and the attribute `password`. All other attributes will be ignored
- `Groups`: requires the attribute `SamAccountName` to be set
- `GroupsMembers`: obviously requires `Users` and `Groups`, and requires the attributes `user_pkey` and `group_pkey` corresponding to the primary keys of `Users` and `Groups`. All other attributes will be ignored
- `SubGroupsMembers`: obviously requires `Groups`, and requires that the `subgroup_pkey` and `group_pkey` attributes match the primary key of the subgroup to be assigned, and that of the assignment group, respectively. All other attributes will be ignored

```yaml
  datamodel:
    Users:
      hermesType: your_server_Users_type_name
      attrsmapping:
        user_pkey: user_primary_key_on_server
        SamAccountName: login_on_server
        UserPrincipalName: "{{ login_on_server ~ '@YOU.AD.DOMAIN.TLD' }}"
        # Not mandatory, only for example:
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

    SubGroupsMembers:
      hermesType: your_server_SubGroupsMembers_type_name
      attrsmapping:
        subgroup_pkey: subgroup_primary_key_on_server
        group_pkey: group_primary_key_on_server
        # ...
```
