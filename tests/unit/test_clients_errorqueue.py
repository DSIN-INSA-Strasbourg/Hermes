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


# Table of event flow in queue
#
# |         |         objpkey=1        |||         objpkey=2        |||         objpkey=3        |||         objpkey=4        |||         objpkey=5        |||
# | Event # |  Remote  |   Local  | Step |  Remote  |   Local  | Step |  Remote  |   Local  | Step |  Remote  |   Local  | Step |  Remote  |   Local  | Step |
# |:-------:|:--------:|:--------:|:----:|:--------:|:--------:|:----:|:--------:|:--------:|:----:|:--------:|:--------:|:----:|:--------:|:--------:|:----:|
# |     1   |   added  |   added  |   0  |          |          |      |          |          |      |          |          |      |          |          |      |
# |     2   |          |          |      |     -    | modified |   0  |          |          |      |          |          |      |          |          |      |
# |     3   |          |          |      |          |          |      | modified | modified |   0  |          |          |      |          |          |      |
# |     4   |          |          |      |          |          |      |          |          |      |   added  |   added  |   0  |          |          |      |
# |     5   |          |          |      |          |          |      |          |          |      |          |          |      |   added  |   added  |   0  |
# |     6   |  removed |  removed |   0  |          |          |      |          |          |      |          |          |      |          |          |      |
# |     7   |          |          |      |     -    | modified |   0  |          |          |      |          |          |      |          |          |      |
# |     8   |          |          |      |          |          |      | modified | modified |   0  |          |          |      |          |          |      |
# |     9   |          |          |      |          |          |      |          |          |      |     -    | modified |   0  |          |          |      |
# |    10   |          |          |      |          |          |      |          |          |      |          |          |      |     -    | modified |   1  |
# |    11   |          |          |      | modified | modified |   0  |          |          |      |          |          |      |          |          |      |
# |    12   |          |          |      |          |          |      |  removed |  removed |   0  |          |          |      |          |          |      |
# |    13   |          |          |      |          |          |      |          |          |      | modified | modified |   0  |          |          |      |
# |    14   |          |          |      |          |          |      |          |          |      |          |          |      | modified | modified |   0  |
# |    15   |          |          |      |          |          |      |   added  |   added  |   0  |          |          |      |          |          |      |
# |    16   |          |          |      |          |          |      |          |          |      |          |          |      |  removed |  removed |   0  |
# |    17   |          |          |      |          |          |      | modified | modified |   1  |          |          |      |          |          |      |
# |    18   |          |          |      |          |          |      |          |          |      |          |          |      |   added  |   added  |   0  |

# Number of events remaining in queue according to autoremediation policy
#
# |                          | objpkey=1 | objpkey=2 | objpkey=3 | objpkey=4 | objpkey=5 | TOTAL IN QUEUE |
# |:------------------------:|:---------:|:---------:|:---------:|:---------:|:---------:|:--------------:|
# | Conservative             |     2     |     1     |     4     |     1     |     5     |       13       |
# | Maximum w/o datasources  |     0     |     1     |     3     |     1     |     4     |        9       |
# | Maximum with datasources |     0     |     1     |     2     |     1     |     3     |        7       |


class TestErrorQueueClass(HermesServerTestCase):
    typesMapping = {"TestObj1": "TestObj1_local"}

    queue = {
        "1": [
            {
                "evcategory": "initsync",
                "eventtype": "added",
                "objtype": "TestObj1",
                "objpkey": 1,
                "objattrs": {
                    "obj_id": 1,
                    "name": "Object1",
                    "description": "Test Object1",
                },
                "step": 0,
                "isPartiallyProcessed": False,
            },
            {
                "evcategory": "initsync",
                "eventtype": "added",
                "objtype": "TestObj1_local",
                "objpkey": 1,
                "objattrs": {
                    "obj_id": 1,
                    "name": "Object1",
                    "description": "Test Object1",
                },
                "step": 0,
                "isPartiallyProcessed": False,
            },
            "Fake error message",
        ],
        "2": [
            None,
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1_local",
                "objpkey": 2,
                "objattrs": {
                    "added": {"new_attr2": "new_attr2_value"},
                    "modified": {"name": "Object2_modified"},
                    "removed": {"description": None},
                },
                "step": 0,
                "isPartiallyProcessed": False,
            },
            "Fake error message",
        ],
        "3": [
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1",
                "objpkey": 3,
                "objattrs": {
                    "added": {"new_attr32": "new_attr32_value"},
                    "modified": {
                        "name": "Object3_modified",
                        "new_attr31": "new_attr31_value",
                    },
                    "removed": {"new_attr30": None},
                },
                "step": 0,
                "isPartiallyProcessed": False,
            },
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1_local",
                "objpkey": 3,
                "objattrs": {
                    "added": {"new_attr32": "new_attr32_value"},
                    "modified": {
                        "name": "Object3_modified",
                        "new_attr31": "new_attr31_value",
                    },
                    "removed": {"new_attr30": None},
                },
                "step": 0,
                "isPartiallyProcessed": False,
            },
            "Fake error message",
        ],
        "4": [
            {
                "evcategory": "base",
                "eventtype": "added",
                "objtype": "TestObj1",
                "objpkey": 4,
                "objattrs": {
                    "obj_id": 4,
                    "name": "Object4",
                    "description": "Test Object4",
                },
                "step": 0,
                "isPartiallyProcessed": False,
            },
            {
                "evcategory": "base",
                "eventtype": "added",
                "objtype": "TestObj1_local",
                "objpkey": 4,
                "objattrs": {
                    "obj_id": 4,
                    "name": "Object4",
                    "description": "Test Object4",
                },
                "step": 0,
                "isPartiallyProcessed": False,
            },
            "Fake error message",
        ],
        "5": [
            {
                "evcategory": "base",
                "eventtype": "added",
                "objtype": "TestObj1",
                "objpkey": 5,
                "objattrs": {
                    "obj_id": 5,
                    "name": "Object5",
                    "description": "Test Object5",
                },
                "step": 0,
                "isPartiallyProcessed": False,
            },
            {
                "evcategory": "base",
                "eventtype": "added",
                "objtype": "TestObj1_local",
                "objpkey": 5,
                "objattrs": {
                    "obj_id": 5,
                    "name": "Object5",
                    "description": "Test Object5",
                },
                "step": 0,
                "isPartiallyProcessed": False,
            },
            "Fake error message",
        ],
        "6": [
            {
                "evcategory": "base",
                "eventtype": "removed",
                "objtype": "TestObj1",
                "objpkey": 1,
                "objattrs": {},
                "step": 0,
                "isPartiallyProcessed": False,
            },
            {
                "evcategory": "base",
                "eventtype": "removed",
                "objtype": "TestObj1_local",
                "objpkey": 1,
                "objattrs": {},
                "step": 0,
                "isPartiallyProcessed": False,
            },
            "Fake error message",
        ],
        "7": [
            None,
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1_local",
                "objpkey": 2,
                "objattrs": {
                    "added": {"description": "Test Object2"},
                    "modified": {
                        "name": "Object2_modified_again",
                        "new_attr2": "new_attr2_value_modified",
                    },
                    "removed": {},
                },
                "step": 0,
                "isPartiallyProcessed": False,
            },
            "Fake error message",
        ],
        "8": [
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1",
                "objpkey": 3,
                "objattrs": {
                    "added": {"new_attr33": "new_attr33_value"},
                    "modified": {
                        "name": "Object3_modified_again",
                        "new_attr31": "new_attr31_value_modified",
                    },
                    "removed": {"new_attr32": None},
                },
                "step": 0,
                "isPartiallyProcessed": False,
            },
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1_local",
                "objpkey": 3,
                "objattrs": {
                    "added": {"new_attr33": "new_attr33_value"},
                    "modified": {
                        "name": "Object3_modified_again",
                        "new_attr31": "new_attr31_value_modified",
                    },
                    "removed": {"new_attr32": None},
                },
                "step": 0,
                "isPartiallyProcessed": False,
            },
            "Fake error message",
        ],
        "9": [
            None,
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1_local",
                "objpkey": 4,
                "objattrs": {
                    "added": {"new_attr4": "new_attr4_value"},
                    "modified": {
                        "name": "Object4_modified",
                    },
                    "removed": {"description": None},
                },
                "step": 0,
                # "isPartiallyProcessed": False,
            },
            "Fake error message",
        ],
        "10": [
            None,
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1_local",
                "objpkey": 5,
                "objattrs": {
                    "added": {"new_attr5": "new_attr5_value"},
                    "modified": {
                        "name": "Object5_modified",
                    },
                    "removed": {"description": None},
                },
                "step": 1,
                # "isPartiallyProcessed": True,
            },
            "Fake error message",
        ],
        "11": [
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1",
                "objpkey": 2,
                "objattrs": {
                    "added": {"new_attr20": "new_attr20_value"},
                    "modified": {
                        "name": "Object2_modified_final",
                    },
                    "removed": {"new_attr2": None},
                },
                "step": 0,
                "isPartiallyProcessed": False,
            },
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1_local",
                "objpkey": 2,
                "objattrs": {
                    "added": {"new_attr20": "new_attr20_value"},
                    "modified": {
                        "name": "Object2_modified_final",
                    },
                    "removed": {"new_attr2": None},
                },
                "step": 0,
                "isPartiallyProcessed": False,
            },
            "Fake error message",
        ],
        "12": [
            {
                "evcategory": "base",
                "eventtype": "removed",
                "objtype": "TestObj1",
                "objpkey": 3,
                "objattrs": {},
                "step": 0,
                "isPartiallyProcessed": False,
            },
            {
                "evcategory": "base",
                "eventtype": "removed",
                "objtype": "TestObj1_local",
                "objpkey": 3,
                "objattrs": {},
                "step": 0,
                "isPartiallyProcessed": False,
            },
            "Fake error message",
        ],
        "13": [
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1",
                "objpkey": 4,
                "objattrs": {
                    "added": {"new_attr41": "new_attr41_value_final"},
                    "modified": {
                        "name": "Object4_modified_final",
                    },
                    "removed": {"description": None},
                },
                "step": 0,
                "isPartiallyProcessed": False,
            },
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1_local",
                "objpkey": 4,
                "objattrs": {
                    "added": {"new_attr41": "new_attr41_value_final"},
                    "modified": {
                        "name": "Object4_modified_final",
                    },
                    "removed": {"description": None},
                },
                "step": 0,
                "isPartiallyProcessed": False,
            },
            "Fake error message",
        ],
        "14": [
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1",
                "objpkey": 5,
                "objattrs": {
                    "added": {"new_attr51": "new_attr51_value_final"},
                    "modified": {
                        "name": "Object5_modified_final",
                    },
                    "removed": {"description": None},
                },
                "step": 0,
                "isPartiallyProcessed": False,
            },
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1_local",
                "objpkey": 5,
                "objattrs": {
                    "added": {"new_attr51": "new_attr51_value_final"},
                    "modified": {
                        "name": "Object5_modified_final",
                    },
                    "removed": {"description": None},
                },
                "step": 0,
                "isPartiallyProcessed": False,
            },
            "Fake error message",
        ],
        "15": [
            {
                "evcategory": "base",
                "eventtype": "added",
                "objtype": "TestObj1",
                "objpkey": 3,
                "objattrs": {
                    "obj_id": 3,
                    "name": "Object3_v2",
                    "description": "Test Object3_v2",
                },
                "step": 0,
                "isPartiallyProcessed": False,
            },
            {
                "evcategory": "base",
                "eventtype": "added",
                "objtype": "TestObj1_local",
                "objpkey": 3,
                "objattrs": {
                    "obj_id": 3,
                    "name": "Object3_v2",
                    "description": "Test Object3_v2",
                },
                "step": 0,
                "isPartiallyProcessed": False,
            },
            "Fake error message",
        ],
        "16": [
            {
                "evcategory": "base",
                "eventtype": "removed",
                "objtype": "TestObj1",
                "objpkey": 5,
                "objattrs": {},
                "step": 0,
                "isPartiallyProcessed": False,
            },
            {
                "evcategory": "base",
                "eventtype": "removed",
                "objtype": "TestObj1_local",
                "objpkey": 5,
                "objattrs": {},
                "step": 0,
                "isPartiallyProcessed": False,
            },
            "Fake error message",
        ],
        "17": [
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1",
                "objpkey": 3,
                "objattrs": {
                    "added": {"new_attr34": "new_attr34_value"},
                    "modified": {
                        "name": "Object3_v2_modified",
                    },
                    "removed": {"description": None},
                },
                "step": 1,
                "isPartiallyProcessed": True,
            },
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1_local",
                "objpkey": 3,
                "objattrs": {
                    "added": {"new_attr34": "new_attr34_value"},
                    "modified": {
                        "name": "Object3_v2_modified",
                    },
                    "removed": {"description": None},
                },
                "step": 1,
                "isPartiallyProcessed": True,
            },
            "Fake error message",
        ],
        "18": [
            {
                "evcategory": "base",
                "eventtype": "added",
                "objtype": "TestObj1",
                "objpkey": 5,
                "objattrs": {
                    "obj_id": 5,
                    "name": "Object5 new",
                    "description": "Test Object5 new",
                },
                "step": 0,
                "isPartiallyProcessed": False,
            },
            {
                "evcategory": "base",
                "eventtype": "added",
                "objtype": "TestObj1_local",
                "objpkey": 5,
                "objattrs": {
                    "obj_id": 5,
                    "name": "Object5 new",
                    "description": "Test Object5 new",
                },
                "step": 0,
                "isPartiallyProcessed": False,
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
                "objpkey": 1,
                "objattrs": {
                    "obj_id": 1,
                    "name": "Object1",
                    "description": "Test Object1"
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            {
                "evcategory": "initsync",
                "eventtype": "added",
                "objtype": "TestObj1_local",
                "objpkey": 1,
                "objattrs": {
                    "obj_id": 1,
                    "name": "Object1",
                    "description": "Test Object1"
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ],
        "2": [
            null,
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1_local",
                "objpkey": 2,
                "objattrs": {
                    "added": {
                        "new_attr2": "new_attr2_value"
                    },
                    "modified": {
                        "name": "Object2_modified"
                    },
                    "removed": {
                        "description": null
                    }
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ],
        "3": [
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1",
                "objpkey": 3,
                "objattrs": {
                    "added": {
                        "new_attr32": "new_attr32_value"
                    },
                    "modified": {
                        "name": "Object3_modified",
                        "new_attr31": "new_attr31_value"
                    },
                    "removed": {
                        "new_attr30": null
                    }
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1_local",
                "objpkey": 3,
                "objattrs": {
                    "added": {
                        "new_attr32": "new_attr32_value"
                    },
                    "modified": {
                        "name": "Object3_modified",
                        "new_attr31": "new_attr31_value"
                    },
                    "removed": {
                        "new_attr30": null
                    }
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ],
        "4": [
            {
                "evcategory": "base",
                "eventtype": "added",
                "objtype": "TestObj1",
                "objpkey": 4,
                "objattrs": {
                    "obj_id": 4,
                    "name": "Object4",
                    "description": "Test Object4"
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            {
                "evcategory": "base",
                "eventtype": "added",
                "objtype": "TestObj1_local",
                "objpkey": 4,
                "objattrs": {
                    "obj_id": 4,
                    "name": "Object4",
                    "description": "Test Object4"
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ],
        "5": [
            {
                "evcategory": "base",
                "eventtype": "added",
                "objtype": "TestObj1",
                "objpkey": 5,
                "objattrs": {
                    "obj_id": 5,
                    "name": "Object5",
                    "description": "Test Object5"
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            {
                "evcategory": "base",
                "eventtype": "added",
                "objtype": "TestObj1_local",
                "objpkey": 5,
                "objattrs": {
                    "obj_id": 5,
                    "name": "Object5",
                    "description": "Test Object5"
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ],
        "6": [
            {
                "evcategory": "base",
                "eventtype": "removed",
                "objtype": "TestObj1",
                "objpkey": 1,
                "objattrs": {},
                "step": 0,
                "isPartiallyProcessed": false
            },
            {
                "evcategory": "base",
                "eventtype": "removed",
                "objtype": "TestObj1_local",
                "objpkey": 1,
                "objattrs": {},
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ],
        "7": [
            null,
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1_local",
                "objpkey": 2,
                "objattrs": {
                    "added": {
                        "description": "Test Object2"
                    },
                    "modified": {
                        "name": "Object2_modified_again",
                        "new_attr2": "new_attr2_value_modified"
                    },
                    "removed": {}
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ],
        "8": [
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1",
                "objpkey": 3,
                "objattrs": {
                    "added": {
                        "new_attr33": "new_attr33_value"
                    },
                    "modified": {
                        "name": "Object3_modified_again",
                        "new_attr31": "new_attr31_value_modified"
                    },
                    "removed": {
                        "new_attr32": null
                    }
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1_local",
                "objpkey": 3,
                "objattrs": {
                    "added": {
                        "new_attr33": "new_attr33_value"
                    },
                    "modified": {
                        "name": "Object3_modified_again",
                        "new_attr31": "new_attr31_value_modified"
                    },
                    "removed": {
                        "new_attr32": null
                    }
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ],
        "9": [
            null,
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1_local",
                "objpkey": 4,
                "objattrs": {
                    "added": {
                        "new_attr4": "new_attr4_value"
                    },
                    "modified": {
                        "name": "Object4_modified"
                    },
                    "removed": {
                        "description": null
                    }
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ],
        "10": [
            null,
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1_local",
                "objpkey": 5,
                "objattrs": {
                    "added": {
                        "new_attr5": "new_attr5_value"
                    },
                    "modified": {
                        "name": "Object5_modified"
                    },
                    "removed": {
                        "description": null
                    }
                },
                "step": 1,
                "isPartiallyProcessed": true
            },
            "Fake error message"
        ],
        "11": [
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1",
                "objpkey": 2,
                "objattrs": {
                    "added": {
                        "new_attr20": "new_attr20_value"
                    },
                    "modified": {
                        "name": "Object2_modified_final"
                    },
                    "removed": {
                        "new_attr2": null
                    }
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1_local",
                "objpkey": 2,
                "objattrs": {
                    "added": {
                        "new_attr20": "new_attr20_value"
                    },
                    "modified": {
                        "name": "Object2_modified_final"
                    },
                    "removed": {
                        "new_attr2": null
                    }
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ],
        "12": [
            {
                "evcategory": "base",
                "eventtype": "removed",
                "objtype": "TestObj1",
                "objpkey": 3,
                "objattrs": {},
                "step": 0,
                "isPartiallyProcessed": false
            },
            {
                "evcategory": "base",
                "eventtype": "removed",
                "objtype": "TestObj1_local",
                "objpkey": 3,
                "objattrs": {},
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ],
        "13": [
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1",
                "objpkey": 4,
                "objattrs": {
                    "added": {
                        "new_attr41": "new_attr41_value_final"
                    },
                    "modified": {
                        "name": "Object4_modified_final"
                    },
                    "removed": {
                        "description": null
                    }
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1_local",
                "objpkey": 4,
                "objattrs": {
                    "added": {
                        "new_attr41": "new_attr41_value_final"
                    },
                    "modified": {
                        "name": "Object4_modified_final"
                    },
                    "removed": {
                        "description": null
                    }
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ],
        "14": [
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1",
                "objpkey": 5,
                "objattrs": {
                    "added": {
                        "new_attr51": "new_attr51_value_final"
                    },
                    "modified": {
                        "name": "Object5_modified_final"
                    },
                    "removed": {
                        "description": null
                    }
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1_local",
                "objpkey": 5,
                "objattrs": {
                    "added": {
                        "new_attr51": "new_attr51_value_final"
                    },
                    "modified": {
                        "name": "Object5_modified_final"
                    },
                    "removed": {
                        "description": null
                    }
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ],
        "15": [
            {
                "evcategory": "base",
                "eventtype": "added",
                "objtype": "TestObj1",
                "objpkey": 3,
                "objattrs": {
                    "obj_id": 3,
                    "name": "Object3_v2",
                    "description": "Test Object3_v2"
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            {
                "evcategory": "base",
                "eventtype": "added",
                "objtype": "TestObj1_local",
                "objpkey": 3,
                "objattrs": {
                    "obj_id": 3,
                    "name": "Object3_v2",
                    "description": "Test Object3_v2"
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ],
        "16": [
            {
                "evcategory": "base",
                "eventtype": "removed",
                "objtype": "TestObj1",
                "objpkey": 5,
                "objattrs": {},
                "step": 0,
                "isPartiallyProcessed": false
            },
            {
                "evcategory": "base",
                "eventtype": "removed",
                "objtype": "TestObj1_local",
                "objpkey": 5,
                "objattrs": {},
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ],
        "17": [
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1",
                "objpkey": 3,
                "objattrs": {
                    "added": {
                        "new_attr34": "new_attr34_value"
                    },
                    "modified": {
                        "name": "Object3_v2_modified"
                    },
                    "removed": {
                        "description": null
                    }
                },
                "step": 1,
                "isPartiallyProcessed": true
            },
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1_local",
                "objpkey": 3,
                "objattrs": {
                    "added": {
                        "new_attr34": "new_attr34_value"
                    },
                    "modified": {
                        "name": "Object3_v2_modified"
                    },
                    "removed": {
                        "description": null
                    }
                },
                "step": 1,
                "isPartiallyProcessed": true
            },
            "Fake error message"
        ],
        "18": [
            {
                "evcategory": "base",
                "eventtype": "added",
                "objtype": "TestObj1",
                "objpkey": 5,
                "objattrs": {
                    "obj_id": 5,
                    "name": "Object5 new",
                    "description": "Test Object5 new"
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            {
                "evcategory": "base",
                "eventtype": "added",
                "objtype": "TestObj1_local",
                "objpkey": 5,
                "objattrs": {
                    "obj_id": 5,
                    "name": "Object5 new",
                    "description": "Test Object5 new"
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ]
    }
}"""

    queueremediatedconservativejson = """{
    "_queue": {
        "1": [
            {
                "evcategory": "initsync",
                "eventtype": "added",
                "objtype": "TestObj1",
                "objpkey": 1,
                "objattrs": {
                    "obj_id": 1,
                    "name": "Object1",
                    "description": "Test Object1"
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            {
                "evcategory": "initsync",
                "eventtype": "added",
                "objtype": "TestObj1_local",
                "objpkey": 1,
                "objattrs": {
                    "obj_id": 1,
                    "name": "Object1",
                    "description": "Test Object1"
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ],
        "2": [
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1",
                "objpkey": 2,
                "objattrs": {
                    "added": {
                        "new_attr20": "new_attr20_value"
                    },
                    "modified": {
                        "name": "Object2_modified_final"
                    },
                    "removed": {
                        "new_attr2": null
                    }
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1_local",
                "objpkey": 2,
                "objattrs": {
                    "added": {
                        "description": "Test Object2",
                        "new_attr20": "new_attr20_value"
                    },
                    "modified": {
                        "name": "Object2_modified_final"
                    },
                    "removed": {}
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ],
        "3": [
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1",
                "objpkey": 3,
                "objattrs": {
                    "added": {
                        "new_attr33": "new_attr33_value"
                    },
                    "modified": {
                        "name": "Object3_modified_again",
                        "new_attr31": "new_attr31_value_modified"
                    },
                    "removed": {
                        "new_attr30": null
                    }
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1_local",
                "objpkey": 3,
                "objattrs": {
                    "added": {
                        "new_attr33": "new_attr33_value"
                    },
                    "modified": {
                        "name": "Object3_modified_again",
                        "new_attr31": "new_attr31_value_modified"
                    },
                    "removed": {
                        "new_attr30": null
                    }
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ],
        "4": [
            {
                "evcategory": "base",
                "eventtype": "added",
                "objtype": "TestObj1",
                "objpkey": 4,
                "objattrs": {
                    "obj_id": 4,
                    "name": "Object4_modified_final",
                    "new_attr41": "new_attr41_value_final"
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            {
                "evcategory": "base",
                "eventtype": "added",
                "objtype": "TestObj1_local",
                "objpkey": 4,
                "objattrs": {
                    "obj_id": 4,
                    "name": "Object4_modified_final",
                    "new_attr4": "new_attr4_value",
                    "new_attr41": "new_attr41_value_final"
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ],
        "5": [
            {
                "evcategory": "base",
                "eventtype": "added",
                "objtype": "TestObj1",
                "objpkey": 5,
                "objattrs": {
                    "obj_id": 5,
                    "name": "Object5",
                    "description": "Test Object5"
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            {
                "evcategory": "base",
                "eventtype": "added",
                "objtype": "TestObj1_local",
                "objpkey": 5,
                "objattrs": {
                    "obj_id": 5,
                    "name": "Object5",
                    "description": "Test Object5"
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ],
        "6": [
            {
                "evcategory": "base",
                "eventtype": "removed",
                "objtype": "TestObj1",
                "objpkey": 1,
                "objattrs": {},
                "step": 0,
                "isPartiallyProcessed": false
            },
            {
                "evcategory": "base",
                "eventtype": "removed",
                "objtype": "TestObj1_local",
                "objpkey": 1,
                "objattrs": {},
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ],
        "7": [
            null,
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1_local",
                "objpkey": 5,
                "objattrs": {
                    "added": {
                        "new_attr5": "new_attr5_value"
                    },
                    "modified": {
                        "name": "Object5_modified"
                    },
                    "removed": {
                        "description": null
                    }
                },
                "step": 1,
                "isPartiallyProcessed": true
            },
            "Fake error message"
        ],
        "8": [
            {
                "evcategory": "base",
                "eventtype": "removed",
                "objtype": "TestObj1",
                "objpkey": 3,
                "objattrs": {},
                "step": 0,
                "isPartiallyProcessed": false
            },
            {
                "evcategory": "base",
                "eventtype": "removed",
                "objtype": "TestObj1_local",
                "objpkey": 3,
                "objattrs": {},
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ],
        "9": [
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1",
                "objpkey": 5,
                "objattrs": {
                    "added": {
                        "new_attr51": "new_attr51_value_final"
                    },
                    "modified": {
                        "name": "Object5_modified_final"
                    },
                    "removed": {
                        "description": null
                    }
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1_local",
                "objpkey": 5,
                "objattrs": {
                    "added": {
                        "new_attr51": "new_attr51_value_final"
                    },
                    "modified": {
                        "name": "Object5_modified_final"
                    },
                    "removed": {
                        "description": null
                    }
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ],
        "10": [
            {
                "evcategory": "base",
                "eventtype": "added",
                "objtype": "TestObj1",
                "objpkey": 3,
                "objattrs": {
                    "obj_id": 3,
                    "name": "Object3_v2",
                    "description": "Test Object3_v2"
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            {
                "evcategory": "base",
                "eventtype": "added",
                "objtype": "TestObj1_local",
                "objpkey": 3,
                "objattrs": {
                    "obj_id": 3,
                    "name": "Object3_v2",
                    "description": "Test Object3_v2"
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ],
        "11": [
            {
                "evcategory": "base",
                "eventtype": "removed",
                "objtype": "TestObj1",
                "objpkey": 5,
                "objattrs": {},
                "step": 0,
                "isPartiallyProcessed": false
            },
            {
                "evcategory": "base",
                "eventtype": "removed",
                "objtype": "TestObj1_local",
                "objpkey": 5,
                "objattrs": {},
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ],
        "12": [
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1",
                "objpkey": 3,
                "objattrs": {
                    "added": {
                        "new_attr34": "new_attr34_value"
                    },
                    "modified": {
                        "name": "Object3_v2_modified"
                    },
                    "removed": {
                        "description": null
                    }
                },
                "step": 1,
                "isPartiallyProcessed": true
            },
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1_local",
                "objpkey": 3,
                "objattrs": {
                    "added": {
                        "new_attr34": "new_attr34_value"
                    },
                    "modified": {
                        "name": "Object3_v2_modified"
                    },
                    "removed": {
                        "description": null
                    }
                },
                "step": 1,
                "isPartiallyProcessed": true
            },
            "Fake error message"
        ],
        "13": [
            {
                "evcategory": "base",
                "eventtype": "added",
                "objtype": "TestObj1",
                "objpkey": 5,
                "objattrs": {
                    "obj_id": 5,
                    "name": "Object5 new",
                    "description": "Test Object5 new"
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            {
                "evcategory": "base",
                "eventtype": "added",
                "objtype": "TestObj1_local",
                "objpkey": 5,
                "objattrs": {
                    "obj_id": 5,
                    "name": "Object5 new",
                    "description": "Test Object5 new"
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ]
    }
}"""

    queueremediatedconservativeatimportjson = """{
    "_queue": {
        "1": [
            {
                "evcategory": "initsync",
                "eventtype": "added",
                "objtype": "TestObj1",
                "objpkey": 1,
                "objattrs": {
                    "obj_id": 1,
                    "name": "Object1",
                    "description": "Test Object1"
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            {
                "evcategory": "initsync",
                "eventtype": "added",
                "objtype": "TestObj1_local",
                "objpkey": 1,
                "objattrs": {
                    "obj_id": 1,
                    "name": "Object1",
                    "description": "Test Object1"
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ],
        "2": [
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1",
                "objpkey": 2,
                "objattrs": {
                    "added": {
                        "new_attr20": "new_attr20_value"
                    },
                    "modified": {
                        "name": "Object2_modified_final"
                    },
                    "removed": {
                        "new_attr2": null
                    }
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1_local",
                "objpkey": 2,
                "objattrs": {
                    "added": {
                        "description": "Test Object2",
                        "new_attr20": "new_attr20_value"
                    },
                    "modified": {
                        "name": "Object2_modified_final"
                    },
                    "removed": {}
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ],
        "3": [
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1",
                "objpkey": 3,
                "objattrs": {
                    "added": {
                        "new_attr33": "new_attr33_value"
                    },
                    "modified": {
                        "name": "Object3_modified_again",
                        "new_attr31": "new_attr31_value_modified"
                    },
                    "removed": {
                        "new_attr30": null
                    }
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1_local",
                "objpkey": 3,
                "objattrs": {
                    "added": {
                        "new_attr33": "new_attr33_value"
                    },
                    "modified": {
                        "name": "Object3_modified_again",
                        "new_attr31": "new_attr31_value_modified"
                    },
                    "removed": {
                        "new_attr30": null
                    }
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ],
        "4": [
            {
                "evcategory": "base",
                "eventtype": "added",
                "objtype": "TestObj1",
                "objpkey": 4,
                "objattrs": {
                    "obj_id": 4,
                    "name": "Object4_modified_final",
                    "new_attr41": "new_attr41_value_final"
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            {
                "evcategory": "base",
                "eventtype": "added",
                "objtype": "TestObj1_local",
                "objpkey": 4,
                "objattrs": {
                    "obj_id": 4,
                    "name": "Object4_modified_final",
                    "new_attr4": "new_attr4_value",
                    "new_attr41": "new_attr41_value_final"
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ],
        "5": [
            {
                "evcategory": "base",
                "eventtype": "added",
                "objtype": "TestObj1",
                "objpkey": 5,
                "objattrs": {
                    "obj_id": 5,
                    "name": "Object5",
                    "description": "Test Object5"
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            {
                "evcategory": "base",
                "eventtype": "added",
                "objtype": "TestObj1_local",
                "objpkey": 5,
                "objattrs": {
                    "obj_id": 5,
                    "name": "Object5",
                    "description": "Test Object5"
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ],
        "6": [
            {
                "evcategory": "base",
                "eventtype": "removed",
                "objtype": "TestObj1",
                "objpkey": 1,
                "objattrs": {},
                "step": 0,
                "isPartiallyProcessed": false
            },
            {
                "evcategory": "base",
                "eventtype": "removed",
                "objtype": "TestObj1_local",
                "objpkey": 1,
                "objattrs": {},
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ],
        "10": [
            null,
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1_local",
                "objpkey": 5,
                "objattrs": {
                    "added": {
                        "new_attr5": "new_attr5_value"
                    },
                    "modified": {
                        "name": "Object5_modified"
                    },
                    "removed": {
                        "description": null
                    }
                },
                "step": 1,
                "isPartiallyProcessed": true
            },
            "Fake error message"
        ],
        "12": [
            {
                "evcategory": "base",
                "eventtype": "removed",
                "objtype": "TestObj1",
                "objpkey": 3,
                "objattrs": {},
                "step": 0,
                "isPartiallyProcessed": false
            },
            {
                "evcategory": "base",
                "eventtype": "removed",
                "objtype": "TestObj1_local",
                "objpkey": 3,
                "objattrs": {},
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ],
        "14": [
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1",
                "objpkey": 5,
                "objattrs": {
                    "added": {
                        "new_attr51": "new_attr51_value_final"
                    },
                    "modified": {
                        "name": "Object5_modified_final"
                    },
                    "removed": {
                        "description": null
                    }
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1_local",
                "objpkey": 5,
                "objattrs": {
                    "added": {
                        "new_attr51": "new_attr51_value_final"
                    },
                    "modified": {
                        "name": "Object5_modified_final"
                    },
                    "removed": {
                        "description": null
                    }
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ],
        "15": [
            {
                "evcategory": "base",
                "eventtype": "added",
                "objtype": "TestObj1",
                "objpkey": 3,
                "objattrs": {
                    "obj_id": 3,
                    "name": "Object3_v2",
                    "description": "Test Object3_v2"
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            {
                "evcategory": "base",
                "eventtype": "added",
                "objtype": "TestObj1_local",
                "objpkey": 3,
                "objattrs": {
                    "obj_id": 3,
                    "name": "Object3_v2",
                    "description": "Test Object3_v2"
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ],
        "16": [
            {
                "evcategory": "base",
                "eventtype": "removed",
                "objtype": "TestObj1",
                "objpkey": 5,
                "objattrs": {},
                "step": 0,
                "isPartiallyProcessed": false
            },
            {
                "evcategory": "base",
                "eventtype": "removed",
                "objtype": "TestObj1_local",
                "objpkey": 5,
                "objattrs": {},
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ],
        "17": [
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1",
                "objpkey": 3,
                "objattrs": {
                    "added": {
                        "new_attr34": "new_attr34_value"
                    },
                    "modified": {
                        "name": "Object3_v2_modified"
                    },
                    "removed": {
                        "description": null
                    }
                },
                "step": 1,
                "isPartiallyProcessed": true
            },
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1_local",
                "objpkey": 3,
                "objattrs": {
                    "added": {
                        "new_attr34": "new_attr34_value"
                    },
                    "modified": {
                        "name": "Object3_v2_modified"
                    },
                    "removed": {
                        "description": null
                    }
                },
                "step": 1,
                "isPartiallyProcessed": true
            },
            "Fake error message"
        ],
        "18": [
            {
                "evcategory": "base",
                "eventtype": "added",
                "objtype": "TestObj1",
                "objpkey": 5,
                "objattrs": {
                    "obj_id": 5,
                    "name": "Object5 new",
                    "description": "Test Object5 new"
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            {
                "evcategory": "base",
                "eventtype": "added",
                "objtype": "TestObj1_local",
                "objpkey": 5,
                "objattrs": {
                    "obj_id": 5,
                    "name": "Object5 new",
                    "description": "Test Object5 new"
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ]
    }
}"""

    queueremediatedmaximumjson = """{
    "_queue": {
        "2": [
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1",
                "objpkey": 2,
                "objattrs": {
                    "added": {
                        "new_attr20": "new_attr20_value"
                    },
                    "modified": {
                        "name": "Object2_modified_final"
                    },
                    "removed": {
                        "new_attr2": null
                    }
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1_local",
                "objpkey": 2,
                "objattrs": {
                    "added": {
                        "description": "Test Object2",
                        "new_attr20": "new_attr20_value"
                    },
                    "modified": {
                        "name": "Object2_modified_final"
                    },
                    "removed": {}
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ],
        "3": [
            {
                "evcategory": "base",
                "eventtype": "removed",
                "objtype": "TestObj1",
                "objpkey": 3,
                "objattrs": {},
                "step": 0,
                "isPartiallyProcessed": false
            },
            {
                "evcategory": "base",
                "eventtype": "removed",
                "objtype": "TestObj1_local",
                "objpkey": 3,
                "objattrs": {},
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ],
        "4": [
            {
                "evcategory": "base",
                "eventtype": "added",
                "objtype": "TestObj1",
                "objpkey": 4,
                "objattrs": {
                    "obj_id": 4,
                    "name": "Object4_modified_final",
                    "new_attr41": "new_attr41_value_final"
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            {
                "evcategory": "base",
                "eventtype": "added",
                "objtype": "TestObj1_local",
                "objpkey": 4,
                "objattrs": {
                    "obj_id": 4,
                    "name": "Object4_modified_final",
                    "new_attr4": "new_attr4_value",
                    "new_attr41": "new_attr41_value_final"
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ],
        "5": [
            {
                "evcategory": "base",
                "eventtype": "added",
                "objtype": "TestObj1",
                "objpkey": 5,
                "objattrs": {
                    "obj_id": 5,
                    "name": "Object5",
                    "description": "Test Object5"
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            {
                "evcategory": "base",
                "eventtype": "added",
                "objtype": "TestObj1_local",
                "objpkey": 5,
                "objattrs": {
                    "obj_id": 5,
                    "name": "Object5",
                    "description": "Test Object5"
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ],
        "6": [
            null,
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1_local",
                "objpkey": 5,
                "objattrs": {
                    "added": {
                        "new_attr5": "new_attr5_value"
                    },
                    "modified": {
                        "name": "Object5_modified"
                    },
                    "removed": {
                        "description": null
                    }
                },
                "step": 1,
                "isPartiallyProcessed": true
            },
            "Fake error message"
        ],
        "7": [
            {
                "evcategory": "base",
                "eventtype": "removed",
                "objtype": "TestObj1",
                "objpkey": 5,
                "objattrs": {},
                "step": 0,
                "isPartiallyProcessed": false
            },
            {
                "evcategory": "base",
                "eventtype": "removed",
                "objtype": "TestObj1_local",
                "objpkey": 5,
                "objattrs": {},
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ],
        "8": [
            {
                "evcategory": "base",
                "eventtype": "added",
                "objtype": "TestObj1",
                "objpkey": 3,
                "objattrs": {
                    "obj_id": 3,
                    "name": "Object3_v2",
                    "description": "Test Object3_v2"
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            {
                "evcategory": "base",
                "eventtype": "added",
                "objtype": "TestObj1_local",
                "objpkey": 3,
                "objattrs": {
                    "obj_id": 3,
                    "name": "Object3_v2",
                    "description": "Test Object3_v2"
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ],
        "9": [
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1",
                "objpkey": 3,
                "objattrs": {
                    "added": {
                        "new_attr34": "new_attr34_value"
                    },
                    "modified": {
                        "name": "Object3_v2_modified"
                    },
                    "removed": {
                        "description": null
                    }
                },
                "step": 1,
                "isPartiallyProcessed": true
            },
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1_local",
                "objpkey": 3,
                "objattrs": {
                    "added": {
                        "new_attr34": "new_attr34_value"
                    },
                    "modified": {
                        "name": "Object3_v2_modified"
                    },
                    "removed": {
                        "description": null
                    }
                },
                "step": 1,
                "isPartiallyProcessed": true
            },
            "Fake error message"
        ],
        "10": [
            {
                "evcategory": "base",
                "eventtype": "added",
                "objtype": "TestObj1",
                "objpkey": 5,
                "objattrs": {
                    "obj_id": 5,
                    "name": "Object5 new",
                    "description": "Test Object5 new"
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            {
                "evcategory": "base",
                "eventtype": "added",
                "objtype": "TestObj1_local",
                "objpkey": 5,
                "objattrs": {
                    "obj_id": 5,
                    "name": "Object5 new",
                    "description": "Test Object5 new"
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ]
    }
}"""

    queueremediatedmaximumatimportjson = """{
    "_queue": {
        "2": [
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1",
                "objpkey": 2,
                "objattrs": {
                    "added": {
                        "new_attr20": "new_attr20_value"
                    },
                    "modified": {
                        "name": "Object2_modified_final"
                    },
                    "removed": {
                        "new_attr2": null
                    }
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1_local",
                "objpkey": 2,
                "objattrs": {
                    "added": {
                        "description": "Test Object2",
                        "new_attr20": "new_attr20_value"
                    },
                    "modified": {
                        "name": "Object2_modified_final"
                    },
                    "removed": {}
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ],
        "3": [
            {
                "evcategory": "base",
                "eventtype": "removed",
                "objtype": "TestObj1",
                "objpkey": 3,
                "objattrs": {},
                "step": 0,
                "isPartiallyProcessed": false
            },
            {
                "evcategory": "base",
                "eventtype": "removed",
                "objtype": "TestObj1_local",
                "objpkey": 3,
                "objattrs": {},
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ],
        "4": [
            {
                "evcategory": "base",
                "eventtype": "added",
                "objtype": "TestObj1",
                "objpkey": 4,
                "objattrs": {
                    "obj_id": 4,
                    "name": "Object4_modified_final",
                    "new_attr41": "new_attr41_value_final"
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            {
                "evcategory": "base",
                "eventtype": "added",
                "objtype": "TestObj1_local",
                "objpkey": 4,
                "objattrs": {
                    "obj_id": 4,
                    "name": "Object4_modified_final",
                    "new_attr4": "new_attr4_value",
                    "new_attr41": "new_attr41_value_final"
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ],
        "5": [
            {
                "evcategory": "base",
                "eventtype": "added",
                "objtype": "TestObj1",
                "objpkey": 5,
                "objattrs": {
                    "obj_id": 5,
                    "name": "Object5",
                    "description": "Test Object5"
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            {
                "evcategory": "base",
                "eventtype": "added",
                "objtype": "TestObj1_local",
                "objpkey": 5,
                "objattrs": {
                    "obj_id": 5,
                    "name": "Object5",
                    "description": "Test Object5"
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ],
        "10": [
            null,
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1_local",
                "objpkey": 5,
                "objattrs": {
                    "added": {
                        "new_attr5": "new_attr5_value"
                    },
                    "modified": {
                        "name": "Object5_modified"
                    },
                    "removed": {
                        "description": null
                    }
                },
                "step": 1,
                "isPartiallyProcessed": true
            },
            "Fake error message"
        ],
        "14": [
            {
                "evcategory": "base",
                "eventtype": "removed",
                "objtype": "TestObj1",
                "objpkey": 5,
                "objattrs": {},
                "step": 0,
                "isPartiallyProcessed": false
            },
            {
                "evcategory": "base",
                "eventtype": "removed",
                "objtype": "TestObj1_local",
                "objpkey": 5,
                "objattrs": {},
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ],
        "15": [
            {
                "evcategory": "base",
                "eventtype": "added",
                "objtype": "TestObj1",
                "objpkey": 3,
                "objattrs": {
                    "obj_id": 3,
                    "name": "Object3_v2",
                    "description": "Test Object3_v2"
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            {
                "evcategory": "base",
                "eventtype": "added",
                "objtype": "TestObj1_local",
                "objpkey": 3,
                "objattrs": {
                    "obj_id": 3,
                    "name": "Object3_v2",
                    "description": "Test Object3_v2"
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ],
        "17": [
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1",
                "objpkey": 3,
                "objattrs": {
                    "added": {
                        "new_attr34": "new_attr34_value"
                    },
                    "modified": {
                        "name": "Object3_v2_modified"
                    },
                    "removed": {
                        "description": null
                    }
                },
                "step": 1,
                "isPartiallyProcessed": true
            },
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1_local",
                "objpkey": 3,
                "objattrs": {
                    "added": {
                        "new_attr34": "new_attr34_value"
                    },
                    "modified": {
                        "name": "Object3_v2_modified"
                    },
                    "removed": {
                        "description": null
                    }
                },
                "step": 1,
                "isPartiallyProcessed": true
            },
            "Fake error message"
        ],
        "18": [
            {
                "evcategory": "base",
                "eventtype": "added",
                "objtype": "TestObj1",
                "objpkey": 5,
                "objattrs": {
                    "obj_id": 5,
                    "name": "Object5 new",
                    "description": "Test Object5 new"
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            {
                "evcategory": "base",
                "eventtype": "added",
                "objtype": "TestObj1_local",
                "objpkey": 5,
                "objattrs": {
                    "obj_id": 5,
                    "name": "Object5 new",
                    "description": "Test Object5 new"
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ]
    }
}"""

    mergemodifyqueue = {
        "1": [
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1",
                "objpkey": 1,
                "objattrs": {
                    "added": {
                        "added_1": "val_added_1",
                        "added_2": "val_added_2",
                        "added_3": "val_added_3",
                    },
                    "modified": {
                        "modified_1": "val_modified_1",
                        "modified_2": "val_modified_2",
                        "modified_3": "val_modified_3",
                    },
                    "removed": {
                        "removed_1": None,
                        "removed_2": None,
                    },
                },
                "step": 0,
                "isPartiallyProcessed": False,
            },
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1_local",
                "objpkey": 1,
                "objattrs": {
                    "added": {
                        "local_added_1": "val_local_added_1",
                        "local_added_2": "val_local_added_2",
                        "local_added_3": "val_local_added_3",
                    },
                    "modified": {
                        "local_modified_1": "val_local_modified_1",
                        "local_modified_2": "val_local_modified_2",
                        "local_modified_3": "val_local_modified_3",
                    },
                    "removed": {
                        "local_removed_1": None,
                        "local_removed_2": None,
                    },
                },
                "step": 0,
                "isPartiallyProcessed": False,
            },
            "Fake error message",
        ],
        "2": [
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1",
                "objpkey": 1,
                "objattrs": {
                    "added": {
                        "new_added_1": "val_new_added_1",
                        "removed_2": "val_removed_2",
                    },
                    "modified": {
                        "new_modified_1": "val_new_modified_1",
                        "added_2": "new_val_added_2",
                        "modified_2": "new_val_modified_2",
                    },
                    "removed": {
                        "new_removed_1": None,
                        "added_3": None,
                        "modified_3": None,
                    },
                },
                "step": 0,
                "isPartiallyProcessed": False,
            },
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1_local",
                "objpkey": 1,
                "objattrs": {
                    "added": {
                        "new_local_added_1": "val_new_local_added_1",
                        "local_removed_2": "val_local_removed_2",
                    },
                    "modified": {
                        "new_local_modified_1": "val_new_local_modified_1",
                        "local_added_2": "new_val_local_added_2",
                        "local_modified_2": "new_val_local_modified_2",
                    },
                    "removed": {
                        "local_new_removed_1": None,
                        "local_added_3": None,
                        "local_modified_3": None,
                    },
                },
                "step": 0,
                "isPartiallyProcessed": False,
            },
            "Fake error message",
        ],
    }

    mergemodifyqueue_remediatedjson = """{
    "_queue": {
        "1": [
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1",
                "objpkey": 1,
                "objattrs": {
                    "added": {
                        "added_1": "val_added_1",
                        "added_2": "new_val_added_2",
                        "new_added_1": "val_new_added_1",
                        "removed_2": "val_removed_2"
                    },
                    "modified": {
                        "modified_1": "val_modified_1",
                        "modified_2": "new_val_modified_2",
                        "new_modified_1": "val_new_modified_1"
                    },
                    "removed": {
                        "removed_1": null,
                        "new_removed_1": null,
                        "modified_3": null
                    }
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            {
                "evcategory": "base",
                "eventtype": "modified",
                "objtype": "TestObj1_local",
                "objpkey": 1,
                "objattrs": {
                    "added": {
                        "local_added_1": "val_local_added_1",
                        "local_added_2": "new_val_local_added_2",
                        "new_local_added_1": "val_new_local_added_1",
                        "local_removed_2": "val_local_removed_2"
                    },
                    "modified": {
                        "local_modified_1": "val_local_modified_1",
                        "local_modified_2": "new_val_local_modified_2",
                        "new_local_modified_1": "val_new_local_modified_1"
                    },
                    "removed": {
                        "local_removed_1": null,
                        "local_new_removed_1": null,
                        "local_modified_3": null
                    }
                },
                "step": 0,
                "isPartiallyProcessed": false
            },
            "Fake error message"
        ]
    }
}"""

    singleAddedEventJson = """
        {
            "evcategory": "base",
            "eventtype": "added",
            "objtype": "TestObj1",
            "objpkey": 1,
            "objattrs": {"obj_id": 1},
            "step": 0,
            "isPartiallyProcessed": false
        }"""
    singleModifiedEventJson = """
        {
            "evcategory": "base",
            "eventtype": "modified",
            "objtype": "TestObj1",
            "objpkey": 1,
            "objattrs": {
                "added": {},
                "modified": {"attr": "value"},
                "removed": {}
            },
            "step": 0,
            "isPartiallyProcessed": false
        }"""
    singleRemovedEventJson = """
        {
            "evcategory": "base",
            "eventtype": "removed",
            "objtype": "TestObj1",
            "objpkey": 1,
            "objattrs": {},
            "step": 0,
            "isPartiallyProcessed": false
        }"""
    singleUnexpectedEventJson = """
        {
            "evcategory": "base",
            "eventtype": "unexpected",
            "objtype": "TestObj1",
            "objpkey": 1,
            "objattrs": {"obj_id": 1},
            "step": 0,
            "isPartiallyProcessed": false
        }"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

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

        self.singleAddedEvent = Event.from_json(self.singleAddedEventJson)
        self.singleModifiedEvent = Event.from_json(self.singleModifiedEventJson)
        self.singleRemovedEvent = Event.from_json(self.singleRemovedEventJson)
        self.singleUnexpectedEvent = Event.from_json(self.singleUnexpectedEventJson)

    def tearDown(self):
        super().tearDown()
        self.purgeTmpdirContent()

    def test_init(self):
        eq = ErrorQueue(typesMapping=self.typesMapping, autoremediate="disabled")
        self.assertEqual(len(eq), 0)

    def test_init_from_invalid_json(self):
        self.assertRaises(
            HermesInvalidErrorQueueJSONError,
            ErrorQueue,
            typesMapping=self.typesMapping,
            autoremediate="disabled",
            from_json_dict={"queue": self.queue},  # key should be "_queue"
        )

    def test_fill_queue_twice_with_same_eventnumber(self):
        eq = ErrorQueue(typesMapping=self.typesMapping, autoremediate="disabled")

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
        eq = ErrorQueue(typesMapping=self.typesMapping, autoremediate="disabled")

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
        eq = ErrorQueue(typesMapping=self.typesMapping, autoremediate="disabled")
        for evremotejson, evlocaljson, errmsg in self.queue.values():
            evremote = (
                None if evremotejson is None else Event(from_json_dict=evremotejson)
            )
            evlocal = Event(from_json_dict=evlocaljson)
            eq.append(evremote, evlocal, errmsg)
        self.assertEqual(len(eq), 18)  # Queue contains 18 items
        self.assertEqual(len(list(eq.allEvents())), 18)  # Queue contains 18 items
        self.assertEqual(len(list(iter(eq))), 5)  # 5 different objects are in queue
        self.assertEqual(eq.to_json(), self.queuejson)

    def test_fill_queue_fromjson_noremediate(self):
        eq = ErrorQueue(
            typesMapping=self.typesMapping,
            autoremediate="disabled",
            from_json_dict={"_queue": self.queue},
        )
        self.assertEqual(len(eq), 18)  # Queue contains 18 items
        self.assertEqual(len(list(eq.allEvents())), 18)  # Queue contains 18 items
        self.assertEqual(len(list(iter(eq))), 5)  # 5 different objects are in queue
        self.assertEqual(eq.to_json(), self.queuejson)

    def test_fill_queue_remediate_conservative(self):
        eq = ErrorQueue(typesMapping=self.typesMapping, autoremediate="conservative")
        for evremotejson, evlocaljson, errmsg in self.queue.values():
            evremote = (
                None if evremotejson is None else Event(from_json_dict=evremotejson)
            )
            evlocal = Event(from_json_dict=evlocaljson)
            eq.append(evremote, evlocal, errmsg)
        self.assertEqual(len(eq), 13)  # Queue contains 13 items
        self.assertEqual(len(list(eq.allEvents())), 13)  # Queue contains 13 items
        self.assertEqual(len(list(iter(eq))), 5)  # 5 different objects are in queue
        self.assertEqual(eq.to_json(), self.queueremediatedconservativejson)

    def test_fill_queue_fromjson_remediate_conservative(self):
        eq = ErrorQueue(
            typesMapping=self.typesMapping,
            autoremediate="conservative",
            from_json_dict={"_queue": self.queue},
        )
        self.assertEqual(len(eq), 13)  # Queue contains 13 items
        self.assertEqual(len(list(eq.allEvents())), 13)  # Queue contains 13 items
        self.assertEqual(len(list(iter(eq))), 5)  # 5 different objects are in queue
        self.assertEqual(eq.to_json(), self.queueremediatedconservativeatimportjson)

    def test_fill_queue_remediate_maximum_with_fallback_for_obj3(self):
        # As no datasource is provided, obj3 will be remediated with conservative policy
        # The case with a datasource provided is tested in functional tests
        eq = ErrorQueue(typesMapping=self.typesMapping, autoremediate="maximum")

        with self.assertLogs(__hermes__.logger, level="INFO") as cm:
            for evremotejson, evlocaljson, errmsg in self.queue.values():
                evremote = (
                    None if evremotejson is None else Event(from_json_dict=evremotejson)
                )
                evlocal = Event(from_json_dict=evlocaljson)
                eq.append(evremote, evlocal, errmsg)
        self.assertEqual(len(eq), 9)  # Queue contains 9 items
        self.assertEqual(len(list(eq.allEvents())), 9)  # Queue contains 9 items
        self.assertEqual(len(list(iter(eq))), 4)  # 4 different objects are in queue
        self.assertEqual(eq.to_json(), self.queueremediatedmaximumjson)
        # Ensure fallback was used
        self.assertIn(
            "INFO:hermes-unit-tests:Unable to merge removed prevEvent="
            "<Event(TestObj1_removed[3])> with added lastEvent.objattrs="
            "{'obj_id': 3, 'name': 'Object3_v2', 'description': 'Test Object3_v2'},"
            " as no datasource is available. Fallback to 'conservative' mode.",
            cm.output,
        )
        self.assertIn(
            "INFO:hermes-unit-tests:Unable to merge removed prevEvent="
            "<Event(TestObj1_local_removed[3])> with added lastEvent.objattrs="
            "{'obj_id': 3, 'name': 'Object3_v2', 'description': 'Test Object3_v2'},"
            " as no datasource is available. Fallback to 'conservative' mode.",
            cm.output,
        )
        self.assertIn(
            "INFO:hermes-unit-tests:Unable to merge removed prevEvent="
            "<Event(TestObj1_removed[5])> with added lastEvent.objattrs="
            "{'obj_id': 5, 'name': 'Object5 new', 'description': 'Test Object5 new'},"
            " as no datasource is available. Fallback to 'conservative' mode.",
            cm.output,
        )
        self.assertIn(
            "INFO:hermes-unit-tests:Unable to merge removed prevEvent="
            "<Event(TestObj1_local_removed[5])> with added lastEvent.objattrs="
            "{'obj_id': 5, 'name': 'Object5 new', 'description': 'Test Object5 new'},"
            " as no datasource is available. Fallback to 'conservative' mode.",
            cm.output,
        )

    def test_fill_queue_fromjson_remediate_maximum_with_fallback_for_obj3(self):
        # As no datasource is provided, obj3 will be remediated with conservative policy
        # The case with a datasource provided is tested in functional tests
        with self.assertLogs(__hermes__.logger, level="INFO") as cm:
            eq = ErrorQueue(
                typesMapping=self.typesMapping,
                autoremediate="maximum",
                from_json_dict={"_queue": self.queue},
            )
        self.assertEqual(len(eq), 9)  # Queue contains 9 items
        self.assertEqual(len(list(eq.allEvents())), 9)  # Queue contains 9 items
        self.assertEqual(len(list(iter(eq))), 4)  # 4 different objects are in queue
        self.assertEqual(eq.to_json(), self.queueremediatedmaximumatimportjson)
        # Ensure fallback was used
        self.assertIn(
            "INFO:hermes-unit-tests:Unable to merge removed prevEvent="
            "<Event(TestObj1_removed[3])> with added lastEvent.objattrs="
            "{'obj_id': 3, 'name': 'Object3_v2', 'description': 'Test Object3_v2'},"
            " as no datasource is available. Fallback to 'conservative' mode.",
            cm.output,
        )
        self.assertIn(
            "INFO:hermes-unit-tests:Unable to merge removed prevEvent="
            "<Event(TestObj1_local_removed[3])> with added lastEvent.objattrs="
            "{'obj_id': 3, 'name': 'Object3_v2', 'description': 'Test Object3_v2'},"
            " as no datasource is available. Fallback to 'conservative' mode.",
            cm.output,
        )
        self.assertIn(
            "INFO:hermes-unit-tests:Unable to merge removed prevEvent="
            "<Event(TestObj1_removed[5])> with added lastEvent.objattrs="
            "{'obj_id': 5, 'name': 'Object5 new', 'description': 'Test Object5 new'},"
            " as no datasource is available. Fallback to 'conservative' mode.",
            cm.output,
        )
        self.assertIn(
            "INFO:hermes-unit-tests:Unable to merge removed prevEvent="
            "<Event(TestObj1_local_removed[5])> with added lastEvent.objattrs="
            "{'obj_id': 5, 'name': 'Object5 new', 'description': 'Test Object5 new'},"
            " as no datasource is available. Fallback to 'conservative' mode.",
            cm.output,
        )

    def test_invalid_remediation_cases(self):
        invalidcouples = [
            (self.singleAddedEvent, self.singleAddedEvent),
            (self.singleRemovedEvent, self.singleModifiedEvent),
            (self.singleRemovedEvent, self.singleRemovedEvent),
            (self.singleModifiedEvent, self.singleAddedEvent),
        ]
        for prev, last in invalidcouples:
            eq = ErrorQueue(
                typesMapping={"TestObj1": "TestObj1"}, autoremediate="maximum"
            )
            eq.append(prev, prev, "Dummy error msg")
            self.assertRaisesRegex(
                AssertionError,
                f"BUG \\: trying to merge a {last.eventtype} event with a"
                f" previous {prev.eventtype} event, this should never happen\\..*$",
                eq.append,
                last,
                last,
                "Dummy error msg",
            )

    def test_unexpected_eventtype_in_remediation(self):
        unexpectedcouples = [
            (self.singleModifiedEvent, self.singleUnexpectedEvent),
            (self.singleUnexpectedEvent, self.singleModifiedEvent),
        ]
        for prevEvent, lastEvent in unexpectedcouples:
            eq = ErrorQueue(
                typesMapping={"TestObj1": "TestObj1"}, autoremediate="maximum"
            )
            eq.append(prevEvent, prevEvent, "Dummy error msg")
            with self.assertRaises(AssertionError) as cm:
                eq.append(lastEvent, lastEvent, "Dummy error msg")
            self.assertEqual(
                str(cm.exception),
                "BUG : unexpected eventtype met when trying to merge two events "
                f"{lastEvent=} {lastEvent.eventtype=} ; {prevEvent=}"
                f" {prevEvent.eventtype=}",
            )

    def test_remediation_inconsistency_between_merge_results(self):
        eq = ErrorQueue(
            typesMapping={"TestObj1": "TestObj1"}, autoremediate="conservative"
        )
        eq.append(self.singleAddedEvent, self.singleAddedEvent, "Dummy error msg")

        self.assertRaisesRegex(
            AssertionError,
            "BUG \\: inconsistency between remote and local merge results \\: .*$",
            eq.append,
            self.singleModifiedEvent,
            self.singleRemovedEvent,
            "Dummy error msg",
        )

    def test_append_unknown_objtype(self):
        eq = ErrorQueue(typesMapping=self.typesMapping, autoremediate="disabled")
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
            "isPartiallyProcessed": False,
        }
        event = Event(from_json_dict=evjson)
        with self.assertLogs(__hermes__.logger, level="INFO") as cm:
            eq.append(event, event, "Fake error message")
        self.assertEqual(len(cm.output), 1)
        self.assertIn(
            "INFO:hermes-unit-tests:Ignore loading of remote event of unknown objtype"
            " UnknownTestObj",
            cm.output,
        )
        self.assertEqual(len(eq), 0)  # Queue should be empty

        with self.assertLogs(__hermes__.logger, level="INFO") as cm:
            eq.append(None, event, "Fake error message")
        self.assertEqual(len(cm.output), 1)
        self.assertIn(
            "INFO:hermes-unit-tests:Ignore loading of local event of unknown objtype"
            " UnknownTestObj",
            cm.output,
        )
        self.assertEqual(len(eq), 0)  # Queue should be empty

    def test_updateErrorMsg_invalid_eventNumber(self):
        eq = ErrorQueue(
            typesMapping=self.typesMapping,
            autoremediate="disabled",
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
            autoremediate="disabled",
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
            autoremediate="disabled",
            from_json_dict={"_queue": self.queue},
        )

        queuelen = len(eq)
        eq.remove(100, ignoreMissingEventNumber=True)
        self.assertEqual(queuelen, len(eq))

    def test_remove_invalid_eventNumber_exception(self):
        eq = ErrorQueue(
            typesMapping=self.typesMapping,
            autoremediate="disabled",
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
            autoremediate="disabled",
            from_json_dict={"_queue": self.queue},
        )
        self.assertEqual(len(eq), 18)
        # 2 events
        eq.purgeAllEvents("TestObj1", 1, isLocalObjtype=False)
        self.assertEqual(len(eq), 16)
        # 3 events (1 remote, 2 local)
        eq.purgeAllEvents("TestObj1", 2, isLocalObjtype=False)
        self.assertEqual(len(eq), 13)
        # 5 events
        eq.purgeAllEvents("TestObj1", 3, isLocalObjtype=False)
        self.assertEqual(len(eq), 8)
        # 3 events (2 remote, 1 local)
        eq.purgeAllEvents("TestObj1", 4, isLocalObjtype=False)
        self.assertEqual(len(eq), 5)
        # 5 events (4 remote, 1 local)
        eq.purgeAllEvents("TestObj1", 5, isLocalObjtype=False)
        self.assertEqual(len(eq), 0)

        eq = ErrorQueue(
            typesMapping=self.typesMapping,
            autoremediate="disabled",
            from_json_dict={"_queue": self.queue},
        )
        self.assertEqual(len(eq), 18)
        # 3 events (2 remote, 1 local)
        eq.purgeAllEvents("TestObj1_local", 4, isLocalObjtype=True)
        self.assertEqual(len(eq), 15)

    def test_iter_with_remove(self):
        eq = ErrorQueue(
            typesMapping=self.typesMapping,
            autoremediate="disabled",
            from_json_dict={"_queue": self.queue},
        )

        total = 0
        for item in iter(eq):
            total += 1
        self.assertEqual(total, 5)  # 5 different objects in queue

        count = 0
        for item in iter(eq):
            count += 1
            eq.purgeAllEvents("TestObj1_local", 4, isLocalObjtype=True)
        self.assertEqual(count, 4)  # 4 remaining different objects in queue

    def test_allEvents_with_remove(self):
        eq = ErrorQueue(
            typesMapping=self.typesMapping,
            autoremediate="disabled",
            from_json_dict={"_queue": self.queue},
        )

        total = 0
        for item in eq.allEvents():
            total += 1
        self.assertEqual(total, 18)  # 18 events in queue

        count = 0
        for item in eq.allEvents():
            count += 1
            eq.purgeAllEvents("TestObj1_local", 4, isLocalObjtype=True)
        self.assertEqual(count, 15)  # 15 remaining events in queue

    def test_containsObjectByEvent(self):
        eq = ErrorQueue(
            typesMapping=self.typesMapping,
            autoremediate="disabled",
            from_json_dict={"_queue": self.queue},
        )

        ev = Event(from_json_dict=self.queue["8"][0])
        self.assertTrue(eq.containsObjectByEvent(ev, isLocalEvent=False))
        eq.purgeAllEvents("TestObj1", 3, isLocalObjtype=False)
        self.assertFalse(eq.containsObjectByEvent(ev, isLocalEvent=False))

    def test_merge_two_modified_events(self):
        eq = ErrorQueue(
            typesMapping=self.typesMapping,
            autoremediate="conservative",
            from_json_dict={"_queue": self.mergemodifyqueue},
        )
        self.assertEqual(len(eq), 1)  # Queue contains 1 item
        self.assertEqual(len(list(eq.allEvents())), 1)  # Queue contains 1 item
        self.assertEqual(eq.to_json(), self.mergemodifyqueue_remediatedjson)
