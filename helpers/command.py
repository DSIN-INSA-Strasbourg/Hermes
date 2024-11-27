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

import subprocess
import sys


class CommandFailed(Exception):
    def __init__(self, cmdlist: list[str], retcode: int, stdout: str, stderr: str):
        super().__init__(f"Command {cmdlist} failed ({retcode=})")
        self.retcode = retcode
        self.stdout = stdout
        self.stderr = stderr


class Command:
    """Helper class to run local commands"""

    DEVNULL = subprocess.DEVNULL
    TOVAR = subprocess.PIPE
    FROMVAR = subprocess.PIPE
    SYSDEFAULT = None

    @staticmethod
    def run(
        cmd: list[str],
        stdout: int = TOVAR,
        stderr: int = TOVAR,
        stdin: int = DEVNULL,
        stdincontent: str = "",
        failOnRetcode: bool = True,
        failOnStderr: bool = False,
        failOnStdout: bool = False,
    ) -> tuple[int, str, str]:
        """Run specified external command
            - cmd: list containing command to run and it optional args
            - stdout: can take one of those values:
                - Command.TOVAR: return stdout in the method return variables
                - Command.SYSDEFAULT: use current stdout value
                - Command.DEVNULL: ignore stdout
            - stderr: can take one of those values:
                - Command.TOVAR: return stderr in the method return variables
                - Command.SYSDEFAULT: use current stderr value
                - Command.DEVNULL: ignore stderr
            - stdin: can take one of those values:
                - Command.SYSDEFAULT: use current stdin value
                - Command.DEVNULL: ignore stdin
                - Command.FROMVAR: use content specified in stdincontent argument
            - stdincontent: content to use for stdin, if argument stdin is
              Command.FROMVAR. Ignored otherwise
        The command will be considered as failed and raise a CommandFailed exception
        according to enabled "fail" args :
            - failOnRetcode: failed if retcode is not 0
            - failOnStderr: failed if stderr content is not empty
            - failOnStdout: failed if stdout content is not empty

        returns a tuple: (command exit code, stdout, stderr)
        """
        outputencoding = sys.stdout.encoding

        try:
            (out, err) = ("", "")
            p = subprocess.Popen(cmd, stdout=stdout, stderr=stderr, stdin=stdin)
            retcode = None
            while retcode is None:
                if stdin == Command.FROMVAR:
                    bstdincontent = stdincontent.encode("utf-8")
                    (o, e) = p.communicate(input=bstdincontent)
                else:
                    (o, e) = p.communicate()

                if stdout == Command.TOVAR:
                    out += o.decode(outputencoding)
                if stderr == Command.TOVAR:
                    err += e.decode(outputencoding)
                retcode = p.poll()
        except OSError as e:
            (retcode, out, err) = (-9999999, "", str(e))

        if (
            (failOnRetcode and retcode != 0)
            or (failOnStderr and err != "")
            or (failOnStdout and out != "")
        ):
            raise CommandFailed(cmd, retcode, out, err)

        return (retcode, out, err)
