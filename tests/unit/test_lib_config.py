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


import unittest

import __main__

import os
import shutil
import signal
from types import FrameType

from .hermestestcase import HermesServerTestCase
from lib.config import (
    HermesConfig,
    HermesInvalidAppname,
    HermesConfigError,
    HermesInvalidConfigSchemaKey,
)


class TestConfigClass(unittest.TestCase):
    fixturesdir = f"{os.path.realpath(os.path.dirname(__file__))}/fixtures"

    def test_validateAppname(self):
        """Test Config._validateAppname"""
        config = HermesConfig(autoload=False)

        for name in ["server", "client-whathever"]:
            self.assertIsNone(config._validateAppname(name))
        for name in [None, 42, ["list"]]:
            self.assertRaisesRegex(
                HermesInvalidAppname,
                "The specified name is of type '<class '[^']+'>' instead of 'str'",
                config._validateAppname,
                name,
            )
        for name in ["other", "client-"]:
            self.assertRaisesRegex(
                HermesInvalidAppname,
                "The specified name '[^']+' doesn't respect app naming scheme. Please refer to the documentation",
                config._validateAppname,
                name,
            )

    def test_getRequiredSchemas_for_server(self):
        """Test Config._getRequiredSchemas in server context"""
        config = HermesConfig(autoload=False)

        config["appname"] = "hermes-server"
        schemas = config._getRequiredSchemas()
        self.assertEqual(list(schemas.keys()), ["hermes", "hermes-server"])
        self.assertRegex(schemas["hermes"], r"/config/config-schema.yml$")
        self.assertRegex(schemas["hermes-server"], r"/server/config-schema-server.yml$")

    def test_getRequiredSchemas_for_client(self):
        """Test Config._getRequiredSchemas in client context"""
        config = HermesConfig(autoload=False)

        config["appname"] = "hermes-client-whathever"
        schemas = config._getRequiredSchemas()
        self.assertEqual(
            list(schemas.keys()), ["hermes", "hermes-client", "hermes-client-whathever"]
        )
        self.assertRegex(schemas["hermes"], r"/config/config-schema.yml$")
        self.assertRegex(
            schemas["hermes-client"], r"/clients/config-schema-client.yml$"
        )
        self.assertRegex(
            schemas["hermes-client-whathever"],
            r"/clients/whathever/config-schema-client-whathever.yml$",
        )

    def test_mergeSchemas_with_empty_schema(self):
        """Test Config._mergeSchemas"""
        __main__.__file__ = f"{os.getcwd()}/hermes.py"
        config = HermesConfig(autoload=False)

        config["appname"] = "hermes-server"
        schemas = config._getRequiredSchemas()

        schemas["hermestestempty"] = f"{self.fixturesdir}/schema_files/empty_schema.yml"
        merged = config._mergeSchemas(schemas)
        self.assertSetEqual(set(merged.keys()), set(["hermes", "hermes-server"]))

    def test_mergeSchemas_with_invalid_schema_several_keys(self):
        """Test Config._mergeSchemas"""
        __main__.__file__ = f"{os.getcwd()}/hermes.py"
        config = HermesConfig(autoload=False)

        config["appname"] = "hermes-server"
        schemas = config._getRequiredSchemas()

        schemas[
            "hermestestschema"
        ] = f"{self.fixturesdir}/schema_files/invalid_several_keys.yml"
        self.assertRaises(HermesInvalidConfigSchemaKey, config._mergeSchemas, schemas)

    def test_mergeSchemas_with_invalid_schema_key_name(self):
        """Test Config._mergeSchemas"""
        __main__.__file__ = f"{os.getcwd()}/hermes.py"
        config = HermesConfig(autoload=False)

        config["appname"] = "hermes-server"
        schemas = config._getRequiredSchemas()

        schemas[
            "hermestestschema"
        ] = f"{self.fixturesdir}/schema_files/invalid_key_name.yml"
        self.assertRaises(HermesInvalidConfigSchemaKey, config._mergeSchemas, schemas)


class TestConfig_Server(HermesServerTestCase):
    def test_valid(self):
        confdata = self.loadYaml()
        self.saveYaml(confdata)

        config = HermesConfig(autoload=False)
        self.assertIsNone(config.load())

    def test_duplicated_keys(self):
        shutil.copy(
            f"{self.fixturesdir}/config_files/duplicated_keys.yml", self.conffile
        )

        config = HermesConfig(autoload=False)

        self.assertRaisesRegex(
            HermesConfigError,
            "Duplicate key 'enable_compression' found in config",
            config.load,
        )

    def test_invalid_schema(self):
        confdata = self.loadYaml()
        del confdata["hermes"]["plugins"]["messagebus"]
        self.saveYaml(confdata)
        config = HermesConfig(autoload=False)

        self.assertRaisesRegex(
            HermesConfigError,
            "{'hermes': \[{'plugins': \[{'messagebus': \['required field'\]}\]}\]}",
            config.load,
        )

    def test_DatasourcesPlugins_are_loaded(self):
        from plugins.datasources.ldap.ldap import DatasourceLdap
        from plugins.datasources.oracle.oracle import DatasourceOracle

        confdata = self.loadYaml()
        config = self.saveYamlAndLoadConfig(confdata)
        self.assertIsInstance(
            config["hermes"]["plugins"]["datasources"]["source1"]["plugininstance"],
            DatasourceOracle,
        )
        self.assertIsInstance(
            config["hermes"]["plugins"]["datasources"]["source2"]["plugininstance"],
            DatasourceLdap,
        )

    def test_MessageBusPlugins_are_loaded(self):
        from plugins.messagebus_producers.sqlite.sqlite import SqliteProducerPlugin

        confdata = self.loadYaml()
        config = self.saveYamlAndLoadConfig(confdata)
        self.assertIsInstance(
            config["hermes"]["plugins"]["messagebus"]["sqlite"]["plugininstance"],
            SqliteProducerPlugin,
        )
        self.assertIsInstance(
            config["hermes"]["plugins"]["messagebus"]["plugininstance"],
            SqliteProducerPlugin,
        )

    def test_AttributesPlugins_are_loaded(self):
        from plugins.attributes.crypto_RSA_OAEP.crypto_RSA_OAEP import (
            Attribute_Crypto_RSA_OAEP_Plugin,
        )

        confdata = self.loadYaml()
        config = self.saveYamlAndLoadConfig(confdata)
        self.assertIsInstance(
            config["hermes"]["plugins"]["attributes"]["crypto_RSA_OAEP"][
                "plugininstance"
            ],
            Attribute_Crypto_RSA_OAEP_Plugin,
        )
        self.assertTrue(
            callable(
                config["hermes"]["plugins"]["attributes"]["_jinjafilters"][
                    "crypto_RSA_OAEP"
                ]
            ),
            "'crypto_RSA_OAEP' jinjafilter is not callable",
        )

    def test_setSignalsHandler_SIGINT(self):
        """Test Config.setSignalsHandler"""
        self.signalReceived = False
        config = HermesConfig(autoload=False)
        config.setSignalsHandler(self.signalHandler)
        os.kill(os.getpid(), signal.SIGINT)  # Send SIGINT to current process
        self.assertTrue(self.signalReceived)

    def test_setSignalsHandler_SIGTERM(self):
        """Test Config.setSignalsHandler"""
        self.signalReceived = False
        config = HermesConfig(autoload=False)
        config.setSignalsHandler(self.signalHandler)
        os.kill(os.getpid(), signal.SIGTERM)  # Send SIGTERM to current process
        self.assertTrue(self.signalReceived)

    def signalHandler(self, signalnumber: int, frame: FrameType | None):
        """Signal handler that will be called on SIGINT and SIGTERM"""
        self.signalReceived = True
