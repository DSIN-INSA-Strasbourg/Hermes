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

# Plugin de source de données `ldap`

## Description

Ce plugin permet d'utiliser un serveur LDAP comme source de données.

## Configuration

Les paramètres de connexion sont requis dans la configuration du plugin.

```yaml
hermes:
  plugins:
    datasources:
      # Nom de la source. Utilisez ce que vous voulez. Sera utilisé dans le modèle de données
      your_source_name:
        type: ldap
        settings:
          # OBLIGATOIRE : URI du serveur LDAP
          uri: ldaps://ldap.example.com:636
          # OBLIGATOIRE : identifiants de connexion au serveur LDAP
          binddn: cn=account,dc=example,dc=com
          bindpassword: s3cReT_p4s5w0rD
          # OBLIGATOIRE : DN de base LDAP
          basedn: dc=example,dc=com

          ssl: # Facultatif
            # Chemin vers le fichier PEM avec les certificats CA
            cafile: /path/to/INTERNAL-CA-chain.crt # Facultatif
            # Chemin vers le fichier de certificat au format PEM pour l'authentification du certificat client, nécessite de définir keyfile
            certfile: /path/to/client.crt # Facultatif
            # Chemin vers le fichier de clé privée du certificat au format PEM pour l'authentification du certificat client, nécessite de définir certfile
            keyfile: /path/to/client.pem # Facultatif

          # Facultatif. Par défaut : false.
          # Comme le client n'a pas connaissance du schéma LDAP, il ne peut pas savoir si
          # un attribut est à valeur unique ou à valeurs multiples. Par défaut, il
          # s'adapte à la valeur qui lui est renvoyée : si elle est unique, il la renverra
          # dans son type de base, et s'il y en a plusieurs, il la renverra sous forme de liste.
          # Si ce paramètre est activé, toutes les valeurs seront toujours renvoyées dans une liste.
          always_return_values_in_list: true
```

## Utilisation

L'utilisation diffère selon le type d'opération spécifié

### fetch

Récupérer les entrées depuis le serveur LDAP.

```yaml
hermes-server:
  datamodel:
    oneDataType:
      sources:
        your_source_name: # 'your_source_name' a été défini dans les paramètres du plugin
          fetch:
            type: fetch
            vars:
              # Facultatif : le basedn à utiliser pour l'opération 'fetch'.
              # Si ce paramètre n'est pas défini, le paramètre basedn de la
              # configuration sera utilisé
              base: "ou=exampleOU,dc=example,dc=com"
              # Facultatif : la portée de l'opération 'fetch'
              # Les valeurs valides sont :
              # - base : pour rechercher l'objet "de base" lui-même
              # - one, onelevel : pour rechercher les enfants immédiats de l'objet "de base"
              # - sub, subtree : pour rechercher l'objet "de base" et tous ses descendants
              # Si non défini, "subtree" sera utilisé
              scope: subtree
              # Facultatif : le filtre LDAP à utiliser pour l'opération 'fetch'
              # Si non défini, "(objectClass=*)" sera utilisé
              filter: "(objectClass=*)"
              # Facultatif : les attributs à récupérer, sous forme de liste de chaînes
              # Si non défini, tous les attributs de chaque entrée sont renvoyés
              attrlist: "{{ REMOTE_ATTRIBUTES }}"
```

### add

Ajouter des entrées au serveur LDAP.

```yaml
hermes-server:
  datamodel:
    oneDataType:
      sources:
        your_source_name: # 'your_source_name' a été défini dans les paramètres du plugin
          fetch:
            type: add
            vars:
              # Facultatif : une liste d'entrées à ajouter.
              # Si elle n'est pas définie, une liste vide sera utilisée (et rien ne sera ajouté)
              addlist:
                  # OBLIGATOIRE : le DN de l'entrée. S'il n'est pas spécifié, l'entrée
                  # sera silencieusement ignorée
                - dn: uid=newentry1,ou=exampleOU,dc=example,dc=com
                  # Facultatif : les attributs à ajouter à l'entrée
                  add:
                    # Créer l'attribut s'il n'existe pas et lui ajouter la valeur "value"
                    "attrnameToAdd": "value",
                    # Créer l'attribut s'il n'existe pas et lui ajouter les valeurs
                    # "value1" et "value2"
                    "attrnameToAddList": ["value1", "value2"],
                - dn: uid=newentry2,ou=exampleOU,dc=example,dc=com
                  # ...
```

### delete

Supprimer des entrées du serveur LDAP.

```yaml
hermes-server:
  datamodel:
    oneDataType:
      sources:
        your_source_name: # 'your_source_name' a été défini dans les paramètres du plugin
          fetch:
            type: delete
            vars:
              # Facultatif : une liste d'entrées à supprimer.
              # Si elle n'est pas définie, une liste vide sera utilisée (et rien ne sera supprimé)
              dellist:
                  # OBLIGATOIRE : le DN de l'entrée. S'il n'est pas spécifié, l'entrée
                  # sera silencieusement ignorée
                - dn: uid=entryToDelete1,ou=exampleOU,dc=example,dc=com
                - dn: uid=entryToDelete2,ou=exampleOU,dc=example,dc=com
                  # ...
```

### modify

Modifier des entrées sur le serveur LDAP.

```yaml
hermes-server:
  datamodel:
    oneDataType:
      sources:
        your_source_name: # 'your_source_name' a été défini dans les paramètres du plugin
          fetch:
            type: modify
            vars:
              # Facultatif : une liste d'entrées à modifier.
              # Si elle n'est pas définie, une liste vide sera utilisée (et rien ne sera modifié)
              modlist:
                  # OBLIGATOIRE : le DN de l'entrée. S'il n'est pas spécifié, l'entrée
                  # sera silencieusement ignorée
                - dn: uid=entryToModify1,ou=exampleOU,dc=example,dc=com

                  # Facultatif : les attributs à ajouter à l'entrée
                  add:
                    # Créer l'attribut s'il n'existe pas et lui ajouter la valeur "value"
                    attrnameToAdd: value
                    # Créer l'attribut s'il n'existe pas et lui ajouter les valeurs
                    # "value1" et "value2"
                    attrnameToAddList: [value1, value2]

                  # Facultatif : les attributs de l'entrée à modifier
                  modify:
                    # Créer l'attribut s'il n'existe pas et remplacer toutes ses valeurs
                    # par la valeur "value"
                    attrnameToModify: newvalue
                    # Créer l'attribut s'il n'existe pas et remplacer toutes ses valeurs
                    # par les valeurs "newvalue1" and "newvalue2"
                    attrnameToModifyList: [newvalue1, newvalue2]

                  # Facultatif: les attributs de l'entrée à supprimer
                  delete:
                    # Supprimer l'attribut spécifié et toutes ses valeurs
                    attrnameToDelete: null
                    # Supprimer la valeur "value" de l'attribut spécifié.
                    # Génère une erreur si la valeur est manquante
                    attrnameToDeleteValue: value
                    # Supprimer les valeurs "value1" et "value2" de l'attribut spécifié.
                    # Génère une erreur si une des valeurs est manquante
                    attrnameToDeleteValueList: [value1, value2]

                - dn: uid=entryToModify2,ou=exampleOU,dc=example,dc=com
                  # ...
```
