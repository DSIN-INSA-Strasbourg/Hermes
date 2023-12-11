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
import oracledb

import logging

logger = logging.getLogger("hermes")

HERMES_PLUGIN_CLASSNAME: str | None = "DatasourceOracle"
"""The plugin class name defined in this module file"""


class DatasourceOracle(AbstractDataSourcePlugin):
    """Remote Data Source for Oracle database"""

    def __init__(self, settings: dict[str, Any]):
        """Instantiate new plugin and store a copy of its settings dict in self._settings"""
        super().__init__(settings)
        self._dbcon: oracledb.connection.Connection | None = None

    def open(self):
        """Establish connection with Oracle Database"""
        params = {
            "user": self._settings["login"],
            "password": self._settings["password"],
            "host": self._settings["server"],
            "port": self._settings["port"],
        }
        if "service_name" in self._settings:
            params["service_name"] = self._settings["service_name"]
        if "sid" in self._settings:
            params["sid"] = self._settings["sid"]

        cp = oracledb.ConnectParams(**params)
        self._dbcon = oracledb.connect(params=cp)

    def close(self):
        """Close connection with Oracle Database"""
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
        with self._dbcon.cursor() as cur:
            cur.execute(query, vars)
            columns = [col[0] for col in cur.description]
            cur.rowfactory = lambda *args: dict(zip(columns, args))
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
