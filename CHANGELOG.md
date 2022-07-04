# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) and this project adheres to [Semantic Versioning](https://semver.org/)

## [1.1.0] 2022-07-04

## Added

- the "Add labels" option now also applies to the entity output

## Changed

- the label option now retrieves the SKOS preferred label if present. The property path hierarchy is `skosxl:prefLabel/skosxl:literalForm`, `skos:prefLabel`, `rdfs:label`
- changes in option labels/descriptions

## Fixed

- When "Add labels" is activated, labels are also addes to `shacl:value` objects that are blank nodes 

## [1.0.1] 2022-06-29

### Added

- initial version

