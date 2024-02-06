#!/usr/bin/python3
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


from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    # Only for type hints, won't import at runtime
    from lib.config import HermesConfig

import sys
import logging
from logging.handlers import TimedRotatingFileHandler


def setup_logger(config: "HermesConfig"):
    """Setup logging for the whole app"""

    loglevels = {
        "critical": logging.CRITICAL,
        "error": logging.ERROR,
        "warning": logging.WARNING,
        "info": logging.INFO,
        "debug": logging.DEBUG,
    }

    __hermes__.logger.setLevel(loglevels[config["hermes"]["logs"]["verbosity"]])

    log_format = logging.Formatter(
        "%(levelname)s:%(asctime)s:%(filename)s:%(lineno)d:%(funcName)s():%(message)s"
    )

    # stderr output (always except when executing unit tests)
    if "unittest" not in sys.modules:  # pragma: no cover
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(log_format)
        stream_handler.setLevel(loglevels[config["hermes"]["logs"]["verbosity"]])
        __hermes__.logger.addHandler(stream_handler)

    # log file output when set up
    if config["hermes"]["logs"]["logfile"] is not None:
        file_handler = TimedRotatingFileHandler(
            config["hermes"]["logs"]["logfile"],
            when="midnight",
            backupCount=config["hermes"]["logs"]["backup_count"],
        )
        file_handler.setFormatter(log_format)
        file_handler.setLevel(loglevels[config["hermes"]["logs"]["verbosity"]])
        __hermes__.logger.addHandler(file_handler)
