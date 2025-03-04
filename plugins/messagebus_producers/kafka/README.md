<!--
Hermes : Change Data Capture (CDC) tool from any source(s) to any target
Copyright (C) 2023, 2024 INSA Strasbourg

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

# `kafka` messagebus_producer plugin

## Description

This plugin allows hermes-server to send produced events over an Apache Kafka server.

## Configuration

It is possible to connect to Kafka server without authentication, or with [SSL (TLS) authentication](https://kafka.apache.org/documentation/#security_ssl).

```yaml
hermes:
  plugins:
    messagebus:
      kafka:
        settings:
          # MANDATORY: the Kafka server or servers list that can be used
          servers:
            - dummy.example.com:9093

          # Facultative: which Kafka API version to use. If unset, the
          # api version will be detected at startup and reported in the logs.
          # Don't set this directive unless you encounter some
          # "kafka.errors.NoBrokersAvailable: NoBrokersAvailable" errors raised
          # by a "self.check_version()" call.
          api_version: [2, 6, 0]

          # Facultative: Hard limit on the size of a message sent to Kafka.
          # You should set a higher value if your Kafka messages are likely to
          # exceed the default of 1MB or if you encountered the error
          #   "MessageSizeTooLargeError: The message is xxx bytes when
          #    serialized which is larger than the maximum request size you
          #    have configured with the max_request_size configuration".
          # Default: 1048576.
          max_request_size: 1048576

          # Facultative: enables SSL authentication. If set, the 3 options below
          # must be defined
          ssl:
            # MANDATORY: hermes-server cert file that will be used for
            # authentication
            certfile: /path/to/.hermes/dummy.crt
            # MANDATORY: hermes-server cert file private key
            keyfile: /path/to/.hermes/dummy.pem
            # MANDATORY: The PKI CA cert
            cafile: /path/to/.hermes/INTERNAL-CA-chain.crt

          # MANDATORY: the topic to send events to
          topic: hermes
```
