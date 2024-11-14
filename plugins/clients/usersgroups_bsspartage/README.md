<!--
Hermes : Change Data Capture (CDC) tool from any source(s) to any target
Copyright (C) 2024 INSA Strasbourg

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

# `usersgroups_bsspartage` client plugin

## Description

This client will handle Users, UserPasswords, Groups, GroupsMembers, GroupsSenders and Ressources events, and store data into the [PARTAGE](https://www.renater.fr/services/collaborer-simplement/partage/) dashboard through its API, handled by [libPythonBssApi](https://github.com/dsi-univ-rennes1/libPythonBssApi).

To avoid security issues, if no hash is available at user creation, a complex random password will be set. This unknown password will be changed when a `userPassword` attribute will be set to the `User` or to the `UserPassword`. This avoids having an enabled account with no password.

The trashbin will only disable the account.

## Configuration

You have to configure an `authentication` mapping containing all domains managed by this client as keys, and their API key as values.

```yaml
hermes-client-usersgroups_bsspartage:
  authentication:
    example.com: "Secret_API_key_of_example.com"
    subdomain.example.com: "Secret_API_key_of_subdomain.example.com"
  
  # When an attribute has no more value, the default behavior is to keep its latest value in place.
  # This setting allow to override this behaviour for the specified attributes, with the replacement values.
  # Please note that it is forbidden to set Users.userPassword, as the default behavior is to generate a new random password.
  # It is also forbidden to set null values, as this reverts to the default behavior. In this case, simply remove the affected attribute from this list.
  #
  # The values set below are the default values used if default_removed_values is not set
  default_removed_values:
    Users:
      co: ""
      company: ""
      description: ""
      displayName: ""
      facsimileTelephoneNumber: ""
      givenName: ""
      homePhone: ""
      initials: ""
      l: ""
      mobile: ""
      name: ""
      pager: ""
      postalCode: ""
      st: ""
      street: ""
      telephoneNumber: ""
      title: ""
      zimbraNotes: ""
      zimbraPrefMailForwardingAddress: ""
      zimbraMailCanonicalAddress: ""
      zimbraPrefFromDisplay: ""
      zimbraMailQuota: 0
    Groups:
      # Values should be set to empty strings, but a bug in API is ignoring them.
      # This bug has been notified to PARTAGE's team.
      description: "-" 
      displayName: "-"
      zimbraNotes: "-"
    Resources:
      co: ""
      description: ""
      l: ""
      postalCode: ""
      st: ""
      street: ""
      zimbraCalResBuilding: ""
      zimbraCalResContactEmail: ""
      zimbraCalResContactName: ""
      zimbraCalResContactPhone: ""
      zimbraCalResFloor: ""
      zimbraCalResLocationDisplayName: ""
      zimbraCalResRoom: ""
      zimbraCalResSite: ""
      zimbraNotes: ""
      zimbraCalResCapacity: "-1"

  # Optional random password generation settings. Default: values specified below
  # Random password is generated to initialize a user whose password is not yet available
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

- `Users`: for users accounts. Requires the attribute `name` and `sn` to be set, a facultative `aliases` attribute may bet set, and the others are attributes as defined and used by [libPythonBssApi](https://github.com/dsi-univ-rennes1/libPythonBssApi) and are facultative.
  Note that `zimbraAllowFromAddress`, `zimbraFeatureContactsEnabled` and `zimbraMailForwardingAddress` attributes are not supported by [libPythonBssApi](https://github.com/dsi-univ-rennes1/libPythonBssApi).
- `UserPasswords`: obviously require `Users`, and requires that its primary keys are corresponding to the primary keys of `Users`, and requires the attribute `userPassword` that have to contain a valid LDAP hash. All other attributes will be ignored. As the `userPassword` attribute can also be managed by `Users`, you have to choose: either you manage it by `Users`, or by `UserPasswords`, but in no case should you use both at the same time for obvious reasons.
- `Groups`: for groups and distribution lists. Requires the attribute `name` and `zimbraMailStatus` to be set, a facultative `aliases` attribute may bet set, and the others are attributes as defined and used by [libPythonBssApi](https://github.com/dsi-univ-rennes1/libPythonBssApi) and are facultative.
- `GroupsMembers`: to add users as group members. Obviously require `Users` and `Groups`, and requires the attributes `user_pkey` and `group_pkey` corresponding to the primary keys of `Users` and `Groups`. All other attributes will be ignored.
- `GroupsSenders`: to add users as group senders. Obviously require `Users` and `Groups`, and requires the attributes `user_pkey` and `group_pkey` corresponding to the primary keys of `Users` and `Groups`. All other attributes will be ignored.
- `Resources`: for resources. Requires the attribute `name`, `zimbraCalResType` and `displayName` to be set, and the others are attributes as defined and used by [libPythonBssApi](https://github.com/dsi-univ-rennes1/libPythonBssApi) and are facultative.

{{% notice warning %}}
If you're setting the `Users.zimbraCOSId`, you should avoid setting COS-managed attributes in your datamodel, as overriding the COS default value may lead to unexpected behaviours.
{{% /notice %}}

{{% notice warning %}}
Since the API does not allow renaming `Groups` and `Resources`, this operation is done by deleting the old instance and recreating the new one in the process. However, this can cause loss of links and information (e.g. resource calendars), and it is probably best to avoid these renames.
{{% /notice %}}

{{% notice tip %}}
To handle `Users.zimbraCOSId`, it is likely that your data source provides a name rather than the COSId. It is possible to declare a mapping table in Jinja directly in your configuration:

```yaml
  datamodel:
    Users:
      hermesType: your_server_Users_type_name
      attrsmapping:
        # ...
        zimbraCOSId: >-
          {{
              {
                'name_of_cos1': '11111111-1111-1111-1111-111111111111',
                'name_of_cos2': '22222222-2222-2222-2222-222222222222',
                'name_of_cos3': '33333333-3333-3333-3333-333333333333',
              }[zimbraCOSName_value_from_server | default('name_of_cos1') | lower]
              | default('11111111-1111-1111-1111-111111111111')
          }}
        # ...
```

{{% /notice %}}

```yaml
  datamodel:
    Users:
      hermesType: your_server_Users_type_name
      attrsmapping:
        # User primary email address <Valid email address>
        name: name_value_from_server
        # User last name <String>
        sn: sn_value_from_server

        # List of aliases for this user <String[]>
        aliases: aliases_value_from_server
        # User EPPN number <String>
        carLicense: carLicense_value_from_server
        # Country name <String>
        co: co_value_from_server
        # Company or institution name <String>
        company: company_value_from_server
        # Account description <String>
        description: description_value_from_server
        # Name displayed in emails <String>
        displayName: displayName_value_from_server
        # User fax <String>
        facsimileTelephoneNumber: facsimileTelephoneNumber_value_from_server
        # User first name <String>
        givenName: givenName_value_from_server
        # User home phone <String>
        homePhone: homePhone_value_from_server
        # Initial (Mr. or Mrs.) <String>
        initials: initials_value_from_server
        # User city <String>
        l: l_value_from_server
        # User mobile number <String>
        mobile: mobile_value_from_server
        # User shortcut number <String>
        pager: pager_value_from_server
        # Postal code <String>
        postalCode: postalCode_value_from_server
        # User state <String>
        st: st_value_from_server
        # User street <String>
        street: street_value_from_server
        # User phone <String>
        telephoneNumber: telephoneNumber_value_from_server
        # User title <String>
        title: title_value_from_server
        # Password hash <String>
        userPassword: userPassword_value_from_server
        # Account status (default active) <String(active, closed, locked)>
        zimbraAccountStatus: zimbraAccountStatus_value_from_server
        # Class of service Id <String>
        zimbraCOSId: zimbraCOSId_value_from_server
        # Briefcase tab <String (TRUE, FALSE)>
        zimbraFeatureBriefcasesEnabled: zimbraFeatureBriefcasesEnabled_value_from_server
        # Calendar tab <String (TRUE, FALSE)>
        zimbraFeatureCalendarEnabled: zimbraFeatureCalendarEnabled_value_from_server
        # Mail tab <String (TRUE, FALSE)>
        zimbraFeatureMailEnabled: zimbraFeatureMailEnabled_value_from_server
        # Allow user to specify forward address <String (TRUE, FALSE)>
        zimbraFeatureMailForwardingEnabled: zimbraFeatureMailForwardingEnabled_value_from_server
        # Options tab <String (TRUE, FALSE)>
        zimbraFeatureOptionsEnabled: zimbraFeatureOptionsEnabled_value_from_server
        # Tasks tab <String (TRUE, FALSE)>
        zimbraFeatureTasksEnabled: zimbraFeatureTasksEnabled_value_from_server
        # Hide in GAL <String (TRUE, FALSE)>
        zimbraHideInGal: zimbraHideInGal_value_from_server
        # 0=unlimited <Integer (bytes)>
        zimbraMailQuota: zimbraMailQuota_value_from_server
        # Free notes <String>
        zimbraNotes: zimbraNotes_value_from_server
        # Must change password at next login <String (TRUE, FALSE)>
        zimbraPasswordMustChange: zimbraPasswordMustChange_value_from_server
        # Forward address entered by user <Valid email address>
        zimbraPrefMailForwardingAddress: zimbraPrefMailForwardingAddress_value_from_server
        # Do not keep a copy of mails on the local client <String (TRUE, FALSE)>
        zimbraPrefMailLocalDeliveryDisabled: zimbraPrefMailLocalDeliveryDisabled_value_from_server
        # Email address visible for outgoing messages <String>
        zimbraMailCanonicalAddress: zimbraMailCanonicalAddress_value_from_server
        # Display name visible for outgoing messages <String>
        zimbraPrefFromDisplay: zimbraPrefFromDisplay_value_from_server

    UserPasswords:
      hermesType: your_server_UserPasswords_type_name
      attrsmapping:
        # Password hash <String>
        userPassword: userPassword_value_from_server

    Groups:
      hermesType: your_server_Groups_type_name
      attrsmapping:
        # Group primary email address <Valid email address>
        name: name_value_from_server
        # Discriminant distribution list/group <String (enabled, disabled)>
        zimbraMailStatus: zimbraMailStatus_value_from_server
        
        # List of aliases for this group <String[]>
        aliases: aliases_value_from_server
        # Group description <String>
        description: description_value_from_server
        # Display name <String>
        displayName: displayName_value_from_server
        # Report available shares to new members <String (TRUE, FALSE)>
        zimbraDistributionListSendShareMessageToNewMembers: zimbraDistributionListSendShareMessageToNewMembers_value_from_server
        # Hide group in GAL <String (TRUE, FALSE)>
        zimbraHideInGal: zimbraHideInGal_value_from_server
        # Free notes <String>
        zimbraNotes: zimbraNotes_value_from_server

    GroupsMembers:
      hermesType: your_server_GroupsMembers_type_name
      attrsmapping:
        user_pkey: user_pkey_value_from_server
        group_pkey: group_pkey_value_from_server

    GroupsSenders:
      hermesType: your_server_GroupsSenders_type_name
      attrsmapping:
        user_pkey: user_pkey_value_from_server
        group_pkey: group_pkey_value_from_server
    
    Resources:
      hermesType: your_server_Resources_type_name
      attrsmapping:
        # Resource primary email address <Valid email address>
        name: name_value_from_server
        # Display name <String>
        displayName: displayName_value_from_server
        # Resource type <String (Location, Equipment)>
        zimbraCalResType: zimbraCalResType_value_from_server
        
        # Country name <String>
        co: co_value_from_server
        # Description <String>
        description: description_value_from_server
        # Resource city <String>
        l: l_value_from_server
        # Postal code <String>
        postalCode: postalCode_value_from_server
        # Resource state <String>
        st: st_value_from_server
        # Resource street <String>
        street: street_value_from_server
        # Password hash <String>
        userPassword: userPassword_value_from_server
        # Resource status (default active) <String (active, closed)>
        zimbraAccountStatus: zimbraAccountStatus_value_from_server
        # Automatically accept or decline invitations <String (TRUE, FALSE)>
        zimbraCalResAutoAcceptDecline: zimbraCalResAutoAcceptDecline_value_from_server
        # Automatically decline invitations if there is a risk of conflict <String (TRUE, FALSE)>
        zimbraCalResAutoDeclineIfBusy: zimbraCalResAutoDeclineIfBusy_value_from_server
        # Automatically decline recurring invitations <String (TRUE, FALSE)>
        zimbraCalResAutoDeclineRecurring: zimbraCalResAutoDeclineRecurring_value_from_server
        # Building <String>
        zimbraCalResBuilding: zimbraCalResBuilding_value_from_server
        # Capacity <Integer>
        zimbraCalResCapacity: zimbraCalResCapacity_value_from_server
        # Contact email address <String>
        zimbraCalResContactEmail: zimbraCalResContactEmail_value_from_server
        # Contact name <String>
        zimbraCalResContactName: zimbraCalResContactName_value_from_server
        # Contact phone <String>
        zimbraCalResContactPhone: zimbraCalResContactPhone_value_from_server
        # Floor <String>
        zimbraCalResFloor: zimbraCalResFloor_value_from_server
        # Name of the displayed location <String>
        zimbraCalResLocationDisplayName: zimbraCalResLocationDisplayName_value_from_server
        # Room <String>
        zimbraCalResRoom: zimbraCalResRoom_value_from_server
        # Site <String>
        zimbraCalResSite: zimbraCalResSite_value_from_server
        # Free notes <String>
        zimbraNotes: zimbraNotes_value_from_server
        # Forward calendar invitations to this address <Array>
        zimbraPrefCalendarForwardInvitesTo: zimbraPrefCalendarForwardInvitesTo_value_from_server

```
