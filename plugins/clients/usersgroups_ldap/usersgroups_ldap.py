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
from lib.config import HermesConfig
from lib.datamodel.dataobject import DataObject

from datetime import datetime

import ldap
import ldap.modlist
from ldap import LDAPError

from typing import Any

HERMES_PLUGIN_CLASSNAME = "LdapClient"


class LdapClient(GenericClient):
    """Hermes-client class handling users, passwords, groups and groupMembers in
    LDAP directory"""

    def __handleLDAPError(self, err: LDAPError):
        """All LDAP exceptions contains a msgid that will change, generating a lot
        of false diff changes. It can be removed safely before propagating exception"""
        if "msgid" in err.args[0]:
            del err.args[0]["msgid"]

        # Once disconnected, python-ldap doesn't reconnect automagically,
        # so we mark connection as disconnected to force a reconnection
        self.ldap = None

    def __init_settings(self):
        self.ldap_uri: str = self.config["uri"]
        self.ldap_binddn: str = self.config["binddn"]
        self.ldap_bindpassword: str = self.config["bindpassword"]
        self.ldap_basedn: str = self.config["basedn"]
        self.users_ou: str = self.config["users_ou"]
        self.groups_ou: str = self.config["groups_ou"]

        self.dnAttrUsers: str = self.config["dnAttributes"]["Users"]
        self.dnAttrGroups: str = self.config["dnAttributes"]["Groups"]

        self.groupMemberAttr: str = self.config["groupMemberAttribute"]
        self.propagateUserDNChangeOnGroupMember: bool = self.config[
            "propagateUserDNChangeOnGroupMember"
        ]
        self.groups_objectclass: str | None = self.config.get("groupsObjectclass")

    def __init__(self, config: HermesConfig):
        super().__init__(config)
        self.__init_settings()
        self.connect()

    def ensureIsConnected(func):
        """Decorator restoring LDAP connection if necessary"""

        def decorated(self, *args, **kwargs):
            if self.ldap is None:
                self.connect()
            return func(self, *args, **kwargs)

        return decorated

    def connect(self):
        # Not well documented in python-ldap,
        # Found this in doc/drafts/draft-ietf-ldapext-ldap-c-api-xx.txt
        # in openldap-master:
        #     LDAP_OPT_RESTART (0x09)
        #     Type for invalue parameter: void * (LDAP_OPT_ON or LDAP_OPT_OFF)
        #
        #     Type for outvalue parameter: int *
        #
        #     Description:
        #          Determines whether LDAP I/O operations are automatically res-
        #          tarted if they abort prematurely. It MAY be set to one of the
        #          constants LDAP_OPT_ON or LDAP_OPT_OFF; any non-NULL pointer
        #          value passed to ldap_set_option() enables this option.  When
        #          reading the current setting using ldap_get_option(), a zero
        #          value means OFF and any non-zero value means ON. This option
        #          is useful if an LDAP I/O operation can be interrupted prema-
        #          turely, for example by a timer going off, or other interrupt.
        #          By default, this option is OFF.
        #
        # Will avoid that an handled SIGINT raises an exception
        ldap.set_option(ldap.OPT_RESTART, ldap.OPT_ON)

        if self.config["ssl"]:
            if "cafile" in self.config["ssl"]:
                ldap.set_option(ldap.OPT_X_TLS_CACERTFILE, self.config["ssl"]["cafile"])
            if "certfile" in self.config["ssl"]:
                ldap.set_option(ldap.OPT_X_TLS_CERTFILE, self.config["ssl"]["certfile"])
            if "keyfile" in self.config["ssl"]:
                ldap.set_option(ldap.OPT_X_TLS_KEYFILE, self.config["ssl"]["keyfile"])

            ldap.set_option(ldap.OPT_X_TLS_NEWCTX, 0)

        self.ldap = ldap.initialize(self.ldap_uri, bytes_mode=False)
        try:
            self.ldap.simple_bind_s(who=self.ldap_binddn, cred=self.ldap_bindpassword)
        except LDAPError as e:
            self.__handleLDAPError(e)
            raise

    @staticmethod
    def datetimeToLDAP(dt: datetime) -> str:
        return dt.strftime("%Y%m%d%H%M%SZ")

    def convertObjToLdap(self, obj: DataObject) -> dict[str, Any]:
        res = {}

        attributesToIgnore: set[str] = set(
            self.config["attributesToIgnore"].get(obj.getType(), [])
        )
        defaultvalues: dict[str, Any] = self.config["defaultValues"].get(
            obj.getType(), {}
        )

        # Add raw data, except attributes specified in attributesToIgnore
        res = {k: v for k, v in obj.toNative().items() if k not in attributesToIgnore}

        # Add default values to use when attributes are not set
        for attr, val in defaultvalues.items():
            if attr not in res:
                res[attr] = val

        # Return result after type conversion
        return LdapClient.convertAttrDictTypes(res)

    @staticmethod
    def convertAttrDictTypes(
        attrdict: dict[str, Any],
    ) -> dict[str, Any]:
        newattrdict = attrdict.copy()
        for attr in newattrdict:
            # Convert dattime instances to ldap datetime
            if isinstance(newattrdict[attr], datetime):
                newattrdict[attr] = LdapClient.datetimeToLDAP(newattrdict[attr])
            if type(newattrdict[attr]) is list:
                newval = []
                for listval in newattrdict[attr]:
                    if isinstance(listval, datetime):
                        newval.append(LdapClient.datetimeToLDAP(listval))
                    else:
                        newval.append(listval)
                newattrdict[attr] = newval

            # Convert values to list if necessary
            if type(newattrdict[attr]) is not list:
                newattrdict[attr] = [newattrdict[attr]]

            # Convert values to str if necessary, then to bytes
            newattrdict[attr] = [
                v.encode("utf-8") if type(v) is str else str(v).encode("utf-8")
                for v in newattrdict[attr]
            ]

        return newattrdict

    @ensureIsConnected
    def on_Users_added(
        self, objkey: Any, eventattrs: "dict[str, Any]", newobj: DataObject
    ):
        newobj_ldapdata = self.convertObjToLdap(newobj)
        addlist = ldap.modlist.addModlist(newobj_ldapdata)
        dn = f"{self.dnAttrUsers}={getattr(newobj, self.dnAttrUsers)},{self.users_ou}"
        try:
            self.ldap.add_s(dn, addlist)
        except LDAPError as e:
            self.__handleLDAPError(e)
            raise

    @ensureIsConnected
    def on_Users_modified(
        self,
        objkey: Any,
        eventattrs: "dict[str, Any]",
        newobj: DataObject,
        cachedobj: DataObject,
    ):
        dn = f"{self.dnAttrUsers}={getattr(newobj, self.dnAttrUsers)},{self.users_ou}"
        prevdn = (
            f"{self.dnAttrUsers}={getattr(cachedobj, self.dnAttrUsers)},{self.users_ou}"
        )

        # Check if a rename is required
        if self.currentStep == 0:
            if dn != prevdn:
                try:
                    self.ldap.rename_s(
                        prevdn,
                        f"{self.dnAttrUsers}={getattr(newobj, self.dnAttrUsers)}",
                    )
                except LDAPError as e:
                    self.__handleLDAPError(e)
                    raise

            self.currentStep += 1

        # If a rename was required, update groups member to reflect new dn
        if self.currentStep == 1:
            if dn != prevdn and self.propagateUserDNChangeOnGroupMember:
                try:
                    groupsDNs = self.ldap.search_s(
                        base=self.groups_ou,
                        scope=ldap.SCOPE_SUBTREE,
                        filterstr=(
                            f"(&(objectClass={self.groups_objectclass})"
                            f"({self.groupMemberAttr}={prevdn}))"
                        ),
                        attrlist=[self.groupMemberAttr],
                        attrsonly=1,
                    )
                except LDAPError as e:
                    self.__handleLDAPError(e)
                    raise

                for groupDN, _ in groupsDNs:
                    modlist = [
                        (ldap.MOD_DELETE, self.groupMemberAttr, prevdn.encode()),
                        (ldap.MOD_ADD, self.groupMemberAttr, dn.encode()),
                    ]
                    try:
                        self.ldap.modify_s(groupDN, modlist)
                    except LDAPError as e:
                        self.__handleLDAPError(e)
                        raise

                # Change login in cached instance to reflect renaming
                setattr(cachedobj, self.dnAttrUsers, getattr(newobj, self.dnAttrUsers))

            self.currentStep += 1

        # Modify
        if self.currentStep == 2:
            cachedobj_ldapdata = self.convertObjToLdap(cachedobj)
            newobj_ldapdata = self.convertObjToLdap(newobj)
            modlist = ldap.modlist.modifyModlist(cachedobj_ldapdata, newobj_ldapdata)
            if len(modlist) > 0:
                try:
                    self.ldap.modify_s(dn, modlist)
                except LDAPError as e:
                    self.__handleLDAPError(e)
                    raise
            self.currentStep += 1

    @ensureIsConnected
    def on_Users_removed(
        self, objkey: Any, eventattrs: "dict[str, Any]", cachedobj: DataObject
    ):
        userdn = (
            f"{self.dnAttrUsers}={getattr(cachedobj, self.dnAttrUsers)},{self.users_ou}"
        )
        try:
            self.ldap.delete_s(userdn)
        except LDAPError as e:
            self.__handleLDAPError(e)
            raise

    @ensureIsConnected
    def on_Groups_added(
        self, objkey: Any, eventattrs: "dict[str, Any]", newobj: DataObject
    ):
        newobj_ldapdata = self.convertObjToLdap(newobj)
        addlist = ldap.modlist.addModlist(newobj_ldapdata)
        dn = (
            f"{self.dnAttrGroups}={getattr(newobj, self.dnAttrGroups)},{self.groups_ou}"
        )
        try:
            self.ldap.add_s(dn, addlist)
        except LDAPError as e:
            self.__handleLDAPError(e)
            raise

    @ensureIsConnected
    def on_Groups_modified(
        self,
        objkey: Any,
        eventattrs: "dict[str, Any]",
        newobj: DataObject,
        cachedobj: DataObject,
    ):
        dn = (
            f"{self.dnAttrGroups}={getattr(newobj, self.dnAttrGroups)},{self.groups_ou}"
        )

        # Check if a rename is required
        if self.currentStep == 0:
            if getattr(newobj, self.dnAttrGroups) != getattr(
                cachedobj, self.dnAttrGroups
            ):
                prevdn = (
                    f"{self.dnAttrGroups}"
                    f"={getattr(cachedobj, self.dnAttrGroups)},{self.groups_ou}"
                )
                try:
                    self.ldap.rename_s(
                        prevdn,
                        f"{self.dnAttrGroups}={getattr(newobj, self.dnAttrGroups)}",
                    )
                except LDAPError as e:
                    self.__handleLDAPError(e)
                    raise
                # Change login in cached instance to reflect renaming
                setattr(
                    cachedobj, self.dnAttrGroups, getattr(newobj, self.dnAttrGroups)
                )
            self.currentStep += 1

        # Modify
        if self.currentStep == 1:
            cachedobj_ldapdata = self.convertObjToLdap(cachedobj)
            newobj_ldapdata = self.convertObjToLdap(newobj)
            modlist = ldap.modlist.modifyModlist(cachedobj_ldapdata, newobj_ldapdata)
            if len(modlist) > 0:
                try:
                    self.ldap.modify_s(dn, modlist)
                except LDAPError as e:
                    self.__handleLDAPError(e)
                    raise
            self.currentStep += 1

    @ensureIsConnected
    def on_Groups_removed(
        self, objkey: Any, eventattrs: "dict[str, Any]", cachedobj: DataObject
    ):
        groupdn = (
            f"{self.dnAttrGroups}"
            f"={getattr(cachedobj, self.dnAttrGroups)},{self.groups_ou}"
        )
        try:
            self.ldap.delete_s(groupdn)
        except LDAPError as e:
            self.__handleLDAPError(e)
            raise

    @ensureIsConnected
    def on_GroupsMembers_added(
        self, objkey: Any, eventattrs: "dict[str, Any]", newobj: DataObject
    ):
        cachedgroup = self.getObjectFromCache("Groups", newobj.group_pkey)
        cacheduser = self.getObjectFromCache("Users", newobj.user_pkey)

        userdn = (
            f"{self.dnAttrUsers}"
            f"={getattr(cacheduser, self.dnAttrUsers)},{self.users_ou}"
        )
        groupdn = (
            f"{self.dnAttrGroups}"
            f"={getattr(cachedgroup, self.dnAttrGroups)},{self.groups_ou}"
        )
        modlist = [(ldap.MOD_ADD, self.groupMemberAttr, userdn.encode("utf-8"))]
        try:
            self.ldap.modify_s(groupdn, modlist)
        except LDAPError as e:
            self.__handleLDAPError(e)
            raise

    @ensureIsConnected
    def on_GroupsMembers_removed(
        self, objkey: Any, eventattrs: "dict[str, Any]", cachedobj: DataObject
    ):
        cachedgroup = self.getObjectFromCache("Groups", cachedobj.group_pkey)
        cacheduser = self.getObjectFromCache("Users", cachedobj.user_pkey)

        userdn = (
            f"{self.dnAttrUsers}"
            f"={getattr(cacheduser, self.dnAttrUsers)},{self.users_ou}"
        )
        groupdn = (
            f"{self.dnAttrGroups}"
            f"={getattr(cachedgroup, self.dnAttrGroups)},{self.groups_ou}"
        )
        modlist = [(ldap.MOD_DELETE, self.groupMemberAttr, userdn.encode("utf-8"))]
        try:
            self.ldap.modify_s(groupdn, modlist)
        except LDAPError as e:
            self.__handleLDAPError(e)
            raise

    @ensureIsConnected
    def on_UserPasswords_added(
        self, objkey: Any, eventattrs: "dict[str, Any]", newobj: DataObject
    ):
        user_pkey = newobj.user_pkey
        self.__process_UserPasswords(
            user_pkey,
            newldapobj=self.convertObjToLdap(newobj),
            cachedldapobj={},
        )

    @ensureIsConnected
    def on_UserPasswords_modified(
        self,
        objkey: Any,
        eventattrs: "dict[str, Any]",
        newobj: DataObject,
        cachedobj: DataObject,
    ):
        user_pkey = newobj.user_pkey
        self.__process_UserPasswords(
            user_pkey,
            newldapobj=self.convertObjToLdap(newobj),
            cachedldapobj=self.convertObjToLdap(cachedobj),
        )

    @ensureIsConnected
    def on_UserPasswords_removed(
        self, objkey: Any, eventattrs: "dict[str, Any]", cachedobj: DataObject
    ):
        user_pkey = cachedobj.user_pkey
        self.__process_UserPasswords(
            user_pkey, newldapobj={}, cachedldapobj=self.convertObjToLdap(cachedobj)
        )

    def __process_UserPasswords(
        self, user_pkey: Any, newldapobj: dict[str, Any], cachedldapobj: dict[str, Any]
    ):
        cacheduser = self.getObjectFromCache("Users", user_pkey)
        dn = (
            f"{self.dnAttrUsers}"
            f"={getattr(cacheduser, self.dnAttrUsers)},{self.users_ou}"
        )

        # Modify
        if self.currentStep == 0:
            modlist = ldap.modlist.modifyModlist(cachedldapobj, newldapobj)
            if len(modlist) > 0:
                try:
                    self.ldap.modify_s(dn, modlist)
                except LDAPError as e:
                    self.__handleLDAPError(e)
                    raise
            self.currentStep += 1
