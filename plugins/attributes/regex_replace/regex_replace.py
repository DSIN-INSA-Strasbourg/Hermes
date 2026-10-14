#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Hermes : Change Data Capture (CDC) tool from any source(s) to any target
# Copyright (C) 2026 INSA Strasbourg
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

# The "filter()" code is heavily based upon ansible-core 'regex_replace' filter :
# https://github.com/ansible/ansible/blob/v2.21.5/lib/ansible/plugins/filter/core.py


import re
from lib.plugins import AbstractAttributePlugin

HERMES_PLUGIN_CLASSNAME: str | None = "RegexReplace"
"""The plugin class name defined in this module file"""


class RegexReplace(AbstractAttributePlugin):
    """Plugin to implement regex_replace filter from Ansible

    This plugin is based upon ansible-core regex_replace implementation :
        - Code : https://github.com/ansible/ansible/blob/v2.21.5/lib/ansible/plugins/filter/core.py
        - Doc : https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/regex_replace_filter.html
    """  # noqa

    def __init__(self, settings: dict[str, any]) -> None:
        """Instantiate new plugin and store a copy of its settings dict in
        self._settings"""
        super().__init__(settings)

    def filter(
        self,
        value: str,
        pattern: str,
        replacement: str,
        ignorecase: bool = False,
        multiline: bool = False,
        count: int = 0,
        mandatory_count: int = 0,
    ) -> str:
        """Perform a re.sub returning a string
        there was no match
        This function is based upon ansible-core regex_replace implementation :
            - Code : https://github.com/ansible/ansible/blob/v2.21.5/lib/ansible/plugins/filter/core.py
            - Doc : https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/regex_replace_filter.html
        """  # noqa

        if type(value) is not str:
            raise TypeError(
                f"Invalid type for value: {type(value)=}." " Value must be a string"
            )

        if type(pattern) is not str:
            raise TypeError(
                f"Invalid type for pattern: {type(pattern)=}."
                " Pattern must be a string"
            )

        if type(replacement) is not str:
            raise TypeError(
                f"Invalid type for replacement: {type(replacement)=}."
                " Replacement must be a string"
            )

        flags = 0
        if ignorecase:
            flags |= re.I
        if multiline:
            flags |= re.M
        _re = re.compile(pattern, flags=flags)
        output, subs = _re.subn(replacement, value, count=count)
        if mandatory_count and mandatory_count != subs:
            raise ValueError(
                f"'{pattern}' should match {mandatory_count} times,"
                f" but matches {count} times in '{value}'"
            )
        return output
