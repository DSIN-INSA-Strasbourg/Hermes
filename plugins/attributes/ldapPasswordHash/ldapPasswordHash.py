#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Hermes : Change Data Capture (CDC) tool from any source(s) to any target
# Copyright (C) 2023, 2024 INSA Strasbourg
#
# This file is part of Hermes.
#
# Hermes is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Hermes is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hermes. If not, see <https://www.gnu.org/licenses/>.


from typing import Type
from jinja2 import Undefined
from passlib.ifc import PasswordHash

from passlib.hash import (
    ldap_md5,
    ldap_sha1,
    ldap_salted_md5,
    ldap_salted_sha1,
    ldap_salted_sha256,
    ldap_salted_sha512,
)


from lib.plugins import AbstractAttributePlugin

HERMES_PLUGIN_CLASSNAME: str | None = "LdapPasswordHashPlugin"
"""The plugin class name defined in this module file"""


class InvalidLdapPasswordHashType(Exception):
    """Raised when an unknown hash type has been requested"""


class LdapPasswordHashPlugin(AbstractAttributePlugin):
    """Plugin to generate LDAP password hashes"""

    __hashclasses: dict[str, Type[PasswordHash]] = {
        "MD5": ldap_md5,
        "SHA": ldap_sha1,
        "SMD5": ldap_salted_md5,
        "SSHA": ldap_salted_sha1,
        "SSHA256": ldap_salted_sha256,
        "SSHA512": ldap_salted_sha512,
    }

    def __init__(self, settings: dict[str, any]) -> None:
        """Instantiate new plugin and store a copy of its settings dict in self._settings"""
        super().__init__(settings)
        self._defaulthashtypes: set[str] = set(self._settings["default_hash_types"])

    def filter(
        self, password: str | None | Undefined, hashtypes: None | str | list[str] = None
    ) -> list[str] | None:
        """Call the plugin with specified value, and returns the result."""

        if password is None:
            return Undefined(hint="No password specified")

        if isinstance(password, Undefined):
            return password

        if type(password) != str:
            raise TypeError(
                f"Invalid type for password: {type(password)=}."
                " Password must be a string"
            )

        if hashtypes is None:
            # No type(s) explicitly specified, use default values specified in config
            _hashtypes: set[str] = self._defaulthashtypes
        else:
            # Use specified type(s), and ensure to store values in a set to filter
            # duplicates
            if type(hashtypes) == str:
                _hashtypes = set([hashtypes])
            elif type(hashtypes) == list:
                _hashtypes = set(hashtypes)
            else:
                raise TypeError(
                    f"Invalid type for hashtypes: {type(hashtypes)=}."
                    " Hashtype must be a string or a list of string"
                )

        unknownHashTypes = _hashtypes - self.__hashclasses.keys()
        if unknownHashTypes:
            raise InvalidLdapPasswordHashType(
                f"Invalid LDAP password hash type specified: {unknownHashTypes}"
            )

        return [
            self.__hashclasses[hashtype].hash(password) for hashtype in set(_hashtypes)
        ]
