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


from clients import GenericClient
from helpers.ldaphash import LDAPHash
from helpers.randompassword import RandomPassword
from lib.config import HermesConfig
from lib.datamodel.dataobject import DataObject

from lib_Partage_BSS.exceptions.ServiceException import ServiceException
from lib_Partage_BSS.models.Account import Account
from lib_Partage_BSS.models.Group import Group
from lib_Partage_BSS.models.Resource import Resource
from lib_Partage_BSS.services import AccountService
from lib_Partage_BSS.services import GroupService
from lib_Partage_BSS.services import ResourceService
from lib_Partage_BSS.services.BSSConnexionService import BSSConnexion

import re

from typing import Any

HERMES_PLUGIN_CLASSNAME = "BSSPartageClient"


class BSSPartageClient(GenericClient):
    """Hermes-client class that does nothing but logging"""

    def __init_settings(self):
        #################
        # Auth settings #
        #################
        self.__auth: dict[str, str] = self.config["authentication"]
        self.domains: list[str] = list(self.__auth.keys())

    def __init__(self, config: HermesConfig):
        super().__init__(config)
        self.__init_settings()
        self.bss = BSSConnexion()
        self.bss.setDomainKey(self.__auth)
        pwd_conf = self.config["random_passwords"]
        self._randomPassword = RandomPassword(
            length=pwd_conf["length"],
            withUpperLetters=pwd_conf["with_upper_letters"],
            minimumNumberOfUpperLetters=pwd_conf["minimum_number_of_upper_letters"],
            withLowerLetters=pwd_conf["with_lower_letters"],
            minimumNumberOfLowerLetters=pwd_conf["minimum_number_of_lower_letters"],
            withNumbers=pwd_conf["with_numbers"],
            minimumNumberOfNumbers=pwd_conf["minimum_number_of_numbers"],
            withSpecialChars=pwd_conf["with_special_chars"],
            minimumNumberOfSpecialChars=pwd_conf["minimum_number_of_special_chars"],
            lettersDict=pwd_conf["letters_dictionary"],
            specialCharsDict=pwd_conf["special_chars_dictionary"],
            avoidAmbigousChars=pwd_conf["avoid_ambigous_chars"],
            ambigousCharsdict=pwd_conf["ambigous_chars_dictionary"],
        )

    def on_Users_added(
        self, objkey: Any, eventattrs: "dict[str, Any]", newobj: DataObject
    ):
        isAlreadyCreated: bool = False
        account = Account(newobj.name)
        changes = eventattrs.copy()

        if "userPassword" not in changes:
            # Password hash does not exist yet, generating the SSHA512 hash
            # of a random password
            changes["userPassword"] = LDAPHash.hash(
                self._randomPassword.generate(), "SSHA512"
            )
        account.fillAccount(changes)

        if (
            hasattr(newobj, "zimbraZimletAvailableZimlets")
            and newobj.zimbraZimletAvailableZimlets
        ):
            for zimlet in newobj.zimbraZimletAvailableZimlets:
                account.addZimbraZimletAvailableZimlets(zimlet)

        if self.currentStep == 0:
            if self.isAnErrorRetry:
                # Test if account has already been created
                bssAccount = AccountService.getAccount(name=newobj.name)
                if bssAccount is not None:
                    isAlreadyCreated = True
            if isAlreadyCreated:
                AccountService.modifyAccount(account)
            else:
                AccountService.createAccountExt(
                    account=account, password=changes["userPassword"]
                )
            self.isPartiallyProcessed = True
            self.currentStep += 1

        if self.currentStep == 1:
            if "aliases" in changes:
                AccountService.modifyAccountAliases(newobj.name, newobj.aliases)
                self.isPartiallyProcessed = True
            self.currentStep += 1

    def on_Users_recycled(
        self, objkey: Any, eventattrs: "dict[str, Any]", newobj: DataObject
    ):
        if self.currentStep == 0:
            AccountService.activateAccount(newobj.name)
            self.isPartiallyProcessed = True
            self.currentStep += 1

    def on_Users_modified(
        self,
        objkey: Any,
        eventattrs: "dict[str, Any]",
        newobj: DataObject,
        cachedobj: DataObject,
    ):
        changes = {}
        for attrname, value in eventattrs["added"].items():
            changes[attrname] = value
        for attrname, value in eventattrs["modified"].items():
            changes[attrname] = value
        for attrname in eventattrs["removed"].keys():
            changes[attrname] = self.config["default_removed_values"]["Users"].get(
                attrname, None
            )

        if "userPassword" in changes and not changes["userPassword"]:
            changes["userPassword"] = LDAPHash.hash(
                self._randomPassword.generate(), "SSHA512"
            )

        if self.currentStep == 0:
            if cachedobj.name != newobj.name:
                # Account is renamed
                AccountService.renameAccount(cachedobj.name, newobj.name)
                self.isPartiallyProcessed = True
            self.currentStep += 1

        if self.currentStep == 1:
            account = Account(newobj.name)
            if "zimbraZimletAvailableZimlets" in changes:
                del changes["zimbraZimletAvailableZimlets"]
                if newobj.zimbraZimletAvailableZimlets:
                    for zimlet in newobj.zimbraZimletAvailableZimlets:
                        account.addZimbraZimletAvailableZimlets(zimlet)
                else:
                    account.resetZimbraZimletAvailableZimlets()

            account.fillAccount(changes)
            AccountService.modifyAccount(account)
            self.isPartiallyProcessed = True
            self.currentStep += 1

        if self.currentStep == 2:
            if "aliases" in eventattrs["added"] or "aliases" in eventattrs["modified"]:
                AccountService.modifyAccountAliases(newobj.name, newobj.aliases)
                self.isPartiallyProcessed = True
            elif "aliases" in eventattrs["removed"]:
                AccountService.modifyAccountAliases(newobj.name, [])
                self.isPartiallyProcessed = True
            self.currentStep += 1

    def on_Users_trashed(
        self, objkey: Any, eventattrs: "dict[str, Any]", cachedobj: DataObject
    ):
        if self.currentStep == 0:
            AccountService.lockAccount(cachedobj.name)
            self.isPartiallyProcessed = True
            self.currentStep += 1

    def on_Users_removed(
        self, objkey: Any, eventattrs: "dict[str, Any]", cachedobj: DataObject
    ):
        isAlreadyRemoved: bool = False
        if self.currentStep == 0:
            if self.isAnErrorRetry:
                # Test if account has already been removed
                bssAccount = AccountService.getAccount(name=cachedobj.name)
                if bssAccount is None:
                    isAlreadyRemoved = True

            if not isAlreadyRemoved:
                AccountService.deleteAccount(cachedobj.name)
                self.isPartiallyProcessed = True
            self.currentStep += 1

    def on_UserPasswords_added(
        self,
        objkey: Any,
        eventattrs: "dict[str, Any]",
        newobj: DataObject,
    ):
        cacheduser = self.getObjectFromCache("Users", newobj.getPKey())
        changes = {}
        if "userPassword" in eventattrs and eventattrs["userPassword"]:
            changes["userPassword"] = eventattrs["userPassword"]
        else:
            changes["userPassword"] = LDAPHash.hash(
                self._randomPassword.generate(), "SSHA512"
            )

        if self.currentStep == 0:
            account = Account(cacheduser.name)
            account.fillAccount(changes)
            AccountService.modifyAccount(account)
            self.isPartiallyProcessed = True
            self.currentStep += 1

    def on_UserPasswords_modified(
        self,
        objkey: Any,
        eventattrs: "dict[str, Any]",
        newobj: DataObject,
        cachedobj: DataObject,
    ):
        cacheduser = self.getObjectFromCache("Users", newobj.getPKey())
        changes = {}
        if (
            "userPassword" in eventattrs["added"]
            or "userPassword" in eventattrs["modified"]
        ):
            changes["userPassword"] = newobj.userPassword
        elif "userPassword" in eventattrs["removed"]:
            changes["userPassword"] = None

        if "userPassword" in changes and not changes["userPassword"]:
            changes["userPassword"] = LDAPHash.hash(
                self._randomPassword.generate(), "SSHA512"
            )

        if self.currentStep == 0:
            account = Account(cacheduser.name)
            account.fillAccount(changes)
            AccountService.modifyAccount(account)
            self.isPartiallyProcessed = True
            self.currentStep += 1

    def on_UserPasswords_removed(
        self, objkey: Any, eventattrs: "dict[str, Any]", cachedobj: DataObject
    ):
        cacheduser = self.getObjectFromCache("Users", cachedobj.getPKey())
        changes = {}
        changes["userPassword"] = LDAPHash.hash(
            self._randomPassword.generate(), "SSHA512"
        )

        if self.currentStep == 0:
            account = Account(cacheduser.name)
            account.fillAccount(changes)
            AccountService.modifyAccount(account)
            self.isPartiallyProcessed = True
            self.currentStep += 1

    def _addGroup(self, newobj: DataObject, startStep: int):
        isAlreadyCreated: bool = False
        if self.currentStep == startStep:
            group = Group(newobj.name)
            group.from_dict(newobj.toEvent())

            if self.isAnErrorRetry:
                # Test if group has already been created
                bssGroup = GroupService.getGroup(name=newobj.name)
                if bssGroup is not None:
                    isAlreadyCreated = True

            if isAlreadyCreated:
                GroupService.modifyGroup(group)
            else:
                # Create group
                GroupService.createGroup(group)
            self.isPartiallyProcessed = True
            self.currentStep += 1

        if self.currentStep == startStep + 1:
            # Create group aliases
            if len(getattr(newobj, "aliases", [])) > 0:
                GroupService.addGroupAliases(newobj.name, newobj.aliases)
                self.isPartiallyProcessed = True
            self.currentStep += 1

    def _deleteGroup(self, cachedobj: DataObject, startStep: int):
        isAlreadyRemoved: bool = False
        if self.currentStep == startStep:
            if self.isAnErrorRetry:
                # Test if group has already been removed
                bssGroup = GroupService.getGroup(name=cachedobj.name)
                if bssGroup is None:
                    isAlreadyRemoved = True

            if not isAlreadyRemoved:
                GroupService.deleteGroup(cachedobj.name)
                self.isPartiallyProcessed = True
            self.currentStep += 1

    def on_Groups_added(
        self, objkey: Any, eventattrs: "dict[str, Any]", newobj: DataObject
    ):
        self._addGroup(newobj, startStep=0)

    def on_Groups_recycled(
        self, objkey: Any, eventattrs: "dict[str, Any]", newobj: DataObject
    ):
        # Do nothing
        pass

    def on_Groups_modified(
        self,
        objkey: Any,
        eventattrs: "dict[str, Any]",
        newobj: DataObject,
        cachedobj: DataObject,
    ):
        #################
        # GROUP RENAMED #
        #################
        # As group rename isn't directly possible through API, we'll delete
        # then re-create the group
        if cachedobj.name != newobj.name:
            # Delete group (step 0)
            self._deleteGroup(cachedobj, startStep=0)
            # Re-create group (step 1) and group aliases (step 2)
            self._addGroup(newobj, startStep=1)
            # As we have created the group with its new properties, we're done
            return

        if self.currentStep < 3:
            self.currentStep = 3

        #####################
        # GROUP NOT RENAMED #
        #####################
        changes = {}
        for attrname, value in eventattrs["added"].items():
            changes[attrname] = value
        for attrname, value in eventattrs["modified"].items():
            changes[attrname] = value
        for attrname in eventattrs["removed"].keys():
            changes[attrname] = self.config["default_removed_values"]["Groups"].get(
                attrname, None
            )

        if self.currentStep == 3:
            group = Group(cachedobj.name)
            group.from_dict(changes)
            GroupService.modifyGroup(group)
            self.isPartiallyProcessed = True
            self.currentStep += 1

        prevAliases = set(getattr(cachedobj, "aliases", []))
        newAliases = set(getattr(newobj, "aliases", []))
        aliasesToAdd = newAliases - prevAliases
        aliasesToRemove = prevAliases - newAliases

        if self.currentStep == 4:
            if aliasesToRemove:
                GroupService.removeGroupAliases(newobj.name, aliasesToRemove)
                self.isPartiallyProcessed = True
            self.currentStep += 1

        if self.currentStep == 5:
            if aliasesToAdd:
                GroupService.addGroupAliases(newobj.name, aliasesToAdd)
                self.isPartiallyProcessed = True
            self.currentStep += 1

    def on_Groups_trashed(
        self, objkey: Any, eventattrs: "dict[str, Any]", cachedobj: DataObject
    ):
        # Do nothing
        pass

    def on_Groups_removed(
        self, objkey: Any, eventattrs: "dict[str, Any]", cachedobj: DataObject
    ):
        self._deleteGroup(cachedobj, startStep=0)

    def on_GroupsMembers_added(
        self, objkey: Any, eventattrs: "dict[str, Any]", newobj: DataObject
    ):
        cachedgroup = self.getObjectFromCache("Groups", newobj.group_pkey)
        cacheduser = self.getObjectFromCache("Users", newobj.user_pkey)

        if self.currentStep == 0:
            # As a groupmember can be re-added without error, no need to do
            # more tests if self.isAnErrorRetry == True
            GroupService.addGroupMembers(cachedgroup.name, cacheduser.name)
            self.isPartiallyProcessed = True
            self.currentStep += 1

    def on_GroupsMembers_recycled(
        self, objkey: Any, eventattrs: "dict[str, Any]", newobj: DataObject
    ):
        # Do nothing
        pass

    def on_GroupsMembers_trashed(
        self, objkey: Any, eventattrs: "dict[str, Any]", cachedobj: DataObject
    ):
        # Do nothing
        pass

    def on_GroupsMembers_removed(
        self, objkey: Any, eventattrs: "dict[str, Any]", cachedobj: DataObject
    ):
        isAlreadyRemoved: bool = False
        cachedgroup = self.getObjectFromCache("Groups", cachedobj.group_pkey)
        cacheduser = self.getObjectFromCache("Users", cachedobj.user_pkey)

        if self.currentStep == 0:
            if self.isAnErrorRetry:
                bssGroup = GroupService.getGroup(cachedgroup.name)
                if cacheduser.name not in bssGroup.members:
                    isAlreadyRemoved = True
            if not isAlreadyRemoved:
                GroupService.removeGroupMembers(cachedgroup.name, cacheduser.name)
                self.isPartiallyProcessed = True
            self.currentStep += 1

    def on_GroupsSenders_added(
        self, objkey: Any, eventattrs: "dict[str, Any]", newobj: DataObject
    ):
        cachedgroup = self.getObjectFromCache("Groups", newobj.group_pkey)
        cacheduser = self.getObjectFromCache("Users", newobj.user_pkey)

        if self.currentStep == 0:
            # As a groupsender can be re-added without error, no need to do
            # more tests if self.isAnErrorRetry == True
            GroupService.addGroupSenders(cachedgroup.name, cacheduser.name)
            self.isPartiallyProcessed = True
            self.currentStep += 1

    def on_GroupsSenders_recycled(
        self, objkey: Any, eventattrs: "dict[str, Any]", newobj: DataObject
    ):
        # Do nothing
        pass

    def on_GroupsSenders_trashed(
        self, objkey: Any, eventattrs: "dict[str, Any]", cachedobj: DataObject
    ):
        # Do nothing
        pass

    def on_GroupsSenders_removed(
        self, objkey: Any, eventattrs: "dict[str, Any]", cachedobj: DataObject
    ):
        isAlreadyRemoved: bool = False
        cachedgroup = self.getObjectFromCache("Groups", cachedobj.group_pkey)
        cacheduser = self.getObjectFromCache("Users", cachedobj.user_pkey)

        if self.currentStep == 0:
            if self.isAnErrorRetry:
                bssGroup = GroupService.getGroup(cachedgroup.name, full_info=True)
                if cacheduser.name not in bssGroup.senders:
                    isAlreadyRemoved = True
            if not isAlreadyRemoved:
                GroupService.removeGroupSenders(cachedgroup.name, cacheduser.name)
                self.isPartiallyProcessed = True
            self.currentStep += 1

    @staticmethod
    def _ResourceService_getResource(name: str) -> Resource | None:
        """Replacement method of ResourceService.getResource, that fixes its
        behavior when a resource doesn't exist.
        Indeed, the original method does not work as its documentation
        indicates: it raises a ServiceException instead of returning None.
        """
        try:
            bssResource = ResourceService.getResource(name=name)
        except ServiceException as e:
            if re.search("no such calendar resource", e.msg):
                return None
            raise
        else:
            return bssResource

    def _addRessource(self, newobj: DataObject, startStep: int):
        isAlreadyCreated: bool = False
        if self.currentStep == startStep:
            # Re-create ressource
            resource = Resource(newobj.name)
            changes = newobj.toEvent().copy()

            if "zimbraPrefCalendarForwardInvitesTo" in changes:
                del changes["zimbraPrefCalendarForwardInvitesTo"]

            if "userPassword" not in changes:
                # Password hash does not exist yet, generating the SSHA512 hash
                # of a random password
                changes["userPassword"] = LDAPHash.hash(
                    self._randomPassword.generate(), "SSHA512"
                )
            if "zimbraCalResCapacity" in changes and type(
                changes["zimbraCalResCapacity"] is int
            ):
                # Convert zimbraCalResCapacity to string, as it's the only
                # type accepted by lib_Partage_BSS
                changes["zimbraCalResCapacity"] = str(changes["zimbraCalResCapacity"])

            resource.from_dict(changes)

            if self.isAnErrorRetry:
                # Test if ressource has already been created
                bssResource = self._ResourceService_getResource(name=newobj.name)
                if bssResource is not None:
                    isAlreadyCreated = True

            if isAlreadyCreated:
                ResourceService.modifyResource(resource)
            else:
                ResourceService.createResourceExt(resource)
            self.isPartiallyProcessed = True
            self.currentStep += 1

        if self.currentStep == startStep + 1:
            # Add forward adresses to ressource
            #
            # Although the documentation states otherwise, it seems that this
            # attribute cannot be set when creating the resource
            emails = getattr(newobj, "zimbraPrefCalendarForwardInvitesTo", [])
            if emails:
                resource = Resource(newobj.name)
                for email in emails:
                    resource.addZimbraPrefCalendarForwardInvitesTo(email)
                ResourceService.modifyResource(resource)
                self.isPartiallyProcessed = True
            self.currentStep += 1

    def _deleteResource(self, cachedobj: DataObject, startStep: int):
        isAlreadyRemoved: bool = False
        if self.currentStep == startStep:
            if self.isAnErrorRetry:
                # Test if ressource has already been removed
                bssResource = self._ResourceService_getResource(name=cachedobj.name)
                if bssResource is None:
                    isAlreadyRemoved = True

            if not isAlreadyRemoved:
                ResourceService.deleteResource(cachedobj.name)
                self.isPartiallyProcessed = True
            self.currentStep += 1

    def on_Resources_added(
        self, objkey: Any, eventattrs: "dict[str, Any]", newobj: DataObject
    ):
        self._addRessource(newobj, startStep=0)

    def on_Resources_modified(
        self,
        objkey: Any,
        eventattrs: "dict[str, Any]",
        newobj: DataObject,
        cachedobj: DataObject,
    ):
        #####################
        # RESSOURCE RENAMED #
        #####################
        # As ressource rename isn't directly possible through API, we'll delete
        # then re-create the ressource
        if cachedobj.name != newobj.name:
            # Delete ressource (step 0)
            self._deleteResource(cachedobj, startStep=0)
            # Re-create ressource (step 1) and
            # add forward adresses to ressource (step 2)
            self._addRessource(newobj, startStep=1)
            # As we have created the resource with its new properties, we're done
            return

        if self.currentStep < 3:
            self.currentStep = 3

        #########################
        # RESSOURCE NOT RENAMED #
        #########################
        changes = {}
        for attrname, value in eventattrs["added"].items():
            changes[attrname] = value
        for attrname, value in eventattrs["modified"].items():
            changes[attrname] = value
        for attrname in eventattrs["removed"].keys():
            changes[attrname] = self.config["default_removed_values"]["Resources"].get(
                attrname, None
            )

        if "zimbraPrefCalendarForwardInvitesTo" in changes:
            del changes["zimbraPrefCalendarForwardInvitesTo"]

        if "userPassword" in changes and not changes["userPassword"]:
            changes["userPassword"] = LDAPHash.hash(
                self._randomPassword.generate(), "SSHA512"
            )

        if "zimbraCalResCapacity" in changes and type(
            changes["zimbraCalResCapacity"] is int
        ):
            # Convert zimbraCalResCapacity to string, as it's the only
            # type accepted by lib_Partage_BSS
            changes["zimbraCalResCapacity"] = str(changes["zimbraCalResCapacity"])

        if self.currentStep == 3:
            resource = Resource(cachedobj.name)
            resource.from_dict(changes)
            if "zimbraPrefCalendarForwardInvitesTo" in eventattrs["removed"]:
                # Should be the following line, but the method is in
                # lib_Partage_BSS git, but not in pypi latest version:
                # resource.resetZimbraPrefCalendarForwardInvitesTo()
                resource._zimbraPrefCalendarForwardInvitesTo = "DELETE_ARRAY"
            elif (
                "zimbraPrefCalendarForwardInvitesTo" in eventattrs["added"]
                or "zimbraPrefCalendarForwardInvitesTo" in eventattrs["modified"]
            ):
                for email in newobj.zimbraPrefCalendarForwardInvitesTo:
                    resource.addZimbraPrefCalendarForwardInvitesTo(email)

            ResourceService.modifyResource(resource)
            self.isPartiallyProcessed = True
            self.currentStep += 1

    def on_Resources_removed(
        self, objkey: Any, eventattrs: "dict[str, Any]", cachedobj: DataObject
    ):
        self._deleteResource(cachedobj, startStep=0)
