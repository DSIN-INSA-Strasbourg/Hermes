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


from .hermestestcase import HermesServerTestCase

from server.datamodel import Datamodel

from lib.datamodel.foreignkey import HermesCircularForeignkeysRefsError
from lib.datamodel.dataschema import (
    Dataschema,
    HermesInvalidDataschemaError,
    HermesInvalidForeignkeysError,
)


class TestDataschemaClass(HermesServerTestCase):
    def setUp(self):
        super().setUp()
        confdata = self.loadYaml()
        self.config = self.saveYamlAndLoadConfig(confdata)
        self.dm = Datamodel(self.config)

        self.base_schema = {
            "Groups": {
                "HERMES_ATTRIBUTES": set(("description", "group_id", "cn")),
                "SECRETS_ATTRIBUTES": set(),
                "CACHEONLY_ATTRIBUTES": set(),
                "LOCAL_ATTRIBUTES": set(),
                "PRIMARYKEY_ATTRIBUTE": "group_id",
                "FOREIGN_KEYS": {},
            },
            "GroupsMembers": {
                "HERMES_ATTRIBUTES": set(("unnecessary", "group_id", "user_id")),
                "SECRETS_ATTRIBUTES": set(),
                "CACHEONLY_ATTRIBUTES": set(),
                "LOCAL_ATTRIBUTES": set(),
                "PRIMARYKEY_ATTRIBUTE": ("group_id", "user_id"),
                "FOREIGN_KEYS": {
                    "group_id": ["Groups", "group_id"],
                    "user_id": ["Users", "user_id"],
                },
            },
            "UserPasswords": {
                "HERMES_ATTRIBUTES": set(
                    (
                        "last_change",
                        "password_cacheonly",
                        "password_encrypted",
                        "password_ldap",
                        "user_id",
                    )
                ),
                "SECRETS_ATTRIBUTES": set(("password_encrypted",)),
                "CACHEONLY_ATTRIBUTES": set(("password_cacheonly",)),
                "LOCAL_ATTRIBUTES": set(("last_change",)),
                "PRIMARYKEY_ATTRIBUTE": "user_id",
                "FOREIGN_KEYS": {
                    "user_id": ["Users", "user_id"],
                },
            },
            "Users": {
                "HERMES_ATTRIBUTES": set(
                    (
                        "cn",
                        "displayname",
                        "edupersonaffiliation",
                        "edupersonaffiliationSplitted",
                        "givenname",
                        "labeleduri",
                        "login",
                        "mail",
                        "modifyTimestamp",
                        "sn",
                        "user_id",
                    )
                ),
                "SECRETS_ATTRIBUTES": set(),
                "CACHEONLY_ATTRIBUTES": set(),
                "LOCAL_ATTRIBUTES": set(("modifyTimestamp",)),
                "PRIMARYKEY_ATTRIBUTE": "user_id",
                "FOREIGN_KEYS": {},
            },
        }

    def tearDown(self):
        super().tearDown()
        self.purgeTmpdirContent()

    def test_init_fails_if_no_args(self):
        self.assertRaisesRegex(
            AttributeError,
            "Cannot instantiate schema from nothing: you must specify one data source",
            Dataschema,
        )

    def test_init_fails_if_two_args(self):
        self.assertRaisesRegex(
            AttributeError,
            "Cannot instantiate schema from multiple data sources at once",
            Dataschema,
            from_raw_dict={},
            from_json_dict={},
        )

    def test_init_invalidschema_missingattr(self):
        del self.base_schema["Users"]["HERMES_ATTRIBUTES"]
        self.assertRaisesRegex(
            HermesInvalidDataschemaError,
            "'Users' is missing the attribute 'HERMES_ATTRIBUTES' in received json"
            " Dataschema",
            Dataschema,
            from_raw_dict=self.base_schema,
        )

    def test_init_invalidschema_wrongtype_attr(self):
        self.base_schema["Users"]["CACHEONLY_ATTRIBUTES"] = "string"
        self.assertRaisesRegex(
            HermesInvalidDataschemaError,
            r"'Users.CACHEONLY_ATTRIBUTES' has wrong type in received json Dataschema"
            r" \('<class 'str'>' instead of '\[<class 'list'>, <class 'tuple'>,"
            r" <class 'set'>\]'\)",
            Dataschema,
            from_raw_dict=self.base_schema,
        )

    def test_valid(self):
        self.maxDiff = None
        self.assertDictEqual(self.base_schema, self.dm.dataschema._schema)

    def test_schema_equals_schema_exported_and_imported(self):
        newschema = Dataschema.from_json(self.dm.dataschema.to_json())
        self.maxDiff = None
        self.assertDictEqual(newschema.schema, self.dm.dataschema.schema)

    def test_invalidforeignkey_invalidcontent(self):
        self.base_schema["GroupsMembers"]["FOREIGN_KEYS"] = {
            "group_id": ["Groups", "group_id", "invalid_third"],
            "user_id": ["invalid_only_one"],
        }

        self.assertRaisesRegex(
            HermesInvalidForeignkeysError,
            "Invalid foreignkeys:\n"
            "  - <GroupsMembers.group_id>: invalid content. 2 items expected,"
            " but 3 found. It is probably a bug.\n"
            "  - <GroupsMembers.user_id>: invalid content. 2 items expected,"
            " but 1 found. It is probably a bug.",
            Dataschema,
            from_raw_dict=self.base_schema,
        )

    def test_invalidforeignkey_unknown_attribute(self):
        confdata = self.loadYaml()
        confdata["hermes-server"]["datamodel"]["GroupsMembers"]["foreignkeys"] = {
            "unknown": {
                "from_objtype": "Groups",
                "from_attr": "group_id",
            },
            "user_id": {
                "from_objtype": "Users",
                "from_attr": "user_id",
            },
        }
        config = self.saveYamlAndLoadConfig(confdata)
        self.assertRaisesRegex(
            HermesInvalidForeignkeysError,
            "Invalid foreignkeys:\n"
            "  - <GroupsMembers.unknown>: the attribute 'unknown' doesn't"
            " exist in 'GroupsMembers' in datamodel",
            Datamodel,
            config,
        )

    def test_invalidforeignkey_attribute_notprimarykey_str(self):
        confdata = self.loadYaml()
        confdata["hermes-server"]["datamodel"]["Users"]["foreignkeys"] = {
            "login": {
                "from_objtype": "Groups",
                "from_attr": "group_id",
            },
        }
        config = self.saveYamlAndLoadConfig(confdata)
        self.assertRaisesRegex(
            HermesInvalidForeignkeysError,
            "Invalid foreignkeys:\n"
            "  - <Users.login>: the attribute 'login' isn't the primary key of 'Users'"
            " in datamodel",
            Datamodel,
            config,
        )

    def test_invalidforeignkey_attribute_notprimarykey_tuple(self):
        confdata = self.loadYaml()
        confdata["hermes-server"]["datamodel"]["GroupsMembers"]["foreignkeys"] = {
            "unnecessary": {
                "from_objtype": "Groups",
                "from_attr": "group_id",
            },
            "user_id": {
                "from_objtype": "Users",
                "from_attr": "user_id",
            },
        }
        config = self.saveYamlAndLoadConfig(confdata)
        self.assertRaisesRegex(
            HermesInvalidForeignkeysError,
            "Invalid foreignkeys:\n"
            "  - <GroupsMembers.unnecessary>: the attribute 'unnecessary' isn't"
            " a primary key of 'GroupsMembers' in datamodel",
            Datamodel,
            config,
        )

    def test_invalidforeignkey_unknown_fkobjtype(self):
        confdata = self.loadYaml()
        confdata["hermes-server"]["datamodel"]["GroupsMembers"]["foreignkeys"] = {
            "group_id": {
                "from_objtype": "unknown",
                "from_attr": "group_id",
            },
            "user_id": {
                "from_objtype": "Users",
                "from_attr": "user_id",
            },
        }
        config = self.saveYamlAndLoadConfig(confdata)
        self.assertRaisesRegex(
            HermesInvalidForeignkeysError,
            "Invalid foreignkeys:\n"
            "  - <GroupsMembers.group_id>: the objtype 'unknown' doesn't"
            " exist in datamodel",
            Datamodel,
            config,
        )

    def test_invalidforeignkey_unknown_fkattribute(self):
        confdata = self.loadYaml()
        confdata["hermes-server"]["datamodel"]["GroupsMembers"]["foreignkeys"] = {
            "group_id": {
                "from_objtype": "Groups",
                "from_attr": "unknown",
            },
            "user_id": {
                "from_objtype": "Users",
                "from_attr": "user_id",
            },
        }
        config = self.saveYamlAndLoadConfig(confdata)
        self.assertRaisesRegex(
            HermesInvalidForeignkeysError,
            "Invalid foreignkeys:\n"
            "  - <GroupsMembers.group_id>: the attribute 'unknown' doesn't"
            " exist in 'Groups' in datamodel",
            Datamodel,
            config,
        )

    def test_invalidforeignkey_invalid_fkattribute_tuple(self):
        confdata = self.loadYaml()
        confdata["hermes-server"]["datamodel"]["Users"]["foreignkeys"] = {
            "user_id": {
                "from_objtype": "GroupsMembers",
                "from_attr": "group_id",
            },
        }
        config = self.saveYamlAndLoadConfig(confdata)
        self.assertRaisesRegex(
            HermesInvalidForeignkeysError,
            "Invalid foreignkeys:\n"
            "  - <Users.user_id>: the objtype 'GroupsMembers' has a tuple as"
            " primary key, foreign keys can't currently be set on a tuple",
            Datamodel,
            config,
        )

    def test_invalidforeignkey_fkattribute_notprimarykey(self):
        confdata = self.loadYaml()
        confdata["hermes-server"]["datamodel"]["GroupsMembers"]["foreignkeys"] = {
            "group_id": {
                "from_objtype": "Groups",
                "from_attr": "group_id",
            },
            "user_id": {
                "from_objtype": "Users",
                "from_attr": "login",
            },
        }
        config = self.saveYamlAndLoadConfig(confdata)
        self.assertRaisesRegex(
            HermesInvalidForeignkeysError,
            "Invalid foreignkeys:\n"
            "  - <GroupsMembers.user_id>: the attribute 'login' is not the primary"
            " key of 'Users' in datamodel",
            Datamodel,
            config,
        )

    def test_circular_foreignkeys(self):
        confdata = self.loadYaml()
        confdata["hermes-server"]["datamodel"]["Groups"]["foreignkeys"] = {
            "group_id": {
                "from_objtype": "UserPasswords",
                "from_attr": "user_id",
            },
        }
        confdata["hermes-server"]["datamodel"]["Users"]["foreignkeys"] = {
            "user_id": {
                "from_objtype": "Groups",
                "from_attr": "group_id",
            },
        }
        confdata["hermes-server"]["datamodel"]["UserPasswords"]["foreignkeys"] = {
            "user_id": {
                "from_objtype": "Users",
                "from_attr": "user_id",
            },
        }
        config = self.saveYamlAndLoadConfig(confdata)
        self.assertRaisesRegex(
            HermesCircularForeignkeysRefsError,
            r"Circular foreign keys references found in"
            r" \[<ForeignKey\(Groups\.group_id -> UserPasswords\.user_id\)>,"
            r" <ForeignKey\(UserPasswords\.user_id -> Users\.user_id\)>,"
            r" <ForeignKey\(Users\.user_id -> Groups\.group_id\)>\]\."
            r" Unable to continue\.",
            Datamodel,
            config,
        )
