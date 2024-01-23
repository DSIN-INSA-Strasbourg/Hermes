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
from clients.eventqueue import EventQueue, HermesInvalidEventQueueJSONError
from lib.datamodel.dataobject import DataObject
from lib.datamodel.event import Event

import logging

logger = logging.getLogger("hermes")


class TestEventQueueClass(HermesServerTestCase):
    typesMapping = {"TestObj1": "TestObj1_local", "TestObj2": "TestObj2_local"}

    queue = {
        "1": [
            "remote",
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
            "Fake error message",
        ],
        "2": [
            "remote",
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
            "Fake error message",
        ],
        "3": [
            "remote",
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
            "Fake error message",
        ],
        "4": [
            "local",
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
            "remote",
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
            "Fake error message",
        ],
        "6": [
            "remote",
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
            "Fake error message",
        ],
        "7": [
            "remote",
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
            "Fake error message",
        ],
        "8": [
            "remote",
            {
                "evcategory": "base",
                "eventtype": "unknown",
                "objtype": "TestObj2",
                "objpkey": 201,
                "objattrs": {},
                "step": 0,
            },
            "Fake error message",
        ],
        "9": [
            "remote",
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
            "Fake error message",
        ],
    }

    queuejson = """{
    "_queue": {
        "1": [
            "remote",
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
            "Fake error message"
        ],
        "2": [
            "remote",
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
            "Fake error message"
        ],
        "3": [
            "remote",
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
            "Fake error message"
        ],
        "4": [
            "local",
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
            "remote",
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
            "Fake error message"
        ],
        "6": [
            "remote",
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
            "Fake error message"
        ],
        "7": [
            "remote",
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
            "Fake error message"
        ],
        "8": [
            "remote",
            {
                "evcategory": "base",
                "eventtype": "unknown",
                "objtype": "TestObj2",
                "objpkey": 201,
                "objattrs": {},
                "step": 0
            },
            "Fake error message"
        ],
        "9": [
            "remote",
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
            "Fake error message"
        ]
    }
}"""

    queueremediatedjson = """{
    "_queue": {
        "1": [
            "remote",
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
            "Fake error message"
        ],
        "2": [
            "remote",
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
            "Fake error message"
        ],
        "3": [
            "local",
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
        "4": [
            "remote",
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
            "Fake error message"
        ],
        "5": [
            "remote",
            {
                "evcategory": "base",
                "eventtype": "unknown",
                "objtype": "TestObj2",
                "objpkey": 201,
                "objattrs": {},
                "step": 0
            },
            "Fake error message"
        ],
        "6": [
            "remote",
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
            "Fake error message"
        ]
    }
}"""

    queueremediatedatimportjson = """{
    "_queue": {
        "1": [
            "remote",
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
            "Fake error message"
        ],
        "2": [
            "remote",
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
            "Fake error message"
        ],
        "4": [
            "local",
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
        "6": [
            "remote",
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
            "Fake error message"
        ],
        "8": [
            "remote",
            {
                "evcategory": "base",
                "eventtype": "unknown",
                "objtype": "TestObj2",
                "objpkey": 201,
                "objattrs": {},
                "step": 0
            },
            "Fake error message"
        ],
        "9": [
            "remote",
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
        eq = EventQueue(typesMapping=self.typesMapping, autoremediate=False)
        self.assertEqual(len(eq), 0)

    def test_init_from_invalid_json(self):
        self.assertRaises(
            HermesInvalidEventQueueJSONError,
            EventQueue,
            typesMapping=self.typesMapping,
            autoremediate=False,
            from_json_dict={"queue": self.queue},  # key should be "_queue"
        )

    def test_init_from_invalid_json(self):
        self.assertRaises(
            HermesInvalidEventQueueJSONError,
            EventQueue,
            typesMapping=self.typesMapping,
            autoremediate=False,
            from_json_dict={"queue": self.queue},  # key should be "_queue"
        )

    def test_fill_queue_twice_with_same_eventnumber(self):
        eq = EventQueue(typesMapping=self.typesMapping, autoremediate=False)

        evtype, evjson, errmsg = self.queue["1"]
        event = Event(from_json_dict=evjson)
        eq._append(evtype, event, errmsg, 1)

        evtype, evjson, errmsg = self.queue["2"]
        event = Event(from_json_dict=evjson)
        self.assertRaisesRegex(
            IndexError,
            "Specified eventNumber=1 already exist in queue",
            eq._append,
            evtype,
            event,
            errmsg,
            1,
        )

    def test_index_event_absent_from_queue(self):
        eq = EventQueue(typesMapping=self.typesMapping, autoremediate=False)

        evtype, evjson, errmsg = self.queue["1"]
        event = Event(from_json_dict=evjson)
        eq._append(evtype, event, errmsg, 1)

        self.assertRaisesRegex(
            IndexError,
            "Specified eventNumber=2 doesn't exist in queue",
            eq._addEventToIndex,
            2,
        )

    def test_fill_queue_noremediate(self):
        eq = EventQueue(typesMapping=self.typesMapping, autoremediate=False)
        for evtype, evjson, errmsg in self.queue.values():
            event = Event(from_json_dict=evjson)
            eq.append(evtype, event, errmsg)
        self.assertEqual(len(eq), 9)  # Queue contains 9 items
        self.assertEqual(len(list(eq.allEvents())), 9)  # Queue contains 9 items
        self.assertEqual(
            len(list(iter(eq))), 3
        )  # Only 3 different objects are in queue
        self.assertEqual(eq.to_json(), self.queuejson)

    def test_fill_queue_fromjson_noremediate(self):
        eq = EventQueue(
            typesMapping=self.typesMapping,
            autoremediate=False,
            from_json_dict={"_queue": self.queue},
        )
        self.assertEqual(len(eq), 9)  # Queue contains 9 items
        self.assertEqual(len(list(eq.allEvents())), 9)  # Queue contains 9 items
        self.assertEqual(
            len(list(iter(eq))), 3
        )  # Only 3 different objects are in queue
        self.assertEqual(eq.to_json(), self.queuejson)

    def test_fill_queue_remediate(self):
        eq = EventQueue(typesMapping=self.typesMapping, autoremediate=True)
        for evtype, evjson, errmsg in self.queue.values():
            event = Event(from_json_dict=evjson)
            eq.append(evtype, event, errmsg)
        self.assertEqual(len(eq), 6)  # Queue contains 6 items
        self.assertEqual(len(list(eq.allEvents())), 6)  # Queue contains 6 items
        self.assertEqual(
            len(list(iter(eq))), 3
        )  # Only 3 different objects are in queue
        self.assertEqual(eq.to_json(), self.queueremediatedjson)

    def test_fill_queue_fromjson_remediate(self):
        eq = EventQueue(
            typesMapping=self.typesMapping,
            autoremediate=True,
            from_json_dict={"_queue": self.queue},
        )
        self.assertEqual(len(eq), 6)  # Queue contains 6 items
        self.assertEqual(len(list(eq.allEvents())), 6)  # Queue contains 6 items
        self.assertEqual(
            len(list(iter(eq))), 3
        )  # Only 3 different objects are in queue
        self.assertEqual(eq.to_json(), self.queueremediatedatimportjson)

    def test_append_unknown_objtype(self):
        eq = EventQueue(typesMapping=self.typesMapping, autoremediate=False)
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
        with self.assertLogs(logger, level="INFO") as cm:
            eq.append("remote", event, "Fake error message")
        self.assertEqual(len(cm.output), 1)
        self.assertRegex(
            cm.output[0],
            "INFO:hermes:Ignore loading of remote event of unknown objtype UnknownTestObj",
        )
        self.assertEqual(len(eq), 0)  # Queue should be empty

    def test_updateErrorMsg_invalid_eventNumber(self):
        eq = EventQueue(
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
        eq = EventQueue(
            typesMapping=self.typesMapping,
            autoremediate=False,
            from_json_dict={"_queue": self.queue},
        )
        eventNumber, evtype, evjson, errmsg = next(iter(eq))
        self.assertEqual(eventNumber, 1)
        self.assertEqual(errmsg, "Fake error message")

        eq.updateErrorMsg(1, "Fake error message updated")

        eventNumber, evtype, evjson, errmsg = next(iter(eq))
        self.assertEqual(eventNumber, 1)
        self.assertEqual(errmsg, "Fake error message updated")

    def test_remove_invalid_eventNumber_ignore(self):
        eq = EventQueue(
            typesMapping=self.typesMapping,
            autoremediate=False,
            from_json_dict={"_queue": self.queue},
        )

        queuelen = len(eq)
        eq.remove(100, ignoreMissingEventNumber=True)
        self.assertEqual(queuelen, len(eq))

    def test_remove_invalid_eventNumber_exception(self):
        eq = EventQueue(
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
        eq = EventQueue(
            typesMapping=self.typesMapping,
            autoremediate=False,
            from_json_dict={"_queue": self.queue},
        )
        self.assertEqual(len(eq), 9)
        eq.purgeAllEvents("remote", "TestObj1", 101)  # 3 events
        self.assertEqual(len(eq), 6)
        eq.purgeAllEvents("remote", "TestObj2", 201)  # 4 events (3 remote, 1 local)
        self.assertEqual(len(eq), 2)
        eq.purgeAllEvents("remote", "TestObj1", 103)  # 2 events
        self.assertEqual(len(eq), 0)

        eq = EventQueue(
            typesMapping=self.typesMapping,
            autoremediate=False,
            from_json_dict={"_queue": self.queue},
        )
        self.assertEqual(len(eq), 9)
        eq.purgeAllEvents(
            "local", "TestObj2_local", 201
        )  # 4 events (3 remote, 1 local)
        self.assertEqual(len(eq), 5)

    def test_iter_with_remove(self):
        eq = EventQueue(
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
            eq.purgeAllEvents("local", "TestObj2_local", 201)
        self.assertEqual(count, 2)  # 2 remaining different objects in queue

    def test_allEvents_with_remove(self):
        eq = EventQueue(
            typesMapping=self.typesMapping,
            autoremediate=False,
            from_json_dict={"_queue": self.queue},
        )

        total = 0
        for item in eq.allEvents():
            total += 1
        self.assertEqual(total, 9)  # 9 events in queue

        count = 0
        for item in eq.allEvents():
            count += 1
            eq.purgeAllEvents("local", "TestObj2_local", 201)
        self.assertEqual(count, 5)  # 5 remaining events in queue

    def test_containsObjectByEvent(self):
        eq = EventQueue(
            typesMapping=self.typesMapping,
            autoremediate=False,
            from_json_dict={"_queue": self.queue},
        )

        ev = Event(from_json_dict=self.queue["6"][1])
        self.assertTrue(eq.containsObjectByEvent("remote", ev))
        eq.purgeAllEvents("remote", "TestObj1", 103)
        self.assertFalse(eq.containsObjectByEvent("remote", ev))

    def test_containsObjectByDataobject(self):
        eq = EventQueue(
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
        self.assertTrue(eq.containsObjectByDataobject("remote", obj))
        eq.purgeAllEventsOfDataObject("remote", obj)
        self.assertFalse(eq.containsObjectByDataobject("remote", obj))
