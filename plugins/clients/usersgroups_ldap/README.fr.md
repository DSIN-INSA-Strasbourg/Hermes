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

# Plugin client `usersgroups_ldap`

## Description

Ce client traite les événements de type Users, Groups et UserPasswords, et stocke les données dans un annuaire LDAP.

Les clés du modèle de données local seront utilisées comme noms d'attributs LDAP, sans aucune contrainte, et il est possible de spécifier avec le paramètre `attributesToIgnore` certaines clés du modèle de données à ignorer (généralement les clés primaires) qui ne seront pas stockées dans l'annuaire LDAP.

`GroupMembers` stockera uniquement les données (généralement l'attribut LDAP `member`) dans les entrées LDAP des groupes puisqu'il est possible d'utiliser des overlays LDAP (`dynlist` ou le désormais obsolète `memberOf`) pour générer dynamiquement les données correspondantes dans les entrées utilisateur. Vous devriez envisager de lire la documentation du paramètre `propagateUserDNChangeOnGroupMember`.

{{% notice style="tip" title="Génération de hachages de mots de passe LDAP" %}}
Si vous devez générer des hachages de mots de passe LDAP, vous devriez regarder le plugin d'attribut [ldapPasswordHash](../../attributes/ldappasswordhash/).
{{% /notice %}}

## Configuration

```yaml
hermes-client-usersgroups_ldap:
    # OBLIGATOIRE : URI du serveur LDAP
    uri: ldaps://ldap.example.com:636
    # OBLIGATOIRE : identifiants de connexion au serveur LDAP
    binddn: cn=account,dc=example,dc=com
    bindpassword: s3cReT_p4s5w0rD
    # OBLIGATOIRE : DN de base LDAP
    basedn: dc=example,dc=com
    users_ou: ou=users,dc=example,dc=com
    groups_ou: ou=groups,dc=example,dc=com

    ssl: # Facultatif
      # Chemin vers le fichier PEM avec les certificats CA
      cafile: /path/to/INTERNAL-CA-chain.crt # Facultatif
      # Chemin vers le fichier de certificat au format PEM pour l'authentification du certificat client, nécessite de définir keyfile
      certfile: /path/to/client.crt # Facultatif
      # Chemin vers le fichier de clé privée du certificat au format PEM pour l'authentification du certificat client, nécessite de définir certfile
      keyfile: /path/to/client.pem # Facultatif

    # OBLIGATOIRE : nom de l'attribut DN pour les utilisateurs, les mots de passe utilisateur et les groupes
    # Vous devez définir des valeurs pour les trois, même si vous n'utilisez pas certains d'entre eux
    dnAttributes:
      Users: uid
      UserPasswords: uid
      Groups: cn

    # En fonction des paramètres de groupe et d'appartenance au groupe du serveur LDAP,
    # vous pourriez utiliser un autre attribut que l'attribut par défaut 'member' pour
    # stocker le DN du membre du groupe
    # Facultatif. Valeur par défaut : "member"
    groupMemberAttribute: member

    # En fonction des paramètres de groupe et d'appartenance au groupe du serveur LDAP,
    # vous pourriez vouloir propager un changement de DN d'utilisateur vers les
    # attributs d'appartenance au groupe. Mais dans certains cas, c'est géré par un
    # overlay, par exemple avec l'overlay memberOf et son paramètre
    # memberof-refint/olcMemberOfRefint à TRUE
    # Si 'propagateUserDNChangeOnGroupMember' est définie à true, il faudra également
    # définir 'groupsObjectclass'
    # Facultatif. Valeur par défaut : true
    propagateUserDNChangeOnGroupMember: true

    # Si vous avez défini 'propagateUserDNChangeOnGroupMember' à true,
    # vous DEVEZ indiquer l'objectClass sera utilisé pour rechercher
    # vos entrées de groupes
    # Obligatoire uniquement si 'propagateUserDNChangeOnGroupMember' est vrai
    groupsObjectclass: groupOfNames

    # Il est possible de définir une valeur par défaut pour certains attributs pour les Users, UserPasswords et Groups
    # La valeur par défaut sera appliquée lors du traitements des événements added et modified, si l'attribut local n'a pas de valeur
    defaultValues:
      Groups:
        member: "" # Hack pour permettre la création d'un groupe vide, néessaire à cause du "MUST member" dans le schéma

    # Les attributs locaux répertoriés ici ne seront pas stockés dans LDAP pour les types Users, UserPasswords and Groups
    attributesToIgnore:
      Users:
        - user_pkey
      UserPasswords:
        - user_pkey
      Groups:
        - group_pkey
```

## Datamodel

Les types de données suivants peuvent être configurés :

- `Users`
- `UserPasswords` : nécessite évidemment `Users` et nécessite l'attribut `user_pkey` correspondant aux clés primaires de `Users`
- `Groups`
- `GroupsMembers` : nécessite évidemment `Users` et `Groups` et nécessite les attributs `user_pkey` et `group_pkey` correspondant aux clés primaires de `Users` et `Groups`

```yaml
  datamodel:
    Users:
      hermesType: your_server_Users_type_name
      attrsmapping:
        user_pkey:  user_primary_key_on_server
        uid: login_on_server
        # ...

    UserPasswords:
      hermesType: your_server_UserPasswords_type_name
      attrsmapping:
        user_pkey:  user_primary_key_on_server
        userPassword:  ldap_pwd_hash_list_on_server
        # ...

    Groups:
      hermesType: your_server_Groups_type_name
      attrsmapping:
        group_pkey:  group_primary_key_on_server
        cn:  group_name_on_server
        # ...

    GroupsMembers:
      hermesType: your_server_GroupsMembers_type_name
      attrsmapping:
        user_pkey:  user_primary_key_on_server
        group_pkey:  group_primary_key_on_server
        # ...
```
