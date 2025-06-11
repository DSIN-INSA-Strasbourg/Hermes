#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Hermes : Change Data Capture (CDC) tool from any source(s) to any target
# Copyright (C) 2025 INSA Strasbourg
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

# The "filter()" code is heavily based upon ansible-core 'regex_search' filter :
# https://github.com/ansible/ansible/blob/v2.18.6/lib/ansible/plugins/filter/core.py


import re
from lib.plugins import AbstractAttributePlugin

HERMES_PLUGIN_CLASSNAME: str | None = "RegexSearch"
"""The plugin class name defined in this module file"""


class RegexSearch(AbstractAttributePlugin):
    """Plugin to implement regex_search filter from Ansible

    This plugin is based upon ansible-core regex_search implementation :
        - Code : https://github.com/ansible/ansible/blob/v2.18.6/lib/ansible/plugins/filter/core.py
        - Doc : https://docs.ansible.com/ansible/latest/collections/ansible/builtin/regex_search_filter.html
    """  # noqa

    def __init__(self, settings: dict[str, any]) -> None:
        """Instantiate new plugin and store a copy of its settings dict in
        self._settings"""
        super().__init__(settings)

    def filter(self, value: str, regex: str, *args, **kwargs) -> list[str] | None:
        """Perform re.search and return the list of matches or a backref, or None of if
        there was no match
        This function is based upon ansible-core regex_search implementation :
            - Code : https://github.com/ansible/ansible/blob/v2.18.6/lib/ansible/plugins/filter/core.py
            - Doc : https://docs.ansible.com/ansible/latest/collections/ansible/builtin/regex_search_filter.html
        """  # noqa

        if type(value) is not str:
            raise TypeError(
                f"Invalid type for value: {type(value)=}." " Value must be a string"
            )

        if type(regex) is not str:
            raise TypeError(
                f"Invalid type for regex: {type(regex)=}." " Regex must be a string"
            )

        groups = list()
        for arg in args:
            if arg.startswith("\\g"):
                match = re.match(r"\\g<(\S+)>", arg).group(1)
                groups.append(match)
            elif arg.startswith("\\"):
                match = int(re.match(r"\\(\d+)", arg).group(1))
                groups.append(match)
            else:
                raise ValueError("Unknown argument")
            raise

        flags = 0
        if kwargs.get("ignorecase"):
            flags |= re.I
        if kwargs.get("multiline"):
            flags |= re.M

        match = re.search(regex, value, flags)
        if match:
            if not groups:
                return match.group()
            else:
                items = list()
                for item in groups:
                    items.append(match.group(item))
                return items
