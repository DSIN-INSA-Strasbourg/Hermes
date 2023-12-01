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


from typing import Any, Iterable

import time

from lib.datamodel.diffobject import DiffObject
from lib.datamodel.dataobject import DataObject, HermesMergingConflictError
from lib.datamodel.serialization import LocalCache

import logging

logger = logging.getLogger("hermes")


class DataObjectList(LocalCache):
    """Generic serializable list of DataObject

    Subclasses must define the following class vars:
    - OBJTYPE: data type contained in list, mandatory for deserialization

    The class provides
    - data storage
    - index creation for DataObject.PRIMARYKEY_ATTRIBUTE.
      Indexed data is accessible by self[pkeyvalue].
    - inconsistencices (duplicates) detection and replacement by cache values
    - mergeConflicts detection and replacement by cache values
    - merge_constraints and integrity_constraints filtered items storage with respective
      attributes mergeFiltered and integrityFiltered
    - json serialization/deserialization
    - diffFrom() function generating DiffFrom object
    """

    OBJTYPE: "type[DataObject]" = DataObject
    """Object type stored by current class"""

    def __init__(
        self,
        objlist: list[DataObject] | None = None,
        from_json_dict: list[dict[str, Any]] | None = None,
    ):
        """Create a new instance, with data coming from json (for deserialization),
        or from specified list of DataObject.

        If data is from json, every objects will be instantiated by deserialization.
        If data is from objlist, every object of another type that self.OBJTYPE will be
        casted to OBJTYPE
        """
        super().__init__(jsondataattr="_data")

        self._inconsistencies: set[Any] = set()
        """Set containing primary keys of all duplicated entries"""

        self._mergeConflicts: set[Any] = set()
        """Set containing primary keys of each entry with a merge conflict (i.e. when the
        same attribute has different values on different sources)"""

        self.mergeFiltered: set[Any] = set()
        """Set containing primary keys of each entry filtered by merge constraints"""

        self.integrityFiltered: set[Any] = set()
        """Set containing primary keys of each entry filtered by integrity constraints"""

        self._datadict: dict[Any, DataObject] = {}
        """Dictionary containing the data, with primary keys as keys, and DataObject as values"""

        if objlist is None and from_json_dict is None:
            err = f"Cannot instantiate object from nothing: you must specify one data source"
            logger.critical(err)
            raise AttributeError(err)

        if objlist is not None and from_json_dict is not None:
            err = f"Cannot instantiate object from multiple data sources at once"
            logger.critical(err)
            raise AttributeError(err)

        if objlist is not None:
            self.__init_from_objlist__(objlist)
        elif from_json_dict is not None:
            self.__init_from_json_dict__(from_json_dict)

    def __init_from_json_dict__(self, from_json_dict: list[dict[str, Any]]):
        """Create a new instance, with data coming from json.
        Every objects in list will be instantiated by deserialization."""
        self.__init_from_objlist__(
            [self.OBJTYPE(from_json_dict=item) for item in from_json_dict]
        )

    def __init_from_objlist__(self, objlist: list[DataObject]):
        """Create a new instance, with data from specified list of DataObject.
        Every object of another type that self.OBJTYPE will be casted to OBJTYPE.
        """
        for obj in objlist:
            self.append(obj)

    @property
    def _data(self) -> list[DataObject]:
        """Returns a list of current DataObject values"""
        return [self._datadict[k] for k in sorted(self._datadict.keys())]

    def __iter__(self) -> Iterable:
        """Returns an iterator of current DataObject values"""
        return iter(self._datadict.values())

    def __getitem__(self, pkey: Any) -> DataObject:
        """Indexer operator '[]' returning DataObject entry with specified pkey"""
        return self._datadict[pkey]

    def __contains__(self, objOrPkey: Any) -> bool:
        """'in' operator: return True if specified DataObject or pkey exists in current instance"""
        if isinstance(objOrPkey, DataObject):
            return objOrPkey.getPKey() in self._datadict
        else:
            return objOrPkey in self._datadict

    def get(self, pkey: Any, __default: Any = None) -> Any:
        """Returns DataObject entry with specified pkey, or __default value if no entry was found"""
        return self._datadict.get(pkey, __default)

    def getPKeys(self) -> set[Any]:
        """Returns a set of each primary key of current DataObject values"""
        return set(self._datadict.keys())

    def append(self, obj: DataObject):
        """Append specified object to current instance.
        If obj is of another type than self.OBJTYPE, it will be casted to OBJTYPE.
        If obj is already in current instance, it will be put in _inconsistencies
        """
        if type(obj) == self.OBJTYPE:
            objconverted = obj
        else:
            # Recreate object with the required type (useful when merging data from datamodel)
            objconverted = self.OBJTYPE(from_json_dict=obj.toNative())

        pkey = objconverted.getPKey()
        if pkey in self._inconsistencies | self._mergeConflicts:
            # logger.debug(
            #     f"<{self.__class__.__name__}> Ignoring {objconverted=} because already known as an inconsistency"
            # )
            return

        if pkey not in self._datadict:
            self._datadict[pkey] = objconverted
        else:
            logger.warning(
                f"<{self.__class__.__name__}> Trying to insert an already existing object: {objconverted=}"
            )
            self._inconsistencies.add(pkey)
            del self._datadict[pkey]

    def replace(self, obj: DataObject):
        """Replace specified DataObject (i.e. with same pkey, but different values) in
        current instance"""
        pkey = obj.getPKey()
        if pkey not in self._datadict:
            raise IndexError(
                f"Cannot replace object with pkey {pkey} as previous doesn't exist"
            )
        self._datadict[pkey] = obj

    def removeByPkey(self, pkey: Any):
        """Remove DataObject corresponding to specified pkey from current instance"""
        if pkey in self._datadict:
            del self._datadict[pkey]

    def remove(self, obj: DataObject):
        """Remove specified DataObject from current instance"""
        self.removeByPkey(obj.getPKey())

    def toNative(self) -> list[dict[str, Any]]:
        """Return a list of complete data dict of current DataObject values"""
        return [item.toNative() for item in self._datadict.values()]

    def mergeWith(
        self,
        objlist: list[DataObject],
        pkeyMergeConstraint: str,
        dontMergeOnConflict=False,
    ) -> set[Any]:
        """Merge specified objlist data in current
        If dontMergeOnConflict is True, pkeys of items with conflict will be put in
        mergeConflicts and items will be removed of current list. Otherwise conflicting data
        of item in current instance will be kept
        Returns a set containing pkeys of items filtered by pkeyMergeConstraint
        """

        validsPkeyMergeConstraints = (
            "noConstraint",
            "mustNotExist",
            "mustAlreadyExist",
            "mustExistInBoth",
        )

        if pkeyMergeConstraint not in validsPkeyMergeConstraints:
            raise AttributeError(
                f"Specified {pkeyMergeConstraint=} is invalid. Valiid values are {validsPkeyMergeConstraints}"
            )

        pkeysMerged = set()
        pkeysToRemove = set()
        pkeysIgnored = set()

        for obj in objlist:
            pkey = obj.getPKey()
            if pkey not in self.getPKeys():
                if pkeyMergeConstraint in ("noConstraint", "mustNotExist"):
                    # Constraint is respected, add object
                    pkeysMerged.add(pkey)
                    self.append(obj)
                elif pkeyMergeConstraint in ("mustAlreadyExist", "mustExistInBoth"):
                    # Constraint isn't respected, don't merge object, nothing else to do
                    pkeysIgnored.add(pkey)
            else:
                if pkeyMergeConstraint in (
                    "noConstraint",
                    "mustAlreadyExist",
                    "mustExistInBoth",
                ):
                    # Constraint is respected, merge object
                    pkeysMerged.add(pkey)
                    newobj = self[pkey]
                    try:
                        newobj.mergeWith(obj, dontMergeOnConflict)
                    except HermesMergingConflictError:
                        self._mergeConflicts.add(pkey)
                        self.removeByPkey(pkey)
                    else:
                        # newobj may be a new instance, so overwrite current reference in datadict
                        self.replace(newobj)
                elif pkeyMergeConstraint == "mustNotExist":
                    # Constraint isn't respected, remove object
                    pkeysToRemove.add(pkey)

        if pkeyMergeConstraint == "mustExistInBoth":
            pkeysToRemove |= self.getPKeys() - pkeysMerged

        if pkeysToRemove:
            for pkey in pkeysToRemove:
                self.removeByPkey(pkey)

        logger.debug(
            f"pkey_merge_constraints: merged {len(pkeysMerged)} objects, ignored {len(pkeysIgnored)} objects, removed {len(pkeysToRemove)} objects from {type(self)}"
        )

        return pkeysIgnored | pkeysToRemove

    def diffFrom(self, other: "DataObjectList") -> DiffObject:
        """Returns a DiffObject containing differences between current instance and
        specified 'other', assuming current is the newest"""
        starttime = time.time()
        diff = DiffObject()

        s = self.getPKeys()
        o = other.getPKeys()
        commonattrs = s & o

        diff.appendRemoved([other[pkey] for pkey in (o - s)])
        diff.appendAdded([self[pkey] for pkey in (s - o)])

        for pkey, obj in self._datadict.items():
            if pkey in commonattrs:
                diffobj = obj.diffFrom(other[pkey])
                if diffobj:
                    diff.appendModified(diffobj)

        elapsedtime = time.time() - starttime
        elapsed = int(round(1000 * elapsedtime))

        diffcount = [f"{len(v)} {k}" for k, v in diff.dict.items() if len(v) > 0]
        info = ", ".join(diffcount) if diffcount else "no difference"
        logger.debug(
            f"{self.__class__.__name__}: Diffed {len(s)}/{len(o)} entries in {elapsed} ms: {info}"
        )
        return diff

    @property
    def inconsistencies(self) -> set[Any]:
        """Returns a set containing primary keys of all duplicated entries

        Warning: only indicate duplicated entries of first declared source in current type,
        duplicated entries of other sources will be notified in mergeConflicts"""
        return self._inconsistencies.copy()

    def replaceInconsistenciesByCachedValues(self, cache: "DataObjectList"):
        """Replace each entry filtered for inconsistency by their cache value, when existing"""
        for src, srcname in [
            (self._inconsistencies, "inconsistency"),
            (self._mergeConflicts, "merge conflict"),
        ]:
            for pkey in src:
                if pkey in cache.getPKeys():
                    self._datadict[pkey] = cache[pkey]
                    logger.warning(
                        f"Entry of pkey {pkey} with {srcname} found in cache, using cache value"
                    )
                else:
                    # Data shouldn't contains an entry with this pkey anymore, nothing to do
                    logger.warning(
                        f"Entry of pkey {pkey} with {srcname} not found in cache, ignoring it"
                    )

    @property
    def mergeConflicts(self) -> set[Any]:
        """Returns a set containing primary keys of each entry with a merge conflict
        (i.e. when the same attribute has different values on different sources)"""
        return self._mergeConflicts.copy()
