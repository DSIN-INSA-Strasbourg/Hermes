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


from clients import GenericClient
from lib.datamodel.dataobject import DataObject

from typing import Any

HERMES_PLUGIN_CLASSNAME = "NullClient"


class NullClient(GenericClient):
    """Hermes-client class that does nothing but logging"""

    def on_Users_added(
        self, objkey: Any, eventattrs: "dict[str, Any]", newobj: DataObject
    ):
        pass

    def on_Users_recycled(
        self, objkey: Any, eventattrs: "dict[str, Any]", newobj: DataObject
    ):
        pass

    def on_Users_modified(
        self,
        objkey: Any,
        eventattrs: "dict[str, Any]",
        newobj: DataObject,
        cachedobj: DataObject,
    ):
        pass

    def on_Users_trashed(
        self, objkey: Any, eventattrs: "dict[str, Any]", cachedobj: DataObject
    ):
        pass

    def on_Users_removed(
        self, objkey: Any, eventattrs: "dict[str, Any]", cachedobj: DataObject
    ):
        pass

    def on_Groups_added(
        self, objkey: Any, eventattrs: "dict[str, Any]", newobj: DataObject
    ):
        pass

    def on_Groups_recycled(
        self, objkey: Any, eventattrs: "dict[str, Any]", newobj: DataObject
    ):
        pass

    def on_Groups_modified(
        self,
        objkey: Any,
        eventattrs: "dict[str, Any]",
        newobj: DataObject,
        cachedobj: DataObject,
    ):
        pass

    def on_Groups_trashed(
        self, objkey: Any, eventattrs: "dict[str, Any]", cachedobj: DataObject
    ):
        pass

    def on_Groups_removed(
        self, objkey: Any, eventattrs: "dict[str, Any]", cachedobj: DataObject
    ):
        pass

    def on_GroupsMembers_added(
        self, objkey: Any, eventattrs: "dict[str, Any]", newobj: DataObject
    ):
        pass

    def on_GroupsMembers_recycled(
        self, objkey: Any, eventattrs: "dict[str, Any]", newobj: DataObject
    ):
        pass

    def on_GroupsMembers_trashed(
        self, objkey: Any, eventattrs: "dict[str, Any]", cachedobj: DataObject
    ):
        pass

    def on_GroupsMembers_removed(
        self, objkey: Any, eventattrs: "dict[str, Any]", cachedobj: DataObject
    ):
        pass

    def on_UserPasswords_added(
        self,
        objkey: Any,
        eventattrs: "dict[str, Any]",
        newobj: DataObject,
    ):
        pass

    def on_UserPasswords_modified(
        self,
        objkey: Any,
        eventattrs: "dict[str, Any]",
        newobj: DataObject,
        cachedobj: DataObject,
    ):
        pass

    def on_UserPasswords_removed(
        self, objkey: Any, eventattrs: "dict[str, Any]", cachedobj: DataObject
    ):
        pass
