# Change Log

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) and this project adheres to [Semantic Versioning](https://semver.org/)

## [Unreleased]

### Changed

- migrate to open source on Github
- changed internal parameter names

## [4.1.2] 2023-05-03

### Changed

- dependency update

## [4.1.1] 2023-05-03

### Changed

- minor plugin description change

### Fixed

- inline code comment edits


## [4.1.0] 2023-05-02

### Added

- advanced pySHACL options *ont_graph*, *inference*, *advanced*

### Changed

- removed `cmem-plugin-base` version check
- update dependencies including `cmem-plugin-base`

### Fixed

- CMEM 23.1 compatibility

## [4.0.3] 2022-11-16

### Changed

- removed unnecessary parameter warnings

## [4.0.2] 2022-11-16

### Fixed

- fixed Meta-SHACL parameter name in documentation 

## [4.0.1] 2022-11-16

### Added

- documentation of advanced option meta-SHACL

### Fixed

- fixed task check:pytest

### Changed

- print warning when 'ExecutionContext' object has no attribute 'user'


## [4.0.0] 2022-11-04

### Fixed

- fixed metashacl with rdflib >= 6.2.0 by updating dependency pyshacl to 0.20.0
- fixed retrieval of plugin information if `Plugin.plugins` is empty or the plugin is not index 0 

### Changed

- dropped support for cmem-plugin-base < 2
- update dependency rdflib to 6.2.0
- using `UserContext` based function `setup_cmempy_user_access` instead of `setup_cmempy_super_user_access`



## [3.1.1] 2022-08-17

### Added

- cmem-plugin-base check for version requirement >= 1.1

## [3.1.0] 2022-08-15

### Changed

- restored compatibility with cmem-plugin-base version < 2

### Added

- setting \_\_version\_\_ in init.py


## [3.0.3] 2022-08-11

### Fixed

- changed Graph.load to Graph.parse in plugin tests for compatibility with rdflib 6.2.0


## [3.0.2] 2022-08-11

### Fixed

- added deprecated Graph.preferredLabel function from rdflib 6.1.1 for compatibility with rdflib 6.2.0

## [3.0.1] 2022-07-30

### Fixed

- removed redundant shacl-shacl.nt file

## [3.0.0] 2022-07-30

### Added

- advanced parameter for enabling the pySHACL meta-SHACL option, validating the SHACL shapes graph against the SHACL-SHACL shapes graph before validating the data graph (default: False)

### Changed

- migrated to cmem-plugin-base v2
- shac-shacl rdf file for testing taken from pyshacl module instead of additional file

### Fixed

- added `rdf:type shui:ShapeCatalog` triple to `shacl-shacl.nt` to avoid failed parameter check for SHACL graph URI when running the plugin test

## [2.0.1] 2022-07-07

### Fixed

- fixed parameter validation for graph availability of data and SHACL graphs

### Changed

- log output for parameter validation

## [2.0.0] 2022-07-07

### Added

- accept input parameters
- check if parameters are valid before executing

## [1.2.2] 2022-07-05

### Added

- log error if post graph response status code is not 204

### Fixed

- added version number to code

## [1.2.1] 2022-07-04

### Fixed

- return only literal from `get_label` function

## [1.2.0] 2022-07-04

### Changed

- `rdfs:label` in the data/shacl graphs is now preferred when adding labels to the validation graph, preserving original `rdfs:label` if present
- plain literals instead of `xsd:string` for new string literals added to validation graph
- using `g.value()` instead of `list(g....)[0]` to retrieve values from graph

## [1.1.0] 2022-07-04

### Added

- the "Add labels" option now also applies to the entity output

### Changed

- the label option now retrieves the SKOS preferred label if present. The property path hierarchy is `skosxl:prefLabel/skosxl:literalForm`, `skos:prefLabel`, `rdfs:label`
- changes in option labels/descriptions

### Fixed

- When "Add labels" is activated, labels are also added to `shacl:value` objects that are blank nodes 

## [1.0.1] 2022-06-29

### Added

- advanced option pySHACL *ont_graph*
- advanced option pySHACL *inference*

### Changed

- removed `cmem-plugin-base` version check
- update dependencies including `cmem-plugin-base` (3.0.0)
- default value for parameter Output values is now True

## [4.0.3] 2022-11-16

### Changed

- removed unnecessary parameter warnings

## [4.0.2] 2022-11-16

### Fixed

- fixed Meta-SHACL parameter name in documentation 

## [4.0.1] 2022-11-16

### Added

- documentation of advanced option meta-SHACL

### Fixed

- fixed task check:pytest

### Changed

- print warning when 'ExecutionContext' object has no attribute 'user'


## [4.0.0] 2022-11-04

### Fixed

- fixed metashacl with rdflib >= 6.2.0 by updating dependency pyshacl to 0.20.0
- fixed retrieval of plugin information if `Plugin.plugins` is empty or the plugin is not index 0 

### Changed

- dropped support for cmem-plugin-base < 2
- update dependency rdflib to 6.2.0
- using `UserContext` based function `setup_cmempy_user_access` instead of `setup_cmempy_super_user_access`



## [3.1.1] 2022-08-17

### Added

- cmem-plugin-base check for version requirement >= 1.1

## [3.1.0] 2022-08-15

### Changed

- restored compatibility with cmem-plugin-base version < 2

### Added

- setting \_\_version\_\_ in init.py


## [3.0.3] 2022-08-11

### Fixed

- changed Graph.load to Graph.parse in plugin tests for compatibility with rdflib 6.2.0


## [3.0.2] 2022-08-11

### Fixed

- added deprecated Graph.preferredLabel function from rdflib 6.1.1 for compatibility with rdflib 6.2.0

## [3.0.1] 2022-07-30

### Fixed

- removed redundant shacl-shacl.nt file

## [3.0.0] 2022-07-30

### Added

- advanced parameter for enabling the pySHACL meta-SHACL option, validating the SHACL shapes graph against the SHACL-SHACL shapes graph before validating the data graph (default: False)

### Changed

- migrated to cmem-plugin-base v2
- shac-shacl rdf file for testing taken from pyshacl module instead of additional file

### Fixed

- added `rdf:type shui:ShapeCatalog` triple to `shacl-shacl.nt` to avoid failed parameter check for SHACL graph URI when running the plugin test

## [2.0.1] 2022-07-07

### Fixed

- fixed parameter validation for graph availability of data and SHACL graphs

### Changed

- log output for parameter validation

## [2.0.0] 2022-07-07

### Added

- accept input parameters
- check if parameters are valid before executing

## [1.2.2] 2022-07-05

### Added

- log error if post graph response status code is not 204

### Fixed

- added version number to code

## [1.2.1] 2022-07-04

### Fixed

- return only literal from `get_label` function

## [1.2.0] 2022-07-04

### Changed

- `rdfs:label` in the data/shacl graphs is now preferred when adding labels to the validation graph, preserving original `rdfs:label` if present
- plain literals instead of `xsd:string` for new string literals added to validation graph
- using `g.value()` instead of `list(g....)[0]` to retrieve values from graph

## [1.1.0] 2022-07-04

### Added

- the "Add labels" option now also applies to the entity output

### Changed

- the label option now retrieves the SKOS preferred label if present. The property path hierarchy is `skosxl:prefLabel/skosxl:literalForm`, `skos:prefLabel`, `rdfs:label`
- changes in option labels/descriptions

### Fixed

- When "Add labels" is activated, labels are also added to `shacl:value` objects that are blank nodes 

## [1.0.1] 2022-06-29

### Added

- advanced option pySHACL *ont_graph*
- advanced option pySHACL *inference*

### Changed

- removed `cmem-plugin-base` version check
- update dependencies including `cmem-plugin-base` (3.0.0)
- default value for parameter Output values is now True

## [4.0.3] 2022-11-16

### Changed

- removed unnecessary parameter warnings

## [4.0.2] 2022-11-16

### Fixed

- fixed Meta-SHACL parameter name in documentation 

## [4.0.1] 2022-11-16

### Added

- documentation of advanced option meta-SHACL

### Fixed

- fixed task check:pytest

### Changed

- print warning when 'ExecutionContext' object has no attribute 'user'


## [4.0.0] 2022-11-04

### Fixed

- fixed metashacl with rdflib >= 6.2.0 by updating dependency pyshacl to 0.20.0
- fixed retrieval of plugin information if `Plugin.plugins` is empty or the plugin is not index 0 

### Changed

- dropped support for cmem-plugin-base < 2
- update dependency rdflib to 6.2.0
- using `UserContext` based function `setup_cmempy_user_access` instead of `setup_cmempy_super_user_access`



## [3.1.1] 2022-08-17

### Added

- cmem-plugin-base check for version requirement >= 1.1

## [3.1.0] 2022-08-15

### Changed

- restored compatibility with cmem-plugin-base version < 2

### Added

- setting \_\_version\_\_ in init.py


## [3.0.3] 2022-08-11

### Fixed

- changed Graph.load to Graph.parse in plugin tests for compatibility with rdflib 6.2.0


## [3.0.2] 2022-08-11

### Fixed

- added deprecated Graph.preferredLabel function from rdflib 6.1.1 for compatibility with rdflib 6.2.0

## [3.0.1] 2022-07-30

### Fixed

- removed redundant shacl-shacl.nt file

## [3.0.0] 2022-07-30

### Added

- advanced parameter for enabling the pySHACL meta-SHACL option, validating the SHACL shapes graph against the SHACL-SHACL shapes graph before validating the data graph (default: False)

### Changed

- migrated to cmem-plugin-base v2
- shac-shacl rdf file for testing taken from pyshacl module instead of additional file

### Fixed

- added `rdf:type shui:ShapeCatalog` triple to `shacl-shacl.nt` to avoid failed parameter check for SHACL graph URI when running the plugin test

## [2.0.1] 2022-07-07

### Fixed

- fixed parameter validation for graph availability of data and SHACL graphs

### Changed

- log output for parameter validation

## [2.0.0] 2022-07-07

### Added

- accept input parameters
- check if parameters are valid before executing

## [1.2.2] 2022-07-05

### Added

- log error if post graph response status code is not 204

### Fixed

- added version number to code

## [1.2.1] 2022-07-04

### Fixed

- return only literal from `get_label` function

## [1.2.0] 2022-07-04

### Changed

- `rdfs:label` in the data/shacl graphs is now preferred when adding labels to the validation graph, preserving original `rdfs:label` if present
- plain literals instead of `xsd:string` for new string literals added to validation graph
- using `g.value()` instead of `list(g....)[0]` to retrieve values from graph

## [1.1.0] 2022-07-04

### Added

- the "Add labels" option now also applies to the entity output

### Changed

- the label option now retrieves the SKOS preferred label if present. The property path hierarchy is `skosxl:prefLabel/skosxl:literalForm`, `skos:prefLabel`, `rdfs:label`
- changes in option labels/descriptions

### Fixed

- When "Add labels" is activated, labels are also added to `shacl:value` objects that are blank nodes 

## [1.0.1] 2022-06-29

### Added

- advanced option pySHACL *ont_graph*
- advanced option pySHACL *inference*

### Changed

- removed `cmem-plugin-base` version check
- update dependencies including `cmem-plugin-base` (3.0.0)
- default value for parameter Output values is now True

## [4.0.3] 2022-11-16

### Changed

- removed unnecessary parameter warnings

## [4.0.2] 2022-11-16

### Fixed

- fixed Meta-SHACL parameter name in documentation 

## [4.0.1] 2022-11-16

### Added

- documentation of advanced option meta-SHACL

### Fixed

- fixed task check:pytest

### Changed

- print warning when 'ExecutionContext' object has no attribute 'user'


## [4.0.0] 2022-11-04

### Fixed

- fixed metashacl with rdflib >= 6.2.0 by updating dependency pyshacl to 0.20.0
- fixed retrieval of plugin information if `Plugin.plugins` is empty or the plugin is not index 0 

### Changed

- dropped support for cmem-plugin-base < 2
- update dependency rdflib to 6.2.0
- using `UserContext` based function `setup_cmempy_user_access` instead of `setup_cmempy_super_user_access`



## [3.1.1] 2022-08-17

### Added

- cmem-plugin-base check for version requirement >= 1.1

## [3.1.0] 2022-08-15

### Changed

- restored compatibility with cmem-plugin-base version < 2

### Added

- setting \_\_version\_\_ in init.py


## [3.0.3] 2022-08-11

### Fixed

- changed Graph.load to Graph.parse in plugin tests for compatibility with rdflib 6.2.0


## [3.0.2] 2022-08-11

### Fixed

- added deprecated Graph.preferredLabel function from rdflib 6.1.1 for compatibility with rdflib 6.2.0

## [3.0.1] 2022-07-30

### Fixed

- removed redundant shacl-shacl.nt file

## [3.0.0] 2022-07-30

### Added

- advanced parameter for enabling the pySHACL meta-SHACL option, validating the SHACL shapes graph against the SHACL-SHACL shapes graph before validating the data graph (default: False)

### Changed

- migrated to cmem-plugin-base v2
- shac-shacl rdf file for testing taken from pyshacl module instead of additional file

### Fixed

- added `rdf:type shui:ShapeCatalog` triple to `shacl-shacl.nt` to avoid failed parameter check for SHACL graph URI when running the plugin test

## [2.0.1] 2022-07-07

### Fixed

- fixed parameter validation for graph availability of data and SHACL graphs

### Changed

- log output for parameter validation

## [2.0.0] 2022-07-07

### Added

- accept input parameters
- check if parameters are valid before executing

## [1.2.2] 2022-07-05

### Added

- log error if post graph response status code is not 204

### Fixed

- added version number to code

## [1.2.1] 2022-07-04

### Fixed

- return only literal from `get_label` function

## [1.2.0] 2022-07-04

### Changed

- `rdfs:label` in the data/shacl graphs is now preferred when adding labels to the validation graph, preserving original `rdfs:label` if present
- plain literals instead of `xsd:string` for new string literals added to validation graph
- using `g.value()` instead of `list(g....)[0]` to retrieve values from graph

## [1.1.0] 2022-07-04

### Added

- the "Add labels" option now also applies to the entity output

### Changed

- the label option now retrieves the SKOS preferred label if present. The property path hierarchy is `skosxl:prefLabel/skosxl:literalForm`, `skos:prefLabel`, `rdfs:label`
- changes in option labels/descriptions

### Fixed

- When "Add labels" is activated, labels are also added to `shacl:value` objects that are blank nodes 

## [1.0.1] 2022-06-29

### Added

- initial version

