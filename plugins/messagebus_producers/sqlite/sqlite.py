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


from lib.plugins import AbstractMessageBusProducerPlugin
from lib.datamodel.event import Event

from datetime import datetime, timedelta
from typing import Any
import sqlite3

import logging

logger = logging.getLogger("hermes")

HERMES_PLUGIN_CLASSNAME: str | None = "SqliteProducerPlugin"
"""The plugin class name defined in this module file"""


class SqliteProducerPlugin(AbstractMessageBusProducerPlugin):
    """Sqlite message bus producer plugin, to allow Hermes-server to emit events
    to an sqlite database (useful for tests, not heavily tested for production use)"""

    def __init__(self, settings: dict[str, Any]):
        """Instantiate new plugin and store a copy of its settings dict in self._settings"""
        super().__init__(settings)
        self._db: sqlite3.Connection | None = None

    def open(self) -> Any:
        """Establish connection with messagebus"""
        self._db = sqlite3.connect(database=self._settings["uri"])
        self.__initdb()
        self.__purgeOldEvents()

    def close(self):
        """Close connection with messagebus"""
        if self._db:
            self._db.commit()
            self._db.close()
            del self._db
            self._db = None

    def _send(self, event: Event):
        """Send specified event to message bus"""
        data = {"data": event.to_json(), "timestamp": datetime.now().timestamp()}
        sql = "INSERT INTO hermesmessages (data, timestamp) VALUES (:data, :timestamp)"
        self._db.execute(sql, data)
        self._db.commit()

    def __initdb(self):
        """Create sqlite table when necessary"""
        sql = (
            "CREATE TABLE IF NOT EXISTS hermesmessages ("
            "msgid INTEGER PRIMARY KEY AUTOINCREMENT, "
            "data TEXT NOT NULL, timestamp REAL NOT NULL)"
        )
        self._db.execute(sql)
        self._db.commit()

    def __purgeOldEvents(self):
        """Purge old events from sqlite database"""
        now = datetime.now()
        retention = timedelta(days=self._settings["retention_in_days"])

        data = {"purgelimit": (now - retention).timestamp()}

        sql = "DELETE FROM hermesmessages WHERE timestamp < :purgelimit"
        self._db.execute(sql, data)
        self._db.commit()
        self._db.execute("VACUUM")
        self._db.commit()
