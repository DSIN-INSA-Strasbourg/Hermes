<!--
Hermes : Change Data Capture (CDC) tool from any source(s) to any target
Copyright (C) 2025 INSA Strasbourg

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

# `regex_search` attribute plugin

## Description

This plugin allows to search in a string to extract the part that matches the specified regular expression.

## Configuration

Nothing to configure for the plugin.

```yaml
hermes:
  plugins:
    attributes:
      regex_search:
```

## Usage

```python
regex_search(string: str, regex: str, multiline=False, ignorecase=False) → list[str] | None
```

As this plugin is just an adaptation of Ansible's `regex_search_filter`, you can also check [its documentation](https://docs.ansible.com/ansible/latest/collections/ansible/builtin/regex_search_filter.html).

```yaml
# Will be unset (contains None)
regex_results: "{{ 'foo' | regex_search('bar') }}"

# Will be unset (contains None)
regex_results: "{{ 'foobar' | regex_search('foo$') }}"

# Will contain 'foo'
regex_results: "{{ 'foobar' | regex_search('^foo') }}"

# Will contain 'foobar'
regex_results: "{{ 'foobar' | regex_search('^foo.*$') }}"


# Below is a more complex approach, where LDAP_PASSWORD_HASHES is a list of LDAP password hashes:
# LDAP_PASSWORD_HASHES:
#   - "{SMD5}NGnIxNg+ZqB3XwhQK/jCRDWWpUQYVbwg"
#   - "{SSHA}9u8ZbEbeLPLI2f4isG7YjJsz6sfonjQAfbbadQ=="
#   - "{SSHA256}l0rZ10MhH6jKGogg2qFvCdiNAqkKVH9OuL0R3FgWRrV4mIaYM2cnYQ=="
#   - "{SSHA512}zKR46tmGg0NKq1FdkmLGZCqXqfnApvFRHSTW4H0Sem9zJH66mgZ6/aB/aypGX+dLAI02akd9lZbplX6y0Typzzir8RIKh6cw,"

# Will contain ['{SSHA}9u8ZbEbeLPLI2f4isG7YjJsz6sfonjQAfbbadQ==']
regex_results: "{{ LDAP_PASSWORD_HASHES | map('regex_search', '^{SSHA}.*$') | reject('none') | list }}"

# Will contain ['{SSHA}9u8ZbEbeLPLI2f4isG7YjJsz6sfonjQAfbbadQ==', '{SSHA512}zKR46tmGg0NKq1FdkmLGZCqXqfnApvFRHSTW4H0Sem9zJH66mgZ6/aB/aypGX+dLAI02akd9lZbplX6y0Typzzir8RIKh6cw,']
regex_results: "{{ LDAP_PASSWORD_HASHES | map('regex_search', '^({SSHA}|{SSHA512}).*$') | reject('none') | list }}"
```
