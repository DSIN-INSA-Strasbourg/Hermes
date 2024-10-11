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

from lib.datamodel.dataobject import DataObject, HermesMergingConflictError
from lib.datamodel.jinja import HermesNativeEnvironment

from jinja2 import StrictUndefined


class TestDataobjectClass(HermesServerTestCase):
    def setUp(self):
        super().setUp()
        jinjaenv: HermesNativeEnvironment = HermesNativeEnvironment(
            undefined=StrictUndefined
        )

        class TestUsersSource1(DataObject):
            HERMES_ATTRIBUTES = set(
                [
                    "cn",
                    "displayname",
                    "edupersonaffiliation",
                    "edupersonaffiliationSplitted",
                    "givenname",
                    "labeleduri",
                    "login",
                    "mail",
                    "nothing",
                    "sn",
                    "user_id",
                ]
            )
            SECRETS_ATTRIBUTES = set()
            CACHEONLY_ATTRIBUTES = set()
            LOCAL_ATTRIBUTES = set()
            PRIMARYKEY_ATTRIBUTE = "user_id"

            REMOTE_ATTRIBUTES = set(
                [
                    "CN",
                    "DISPLAYNAME",
                    "EDUPERSONAFFILIATION",
                    "EDUPERSONPRIMARYAFFILIATION",
                    "EDUPERSONAFFILIATION1",
                    "EDUPERSONAFFILIATION2",
                    "EDUPERSONAFFILIATION3",
                    "GIVENNAME",
                    "LABELEDURI",
                    "LOGIN",
                    "MAIL",
                    "NOTHING1",
                    "NOTHING2",
                    "NOTHING3",
                    "SN",
                    "USER_ID",
                ]
            )
            HERMES_TO_REMOTE_MAPPING = {
                "cn": "CN",
                "displayname": "DISPLAYNAME",
                "edupersonaffiliation": jinjaenv.from_string(
                    "{{ EDUPERSONAFFILIATION if EDUPERSONAFFILIATION is none else"
                    " EDUPERSONAFFILIATION.split(';') }}"
                ),
                "edupersonaffiliationSplitted": [
                    "EDUPERSONPRIMARYAFFILIATION",
                    "EDUPERSONAFFILIATION1",
                    "EDUPERSONAFFILIATION2",
                    "EDUPERSONAFFILIATION3",
                ],
                "givenname": "GIVENNAME",
                "labeleduri": "LABELEDURI",
                "login": "LOGIN",
                "mail": "MAIL",
                "nothing": ["NOTHING1", "NOTHING2", "NOTHING3"],
                "sn": "SN",
                "user_id": "USER_ID",
            }

        class TestUsersSource2(DataObject):
            HERMES_ATTRIBUTES = set(
                [
                    "cn",
                    "displayname",
                    "modifyTimestamp",
                    "password",
                    "encrypted_password",
                    "user_id",
                ]
            )
            SECRETS_ATTRIBUTES = set(["password"])
            CACHEONLY_ATTRIBUTES = set(["encrypted_password"])
            LOCAL_ATTRIBUTES = set(["modifyTimestamp"])
            PRIMARYKEY_ATTRIBUTE = "user_id"

            REMOTE_ATTRIBUTES = set(
                [
                    "CN",
                    "DISPLAYNAME",
                    "modifyTimestamp",
                    "PASSWORD",
                    "ENCRYPTED_PASSWORD",
                    "UID",
                ]
            )
            HERMES_TO_REMOTE_MAPPING = {
                "cn": "CN",
                "displayname": "DISPLAYNAME",
                "modifyTimestamp": "modifyTimestamp",
                "password": "PASSWORD",
                "encrypted_password": "ENCRYPTED_PASSWORD",
                "user_id": "UID",
            }

        class TestUsers(DataObject):
            HERMES_ATTRIBUTES = set(
                [
                    "cn",
                    "displayname",
                    "edupersonaffiliation",
                    "edupersonaffiliationSplitted",
                    "givenname",
                    "labeleduri",
                    "login",
                    "mail",
                    "modifyTimestamp",
                    "password",
                    "encrypted_password",
                    "sn",
                    "user_id",
                ]
            )
            SECRETS_ATTRIBUTES = set(["password"])
            CACHEONLY_ATTRIBUTES = set(["encrypted_password"])
            LOCAL_ATTRIBUTES = set(["modifyTimestamp"])
            PRIMARYKEY_ATTRIBUTE = "user_id"

        class TestGroupsMembers(DataObject):
            HERMES_ATTRIBUTES = set(
                [
                    "group_id",
                    "user_id",
                ]
            )
            SECRETS_ATTRIBUTES = set()
            CACHEONLY_ATTRIBUTES = set()
            LOCAL_ATTRIBUTES = set()
            PRIMARYKEY_ATTRIBUTE = ("group_id", "user_id")

        self.TestUsers = TestUsers
        self.TestUsersSource1 = TestUsersSource1
        self.TestUsersSource2 = TestUsersSource2
        self.TestGroupsMembers = TestGroupsMembers

        self.validjson_src1 = {
            "cn": "Test User",
            "displayname": "User Test",
            "edupersonaffiliation": ["employee", "member", "staff"],
            "edupersonaffiliationSplitted": ["employee", "member", "staff"],
            "givenname": "Test",
            "labeleduri": None,
            "login": "test.user",
            "mail": "test.user@example.com",
            "sn": "User",
            "user_id": 42,
        }

        self.validjson_src2 = {
            "cn": "Test User",
            "displayname": "User Test",
            "modifyTimestamp": "2023-01-13T12:34:56.789012",
            "password": "SeCr3t",
            "encrypted_password": "EnCrYpTeD_SeCr3t",
            "user_id": 42,
        }

    def tearDown(self):
        super().tearDown()
        self.purgeTmpdirContent()

    def test_init_fails_if_no_args(self):
        self.assertRaisesRegex(
            AttributeError,
            "Cannot instantiate object from nothing: you must specify one data source",
            self.TestUsers,
        )

    def test_init_fails_if_two_args(self):
        self.assertRaisesRegex(
            AttributeError,
            "Cannot instantiate object from multiple data sources at once",
            self.TestUsers,
            from_remote={},
            from_json_dict={},
        )

    def test_init_fromRemote_fails_if_REMOTE_ATTRIBUTES_is_none(self):
        self.assertRaisesRegex(
            AttributeError,
            "Current class TestUsers can't be instantiated with 'from_remote' args as"
            " TestUsers.REMOTE_ATTRIBUTES is not defined",
            self.TestUsers,
            from_remote=dict(),
        )

    def test_init_fromRemote_fails_if_empty(self):
        self.assertRaisesRegex(
            AttributeError,
            "^Required attributes are missing from specified from_remote dict: ",
            self.TestUsersSource1,
            from_remote=dict(),
        )

    def test_init_fromRemote_fails_if_invalid_type_in_value_of_HERMES_TO_REMOTE_MAPPING(
        self,
    ):
        data = {
            "CN": "Test User",
            "DISPLAYNAME": "User Test",
            "EDUPERSONAFFILIATION": "employee;member;staff",
            "EDUPERSONPRIMARYAFFILIATION": "employee",
            "EDUPERSONAFFILIATION1": "member",
            "EDUPERSONAFFILIATION2": "staff",
            "EDUPERSONAFFILIATION3": None,
            "GIVENNAME": "Test",
            "LABELEDURI": None,
            "LOGIN": "test.user",
            "MAIL": "test.user@example.com",
            "NOTHING1": None,
            "NOTHING2": None,
            "NOTHING3": None,
            "SN": "User",
            "USER_ID": 42,
        }

        self.TestUsersSource1.HERMES_TO_REMOTE_MAPPING["cn"] = 1
        self.assertRaisesRegex(
            AttributeError,
            r"^Invalid type met in HERMES_TO_REMOTE_MAPPING\['cn'\]: <class 'int'>",
            self.TestUsersSource1,
            from_remote=data,
        )

        self.TestUsersSource1.HERMES_TO_REMOTE_MAPPING["cn"] = {"a": 1}
        self.assertRaisesRegex(
            AttributeError,
            r"^Invalid type met in HERMES_TO_REMOTE_MAPPING\['cn'\]: <class 'dict'>",
            self.TestUsersSource1,
            from_remote=data,
        )

    def test_init_fromRemote_succeed(self):
        data = {
            "CN": "Test User",
            "DISPLAYNAME": "User Test",
            "EDUPERSONAFFILIATION": "employee;member;staff",
            "EDUPERSONPRIMARYAFFILIATION": "employee",
            "EDUPERSONAFFILIATION1": "member",
            "EDUPERSONAFFILIATION2": "staff",
            "EDUPERSONAFFILIATION3": None,
            "GIVENNAME": "Test",
            "LABELEDURI": None,
            "LOGIN": "test.user",
            "MAIL": "test.user@example.com",
            "NOTHING1": None,
            "NOTHING2": None,
            "NOTHING3": None,
            "SN": "User",
            "USER_ID": 42,
        }
        user = self.TestUsersSource1(from_remote=data)
        self.assertIsInstance(user, self.TestUsersSource1)
        self.assertEqual(user.cn, "Test User")
        self.assertRaisesRegex(
            AttributeError,
            "^'TestUsersSource1' object has no attribute 'labeleduri'",
            getattr,
            user,
            "labeleduri",
        )
        self.assertListEqual(user.edupersonaffiliation, ["employee", "member", "staff"])
        self.assertListEqual(
            user.edupersonaffiliationSplitted, ["employee", "member", "staff"]
        )
        self.assertRaisesRegex(
            AttributeError,
            "^'TestUsersSource1' object has no attribute 'nothing'",
            getattr,
            user,
            "nothing",
        )
        self.assertEqual(user.user_id, 42)

    def test_init_fromJson_empty_succeed(self):
        user = self.TestUsersSource1(from_json_dict={})
        self.assertIsInstance(user, self.TestUsersSource1)

    def test_init_fromJson_succeed(self):
        user = self.TestUsersSource1(from_json_dict=self.validjson_src1)
        self.assertIsInstance(user, self.TestUsersSource1)
        self.assertEqual(user.cn, "Test User")
        self.assertIsNone(user.labeleduri)
        self.assertListEqual(user.edupersonaffiliation, ["employee", "member", "staff"])
        self.assertListEqual(
            user.edupersonaffiliationSplitted, ["employee", "member", "staff"]
        )
        self.assertEqual(user.user_id, 42)

    def test_getattribute_missing(self):
        user = self.TestUsersSource1(from_json_dict=self.validjson_src1)

        # Attr that could exist in data dict
        self.assertRaisesRegex(
            AttributeError,
            "'TestUsersSource1' object has no attribute 'nothing'",
            getattr,
            user,
            "nothing",
        )

        # Attr that could not exist in data dict
        self.assertRaisesRegex(
            AttributeError,
            "'TestUsersSource1' object has no attribute 'undefinednothing'",
            getattr,
            user,
            "undefinednothing",
        )

    def test_setattribute(self):
        user = self.TestUsersSource1(from_json_dict=self.validjson_src1)

        # Attr that could exist in data dict
        user.nothing = "value_nothing"
        self.assertIn("nothing", user._data)
        self.assertEqual(user.nothing, "value_nothing")

        # Attr that could not exist in data dict
        user.undefinednothing = "value_undefinednothing"
        self.assertNotIn("undefinednothing", user._data)
        self.assertEqual(user.undefinednothing, "value_undefinednothing")

    def test_delattribute(self):
        user = self.TestUsersSource1(from_json_dict=self.validjson_src1)

        # Attr that could exist in data dict
        user.nothing = "value_nothing"
        delattr(user, "nothing")
        self.assertNotIn("nothing", user._data)
        self.assertRaisesRegex(
            AttributeError,
            "'TestUsersSource1' object has no attribute 'nothing'",
            getattr,
            user,
            "nothing",
        )

        # Attr that could not exist in data dict
        user.undefinednothing = "value_undefinednothing"
        delattr(user, "undefinednothing")
        self.assertNotIn("undefinednothing", user._data)
        self.assertRaisesRegex(
            AttributeError,
            "'TestUsersSource1' object has no attribute 'undefinednothing'",
            getattr,
            user,
            "undefinednothing",
        )

    def test_eq_operator(self):
        user1 = self.TestUsersSource1(from_json_dict=self.validjson_src1)
        user2 = self.TestUsersSource1(from_json_dict=self.validjson_src1)
        self.assertEqual(user1, user2)
        user1.sn = "Use"
        self.assertFalse(user1 == user2)
        user1.sn = "User"
        self.assertEqual(user1, user2)

    def test_ne_operator(self):
        user1 = self.TestUsersSource1(from_json_dict=self.validjson_src1)
        user2 = self.TestUsersSource1(from_json_dict=self.validjson_src1)
        self.assertFalse(user1 != user2)
        user1.sn = "Use"
        self.assertNotEqual(user1, user2)
        user1.sn = "User"
        self.assertFalse(user1 != user2)

    def test_lt_operator(self):
        user1 = self.TestUsersSource1(from_json_dict=self.validjson_src1)
        user2 = self.TestUsersSource1(from_json_dict=self.validjson_src1)
        self.assertFalse(user1 < user2)
        user1.user_id -= 1
        self.assertTrue(user1 < user2)

    def test_jsondata_property_filters_LOCAL_and_SECRETS_attributes(self):
        user = self.TestUsersSource2(from_json_dict=self.validjson_src2)
        # We should get validjson_src2 data, minus LOCAL and SECRETS attributes
        # (modifyTimestamp and password)
        awaited_data = dict(self.validjson_src2)
        del awaited_data["modifyTimestamp"]
        del awaited_data["password"]

        self.assertDictEqual(awaited_data, user._jsondata)

    def test_diffFrom_equals(self):
        user1 = self.TestUsersSource2(from_json_dict=self.validjson_src2)
        user2 = self.TestUsersSource2(from_json_dict=self.validjson_src2)

        d = user1.diffFrom(user2)
        self.assertDictEqual({"added": {}, "modified": {}, "removed": {}}, d.dict)

    def test_diffFrom_added(self):
        user1 = self.TestUsersSource2(from_json_dict=self.validjson_src2)
        user2 = self.TestUsersSource2(from_json_dict=self.validjson_src2)
        delattr(user2, "cn")

        d = user1.diffFrom(user2)
        self.assertDictEqual(
            {"added": {"cn": "Test User"}, "modified": {}, "removed": {}}, d.dict
        )

    def test_diffFrom_added_and_modified(self):
        user1 = self.TestUsersSource2(from_json_dict=self.validjson_src2)
        user2 = self.TestUsersSource2(from_json_dict=self.validjson_src2)
        user1.cn = ["Other User and type"]

        d = user1.diffFrom(user2)
        self.assertDictEqual(
            {"added": {}, "modified": {"cn": ["Other User and type"]}, "removed": {}},
            d.dict,
        )

    def test_diffFrom_removed(self):
        user1 = self.TestUsersSource2(from_json_dict=self.validjson_src2)
        user2 = self.TestUsersSource2(from_json_dict=self.validjson_src2)
        delattr(user1, "cn")

        d = user1.diffFrom(user2)
        self.assertDictEqual(
            {"added": {}, "modified": {}, "removed": {"cn": None}}, d.dict
        )

    def test_diffFrom_ignore_LOCAL_AND_CACHEONLY_attrs_only(self):
        user1 = self.TestUsersSource2(from_json_dict=self.validjson_src2)
        user2 = self.TestUsersSource2(from_json_dict={})

        # We should get validjson_src2 data, minus LOCAL and CACHEONLY attributes
        # (modifyTimestamp and encrypted_password)
        awaited_data = dict(self.validjson_src2)
        del awaited_data["modifyTimestamp"]
        del awaited_data["encrypted_password"]

        d = user1.diffFrom(user2)
        self.assertDictEqual(
            {"added": awaited_data, "modified": {}, "removed": {}}, d.dict
        )

    def test_isdifferent(self):
        self.assertTrue(DataObject.isDifferent("1", 1))
        self.assertFalse(DataObject.isDifferent(1, 1))
        self.assertFalse(DataObject.isDifferent("1", "1"))
        self.assertTrue(DataObject.isDifferent([1], [1, 2]))
        self.assertTrue(DataObject.isDifferent([1, 3], [1, 2]))
        self.assertFalse(DataObject.isDifferent([1, 2], [1, 2]))
        self.assertFalse(
            DataObject.isDifferent({"a": [1, 2], "b": 3}, {"a": [1, 2], "b": 3})
        )
        self.assertTrue(
            DataObject.isDifferent({"a": [1, 2], "b": 3}, {"a": [1, 2], "c": 3})
        )
        self.assertTrue(
            DataObject.isDifferent({"a": [1, 2], "b": 3}, {"a": [1, 2, 3], "b": 3})
        )

        user1 = self.TestUsersSource2(from_json_dict=self.validjson_src2)
        user2 = self.TestUsersSource2(from_json_dict=self.validjson_src2)
        self.assertFalse(DataObject.isDifferent(user1, user2))
        user1.cn = "Other User"
        self.assertTrue(DataObject.isDifferent(user1, user2))

    def test_toNative(self):
        user = self.TestUsersSource2(from_json_dict=self.validjson_src2)
        self.assertDictEqual(user.toNative(), self.validjson_src2)

    def test_toEvent(self):
        user = self.TestUsersSource2(from_json_dict=self.validjson_src2)

        # We should get validjson_src2 data, minus LOCAL and CACHEONLY attributes
        # (modifyTimestamp and encrypted_password)
        awaited_data = dict(self.validjson_src2)
        del awaited_data["modifyTimestamp"]
        del awaited_data["encrypted_password"]

        self.assertDictEqual(user.toEvent(), awaited_data)

    def test_mergeWith_conflict_error_exception(self):
        user1 = self.TestUsersSource1(from_json_dict=self.validjson_src1)
        user2 = self.TestUsersSource2(from_json_dict=self.validjson_src2)

        # Change user1.cn to have a different value from user2
        user1.cn = "Other User"
        self.assertRaisesRegex(
            HermesMergingConflictError,
            r"Merging conflict. Attribute 'cn' exist on both objects with differents"
            r" values \(<TestUsersSource1\[42\]>: 'Other User' /"
            r" <TestUsersSource2\[42\]>: 'Test User'\)",
            user1.mergeWith,
            other=user2,
            raiseExceptionOnConflict=True,
        )

    def test_mergeWith_conflict_error_noexception(self):
        user = self.TestUsers(from_json_dict={})
        user1 = self.TestUsersSource1(from_json_dict=self.validjson_src1)
        user2 = self.TestUsersSource2(from_json_dict=self.validjson_src2)

        # Change user1.cn to have a different value from user2
        user1.cn = "Other User"

        user.mergeWith(other=user1, raiseExceptionOnConflict=False)
        with self.assertLogs(__hermes__.logger, level="DEBUG") as cm:
            user.mergeWith(other=user2, raiseExceptionOnConflict=False)

        self.assertEqual(
            cm.output,
            [
                "DEBUG:hermes-unit-tests:Merging conflict. Attribute 'cn' exist on both"
                " objects with differents values (<TestUsers[42]>: 'Other User' /"
                " <TestUsersSource2[42]>: 'Test User'). The first one is kept"
            ],
        )

        awaiteddata = self.validjson_src2 | self.validjson_src1 | {"cn": "Other User"}
        self.assertEqual(user.toNative(), awaiteddata)

    def test_mergeWith_success(self):
        user = self.TestUsers(from_json_dict={})
        user1 = self.TestUsersSource1(from_json_dict=self.validjson_src1)
        user2 = self.TestUsersSource2(from_json_dict=self.validjson_src2)

        user.mergeWith(other=user1, raiseExceptionOnConflict=False)
        user.mergeWith(other=user2, raiseExceptionOnConflict=False)
        awaiteddata = self.validjson_src2 | self.validjson_src1
        self.assertEqual(user.toNative(), awaiteddata)

    def test_getPkey_oneattr(self):
        user = self.TestUsersSource1(from_json_dict=self.validjson_src1)
        self.assertEqual(user.getPKey(), 42)

    def test_getPkey_severalattrs(self):
        json = {
            "group_id": 123,
            "user_id": 456,
        }
        gm = self.TestGroupsMembers(from_json_dict=json)
        self.assertTupleEqual(gm.getPKey(), (123, 456))

    def test_getType(self):
        user = self.TestUsersSource1(from_json_dict=self.validjson_src1)
        self.assertEqual(user.getType(), "TestUsersSource1")
