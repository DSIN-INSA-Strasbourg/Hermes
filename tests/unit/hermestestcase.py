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


import unittest

import __main__

import builtins
import os
import shutil
import sys
from tempfile import TemporaryDirectory
import threading
import yaml

from lib.config import HermesConfig
import logging


class HermesServerTestCase(unittest.TestCase):
    main = __main__.__file__
    argv = sys.argv.copy()
    cwd = os.getcwd()
    fixturesdir = f"{os.path.realpath(os.path.dirname(__file__))}/fixtures"
    tmpdir: TemporaryDirectory | None = None
    conffile = None

    @classmethod
    def setUpClass(cls):
        logging.disable(logging.CRITICAL)

        # Global logger setup
        appname = "hermes-unit-tests"
        builtins.__hermes__ = threading.local()
        __hermes__.appname = appname
        __hermes__.logger = logging.getLogger(appname)

        # Force server context
        __main__.__file__ = f"{cls.cwd}/hermes.py"
        sys.argv = ["hermes.py", "server"]

        # Create temp workdir
        cls.tmpdir = TemporaryDirectory()
        os.chdir(cls.tmpdir.name)
        cls.conffile = f"{cls.tmpdir.name}/hermes-server-config.yml"

    @classmethod
    def tearDownClass(cls):
        logging.disable(logging.NOTSET)
        __main__.__file__ = cls.main
        sys.argv = cls.argv
        os.chdir(cls.cwd)
        cls.tmpdir.cleanup()

    @classmethod
    def loadYaml(cls, path=None):
        if path is None:
            path = f"{cls.fixturesdir}/config_files/server-valid.yml"
        with open(path) as f:
            conf = yaml.load(f, Loader=yaml.CSafeLoader)

        conf["hermes"]["cache"]["dirpath"] = cls.tmpdir.name
        return conf

    @classmethod
    def saveYaml(cls, content, path=None):
        if path is None:
            path = cls.conffile
        with open(path, "w") as yaml_file:
            yaml.dump(content, yaml_file, default_flow_style=False)

    @classmethod
    def saveYamlAndLoadConfig(cls, content, path=None) -> HermesConfig:
        cls.saveYaml(content, path)
        return HermesConfig()

    @classmethod
    def purgeTmpdirContent(cls):
        for filename in os.listdir(cls.tmpdir.name):
            filepath = os.path.join(cls.tmpdir.name, filename)
            try:
                shutil.rmtree(filepath)
            except OSError:
                os.remove(filepath)
