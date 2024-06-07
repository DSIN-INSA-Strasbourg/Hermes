# Changelog

All notable changes to Hermes will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Added the ability to fetch dictionnaries values for attributes : the dictionnaries can contain any supported value type : int, float, str, datetime, list, dict. No filtering of dict values is made : None, empty sub-dict, or empty list are left as provided.

### Fixed

- Fixed an improper validation of the `from_raw_dict` and `from_json_dict` arguments of the Dataschema constructor, which treated an empty dictionary as if the argument had not been defined. Thanks to Julien Houchard for reporting and fixing this bug.

## [1.0.0-alpha.1] - 2024-04-29

### Added

- First release, by [@Boris Lechner](https://github.com/orgs/DSIN-INSA-Strasbourg/people/Boris-INSA). The code is stable enough to start testing it.
