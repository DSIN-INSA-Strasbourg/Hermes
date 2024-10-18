# Hermes

[![GitHub](https://img.shields.io/github/license/DSIN-INSA-Strasbourg/Hermes)](https://github.com/DSIN-INSA-Strasbourg/Hermes/blob/main/LICENSE)
[![GitHub top language](https://img.shields.io/github/languages/top/DSIN-INSA-Strasbourg/Hermes)](https://www.python.org/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![flake8](https://dsin-insa-strasbourg.github.io/Hermes/badges/flake8.svg)](https://dsin-insa-strasbourg.github.io/Hermes/flake8_report/)  
[![Python 3.10](https://img.shields.io/badge/python-3.10-blue)](https://www.python.org/downloads/release/python-3100/)
[![tests py310](https://dsin-insa-strasbourg.github.io/Hermes/badges/tests_py310.svg)](https://dsin-insa-strasbourg.github.io/Hermes/tests_reports/hermes_tests_py310.html)
[![codecov py310](https://dsin-insa-strasbourg.github.io/Hermes/badges/coverage_py310.svg)](https://dsin-insa-strasbourg.github.io/Hermes/coverage_report_py310/)  
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue)](https://www.python.org/downloads/release/python-3110/)
[![tests py311](https://dsin-insa-strasbourg.github.io/Hermes/badges/tests_py311.svg)](https://dsin-insa-strasbourg.github.io/Hermes/tests_reports/hermes_tests_py311.html)
[![codecov py311](https://dsin-insa-strasbourg.github.io/Hermes/badges/coverage_py311.svg)](https://dsin-insa-strasbourg.github.io/Hermes/coverage_report_py311/)  
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue)](https://www.python.org/downloads/release/python-3120/)
[![tests py312](https://dsin-insa-strasbourg.github.io/Hermes/badges/tests_py312.svg)](https://dsin-insa-strasbourg.github.io/Hermes/tests_reports/hermes_tests_py312.html)
[![codecov py312](https://dsin-insa-strasbourg.github.io/Hermes/badges/coverage_py312.svg)](https://dsin-insa-strasbourg.github.io/Hermes/coverage_report_py312/)

---

[Change Data Capture (CDC)](https://medium.com/event-driven-utopia/a-gentle-introduction-to-event-driven-change-data-capture-683297625f9b) tool from any source(s) to any target.

> [!CAUTION]
> :warning: **The code is considered stable enough to be evaluated but needs more testing to ensure its stability** :warning:

## Features

- Does not require any change to sources data model (*e.g.* no need to add a `last_updated` column)
- Multi-source, with ability to set merge/aggregation constraints
- Able to handle several data types, with link (*foreign keys*) between them, and to enforce integrity constraints
- Able to transform data with [Jinja filters](https://jinja.palletsprojects.com/en/3.1.x/templates/#filters) in configuration files: no need to edit some Python code
- Clean error handling, to avoid synchronization problems, and an optional mechanism of error remediation
- Offer a trashbin on clients for removed data
- Insensitive to unavailability and errors on each link (source, message bus, target)
- Easy to extend by design. All following items are implemented as plugins:
  - Datasources
  - Attributes filters (data filters)
  - Clients (targets)
  - Messagebus
- Changes to the datamodel are easy and safe to integrate and propagate, whether on the server or on the clients

## Roadmap

- [x] Allow changing primary keys values safely (server and clients)
- [x] Add a facultative option to remediate errors by merging added/modified events of a same object in errorqueue (clients)
- [ ] Write documentation for
  - [x] installing
  - [ ] using
  - [ ] examples
  - [x] developping a plugin
  - [ ] contributing to core
- [x] Write functional tests
- [ ] Write more tests
- [x] (Maybe) Force remote primary keys in client datamodel. Requires a lot of troubleshooting to safely update "internal" attrnames and values on Dataschema primary key change: in Datasources and Errorqueue
- [x] (Maybe) Provide information allowing client plugins to determine whether a handler is called following the reception of an event or for a retry after an error
- [ ] (Maybe) Reduce RAM consumption by storing the cache in a SQLite database, which would allow loading objects only on demand, and no longer systematically
- [ ] (Maybe) Design a generic way to handle adding a client whose target already contains data
- [ ] (Maybe) Implement data consistency check when initsync sequence is met on an already initialized client (clients)
- [ ] (Maybe) Implement a check to ensure clients subclasses required types and attributes are set in datamodel

## Contributing

Contributions are always welcome, but may take some time to be merged.

## Documentation

[Documentation](https://hermes.insa-strasbourg.fr/)

## License

[GNU GPLv3](https://choosealicense.com/licenses/gpl-3.0/)

## Authors

- [@Boris Lechner](https://github.com/orgs/DSIN-INSA-Strasbourg/people/Boris-INSA)
