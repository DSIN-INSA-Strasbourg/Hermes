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

from lib.datamodel.datasource import Datasource
from lib.datamodel.dataschema import Dataschema
from server.datamodel import Datamodel

import logging

logger = logging.getLogger("hermes")


class TestDatasourceClass(HermesServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # logging.disable(logging.NOTSET)

    def setUp(self):
        super().setUp()
        confdata = self.loadYaml()
        self.config = self.saveYamlAndLoadConfig(confdata)
        self.dm = Datamodel(self.config)

    def getObjList(self, start=1, stop=3):
        res = []
        for i in range(start, stop + 1):
            d = {
                "user_id": i,
                "login": f"user_{i}",
                "edupersonaffiliation": ["employee", "member", "staff"],
            }
            res.append(self.dm.dataschema.objectTypes["Users"](from_json_dict=d))
        return res

    def getJson(self):
        return [
            {
                "user_id": 1,
                "login": "user_1",
                "edupersonaffiliation": ["employee", "member", "staff"],
            },
            {
                "user_id": 2,
                "login": "user_2",
                "edupersonaffiliation": ["employee", "member", "staff"],
            },
            {
                "user_id": 3,
                "login": "user_3",
                "edupersonaffiliation": ["employee", "member", "staff"],
            },
        ]

    def tearDown(self):
        super().tearDown()
        self.purgeTmpdirContent()

    def test_withTrashbin(self):
        data = Datasource(
            schema=self.dm.dataschema, enableTrashbin=True, enableCache=False
        )
        data["Users"] = self.dm.dataschema.objectlistTypes["Users"](self.getObjList())
        data.save()

        loadeddata = Datasource(
            schema=self.dm.dataschema, enableTrashbin=True, enableCache=False
        )
        loadeddata.loadFromCache()

        diff = data["Users"].diffFrom(loadeddata["Users"])
        self.assertFalse(diff)

    def test_withoutTrashbin(self):
        data = Datasource(
            schema=self.dm.dataschema, enableTrashbin=False, enableCache=False
        )
        data["Users"] = self.dm.dataschema.objectlistTypes["Users"](self.getObjList())
        data.save()

        loadeddata = Datasource(
            schema=self.dm.dataschema, enableTrashbin=False, enableCache=False
        )
        loadeddata.loadFromCache()

        diff = data["Users"].diffFrom(loadeddata["Users"])
        self.assertFalse(diff)
