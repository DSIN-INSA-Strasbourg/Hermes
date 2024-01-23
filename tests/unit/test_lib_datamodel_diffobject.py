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

from lib.datamodel.diffobject import DiffObject


class SampleObject:
    def __init__(self, name="SampleObject"):
        self.name = name

    def __repr__(self) -> str:
        return self.name


class TestDiffobjectClass(HermesServerTestCase):
    def setUpSamplePropertiesObjects(self):
        self.objold = SampleObject("objold")
        self.objold.prop1 = "prop1_value"
        self.objold.prop2 = "prop2_value"
        self.objold.prop3 = "prop3_value"

        self.objnew = SampleObject("objnew")
        self.objnew.prop1 = "prop1_value"
        self.objnew.prop2 = "other_prop2_value"
        self.objnew.prop4 = "prop4_value"
        self.objnew.prop5 = "prop5_value"

        self.diff = DiffObject(objnew=self.objnew, objold=self.objold)
        self.diff.appendAdded(["prop5", "prop4"])  # Not in order to test sorting
        self.diff.appendModified("prop2")
        self.diff.appendRemoved("prop3")

    def test_objproperties_added(self):
        self.setUpSamplePropertiesObjects()
        self.assertListEqual(self.diff.added, ["prop4", "prop5"])

    def test_objproperties_modified(self):
        self.setUpSamplePropertiesObjects()
        self.assertListEqual(self.diff.modified, ["prop2"])

    def test_objproperties_removed(self):
        self.setUpSamplePropertiesObjects()
        self.assertListEqual(self.diff.removed, ["prop3"])

    def test_objproperties_dict(self):
        self.setUpSamplePropertiesObjects()
        awaited = {
            "added": {"prop4": "prop4_value", "prop5": "prop5_value"},
            "modified": {"prop2": "other_prop2_value"},
            "removed": {"prop3": None},
        }
        self.assertDictEqual(self.diff.dict, awaited)

    def test_objproperties_bool(self):
        self.setUpSamplePropertiesObjects()
        emptyDiff = DiffObject(objnew=self.objnew, objold=self.objold)
        self.assertFalse(emptyDiff)
        self.assertTrue(self.diff)

    ##################################################

    def setUpSampleRawObjects(self):
        self.raw1 = SampleObject("raw1")
        self.raw2 = SampleObject("raw2")
        self.raw3 = SampleObject("raw3")
        self.raw4 = SampleObject("raw4")
        self.raw5 = SampleObject("raw5")
        self.raw6 = SampleObject("raw6")
        self.raw7 = SampleObject("raw7")

        self.rawold = [self.raw1, self.raw2, self.raw3, self.raw4, self.raw5]
        self.rawnew = [self.raw1, self.raw2, self.raw3, self.raw6, self.raw7]
        self.diff = DiffObject()
        self.diff.appendAdded([self.raw7, self.raw6])
        self.diff.appendModified([self.raw2, self.raw3])
        self.diff.appendRemoved(self.raw4)
        self.diff.appendRemoved(self.raw5)

    def test_rawobj_added(self):
        self.setUpSampleRawObjects()
        self.assertSetEqual(self.diff.added, set([self.raw7, self.raw6]))

    def test_rawobj_modified(self):
        self.setUpSampleRawObjects()
        self.assertSetEqual(self.diff.modified, set([self.raw2, self.raw3]))

    def test_rawobj_removed(self):
        self.setUpSampleRawObjects()
        self.assertSetEqual(self.diff.removed, set([self.raw4, self.raw5]))

    def test_rawobj_dict(self):
        self.setUpSampleRawObjects()
        awaited = {
            "added": set([self.raw7, self.raw6]),
            "modified": set([self.raw2, self.raw3]),
            "removed": set([self.raw4, self.raw5]),
        }
        self.assertDictEqual(self.diff.dict, awaited)

    def test_rawobj_bool(self):
        self.setUpSampleRawObjects()
        emptyDiff = DiffObject()
        self.assertFalse(emptyDiff)
        self.assertTrue(self.diff)
