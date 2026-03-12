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


from clients import GenericClient
from lib.config import HermesConfig
from lib.datamodel.dataobject import DataObject

import os
import os.path
from typing import Any

HERMES_PLUGIN_CLASSNAME = "FlatfilesEmailsOfGroups"


class FlatfilesEmailsOfGroups(GenericClient):
    """Hermes-client class that does nothing but logging"""

    def __init_settings(self):
        self.destdir: str = self.config["destDir"]
        self.onlyTheseGroups: list[str] = self.config["onlyTheseGroups"]

    def __init__(self, config: HermesConfig):
        super().__init__(config)
        self.__init_settings()
        self.groupsChanged: set[Any] = set()
        """Will contains pkeys of groups to update"""

    def _updateGroupFile(self, group: DataObject, evtsrc: str):
        if self.onlyTheseGroups and group.name not in self.onlyTheseGroups:
            return

        if evtsrc == "GroupsMembers":
            emails = self._getEmailFromGroupsMembers(group)
        elif evtsrc == "MembersOfGroups":
            emails = self._getEmailFromMembersOfGroups(group)
        else:
            raise AssertionError(f"BUG ! Invalid event src met: {evtsrc=}")

        with open(f"{self.destdir}/{group.name}.txt", "+wt") as fd:
            fd.write("\n".join(sorted(emails)))

    def _getEmailFromGroupsMembers(self, group: DataObject) -> list[str]:
        groupmembers = self.getDataobjectlistFromCache("GroupsMembers")
        users_pkey = set(
            [gm.user_pkey for gm in groupmembers if gm.group_pkey == group.getPKey()]
        )

        users = self.getDataobjectlistFromCache("Users")
        return [u.mail for u in users if u.getPKey() in users_pkey]

    def _getEmailFromMembersOfGroups(self, group: DataObject) -> list[str]:
        membersLogins: set[str] = set(
            getattr(
                self.getDataobjectlistFromCache("MembersOfGroups").get(group.getPKey()),
                "groupmembers",
                [],
            )
        )
        emails = set()

        for user in self.getDataobjectlistFromCache("Users"):
            if getattr(user, "login", None) in membersLogins:
                if hasattr(user, "mail"):
                    emails.add(user.mail)

        return emails

    def on_Groups_removed(
        self, objkey: Any, eventattrs: "dict[str, Any]", cachedobj: DataObject
    ):
        path = f"{self.destdir}/{cachedobj.name}.txt"
        if os.path.isfile(path):
            os.remove(path)

    def on_GroupsMembers_added(
        self, objkey: Any, eventattrs: "dict[str, Any]", newobj: DataObject
    ):
        self.groupsChanged.add(
            (newobj.group_pkey, "GroupsMembers"),
        )

    def on_GroupsMembers_removed(
        self, objkey: Any, eventattrs: "dict[str, Any]", cachedobj: DataObject
    ):
        self.groupsChanged.add(
            (cachedobj.group_pkey, "GroupsMembers"),
        )

    def on_MembersOfGroups_added(
        self, objkey: Any, eventattrs: "dict[str, Any]", newobj: DataObject
    ):
        self.groupsChanged.add(
            (newobj.group_pkey, "MembersOfGroups"),
        )

    def on_MembersOfGroups_recycled(
        self, objkey: Any, eventattrs: "dict[str, Any]", newobj: DataObject
    ):
        self.groupsChanged.add(
            (newobj.group_pkey, "MembersOfGroups"),
        )

    def on_MembersOfGroups_modified(
        self,
        objkey: Any,
        eventattrs: "dict[str, Any]",
        newobj: DataObject,
        cachedobj: DataObject,
    ):
        self.groupsChanged.add(
            (newobj.group_pkey, "MembersOfGroups"),
        )

    def on_MembersOfGroups_trashed(
        self, objkey: Any, eventattrs: "dict[str, Any]", cachedobj: DataObject
    ):
        self.groupsChanged.add(
            (cachedobj.group_pkey, "MembersOfGroups"),
        )

    def on_MembersOfGroups_removed(
        self, objkey: Any, eventattrs: "dict[str, Any]", cachedobj: DataObject
    ):
        self.groupsChanged.add(
            (cachedobj.group_pkey, "MembersOfGroups"),
        )

    def on_save(self):
        for pkey, evtsrc in self.groupsChanged:
            try:
                group = self.getObjectFromCache("Groups", pkey)
            except IndexError:
                continue
            self._updateGroupFile(group, evtsrc)
        self.groupsChanged = set()
