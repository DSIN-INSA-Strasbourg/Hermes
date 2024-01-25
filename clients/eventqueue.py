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


class HermesInvalidEventQueueJSONError(Exception):
    """Raised when trying to import an EventQueue from json with invalid JSON data"""


class EventQueue(LocalCache):
    """Store and manage an indexed event queue. Useful for retrying Event in error"""

    def __init__(
        self,
        typesMapping: dict[str, str],
        from_json_dict: dict[str, Any] | None = None,
        autoremediate: bool = False,
    ):
        """Create an empty Event queue, or load it from specified 'from_json_dict'"""

        self._autoremediate: bool = autoremediate
        """Indicate if queue must autoremediate by merging all add/modify events"""

        self._queue: dict[int, tuple[str, Event, str]] = {}
        """The event queue, key is a unique integer, value is a tuple with the event
        type, the event, and a string containing an optional error message"""

        self._index: dict[str, dict[str, dict[Any, set[int]]]] = {}
        """Index table of events.
        The keys are 
            1. the event type (str)
            2. the event object type (str)
            3. the event object primary key (Any)
        The value is a set containing all eventNumber in queue for the keys
        
        self._index[eventType][event.objtype][event.objpkey] = set([eventNumber1, eventNumber2, ...])
        """

        self._typesMapping = {
            "local": {v: k for k, v in typesMapping.items()},
            "remote": {k: v for k, v in typesMapping.items()},
        }
        """Mapping between local and remote objects types
            - self._typesMapping["local"]["local_type"] return the corresponding remote type
            - self._typesMapping["remote"]["remote_type"] return the corresponding local type
        """

        super().__init__(jsondataattr=["_queue"])

        if from_json_dict:
            if from_json_dict.keys() != set(["_queue"]):
                raise HermesInvalidEventQueueJSONError(f"{from_json_dict=}")
            else:
                # Prevent changes on deep references of from_json_dict
                from_json = deepcopy(from_json_dict)
                for eventNumber, (eventType, eventDict, errorMsg) in from_json[
                    "_queue"
                ].items():
                    event = Event(from_json_dict=eventDict)
                    self._append(eventType, event, errorMsg, int(eventNumber))

    def append(self, eventType: str, event: Event, errorMsg: str):
        """Append specified event of specified eventType to queue"""
        self._append(eventType, event, errorMsg, 1 + max(self._queue.keys(), default=0))

    def _append(self, eventType: str, event: Event, errorMsg: str, eventNumber: int):
        """Append specified event of specified eventType to queue, at specified eventNumber"""
        if eventNumber in self._queue:
            raise IndexError(f"Specified {eventNumber=} already exist in queue")

        if event.objtype not in self._typesMapping[eventType]:
            __hermes__.logger.info(
                f"Ignore loading of {eventType} event of unknown objtype {event.objtype}"
            )
            return

        self._queue[eventNumber] = (eventType, event, errorMsg)
        self._addEventToIndex(eventNumber)

        if self._autoremediate:
            self._remediateWithPrevious(eventNumber)

    def _remediateWithPrevious(self, eventNumber: int):
        lastEventNumber = eventNumber
        (lastEventType, lastEvent, lastErrorMsg) = self._queue[lastEventNumber]
        if lastEvent.eventtype != "modified":
            # Won't be able to remediate added or removed event with previous
            return

        allEventNumbers = sorted(
            self._index[lastEventType][lastEvent.objtype][lastEvent.objpkey]
        )
        allEvents = [self._queue[evNum] for evNum in allEventNumbers]
        if len(allEvents) < 2:
            # No previous event to remediate with
            return

        (prevEventType, prevEvent, prevErrorMsg) = allEvents[-2]

        if prevEventType != lastEventType:
            # Won't remediate across different eventTypes
            return

        if prevEvent.eventtype == "added":
            # Merge
            objattrs = prevEvent.objattrs.copy()
            objattrs.update(lastEvent.objattrs.get("added", dict()))
            objattrs.update(lastEvent.objattrs.get("modified", dict()))
            for key in (
                objattrs.keys() & lastEvent.objattrs.get("removed", dict()).keys()
            ):
                del objattrs[key]

            __hermes__.logger.info(
                f"Merging {prevEvent.objattrs=} with {lastEvent.objattrs=}, result is {objattrs=}"
            )
            prevEvent.objattrs = objattrs
        elif prevEvent.eventtype == "modified":
            # Merge
            objattrs = prevEvent.objattrs.copy()

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
                f"Merging {prevEvent.objattrs=} with {lastEvent.objattrs=}, result is {objattrs=}"
            )
            prevEvent.objattrs = objattrs
        else:
            # Won't be able to merge with previous eventtype
            return

        # Last event was merge into previous, remove it from queue
        self.remove(lastEventNumber)

    def _addEventToIndex(self, eventNumber: int):
        """Add specified event of specified eventType to index"""
        if eventNumber not in self._queue:
            raise IndexError(f"Specified {eventNumber=} doesn't exist in queue")

        eventType: str
        event: Event
        eventType, event, errorMsg = self._queue[eventNumber]

        for evType in ("local", "remote"):
            if evType == eventType:
                objtype = event.objtype
            else:
                objtype = self._typesMapping[eventType][event.objtype]

            # Create index sublevels if they doesn't exist
            if evType not in self._index:
                self._index[evType] = {}

            if objtype not in self._index[evType]:
                self._index[evType][objtype] = {}

            if event.objpkey not in self._index[evType][objtype]:
                # Create the set with specified eventNumber
                self._index[evType][objtype][event.objpkey] = set([eventNumber])
            else:
                # Add specified eventNumber to the set
                self._index[evType][objtype][event.objpkey].add(eventNumber)

    def updateErrorMsg(self, eventNumber: int, errorMsg: str):
        """Update errorMsg of specified eventNumber"""
        if eventNumber not in self._queue:
            raise IndexError(f"Specified {eventNumber=} doesn't exist in queue")

        eventType: str
        event: Event
        eventType, event, oldErrorMsg = self._queue[eventNumber]
        self._queue[eventNumber] = (eventType, event, errorMsg)

    def remove(self, eventNumber: int, ignoreMissingEventNumber=False):
        """Remove event of specified eventNumber from queue"""
        if eventNumber not in self._queue:
            if ignoreMissingEventNumber:
                return
            else:
                raise IndexError(f"Specified {eventNumber=} doesn't exist in queue")

        eventType: str
        event: Event
        eventType, event, errorMsg = self._queue[eventNumber]

        del self._queue[eventNumber]  # Remove data from queue

        for evType in ("local", "remote"):
            if evType == eventType:
                objtype = event.objtype
            else:
                objtype = self._typesMapping[eventType][event.objtype]

            # Remove from index
            self._index[evType][objtype][event.objpkey].remove(eventNumber)

            # Purge index uplevels when empty
            if not self._index[evType][objtype][event.objpkey]:
                del self._index[evType][objtype][event.objpkey]

                if not self._index[evType][objtype]:
                    del self._index[evType][objtype]

                    if not self._index[evType]:
                        del self._index[evType]

    def __iter__(self) -> Iterable:
        """Returns an iterator of current instance events to process
        It will ignore events about an object that still have older event in queue

        Each entry will contains 4 values:
            1. eventNumber: int
            2. eventType: str
            3. event: Event
            4. errorMsg: str
        """
        eventNumber: int
        eventType: str
        event: Event
        errorMsg: str

        for eventNumber in list(self._queue.keys()):
            # Event may have been removed during iteration
            # e.g. a call to purgeAllEventsOfDataObject() may remove several events
            if eventNumber not in self._queue:
                continue

            eventType, event, errorMsg = self._queue[eventNumber]
            objindex = self._index[eventType][event.objtype][event.objpkey]

            # If current event isn't the first of its object index, ignore it
            # because the previous must be processed before
            if eventNumber != min(objindex):
                continue

            yield (eventNumber, eventType, event, errorMsg)

    def allEvents(self) -> Iterable:
        """Returns an iterator of all current instance events

        Each entry will contains 4 values:
            1. eventNumber: int
            2. eventType: str
            3. event: Event
            4. errorMsg: str
        """
        eventNumber: int
        eventType: str
        event: Event
        errorMsg: str

        for eventNumber in list(self._queue.keys()):
            # Event may have been removed during iteration
            # e.g. a call to purgeAllEventsOfDataObject() may remove several events
            if eventNumber not in self._queue:
                continue

            eventType, event, errorMsg = self._queue[eventNumber]
            yield (eventNumber, eventType, event, errorMsg)

    def __len__(self) -> int:
        """Returns the number of Event in queue"""
        return len(self._queue)

    def containsObject(self, eventType: str, objtype: str, objpkey: Any) -> bool:
        """Indicate if object of specified objpkey of specified objtype of specified
        eventType exists in current instance"""
        if (
            eventType not in self._index
            or objtype not in self._index[eventType]
            or objpkey not in self._index[eventType][objtype]
        ):
            return False
        else:
            return True

    def containsObjectByEvent(self, eventType: str, event: Event) -> bool:
        """Indicate if object of specified event of specified eventType exists in current instance"""
        return self.containsObject(eventType, event.objtype, event.objpkey)

    def containsObjectByDataobject(self, eventType: str, obj: DataObject) -> bool:
        """Indicate if specified obj of specified eventType exists in current instance"""
        return self.containsObject(eventType, obj.getType(), obj.getPKey())

    def purgeAllEvents(self, eventType: str, objtype: str, objpkey: Any):
        """Delete all events of specified objpkey of specified objtype of specified
        eventType from current instance"""
        if not self.containsObject(eventType, objtype, objpkey):
            return

        eventNumbers = self._index[eventType][objtype][objpkey]

        # Loop over a copy as content may be removed during iteration
        for eventNumber in eventNumbers.copy():
            self.remove(eventNumber)

    def purgeAllEventsOfDataObject(self, eventType: str, obj: DataObject):
        """Delete all events of specified objpkey of specified objtype of specified
        eventType from current instance"""
        self.purgeAllEvents(eventType, obj.getType(), obj.getPKey())

    def updatePrimaryKeys(
        self,
        new_remote_pkeys: dict[str, str],
        remote_data: Datasource,
        new_local_pkeys: dict[str, str],
        local_data: Datasource,
    ):
        """Will update primary keys. new_remote_pkeys is a dict with remote objtype as key,
        and the new remote primary key attribute name as value. new_local_pkeys is a dict
        with local objtype as key, and the new local primary key attribute name as value.
        The specified datasources must not have their primary keys updated yet, to allow conversion.

        The EventQueue MUST immediately be saved and re-instantiated from cache by caller to reflect
        data changes Dataschema changes.
        """
        newqueue = {}
        for eventNumber, (eventType, event, errorMsg) in self._queue.items():
            if eventType == "remote":
                new_pkeys = new_remote_pkeys
                ds = remote_data
            else:
                new_pkeys = new_local_pkeys
                ds = local_data

            newevent = deepcopy(event)
            oldobj = ds[event.objtype][event.objpkey]
            newevent.objpkey = getattr(oldobj, new_pkeys[event.objtype])
            newqueue[eventNumber] = (eventType, newevent, errorMsg)

        self._queue = newqueue
