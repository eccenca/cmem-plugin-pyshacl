# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) and this project adheres to [Semantic Versioning](https://semver.org/)

## [Unreleased]

# Added

- advanced parameter for enabling the pySHACL meta-SHACL option, validating the SHACL shapes graph against the SHACL-SHACL shapes graph before validating the data graph (default: False).

# Changed

- migrated to cmem-plugin-base v2
- shac-shacl rdf file for testing taken from pyshacl module instead of additional file

# Fixed

- added `rdf:type shui:ShapeCatalog` triple to `shacl-shacl.nt` to avoid failed parameter check for SHACL graph URI when running the plugin test

## [2.0.1] 2022-07-07

## Fixed

- fixed parameter validation for graph availability of data and SHACL graphs

## Changed

- log output for parameter validation

## [2.0.0] 2022-07-07

# Added

- accept input parameters
- check if parameters are valid before executing

## [1.2.2] 2022-07-05

## Added

- log error if post graph response status code is not 204

## Fixed

- added version number to code

## [1.2.1] 2022-07-04

## Fixed

- return only object literal from `get_label` function

## [1.2.0] 2022-07-04

## Changed

- `rdfs:label` in the data/shacl graphs is now preferred when adding labels to the validation graph, preserving original `rdfs:label` if present
- plain literals instead of `xsd:string` for new string literals added to validation graph
- using `g.value()` instead of `list(g....)[0]` to retrieve values from graph

## [1.1.0] 2022-07-04

## Added

- the "Add labels" option now also applies to the entity output

## Changed

- the label option now retrieves the SKOS preferred label if present. The property path hierarchy is `skosxl:prefLabel/skosxl:literalForm`, `skos:prefLabel`, `rdfs:label`
- changes in option labels/descriptions

## Fixed

- When "Add labels" is activated, labels are also added to `shacl:value` objects that are blank nodes 

## [1.0.1] 2022-06-29

### Added

- initial version

