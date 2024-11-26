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

# Plugin client `usersgroups_kadmin_heimdal`

## Description

Ce client traite les événements de type `Users` and `UserPassword` et stocke les données sur un serveur Kerberos Heimdal.

## Configuration

```yaml
hermes-client-usersgroups_kadmin_heimdal:
  # OBLIGATOIRE : Principal disposant des droits requis pour gérer les utilisateurs et les mots de passe dans kadmin
  kadmin_login: root/admin
  # OBLIGATOIRE : Mot de passe du principal ci-dessus
  kadmin_password: "s3cReT_p4s5w0rD"
  # OBLIGATOIRE : nom du domaine Kerberos
  kadmin_realm: KERBEROS_REALM

  # Nom du principal de service pour lequel obtenir un ticket. Par défaut : kadmin/admin
  kinit_spn: kadmin/admin
  # Commande kinit à utiliser. Par défaut : kinit.heimdal
  kinit_cmd: kinit.heimdal
  # Commande kadmin à utiliser. Par défaut : kadmin.heimdal
  kadmin_cmd: kadmin.heimdal
  # Commande kdestroy à utiliser. Par défaut : kdestroy.heimdal
  kdestroy_cmd: kdestroy.heimdal

  # Paramètre kadmin supplémentaires à utiliser lors de l'ajout d'un utilisateur. Doit être une liste de chaînes. Valeur par défaut :
  #   - "--max-ticket-life=1 day"
  #   - "--max-renewable-life=1 week"
  #   - "--attributes="
  #   - "--expiration-time=never"
  #   - "--policy=default"
  #   - "--pw-expiration-time=never"
  kadmin_user_add_additional_options:
    - "--max-ticket-life=1 day"
    - "--max-renewable-life=1 week"
    - "--attributes="
    - "--expiration-time=never"
    - "--policy=default"
    - "--pw-expiration-time=never"
  
  # Définir à true pour démarrer avec une base de données Kerberos déjà remplie. Valeur par défaut : false
  dont_fail_on_existing_user: false

  # Paramètres de génération de mot de passe aléatoire facultatifs. Par défaut : les valeurs spécifiées ci-dessous
  # Un mot de passe aléatoire est généré pour initialiser un utilisateur dont le mot de passe n'est pas encore disponible
  random_passwords:
    # Longueur du mot de passe
    length: 32
    # Si true, le mot de passe généré peut contenir des lettres majuscules
    with_upper_letters: true
    # Le mot de passe généré contiendra au moins ce nombre de lettres majuscules
    minimum_number_of_upper_letters: 1
    # Si true, le mot de passe généré peut contenir des lettres minuscules
    with_lower_letters: true
    # Le mot de passe généré contiendra au moins ce nombre de lettres minuscules
    minimum_number_of_lower_letters: 1
    # Si true, le mot de passe généré peut contenir des chiffres
    with_numbers: true
    # Le mot de passe généré contiendra au moins ce nombre de chiffres
    minimum_number_of_numbers: 1
    # Si true, le mot de passe généré peut contenir des caractères spéciaux
    with_special_chars: true
    # Le mot de passe généré contiendra au moins ce nombre de caractères spéciaux
    minimum_number_of_special_chars: 1
    # Si true, le mot de passe généré ne contiendra pas les caractères spécifiés dans 'ambigous_chars_dictionary'
    avoid_ambigous_chars: false
    # Le dictionnaire des caractères ambigus (sensibles à la casse) qui peuvent être interdits dans le mot de passe, même si certains sont présents dans d'autres dictionnaires
    ambigous_chars_dictionary: "lIO01"
    # Le dictionnaire des lettres (insensibles à la casse) autorisées dans le mot de passe
    letters_dictionary: "abcdefghijklmnopqrstuvwxyz"
    # Le dictionnaire des caractères spéciaux autorisés dans le mot de passe
    special_chars_dictionary: "!@#$%^&*"
```

## Datamodel

Les types de données suivants doivent être configurés :

- `Users`, nécessite les noms d'attribut suivants :
  - `login` : le login de l'utilisateur qui sera utilisé comme principal
- `UserPasswords`, nécessite les noms d'attribut suivants :
  - `password` : le mot de passe de l'utilisateur

Évidemment, les clés primaires de `Users` et `UserPasswords` doivent correspondre pour pouvoir lier le login au mot de passe.

```yaml
  datamodel:
    Users:
      hermesType: your_server_Users_type_name
      attrsmapping:
        login: login_on_server

    UserPasswords:
      hermesType: your_server_UserPasswords_type_name
      attrsmapping:
        password: password_on_server
```
