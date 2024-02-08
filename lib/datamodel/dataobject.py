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


from lib.datamodel.diffobject import DiffObject
from lib.datamodel.serialization import JSONSerializable

from jinja2.environment import Template
from typing import Any


class HermesMergingConflictError(Exception):
    """Raised when merging two objects with the same attribute having different values"""


class DataObject(JSONSerializable):
    """Generic serializable object to create from several external sources

    Subclasses MUST define the following class vars:
    - HERMES_TO_REMOTE_MAPPING
    - HERMES_ATTRIBUTES
    - REMOTE_ATTRIBUTES
    - INTERNALATTRIBUTES
    - SECRETS_ATTRIBUTES
    - LOCAL_ATTRIBUTES
    - CACHEONLY_ATTRIBUTES
    - PRIMARYKEY_ATTRIBUTE

    The class provides
    - data storage
    - json serialization/deserialization
    - full equality/difference operators based on attributes name and content
    - diffFrom() function generating DiffFrom object
    """

    HERMES_TO_REMOTE_MAPPING: dict[str, Any] = {}
    """Mapping dictionary containing datamodel attributes as key, and datasources fields
    as values, eventually stored in a list. Used by DataObject only on server side"""
    REMOTE_ATTRIBUTES: set[str] = None
    """Set containing datamodel fields. Used by DataObject and Datamodel only on server
    side"""
    HERMES_ATTRIBUTES: set[str] = None
    """Set containing datamodel attributes fields. Used by DataObject"""
    INTERNALATTRIBUTES: set[str] = set(["_trashbin_timestamp"])
    """Set containing internal datamodel fields. Used by DataObject"""
    SECRETS_ATTRIBUTES: set[str] = None
    """Set containing password attributes fields. Used by DataObject"""
    LOCAL_ATTRIBUTES: set[str] = None
    """Set containing attributes names that won't be sent in events, cached or used for
    diff. Used by DataObject"""
    CACHEONLY_ATTRIBUTES: set[str] = None
    """Set containing attributes names that won't be sent in events or used for diff, but
    will be cached. Used by DataObject"""
    PRIMARYKEY_ATTRIBUTE: str | tuple[str, ...] = None
    """String or tuple of strings containing datamodel primary key(s) attribute name(s)"""
    TOSTRING: Template | None = None
    """Contains a compiled Jinja template for objects repr/string representation if set in
    datamodel, or None to use default one"""

    def __init__(
        self,
        from_remote: dict[str, Any] | None = None,
        from_json_dict: dict[str, Any] | None = None,
        jinjaContextVars: dict[str, Any] = {},
    ):
        """Create a new instance, with data coming from json (for deserialization),
        or from remote source.

        If data is from json, no check will be done.
        If data is from remote, every attributes specified in REMOTE_ATTRIBUTES must
        exists in from_remote dict, eventually with None value to be ignored

        jinjaContextVars may contains additional vars to pass to Jinja render() method when
        called with 'from_remote'
        """
        super().__init__(jsondataattr="_jsondata")
        self._hash = None

        if from_remote is None and from_json_dict is None:
            err = f"Cannot instantiate object from nothing: you must specify one data source"
            __hermes__.logger.critical(err)
            raise AttributeError(err)

        if from_remote is not None and from_json_dict is not None:
            err = f"Cannot instantiate object from multiple data sources at once"
            __hermes__.logger.critical(err)
            raise AttributeError(err)

        if from_remote is not None:
            self.__init_from_remote__(from_remote, jinjaContextVars)
        elif from_json_dict is not None:
            self.__init_from_json_dict__(from_json_dict)

    def __init_from_remote__(
        self, from_remote: dict[str, Any], jinjaContextVars: dict[str, Any] = {}
    ):
        """Create a new instance from remote source, check that all attributes in
        REMOTE_ATTRIBUTES/HERMES_TO_REMOTE_MAPPING are set, and ignore others.
        Will render Jinja template if any, passing a merged dict of from_remote
        and jinjaContextVars"""
        if self.REMOTE_ATTRIBUTES is None:
            raise AttributeError(
                f"Current class {self.__class__.__name__} can't be instantiated with 'from_remote' args as {self.__class__.__name__}.REMOTE_ATTRIBUTES is not defined"
            )
        missingattrs = self.REMOTE_ATTRIBUTES.difference(from_remote.keys())
        if len(missingattrs) > 0:
            err = f"Required attributes are missing from specified from_remote dict: {missingattrs}"
            __hermes__.logger.critical(err)
            raise AttributeError(err)

        self._data: dict[str, Any] = {}
        for attr, remoteattr in self.HERMES_TO_REMOTE_MAPPING.items():
            if isinstance(remoteattr, Template):  # May be a compiled Jinja Template
                result = remoteattr.render(jinjaContextVars | from_remote)
                if type(result) == list:
                    result = [v for v in result if v is not None]
                if result is not None and result != []:
                    self._data[attr] = result
            elif type(remoteattr) == str:
                if from_remote[remoteattr] is not None:
                    self._data[attr] = from_remote[remoteattr]
            elif type(remoteattr) == list:
                self._data[attr] = []
                for remoteattritem in remoteattr:
                    value = from_remote[remoteattritem]
                    if value is not None:
                        self._data[attr].append(value)
                if len(self._data[attr]) == 0:
                    del self._data[attr]
            else:
                err = f"Invalid type met in HERMES_TO_REMOTE_MAPPING['{attr}']: {type(remoteattr)}"
                __hermes__.logger.critical(err)
                raise AttributeError(err)

    def __init_from_json_dict__(self, from_json_dict: dict[str, Any]):
        """Create a new instance from json source, without checking anything"""
        self._data = from_json_dict.copy()

    def __getattribute__(self, attr: str) -> Any:
        """Return attribute from "data" dict or from instance"""
        try:
            return super().__getattribute__("_data")[attr]
        except (KeyError, AttributeError, TypeError):
            return super().__getattribute__(attr)

    def __setattr__(self, attr: str, value: Any):
        """Set attribute in "data" dict (and reset instance hash cache) if attrname exists
        in HERMES_ATTRIBUTES or INTERNALATTRIBUTES. Otherwise set it in "standard" python
        way"""
        if attr not in (self.HERMES_ATTRIBUTES | self.INTERNALATTRIBUTES):
            super().__setattr__(attr, value)
        else:
            self._hash = None
            self._data[attr] = value

    def __delattr__(self, attr: str):
        """Remove attribute from "data" dict (and reset instance hash cache) if attrname
        exists in it. Otherwise remove it in "standard" python way"""
        if attr not in self._data:
            super().__delattr__(attr)
        else:
            self._hash = None
            del self._data[attr]

    def __eq__(self, other) -> bool:
        """Equality operator, computed on hash equality"""
        return hash(self) == hash(other)

    def __ne__(self, other) -> bool:
        """Difference operator, computed on hash difference"""
        return hash(self) != hash(other)

    def __lt__(self, other) -> bool:
        """Less than operator, used for sorting. Computed on primary key comparison"""
        return self.getPKey() < other.getPKey()

    def __hash__(self) -> int:
        """Hash operator, compute hash based on attrnames and values, ignoring internal,
        local and cacheonly attributes. As the computation is slow, the value is cached
        """
        if self._hash is None:
            keys = tuple(
                sorted(
                    set(self._data.keys())
                    - self.INTERNALATTRIBUTES
                    - self.LOCAL_ATTRIBUTES
                    - self.CACHEONLY_ATTRIBUTES
                )
            )
            self._hash = hash(
                (
                    hash(keys),
                    hash(
                        tuple(
                            [
                                (
                                    tuple(self._data[k])
                                    if type(self._data[k]) == list
                                    else self._data[k]
                                )
                                for k in keys
                            ]
                        )
                    ),
                )
            )
        return self._hash

    @property
    def _jsondata(self) -> dict[str, Any]:
        """Return serializable data (all data minus LOCAL_ATTRIBUTES and
        SECRETS_ATTRIBUTES)"""
        return {
            k: self._data[k]
            for k in sorted(self._data.keys())
            if k not in self.LOCAL_ATTRIBUTES | self.SECRETS_ATTRIBUTES
        }

    def diffFrom(self, other: "DataObject") -> DiffObject:
        """Return DiffObject with differences (attributes names) of current instance from
        another"""
        diff = DiffObject(self, other)

        s = set(
            self._data.keys()
            - self.INTERNALATTRIBUTES
            - self.LOCAL_ATTRIBUTES
            - self.CACHEONLY_ATTRIBUTES
        )
        o = set(
            other._data.keys()
            - self.INTERNALATTRIBUTES
            - self.LOCAL_ATTRIBUTES
            - self.CACHEONLY_ATTRIBUTES
        )
        commonattrs = s & o

        diff.appendRemoved(o - s)
        diff.appendAdded(s - o)

        for k, v in self._data.items():
            if k in commonattrs and DataObject.isDifferent(v, other._data[k]):
                diff.appendModified(k)

        return diff

    @staticmethod
    def isDifferent(a: Any, b: Any) -> bool:
        """Test true difference between two object: recursive compare of type,
        len and values"""
        if type(a) != type(b):
            return True

        if type(a) == list:
            if len(a) != len(b):
                return True
            else:
                for i in range(len(a)):
                    if DataObject.isDifferent(a[i], b[i]):
                        return True
        elif type(a) == dict:
            if a.keys() != b.keys():
                return True
            else:
                for k in a.keys():
                    if DataObject.isDifferent(a[k], b[k]):
                        return True
        else:
            return a != b

        return False

    def toNative(self) -> dict[str, Any]:
        """Return complete data dict"""
        return self._data

    def toEvent(self) -> dict[str, Any]:
        """Return data to send in Event (all data minus LOCAL_ATTRIBUTES and
        CACHEONLY_ATTRIBUTES)"""
        return {
            k: self._data[k]
            for k in self._data.keys()
            - self.LOCAL_ATTRIBUTES
            - self.CACHEONLY_ATTRIBUTES
        }

    def mergeWith(self, other: "DataObject", raiseExceptionOnConflict=False):
        """Merge data of current instance with another"""
        for k, v in other._data.items():
            if not hasattr(self, k):
                # Attribute wasn't set, so set it from other's value
                setattr(self, k, v)
            elif self.isDifferent(v, getattr(self, k)):
                # Attribute was set, and had another value than other's
                err = (
                    f"Merging conflict. Attribute '{k}' exist on both objects with"
                    f" differents values ({repr(self)}:"
                    f" '{getattr(self, k)}' / {repr(other)}: '{v}')"
                )
                if raiseExceptionOnConflict:
                    raise HermesMergingConflictError(err)
                else:
                    __hermes__.logger.debug(f"{err}. The first one is kept")
            # else: attributes have same value

    def getPKey(self) -> Any:
        """Return primary key value"""
        if type(self.PRIMARYKEY_ATTRIBUTE) == tuple:
            return tuple([getattr(self, key) for key in self.PRIMARYKEY_ATTRIBUTE])
        else:
            return getattr(self, self.PRIMARYKEY_ATTRIBUTE)

    def getType(self) -> str:
        """Return current class name"""
        return self.__class__.__name__

    def __repr__(self) -> str:
        """String representation of current instance"""
        if isinstance(self.TOSTRING, Template):
            return self.TOSTRING.render(self._data)
        else:
            return f"<{self.getType()}[{self.getPKey()}]>"

    def __str__(self) -> str:
        """Multiline string representation of current instance, with data it contains"""
        lf = "\n"
        ret = repr(self)
        for attr in sorted(self._data):
            if attr in self.SECRETS_ATTRIBUTES:
                ret += f"{lf}  - {attr}: <SECRET_VALUE({type(getattr(self, attr))})>"
            else:
                ret += f"{lf}  - {attr}: {repr(getattr(self, attr))}"
        return ret
