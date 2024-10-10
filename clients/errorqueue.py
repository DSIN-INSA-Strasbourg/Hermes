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


from copy import deepcopy
from typing import Any, Iterable

from lib.datamodel.event import Event
from lib.datamodel.dataobject import DataObject
from lib.datamodel.datasource import Datasource
from lib.datamodel.serialization import LocalCache


class HermesInvalidErrorQueueJSONError(Exception):
    """Raised when trying to import an ErrorQueue from json with invalid JSON data"""


class ErrorQueue(LocalCache):
    """Store and manage an indexed event queue. Useful for retrying Event in error"""

    def __init__(
        self,
        typesMapping: dict[str, str],
        remotedata: Datasource | None = None,
        remotedata_complete: Datasource | None = None,
        localdata: Datasource | None = None,
        localdata_complete: Datasource | None = None,
        from_json_dict: dict[str, Any] | None = None,
        autoremediate: str = "disabled",
    ):
        """Create an empty Event queue, or load it from specified 'from_json_dict'"""

        if autoremediate in ("conservative", "maximum"):
            self._autoremediate: str | None = autoremediate
            """If set, indicate the policy to use for autoremediation"""
        else:
            self._autoremediate = None

        self._queue: dict[int, tuple[Event | None, Event, str | None]] = {}
        """The event queue, key is a unique integer, value is a tuple with the
        remote event (or None if the entry was generated by a "pure" local event,
        eg. a change in the client datamodel), the local event, and a string
        containing an optional error message"""

        self._index: dict[str, dict[Any, set[int]]] = {}
        """Index table of events.
        The keys are
            1. the local event object type (str)
            2. the event object primary key (Any)
        The value is a set containing all eventNumber in queue for the keys

        self._index[localevent.objtype][localevent.objpkey] =
        set([eventNumber1, eventNumber2, ...])
        """

        self._typesMapping = {
            "local": {v: k for k, v in typesMapping.items()},
            "remote": {k: v for k, v in typesMapping.items()},
        }
        """Mapping between local and remote objects types
            - self._typesMapping["local"]["local_type"] return the corresponding remote
              type
            - self._typesMapping["remote"]["remote_type"] return the corresponding
              local type
        """

        super().__init__(jsondataattr=["_queue"])

        self.updateDatasources(
            remotedata, remotedata_complete, localdata, localdata_complete
        )

        if from_json_dict:
            if from_json_dict.keys() != set(["_queue"]):
                raise HermesInvalidErrorQueueJSONError(f"{from_json_dict=}")
            else:
                # Prevent changes on deep references of from_json_dict
                from_json = deepcopy(from_json_dict)
                for eventNumber, (
                    remoteEventDict,
                    localEventDict,
                    errorMsg,
                ) in from_json["_queue"].items():
                    if remoteEventDict is None:
                        remoteEvent = None
                    else:
                        remoteEvent = Event(from_json_dict=remoteEventDict)
                    localEvent = Event(from_json_dict=localEventDict)
                    self._append(remoteEvent, localEvent, errorMsg, int(eventNumber))

    def updateDatasources(
        self,
        remotedata: Datasource | None = None,
        remotedata_complete: Datasource | None = None,
        localdata: Datasource | None = None,
        localdata_complete: Datasource | None = None,
    ):
        """Update the references to the datasources used, required for a case in
        autoremediation"""
        self._remotedata: Datasource | None = remotedata
        self._remotedata_complete: Datasource | None = remotedata_complete
        self._localdata: Datasource | None = localdata
        self._localdata_complete: Datasource | None = localdata_complete

    def append(
        self, remoteEvent: Event | None, localEvent: Event | None, errorMsg: str | None
    ):
        """Append specified event to queue"""
        self._append(
            remoteEvent, localEvent, errorMsg, 1 + max(self._queue.keys(), default=0)
        )

    def _append(
        self,
        remoteEvent: Event | None,
        localEvent: Event | None,
        errorMsg: str | None,
        eventNumber: int,
    ):
        """Append specified event to queue, at specified eventNumber"""
        if eventNumber in self._queue:
            raise IndexError(f"Specified {eventNumber=} already exist in queue")

        if (
            remoteEvent is not None
            and remoteEvent.objtype not in self._typesMapping["remote"]
        ):
            __hermes__.logger.info(
                "Ignore loading of remote event of unknown objtype"
                f" {remoteEvent.objtype}"
            )
            return

        if localEvent.objtype not in self._typesMapping["local"]:
            __hermes__.logger.info(
                f"Ignore loading of local event of unknown objtype {localEvent.objtype}"
            )
            return

        self._queue[eventNumber] = (remoteEvent, localEvent, errorMsg)
        self._addEventToIndex(eventNumber)

        if self._autoremediate:
            self._remediateWithPrevious(eventNumber)

    def _mergeEvents(
        self,
        prevEvent: Event | None,
        lastEvent: Event | None,
        datasource: Datasource | None,
        datasource_complete: Datasource | None,
        previousEvents: list[Event],
    ) -> tuple[bool, Event | None]:
        """Merge two events for remediation, and returns the result as a tuple with
        - wasMerged : a boolean indicating that the merge was done, meaning that the
          last event must be removed. If False, the values of removeBothEvents and
          newEvent in tuple must be ignored
        - removeBothEvents: a boolean indicating that the merge consists of both events
          removal. If True, the value of newEvent must be ignored
        - newEvent: the merged Event
        """
        # Handle None values, that may only occurs for remote events
        if lastEvent is None and prevEvent is None:
            # No data : merging is easy
            __hermes__.logger.info("Merging two None events, result is None")
            return (True, False, None)
        elif lastEvent is None:
            # Keep prevEvent values
            __hermes__.logger.info(
                f"Merging {prevEvent.objattrs=} with lastEvent=None,"
                f" result is {prevEvent=}"
            )
            return (True, False, prevEvent)
        elif prevEvent is None:
            # Keep lastEvent values
            __hermes__.logger.info(
                f"Merging prevEvent=None with {lastEvent.objattrs=},"
                f" result is {lastEvent=}"
            )
            return (True, False, lastEvent)

        if (
            (prevEvent.eventtype == "added" and lastEvent.eventtype == "added")
            or (prevEvent.eventtype == "removed" and lastEvent.eventtype == "modified")
            or (prevEvent.eventtype == "removed" and lastEvent.eventtype == "removed")
            or (prevEvent.eventtype == "modified" and lastEvent.eventtype == "added")
        ):
            errmsg = (
                f"BUG : trying to merge a {lastEvent.eventtype} event with a"
                f" previous {prevEvent.eventtype} event, this should never happen."
                f" {lastEvent=} {prevEvent=}"
            )
            __hermes__.logger.critical(errmsg)
            raise AssertionError(errmsg)

        elif prevEvent.eventtype == "added" and lastEvent.eventtype == "modified":
            # Merge the modified event data into the added event
            mergedEvent = deepcopy(prevEvent)
            objattrs = mergedEvent.objattrs
            objattrs.update(lastEvent.objattrs.get("added", dict()))
            objattrs.update(lastEvent.objattrs.get("modified", dict()))
            for key in (
                objattrs.keys() & lastEvent.objattrs.get("removed", dict()).keys()
            ):
                del objattrs[key]

            __hermes__.logger.info(
                f"Merging added {prevEvent.objattrs=} with modified"
                f" {lastEvent.objattrs=}, result is added {objattrs=}"
            )
            return (True, False, mergedEvent)
        elif prevEvent.eventtype == "added" and lastEvent.eventtype == "removed":
            if self._autoremediate == "maximum":
                # Remove the two events
                return (True, True, None)
            # Use "conservative" as fallback : don't merge the events
            return (False, False, None)
        elif prevEvent.eventtype == "removed" and lastEvent.eventtype == "added":
            if self._autoremediate == "maximum":
                # Ensure required data to process is available, otherwise fallback to
                # "conservative" policy
                if datasource is None:
                    __hermes__.logger.info(
                        f"Unable to merge removed {prevEvent=} with added "
                        f"{lastEvent.objattrs=}, as no datasource is available. "
                        "Fallback to 'conservative' mode."
                    )
                else:
                    currentObj: DataObject | None = datasource.get(
                        lastEvent.objtype, {}
                    ).get(lastEvent.objpkey, None)

                    newObj: DataObject | None = datasource_complete.get(
                        lastEvent.objtype, {}
                    ).get(lastEvent.objpkey, None)

                    if len(previousEvents) != 0:
                        # There are previous unprocesed events in error queue.
                        # Merging is possible but first we have to apply previous
                        # events changes to (a copy of) currentObj in order to
                        # determine object's state before prevEvent

                        # Imported here to avoid circular dependency
                        from .datamodel import Datamodel

                        currentObj = deepcopy(currentObj)
                        ev: Event
                        for ev in previousEvents:
                            if ev is None:
                                continue
                            elif ev.eventtype == "added":
                                currentObj = Datamodel.createDataobject(
                                    datasource.schema, ev.objtype, ev.objattrs
                                )
                            elif ev.eventtype == "modified":
                                if currentObj is None:
                                    # Should never occur
                                    errmsg = (
                                        "BUG : unexpected object status met when trying"
                                        f" to merge two events {lastEvent=}"
                                        f" {lastEvent.eventtype=} ; {prevEvent=}"
                                        f" {prevEvent.eventtype=}"
                                    )
                                    __hermes__.logger.critical(errmsg)
                                    raise AssertionError(errmsg)
                                currentObj = Datamodel.getUpdatedObject(
                                    currentObj, ev.objattrs
                                )
                            elif ev.eventtype == "removed":
                                # Should never occur
                                currentObj = None

                    if currentObj is None or newObj is None:
                        __hermes__.logger.warning(
                            f"BUG ? - Unable to merge removed {prevEvent=} with added "
                            f"{lastEvent.objattrs=}, as related object was not found "
                            f"in caches. {currentObj=} {newObj=}"
                        )
                    else:
                        # Diff the desired object with current one to generate a
                        # modified event
                        mergedEvent, _ = Event.fromDiffItem(
                            newObj.diffFrom(currentObj), "base", "modified"
                        )

                        if (
                            mergedEvent.objattrs["added"]
                            or mergedEvent.objattrs["modified"]
                            or mergedEvent.objattrs["removed"]
                        ):
                            __hermes__.logger.info(
                                f"Merging removed {prevEvent=} with added"
                                f" {lastEvent.objattrs=}, result is modified"
                                f" {mergedEvent=} {mergedEvent.objattrs=}"
                            )
                            return (True, False, mergedEvent)
                        else:
                            __hermes__.logger.info(
                                f"Merging removed {prevEvent=} with added "
                                f"{lastEvent.objattrs=}, result is an empty modified"
                                " event (without any change). Ignoring it"
                            )
                            return (True, True, mergedEvent)

            # Use "conservative" as fallback : don't merge the events
            return (False, False, None)
        elif prevEvent.eventtype == "modified" and lastEvent.eventtype == "modified":
            # Merge the two modified events
            mergedEvent = deepcopy(prevEvent)
            objattrs = mergedEvent.objattrs

            # Added
            objattrs["added"] = objattrs.get("added", dict()) | lastEvent.objattrs.get(
                "added", dict()
            )
            for key in objattrs["added"].keys() & lastEvent.objattrs.get(
                "modified", dict()
            ):
                objattrs["added"][key] = lastEvent.objattrs["modified"][key]

            # Modified
            for key in (
                lastEvent.objattrs.get("modified", dict()).keys()
                - objattrs["added"].keys()
            ):
                objattrs["modified"][key] = lastEvent.objattrs["modified"][key]

            # Removed
            for prevAction in ("added", "modified"):
                for key in lastEvent.objattrs.get(
                    "removed", dict()
                ).keys() & objattrs.get(prevAction, dict()):
                    del objattrs[prevAction][key]

            __hermes__.logger.info(
                f"Merging modified {prevEvent.objattrs=} with modified"
                f" {lastEvent.objattrs=}, result is modified {objattrs=}"
            )
            return (True, False, mergedEvent)
        elif prevEvent.eventtype == "modified" and lastEvent.eventtype == "removed":
            if self._autoremediate == "maximum":
                # Remove prevEvent
                __hermes__.logger.info(
                    f"Merging modified {prevEvent.objattrs=} with removed"
                    f" {lastEvent.objattrs=}, result is removed {lastEvent=}"
                )
                return (True, False, lastEvent)
            # Use "conservative" as fallback : don't merge the events
            return (False, False, None)
        else:
            errmsg = (
                "BUG : unexpected eventtype met when trying to merge two events "
                f"{lastEvent=} {lastEvent.eventtype=}"
                f" ; {prevEvent=} {prevEvent.eventtype=}"
            )
            __hermes__.logger.critical(errmsg)
            raise AssertionError(errmsg)

    def _remediateWithPrevious(self, eventNumber: int):
        lastEventNumber = eventNumber
        (lastRemoteEvent, lastLocalEvent, lastErrorMsg) = self._queue[lastEventNumber]

        allEventNumbers = sorted(
            self._index[lastLocalEvent.objtype][lastLocalEvent.objpkey]
        )
        allEvents = [self._queue[evNum] for evNum in allEventNumbers]
        if len(allEvents) < 2:
            # No previous event to remediate with
            return

        previousRemoteEvents = [i[0] for i in allEvents[:-2]]
        previousLocalEvents = [i[1] for i in allEvents[:-2]]

        prevEventNumber = allEventNumbers[-2]
        (prevRemoteEvent, prevLocalEvent, prevErrorMsg) = allEvents[-2]

        # Can't merge partially processed events
        if (
            prevLocalEvent.isPartiallyProcessed
            or lastLocalEvent.isPartiallyProcessed
            or (prevRemoteEvent is not None and prevRemoteEvent.isPartiallyProcessed)
            or (lastRemoteEvent is not None and lastRemoteEvent.isPartiallyProcessed)
        ):
            stepsvalues = []
            if prevRemoteEvent is not None:
                stepsvalues.append(f"{prevRemoteEvent.isPartiallyProcessed=}")
            else:
                stepsvalues.append(f"{prevRemoteEvent=}")
            stepsvalues.append(f"{prevLocalEvent.isPartiallyProcessed=}")
            if lastRemoteEvent is not None:
                stepsvalues.append(f"{lastRemoteEvent.isPartiallyProcessed=}")
            else:
                stepsvalues.append(f"{lastRemoteEvent=}")
            stepsvalues.append(f"{lastLocalEvent.isPartiallyProcessed=}")

            __hermes__.logger.info(
                "Unable to merge two events of which at least one has already been"
                f" partially processed. {' '.join(stepsvalues)}"
            )
            return

        (remotedWasMerged, remoteRemoveBothEvents, newRemoteEvent) = self._mergeEvents(
            prevRemoteEvent,
            lastRemoteEvent,
            self._remotedata,
            self._remotedata_complete,
            previousRemoteEvents,
        )
        (localWasMerged, localRemoveBothEvents, newLocalEvent) = self._mergeEvents(
            prevLocalEvent,
            lastLocalEvent,
            self._localdata,
            self._localdata_complete,
            previousLocalEvents,
        )

        if remotedWasMerged != localWasMerged:
            errmsg = (
                "BUG : inconsistency between remote and local merge results :"
                f" {remotedWasMerged=}, {localWasMerged=}. {prevEventNumber=},"
                f" {lastEventNumber=} {prevRemoteEvent.toString(set())=}"
                f" {lastRemoteEvent.toString(set())=},"
                f" {prevLocalEvent.toString(set())=}, {lastLocalEvent.toString(set())=}"
            )
            __hermes__.logger.critical(errmsg)
            raise AssertionError(errmsg)

        if not localWasMerged:
            # No merge was done
            return

        # Local processing result is the only one that really matters here
        if localRemoveBothEvents:
            self.remove(lastEventNumber)
            self.remove(prevEventNumber)
        else:
            # Last event was merged into previous, update previous and remove last from
            # queue
            self._queue[prevEventNumber] = (newRemoteEvent, newLocalEvent, prevErrorMsg)
            self.remove(lastEventNumber)

    def _addEventToIndex(self, eventNumber: int):
        """Add specified event to index"""
        if eventNumber not in self._queue:
            raise IndexError(f"Specified {eventNumber=} doesn't exist in queue")

        remoteEvent: Event | None
        localEvent: Event
        remoteEvent, localEvent, errorMsg = self._queue[eventNumber]

        objtype = localEvent.objtype

        # Create objtype sublevel if it doesn't exist yet
        if objtype not in self._index:
            self._index[objtype] = {}

        if localEvent.objpkey not in self._index[objtype]:
            # Create the set with specified eventNumber
            self._index[objtype][localEvent.objpkey] = set([eventNumber])
        else:
            # Add specified eventNumber to the set
            self._index[objtype][localEvent.objpkey].add(eventNumber)

    def updateErrorMsg(self, eventNumber: int, errorMsg: str):
        """Update errorMsg of specified eventNumber"""
        if eventNumber not in self._queue:
            raise IndexError(f"Specified {eventNumber=} doesn't exist in queue")

        remoteEvent: Event | None
        localEvent: Event
        remoteEvent, localEvent, oldErrorMsg = self._queue[eventNumber]
        self._queue[eventNumber] = (remoteEvent, localEvent, errorMsg)

    def remove(self, eventNumber: int, ignoreMissingEventNumber=False):
        """Remove event of specified eventNumber from queue"""
        if eventNumber not in self._queue:
            if ignoreMissingEventNumber:
                return
            else:
                raise IndexError(f"Specified {eventNumber=} doesn't exist in queue")

        remoteEvent: Event | None
        localEvent: Event
        remoteEvent, localEvent, errorMsg = self._queue[eventNumber]

        del self._queue[eventNumber]  # Remove data from queue

        objtype = localEvent.objtype

        # Remove from index
        self._index[objtype][localEvent.objpkey].remove(eventNumber)

        # Purge index uplevels when empty
        if not self._index[objtype][localEvent.objpkey]:
            del self._index[objtype][localEvent.objpkey]

            if not self._index[objtype]:
                del self._index[objtype]

    def __iter__(self) -> Iterable:
        """Returns an iterator of current instance events to process
        It will ignore events about an object that still have older event in queue

        Each entry will contains 4 values:
            1. eventNumber: int
            2. remoteEvent: remote event, or None if the entry was generated by a
               "pure" local event (eg. a change in the client datamodel)
            3. localEvent: local event
            4. errorMsg: str or None
        """
        eventNumber: int
        remoteEvent: Event | None
        localEvent: Event
        errorMsg: str | None

        for eventNumber in list(self._queue.keys()):
            # Event may have been removed during iteration
            # e.g. a call to purgeAllEventsOfDataObject() may remove several events
            if eventNumber not in self._queue:
                continue

            remoteEvent, localEvent, errorMsg = self._queue[eventNumber]
            objindex = self._index[localEvent.objtype][localEvent.objpkey]

            # If current event isn't the first of its object index, ignore it
            # because the previous must be processed before
            if eventNumber != min(objindex):
                continue

            yield (eventNumber, remoteEvent, localEvent, errorMsg)

    def allEvents(self) -> Iterable:
        """Returns an iterator of all current instance events

        Each entry will contains 4 values:
            1. eventNumber: int
            2. remoteEvent: remote event, or None if the entry was generated by a
               "pure" local event (eg. a change in the client datamodel)
            3. localEvent: local event
            4. errorMsg: str or None
        """
        eventNumber: int
        remoteEvent: Event | None
        localEvent: Event
        errorMsg: str | None

        for eventNumber in list(self._queue.keys()):
            # Event may have been removed during iteration
            # e.g. a call to purgeAllEventsOfDataObject() may remove several events
            if eventNumber not in self._queue:
                continue

            remoteEvent, localEvent, errorMsg = self._queue[eventNumber]
            yield (eventNumber, remoteEvent, localEvent, errorMsg)

    def __len__(self) -> int:
        """Returns the number of Event in queue"""
        return len(self._queue)

    def _getLocalObjtype(self, objtype: str, isLocalObjtype: bool) -> str | None:
        """Returns the local objtype, or None if it doesn't exist"""
        if isLocalObjtype:
            if objtype in self._typesMapping["local"]:
                return objtype
            else:
                return None
        else:
            return self._typesMapping["remote"].get(objtype)

    def containsObject(self, objtype: str, objpkey: Any, isLocalObjtype: bool) -> bool:
        """Indicate if object of specified objpkey of specified objtype exists in
        current instance"""
        l_objtype = self._getLocalObjtype(objtype, isLocalObjtype)
        if l_objtype is None:
            return False
        return l_objtype in self._index and objpkey in self._index[l_objtype]

    def containsObjectByEvent(self, event: Event, isLocalEvent: bool) -> bool:
        """Indicate if object of specified event exists in current instance"""
        return self.containsObject(event.objtype, event.objpkey, isLocalEvent)

    def purgeAllEvents(self, objtype: str, objpkey: Any, isLocalObjtype: bool):
        """Delete all events of specified objpkey of specified objtype from current
        instance"""
        if not self.containsObject(objtype, objpkey, isLocalObjtype):
            return

        l_objtype = self._getLocalObjtype(objtype, isLocalObjtype)
        if l_objtype is None:
            return

        eventNumbers = self._index[l_objtype][objpkey]

        # Loop over a copy as content may be removed during iteration
        for eventNumber in eventNumbers.copy():
            self.remove(eventNumber)

    def purgeAllEventsOfDataObject(self, obj: DataObject, isLocalObjtype: bool):
        """Delete all events of specified objpkey of specified objtype from current
        instance"""
        self.purgeAllEvents(obj.getType(), obj.getPKey(), isLocalObjtype)

    def updatePrimaryKeys(
        self,
        new_remote_pkeys: dict[str, str],
        remote_data: Datasource,
        remote_data_complete: Datasource,
        new_local_pkeys: dict[str, str],
        local_data: Datasource,
        local_data_complete: Datasource,
    ):
        """Will update primary keys. new_remote_pkeys is a dict with remote objtype as
        key, and the new remote primary key attribute name as value. new_local_pkeys is
        a dict with local objtype as key, and the new local primary key attribute name
        as value.
        The specified datasources must not have their primary keys updated yet, to
        allow conversion.

        The ErrorQueue MUST immediately be saved and re-instantiated from cache by
        caller to reflect data changes.
        """
        newqueue = {}
        for eventNumber, (remoteEvent, localEvent, errorMsg) in self._queue.items():
            # Remote event, if any
            if remoteEvent is None:
                newRemoteEvent = None
            else:
                if remoteEvent.objtype not in new_remote_pkeys.keys():
                    # Objtype of remote event has no pkey update
                    newRemoteEvent = remoteEvent
                else:
                    oldobj = remote_data[remoteEvent.objtype].get(remoteEvent.objpkey)
                    if oldobj is None:
                        oldobj = remote_data_complete[remoteEvent.objtype][
                            remoteEvent.objpkey
                        ]
                    if type(new_remote_pkeys[remoteEvent.objtype]) is tuple:
                        # New pkey is a tuple, loop over each attr
                        newpkey = []
                        for pkattr in new_remote_pkeys[remoteEvent.objtype]:
                            newpkey.append(getattr(oldobj, pkattr))
                        newpkey = tuple(newpkey)
                    else:
                        newpkey = getattr(oldobj, new_remote_pkeys[remoteEvent.objtype])

                    # Save modified remote event
                    newRemoteEvent = deepcopy(remoteEvent)
                    newRemoteEvent.objpkey = newpkey

            # Local event
            if localEvent.objtype not in new_local_pkeys.keys():
                # Objtype of local event has no pkey update
                newLocalEvent = localEvent
            else:
                oldobj = local_data[localEvent.objtype].get(localEvent.objpkey)
                if oldobj is None:
                    oldobj = local_data_complete[localEvent.objtype][localEvent.objpkey]
                if type(new_local_pkeys[localEvent.objtype]) is tuple:
                    # New pkey is a tuple, loop over each attr
                    newpkey = []
                    for pkattr in new_local_pkeys[localEvent.objtype]:
                        newpkey.append(getattr(oldobj, pkattr))
                    newpkey = tuple(newpkey)
                else:
                    newpkey = getattr(oldobj, new_local_pkeys[localEvent.objtype])

                # Save modified local event
                newLocalEvent = deepcopy(localEvent)
                newLocalEvent.objpkey = newpkey

                # Update reserved _pkey* attributes in added events
                if newLocalEvent.eventtype == "added":
                    # Remove previous pkey attributes
                    for attr in list(newLocalEvent.objattrs.keys()):
                        if attr.startswith("_pkey_"):
                            del newLocalEvent.objattrs[attr]
                    # Add new pkey attributes
                    if type(new_local_pkeys[localEvent.objtype]) is tuple:
                        for i in range(len(newpkey)):
                            newLocalEvent.objattrs[
                                new_local_pkeys[localEvent.objtype][i]
                            ] = newpkey[i]
                    else:
                        newLocalEvent.objattrs[new_local_pkeys[localEvent.objtype]] = (
                            newpkey
                        )

            # Save modified entry
            newqueue[eventNumber] = (newRemoteEvent, newLocalEvent, errorMsg)

        self._queue = newqueue
