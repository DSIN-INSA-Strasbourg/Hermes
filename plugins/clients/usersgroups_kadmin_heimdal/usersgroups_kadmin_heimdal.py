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
from helpers.command import Command, CommandFailed
from helpers.randompassword import RandomPassword
from lib.config import HermesConfig
from lib.datamodel.dataobject import DataObject

from typing import Any

HERMES_PLUGIN_CLASSNAME = "KadminHeimdalClient"


class KadminAuthFailed(Exception):
    pass


class KadminUserAlreadyExists(Exception):
    pass


class KadminUserDoesntExists(Exception):
    pass


class InconsistentActionRequired(Exception):
    pass


class KadminHeimdalClient(GenericClient):
    """Hermes-client class handling users and password in Heimdal Kerberos via local
    kadmin.heimdal command"""

    def __init__(self, config: HermesConfig):
        super().__init__(config)
        self.kadmin = Kadmin(self.config)
        self.__dont_fail_on_existing_user: bool = self.config[
            "dont_fail_on_existing_user"
        ]
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
        # Don't fail if principal already exist when dont_fail_on_existing_user is set
        if self.__dont_fail_on_existing_user and self.kadmin.userExists(newobj.login):
            return
        self.kadmin.addUser(newobj.login, self._randomPassword.generate())

    def on_Users_modified(
        self,
        objkey: Any,
        eventattrs: "dict[str, Any]",
        newobj: DataObject,
        cachedobj: DataObject,
    ):
        for action, attrs in eventattrs.items():
            if "login" in attrs:
                if action == "removed":
                    raise InconsistentActionRequired(
                        f"Cannot remove login from an account ! {cachedobj.login=}"
                    )
                else:
                    self.kadmin.renameUser(cachedobj.login, attrs["login"])

    def on_Users_removed(
        self, objkey: Any, eventattrs: "dict[str, Any]", cachedobj: DataObject
    ):
        self.kadmin.deleteUser(cachedobj.login)

    def on_UserPasswords_added(
        self,
        objkey: Any,
        eventattrs: "dict[str, Any]",
        newobj: DataObject,
    ):
        if hasattr(newobj, "password"):
            cacheduser = self.getObjectFromCache("Users", objkey)
            self.kadmin.changePassword(cacheduser.login, newobj.password)

    def on_UserPasswords_modified(
        self,
        objkey: Any,
        eventattrs: "dict[str, Any]",
        newobj: DataObject,
        cachedobj: DataObject,
    ):
        if hasattr(newobj, "password"):
            cacheduser = self.getObjectFromCache("Users", objkey)
            self.kadmin.changePassword(cacheduser.login, newobj.password)

    def on_UserPasswords_removed(
        self, objkey: Any, eventattrs: "dict[str, Any]", cachedobj: DataObject
    ):
        password = self._randomPassword.generate()
        cacheduser = self.getObjectFromCache("Users", objkey)
        self.kadmin.changePassword(cacheduser.login, password)

    def on_save(self):
        self.kadmin.kdestroy()


class Kadmin:
    """Heimdal Kerberos kadmin helper class"""

    def __init__(self, config: dict[str, Any]) -> None:
        self.__login: str = config["kadmin_login"]
        self.__password: str = config["kadmin_password"]
        self.__realm: str = config["kadmin_realm"]
        self.__spn: str = config["kinit_spn"]
        self.__kinitcmd: str = config["kinit_cmd"]
        self.__kadmincmd: str = config["kadmin_cmd"]
        self.__kdestroycmd: str = config["kdestroy_cmd"]
        self.__kadmin_add_additionalopts: list[str] = config[
            "kadmin_user_add_additional_options"
        ]
        self.__isAuthenticated: bool = False

    def kinit(self):
        if self.__isAuthenticated:
            return
        cmd = [
            self.__kinitcmd,
            "--password-file=STDIN",
            "-S",
            f"{self.__spn}@{self.__realm}",
            self.__login,
        ]
        try:
            Command.run(
                cmd,
                stdin=Command.FROMVAR,
                stdincontent=self.__password + "\n",
                failOnStderr=True,
            )
        except CommandFailed as err:
            raise KadminAuthFailed(err.stderr)
        self.__isAuthenticated = True

    def kdestroy(self):
        if not self.__isAuthenticated:
            return

        cmd = [
            self.__kdestroycmd,
        ]
        try:
            Command.run(
                cmd,
                stdin=Command.FROMVAR,
                stdincontent=self.__password + "\n",
                failOnStderr=True,
            )
        except CommandFailed as err:
            raise KadminAuthFailed(err.stderr)
        self.__isAuthenticated = False

    def userExists(self, login: str) -> bool:
        self.kinit()
        cmd = [
            self.__kadmincmd,
            "-p",
            self.__login,
            "get",
            login,
        ]
        try:
            Command.run(cmd, failOnStderr=True)
        except CommandFailed as err:
            if "Principal does not exist" not in err.stderr:
                raise
            return False
        return True

    def addUser(self, login: str, password: str):
        if self.userExists(login):
            raise KadminUserAlreadyExists(f"User {login} already exists")

        cmd = [
            self.__kadmincmd,
            "-p",
            self.__login,
            "add",
            f"--password={password}",
        ]
        cmd.extend(self.__kadmin_add_additionalopts)
        cmd.append(f"{login}@{self.__realm}")
        try:
            Command.run(cmd, failOnStderr=True)
        except CommandFailed as err:
            cmd[4] = "--password=<SECRET_VALUE>"
            raise CommandFailed(cmd, err.retcode, err.stdout, err.stderr) from None

    def renameUser(self, oldlogin: str, newlogin: str):
        if not self.userExists(oldlogin):
            raise KadminUserDoesntExists(f"User {oldlogin} doesn't exists")
        if self.userExists(newlogin):
            raise KadminUserAlreadyExists(f"User {newlogin} already exists")

        cmd = [
            self.__kadmincmd,
            "-p",
            self.__login,
            "rename",
            f"{oldlogin}@{self.__realm}",
            f"{newlogin}@{self.__realm}",
        ]
        Command.run(cmd, failOnStderr=True)

    def changePassword(self, login: str, password: str):
        if not self.userExists(login):
            raise KadminUserDoesntExists(f"User {login} doesn't exists")

        cmd = [
            self.__kadmincmd,
            "-p",
            self.__login,
            "passwd",
            f"--password={password}",
            f"{login}@{self.__realm}",
        ]
        try:
            Command.run(cmd, failOnStderr=True)
        except CommandFailed as err:
            cmd[4] = "--password=<SECRET_VALUE>"
            raise CommandFailed(cmd, err.retcode, err.stdout, err.stderr) from None

    def deleteUser(self, login: str):
        if not self.userExists(login):
            raise KadminUserDoesntExists(f"User {login} doesn't exists")

        cmd = [
            self.__kadmincmd,
            "-p",
            self.__login,
            "del",
            f"{login}@{self.__realm}",
        ]
        Command.run(cmd, failOnStderr=True)
