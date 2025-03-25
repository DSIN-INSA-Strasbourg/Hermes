# Changelog

All notable changes to Hermes will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Client plugins `usersgroups_adpypsrp`: added installation of Kerberos authentication dependencies

### Removed

- Removed client plugin `usersgroups_adwinrm` as it has poor performances and was redundant with `usersgroups_adpypsrp`

## [v1.0.1] - 2025-03-19

### Added

- Client plugins `usersgroups_adpypsrp`: added a new optional setting `Users_mandatory_groups` that allows to force each new user to be added to the specified group list

### Security

- Bumped python dependencies to their latest version:
  - Cerberus
  - cryptography (used by plugins/clients/usersgroups_adwinrm)
  - Jinja2
  - oracledb (used by plugins/datasources/oracle)

## [v1.0.0] - 2024-12-06

### Security

- Bumped python dependencies to their latest version:
  - cryptography (used by plugins/clients/usersgroups_adwinrm)

## [v1.0.0-alpha.8] - 2024-12-04

### Added

- Added a new client plugin `usersgroups_bsspartage` to manage Users, UserPasswords, Groups, GroupsMembers, GroupsSenders and Ressources on a RENATER's PARTAGE instance.
- Added the `ldaphash` helper that replace the passlib dependency in `plugins.attributes.ldapPasswordHash` and `plugins.clients.usersgroups_bsspartage`
- Added Python 3.13 to compatibility list

### Fixed

- The `plugins.attributes.ldapPasswordHash` plugin now provides the hash list in the same order as the different algorithms were specified to it
- Ensure the timezone info of datetime instances is discarded during serialization
- `plugins.datasources.ldap` : when converting LDAP datetime string to datetime instance, discard the timezone info

### Changed

- Moved helpers classes from `clients.helpers` to `helpers`, as helpers can be useful to other types of plugins

### Removed

- Removed passlib dependency, which is incompatible with Python 3.13

### Security

- Bumped python dependencies to their latest version:
  - cryptography (used by plugins/clients/usersgroups_adwinrm)
  - oracledb (used by plugins/datasources/oracle)

## [v1.0.0-alpha.7] - 2024-10-29

### Added

- Added `isAnErrorRetry` read-only attribute that can let client plugin handler know if the current event is being processed as part of an error retry. This can be useful for example to perform additional checks when a library happens to throw exceptions even though it has correctly processed the requested changes, as python-ldap sometimes does.
- Usergroups_LDAP client plugin: Significantly improved reliability in case of error recovery, by adding specific checks to determine what may have already been processed in `plugins.clients.usergroups_ldap`

### Fixed

- Fixed a bug in autoremediation: two modified events were previously merged incorrectly. Tests have been updated to ensure this does not happen again
- Usergroups_LDAP client plugin: internal primary key attributes are now automatically added to the `attributesToIgnore` in `plugins.clients.usergroups_ldap`
- Usergroups_LDAP client plugin: fixed missing escape of a value in LDAP search filter in `plugins.clients.usergroups_ldap`
- SQLite messagebus consumer plugin `plugins.messagebus_consumers.sqlite`: fixed an error raised when the message bus was empty, *e.g.* when all events it contained had been purged because they had exceeded their retention duration.
- Improved the way logs are handled in unit tests: now using a NullHandler instead of calls to logging.disable(). This fixes new functional tests that monitor logs, which were failing from github actions.
- Force a save of `_hermesconfig.json` and `_dataschema.json` clients cache files at exit, to ensure cache files version update is saved, and avoid version migrations at each restart as those files aren't expected to be updated often.

### Security

- Bumped python dependencies to their latest version :
  - kafka-python-ng (used by plugins/messagebus_consumers kafka and plugins/messagebus_producers/kafka)
  - pycryptodomex (used by plugins/attributes/crypto_RSA_OAEP)

## [v1.0.0-alpha.6] - 2024-10-10

### Added

- Added foreign keys support ([documentation](https://hermes.insa-strasbourg.fr/en/hermes/how-it-works/hermes-client/foreign-keys/)).
  - Added a `hermes-server.datamodel.*objtype*.foreignkeys` configuration directive on server allowing to declare foreign keys, to improve error handling on client. The foreign keys will be propagated to clients.
  - Added a `hermes-client.foreignkeys_policy` configuration directive on clients allowing to chose how to handle events on "parent objects" of objects with errors.

### Fixed

- Fixed a KeyError exception that could only occur on client primary keys update, if a removed event was in error queue.
- kafka-python-ng set a default hard limit of 1MB for each message (event) sent to Kafka message bus. This limit can now be overriden by setting the new optional `plugins.messagebus.kafka.settings.max_request_size` configuration directive for `plugins.messagebus_producers.kafka` used only by `hermes-server`.

## [v1.0.0-alpha.5] - 2024-09-05

### Fixed

- Kafka messagebus consumer and producer plugins: fixed occasional `kafka.errors.NoBrokersAvailable: NoBrokersAvailable` errors caused by a timeout while detecting the Kafka broker API version. Now the broker API version is only detected at application startup and reported in the logs, allowing to declare it using a new optional `plugins.messagebus.kafka.settings.api_version` configuration directive, which will disable the broker API version detection.

### Security

- Bumped python dependencies to their latest version :
  - PyYAML
  - cryptography (used by plugins/clients/usersgroups_adwinrm)
  - pywinrm (used by plugins/clients/usersgroups_adwinrm)
  - oracledb (used by plugins/datasources/oracle)

## [v1.0.0-alpha.4] - 2024-07-17

### Added

- Added a directory `clients/helpers/` to store some helpers modules that can be used by client plugins.
- Added `clients.helper.command` helper, to run local commands on client's host.
- Added `clients.helper.randompassword` helper, to generate random passwords with specific constraints.
- Client plugins `usersgroups_adpypsrp` and `usersgroups_adwinrm`: replaced the random generation of non-configurable passwords with the `clients.helper.randompassword` helper, and added the possibility of configuring it using the client plugin configuration file.
- Added a new client plugin `usersgroups_kadmin_heimdal` to manage users and their passwords in an Heimdal Kerberos server.

## [v1.0.0-alpha.3] - 2024-07-12

### Added

- Added a setting `hermes.logs.long_string_limit` to avoid to fill the logs with big strings content. If a string attribute content is greater than this limit, it will be truncated to this limit and marked as a LONG_STRING in logs.
- Added the support of the python type `bytes` from datasources. It works, but should be used only for small binary content.
- Added the BLOB support in the Oracle datasource plugin (plugins/datasources/oracle/), now that `bytes` are supported.

## [v1.0.0-alpha.2] - 2024-07-11

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

## [v1.0.0-alpha.1] - 2024-04-29

### Added

- First release, by [@Boris Lechner](https://github.com/orgs/DSIN-INSA-Strasbourg/people/Boris-INSA). The code is stable enough to start testing it.
