# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) and this project adheres to [Semantic Versioning](https://semver.org/)


## Unreleased

### Changed

- Update template and dependencies (rdflib >=7)
- Update depedencies


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


