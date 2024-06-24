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

from lib.config import HermesConfig

from email.message import EmailMessage
from dataclasses import dataclass
import difflib
import gzip
import smtplib


@dataclass
class Attachment:
    filename: str
    mimetype: str
    content: bytes

    def __len__(self) -> int:
        return len(self.content)

    @property
    def maintype(self) -> str:
        return self.mimetype.split("/", 1)[0]

    @property
    def subtype(self) -> str:
        return self.mimetype.split("/", 1)[1]


class Email:
    """Helper class to send mails"""

    @staticmethod
    def send(
        config: HermesConfig,
        subject: str,
        content: str,
        attachments: list[Attachment] = [],
    ):
        """Send a mail with specified subject and content, using "server",
        "from" and "to" set in specified config.
        Can attach files from 'attachments' list"""
        try:
            server = config["hermes"]["mail"]["server"]
            mailfrom = config["hermes"]["mail"]["from"]
            mailto = config["hermes"]["mail"]["to"]

            # Create a text/plain message
            msg = EmailMessage()
            msg.set_content(content)

            msg["Subject"] = subject
            msg["From"] = mailfrom
            msg["To"] = mailto

            for attachment in attachments:
                msg.add_attachment(
                    attachment.content,
                    maintype=attachment.maintype,
                    subtype=attachment.subtype,
                    filename=attachment.filename,
                )

            s = smtplib.SMTP(server)
            s.send_message(msg)
            s.quit()
        except Exception as e:
            __hermes__.logger.warning(f"Fail to send mail {subject=}: {str(e)}")

    @staticmethod
    def sendDiff(
        config: HermesConfig,
        contentdesc: str,
        previous: str,
        current: str,
    ):
        """Send a mail with a diff between two strings.

        'contentdesc': string (first letter should be lowercase) that will be used
                        in mail subject, and as prefix of mail content
        'previous': previous data used to compute diff
        'current': current data used to compute diff
        """
        nl = "\n"

        d = difflib.unified_diff(
            previous.splitlines(keepends=True),
            current.splitlines(keepends=True),
            "previous.txt",
            "current.txt",
            n=0,
        )
        diff = "".join(d)

        # Convert string to bytes
        previous = "".join(previous).encode()
        current = "".join(current).encode()
        difffile = diff.encode()

        if config["hermes"]["mail"]["compress_attachments"]:
            mimetype = "application/gzip"
            ext = ".txt.gz"
            compress = gzip.compress
        else:
            mimetype = "text/plain"
            ext = ".txt"
            compress = Email._dontCompress  # Keep data as is

        tmpattachments = [
            Attachment(f"previous{ext}", mimetype, compress(previous)),
            Attachment(f"current{ext}", mimetype, compress(current)),
            Attachment(f"diff{ext}", mimetype, compress(difffile)),
        ]

        # Ensure attachments doesn't exceed attachment_maxsize
        attachments = []
        toobig = []
        errmsg = ""
        for a in tmpattachments:
            if len(a) <= config["hermes"]["mail"]["attachment_maxsize"]:
                attachments.append(a)
            else:
                toobig.append(a.filename)

        if toobig:
            errmsg = (
                f"Some files were too big to be attached to mail: {toobig}.{nl}{nl}"
            )

        if len(diff.encode()) < config["hermes"]["mail"]["mailtext_maxsize"]:
            content = f"{errmsg}{contentdesc.capitalize()}. Diff is:{nl}{nl}{diff}"
        else:
            content = (
                f"{errmsg}{contentdesc.capitalize()}. "
                "Diff is too big to be displayed in mail content, "
                "please see attachments or log files."
            )

        Email.send(
            config=config,
            subject=f"[{config['appname']}] {contentdesc}",
            content=content,
            attachments=attachments,
        )

    @staticmethod
    def _dontCompress(data: Any) -> Any:
        return data
