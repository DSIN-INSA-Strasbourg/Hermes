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

from typing import Any

from copy import deepcopy
from datetime import datetime

from .hermesintegrationtestcase import (
    HermesIntegrationTestCase,
    EmailFixture,
    NewPendingEmail,
)


import inspect


def myself() -> str:
    return inspect.stack()[1][3]


class TestScenarioSingle(HermesIntegrationTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls._serverdataintegritylencache: dict[str, int] = {}
        cls._serverdatalencache: dict[str, int | None] = {}
        cls._clientdatalencache: dict[str, int | None] = {}

        # *** DB ***
        # Fill db_single with all data except 10 first users
        dbname = "db_single"
        db = cls.databases[dbname]
        for tablename, entries in deepcopy(cls.fixtures).items():
            # Force some users to generate errors (storres and kturner)
            if tablename in ("users_all",):

                def errusers(d: dict[str, Any]):
                    return d["login"] in ["storres", "kturner"]

                for entry in filter(errusers, entries):
                    entry["middle_name"] = "error"

            # Force some users to generate partially processed event errors (twagner)
            if tablename in ("users_all",):

                def errusers(d: dict[str, Any]):
                    return d["login"] in ["twagner"]

                for entry in filter(errusers, entries):
                    entry["middle_name"] = "error_on_second_step"

            # Force some groups to generate errors (marine_engineering and energy)
            if tablename == "groups":

                def errgroups(d: dict[str, Any]):
                    return d["name"] in [
                        "marine_engineering",
                        "energy",
                    ]

                for entry in filter(errgroups, entries):
                    entry["name"] = f'{entry["name"]}_error'

            if tablename not in cls.databases_tables[dbname]:
                continue
            if tablename == "users_all":
                filtered_entries = entries[10:]
            else:
                filtered_entries = entries
            for entry in filtered_entries:
                cls.insertEntry(db, tablename, entry)

        # *** SERVER ***
        conf = cls.loadYamlServer("single")
        cls.serverthread.start_server(conf)
        cls.serverthread.update()
        cls.serverthread.initSync()

        # *** CLIENT ***
        conf = cls.loadYamlClient("single")
        cls.clientthread.start_client(conf)

    #######################
    # Standard operations #
    #######################

    def test_001a_server_first_state(self):
        self.log_current_test_name(myself())
        self.assertServerdataLen(SRVUsers=290, SRVGroups=31, SRVGroupsMembers=840)
        self.assertServerIntegrityfiltered(SRVUsers=0, SRVGroups=0, SRVGroupsMembers=28)

    def test_001b_client_first_state(self):
        self.log_current_test_name(myself())
        self.assertRaises(NewPendingEmail, self.clientthread.update)
        self.assertEqual(EmailFixture.numberOfUnreadEmails(), 1)
        self.assertEqual(
            EmailFixture.emails[0].subject,
            "[hermes-client-usersgroups_null] objects in error queue have changed",
        )
        self.assertClientdataLen(Users=287, Groups=29, GroupsMembers=840)

        diff = self.clientdata("Users").diffFrom(self.serverdata("SRVUsers"))
        self.assertEqual(len(diff.dict["added"]), 0)
        self.assertEqual(len(diff.dict["modified"]), 287)  # Local _pkey attribute
        self.assertEqual(len(diff.dict["removed"]), 3)  # 3 users in error

    def test_002a_server_insert_missing_users(self):
        self.log_current_test_name(myself())
        for entry in self.fixtures["users_all"][:10]:
            self.insertEntry(self.databases["db_single"], "users_all", entry)
        self.serverthread.update()

        self.assertServerdataLen(SRVUsers=+10, SRVGroupsMembers=+28)
        self.assertServerIntegrityfiltered(SRVGroupsMembers=-28)

    def test_002b_client_insert_missing_users(self):
        self.log_current_test_name(myself())
        self.clientthread.update()
        self.assertClientdataLen(Users=+10, GroupsMembers=+28)

        diff = self.clientdata("Users").diffFrom(self.serverdata("SRVUsers"))
        self.assertEqual(len(diff.dict["added"]), 0)
        self.assertEqual(len(diff.dict["modified"]), 297)  # Local _pkey attribute
        self.assertEqual(len(diff.dict["removed"]), 3)  # 3 users in error

    def test_003a_server_trashbin_user(self):
        self.log_current_test_name(myself())
        # Remove tmays and store it in trashbin
        uid = "a42d0cd7-fd35-4f6a-b450-388748d90846"
        self.deleteEntry(self.databases["db_single"], "users_all", ["id"], {"id": uid})
        self.serverthread.update()

        self.assertServerdataLen(SRVUsers=-1, SRVGroupsMembers=-3)
        self.assertServerIntegrityfiltered(SRVGroupsMembers=+3)

    def test_003b_client_trashbin_user(self):
        self.log_current_test_name(myself())
        self.clientthread.update()
        self.assertClientdataLen()

    def test_004a_validate_desired_jobs(self):
        self.log_current_test_name(myself())
        # Test on aharris
        uid = "e00da49d-effa-4002-b040-413c4690fb15"
        contexts = {
            "hermes-server": self.serverdata("SRVUsers")[uid],
            "hermes-client": self.clientdata("Users")[uid],
        }
        desjobs = [
            "Armed forces operational officer",
            "Operational investment banker",
            "Print production planner",
        ]
        for context, user in contexts.items():
            with self.subTest(f"Validate attributes 'desired_jobs' of {context}"):
                self.assertListEqual(user.desired_jobs_joined, desjobs)
                self.assertListEqual(user.desired_jobs_columns, desjobs)

    def test_004b_validate_attributes_present(self):
        self.log_current_test_name(myself())
        # Test on aharris
        uid = "e00da49d-effa-4002-b040-413c4690fb15"
        contexts = {
            "hermes-server": self.serverdata("SRVUsers")[uid],
            "hermes-client": self.clientdata("Users")[uid],
        }

        presentAttributes = [
            "first_name",
            "last_name",
            "dateOfBirth",
            "login",
            "specialty",
            "desired_jobs_joined",
            "desired_jobs_columns",
        ]

        missingAttributes = [
            "middle_name",
        ]

        for context, user in contexts.items():
            with self.subTest(f"Validate attributes of {context}"):
                # Present attributes
                for attr in presentAttributes:
                    self.assertTrue(
                        hasattr(user, attr),
                        f"aharris's attribute '{attr}' is missing from {context} but"
                        " should be present",
                    )
                # Missing attributes
                for attr in missingAttributes:
                    self.assertFalse(
                        hasattr(user, attr),
                        f"aharris's attribute '{attr}' is present on {context} but"
                        " should be missing",
                    )

    def test_004c_validate_attributes_types(self):
        self.log_current_test_name(myself())
        # Test on aharris
        uid = "e00da49d-effa-4002-b040-413c4690fb15"
        contexts = {
            "hermes-server": self.serverdata("SRVUsers")[uid],
            "hermes-client": self.clientdata("Users")[uid],
        }

        attributes = {
            "first_name": str,
            "last_name": str,
            "dateOfBirth": datetime,
            "login": str,
            "specialty": str,
            "desired_jobs_joined": list,
            "desired_jobs_columns": list,
        }

        for context, user in contexts.items():
            with self.subTest(f"Validate attributes types of {context}"):
                for attr, expectedType in attributes.items():
                    currentType = type(getattr(user, attr))
                    self.assertEqual(
                        expectedType,
                        currentType,
                        f"aharris's attribute '{attr}' has unexpected type on"
                        f" {context}. {currentType=} {expectedType=}",
                    )

    def test_005_update_values(self):
        self.log_current_test_name(myself())
        # Test on jvang and mpatel
        jvanguid = "5fbbf0b1-8083-49c8-a57e-01c90da23e5c"
        jvang = {
            "id": jvanguid,
            "middle_name": "Jack",  # Add middle name
            "dateOfBirth": "1965-01-13T12:34:56",  # Modify time
            "desired_jobs_joined": "Arboriculturist",  # Remove Copywriter, advertising
            "desired_job_1": None,  # Remove Copywriter, advertising
        }
        expectedjvang = deepcopy(self.serverdata("SRVUsers")[jvanguid].toNative())
        expectedjvang["middle_name"] = "Jack"
        expectedjvang["dateOfBirth"] = datetime(1965, 1, 13, 12, 34, 56)
        expectedjvang["desired_jobs_joined"].remove("Copywriter, advertising")
        expectedjvang["desired_jobs_columns"].remove("Copywriter, advertising")

        mpateluid = "97fe56c5-4c9a-4f24-97b4-c294bd44089d"
        mpatel = {
            "id": mpateluid,
            "middle_name": "Paula",  # Add middle name
            "desired_jobs_joined": (
                "Pension scheme manager;Geneticist, molecular;Microbiologist"
            ),  # Add new desired_jobs
            "desired_job_2": "Geneticist, molecular",  # Add desired_job
            "desired_job_9": "Microbiologist",  # Add desired_job
        }
        expectedmpatel = deepcopy(self.serverdata("SRVUsers")[mpateluid].toNative())
        expectedmpatel["middle_name"] = "Paula"
        expectedmpatel["desired_jobs_joined"] = [
            "Pension scheme manager",
            "Geneticist, molecular",
            "Microbiologist",
        ]
        expectedmpatel["desired_jobs_columns"] = [
            "Pension scheme manager",
            "Geneticist, molecular",
            "Microbiologist",
        ]

        # Server
        self.updateEntry(self.databases["db_single"], "users_all", ["id"], jvang)
        self.updateEntry(self.databases["db_single"], "users_all", ["id"], mpatel)
        self.serverthread.update()

        self.assertServerdataLen()
        self.assertServerIntegrityfiltered()

        self.assertDictEqual(
            expectedjvang, self.serverdata("SRVUsers")[jvanguid].toNative()
        )
        self.assertDictEqual(
            expectedmpatel, self.serverdata("SRVUsers")[mpateluid].toNative()
        )

        # Client
        self.clientthread.update()
        self.assertClientdataLen()

        self.maxDiff = None

        expectedjvang["_pkey_id"] = jvanguid
        del expectedjvang["id"]
        del expectedjvang["simpleid"]
        self.assertDictEqual(
            expectedjvang, self.clientdata("Users")[jvanguid].toNative()
        )
        expectedmpatel["_pkey_id"] = mpateluid
        del expectedmpatel["id"]
        del expectedmpatel["simpleid"]
        self.assertDictEqual(
            expectedmpatel, self.clientdata("Users")[mpateluid].toNative()
        )

    ###########################################
    # Datamodel update : add/remove of types  #
    ###########################################

    def test_101a_server_datamodel_servertype_removal(self):
        self.log_current_test_name(myself())
        conf = self.loadYamlServer("single")
        del conf["hermes-server"]["datamodel"]["SRVGroupsMembers"]

        self.serverthread.restart_server(conf)
        self.serverthread.update()

        self.assertServerdataLen(SRVGroupsMembers=None)
        self.assertServerIntegrityfiltered(SRVGroupsMembers=None)

    def test_101b_client_datamodel_servertype_removal(self):
        self.log_current_test_name(myself())
        self.assertRaises(NewPendingEmail, self.clientthread.update)
        self.assertEqual(EmailFixture.numberOfUnreadEmails(), 1)
        self.assertEqual(
            EmailFixture.emails[0].subject,
            "[hermes-client-usersgroups_null] datamodel warnings have changed",
        )

        self.assertClientdataLen(GroupsMembers=None)

    def test_102a_server_datamodel_servertype_add(self):
        self.log_current_test_name(myself())
        # Restore conf["hermes-server"]["datamodel"]["SRVGroupsMembers"]
        conf = self.loadYamlServer("single")
        self.serverthread.restart_server(conf)
        self.serverthread.update()

        self.assertServerdataLen(SRVGroupsMembers=865)
        self.assertServerIntegrityfiltered(SRVGroupsMembers=3)

    def test_102b_client_datamodel_servertype_add(self):
        self.log_current_test_name(myself())
        self.assertRaises(NewPendingEmail, self.clientthread.update)
        self.assertEqual(EmailFixture.numberOfUnreadEmails(), 1)
        self.assertEqual(
            EmailFixture.emails[0].subject,
            "[hermes-client-usersgroups_null] no more datamodel warnings",
        )
        self.assertClientdataLen(GroupsMembers=868)

    def test_103a_client_datamodel_clienttype_removal(self):
        self.log_current_test_name(myself())
        conf = self.loadYamlClient("single")
        del conf["hermes-client"]["datamodel"]["GroupsMembers"]
        self.clientthread.restart_client(conf)
        self.clientthread.update()
        self.assertClientdataLen(GroupsMembers=None)

    def test_103b_server_datamodel_clienttype_removal(self):
        self.log_current_test_name(myself())
        # Remove lblair from year_3 group
        gm = {
            "group_id": "7324ae9f-2338-37e7-b640-b782813cb162",  # year_3
            "user_id": "43b7a3a6-9a8d-4a03-980d-7b71d8f56413",  # lblair
        }

        self.deleteEntry(
            self.databases["db_single"], "groupmembers", ["group_id", "user_id"], gm
        )
        self.serverthread.update()

        self.assertServerdataLen(SRVGroupsMembers=-1)
        self.assertServerIntegrityfiltered()

        # Update client, nothing should have changed
        self.clientthread.update()
        self.assertClientdataLen()

    def test_104a_client_datamodel_clienttype_add_from_cache(self):
        self.log_current_test_name(myself())
        # Restore conf["hermes-client"]["datamodel"]["GroupsMembers"]
        conf = self.loadYamlClient("single")

        self.clientthread.restart_client(conf)
        self.clientthread.update()
        # GroupsMembers is 1001, as lblair's membership objects in trashbin are counted,
        # but tmays's aren't anymore since SRVGroupMembers deletion on server
        self.assertClientdataLen(GroupsMembers=865)

    def test_105a_restore_data(self):
        self.log_current_test_name(myself())
        # Restore lblair to year_3 group
        entry = self.fixtures["groupmembers"][10]

        # Ensure we use the expected entry
        self.assertEqual(entry["group_id"], "7324ae9f-2338-37e7-b640-b782813cb162")
        self.assertEqual(entry["user_id"], "43b7a3a6-9a8d-4a03-980d-7b71d8f56413")

        self.insertEntry(self.databases["db_single"], "groupmembers", entry)

        self.serverthread.update()

        # Server consistency
        self.assertServerdataLen(SRVGroupsMembers=+1)
        self.assertServerIntegrityfiltered()

        # Client consistency
        self.clientthread.update()
        self.assertClientdataLen()

    #######################################################
    # Datamodel update : add/update/remove of attributes  #
    #######################################################

    def test_201a_client_datamodel_add_attribute(self):
        self.log_current_test_name(myself())
        # Add a new attr "login_uppercase" to each user, not declared in server
        # datamodel.
        # Restore conf["hermes-client"]["datamodel"]["GroupsMembers"]
        conf = self.loadYamlClient("single")
        conf["hermes-client"]["datamodel"]["Users"]["attrsmapping"][
            "login_uppercase"
        ] = "login_uppercase"
        self.clientthread.restart_client(conf)

        self.assertRaises(NewPendingEmail, self.clientthread.update)
        self.assertEqual(EmailFixture.numberOfUnreadEmails(), 1)
        self.assertEqual(
            EmailFixture.emails[0].subject,
            "[hermes-client-usersgroups_null] datamodel warnings have changed",
        )
        self.assertClientdataLen()

    def test_201b_server_datamodel_add_attribute(self):
        self.log_current_test_name(myself())
        conf = self.loadYamlServer("single")
        # Add a new attr "login_uppercase" to each user
        conf["hermes-server"]["datamodel"]["SRVUsers"]["sources"]["db_single"][
            "attrsmapping"
        ]["login_uppercase"] = "{{ login | upper }}"
        self.serverthread.restart_server(conf)
        self.serverthread.update()

        # Server consistency
        self.assertServerdataLen()
        self.assertServerIntegrityfiltered()

        # Verify attribute content
        for user in self.serverdata("SRVUsers"):
            self.assertNotEqual(user.login, user.login_uppercase)
            self.assertEqual(user.login.upper(), user.login_uppercase)

    def test_201c_client_datamodel_add_attribute(self):
        self.log_current_test_name(myself())
        # Fetch new attr "login_uppercase" values, as now declared in server datamodel
        self.assertRaises(NewPendingEmail, self.clientthread.update)
        self.assertEqual(EmailFixture.numberOfUnreadEmails(), 1)
        self.assertEqual(
            EmailFixture.emails[0].subject,
            "[hermes-client-usersgroups_null] no more datamodel warnings",
        )
        self.assertClientdataLen()

        # Verify attribute content
        for user in self.clientdata("Users"):
            if hasattr(user, "_trashbin_timestamp"):
                # Ignore users in trashbin as they don't have the new attribute
                continue
            self.assertNotEqual(user.login, user.login_uppercase)
            self.assertEqual(user.login.upper(), user.login_uppercase)

    def test_202a_client_datamodel_modify_attribute_to_filter(self):
        self.log_current_test_name(myself())
        # Modify attr "login_uppercase" to a jinja filter
        conf = self.loadYamlClient("single")
        conf["hermes-client"]["datamodel"]["Users"]["attrsmapping"][
            "login_uppercase"
        ] = "{{ login_uppercase | capitalize }}"
        self.clientthread.restart_client(conf)
        # The attribute will change in error queue too, so a change notification will
        # be sent
        self.assertRaises(NewPendingEmail, self.clientthread.update)
        self.assertEqual(EmailFixture.numberOfUnreadEmails(), 1)
        self.assertEqual(
            EmailFixture.emails[0].subject,
            "[hermes-client-usersgroups_null] objects in error queue have changed",
        )
        self.assertClientdataLen()

        # Verify attribute content
        for user in self.clientdata("Users"):
            if hasattr(user, "_trashbin_timestamp"):
                # Ignore users in trashbin as they don't have the new attribute
                continue
            self.assertEqual(user.login.capitalize(), user.login_uppercase)

    def test_203a_client_datamodel_modify_attribute(self):
        self.log_current_test_name(myself())
        # Modify attr "login_uppercase" to another attribute
        conf = self.loadYamlClient("single")
        conf["hermes-client"]["datamodel"]["Users"]["attrsmapping"][
            "login_uppercase"
        ] = "login"
        self.clientthread.restart_client(conf)
        # The attribute will change in error queue too, so a change notification will
        # be sent
        self.assertRaises(NewPendingEmail, self.clientthread.update)
        self.assertEqual(EmailFixture.numberOfUnreadEmails(), 1)
        self.assertEqual(
            EmailFixture.emails[0].subject,
            "[hermes-client-usersgroups_null] objects in error queue have changed",
        )
        self.assertClientdataLen()

        # Verify attribute content
        for user in self.clientdata("Users"):
            if hasattr(user, "_trashbin_timestamp"):
                # Ignore users in trashbin as they don't have the new attribute
                continue
            self.assertEqual(user.login, user.login_uppercase)

    def test_204a_client_datamodel_restore_login_uppercase_attribute(self):
        self.log_current_test_name(myself())
        # Restore attr "login_uppercase" to server "login_uppercase"
        conf = self.loadYamlClient("single")
        conf["hermes-client"]["datamodel"]["Users"]["attrsmapping"][
            "login_uppercase"
        ] = "login_uppercase"
        self.clientthread.restart_client(conf)
        # The attribute will change in error queue too, so a change notification will
        # be sent
        self.assertRaises(NewPendingEmail, self.clientthread.update)
        self.assertEqual(EmailFixture.numberOfUnreadEmails(), 1)
        self.assertEqual(
            EmailFixture.emails[0].subject,
            "[hermes-client-usersgroups_null] objects in error queue have changed",
        )
        self.assertClientdataLen()

        # Verify attribute content
        for user in self.clientdata("Users"):
            if hasattr(user, "_trashbin_timestamp"):
                # Ignore users in trashbin as they don't have the new attribute
                continue
            self.assertNotEqual(user.login, user.login_uppercase)
            self.assertEqual(user.login.upper(), user.login_uppercase)

    def test_205a_server_datamodel_modify_attribute_filter(self):
        self.log_current_test_name(myself())
        conf = self.loadYamlServer("single")
        # Add a new attr "login_uppercase" to each user
        conf["hermes-server"]["datamodel"]["SRVUsers"]["sources"]["db_single"][
            "attrsmapping"
        ]["login_uppercase"] = "{{ login | capitalize }}"
        self.serverthread.restart_server(conf)
        self.serverthread.update()

        # Server consistency
        self.assertServerdataLen()
        self.assertServerIntegrityfiltered()

        # Verify attribute content
        for user in self.serverdata("SRVUsers"):
            self.assertNotEqual(user.login, user.login_uppercase)
            self.assertEqual(user.login.capitalize(), user.login_uppercase)

    def test_205b_client_datamodel_server_modified_attribute_filter(self):
        self.log_current_test_name(myself())
        self.clientthread.update()
        self.assertClientdataLen()

        # Verify attribute content
        for user in self.clientdata("Users"):
            if hasattr(user, "_trashbin_timestamp"):
                # Ignore users in trashbin as they don't have the new attribute
                continue
            self.assertEqual(user.login.capitalize(), user.login_uppercase)

    def test_206a_client_datamodel_remove_attribute(self):
        self.log_current_test_name(myself())
        # Remove attr "login_uppercase"
        conf = self.loadYamlClient("single")
        self.clientthread.restart_client(conf)
        # The attribute will be removed in error queue too, so a change notification
        # will be sent
        self.assertRaises(NewPendingEmail, self.clientthread.update)
        self.assertEqual(EmailFixture.numberOfUnreadEmails(), 1)
        self.assertEqual(
            EmailFixture.emails[0].subject,
            "[hermes-client-usersgroups_null] objects in error queue have changed",
        )
        self.assertClientdataLen()

        # Verify attribute content
        for user in self.clientdata("Users"):
            if hasattr(user, "_trashbin_timestamp"):
                # Ignore users in trashbin as they don't have the new attribute
                continue
            self.assertFalse(hasattr(user, "login_uppercase"))

    def test_207a_server_datamodel_modify_attribute(self):
        self.log_current_test_name(myself())
        conf = self.loadYamlServer("single")
        # Modify attr "login_uppercase" to contain first_name
        conf["hermes-server"]["datamodel"]["SRVUsers"]["sources"]["db_single"][
            "attrsmapping"
        ]["login_uppercase"] = "first_name"
        self.serverthread.restart_server(conf)
        self.serverthread.update()

        # Server consistency
        self.assertServerdataLen()
        self.assertServerIntegrityfiltered()

        # Verify attribute content
        for user in self.serverdata("SRVUsers"):
            self.assertEqual(user.first_name, user.login_uppercase)

    def test_208a_client_datamodel_no_change(self):
        self.log_current_test_name(myself())
        self.loadYamlClient("single")
        self.clientthread.update()
        self.assertClientdataLen()

        # Verify that attribute still doesn't exist
        for user in self.clientdata("Users"):
            if hasattr(user, "_trashbin_timestamp"):
                # Ignore users in trashbin as they don't have the new attribute
                continue
            self.assertFalse(hasattr(user, "login_uppercase"))

    def test_209a_client_datamodel_restore_attribute(self):
        self.log_current_test_name(myself())
        # Restore attr "login_uppercase"
        conf = self.loadYamlClient("single")
        conf["hermes-client"]["datamodel"]["Users"]["attrsmapping"][
            "login_uppercase"
        ] = "login_uppercase"
        self.clientthread.restart_client(conf)
        # The attribute will change in error queue too, so a change notification will
        # be sent
        self.assertRaises(NewPendingEmail, self.clientthread.update)
        self.assertEqual(EmailFixture.numberOfUnreadEmails(), 1)
        self.assertEqual(
            EmailFixture.emails[0].subject,
            "[hermes-client-usersgroups_null] objects in error queue have changed",
        )
        self.assertClientdataLen()

        # Verify attribute content
        for user in self.clientdata("Users"):
            if hasattr(user, "_trashbin_timestamp"):
                # Ignore users in trashbin as they don't have the new attribute
                continue
            self.assertEqual(user.first_name, user.login_uppercase)

    def test_210a_server_datamodel_remove_attribute(self):
        self.log_current_test_name(myself())
        conf = self.loadYamlServer("single")
        # Remove attr "login_uppercase"
        self.serverthread.restart_server(conf)
        self.serverthread.update()

        # Server consistency
        self.assertServerdataLen()
        self.assertServerIntegrityfiltered()

        # Verify attribute content
        for user in self.serverdata("SRVUsers"):
            self.assertFalse(hasattr(user, "login_uppercase"))

    def test_210b_client_datamodel_no_change_but_server_attr_removed(self):
        self.log_current_test_name(myself())
        self.assertRaises(NewPendingEmail, self.clientthread.update)
        self.assertEqual(EmailFixture.numberOfUnreadEmails(), 1)
        self.assertEqual(
            EmailFixture.emails[0].subject,
            "[hermes-client-usersgroups_null] datamodel warnings have changed",
        )
        self.assertClientdataLen()

        # Verify that attribute still doesn't exist
        for user in self.clientdata("Users"):
            if hasattr(user, "_trashbin_timestamp"):
                # Ignore users in trashbin as they don't have the new attribute
                continue
            self.assertFalse(hasattr(user, "login_uppercase"))

    def test_210c_client_datamodel_remove_attribute(self):
        self.log_current_test_name(myself())
        # Restore attr "login_uppercase"
        conf = self.loadYamlClient("single")
        self.clientthread.restart_client(conf)
        self.assertRaises(NewPendingEmail, self.clientthread.update)
        self.assertEqual(EmailFixture.numberOfUnreadEmails(), 2)
        self.assertEqual(
            EmailFixture.emails[0].subject,
            "[hermes-client-usersgroups_null] no more datamodel warnings",
        )
        # The attribute will be removed in error queue too, so a change notification
        # will be sent
        self.assertEqual(
            EmailFixture.emails[1].subject,
            "[hermes-client-usersgroups_null] objects in error queue have changed",
        )
        self.assertClientdataLen()

        # Verify that attribute still doesn't exist
        for user in self.clientdata("Users"):
            if hasattr(user, "_trashbin_timestamp"):
                # Ignore users in trashbin as they don't have the new attribute
                continue
            self.assertFalse(hasattr(user, "login_uppercase"))

    #######################
    # Primary key updates #
    #######################

    def test_301a_server_primary_key_change_id_to_simpleid(self):
        self.log_current_test_name(myself())
        conf = self.loadYamlServer("single")
        conf["hermes-server"]["datamodel"]["SRVGroups"]["primarykeyattr"] = "simpleid"
        conf["hermes-server"]["datamodel"]["SRVUsers"]["primarykeyattr"] = "simpleid"
        conf["hermes-server"]["datamodel"]["SRVGroupsMembers"]["primarykeyattr"] = [
            "group_simpleid",
            "user_simpleid",
        ]
        conf["hermes-server"]["datamodel"]["SRVGroupsMembers"][
            "integrity_constraints"
        ] = [
            "{{ _SELF.user_simpleid in SRVUsers_pkeys"
            " and _SELF.group_simpleid in SRVGroups_pkeys }}"
        ]
        self.serverthread.restart_server(conf)
        self.serverthread.update()

        # Server consistency
        self.assertServerdataLen()
        self.assertServerIntegrityfiltered()

        # Verify new primary key
        for group in self.serverdata("SRVGroups"):
            self.assertEqual(group.getPKey(), group.simpleid)
        for user in self.serverdata("SRVUsers"):
            self.assertEqual(user.getPKey(), user.simpleid)
        for gm in self.serverdata("SRVGroupsMembers"):
            self.assertTupleEqual(gm.getPKey(), (gm.group_simpleid, gm.user_simpleid))

    def test_301b_client_primary_key_change_id_to_simpleid(self):
        self.log_current_test_name(myself())
        self.clientthread.update()
        self.assertClientdataLen()

        # Verify new primary key
        for group in self.clientdata("Groups"):
            self.assertEqual(group.getPKey(), group._pkey_simpleid)
        for user in self.clientdata("Users"):
            self.assertEqual(user.getPKey(), user._pkey_simpleid)
        for gm in self.clientdata("GroupsMembers"):
            self.assertTupleEqual(
                gm.getPKey(), (gm._pkey_group_simpleid, gm._pkey_user_simpleid)
            )

        self.assertRaises(NewPendingEmail, self.clientthread.update)
        self.assertEqual(EmailFixture.numberOfUnreadEmails(), 1)
        # The error queue objects primary keys were changed, so a change notification
        # will be sent
        self.assertEqual(
            EmailFixture.emails[0].subject,
            "[hermes-client-usersgroups_null] objects in error queue have changed",
        )

    def test_302a_server_reverse_gm_primary_key_order(self):
        self.log_current_test_name(myself())
        conf = self.loadYamlServer("single")
        conf["hermes-server"]["datamodel"]["SRVGroups"]["primarykeyattr"] = "simpleid"
        conf["hermes-server"]["datamodel"]["SRVUsers"]["primarykeyattr"] = "simpleid"
        conf["hermes-server"]["datamodel"]["SRVGroupsMembers"]["primarykeyattr"] = [
            "user_simpleid",
            "group_simpleid",
        ]
        conf["hermes-server"]["datamodel"]["SRVGroupsMembers"][
            "integrity_constraints"
        ] = [
            "{{ _SELF.user_simpleid in SRVUsers_pkeys"
            " and _SELF.group_simpleid in SRVGroups_pkeys }}"
        ]
        self.serverthread.restart_server(conf)
        self.serverthread.update()

        # Server consistency
        self.assertServerdataLen()
        self.assertServerIntegrityfiltered()

        # Verify new primary key
        for group in self.serverdata("SRVGroups"):
            self.assertEqual(group.getPKey(), group.simpleid)
        for user in self.serverdata("SRVUsers"):
            self.assertEqual(user.getPKey(), user.simpleid)
        for gm in self.serverdata("SRVGroupsMembers"):
            self.assertTupleEqual(gm.getPKey(), (gm.user_simpleid, gm.group_simpleid))

    def test_302b_client_reverse_gm_primary_key_order(self):
        self.log_current_test_name(myself())
        self.clientthread.update()
        self.assertClientdataLen()

        # Verify new primary key
        for group in self.clientdata("Groups"):
            self.assertEqual(group.getPKey(), group._pkey_simpleid)
        for user in self.clientdata("Users"):
            self.assertEqual(user.getPKey(), user._pkey_simpleid)
        for gm in self.clientdata("GroupsMembers"):
            self.assertTupleEqual(
                gm.getPKey(), (gm._pkey_user_simpleid, gm._pkey_group_simpleid)
            )

    def test_303a_server_remove_groupsmembers_type(self):
        self.log_current_test_name(myself())
        conf = self.loadYamlServer("single")
        conf["hermes-server"]["datamodel"]["SRVGroups"]["primarykeyattr"] = "simpleid"
        conf["hermes-server"]["datamodel"]["SRVUsers"]["primarykeyattr"] = "simpleid"
        del conf["hermes-server"]["datamodel"]["SRVGroupsMembers"]
        self.serverthread.restart_server(conf)
        self.serverthread.update()

        # Server consistency
        self.assertServerdataLen(SRVGroupsMembers=None)
        self.assertServerIntegrityfiltered(SRVGroupsMembers=None)

    def test_303b_client_remove_groupsmembers_type(self):
        self.log_current_test_name(myself())
        conf = self.loadYamlClient("single")
        del conf["hermes-client"]["datamodel"]["GroupsMembers"]
        self.clientthread.restart_client(conf)
        self.clientthread.update()
        self.assertClientdataLen(GroupsMembers=None)

    def test_304a_server_primary_key_change_int_to_tuple(self):
        self.log_current_test_name(myself())
        conf = self.loadYamlServer("single")
        conf["hermes-server"]["datamodel"]["SRVGroups"]["primarykeyattr"] = [
            "id",
            "simpleid",
        ]
        conf["hermes-server"]["datamodel"]["SRVUsers"]["primarykeyattr"] = [
            "id",
            "simpleid",
        ]
        del conf["hermes-server"]["datamodel"]["SRVGroupsMembers"]
        self.serverthread.restart_server(conf)
        self.serverthread.update()

        # Server consistency
        self.assertServerdataLen()
        self.assertServerIntegrityfiltered()

        # Verify new primary key
        for group in self.serverdata("SRVGroups"):
            self.assertTupleEqual(group.getPKey(), (group.id, group.simpleid))
        for user in self.serverdata("SRVUsers"):
            self.assertTupleEqual(user.getPKey(), (user.id, user.simpleid))

    def test_304b_client_primary_key_change_int_to_tuple(self):
        self.log_current_test_name(myself())
        self.clientthread.update()
        self.assertClientdataLen()

        # Verify new primary key
        for group in self.clientdata("Groups"):
            self.assertTupleEqual(
                group.getPKey(), (group._pkey_id, group._pkey_simpleid)
            )
        for user in self.clientdata("Users"):
            self.assertTupleEqual(user.getPKey(), (user._pkey_id, user._pkey_simpleid))

        self.assertRaises(NewPendingEmail, self.clientthread.update)
        self.assertEqual(EmailFixture.numberOfUnreadEmails(), 1)
        # The error queue objects primary keys were changed, so a change notification
        # will be sent
        self.assertEqual(
            EmailFixture.emails[0].subject,
            "[hermes-client-usersgroups_null] objects in error queue have changed",
        )

    def test_305a_server_primary_key_change_tuple_to_int(self):
        self.log_current_test_name(myself())
        conf = self.loadYamlServer("single")
        del conf["hermes-server"]["datamodel"]["SRVGroupsMembers"]
        self.serverthread.restart_server(conf)
        self.serverthread.update()

        # Server consistency
        self.assertServerdataLen()
        self.assertServerIntegrityfiltered()

        # Verify new primary key
        for group in self.serverdata("SRVGroups"):
            self.assertEqual(group.getPKey(), group.id)
        for user in self.serverdata("SRVUsers"):
            self.assertEqual(user.getPKey(), user.id)

    def test_305b_client_primary_key_change_tuple_to_int(self):
        self.log_current_test_name(myself())
        self.clientthread.update()
        self.assertClientdataLen()

        # Verify new primary key
        for group in self.clientdata("Groups"):
            self.assertEqual(group.getPKey(), group._pkey_id)
        for user in self.clientdata("Users"):
            self.assertEqual(user.getPKey(), user._pkey_id)

        self.assertRaises(NewPendingEmail, self.clientthread.update)
        self.assertEqual(EmailFixture.numberOfUnreadEmails(), 1)
        # The error queue objects primary keys were changed, so a change notification
        # will be sent
        self.assertEqual(
            EmailFixture.emails[0].subject,
            "[hermes-client-usersgroups_null] objects in error queue have changed",
        )

    def test_306a_server_add_new_primary_key_attribute(self):
        self.log_current_test_name(myself())
        conf = self.loadYamlServer("single")
        conf["hermes-server"]["datamodel"]["SRVGroups"]["sources"]["db_single"][
            "attrsmapping"
        ]["newid"] = "{{ id | upper }}"
        conf["hermes-server"]["datamodel"]["SRVUsers"]["sources"]["db_single"][
            "attrsmapping"
        ]["newid"] = "{{ id | upper }}"
        del conf["hermes-server"]["datamodel"]["SRVGroupsMembers"]
        self.serverthread.restart_server(conf)
        self.serverthread.update()

        # Server consistency
        self.assertServerdataLen()
        self.assertServerIntegrityfiltered()

        # Verify primary key
        for group in self.serverdata("SRVGroups"):
            self.assertEqual(group.getPKey(), group.id)
        for user in self.serverdata("SRVUsers"):
            self.assertEqual(user.getPKey(), user.id)

    def test_306b_server_primary_key_change_new_attribute(self):
        self.log_current_test_name(myself())
        conf = self.loadYamlServer("single")
        conf["hermes-server"]["datamodel"]["SRVGroups"]["sources"]["db_single"][
            "attrsmapping"
        ]["newid"] = "{{ id | upper }}"
        conf["hermes-server"]["datamodel"]["SRVUsers"]["sources"]["db_single"][
            "attrsmapping"
        ]["newid"] = "{{ id | upper }}"
        conf["hermes-server"]["datamodel"]["SRVGroups"]["primarykeyattr"] = "newid"
        conf["hermes-server"]["datamodel"]["SRVUsers"]["primarykeyattr"] = "newid"
        del conf["hermes-server"]["datamodel"]["SRVGroupsMembers"]
        self.serverthread.restart_server(conf)
        self.serverthread.update()

        # Server consistency
        self.assertServerdataLen()
        self.assertServerIntegrityfiltered()

        # Verify new primary key
        for group in self.serverdata("SRVGroups"):
            self.assertNotEqual(group.getPKey(), group.id)
            self.assertEqual(group.getPKey(), group.id.upper())
        for user in self.serverdata("SRVUsers"):
            self.assertNotEqual(user.getPKey(), user.id)
            self.assertEqual(user.getPKey(), user.id.upper())

    def test_306c_client_primary_key_change_missing_attribute(self):
        self.log_current_test_name(myself())
        # As the trashbin entry can't contain the new pkey, it'll be purged
        self.clientthread.update()
        self.assertClientdataLen(Users=-1)  # The user purged from trashbin

    def test_306d_client_primary_key_change_new_attribute(self):
        self.log_current_test_name(myself())
        conf = self.loadYamlClient("single")
        del conf["hermes-client"]["datamodel"]["GroupsMembers"]
        self.clientthread.restart_client(conf)
        self.assertRaises(NewPendingEmail, self.clientthread.update)
        self.assertEqual(EmailFixture.numberOfUnreadEmails(), 1)
        self.assertEqual(
            EmailFixture.emails[0].subject,
            "[hermes-client-usersgroups_null] objects in error queue have changed",
        )
        self.assertClientdataLen()

    def test_307a_server_restore_default_pkeys(self):
        self.log_current_test_name(myself())
        conf = self.loadYamlServer("single")
        conf["hermes-server"]["datamodel"]["SRVGroups"]["sources"]["db_single"][
            "attrsmapping"
        ]["newid"] = "{{ id | upper }}"
        conf["hermes-server"]["datamodel"]["SRVUsers"]["sources"]["db_single"][
            "attrsmapping"
        ]["newid"] = "{{ id | upper }}"
        del conf["hermes-server"]["datamodel"]["SRVGroupsMembers"]
        self.serverthread.restart_server(conf)
        self.serverthread.update()

        # Server consistency
        self.assertServerdataLen()
        self.assertServerIntegrityfiltered()

    def test_307b_client_restore_default_pkeys(self):
        self.log_current_test_name(myself())
        self.clientthread.update()
        # Client consistency
        self.assertClientdataLen()

    def test_307c_restore_base_settings(self):
        # Restore server config
        self.log_current_test_name(myself())
        conf = self.loadYamlServer("single")
        self.serverthread.restart_server(conf)
        self.serverthread.update()

        # Restore client config
        conf = self.loadYamlClient("single")
        self.clientthread.restart_client(conf)
        self.assertRaises(NewPendingEmail, self.clientthread.update)
        self.assertEqual(EmailFixture.numberOfUnreadEmails(), 3)
        self.assertEqual(
            EmailFixture.emails[0].subject,
            "[hermes-client-usersgroups_null] datamodel warnings have changed",
        )
        self.assertEqual(
            EmailFixture.emails[1].subject,
            "[hermes-client-usersgroups_null] no more datamodel warnings",
        )
        self.assertEqual(
            EmailFixture.emails[2].subject,
            "[hermes-client-usersgroups_null] objects in error queue have changed",
        )

        # Server consistency
        self.assertServerdataLen(SRVGroupsMembers=865)
        self.assertServerIntegrityfiltered(SRVGroupsMembers=3)

        # Client consistency
        self.assertClientdataLen(GroupsMembers=865)

    def test_307d_server_add_tmays(self):
        self.log_current_test_name(myself())
        tmays = [
            entry for entry in self.fixtures["users_all"] if entry["login"] == "tmays"
        ][0]

        # Add tmays on server
        self.insertEntry(self.databases["db_single"], "users_all", tmays)
        self.serverthread.update()
        self.assertServerdataLen(SRVUsers=+1, SRVGroupsMembers=+3)
        self.assertServerIntegrityfiltered(SRVGroupsMembers=-3)

        # Remove tmays from server
        self.deleteEntry(self.databases["db_single"], "users_all", ["id"], tmays)
        self.serverthread.update()
        self.assertServerdataLen(SRVUsers=-1, SRVGroupsMembers=-3)
        self.assertServerIntegrityfiltered(SRVGroupsMembers=+3)

        # Update client to store tmays in trashbin
        self.clientthread.update()
        self.assertClientdataLen(Users=+1, GroupsMembers=+3)

    ############
    # Trashbin #
    ############

    def test_401a_server_restore_trashed_user_with_changes(self):
        self.log_current_test_name(myself())

        # Re-add tmays
        tmays = deepcopy(
            [
                entry
                for entry in self.fixtures["users_all"]
                if entry["login"] == "tmays"
            ][0]
        )
        # Add/modify/remove some entry values
        tmays["desired_job_8"] = "POTUS"  # Add
        tmays["desired_jobs_joined"] += ";POTUS"  # Modify
        tmays["login"] = "tmays_modified"  # Modify
        tmays["dateOfBirth"] = None  # Remove

        self.insertEntry(self.databases["db_single"], "users_all", tmays)
        self.serverthread.update()

        self.assertServerdataLen(SRVUsers=+1, SRVGroupsMembers=+3)
        self.assertServerIntegrityfiltered(SRVGroupsMembers=-3)

    def test_401b_client_restore_trashed_user(self):
        self.log_current_test_name(myself())
        self.clientthread.update()  # Restore from trashbin as is
        self.assertClientdataLen()

        tmays_id = "a42d0cd7-fd35-4f6a-b450-388748d90846"
        trashedtmays = {
            "_pkey_id": tmays_id,
            "first_name": "Troy",
            "last_name": "Mays",
            "dateOfBirth": datetime(1977, 12, 9, 0, 0),
            "login": "tmays",
            "specialty": "Mechatronics",
            "desired_jobs_joined": [
                "Furniture designer",
                "Electronics engineer",
                "Administrator, education",
                "Leisure centre manager",
                "Hotel manager",
                "Tax inspector",
                "Engineer, automotive",
            ],
            "desired_jobs_columns": [
                "Furniture designer",
                "Electronics engineer",
                "Administrator, education",
                "Leisure centre manager",
                "Hotel manager",
                "Tax inspector",
                "Engineer, automotive",
            ],
        }
        client_tmays = self.clientdata("Users")[tmays_id].toNative()
        self.assertDictEqual(trashedtmays, client_tmays)

        self.clientthread.update()  # Process local changes post-restore
        self.assertClientdataLen()

        expectedtmays = {
            "_pkey_id": tmays_id,
            "first_name": "Troy",
            "last_name": "Mays",
            "login": "tmays_modified",
            "specialty": "Mechatronics",
            "desired_jobs_joined": [
                "Furniture designer",
                "Electronics engineer",
                "Administrator, education",
                "Leisure centre manager",
                "Hotel manager",
                "Tax inspector",
                "Engineer, automotive",
                "POTUS",
            ],
            "desired_jobs_columns": [
                "Furniture designer",
                "Electronics engineer",
                "Administrator, education",
                "Leisure centre manager",
                "Hotel manager",
                "Tax inspector",
                "Engineer, automotive",
                "POTUS",
            ],
        }
        client_tmays = self.clientdata("Users")[tmays_id].toNative()
        self.assertDictEqual(expectedtmays, client_tmays)

    def test_402a_server_restore_user_values_and_delete_it(self):
        self.log_current_test_name(myself())

        # Reset tmays entrie to its original values
        tmays = [
            entry for entry in self.fixtures["users_all"] if entry["login"] == "tmays"
        ][0]

        self.updateEntry(self.databases["db_single"], "users_all", ["id"], tmays)
        self.serverthread.update()
        self.assertServerdataLen()
        self.assertServerIntegrityfiltered()

        self.deleteEntry(self.databases["db_single"], "users_all", ["id"], tmays)
        self.serverthread.update()
        self.assertServerdataLen(SRVUsers=-1, SRVGroupsMembers=-3)
        self.assertServerIntegrityfiltered(SRVGroupsMembers=+3)

    def test_402b_client_restore_user_values_and_delete_it(self):
        self.log_current_test_name(myself())
        self.clientthread.update()
        self.assertClientdataLen()

    ##############
    # Errorqueue #
    ##############

    def test_501a_server_maxremediation_removed_then_added_with_previous_added(
        self,
    ):
        self.log_current_test_name(myself())
        # Remove twagner, event will be appended in errorqueue
        twagner = [
            entry for entry in self.fixtures["users_all"] if entry["login"] == "twagner"
        ][0]
        self.deleteEntry(self.databases["db_single"], "users_all", ["id"], twagner)

        self.serverthread.update()
        self.assertServerdataLen(SRVUsers=-1, SRVGroupsMembers=-3)
        self.assertServerIntegrityfiltered(SRVGroupsMembers=+3)

    def test_501b_client_maxremediation_removed_then_added_with_previous_added(
        self,
    ):
        self.log_current_test_name(myself())
        conf = self.loadYamlClient("single")
        conf["hermes-client"]["autoremediation"] = "maximum"
        self.clientthread.restart_client(conf)
        self.clientthread.update()
        self.assertClientdataLen()

    def test_501c_server_maxremediation_removed_then_added_with_previous_added(
        self,
    ):
        self.log_current_test_name(myself())
        # Add a modified twagner account to store it in errorqueue
        twagner = [
            deepcopy(entry)
            for entry in self.fixtures["users_all"]
            if entry["login"] == "twagner"
        ][0]
        del twagner["middle_name"]  # Resolve errors
        del twagner["dateOfBirth"]  # Remove an attribute
        twagner["specialty"] = "Materials engineering"  # Modify an attribute

        self.insertEntry(self.databases["db_single"], "users_all", twagner)

        self.serverthread.update()
        self.assertServerdataLen(SRVUsers=+1, SRVGroupsMembers=+3)
        self.assertServerIntegrityfiltered(SRVGroupsMembers=-3)

    def test_501d_client_maxremediation_removed_then_added_with_previous_added(
        self,
    ):
        self.log_current_test_name(myself())
        self.clientthread.update()  # Update data
        self.assertClientdataLen()

    def test_501e_client_maxremediation_removed_then_added_with_previous_added(
        self,
    ):
        twagneruid = "f3abea0d-5be9-4db3-9d92-dd7c0db977a9"

        # Resolve first twagner event manually
        self.log_current_test_name(myself())
        for evNumber, remoteEv, localEv, errMsg in self.clienterrorqueue().allEvents():
            if (
                localEv.objpkey == twagneruid
                and localEv.isPartiallyProcessed
                and remoteEv is not None
            ):
                del remoteEv.objattrs["middle_name"]
                del localEv.objattrs["middle_name"]
                break

        self.assertRaises(NewPendingEmail, self.clientthread.update)
        self.assertEqual(EmailFixture.numberOfUnreadEmails(), 1)
        self.assertEqual(
            EmailFixture.emails[0].subject,
            "[hermes-client-usersgroups_null] objects in error queue have changed",
        )
        self.assertClientdataLen(Users=+1)

        # Verify that cached data is expected data
        expectedtwagner = deepcopy(self.serverdata("SRVUsers")[twagneruid].toNative())
        expectedtwagner["_pkey_id"] = twagneruid
        del expectedtwagner["id"]
        del expectedtwagner["simpleid"]
        self.assertDictEqual(
            expectedtwagner, self.clientdata("Users")[twagneruid].toNative()
        )

    def test_502a_client_maxremediation_removed_then_added_with_prev_local_modified(
        self,
    ):
        self.log_current_test_name(myself())
        # Use a jinja filter to add a local-only modified event to errorqueue
        conf = self.loadYamlClient("single")
        conf["hermes-client"]["datamodel"]["Users"]["attrsmapping"]["middle_name"] = (
            "{{ middle_name|default(None) if login != 'twagner'"
            " else 'error_on_second_step' }}"
        )
        # Enable autoremediation
        conf["hermes-client"]["autoremediation"] = "maximum"
        self.clientthread.restart_client(conf)
        # The attribute will change in error queue too, so a change notification will
        # be sent
        self.assertRaises(NewPendingEmail, self.clientthread.update)
        self.assertEqual(EmailFixture.numberOfUnreadEmails(), 1)
        self.assertEqual(
            EmailFixture.emails[0].subject,
            "[hermes-client-usersgroups_null] objects in error queue have changed",
        )
        self.assertClientdataLen()

    def test_502b_server_maxremediation_removed_then_added_with_prev_local_modified(
        self,
    ):
        self.log_current_test_name(myself())
        # Remove twagner, event will be appended in errorqueue
        twagner = [
            entry for entry in self.fixtures["users_all"] if entry["login"] == "twagner"
        ][0]
        self.deleteEntry(self.databases["db_single"], "users_all", ["id"], twagner)

        self.serverthread.update()
        self.assertServerdataLen(SRVUsers=-1, SRVGroupsMembers=-3)
        self.assertServerIntegrityfiltered(SRVGroupsMembers=+3)

    def test_502c_client_maxremediation_removed_then_added_with_prev_local_modified(
        self,
    ):
        self.log_current_test_name(myself())
        self.clientthread.update()
        self.assertClientdataLen()

    def test_502d_server_maxremediation_removed_then_added_with_prev_local_modified(
        self,
    ):
        self.log_current_test_name(myself())
        # Add a modified twagner account to store it in errorqueue
        twagner = [
            deepcopy(entry)
            for entry in self.fixtures["users_all"]
            if entry["login"] == "twagner"
        ][0]
        del twagner["middle_name"]  # Resolve errors
        del twagner["dateOfBirth"]
        twagner["specialty"] = "Materials engineering"  # Modify an attribute

        self.insertEntry(self.databases["db_single"], "users_all", twagner)

        self.serverthread.update()
        self.assertServerdataLen(SRVUsers=+1, SRVGroupsMembers=+3)
        self.assertServerIntegrityfiltered(SRVGroupsMembers=-3)

    def test_502e_client_maxremediation_removed_then_added_with_prev_local_modified(
        self,
    ):
        self.log_current_test_name(myself())
        self.clientthread.update()
        self.assertClientdataLen()

    def test_502f_client_maxremediation_removed_then_added_with_prev_local_modified(
        self,
    ):
        twagneruid = "f3abea0d-5be9-4db3-9d92-dd7c0db977a9"

        # Resolve first twagner event manually
        self.log_current_test_name(myself())
        for evNumber, remoteEv, localEv, errMsg in self.clienterrorqueue().allEvents():
            if (
                localEv.objpkey == twagneruid
                and localEv.isPartiallyProcessed
                and remoteEv is None
            ):
                del localEv.objattrs["added"]["middle_name"]
                break

        self.assertRaises(NewPendingEmail, self.clientthread.update)
        self.assertEqual(EmailFixture.numberOfUnreadEmails(), 1)
        self.assertEqual(
            EmailFixture.emails[0].subject,
            "[hermes-client-usersgroups_null] objects in error queue have changed",
        )
        self.assertClientdataLen()

        # Verify that cached data is expected data
        expectedtwagner = deepcopy(self.serverdata("SRVUsers")[twagneruid].toNative())
        expectedtwagner["_pkey_id"] = twagneruid
        del expectedtwagner["id"]
        del expectedtwagner["simpleid"]
        self.maxDiff = None
        self.assertDictEqual(
            expectedtwagner, self.clientdata("Users")[twagneruid].toNative()
        )

        # Restore standard "middle_name" settings in attrsmapping
        conf = self.loadYamlClient("single")
        # Enable autoremediation
        conf["hermes-client"]["autoremediation"] = "maximum"
        self.clientthread.restart_client(conf)
        self.clientthread.update()
        self.assertClientdataLen()

    def test_503a_server_fix_errors(self):
        self.log_current_test_name(myself())

        # Fix users with errors (storres, kturner and twagner)
        def errusers(d: dict[str, Any]):
            return d["login"] in ["storres", "kturner", "twagner"]

        for entry in filter(errusers, self.fixtures["users_all"]):
            self.updateEntry(self.databases["db_single"], "users_all", ["id"], entry)

        # Fix groups with errors (marine_engineering and energy)
        def errgroups(d: dict[str, Any]):
            return d["name"] in [
                "marine_engineering",
                "energy",
            ]

        for entry in filter(errgroups, self.fixtures["groups"]):
            self.updateEntry(self.databases["db_single"], "groups", ["id"], entry)

        self.serverthread.update()
        self.assertServerdataLen()
        self.assertServerIntegrityfiltered()

    def test_503b_client_fix_errors(self):
        self.log_current_test_name(myself())
        # First loop to fetch new data, and apply autoremediation patch to error queue
        self.assertRaises(NewPendingEmail, self.clientthread.update)
        self.assertEqual(EmailFixture.numberOfUnreadEmails(), 1)
        self.assertEqual(
            EmailFixture.emails[0].subject,
            "[hermes-client-usersgroups_null] objects in error queue have changed",
        )
        self.assertClientdataLen()

        # Second loop to retry error queue
        self.assertRaises(NewPendingEmail, self.clientthread.update)
        self.assertEqual(EmailFixture.numberOfUnreadEmails(), 1)
        self.assertEqual(
            EmailFixture.emails[0].subject,
            "[hermes-client-usersgroups_null] no more objects in error queue",
        )
        self.assertClientdataLen(Users=+2, Groups=+2)
