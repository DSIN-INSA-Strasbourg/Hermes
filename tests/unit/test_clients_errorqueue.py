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
            },
            "Fake error message",
        ],
        "5": [
            {
                "evcategory": "base",
                "eventtype": "removed",
                "objtype": "TestObj1",
                "objpkey": 1,
                "objattrs": {},
                "step": 0,
            },
            {
                "evcategory": "base",
                "eventtype": "removed",
                "objtype": "TestObj1_local",
                "objpkey": 1,
                "objattrs": {},
                "step": 0,
            },
            "Fake error message",
        ],
        "6": [
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
            },
            "Fake error message",
        ],
        "7": [
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
            },
            "Fake error message",
        ],
        "8": [
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
            },
            "Fake error message",
        ],
        "9": [
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
            },
            "Fake error message",
        ],
        "10": [
            {
                "evcategory": "base",
                "eventtype": "removed",
                "objtype": "TestObj1",
                "objpkey": 3,
                "objattrs": {},
                "step": 0,
            },
            {
                "evcategory": "base",
                "eventtype": "removed",
                "objtype": "TestObj1_local",
                "objpkey": 3,
                "objattrs": {},
                "step": 0,
            },
            "Fake error message",
        ],
        "11": [
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
            },
            "Fake error message",
        ],
        "12": [
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
                "step": 0
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
                "step": 0
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
                "step": 0
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
                "step": 0
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
                "step": 0
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
                "step": 0
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
                "step": 0
            },
            "Fake error message"
        ],
        "5": [
            {
                "evcategory": "base",
                "eventtype": "removed",
                "objtype": "TestObj1",
                "objpkey": 1,
                "objattrs": {},
                "step": 0
            },
            {
                "evcategory": "base",
                "eventtype": "removed",
                "objtype": "TestObj1_local",
                "objpkey": 1,
                "objattrs": {},
                "step": 0
            },
            "Fake error message"
        ],
        "6": [
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
                "step": 0
            },
            "Fake error message"
        ],
        "7": [
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
                "step": 0
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
                "step": 0
            },
            "Fake error message"
        ],
        "8": [
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
                "step": 0
            },
            "Fake error message"
        ],
        "9": [
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
                "step": 0
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
                "step": 0
            },
            "Fake error message"
        ],
        "10": [
            {
                "evcategory": "base",
                "eventtype": "removed",
                "objtype": "TestObj1",
                "objpkey": 3,
                "objattrs": {},
                "step": 0
            },
            {
                "evcategory": "base",
                "eventtype": "removed",
                "objtype": "TestObj1_local",
                "objpkey": 3,
                "objattrs": {},
                "step": 0
            },
            "Fake error message"
        ],
        "11": [
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
                "step": 0
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
                "step": 0
            },
            "Fake error message"
        ],
        "12": [
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
                "step": 0
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
                "step": 0
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
                "step": 0
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
                "step": 0
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
                "step": 0
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
                    "removed": {
                        "description": null
                    }
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
                "step": 0
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
                "step": 0
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
                "step": 0
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
                "step": 0
            },
            "Fake error message"
        ],
        "5": [
            {
                "evcategory": "base",
                "eventtype": "removed",
                "objtype": "TestObj1",
                "objpkey": 1,
                "objattrs": {},
                "step": 0
            },
            {
                "evcategory": "base",
                "eventtype": "removed",
                "objtype": "TestObj1_local",
                "objpkey": 1,
                "objattrs": {},
                "step": 0
            },
            "Fake error message"
        ],
        "6": [
            {
                "evcategory": "base",
                "eventtype": "removed",
                "objtype": "TestObj1",
                "objpkey": 3,
                "objattrs": {},
                "step": 0
            },
            {
                "evcategory": "base",
                "eventtype": "removed",
                "objtype": "TestObj1_local",
                "objpkey": 3,
                "objattrs": {},
                "step": 0
            },
            "Fake error message"
        ],
        "7": [
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
                "step": 0
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
                "step": 0
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
                "step": 0
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
                "step": 0
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
                "step": 0
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
                    "removed": {
                        "description": null
                    }
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
                "step": 0
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
                "step": 0
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
                "step": 0
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
                "step": 0
            },
            "Fake error message"
        ],
        "5": [
            {
                "evcategory": "base",
                "eventtype": "removed",
                "objtype": "TestObj1",
                "objpkey": 1,
                "objattrs": {},
                "step": 0
            },
            {
                "evcategory": "base",
                "eventtype": "removed",
                "objtype": "TestObj1_local",
                "objpkey": 1,
                "objattrs": {},
                "step": 0
            },
            "Fake error message"
        ],
        "10": [
            {
                "evcategory": "base",
                "eventtype": "removed",
                "objtype": "TestObj1",
                "objpkey": 3,
                "objattrs": {},
                "step": 0
            },
            {
                "evcategory": "base",
                "eventtype": "removed",
                "objtype": "TestObj1_local",
                "objpkey": 3,
                "objattrs": {},
                "step": 0
            },
            "Fake error message"
        ],
        "12": [
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
                "step": 0
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
                "step": 0
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
                "step": 0
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
                    "removed": {
                        "description": null
                    }
                },
                "step": 0
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
                "step": 0
            },
            {
                "evcategory": "base",
                "eventtype": "removed",
                "objtype": "TestObj1_local",
                "objpkey": 3,
                "objattrs": {},
                "step": 0
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
                "step": 0
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
                "step": 0
            },
            "Fake error message"
        ],
        "5": [
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
                "step": 0
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
                "step": 0
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
                "step": 0
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
                    "removed": {
                        "description": null
                    }
                },
                "step": 0
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
                "step": 0
            },
            {
                "evcategory": "base",
                "eventtype": "removed",
                "objtype": "TestObj1_local",
                "objpkey": 3,
                "objattrs": {},
                "step": 0
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
                "step": 0
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
                "step": 0
            },
            "Fake error message"
        ],
        "12": [
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
                "step": 0
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
                "step": 0
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
            "step": 0
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
            "step": 0
        }"""
    singleRemovedEventJson = """
        {
            "evcategory": "base",
            "eventtype": "removed",
            "objtype": "TestObj1",
            "objpkey": 1,
            "objattrs": {},
            "step": 0
        }"""
    singleUnexpectedEventJson = """
        {
            "evcategory": "base",
            "eventtype": "unexpected",
            "objtype": "TestObj1",
            "objpkey": 1,
            "objattrs": {"obj_id": 1},
            "step": 0
        }"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def setUp(self):
        super().setUp()
        logging.disable(logging.NOTSET)
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
        self.assertEqual(len(eq), 12)  # Queue contains 12 items
        self.assertEqual(len(list(eq.allEvents())), 12)  # Queue contains 12 items
        self.assertEqual(
            len(list(iter(eq))), 4
        )  # Only 4 different objects are in queue
        self.assertEqual(eq.to_json(), self.queuejson)

    def test_fill_queue_fromjson_noremediate(self):
        eq = ErrorQueue(
            typesMapping=self.typesMapping,
            autoremediate="disabled",
            from_json_dict={"_queue": self.queue},
        )
        self.assertEqual(len(eq), 12)  # Queue contains 12 items
        self.assertEqual(len(list(eq.allEvents())), 12)  # Queue contains 12 items
        self.assertEqual(
            len(list(iter(eq))), 4
        )  # Only 4 different objects are in queue
        self.assertEqual(eq.to_json(), self.queuejson)

    def test_fill_queue_remediate_conservative(self):
        eq = ErrorQueue(typesMapping=self.typesMapping, autoremediate="conservative")
        for evremotejson, evlocaljson, errmsg in self.queue.values():
            evremote = (
                None if evremotejson is None else Event(from_json_dict=evremotejson)
            )
            evlocal = Event(from_json_dict=evlocaljson)
            eq.append(evremote, evlocal, errmsg)
        self.assertEqual(len(eq), 7)  # Queue contains 7 items
        self.assertEqual(len(list(eq.allEvents())), 7)  # Queue contains 7 items
        self.assertEqual(
            len(list(iter(eq))), 4
        )  # Only 4 different objects are in queue
        self.assertEqual(eq.to_json(), self.queueremediatedconservativejson)

    def test_fill_queue_fromjson_remediate_conservative(self):
        eq = ErrorQueue(
            typesMapping=self.typesMapping,
            autoremediate="conservative",
            from_json_dict={"_queue": self.queue},
        )
        self.assertEqual(len(eq), 7)  # Queue contains 7 items
        self.assertEqual(len(list(eq.allEvents())), 7)  # Queue contains 7 items
        self.assertEqual(
            len(list(iter(eq))), 4
        )  # Only 4 different objects are in queue
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
        self.assertEqual(len(eq), 4)  # Queue contains 4 items
        self.assertEqual(len(list(eq.allEvents())), 4)  # Queue contains 4 items
        self.assertEqual(
            len(list(iter(eq))), 3
        )  # Only 3 different objects are in queue
        self.assertEqual(eq.to_json(), self.queueremediatedmaximumjson)
        # Ensure fallback was used
        self.assertEqual(
            cm.output[-2],
            "INFO:hermes-unit-tests:Unable to merge removed prevEvent=<Event(TestObj1_removed[3])> with added lastEvent.objattrs={'obj_id': 3, 'name': 'Object3_v2', 'description': 'Test Object3_v2'}, as no datasource is available. Fallback to 'conservative' mode.",
        )
        self.assertEqual(
            cm.output[-1],
            "INFO:hermes-unit-tests:Unable to merge removed prevEvent=<Event(TestObj1_local_removed[3])> with added lastEvent.objattrs={'obj_id': 3, 'name': 'Object3_v2', 'description': 'Test Object3_v2'}, as no datasource is available. Fallback to 'conservative' mode.",
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
        self.assertEqual(len(eq), 4)  # Queue contains 4 items
        self.assertEqual(len(list(eq.allEvents())), 4)  # Queue contains 4 items
        self.assertEqual(
            len(list(iter(eq))), 3
        )  # Only 3 different objects are in queue
        self.assertEqual(eq.to_json(), self.queueremediatedmaximumatimportjson)
        # Ensure fallback was used
        self.assertEqual(
            cm.output[-2],
            "INFO:hermes-unit-tests:Unable to merge removed prevEvent=<Event(TestObj1_removed[3])> with added lastEvent.objattrs={'obj_id': 3, 'name': 'Object3_v2', 'description': 'Test Object3_v2'}, as no datasource is available. Fallback to 'conservative' mode.",
        )
        self.assertEqual(
            cm.output[-1],
            "INFO:hermes-unit-tests:Unable to merge removed prevEvent=<Event(TestObj1_local_removed[3])> with added lastEvent.objattrs={'obj_id': 3, 'name': 'Object3_v2', 'description': 'Test Object3_v2'}, as no datasource is available. Fallback to 'conservative' mode.",
        )

    def test_invalid_remediation_cases(self):
        logging.disable(logging.CRITICAL)
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
        logging.disable(logging.CRITICAL)
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
                f"{lastEvent=} {lastEvent.eventtype=} ; {prevEvent=} {prevEvent.eventtype=}",
            )

    def test_remediation_inconsistency_between_merge_results(self):
        logging.disable(logging.CRITICAL)
        eq = ErrorQueue(
            typesMapping={"TestObj1": "TestObj1"}, autoremediate="conservative"
        )
        eq.append(self.singleAddedEvent, self.singleAddedEvent, "Dummy error msg")

        self.assertRaisesRegex(
            AssertionError,
            f"BUG \\: inconsistency between remote and local merge results \\: .*$",
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
        self.assertEqual(len(eq), 12)
        # 2 events
        eq.purgeAllEvents("TestObj1", 1, isLocalObjtype=False)
        self.assertEqual(len(eq), 10)
        # 3 events (1 remote, 2 local)
        eq.purgeAllEvents("TestObj1", 2, isLocalObjtype=False)
        self.assertEqual(len(eq), 7)
        # 4 events
        eq.purgeAllEvents("TestObj1", 3, isLocalObjtype=False)
        self.assertEqual(len(eq), 3)
        # 3 events (2 remote, 1 local)
        eq.purgeAllEvents("TestObj1", 4, isLocalObjtype=False)
        self.assertEqual(len(eq), 0)

        eq = ErrorQueue(
            typesMapping=self.typesMapping,
            autoremediate="disabled",
            from_json_dict={"_queue": self.queue},
        )
        self.assertEqual(len(eq), 12)
        # 3 events (2 remote, 1 local)
        eq.purgeAllEvents("TestObj1_local", 4, isLocalObjtype=True)
        self.assertEqual(len(eq), 9)

    def test_iter_with_remove(self):
        eq = ErrorQueue(
            typesMapping=self.typesMapping,
            autoremediate="disabled",
            from_json_dict={"_queue": self.queue},
        )

        total = 0
        for item in iter(eq):
            total += 1
        self.assertEqual(total, 4)  # 4 different objects in queue

        count = 0
        for item in iter(eq):
            count += 1
            eq.purgeAllEvents("TestObj1_local", 4, isLocalObjtype=True)
        self.assertEqual(count, 3)  # 3 remaining different objects in queue

    def test_allEvents_with_remove(self):
        eq = ErrorQueue(
            typesMapping=self.typesMapping,
            autoremediate="disabled",
            from_json_dict={"_queue": self.queue},
        )

        total = 0
        for item in eq.allEvents():
            total += 1
        self.assertEqual(total, 12)  # 12 events in queue

        count = 0
        for item in eq.allEvents():
            count += 1
            eq.purgeAllEvents("TestObj1_local", 4, isLocalObjtype=True)
        self.assertEqual(count, 9)  # 9 remaining events in queue

    def test_containsObjectByEvent(self):
        eq = ErrorQueue(
            typesMapping=self.typesMapping,
            autoremediate="disabled",
            from_json_dict={"_queue": self.queue},
        )

        ev = Event(from_json_dict=self.queue["7"][0])
        self.assertTrue(eq.containsObjectByEvent(ev, isLocalEvent=False))
        eq.purgeAllEvents("TestObj1", 3, isLocalObjtype=False)
        self.assertFalse(eq.containsObjectByEvent(ev, isLocalEvent=False))

    def test_containsObjectByDataobject(self):
        eq = ErrorQueue(
            typesMapping=self.typesMapping,
            autoremediate="disabled",
            from_json_dict={"_queue": self.queue},
        )

        objvals = {
            "OBJ_ID": 3,
            "NAME": "Object3",
            "DESCRIPTION": "Test Object3",
            "NEW_ATTR1": "new_attr1_value",
            "NEW_ATTR2": "new_attr2_value",
            "NEW_ATTR3": "new_attr3_value",
        }
        obj = self.TestObj1(from_remote=objvals)
        self.assertTrue(eq.containsObjectByDataobject(obj, isLocalObjtype=False))
        eq.purgeAllEventsOfDataObject(obj, isLocalObjtype=False)
        self.assertFalse(eq.containsObjectByDataobject(obj, isLocalObjtype=False))
