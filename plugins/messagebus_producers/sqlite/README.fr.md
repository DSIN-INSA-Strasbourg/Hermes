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

# Plugin producteur de bus de messages `sqlite`

## Description

Ce plugin permet à hermes-server d'envoyer les événements produits vers une base de données SQLite.

## Configuration

Pour imiter le comportement d'autres bus de messages qui suppriment les messages une fois certaines conditions remplies, `retention_in_days` peut être définie. Les messages plus anciens que le nombre de jours spécifié seront automatiquement supprimés.

```yaml
hermes:
  plugins:
    messagebus:
      sqlite:
        settings:
          # OBLIGATOIRE :
          uri: /path/to/.hermes/bus.sqlite
          retention_in_days: 1
```
