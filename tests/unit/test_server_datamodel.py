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

from server.datamodel import (
    Datamodel,
    HermesDataModelMissingPrimarykeyError,
)

from lib.datamodel.jinja import HermesDataModelAttrsmappingError


class TestDatamodelClass(HermesServerTestCase):
    def tearDown(self):
        super().tearDown()
        self.purgeTmpdirContent()

    def test_valid(self):
        confdata = self.loadYaml()
        confdata["hermes"]["cache"] = {
            "backup_count": 5,
            "dirpath": "/tmp",
            "enable_compression": True,
        }
        config = self.saveYamlAndLoadConfig(confdata)

        dm = Datamodel(config)
        self.assertEqual(
            dm.dataschema.objectTypes["Users"].PRIMARYKEY_ATTRIBUTE, "user_id"
        )

        hermesattrs = {
            dm.dataschema.objectTypes["Users"]: set(
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
                ),
            ),
            dm.dataschema.objectTypes["UserPasswords"]: set(
                (
                    "user_id",
                    "password_encrypted",
                    "password_cacheonly",
                    "password_ldap",
                    "last_change",
                ),
            ),
            dm.dataschema.objectTypes["Groups"]: set(
                (
                    "cn",
                    "description",
                    "group_id",
                ),
            ),
            dm.dataschema.objectTypes["GroupsMembers"]: set(
                (
                    "group_id",
                    "user_id",
                    "unnecessary",
                ),
            ),
        }
        for cls, attrs in hermesattrs.items():
            self.assertSetEqual(cls.HERMES_ATTRIBUTES, attrs)

    def test_attrsmapping_value_empty(self):
        confdata = self.loadYaml()
        confdata["hermes-server"]["datamodel"]["Users"]["sources"]["source1"][
            "attrsmapping"
        ]["cn"] = ""
        config = self.saveYamlAndLoadConfig(confdata)

        self.assertRaisesRegex(
            HermesDataModelAttrsmappingError,
            "hermes-server.datamodel.Users.source1.attrsmapping: Empty value was found",
            Datamodel,
            config,
        )

    def test_attrsmapping_value_multiplejinjatemplates(self):
        confdata = self.loadYaml()
        confdata["hermes-server"]["datamodel"]["Users"]["sources"]["source1"][
            "attrsmapping"
        ]["cn"] = r"{% set testing = 'it worked' %}{{ CN | lower() }}"
        config = self.saveYamlAndLoadConfig(confdata)

        self.assertRaisesRegex(
            HermesDataModelAttrsmappingError,
            (
                "hermes-server.datamodel.Users.source1.attrsmapping: Multiple jinja"
                " templates found in '''{% set testing = 'it worked' %}"
                "{{ CN | lower() }}''', only one is allowed"
            ),
            Datamodel,
            config,
        )

    def test_DatamodelFragment_jinjatemplates_compiled(self):
        from jinja2.environment import Template

        confdata = self.loadYaml()
        config = self.saveYamlAndLoadConfig(confdata)
        dm = Datamodel(config)

        self.assertIsInstance(
            dm._fragments["Users"][0]._compiledsettings["attrsmapping"][
                "edupersonaffiliation"
            ],
            Template,
        )
        self.assertIsInstance(
            dm._fragments["Users"][0]._compiledsettings["fetch"]["query"], Template
        )

    def test_Datamodel_jinjatemplates_compiled(self):
        from jinja2.environment import Template

        confdata = self.loadYaml()
        config = self.saveYamlAndLoadConfig(confdata)
        Datamodel(config)

        self.assertIsInstance(
            config["hermes-server"]["datamodel"]["UserPasswords"][
                "integrity_constraints"
            ][0],
            Template,
        )
        self.assertIsInstance(
            config["hermes-server"]["datamodel"]["GroupsMembers"][
                "integrity_constraints"
            ][0],
            Template,
        )
        self.assertSetEqual(
            config["hermes-server"]["datamodel"]["UserPasswords"][
                "integrity_constraints_vars"
            ],
            set(("Users_pkeys", "_SELF")),
        )
        self.assertSetEqual(
            config["hermes-server"]["datamodel"]["GroupsMembers"][
                "integrity_constraints_vars"
            ],
            set(("Users_pkeys", "_SELF", "Groups_pkeys")),
        )

    def test_attrsmapping_value_mixedjinjatemplateandrawdata(self):
        confdata = self.loadYaml()
        confdata["hermes-server"]["datamodel"]["Users"]["sources"]["source1"][
            "attrsmapping"
        ]["cn"] = r"{{ CN | lower() }} is the CN"
        config = self.saveYamlAndLoadConfig(confdata)

        self.assertRaisesRegex(
            HermesDataModelAttrsmappingError,
            (
                "hermes-server.datamodel.Users.source1.attrsmapping: A mix between"
                " jinja templates and raw data was found in '''{{ CN | lower() }} is"
                " the CN''', with this configuration it's impossible to determine"
                " source attribute name"
            ),
            Datamodel,
            config,
        )

    def test_attrsmapping_value_missingprimarykey(self):
        confdata = self.loadYaml()
        del confdata["hermes-server"]["datamodel"]["Users"]["sources"]["source1"][
            "attrsmapping"
        ]["user_id"]
        config = self.saveYamlAndLoadConfig(confdata)

        self.assertRaisesRegex(
            HermesDataModelMissingPrimarykeyError,
            "The primary key 'user_id' must be fetched from each datasource",
            Datamodel,
            config,
        )

    def test_attrsmapping_value_partialprimarykey(self):
        confdata = self.loadYaml()
        confdata["hermes-server"]["datamodel"]["Users"]["primarykeyattr"] = [
            "user_id",
            "login",
        ]
        config = self.saveYamlAndLoadConfig(confdata)

        self.assertRaisesRegex(
            HermesDataModelMissingPrimarykeyError,
            r"The primary key '\('user_id', 'login'\)' must be fetched from each"
            r" datasource",
            Datamodel,
            config,
        )
