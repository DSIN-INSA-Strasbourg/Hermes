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


from datetime import datetime
import os.path

from .hermestestcase import HermesServerTestCase
from lib.datamodel.serialization import (
    JSONSerializable,
    LocalCache,
    HermesInvalidJSONError,
    HermesInvalidJSONDataError,
    HermesInvalidJSONDataattrTypeError,
    HermesInvalidCacheDirError,
    HermesUnspecifiedCacheFilename,
)

import logging


class TestJSONEncoderClass(HermesServerTestCase):
    dict = {
        "single1": "val1",
        "list2": ["val21", 22, True, None],
        "dict3": {
            "key31": "val31",
            "key32": 32,
            "key33": False,
            "key34": None,
            "date1": datetime(2023, 6, 20, 8, 42, 1),
        },
    }
    json = "\n".join(
        (
            "{",
            '    "single1": "val1",',
            '    "list2": [',
            '        "val21",',
            "        22,",
            "        true,",
            "        null",
            "    ],",
            '    "dict3": {',
            '        "key31": "val31",',
            '        "key32": 32,',
            '        "key33": false,',
            '        "key34": null,',
            '        "date1": "HermesDatetime(2023-06-20T08:42:01Z)"',
            "    }",
            "}",
        ),
    )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        logging.disable(logging.NOTSET)
        confdata = cls.loadYaml()
        config = cls.saveYamlAndLoadConfig(confdata)

        class SerializationObjByAttrs(JSONSerializable):
            def __init__(self, from_json_dict=None, from_raw_dict=None):
                super().__init__(jsondataattr=list(cls.dict.keys()))

                if from_raw_dict is not None:
                    for k, v in from_raw_dict.items():
                        setattr(self, k, v)
                elif from_json_dict is not None:
                    for k, v in from_json_dict.items():
                        setattr(self, k, v)

        class SerializationObjByDict(JSONSerializable):
            def __init__(self, from_json_dict=None, from_raw_dict=None):
                super().__init__(jsondataattr="attrs")

                if from_raw_dict is not None:
                    self.attrs = from_raw_dict
                elif from_json_dict is not None:
                    self.attrs = from_json_dict

        cls.SerializationObjByAttrs = SerializationObjByAttrs
        cls.SerializationObjByDict = SerializationObjByDict

    def test_tojson_fromrawdict(self):
        o = self.SerializationObjByAttrs(from_raw_dict=TestJSONEncoderClass.dict)
        self.assertEqual(o.to_json(), TestJSONEncoderClass.json)
        o = self.SerializationObjByDict(from_raw_dict=TestJSONEncoderClass.dict)
        self.assertEqual(o.to_json(), TestJSONEncoderClass.json)

    def test_tojson_fromrawdict_withJSONSerializableInstances(self):
        o1 = self.SerializationObjByAttrs.from_json(jsondata=TestJSONEncoderClass.dict)
        o2 = self.SerializationObjByAttrs.from_json(jsondata=TestJSONEncoderClass.dict)

        ### SerializationObjByAttrs
        # Build a new obj merging two test objs
        dict = {"obj1": o1, "obj2": o2}
        o = self.SerializationObjByAttrs.from_json(dict)
        o._jsondataattr = ("obj1", "obj2")  # Update attr for this new object type

        # Build the awaited json str
        nl = "\n"  # Newline var for f-string
        splitted = TestJSONEncoderClass.json.split("\n")
        reindented = "\n    ".join(splitted)
        json = f"""{{{nl}    "obj1": {reindented},{nl}    "obj2": {reindented}{nl}}}"""
        self.assertEqual(o.to_json(), json)

        ### SerializationObjByDict
        # Build a new obj merging two test objs
        dict = {"obj1": o1, "obj2": o2}
        o = self.SerializationObjByDict.from_json(dict)

        # Build the awaited json str
        nl = "\n"  # Newline var for f-string
        splitted = TestJSONEncoderClass.json.split("\n")
        reindented = "\n    ".join(splitted)
        json = f"""{{{nl}    "obj1": {reindented},{nl}    "obj2": {reindented}{nl}}}"""
        self.assertEqual(o.to_json(), json)

    def test_tojson_fromjsondict(self):
        o = self.SerializationObjByAttrs.from_json(jsondata=TestJSONEncoderClass.dict)
        self.assertEqual(o.to_json(), TestJSONEncoderClass.json)

        o = self.SerializationObjByDict.from_json(jsondata=TestJSONEncoderClass.dict)
        self.assertEqual(o.to_json(), TestJSONEncoderClass.json)

    def test_fromjson_fromjsonstr(self):
        o = self.SerializationObjByAttrs.from_json(jsondata=TestJSONEncoderClass.json)
        self.assertEqual(o.to_json(), TestJSONEncoderClass.json)

        o = self.SerializationObjByDict.from_json(jsondata=TestJSONEncoderClass.json)
        self.assertEqual(o.to_json(), TestJSONEncoderClass.json)

    def test_tojson_then_fromjson(self):
        o1 = self.SerializationObjByAttrs(from_raw_dict=TestJSONEncoderClass.dict)
        o2 = self.SerializationObjByAttrs.from_json(o1.to_json())
        for k, v in TestJSONEncoderClass.dict.items():
            if type(v) == list:
                self.assertListEqual(getattr(o1, k), getattr(o2, k))
            elif type(v) == dict:
                self.assertDictEqual(getattr(o1, k), getattr(o2, k))
            else:
                self.assertEqual(getattr(o1, k), getattr(o2, k))

        o1 = self.SerializationObjByDict(from_raw_dict=TestJSONEncoderClass.dict)
        o2 = self.SerializationObjByDict.from_json(o1.to_json())
        self.assertDictEqual(o1.attrs, o2.attrs)

    def test_fromjson_with_invalidjson(self):
        self.assertRaises(
            HermesInvalidJSONError,
            self.SerializationObjByAttrs.from_json,
            jsondata=TestJSONEncoderClass.json[1:],
        )
        self.assertRaises(
            HermesInvalidJSONError,
            self.SerializationObjByAttrs.from_json,
            jsondata=TestJSONEncoderClass.json[:-1],
        )

    def test_fromjson_with_invalidtype(self):
        self.assertRaisesRegex(
            HermesInvalidJSONDataError,
            "The 'jsondata' arg must be a str or a dict. Here we have '<class 'int'>'",
            self.SerializationObjByAttrs.from_json,
            jsondata=1,
        )
        self.assertRaisesRegex(
            HermesInvalidJSONDataError,
            "The 'jsondata' arg must be a str or a dict. Here we have '<class 'list'>'",
            self.SerializationObjByAttrs.from_json,
            jsondata=["str"],
        )

    def test_tojson_withunsortable(self):
        class SerializationObj2(JSONSerializable):
            def __init__(self, from_json_dict=None):
                super().__init__(jsondataattr="attrs")
                if from_json_dict is not None:
                    self.attrs = from_json_dict
                else:
                    self.attrs = 1

        o = SerializationObj2()
        with self.assertLogs(__hermes__.logger, level="WARNING") as cm:
            o.to_json()
        self.assertEqual(
            cm.output,
            [
                "WARNING:hermes-unit-tests:Unsortable type <class 'unit.test_lib_datamodel_serialization.TestJSONEncoderClass.test_tojson_withunsortable.<locals>.SerializationObj2'> exported as JSON. You should consider to set is sortable"
            ],
        )

    def test_tojson_with_invalidtype(self):
        class Unserializable:
            def __init__(self):
                pass

        dict = {"obj": Unserializable()}
        o = self.SerializationObjByDict(from_raw_dict=dict)
        self.assertRaisesRegex(
            TypeError,
            "Object of type Unserializable is not JSON serializable",
            o.to_json,
        )

    def test_invalid_jsondataattrtype(self):
        class InvalidSerializationObj(JSONSerializable):
            def __init__(self, from_json_dict=None, from_raw_dict=None):
                super().__init__(jsondataattr=1)

        self.assertRaisesRegex(
            HermesInvalidJSONDataattrTypeError,
            "Invalid jsondataattr type '<class 'int'>'. It must be one of the following types: \\[str, list, tuple, set\\]",
            InvalidSerializationObj,
        )

        class InvalidSerializationObj2(JSONSerializable):
            def __init__(self, from_json_dict=None, from_raw_dict=None):
                super().__init__(jsondataattr={"attr1": "val1"})

        self.assertRaisesRegex(
            HermesInvalidJSONDataattrTypeError,
            "Invalid jsondataattr type '<class 'dict'>'. It must be one of the following types: \\[str, list, tuple, set\\]",
            InvalidSerializationObj2,
        )

        class InvalidSerializationObj3(JSONSerializable):
            def __init__(self, from_json_dict=None, from_raw_dict=None):
                super().__init__(jsondataattr="attr1")

        obj = InvalidSerializationObj3()
        obj._jsondataattr = 1

        self.assertRaisesRegex(
            HermesInvalidJSONDataattrTypeError,
            "Invalid _jsondataattr type '<class 'int'>'. It must be one of the following types: \\[str, list, tuple, set\\]",
            obj.to_json,
        )


class TestLocalCacheClass(HermesServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        logging.disable(logging.NOTSET)

        class SerializationObj(LocalCache):
            def __init__(self, from_json_dict=None, from_raw_dict=None):
                super().__init__(
                    jsondataattr="attrs", cachefilename="testserialization"
                )

                if from_raw_dict is not None:
                    self.attrs = from_raw_dict
                elif from_json_dict is not None:
                    self.attrs = from_json_dict

        cls.SerializationObj = SerializationObj

        class SerializationObjNoCacheFilename(LocalCache):
            def __init__(self, from_json_dict=None, from_raw_dict=None):
                super().__init__(jsondataattr="attrs")

                if from_raw_dict is not None:
                    self.attrs = from_raw_dict
                elif from_json_dict is not None:
                    self.attrs = from_json_dict

        cls.SerializationObj = SerializationObj
        cls.SerializationObjNoCacheFilename = SerializationObjNoCacheFilename

    def setUp(self):
        super().setUp()
        confdata = self.loadYaml()
        self.config = self.saveYamlAndLoadConfig(confdata)

    def tearDown(self):
        super().tearDown()
        self.purgeTmpdirContent()

    def test_reloadcachefile(self):
        o1 = self.SerializationObj(from_raw_dict=TestJSONEncoderClass.dict)
        o1.savecachefile()
        o2 = self.SerializationObj.loadcachefile("testserialization")
        self.assertDictEqual(o1.attrs, o2.attrs)

    def test_savecachefile_withspecified_cacheFilename(self):
        o1 = self.SerializationObjNoCacheFilename(
            from_raw_dict=TestJSONEncoderClass.dict
        )
        o1.savecachefile("testserialization_customname")
        o2 = self.SerializationObjNoCacheFilename.loadcachefile(
            "testserialization_customname"
        )
        self.assertDictEqual(o1.attrs, o2.attrs)

    def test_savecachefile_without_cacheFilename(self):
        o1 = self.SerializationObjNoCacheFilename(
            from_raw_dict=TestJSONEncoderClass.dict
        )
        self.assertRaisesRegex(
            HermesUnspecifiedCacheFilename,
            r"Unable to save cache file without having specified the cacheFilename with setCacheFilename\(\)",
            o1.savecachefile,
        )

    def test_savecachefile_twice(self):
        # Test rotation
        o1 = self.SerializationObj(from_raw_dict=TestJSONEncoderClass.dict)
        o1.savecachefile()
        self.assertTrue(
            os.path.isfile(f"{self.tmpdir.name}/testserialization.json.gz"),
            "Main cache file not found",
        )
        self.assertFalse(
            os.path.isfile(f"{self.tmpdir.name}/testserialization.000001.json.gz"),
            "First rotated cache file was found",
        )

        o1.savecachefile()  # no change, should do nothing
        self.assertTrue(
            os.path.isfile(f"{self.tmpdir.name}/testserialization.json.gz"),
            "Main cache file not found",
        )
        self.assertFalse(
            os.path.isfile(f"{self.tmpdir.name}/testserialization.000001.json.gz"),
            "First rotated cache file was found",
        )

        o1.attrs["single1"] = "newval1"
        o1.savecachefile()  # data has changed, should rotate
        self.assertTrue(
            os.path.isfile(f"{self.tmpdir.name}/testserialization.json.gz"),
            "Main cache file not found",
        )
        self.assertTrue(
            os.path.isfile(f"{self.tmpdir.name}/testserialization.000001.json.gz"),
            "First rotated cache file not found",
        )

    def test_load_compressed_with_compression_disabled(self):
        self.config["hermes"]["cache"]["enable_compression"] = True
        LocalCache.setup(self.config)

        o1 = self.SerializationObj(from_raw_dict=TestJSONEncoderClass.dict)
        o1.savecachefile()

        self.config["hermes"]["cache"]["enable_compression"] = False
        LocalCache.setup(self.config)

        o2 = self.SerializationObj.loadcachefile("testserialization")
        self.assertDictEqual(o1.attrs, o2.attrs)

    def test_load_uncompressed_with_compression_enabled(self):
        self.config["hermes"]["cache"]["enable_compression"] = False
        LocalCache.setup(self.config)
        o1 = self.SerializationObj(from_raw_dict=TestJSONEncoderClass.dict)
        o1.savecachefile()

        self.config["hermes"]["cache"]["enable_compression"] = True
        LocalCache.setup(self.config)

        o2 = self.SerializationObj.loadcachefile("testserialization")
        self.assertDictEqual(o1.attrs, o2.attrs)

    def test_loadcachefile_unexistent(self):
        with self.assertLogs(__hermes__.logger, level="INFO") as cm:
            o = self.SerializationObj.loadcachefile("testserialization")

        self.assertDictEqual(o.attrs, dict())
        self.assertEqual(len(cm.output), 1)
        self.assertRegex(
            cm.output[0],
            "INFO:hermes-unit-tests:Specified cache file '.+' doesn't exists, returning empty data",
        )

    def test_createcachedir(self):
        LocalCache._settingsbyappname[__hermes__.appname]["_cachedir"] += "/hermes-test"
        with self.assertLogs(__hermes__.logger, level="INFO") as cm:
            o = self.SerializationObj(from_raw_dict=TestJSONEncoderClass.dict)

        self.assertRegex(
            cm.output[0],
            f"INFO:hermes-unit-tests:Local cache dir '{LocalCache._cachedir()}' doesn't exists: create it",
        )

    def test_unabletocreatecachedir(self):
        LocalCache._settingsbyappname[__hermes__.appname][
            "_cachedir"
        ] = "/sbin/hermes-test"
        with self.assertLogs(__hermes__.logger, level="FATAL"):
            self.assertRaisesRegex(
                PermissionError,
                "\\[Errno 13\\] Permission denied: '/sbin/hermes-test'",
                self.SerializationObj,
                from_raw_dict=TestJSONEncoderClass.dict,
            )

    def test_invalidcachedir_isfile(self):
        LocalCache._settingsbyappname[__hermes__.appname]["_cachedir"] = "/dev/null"
        with self.assertLogs(__hermes__.logger, level="FATAL"):
            self.assertRaisesRegex(
                HermesInvalidCacheDirError,
                "Local cache dir '/dev/null' exists and is not a directory",
                self.SerializationObj,
                from_raw_dict=TestJSONEncoderClass.dict,
            )

    def test_invalidcachedir_nowriteaccess(self):
        LocalCache._settingsbyappname[__hermes__.appname]["_cachedir"] = "/sbin"
        with self.assertLogs(__hermes__.logger, level="FATAL"):
            self.assertRaisesRegex(
                HermesInvalidCacheDirError,
                "Local cache dir '/sbin' exists but is not writeable",
                self.SerializationObj,
                from_raw_dict=TestJSONEncoderClass.dict,
            )
