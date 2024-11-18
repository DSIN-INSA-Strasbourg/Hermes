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

# `sqlite` messagebus_producer plugin

## Description

This plugin allows hermes-server to send produced events over an SQLite database.

## Configuration

To emulate the behavior of other message buses that delete messages once some conditions are met, `retention_in_days` can be set. It will delete messages older than the specified number of days.

```yaml
hermes:
  plugins:
    messagebus:
      sqlite:
        settings:
          # MANDATORY:
          uri: /path/to/.hermes/bus.sqlite
          retention_in_days: 1
```
