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

# Plugin d'attribut `ldapPasswordHash`

## Description

Ce plugin permet de générer des hachages LDAP aux formats spécifiés, depuis une chaîne contenant un mot de passe en clair.

## Configuration

Vous pouvez configurer une liste facultative de types de hachage par défaut dans les paramètres du plug-in. Cette liste sera utilisée si les types de hachage ne sont pas spécifiés dans les arguments du filtre, sinon les types de hachage spécifiés seront utilisés.

```yaml
hermes:
  plugins:
    attributes:
      ldapPasswordHash:
        settings:
          default_hash_types:
            - SSHA256
            - SSHA384
            - SSHA512
```

Les valeurs valides pour `default_hash_types` sont :

- MD5
- SHA
- SHA256
- SHA384
- SHA512
- SMD5
- SSHA
- SSHA256
- SSHA384
- SSHA512

## Utilisation

```python
ldapPasswordHash(password: str, hashtypes: None | str | list[str] = None) → list[str]
```

Une fois que tout est configuré, vous pouvez générer votre liste de hachages comme ceci dans un filtre Jinja :

```yaml
# Contiendra une liste de hachages de PASSWORD_CLEAR selon les paramètres
# de default_hash_types : SMD5, SSHA, SSHA256, SSHA512
ldap_password_hashes: "{{ PASSWORD_CLEAR | ldapPasswordHash }}"

# Contiendra une liste contenant uniquement le hachage SSHA512 de PASSWORD_CLEAR
ldap_password_hashes: "{{ PASSWORD_CLEAR | ldapPasswordHash('SSHA512') }}"

# Contiendra une liste contenant uniquement les hachages SSHA256
# et SSHA512 de PASSWORD_CLEAR
ldap_password_hashes: "{{ PASSWORD_CLEAR | ldapPasswordHash(['SSHA256', 'SSHA512']) }}"
```
