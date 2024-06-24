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


from lib.plugins import AbstractMessageBusProducerPlugin
from lib.datamodel.event import Event

from kafka import KafkaProducer
from typing import Any

HERMES_PLUGIN_CLASSNAME: str | None = "KafkaProducerPlugin"
"""The plugin class name defined in this module file"""


class KafkaProducerPlugin(AbstractMessageBusProducerPlugin):
    """Kafka message bus producer plugin, to allow Hermes-server to emit events
    to Apache Kafka."""

    def __init__(self, settings: dict[str, Any]):
        """Instantiate new plugin and store a copy of its settings dict in
        self._settings"""
        super().__init__(settings)
        self._kafka: KafkaProducer | None = None

    def open(self) -> Any:
        """Establish connection with messagebus"""
        if "ssl" in self._settings:
            self._kafka = KafkaProducer(
                bootstrap_servers=self._settings["servers"],
                security_protocol="SSL",
                ssl_check_hostname=True,
                ssl_certfile=self._settings["ssl"]["certfile"],
                ssl_keyfile=self._settings["ssl"]["keyfile"],
                ssl_cafile=self._settings["ssl"]["cafile"],
            )
        else:
            self._kafka = KafkaProducer(
                bootstrap_servers=self._settings["servers"],
                security_protocol="PLAINTEXT",
            )

    def close(self):
        """Close connection with messagebus"""
        if self._kafka:
            self._kafka.close()
            self._kafka = None

    def _send(self, event: Event):
        """Send specified event to message bus"""
        future = self._kafka.send(
            topic=self._settings["topic"],
            key=event.evcategory.encode(),
            value=event.to_json().encode(),
        )
        # Only way to ensure message is stored on broker. Will raise an exception
        # otherwise
        # Don't trust self._kafka.flush() or future.is_done for that, or you'll lose
        # some messages
        future.get()
