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


from datetime import datetime

try:
    from faker import Faker
except ModuleNotFoundError:
    import sys

    print("***********************************************", file=sys.stderr)
    print("* 'Faker' module is not installed by default, *", file=sys.stderr)
    print("* as it is only required for this script.     *", file=sys.stderr)
    print("*                                             *", file=sys.stderr)
    print("* Please install it with 'pip install Faker'  *", file=sys.stderr)
    print("***********************************************", file=sys.stderr)
    sys.exit(1)
from faker.providers import DynamicProvider
import json
from typing import Any
import unicodedata
import uuid


specialization_provider = DynamicProvider(
    provider_name="specialization",
    elements=[
        "Civil engineering",
        "Electrical engineering",
        "Mechanical engineering",
        "Computer engineering",
        "Aerospace engineering",
        "Biomedical engineering",
        "Chemical engineering",
        "Environmental engineering",
        "Marine engineering",
        "Geotechnical engineering",
        "Petroleum engineering",
        "Automotive engineering",
        "Engineering Management",
        "Materials engineering",
        "Transportation engineering",
        "Industrial engineering",
        "Mechatronics",
        "Nanotechnology",
        "Robotics",
        "Software engineering",
        "Hydraulic engineering",
        "Architectural engineering",
        "Energy",
        "Manufacturing",
    ],
)

hair_colour_provider = DynamicProvider(
    provider_name="hair_colour",
    elements=[
        "bald",
        "black",
        "blond",
        "brown",
        "ginger",
        "grey",
        "white",
    ],
)


eye_colour_provider = DynamicProvider(
    provider_name="eye_colour",
    elements=[
        "brown",
        "amber",
        "hazel",
        "green",
        "blue",
        "gray",
    ],
)

if __name__ == "__main__":
    users_all: list = []
    users_staff: list = []
    users_students: list = []
    groups: dict[str, dict[str, Any]] = {}
    groupmembers: list[dict[str, Any]] = []
    biological_data: list[dict[str, Any]] = []

    logins: set[str] = set()

    def getLogin(firstname: str, lastname: str):
        login = (firstname[0] + lastname[:14]).lower()
        # Normalize login
        nfkd_form = unicodedata.normalize("NFKD", login)
        return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

    def addGroupMember(groupname: str, user: dict[str, Any]):
        # Normalize groupname
        grpname = groupname.lower().replace(" ", "_")

        # Add group, if not already present
        groups.setdefault(
            grpname,
            {
                "name": grpname,
                "id": str(uuid.uuid3(uuid.NAMESPACE_DNS, grpname)),
                "simpleid": len(groups) + 1,
            },
        )

        groupmembers.append(
            {
                "group_id": groups[grpname]["id"],
                "group_simpleid": groups[grpname]["simpleid"],
                "group_name": grpname,
                "user_login": user["login"],
                "user_id": user["id"],
                "user_simpleid": user["simpleid"],
            }
        )

    def addBiologicalData(user: dict[str, Any]):
        biological_data.append(
            {
                "user_login": user["login"],
                "user_id": user["id"],
                "user_simpleid": user["simpleid"],
                "hair_colour": f.hair_colour(),
                "eye_colour": f.eye_colour(),
            }
        )

    Faker.seed(42)
    f = Faker()
    f.add_provider(specialization_provider)
    f.add_provider(hair_colour_provider)
    f.add_provider(eye_colour_provider)

    fu = f.unique
    for simpleid in range(300):

        user = {
            "id": fu.uuid4(),
            "simpleid": simpleid + 1,
            "first_name": fu.first_name(),
            "middle_name": None,
            "last_name": fu.last_name(),
            "dateOfBirth": None,
            "login": None,
            "specialty": f.specialization(),
            "desired_jobs_joined": "",
            "desired_job_1": None,
            "desired_job_2": None,
            "desired_job_3": None,
            "desired_job_4": None,
            "desired_job_5": None,
            "desired_job_6": None,
            "desired_job_7": None,
            "desired_job_8": None,
            "desired_job_9": None,
        }
        # Login
        user["login"] = getLogin(user["first_name"], user["last_name"])

        # Date of birth
        dob = f.date_of_birth(minimum_age=18, maximum_age=70)
        dt = datetime(dob.year, dob.month, dob.day)
        user["dateOfBirth"] = f"{dt.isoformat(timespec='seconds')}"

        addBiologicalData(user)

        users_all.append(user)
        # 10% of users are staff
        if f.random_int(min=0, max=100) < 10:
            # Staff
            users_staff.append(user)
            addGroupMember("staff", user)
            addGroupMember(user["specialty"], user)

            # No desired job
        else:
            # Student
            users_students.append(user)
            addGroupMember("students", user)
            addGroupMember(user["specialty"], user)
            addGroupMember(f"year_{f.random_int(min=1, max=5)}", user)

            # Set desired jobs
            jobs = []
            for idx in range(f.random_digit()):  # 0 to 9
                prevlen = len(jobs)
                while len(jobs) == prevlen:
                    job = f.job()
                    if job not in jobs:
                        jobs.append(job)
                        user[f"desired_job_{1+idx}"] = job
            user["desired_jobs_joined"] = ";".join(jobs)

    with open("users_all.json", "+wt") as f:
        f.write(json.dumps(users_all, cls=json.JSONEncoder, indent=4))
    with open("users_students.json", "+wt") as f:
        f.write(json.dumps(users_students, cls=json.JSONEncoder, indent=4))
    with open("users_staff.json", "+wt") as f:
        f.write(json.dumps(users_staff, cls=json.JSONEncoder, indent=4))
    with open("groups.json", "+wt") as f:
        f.write(json.dumps(list(groups.values()), cls=json.JSONEncoder, indent=4))
    with open("groupmembers.json", "+wt") as f:
        f.write(json.dumps(list(groupmembers), cls=json.JSONEncoder, indent=4))
    with open("biologicaldata.json", "+wt") as f:
        f.write(json.dumps(list(biological_data), cls=json.JSONEncoder, indent=4))
