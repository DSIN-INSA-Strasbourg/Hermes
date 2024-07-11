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

from copy import deepcopy
from datetime import datetime
from jinja2 import StrictUndefined
from jinja2.environment import Template
from typing import Any

from clients.errorqueue import ErrorQueue
from lib.datamodel.dataobject import DataObject
from lib.datamodel.dataobjectlist import DataObjectList
from lib.datamodel.dataschema import Dataschema
from lib.datamodel.datasource import Datasource
from lib.datamodel.diffobject import DiffObject
from lib.datamodel.event import Event
from lib.datamodel.serialization import LocalCache
from lib.datamodel.jinja import (
    HermesNativeEnvironment,
    Jinja,
    HermesUnknownVarsInJinjaTemplateError,
)


class InvalidDataError(Exception):
    """Raised when a case that should never happen occurs (a critical bug)"""


class Datamodel:
    """Load and build the Datamodel from config, and validates it according to remote
    Dataschema.

    In charge of:
        - handling updates of Datamodel (hermes-client.datamodel changes in config file)
        - handling updates of remote Dataschema (hermes-server.datamodel in server
          config file)
        - converting a remote Event to a local one
        - handling remote and local data caches (remotedata and localdata attributes,
          each of Datasource type)
    """

    def __init__(
        self,
        config: HermesConfig,
    ):
        """Build the datamodel from config"""

        self.unknownRemoteTypes: set[str] = set()
        """List remote types set in client Datamodel, but missing in remote
        Dataschema"""
        self.unknownRemoteAttributes: dict[str, set[str]] = set()
        """List remote attributes set in client Datamodel, but missing in remote
        Dataschema. The dict key contains the remote type, the set contains the missing
        attributes"""

        self._config: HermesConfig = config

        self._rawdatamodel: dict[str, Any] = self._config["hermes-client"]["datamodel"]
        """Local datamodel dictionary, as found in config"""

        self._datamodel: dict[str, Any]
        """Local datamodel dictionary, with compiled Jinja templates"""

        self._jinjaenv: HermesNativeEnvironment = HermesNativeEnvironment(
            undefined=StrictUndefined
        )
        if "hermes" in self._config:
            self._jinjaenv.filters |= self._config["hermes"]["plugins"]["attributes"][
                "_jinjafilters"
            ]

        self.remote_schema: Dataschema = Dataschema.loadcachefile("_dataschema")
        """Remote schema"""
        self.local_schema: Dataschema | None = None
        """Local schema"""

        self.remotedata: Datasource | None = None
        """Datasource of remote objects"""
        self.localdata: Datasource | None = None
        """Datasource of local objects"""

        self.remotedata_complete: Datasource | None = None
        """Datasource of remote objects as it should be without error"""
        self.localdata_complete: Datasource | None = None
        """Datasource of local objects as it should be without error"""

        self.errorqueue: ErrorQueue | None = None
        """Queue of Events in error"""

        self.typesmapping: dict[str, str]
        """Mapping of datamodel types: hermes-server type as key, hermes-client type as
        value"""
        self._remote2local: dict[str, dict[str, list[str]]]
        """Mapping with remote type name as key, and dict containing remote attrname as
        key and local attrname as value. Example:
        {
            remote_type_name: {
                remote_attrname1: client_attrname1,
                ...
            },
            ...
        }
        """

        if self.hasRemoteSchema():
            self._mergeWithSchema(self.remote_schema)

    def hasRemoteSchema(self) -> bool:
        """Returns true if remote schema has data"""
        return len(self.remote_schema.schema) != 0

    def diffFrom(self, other: "Datamodel") -> DiffObject:
        """Return DiffObject with differences (attributes names) of current instance
        from another"""
        diff = DiffObject()

        s = self._rawdatamodel.keys()
        o = other._rawdatamodel.keys()
        commonattrs = s & o

        diff.appendRemoved(o - s)
        diff.appendAdded(s - o)

        for k, v in self._rawdatamodel.items():
            if k in commonattrs and DataObject.isDifferent(v, other._rawdatamodel[k]):
                diff.appendModified(k)

        return diff

    def loadLocalData(self):
        """Load or reload localdata and localdata_complete from cache"""
        self.localdata = Datasource(
            schema=self.local_schema, enableTrashbin=True, cacheFilePrefix="__"
        )
        self.localdata.loadFromCache()
        self.localdata_complete = Datasource(
            schema=self.local_schema,
            enableTrashbin=True,
            cacheFilePrefix="__",
            cacheFileSuffix="_complete__",
        )
        self.localdata_complete.loadFromCache()

    def saveLocalData(self):
        """Save localdata and localdata_complete when they're set"""
        if self.localdata is not None:
            self.localdata.save()
        if self.localdata_complete is not None:
            self.localdata_complete.save()

    def loadRemoteData(self):
        """Load or reload remotedata and remotedata_complete from cache"""
        self.remotedata = Datasource(schema=self.remote_schema, enableTrashbin=True)
        self.remotedata.loadFromCache()
        self.remotedata_complete = Datasource(
            schema=self.remote_schema,
            enableTrashbin=True,
            cacheFileSuffix="_complete__",
        )
        self.remotedata_complete.loadFromCache()
        if self.errorqueue is not None:
            self.errorqueue.updateDatasources(
                self.remotedata,
                self.remotedata_complete,
                self.localdata,
                self.localdata_complete,
            )

    def saveRemoteData(self):
        """Save remotedata and remotedata_complete when they're set"""
        if self.remotedata is not None:
            self.remotedata.save()
        if self.remotedata_complete is not None:
            self.remotedata_complete.save()

    def loadLocalAndRemoteData(self):
        """Load or reload localdata, localdata_complete, remotedata and
        remotedata_complete from cache"""
        self.loadLocalData()
        self.loadRemoteData()

    def saveLocalAndRemoteData(self):
        """Save localdata, localdata_complete, remotedata and remotedata_complete
        from cache when they're set"""
        self.saveLocalData()
        self.saveRemoteData()

    def loadErrorQueue(self):
        """Load or reload error queue from cache"""
        if self.hasRemoteSchema():
            self.errorqueue = ErrorQueue.loadcachefile(
                "_errorqueue",
                typesMapping=self.typesmapping,
                remotedata_complete=self.remotedata_complete,
                remotedata=self.remotedata,
                localdata=self.localdata,
                localdata_complete=self.localdata_complete,
                autoremediate=self._config["hermes-client"]["autoremediation"],
            )
        else:
            self.errorqueue = None

    def saveErrorQueue(self):
        """Save error queue to cache"""
        if self.errorqueue is not None:
            self.errorqueue.savecachefile()

    def _mergeWithSchema(self, remote_schema: Dataschema):
        """Build or update the datamodel according to specified remote_schema"""
        prev_remote_schema = self.remote_schema
        self.remote_schema = remote_schema
        self._remote2local = {}

        prev_remote_pkeys, new_remote_pkeys = self._checkForSchemaChanges(
            prev_remote_schema, self.remote_schema
        )

        self._fillDatamodelDict()  # Filled upon config only
        self._fillConversionVars()  # Filled upon config only

        self.local_schema = self._setupLocalSchema()

        # Update pkeys when necessary
        if new_remote_pkeys:
            __hermes__.logger.info("Updating local cache primary keys")

            self.saveLocalAndRemoteData()
            self.saveErrorQueue()

            new_local_pkeys: dict[str, str | tuple[str]] = {}
            l_pkeys_to_add: dict[str, set[str]] = {}
            l_pkeys_to_remove: dict[str, set[str]] = {}
            local_types: dict[str, set[type[DataObject]]] = {}
            for r_objtype in new_remote_pkeys.keys():
                if r_objtype not in self.typesmapping:
                    continue

                # Determine local objtype and its new primary key
                l_objtype = self.typesmapping[r_objtype]
                new_local_pkeys[l_objtype] = self.local_schema.schema[l_objtype][
                    "PRIMARYKEY_ATTRIBUTE"
                ]

                # Compute local pkeys to add and to remove for each local data type
                r_prev_pkeys = prev_remote_pkeys[r_objtype]
                r_new_pkeys = new_remote_pkeys[r_objtype]
                if type(r_prev_pkeys) is str:
                    r_prev_pkeys = (r_prev_pkeys,)
                if type(r_new_pkeys) is str:
                    r_new_pkeys = (r_new_pkeys,)
                l_prev_pkeys = set([f"_pkey_{pkey}" for pkey in r_prev_pkeys])
                l_new_pkeys = set([f"_pkey_{pkey}" for pkey in r_new_pkeys])
                l_pkeys_to_add[l_objtype] = l_new_pkeys - l_prev_pkeys
                l_pkeys_to_remove[l_objtype] = l_prev_pkeys - l_new_pkeys

                local_types[l_objtype] = set()

                # Add new pkey attributes and values to localdata objects
                for src in (self.localdata, self.localdata_complete):
                    for type_prefix in ("", "trashbin_"):
                        obj: DataObject
                        for obj in src[f"{type_prefix}{l_objtype}"]:
                            if type(obj) not in local_types[l_objtype]:
                                local_types[l_objtype].add(type(obj))
                                type(obj).HERMES_ATTRIBUTES |= l_pkeys_to_add[l_objtype]
                            # Get corresponding remote object from cache
                            (_, r_obj) = Datamodel.getObjectFromCacheOrTrashbin(
                                self.remotedata_complete, r_objtype, obj.getPKey()
                            )
                            if r_obj is None:
                                # Should never happen : if so, it's a bug
                                msg = (
                                    f"BUG ! No matching of local object {repr(obj)}"
                                    " found in remotedata_complete cache. The client is"
                                    " probably broken"
                                )
                                __hermes__.logger.critical(msg)
                                raise InvalidDataError(msg)

                            for pkey in r_new_pkeys:
                                try:
                                    # Get pkey value from remote object
                                    value = getattr(r_obj, pkey)
                                except AttributeError:
                                    # Should never happen : if so, it's a bug
                                    msg = (
                                        "BUG ! No value exist in remote cache for"
                                        f" attribute '{pkey}' of object {r_obj}. The"
                                        " client is probably broken"
                                    )
                                    __hermes__.logger.critical(msg)
                                    raise InvalidDataError(msg)
                                # Store pkey value to local object
                                setattr(obj, f"_pkey_{pkey}", value)

                # Update PRIMARYKEY_ATTRIBUTE of each local type
                for l_objtype, l_types in local_types.items():
                    for l_type in l_types:
                        l_type.PRIMARYKEY_ATTRIBUTE = new_local_pkeys[l_objtype]

                # Remove previous pkey attributes that are not used anymore from
                # localdata objects
                for src in (self.localdata, self.localdata_complete):
                    for type_prefix in ("", "trashbin_"):
                        obj: DataObject
                        for obj in src[f"{type_prefix}{l_objtype}"]:
                            for pkey in l_pkeys_to_remove[l_objtype]:
                                try:
                                    delattr(obj, pkey)
                                except AttributeError:
                                    pass

                # Remove previous pkey attributes that are not used anymore from
                # HERMES_ATTRIBUTES of each local type
                for l_objtype, l_types in local_types.items():
                    for l_type in l_types:
                        l_type.HERMES_ATTRIBUTES -= l_pkeys_to_remove[l_objtype]

            self.saveLocalData()

            __hermes__.logger.info("Updating changed primary keys in error queue")
            self.errorqueue.updatePrimaryKeys(
                new_remote_pkeys,
                self.remotedata_complete,
                new_local_pkeys,
                self.localdata_complete,
            )

            # Save and reload error queue
            self.saveErrorQueue()
            self.loadErrorQueue()

        # Load local and remote Datasource caches
        self.loadLocalAndRemoteData()

    def updateSchema(self, remote_schema: Dataschema):
        """Build or update the datamodel according to specified remote_schema.
        Data caches (locadata, locadata_complete, remotedata and remotedata_complete)
        will be saved and reloaded to be updated according to new schema.
        Remote and local schemas caches will be saved.
        """
        # Save current data before updating schema and reloading them
        self.saveLocalAndRemoteData()
        self._mergeWithSchema(remote_schema)
        self.remote_schema.savecachefile()

    def forcePurgeOfTrashedObjectsWithoutNewPkeys(
        self, oldschema: Dataschema | None, newschema: Dataschema
    ) -> dict[str, set[Any]]:
        """On schema update, when primary key have changed, the trashed objects may not
        contain the value of the new primary key attribute(s). This function will
        change the trashbin timestamp of all those objects to force their removal.
        Returns True if a trashbin purge is required, False otherwise
        """
        isTrashbinPurgeRequired: bool = False
        if oldschema is None:
            return False

        diff = newschema.diffFrom(oldschema)

        if not (diff and diff.modified):
            return False

        old: dict[str, Any] = oldschema.schema
        new: dict[str, Any] = newschema.schema
        for objtype in diff.modified:
            if objtype not in self.typesmapping:
                continue
            npkey = new[objtype]["PRIMARYKEY_ATTRIBUTE"]
            opkey = old[objtype]["PRIMARYKEY_ATTRIBUTE"]
            if not DataObject.isDifferent(npkey, opkey):
                continue
            npkeys = (npkey,) if type(npkey) is str else npkey
            obj: DataObject
            for obj in self.remotedata[f"trashbin_{objtype}"]:
                for pkey in npkeys:
                    if not hasattr(obj, pkey):
                        __hermes__.logger.warning(
                            f"Object {repr(obj)} of type '{objtype}' in trashbin will"
                            " be purged, as it doesn't have the new primary key value"
                        )
                        isTrashbinPurgeRequired = True
                        obj._trashbin_timestamp = datetime(year=1, month=1, day=1)
                        break
        return isTrashbinPurgeRequired

    def _checkForSchemaChanges(
        self, oldschema: Dataschema | None, newschema: Dataschema
    ) -> tuple[dict[str, str | tuple[str]], dict[str, str | tuple[str]]]:
        """Returns a tuple of two dicts :
        - first dict with remote types as key, and previous remote primary key
          attribute as value
        - second dict with remote types as key, and new remote primary key attribute as
          value
        """
        previouspkeys = {}
        newpkeys = {}
        if oldschema is None:
            return (previouspkeys, newpkeys)

        diff = newschema.diffFrom(oldschema)

        if diff:
            old: dict[str, Any] = oldschema.schema
            new: dict[str, Any] = newschema.schema

            if diff.added:
                __hermes__.logger.info(f"Types added in Dataschema: {diff.added}")

            if diff.removed:
                __hermes__.logger.info(
                    f"Types removed from Dataschema: {diff.removed},"
                    " purging cache files"
                )
                self.purgeOldCacheFiles(diff.removed)

            if diff.modified:
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
                            f"Removed attributes from dataschema type '{objtype}':"
                            f" {removed}"
                        )

                    # SECRETS_ATTRIBUTES
                    added = n["SECRETS_ATTRIBUTES"] - o["SECRETS_ATTRIBUTES"]
                    removed = o["SECRETS_ATTRIBUTES"] - n["SECRETS_ATTRIBUTES"]
                    if added:
                        __hermes__.logger.info(
                            f"New secrets attributes in dataschema type '{objtype}':"
                            f" {added}"
                        )
                        # We need to purge attribute from cache: as cache is loaded with
                        # attribute set up as SECRET, we just have to save the cache
                        # (attr won't be saved anymore, as it's SECRET) and reload
                        # cache to "forget" values loaded from previous cache
                        self.saveRemoteData()
                        self.loadRemoteData()
                    if removed:
                        __hermes__.logger.info(
                            "Removed secrets attributes from dataschema type"
                            f" '{objtype}': {removed}"
                        )

                    # PRIMARYKEY_ATTRIBUTE
                    npkey = n["PRIMARYKEY_ATTRIBUTE"]
                    opkey = o["PRIMARYKEY_ATTRIBUTE"]
                    if DataObject.isDifferent(npkey, opkey):
                        previouspkeys[objtype] = opkey
                        newpkeys[objtype] = npkey
                        __hermes__.logger.info(
                            "New primary key attribute in dataschema type"
                            f" '{objtype}': {npkey}"
                        )

        return (previouspkeys, newpkeys)

    def convertEventToLocal(
        self,
        event: Event,
        new_obj: DataObject | None = None,
        allowEmptyEvent: bool = False,
    ) -> Event | None:
        """Convert specified remote event to local one.
        If new_obj is provided, it must contains all the new remote object values,
        and will only be used to render Jinja Templates.
        Returns None if local event doesn't contains any attribute and allowEmptyEvent
        is False"""
        if event.objtype not in self.typesmapping:
            __hermes__.logger.debug(
                f"Unknown {event.objtype=}. Known are {self.typesmapping}"
            )
            return None  # Unknown type

        objtype = self.typesmapping[event.objtype]

        # Handle that event.objattrs is 1 depth deeper for "modified" events
        if event.eventtype == "modified":
            sources = ("added", "modified", "removed")
        else:
            sources = (None,)

        hasContent: bool = False
        objattrs = {}
        for source in sources:
            attrs = {}
            if source is None:
                src = event.objattrs
            else:
                src = event.objattrs[source]

            # Hack to handle Jinja templates containing only static data
            if None in self._remote2local[event.objtype] and event.eventtype == "added":
                loopsrc = src.copy()
                loopsrc[None] = None
            else:
                loopsrc = src

            for k, v in loopsrc.items():
                if k in self._remote2local[event.objtype]:
                    for dest in self._remote2local[event.objtype][k]:
                        remoteattr = self._datamodel[objtype]["attrsmapping"][dest]
                        if isinstance(
                            remoteattr, Template
                        ):  # May be a compiled Jinja Template
                            if new_obj is None:
                                val = remoteattr.render(src)
                            else:
                                # We must provide all new object vars values to
                                # render a Jinja Template computed from several vars,
                                # in case of "modified" event changing the value of
                                # only one var value used by the template.
                                # The event objattrs won't be enough in this specific
                                # case.
                                val = remoteattr.render(new_obj.toNative())

                            if type(val) is list:
                                val = [v for v in val if v is not None]

                            if source == "removed" or (val is not None and val != []):
                                attrs[dest] = val
                        else:
                            attrs[dest] = v
            if attrs:
                hasContent = True

            if source is None:
                objattrs = attrs
            else:
                objattrs[source] = attrs

        res = None
        if hasContent or allowEmptyEvent or event.eventtype == "removed":
            res = Event(
                evcategory=event.evcategory,
                eventtype=event.eventtype,
                objattrs=objattrs,
            )
            res.objtype = objtype
            res.objpkey = event.objpkey
            res.objrepr = str(res.objpkey)
            res.timestamp = event.timestamp
            res.step = event.step
            res.isPartiallyProcessed = event.isPartiallyProcessed
        return res

    def createLocalDataobject(
        self, objtype: str, objattrs: dict[str:Any]
    ) -> DataObject:
        """Returns instance of specified local Dataobject type from specified
        attributes"""
        return self.createDataobject(self.local_schema, objtype, objattrs)

    def createRemoteDataobject(
        self, objtype: str, objattrs: dict[str:Any]
    ) -> DataObject:
        """Returns instance of specified remote Dataobject type from specified
        attributes"""
        return self.createDataobject(self.remote_schema, objtype, objattrs)

    @staticmethod
    def createDataobject(
        schema: Dataschema, objtype: str, objattrs: dict[str:Any]
    ) -> DataObject:
        """Returns instance of specified Dataobject type from specified attributes"""
        return schema.objectTypes[objtype](from_json_dict=objattrs)

    @staticmethod
    def getUpdatedObject(obj: DataObject, objattrs: dict[str, Any]) -> DataObject:
        """Return a deepcopy of specified obj, with its attributes updated upon
        specified objattrs dict from Event"""
        newobj = deepcopy(obj)

        # Update newobj attributes
        for attrname, value in objattrs["added"].items():
            setattr(newobj, attrname, value)  # Add new attributes
        for attrname, value in objattrs["modified"].items():
            setattr(newobj, attrname, value)  # Update existing attributes
        for attrname, value in objattrs["removed"].items():
            if hasattr(newobj, attrname):
                delattr(newobj, attrname)  # Delete existing attributes

        return newobj

    def convertDataObjectToLocal(self, obj: DataObject) -> DataObject:
        """Convert specified Dataobject (remote) to local one"""
        tmpEvent = self.convertEventToLocal(
            Event("conversion", "added", obj, obj.toNative())
        )
        return self.local_schema.objectTypes[self.typesmapping[obj.getType()]](
            from_json_dict=tmpEvent.objattrs
        )

    def convertDataObjectListToLocal(
        self, remoteobjtype: str, objlist: DataObjectList
    ) -> DataObjectList:
        """Convert specified DataObjectList (remote) to local one"""
        localobjs = [self.convertDataObjectToLocal(obj) for obj in objlist]
        return self.local_schema.objectlistTypes[self.typesmapping[remoteobjtype]](
            objlist=localobjs
        )

    @staticmethod
    def purgeOldCacheFiles(
        objtypes: list[str] | set[str],
        cacheFilePrefix: str = "",
        cacheFileSuffix: str = "",
    ):
        """ "Delete all cache files of specified objtypes"""
        for objtype in objtypes:
            LocalCache.deleteAllCacheFiles(
                f"{cacheFilePrefix}{objtype}{cacheFileSuffix}"
            )
            LocalCache.deleteAllCacheFiles(
                f"{cacheFilePrefix}{objtype}_complete__{cacheFileSuffix}"
            )
            LocalCache.deleteAllCacheFiles(
                f"{cacheFilePrefix}trashbin_{objtype}{cacheFileSuffix}"
            )
            LocalCache.deleteAllCacheFiles(
                f"{cacheFilePrefix}trashbin_{objtype}_complete__{cacheFileSuffix}"
            )

    def _fillDatamodelDict(self):
        # Fill the datamodel dict
        self._datamodel = {}
        for objtype in self._config["hermes-client"]["datamodel"]:
            self._datamodel[objtype] = {}
            for k, v in self._config["hermes-client"]["datamodel"][objtype].items():
                if k == "attrsmapping":
                    self._datamodel[objtype][k] = dict(v)
                elif k == "toString" and v is not None:
                    # Compile toString's jinja template
                    jinjavars = set()
                    self._datamodel[objtype][k] = Jinja.compileIfJinjaTemplate(
                        v,
                        jinjavars,
                        self._jinjaenv,
                        f"hermes-client.datamodel.{objtype}.toString",
                        False,
                        False,
                    )
                    # Ensure jinja vars are known local attrs
                    unknownattrs = (
                        jinjavars
                        - self._config["hermes-client"]["datamodel"][objtype][
                            "attrsmapping"
                        ].keys()
                    )
                    if unknownattrs:
                        raise HermesUnknownVarsInJinjaTemplateError(
                            "Unknown attributes met in 'hermes-client.datamodel"
                            f".{objtype}.toString' jinja template: {unknownattrs}"
                        )
                else:
                    self._datamodel[objtype][k] = v

    def _fillConversionVars(self):
        # Fill the types mapping (remote as key, local as value)
        typesmapping = {v["hermesType"]: k for k, v in self._datamodel.items()}

        # Types consistency check
        self.unknownRemoteTypes = typesmapping.keys() - self.remote_schema.schema.keys()
        if self.unknownRemoteTypes:
            for t in self.unknownRemoteTypes:
                del typesmapping[t]

        # Reorder typemapping to respect the order specified on remote schema
        self.typesmapping = {}
        for rtype in self.remote_schema.schema:
            if rtype in typesmapping:
                self.typesmapping[rtype] = typesmapping[rtype]

        # Fill the remote2local mapping dict
        for objsettings in self._datamodel.values():
            remote_objtype = objsettings["hermesType"]
            self._remote2local[remote_objtype] = {}
            # Add primary keys to mapping to ensure they're always available
            if remote_objtype in self.remote_schema.schema:
                pkeys = self.remote_schema.schema[remote_objtype][
                    "PRIMARYKEY_ATTRIBUTE"
                ]
                if type(pkeys) not in [list, tuple]:
                    pkeys = [pkeys]
                for pkey in pkeys:
                    objsettings["attrsmapping"][f"_pkey_{pkey}"] = pkey

            for local_attr, remote_attr in objsettings["attrsmapping"].items():
                remote_vars = set()
                objsettings["attrsmapping"][local_attr] = Jinja.compileIfJinjaTemplate(
                    remote_attr,
                    remote_vars,
                    self._jinjaenv,
                    f"hermes-client.datamodel.{remote_objtype}.attrsmapping",
                    False,
                    False,
                )
                if len(remote_vars) == 0:
                    # Hack to handle Jinja templates containing only static data
                    remote_vars.add(None)

                for remote_var in remote_vars:
                    # As many local attrs can be mapped on a same remote attr,
                    # store the mapping in a list
                    self._remote2local[remote_objtype].setdefault(
                        remote_var, []
                    ).append(local_attr)

        # Attributes consistency check
        self.unknownRemoteAttributes = {}
        for rtype in self.typesmapping:
            diff = (
                self._remote2local[rtype].keys()
                - self.remote_schema.schema[rtype]["HERMES_ATTRIBUTES"]
                - set([None])  # Ignore Jinja templates with static data only
            )
            if diff:
                self.unknownRemoteAttributes[rtype] = diff

    def _setupLocalSchema(self) -> Dataschema:
        """Build local schema from local datamodel and remote schema"""
        rschema: dict[str, Any] = self.remote_schema.schema
        schema: dict[str, Any] = {}
        for objtype in self.typesmapping.values():
            remote_objtype = self._datamodel[objtype]["hermesType"]

            secrets = []
            for attr in rschema[remote_objtype]["SECRETS_ATTRIBUTES"]:
                v = self._remote2local[remote_objtype].get(attr)
                if v is not None:
                    secrets.extend(v)

            # Add primary keys to mapping to ensure they're always there
            pkeys = self.remote_schema.schema[remote_objtype]["PRIMARYKEY_ATTRIBUTE"]
            if type(pkeys) in [list, tuple]:
                pkey = tuple([f"_pkey_{pkey}" for pkey in pkeys])
            else:
                pkey = f"_pkey_{pkeys}"

            schema[objtype] = {
                "HERMES_ATTRIBUTES": set(
                    self._datamodel[objtype]["attrsmapping"].keys()
                ),
                "SECRETS_ATTRIBUTES": set(secrets),
                "CACHEONLY_ATTRIBUTES": set(),
                "LOCAL_ATTRIBUTES": set(),
                "PRIMARYKEY_ATTRIBUTE": pkey,
                "TOSTRING": self._datamodel[objtype]["toString"],
            }

        res = Dataschema(schema)
        return res

    @staticmethod
    def getObjectFromCacheOrTrashbin(
        ds: Datasource, objtype: str, objpkey: Any
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
