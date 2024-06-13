#!/usr/bin/python3
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


from typing import Any, Callable, Hashable, Iterable
from types import FrameType

from cerberus import Validator
from copy import deepcopy
import argparse
import importlib
import os.path
import sys
import signal
import threading
import warnings
import yaml
from lib.datamodel.serialization import LocalCache
from lib.plugins import (
    AbstractAttributePlugin,
    AbstractDataSourcePlugin,
    AbstractMessageBusConsumerPlugin,
    AbstractMessageBusProducerPlugin,
)
from lib.utils.singleton import SingleInstance, SingleInstanceException

import lib.utils.logging


class HermesConfigError(Exception):
    """Raised when the config file doesn't validate the config schema"""


class HermesInvalidAppname(Exception):
    """Raised when the appname specified on launch doesn't respect app naming scheme"""


class HermesInvalidConfigSchemaKey(Exception):
    """Raised when one config schema is defining another key than its name"""


class HermesPluginNotFoundError(Exception):
    """Raised when specified plugin is not found"""


class HermesPluginError(Exception):
    """Raised when specified plugin exists but cannot be imported"""


class HermesPluginClassNotFoundError(Exception):
    """Raised when declared plugin class cannot be found"""


class YAMLUniqueKeyCSafeLoader(yaml.CSafeLoader):
    """Override yaml load to raise an error when some duplicated keys are found
    Tweak found on https://gist.github.com/pypt/94d747fe5180851196eb?permalink_comment_id=4015118#gistcomment-4015118
    """

    def construct_mapping(self, node, deep=False) -> dict[Hashable, Any]:
        mapping = set()
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in mapping:
                raise HermesConfigError(f"Duplicate key '{key}' found in config")
            mapping.add(key)
        return super().construct_mapping(node, deep)


class HermesConfig(LocalCache):
    """Load, validate config from config file, and expose config dict via current instance

    config always contains the following keys:
    - appname: the current app name (hermes-server, hermes-client-ldap, ...)
    - hermes: hermes global config, for servers and clients

    For server, it will contains too:
    - hermes-server: config for server

    For clients, it will contains too:
    - hermes-client: global config for client, for options defined in GenericClient (e.g. trashbinRetentionInDays)
    - hermes-client-CLIENTNAME: specific config for client. e.g. LDAP connection settings for hermes-client-ldap

    The instance contains the method setSignalsHandler() that can be called to define a
    handler for SIGINT and SIGTERM
    """

    def __init__(
        self,
        autoload: bool = True,
        from_json_dict: None | dict[str, Any] = None,
        allowMultipleInstances: bool = False,
    ):
        """Setup a config instance, and call load() if autoload is True"""
        self._config: dict[str, Any] = {}
        """ Configuration dictionary """
        self._rawconfig: dict[str, Any] = {}
        """ Raw configuration dictionary (merges config files, without plugins instances) """
        self._allowMultipleInstances: bool = allowMultipleInstances
        """Indicate if we must abort if another instance is already running"""

        warnings.filterwarnings(
            "ignore",
            "_SixMetaPathImporter.find_spec.. not found; falling back to find_module..",
            ImportWarning,
        )
        warnings.filterwarnings(
            "ignore",
            "_SixMetaPathImporter.exec_module.. not found; falling back to load_module..",
            ImportWarning,
        )

        if from_json_dict is not None:
            self._rawconfig = from_json_dict
            self._config = deepcopy(self._rawconfig)
            super().__init__(jsondataattr="_rawconfig", cachefilename="_hermesconfig")
            if self.hasData():
                self._loadDatasourcesPlugins()
                self._loadMessageBusPlugins()
                self._loadAttributesPlugins()
        else:
            if autoload:
                self.load()

    def savecachefile(self, cacheFilename: str | None = None):
        """Override method only to disable backup files in cache"""
        return super().savecachefile(cacheFilename, dontKeepBackup=True)

    def load(self, loadplugins: bool = True, dontManageCacheDir: bool = False):
        """Load and validate config of current appname, and fill config dictionary.
        Setup logging, and signals handlers.
        Load plugins, and validate their config.
        """
        self._config = {}
        self._setAppname()
        schemas = self._getRequiredSchemas()
        schema = self._mergeSchemas(schemas)

        with open(f"""{self._config["appname"]}-config.yml""") as f:
            config = yaml.load(f, Loader=YAMLUniqueKeyCSafeLoader)

        validator = Validator(schema)
        if not validator.validate(config):
            raise HermesConfigError(validator.errors)

        self._config |= validator.normalized(config)
        self._rawconfig = deepcopy(self._config)

        # Setup logging
        lib.utils.logging.setup_logger(self)
        LocalCache.setup(self)  # Update cache files settings

        super().__init__(
            jsondataattr="_rawconfig",
            cachefilename="_hermesconfig",
            dontManageCacheDir=dontManageCacheDir,
        )

        if not self._allowMultipleInstances:
            # Ensure no other instance is already running
            try:
                self.__me = SingleInstance(self._config["appname"])
            except SingleInstanceException:
                sys.exit(1)

        # Load plugins
        if loadplugins:
            self._loadDatasourcesPlugins()
            self._loadMessageBusPlugins()
            self._loadAttributesPlugins()

    def setSignalsHandler(self, handler: Callable[[int, FrameType | None], None]):
        """Defines a handler that will intercept thoses signals: SIGINT, SIGTERM

        The handler prototype is:
            handler(signalnumber: int, frame: FrameType | None) -> None
        See https://docs.python.org/3/library/signal.html#signal.signal
        """
        if threading.current_thread() is not threading.main_thread():
            # Do nothing if ran in a sub thread
            # (should happen only from from functional tests)
            return
        for signum in [signal.SIGINT, signal.SIGTERM]:
            signal.signal(signum, handler)

    def __getitem__(self, key: Any) -> Any:
        """Returns config value of specified config key"""
        return self._config[key]

    def __setitem__(self, key: Any, value: Any):
        """Set specified config value of specified config key"""
        self._config[key] = value

    def __delitem__(self, key: Any):
        """Delete config value of specified config key"""
        del self._config[key]

    def __iter__(self) -> Iterable:
        """Iterate over top level config keys"""
        return iter(self._config)

    def __len__(self) -> int:
        """Returns number of items at top level of config"""
        return len(self._config)

    def hasData(self) -> bool:
        """Allow to test if current config contains minimal entries"""
        return "appname" in self

    def _setAppname(self):
        """Determine and store appname in config dict on first arg passed to hermes.py

        Apps MUST respect the following naming scheme:
        - server for server
        - client-CLIENTNAME for clients

        The computed appname will be prefixed by 'hermes-'
        """
        parser = argparse.ArgumentParser(description="Hermes launcher", add_help=False)
        parser.add_argument(
            "appname",
            help="The Hermes application to launch ('server', 'client-ldap', ...)",
        )
        (args, _) = parser.parse_known_args()
        self._validateAppname(args.appname)
        self._config["appname"] = f"hermes-{args.appname}"

    def _validateAppname(self, name: str):
        """Validate specified name upon appname scheme.

        Raise HermesInvalidAppname if name is invalid
        """
        if type(name) != str:
            raise HermesInvalidAppname(
                f"The specified name is of type '{type(name)}' instead of 'str'"
            )

        if name == "server":
            return

        if name.startswith("client-") and len(name) > len("client-"):
            return

        raise HermesInvalidAppname(
            f"The specified name '{name}' doesn't respect app naming scheme. Please refer to the documentation"
        )

    def _getRequiredSchemas(self) -> dict[str, str]:
        """Fill a dict containing main config key and absolute path of config schemas required by current appname.
        Those values will be used to build Cerberus validation schema in order to validate config file.
        """
        main = self._config["appname"]

        # Retrieve absolute path of hermes source directory
        appdir = os.path.realpath(os.path.dirname(__file__) + "/../../")

        schemas = {
            # Global config
            "hermes": f"{appdir}/lib/config/config-schema.yml",
        }

        if main == "hermes-server":
            # Server config
            schemas |= {"hermes-server": f"{appdir}/server/config-schema-server.yml"}
        elif main.startswith("hermes-client-"):
            # Client
            clientname = main[len("hermes-client-") :]
            schemas |= {
                # Global client config
                "hermes-client": f"{appdir}/clients/config-schema-client.yml",
                # Client plugin config
                f"hermes-client-{clientname}": f"{appdir}/plugins/clients/{clientname}/config-schema-client-{clientname}.yml",
            }

        return schemas

    @staticmethod
    def _mergeSchemas(schemas: dict[str, str]) -> dict[str, Any]:
        """Return a dict containing Cerberus validation schema for current appname"""
        schema: dict[str, Any] = {}
        for name, path in schemas.items():
            with open(path) as f:
                curschema = yaml.load(f, Loader=YAMLUniqueKeyCSafeLoader)

            if curschema is None:  # A schema can be empty
                continue

            if len(curschema) > 1 or list(curschema.keys())[0] != name:
                raise HermesInvalidConfigSchemaKey(
                    f"The schema defined in '{path}' must define only the schema of key '{name}'. "
                    f"It currently defines { list(set(curschema.keys()) - set([name])) }"
                )
            schema |= curschema

        return schema

    def _loadPlugin(
        self,
        pluginFamilyDir: str,
        pluginName: str,
        pluginSuperClass: type,
        pluginSubDictInConf: dict,
        pluginSettingsDotPath: str,
    ):
        """Generic plugin loader"""
        # Retrieve absolute path of hermes source directory
        appdir = os.path.realpath(os.path.dirname(__file__) + "/../../")

        modulepath = f"plugins.{pluginFamilyDir}.{pluginName}.{pluginName}"
        try:
            module = importlib.import_module(modulepath)
        except ModuleNotFoundError as e:
            raise HermesPluginNotFoundError(
                f"Unable to load plugin '{pluginName}' of type '{pluginFamilyDir}': {str(e)}"
            )
        except Exception as e:
            raise HermesPluginError(
                f"Unable to load plugin '{pluginName}' of type '{pluginFamilyDir}', probably due to a syntax error in plugin code: {str(e)}"
            )

        try:
            plugin_cls = getattr(module, module.HERMES_PLUGIN_CLASSNAME)
        except AttributeError as e:
            raise HermesPluginClassNotFoundError(str(e))
        path = f"{appdir}/plugins/{pluginFamilyDir}/{pluginName}/config-schema-plugin-{pluginName}.yml"

        with open(path) as f:
            schema = yaml.load(f, Loader=YAMLUniqueKeyCSafeLoader)

        validator = Validator(schema)
        if not validator.validate(pluginSubDictInConf["settings"]):
            raise HermesConfigError(f"{pluginSettingsDotPath}: {validator.errors}")

        pluginSubDictInConf["settings"] = validator.normalized(
            pluginSubDictInConf["settings"]
        )
        pluginSubDictInConf["plugininstance"] = plugin_cls(
            pluginSubDictInConf["settings"]
        )
        if not isinstance(pluginSubDictInConf["plugininstance"], pluginSuperClass):
            raise TypeError(
                f"Plugin <{pluginName}> is not a subclass of '{pluginSuperClass.__name__}'"
            )
        __hermes__.logger.info(f"Loaded plugin {pluginFamilyDir}/{pluginName}")

    def _loadDatasourcesPlugins(self):
        """Load every Datasources plugins"""
        if self["appname"] != "hermes-server":
            return

        for name, source in self["hermes"]["plugins"]["datasources"].items():
            pluginname = source["type"]
            self._loadPlugin(
                pluginFamilyDir="datasources",
                pluginName=pluginname,
                pluginSuperClass=AbstractDataSourcePlugin,
                pluginSubDictInConf=source,
                pluginSettingsDotPath=f"hermes.plugins.datasources.{name}.settings",
            )

    def _loadMessageBusPlugins(self):
        """Load every MessageBus plugins"""
        if self["appname"] == "hermes-server":
            familydir = "messagebus_producers"
            superclass = AbstractMessageBusProducerPlugin
        else:
            familydir = "messagebus_consumers"
            superclass = AbstractMessageBusConsumerPlugin

        for pluginname, source in self["hermes"]["plugins"]["messagebus"].items():
            self._loadPlugin(
                pluginFamilyDir=familydir,
                pluginName=pluginname,
                pluginSuperClass=superclass,
                pluginSubDictInConf=source,
                pluginSettingsDotPath=f"hermes.plugins.messagebus.{pluginname}.settings",
            )
        # As only one can be registered, put instance one level upper
        self["hermes"]["plugins"]["messagebus"]["plugininstance"] = source[
            "plugininstance"
        ]

    def _loadAttributesPlugins(self):
        """Load every Attributes plugins"""
        jinjafilters = {}

        for pluginname, source in self["hermes"]["plugins"]["attributes"].items():
            self._loadPlugin(
                pluginFamilyDir="attributes",
                pluginName=pluginname,
                pluginSuperClass=AbstractAttributePlugin,
                pluginSubDictInConf=source,
                pluginSettingsDotPath=f"hermes.plugins.attributes.{pluginname}.settings",
            )

            jinjafilters[pluginname] = source["plugininstance"].filter

        self["hermes"]["plugins"]["attributes"]["_jinjafilters"] = jinjafilters
