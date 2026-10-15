# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) and this project adheres to [Semantic Versioning](https://semver.org/)

## [Unreleased]

### Changed

- updated template to v9.9.0
- updated dependencies: pySHACL 0.40.1, rdflib 7.6.0, validators 0.36.0 and cmem-client 1.3.0
- the `SHACL-JS features` parameter description now says what is evaluated and that
  JavaScript libraries must be reachable from DataIntegration

### Fixed

- graphs named with a URN, such as `urn:graph`, are no longer rejected as invalid.
  The data, SHACL shapes and ontology graphs no longer need a URL as their IRI, as long as
  they exist and have the expected graph type, and the validation graph URI may be a URL
  or a URN
- `SHACL-JS features` had no effect: the JavaScript engine pySHACL needs for it was not
  installed, so JavaScript constraints were skipped and a graph violating them was reported
  as conforming. pySHACL is now installed with its JavaScript engine (pyduktape2), and the
  task fails with an error if the engine is missing instead of skipping the constraints

## [5.4.1]

### Fixed

- 401 error on parameter validation because the graph list was still fetched with
  `cmem-cmempy` instead of the client created from the execution context (CMEM-8082)


## [5.4.0]

### Changed

- update template and dependencies
- remove `cmem-cmempy` dependency

## [5.3.1]

### Fixed

- close input ports since they are not used

## [5.3.0]

### Changed

- update template and dependencies
- ensure python 3.13 compatability
- python 3.13 now required

## [5.2.0] 2025-07-03

### Changed

- upgrade cmem-plugin-base to v4.12.1

## [5.1.2] 2025-02-21

### Changed

- Parameters "Data" graph URI" and "SHACL shapes graph URI" marked as "required"
- Do not disable SSL verification for requests
- New icon

## [5.1.0] 2024-12-03

### Added

 - Option to enable SHACL-JS Features

## [5.0.2] 2024-11-13

### Fixed

- Temporary file is now created using the Python tempfile module

### Added

- Raise OSError on post result graph error

### Changed

- Update pySHACL to 0.28.1

## [5.0.1] 2024-07-12

### Fixed

- Check if max-validation-depth is an integer 1-999
- fixed errors on CMEM instances with self-signed/invalid certificates

## [5.0.0] 2024-06-17

### Added

- Added ability to specify a custom max-evaluation-depth introduced with pySHACL 0.26.0


