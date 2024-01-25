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


from typing import Any

from lib.plugins import AbstractDataSourcePlugin
import psycopg
from psycopg.rows import dict_row

HERMES_PLUGIN_CLASSNAME: str | None = "DatasourcePostgresql"
"""The plugin class name defined in this module file"""


class DatasourcePostgresql(AbstractDataSourcePlugin):
    """Remote Data Source for Postgresql database"""

    def __init__(self, settings: dict[str, Any]):
        """Instantiate new plugin and store a copy of its settings dict in self._settings"""
        super().__init__(settings)
        self._dbcon: psycopg.Connection | None = None

    def open(self):
        """Establish connection with Postgresql Database"""
        self._dbcon = psycopg.connect(
            dbname=self._settings["dbname"],
            user=self._settings["login"],
            password=self._settings["password"],
            host=self._settings["server"],
            port=self._settings["port"],
        )

    def close(self):
        """Close connection with Postgresql Database"""
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
        with self._dbcon.cursor(row_factory=dict_row) as cur:
            cur.execute(query, vars)
            for row in cur:
                fetcheddata.append(row)
        return fetcheddata

    def add(self, query: str | None, vars: dict[str, Any]):
        """Add data to datasource with specified query and optional queryvars"""
        with self._dbcon.cursor() as cur:
            cur.execute(query, vars)
        self._dbcon.commit()

    def delete(self, query: str | None, vars: dict[str, Any]):
        """Delete data from datasource with specified query and optional queryvars"""
        with self._dbcon.cursor() as cur:
            cur.execute(query, vars)
        self._dbcon.commit()

    def modify(self, query: str | None, vars: dict[str, Any]):
        """Modify data on datasource with specified query and optional queryvars"""
        with self._dbcon.cursor() as cur:
            cur.execute(query, vars)
        self._dbcon.commit()
