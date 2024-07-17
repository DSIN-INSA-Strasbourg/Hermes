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

# `usersgroups_kadmin_heimdal` client plugin

## Description

This client will handle `Users` and `UserPassword`, and store data in an Heimdal Kerberos server.

## Configuration

```yaml
hermes-client-usersgroups_kadmin_heimdal:
  # MANDATORY: Principal with required rights to manage users and passwords in kadmin
  kadmin_login: root/admin
  # MANDATORY: Password of principal above
  kadmin_password: "s3cReT_p4s5w0rD"
  # MANDATORY: Name of Kerberos realm
  kadmin_realm: KERBEROS_REALM

  # Service principal name to get ticket for. Default: kadmin/admin
  kinit_spn: kadmin/admin
  # kinit command to use. Default: kinit.heimdal
  kinit_cmd: kinit.heimdal
  # kadmin command to use. Default: kadmin.heimdal
  kadmin_cmd: kadmin.heimdal
  # kdestroy command to use. Default: kdestroy.heimdal
  kdestroy_cmd: kdestroy.heimdal

  # kadmin additional args to use when adding a user. Must be a list of strings. Default:
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
  
  # Set to true to start with an already filled Kerberos database. Default: false
  dont_fail_on_existing_user: false

  # Optional random password generation settings. Default: values specified below
  # Random password is generated to initialize a user whose password is not yet available,
  # or when the user password is removed but the user still exists
  random_passwords:
    # Password length
    length: 32
    # If true, the generated password may contains some upper cased letters
    with_upper_letters: true
    # The generated password will contain at least this number of upper cased letters
    minimum_number_of_upper_letters: 1
    # If true, the generated password may contains some lower cased letters
    with_lower_letters: true
    # The generated password will contain at least this number of lower cased letters
    minimum_number_of_lower_letters: 1
    # If true, the generated password may contains some numbers
    with_numbers: true
    # The generated password will contain at least this number of numbers
    minimum_number_of_numbers: 1
    # If true, the generated password may contains some special chars
    with_special_chars: true
    # The generated password will contain at least this number of special chars
    minimum_number_of_special_chars: 1
    # If true, the generated password won't contains the chars specified in 'ambigous_chars_dictionary'
    avoid_ambigous_chars: false
    # The dictionary of ambigous chars (case sensitive) that may be forbidden in password, even if some are present in other dictionnaries
    ambigous_chars_dictionary: "lIO01"
    # The dictionary of letters (case unsensitive) allowed in password
    letters_dictionary: "abcdefghijklmnopqrstuvwxyz"
    # The dictionary of special chars allowed in password
    special_chars_dictionary: "!@#$%^&*"
```

## Datamodel

The following data types must be set up:

- `Users`, requires the following attribute names:
  - `login`: the user login, that will be used as principal
- `UserPasswords`, requires the following attribute names:
  - `password`: the password of the user

Obviously, the primary keys of `Users` and `UserPasswords` must match to be able to link login with password.

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
