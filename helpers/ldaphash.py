#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Hermes : Change Data Capture (CDC) tool from any source(s) to any target
# Copyright (C) 2024 INSA Strasbourg
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

from typing import Callable, TypedDict
import base64
import hashlib
import os


class _LDAPHashType(TypedDict):
    hashfunc: Callable[[bytes], "hashlib._Hash"]
    saltsize: int | None


class LDAPHash:
    """Helper class to compute LDAP hashes from plaintext passwords"""

    __hashtypes: dict[str, _LDAPHashType] = {
        "MD5": {
            "hashfunc": hashlib.md5,
            "saltsize": None,
        },
        "SHA": {
            "hashfunc": hashlib.sha1,
            "saltsize": None,
        },
        "SHA256": {
            "hashfunc": hashlib.sha256,
            "saltsize": None,
        },
        "SHA384": {
            "hashfunc": hashlib.sha384,
            "saltsize": None,
        },
        "SHA512": {
            "hashfunc": hashlib.sha512,
            "saltsize": None,
        },
        "SMD5": {
            "hashfunc": hashlib.md5,
            # Min 4, max 16
            "saltsize": 4,
        },
        "SSHA": {
            "hashfunc": hashlib.sha1,
            # Min 4, max 16
            "saltsize": 4,
        },
        "SSHA256": {
            "hashfunc": hashlib.sha256,
            # Min 4, max 16
            "saltsize": 8,
        },
        "SSHA384": {
            "hashfunc": hashlib.sha384,
            # Min 4, max 16
            "saltsize": 8,
        },
        "SSHA512": {
            "hashfunc": hashlib.sha512,
            # Min 4, max 16
            "saltsize": 8,
        },
    }

    @staticmethod
    def getAvailableHashtypes() -> list[str]:
        """Returns a list containing all supported hash types"""
        return list(LDAPHash.__hashtypes.keys())

    @staticmethod
    def hash(password: str, hashtype: str) -> str:
        """Returns the LDAP hash of the given password with specified hashtype"""

        if hashtype not in LDAPHash.getAvailableHashtypes():
            raise ValueError(
                f"Specified {hashtype=} is invalid. Valid hashtypes are"
                f" {LDAPHash.getAvailableHashtypes()}"
            )

        hasht: _LDAPHashType = LDAPHash.__hashtypes[hashtype]

        if hasht["saltsize"]:
            salt: bytes = os.urandom(hasht["saltsize"])
        else:
            salt = b""

        # Hash the password and append the salt when applicable
        hash = hasht["hashfunc"](password.encode())
        hash.update(salt)

        # Create a base64 encoded string of the concatenated digest + salt
        base64hash = base64.b64encode(hash.digest() + salt).decode()

        # Prepend the base64hash with the hashtype tag
        return f"{{{hashtype}}}{base64hash}"
