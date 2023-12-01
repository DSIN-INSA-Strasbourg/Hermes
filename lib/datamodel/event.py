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


import logging

from typing import Any

from lib.datamodel.dataobject import DataObject
from lib.datamodel.diffobject import DiffObject
from lib.datamodel.serialization import JSONSerializable

from datetime import datetime

logger = logging.getLogger("hermes")


class Event(JSONSerializable):
    """Serializable Event message"""

    EVTYPES = ["initsync", "added", "modified", "removed", "dataschema"]

    def __init__(
        self,
        evcategory: str | None = None,
        eventtype: str | None = None,
        obj: DataObject | None = None,
        objattrs: dict[str, Any] | None = None,
        from_json_dict: dict[str, Any] | None = None,
    ):
        """Create Event message
         - of specified category (base/initsync)
         - of specified type (init-start, init-stop, added, modified, removed)
         - with facultative Dataobject instance obj that will be used to store it type and pkey
         - with specified objattrs that should contains a dict with useful attributes in
           current context defined by evcategory and eventtype
        or a from_json_dict to deserialize an Event instance
        """

        if objattrs is None and from_json_dict is None:
            err = f"Cannot instantiate object from nothing: you must specify one data source"
            logger.critical(err)
            raise AttributeError(err)

        if objattrs is not None and from_json_dict is not None:
            err = f"Cannot instantiate object from multiple data sources at once"
            logger.critical(err)
            raise AttributeError(err)

        __jsondataattrs = [
            "evcategory",
            "eventtype",
            "objtype",
            "objpkey",
            "objattrs",
            "step",
        ]
        super().__init__(jsondataattr=__jsondataattrs)
        self.offset: int | None = None
        self.timestamp: datetime = datetime(year=1, month=1, day=1)
        self.step: int = 0
        if from_json_dict is not None:
            for attr in __jsondataattrs:
                if attr in from_json_dict:
                    setattr(self, attr, from_json_dict[attr])
                    if attr == "objpkey" and type(self.objpkey) == list:
                        self.objpkey = tuple(self.objpkey)
            # As obj instance isn't available, use pkey as default repr
            self.objrepr = str(self.objpkey)
        else:
            self.evcategory: str | None = evcategory
            self.eventtype: str | None = eventtype
            if obj is None:
                self.objtype: str | None = None
                self.objpkey: Any = None
                self.objrepr: str | None = None
            else:
                self.objtype = obj.getType()
                self.objpkey = obj.getPKey()
                self.objrepr = repr(obj)
            self.objattrs: dict[str, Any] | None = objattrs

    def __repr__(self) -> str:
        """Returns a printable representation of current Event"""
        category = f"{self.evcategory}_" if self.evcategory != "base" else ""

        if self.objtype is None:
            s = f"<Event({category}{self.eventtype})>"
        else:
            s = f"<Event({category}{self.objtype}_{self.eventtype}[{self.objrepr}])>"
        return s

    def toString(self, secretattrs: set[str]) -> str:
        """Returns a printable string of current Event"""
        category = f"{self.evcategory}_" if self.evcategory != "base" else ""
        objattrs = self.objattrsToString(self.objattrs, secretattrs)

        if self.objtype is None:
            s = f"<Event({category}{self.eventtype}, {objattrs})>"
        else:
            s = f"<Event({category}{self.objtype}_{self.eventtype}[{self.objrepr}], {objattrs})>"
        return s

    @staticmethod
    def objattrsToString(objattrs: dict[str, any], secretattrs: set[str]) -> str:
        """Returns a printable string of current objattrs dict, with specified
        secret attributes filtered"""
        res = {}
        for k, v in objattrs.items():
            if type(v) == dict:
                res[k] = Event.objattrsToString(v, secretattrs)
                continue

            if k in secretattrs:
                res[k] = f"<SECRET_VALUE({type(v)})>"
            else:
                res[k] = v
        return res

    @staticmethod
    def fromDiffItem(
        diffitem: DiffObject | DataObject, eventCategory: str, changeType: str
    ) -> tuple["Event", DataObject]:
        """Convert the specified diffitem (item from DiffObject of two DataObjectList)
        to Event with specified eventCategory and changeType.
        Return the event, and the 'new' DataObject from diffitem"""
        obj: DataObject
        objattrs: dict[str, Any]

        match changeType:
            case "modified":
                # changetype is "modified", so diffitem is a DiffObject
                obj = diffitem.objnew
                objattrs = diffitem.dict
            case "added":
                # changetype isn't "modified", so diffitem is a DataObject
                obj = diffitem
                objattrs = diffitem.toEvent()
            case "removed":
                # changetype isn't "modified", so diffitem is a DataObject
                obj = diffitem
                objattrs = {}
            case "_":
                raise AttributeError(
                    f"Invalid {changeType=} specified: valid values are ['added', 'modified', 'removed']"
                )

        return (
            Event(
                evcategory=eventCategory,
                eventtype=changeType,
                obj=obj,
                objattrs=objattrs,
            ),
            obj,
        )
