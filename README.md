# Hermes

![GitHub](https://img.shields.io/github/license/DSIN-INSA-Strasbourg/Hermes)
![GitHub top language](https://img.shields.io/github/languages/top/DSIN-INSA-Strasbourg/Hermes)

---

[Change Data Capture (CDC)](https://medium.com/event-driven-utopia/a-gentle-introduction-to-event-driven-change-data-capture-683297625f9b) tool from any source(s) to any target.

> [!CAUTION]
> :warning: **This project is still under developpement and is not ready for production use yet** :warning:

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
- [ ] Extend tests
- [ ] Implement data consistency check when initsync sequence is met on an already initialized client (clients)
- [ ] (Maybe) Force remote primary keys in client datamodel. Requires a lot of troubleshooting to safely update "internal" attrnames and values on Dataschema primary key change: in Datasources and Eventqueue
- [ ] (Maybe) Implement a check to ensure clients subclasses required types and attributes are set in datamodel

## Contributing

Contributions are always welcome, but may take some time to be merged.

## Documentation

[Documentation](https://hermes.insa-strasbourg.fr/)

## License

[GNU GPLv3](https://choosealicense.com/licenses/gpl-3.0/)

## Authors

- [@Boris Lechner](https://github.com/orgs/DSIN-INSA-Strasbourg/people/Boris-INSA)
