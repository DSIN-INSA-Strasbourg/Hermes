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


# File mostly based on singleton.py from tendo package under PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2 :
#  - https://github.com/pycontribs/tendo
#  - https://raw.githubusercontent.com/pycontribs/tendo/master/tendo/singleton.py
#  - https://pypi.org/project/tendo/


import os
import sys
import tempfile

import logging

logger = logging.getLogger("hermes")


if sys.platform != "win32":
    import fcntl


class SingleInstanceException(BaseException):  # pragma: no cover
    pass


class SingleInstance(object):  # pragma: no cover
    """Class that can be instantiated only once per machine.

    If you want to prevent your script from running in parallel just instantiate
    SingleInstance() class.
    If is there another instance already running it will throw a
    `SingleInstanceException`.

    >>> import tendo
    ... me = SingleInstance("appname")

    This option is very useful if you have scripts executed by crontab at small
    amounts of time.

    Remember that this works by creating a lock file with a filename based on the
    full dir path to the script file and the specified appname.
    """

    def __init__(self, appname: str):
        self.initialized = False
        basename = (
            os.path.dirname(os.path.abspath(sys.argv[0])) + "/" + appname
        ).replace("/", "-").replace(":", "").replace("\\", "-") + ".lock"
        self.lockfile = os.path.normpath(tempfile.gettempdir() + "/" + basename)

        logger.debug("SingleInstance lockfile: " + self.lockfile)
        if sys.platform == "win32":
            try:
                # file already exists, we try to remove (in case previous
                # execution was interrupted)
                if os.path.exists(self.lockfile):
                    os.unlink(self.lockfile)
                self.fd = os.open(self.lockfile, os.O_CREAT | os.O_EXCL | os.O_RDWR)
            except OSError:
                type, e, tb = sys.exc_info()
                if e.errno == 13:
                    logger.error("Another instance is already running, quitting.")
                    raise SingleInstanceException()
                print(e.errno)
                raise
        else:  # non Windows
            self.fp = open(self.lockfile, "w")
            self.fp.flush()
            try:
                fcntl.lockf(self.fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except IOError:
                logger.error("Another instance is already running, quitting.")
                raise SingleInstanceException()
        self.initialized = True

    def __del__(self):
        if not self.initialized:
            return
        try:
            if sys.platform == "win32":
                if hasattr(self, "fd"):
                    os.close(self.fd)
                    os.unlink(self.lockfile)
            else:
                fcntl.lockf(self.fp, fcntl.LOCK_UN)
                self.fp.close()
                if os.path.isfile(self.lockfile):
                    os.unlink(self.lockfile)
        except Exception as e:
            if logger:
                logger.warning(e)
            else:
                print("Unloggable error: %s" % e)
            sys.exit(-1)
