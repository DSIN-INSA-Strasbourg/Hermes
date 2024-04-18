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
from clients.errorqueue import ErrorQueue, HermesInvalidErrorQueueJSONError
from lib.datamodel.dataobject import DataObject
from lib.datamodel.event import Event

import logging


class TestErrorQueueClass(HermesServerTestCase):
    typesMapping = {"TestObj1": "TestObj1_local", "TestObj2": "TestObj2_local"}

    queue = {
        "1": [
            {
                "evcategory": "initsync",
                "eventtype": "added",
                "objtype": "TestObj1",
                "objpkey": 101,
                "objattrs": {
                    "obj_id": 101,
                    "name": "Object1_01",
                    "description": "Test Object1 01",
                },
                "step": 0,
            },
            {
                "evcategory": "initsync",
                "eventtype": "added",
                "objtype": "TestObj1_local",
                "objpkey": 101,
                "objattrs": {
                    "obj_id": 101,
                    "name": "Object1_01",
                    "description": "Test Object1 01",
                },
                "step": 0,
            },
            "Fake error message",
        ],
        "2": [
            {
                "evcategory": "initsync",
                "eventtype": "added",
                "objtype": "TestObj2",
                "objpkey": 201,
                "objattrs": {
                    "obj_id": 201,
                    "name": "Object2_01",
                    "description": "Test Object2 01",
                },
                "step": 0,
            },
            {
                "evcategory": "initsync",
                "eventtype": "added",
                "objtype": "TestObj2_local",
                "objpkey": 201,
                "objattrs": {
                    "obj_id": 201,
                    "name": "Object2_01",
                    "description": "Test Object2 01",
                },
                "step": 0,
            },
            "Fake error message",
        ],
        "3": [
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1",
                "objpkey": 101,
                "objattrs": {
                    "added": {"new_attr1": "new_attr1_value"},
                    "modified": {"name": "Object1_01_modified"},
                    "removed": {"description": None},
                },
                "step": 0,
            },
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1_local",
                "objpkey": 101,
                "objattrs": {
                    "added": {"new_attr1": "new_attr1_value"},
                    "modified": {"name": "Object1_01_modified"},
                    "removed": {"description": None},
                },
                "step": 0,
            },
            "Fake error message",
        ],
        "4": [
            None,
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj2_local",
                "objpkey": 201,
                "objattrs": {
                    "added": {"new_attr1": "new_attr1_value"},
                    "modified": {"name": "Object2_02_modified"},
                    "removed": {"description": None},
                },
                "step": 0,
            },
            "Fake error message",
        ],
        "5": [
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1",
                "objpkey": 101,
                "objattrs": {
                    "added": {
                        "new_attr2": "new_attr2_value",
                        "description": "Test Object2 01 modified",
                    },
                    "modified": {"name": "Object1_01_modified_again"},
                    "removed": {"new_attr1": None},
                },
                "step": 0,
            },
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1_local",
                "objpkey": 101,
                "objattrs": {
                    "added": {
                        "new_attr2": "new_attr2_value",
                        "description": "Test Object2 01 modified",
                    },
                    "modified": {"name": "Object1_01_modified_again"},
                    "removed": {"new_attr1": None},
                },
                "step": 0,
            },
            "Fake error message",
        ],
        "6": [
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1",
                "objpkey": 103,
                "objattrs": {
                    "added": {
                        "new_attr1": "new_attr1_value",
                        "new_attr2": "new_attr2_value",
                    },
                    "modified": {"name": "Object1_03_modified"},
                    "removed": {"description": None},
                },
                "step": 0,
            },
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1_local",
                "objpkey": 103,
                "objattrs": {
                    "added": {
                        "new_attr1": "new_attr1_value",
                        "new_attr2": "new_attr2_value",
                    },
                    "modified": {"name": "Object1_03_modified"},
                    "removed": {"description": None},
                },
                "step": 0,
            },
            "Fake error message",
        ],
        "7": [
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1",
                "objpkey": 103,
                "objattrs": {
                    "added": {"new_attr3": "new_attr3_value"},
                    "modified": {
                        "name": "Object1_03_modified_again",
                        "new_attr2": "new_attr2_value_modified",
                    },
                    "removed": {"new_attr1": None},
                },
                "step": 0,
            },
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1_local",
                "objpkey": 103,
                "objattrs": {
                    "added": {"new_attr3": "new_attr3_value"},
                    "modified": {
                        "name": "Object1_03_modified_again",
                        "new_attr2": "new_attr2_value_modified",
                    },
                    "removed": {"new_attr1": None},
                },
                "step": 0,
            },
            "Fake error message",
        ],
        "8": [
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj2",
                "objpkey": 201,
                "objattrs": {
                    "added": {"new_attr2": "new_attr2_value"},
                    "modified": {"name": "Object2_01_modified_again"},
                    "removed": {},
                },
                "step": 0,
            },
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj2_local",
                "objpkey": 201,
                "objattrs": {
                    "added": {"new_attr2": "new_attr2_value"},
                    "modified": {"name": "Object2_01_modified_again"},
                    "removed": {},
                },
                "step": 0,
            },
            "Fake error message",
        ],
    }

    queuejson = """{
    "_queue": {
        "1": [
            {
                "evcategory": "initsync",
                "eventtype": "added",
                "objtype": "TestObj1",
                "objpkey": 101,
                "objattrs": {
                    "obj_id": 101,
                    "name": "Object1_01",
                    "description": "Test Object1 01"
                },
                "step": 0
            },
            {
                "evcategory": "initsync",
                "eventtype": "added",
                "objtype": "TestObj1_local",
                "objpkey": 101,
                "objattrs": {
                    "obj_id": 101,
                    "name": "Object1_01",
                    "description": "Test Object1 01"
                },
                "step": 0
            },
            "Fake error message"
        ],
        "2": [
            {
                "evcategory": "initsync",
                "eventtype": "added",
                "objtype": "TestObj2",
                "objpkey": 201,
                "objattrs": {
                    "obj_id": 201,
                    "name": "Object2_01",
                    "description": "Test Object2 01"
                },
                "step": 0
            },
            {
                "evcategory": "initsync",
                "eventtype": "added",
                "objtype": "TestObj2_local",
                "objpkey": 201,
                "objattrs": {
                    "obj_id": 201,
                    "name": "Object2_01",
                    "description": "Test Object2 01"
                },
                "step": 0
            },
            "Fake error message"
        ],
        "3": [
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1",
                "objpkey": 101,
                "objattrs": {
                    "added": {
                        "new_attr1": "new_attr1_value"
                    },
                    "modified": {
                        "name": "Object1_01_modified"
                    },
                    "removed": {
                        "description": null
                    }
                },
                "step": 0
            },
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1_local",
                "objpkey": 101,
                "objattrs": {
                    "added": {
                        "new_attr1": "new_attr1_value"
                    },
                    "modified": {
                        "name": "Object1_01_modified"
                    },
                    "removed": {
                        "description": null
                    }
                },
                "step": 0
            },
            "Fake error message"
        ],
        "4": [
            null,
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj2_local",
                "objpkey": 201,
                "objattrs": {
                    "added": {
                        "new_attr1": "new_attr1_value"
                    },
                    "modified": {
                        "name": "Object2_02_modified"
                    },
                    "removed": {
                        "description": null
                    }
                },
                "step": 0
            },
            "Fake error message"
        ],
        "5": [
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1",
                "objpkey": 101,
                "objattrs": {
                    "added": {
                        "new_attr2": "new_attr2_value",
                        "description": "Test Object2 01 modified"
                    },
                    "modified": {
                        "name": "Object1_01_modified_again"
                    },
                    "removed": {
                        "new_attr1": null
                    }
                },
                "step": 0
            },
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1_local",
                "objpkey": 101,
                "objattrs": {
                    "added": {
                        "new_attr2": "new_attr2_value",
                        "description": "Test Object2 01 modified"
                    },
                    "modified": {
                        "name": "Object1_01_modified_again"
                    },
                    "removed": {
                        "new_attr1": null
                    }
                },
                "step": 0
            },
            "Fake error message"
        ],
        "6": [
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1",
                "objpkey": 103,
                "objattrs": {
                    "added": {
                        "new_attr1": "new_attr1_value",
                        "new_attr2": "new_attr2_value"
                    },
                    "modified": {
                        "name": "Object1_03_modified"
                    },
                    "removed": {
                        "description": null
                    }
                },
                "step": 0
            },
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1_local",
                "objpkey": 103,
                "objattrs": {
                    "added": {
                        "new_attr1": "new_attr1_value",
                        "new_attr2": "new_attr2_value"
                    },
                    "modified": {
                        "name": "Object1_03_modified"
                    },
                    "removed": {
                        "description": null
                    }
                },
                "step": 0
            },
            "Fake error message"
        ],
        "7": [
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1",
                "objpkey": 103,
                "objattrs": {
                    "added": {
                        "new_attr3": "new_attr3_value"
                    },
                    "modified": {
                        "name": "Object1_03_modified_again",
                        "new_attr2": "new_attr2_value_modified"
                    },
                    "removed": {
                        "new_attr1": null
                    }
                },
                "step": 0
            },
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1_local",
                "objpkey": 103,
                "objattrs": {
                    "added": {
                        "new_attr3": "new_attr3_value"
                    },
                    "modified": {
                        "name": "Object1_03_modified_again",
                        "new_attr2": "new_attr2_value_modified"
                    },
                    "removed": {
                        "new_attr1": null
                    }
                },
                "step": 0
            },
            "Fake error message"
        ],
        "8": [
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj2",
                "objpkey": 201,
                "objattrs": {
                    "added": {
                        "new_attr2": "new_attr2_value"
                    },
                    "modified": {
                        "name": "Object2_01_modified_again"
                    },
                    "removed": {}
                },
                "step": 0
            },
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj2_local",
                "objpkey": 201,
                "objattrs": {
                    "added": {
                        "new_attr2": "new_attr2_value"
                    },
                    "modified": {
                        "name": "Object2_01_modified_again"
                    },
                    "removed": {}
                },
                "step": 0
            },
            "Fake error message"
        ]
    }
}"""

    queueremediatedjson = """{
    "_queue": {
        "1": [
            {
                "evcategory": "initsync",
                "eventtype": "added",
                "objtype": "TestObj1",
                "objpkey": 101,
                "objattrs": {
                    "obj_id": 101,
                    "name": "Object1_01_modified_again",
                    "new_attr2": "new_attr2_value",
                    "description": "Test Object2 01 modified"
                },
                "step": 0
            },
            {
                "evcategory": "initsync",
                "eventtype": "added",
                "objtype": "TestObj1_local",
                "objpkey": 101,
                "objattrs": {
                    "obj_id": 101,
                    "name": "Object1_01_modified_again",
                    "new_attr2": "new_attr2_value",
                    "description": "Test Object2 01 modified"
                },
                "step": 0
            },
            "Fake error message"
        ],
        "2": [
            {
                "evcategory": "initsync",
                "eventtype": "added",
                "objtype": "TestObj2",
                "objpkey": 201,
                "objattrs": {
                    "obj_id": 201,
                    "name": "Object2_01_modified_again",
                    "description": "Test Object2 01",
                    "new_attr2": "new_attr2_value"
                },
                "step": 0
            },
            {
                "evcategory": "initsync",
                "eventtype": "added",
                "objtype": "TestObj2_local",
                "objpkey": 201,
                "objattrs": {
                    "obj_id": 201,
                    "name": "Object2_01_modified_again",
                    "new_attr1": "new_attr1_value",
                    "new_attr2": "new_attr2_value"
                },
                "step": 0
            },
            "Fake error message"
        ],
        "3": [
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1",
                "objpkey": 103,
                "objattrs": {
                    "added": {
                        "new_attr2": "new_attr2_value_modified",
                        "new_attr3": "new_attr3_value"
                    },
                    "modified": {
                        "name": "Object1_03_modified_again"
                    },
                    "removed": {
                        "description": null
                    }
                },
                "step": 0
            },
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1_local",
                "objpkey": 103,
                "objattrs": {
                    "added": {
                        "new_attr2": "new_attr2_value_modified",
                        "new_attr3": "new_attr3_value"
                    },
                    "modified": {
                        "name": "Object1_03_modified_again"
                    },
                    "removed": {
                        "description": null
                    }
                },
                "step": 0
            },
            "Fake error message"
        ]
    }
}"""

    queueremediatedatimportjson = """{
    "_queue": {
        "1": [
            {
                "evcategory": "initsync",
                "eventtype": "added",
                "objtype": "TestObj1",
                "objpkey": 101,
                "objattrs": {
                    "obj_id": 101,
                    "name": "Object1_01_modified_again",
                    "new_attr2": "new_attr2_value",
                    "description": "Test Object2 01 modified"
                },
                "step": 0
            },
            {
                "evcategory": "initsync",
                "eventtype": "added",
                "objtype": "TestObj1_local",
                "objpkey": 101,
                "objattrs": {
                    "obj_id": 101,
                    "name": "Object1_01_modified_again",
                    "new_attr2": "new_attr2_value",
                    "description": "Test Object2 01 modified"
                },
                "step": 0
            },
            "Fake error message"
        ],
        "2": [
            {
                "evcategory": "initsync",
                "eventtype": "added",
                "objtype": "TestObj2",
                "objpkey": 201,
                "objattrs": {
                    "obj_id": 201,
                    "name": "Object2_01_modified_again",
                    "description": "Test Object2 01",
                    "new_attr2": "new_attr2_value"
                },
                "step": 0
            },
            {
                "evcategory": "initsync",
                "eventtype": "added",
                "objtype": "TestObj2_local",
                "objpkey": 201,
                "objattrs": {
                    "obj_id": 201,
                    "name": "Object2_01_modified_again",
                    "new_attr1": "new_attr1_value",
                    "new_attr2": "new_attr2_value"
                },
                "step": 0
            },
            "Fake error message"
        ],
        "6": [
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1",
                "objpkey": 103,
                "objattrs": {
                    "added": {
                        "new_attr2": "new_attr2_value_modified",
                        "new_attr3": "new_attr3_value"
                    },
                    "modified": {
                        "name": "Object1_03_modified_again"
                    },
                    "removed": {
                        "description": null
                    }
                },
                "step": 0
            },
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1_local",
                "objpkey": 103,
                "objattrs": {
                    "added": {
                        "new_attr2": "new_attr2_value_modified",
                        "new_attr3": "new_attr3_value"
                    },
                    "modified": {
                        "name": "Object1_03_modified_again"
                    },
                    "removed": {
                        "description": null
                    }
                },
                "step": 0
            },
            "Fake error message"
        ]
    }
}"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        logging.disable(logging.NOTSET)

    def setUp(self):
        super().setUp()
        confdata = self.loadYaml()
        self.config = self.saveYamlAndLoadConfig(confdata)

        class TestObj1(DataObject):
            HERMES_ATTRIBUTES = set(
                [
                    "obj_id",
                    "name",
                    "description",
                    "new_attr1",
                    "new_attr2",
                    "new_attr3",
                ]
            )
            SECRETS_ATTRIBUTES = set()
            CACHEONLY_ATTRIBUTES = set()
            LOCAL_ATTRIBUTES = set()
            PRIMARYKEY_ATTRIBUTE = "obj_id"

            REMOTE_ATTRIBUTES = set(
                [
                    "OBJ_ID",
                    "NAME",
                    "DESCRIPTION",
                    "NEW_ATTR1",
                    "NEW_ATTR2",
                    "NEW_ATTR3",
                ]
            )
            HERMES_TO_REMOTE_MAPPING = {
                "obj_id": "OBJ_ID",
                "name": "NAME",
                "description": "DESCRIPTION",
                "new_attr1": "NEW_ATTR1",
                "new_attr2": "NEW_ATTR2",
                "new_attr3": "NEW_ATTR3",
            }

        self.TestObj1 = TestObj1

    def tearDown(self):
        super().tearDown()
        self.purgeTmpdirContent()

    def test_init(self):
        eq = ErrorQueue(typesMapping=self.typesMapping, autoremediate=False)
        self.assertEqual(len(eq), 0)

    def test_init_from_invalid_json(self):
        self.assertRaises(
            HermesInvalidErrorQueueJSONError,
            ErrorQueue,
            typesMapping=self.typesMapping,
            autoremediate=False,
            from_json_dict={"queue": self.queue},  # key should be "_queue"
        )

    def test_init_from_invalid_json(self):
        self.assertRaises(
            HermesInvalidErrorQueueJSONError,
            ErrorQueue,
            typesMapping=self.typesMapping,
            autoremediate=False,
            from_json_dict={"queue": self.queue},  # key should be "_queue"
        )

    def test_fill_queue_twice_with_same_eventnumber(self):
        eq = ErrorQueue(typesMapping=self.typesMapping, autoremediate=False)

        evremotejson, evlocaljson, errmsg = self.queue["1"]
        evremote = None if evremotejson is None else Event(from_json_dict=evremotejson)
        evlocal = Event(from_json_dict=evlocaljson)
        eq._append(evremote, evlocal, errmsg, 1)

        evremotejson, evlocaljson, errmsg = self.queue["2"]
        evremote = None if evremotejson is None else Event(from_json_dict=evremotejson)
        evlocal = Event(from_json_dict=evlocaljson)
        self.assertRaisesRegex(
            IndexError,
            "Specified eventNumber=1 already exist in queue",
            eq._append,
            evremote,
            evlocal,
            errmsg,
            1,
        )

    def test_index_event_absent_from_queue(self):
        eq = ErrorQueue(typesMapping=self.typesMapping, autoremediate=False)

        evremotejson, evlocaljson, errmsg = self.queue["1"]
        evremote = None if evremotejson is None else Event(from_json_dict=evremotejson)
        evlocal = Event(from_json_dict=evlocaljson)
        eq._append(evremote, evlocal, errmsg, 1)

        self.assertRaisesRegex(
            IndexError,
            "Specified eventNumber=2 doesn't exist in queue",
            eq._addEventToIndex,
            2,
        )

    def test_fill_queue_noremediate(self):
        eq = ErrorQueue(typesMapping=self.typesMapping, autoremediate=False)
        for evremotejson, evlocaljson, errmsg in self.queue.values():
            evremote = (
                None if evremotejson is None else Event(from_json_dict=evremotejson)
            )
            evlocal = Event(from_json_dict=evlocaljson)
            eq.append(evremote, evlocal, errmsg)
        self.assertEqual(len(eq), 8)  # Queue contains 8 items
        self.assertEqual(len(list(eq.allEvents())), 8)  # Queue contains 8 items
        self.assertEqual(
            len(list(iter(eq))), 3
        )  # Only 3 different objects are in queue
        self.assertEqual(eq.to_json(), self.queuejson)

    def test_fill_queue_fromjson_noremediate(self):
        eq = ErrorQueue(
            typesMapping=self.typesMapping,
            autoremediate=False,
            from_json_dict={"_queue": self.queue},
        )
        self.assertEqual(len(eq), 8)  # Queue contains 8 items
        self.assertEqual(len(list(eq.allEvents())), 8)  # Queue contains 8 items
        self.assertEqual(
            len(list(iter(eq))), 3
        )  # Only 3 different objects are in queue
        self.assertEqual(eq.to_json(), self.queuejson)

    def test_fill_queue_remediate(self):
        eq = ErrorQueue(typesMapping=self.typesMapping, autoremediate=True)
        for evremotejson, evlocaljson, errmsg in self.queue.values():
            evremote = (
                None if evremotejson is None else Event(from_json_dict=evremotejson)
            )
            evlocal = Event(from_json_dict=evlocaljson)
            eq.append(evremote, evlocal, errmsg)
        self.assertEqual(len(eq), 3)  # Queue contains 3 items
        self.assertEqual(len(list(eq.allEvents())), 3)  # Queue contains 3 items
        self.assertEqual(
            len(list(iter(eq))), 3
        )  # Only 3 different objects are in queue
        self.assertEqual(eq.to_json(), self.queueremediatedjson)

    def test_fill_queue_fromjson_remediate(self):
        eq = ErrorQueue(
            typesMapping=self.typesMapping,
            autoremediate=True,
            from_json_dict={"_queue": self.queue},
        )
        self.assertEqual(len(eq), 3)  # Queue contains 3 items
        self.assertEqual(len(list(eq.allEvents())), 3)  # Queue contains 3 items
        self.assertEqual(
            len(list(iter(eq))), 3
        )  # Only 3 different objects are in queue
        self.assertEqual(eq.to_json(), self.queueremediatedatimportjson)

    def test_append_unknown_objtype(self):
        eq = ErrorQueue(typesMapping=self.typesMapping, autoremediate=False)
        evjson = {
            "evcategory": "base",
            "eventtype": "added",
            "objtype": "UnknownTestObj",
            "objpkey": 1,
            "objattrs": {
                "obj_id": 1,
                "name": "UnknownTestObj_01",
                "description": "Unknown Test Object 01",
            },
            "step": 0,
        }
        event = Event(from_json_dict=evjson)
        with self.assertLogs(__hermes__.logger, level="INFO") as cm:
            eq.append(event, event, "Fake error message")
        self.assertEqual(len(cm.output), 1)
        self.assertRegex(
            cm.output[0],
            "INFO:hermes-unit-tests:Ignore loading of remote event of unknown objtype UnknownTestObj",
        )
        self.assertEqual(len(eq), 0)  # Queue should be empty

        with self.assertLogs(__hermes__.logger, level="INFO") as cm:
            eq.append(None, event, "Fake error message")
        self.assertEqual(len(cm.output), 1)
        self.assertRegex(
            cm.output[0],
            "INFO:hermes-unit-tests:Ignore loading of local event of unknown objtype UnknownTestObj",
        )
        self.assertEqual(len(eq), 0)  # Queue should be empty

    def test_updateErrorMsg_invalid_eventNumber(self):
        eq = ErrorQueue(
            typesMapping=self.typesMapping,
            autoremediate=False,
            from_json_dict={"_queue": self.queue},
        )

        self.assertRaisesRegex(
            IndexError,
            "Specified eventNumber=100 doesn't exist in queue",
            eq.updateErrorMsg,
            100,
            "Fake error message updated",
        )

    def test_updateErrorMsg(self):
        eq = ErrorQueue(
            typesMapping=self.typesMapping,
            autoremediate=False,
            from_json_dict={"_queue": self.queue},
        )
        eventNumber, evremotejson, evlocaljson, errmsg = next(iter(eq))
        self.assertEqual(eventNumber, 1)
        self.assertEqual(errmsg, "Fake error message")

        eq.updateErrorMsg(1, "Fake error message updated")

        eventNumber, evremotejson, evlocaljson, errmsg = next(iter(eq))
        self.assertEqual(eventNumber, 1)
        self.assertEqual(errmsg, "Fake error message updated")

    def test_remove_invalid_eventNumber_ignore(self):
        eq = ErrorQueue(
            typesMapping=self.typesMapping,
            autoremediate=False,
            from_json_dict={"_queue": self.queue},
        )

        queuelen = len(eq)
        eq.remove(100, ignoreMissingEventNumber=True)
        self.assertEqual(queuelen, len(eq))

    def test_remove_invalid_eventNumber_exception(self):
        eq = ErrorQueue(
            typesMapping=self.typesMapping,
            autoremediate=False,
            from_json_dict={"_queue": self.queue},
        )

        self.assertRaisesRegex(
            IndexError,
            "Specified eventNumber=100 doesn't exist in queue",
            eq.remove,
            100,
            ignoreMissingEventNumber=False,
        )

    def test_purgeAllEvents(self):
        eq = ErrorQueue(
            typesMapping=self.typesMapping,
            autoremediate=False,
            from_json_dict={"_queue": self.queue},
        )
        self.assertEqual(len(eq), 8)
        # 3 events
        eq.purgeAllEvents("TestObj1", 101, isLocalObjtype=False)
        self.assertEqual(len(eq), 5)
        # 3 events (2 remote, 1 local)
        eq.purgeAllEvents("TestObj2", 201, isLocalObjtype=False)
        self.assertEqual(len(eq), 2)
        # 2 events
        eq.purgeAllEvents("TestObj1", 103, isLocalObjtype=False)
        self.assertEqual(len(eq), 0)

        eq = ErrorQueue(
            typesMapping=self.typesMapping,
            autoremediate=False,
            from_json_dict={"_queue": self.queue},
        )
        self.assertEqual(len(eq), 8)
        # 3 events (2 remote, 1 local)
        eq.purgeAllEvents("TestObj2_local", 201, isLocalObjtype=True)
        self.assertEqual(len(eq), 5)

    def test_iter_with_remove(self):
        eq = ErrorQueue(
            typesMapping=self.typesMapping,
            autoremediate=False,
            from_json_dict={"_queue": self.queue},
        )

        total = 0
        for item in iter(eq):
            total += 1
        self.assertEqual(total, 3)  # 3 different objects in queue

        count = 0
        for item in iter(eq):
            count += 1
            eq.purgeAllEvents("TestObj2_local", 201, isLocalObjtype=True)
        self.assertEqual(count, 2)  # 2 remaining different objects in queue

    def test_allEvents_with_remove(self):
        eq = ErrorQueue(
            typesMapping=self.typesMapping,
            autoremediate=False,
            from_json_dict={"_queue": self.queue},
        )

        total = 0
        for item in eq.allEvents():
            total += 1
        self.assertEqual(total, 8)  # 8 events in queue

        count = 0
        for item in eq.allEvents():
            count += 1
            eq.purgeAllEvents("TestObj2_local", 201, isLocalObjtype=True)
        self.assertEqual(count, 5)  # 5 remaining events in queue

    def test_containsObjectByEvent(self):
        eq = ErrorQueue(
            typesMapping=self.typesMapping,
            autoremediate=False,
            from_json_dict={"_queue": self.queue},
        )

        ev = Event(from_json_dict=self.queue["6"][0])
        self.assertTrue(eq.containsObjectByEvent(ev, isLocalEvent=False))
        eq.purgeAllEvents("TestObj1", 103, isLocalObjtype=False)
        self.assertFalse(eq.containsObjectByEvent(ev, isLocalEvent=False))

    def test_containsObjectByDataobject(self):
        eq = ErrorQueue(
            typesMapping=self.typesMapping,
            autoremediate=False,
            from_json_dict={"_queue": self.queue},
        )

        objvals = {
            "OBJ_ID": 103,
            "NAME": "Object1_03",
            "DESCRIPTION": "Test Object1 03",
            "NEW_ATTR1": "new_attr1_value",
            "NEW_ATTR2": "new_attr2_value",
            "NEW_ATTR3": "new_attr3_value",
        }
        obj = self.TestObj1(from_remote=objvals)
        self.assertTrue(eq.containsObjectByDataobject(obj, isLocalObjtype=False))
        eq.purgeAllEventsOfDataObject(obj, isLocalObjtype=False)
        self.assertFalse(eq.containsObjectByDataobject(obj, isLocalObjtype=False))
