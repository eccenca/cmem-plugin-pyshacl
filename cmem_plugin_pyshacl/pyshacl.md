Validates a knowledge graph against SHACL shapes with [pySHACL](https://github.com/RDFLib/pySHACL). The data graph, the SHACL shapes graph and an optional ontology graph are read from eccenca Corporate Memory and validated in memory.

## Input and output

The task has no input port. It reports the validation results in two forms, at least one of which has to be enabled:

- **Entities** on the output port, one per validation result, with its focus node, result path, value, source shape, constraint component, message and severity, plus whether the data graph conforms, the IRIs of the data and shapes graphs and the time of the validation.
- **A validation graph** written to Corporate Memory: the SHACL validation report, with labels, `shui:conforms` flags and provenance added as configured.

The output port only exists while entities are output. Its schema is fixed, so a connection to it is checked while the workflow is being drawn.

## In a workflow

The task usually ends a workflow. Its entities can be written to a CSV dataset to get a table of the validation results, while the validation graph keeps the complete report in Corporate Memory.

## Caveats

- **The graphs are held in memory.** The data graph is loaded completely, together with the graphs it imports when `owl:imports` are resolved, so memory use and run time grow with its size.
- **The validated graphs are not changed.** Removing graph types and inference only affect the copy in memory.
- **SHACL-JS needs its JavaScript from somewhere.** A shape only names a function and the file that defines it, with `sh:jsLibraryURL`:

  ```turtle
  ex:PersonShape sh:js [
      a sh:JSConstraint ;
      sh:jsFunctionName "hasCapitalisedName" ;
      sh:jsLibrary [ sh:jsLibraryURL "js/constraints.js" ]
  ] .
  ```

  The value decides where the file comes from:

  - a relative path, such as `js/constraints.js`, names a file resource of the project the task belongs to;
  - an absolute path or a `file:` URL is read from the file system of the DataIntegration server, for example from a folder mounted into it;
  - a `data:` URL contains the code itself, such as `data:text/javascript,function hasCapitalisedName($this) { … }`.

  Other schemes are rejected, `http:` and `https:` included, since the server would then run code from outside Corporate Memory. Each file may be at most 10 MB. All files are read before the data graph is loaded, so a malformed path or a missing file stops the task early. Relative paths and `data:` URLs are meant for this task, since other SHACL-JS engines resolve them differently.
- **Blank nodes in the entities are shown as Turtle**, at most 50 lines of their description, unless a label replaces them.
