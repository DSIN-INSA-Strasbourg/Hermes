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

# `usersgroups_null` client plugin

## Description

This client will handle Users, Groups and UserPasswords events, but does nothing but logging.

## Configuration

Nothing to configure for the plugin.

```yaml
hermes-client-usersgroups_null:
```

## Datamodel

The following data types may be set up, without any specific constraint as nothing will be processed.

- Users
- UserPasswords
- Groups
- GroupsMembers

```yaml
  datamodel:
    Users:
      hermesType: your_server_Users_type_name
      attrsmapping:
        attr1_client:  attr1_server
        # ...

    UserPasswords:
      hermesType: your_server_UserPasswords_type_name
      attrsmapping:
        attr1_client:  attr1_server
        # ...

    Groups:
      hermesType: your_server_Groups_type_name
      attrsmapping:
        attr1_client:  attr1_server
        # ...

    GroupsMembers:
      hermesType: your_server_GroupsMembers_type_name
      attrsmapping:
        attr1_client:  attr1_server
        # ...
```
