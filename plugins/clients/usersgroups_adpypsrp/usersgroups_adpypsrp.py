#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Hermes : Change Data Capture (CDC) tool from any source(s) to any target
# Copyright (C) 2023, 2024, 2025 INSA Strasbourg
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
from helpers.randompassword import RandomPassword
from lib.config import HermesConfig
from lib.datamodel.dataobject import DataObject

from pypsrp.complex_objects import ObjectMeta
from pypsrp.powershell import PowerShell, RunspacePool
from pypsrp.wsman import WSMan

from typing import Any

HERMES_PLUGIN_CLASSNAME = "PypsrpADClient"


class RemoteCommandFailed(Exception):
    pass


class InconsistentActionRequested(Exception):
    pass


class PypsrpADClient(GenericClient):
    """Hermes-client class handling users, passwords, groups and groupMembers in
    Active Directory with Powershell scripts run remotely via Pypsrp"""

    def __init_settings(self):
        ##################
        # WinRM settings #
        ##################
        self.winrm_host = self.config["WinRM"]["host"]
        self.winrm_port = self.config["WinRM"]["port"]
        self.winrm_login = self.config["WinRM"]["login"]
        self.winrm_password = self.config["WinRM"]["password"]
        self.winrm_ssl = self.config["WinRM"]["ssl"]
        self.winrm_ssl_cert_validation = self.config["WinRM"]["ssl_cert_validation"]
        self.winrm_credssp_disable_tlsv1_2 = self.config["WinRM"][
            "credssp_disable_tlsv1_2"
        ]
        self.winrm_encryption = self.config["WinRM"]["encryption"]
        self.winrm_path = self.config["WinRM"]["path"]
        self.winrm_auth = self.config["WinRM"]["auth"]
        self.winrm_negotiate_service = self.config["WinRM"]["negotiate_service"]

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
            self.__connect()
            return func(self, *args, **kwargs)

        return decorated

    def __init__(self, config: HermesConfig):
        super().__init__(config)
        self.__init_settings()
        self.pool: RunspacePool | None = None
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

        if len(self.config["Users_mandatory_groups"]) == 0:
            self.users_mandatory_groups: str | None = None
            """ String containing escaped and quoted group from Users_mandatory_groups
                config, or None if empty"""
        else:
            self.users_mandatory_groups = ", ".join(
                [
                    f"'{self.escape(grp)}'"
                    for grp in self.config["Users_mandatory_groups"]
                ]
            )

    def __connect(self):
        if self.pool is not None:
            if self.pool.state == 2:  # Connection is up
                return
            self.__disconnect()

        self.wsman = WSMan(
            server=self.winrm_host,
            port=self.winrm_port,
            username=self.winrm_login,
            password=self.winrm_password,
            ssl=self.winrm_ssl,
            cert_validation=self.winrm_ssl_cert_validation,
            credssp_disable_tlsv1_2=self.winrm_credssp_disable_tlsv1_2,
            encryption=self.winrm_encryption,
            path=self.winrm_path,
            auth=self.winrm_auth,
            negotiate_service=self.winrm_negotiate_service,
        )

        self.pool = RunspacePool(self.wsman)
        self.pool.open()
        self.run_ps("Import-Module ActiveDirectory")

    def __disconnect(self):
        if self.pool is None:
            return  # Not connected

        try:
            self.pool.close()
        except Exception:
            pass
        del self.pool
        self.pool = None

    @staticmethod
    def escape(arg: str) -> str:
        # Always use single quoted string, easier to escape
        # https://www.rlmueller.net/PowerShellEscape.htm
        return arg.replace("'", "''")

    @ensureIsConnected
    def run_ps(self, script: str):
        ps = PowerShell(self.pool)
        ps.add_script(script)
        ps.invoke()

        if ps.had_errors:
            NL = "\n"
            stderr = "  \n".join([str(i) for i in ps.streams.error])
            raise RemoteCommandFailed(f"Powershell script failed.{NL}  {stderr=}")

    @ensureIsConnected
    def changePasswordSecure(self, userdn: str, password: str):
        """Will change the password of the specified userdn to the specified
        password value. This function send the password threw a locally generated
        powershell secure string to avoid password leak in logs or on the wire"""

        self.pool.exchange_keys()
        secure_string = self.pool.serialize(password, ObjectMeta("SS"))
        ps = PowerShell(self.pool)
        ps.add_cmdlet("Set-ADAccountPassword").add_parameters(
            {
                "Identity": userdn,
                "NewPassword": secure_string,
                "Reset": None,
                "Confirm": False,
            }
        )

        ps.invoke()
        if ps.had_errors:
            NL = "\n"
            stderr = "  \n".join([str(i) for i in ps.streams.error])
            raise RemoteCommandFailed(f"Powershell script failed.{NL}  {stderr=}")

    def changePassword(self, userdn: str, password: str):
        """Will change the password of the specified userdn to the specified
        password value"""
        cmd = [
            "Set-ADAccountPassword",
            f"-Identity '{self.escape(userdn)}'",
            f"-NewPassword (ConvertTo-SecureString '{self.escape(password)}'"
            " -AsPlainText -force)",
            "-Reset",
            "-Confirm:$False",
        ]
        self.run_ps(" `\n  ".join(cmd))

    def convertAttrToPS(self, attrname: str, value: Any, src: dict[str, str]) -> str:
        if attrname not in src:
            raise KeyError(f"Unknown attribute name '{attrname}'")

        attrType = src[attrname]

        match attrType:
            case "<Boolean[]>":
                if isinstance(value, (list, tuple, set)):
                    values = value
                elif type(value) is bool:
                    values = [value]
                else:
                    raise TypeError(
                        f"Invalid type for attribute '{attrname}'. Must be a boolean or"
                        f" a list of boolean, but received a {type(value)}"
                    )
                res = []
                for v in values:
                    if type(v) is not bool:
                        raise TypeError(
                            f"Invalid type for a value of list attribute '{attrname}'."
                            f" Must be a boolean, but received a {type(v)}"
                        )
                    if v:
                        res.append("$True")
                    else:
                        res.append("$False")
                return ",".join(res)

            case "<Boolean>":
                if type(value) is not bool:
                    raise TypeError(
                        f"Invalid type for attribute '{attrname}'. Must be a boolean,"
                        f" but received a {type(value)}"
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
                        f"Invalid type for attribute '{attrname}'. Must be a string,"
                        f" but received a {type(value)}"
                    )
                return f"'{self.escape(str(value))}'"

    def on_Users_added(
        self, objkey: Any, eventattrs: "dict[str, Any]", newobj: DataObject
    ):
        if self.currentStep == 0:
            std_attrs = eventattrs.keys() & self.standardAttrs["Users"].keys()
            other_attrs = eventattrs.keys() & self.otherAttrs["Users"].keys()
            cmd = [
                "New-ADUser",
                f"-Path '{self.users_ou}'",
                f"-Name '{self.escape(newobj.SamAccountName)}'",
                (
                    f"-AccountPassword (ConvertTo-SecureString"
                    f" '{self.escape(self._randomPassword.generate())}'"
                    " -AsPlainText -force)"
                ),
                "-Confirm:$False",
            ]
            cmd += [
                f"-{k} {
                    self.convertAttrToPS(k, eventattrs[k], self.standardAttrs['Users'])
                }"
                for k in std_attrs
            ]

            if other_attrs:
                other_attrs_str = "; ".join(
                    [
                        f"'{k}'={
                            self.convertAttrToPS(
                                k,
                                eventattrs[k],
                                self.otherAttrs['Users']
                            )
                        }"
                        for k in other_attrs
                    ]
                )
                cmd.append(f"""-OtherAttributes @{{ {other_attrs_str} }}""")

            self.run_ps(" `\n  ".join(cmd))
            self.isPartiallyProcessed = True
            self.currentStep += 1

        if self.currentStep == 1:
            if self.users_mandatory_groups is not None:
                cmd = [
                    "Add-ADPrincipalGroupMembership",
                    f"-Identity '{self.escape(newobj.SamAccountName)}'",
                    f"-MemberOf {self.users_mandatory_groups}",
                    "-Confirm:$False",
                ]
                self.run_ps(" `\n  ".join(cmd))
                self.isPartiallyProcessed = True
            self.currentStep += 1

    def on_Users_recycled(
        self, objkey: Any, eventattrs: "dict[str, Any]", newobj: DataObject
    ):
        cmd = [
            "Enable-ADAccount",
            f"-Identity 'CN={self.escape(newobj.SamAccountName)},{self.users_ou}'",
            "-Confirm:$False",
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
                "Cannot add login to an existing AD account !"
                f" {cachedobj.SamAccountName=}"
            )
        if "SamAccountName" in eventattrs["removed"]:
            raise InconsistentActionRequested(
                f"Cannot remove login from an AD account ! {cachedobj.SamAccountName=}"
            )

        if self.currentStep == 0:
            if "SamAccountName" in eventattrs["modified"]:
                cmd = [
                    "Rename-ADObject",
                    (
                        f"-Identity "
                        f"'CN={self.escape(cachedobj.SamAccountName)},{self.users_ou}'"
                    ),
                    f"-NewName '{self.escape(newobj.SamAccountName)}'",
                    "-Confirm:$False",
                ]
                self.run_ps(" `\n  ".join(cmd))
                self.isPartiallyProcessed = True
            self.currentStep += 1

        if self.currentStep == 1:
            cmd = [
                "Set-ADUser",
                f"-Identity 'CN={self.escape(newobj.SamAccountName)},{self.users_ou}'",
                "-Confirm:$False",
            ]

            # added/modified attributes
            std_attrs = (
                eventattrs["added"].keys() | eventattrs["modified"].keys()
            ) & self.standardAttrs["Users"].keys()
            cmd += [
                f"-{k} {
                    self.convertAttrToPS(
                        k,
                        getattr(newobj, k),
                        self.standardAttrs['Users']
                    )
                }"
                for k in std_attrs
            ]

            other_attrs = (
                eventattrs["added"].keys() | eventattrs["modified"].keys()
            ) & self.otherAttrs["Users"].keys()
            if other_attrs:
                other_attrs_str = "; ".join(
                    [
                        f"'{k}'={
                            self.convertAttrToPS(
                                k,
                                getattr(newobj, k),
                                self.otherAttrs['Users']
                            )
                        }"
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
            self.isPartiallyProcessed = True
            self.currentStep += 1

    def on_Users_trashed(
        self, objkey: Any, eventattrs: "dict[str, Any]", cachedobj: DataObject
    ):
        cmd = [
            "Disable-ADAccount",
            f"-Identity 'CN={self.escape(cachedobj.SamAccountName)},{self.users_ou}'",
            "-Confirm:$False",
        ]
        self.run_ps(" `\n  ".join(cmd))

    def on_Users_removed(
        self, objkey: Any, eventattrs: "dict[str, Any]", cachedobj: DataObject
    ):
        cmd = [
            "Remove-ADUser",
            f"-Identity 'CN={self.escape(cachedobj.SamAccountName)},{self.users_ou}'",
            "-Confirm:$False",
        ]
        self.run_ps(" `\n  ".join(cmd))

    def on_Groups_added(
        self, objkey: Any, eventattrs: "dict[str, Any]", newobj: DataObject
    ):
        std_attrs = eventattrs.keys() & self.standardAttrs["Groups"].keys()
        other_attrs = eventattrs.keys() & self.otherAttrs["Groups"].keys()

        cmd = [
            "New-ADGroup",
            f"-Path '{self.groups_ou}'",
            f"-Name '{self.escape(newobj.SamAccountName)}'",
            "-Confirm:$False",
        ]
        cmd += [
            f"-{k} {
                self.convertAttrToPS(k, eventattrs[k], self.standardAttrs['Groups'])
            }"
            for k in std_attrs
        ]

        if other_attrs:
            other_attrs_str = "; ".join(
                [
                    f"'{k}'={
                        self.convertAttrToPS(
                            k,
                            eventattrs[k],
                            self.otherAttrs['Groups']
                        )
                    }"
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
                    "Rename-ADObject",
                    "-Identity"
                    f" 'CN={self.escape(cachedobj.SamAccountName)},{self.groups_ou}'",
                    f"-NewName '{self.escape(newobj.SamAccountName)}'",
                    "-Confirm:$False",
                ]
                self.run_ps(" `\n  ".join(cmd))
                self.isPartiallyProcessed = True
            self.currentStep += 1

        if self.currentStep == 1:
            cmd = [
                "Set-ADGroup",
                f"-Identity 'CN={self.escape(newobj.SamAccountName)},{self.groups_ou}'",
                "-Confirm:$False",
            ]

            # added/modified attributes
            std_attrs = (
                eventattrs["added"].keys() | eventattrs["modified"].keys()
            ) & self.standardAttrs["Groups"].keys()
            cmd += [
                f"-{k} {
                    self.convertAttrToPS(
                        k,
                        getattr(newobj, k),
                        self.standardAttrs['Groups']
                    )
                }"
                for k in std_attrs
            ]

            other_attrs = (
                eventattrs["added"].keys() | eventattrs["modified"].keys()
            ) & self.otherAttrs["Groups"].keys()
            if other_attrs:
                other_attrs_str = "; ".join(
                    [
                        f"'{k}'={
                            self.convertAttrToPS(
                                k,
                                getattr(newobj, k),
                                self.otherAttrs['Groups']
                            )
                        }"
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
            self.isPartiallyProcessed = True
            self.currentStep += 1

    def on_Groups_removed(
        self, objkey: Any, eventattrs: "dict[str, Any]", cachedobj: DataObject
    ):
        cmd = [
            "Remove-ADGroup",
            f"-Identity 'CN={self.escape(cachedobj.SamAccountName)},{self.groups_ou}'",
            "-Confirm:$False",
        ]
        self.run_ps(" `\n  ".join(cmd))

    def on_GroupsMembers_added(
        self, objkey: Any, eventattrs: "dict[str, Any]", newobj: DataObject
    ):
        cachedgroup = self.getObjectFromCache("Groups", newobj.group_pkey)
        cacheduser = self.getObjectFromCache("Users", newobj.user_pkey)

        cmd = [
            "Add-ADGroupMember",
            "-Identity",
            f"'CN={self.escape(cachedgroup.SamAccountName)},{self.groups_ou}'",
            f"-Members 'CN={self.escape(cacheduser.SamAccountName)},{self.users_ou}'",
            "-DisablePermissiveModify:$False",
            "-Confirm:$False",
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
            "Remove-ADGroupMember",
            f"-Identity 'CN={cachedgroup.SamAccountName},{self.groups_ou}'",
            f"-Members 'CN={cacheduser.SamAccountName},{self.users_ou}'",
            "-DisablePermissiveModify:$False",
            "-Confirm:$False",
        ]
        self.run_ps(" `\n  ".join(cmd))

    def on_SubGroupsMembers_added(
        self, objkey: Any, eventattrs: "dict[str, Any]", newobj: DataObject
    ):
        cachedgroup = self.getObjectFromCache("Groups", newobj.group_pkey)
        cachedsubgr = self.getObjectFromCache("Groups", newobj.subgroup_pkey)

        cmd = [
            "Add-ADGroupMember",
            "-Identity",
            f"'CN={self.escape(cachedgroup.SamAccountName)},{self.groups_ou}'",
            f"-Members 'CN={self.escape(cachedsubgr.SamAccountName)},{self.groups_ou}'",
            "-DisablePermissiveModify:$False",
            "-Confirm:$False",
        ]
        self.run_ps(" `\n  ".join(cmd))

    def on_SubGroupsMembers_recycled(
        self, objkey: Any, eventattrs: "dict[str, Any]", newobj: DataObject
    ):
        # Won't generate an error if called several times
        self.on_SubGroupsMembers_added(objkey, eventattrs, newobj)

    def on_SubGroupsMembers_trashed(
        self, objkey: Any, eventattrs: "dict[str, Any]", cachedobj: DataObject
    ):
        # Won't generate an error if called several times
        self.on_SubGroupsMembers_removed(objkey, eventattrs, cachedobj)

    def on_SubGroupsMembers_removed(
        self, objkey: Any, eventattrs: "dict[str, Any]", cachedobj: DataObject
    ):
        cachedgroup = self.getObjectFromCache("Groups", cachedobj.group_pkey)
        cachedsubgr = self.getObjectFromCache("Groups", cachedobj.subgroup_pkey)

        cmd = [
            "Remove-ADGroupMember",
            f"-Identity 'CN={cachedgroup.SamAccountName},{self.groups_ou}'",
            f"-Members 'CN={cachedsubgr.SamAccountName},{self.groups_ou}'",
            "-DisablePermissiveModify:$False",
            "-Confirm:$False",
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
            self.changePasswordSecure(
                userdn=f"CN={self.escape(cacheduser.SamAccountName)},{self.users_ou}",
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
            self.changePasswordSecure(
                userdn=f"CN={self.escape(cacheduser.SamAccountName)},{self.users_ou}",
                password=newobj.password,
            )

    def on_UserPasswords_removed(
        self, objkey: Any, eventattrs: "dict[str, Any]", cachedobj: DataObject
    ):
        cacheduser = self.getObjectFromCache("Users", cachedobj.user_pkey)
        self.changePasswordSecure(
            userdn=f"CN={self.escape(cacheduser.SamAccountName)},{self.users_ou}",
            password=self.escape(self._randomPassword.generate()),
        )

    def on_save(self):
        # As an idle pypsrp session may quickly become invalid, close it on processing
        # end to avoid errors
        self.__disconnect()
