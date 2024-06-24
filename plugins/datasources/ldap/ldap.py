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


from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    # Only for type hints, won't import at runtime
    from ldap.ldapobject import LDAPObject

from lib.plugins import AbstractDataSourcePlugin
import ldap
import ldap.modlist
from datetime import datetime

HERMES_PLUGIN_CLASSNAME: str | None = "DatasourceLdap"
"""The plugin class name defined in this module file"""


class DatasourceLdap(AbstractDataSourcePlugin):
    """Remote Data Source for LDAP server"""

    def __init__(self, settings: dict[str, Any]):
        """Instantiate new plugin and store a copy of its settings dict in
        self._settings"""
        super().__init__(settings)
        self._ldap: LDAPObject | None = None

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

        if settings["ssl"]:
            if "cafile" in settings["ssl"]:
                ldap.set_option(ldap.OPT_X_TLS_CACERTFILE, settings["ssl"]["cafile"])
            if "certfile" in settings["ssl"]:
                ldap.set_option(ldap.OPT_X_TLS_CERTFILE, settings["ssl"]["certfile"])
            if "keyfile" in settings["ssl"]:
                ldap.set_option(ldap.OPT_X_TLS_KEYFILE, settings["ssl"]["keyfile"])

            ldap.set_option(ldap.OPT_X_TLS_NEWCTX, 0)

    def open(self):
        """Establish connection with LDAP server"""
        self._ldap = ldap.initialize(self._settings["uri"], bytes_mode=False)
        self._ldap.simple_bind_s(
            who=self._settings["binddn"],
            cred=self._settings["bindpassword"],
        )

    def close(self):
        """Close connection with LDAP server"""
        self._ldap.unbind_s()
        self._ldap = None

    def fetch(
        self,
        query: str | None,
        vars: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Fetch data from datasource with specified query and optional queryvars.
        Returns a list of dict containing each entry fetched, with REMOTE_ATTRIBUTES
        as keys, and corresponding fetched values as values"""
        scopes = {
            "base": ldap.SCOPE_BASE,
            "one": ldap.SCOPE_ONELEVEL,
            "onelevel": ldap.SCOPE_ONELEVEL,
            "sub": ldap.SCOPE_SUBTREE,
            "subtree": ldap.SCOPE_SUBTREE,
            "DEFAULT": ldap.SCOPE_SUBTREE,
        }
        fetcheddata = []

        results = self._ldap.search_s(
            base=vars.get("base", self._settings["basedn"]),
            scope=scopes.get(vars.get("scope", "DEFAULT"), "DEFAULT"),
            filterstr=vars.get("filter", "(objectClass=*)"),
            attrlist=vars.get("attrlist", None),
        )

        for dn, entry in results:
            flatentry = dict()
            for k in vars.get("attrlist", entry.keys()):
                v = entry.get(k, [])
                if self._settings["always_return_values_in_list"] or len(v) > 1:
                    flatentry[k] = self._convert_from_ldap(v)
                elif len(v) == 1:
                    flatentry[k] = self._convert_from_ldap(v[0])
                else:
                    flatentry[k] = None
            fetcheddata.append(flatentry)
        return fetcheddata

    def add(self, query: str | None, vars: dict[str, Any]):
        """Add LDAP entries on datasource with specified vars. Query is ignored
        Example of vars dict:
            vars = {
                "addlist": [
                    {
                        "dn": "uid=whatever,ou=company,dc=example,dc=com",  # Mandatory
                        "add": {  # Facultative
                            # Create attribute if it doesn't exist,
                            # and add "value" to it
                            "attrnameToAdd": "value",
                            # Create attribute if it doesn't exist,
                            # and add "value1" and "value2" to it
                            "attrnameToAddList": ["value1", "value2"],
                        },
                    },
                    {
                        "dn": "uid=otherdn,ou=company,dc=example,dc=com",
                        ...
                    },
                    ...
                ]
            }
        """
        for item in vars.get("addlist", []):
            addlist = []

            dn = item.get("dn")
            if not dn:
                continue

            for attrname, attrvalue in item.get("add", {}).items():
                addlist.append(
                    (attrname, self.convert_to_ldap(attrvalue)),
                )

            if addlist:
                self._ldap.add_s(dn, addlist)

    def delete(self, query: str | None, vars: dict[str, Any]):
        """Delete LDAP entries on datasource with specified vars. Query is ignored
        Example of vars dict:
            vars = {
                "dellist": [
                    {
                        "dn": "uid=whatever,ou=company,dc=example,dc=com",  # Mandatory
                    },
                    {
                        "dn": "uid=otherdn,ou=company,dc=example,dc=com",
                        ...
                    },
                    ...
                ]
            }
        """
        for item in vars.get("dellist", []):
            dn = item.get("dn")
            if dn:
                self._ldap.delete_s(dn)

    def modify(self, query: str | None, vars: dict[str, Any]):
        """Modify LDAP entries on datasource with specified vars. Query is ignored
        Example of vars dict:
            vars = {
                "modlist": [
                    {
                        "dn": "uid=whatever,ou=company,dc=example,dc=com",  # Mandatory
                        "add": {  # Facultative
                            # Create attribute if it doesn't exist,
                            # and add "value" to it
                            "attrnameToAdd": "value",
                            # Create attribute if it doesn't exist,
                            # and add "value1" and "value2" to it
                            "attrnameToAddList": ["value1", "value2"],
                        },
                        "modify": {  # Facultative
                            # Create attribute if it doesn't exist,
                            # and replace all its value by "value"
                            "attrnameToModify": "newvalue",
                            # Create attribute if it doesn't exist,
                            # and replace all its value by "newvalue1" and "newvalue2"
                            "attrnameToModifyList": ["newvalue1", "newvalue2"],
                        },
                        "delete": {  # Facultative
                            # Delete specified attribute and all of its values
                            "attrnameToDelete": None,
                            # Delete "value" from specified attribute.
                            # Raise an error if value is missing
                            "attrnameToDeleteValue": "value",
                            # Delete "value1" and "value2" from specified attribute.
                            # Raise an error if a value is missing
                            "attrnameToDeleteValueList": ["value1", "value2"],
                        },
                    },
                    {
                        "dn": "uid=otherdn,ou=company,dc=example,dc=com",
                        ...
                    },
                    ...
                ]
            }
        """
        for item in vars.get("modlist", []):
            modlist = []

            dn = item.get("dn")
            if not dn:
                continue

            for action, ldpaaction in (
                ("delete", ldap.MOD_DELETE),
                ("add", ldap.MOD_ADD),
                ("modify", ldap.MOD_REPLACE),
            ):
                for attrname, attrvalue in item.get(action, {}).items():
                    modlist.append(
                        (ldpaaction, attrname, self.convert_to_ldap(attrvalue)),
                    )

            if modlist:
                self._ldap.modify_s(dn, modlist)

    @classmethod
    def _convert_from_ldap(
        cls, data: bytearray | list[bytearray]
    ) -> int | float | datetime | str | list[int | float | datetime | str]:
        """Convert specified bytearray data to native type and returns it"""
        if type(data) is list:
            return [cls._convert_from_ldap(i) for i in data]

        val = data.decode()
        tests = [
            int,
            float,
            cls._convertdatetime_from_ldap,
        ]

        for func in tests:
            try:
                res = func(val)
            except ValueError:
                pass
            else:
                return res  # Conversion succeed

        return val  # str

    @classmethod
    def _convertdatetime_from_ldap(cls, val: str) -> datetime:
        """Try to convert specified val to datetime returns it.
        Raise ValueError if conversion failed"""
        res = datetime.strptime(val, "%Y%m%d%H%M%S%z")
        return res

    @staticmethod
    def convert_to_ldap(value: Any) -> list[bytearray]:
        """Convert specified value to ldap format"""

        # Particular case for delete operation, must not be encased in list
        if value is None:
            return None

        # Convert dattime instances to ldap datetime
        if isinstance(value, datetime):
            res = DatasourceLdap._convertdatetime_to_ldap(value)
        elif type(value) is list:
            res = []
            for listval in value:
                if isinstance(listval, datetime):
                    res.append(DatasourceLdap._convertdatetime_to_ldap(listval))
                else:
                    res.append(listval)
        else:
            # Convert values to list
            res = [value]

        # Convert values to str if necessary, then to bytes
        res = [str(v).encode("utf-8") for v in res]

        return res

    @classmethod
    def _convertdatetime_to_ldap(cls, dt: datetime) -> str:
        """Try to convert specified datetime dt to ldap str and returns it.
        Raise ValueError if conversion failed"""
        return dt.strftime("%Y%m%d%H%M%SZ")
