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


import argparse
import atexit
import grp
import logging
import os
import pwd
import socket
import threading

from stat import S_ISSOCK
from time import sleep
from typing import Any, Callable, IO

from lib.datamodel.serialization import JSONSerializable


class InvalidSocketMessageError(Exception):
    """Raised when receiving a malformed message on socket"""


class SocketNotFoundError(Exception):
    """Raised when a client attempt to connect to a non-existent socket file"""


class SocketParsingError(Exception):
    """Raised when argparse failed. Converting exception to string will provide argparse
    message"""


class SocketParsingMessage(Exception):
    """Raised when argparse try to print a message. Pass the message in exception content
    instead of printing it"""


class InvalidOwnerError(Exception):
    """Raised when specified socket owner doesn't exist"""


class InvalidGroupError(Exception):
    """Raised when specified socket group doesn't exist"""


class SocketArgumentParser(argparse.ArgumentParser):  # pragma: no cover
    """Subclass of argument parser to avoid exiting on error. Will parse arguments received
    on server socket"""

    def format_error(self, message: str) -> str:
        """Format error message"""
        return self.format_help() + "\n" + message

    def _print_message(self, message: str, file: IO[str] | None = None):
        """Override print message to store message in SocketParsingMessage exception instead
        of printing it"""
        if message:
            raise SocketParsingMessage(message)

    def exit(self, status=0, message=None):
        """Prevent argparser from exiting app"""
        pass

    def error(self, message: str):
        """Raise a SocketParsingError containing error message instead of exiting"""
        raise SocketParsingError(self.format_error(message))


class SocketMessageToServer(JSONSerializable):
    """Serializable message that SockServer can understand
    It is intended to be equivalent to sys.argv"""

    def __init__(
        self,
        argv: list[str] | None = None,
        from_json_dict: dict[str, Any] | None = None,
    ):
        """Create a new message with specified argv list or from deserialized json dict"""
        super().__init__(jsondataattr=["argv"])

        if argv is None and from_json_dict is None:
            err = f"Cannot instantiante object from nothing: you must specify one data source"
            __hermes__.logger.critical(err)
            raise AttributeError(err)

        if argv is not None and from_json_dict is not None:
            err = f"Cannot instantiante object from multiple data sources at once"
            __hermes__.logger.critical(err)
            raise AttributeError(err)

        if argv is not None:
            self.argv: list[str] = argv
        else:
            self.argv = from_json_dict["argv"]

        if type(self.argv) != list:
            err = f"Invalid type for argv: {type(self.argv)} instead of list"
            __hermes__.logger.warning(err)
            raise InvalidSocketMessageError(err)

        for item in self.argv:
            if type(item) != str:
                err = f"Invalid type in argv: {type(item)} instead of str"
                __hermes__.logger.warning(err)
                raise InvalidSocketMessageError(err)


class SocketMessageToClient(JSONSerializable):
    """Serializable message (answer) that SockClient can understand
    It is intended to be equivalent to a command result with a retcode (0 if no error),
    and an output string"""

    def __init__(
        self,
        retcode: int | None = None,
        retmsg: str | None = None,
        from_json_dict: dict[str, Any] | None = None,
    ):
        """Create a new message with specified retcode and retmsg, or from deserialized json dict"""
        super().__init__(jsondataattr=["retcode", "retmsg"])

        if (retcode is None or retmsg is None) and from_json_dict is None:
            err = f"Cannot instantiante object from nothing: you must specify one data source"
            __hermes__.logger.critical(err)
            raise AttributeError(err)

        if (retcode is not None or retmsg is not None) and from_json_dict is not None:
            err = f"Cannot instantiante object from multiple data sources at once"
            __hermes__.logger.critical(err)
            raise AttributeError(err)

        if retcode is not None:
            self.retcode: int = retcode
            self.retmsg: str = retmsg
        else:
            self.retcode = from_json_dict["retcode"]
            self.retmsg = from_json_dict["retmsg"]

        if type(self.retcode) != int:
            err = f"Invalid type for retcode: {type(self.retcode)} instead of int"
            __hermes__.logger.warning(err)
            raise InvalidSocketMessageError(err)

        if type(self.retmsg) != str:
            err = f"Invalid type for retmsg: {type(self.retmsg)} instead of str"
            __hermes__.logger.warning(err)
            raise InvalidSocketMessageError(err)


class SockServer:
    """Create a server awaiting messages on Unix socket, and sending them on a specified
    handler at each call of processMessagesInQueue()"""

    def __init__(
        self,
        path: str,
        processHdlr: Callable[[SocketMessageToServer], SocketMessageToClient],
        owner: str | None = None,
        group: str | None = None,
        mode: int = 0o0700,
    ):
        """Create a new server, and its Unix socket on sockpath, with specified mode.
        All received messages will be send to specified processHdlr"""
        atexit.register(self._cleanup)  # Do our best to delete sock file at exit
        self._sockpath: str = path
        self._processHdlr: Callable[[SocketMessageToServer], SocketMessageToClient] = (
            processHdlr
        )
        self._sock = None

        self._removeSocket()  # Try to remove the socket if it already exist

        # Create a non blocking unix stream socket
        self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._sock.setblocking(False)

        # Bind the socket to the specified path
        self._sock.bind(self._sockpath)

        # Set socket rights as requested
        try:
            uid = pwd.getpwnam(owner).pw_uid if owner else -1
        except KeyError:
            raise InvalidOwnerError(
                f"Specified socket {owner=} doesn't exists"
            ) from None

        try:
            gid = grp.getgrnam(group).gr_gid if group else -1
        except KeyError:
            raise InvalidGroupError(
                f"Specified socket {group=} doesn't exists"
            ) from None

        if uid != -1 or gid != -1:
            os.chown(self._sockpath, uid, gid)

        os.chmod(self._sockpath, mode)

        self._sock.listen()  # Listen for incoming connections

    def _removeSocket(self):
        """Try to remove the socket file"""
        if not os.path.exists(self._sockpath):
            return  # Path doesn't exists, nothing to do

        # Is path a socket ?
        st = os.stat(self._sockpath)
        if not S_ISSOCK(st.st_mode):
            # Not a socket, raise an exception
            raise FileExistsError(
                f"The specified path for the unix socket '{self._sockpath}'"
                f" already exists and is not a socket"
            )

        try:  # Is a socket, try to delete it
            os.unlink(self._sockpath)
        except OSError:
            if os.path.exists(self._sockpath):
                raise

    def _cleanup(self):
        """Close the socket and try to remove the socket file"""
        if self._sock:
            self._sock.close()  # Close the socket
        self._removeSocket()  # Try to remove the socket file

    def processMessagesInQueue(self):
        """Process every message waiting on socket and send them to handler
        Returns when no message left"""
        while True:
            try:
                # Check for new incoming connection
                connection, client_address = self._sock.accept()
            except BlockingIOError:
                # __hermes__.logger.debug("No new connection")
                break

            # Set a reasonnable timeout to prevent blocking whole app if a client
            # doesn't close its sending pipe
            connection.settimeout(1)

            __hermes__.logger.debug(f"New CLI connection")
            # Receive the data
            msg = b""
            try:
                while True:
                    data = connection.recv(9999)
                    if not data:
                        break  # EOF
                    msg += data
            except Exception as e:
                __hermes__.logger.warning(f"Got exception during receive: {str(e)}")
            else:
                # Process message, and generate reply
                try:
                    m = SocketMessageToServer.from_json(msg.decode())
                except InvalidSocketMessageError:
                    # Ignoring message
                    pass
                else:
                    reply: SocketMessageToClient = self._processHdlr(m)
                    try:
                        connection.sendall(reply.to_json().encode())  # send reply
                    except Exception as e:
                        __hermes__.logger.warning(
                            f"Got exception during send: {str(e)}"
                        )

            try:
                connection.close()
            except Exception as e:
                __hermes__.logger.warning(f"Got exception during close: {str(e)}")

    def startProcessMessagesDaemon(self, appname: str | None = None):
        """Will call undefinitly processMessagesInQueue() in a separate thread.
        Its to the caller responsability to ensure there will be no race
        condition beetween threads

        If appname is specified, the daemon loop will fill local thread attributes of
        builtin var "__hermes__" at start
        """
        if appname:
            threadname = f"{appname}-cli-listener"
        else:
            threadname = None

        t = threading.Thread(
            target=self.__daemonLoop,
            name=threadname,
            kwargs={"appname": appname},
            daemon=True,
        )
        t.start()

    def __daemonLoop(self, appname: str | None = None):
        if appname:
            __hermes__.appname = appname
            __hermes__.logger = logging.getLogger(appname)

        while True:
            self.processMessagesInQueue()
            sleep(0.5)


class SockClient:
    """Create a client sending a command on Unix socket, and waiting for result"""

    @classmethod
    def send(
        cls, sockpath: str, message: SocketMessageToServer
    ) -> SocketMessageToClient:
        """Send specified message to server via specified unix sockpath, block until result
        is received, and returns it"""
        # Create a blocking unix stream socket
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            try:
                sock.connect(sockpath)  # Connect to the socket file
            except FileNotFoundError:
                raise SocketNotFoundError()
            sock.sendall(message.to_json().encode())  # Send message
            sock.shutdown(socket.SHUT_WR)  # Close the sending pipe

            reply = b""
            while True:
                data = sock.recv(9999)
                if not data:  # EOF
                    return SocketMessageToClient.from_json(reply.decode())
                reply += data
