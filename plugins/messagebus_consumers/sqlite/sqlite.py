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


from typing import Any, Iterable

from lib.plugins import AbstractMessageBusConsumerPlugin
from lib.datamodel.event import Event

from datetime import datetime, timedelta
import sqlite3
import time

import logging

logger = logging.getLogger("hermes")

HERMES_PLUGIN_CLASSNAME: str | None = "SqliteConsumerPlugin"
"""The plugin class name defined in this module file"""


class SqliteConsumerPlugin(AbstractMessageBusConsumerPlugin):
    """Sqlite message bus consumer plugin, to allow Hermes-clients to fetch events
    from an sqlite database (useful for tests, not heavily tested for production use).
    """

    def __init__(self, settings: dict[str, Any]):
        """Instantiate new plugin and store a copy of its settings dict in self._settings"""
        super().__init__(settings)
        self._db: sqlite3.Connection | None = None
        self.__curoffset = None
        self._timeout: int | None = 1

    def open(self) -> Any:
        """Establish connection with messagebus"""
        database = f"file:{self._settings['uri']}?mode=ro"
        try:
            self._db = sqlite3.connect(database=database, uri=True)
        except sqlite3.OperationalError:
            # No db file found
            logger.info(f"Sqlite bus file '{self._settings['uri']}' doesn't exist yet")
        else:
            self._db.row_factory = sqlite3.Row

    def close(self):
        """Close connection with messagebus"""
        if self._db:
            self._db.close()
            del self._db
            self._db = None

    def seekToBeginning(self):
        """Seek to first (older) event in message bus queue"""
        if not self._db:
            self.open()
            if not self._db:
                self.__curoffset = -1
                return

        sql = "SELECT MIN(msgid) AS msgid FROM hermesmessages"
        cur = self._db.execute(sql)

        entry = cur.fetchone()
        if entry is None:
            self.__curoffset = -1
            return
        self.__curoffset = entry["msgid"]

    def seek(self, offset: Any):
        """Seek to specified offset event in message bus queue"""
        if not self._db:
            self.open()
            if not self._db:
                raise IndexError(
                    f"Specified offset '{offset}' doesn't exists in bus (bus is empty)"
                ) from None

        sql = (
            "SELECT "
            "  min(hermesmessages.msgid) AS minmsgid, "
            "  max(hermesmessages.msgid) AS maxmsgid, "
            "  max(sqlite_sequence.seq)+1 AS nextmsgid "
            "FROM hermesmessages, sqlite_sequence "
            "WHERE sqlite_sequence.name = 'hermesmessages'"
        )
        cur = self._db.execute(sql)
        entry = cur.fetchone()
        if entry is None:
            raise IOError("Bus database seems invalid") from None
        else:
            if entry["minmsgid"] <= offset <= entry["nextmsgid"]:
                self.__curoffset = offset
            else:
                raise IndexError(
                    f"Specified offset '{offset}' doesn't exists in bus"
                ) from None

    def setTimeout(self, timeout_ms: int | None):
        """Set timeout (in milliseconds) before aborting when waiting for next event.
        If None, wait forever"""
        if timeout_ms is None:
            self._timeout = None
        else:
            self._timeout = timeout_ms / 1000

    def findNextEventOfCategory(self, category: str) -> Event | None:
        """Lookup for first message with specified category and returns it,
        or returns None if none was found"""
        event: Event
        for event in self:
            if event.evcategory == category:
                return event

        return None  # Not found

    def __iter__(self) -> Iterable:
        """Iterate over message bus returning each Event, starting at current offset.
        When every event has been consumed, wait for next message until timeout set with
        setTimeout() has been reached"""
        try:
            if self._timeout:
                nexttimeout = datetime.now() + timedelta(seconds=self._timeout)
            else:
                nexttimeout = datetime.now() + timedelta(days=9999999)  # Infinite

            while datetime.now() < nexttimeout:
                if not self._db:
                    self.open()
                    if not self._db:
                        # No database, so no data : wait and retry until data or timeout
                        time.sleep(0.5)
                        continue

                sql = "SELECT * FROM hermesmessages WHERE msgid>=:offset ORDER BY msgid"
                cur = self._db.execute(sql, {"offset": self.__curoffset})

                entries = cur.fetchall()
                if len(entries) == 0:
                    # No data, wait and retry until data or timeout
                    time.sleep(0.5)
                    continue

                for entry in entries:
                    yield self.__entryToEvent(entry)
                    self.__curoffset = entry["msgid"] + 1
                if self._timeout:
                    nexttimeout = datetime.now() + timedelta(seconds=self._timeout)
        except Exception:
            raise

    @classmethod
    def __entryToEvent(cls, entry) -> Event:
        """Convert sql entry to Event and returns it"""
        event = Event.from_json(entry["data"])
        event.offset = entry["msgid"]
        event.timestamp = datetime.fromtimestamp(entry["timestamp"])
        return event
