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


from typing import Any


class DiffObject:
    """Contain differences between two DataObject or two DataObjectList.
    Differences will be stored as keys in 3 properties sets:
        - added
        - modified
        - removed
    The sets should contain object properties names when objnew and objold are specified
    in constructor (e.g. when comparing two DataObject), or some objects otherwise (e.g. when
    comparing two DataObjectList). Objects added MUST not be tuple, list, set or frozenset.

    When tested with 'if instance', DiffObject instance returns False if no
    difference was found, True otherwise.
    """

    def __init__(self, objnew: Any = None, objold: Any = None):
        """Create an empty new diff object"""
        self.objnew = objnew
        self.objold = objold
        self._added: set[Any] = set()
        self._modified: set[Any] = set()
        self._removed: set[Any] = set()

    @property
    def added(self) -> list[Any] | set[Any]:
        """Returns a list of what is present in objnew and not in objold.
        If content can be sorted, returns a sorted list, returns a set otherwise"""
        try:
            return sorted(self._added)
        except TypeError:
            return self._added

    @property
    def modified(self) -> list[Any] | set[Any]:
        """Returns a list of what exists in objnew and objold, but differs.
        If content can be sorted, returns a sorted list, returns a set otherwise"""
        try:
            return sorted(self._modified)
        except TypeError:
            return self._modified

    @property
    def removed(self) -> list[Any] | set[Any]:
        """Returns a list of what is present in objold and not in objnew.
        If content can be sorted, returns a sorted list, returns a set otherwise"""
        try:
            return sorted(self._removed)
        except TypeError:
            return self._removed

    @property
    def dict(self) -> dict[str, Any]:
        """Returns a diff dict always containing three keys: 'added', 'modified' and
        'removed'.
        The values differs depending on whether objnew has been set on constructor or not.
        - If objnew has been set:
            - 'added' and 'modified' will be a dict with attrname as key, and objnew's value
               of 'attrname'
            - 'removed' will be a dict with attrname as key, and None as value
        - If objnew hasn't been set, 'added', 'modified' and 'removed' will be a list of
          objects, sorted when possible
        """
        if self.objnew is not None:
            return {
                "added": {attr: getattr(self.objnew, attr) for attr in self.added},
                "modified": {
                    attr: getattr(self.objnew, attr) for attr in self.modified
                },
                "removed": {attr: None for attr in self.removed},
            }

        return {
            "added": self.added,
            "modified": self.modified,
            "removed": self.removed,
        }

    def appendAdded(self, value: Any):
        """Mark specified value as added. Multiple values can be specified at once by
        encapsulating them in tuple, list, set, or frozenset"""
        self._append("_added", value)

    def appendModified(self, value: Any):
        """Mark specified value as modified. Multiple values can be specified at once by
        encapsulating them in tuple, list, set, or frozenset"""
        self._append("_modified", value)

    def appendRemoved(self, value: Any):
        """Mark specified value as removed. Multiple values can be specified at once by
        encapsulating them in tuple, list, set, or frozenset"""
        self._append("_removed", value)

    def _append(self, attrname: str, value: Any):
        """Mark specified value as specified attrname. Multiple values can be specified at
        once by encapsulating them in tuple, list, set, or frozenset"""
        attr: set = getattr(self, attrname)
        if isinstance(value, (tuple, list, set, frozenset)):
            attr |= set(value)
        else:
            attr.add(value)

    def __bool__(self) -> bool:
        """Allow to test current instance and return False if there's no difference, True
        otherwise"""
        return len(self._removed) + len(self._added) + len(self._modified) > 0
