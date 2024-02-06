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


from lib.config import HermesConfig
from lib.datamodel.dataschema import Dataschema
from lib.datamodel.dataobject import DataObject
from lib.datamodel.datasource import Datasource
from lib.datamodel.diffobject import DiffObject
from lib.datamodel.event import Event
from lib.datamodel.serialization import LocalCache, JSONEncoder
from lib.plugins import AbstractMessageBusProducerPlugin, FailedToSendEventError
from lib.utils.mail import Email
from lib.utils.socket import (
    SockServer,
    SocketMessageToServer,
    SocketMessageToClient,
    SocketArgumentParser,
    SocketParsingError,
    SocketParsingMessage,
)
from server.datamodel import Datamodel

from datetime import datetime, timedelta
import argparse
import json
import time
import signal
import traceback
from types import FrameType
from typing import Any


class HermesServerCache(LocalCache):
    """Hermes server data to cache"""

    def __init__(self, from_json_dict: dict[str, Any] = {}):
        super().__init__(
            jsondataattr=["lastUpdate", "errors", "exception"],
            cachefilename="_hermes-server",
        )

        self.lastUpdate: datetime | None = from_json_dict.get("lastUpdate")
        """Datetime of latest update"""

        self.errors: dict[str, dict[str, dict[str, Any]]] = from_json_dict.get(
            "errors", {}
        )
        """Dictionary containing current errors, for notifications"""

        self.exception: str | None = from_json_dict.get("exception")
        """String containing latest exception trace"""

    def savecachefile(self, cacheFilename: str | None = None):
        """Override method only to disable backup files in cache"""
        return super().savecachefile(cacheFilename, dontKeepBackup=True)


class HermesServer:
    """Hermes-server main class"""

    def __init__(self, config: HermesConfig):
        """Set up a server instance.
        The mainloop() method MUST then be called to start the service"""

        # Setup the signals handler
        config.setSignalsHandler(self.signalHandler)

        self.config: HermesConfig = config
        self._msgbus: AbstractMessageBusProducerPlugin = self.config["hermes"][
            "plugins"
        ]["messagebus"]["plugininstance"]
        self.dm: Datamodel = Datamodel(self.config)

        self._cache: HermesServerCache = HermesServerCache.loadcachefile(
            "_hermes-server"
        )
        """Cached attributes"""

        self._initSyncRequested: bool = False
        """Indicate that an initsync sequence has been requested"""
        self._isStopped: bool = False
        """mainloop() will run until this var is set to True"""
        self._isPaused: datetime | None = None
        """Contains pause datetime if standard processing is paused, None otherwise"""
        self._forceUpdate = False
        """Indicate that a (forced) update command has been requested"""
        self._updateInterval: timedelta = timedelta(
            seconds=config["hermes-server"]["updateInterval"]
        )
        """Interval between two update"""
        self._numberOfLoopToProcess: int | None = None
        """**For functionnal tests only**, if a value is set, will process for *value*
        iterations of mainloop and pause execution until a new positive value is set"""

        self._firstFetchDone = False
        """Indicate if a full data set has been fetched since start"""

        now = datetime.now()
        self._nextUpdate: datetime = now
        """Datetime to wait before processing next update"""
        if (
            self._cache.lastUpdate
            and now < self._cache.lastUpdate + self._updateInterval
        ):
            self._nextUpdate = self._cache.lastUpdate + self._updateInterval

        self.startTime: datetime | None = None
        """Datetime when mainloop was started"""

        self._sock: SockServer | None = None
        if config["hermes"]["cli_socket"]["path"] is not None:
            self._sock = SockServer(
                path=config["hermes"]["cli_socket"]["path"],
                owner=config["hermes"]["cli_socket"]["owner"],
                group=config["hermes"]["cli_socket"]["group"],
                mode=config["hermes"]["cli_socket"]["mode"],
                processHdlr=self._processSocketMessage,
            )
            self.__setupSocketParser()

    def __setupSocketParser(self):
        """Set up the argparse context for unix socket commands"""
        self._parser = SocketArgumentParser(
            prog=f"{self.config['appname']}-cli",
            description="Hermes Server CLI",
            exit_on_error=False,
        )

        subparsers = self._parser.add_subparsers(help="Sub-commands")

        # Initsync
        sp_initsync = subparsers.add_parser(
            "initsync",
            help="Send specific init message containing all data but passwords. Useful to fill new client",
        )
        sp_initsync.set_defaults(func=self.sock_initsync)

        # Update
        sp_update = subparsers.add_parser(
            "update",
            help="Force update now, ignoring updateInterval",
        )
        sp_update.set_defaults(func=self.sock_update)

        # Quit
        sp_quit = subparsers.add_parser("quit", help="Stop server")
        sp_quit.set_defaults(func=self.sock_quit)

        # Pause
        sp_pause = subparsers.add_parser(
            "pause", help="Pause processing until 'resume' command is sent"
        )
        sp_pause.set_defaults(func=self.sock_pause)

        # Resume
        sp_resume = subparsers.add_parser(
            "resume", help="Resume processing that has been paused with 'pause'"
        )
        sp_resume.set_defaults(func=self.sock_resume)

        # Status
        sp_status = subparsers.add_parser("status", help="Show server status")
        sp_status.set_defaults(func=self.sock_status)
        sp_status.add_argument(
            "-j",
            "--json",
            action="store_const",
            const=True,
            default=False,
            help="Print status as json",
        )
        sp_status.add_argument(
            "-v",
            "--verbose",
            action="store_const",
            const=True,
            default=False,
            help="Output items without values",
        )

    def signalHandler(self, signalnumber: int, frame: FrameType | None):
        """Signal handler that will be called on SIGINT and SIGTERM"""
        __hermes__.logger.critical(
            f"Signal '{signal.strsignal(signalnumber)}' received, terminating"
        )
        self._isStopped = True

    def _processSocketMessage(
        self, msg: SocketMessageToServer
    ) -> SocketMessageToClient:
        """Handler that process specified msg received on unix socket and returns the answer
        to send"""
        reply: SocketMessageToClient | None = None

        try:
            args = self._parser.parse_args(msg.argv)
            if "func" not in args:
                raise SocketParsingMessage(self._parser.format_help())
        except (SocketParsingError, SocketParsingMessage) as e:
            retmsg = str(e)
        except argparse.ArgumentError as e:
            retmsg = self._parser.format_error(str(e))
        else:
            try:
                reply = args.func(args)
            except Exception as e:
                lines = traceback.format_exception(type(e), e, e.__traceback__)
                trace = "".join(lines).strip()
                __hermes__.logger.critical(f"Unhandled exception: {trace}")
                retmsg = trace

        if reply is None:  # Error was met
            reply = SocketMessageToClient(retcode=1, retmsg=retmsg)

        return reply

    def sock_initsync(self, args: argparse.Namespace) -> SocketMessageToClient:
        """Handler called when a valid initsync subcommand is requested on unix socket"""
        self._initSyncRequested = True
        return SocketMessageToClient(retcode=0, retmsg="")

    def sock_update(self, args: argparse.Namespace) -> SocketMessageToClient:
        """Handler called when a valid update subcommand is requested on unix socket"""
        self._forceUpdate = True
        return SocketMessageToClient(retcode=0, retmsg="")

    def sock_quit(self, args: argparse.Namespace) -> SocketMessageToClient:
        """Handler called when quit subcommand is requested on unix socket"""
        self._isStopped = True
        __hermes__.logger.info("hermes-server has been requested to quit")
        return SocketMessageToClient(retcode=0, retmsg="")

    def sock_pause(self, args: argparse.Namespace) -> SocketMessageToClient:
        """Handler called when pause subcommand is requested on unix socket"""
        if self._isStopped:
            return SocketMessageToClient(
                retcode=1, retmsg="Error: server is currently being stopped"
            )

        if self._isPaused:
            return SocketMessageToClient(
                retcode=1, retmsg="Error: server is already paused"
            )

        __hermes__.logger.info("hermes-server has been requested to pause")
        self._isPaused = datetime.now()
        return SocketMessageToClient(retcode=0, retmsg="")

    def sock_resume(self, args: argparse.Namespace) -> SocketMessageToClient:
        """Handler called when resume subcommand is requested on unix socket"""
        if self._isStopped:
            return SocketMessageToClient(
                retcode=1, retmsg="Error: server is currently being stopped"
            )

        if not self._isPaused:
            return SocketMessageToClient(
                retcode=1, retmsg="Error: server is not paused"
            )

        __hermes__.logger.info("hermes-server has been requested to resume")
        self._isPaused = None
        return SocketMessageToClient(retcode=0, retmsg="")

    def sock_status(self, args: argparse.Namespace) -> SocketMessageToClient:
        """Handler called when status subcommand is requested on unix socket"""
        status = self.status(verbose=args.verbose)
        if args.json:
            msg = json.dumps(status, indent=4)
        else:
            nl = "\n"
            info2printable = {
                "inconsistencies": "Inconsistencies",
                "mergeConflicts": "Merge conflicts",
                "integrityFiltered": "Filtered by integrity constraints",
                "mergeFiltered": "Filtered by merge constraints",
            }
            msg = ""
            for objname in ["hermes-server"] + list(status.keys() - ("hermes-server",)):
                infos = status[objname]
                msg += f"{objname}:{nl}"
                for category in ("information", "warning", "error"):
                    if category not in infos:
                        continue
                    if not infos[category]:
                        msg += f"  * {category.capitalize()}: []{nl}"
                        continue

                    msg += f"  * {category.capitalize()}{nl}"
                    for infoname, infodata in infos[category].items():
                        indentedinfodata = str(infodata).replace("\n", "\n      ")
                        msg += f"    - {info2printable.get(infoname, infoname)}: {indentedinfodata}{nl}"
            msg = msg.rstrip()

        return SocketMessageToClient(retcode=0, retmsg=msg)

    def _checkForSchemaChanges(self):
        curschema: Dataschema = self.dm.dataschema
        oldschema: Dataschema = Dataschema.loadcachefile("_dataschema")
        diff = curschema.diffFrom(oldschema)

        if diff:
            old: dict[str, Any] = oldschema.schema
            new: dict[str, Any] = curschema.schema
            if old:
                __hermes__.logger.info("Dataschema has changed since last run")
            else:
                __hermes__.logger.info("Loading first dataschema")

            if diff.added:
                __hermes__.logger.info(f"Types added in Dataschema: {diff.added}")

            if diff.removed:
                __hermes__.logger.info(
                    f"Types removed from Dataschema: {diff.removed}, generate events to mark data as deleted"
                )

                # Create a datasource with same content as cache, minus the types to remove
                olddata: Datasource = Datasource(
                    schema=oldschema, enableTrashbin=False, enableCache=False
                )
                olddata.loadFromCache()

                # Create an empty datasource and copy the data types to keep into it
                newdata: Datasource = Datasource(
                    schema=oldschema, enableTrashbin=False, enableCache=False
                )
                for objtype in oldschema.schema.keys():
                    if objtype not in diff.removed:
                        newdata[objtype] = olddata[objtype]

                # Send remove event of each entry of each removed type
                self.generateAndSendEvents(
                    eventCategory="base",
                    data=newdata,
                    cache=olddata,
                    save=True,
                    commit=False,
                    sendEvents=True,
                )

                __hermes__.logger.info(
                    f"Types removed from Dataschema: {diff.removed}, purging cache files"
                )
                for objtype in diff.removed:
                    LocalCache.deleteAllCacheFiles(objtype)

            if diff.modified:
                newpkeys = {}
                for objtype in diff.modified:
                    n = new[objtype]
                    o = old[objtype]
                    # HERMES_ATTRIBUTES
                    added = n["HERMES_ATTRIBUTES"] - o["HERMES_ATTRIBUTES"]
                    removed = o["HERMES_ATTRIBUTES"] - n["HERMES_ATTRIBUTES"]
                    if added:
                        __hermes__.logger.info(
                            f"New attributes in dataschema type '{objtype}': {added}"
                        )
                    if removed:
                        __hermes__.logger.info(
                            f"Removed attributes from dataschema type '{objtype}': {removed}"
                        )

                    # SECRETS_ATTRIBUTES
                    added = n["SECRETS_ATTRIBUTES"] - o["SECRETS_ATTRIBUTES"]
                    removed = o["SECRETS_ATTRIBUTES"] - n["SECRETS_ATTRIBUTES"]
                    if added:
                        __hermes__.logger.info(
                            f"New secrets attributes in dataschema type '{objtype}': {added}"
                        )
                        # We need to purge attribute from cache: as cache is loaded with
                        # attribute set up as SECRET, we just have to save the cache (attr
                        # won't be saved anymore, as it's SECRET) and reload cache to
                        # "forget" values loaded from previous cache
                        self.dm.data.cache.save()
                        self.dm.data.cache.loadFromCache()
                    if removed:
                        __hermes__.logger.info(
                            f"Removed secrets attributes from dataschema type '{objtype}': {removed}"
                        )

                    # PRIMARYKEY_ATTRIBUTE
                    npkey = n["PRIMARYKEY_ATTRIBUTE"]
                    opkey = o["PRIMARYKEY_ATTRIBUTE"]
                    if DataObject.isDifferent(npkey, opkey):
                        newpkeys[objtype] = npkey

                if newpkeys:
                    # Load previous data
                    olddata: Datasource = Datasource(
                        schema=oldschema, enableTrashbin=False, enableCache=False
                    )
                    olddata.loadFromCache()
                    __hermes__.logger.info(
                        f"Updating changed primary keys in cache {newpkeys=}"
                    )
                    # Only necessary to ensure no problem is met, may be removed
                    olddata.updatePrimaryKeys(newpkeys)
                    self.dm.data.loadFromCache()  # Reload modified data to get new pkeys values

            if old:
                e = Event(
                    evcategory="base",
                    eventtype="dataschema",
                    objattrs=new,
                )
                __hermes__.logger.info(
                    f"Sending new schema on message bus {e.toString(set())}"
                )
                with self._msgbus:
                    self._msgbus.send(event=e)

        self.dm.dataschema.savecachefile()

    def mainLoop(self):
        """Server main loop"""
        self.startTime = datetime.now()

        if self._sock is not None:
            self._sock.startProcessMessagesDaemon(appname=__hermes__.appname)

        # Process schema changes if any, until it succeed
        checkForSchemaChangesDone = False
        while not self._isStopped and not checkForSchemaChangesDone:
            try:
                self._checkForSchemaChanges()
            except Exception as e:
                lines = traceback.format_exception(type(e), e, e.__traceback__)
                trace = "".join(lines).strip()
                self.notifyException(trace)
                self._cache.savecachefile()
            else:
                checkForSchemaChangesDone = True

        # Reduce sleep duration during functional tests to speed them up
        sleepDuration = 1 if self._numberOfLoopToProcess is None else 0.05

        while not self._isStopped:
            try:
                if self._initSyncRequested:
                    self.initsync()
                    self._initSyncRequested = False

                if self._numberOfLoopToProcess is None:
                    # Normal operations
                    updateRequired = self._forceUpdate or (
                        not self._isPaused and datetime.now() >= self._nextUpdate
                    )
                else:
                    # Special case for functional tests
                    updateRequired = self._numberOfLoopToProcess > 0

                if not updateRequired:
                    time.sleep(sleepDuration)
                    if self._nextUpdate + self._updateInterval < datetime.now():
                        # Keep updating _nextUpdate even when paused, ensuring that its
                        # value remains in the past. This will avoid an uninterrupted
                        # update sequence to make up for the pause time
                        self._nextUpdate += self._updateInterval
                    continue

                # Standard run
                if self._forceUpdate:
                    self._forceUpdate = False
                else:
                    self._nextUpdate += self._updateInterval

                self.dm.fetch()
                self.generateAndSendEvents(
                    eventCategory="base",
                    data=self.dm.data,
                    cache=self.dm.data.cache,
                    save=True,
                    commit=True,
                    sendEvents=(self._cache.lastUpdate is not None),
                )
                self._cache.lastUpdate = datetime.now()
                self.notifyException(None)
                self._cache.savecachefile()

            except Exception as e:
                lines = traceback.format_exception(type(e), e, e.__traceback__)
                trace = "".join(lines).strip()
                self.notifyException(trace)
                self._cache.savecachefile()

            # Only used in functionnal tests
            if self._numberOfLoopToProcess:
                self._numberOfLoopToProcess -= 1

        self._cache.savecachefile()

    def status(
        self, verbose=False, level="information", ignoreUnhandledExceptions=False
    ) -> dict[str, dict[str, dict[str, Any]]]:
        """Returns a dict containing status for hermes-server and each defined type in
        datamodel.

        Each status contains 3 categories/levels: ""information", "warning" and "error"
        """
        if level not in ("information", "warning", "error"):
            raise AttributeError(
                f"""Specified level '{level}' is invalid. Possible values are ("information", "warning", "error"):"""
            )

        if level == "error":
            levels = ["error"]
        elif level == "warning":
            levels = [
                "warning",
                "error",
            ]
        elif level == "information":
            levels = [
                "information",
                "warning",
                "error",
            ]

        res = {
            "hermes-server": {
                "information": {
                    "startTime": self.startTime.strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "paused" if self._isPaused else "running",
                    "pausedSince": (
                        self._isPaused.strftime("%Y-%m-%d %H:%M:%S")
                        if self._isPaused
                        else "None"
                    ),
                    "lastUpdate": (
                        self._cache.lastUpdate.strftime("%Y-%m-%d %H:%M:%S")
                        if self._cache.lastUpdate
                        else "None"
                    ),
                    "nextUpdate": self._nextUpdate.strftime("%Y-%m-%d %H:%M:%S"),
                },
                "warning": {},
                "error": {},
            },
        }
        if not ignoreUnhandledExceptions and self._cache.exception:
            res["hermes-server"]["error"]["unhandledException"] = self._cache.exception

        for objname, objlist in self.dm.data.items():
            res[objname] = {
                "information": {},
                "warning": {},
                "error": {},
            }
            if not self._firstFetchDone and objname in self._cache.errors:
                res[objname] |= self._cache.errors[objname]

            for level, src in [
                ("error", "inconsistencies"),
                ("error", "mergeConflicts"),
                ("warning", "integrityFiltered"),
                ("warning", "mergeFiltered"),
            ]:
                if getattr(objlist, src):
                    res[objname][level][src] = []
                    for pkey in sorted(getattr(objlist, src)):
                        obj = objlist.get(pkey)
                        objrepr = pkey if obj is None else repr(obj)
                        res[objname][level][src].append(objrepr)

        for objname in self.dm.data.keys() | ("hermes-server",):
            for category in ("information", "warning", "error"):
                if category not in levels or (
                    not verbose and not res[objname][category]
                ):
                    del res[objname][category]

            if not verbose and not res[objname]:
                del res[objname]

        return res

    def initsync(self):
        """Send an initsync sequence"""
        empty: Datasource = Datasource(
            schema=self.dm.dataschema, enableTrashbin=False, enableCache=False
        )
        self.generateAndSendEvents(
            eventCategory="initsync",
            data=self.dm.data.cache,
            cache=empty,
            save=False,
            commit=False,
            sendEvents=True,
        )

    def generateAndSendEvents(
        self,
        eventCategory: str,
        data: Datasource,
        cache: Datasource,
        save: bool,
        commit: bool,
        sendEvents: bool,
    ):
        """Generate and send events of specified eventCategory ("base" or "initsync"),
        computed upon differences between specified data and cache.
        If save is True, cache will be updated and saved on disk.
        If sendEvents is True, events will be sent on msgbus.
        If commit and sendEvents are True, the datamodel commit_one and commit_all
        methods will be called"""

        if eventCategory not in ("base", "initsync"):
            err = f"Specified eventType '{eventCategory}' is invalid"
            __hermes__.logger.critical(err)
            raise ValueError(err)

        with self._msgbus:
            if eventCategory == "initsync" and sendEvents:
                self._msgbus.send(
                    Event(
                        evcategory=eventCategory,
                        eventtype="init-start",
                        obj=None,
                        objattrs=self.dm.dataschema.schema,  # Send current schema
                    )
                )

            # Loop over each datamodel type to compute diffs
            diffs: dict[str, DiffObject] = {}
            for objtype in data.keys():
                # Generate diff between fresh data and cache
                diff = data[objtype].diffFrom(cache[objtype])
                diffs[objtype] = diff
                if diff:
                    __hermes__.logger.info(
                        f"{objtype} have changed: {len(diff.added)} added,"
                        f" {len(diff.modified)} modified,"
                        f" {len(diff.removed)} removed"
                    )

            # Process events
            for changeType in ["added", "modified", "removed"]:
                if changeType == "removed":
                    # Process removed events in the datamodel reversed declaration order
                    objTypes = reversed(data.keys())
                else:
                    # Process other events in the datamodel declaration order
                    objTypes = data.keys()

                for objtype in objTypes:
                    secretAttrs = data.schema.secretsAttributesOf(objtype)
                    diff = diffs[objtype]
                    difflist = diff.dict[changeType]
                    # Loop over each diff item of current changeType and create event
                    diffitem: DiffObject | DataObject
                    for diffitem in difflist:
                        (event, obj) = Event.fromDiffItem(
                            diffitem, eventCategory, changeType
                        )

                        if sendEvents:
                            # Send event
                            try:
                                __hermes__.logger.info(
                                    f"Sending {event.toString(secretAttrs)}"
                                )
                                self._msgbus.send(event=event)
                            except FailedToSendEventError as e:
                                # Event not sent
                                if save:
                                    cache.save()
                                __hermes__.logger.critical(
                                    f"Failed to send event. Execution aborted: {str(e)}"
                                )
                                raise

                        # Event sent, validate its changes
                        if eventCategory == "base":
                            if sendEvents and commit:
                                self.dm.commit_one(obj)

                            match event.eventtype:
                                case "added":
                                    cache[objtype].append(obj)
                                case "removed":
                                    cache[objtype].remove(obj)
                                case "modified":
                                    cache[objtype].replace(obj)

                if sendEvents and commit:
                    self.dm.commit_all(objtype)

                if save:
                    cache.save()

            if eventCategory == "initsync" and sendEvents:
                self._msgbus.send(
                    Event(
                        evcategory=eventCategory,
                        eventtype="init-stop",
                        obj=None,
                        objattrs={},
                    )
                )

        self._firstFetchDone = True
        self.notifyErrors()

    def notifyErrors(self):
        """Notify of any data error met/solved"""
        new_errors = self.status(level="error", ignoreUnhandledExceptions=True)

        new_errstr = json.dumps(
            new_errors,
            cls=JSONEncoder,
            indent=4,
        )
        old_errstr = json.dumps(self._cache.errors, cls=JSONEncoder, indent=4)

        nl = "\n"

        if new_errors:
            __hermes__.logger.error(f"Data errors met: {nl}{new_errstr}")

        if new_errstr != old_errstr:
            if new_errors:
                desc = "data errors met"
            else:
                desc = "no more data errors"

            __hermes__.logger.info(desc)
            Email.sendDiff(
                config=self.config,
                contentdesc=desc,
                previous=old_errstr,
                current=new_errstr,
            )
            self._cache.errors = new_errors

    def notifyException(self, trace: str | None):
        """Notify of any unhandled exception met/solved"""
        if trace:
            __hermes__.logger.critical(f"Unhandled exception: {trace}")

        if self._cache.exception != trace:
            if trace:
                desc = "unhandled exception"
            else:
                desc = "no more unhandled exception"

            __hermes__.logger.info(desc)
            previous = "" if self._cache.exception is None else self._cache.exception
            current = "" if trace is None else trace
            Email.sendDiff(
                config=self.config,
                contentdesc=desc,
                previous=previous,
                current=current,
            )
            self._cache.exception = trace
