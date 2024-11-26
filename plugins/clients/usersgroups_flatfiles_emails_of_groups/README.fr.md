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

# Plugin client `usersgroups_flatfiles_emails_of_groups`

## Description

Ce client génére un fichier txt plat par `Groups`, contenant les adresses e-mail de ses membres (une par ligne).

## Configuration

```yaml
hermes-client-usersgroups_flatfiles_emails_of_groups:
  # OBLIGATOIRE
  destDir: "/path/where/files/are/stored"

  # Facultatif : si défini, générera un fichier uniquement pour les noms de groupe spécifiés dans cette liste
  onlyTheseGroups:
    - group1
    - group2
```

## Datamodel

Les types de données suivants doivent être configurés :

- `Users`, nécessite les noms d'attribut suivants :
  - `user_pkey` : la clé primaire de l'utilisateur
  - `mail` : l'adresse e-mail de l'utilisateur
- `Groups`, nécessite les noms d'attribut suivants :
  - `group_pkey` : la clé primaire du groupe
  - `name` : le nom du groupe, qui sera comparé à ceux de `onlyTheseGroups`, et utilisé pour nommer le fichier de destination "*groupName*.txt"
- `GroupsMembers`, nécessite les noms d'attribut suivants :
  - `user_pkey` : la clé primaire de l'utilisateur
  - `group_pkey` : la clé primaire du groupe

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
