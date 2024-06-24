#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Hermes : Change Data Capture (CDC) tool from any source(s) to any target
# Copyright (C) 2024 INSA Strasbourg
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


# For debugging, it may be desirable to have access to logs and cache files.
# By default, these files are stored in a temporary folder, which is always
# deleted at the end of test execution.
# It is possible to store the files in a permanent folder, simply set its
# path in an env var HERMESFUNCTIONALTESTS_DEBUGTMPDIR

from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:  # pragma: no cover
    # Only for type hints, won't import at runtime
    from clients.errorqueue import ErrorQueue
    from lib.datamodel.dataobject import DataObject
    from lib.datamodel.dataobjectlist import DataObjectList


import json
import sqlite3
import unittest

import builtins
import os
import shutil
import sys
from tempfile import TemporaryDirectory
from datetime import datetime, timedelta
import time
import threading
import yaml

from lib.config import HermesConfig
from lib.utils.mail import Email
from plugins.clients.usersgroups_null.usersgroups_null import NullClient
from server.hermesserver import HermesServer


import logging


class NewPendingEmail(Exception):
    """Raised when a mail has been intercepted"""


class NullClientFixture:
    """Fixture of Hermes-client with error generation"""

    def on_Users_added(
        self, objkey: Any, eventattrs: "dict[str, Any]", newobj: "DataObject"
    ):
        if (
            hasattr(newobj, "middle_name")
            and type(newobj.middle_name) is str
            and "error" in newobj.middle_name
        ):
            if "error_on_second_step" in newobj.middle_name:
                self.currentStep = 1
            raise AssertionError(f"User {newobj} has error")

    def on_Users_modified(
        self,
        objkey: Any,
        eventattrs: "dict[str, Any]",
        newobj: "DataObject",
        cachedobj: "DataObject",
    ):
        if (
            hasattr(newobj, "middle_name")
            and type(newobj.middle_name) is str
            and "error" in newobj.middle_name
        ):
            if "error_on_second_step" in newobj.middle_name:
                self.currentStep = 1
            raise AssertionError(f"User {newobj} has error")

    def on_Users_removed(
        self, objkey: Any, eventattrs: "dict[str, Any]", cachedobj: "DataObject"
    ):
        if (
            hasattr(cachedobj, "middle_name")
            and type(cachedobj.middle_name) is str
            and "fail_on_remove" in cachedobj.middle_name
        ):
            if "fail_on_remove_second_step" in cachedobj.middle_name:
                self.currentStep = 1
            raise AssertionError(f"User {cachedobj} has error")

    def on_Groups_added(
        self, objkey: Any, eventattrs: "dict[str, Any]", newobj: "DataObject"
    ):
        if (
            hasattr(newobj, "name")
            and type(newobj.name) is str
            and "error" in newobj.name
        ):
            if "error_on_second_step" in newobj.name:
                self.currentStep = 1
            raise AssertionError(f"Group {newobj} has error")

    def on_Groups_modified(
        self,
        objkey: Any,
        eventattrs: "dict[str, Any]",
        newobj: "DataObject",
        cachedobj: "DataObject",
    ):
        if (
            hasattr(newobj, "name")
            and type(newobj.name) is str
            and "error" in newobj.name
        ):
            if "error_on_second_step" in newobj.name:
                self.currentStep = 1
            raise AssertionError(f"Group {newobj} has error")


class EmailFixture:
    """Fixture class to intercept emails that server or client could send"""

    emails: list["EmailFixture"] = []
    """Unread emails"""

    def __init__(self, subject: str, content: str) -> None:
        self.subject = subject
        self.content = content
        EmailFixture.emails.append(self)

    def __repr__(self) -> str:
        return f"Email({self.subject=})"

    def __str__(self) -> str:
        return f"Email({self.subject=}, {self.content=})"

    @staticmethod
    def send(
        config: HermesConfig,
        subject: str,
        content: str,
        attachments: list = [],
    ):
        EmailFixture(subject, content)

    @staticmethod
    def numberOfUnreadEmails() -> int:
        return len(EmailFixture.emails)

    @staticmethod
    def purgeUnreadEmails():
        EmailFixture.emails.clear()


class HermeClientThread:
    def __init__(self):
        self._thread: threading.Thread | None = None
        self._GenericClient__clientstatus = None
        self.logger: logging.Logger | None = None

    def run(self):
        """Dont call this method directly, use start_client instead !"""

        # Global logger setup
        appname = "hermes-client-functional-tests"
        __hermes__.appname = appname
        __hermes__.logger = logging.getLogger(appname)
        self.logger = __hermes__.logger

        # Client init
        orig_argv = sys.argv
        sys.argv = ["hermes", "client-usersgroups_null"]
        config = HermesConfig()

        self.client = NullClient(config)
        # Request client to process updates only on demand
        self.client._GenericClient__numberOfLoopToProcess = 0

        sys.argv = orig_argv

        self.client.mainLoop()

        # Remove all logger handlers to avoid duplicates if client is restarted
        self.logger = None
        while __hermes__.logger.hasHandlers():
            hdlr = __hermes__.logger.handlers[0]
            hdlr.flush()
            hdlr.close()
            __hermes__.logger.removeHandler(hdlr)

    @staticmethod
    def generate_config_file(conf_dict: dict[str, Any]):
        with open("hermes-client-usersgroups_null-config.yml", "w") as yaml_file:
            yaml.dump(conf_dict, yaml_file, default_flow_style=False, sort_keys=False)

    def start_client(self, conf_dict: dict[str, Any]):
        if self._thread and self._thread.is_alive():
            raise RuntimeError("Trying to start a client that is already running")

        self._thread = threading.Thread(target=self.run, name="hermes-client")
        self.__clientstatus = None
        self.generate_config_file(conf_dict)

        # Start client in another thread
        self._thread.start()
        while not hasattr(self, "client"):
            time.sleep(0.1)
        time.sleep(1)

    def stop_client(self):
        self.__clientstatus = None
        if not self._thread or not self._thread.is_alive():
            return
        self.client._GenericClient__isStopped = True
        self._thread.join()
        del self.client

    def restart_client(self, conf_dict: dict[str, Any]):
        self.stop_client()
        self.start_client(conf_dict)

    def update(self, numberOfLoopToProcess=1, ignoreEmails=False, timeout=10):
        if not self._thread or not self._thread.is_alive():
            raise RuntimeError("hermes-client is not running")
        EmailFixture.purgeUnreadEmails()
        self.__clientstatus = None
        self.client._GenericClient__numberOfLoopToProcess = numberOfLoopToProcess
        # Force trashbin purge, and errorqueue retry
        self.client._GenericClient__trashbin_lastpurge = datetime(
            year=1, month=1, day=1
        )
        self.client._GenericClient__errorQueue_lastretry = datetime(
            year=1, month=1, day=1
        )
        timeoutlimit = datetime.now() + timedelta(seconds=timeout)
        # Client will process its update.
        # A change of its lastupdate value will indicate it's done
        while self.client._GenericClient__numberOfLoopToProcess > 0:
            if datetime.now() > timeoutlimit:
                raise TimeoutError(
                    "hermes-client hasn't ended its update operation,"
                    " timeout delay was reached"
                )
            time.sleep(0.2)

        if not ignoreEmails and EmailFixture.numberOfUnreadEmails():
            raise NewPendingEmail(EmailFixture.numberOfUnreadEmails())

    def clientstatus(self, *args) -> dict:
        if self.__clientstatus is None:
            self.__clientstatus = self.client._GenericClient__status(verbose=True)

        if len(args) == 0:
            return self.__clientstatus

        res = self.__clientstatus
        for arg in args:
            res = res.get(arg, {})
        return res


class HermeServerThread:
    def __init__(self):
        self._thread = None
        self.__serverstatus = None
        self.logger: logging.Logger | None = None

    def run(self):
        """Dont call this method directly, use start_server instead !"""

        # Global logger setup
        appname = "hermes-server-functional-tests"
        __hermes__.appname = appname
        __hermes__.logger = logging.getLogger(appname)
        self.logger = __hermes__.logger

        # Server init
        orig_argv = sys.argv
        sys.argv = ["hermes", "server"]
        config = HermesConfig()

        self.server = HermesServer(config)
        # Request server to process updates only on demand
        self.server._numberOfLoopToProcess = 0

        sys.argv = orig_argv

        self.server.mainLoop()

        # Remove all logger handlers to avoid duplicates if server is restarted
        self.logger = None
        while __hermes__.logger.hasHandlers():
            hdlr = __hermes__.logger.handlers[0]
            hdlr.flush()
            hdlr.close()
            __hermes__.logger.removeHandler(hdlr)

    @staticmethod
    def generate_config_file(conf_dict: dict[str, Any]):
        with open("hermes-server-config.yml", "w") as yaml_file:
            yaml.dump(conf_dict, yaml_file, default_flow_style=False, sort_keys=False)

    def start_server(self, conf_dict: dict[str, Any]):
        if self._thread and self._thread.is_alive():
            raise RuntimeError("Trying to start a server that is already running")

        self._thread = threading.Thread(target=self.run, name="hermes-server")
        self.__serverstatus = None
        self.generate_config_file(conf_dict)

        # Start server in another thread
        self._thread.start()
        time.sleep(1)

    def stop_server(self):
        self.__serverstatus = None
        if not self._thread or not self._thread.is_alive():
            return
        self.server._isStopped = True
        self._thread.join()
        del self.server

    def restart_server(self, conf_dict: dict[str, Any]):
        self.stop_server()
        self.start_server(conf_dict)

    def update(self, numberOfLoopToProcess=1, ignoreEmails=False, timeout=10):
        if not self._thread or not self._thread.is_alive():
            raise RuntimeError("hermes-server is not running")
        EmailFixture.purgeUnreadEmails()
        self.__serverstatus = None
        self.server._numberOfLoopToProcess = numberOfLoopToProcess
        timeoutlimit = datetime.now() + timedelta(seconds=timeout)
        # Server will process its update.
        # A change of its lastupdate value will indicate it's done
        while self.server._numberOfLoopToProcess > 0:
            if datetime.now() > timeoutlimit:
                raise TimeoutError(
                    "hermes-server hasn't ended its update operation,"
                    " timeout delay was reached"
                )
            time.sleep(0.2)

        if not ignoreEmails and EmailFixture.numberOfUnreadEmails():
            raise NewPendingEmail(EmailFixture.numberOfUnreadEmails())

    def initSync(self):
        if not self._thread or not self._thread.is_alive():
            raise RuntimeError("hermes-server is not running")
        self.__serverstatus = None
        self.server._initSyncRequested = True
        # Server will process its initsync.
        # A change of its _initSyncRequested value will indicate it's done
        while self.server._initSyncRequested:
            time.sleep(0.2)

    def serverstatus(self, *args) -> dict:
        if self.__serverstatus is None:
            self.__serverstatus = self.server.status(verbose=True)

        if len(args) == 0:
            return self.__serverstatus

        res = self.__serverstatus
        for arg in args:
            res = res.get(arg, {})
        return res


class HermesIntegrationTestCase(unittest.TestCase):
    orig_cwd = os.getcwd()
    tmpdir: TemporaryDirectory | None = None
    databases_tables: dict[str, list[str]] = {
        "db_single": ["users_all", "groups", "groupmembers"],
        # Created to aggregate users_students + users_staff
        "db_aggregating_users_students_and_common": [
            "users_students",
            "groups",
            "groupmembers",
        ],
        "db_aggregating_users_staff": ["users_staff"],
        # Created to merge db_single.users_all with db_merging_biological.biologicaldata
        "db_merging_biological": ["biologicaldata"],
    }
    """Dict of databases names, and their tables list"""

    databases: dict[str, sqlite3.Connection] = {}
    """Dict of databases, with name as key, and the database connection as value"""

    fixtures: dict[str, list[dict[str, Any]]] = {}
    """Dict containing all fixtures"""

    fixturesdir = f"{os.path.realpath(os.path.dirname(__file__))}/fixtures"
    """Path of fixture directory"""

    def serverstatus(self, *args) -> dict:
        return self.serverthread.serverstatus(*args)

    def clientstatus(self, *args) -> dict:
        return self.clientthread.clientstatus(*args)

    @classmethod
    def createEmptyDatabases(cls):
        for dbname, dbtables in cls.databases_tables.items():
            dbpath = f"{dbname}.sqlite"
            if os.path.isfile(dbpath):
                os.remove(dbpath)

            cls.databases[dbname] = sqlite3.connect(database=dbpath)
            for tablename in [
                "users_all",
                "users_staff",
                "users_students",
            ]:
                if tablename not in dbtables:
                    continue
                sql = (
                    f"CREATE TABLE IF NOT EXISTS {tablename} ("
                    "  id                     TEXT PRIMARY KEY, "
                    "  simpleid               INTEGER UNIQUE NOT NULL, "
                    "  first_name             TEXT NOT NULL, "
                    "  middle_name            TEXT, "
                    "  last_name              TEXT NOT NULL, "
                    "  dateOfBirth            datetime, "
                    "  login                  TEXT UNIQUE NOT NULL, "
                    "  specialty              TEXT, "
                    "  desired_jobs_joined    TEXT, "
                    "  desired_job_1          TEXT, "
                    "  desired_job_2          TEXT, "
                    "  desired_job_3          TEXT, "
                    "  desired_job_4          TEXT, "
                    "  desired_job_5          TEXT, "
                    "  desired_job_6          TEXT, "
                    "  desired_job_7          TEXT, "
                    "  desired_job_8          TEXT, "
                    "  desired_job_9          TEXT"
                    ")"
                )
                cls.databases[dbname].execute(sql)

            if "groups" in dbtables:
                sql = (
                    "CREATE TABLE IF NOT EXISTS groups ("
                    "  id      TEXT PRIMARY KEY, "
                    "  name    TEXT UNIQUE NOT NULL, "
                    "  simpleid INTEGER UNIQUE NOT NULL "
                    ")"
                )
                cls.databases[dbname].execute(sql)

            if "groupmembers" in dbtables:
                sql = (
                    "CREATE TABLE IF NOT EXISTS groupmembers ("
                    "  group_id       TEXT, "
                    "  group_simpleid INTEGER, "
                    "  group_name     TEXT, "
                    "  user_id        TEXT, "
                    "  user_simpleid  INTEGER, "
                    "  user_login     TEXT"
                    ")"
                )
                cls.databases[dbname].execute(sql)

            if "biologicaldata" in dbtables:
                sql = (
                    "CREATE TABLE IF NOT EXISTS biologicaldata ("
                    "  user_id       TEXT UNIQUE NOT NULL, "
                    "  user_simpleid INTEGER UNIQUE NOT NULL, "
                    "  user_login    TEXT UNIQUE NOT NULL, "
                    "  hair_colour   TEXT, "
                    "  eye_colour    TEXT"
                    ")"
                )
                cls.databases[dbname].execute(sql)
            cls.databases[dbname].commit()

    @classmethod
    def loadFixtures(cls):
        cls.fixtures = {}
        for src in [
            "users_all",
            "users_staff",
            "users_students",
            "groups",
            "groupmembers",
            "biologicaldata",
        ]:
            with open(f"{cls.fixturesdir}/data/{src}.json") as f:
                content = "\n".join(f.readlines())
                cls.fixtures[src] = json.loads(content)

    @classmethod
    def insertEntry(cls, db: sqlite3.Connection, tablename: str, entry: dict[str, Any]):
        sql = (
            f"INSERT INTO {tablename}"
            f" ({', '.join(entry.keys())})"
            f" VALUES (:{', :'.join(entry.keys())})"
        )
        db.execute(sql, entry)
        db.commit()

    @classmethod
    def updateEntry(
        cls,
        db: sqlite3.Connection,
        tablename: str,
        idattrsname: list[str],
        entry: dict[str, Any],
    ):
        whereclause = " AND ".join([f"{idattr} = :{idattr}" for idattr in idattrsname])
        sql = (
            f"UPDATE {tablename}"
            f""" SET {', '.join(f"{k} = :{k}" for k in entry)}"""
            f" WHERE {whereclause}"
        )
        db.execute(sql, entry)
        db.commit()

    @classmethod
    def deleteEntry(
        cls,
        db: sqlite3.Connection,
        tablename: str,
        idattrsname: list[str],
        entry: dict[str, Any],
    ):
        whereclause = " AND ".join([f"{idattr} = :{idattr}" for idattr in idattrsname])
        sql = f"""DELETE FROM {tablename} WHERE {whereclause}"""
        db.execute(sql, entry)
        db.commit()

    @classmethod
    def setUpClass(cls):
        # Monkey patch Email.send() to intercept emails
        Email.send = EmailFixture.send

        # Monkey patch NullClient to generate some errors
        NullClient.on_Groups_added = NullClientFixture.on_Groups_added
        NullClient.on_Groups_modified = NullClientFixture.on_Groups_modified
        NullClient.on_Users_added = NullClientFixture.on_Users_added
        NullClient.on_Users_modified = NullClientFixture.on_Users_modified
        NullClient.on_Users_trashed = NullClientFixture.on_Users_removed
        NullClient.on_Users_removed = NullClientFixture.on_Users_removed

        # Create workdir
        if "HERMESFUNCTIONALTESTS_DEBUGTMPDIR" in os.environ:
            dirname = os.environ["HERMESFUNCTIONALTESTS_DEBUGTMPDIR"]
            if not os.path.exists(dirname):
                os.makedirs(dirname)
            else:
                cls.purgeDirContent(dirname)
        else:
            logging.disable(logging.CRITICAL)
            cls.tmpdir = TemporaryDirectory()
            dirname = cls.tmpdir.name

        os.chdir(dirname)
        for subdir in ["server-cache", "client-cache", "logs"]:
            os.mkdir(subdir)
        cls.loadFixtures()
        cls.createEmptyDatabases()
        cls.serverthread = HermeServerThread()
        cls._serverstatus = None
        cls.clientthread = HermeClientThread()
        cls._clientstatus = None

        # Global logger setup
        appname = "hermes-functional-tests"
        builtins.__hermes__ = threading.local()
        __hermes__.appname = appname
        __hermes__.logger = logging.getLogger(appname)

        # Serialization need to be setup by instanciating an HermesConfig,
        # even if it won't be used
        orig_argv = sys.argv
        sys.argv = ["hermes", "server"]
        HermeServerThread.generate_config_file(cls.loadYamlServer("single"))
        HermesConfig()
        sys.argv = orig_argv

    @classmethod
    def tearDownClass(cls):
        cls.serverthread.stop_server()
        cls.clientthread.stop_client()
        logging.disable(logging.NOTSET)
        os.chdir(cls.orig_cwd)
        if "HERMESFUNCTIONALTESTS_DEBUGTMPDIR" not in os.environ:
            cls.tmpdir.cleanup()

    @classmethod
    def loadYamlServer(cls, scenario_name: str) -> dict[str, Any]:
        scenarios = ["single", "merging", "aggregating"]
        with open(f"{cls.fixturesdir}/config_files/server.yml") as f:
            conf = yaml.load(f, Loader=yaml.CSafeLoader)

        # Minimize files if not ran for debug
        if "HERMESFUNCTIONALTESTS_DEBUGTMPDIR" not in os.environ:
            conf["hermes"]["cache"]["enable_compression"] = True
            conf["hermes"]["cache"]["backup_count"] = 0
            del conf["hermes"]["logs"]["logfile"]

        conf["hermes"]["plugins"]["datasources"] = conf["hermes"]["plugins"][
            f"datasources_{scenario_name}"
        ]
        conf["hermes-server"]["datamodel"] = conf["hermes-server"][
            f"datamodel_{scenario_name}"
        ]
        for scenario in scenarios:
            del conf["hermes"]["plugins"][f"datasources_{scenario}"]
            del conf["hermes-server"][f"datamodel_{scenario}"]

        return conf

    @classmethod
    def loadYamlClient(cls, scenario_name: str) -> dict[str, Any]:
        scenarios = ["single", "merging", "aggregating"]
        with open(f"{cls.fixturesdir}/config_files/client.yml") as f:
            conf = yaml.load(f, Loader=yaml.CSafeLoader)

        # Minimize files if not ran for debug
        if "HERMESFUNCTIONALTESTS_DEBUGTMPDIR" not in os.environ:
            conf["hermes"]["cache"]["enable_compression"] = True
            conf["hermes"]["cache"]["backup_count"] = 0
            del conf["hermes"]["logs"]["logfile"]

        conf["hermes-client"]["datamodel"] = conf["hermes-client"][
            f"datamodel_{scenario_name}"
        ]
        for scenario in scenarios:
            del conf["hermes-client"][f"datamodel_{scenario}"]

        return conf

    @classmethod
    def purgeDirContent(cls, dirpath):
        if not os.path.isdir(dirpath):
            return

        for filename in os.listdir(dirpath):
            filepath = os.path.join(dirpath, filename)
            try:
                shutil.rmtree(filepath)
            except OSError:
                os.remove(filepath)

    def log_current_test_name(self, test_name: str):
        NL = "\n"
        for logger in (self.serverthread.logger, self.clientthread.logger):
            if logger is not None:
                logger.info(
                    f"{NL}"
                    f"{NL}****{'*' * len(test_name)}"
                    f"{NL}* {test_name} *"
                    f"{NL}****{'*' * len(test_name)}"
                )

    @property
    def emails(self) -> list[EmailFixture]:
        return EmailFixture.emails

    def numberOfUnreadEmails(self) -> int:
        return EmailFixture.numberOfUnreadEmails()

    def serverdata(self, objtype: str) -> "DataObjectList":
        return self.serverthread.server.dm.data[objtype]

    def clientdata(self, objtype: str) -> "DataObjectList":
        return self.clientthread.client.getDataobjectlistFromCache(objtype)

    def clienterrorqueue(self) -> "ErrorQueue":
        return self.clientthread.client._GenericClient__datamodel.errorqueue

    def assertServerIntegrityfiltered(self, **kwargs: int):
        cachesrc = self._serverdataintegritylencache
        # Update cache values
        for arg, val in kwargs.items():
            if val is None:
                cachesrc[arg] = 0
            elif arg not in cachesrc:
                cachesrc[arg] = val
            else:
                cachesrc[arg] += val

        # Assert on each cache values, not only those specified in kwargs
        for arg, val in cachesrc.items():
            curval = len(self.serverstatus(arg, "warning", "integrityFiltered"))
            self.assertEqual(
                curval, val, msg=f"Expected that {arg} was {val}, but {arg}={curval}"
            )

    def assertClientdataLen(self, **kwargs: int | None):
        self.assertdataLen(self.clientdata, self._clientdatalencache, **kwargs)

    def assertServerdataLen(self, **kwargs: int | None):
        self.assertdataLen(self.serverdata, self._serverdatalencache, **kwargs)

    def assertdataLen(
        self,
        datasrc: Callable[[str], "DataObjectList"],
        cachesrc: dict[str : int | None],
        **kwargs: int | None,
    ):
        # Update cache values
        for arg, val in kwargs.items():
            if arg not in cachesrc or cachesrc[arg] is None or val is None:
                cachesrc[arg] = val
            else:
                cachesrc[arg] += val

        # Assert on each cache values, not only those specified in kwargs
        for arg, val in cachesrc.items():
            if val is None:
                try:
                    curval = len(datasrc(arg))
                except KeyError:
                    curval = None

                with self.assertRaises(
                    KeyError,
                    msg=(
                        f"Expected {arg} was missing, but it is present :"
                        f" {arg}={curval}"
                    ),
                ):
                    datasrc(arg)
                self.assertRaises(KeyError, datasrc, val)
            else:
                self.assertEqual(
                    len(datasrc(arg)),
                    val,
                    msg=f"Expected that {arg} was {val}, but {arg}={len(datasrc(arg))}",
                )
