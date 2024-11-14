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

# Plugin client `usersgroups_bsspartage`

## Description

Ce client traite les évènements de type Users, UserPasswords, Groups, GroupsMembers, GroupsSenders et Ressources, et stocke les données dans le tableau de bord de [PARTAGE](https://www.renater.fr/services/collaborer-simplement/partage/) via son API, gérée par [libPythonBssApi](https://github.com/dsi-univ-rennes1/libPythonBssApi).

Pour éviter les problèmes de sécurité, si aucun hash n'est disponible à la création de l'utilisateur, un mot de passe aléatoire complexe sera défini. Ce mot de passe inconnu sera modifié lorsqu'un attribut `userPassword` sera défini sur `User` ou sur `UserPassword`. Cela évite d'avoir un compte activé sans mot de passe.

La corbeille ne fait que désactiver le compte.

## Configuration

Vous devez configurer un mapping d'authentification `authentication` contenant tous les domaines gérés par ce client en tant que clés et leur clé API en tant que valeurs.

```yaml
hermes-client-usersgroups_bsspartage:
  authentication:
    example.com: "Secret_API_key_of_example.com"
    subdomain.example.com: "Secret_API_key_of_subdomain.example.com"
  
  # Lorsqu'un attribut n'a plus de valeur, le comportement par défaut est de conserver sa dernière valeur en place.
  # Ce paramètre permet de remplacer ce comportement pour les attributs spécifiés, avec des valeurs de remplacement.
  # Veuillez noter qu'il est interdit de définir Users.userPassword, car le comportement par défaut est de générer un nouveau mot de passe aléatoire.
  # Il est également interdit de définir des valeurs nulles, car cela revient au comportement par défaut. Dans ce cas, supprimez simplement l'attribut concerné de cette liste.
  #
  # Les valeurs définies ci-dessous sont les valeurs par défaut utilisées si default_removed_values ​​n'est pas défini
  default_removed_values:
    Users:
      co: ""
      company: ""
      description: ""
      displayName: ""
      facsimileTelephoneNumber: ""
      givenName: ""
      homePhone: ""
      initials: ""
      l: ""
      mobile: ""
      name: ""
      pager: ""
      postalCode: ""
      st: ""
      street: ""
      telephoneNumber: ""
      title: ""
      zimbraNotes: ""
      zimbraPrefMailForwardingAddress: ""
      zimbraMailCanonicalAddress: ""
      zimbraPrefFromDisplay: ""
      zimbraMailQuota: 0
    Groups:
      # Ces valeurs devraient être définies comme des chaînes vides, mais un bug dans l'API les ignore.
      # Ce bug a été signalé à l'équipe de PARTAGE.
      description: "-" 
      displayName: "-"
      zimbraNotes: "-"
    Resources:
      co: ""
      description: ""
      l: ""
      postalCode: ""
      st: ""
      street: ""
      zimbraCalResBuilding: ""
      zimbraCalResContactEmail: ""
      zimbraCalResContactName: ""
      zimbraCalResContactPhone: ""
      zimbraCalResFloor: ""
      zimbraCalResLocationDisplayName: ""
      zimbraCalResRoom: ""
      zimbraCalResSite: ""
      zimbraNotes: ""
      zimbraCalResCapacity: "-1"

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

- `Users` : pour les comptes utilisateurs. Nécessite la définition des attributs `name` et `sn`, un attribut facultatif `aliases` peut être défini, et les autres sont des attributs tels que définis et utilisés par [libPythonBssApi](https://github.com/dsi-univ-rennes1/libPythonBssApi) et sont facultatifs.
Notez que les attributs `zimbraAllowFromAddress`, `zimbraFeatureContactsEnabled` et `zimbraMailForwardingAddress` ne sont pas pris en charge par [libPythonBssApi](https://github.com/dsi-univ-rennes1/libPythonBssApi).
- `UserPasswords` : nécessite évidemment `Users` et que ses clés primaires correspondent aux clés primaires de `Users`, et nécessite l'attribut `userPassword` qui doit contenir un hash LDAP valide. Tous les autres attributs seront ignorés. Comme l'attribut `userPassword` peut également être géré par `Users`, vous devez choisir : soit vous le gérez par `Users`, soit par `UserPasswords`, mais pour des raisons évidentes vous ne devez en aucun cas utiliser les deux en même temps.
- `Groups` : pour les groupes et les listes de distribution. Nécessite que les attributs `name` et `zimbraMailStatus` soient définis, un attribut facultatif `aliases` peut être défini, et les autres sont des attributs tels que définis et utilisés par [libPythonBssApi](https://github.com/dsi-univ-rennes1/libPythonBssApi) et sont facultatifs.
- `GroupsMembers` : pour ajouter des utilisateurs en tant que membres du groupe. Nécessite évidemment `Users` et `Groups`, et nécessite les attributs `user_pkey` et `group_pkey` correspondant aux clés primaires de `Users` et `Groups`. Tous les autres attributs seront ignorés.
- `GroupsSenders` : pour ajouter des utilisateurs en tant qu'expéditeurs du groupe. Nécessite évidemment `Users` et `Groups`, et nécessite les attributs `user_pkey` et `group_pkey` correspondant aux clés primaires de `Users` et `Groups`. Tous les autres attributs seront ignorés.
- `Resources` : pour les ressources. Nécessite que les attributs `name`, `zimbraCalResType` et `displayName` soient définis, et les autres sont des attributs tels que définis et utilisés par [libPythonBssApi](https://github.com/dsi-univ-rennes1/libPythonBssApi) et sont facultatifs.

{{% notice warning %}}
Si vous définissez `Users.zimbraCOSId`, vous devriez éviter de définir des attributs gérés par la COS dans votre modèle de données, car le remplacement de la valeur par défaut de la COS peut entraîner des comportements inattendus.
{{% /notice %}}

{{% notice warning %}}
Étant donné que l'API ne permet pas de renommer des `Groups` et `Resources`, cette opération est effectuée en supprimant l'ancienne instance et en recréant la nouvelle dans la foulée. Cependant, cela peut entraîner des pertes de liens et d'informations (par exemple, des calendriers de ressources), et il est probablement préférable d'éviter ces renommages.
{{% /notice %}}

{{% notice tip %}}
Pour gérer `Users.zimbraCOSId`, il est probable que votre source de données fournisse un nom plutôt que le COSId. Il est possible de déclarer une table de correspondance en Jinja directement dans votre configuration :

```yaml
  datamodel:
    Users:
      hermesType: your_server_Users_type_name
      attrsmapping:
        # ...
        zimbraCOSId: >-
          {{
              {
                'name_of_cos1': '11111111-1111-1111-1111-111111111111',
                'name_of_cos2': '22222222-2222-2222-2222-222222222222',
                'name_of_cos3': '33333333-3333-3333-3333-333333333333',
              }[zimbraCOSName_value_from_server | default('name_of_cos1') | lower]
              | default('11111111-1111-1111-1111-111111111111')
          }}
        # ...
```

{{% /notice %}}

```yaml
  datamodel:
    Users:
      hermesType: your_server_Users_type_name
      attrsmapping:
        # Adresse mail principale de l’utilisateur <Adresse mail valide>
        name: name_value_from_server
        # Nom de famille de l'utilisateur <String>
        sn: sn_value_from_server

        # Liste des alias de cet utilisateur <String[]>
        aliases: aliases_value_from_server
        # Numéro EPPN de l’utilisateur <String>
        carLicense: carLicense_value_from_server
        # Nom du pays <String>
        co: co_value_from_server
        # Nom de la société ou de l'établissement <String>
        company: company_value_from_server
        # Description du compte <String>
        description: description_value_from_server
        # Nom affiché dans les emails <String>
        displayName: displayName_value_from_server
        # Fax de l'utilisateur <String>
        facsimileTelephoneNumber: facsimileTelephoneNumber_value_from_server
        # Prénom de l'utilisateur <String>
        givenName: givenName_value_from_server
        # Téléphone domicile de l'utilisateur <String>
        homePhone: homePhone_value_from_server
        # Initiales (M. ou Mme) <String>
        initials: initials_value_from_server
        # Ville de l'utilisateur <String>
        l: l_value_from_server
        # Numéro de mobile de l'utilisateur <String>
        mobile: mobile_value_from_server
        # Numéro raccourci de l'utilisateur <String>
        pager: pager_value_from_server
        # Code postal <String>
        postalCode: postalCode_value_from_server
        # État de l'utilisateur <String>
        st: st_value_from_server
        # Rue de l'utilisateur <String>
        street: street_value_from_server
        # Téléphone de l'utilisateur <String>
        telephoneNumber: telephoneNumber_value_from_server
        # Fonction de l'utilisateur <String>
        title: title_value_from_server
        # Empreinte du mot de passe <String>
        userPassword: userPassword_value_from_server
        # État du compte (défaut active) <String(active, closed, locked)>
        zimbraAccountStatus: zimbraAccountStatus_value_from_server
        # Id de la classe de service <String>
        zimbraCOSId: zimbraCOSId_value_from_server
        # Onglet porte document <String (TRUE, FALSE)>
        zimbraFeatureBriefcasesEnabled: zimbraFeatureBriefcasesEnabled_value_from_server
        # Onglet calendrier <String (TRUE, FALSE)>
        zimbraFeatureCalendarEnabled: zimbraFeatureCalendarEnabled_value_from_server
        # Onglet mail <String (TRUE, FALSE)>
        zimbraFeatureMailEnabled: zimbraFeatureMailEnabled_value_from_server
        # Permettre à l’utilisateur d’indiquer une adresse de redirection <String (TRUE, FALSE)>
        zimbraFeatureMailForwardingEnabled: zimbraFeatureMailForwardingEnabled_value_from_server
        # Onglet préférences <String (TRUE, FALSE)>
        zimbraFeatureOptionsEnabled: zimbraFeatureOptionsEnabled_value_from_server
        # Onglet tâche <String (TRUE, FALSE)>
        zimbraFeatureTasksEnabled: zimbraFeatureTasksEnabled_value_from_server
        # Masquer dans la GAL <String (TRUE, FALSE)>
        zimbraHideInGal: zimbraHideInGal_value_from_server
        # 0=illimité <Integer (octet)>
        zimbraMailQuota: zimbraMailQuota_value_from_server
        # Notes libres <String>
        zimbraNotes: zimbraNotes_value_from_server
        # Doit changer son mot de passe à la prochaine connexion <String (TRUE, FALSE)>
        zimbraPasswordMustChange: zimbraPasswordMustChange_value_from_server
        # Adresse de redirection saisie par l’utilisateur <Adresse mail valide>
        zimbraPrefMailForwardingAddress: zimbraPrefMailForwardingAddress_value_from_server
        # Ne pas conserver de copie des mails sur le client local <String (TRUE, FALSE)>
        zimbraPrefMailLocalDeliveryDisabled: zimbraPrefMailLocalDeliveryDisabled_value_from_server
        # Adresse email visible pour les messages sortants <String>
        zimbraMailCanonicalAddress: zimbraMailCanonicalAddress_value_from_server
        # Nom affiché visible pour les messages sortants <String>
        zimbraPrefFromDisplay: zimbraPrefFromDisplay_value_from_server

    UserPasswords:
      hermesType: your_server_UserPasswords_type_name
      attrsmapping:
        # Empreinte du mot de passe <String>
        userPassword: userPassword_value_from_server

    Groups:
      hermesType: your_server_Groups_type_name
      attrsmapping:
        # Adresse mail principale du groupe <Adresse mail valide>
        name: name_value_from_server
        # Discriminant liste de distribution / groupe <String (enabled, disabled)>
        zimbraMailStatus: zimbraMailStatus_value_from_server
        
        # Liste des alias de ce groupe <String[]>
        aliases: aliases_value_from_server
        # Description du groupe <String>
        description: description_value_from_server
        # Nom affiché <String>
        displayName: displayName_value_from_server
        # Signaler les partages disponibles aux nouveaux membres <String (TRUE, FALSE)>
        zimbraDistributionListSendShareMessageToNewMembers: zimbraDistributionListSendShareMessageToNewMembers_value_from_server
        # Masquer le groupe dans la liste GAL <String (TRUE, FALSE)>
        zimbraHideInGal: zimbraHideInGal_value_from_server
        # Notes libres <String>
        zimbraNotes: zimbraNotes_value_from_server

    GroupsMembers:
      hermesType: your_server_GroupsMembers_type_name
      attrsmapping:
        user_pkey: user_pkey_value_from_server
        group_pkey: group_pkey_value_from_server

    GroupsSenders:
      hermesType: your_server_GroupsSenders_type_name
      attrsmapping:
        user_pkey: user_pkey_value_from_server
        group_pkey: group_pkey_value_from_server
    
    Resources:
      hermesType: your_server_Resources_type_name
      attrsmapping:
        # Adresse mail principale de la ressource <Adresse mail valide>
        name: name_value_from_server
        # Nom affiché <String>
        displayName: displayName_value_from_server
        # Type de la ressource <String (Location, Equipment)>
        zimbraCalResType: zimbraCalResType_value_from_server
        
        # Nom du pays <String>
        co: co_value_from_server
        # Description <String>
        description: description_value_from_server
        # Ville de la ressource <String>
        l: l_value_from_server
        # Code postal <String>
        postalCode: postalCode_value_from_server
        # État de la ressource <String>
        st: st_value_from_server
        # Rue de la ressource <String>
        street: street_value_from_server
        # empreinte du mot de passe <String>
        userPassword: userPassword_value_from_server
        # État de la ressource (défaut active) <String (active, closed)>
        zimbraAccountStatus: zimbraAccountStatus_value_from_server
        # Accepte ou décline automatiquement les invitations <String (TRUE, FALSE)>
        zimbraCalResAutoAcceptDecline: zimbraCalResAutoAcceptDecline_value_from_server
        # Décline automatiquement les invitations si risque de conflit <String (TRUE, FALSE)>
        zimbraCalResAutoDeclineIfBusy: zimbraCalResAutoDeclineIfBusy_value_from_server
        # Décline automatiquement les invitations récurrente <String (TRUE, FALSE)>
        zimbraCalResAutoDeclineRecurring: zimbraCalResAutoDeclineRecurring_value_from_server
        # Bâtiment <String>
        zimbraCalResBuilding: zimbraCalResBuilding_value_from_server
        # Capacité <Integer>
        zimbraCalResCapacity: zimbraCalResCapacity_value_from_server
        # Adresse mail du contact <String>
        zimbraCalResContactEmail: zimbraCalResContactEmail_value_from_server
        # Nom du contact <String>
        zimbraCalResContactName: zimbraCalResContactName_value_from_server
        # Téléphone du contact <String>
        zimbraCalResContactPhone: zimbraCalResContactPhone_value_from_server
        # Etage <String>
        zimbraCalResFloor: zimbraCalResFloor_value_from_server
        # Nom du lieu affiché <String>
        zimbraCalResLocationDisplayName: zimbraCalResLocationDisplayName_value_from_server
        # Salle <String>
        zimbraCalResRoom: zimbraCalResRoom_value_from_server
        # Lieu <String>
        zimbraCalResSite: zimbraCalResSite_value_from_server
        # Notes libres <String>
        zimbraNotes: zimbraNotes_value_from_server
        # Faire suivre les invitations de calendrier à cette adresse <Array>
        zimbraPrefCalendarForwardInvitesTo: zimbraPrefCalendarForwardInvitesTo_value_from_server
```
