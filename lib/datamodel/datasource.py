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


from collections.abc import KeysView, ValuesView, ItemsView
from typing import Any, Iterator

from lib.datamodel.dataobject import DataObject
from lib.datamodel.dataobjectlist import DataObjectList
from lib.datamodel.dataschema import Dataschema

from copy import deepcopy
import logging

logger = logging.getLogger("hermes")


class Datasource:
    """Generic data source offering basic methods for data access
    Also offers optional trashbin and cache management
    """

    def __init__(
        self,
        schema: Dataschema,
        enableTrashbin: bool = False,
        enableCache: bool = True,
        cacheFilePrefix: str = "",
        cacheFileSuffix: str = "",
    ):
        self._hasTrashbin: bool = enableTrashbin
        self._hasCache: bool = enableCache
        self.__cacheFilePrefix: str = cacheFilePrefix
        self.__cacheFileSuffix: str = cacheFileSuffix
        self.schema: Dataschema = schema
        """Copy of Dataschema used to build current datasource"""

        self._data: dict[str, DataObjectList] = {}
        """Dictionary containing the datamodel object types specified in server datamodel
        or in client schema with object name as key, and their corresponding
        DataObjectList as value"""

        for objtype, objlistcls in self.schema.objectlistTypes.items():
            self._data[objtype] = objlistcls(from_json_dict=[])

        if self._hasTrashbin:
            for objtype, objlistcls in self.schema.objectlistTypes.items():
                self._data["trashbin_" + objtype] = objlistcls(from_json_dict=[])

        if self._hasCache:
            self._cache: Datasource = Datasource(
                schema=self.schema,
                enableTrashbin=self._hasTrashbin,
                enableCache=False,
                cacheFilePrefix=cacheFilePrefix,
                cacheFileSuffix=cacheFileSuffix,
            )
            self._cache.loadFromCache()

    @property
    def cache(self) -> "Datasource":
        """Returns the cache"""
        if self._hasCache:
            return self._cache
        raise AttributeError("Asking for cache on an instance with cache disabled")

    def loadFromCache(self):
        for objtype, objlistcls in self.schema.objectlistTypes.items():
            self._data[objtype] = objlistcls.loadcachefile(
                f"{self.__cacheFilePrefix}{objtype}{self.__cacheFileSuffix}"
            )

        if self._hasTrashbin:
            for objtype, objlistcls in self.schema.objectlistTypes.items():
                self._data["trashbin_" + objtype] = objlistcls.loadcachefile(
                    f"{self.__cacheFilePrefix}trashbin_{objtype}{self.__cacheFileSuffix}"
                )

    def save(self):
        for objtype in self.schema.objectlistTypes:
            self._data[objtype].savecachefile(
                f"{self.__cacheFilePrefix}{objtype}{self.__cacheFileSuffix}"
            )

        if self._hasTrashbin:
            for objtype in self.schema.objectlistTypes:
                self._data["trashbin_" + objtype].savecachefile(
                    f"{self.__cacheFilePrefix}trashbin_{objtype}{self.__cacheFileSuffix}"
                )

    def updatePrimaryKeys(self, newpkeys: dict[str, str]):
        """Will update primary keys. newpkeys is a dict with objtype as key,
        and the new primary key attribute name as value.
        Data update will be processed for each objtype specified, and then, if no error
        was met, the cache files will be saved.
        The Datasource MUST be re-instantiated by caller to reflect Dataschema changes,
        and update data in memory.
        """
        for objtype, newpkey in newpkeys.items():
            self._updatePrimaryKeysOf(objtype, objtype, newpkey)
            if self._hasTrashbin:
                self._updatePrimaryKeysOf(f"trashbin_{objtype}", objtype, newpkey)

        # No error met during update, save cache files
        for objtype in newpkeys.keys():
            self._data[objtype].savecachefile(
                f"{self.__cacheFilePrefix}{objtype}{self.__cacheFileSuffix}"
            )
            if self._hasTrashbin:
                self._data[f"trashbin_{objtype}"].savecachefile(
                    f"{self.__cacheFilePrefix}trashbin_{objtype}{self.__cacheFileSuffix}"
                )

    def _updatePrimaryKeysOf(self, dest: str, objtype: str, newpkey: str):
        """Update primary keys of specified objtype, stored in specified dest.
        newpkey is the new primary key attribute name.
        """
        objlistcls = self.schema.objectlistTypes[objtype]
        prevdata = self._data[dest]
        newdata = objlistcls(objlist=[])
        obj: DataObject
        for obj in prevdata:
            newobj: DataObject = deepcopy(obj)
            newobj.setPKey(getattr(obj, newpkey))
            newdata.append(newobj)

        self._data[dest] = newdata

    def __len__(self) -> int:
        return self._data.__len__()

    def __getitem__(self, key: str) -> DataObjectList:
        return self._data.__getitem__(key)

    def __setitem__(self, key: str, value: DataObjectList):
        self._data.__setitem__(key, value)

    def __delitem__(self, key: str):
        self._data.__delitem__(key)

    def __iter__(self) -> Iterator[str]:
        return self._data.__iter__()

    def __reversed__(self) -> Iterator[str]:
        return self._data.__reversed__()

    def __contains__(self, key: str) -> bool:
        return self._data.__contains__(key)

    def keys(self) -> KeysView[str]:
        return self._data.keys()

    def values(self) -> ValuesView[DataObjectList]:
        return self._data.values()

    def items(self) -> ItemsView[str, DataObjectList]:
        return self._data.items()

    def get(self, key: str, default: Any = None) -> DataObjectList | Any:
        return self._data.get(key, default)

    def clear(self):
        return self._data.clear()

    def setdefault(self, key: str, default: DataObjectList) -> DataObjectList:
        return self._data.setdefault(key, default)

    def pop(self, key: str, default: Any = None) -> DataObjectList | Any:
        return self._data.pop(key, default)

    def popitem(self) -> tuple[str, DataObjectList]:
        return self._data.popitem()

    def copy(self) -> dict[str, DataObjectList]:
        return self._data.copy()

    def deepcopy(self) -> dict[str, DataObjectList]:
        return deepcopy(self._data)

    def update(self, **kwargs: DataObjectList):
        self._data.update(kwargs)
