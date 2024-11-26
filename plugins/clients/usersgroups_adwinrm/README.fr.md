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

# Plugin client `usersgroups_adwinrm`

{{% notice style="warning" title="pywinrm est très lent" %}}
Comme pywinrm génère un nouveau terminal et une nouvelle instance Powershell à chaque fois que vous exécutez une commande, il est vraiment lent.
Ce plugin est conservé au cas où, mais vous devriez **vraiment** envisager d'utiliser le plugin client `usersgroups_adpypsrp` à la place lorsque cela est possible : il est plus de 20 fois plus rapide (!).
La configuration est similaire sur les deux plugins (sauf `hermes-client-usersgroups_adwinrm.WinRM`).
{{% /notice %}}

## Description

Ce client traite les événements de type Users, Groups et UserPasswords, et stocke les données dans un Active Directory via des commandes Powershell sur pywinrm.

La liste des paramètres `standardAttributes` contient les paramètres des cmdlet utilisées pour les utilisateurs ([`New-ADUser`](https://learn.microsoft.com/en-us/powershell/module/activedirectory/new-aduser) / [`Set-ADUser`](https://learn.microsoft.com/en-us/powershell/module/activedirectory/set-aduser)) et les groupes ([`New-ADGroup`](https://learn.microsoft.com/en-us/powershell/module/activedirectory/new-adgroup) / [`Set-ADGroup`](https://learn.microsoft.com/en-us/powershell/module/activedirectory/set-adgroup)).
La liste de paramètres `otherAttributes` peut contenir des noms d'attributs LDAP (`ldapDisplayName`) disponibles pour gérer ceux qui ne sont pas représentés par les paramètres de cmdlet pour les utilisateurs et les groupes.

Les clés du modèle de données local DOIVENT exister dans `standardAttributes` ou `otherAttributes`, et seront utilisées comme paramètres de cmdlet avec leurs valeurs associées, permettant de gérer tous les attributs AD.

`GroupMembers` associera uniquement un `User` à un `Group` et ne pourra pas gérer les groupes imbriqués.

Pour éviter les problèmes de sécurité et les cas particuliers avec la corbeille, un mot de passe aléatoire complexe est défini lors de la création de l'utilisateur. Ce mot de passe inconnu sera écrasé par le prochain événement `UserPassword` de `User`. Cela évite d'avoir un compte activé sans mot de passe.

La corbeille ne fait que désactiver le compte.

## Configuration

```yaml
hermes-client-usersgroups_adwinrm:
  WinRM:  # Pour plus de détails sur les options, vous pouvez consulter https://github.com/diyan/pywinrm/#run-process-with-low-level-api-with-domain-user-disabling-https-cert-validation
    # OBLIGATOIRE : URI et port du serveur AD
    host: radon1.in.insa-strasbourg.fr
    port: 5986
    # OBLIGATOIRE : identifiants de connexion au serveur AD
    login: administrator
    password: "s3cReT_p4s5w0rD"
    # Par défaut : 'validate'. Set 'ignore' to disable
    ssl_cert_validation: ignore

  AD_domain:
    # OBLIGATOIRE : nom de domaine AD et DN
    name: in.insa-strasbourg.fr
    dn: DC=in,DC=insa-strasbourg,DC=fr
    # OBLIGATOIRE : OUs où les utilisateurs et les groupes seront stockés
    users_ou: OU=INSA,OU=People,DC=in,DC=insa-strasbourg,DC=fr
    groups_ou: OU=INSA,OU=Groups,DC=in,DC=insa-strasbourg,DC=fr

  # Définit les paramètres de cmdlet qui peuvent être définis et le type valide de la valeur qui leur est associée
  # Vous devriez vraiment le définir tel quel.
  standardAttributes:
    Users:
      AccountExpirationDate: "<DateTime>"
      AccountNotDelegated: "<Boolean>"
      AllowReversiblePasswordEncryption: "<Boolean>"
      AuthenticationPolicy: "<ADAuthenticationPolicy>"
      AuthenticationPolicySilo: "<ADAuthenticationPolicySilo>"
      AuthType: "<ADAuthType>"
      CannotChangePassword: "<Boolean>"
      ChangePasswordAtLogon: "<Boolean>"
      City: "<String>"
      Company: "<String>"
      CompoundIdentitySupported: "<Boolean>"
      Country: "<String>"
      # Credential: "<PSCredential>" # Inutile : spécifie les identifiants de connexion du compte utilisateur à utiliser pour effectuer cette tâche
      Department: "<String>"
      Description: "<String>"
      DisplayName: "<String>"
      Division: "<String>"
      EmailAddress: "<String>"
      EmployeeID: "<String>"
      EmployeeNumber: "<String>"
      Enabled: "<Boolean>"
      Fax: "<String>"
      GivenName: "<String>"
      HomeDirectory: "<String>"
      HomeDrive: "<String>"
      HomePage: "<String>"
      HomePhone: "<String>"
      KerberosEncryptionType: "<ADKerberosEncryptionType>"
      LogonWorkstations: "<String>"
      Manager: "<ADUser>"
      MobilePhone: "<String>"
      Office: "<String>"
      OfficePhone: "<String>"
      Organization: "<String>"
      OtherName: "<String>"
      PasswordNeverExpires: "<Boolean>"
      PasswordNotRequired: "<Boolean>"
      POBox: "<String>"
      PostalCode: "<String>"
      # PrincipalsAllowedToDelegateToAccount: "<ADPrincipal[]>" # Ne sera pas défini
      ProfilePath: "<String>"
      SamAccountName: "<String>"
      ScriptPath: "<String>"
      # Server: "<String>" # Inutile : spécifie l'instance de service de domaine Active Directory à laquelle se connecter
      SmartcardLogonRequired: "<Boolean>"
      State: "<String>"
      StreetAddress: "<String>"
      Surname: "<String>"
      Title: "<String>"
      # TrustedForDelegation: "<Boolean>" # Ne sera pas défini
      UserPrincipalName: "<String>"

    Groups:
      AuthType: "<ADAuthType>"
      # Credential: "<PSCredential>" # Inutile : spécifie les identifiants de connexion du compte utilisateur à utiliser pour effectuer cette tâche
      Description: "<String>"
      DisplayName: "<String>"
      GroupCategory: "<ADGroupCategory>"
      GroupScope: "<ADGroupScope>"
      HomePage: "<String>"
      ManagedBy: "<ADPrincipal>"
      SamAccountName: "<String>"
      # Server: "<String>" # Inutile : spécifie l'instance de service de domaine Active Directory à laquelle se connecter

  # Définit les attributs LDAP (ldapDisplayName) à gérer, qui ne sont pas gérés par les attributs standard.
  # Vous pouvez définir les valeurs souhaitées. Les valeurs ci-dessous sont données à titre d'exemple.
  otherAttributes:
    Users:
      otherMobile: "<String[]>"
      otherTelephone: "<String[]>"
      url: "<String[]>"

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

Les types de données suivants peuvent être configurés :

- `Users` : nécessite que l'attribut `SamAccountName` soit défini
- `UserPasswords` : nécessite évidemment `Users`, et que l'attribut `user_pkey` corresponde aux clés primaires de `Users`, et nécessite l'attribut `password`. Tous les autres attributs seront ignorés
- `Groups` : nécessite que l'attribut `SamAccountName` soit défini
- `GroupsMembers` : nécessite évidemment `Users` et `Groups`, et nécessite que les attributs `user_pkey` et `group_pkey` correspondent aux clés primaires de `Users` et `Groups`. Tous les autres attributs seront ignorés

```yaml
  datamodel:
    Users:
      hermesType: your_server_Users_type_name
      attrsmapping:
        user_pkey: user_primary_key_on_server
        SamAccountName: login_on_server
        UserPrincipalName: "{{ login_on_server ~ '@YOU.AD.DOMAIN.TLD' }}"
        # Pas obligatoire, juste présent pour exemple :
        MobilePhone: "{{ (mobile | default([None]))[0] }}" # <String>
        otherMobile: "{{ (mobile | default([]))[1:]  }}" # <String[]>
        # ...

    UserPasswords:
      hermesType: your_server_UserPasswords_type_name
      attrsmapping:
        user_pkey: user_primary_key_on_server
        password: cleartext_password_on_server
        # ...

    Groups:
      hermesType: your_server_Groups_type_name
      attrsmapping:
        group_pkey: group_primary_key_on_server
        SamAccountName: group_name_on_server
        # ...

    GroupsMembers:
      hermesType: your_server_GroupsMembers_type_name
      attrsmapping:
        user_pkey: user_primary_key_on_server
        group_pkey: group_primary_key_on_server
        # ...
```
