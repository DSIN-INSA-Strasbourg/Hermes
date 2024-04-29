#! /bin/bash

# Erase previously collected coverage data
coverage erase

echo "*** Unit tests ***"
coverage run -a --source "clients,lib,plugins,server" -m unittest discover -s tests/unit -t tests
# Reminder on how to run a single test file :
# coverage run -a --source "clients,lib,plugins,server" -m unittest tests.unit.test_clients_errorqueue.TestErrorQueueClass

echo -e "\n*** Functional tests ***"
coverage run -a --source "clients,lib,plugins,server" -m unittest discover -s tests/functional -t tests --failfast
# Reminder on how to run a single test file :
# coverage run -a --source "clients,lib,plugins,server" -m unittest --failfast tests.functional.test_scenario_01_single_datasource.TestScenarioSingle

echo -e "\n*** Code coverage ***"
coverage report -m
