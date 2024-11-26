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

# Plugin consommateur de bus de messages `kafka`

## Description

Ce plugin permet à hermes-client de recevoir des événements depuis un serveur Apache Kafka.

## Configuration

Il est possible de se connecter au serveur Kafka sans authentification, ou avec une [authentification SSL (TLS)](https://kafka.apache.org/documentation/#security_ssl).

```yaml
hermes:
  plugins:
    messagebus:
      kafka:
        settings:
          # OBLIGATOIRE : la liste des serveurs Kafka pouvant être utilisés
          servers:
            - dummy.example.com:9093

          # Facultatif : quelle version de l'API Kafka utiliser. Si elle n'est
          # pas définie, la version de l'API sera détectée au démarrage et
          # indiquée dans les fichiers log.
          # Ne définissez pas cette directive à moins que vous ne rencontriez
          # des erreurs "kafka.errors.NoBrokersAvailable : NoBrokersAvailable"
          # générées par un appel "self.check_version()".
          api_version: [2, 6, 0]

          # Facultatif : active l'authentification SSL. Si active, les 3 options
          # ci-dessous doivent être définies
          ssl:
            # OBLIGATOIRE : fichier de certificat hermes-server qui sera
            # utilisé pour l'authentification
            certfile: /path/to/.hermes/dummy.crt
            # OBLIGATOIRE : Chemin vers le fichier de clé privée du certificat
            # hermes-server
            keyfile: /path/to/.hermes/dummy.pem
            # OBLIGATOIRE : le certificat CA de la PKI
            cafile: /path/to/.hermes/INTERNAL-CA-chain.crt

          # OBLIGATOIRE : le sujet sur lequel retrouver les événements
          topic: hermes
          # OBLIGATOIRE : le group_id auquel rattacher le client. Définissez ce que vous voulez ici.
          group_id: hermes-grp
```
