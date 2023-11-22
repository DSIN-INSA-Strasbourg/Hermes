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

# `kafka` messagebus_consumer plugin

## Description

This plugin allow hermes-client to receive events from an Apache Kafka server.

## Configuration

It is possible to connect to Kafka server without authentication, or with [SSL (TLS) authentication](https://kafka.apache.org/documentation/#security_ssl).

```yaml
hermes:
  plugins:
    messagebus:
      kafka:
        settings:
          # MANDATORY : the Kafka server or servers list that can be used
          servers:
            - dummy.example.com:9093

          # Facultative : enables SSL authentication. If set, the 3 options below
          # must be defined
          ssl:
            # MANDATORY : hermes-client cert file that will be used for
            # authentication
            certfile: /path/to/.hermes/dummy.crt
            # MANDATORY : hermes-client cert file private key
            keyfile: /path/to/.hermes/dummy.pem
            # MANDATORY : The PKI CA cert
            cafile: /path/to/.hermes/INTERNAL-CA-chain.crt

          # MANDATORY : the topic to send events to
          topic: hermes
          # MANDATORY : the group_id to assign client to. Set what you want here.
          group_id: hermes-grp
```
