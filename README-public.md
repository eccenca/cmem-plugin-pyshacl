# cmem-plugin-pyshacl

This is a plugin for [eccenca](https://eccenca.com) [Corporate Memory](https://documentation.eccenca.com) plugin performing [SHACL](https://www.w3.org/TR/shacl/) validation with [pySHACL](https://github.com/RDFLib/pySHACL).

## Installation

```
cmemc admin workspace python install cmem-plugin-pyshacl
```

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

### Output entities

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

### Meta-SHACL

If enabled, the SHACL shapes graph is validated against the SHACL-SHACL shapes graph before validating the data graph. Default value: *false*.

### Ontology graph URI

The URI of a graph containing extra ontological information. RDFS and OWL definitions from this are used to inoculate the data graph. The graph URI is selected from a list of graphs of type `owl:Ontology`.

### Inference

If enabled, OWL inferencing expansion of the data graph is performed before validation. Options are *RDFS*, *OWLRL*, *Both*, *None*. Default value: *None*.

### Advanced

Enable SHACL Advanced Features. Default value: *false*.


## Parameter Input

In order to set options via the input the following parameter names can be used:

| Option                                         | Name                   |
|------------------------------------------------|------------------------|
| Data graph URI                                 | data_graph_uri         |
| SHACL graph URI                                | shacl_graph_uri        |
| Generate validation graph                      | generate_graph         |
| Validation graph URI                           | validation_graph_uri   |
| Output entities                                | output_entities        |
| Clear validation graph                         | clear_validation_graph |
| Resolve owl:imports                            | owl_imports            |
| Blank node skolemization                       | skolemize              |
| Add labels                                     | add_labels             |
| Add labels from data and SHACL graphs          | include_graphs_labels  |
| Add shui:conforms flag to focus node resources | add_shui_conforms      | 
| Meta-SHACL                                     | meta_shacl             |
| Ontology graph URI                             | ontology_graph_uri     |
| Inference                                      | inference              |
| Advanced                                       | advanced               |