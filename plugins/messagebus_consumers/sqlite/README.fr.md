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

# Plugin consommateur de bus de messages `sqlite`

## Description

Ce plugin permet à hermes-client de recevoir des événements depuis une base de données SQLite.

## Configuration

```yaml
hermes:
  plugins:
    messagebus:
      sqlite:
        settings:
          # OBLIGATOIRE :
          uri: /path/to/.hermes/bus.sqlite
```
