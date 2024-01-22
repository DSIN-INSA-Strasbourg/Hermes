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


from typing import Any

from lib.plugins import AbstractDataSourcePlugin
from datetime import datetime
import sqlite3

import logging

logger = logging.getLogger("hermes")

HERMES_PLUGIN_CLASSNAME: str | None = "DatasourceSqlite"
"""The plugin class name defined in this module file"""


class DatasourceSqlite(AbstractDataSourcePlugin):
    """Remote Data Source for SQLite database"""

    def __init__(self, settings: dict[str, Any]):
        """Instantiate new plugin and store a copy of its settings dict in self._settings"""
        super().__init__(settings)
        self._dbcon: sqlite3.Connection | None = None
        sqlite3.register_adapter(datetime, self.adapt_datetime_iso)
        sqlite3.register_converter("datetime", self.convert_datetime)

    @staticmethod
    def adapt_datetime_iso(val: datetime) -> str:
        """Convert datetime to ISO 8601 datetime string without timezone"""
        return val.isoformat()

    @staticmethod
    def convert_datetime(val: bytes) -> datetime:
        """Convert ISO 8601 datetime string to datetime object"""
        return datetime.fromisoformat(val.decode())

    def open(self):
        """Establish connection with SQLite Database"""
        self._dbcon = sqlite3.connect(
            database=self._settings["uri"],
            detect_types=sqlite3.PARSE_DECLTYPES,
        )

    def close(self):
        """Close connection with SQLite Database"""
        self._dbcon.close()
        self._dbcon = None

    def fetch(
        self,
        query: str | None,
        vars: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Fetch data from datasource with specified query and optional queryvars.
        Returns a list of dict containing each entry fetched, with REMOTE_ATTRIBUTES
        as keys, and corresponding fetched values as values"""
        fetcheddata = []
        cur = self._dbcon.cursor()
        cur.execute(query, vars)
        columns = [col[0] for col in cur.description]
        cur.row_factory = lambda _, args: dict(zip(columns, args))
        for row in cur:
            fetcheddata.append(row)
        return fetcheddata

    def add(self, query: str | None, vars: dict[str, Any]):
        """Add data to datasource with specified query and optional queryvars"""
        cur = self._dbcon.cursor()
        cur.execute(query, vars)
        self._dbcon.commit()

    def delete(self, query: str | None, vars: dict[str, Any]):
        """Delete data from datasource with specified query and optional queryvars"""
        cur = self._dbcon.cursor()
        cur.execute(query, vars)
        self._dbcon.commit()

    def modify(self, query: str | None, vars: dict[str, Any]):
        """Modify data on datasource with specified query and optional queryvars"""
        cur = self._dbcon.cursor()
        cur.execute(query, vars)
        self._dbcon.commit()
