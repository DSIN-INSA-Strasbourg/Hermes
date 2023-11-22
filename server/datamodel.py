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


from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    # Only for type hints, won't import at runtime
    from lib.config import HermesConfig

from typing import Callable

from jinja2 import StrictUndefined
from jinja2.environment import Template
from jinja2.nativetypes import NativeEnvironment
import time

from lib.datamodel.dataschema import Dataschema
from lib.datamodel.dataobject import DataObject
from lib.datamodel.dataobjectlist import DataObjectList
from lib.datamodel.jinja import Jinja, HermesUnknownVarsInJinjaTemplateError
from lib.plugins import AbstractDataSourcePlugin
from lib.datamodel.datasource import Datasource

import logging

logger = logging.getLogger("hermes")


class HermesDataModelMissingPrimarykeyError(Exception):
    """Raised when the primarykey is missing from the attrsmapping of a source in datamodel"""


class HermesDataModelInvalidQueryTypeError(Exception):
    """Raised when _runQuery() is called with an invalid querytype"""


class DatamodelFragment:
    """Handle settings, data and access to remote source data of one datamodel type for one
    source.

    The data from several DatamodelFragment will then be consolidated and merged in and by
    Datamodel.
    """

    HERMES_RESERVED_JINJA_VARS = set(
        [
            "_SELF",
            "REMOTE_ATTRIBUTES",
            "ITEM_CACHED_VALUES",
            "ITEM_FETCHED_VALUES",
            "CACHED_VALUES",
            "FETCHED_VALUES",
        ]
    )
    """Jinja variables names reserved for internal use"""

    def __init__(
        self,
        dataobjtype: str,
        datasourcename: str,
        fragmentSettings: dict[str, str | dict],
        primarykeyattr: str | tuple[str],
        datasourceplugin: AbstractDataSourcePlugin,
        attributesplugins: dict[str, Callable[..., Any]],
    ):
        """Create a new DatamodelFragment of specified dataobjtype, from specified datasourcename.
        To allow data to be fetched/commited properly, fragmentSettings (source settings)
        must be specified, as primarykeyattr, datasourceplugin and attributesplugins"""
        self._dataobjects: list[DataObject] = []
        self._datasourceplugin: AbstractDataSourcePlugin = datasourceplugin
        self._errorcontext: str = (
            f"hermes-server.datamodel.{dataobjtype}.{datasourcename}.attrsmapping"
        )
        self._jinjaenv: NativeEnvironment = NativeEnvironment(undefined=StrictUndefined)
        self._jinjaenv.filters |= attributesplugins
        self.datasourcename: str = datasourcename
        self._settings: dict[str, str | dict] = fragmentSettings
        self._compiledsettings = Jinja.compileIfJinjaTemplate(
            self._settings, None, self._jinjaenv, self._errorcontext, False, False
        )
        self._dataobjclass: type[DataObject] = self.__createDataObjectsubclass(
            dataobjtype, datasourcename, primarykeyattr
        )

    def __createDataObjectsubclass(
        self, dataobjtype: str, datasourcename: str, primarykeyattr: str | tuple[str]
    ) -> type[DataObject]:
        """Dynamically create a new subclass of DataObject class, and set it up according
        to Datamodel"""
        newcls: type[DataObject] = Dataschema.createSubclass(
            f"{dataobjtype}_{datasourcename}", DataObject
        )

        newcls.PRIMARYKEY_ATTRIBUTE = primarykeyattr
        newcls.REMOTE_ATTRIBUTES = set()
        # This function will fill newcls.REMOTE_ATTRIBUTES
        newcls.HERMES_TO_REMOTE_MAPPING = Jinja.compileIfJinjaTemplate(
            self._settings["attrsmapping"],
            newcls.REMOTE_ATTRIBUTES,
            self._jinjaenv,
            self._errorcontext,
            True,
            False,
            excludeFlatVars=self.HERMES_RESERVED_JINJA_VARS,
        )
        newcls.HERMES_ATTRIBUTES = set(self._settings["attrsmapping"].keys())
        newcls.SECRETS_ATTRIBUTES = set(self._settings["secrets_attrs"])
        newcls.CACHEONLY_ATTRIBUTES = set(self._settings["cacheonly_attrs"])
        newcls.LOCAL_ATTRIBUTES = set(self._settings["local_attrs"])

        logger.debug(
            f"Created dynamic class :\n"
            f"  {newcls.__name__}:\n"
            f"    - {newcls.PRIMARYKEY_ATTRIBUTE=}\n"
            f"    - {newcls.HERMES_ATTRIBUTES=}\n"
            f"    - {newcls.REMOTE_ATTRIBUTES=}\n"
            f"    - {newcls.HERMES_TO_REMOTE_MAPPING=}\n"
            f"    - {newcls.SECRETS_ATTRIBUTES=}\n"
            f"    - {newcls.CACHEONLY_ATTRIBUTES=}\n"
            f"    - {newcls.LOCAL_ATTRIBUTES=}"
        )
        return newcls

    def getDataobjClass(self) -> type[DataObject]:
        """Return DataObject subclass of current fragment"""
        return self._dataobjclass

    def fetch(self, cache: DataObjectList):
        """Fetch data from current fragment source"""
        cached_values: list[dict[str, Any]] = cache.toNative()
        objcls = self.getDataobjClass()

        context = {
            "REMOTE_ATTRIBUTES": objcls.REMOTE_ATTRIBUTES,
            "CACHED_VALUES": cached_values,
        }
        query = self._compiledsettings["fetch"]["query"]
        if isinstance(query, Template):
            query = query.render(context)

        queryvars = Jinja.renderQueryVars(
            self._compiledsettings["fetch"]["vars"], context
        )
        fetcheddata = self._runQuery(self._settings["fetch"]["type"], query, queryvars)

        self._dataobjects = []
        for objdata in fetcheddata:
            # As primary key may be a tuple, we'll have to render each value of tuple
            objpkeys = []
            if type(objcls.PRIMARYKEY_ATTRIBUTE) == tuple:
                pkey_attrs = objcls.PRIMARYKEY_ATTRIBUTE
            else:
                pkey_attrs = (objcls.PRIMARYKEY_ATTRIBUTE,)

            for pkey_attr in pkey_attrs:
                # Render pkey value
                remotepkeyattr = self._compiledsettings["attrsmapping"][pkey_attr]
                if isinstance(remotepkeyattr, Template):
                    # Render from compiled Jinja Template
                    objpkeys.append(remotepkeyattr.render(objdata))
                else:
                    # Raw value
                    objpkeys.append(objdata.get(remotepkeyattr))

            if type(objcls.PRIMARYKEY_ATTRIBUTE) == tuple:
                objpkey = tuple(objpkeys)
            else:
                objpkey = objpkeys[0]

            item_cache = cache.get(objpkey)
            if item_cache:
                objcontext = {"ITEM_CACHED_VALUES": item_cache.toNative()}
            else:
                objcontext = {"ITEM_CACHED_VALUES": {}}

            self._dataobjects.append(
                objcls(from_remote=objdata, jinjaContextVars=objcontext)
            )

    def commit_one(
        self, item_cached_values: dict[str, Any], item_fetched_values: dict[str, Any]
    ):
        """Commit that one object data changes have successfully sent to message bus"""
        if self._settings.get("commit_one") is None:
            return

        objcls = self.getDataobjClass()

        context = {
            "REMOTE_ATTRIBUTES": objcls.REMOTE_ATTRIBUTES,
            "ITEM_CACHED_VALUES": item_cached_values,
            "ITEM_FETCHED_VALUES": item_fetched_values,
        }
        query = self._compiledsettings["commit_one"].get("query", "")
        if isinstance(query, Template):
            query = query.render(context)

        queryvars = Jinja.renderQueryVars(
            self._compiledsettings["commit_one"]["vars"], context
        )
        self._runQuery(self._settings["commit_one"]["type"], query, queryvars)

    def commit_all(
        self, cached_values: list[dict[str, Any]], fetched_values: list[dict[str, Any]]
    ):
        """Commit that all data fetched has successfully sent to message bus"""
        if self._settings.get("commit_all") is None:
            return

        objcls = self.getDataobjClass()

        context = {
            "REMOTE_ATTRIBUTES": objcls.REMOTE_ATTRIBUTES,
            "CACHED_VALUES": cached_values,
            "FETCHED_VALUES": fetched_values,
        }
        query = self._compiledsettings["commit_all"].get("query", "")
        if isinstance(query, Template):
            query = query.render(context)

        queryvars = Jinja.renderQueryVars(
            self._compiledsettings["commit_all"]["vars"], context
        )
        self._runQuery(self._settings["commit_all"]["type"], query, queryvars)

    def _runQuery(
        self, querytype: str, query: str, queryvars: dict[str, Any]
    ) -> list[dict[str, Any]] | None:
        """Run specified query with specified quetyvars  on datasource.
        querytype must be one of fetch, add, delete, modify.

        Returns None when querytype isn't "fetch",
        otherwise returns a list of dict containg each entry fetched, with
        REMOTE_ATTRIBUTES as keys, and corresponding fetched values as values
        """
        logger.debug(
            f"{self.getDataobjClass().__name__} : _runQuery({querytype=}, {query=}, {queryvars=})"
        )
        fetcheddata = None
        starttime = time.time()
        with self._datasourceplugin:
            if querytype == "fetch":
                fetcheddata = self._datasourceplugin.fetch(query, queryvars)
            elif querytype == "add":
                self._datasourceplugin.add(query, queryvars)
            elif querytype == "delete":
                self._datasourceplugin.delete(query, queryvars)
            elif querytype == "modify":
                self._datasourceplugin.modify(query, queryvars)
            else:
                raise HermesDataModelInvalidQueryTypeError(
                    f"runQuery called with invalid querytype '{querytype}'"
                )

        elapsedms = int(round(1000 * (time.time() - starttime)))
        if fetcheddata is None:
            logger.debug(
                f"{self.getDataobjClass().__name__} : _runQuery() returned in {elapsedms} ms"
            )
        else:
            logger.debug(
                f"{self.getDataobjClass().__name__} : _runQuery() returned {len(fetcheddata)} entries in {elapsedms} ms"
            )

        return fetcheddata


class Datamodel:
    """Load and build the Datamodel from config.

    In charge of :
    - generating Dataschema
    - retrieving remote data from all sources, and merging it
    """

    def __init__(self, config: "HermesConfig"):
        """Build the datamodel from config"""
        self._fragments: dict[str, list[DatamodelFragment]] = {
            k: [] for k in config["hermes-server"]["datamodel"].keys()
        }

        self._config: "HermesConfig" = config
        self._jinjaenv: NativeEnvironment = NativeEnvironment(undefined=StrictUndefined)

        # Fill the _fragments dictionnary
        datamodel: dict[str, Any] = config["hermes-server"]["datamodel"]
        for objtype, fragmentslist in self._fragments.items():
            for sourcename, sourcesettings in datamodel[objtype]["sources"].items():
                pkeyattr = datamodel[objtype]["primarykeyattr"]
                if type(pkeyattr) == list:
                    pkeyattr = tuple(pkeyattr)
                item = DatamodelFragment(
                    objtype,
                    sourcename,
                    sourcesettings,
                    pkeyattr,
                    config["hermes"]["plugins"]["datasources"][sourcename][
                        "plugininstance"
                    ],
                    config["hermes"]["plugins"]["attributes"]["_jinjafilters"],
                )
                fragmentslist.append(item)

        # Consolidate _fragments data to set up the Dataschema
        self.dataschema: Dataschema = self.__setupSchema()
        """Current Dataschema"""

        # Compile Jinja template of integrity_constraints, and store vars of
        # merge_constraints for "lazy" generation of template vars
        self._compileJinja()

        # Load Datasource with cache
        self.data: Datasource = Datasource(
            schema=self.dataschema, enableTrashbin=False, enableCache=True
        )

    def __setupSchema(self) -> Dataschema:
        """Consolidate _fragments data to set up the Dataschema"""
        schema: dict[str, Any] = {}
        for objtype in self._fragments.keys():
            count: dict[str, int] = {}
            secrets_attrs = set()
            cacheonly_attrs = set()
            local_attrs = set()
            # Ensure primarykey is in attrsmapping of each sources
            for fragment in self._fragments[objtype]:
                objcls = fragment.getDataobjClass()
                if objcls.SECRETS_ATTRIBUTES:
                    secrets_attrs |= objcls.SECRETS_ATTRIBUTES
                if objcls.CACHEONLY_ATTRIBUTES:
                    cacheonly_attrs |= objcls.CACHEONLY_ATTRIBUTES
                if objcls.LOCAL_ATTRIBUTES:
                    local_attrs |= objcls.LOCAL_ATTRIBUTES
                for attr in objcls.HERMES_ATTRIBUTES:
                    count[attr] = count[attr] + 1 if attr in count else 1
            pkey = self._fragments[objtype][0].getDataobjClass().PRIMARYKEY_ATTRIBUTE

            if type(pkey) == tuple:
                for key in pkey:
                    if count[key] != len(self._fragments[objtype]):
                        raise HermesDataModelMissingPrimarykeyError(
                            f"The primary key '{pkey}' must be fetched from each datasource"
                        )
            else:
                if count[pkey] != len(self._fragments[objtype]):
                    raise HermesDataModelMissingPrimarykeyError(
                        f"The primary key '{pkey}' must be fetched from each datasource"
                    )

            # Compile toString jinja template
            jinjavars = set()
            tostringTpl = Jinja.compileIfJinjaTemplate(
                self._config["hermes-server"]["datamodel"][objtype]["toString"],
                jinjavars,
                self._jinjaenv,
                f"hermes-server.datamodel.{objtype}.toString",
                False,
                False,
            )
            # Ensure jinja vars are known local attrs
            unknownattrs = jinjavars - set(count.keys())
            if unknownattrs:
                raise HermesUnknownVarsInJinjaTemplateError(
                    f"Unknown attributes met in 'hermes-server.datamodel.{objtype}.toString' jinja template : {unknownattrs}"
                )
            schema[objtype] = {
                "HERMES_ATTRIBUTES": set(count.keys()),
                "SECRETS_ATTRIBUTES": secrets_attrs,
                "CACHEONLY_ATTRIBUTES": cacheonly_attrs,
                "LOCAL_ATTRIBUTES": local_attrs,
                "PRIMARYKEY_ATTRIBUTE": pkey,
                "TOSTRING": tostringTpl,
            }

        res = Dataschema(schema)
        return res

    def _compileJinja(self):
        """Compile Jinja template of integrity_constraints, and store vars of
        merge_constraints for "lazy" generation of template vars"""
        for dataobjtype, settings in self._config["hermes-server"]["datamodel"].items():
            # Fill merge_constraints_vars that will contain required vars by differents
            # merge_constraints specified in sources. This will allow lazy generation of
            # Jinja env vars
            settings["merge_constraints_vars"] = set()
            for srcname, srcsettings in settings["sources"].items():
                Jinja.compileIfJinjaTemplate(
                    var=srcsettings["merge_constraints"],
                    flatvars_set=settings["merge_constraints_vars"],
                    jinjaenv=self._jinjaenv,
                    errorcontext=f"hermes-server.datamodel.{dataobjtype}.sources.{srcname}.merge_constraints",
                    allowOnlyOneTemplate=False,
                    allowOnlyOneVar=False,
                )

            # Compile integrity_constraints templates and fill integrity_constraints_vars that
            # will contain required vars. This will allow lazy generation of Jinja env vars
            settings["integrity_constraints_vars"] = set()
            settings["integrity_constraints"] = Jinja.compileIfJinjaTemplate(
                var=settings["integrity_constraints"],
                flatvars_set=settings["integrity_constraints_vars"],
                jinjaenv=self._jinjaenv,
                errorcontext=f"hermes-server.datamodel.{dataobjtype}.integrity_constraints",
                allowOnlyOneTemplate=False,
                allowOnlyOneVar=False,
            )

    def fetch(self):
        """Fetch data from all sources, enforce merge and integrity constraints, and store
        merged data in 'ds' attribute"""
        fragment: DatamodelFragment
        # Load data starting in specific order to minimize inconsistencies if any
        # modifications are processed in the same time
        for objtype, objlistcls in self.dataschema.objectlistTypes.items():
            settings = self._config["hermes-server"]["datamodel"][objtype]
            dontMergeOnConflict = settings["on_merge_conflict"] == "use_cached_entry"
            cache = self.data.cache[objtype]
            mergeFiltered: set[Any] = set()  # pkeys

            # Fetch data
            starttime = time.time()
            for fragment in self._fragments[objtype]:
                fragment.fetch(cache)  # Fetch fragment data from remote source
            elapsedms = int(round(1000 * (time.time() - starttime)))
            logger.debug(
                f"Fetched and converted all <{objtype}> data in {elapsedms} ms"
            )

            # Enforce merge constraints, if any
            if any(
                len(i._compiledsettings["merge_constraints"]) > 0
                for i in self._fragments[objtype]
            ):
                starttime = time.time()
                hasChanged = True
                # Loop until no change is made
                while hasChanged:
                    hasChanged = False

                    # Fill vars dict
                    vars = {}
                    for fragment in self._fragments[objtype]:
                        dataobjlist = objlistcls(objlist=fragment._dataobjects)
                        # Generate vars only if required
                        if (
                            fragment.datasourcename + "_pkeys"
                            in settings["merge_constraints_vars"]
                        ):
                            vars[
                                fragment.datasourcename + "_pkeys"
                            ] = dataobjlist.getPKeys()
                        if (
                            fragment.datasourcename
                            in settings["merge_constraints_vars"]
                        ):
                            vars[fragment.datasourcename] = dataobjlist.toNative()

                    # Apply constraints
                    for fragment in self._fragments[objtype]:
                        constraints = fragment._compiledsettings["merge_constraints"]
                        if not constraints:
                            continue
                        toRemove = set()
                        for obj in fragment._dataobjects:
                            for constraint in constraints:
                                # Generate _SELF var only if required
                                if "_SELF" in settings["merge_constraints_vars"]:
                                    vars["_SELF"] = obj.toNative()
                                if not constraint.render(vars):
                                    toRemove.add(obj)
                                    break
                        if toRemove:
                            hasChanged = True
                            # logger.debug(
                            #     f"Merge constraints : filtering {len(toRemove)} item(s) from {fragment.datasourcename}"
                            # )
                            for obj in toRemove:
                                fragment._dataobjects.remove(obj)
                                mergeFiltered.add(obj.getPKey())

                elapsedms = int(round(1000 * (time.time() - starttime)))
                logger.debug(
                    f"Enforced <{objtype}> merge constraints in {elapsedms} ms : filtered {len(mergeFiltered)} item(s)"
                )

            # Merge data
            starttime = time.time()
            objlist: DataObjectList = None
            for fragment in self._fragments[objtype]:
                if objlist is None:  # First fragment
                    objlist = objlistcls(objlist=fragment._dataobjects)
                else:  # other fragments than first
                    mergeFiltered |= objlist.mergeWith(
                        objlist=fragment._dataobjects,
                        pkeyMergeConstraint=fragment._settings["pkey_merge_constraint"],
                        dontMergeOnConflict=dontMergeOnConflict,
                    )
            objlist.mergeFiltered |= mergeFiltered
            elapsedms = int(round(1000 * (time.time() - starttime)))
            logger.debug(
                f"Merged all <{objtype}> data in {elapsedms} ms : filtered {len(mergeFiltered)} item(s)"
            )

            # Store merged data in current Datasource var
            self.data[objtype] = objlist

            # Replace inconsistencies and merge conflicts by cache values
            self.data[objtype].replaceInconsistenciesByCachedValues(
                self.data.cache[objtype]
            )

        # Enforce integrity constraints, if any
        if any(
            len(self._config["hermes-server"]["datamodel"][t]["integrity_constraints"])
            > 0
            for t in self.dataschema.objectlistTypes
        ):
            starttime = time.time()
            hasChanged = True
            # Loop until no change is made
            while hasChanged:
                hasChanged = False

                # Fill vars dict
                vars = {}
                for objtype in self.dataschema.objectlistTypes:
                    # Generate vars only if required
                    if objtype + "_pkeys" in settings["integrity_constraints_vars"]:
                        vars[objtype + "_pkeys"] = self.data[objtype].getPKeys()
                    if objtype in settings["integrity_constraints_vars"]:
                        vars[objtype] = self.data[objtype].toNative()

                # Apply constraints
                for objtype in self.dataschema.objectlistTypes:
                    settings = self._config["hermes-server"]["datamodel"][objtype]
                    if not settings["integrity_constraints"]:
                        continue

                    integrityFiltered = set()
                    for obj in self.data[objtype]:
                        for constraint in settings["integrity_constraints"]:
                            # Generate _SELF var only if required
                            if "_SELF" in settings["integrity_constraints_vars"]:
                                vars["_SELF"] = obj.toNative()
                            if not constraint.render(vars):
                                integrityFiltered.add(obj.getPKey())
                                break
                    if integrityFiltered:
                        hasChanged = True
                        for pkey in integrityFiltered:
                            self.data[objtype].removeByPkey(pkey)
                        logger.debug(
                            f"Integrity constraints : filtered {len(integrityFiltered)} item(s) from {objtype}"
                        )
                        self.data[objtype].integrityFiltered |= integrityFiltered

            elapsedms = int(round(1000 * (time.time() - starttime)))
            logger.debug(f"Integrity constraints enforced in {elapsedms} ms")

    def commit_one(self, obj: DataObject):
        """Commit that specified 'obj' data changes have successfully sent to message bus"""
        for objtype, objcls in self.dataschema.objectTypes.items():
            if isinstance(obj, objcls):
                cachedobj: DataObject | None = self.data.cache[objtype].get(
                    obj.getPKey()
                )
                cachedvalues = cachedobj.toNative() if cachedobj else {}
                fetchedvalues = obj.toNative()
                fragments = self._fragments[objtype]
                break
        else:
            raise TypeError(
                f"Specified object {repr(obj)} has invalid type '{type(obj)}'"
            )

        for fragment in fragments:
            fragment.commit_one(cachedvalues, fetchedvalues)

    def commit_all(self, objtype: str):
        """Commit that all data fetched has successfully sent to message bus"""
        cachedvalues = self.data.cache[objtype].toNative()
        fetchedvalues = self.data[objtype].toNative()
        fragments = self._fragments[objtype]

        for fragment in fragments:
            fragment.commit_all(cachedvalues, fetchedvalues)
