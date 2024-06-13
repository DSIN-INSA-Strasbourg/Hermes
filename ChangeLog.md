# Changelog

All notable changes to Hermes will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Added the ability to fetch dictionnaries values for attributes : the dictionnaries can contain any supported value type : int, float, str, datetime, list, dict. No filtering of dict values is made : None, empty sub-dict, or empty list are left as provided.
- Added a new setting `hermes.cli_socket.dont_manage_sockfile` that allow to delegate the CLI server sockfile creation to SystemD.

### Fixed

- Fixed an improper validation of the `from_raw_dict` and `from_json_dict` arguments of the Dataschema constructor, which treated an empty dictionary as if the argument had not been defined. Thanks to Julien Houchard for reporting and fixing this bug.
- Removed unnecessary cache directory checks in CLI tools that could have caused failure in case of missing directory or missing write permissions.

### Security

- Bumped python dependencies to their latest version :
  - Jinja2
  - cryptography (used by plugins/clients/usersgroups_adwinrm)
  - oracledb (used by plugins/datasources/oracle)
  - kafka-python isn't maintained anymore : replaced by kafka-python-ng (used by plugins/messagebus_consumers kafka and plugins/messagebus_producers/kafka)

## [1.0.0-alpha.1] - 2024-04-29

### Added

- First release, by [@Boris Lechner](https://github.com/orgs/DSIN-INSA-Strasbourg/people/Boris-INSA). The code is stable enough to start testing it.
