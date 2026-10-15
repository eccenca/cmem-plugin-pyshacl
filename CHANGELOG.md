# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) and this project adheres to [Semantic Versioning](https://semver.org/)

## [Unreleased]

### Added

- the JavaScript files of SHACL-JS are read from the file resources of the project the task
  belongs to: every `sh:jsLibraryURL` must be a path relative to them, such as
  `js/constraints.js`, so no web server is needed to host them. Absolute URLs are rejected.
  The files are checked and read before the data graph is loaded, so a malformed path or a
  missing file stops the task early, and a warning is logged if the shapes graph references
  no JavaScript files at all

### Changed

- updated template to v9.9.0
- updated dependencies: pySHACL 0.40.1, rdflib 7.6.0, validators 0.36.0 and cmem-client 1.3.0
- the `SHACL-JS features` parameter description now says what is evaluated and where the
  JavaScript code is read from
- the `Validation graph URI` and `Generate validation graph` parameter descriptions no
  longer refer to the product as CMEM
- the `Specify a custom max-evaluation-depth` parameter is now labeled `Maximum validation
  depth`, with a description saying what it limits, and the `Add shui:conforms flag to focus
  node resources` label lost its trailing period
- the task documentation is rewritten: what the task produces, where it fits in a workflow,
  and its caveats, including how SHACL-JS finds its JavaScript files
- the task declares its output port: with `Output entities` enabled it has the fixed schema of
  the validation results, so connections to it are checked while the workflow is drawn, and
  without it the task has no output port. If an existing workflow connects the task's output
  to a dataset or another task while `Output entities` is disabled, that connection never
  passed on any entities, and it may now be shown as invalid
- the readme only covers the installation, as in other eccenca plugins, since the parameters
  are documented in Corporate Memory itself

### Fixed

- graphs named with a URN, such as `urn:graph`, are no longer rejected as invalid.
  The data, SHACL shapes and ontology graphs no longer need a URL as their IRI, as long as
  they exist and have the expected graph type, and the validation graph URI may be a URL
  or a URN
- `SHACL-JS features` had no effect: the JavaScript engine pySHACL needs for it was not
  installed, so JavaScript constraints were skipped and a graph violating them was reported
  as conforming. pySHACL is now installed with its JavaScript engine (pyduktape2)
- `Add shui:conforms flag to focus node resources` added no flags when `Add labels` was
  enabled and `Add labels to focus nodes and values` was not, which are their defaults
- `Meta-SHACL` rejected valid shapes graphs using property paths such as `sh:inversePath`,
  `sh:zeroOrMorePath` or `sh:alternativePath` when combined with `OWLRL` or `Both` inference,
  because the inference was applied to the shapes graph as well. The shapes are now checked
  as written, and before the data graph is loaded

## [5.4.1] 2026-08-25

### Fixed

- 401 error on parameter validation because the graph list was still fetched with
  `cmem-cmempy` instead of the client created from the execution context (CMEM-8082)


## [5.4.0] 2026-08-14

### Changed

- update template and dependencies
- remove `cmem-cmempy` dependency

## [5.3.1] 2026-01-27

### Fixed

- close input ports since they are not used

## [5.3.0] 2025-10-20

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

## [5.1.1] 2025-02-19

### Changed

- Use dcterms:created instead of prov:generatedAtTime in validation graph metadata
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


