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


from hermestestcase import HermesServerTestCase

from lib.datamodel.dataobject import DataObject
from lib.datamodel.event import Event

import logging

logger = logging.getLogger("hermes")


class TestEventClass(HermesServerTestCase):
    def setUp(self):
        class TestUsers(DataObject):
            HERMES_ATTRIBUTES = set(
                [
                    "edupersonaffiliation",
                    "login",
                    "newattr",
                    "user_id",
                ]
            )
            SECRETS_ATTRIBUTES = set()
            CACHEONLY_ATTRIBUTES = set()
            LOCAL_ATTRIBUTES = set()
            PRIMARYKEY_ATTRIBUTE = "user_id"

        self.TestUsers = TestUsers

    def getObj(self):
        d = {
            "user_id": 1,
            "login": f"user_1",
            "edupersonaffiliation": ["employee", "member", "staff"],
        }
        return self.TestUsers(from_json_dict=d)

    def getJson(self):
        return {
            "evcategory": "base",
            "eventtype": "added",
            "objtype": "TestUsers",
            "objpkey": 1,
            "objattrs": {
                "edupersonaffiliation": ["employee", "member", "staff"],
                "user_id": 1,
                "login": "user_1",
            },
        }

    def test_init_fails_if_no_args(self):
        self.assertRaisesRegex(
            AttributeError,
            "Cannot instanciate object from nothing : you must specify one data source",
            Event,
        )

    def test_init_fails_if_two_args(self):
        self.assertRaisesRegex(
            AttributeError,
            "Cannot instanciate object from multiple data sources at once",
            Event,
            objattrs={},
            from_json_dict={},
        )

    def test_init_from_objattrs(self):
        o = self.getObj()
        e = Event(evcategory="base", eventtype="added", obj=o, objattrs=o.toEvent())
        self.assertRegex(e.toString(set()), "^<Event\(TestUsers_added\[<TestUsers\[1\]>\], .*\)>")

    def test_init_from_json(self):
        e = Event(from_json_dict=self.getJson())
        self.assertRegex(e.toString(set()), "^<Event\(TestUsers_added\[1\], .*\)>")

    def test_init_from_objattrs_withoutobj(self):
        o = self.getObj()
        e = Event(evcategory="base", eventtype="added", objattrs=o.toEvent())
        self.assertRegex(e.toString(set()), "^<Event\(added, .*\)>")

    def test_init_from_objattrs_initsync(self):
        o = self.getObj()
        e = Event(evcategory="initsync", eventtype="added", obj=o, objattrs=o.toEvent())
        self.assertRegex(
            e.toString(set()), "^<Event\(initsync_TestUsers_added\[<TestUsers\[1\]>\], .*\)>"
        )

    def test_init_from_objattrs_initstart(self):
        e = Event(evcategory="initsync", eventtype="init-start", obj=None, objattrs={})
        self.assertRegex(e.toString(set()), "^<Event\(initsync_init-start, .*\)>")
