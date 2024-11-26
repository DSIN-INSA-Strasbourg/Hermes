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

# Plugin client `usersgroups_null`

## Description

Ce client traite les événements de type Users, Groups and UserPasswords, mais ne fait rien d'autre que de générer des logs.

## Configuration

Rien à configurer pour le plugin.

```yaml
hermes-client-usersgroups_null:
```

## Datamodel

Les types de données suivants peuvent être configurés, sans contrainte particulière puisque rien ne sera traité.

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
