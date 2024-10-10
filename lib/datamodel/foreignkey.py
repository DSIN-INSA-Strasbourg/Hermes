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

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    # Only for type hints, won't import at runtime
    from lib.datamodel.dataobject import DataObject
    from lib.datamodel.datasource import Datasource


class HermesCircularForeignkeysRefsError(Exception):
    """Raised when the some circular foreign keys references are found"""


class ForeignKey:
    """Handle foreign keys, and allow to retrieve foreign objects references"""

    def __init__(
        self,
        from_obj: str,
        from_attr: str,
        to_obj: str,
        to_attr: str,
    ):
        """Setup a new ForeignKey"""
        self._from_obj: str = from_obj
        self._from_attr: str = from_attr
        self._to_obj: str = to_obj
        self._to_attr: str = to_attr

        self._repr: str = (
            f"<ForeignKey({self._from_obj}.{self._from_attr}"
            f" -> {self._to_obj}.{self._to_attr})>"
        )
        self._hash: int = hash(self._repr)

    def __repr__(self) -> str:
        return self._repr

    def __hash__(self) -> int:
        return self._hash

    def __eq__(self, other: "ForeignKey") -> bool:
        return hash(self) == hash(other)

    @staticmethod
    def checkForCircularForeignKeysRefs(
        allfkeys: dict[str, list["ForeignKey"]],
        fkeys: list["ForeignKey"],
        _alreadyMet: list["ForeignKey"] | None = None,
    ):
        """Will check recursively for circular references in foreign keys,
        and raise HermesCircularForeignkeysRefsError if any is found"""
        if _alreadyMet is None:
            _alreadyMet = []

        for fkey in fkeys:
            if fkey in _alreadyMet:
                errmsg = (
                    f"Circular foreign keys references found in {_alreadyMet}."
                    " Unable to continue."
                )
                __hermes__.logger.critical(errmsg)
                raise HermesCircularForeignkeysRefsError(errmsg)
            _alreadyMet.append(fkey)
            ForeignKey.checkForCircularForeignKeysRefs(
                allfkeys, allfkeys[fkey._to_obj], _alreadyMet
            )

    @staticmethod
    def fetchParentObjs(ds: "Datasource", obj: "DataObject") -> list["DataObject"]:
        """Returns a list of parent objects of specified obj from specified
        Datasource ds"""
        res: list["DataObject"] = []
        objlist = ds[obj.getType()]
        for fkey in objlist.FOREIGNKEYS:
            parent = ds[fkey._to_obj].get(getattr(obj, fkey._from_attr))
            if parent is not None:
                res.append(parent)
                res.extend(ForeignKey.fetchParentObjs(ds, parent))
        return res
