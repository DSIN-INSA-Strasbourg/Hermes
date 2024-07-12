# Changelog

All notable changes to Hermes will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0-alpha.3] - 2024-07-12

### Added

- Added a setting `hermes.logs.long_string_limit` to avoid to fill the logs with big strings content. If a string attribute content is greater than this limit, it will be truncated to this limit and marked as a LONG_STRING in logs.
- Added the support of the python type `bytes` from datasources. It works, but should be used only for small binary content.
- Added the BLOB support in the Oracle datasource plugin (plugins/datasources/oracle/), now that `bytes` are supported.

## [1.0.0-alpha.2] - 2024-07-11

### Added

- Improved autoremediation. A new attribute `isPartiallyProcessed` has been added to clients, and **should be used in most clients plugins**. It must be set to `True` as soon as the slightest modification has been propagated to the target. It allows to merge events whose `currentStep` is different from 0 but whose previous steps have not modified anything on the target. See [clients plugins error handling documentation](https://hermes.insa-strasbourg.fr/en/development/plugins/clients/#error-handling) for details.
- Added the ability to fetch dictionnaries values for attributes : the dictionnaries can contain any supported value type : int, float, str, datetime, list, dict. No filtering of dict values is made : None, empty sub-dict, or empty list are left as provided.
- Added a new setting `hermes.cli_socket.dont_manage_sockfile` that allow to delegate the CLI server sockfile creation to SystemD.
- Added a facultative configuration file named ***APPNAME*-cli-config.yml** for CLI tools to allow certain users to use the CLI without granting them read access to the configuration file.
- Added a new setting `hermes.umask` allowing to set up the default umask for each file or directory created by the application : cache dirs, cache files and log files.
- Now using tox to validate code with black and flake8, run the test suite on each supported major version of Python, and print coverage results
- Added Python 3.11 and 3.12 to compatibility list

### Fixed

- Fixed an improper validation of the `from_raw_dict` and `from_json_dict` arguments of the Dataschema constructor, which treated an empty dictionary as if the argument had not been defined. Thanks to Julien Houchard for reporting and fixing this bug.
- Removed unnecessary cache and logs directories checks in CLI tools that could have caused failure in case of missing directory or missing write permissions.
- Fixed a bug which prevented the Kafka consumer plugin (plugins/messagebus_consumers/kafka/) from running due to an improper call to define the timeout.
- Fixed regex escape sequences that was generating SyntaxWarning on Python >= 3.12
- Updated the code to make it compatible with flake8, in addition to black
- Added missing dependency of `requests-credssp` to client plugin `usersgroups_adpypsrp`
- Clients stopped whenever the message bus was unavailable. Now they wait 60 seconds before retrying to contact it
- Server kept trying to contact the message bus when it was unavailable, causing excessive CPU load and log file filling. Now the server waits 60 seconds before retrying to contact it

### Security

- Bumped python dependencies to their latest version :
  - Jinja2
  - cryptography (used by plugins/clients/usersgroups_adwinrm)
  - oracledb (used by plugins/datasources/oracle)
  - kafka-python isn't maintained anymore : replaced by kafka-python-ng (used by plugins/messagebus_consumers kafka and plugins/messagebus_producers/kafka)

## [1.0.0-alpha.1] - 2024-04-29

### Added

- First release, by [@Boris Lechner](https://github.com/orgs/DSIN-INSA-Strasbourg/people/Boris-INSA). The code is stable enough to start testing it.
