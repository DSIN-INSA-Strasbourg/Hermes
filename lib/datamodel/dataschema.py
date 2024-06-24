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


from copy import deepcopy
from typing import Any

from lib.datamodel.serialization import LocalCache
from lib.datamodel.dataobject import DataObject
from lib.datamodel.dataobjectlist import DataObjectList
from lib.datamodel.diffobject import DiffObject


class HermesInvalidDataschemaError(Exception):
    """Raised when the dataschema is invalid"""


class Dataschema(LocalCache):
    """Handle the Dataschema computed from server config, or received from server on
    clients side
    This class will offer the main datamodel types names and their corresponding
    DataObject and DataObjectList subclasses in 'objectTypes' and 'objectlistTypes'
    attributes.
    These attributes will be set only once the class method 'fillObjectTypes' have been
    called on server, or at Dataschema instantiation on clients
    """

    def __init__(
        self,
        from_raw_dict: None | dict[str, Any] = None,
        from_json_dict: None | dict[str, Any] = None,
    ):
        """Setup a new DataSchema"""

        self.objectTypes: dict[str, type[DataObject]] = {}
        """Contains the datamodel object types specified in server datamodel or in
        client schema with object name as key, and dynamically created DataObject
        subclass as value
        """

        self.objectlistTypes: dict[str, type[DataObjectList]] = {}
        """Contains the datamodel objectlist types specified in server datamodel or in
        client schema with object name as key, and dynamically created DataObjectList
        subclass as value
        """

        # Args validity check
        if from_raw_dict is None and from_json_dict is None:
            err = (
                "Cannot instantiate schema from nothing: you must specify one data"
                " source"
            )
            __hermes__.logger.critical(err)
            raise AttributeError(err)

        if from_raw_dict is not None and from_json_dict is not None:
            err = "Cannot instantiate schema from multiple data sources at once"
            __hermes__.logger.critical(err)
            raise AttributeError(err)

        from_dict: dict[str, Any] = (
            from_raw_dict if from_raw_dict is not None else from_json_dict
        )

        if from_json_dict is not None:
            # Update data types if imported from json
            for typesettings in from_dict.values():
                for k, v in typesettings.items():
                    if type(v) is list:
                        if k == "PRIMARYKEY_ATTRIBUTE":
                            typesettings[k] = tuple(v)
                        else:
                            typesettings[k] = set(v)
        super().__init__("schema", "_dataschema")

        # Schema validity check
        self._schema: dict[str, Any] = {}

        for objtype, objdata in from_dict.items():
            for attr, attrtype in {
                "HERMES_ATTRIBUTES": [list, tuple, set],
                "SECRETS_ATTRIBUTES": [list, tuple, set],
                "CACHEONLY_ATTRIBUTES": [list, tuple, set],
                "LOCAL_ATTRIBUTES": [list, tuple, set],
                "PRIMARYKEY_ATTRIBUTE": [str, list, tuple],
            }.items():
                if attr not in objdata:
                    if attr in ("CACHEONLY_ATTRIBUTES", "LOCAL_ATTRIBUTES"):
                        objdata[attr] = set()
                    else:
                        raise HermesInvalidDataschemaError(
                            f"'{objtype}' is missing the attribute '{attr}' in received"
                            " json Dataschema"
                        )
                if type(objdata[attr]) not in attrtype:
                    raise HermesInvalidDataschemaError(
                        f"'{objtype}.{attr}' has wrong type in received json Dataschema"
                        f" ('{type(objdata[attr])}' instead of '{attrtype}')"
                    )
            self._schema[objtype] = {
                "HERMES_ATTRIBUTES": set(objdata["HERMES_ATTRIBUTES"]),
                "SECRETS_ATTRIBUTES": objdata["SECRETS_ATTRIBUTES"],
                "CACHEONLY_ATTRIBUTES": objdata["CACHEONLY_ATTRIBUTES"],
                "LOCAL_ATTRIBUTES": objdata["LOCAL_ATTRIBUTES"],
                "PRIMARYKEY_ATTRIBUTE": objdata["PRIMARYKEY_ATTRIBUTE"],
            }

            if "TOSTRING" in objdata:
                self._schema[objtype]["TOSTRING"] = objdata["TOSTRING"]
            else:
                self._schema[objtype]["TOSTRING"] = None

        self._setupDataobjects()

    def _setupDataobjects(self):
        """Set up dynamic subclasses according to schema"""
        self.fillObjectTypes(self._schema.keys())

        for objname, objcls in self.objectTypes.items():
            objcls.HERMES_ATTRIBUTES = set(self._schema[objname]["HERMES_ATTRIBUTES"])
            objcls.SECRETS_ATTRIBUTES = self._schema[objname]["SECRETS_ATTRIBUTES"]
            objcls.CACHEONLY_ATTRIBUTES = self._schema[objname]["CACHEONLY_ATTRIBUTES"]
            objcls.LOCAL_ATTRIBUTES = self._schema[objname]["LOCAL_ATTRIBUTES"]
            objcls.PRIMARYKEY_ATTRIBUTE = self._schema[objname]["PRIMARYKEY_ATTRIBUTE"]
            objcls.TOSTRING = self._schema[objname]["TOSTRING"]
            # Remove TOSTRING as we don't need it anymore, and because a compiled Jinja
            # template can't be copied with deepcopy
            del self._schema[objname]["TOSTRING"]
            __hermes__.logger.debug(
                f"<{objname} has been set up from schema>:"
                f" PRIMARYKEY_ATTRIBUTE='{objcls.PRIMARYKEY_ATTRIBUTE}'"
                f" - HERMES_ATTRIBUTES={objcls.HERMES_ATTRIBUTES}"
                f" - SECRETS_ATTRIBUTES={objcls.SECRETS_ATTRIBUTES}"
                f" - CACHEONLY_ATTRIBUTES={objcls.CACHEONLY_ATTRIBUTES}"
                f" - LOCAL_ATTRIBUTES={objcls.LOCAL_ATTRIBUTES}"
            )

    def fillObjectTypes(self, objnames: list[str]):
        """Create empty dynamic subclasses from list of datamodel object types names"""
        # Delete old and unused classes if schema has changed
        for objname in self.objectTypes.keys() - set(objnames):
            del self.objectTypes[objname]
            del self.objectlistTypes[objname]

        # (Re-)create classes
        for objname in objnames:
            self.objectTypes[objname] = Dataschema.createSubclass(objname, DataObject)

            objlistcls = Dataschema.createSubclass(
                # The trailing underscore is here to avoid name conflicts between
                # DataObjectLists and server DatamodelFragment DataObjects
                objname + "List_",
                DataObjectList,
            )
            objlistcls.OBJTYPE = self.objectTypes[objname]
            self.objectlistTypes[objname] = objlistcls

    @staticmethod
    def createSubclass(name: str, baseClass: type[Any]) -> type[Any]:
        """Dynamically create a subclass of baseClass with specified name, and return
        it"""
        newclass: type[Any] = type(name, (baseClass,), {})
        newclass._clsname_ = name
        return newclass

    def diffFrom(self, other: "Dataschema") -> DiffObject:
        """Return DiffObject with differences (attributes names) of current instance
        from another"""
        diff = DiffObject()

        s = self.schema.keys()
        o = other.schema.keys()
        commonattrs = s & o

        diff.appendRemoved(o - s)
        diff.appendAdded(s - o)

        for k, v in self.schema.items():
            if k in commonattrs and DataObject.isDifferent(v, other.schema[k]):
                diff.appendModified(k)

        return diff

    def secretsAttributesOf(self, objtype: str) -> set[str]:
        """Returns a set containing the SECRETS_ATTRIBUTES of specified objtype
        As the set is returned by reference, it MUST not be modified
        """
        return self._schema[objtype]["SECRETS_ATTRIBUTES"]

    @property
    def schema(self) -> dict[str, Any]:
        """Returns the public schema (without CACHEONLY_ATTRIBUTES and
        LOCAL_ATTRIBUTES)"""
        schema = deepcopy(self._schema)
        for objschema in schema.values():
            objschema["HERMES_ATTRIBUTES"] -= (
                objschema["CACHEONLY_ATTRIBUTES"] | objschema["LOCAL_ATTRIBUTES"]
            )
            del objschema["CACHEONLY_ATTRIBUTES"]
            del objschema["LOCAL_ATTRIBUTES"]

        return schema
