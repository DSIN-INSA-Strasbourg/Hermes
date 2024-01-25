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

import random
import winrm

from typing import Any

HERMES_PLUGIN_CLASSNAME = "WinrmADClient"


class RemoteCommandFailed(Exception):
    pass


class InconsistentActionRequested(Exception):
    pass


class WinrmADClient(GenericClient):
    """Hermes-client class handling users, passwords, groups and groupMembers in
    Active Directory with Powershell scripts run remotely via WinRM"""

    def __init_settings(self):
        ##################
        # WinRM settings #
        ##################
        self.winrm_host = self.config["WinRM"]["host"]
        self.winrm_login = self.config["WinRM"]["login"]
        self.winrm_password = self.config["WinRM"]["password"]
        self.winrm_port = self.config["WinRM"]["port"]
        self.winrm_server_cert_validation = self.config["WinRM"][
            "server_cert_validation"
        ]

        ###################
        # Domain settings #
        ###################
        self.domain = self.config["AD_domain"]["name"]
        self.domaindn = self.config["AD_domain"]["dn"]
        self.users_ou = self.config["AD_domain"]["users_ou"]
        self.groups_ou = self.config["AD_domain"]["groups_ou"]

        #######################
        # Attributes settings #
        #######################
        self.standardAttrs = self.config["standardAttributes"]
        self.otherAttrs = self.config["otherAttributes"]

    def ensureIsConnected(func):
        """Decorator restoring connection if necessary"""

        def decorated(self, *args, **kwargs):
            if not self.win.protocol.transport.session:
                self.__connect()
            return func(self, *args, **kwargs)

        return decorated

    def __init__(self, config: HermesConfig):
        super().__init__(config)
        self.__init_settings()
        self.__connect()

    def __connect(self):
        self.win = winrm.Session(
            f"https://{self.winrm_host}:{self.winrm_port}",
            auth=(self.winrm_login, self.winrm_password),
            transport="credssp",
            server_cert_validation=self.winrm_server_cert_validation,
        )

    @staticmethod
    def escape(arg: str) -> str:
        # Always use single quoted string, easier to escape
        # https://www.rlmueller.net/PowerShellEscape.htm
        return arg.replace("'", "''")

    @staticmethod
    def generateRandomPassword(length: int = 32) -> str:
        lower = "aàäâbcçdeéèêëfghiîïjklmnoôöpqrstuùûüvwxyz"
        upper = "AÀÄÂBCÇDEÉÈÊËFGHIÎÏJKLMNOÔÖPQRSTUÙÛÜVWXYZ"
        numbers = "0123456789"
        specials = "#{}()[]_@°=+-*.,?:!§%$£"
        chars = lower + upper + numbers + specials
        srcs = [lower, upper, numbers, specials, chars]

        pw = ""
        for i in range(0, length):
            # Ensure at least on char of each type is used in returned password
            if i < len(srcs):
                src = srcs[i]
            pw += random.choice(src)
        return pw

    @ensureIsConnected
    def run_ps(self, script: str):
        r = self.win.run_ps("Import-Module ActiveDirectory\n" + script)
        stdout = r.std_out.decode("utf-8")
        stderr = r.std_err.decode("utf-8")
        if r.status_code != 0:
            newline = "\n"
            raise RemoteCommandFailed(
                f"Powershell script failed (retcode={r.status_code}).{newline}{stdout=}{newline}{stderr=}"
            )

    def changePassword(self, userdn: str, password: str):
        """Will change the password of the specified userdn to the specified
        password value"""
        cmd = [
            f"Set-ADAccountPassword",
            f"-Identity '{self.escape(userdn)}'",
            f"-NewPassword (ConvertTo-SecureString '{self.escape(password)}' -AsPlainText -force)",
            f"-Reset",
            f"-Confirm:$False",
        ]
        self.run_ps(" `\n  ".join(cmd))

    def convertAttrToPS(self, attrname: str, value: Any, src: dict[str, str]) -> str:
        if attrname not in src:
            raise KeyError(f"Unknown attribute name '{attrname}'")

        attrType = src[attrname]

        match attrType:
            case "<Boolean[]>":
                if type(value) in [list, tuple, set]:
                    values = value
                elif type(value) == bool:
                    values = [value]
                else:
                    raise TypeError(
                        f"Invalid type for attribute '{attrname}'. Must be a boolean or a list of boolean, but received a {type(value)}"
                    )
                res = []
                for v in values:
                    if type(v) != bool:
                        raise TypeError(
                            f"Invalid type for a value of list attribute '{attrname}'. Must be a boolean, but received a {type(v)}"
                        )
                    if v:
                        res.append("$True")
                    else:
                        res.append("$False")
                return ",".join(res)

            case "<Boolean>":
                if type(value) != bool:
                    raise TypeError(
                        f"Invalid type for attribute '{attrname}'. Must be a boolean, but received a {type(value)}"
                    )
                if value:
                    return "$True"
                else:
                    return "$False"
            case v if v.endswith("[]>"):  # Treat all other list types as <Strings[]>
                if type(value) in [list, tuple, set]:
                    values = value
                else:
                    values = [value]
                res = []
                for v in values:
                    res.append(f"'{self.escape(str(v))}'")
                return ",".join(res)

            case _:  # Treat all other types as strings
                if type(value) in [list, tuple, set, dict]:
                    raise TypeError(
                        f"Invalid type for attribute '{attrname}'. Must be a string, but received a {type(value)}"
                    )
                return f"'{self.escape(str(value))}'"

    def on_Users_added(
        self, objkey: Any, eventattrs: "dict[str, Any]", newobj: DataObject
    ):
        std_attrs = eventattrs.keys() & self.standardAttrs["Users"].keys()
        other_attrs = eventattrs.keys() & self.otherAttrs["Users"].keys()
        cmd = [
            f"New-ADUser",
            f"-Path '{self.users_ou}'",
            f"-Name '{self.escape(newobj.SamAccountName)}'",
            f"-AccountPassword (ConvertTo-SecureString '{self.escape(self.generateRandomPassword())}' -AsPlainText -force)",
            f"-Confirm:$False",
        ]
        cmd += [
            f"-{k} {self.convertAttrToPS(k, eventattrs[k], self.standardAttrs['Users'])}"
            for k in std_attrs
        ]

        if other_attrs:
            other_attrs_str = "; ".join(
                [
                    f"'{k}'={self.convertAttrToPS(k, eventattrs[k], self.otherAttrs['Users'])}"
                    for k in other_attrs
                ]
            )
            cmd.append(f"""-OtherAttributes @{{ {other_attrs_str} }}""")

        self.run_ps(" `\n  ".join(cmd))

    def on_Users_recycled(
        self, objkey: Any, eventattrs: "dict[str, Any]", newobj: DataObject
    ):
        cmd = [
            f"Enable-ADAccount",
            f"-Identity 'CN={self.escape(newobj.SamAccountName)},{self.users_ou}'",
            f"-Confirm:$False",
        ]
        self.run_ps(" `\n  ".join(cmd))

    def on_Users_modified(
        self,
        objkey: Any,
        eventattrs: "dict[str, Any]",
        newobj: DataObject,
        cachedobj: DataObject,
    ):
        # Example:
        # eventattrs={
        #     'added': {},
        #     'modified': {
        #         'cn': 'John Doe',
        #         'displayname': 'John Doe',
        #         'givenname': 'John',
        #         'memberof': ['group1', 'group2'],
        #     },
        #     'removed': {}
        # }

        if "SamAccountName" in eventattrs["added"]:
            raise InconsistentActionRequested(
                f"Cannot add login to an existing AD account ! {cachedobj.SamAccountName=}"
            )
        if "SamAccountName" in eventattrs["removed"]:
            raise InconsistentActionRequested(
                f"Cannot remove login from an AD account ! {cachedobj.SamAccountName=}"
            )

        if self.currentStep == 0:
            if "SamAccountName" in eventattrs["modified"]:
                cmd = [
                    f"Rename-ADObject",
                    f"-Identity 'CN={self.escape(cachedobj.SamAccountName)},{self.users_ou}'",
                    f"-NewName '{self.escape(newobj.SamAccountName)}'",
                    f"-Confirm:$False",
                ]
                self.run_ps(" `\n  ".join(cmd))
            self.currentStep += 1

        if self.currentStep == 1:
            cmd = [
                f"Set-ADUser",
                f"-Identity 'CN={self.escape(newobj.SamAccountName)},{self.users_ou}'",
                f"-Confirm:$False",
            ]

            # added/modified attributes
            std_attrs = (
                eventattrs["added"].keys() | eventattrs["modified"].keys()
            ) & self.standardAttrs["Users"].keys()
            cmd += [
                f"-{k} {self.convertAttrToPS(k, getattr(newobj, k), self.standardAttrs['Users'])}"
                for k in std_attrs
            ]

            other_attrs = (
                eventattrs["added"].keys() | eventattrs["modified"].keys()
            ) & self.otherAttrs["Users"].keys()
            if other_attrs:
                other_attrs_str = "; ".join(
                    [
                        f"'{k}'={self.convertAttrToPS(k, getattr(newobj, k), self.otherAttrs['Users'])}"
                        for k in other_attrs
                    ]
                )
                cmd.append(f"""-Replace @{{ {other_attrs_str} }}""")

            # removed attributes
            std_attrs = (
                eventattrs["removed"].keys() & self.standardAttrs["Users"].keys()
            )
            cmd += [f"-{k} $Null" for k in std_attrs]

            other_attrs = eventattrs["removed"].keys() & self.otherAttrs["Users"].keys()
            if other_attrs:
                cmd.append(f"""-Clear {','.join(other_attrs)}""")

            self.run_ps(" `\n  ".join(cmd))
            self.currentStep += 1

    def on_Users_trashed(
        self, objkey: Any, eventattrs: "dict[str, Any]", cachedobj: DataObject
    ):
        cmd = [
            f"Disable-ADAccount",
            f"-Identity 'CN={self.escape(cachedobj.SamAccountName)},{self.users_ou}'",
            f"-Confirm:$False",
        ]
        self.run_ps(" `\n  ".join(cmd))

    def on_Users_removed(
        self, objkey: Any, eventattrs: "dict[str, Any]", cachedobj: DataObject
    ):
        cmd = [
            f"Remove-ADUser",
            f"-Identity 'CN={self.escape(cachedobj.SamAccountName)},{self.users_ou}'",
            f"-Confirm:$False",
        ]
        self.run_ps(" `\n  ".join(cmd))

    def on_Groups_added(
        self, objkey: Any, eventattrs: "dict[str, Any]", newobj: DataObject
    ):
        std_attrs = eventattrs.keys() & self.standardAttrs["Groups"].keys()
        other_attrs = eventattrs.keys() & self.otherAttrs["Groups"].keys()

        cmd = [
            f"New-ADGroup",
            f"-Path '{self.groups_ou}'",
            f"-Name '{self.escape(newobj.SamAccountName)}'",
            f"-Confirm:$False",
        ]
        cmd += [
            f"-{k} {self.convertAttrToPS(k, eventattrs[k], self.standardAttrs['Groups'])}"
            for k in std_attrs
        ]

        if other_attrs:
            other_attrs_str = "; ".join(
                [
                    f"'{k}'={self.convertAttrToPS(k, eventattrs[k], self.otherAttrs['Groups'])}"
                    for k in other_attrs
                ]
            )
            cmd.append(f"""-OtherAttributes @{{ {other_attrs_str} }}""")

        self.run_ps(" `\n  ".join(cmd))

    def on_Groups_modified(
        self,
        objkey: Any,
        eventattrs: "dict[str, Any]",
        newobj: DataObject,
        cachedobj: DataObject,
    ):
        # Example:
        # eventattrs={
        #     'added': {},
        #     'modified': {
        #         'name': 'groupName',
        #         'description': 'Group description',
        #     },
        #     'removed': {}
        # }

        if "SamAccountName" in eventattrs["added"]:
            raise InconsistentActionRequested(
                f"Cannot add name to an existing AD group ! {cachedobj.SamAccountName=}"
            )
        if "SamAccountName" in eventattrs["removed"]:
            raise InconsistentActionRequested(
                f"Cannot remove name from an AD group ! {cachedobj.SamAccountName=}"
            )

        if self.currentStep == 0:
            if "SamAccountName" in eventattrs["modified"]:
                cmd = [
                    f"Rename-ADObject",
                    f"-Identity 'CN={self.escape(cachedobj.SamAccountName)},{self.groups_ou}'",
                    f"-NewName '{self.escape(newobj.SamAccountName)}'",
                    f"-Confirm:$False",
                ]
                self.run_ps(" `\n  ".join(cmd))
            self.currentStep += 1

        if self.currentStep == 1:
            cmd = [
                f"Set-ADGroup",
                f"-Identity 'CN={self.escape(newobj.SamAccountName)},{self.groups_ou}'",
                f"-Confirm:$False",
            ]

            # added/modified attributes
            std_attrs = (
                eventattrs["added"].keys() | eventattrs["modified"].keys()
            ) & self.standardAttrs["Groups"].keys()
            cmd += [
                f"-{k} {self.convertAttrToPS(k, getattr(newobj, k), self.standardAttrs['Groups'])}"
                for k in std_attrs
            ]

            other_attrs = (
                eventattrs["added"].keys() | eventattrs["modified"].keys()
            ) & self.otherAttrs["Groups"].keys()
            if other_attrs:
                other_attrs_str = "; ".join(
                    [
                        f"'{k}'={self.convertAttrToPS(k, getattr(newobj, k), self.otherAttrs['Groups'])}"
                        for k in other_attrs
                    ]
                )
                cmd.append(f"""-Replace @{{ {other_attrs_str} }}""")

            # removed attributes
            std_attrs = (
                eventattrs["removed"].keys() & self.standardAttrs["Groups"].keys()
            )
            cmd += [f"-{k} $Null" for k in std_attrs]

            other_attrs = (
                eventattrs["removed"].keys() & self.otherAttrs["Groups"].keys()
            )
            if other_attrs:
                cmd.append(f"""-Clear {','.join(other_attrs)}""")

            self.run_ps(" `\n  ".join(cmd))
            self.currentStep += 1

    def on_Groups_removed(
        self, objkey: Any, eventattrs: "dict[str, Any]", cachedobj: DataObject
    ):
        cmd = [
            f"Remove-ADGroup",
            f"-Identity 'CN={self.escape(cachedobj.SamAccountName)},{self.groups_ou}'",
            f"-Confirm:$False",
        ]
        self.run_ps(" `\n  ".join(cmd))

    def on_GroupsMembers_added(
        self, objkey: Any, eventattrs: "dict[str, Any]", newobj: DataObject
    ):
        cachedgroup = self.getObjectFromCache("Groups", newobj.group_pkey)
        cacheduser = self.getObjectFromCache("Users", newobj.user_pkey)

        cmd = [
            f"Add-ADGroupMember",
            f"-Identity 'CN={self.escape(cachedgroup.SamAccountName)},{self.groups_ou}'",
            f"-Members 'CN={self.escape(cacheduser.SamAccountName)},{self.users_ou}'",
            f"-DisablePermissiveModify:$False",
            f"-Confirm:$False",
        ]
        self.run_ps(" `\n  ".join(cmd))

    def on_GroupsMembers_recycled(
        self, objkey: Any, eventattrs: "dict[str, Any]", newobj: DataObject
    ):
        # Won't generate an error if called several times
        self.on_GroupsMembers_added(objkey, eventattrs, newobj)

    def on_GroupsMembers_trashed(
        self, objkey: Any, eventattrs: "dict[str, Any]", cachedobj: DataObject
    ):
        # Won't generate an error if called several times
        self.on_GroupsMembers_removed(objkey, eventattrs, cachedobj)

    def on_GroupsMembers_removed(
        self, objkey: Any, eventattrs: "dict[str, Any]", cachedobj: DataObject
    ):
        cachedgroup = self.getObjectFromCache("Groups", cachedobj.group_pkey)
        cacheduser = self.getObjectFromCache("Users", cachedobj.user_pkey)

        cmd = [
            f"Remove-ADGroupMember",
            f"-Identity 'CN={cachedgroup.SamAccountName},{self.groups_ou}'",
            f"-Members 'CN={cacheduser.SamAccountName},{self.users_ou}'",
            f"-DisablePermissiveModify:$False",
            f"-Confirm:$False",
        ]
        self.run_ps(" `\n  ".join(cmd))

    def on_UserPasswords_added(
        self,
        objkey: Any,
        eventattrs: "dict[str, Any]",
        newobj: DataObject,
    ):
        if hasattr(newobj, "password"):
            cacheduser = self.getObjectFromCache("Users", newobj.user_pkey)
            self.changePassword(
                userdn=f"CN={cacheduser.SamAccountName},{self.users_ou}",
                password=newobj.password,
            )

    def on_UserPasswords_modified(
        self,
        objkey: Any,
        eventattrs: "dict[str, Any]",
        newobj: DataObject,
        cachedobj: DataObject,
    ):
        if hasattr(newobj, "password"):
            cacheduser = self.getObjectFromCache("Users", newobj.user_pkey)
            self.changePassword(
                userdn=f"CN={self.escape(cacheduser.SamAccountName)},{self.users_ou}",
                password=newobj.password,
            )

    def on_UserPasswords_removed(
        self, objkey: Any, eventattrs: "dict[str, Any]", cachedobj: DataObject
    ):
        cacheduser = self.getObjectFromCache("Users", cachedobj.user_pkey)
        self.changePassword(
            userdn=f"CN={self.escape(cacheduser.SamAccountName)},{self.users_ou}",
            password=self.escape(self.generateRandomPassword()),
        )
