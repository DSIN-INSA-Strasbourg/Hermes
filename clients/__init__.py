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


from clients.datamodel import Datamodel
from lib.config import HermesConfig
from lib.datamodel.dataobject import DataObject
from lib.datamodel.dataobjectlist import DataObjectList
from lib.datamodel.datasource import Dataschema, Datasource
from lib.datamodel.diffobject import DiffObject
from lib.datamodel.event import Event
from lib.datamodel.serialization import LocalCache, JSONEncoder
from lib.plugins import AbstractMessageBusConsumerPlugin
from lib.utils.mail import Email
from lib.utils.socket import (
    SockServer,
    SocketMessageToServer,
    SocketMessageToClient,
    SocketArgumentParser,
    SocketParsingError,
    SocketParsingMessage,
)

from copy import deepcopy
from datetime import datetime, timedelta
from time import sleep
from types import FrameType
from typing import Any
import argparse
import json
import signal
import traceback

import logging

logger = logging.getLogger("hermes")


class HermesAlreadyNotifiedException(Exception):
    """Raised when an exception has already been notified, to avoid a second notification"""


class HermesClientHandlerError(Exception):
    """Raised when an exception is met during client handler call"""

    def __init__(self, err: Exception | str | None):
        if isinstance(err, Exception):
            self.msg: str | None = HermesClientHandlerError.exceptionToString(err)
            """Printable error message, None in a rare case where exception is raised
            without error, but to postpone an event processing"""
        else:
            self.msg = err
        super().__init__(self.msg)

    @staticmethod
    def exceptionToString(
        exception: Exception, purgeCurrentFileFromTrace: bool = True
    ) -> str:
        """Convert the specified exception to a string containing its full trace"""
        lines = traceback.format_exception(
            type(exception), exception, exception.__traceback__
        )

        if purgeCurrentFileFromTrace:
            # Purging current file infos from traceback
            lines = [line for line in lines if __file__ not in line]

        return "".join(lines).strip()


class HermesClientCache(LocalCache):
    """Hermes client data to cache"""

    def __init__(self, from_json_dict: dict[str, Any] = {}):
        super().__init__(
            jsondataattr=[
                "queueErrors",
                "datamodelWarnings",
                "exception",
                "initstartoffset",
                "initstopoffset",
                "nextoffset",
            ],
        )

        self.queueErrors: dict[str, dict[str, dict[str, Any]]] = from_json_dict.get(
            "queueErrors", {}
        )
        """Dictionnary containing current objects in error queue, for notifications"""

        self.datamodelWarnings: dict[
            str, dict[str, dict[str, Any]]
        ] = from_json_dict.get("datamodelWarnings", {})
        """Dictionnary containing current datamodel warnings, for notifications"""

        self.exception: str | None = from_json_dict.get("exception")
        """String containg latest exception trace"""

        self.initstartoffset: Any | None = from_json_dict.get("initstartoffset")
        self.initstopoffset: Any | None = from_json_dict.get("initstopoffset")
        self.nextoffset: Any | None = from_json_dict.get("nextoffset")

    def savecachefile(self, cacheFilename: str | None = None):
        """Override method only to disable backup files in cache"""
        return super().savecachefile(cacheFilename, dontKeepBackup=True)


class GenericClient:
    """Superclass of all hermes-client implementations.
    Manage all the internals of hermes for a client : datamodel updates, caching, error management, trashbin and
    converting messages from message bus into events handlers calls"""

    def __init__(self, config: HermesConfig):
        """Instanciate a new client"""

        # Setup the signals handler
        config.setSignalsHandler(self.__signalHandler)

        self.__config: HermesConfig = config
        """Current config"""
        try:
            self.config: dict[str, Any] = self.__config[self.__config["appname"]]
            """Dict containing the client plugin configuration"""
        except KeyError:
            self.config = {}

        self.__previousconfig: HermesConfig = HermesConfig.loadcachefile(
            "_hermesconfig"
        )
        """Previous config (from cache)"""

        self._msgbus: AbstractMessageBusConsumerPlugin = self.__config["hermes"][
            "plugins"
        ]["messagebus"]["plugininstance"]
        self._msgbus.setTimeout(self.__config["hermes-client"]["updateInterval"] * 1000)

        self.__cache: HermesClientCache = HermesClientCache.loadcachefile(
            f"_{self.__config['appname']}"
        )
        """Cached attributes"""
        self.__cache.setCacheFilename(f"_{self.__config['appname']}")

        self.__startTime: datetime | None = None
        """Datetime when mainloop was started"""

        self.__isPaused: datetime | None = None
        """Contains pause datetime if standard processing is paused, None otherwise"""

        self.__isStopped: bool = False
        """mainloop() will run until this var is set to True"""

        self.__sock: SockServer | None = None
        """Facultative socket to allow cli communication"""
        if self.__config["hermes"]["cli_socket"]["path"] is not None:
            self.__sock = SockServer(
                path=self.__config["hermes"]["cli_socket"]["path"],
                owner=self.__config["hermes"]["cli_socket"]["owner"],
                group=self.__config["hermes"]["cli_socket"]["group"],
                mode=self.__config["hermes"]["cli_socket"]["mode"],
                processHdlr=self.__processSocketMessage,
            )
            self.__setupSocketParser()

        self.__useFirstInitsyncSequence: bool = self.__config["hermes-client"][
            "useFirstInitsyncSequence"
        ]
        """Indicate if we prefer using the first/oldest or last/most recent
        initsync sequence available on message bus"""

        self.__newdatamodel: Datamodel = Datamodel(config=self.__config)
        """New datamodel (from current config)"""

        if self.__previousconfig.hasData():
            # Start app with previous datamodel to be able to check differences with
            # new one through self.__processDatamodelUpdate()
            self.__datamodel: Datamodel = Datamodel(config=self.__previousconfig)
            """Current datamodel"""
        else:
            # As no previous datamodel is available, start app with new one
            self.__datamodel = self.__newdatamodel

        self.__trashbin_retention: timedelta | None = None
        """Timedelta with delay to keep removed data in trashbin before permanently
        deleting it. 'None' means no trashbin"""
        if self.__config["hermes-client"]["trashbin_retention"] > 0:
            self.__trashbin_retention = timedelta(
                days=self.__config["hermes-client"]["trashbin_retention"]
            )

        self.__trashbin_purgeInterval: timedelta | None = timedelta(
            minutes=self.__config["hermes-client"]["trashbin_purgeInterval"]
        )
        """Timedelta with delay between two trashbin purge attempts"""

        self.__trashbin_lastpurge: datetime = datetime(year=1, month=1, day=1)
        """Datetime when latest trashbin purge was ran"""

        self.__errorQueue_retryInterval: timedelta | None = timedelta(
            minutes=self.__config["hermes-client"]["errorQueue_retryInterval"]
        )
        """Timedelta with delay between two attempts of processing events in error"""

        self.__errorQueue_lastretry: datetime = datetime(year=1, month=1, day=1)
        """Datetime when latest error queue retry was ran"""

        self.__currentStep: int = 0
        """Store the step number of current event processing. Will be stored in events in
        error queue to allow clients to resume an event where it has failed"""

        self.__saveRequired: bool = False
        """Reset to False at each loop start, and if any change is made during
        processing, set to True in order to save all cache at the loop end.
        Used to avoid expensive .save() calls when unnecessary
        """

    def getObjectFromCache(self, objtype: str, objpkey: Any) -> DataObject:
        """Returns a deepcopy of an object from cache.
        Raise IndexError if objtype is invalid, or if objpkey is not found
        """
        return deepcopy(self.__datamodel.localdata[objtype][objpkey])

    def getDataobjectlistFromCache(self, objtype: str) -> DataObjectList:
        """Returns cache of specified objtype, by reference.
        WARNING : Any modification of the cache content will mess up your client !!!
        Raise IndexError if objtype is invalid
        """
        return self.__datamodel.localdata[objtype]

    def __signalHandler(self, signalnumber: int, frame: FrameType | None):
        """Signal handler that will be called on SIGINT and SIGTERM"""
        logger.critical(
            f"Signal '{signal.strsignal(signalnumber)}' received, terminating"
        )
        self.__isStopped = True

    def __setupSocketParser(self):
        """Set up the argparse context for unix socket commands"""
        self.__parser = SocketArgumentParser(
            description=f"Hermes client {self.__config['appname']} CLI",
            exit_on_error=False,
        )

        subparsers = self.__parser.add_subparsers(help="Sub-commands")

        # Quit
        sp_quit = subparsers.add_parser("quit", help=f"Stop {self.__config['appname']}")
        sp_quit.set_defaults(func=self.__sock_quit)

        # Pause
        sp_pause = subparsers.add_parser(
            "pause", help="Pause processing until 'resume' command is sent"
        )
        sp_pause.set_defaults(func=self.__sock_pause)

        # Resume
        sp_resume = subparsers.add_parser(
            "resume", help="Resume processing that has been paused with 'pause'"
        )
        sp_resume.set_defaults(func=self.__sock_resume)

        # Status
        sp_status = subparsers.add_parser(
            "status", help=f"Show {self.__config['appname']} status"
        )
        sp_status.set_defaults(func=self.__sock_status)
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

    def __processSocketMessage(
        self, msg: SocketMessageToServer
    ) -> SocketMessageToClient:
        """Handler that process specified msg received on unix socket and returns the answer
        to send"""
        reply: SocketMessageToClient | None = None

        try:
            args = self.__parser.parse_args(msg.argv)
            if "func" not in args:
                raise SocketParsingMessage(self.__parser.format_help())
        except (SocketParsingError, SocketParsingMessage) as e:
            retmsg = str(e)
        except argparse.ArgumentError as e:
            retmsg = self.__parser.format_error(str(e))
        else:
            try:
                reply = args.func(args)
            except Exception as e:
                lines = traceback.format_exception(type(e), e, e.__traceback__)
                trace = "".join(lines).strip()
                logger.critical(f"Unhandled exception : {trace}")
                retmsg = trace

        if reply is None:  # Error was met
            reply = SocketMessageToClient(retcode=1, retmsg=retmsg)

        return reply

    def __sock_quit(self, args: argparse.Namespace) -> SocketMessageToClient:
        """Handler called when quit subcommand is requested on unix socket"""
        self.__isStopped = True
        logger.info(f"{self.__config['appname']} has been requested to quit")
        return SocketMessageToClient(retcode=0, retmsg="")

    def __sock_pause(self, args: argparse.Namespace) -> SocketMessageToClient:
        """Handler called when pause subcommand is requested on unix socket"""
        if self.__isStopped:
            return SocketMessageToClient(
                retcode=1,
                retmsg=f"Error : {self.__config['appname']} is currently being stopped",
            )

        if self.__isPaused:
            return SocketMessageToClient(
                retcode=1,
                retmsg=f"Error : {self.__config['appname']} is already paused",
            )

        logger.info(f"{self.__config['appname']} has been requested to pause")
        self.__isPaused = datetime.now()
        return SocketMessageToClient(retcode=0, retmsg="")

    def __sock_resume(self, args: argparse.Namespace) -> SocketMessageToClient:
        """Handler called when resume subcommand is requested on unix socket"""
        if self.__isStopped:
            return SocketMessageToClient(
                retcode=1,
                retmsg=f"Error : {self.__config['appname']} is currently being stopped",
            )

        if not self.__isPaused:
            return SocketMessageToClient(
                retcode=1, retmsg=f"Error : {self.__config['appname']} is not paused"
            )

        logger.info(f"{self.__config['appname']} has been requested to resume")
        self.__isPaused = None
        return SocketMessageToClient(retcode=0, retmsg="")

    def __sock_status(self, args: argparse.Namespace) -> SocketMessageToClient:
        """Handler called when status subcommand is requested on unix socket"""
        status = self.__status(verbose=args.verbose)
        if args.json:
            msg = json.dumps(status, cls=JSONEncoder, indent=4)
        else:
            nl = "\n"
            info2printable = {}
            msg = ""
            for objname in [self.__config["appname"]] + list(
                status.keys() - (self.__config["appname"],)
            ):
                infos = status[objname]
                msg += f"{objname} :{nl}"
                for category in ("information", "warning", "error"):
                    if category not in infos:
                        continue
                    if not infos[category]:
                        msg += f"  * {category.capitalize()} : []{nl}"
                        continue

                    msg += f"  * {category.capitalize()}{nl}"
                    for infoname, infodata in infos[category].items():
                        indentedinfodata = str(infodata).replace("\n", "\n      ")
                        msg += f"    - {info2printable.get(infoname, infoname)} : {indentedinfodata}{nl}"
            msg = msg.rstrip()

        return SocketMessageToClient(retcode=0, retmsg=msg)

    @property
    def currentStep(self) -> int:
        """Step number of current event processed.
        Allow clients to resume an event where it has failed"""
        return self.__currentStep

    @currentStep.setter
    def currentStep(self, value: int):
        if type(value) != int:
            raise TypeError(
                f"Specified step {value=} has invalid type '{type(value)}' instead of int"
            )

        if value < 0:
            raise ValueError(f"Specified step {value=} must be greater or equal to 0")

        self.__currentStep = value

    def mainLoop(self):
        """Client main loop"""
        self.__startTime = datetime.now()

        self.__checkDatamodelWarnings()
        # TODO : implement a check to ensure subclasses required data types and
        # attributes exist in datamodel

        if self.__datamodel.hasRemoteSchema():
            logger.debug(
                f"Remote Dataschema in cache : {self.__datamodel.remote_schema.to_json()=}"
            )
            self.__datamodel.loadErrorQueue()
        else:
            logger.debug(f"No remote Dataschema in cache yet")

        if self.__sock is not None:
            self.__sock.startProcessMessagesDaemon()

        isFirstLoopIteration: bool = True
        while not self.__isStopped:
            self.__saveRequired = False

            with self._msgbus:
                try:
                    if self.__isPaused:
                        sleep(1)
                        continue

                    if self.__hasAlreadyBeenInitialized():
                        if isFirstLoopIteration:
                            try:
                                self.__processDatamodelUpdate()
                            except Exception as e:
                                self.__notifyFatalException(
                                    HermesClientHandlerError.exceptionToString(
                                        e, purgeCurrentFileFromTrace=False
                                    )
                                )
                                raise HermesAlreadyNotifiedException
                        self.__retryErrorQueue()
                        self.__emptyTrashBin()
                        self.__processEvents(isInitSync=False)
                    else:
                        logger.info(
                            f"Client hasn't ran its first initsync sequence yet"
                        )
                        if self.__canBeInitialized():
                            logger.info(f"First initsync sequence processing begins")
                            self.__processEvents(isInitSync=True)
                            if self.__hasAlreadyBeenInitialized():
                                logger.info(
                                    f"First initsync sequence processing completed"
                                )
                        else:
                            logger.info(
                                f"No initsync sequence is available on message bus. Retry..."
                            )

                    self.__notifyException(None)

                except HermesAlreadyNotifiedException:
                    pass
                except Exception as e:
                    self.__notifyException(
                        HermesClientHandlerError.exceptionToString(
                            e, purgeCurrentFileFromTrace=False
                        )
                    )
                finally:
                    isFirstLoopIteration = False
                    if self.__saveRequired or self.__isStopped:
                        self.__datamodel.saveErrorQueue()
                        self.__cache.savecachefile()
                        if self.__hasAtLeastBeganInitialization():
                            self.__datamodel.saveLocalAndRemoteData()
                        self.__callHandler("", "save")  # Call special event "on_save()"
                        self.__notifyQueueErrors()

    def __retryErrorQueue(self):
        # Enforce retryInterval
        now = datetime.now()
        if now < self.__errorQueue_lastretry + self.__errorQueue_retryInterval:
            return  # Too early to process again

        eventNumber: int
        eventType: str
        event: Event
        for eventNumber, eventType, event, errorMsg in self.__datamodel.errorqueue:
            match eventType:
                case "remote":
                    logger.info(
                        f"Retrying to process remote event {event} from error queue"
                    )
                    try:
                        self.__processRemoteEvent(event, enqueueEventWithError=False)
                    except HermesClientHandlerError as e:
                        logger.info(f"... failed on step {self.currentStep} : {str(e)}")
                        event.step = self.currentStep
                        self.__datamodel.errorqueue.updateErrorMsg(eventNumber, e.msg)
                    else:
                        # If event has suppressed object, eventNumber has already been
                        # purged from queue
                        self.__datamodel.errorqueue.remove(
                            eventNumber, ignoreMissingEventNumber=True
                        )
                case "local":
                    logger.info(
                        f"Retrying to process local event {event} from error queue"
                    )
                    try:
                        self.__processLocalEvent(event, enqueueEventWithError=False)
                    except HermesClientHandlerError as e:
                        logger.info(f"... failed on step {self.currentStep} : {str(e)}")
                        event.step = self.currentStep
                        self.__datamodel.errorqueue.updateErrorMsg(eventNumber, e.msg)
                    else:
                        # If event has suppressed object, eventNumber has already been
                        # purged from queue
                        self.__datamodel.errorqueue.remove(
                            eventNumber, ignoreMissingEventNumber=True
                        )
            while self.__isPaused and not self.__isStopped:
                sleep(1)  # Allow loop to be paused
            if self.__isStopped:
                break  # Allow loop to be interrupted if requested
        else:
            # Update __errorQueue_lastretry only if loop hasn't been interrupted
            self.__errorQueue_lastretry = now

    def __emptyTrashBin(self):
        # Enforce purgeInterval
        now = datetime.now()
        if now < self.__trashbin_lastpurge + self.__trashbin_purgeInterval:
            return  # Too early to process again
        if self.__trashbin_retention is not None:
            retentionLimit = datetime.now() - self.__trashbin_retention

        objtype: str
        objs: DataObjectList
        # As we'll remove objects, process data in the datamodel's reversed declaration
        # order
        for objtype, objs in reversed(self.__datamodel.remotedata.items()):
            if not objtype.startswith("trashbin_"):
                continue

            for pkey in objs.getPKeys():
                obj = objs.get(pkey)
                if (
                    self.__trashbin_retention is None
                    or obj._trashbin_timestamp < retentionLimit
                ):
                    event = Event(
                        evcategory="base", eventtype="removed", obj=obj, objattrs={}
                    )
                    logger.info(f"Trying to purge {repr(obj)} from trashbin")
                    if self.__datamodel.errorqueue.containsObjectByEvent(
                        "remote", event
                    ):
                        try:
                            self.__processRemoteEvent(
                                event, enqueueEventWithError=False
                            )
                        except HermesClientHandlerError:
                            pass
                    else:
                        self.__processRemoteEvent(event, enqueueEventWithError=True)

                while self.__isPaused and not self.__isStopped:
                    sleep(1)  # Allow loop to be paused
                if self.__isStopped:
                    break  # Allow loop to be interrupted if requested

            while self.__isPaused and not self.__isStopped:
                sleep(1)  # Allow loop to be paused
            if self.__isStopped:
                break  # Allow loop to be interrupted if requested
        else:
            # Update __trashbin_lastpurge only if loop hasn't been interrupted
            self.__trashbin_lastpurge = now

    def __hasAlreadyBeenInitialized(self) -> bool:
        if (
            self.__cache.initstartoffset is None
            or self.__cache.initstopoffset is None
            or self.__cache.nextoffset is None
            or self.__cache.nextoffset < self.__cache.initstopoffset
        ):
            return False
        return True

    def __hasAtLeastBeganInitialization(self) -> bool:
        return (
            self.__cache.initstartoffset is not None
            and self.__datamodel.hasRemoteSchema()
        )

    def __canBeInitialized(self) -> bool:
        self._msgbus.seekToBeginning()

        # List of (start, stop) offsets of initsync sequences found
        initSyncFound: list[tuple[Any, Any]] = []

        start = None
        stop = None
        event: Event
        for event in self._msgbus:
            if event.evcategory != "initsync":
                continue
            if event.eventtype == "init-start":
                start = event.offset
            elif event.eventtype == "init-stop" and start is not None:
                stop = event.offset
                initSyncFound.append(
                    (start, stop),
                )
                if self.__useFirstInitsyncSequence:
                    break  # We found the first sequence
                else:
                    # Continue to find a new complete sequence
                    start = None
                    stop = None

        if not initSyncFound:
            return False

        if self.__useFirstInitsyncSequence:
            start, stop = initSyncFound[0]
        else:
            start, stop = initSyncFound[-1]

        if self.__cache.nextoffset is None or self.__cache.nextoffset < start:
            self.__cache.nextoffset = start

        self.__cache.initstartoffset = start
        self.__cache.initstopoffset = stop
        logger.debug(
            f"Init sequence was found in Kafka at offsets [{self.__cache.initstartoffset} ; {self.__cache.initstopoffset}]"
        )
        return True

    def __updateSchema(self, newSchema: Dataschema):
        self.__datamodel.updateSchema(newSchema)
        self.__config.savecachefile()  # Save config to be able to rebuild datamodel
        # Save and reload error queue to purge it from events of suppressed types, if any
        self.__datamodel.saveErrorQueue()
        self.__datamodel.loadErrorQueue()
        self.__checkDatamodelWarnings()

    def __checkDatamodelWarnings(self):
        if self.__datamodel.unknownRemoteTypes:
            logger.warning(
                f"Datamodel errors : remote type '{self.__datamodel.unknownRemoteTypes}' doesn't exist in current Dataschema"
            )

        if self.__datamodel.unknownRemoteAttributes:
            logger.warning(
                f"Datamodel errors : remote attributes doesn't exist in current Dataschema : {self.__datamodel.unknownRemoteAttributes}"
            )
        self.__notifyDatamodelWarnings()

    def __processEvents(self, isInitSync=False):
        remote_event: Event
        schema: Dataschema | None = None
        evcategory: str = "initsync" if isInitSync else "base"

        self._msgbus.seek(self.__cache.nextoffset)

        for remote_event in self._msgbus:
            self.__saveRequired = True
            if isInitSync and remote_event.offset > self.__cache.initstopoffset:
                # Should never be called
                self.__cache.nextoffset = remote_event.offset + 1
                break

            # TODO : implement data consistency check if event.evcategory==initsync
            # and evcategory==base

            if remote_event.evcategory != evcategory:
                self.__cache.nextoffset = remote_event.offset + 1
                continue

            if isInitSync:
                if remote_event.eventtype == "init-start":
                    schema = Dataschema.from_json(remote_event.objattrs)
                    self.__updateSchema(schema)
                    continue

                if remote_event.eventtype == "init-stop":
                    self.__cache.nextoffset = remote_event.offset + 1
                    break

                if schema is None and not self.__hasAtLeastBeganInitialization():
                    msg = "Invalid initsync sequence met, ignoring"
                    logger.critical(msg)
                    return

            # Traiter message "standard"
            match remote_event.eventtype:
                case "added" | "modified" | "removed":
                    self.__processRemoteEvent(remote_event, enqueueEventWithError=True)
                case "dataschema":
                    schema = Dataschema.from_json(remote_event.objattrs)
                    self.__updateSchema(schema)
                case _:
                    logger.error(
                        f"Received an event with unknown type '{remote_event.eventtype}' : ignored"
                    )

            self.__cache.nextoffset = remote_event.offset + 1

            while self.__isPaused and not self.__isStopped:
                sleep(1)  # Allow loop to be paused
            if self.__isStopped:
                break  # Allow loop to be interrupted if requested

    def __processRemoteEvent(
        self,
        remote_event: Event | None,
        enqueueEventWithError: bool,
        simulateOnly: bool = False,
    ):
        secretAttrs = self.__datamodel.remote_schema.secretsAttributesOf(
            remote_event.objtype
        )
        logger.debug(f"__processRemoteEvent({remote_event.toString(secretAttrs)})")
        self.__saveRequired = True

        if (
            not simulateOnly
            and enqueueEventWithError
            and self.__datamodel.errorqueue.containsObjectByEvent(
                "remote", remote_event
            )
        ):
            secretAttrs = self.__datamodel.remote_schema.secretsAttributesOf(
                remote_event.objtype
            )
            errorMsg = f"Object in remote event {remote_event.toString(secretAttrs)} already had unresolved errors : appending event to error queue"
            logger.warning(errorMsg)
            self.__processRemoteEvent(
                remote_event, enqueueEventWithError=False, simulateOnly=True
            )
            self.__datamodel.errorqueue.append("remote", remote_event, errorMsg)
            return

        # In case of modification, try to compose full object in order to provide all
        # attributes values, in order to render Jinja Template with several vars.
        # In this specific case, one of the template's var may have been modified,
        # but not the other, so the event's attrs are not enough to process the
        # template rendering
        r_obj_complete: DataObject | None = None
        if remote_event.eventtype == "modified":
            cache_complete, r_cachedobj_complete = self.__getObjectFromCacheOrTrashbin(
                self.__datamodel.remotedata_complete,
                remote_event.objtype,
                remote_event.objpkey,
            )
            if r_cachedobj_complete is not None:
                r_obj_complete = self.__getUpdatedObject(
                    r_cachedobj_complete, remote_event.objattrs
                )

        local_event = self.__datamodel.convertEventToLocal(remote_event, r_obj_complete)
        trashbin = self.__datamodel.remotedata[f"trashbin_{remote_event.objtype}"]
        try:
            match remote_event.eventtype:
                case "added":
                    if (
                        self.__trashbin_retention is not None
                        and remote_event.objpkey in trashbin
                    ):
                        # Object is in trashbin, recycle it
                        self.__remoteRecycled(remote_event, local_event, simulateOnly)
                    else:
                        # Add new object
                        self.__remoteAdded(remote_event, local_event, simulateOnly)

                case "modified":
                    self.__remoteModified(remote_event, local_event, simulateOnly)

                case "removed":
                    # Remove object on any of these conditions :
                    #   - trashbin retention is disabled
                    #   - object is already in trashbin
                    if (
                        self.__trashbin_retention is None
                        or remote_event.objpkey in trashbin
                    ):
                        # Remove object
                        self.__remoteRemoved(remote_event, local_event, simulateOnly)
                    else:
                        # Store object in trashbin
                        self.__remoteTrashed(remote_event, local_event, simulateOnly)
        except HermesClientHandlerError as e:
            if not simulateOnly and enqueueEventWithError:
                self.__processRemoteEvent(
                    remote_event, enqueueEventWithError=False, simulateOnly=True
                )
                remote_event.step = self.currentStep
                self.__datamodel.errorqueue.append("remote", remote_event, e.msg)
            else:
                raise

    def __processLocalEvent(
        self,
        local_event: Event | None,
        enqueueEventWithError: bool,
        simulateOnly: bool = False,
    ):
        if local_event is None:
            logger.debug(f"__processLocalEvent(None)")
            return

        secretAttrs = self.__datamodel.local_schema.secretsAttributesOf(
            local_event.objtype
        )
        logger.debug(f"__processLocalEvent({local_event.toString(secretAttrs)})")

        self.__saveRequired = True

        if not simulateOnly:
            self.currentStep = local_event.step  # Reset current step

        if (
            not simulateOnly
            and enqueueEventWithError
            and self.__datamodel.errorqueue.containsObjectByEvent("local", local_event)
        ):
            secretAttrs = self.__datamodel.local_schema.secretsAttributesOf(
                local_event.objtype
            )
            errorMsg = f"Object in local event {local_event.toString(secretAttrs)} has unresolved errors, appending event to error queue"
            logger.info(errorMsg)
            self.__processLocalEvent(
                local_event, enqueueEventWithError=False, simulateOnly=True
            )
            self.__datamodel.errorqueue.append("local", local_event, errorMsg)
            return

        trashbin = self.__datamodel.localdata[f"trashbin_{local_event.objtype}"]
        try:
            match local_event.eventtype:
                case "added":
                    if (
                        self.__trashbin_retention is not None
                        and local_event.objpkey in trashbin
                    ):
                        # Object is in trashbin, recycle it
                        self.__localRecycled(local_event, simulateOnly)
                    else:
                        self.__localAdded(local_event, simulateOnly)
                case "modified":
                    if not simulateOnly and local_event.objpkey in trashbin:
                        # Object is in trashbin, and cannot be modified until it is restored
                        if enqueueEventWithError:
                            # As the object's changes will be processed at restore, ignore the change
                            self.__processLocalEvent(
                                local_event,
                                enqueueEventWithError=False,
                                simulateOnly=True,
                            )
                        else:
                            # Propagate error as requested
                            raise HermesClientHandlerError(
                                f"Object of event {repr(local_event)} is in trashbin, and cannot be modified until it is restored"
                            )
                    else:
                        self.__localModified(local_event, simulateOnly)
                case "removed":
                    # Remove object on any of these conditions :
                    #   - trashbin retention is disabled
                    #   - object is already in trashbin
                    if (
                        self.__trashbin_retention is None
                        or local_event.objpkey in trashbin
                    ):
                        self.__localRemoved(local_event, simulateOnly)
                    else:
                        self.__localTrashed(local_event, simulateOnly)
        except HermesClientHandlerError as e:
            if not simulateOnly and enqueueEventWithError:
                self.__processLocalEvent(
                    local_event, enqueueEventWithError=False, simulateOnly=True
                )
                local_event.step = self.currentStep
                self.__datamodel.errorqueue.append("local", local_event, e.msg)
            else:
                raise

    def __remoteAdded(
        self, remote_event: Event, local_event: Event, simulateOnly: bool = False
    ):
        secretAttrs = self.__datamodel.remote_schema.secretsAttributesOf(
            remote_event.objtype
        )
        logger.debug(f"__remoteAdded({remote_event.toString(secretAttrs)})")

        r_obj = self.__datamodel.createRemoteDataobject(
            remote_event.objtype, remote_event.objattrs
        )
        self.__processLocalEvent(
            local_event, enqueueEventWithError=False, simulateOnly=simulateOnly
        )

        # Add remote object to cache
        if not simulateOnly:
            self.__datamodel.remotedata[remote_event.objtype].append(r_obj)
        # May already been added if current event is from errorqueue
        if r_obj not in self.__datamodel.remotedata_complete[remote_event.objtype]:
            self.__datamodel.remotedata_complete[remote_event.objtype].append(r_obj)

    def __localAdded(self, local_ev: Event, simulateOnly: bool = False):
        secretAttrs = self.__datamodel.local_schema.secretsAttributesOf(
            local_ev.objtype
        )
        logger.debug(f"__localAdded({local_ev.toString(secretAttrs)})")

        l_obj = self.__datamodel.createLocalDataobject(
            local_ev.objtype, local_ev.objattrs
        )

        if not simulateOnly:
            # Call added handler
            self.__callHandler(
                objtype=local_ev.objtype,
                eventtype="added",
                objkey=local_ev.objpkey,
                eventattrs=local_ev.objattrs,
                newobj=deepcopy(l_obj),
            )

        # Add local object to cache
        if not simulateOnly:
            self.__datamodel.localdata[local_ev.objtype].append(l_obj)
        # May already been added if current event is from errorqueue
        if l_obj not in self.__datamodel.localdata_complete[local_ev.objtype]:
            self.__datamodel.localdata_complete[local_ev.objtype].append(l_obj)

    def __remoteRecycled(
        self, remote_event: Event, local_event: Event, simulateOnly: bool = False
    ):
        secretAttrs = self.__datamodel.remote_schema.secretsAttributesOf(
            remote_event.objtype
        )
        logger.debug(f"__remoteRecycled({remote_event.toString(secretAttrs)})")
        maincache = self.__datamodel.remotedata[remote_event.objtype]
        maincache_complete = self.__datamodel.remotedata_complete[remote_event.objtype]
        trashbin = self.__datamodel.remotedata[f"trashbin_{remote_event.objtype}"]
        trashbin_complete = self.__datamodel.remotedata_complete[
            f"trashbin_{remote_event.objtype}"
        ]

        r_obj = self.__datamodel.createRemoteDataobject(
            remote_event.objtype, remote_event.objattrs
        )

        self.__processLocalEvent(
            local_event, enqueueEventWithError=False, simulateOnly=simulateOnly
        )

        # Remove remote object from trashbin
        if not simulateOnly:
            trashbin.removeByPkey(remote_event.objpkey)
        trashbin_complete.removeByPkey(remote_event.objpkey)
        # Restore remote object, with its potential changes, in main cache
        if not simulateOnly:
            maincache.append(r_obj)
        # May already been recycled if current event is from errorqueue
        if r_obj not in maincache_complete:
            maincache_complete.append(r_obj)

    def __localRecycled(self, local_ev: Event, simulateOnly: bool = False):
        secretAttrs = self.__datamodel.local_schema.secretsAttributesOf(
            local_ev.objtype
        )
        logger.debug(f"__localRecycled({local_ev.toString(secretAttrs)})")
        maincache = self.__datamodel.localdata[local_ev.objtype]
        maincache_complete = self.__datamodel.localdata_complete[local_ev.objtype]
        trashbin = self.__datamodel.localdata[f"trashbin_{local_ev.objtype}"]
        trashbin_complete = self.__datamodel.localdata_complete[
            f"trashbin_{local_ev.objtype}"
        ]

        l_obj = self.__datamodel.createLocalDataobject(
            local_ev.objtype, local_ev.objattrs
        )
        l_obj_trash: DataObject = deepcopy(trashbin.get(local_ev.objpkey))
        del l_obj_trash._trashbin_timestamp  # Remove trashbin timestamp from object

        l_obj_trash_complete: DataObject = deepcopy(
            trashbin_complete.get(local_ev.objpkey)
        )

        # May already been recycled if current event is from errorqueue
        if l_obj_trash_complete is not None:
            del (
                l_obj_trash_complete._trashbin_timestamp
            )  # Remove trashbin timestamp from object

        if not simulateOnly:
            # Call recycled handler
            self.__callHandler(
                objtype=local_ev.objtype,
                eventtype="recycled",
                objkey=l_obj_trash.getPKey(),
                eventattrs=l_obj_trash.toNative(),
                newobj=deepcopy(l_obj_trash),
            )

        if not simulateOnly:
            # Remove local object from trashbin
            trashbin.remove(l_obj_trash)
            # Restore local object in main cache
            maincache.append(l_obj_trash)

        # May already been recycled if current event is from errorqueue
        if l_obj_trash_complete is not None:
            trashbin_complete.remove(l_obj_trash_complete)
            maincache_complete.append(l_obj_trash_complete)

        diff = l_obj.diffFrom(l_obj_trash)  # Handle local object's changes if any
        if diff and not simulateOnly:
            (event, obj) = Event.fromDiffItem(
                diffitem=diff,
                eventCategory=local_ev.evcategory,
                changeType="modified",
            )
            # Hack : we pass this second event (modified) to error queue in order to
            # postpone its processing once all caches of previous one are up to date.
            # Otherwise, if an error is met on this second event (modified), we'll try
            # to reprocess the first one (recycled)
            self.__datamodel.errorqueue.append("local", event, errorMsg=None)
            # ... and force error queue to be retried asap in order to process the
            # pending event
            self.__errorQueue_lastretry = datetime(year=1, month=1, day=1)

    def __remoteModified(
        self, remote_event: Event, local_event: Event, simulateOnly: bool = False
    ):
        secretAttrs = self.__datamodel.remote_schema.secretsAttributesOf(
            remote_event.objtype
        )
        logger.debug(f"__remoteModified({remote_event.toString(secretAttrs)})")
        maincache = self.__datamodel.remotedata[remote_event.objtype]

        if not simulateOnly:
            r_cachedobj: DataObject = maincache.get(remote_event.objpkey)
            r_obj = self.__getUpdatedObject(r_cachedobj, remote_event.objattrs)

        cache_complete, r_cachedobj_complete = self.__getObjectFromCacheOrTrashbin(
            self.__datamodel.remotedata_complete,
            remote_event.objtype,
            remote_event.objpkey,
        )
        r_obj_complete = self.__getUpdatedObject(
            r_cachedobj_complete, remote_event.objattrs
        )

        self.__processLocalEvent(
            local_event, enqueueEventWithError=False, simulateOnly=simulateOnly
        )

        # Update remote object in cache
        if not simulateOnly:
            maincache.replace(r_obj)

        # May not exist
        if cache_complete is not None:
            cache_complete.replace(r_obj_complete)

    def __localModified(self, local_ev: Event, simulateOnly: bool = False):
        secretAttrs = self.__datamodel.local_schema.secretsAttributesOf(
            local_ev.objtype
        )
        logger.debug(f"__localModified({local_ev.toString(secretAttrs)})")
        maincache = self.__datamodel.localdata[local_ev.objtype]

        if not simulateOnly:
            l_cachedobj: DataObject = maincache.get(local_ev.objpkey)
            l_obj = self.__getUpdatedObject(l_cachedobj, local_ev.objattrs)

        cache_complete, l_cachedobj_complete = self.__getObjectFromCacheOrTrashbin(
            self.__datamodel.localdata_complete, local_ev.objtype, local_ev.objpkey
        )

        # May not exist
        if cache_complete is not None:
            l_obj_complete = self.__getUpdatedObject(
                l_cachedobj_complete, local_ev.objattrs
            )

        if not simulateOnly:
            # Call modified handler
            self.__callHandler(
                objtype=local_ev.objtype,
                eventtype="modified",
                objkey=local_ev.objpkey,
                eventattrs=local_ev.objattrs,
                newobj=deepcopy(l_obj),
                cachedobj=deepcopy(l_cachedobj),
            )

        # Update local object in cache
        if not simulateOnly:
            maincache.replace(l_obj)

        # May not exist
        if cache_complete is not None:
            cache_complete.replace(l_obj_complete)

    def __remoteTrashed(
        self, remote_event: Event, local_event: Event, simulateOnly: bool = False
    ):
        secretAttrs = self.__datamodel.remote_schema.secretsAttributesOf(
            remote_event.objtype
        )
        logger.debug(f"__remoteTrashed({remote_event.toString(secretAttrs)})")
        maincache = self.__datamodel.remotedata[remote_event.objtype]
        maincache_complete = self.__datamodel.remotedata_complete[remote_event.objtype]
        trashbin = self.__datamodel.remotedata[f"trashbin_{remote_event.objtype}"]
        trashbin_complete = self.__datamodel.remotedata_complete[
            f"trashbin_{remote_event.objtype}"
        ]

        r_cachedobj: DataObject = maincache.get(remote_event.objpkey)
        r_cachedobj_complete: DataObject = maincache_complete.get(remote_event.objpkey)

        self.__processLocalEvent(
            local_event, enqueueEventWithError=False, simulateOnly=simulateOnly
        )

        if not simulateOnly:
            # Remove remote object from cache
            maincache.remove(r_cachedobj)
            r_cachedobj._trashbin_timestamp = remote_event.timestamp
            # Add remote object to trashbin
            trashbin.append(r_cachedobj)

        if r_cachedobj_complete is not None:
            maincache_complete.remove(r_cachedobj_complete)
            r_cachedobj_complete._trashbin_timestamp = remote_event.timestamp
            trashbin_complete.append(r_cachedobj_complete)

    def __localTrashed(self, local_ev: Event, simulateOnly: bool = False):
        secretAttrs = self.__datamodel.local_schema.secretsAttributesOf(
            local_ev.objtype
        )
        logger.debug(f"__localTrashed({local_ev.toString(secretAttrs)})")
        maincache = self.__datamodel.localdata[local_ev.objtype]
        maincache_complete = self.__datamodel.localdata_complete[local_ev.objtype]
        trashbin = self.__datamodel.localdata[f"trashbin_{local_ev.objtype}"]
        trashbin_complete = self.__datamodel.localdata_complete[
            f"trashbin_{local_ev.objtype}"
        ]

        l_cachedobj: DataObject = maincache.get(local_ev.objpkey)
        l_cachedobj_complete: DataObject = maincache_complete.get(local_ev.objpkey)

        if not simulateOnly:
            # Call trashed handler
            self.__callHandler(
                objtype=local_ev.objtype,
                eventtype="trashed",
                objkey=local_ev.objpkey,
                eventattrs=local_ev.objattrs,
                cachedobj=deepcopy(l_cachedobj),
            )

        if not simulateOnly:
            # Remove local object from cache
            maincache.remove(l_cachedobj)
            l_cachedobj._trashbin_timestamp = local_ev.timestamp
            # Add local object to trashbin
            trashbin.append(l_cachedobj)

        if l_cachedobj_complete is not None:
            maincache_complete.remove(l_cachedobj_complete)
            l_cachedobj_complete._trashbin_timestamp = local_ev.timestamp
            trashbin_complete.append(l_cachedobj_complete)

    def __remoteRemoved(
        self, remote_event: Event, local_event: Event, simulateOnly: bool = False
    ):
        secretAttrs = self.__datamodel.remote_schema.secretsAttributesOf(
            remote_event.objtype
        )
        logger.debug(f"__remoteRemoved({remote_event.toString(secretAttrs)})")

        cache, r_cachedobj = self.__getObjectFromCacheOrTrashbin(
            self.__datamodel.remotedata,
            remote_event.objtype,
            remote_event.objpkey,
        )

        cache_complete, r_cachedobj_complete = self.__getObjectFromCacheOrTrashbin(
            self.__datamodel.remotedata_complete,
            remote_event.objtype,
            remote_event.objpkey,
        )

        self.__processLocalEvent(
            local_event, enqueueEventWithError=False, simulateOnly=simulateOnly
        )

        # Remove remote object from cache or trashbin
        if not simulateOnly:
            cache.remove(r_cachedobj)

        # May already been removed if current event is from errorqueue
        if cache_complete is not None:
            cache_complete.remove(r_cachedobj_complete)

        if not simulateOnly:
            # Remove eventual events relative to current object from error queue
            self.__datamodel.errorqueue.purgeAllEventsOfDataObject(
                "remote", r_cachedobj
            )

    def __localRemoved(self, local_ev: Event, simulateOnly: bool = False):
        secretAttrs = self.__datamodel.local_schema.secretsAttributesOf(
            local_ev.objtype
        )
        logger.debug(f"__localRemoved({local_ev.toString(secretAttrs)})")

        cache, l_cachedobj = self.__getObjectFromCacheOrTrashbin(
            self.__datamodel.localdata,
            local_ev.objtype,
            local_ev.objpkey,
        )

        cache_complete, l_cachedobj_complete = self.__getObjectFromCacheOrTrashbin(
            self.__datamodel.localdata_complete,
            local_ev.objtype,
            local_ev.objpkey,
        )

        if not simulateOnly:
            # Call removed handler
            self.__callHandler(
                objtype=local_ev.objtype,
                eventtype="removed",
                objkey=local_ev.objpkey,
                eventattrs=local_ev.objattrs,
                cachedobj=deepcopy(l_cachedobj),
            )

        # Remove local object from cache or trashbin
        if not simulateOnly:
            cache.remove(l_cachedobj)
        # May already been removed if current event is from errorqueue
        if cache_complete is not None:
            cache_complete.remove(l_cachedobj_complete)

        if not simulateOnly:
            # Remove eventual events relative to current object from error queue
            self.__datamodel.errorqueue.purgeAllEventsOfDataObject("local", l_cachedobj)

    def __callHandler(self, objtype: str, eventtype: str, **kwargs):
        if not objtype:
            handlerName = f"on_{eventtype}"
            kwargs_filtered = kwargs
        else:
            handlerName = f"on_{objtype}_{eventtype}"

            # Filter secrets values
            secretAttrs = self.__datamodel.local_schema.secretsAttributesOf(objtype)
            kwargs_filtered = kwargs.copy()
            kwargs_filtered["eventattrs"] = Event.objattrsToString(
                kwargs["eventattrs"], secretAttrs
            )

        kwargsstr = ", ".join([f"{k}={repr(v)}" for k, v in kwargs_filtered.items()])

        hdlr = getattr(self, handlerName, None)

        if not callable(hdlr):
            logger.debug(
                f"Calling '{handlerName}({kwargsstr})' : handler '{handlerName}()' doesn't exists"
            )
            return

        logger.info(
            f"Calling '{handlerName}({kwargsstr})' - currentStep={self.currentStep}"
        )

        try:
            hdlr(**kwargs)
        except Exception as e:
            logger.error(
                f"Calling '{handlerName}({kwargsstr})' : error met on step {self.currentStep} '{str(e)}'"
            )
            raise HermesClientHandlerError(e)

    def __getObjectFromCacheOrTrashbin(
        self, ds: Datasource, objtype: str, objpkey: Any
    ) -> tuple[DataObjectList | None, DataObject | None]:
        """Look for objpkey in maincache and trashbin of objtype in specified ds.
        If found, returns a tuple with a the DataObjectList where the object is, and the
        object itself. Otherwise, returns (None, None)"""
        src: DataObjectList
        obj: DataObject | None
        for src in (ds[objtype], ds[f"trashbin_{objtype}"]):
            obj = src.get(objpkey)
            if obj is not None:
                return (src, obj)
        return (None, None)

    def __processDatamodelUpdate(self):
        """Check difference between current datamodel and previous one. If datamodel has
        changed, generate local events according to datamodel changes"""

        diff = self.__newdatamodel.diffFrom(self.__datamodel)

        if not diff:
            logger.info("No change in datamodel")
            # Start working with new datamodel
            self.__datamodel = self.__newdatamodel
            self.__datamodel.loadErrorQueue()
            return

        logger.info(f"Datamodel has changed : {diff.dict}")
        self.__saveRequired = True

        # Start by removed types, as it requires the previous datamodel to process data removal
        if diff.removed:
            for l_objtype in diff.removed:
                logger.info(f"About to purge data from type '{l_objtype}'")
                if l_objtype not in self.__datamodel.typesmapping.values():
                    logger.warning(
                        f"Requested to purge data from type '{l_objtype}', but it doesn't exist in previous datamodel : ignoring"
                    )
                    continue

                pkeys = (
                    self.__datamodel.localdata[l_objtype].getPKeys()
                    | self.__datamodel.localdata[f"trashbin_{l_objtype}"].getPKeys()
                )

                # Call remove on each object
                for pkey in pkeys:
                    _, l_obj = self.__getObjectFromCacheOrTrashbin(
                        self.__datamodel.localdata, l_objtype, pkey
                    )
                    if l_obj:
                        l_ev = Event(
                            evcategory="base",
                            eventtype="removed",
                            obj=l_obj,
                            objattrs={},
                        )
                        secretAttrs = self.__datamodel.local_schema.secretsAttributesOf(
                            l_objtype
                        )
                        logger.debug(
                            f"Removing local object of {pkey=} : {l_ev.toString(secretAttrs)=}"
                        )
                        self.__localRemoved(l_ev)
                    else:
                        logger.error(f"Local object of {pkey=} not found")

                # All objects have been removed, remove remaining events from errorqueue, if any
                for l_obj in self.__datamodel.localdata_complete[l_objtype]:
                    # Remove eventual events relative to current object from error queue
                    self.__datamodel.errorqueue.purgeAllEventsOfDataObject(
                        "local", l_obj
                    )

            self.__datamodel.saveLocalAndRemoteData()  # Save changes

            # Purge old remote and local cache files, if any
            logger.info(
                f"Types removed from Datamodel : {diff.removed}, purging cache files"
            )
            Datamodel.purgeOldCacheFiles(diff.removed, cacheFilePrefix="__")

        # Start working with new datamodel
        self.__datamodel = self.__newdatamodel
        self.__datamodel.loadLocalAndRemoteData()

        # Reload error queue to allow it to handle new datamodel
        self.__datamodel.saveErrorQueue()
        self.__datamodel.loadErrorQueue()

        if diff.added or diff.modified:
            # Generate diff events according to datamodel changes
            new_local_data: dict[str, DataObjectList] = {}

            # Work on "complete" copy of data cache, representing the cache that should be
            # without any event in error queue in order to compute diff on complete cache
            # representation
            completeRemoteData = self.__datamodel.remotedata_complete
            completeLocalData = self.__datamodel.localdata_complete

            # Loop over each remote type
            for r_objtype in self.__datamodel.remote_schema.objectTypes:
                # For each type, we'll work on classic data, and on trashbin data
                for prefix in ("", "trashbin_"):
                    if r_objtype not in self.__datamodel.typesmapping:
                        continue  # Remote objtype isn't set in current Datamodel

                    # Fetch corresponding local type
                    l_objtype = f"{prefix}{self.__datamodel.typesmapping[r_objtype]}"

                    # Convert remote data cache to local data
                    new_local_data[
                        l_objtype
                    ] = self.__datamodel.convertDataObjectListToLocal(
                        r_objtype, completeRemoteData[f"{prefix}{r_objtype}"]
                    )

                    # Compute differences between new local data and local data cache
                    datadiff = new_local_data[l_objtype].diffFrom(
                        completeLocalData.get(l_objtype, DataObjectList([]))
                    )

                    for changeType, difflist in datadiff.dict.items():
                        diffitem: DiffObject | DataObject
                        for diffitem in difflist:
                            # Convert diffitem to local Event
                            (event, obj) = Event.fromDiffItem(
                                diffitem=diffitem,
                                eventCategory="base",
                                changeType=changeType,
                            )

                            if prefix == "trashbin_":
                                # Preserve object's _trashbin_timestamp
                                obj._trashbin_timestamp = completeLocalData[l_objtype][
                                    obj.getPKey()
                                ]._trashbin_timestamp

                            # Process Event and update cache if no error is met,
                            # enqueue event otherwise
                            self.__processLocalEvent(event, enqueueEventWithError=True)

        self.__config.savecachefile()  # Save config to be able to rebuild datamodel
        self.__datamodel.saveLocalAndRemoteData()  # Save data
        self.__checkDatamodelWarnings()

    @classmethod
    def __getUpdatedObject(
        cls, obj: DataObject, objattrs: dict[str, Any]
    ) -> DataObject:
        """Return a deepcopy of specified obj, with its attributes updated upon specified
        objattrs dict from Event"""
        newobj = deepcopy(obj)

        # Update newobj's attributes
        for attrname, value in objattrs["added"].items():
            setattr(newobj, attrname, value)  # Add new attributes
        for attrname, value in objattrs["modified"].items():
            setattr(newobj, attrname, value)  # Update existing attributes
        for attrname, value in objattrs["removed"].items():
            if hasattr(newobj, attrname):
                delattr(newobj, attrname)  # Delete existing attributes

        return newobj

    def __status(
        self, verbose=False, level="information", ignoreUnhandledExceptions=False
    ) -> dict[str, dict[str, dict[str, Any]]]:
        """Returns a dict containing status for current client's Datamodel and error queue'.

        Each status contains 3 categories/levels : "information", "warning" and "error"
        """
        if level not in ("information", "warning", "error"):
            raise AttributeError(
                f"""Specified level '{level}' is invalid. Possible values are ("information", "warning", "error"):"""
            )

        appname: str = self.__config["appname"]

        match level:
            case "error":
                levels = ["error"]
            case "warning":
                levels = [
                    "warning",
                    "error",
                ]
            case "information":
                levels = [
                    "information",
                    "warning",
                    "error",
                ]

        res = {
            appname: {
                "information": {
                    "startTime": self.__startTime.strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "paused" if self.__isPaused else "running",
                    "pausedSince": self.__isPaused.strftime("%Y-%m-%d %H:%M:%S")
                    if self.__isPaused
                    else "None",
                },
                "warning": {},
                "error": {},
            },
        }
        if not ignoreUnhandledExceptions and self.__cache.exception:
            res[appname]["error"]["unhandledException"] = self.__cache.exception

        # Datamodel
        res["datamodel"] = {
            "information": {},
            "warning": {},
            "error": {},
        }
        if self.__datamodel.unknownRemoteTypes:
            res["datamodel"]["warning"]["unknownRemoteTypes"] = sorted(
                self.__datamodel.unknownRemoteTypes
            )
        if self.__datamodel.unknownRemoteAttributes:
            res["datamodel"]["warning"]["unknownRemoteAttributes"] = {
                k: sorted(v)
                for k, v in self.__datamodel.unknownRemoteAttributes.items()
            }

        # Error queue
        res["errorQueue"] = {
            "information": {},
            "warning": {},
            "error": {},
        }

        if self.__datamodel.errorqueue is not None:
            eventNumber: int
            eventType: str
            event: Event
            errorMsg: str
            for eventNumber, eventType, event, errorMsg in self.__datamodel.errorqueue:
                if errorMsg is None:
                    # Ignore the events in queue that are not errors
                    continue

                # Always try to get object from local cache in order to use configured
                # toString template for obj's repr()
                if eventType == "remote":
                    objtype = self.__datamodel.typesmapping[event.objtype]
                else:
                    objtype = event.objtype

                _, obj = self.__getObjectFromCacheOrTrashbin(
                    self.__datamodel.localdata_complete, objtype, event.objpkey
                )
                if obj is None and eventType == "remote":
                    _, obj = self.__getObjectFromCacheOrTrashbin(
                        self.__datamodel.remotedata_complete,
                        event.objtype,
                        event.objpkey,
                    )
                if obj is None:
                    obj = f"<{event.objtype}[{event.objpkey}]>"
                else:
                    obj = repr(obj)

                res["errorQueue"]["error"][eventNumber] = {
                    "eventType": eventType,
                    "objrepr": obj,
                    "errorMsg": errorMsg,
                }
                if verbose:
                    res["errorQueue"]["error"][eventNumber] |= {
                        "objtype": event.objtype,
                        "objpkey": event.objpkey,
                        "objattrs": event.objattrs,
                    }

        # Clean empty categories
        for objname in list(res.keys()):
            for category in ("information", "warning", "error"):
                if category not in levels or (
                    not verbose and not res[objname][category]
                ):
                    del res[objname][category]

            if not verbose and not res[objname]:
                del res[objname]

        return res

    def __notifyQueueErrors(self):
        """Notify of any objects change in error queue"""
        new_error = self.__status(level="error", ignoreUnhandledExceptions=True)

        new_errors = {}
        if "errorQueue" in new_error:
            for errNumber, err in new_error["errorQueue"]["error"].items():
                new_errors[errNumber] = f"{err['objrepr']} : {err['errorMsg']}"

        new_errstr = json.dumps(
            new_errors,
            cls=JSONEncoder,
            indent=4,
        )
        old_errstr = json.dumps(self.__cache.queueErrors, cls=JSONEncoder, indent=4)

        if new_errstr != old_errstr:
            if new_errors:
                desc = "objects in error queue have changed"
            else:
                desc = "no more objects in error queue"

            logger.info(desc)
            Email.sendDiff(
                config=self.__config,
                contentdesc=desc,
                previous=old_errstr,
                current=new_errstr,
            )
            self.__cache.queueErrors = new_errors

    def __notifyDatamodelWarnings(self):
        """Notify of any data model warnings changes"""
        new_errors = self.__status(level="warning", ignoreUnhandledExceptions=True)

        if "datamodel" not in new_errors:
            new_errors = {}
        else:
            new_errors = new_errors["datamodel"]

        new_errstr = json.dumps(
            new_errors,
            cls=JSONEncoder,
            indent=4,
        )
        old_errstr = json.dumps(
            self.__cache.datamodelWarnings, cls=JSONEncoder, indent=4
        )

        if new_errors:
            logger.error("Datamodel has warnings :\n" + new_errstr)

        if new_errstr != old_errstr:
            if new_errors:
                desc = "datamodel warnings have changed"
            else:
                desc = "no more datamodel warnings"

            logger.info(desc)
            Email.sendDiff(
                config=self.__config,
                contentdesc=desc,
                previous=old_errstr,
                current=new_errstr,
            )
            self.__cache.datamodelWarnings = new_errors

    def __notifyException(self, trace: str | None):
        """Notify of any unhandled exception met/solved"""
        if trace:
            logger.critical(f"Unhandled exception : {trace}")

        if self.__cache.exception != trace:
            if trace:
                desc = "unhandled exception"
            else:
                desc = "no more unhandled exception"

            logger.info(desc)
            previous = "" if self.__cache.exception is None else self.__cache.exception
            current = "" if trace is None else trace
            Email.sendDiff(
                config=self.__config,
                contentdesc=desc,
                previous=previous,
                current=current,
            )
            self.__cache.exception = trace

    def __notifyFatalException(self, trace: str):
        """Notify of any fatal exception met before, and terminate app"""
        self.__isStopped = True

        desc = "Unhandled fatal exception, APP WILL TERMINATE IMMEDIATELY"
        NL = "\n"

        logger.critical(f"{desc} : {trace}")

        Email.send(
            config=self.__config,
            subject=f"[{self.__config['appname']}] {desc}",
            content=f"{desc} :{NL}{NL}{trace}",
        )
