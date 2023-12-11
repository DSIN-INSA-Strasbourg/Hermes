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

# `sqlite` datasource plugin

## Description

This plugin allows using an SQLite database as datasource.

{{% notice warning %}}
This plugin is provided for testing but shouldn’t be used for production.
{{% /notice %}}

## Configuration

Connection settings are required in plugin configuration.

```yaml
hermes:
  plugins:
    datasources:
      # Source name. Use whatever you want. Will be used in datamodel
      your_source_name:
        type: sqlite
        settings:
          # MANDATORY: the database file path
          uri: /path/to/sqlite.db
```

## Usage

Specify a query. If you'd like to provide values from cache, you should provide them in a `vars` dict, and refer to them by specifying the column-prefixed `:` var key name in the query: this will automatically sanitize the query.

The example `vars` names are prefixed with `sanitized_` only for clarity, it's not a requirement.

```yaml
hermes-server:
  datamodel:
    oneDataType:
      sources:
        your_source_name: # 'your_source_name' was set in plugin settings
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
