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

# `usersgroups_flatfiles_emails_of_groups` client plugin

## Description

This client will generate a flat txt file by `Groups`, containing the e-mail addresses of its members (one by line).

## Configuration

```yaml
hermes-client-usersgroups_flatfiles_emails_of_groups:
  # MANDATORY
  destDir: "/path/where/files/are/stored"

  # Facultative: if set, will generate a file only for the specified group names in list
  onlyTheseGroups:
    - group1
    - group2
```

## Datamodel

The following data types must be set up:

- `Users`, requires the following attribute names:
  - `user_pkey`: the user primary key
  - `mail`: the user email address
- `Groups`, requires the following attribute names:
  - `group_pkey`: the group primary key
  - `name`: the group name, that will be compared to those in `onlyTheseGroups`, and used to name the destination file "*groupName*.txt"
- `GroupsMembers`, requires the following attribute names:
  - `user_pkey`: the user primary key
  - `group_pkey`: the group primary key

```yaml
  datamodel:
    Users:
      hermesType: your_server_Users_type_name
      attrsmapping:
        user_pkey: user_pkey_on_server
        mail: mail_on_server

    Groups:
      hermesType: your_server_Groups_type_name
      attrsmapping:
        group_pkey: group_pkey_on_server
        name: group_name_on_server

    GroupsMembers:
      hermesType: your_server_GroupsMembers_type_name
      attrsmapping:
        user_pkey: user_pkey_on_server
        group_pkey: group_pkey_on_server
```
