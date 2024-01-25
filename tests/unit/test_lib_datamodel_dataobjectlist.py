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

from lib.datamodel.dataobject import DataObject
from lib.datamodel.dataobjectlist import DataObjectList


class TestDataobjectlistClass(HermesServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # logging.disable(logging.NOTSET)

    def setUp(self):
        super().setUp()
        confdata = self.loadYaml()
        self.config = self.saveYamlAndLoadConfig(confdata)

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

        class TestUsers2(TestUsers):
            pass

        class TestUsersList(DataObjectList):
            OBJTYPE = TestUsers

        self.TestUsers = TestUsers
        self.TestUsers2 = TestUsers2
        self.TestUsersList = TestUsersList

    def getObjList(self, start=1, stop=3):
        res = []
        for i in range(start, stop + 1):
            d = {
                "user_id": i,
                "login": f"user_{i}",
                "edupersonaffiliation": ["employee", "member", "staff"],
            }
            if i % 2 == 0:
                o = self.TestUsers(from_json_dict=d)
            else:
                o = self.TestUsers2(from_json_dict=d)
            res.append(o)
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

    def test_init_fails_if_no_args(self):
        self.assertRaisesRegex(
            AttributeError,
            "Cannot instantiate object from nothing: you must specify one data source",
            self.TestUsersList,
        )

    def test_init_fails_if_two_args(self):
        self.assertRaisesRegex(
            AttributeError,
            "Cannot instantiate object from multiple data sources at once",
            self.TestUsersList,
            objlist={},
            from_json_dict={},
        )

    def test_init_from_objlist(self):
        l = self.TestUsersList(objlist=self.getObjList(start=1, stop=3))
        self.assertEqual(len(l._data), 3)

    def test_init_from_json(self):
        l = self.TestUsersList(from_json_dict=self.getJson())
        self.assertEqual(len(l._data), 3)

    def test_iter(self):
        l = self.TestUsersList(objlist=self.getObjList(start=1, stop=3))
        for index, item in enumerate(l, start=1):
            self.assertEqual(repr(item), f"<TestUsers[{index}]>")

    def test_getitem(self):
        l = self.TestUsersList(objlist=self.getObjList(start=1, stop=3))
        self.assertEqual(repr(l[2]), f"<TestUsers[2]>")
        self.assertRaises(KeyError, l.__getitem__, 4)

    def test_get(self):
        l = self.TestUsersList(objlist=self.getObjList(start=1, stop=3))
        self.assertEqual(repr(l.get(2)), f"<TestUsers[2]>")
        self.assertIsNone(l.get(4))

    def test_getPKeys(self):
        l = self.TestUsersList(objlist=self.getObjList(start=1, stop=3))
        self.assertSetEqual(l.getPKeys(), set([1, 2, 3]))

    def test_append(self):
        l = self.TestUsersList(objlist=self.getObjList(start=1, stop=3))

        # Append pkeys 4 to 6
        for o in self.getObjList(4, 6):
            l.append(o)

        self.assertSetEqual(l.getPKeys(), set([1, 2, 3, 4, 5, 6]))
        self.assertSetEqual(l.inconsistencies, set())  # Must be empty

        l.append(o)  # Append again pkey 6 -> should go to inconsistencies
        self.assertSetEqual(l.getPKeys(), set([1, 2, 3, 4, 5]))
        self.assertSetEqual(l.inconsistencies, set([6]))

        # Append again pkey 6 -> should change nothing, as already in inconsistencies
        l.append(o)
        self.assertSetEqual(l.getPKeys(), set([1, 2, 3, 4, 5]))
        self.assertSetEqual(l.inconsistencies, set([6]))

    def test_replace(self):
        l = self.TestUsersList(objlist=self.getObjList(start=1, stop=3))
        self.assertEqual(l[2].login, "user_2")

        # Replace existing
        d = {
            "user_id": 2,
            "login": "user_2_new",
            "edupersonaffiliation": ["employee", "member", "staff"],
        }
        newobj2 = self.TestUsers(from_json_dict=d)
        l.replace(newobj2)
        self.assertEqual(l[2].login, "user_2_new")

        # Replace missing -> fail
        d = {
            "user_id": 4,
            "login": "user_4_new",
            "edupersonaffiliation": ["employee", "member", "staff"],
        }
        newobj4 = self.TestUsers(from_json_dict=d)
        self.assertRaisesRegex(
            IndexError,
            "Cannot replace object with pkey 4 as previous doesn't exist",
            l.replace,
            newobj4,
        )

    def test_removeByPkey(self):
        l = self.TestUsersList(objlist=self.getObjList(start=1, stop=3))
        # self.assertSetEqual(l.getPKeys(), set([1, 2, 3]))
        l.removeByPkey(2)
        self.assertSetEqual(l.getPKeys(), set([1, 3]))

    def test_remove(self):
        l = self.TestUsersList(objlist=self.getObjList(start=1, stop=3))
        # self.assertSetEqual(l.getPKeys(), set([1, 2, 3]))

        d = {
            "user_id": 2,
            "login": "user_2",
            "edupersonaffiliation": ["employee", "member", "staff"],
        }
        obj = self.TestUsers(from_json_dict=d)
        l.remove(obj)
        self.assertSetEqual(l.getPKeys(), set([1, 3]))

    def test_toNative(self):
        l = self.TestUsersList(objlist=self.getObjList(start=1, stop=3))
        native = [
            {
                "edupersonaffiliation": ["employee", "member", "staff"],
                "login": "user_1",
                "user_id": 1,
            },
            {
                "edupersonaffiliation": ["employee", "member", "staff"],
                "login": "user_2",
                "user_id": 2,
            },
            {
                "edupersonaffiliation": ["employee", "member", "staff"],
                "login": "user_3",
                "user_id": 3,
            },
        ]
        self.assertListEqual(l.toNative(), native)

    def test_mergeWith_invalid_pkeyMergeConstraint(self):
        l = self.TestUsersList(objlist=self.getObjList(start=1, stop=3))
        self.assertRaises(
            AttributeError, l.mergeWith, self.getObjList(start=1, stop=3), "invalid"
        )

    def test_mergeWith_noConstraint(self):
        l = self.TestUsersList(objlist=self.getObjList(start=1, stop=6))
        other = self.getObjList(start=3, stop=8)
        other[1].login = "user_4_new"
        other[2].login = "user_5_new"
        res = l.mergeWith(other, "noConstraint", dontMergeOnConflict=False)
        self.assertSetEqual(res, set())
        self.assertSetEqual(l.mergeConflicts, set())
        self.assertSetEqual(l.getPKeys(), set([1, 2, 3, 4, 5, 6, 7, 8]))

    def test_mergeWith_noConstraint_mergeconflict(self):
        l = self.TestUsersList(objlist=self.getObjList(start=1, stop=6))
        other = self.getObjList(start=3, stop=8)
        other[1].login = "user_4_new"
        other[2].login = "user_5_new"
        res = l.mergeWith(other, "noConstraint", dontMergeOnConflict=True)
        self.assertSetEqual(res, set())
        self.assertSetEqual(l.mergeConflicts, set([4, 5]))
        self.assertSetEqual(l.getPKeys(), set([1, 2, 3, 6, 7, 8]))

    def test_mergeWith_mustNotExist(self):
        l = self.TestUsersList(objlist=self.getObjList(start=1, stop=6))
        other = self.getObjList(start=3, stop=8)
        other[1].login = "user_4_new"
        other[2].login = "user_5_new"
        res = l.mergeWith(other, "mustNotExist", dontMergeOnConflict=False)
        self.assertSetEqual(res, set([3, 4, 5, 6]))
        self.assertSetEqual(l.mergeConflicts, set())
        self.assertSetEqual(l.getPKeys(), set([1, 2, 7, 8]))

    def test_mergeWith_mustNotExist_mergeconflict(self):
        l = self.TestUsersList(objlist=self.getObjList(start=1, stop=6))
        other = self.getObjList(start=3, stop=8)
        other[1].login = "user_4_new"
        other[2].login = "user_5_new"
        res = l.mergeWith(other, "mustNotExist", dontMergeOnConflict=True)
        self.assertSetEqual(res, set([3, 4, 5, 6]))
        self.assertSetEqual(l.mergeConflicts, set([]))
        self.assertSetEqual(l.getPKeys(), set([1, 2, 7, 8]))

    def test_mergeWith_mustAlreadyExist(self):
        l = self.TestUsersList(objlist=self.getObjList(start=1, stop=6))
        other = self.getObjList(start=3, stop=8)
        other[1].login = "user_4_new"
        other[2].login = "user_5_new"
        res = l.mergeWith(other, "mustAlreadyExist", dontMergeOnConflict=False)
        self.assertSetEqual(res, set([7, 8]))
        self.assertSetEqual(l.mergeConflicts, set())
        self.assertSetEqual(l.getPKeys(), set([1, 2, 3, 4, 5, 6]))

    def test_mergeWith_mustAlreadyExist_mergeconflict(self):
        l = self.TestUsersList(objlist=self.getObjList(start=1, stop=6))
        other = self.getObjList(start=3, stop=8)
        other[1].login = "user_4_new"
        other[2].login = "user_5_new"
        res = l.mergeWith(other, "mustAlreadyExist", dontMergeOnConflict=True)
        self.assertSetEqual(res, set([7, 8]))
        self.assertSetEqual(l.mergeConflicts, set([4, 5]))
        self.assertSetEqual(l.getPKeys(), set([1, 2, 3, 6]))

    def test_mergeWith_mustExistInBoth(self):
        l = self.TestUsersList(objlist=self.getObjList(start=1, stop=6))
        other = self.getObjList(start=3, stop=8)
        other[1].login = "user_4_new"
        other[2].login = "user_5_new"
        res = l.mergeWith(other, "mustExistInBoth", dontMergeOnConflict=False)
        self.assertSetEqual(res, set([1, 2, 7, 8]))
        self.assertSetEqual(l.mergeConflicts, set())
        self.assertSetEqual(l.getPKeys(), set([3, 4, 5, 6]))

    def test_mergeWith_mustExistInBoth_mergeconflict(self):
        l = self.TestUsersList(objlist=self.getObjList(start=1, stop=6))
        other = self.getObjList(start=3, stop=8)
        other[1].login = "user_4_new"
        other[2].login = "user_5_new"
        res = l.mergeWith(other, "mustExistInBoth", dontMergeOnConflict=True)
        self.assertSetEqual(res, set([1, 2, 7, 8]))
        self.assertSetEqual(l.mergeConflicts, set([4, 5]))
        self.assertSetEqual(l.getPKeys(), set([3, 6]))

    def test_diffFrom(self):
        lst_prev = self.getObjList(start=1, stop=6)
        l_prev = self.TestUsersList(objlist=lst_prev)

        lst_new = self.getObjList(start=3, stop=8)

        # Modify obj with pkey=4
        lst_new[1].login = "user_4_new"  # Modify login
        delattr(lst_new[1], "edupersonaffiliation")  # Remove edupersonaffiliation
        lst_new[1].newattr = "user_4_newattr"  # Add newattr

        l_new = self.TestUsersList(objlist=lst_new)
        diff = l_new.diffFrom(l_prev)

        expected = {
            "added": [l_new[7], l_new[8]],
            "modified": [
                {
                    "added": {"newattr": "user_4_newattr"},
                    "modified": {"login": "user_4_new"},
                    "removed": {"edupersonaffiliation": None},
                },
            ],
            "removed": [l_prev[1], l_prev[2]],
        }
        diff_modified_dicts = [d.dict for d in diff.dict["modified"]]

        self.assertListEqual(diff.dict["added"], expected["added"])
        self.assertListEqual(diff.dict["removed"], expected["removed"])
        self.assertListEqual(diff_modified_dicts, expected["modified"])

    def test_replaceInconsistenciesByCachedValues(self):
        lst_prev = self.getObjList(start=1, stop=6)

        lst_new = self.getObjList(start=1, stop=8)
        lst_new[3].login = "user_4_new"  # Modify login of obj with pkey=4
        lst_new[4].login = "user_5_new"  # Modify login of obj with pkey=5
        l_new = self.TestUsersList(objlist=lst_new)

        res = l_new.mergeWith(lst_prev, "noConstraint", dontMergeOnConflict=True)

        # Generate cache with another login
        lst_cache = self.getObjList(start=1, stop=4)
        for obj in lst_cache:
            obj.login += "_cache"
        l_cache = self.TestUsersList(objlist=lst_cache)

        self.assertSetEqual(res, set())
        self.assertSetEqual(l_new.mergeConflicts, set([4, 5]))
        self.assertSetEqual(l_new.getPKeys(), set([1, 2, 3, 6, 7, 8]))

        l_new.replaceInconsistenciesByCachedValues(l_cache)

        self.assertSetEqual(l_new.getPKeys(), set([1, 2, 3, 4, 6, 7, 8]))
        self.assertEqual(l_new[3].login, "user_3")
        self.assertEqual(l_new[4].login, "user_4_cache")
