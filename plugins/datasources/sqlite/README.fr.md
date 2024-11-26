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

# Plugin de source de données `sqlite`

## Description

Ce plugin permet d'utiliser une base de données SQLite comme source de données.

## Configuration

Les paramètres de connexion sont requis dans la configuration du plugin.

```yaml
hermes:
  plugins:
    datasources:
      # Nom de la source. Utilisez ce que vous voulez. Sera utilisé dans le modèle de données
      your_source_name:
        type: sqlite
        settings:
          # OBLIGATOIRE : le chemin vers le fichier de base de données
          uri: /path/to/sqlite.db
```

## Utilisation

Spécifiez une requête. Si vous souhaitez utiliser des valeurs provenant du cache, il est possible de les indiquer dans un dictionnaire `vars`, et y faire référence en spécifiant le nom de variable (clé) préfixé par un double-points `:` dans la requête : cela nettoiera automatiquement les données dans la requête pour limiter les risques d'injection SQL.

Les noms d'exemple dans `vars` sont préfixés par `sanitized_` pour donner plus de clarté, mais cela n'a rien d'obligatoire.

```yaml
hermes-server:
  datamodel:
    oneDataType:
      sources:
        your_source_name: # 'your_source_name' a été défini dans les paramètres du plugin
          fetch:
            type: fetch
            query: >-
              SELECT {{ REMOTE_ATTRIBUTES | join(', ') }}
              FROM AN_SQLITE_TABLE

          commit_one:
            type: modify
            query: >-
              UPDATE AN_SQLITE_TABLE
              SET
                valueToSet = :sanitized_valueToSet
              WHERE pkey = :sanitized_pkey

            vars:
              sanitized_pkey: "{{ ITEM_FETCHED_VALUES.pkey }}"
              sanitized_valueToSet: "{{ ITEM_FETCHED_VALUES.valueToSet }}"
```
