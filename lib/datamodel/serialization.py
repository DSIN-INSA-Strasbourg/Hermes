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


from typing import TypeVar, Any, TYPE_CHECKING

AnyJSONSerializable = TypeVar("AnyJSONSerializable", bound="JSONSerializable")
AnyLocalCache = TypeVar("AnyLocalCache", bound="LocalCache")

if TYPE_CHECKING:  # pragma: no cover
    # Only for type hints, won't import at runtime
    from typing import Callable, IO
    from lib.config import HermesConfig

from datetime import datetime
from tempfile import NamedTemporaryFile
import json
import os
import os.path
import gzip
import re

import logging

logger = logging.getLogger("hermes")


class HermesInvalidJSONError(Exception):
    """Raised when the json passed to from_json is invalid"""


class HermesInvalidJSONDataError(Exception):
    """Raised when the data passed to from_json has invalid type"""


class HermesInvalidJSONDataattrTypeError(Exception):
    """Raised when the type of specified jsondataattr is invalid"""


class HermesInvalidCacheDirError(Exception):
    """Raised when an CacheDir exist and isn't a directory or isn't writeable"""


class HermesUnspecifiedCacheFilename(Exception):
    """Raised when trying to save cache file from an instance where setCacheFilename()
    has never been called"""


class JSONEncoder(json.JSONEncoder):
    """Helper to serialize specific objects (datetime, JSONSerializable) in JSON"""

    def default(self, obj: Any) -> Any:
        # If object to encode is a datetime, convert it to isoformat string
        if isinstance(obj, datetime):
            return f"{obj.isoformat(timespec='seconds')}Z"
        if isinstance(obj, JSONSerializable):
            return obj._get_jsondict()
        if isinstance(obj, set):
            return sorted(list(obj))
        return json.JSONEncoder.default(self, obj)


class JSONSerializable:
    """Class to extend in order to obtain json serialization/deserialization.

    Children classes have to :
    - offer a constructor that must be callable with the named parameter
        'from_json_dict' only
    - specify the jsondatattr, with a different behavior function of its type :
        - str : name of their instance's attribute (dict) containing the data to
                serialize
        - list | tuple | set : name of the instance's attributes to serialize. The json
                will have each attr name as key, and their content as values
    """

    def __init__(self, jsondataattr: str | list[str] | tuple[str] | set[str]):
        if type(jsondataattr) not in (str, list, tuple, set):
            raise HermesInvalidJSONDataattrTypeError(
                f"Invalid jsondataattr type '{type(jsondataattr)}'."
                " It must be one of the following types : [str, list, tuple, set]"
            )
        self._jsondataattr: str | list[str] | tuple[str] | set[str] = jsondataattr
        """Name of instance's attribute containing the data to serialize, with a
        different behavior function of its type :
            - str : name of their instance's attribute (dict) containing the data to
                    serialize
            - list | tuple | set : name of the instance's attributes to serialize. The
                    json will have each attr name as key, and their content as values
        """

    def _get_jsondict(self) -> dict[str, Any]:
        if type(self._jsondataattr) == str:
            return getattr(self, self._jsondataattr)
        elif type(self._jsondataattr) in (list, tuple, set):
            return {attr: getattr(self, attr) for attr in self._jsondataattr}
        else:
            raise HermesInvalidJSONDataattrTypeError(
                f"Invalid _jsondataattr type '{type(self._jsondataattr)}'."
                " It must be one of the following types : [str, list, tuple, set]"
            )

    def to_json(self) -> str:
        data = self._get_jsondict()
        try:
            if not isinstance(data, dict):
                data = sorted(data)
        except TypeError:
            logger.warning(
                f"Unsortable type {type(self)} exported as JSON. You should consider to set is sortable"
            )
        return json.dumps(data, cls=JSONEncoder, indent=4)

    @classmethod
    def from_json(
        cls: type[AnyJSONSerializable],
        jsondata: str | dict[Any, Any],
        **kwargs: None | Any,
    ) -> AnyJSONSerializable:
        if type(jsondata) == str:
            try:
                jsondict = json.loads(jsondata, object_hook=cls._json_parser)
            except json.decoder.JSONDecodeError as e:
                raise HermesInvalidJSONError(str(e))
        elif isinstance(jsondata, dict):
            jsondict = jsondata
        else:
            raise HermesInvalidJSONDataError(
                f"The 'jsondata' arg must be a str or a dict. Here we have '{type(jsondata)}'"
            )

        return cls(from_json_dict=jsondict, **kwargs)

    @classmethod
    def _json_parser(
        cls: type[AnyJSONSerializable], value: dict[str, Any]
    ) -> dict[str, Any]:
        if isinstance(value, dict):
            for k, v in value.items():
                value[k] = cls._json_parser(v)
        elif isinstance(value, list):
            for index, row in enumerate(value):
                value[index] = cls._json_parser(row)
        elif isinstance(value, str) and value:
            # String have to match "yyyy-mm-ddThh:mm:ssZ" to be converted to datetime
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value):
                pass
            try:
                # Ignore trailing "Z" : handle timezone could create a lot of troubles
                value = datetime.fromisoformat(value[:-1])
            except ValueError:
                pass
        return value


class LocalCache(JSONSerializable):
    """Base class to manage local cache file, extending JSONSerializable objects.
    This class offer file management, compression, rotation, and the ability to create
    instance from cache file or save current instance to cache file.
    """

    _backupCount: int = 0
    """Number of backup files to retain"""

    _cachedir: str = "/dev/null"
    """Directory where cache file(s) will be stored"""

    _compressCache = False
    """Boolean indicating if cache files must be gzipped or store as plain text"""

    _extensions = {True: ".json.gz", False: ".json"}
    """Possible cache files extensions according to LocalCache._compressCache value"""

    _extension = _extensions[_compressCache]
    """Default cache files extension according to LocalCache._compressCache value"""

    @staticmethod
    def setup(config: "HermesConfig"):
        LocalCache._backupCount = config["hermes"]["cache"]["backup_count"]
        """Number of backup files to retain"""

        LocalCache._cachedir = config["hermes"]["cache"]["dirpath"]
        """Directory where cache file(s) will be stored"""

        LocalCache._compressCache = config["hermes"]["cache"]["enable_compression"]
        """Boolean indicating if cache files must be gzipped or store as plain text"""

        LocalCache._extensions = {True: ".json.gz", False: ".json"}
        """Possible cache files extensions according to LocalCache._compressCache value"""

        LocalCache._extension = LocalCache._extensions[LocalCache._compressCache]
        """Default cache files extension according to LocalCache._compressCache value"""

    def __init__(
        self,
        jsondataattr: str | list[str] | tuple[str] | set[str],
        cachefilename: str | None = None,
    ):
        super().__init__(jsondataattr)
        self.setCacheFilename(cachefilename)

        if not os.path.exists(LocalCache._cachedir):
            logger.info(
                f"Local cache dir '{LocalCache._cachedir}' doesn't exists : create it"
            )
            try:
                os.makedirs(LocalCache._cachedir, 0o770)
            except Exception as e:
                logger.fatal(
                    f"Unable to create local cache dir '{LocalCache._cachedir}' : {str(e)}"
                )
                raise

        if not os.path.isdir(LocalCache._cachedir):
            err = f"Local cache dir '{LocalCache._cachedir}' exists and is not a directory"
            logger.fatal(err)
            raise HermesInvalidCacheDirError(err)

        if not os.access(LocalCache._cachedir, os.W_OK):
            err = (
                f"Local cache dir '{LocalCache._cachedir}' exists but is not writeable"
            )
            logger.fatal(err)
            raise HermesInvalidCacheDirError(err)

    def savecachefile(
        self, cacheFilename: str | None = None, dontKeepBackup: bool = False
    ):
        if cacheFilename is not None:
            self.setCacheFilename(cacheFilename)

        if self._localCache_filename is None:
            raise HermesUnspecifiedCacheFilename(
                "Unable to save cache file without having specified the cacheFilename with setCacheFilename()"
            )

        # Generate content before everything else to avoid cache corruption in case of failure
        content = self.to_json()

        found, filepath, ext = self._getExistingFilePath(self._localCache_filename)
        if not found:
            oldcontent = ""
        else:
            # Retrieve previous content
            with self._open(filepath, "rt") as f:
                oldcontent = f.read()

        # Save only if content has changed
        if content != oldcontent:
            # Use a temp file to ensure new data is written before rotating old files
            tmpfilepath: str
            destpath: str = f"{LocalCache._cachedir}/{self._localCache_filename}{LocalCache._extension}"

            with NamedTemporaryFile(
                dir=LocalCache._cachedir,
                suffix=LocalCache._extension,
                mode="wt",
                delete=False,
            ) as tmp:
                # Save full path, and close file to allow to open it with self._open
                # that could allow transparent gzip compression
                tmpfilepath = tmp.name

            with self._open(tmpfilepath, "wt") as f:
                f.write(content)

            if not dontKeepBackup:
                self._rotatecachefile(self._localCache_filename)
            os.rename(tmpfilepath, destpath)

    def setCacheFilename(self, filename: str | None):
        self._localCache_filename = filename

    @classmethod
    def loadcachefile(
        cls: type[AnyLocalCache], filename: str, **kwargs: None | Any
    ) -> AnyLocalCache:
        found, filepath, ext = cls._getExistingFilePath(filename)
        if not found:
            logger.info(
                f"Specified cache file '{filepath}' doesn't exists, returning empty data"
            )
            jsondata = "{}"
        else:
            with cls._open(filepath, "rt") as f:
                jsondata = f.read()

        ret = cls.from_json(jsondata, **kwargs)
        ret.setCacheFilename(filename)
        return ret

    @classmethod
    def _getExistingFilePath(
        cls: type[AnyLocalCache], filename: str
    ) -> tuple[bool, str, str | None]:
        """Check if specified filename exists with default extension, or with other
        This allow the user to change the "enable_compression" setting without breaking
        the current cache.

        Returns a tuple (found, filepath, extension)
            - found: boolean indicating if filepath was found
            - filepath: if found : str indicating filepath, otherwise filepath with
                default extension (may be useful for logging)
            - extension: if found : str containing the extension of the filepath found,
                None otherwise
        """
        for extension in (
            # Extension that should be used according to Config
            LocalCache._extensions[LocalCache._compressCache],
            # Extension that could be used if settings has changed
            LocalCache._extensions[not LocalCache._compressCache],
        ):
            filepath = f"{LocalCache._cachedir}/{filename}{extension}"
            if os.path.exists(filepath):
                return (True, filepath, extension)

        # Not found
        return (
            False,
            f"{LocalCache._cachedir}/{filename}{LocalCache._extension}",
            None,
        )

    @classmethod
    def _open(cls: type[AnyLocalCache], path: str, mode: str = "r") -> "IO":
        gzipped = path.endswith(LocalCache._extensions[True])
        _open: Callable[[str, str], "IO"] = gzip.open if gzipped else open
        return _open(path, mode)

    @classmethod
    def _rotatecachefile(cls: type[AnyLocalCache], filename: str):
        idxlen = 6
        for i in range(LocalCache._backupCount, 0, -1):
            oldsuffix = f".{str(i-1).zfill(idxlen)}" if i > 1 else ""
            found, old, ext = cls._getExistingFilePath(f"{filename}{oldsuffix}")
            if found:
                new = f"{LocalCache._cachedir}/{filename}.{str(i).zfill(idxlen)}{ext}"
                os.rename(old, new)

    @classmethod
    def deleteAllCacheFiles(cls: type[AnyLocalCache], filename: str):
        """Delete cache files and its backups with specified filename"""
        # Remove main cache file
        found, path, ext = cls._getExistingFilePath(f"{filename}")
        if found:
            logger.debug(f"Deleting '{path}'")
            os.remove(path)

        # Remove backup cache files
        idxlen = 6
        for i in range(LocalCache._backupCount, 0, -1):
            suffix = f".{str(i-1).zfill(idxlen)}" if i > 1 else ""
            found, path, ext = cls._getExistingFilePath(f"{filename}{suffix}")
            if found:
                logger.debug(f"Deleting '{path}'")
                os.remove(path)
