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

from datetime import datetime
from kafka import KafkaConsumer, TopicPartition

import logging

logger = logging.getLogger("hermes")

HERMES_PLUGIN_CLASSNAME: str | None = "KafkaConsumerPlugin"
"""The plugin class name defined in this module file"""


class KafkaConsumerPlugin(AbstractMessageBusConsumerPlugin):
    """Kafka message bus consumer plugin, to allow Hermes-clients to fetch events
    from Apache Kafka."""

    def __init__(self, settings: dict[str, Any]):
        """Instanciate new plugin and store a copy of its settings dict in self._settings"""
        super().__init__(settings)
        self._kafka: KafkaConsumer | None = None

    def open(self) -> Any:
        """Establish connection with messagebus"""
        if "ssl" in self._settings:
            self._kafka = KafkaConsumer(
                bootstrap_servers=self._settings["servers"],
                security_protocol="SSL",
                ssl_check_hostname=True,
                ssl_certfile=self._settings["ssl"]["certfile"],
                ssl_keyfile=self._settings["ssl"]["keyfile"],
                ssl_cafile=self._settings["ssl"]["cafile"],
                enable_auto_commit=False,
                auto_offset_reset="earliest",
                consumer_timeout_ms=1000,
                group_id=self._settings["group_id"],
            )
        else:
            self._kafka = KafkaConsumer(
                bootstrap_servers=self._settings["servers"],
                security_protocol="PLAINTEXT",
                enable_auto_commit=False,
                auto_offset_reset="earliest",
                consumer_timeout_ms=1000,
                group_id=self._settings["group_id"],
            )
        self.__kafkapartition = TopicPartition(
            self._settings["topic"],
            self._kafka.partitions_for_topic(self._settings["topic"]).pop(),
        )
        self._kafka.assign([self.__kafkapartition])

    def close(self):
        """Close connection with messagebus"""
        if self._kafka:
            self._kafka.close()
            self._kafka = None

    def seekToBeginning(self):
        """Seek to first (older) event in message bus queue"""
        self._kafka.seek_to_beginning()

    def seek(self, offset: Any):
        """Seek to specified offset's event in message bus queue"""
        self._kafka.seek(self.__kafkapartition, offset)

    def setTimeout(self, timeout_ms: int | None):
        """Set timeout (in milliseconds) before aborting when waiting for next event.
        If None, wait forever"""
        if timeout_ms is None:
            self._kafka.config["consumer_timeout_ms"] = float("inf")
        else:
            self._kafka.config["consumer_timeout_ms"] = timeout_ms

    def findNextEventOfCategory(self, category: str) -> Event | None:
        """Lookup for first message with specified category and returns it,
        or returns None if none was found"""
        categoryBytes = category.encode()
        for msg in self._kafka:
            if msg.key == categoryBytes:
                return self.__messageToEvent(msg)

        return None  # Not found

    def __iter__(self) -> Iterable:
        """Iterate over message bus returning each Event, starting at current offset.
        When every event has been consumed, wait for next message until timeout set with
        setTimeout() has been reached"""
        for msg in self._kafka:
            yield self.__messageToEvent(msg)

    @classmethod
    def __messageToEvent(cls, msg) -> Event:
        """Convert Kafka message to Event and returns it"""
        event = Event.from_json(msg.value.decode())
        event.offset = msg.offset
        event.timestamp = datetime.fromtimestamp(msg.timestamp / 1000)
        return event
