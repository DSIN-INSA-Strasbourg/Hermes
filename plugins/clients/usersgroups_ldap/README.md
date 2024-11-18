<!--
Hermes : Change Data Capture (CDC) tool from any source(s) to any target
Copyright (C) 2023, 2024 INSA Strasbourg

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

# `usersgroups_ldap` client plugin

## Description

This client will handle Users, Groups and UserPasswords events, and store data in an LDAP directory.

The local Datamodel keys will be used as LDAP attributes names, without any constraints, and it is possible to specify some Datamodel keys to ignore (typically the primary keys) that won't be stored in LDAP directory with the `attributesToIgnore` setting.

The `GroupMembers` will only store data (typically LDAP `member` attribute) in LDAP group entries as it is possible to use LDAP overlays (`dynlist` or the deprecated `memberOf`) to dynamically generate the corresponding data in user entries. You should consider reading the `propagateUserDNChangeOnGroupMember` setting documentation.

{{% notice style="tip" title="LDAP password hashes generation" %}}
If you need to generate LDAP password hashes, you may consider looking at [ldapPasswordHash](../../attributes/ldappasswordhash/) attribute plugin.
{{% /notice %}}

## Configuration

```yaml
hermes-client-usersgroups_ldap:
    # MANDATORY: LDAP server URI
    uri: ldaps://ldap.example.com:636
    # MANDATORY: LDAP server credentials to use
    binddn: cn=account,dc=example,dc=com
    bindpassword: s3cReT_p4s5w0rD
    # MANDATORY: LDAP base DN
    basedn: dc=example,dc=com
    users_ou: ou=users,dc=example,dc=com
    groups_ou: ou=groups,dc=example,dc=com

    ssl: # Facultative
      # Path to PEM file with CA certs
      cafile: /path/to/INTERNAL-CA-chain.crt # Facultative
      # Path to file with PEM encoded cert for client cert authentication, requires keyfile
      certfile: /path/to/client.crt # Facultative
      # Path to file with PEM encoded key for client cert authentication, requires certfile
      keyfile: /path/to/client.pem # Facultative

    # MANDATORY: Name of DN attribute for Users, UserPasswords and Groups
    # You have to set up values for the three, even if you don't use some of the types
    dnAttributes:
      Users: uid
      UserPasswords: uid
      Groups: cn

    # Depending on group and group membership settings in LDAP, you may use another
    # attribute than the default 'member' attribute to store the group member DN
    # Facultative. Default value: "member"
    groupMemberAttribute: member

    # Depending on group and group membership settings in LDAP, you usually may want
    # to propagate a user DN change on group member attributes. But sometimes, it
    # may be handled by an overlay, e.g. with memberOf overlay and the
    # memberof-refint/olcMemberOfRefint setting to TRUE
    # If set to true, it requires 'groupsObjectclass' to be defined
    # Facultative. Default value: true
    propagateUserDNChangeOnGroupMember: true

    # If you've set 'propagateUserDNChangeOnGroupMember' to true,
    # you MUST indicate your group objectClass that will be used to search
    # your groups entries
    # Mandatory only if 'propagateUserDNChangeOnGroupMember' is true
    groupsObjectclass: groupOfNames

    # It is possible to set a default value for some attributes for Users, UserPasswords and Groups
    # The default value will be set on added and modified events if the local attribute has no value
    defaultValues:
      Groups:
        member: "" # Hack to allow creation of an empty group, because of the "MUST member" in schema

    # The local attributes listed here won't be stored in LDAP for Users, UserPasswords and Groups
    attributesToIgnore:
      Users:
        - user_pkey
      UserPasswords:
        - user_pkey
      Groups:
        - group_pkey
```

## Datamodel

The following data types may be set up:

- `Users`
- `UserPasswords`: obviously require `Users`, and requires the following attribute names `user_pkey` corresponding to the primary keys of `Users`
- `Groups`
- `GroupsMembers`: obviously require `Users` and `Groups`, and requires the following attribute names `user_pkey` `group_pkey` corresponding to the primary keys of `Users` and `Groups`

```yaml
  datamodel:
    Users:
      hermesType: your_server_Users_type_name
      attrsmapping:
        user_pkey:  user_primary_key_on_server
        uid: login_on_server
        # ...

    UserPasswords:
      hermesType: your_server_UserPasswords_type_name
      attrsmapping:
        user_pkey:  user_primary_key_on_server
        userPassword:  ldap_pwd_hash_list_on_server
        # ...

    Groups:
      hermesType: your_server_Groups_type_name
      attrsmapping:
        group_pkey:  group_primary_key_on_server
        cn:  group_name_on_server
        # ...

    GroupsMembers:
      hermesType: your_server_GroupsMembers_type_name
      attrsmapping:
        user_pkey:  user_primary_key_on_server
        group_pkey:  group_primary_key_on_server
        # ...
```
