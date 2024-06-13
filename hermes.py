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

import builtins
import importlib
import sys
import threading
import traceback
import logging
from os.path import basename

if __name__ == "__main__":
    # Allow the app context to be specified by script name or symlink name
    scriptname = basename(sys.argv[0])
    if scriptname.endswith(".py"):
        scriptname = scriptname[: -len(".py")]
    if scriptname.startswith("hermes-"):
        scriptname = scriptname[len("hermes-") :]

    if scriptname != "hermes":
        sys.argv.insert(1, scriptname)  # Hack to force context specified by scriptname

    if len(sys.argv) <= 1:
        config = HermesConfig()
        appname = config["appname"]
    else:
        appname = f"hermes-{sys.argv[1]}"

    # Global logger setup
    builtins.__hermes__ = threading.local()
    __hermes__.appname = appname
    __hermes__.logger = logging.getLogger(appname)

    try:
        #######
        # CLI #
        #######
        if (
            appname.startswith("hermes-")
            and appname.endswith("-cli")
            and len(appname) > len("hermes-") + len("-cli")
        ):
            from lib.utils.socket import (
                SockClient,
                SocketMessageToServer,
                SocketNotFoundError,
            )

            sys.argv[1] = appname[
                len("hermes-") : -len("-cli")
            ]  # Hack to force app context
            config = HermesConfig(autoload=False, allowMultipleInstances=True)
            config.load(loadplugins=False, dontManageCacheDir=True)

            if config["hermes"]["cli_socket"]["path"] is None:
                print(
                    f"CLI is disabled, as cli_socket.path is not set in {config['appname']} config",
                    file=sys.stderr,
                )
                sys.exit(1)

            msg = SocketMessageToServer(argv=sys.argv[2:])
            try:
                reply = SockClient.send(config["hermes"]["cli_socket"]["path"], msg)
            except SocketNotFoundError:
                print(
                    f"""Socket '{config["hermes"]["cli_socket"]["path"]}' not found. Maybe {config['appname']} isn't running or socket permissions are too restrictive""",
                    file=sys.stderr,
                )
                sys.exit(1)

            if reply.retmsg:
                if reply.retcode == 0:
                    print(reply.retmsg)
                else:
                    print(reply.retmsg, file=sys.stderr)

            sys.exit(reply.retcode)

        ##########
        # SERVER #
        ##########
        elif appname == "hermes-server":
            from server.hermesserver import HermesServer

            config = HermesConfig()
            srv = HermesServer(config)
            srv.mainLoop()

        ##########
        # CLIENT #
        ##########
        elif appname.startswith("hermes-client-"):
            clientname = appname[len("hermes-client-") :]
            try:
                module = importlib.import_module(
                    f"plugins.clients.{clientname}.{clientname}"
                )
            except ModuleNotFoundError:
                __hermes__.logger.critical(
                    f"""Specified client '{clientname}' doesn't exist"""
                )
                sys.exit(2)

            config = HermesConfig()
            client = getattr(module, module.HERMES_PLUGIN_CLASSNAME)(config)
            client.mainLoop()

    except Exception as e:
        lines = traceback.format_exception(type(e), e, e.__traceback__)
        trace = "".join(lines).strip()

        __hermes__.logger.critical(f"Unhandled exception: {trace}")
        sys.exit(1)

    sys.exit(0)
