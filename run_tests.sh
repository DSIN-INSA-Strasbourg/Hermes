#! /bin/bash
# python -m unittest discover -s tests
# coverage run --source "hermes.py,clients,lib,plugins,server" -m unittest discover -s tests
coverage run --source "clients,lib,plugins,server" -m unittest discover -s tests
coverage report -m

