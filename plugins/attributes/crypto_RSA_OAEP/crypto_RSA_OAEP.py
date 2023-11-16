#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Hermes : Change Data Capture (CDC) tool from any source(s) to any target
# Copyright (C) 2023 INSA Strasbourg
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


from typing import Any, Type

from Cryptodome.PublicKey import RSA
from Cryptodome.Cipher import PKCS1_OAEP
from Cryptodome.Cipher.PKCS1_OAEP import PKCS1OAEP_Cipher
from Cryptodome.Hash import (
    SHA224,
    SHA256,
    SHA384,
    SHA512,
    SHA3_224,
    SHA3_256,
    SHA3_384,
    SHA3_512,
)
from jinja2 import Undefined

import base64

from lib.plugins import AbstractAttributePlugin

import logging

logger = logging.getLogger("hermes")


HERMES_PLUGIN_CLASSNAME: str | None = "Attribute_Crypto_RSA_OAEP_Plugin"
"""The plugin class name defined in this module file"""


class Attribute_Crypto_RSA_OAEP_Plugin(AbstractAttributePlugin):
    """Plugin to encrypt/decrypt strings with asymetric RSA keys, using PKCS#1
    OAEP,an asymmetric cipher based on RSA and the OAEP padding"""

    __hashclasses: dict[str, Type[Any]] = {
        "SHA224": SHA224,
        "SHA256": SHA256,
        "SHA384": SHA384,
        "SHA512": SHA512,
        "SHA3_224": SHA3_224,
        "SHA3_256": SHA3_256,
        "SHA3_384": SHA3_384,
        "SHA3_512": SHA3_512,
    }

    def __init__(self, settings: dict[str, any]) -> None:
        """Instanciate new plugin and store a copy of its settings dict in self._settings"""
        super().__init__(settings)

        self.__keys: dict[str, tuple[str, PKCS1OAEP_Cipher]] = {}
        for key, keysettings in settings["keys"].items():
            rsa = RSA.importKey(keysettings["rsa_key"])
            operation = "decrypt" if rsa.has_private() else "encrypt"
            self.__keys[key] = (
                operation,
                PKCS1_OAEP.new(
                    rsa,
                    hashAlgo=self.__hashclasses[keysettings["hash"]],
                ),
            )

    def filter(self, value: bytes | str | None | Undefined, keyname: str) -> str:
        """Call the plugin with specified value and keyname, and returns the result.
        The plugin will determine if it's an encryption or a decryption operation upon
        the key type : decryption for private keys, and encryption for public keys.

        Encryption : value is either a byte-array or a string, and result is a base64
        encoded byte-array.

        Decryption : value is either a byte-array or a base64 encoded byte-array, and
        result is a string.
        """
        if keyname not in self.__keys:
            raise IndexError(
                f"Specified {keyname=} doesn't exist in"
                " hermes.plugins.attributes.RSA_OAEP_crypto.settings in config file"
            )

        if value is None:
            return Undefined(hint="No value specified")

        if isinstance(value, Undefined):
            return value

        if type(value) not in (bytes, str):
            raise TypeError(
                f"Invalid value type {type(value)=}. Valid types are (bytes, str)"
            )

        operation, cipherinst = self.__keys[keyname]

        if operation == "decrypt":
            return self.decrypt(value, cipherinst)
        else:
            return self.encrypt(value, cipherinst)

    def encrypt(self, value: bytes | str, cipherinst: PKCS1OAEP_Cipher) -> str:
        """Encrypt the specified value, and returns the resulting byte-array
        encoded in a base64 string"""
        if type(value) == bytes:
            # Raw binary encoded byte array
            value_bytes = value
        else:
            # UTF8 string
            value_bytes = value.encode("utf8")

        return base64.b64encode(cipherinst.encrypt(value_bytes)).decode("ascii")

    def decrypt(self, value: bytes | str, cipherinst: PKCS1OAEP_Cipher) -> str:
        """Decrypt the specified value, and returns the result as a string"""
        if type(value) == bytes:
            # Raw binary encoded byte array
            value_bytes = value
        else:
            # Base64 encoded byte array
            value_bytes = base64.b64decode(value.encode("ascii"))

        return cipherinst.decrypt(value_bytes).decode("utf8")
