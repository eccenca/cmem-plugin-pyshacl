# pySHACL CMEM Workflow Plugin

An eccenca Corporate Memory (CMEM) plugin performing in-memory SHACL validation with pySHACL.

## Options

### Data graph URI

The URI of the graph to be validated. The graph URI is selected from a list of graphs of types:
- `di:Dataset`
- `dsm:ThesaurusProject`
- `owl:Ontology`
- `shui:ShapeCatalog`
- `void:Dataset`


### SHACL graph URI

The URI of the graph containing the SHACL shapes to be validated against. The graph URI is selected from a list of graphs of type `shui:ShapeCatalog`.

### Generate validation graph

If enabled, the validation graph is posted to the CMEM instance with the graph URI specified with the *validation graph URI* option. Default value: *false*.

### Validation graph URI

If the *generate validation graph* option is enabled the validation graph is posted to the CMEM instance with this graph URI.

### Output values

If enabled, the plugin outputs the validation results and can be connected to, for instance, a CSV dataset to produce a results table. Default value: *false*.

### Clear validation graph

If enabled, the validation graph is cleared before workflow execution. Default value: *true*.

## Advanced Options

### Resolve owl:imports

If enabled, the graph tree defined with `owl:imports` in the data graph is resolved. Default value: *true*.

### Blank node skolemization

If enabled, blank nodes in the validation graph are skolemized into URIs. Default value: *true*.

### Add labels

If enabled, `rdfs:label` triples are added to the validation graph for instances of `sh:ValidationReport` and `sh:ValidationResult`. Default value: *true*.

### Add labels from data and SHACL graphs

If enabled along with the *add labels* option, `rdfs:label` triples are added for the focus nodes, values and SHACL shapes in the validation graph. The labels are taken from the specified data and SHACL graphs. Default value: *false*.

### Add shui:conforms flag to focus node resources

If enabled, `shui:conforms false` triples are added to the focus nodes in the validation graph. Default value: *false*.

## Parameter Input

In order to set options via the input the following parameter names can be used:

| Option                    | Name                                  |
|---------------------------|---------------------------------------|
| Data graph URI            | data_graph_uri                        |
| SHACL graph URI           | shacl_graph_uri                       |
| Generate validation graph | generate_graph                        |
| Validation graph URI      | validation_graph_uri                  |
| Output values             | output_values                         |
| Clear validation graph    | clear_validation_graph                |
| Resolve owl:imports       | owl_imports_resolution                |
| Blank node skolemization  | skolemize_validation_graph            |
| Add labels                | add_labels_to_validation_graph        |
| Add labels from data and SHACL graphs | include_graphs_labels                 |
| Add shui:conforms flag to focus node resources | add_shui_conforms_to_validation_graph | 

Currently, the plugin only accepts one set of parameters.