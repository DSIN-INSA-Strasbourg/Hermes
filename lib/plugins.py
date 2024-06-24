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


from typing import Any, Iterable
from jinja2 import Undefined

from lib.datamodel.event import Event


class FailedToSendEventError(Exception):
    """Raised when AbstractMessageBusProducerPlugin was unable to send event to
    MessageBus"""


class AbstractAttributePlugin:
    """Superclass of attribute plugins (Jinja).
    Those plugins can be used as Jinja filters in hermes-server.datamodel settings and
    dynamically transform values

    Settings can be provided in config file, and a cerberus
    config-schema-plugin-PLUGINNAME.yml can be provided in the plugin dir, containing
    the settings validation rules schemas in yaml format to allow Hermes to validate
    plugin settings.
    See https://docs.python-cerberus.org/validation-rules.html
    """

    def __init__(self, settings: dict[str, Any]):
        """Instantiate new plugin and store a copy of its settings dict in
        self._settings"""
        self._settings = settings.copy()

    def filter(self, value: Any | None | Undefined, *args: Any, **kwds: Any) -> Any:
        """Call the plugin with specified value, and returns the result"""
        raise NotImplementedError


class AbstractDataSourcePlugin:
    """Superclass of datasource plugins, to interface Hermes with database, ldap
    directory, webservice or whatever you need
    The connection is established in a with-statement context handled by this class that
    will call open() and close() methods

    Settings can be provided in config file, and a cerberus
    config-schema-plugin-PLUGINNAME.yml can be provided in the plugin dir, containing
    the settings validation rules schemas in yaml format to allow Hermes to validate
    plugin settings.
    See https://docs.python-cerberus.org/validation-rules.html
    """

    def __init__(self, settings: dict[str, Any]):
        """Instantiate new plugin and store a copy of its settings dict in
        self._settings"""
        self._settings = settings.copy()

    def __enter__(self) -> "AbstractDataSourcePlugin":
        """Calls open() method when entering in a with statement"""
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Calls close() method when exiting of a with statement.
        Handle any close() exception"""
        try:
            self.close()
        except Exception as e:
            __hermes__.logger.error(
                f"Error when disconnecting from {self.__class__.__name__}: {str(e)}"
            )
            return False

        # Return false if called because an exception occurred in context
        if exc_type:
            return False
        return True

    def open(self):
        """Establish connection with datasource"""
        raise NotImplementedError

    def close(self):
        """Close connection with datasource"""
        raise NotImplementedError

    def fetch(
        self,
        query: str | None,
        vars: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Fetch data from datasource with specified query and optional queryvars.
        Returns a list of dict containing each entry fetched, with REMOTE_ATTRIBUTES
        as keys, and corresponding fetched values as values"""
        raise NotImplementedError

    def add(self, query: str | None, vars: dict[str, Any]):
        """Add data to datasource with specified query and optional queryvars"""
        raise NotImplementedError

    def delete(self, query: str | None, vars: dict[str, Any]):
        """Delete data from datasource with specified query and optional queryvars"""
        raise NotImplementedError

    def modify(self, query: str | None, vars: dict[str, Any]):
        """Modify data on datasource with specified query and optional queryvars"""
        raise NotImplementedError


class AbstractMessageBusProducerPlugin:
    """Superclass of message bus producers plugins, to allow Hermes-server to emit
    events to message bus.
    The connection to the bus is established in a with-statement context handled by this
    class that will call open() and close() methods.
    The subclasses must defines _open() method, and not override open() method that
    exists only to call _open() and handle errors.

    Settings can be provided in config file, and a cerberus
    config-schema-plugin-PLUGINNAME.yml can be provided in the plugin dir, containing
    the settings validation rules schemas in yaml format to allow Hermes to validate
    plugin settings.
    See https://docs.python-cerberus.org/validation-rules.html
    """

    def __init__(self, settings: dict[str, Any]):
        """Instantiate new plugin and store a copy of its settings dict in
        self._settings"""
        self._settings = settings.copy()

    def __enter__(self) -> "AbstractMessageBusProducerPlugin":
        """Calls open() method when entering in a with statement"""
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Calls close() method when exiting of a with statement.
        Handle any close() exception"""
        try:
            self.close()
        except Exception as e:
            __hermes__.logger.error(
                f"Error when disconnecting from {self.__class__.__name__}: {str(e)}"
            )
            return False

        # Return false if called because an exception occurred in context
        if exc_type:
            return False
        return True

    def open(self) -> Any:
        """Establish connection with messagebus"""
        raise NotImplementedError

    def close(self):
        """Close connection with messagebus"""
        raise NotImplementedError

    def _send(self, event: Event):
        """Send specified event to message bus"""
        raise NotImplementedError

    def send(self, event: Event):
        """Call _send() with specified event to message bus, and handle errors"""
        try:
            self._send(event)
        except Exception as e:
            __hermes__.logger.critical(f"Failed to send event: {str(e)}")
            raise FailedToSendEventError(str(e)) from None


class AbstractMessageBusConsumerPlugin:
    """Superclass of message bus consumers plugins, to allow Hermes-clients to fetch
    events from message bus.
    The connection to the bus is established in a with-statement context handled by this
    class that will call open() and close() methods.

    Settings can be provided in config file, and a cerberus
    config-schema-plugin-PLUGINNAME.yml can be provided in the plugin dir, containing
    the settings validation rules schemas in yaml format to allow Hermes to validate
    plugin settings.
    See https://docs.python-cerberus.org/validation-rules.html
    """

    def __init__(self, settings: dict[str, Any]):
        """Instantiate new plugin and store a copy of its settings dict in
        self._settings"""
        self._settings = settings.copy()

    def __enter__(self) -> "AbstractMessageBusConsumerPlugin":
        """Calls open() method when entering in a with statement"""
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Calls close() method when exiting of a with statement.
        Handle any close() exception"""
        try:
            self.close()
        except Exception as e:
            __hermes__.logger.error(
                f"Error when disconnecting from {self.__class__.__name__}: {str(e)}"
            )
            return False

        # Return false if called because an exception occurred in context
        if exc_type:
            return False
        return True

    def open(self) -> Any:
        """Establish connection with messagebus"""
        raise NotImplementedError

    def close(self):
        """Close connection with messagebus"""
        raise NotImplementedError

    def seekToBeginning(self):
        """Seek to first (older) event in message bus queue"""
        raise NotImplementedError

    def seek(self, offset: Any):
        """Seek to specified offset event in message bus queue"""
        raise NotImplementedError

    def setTimeout(self, timeout_ms: int | None):
        """Set timeout (in milliseconds) before aborting when waiting for next event.
        If None, wait forever"""
        raise NotImplementedError

    def findNextEventOfCategory(self, category: str) -> Event | None:
        """Lookup for first message with specified category and returns it,
        or returns None if none was found"""
        raise NotImplementedError

    def __iter__(self) -> Iterable:
        """Iterate over message bus returning each Event, starting at current offset.
        When every event has been consumed, wait for next message until timeout set with
        setTimeout() has been reached"""
        raise NotImplementedError
