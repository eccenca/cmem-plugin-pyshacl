"""Plugin tests."""
from cmem_plugin_pyshacl.plugin_pyshacl import ShaclValidation
from cmem.cmempy.dp.proxy.graph import post, get, delete
from uuid import uuid4

def test_execution():
    """Test plugin execution"""
    shacl_graph_uri = f"https://example.org/pyshacl-plugin-test/{uuid4()}"
    data_graph_uri = shacl_graph_uri
    validation_graph_uri = f"https://example.org/pyshacl-plugin-test/{uuid4()}"
    generate_graph = True
    output_values = True
    clear_validation_graph = True
    owl_imports_resolution = True
    skolemize_validation_graph = True
    add_labels_to_validation_graph = True
    include_graphs_labels = True
    add_shui_conforms_to_validation_graph = True
    post(shacl_graph_uri, "tests/shacl-shacl.nt", replace=True)
    response = get(shacl_graph_uri)
    if response.status_code != 200:
        raise ValueError(f"Response {response.status_code}: {response.url}")
    plugin = ShaclValidation(
        data_graph_uri=data_graph_uri,
        shacl_graph_uri=shacl_graph_uri,
        validation_graph_uri=validation_graph_uri,
        generate_graph=generate_graph,
        output_values=output_values,
        clear_validation_graph=clear_validation_graph,
        owl_imports_resolution=owl_imports_resolution,
        skolemize_validation_graph=skolemize_validation_graph,
        add_labels_to_validation_graph=add_labels_to_validation_graph,
        include_graphs_labels=include_graphs_labels,
        add_shui_conforms_to_validation_graph=add_shui_conforms_to_validation_graph
    )
    result = plugin.execute()
    response = get(validation_graph_uri)
    if response.status_code != 200:
        raise ValueError(f"Response {response.status_code}: {response.url}")
    delete(shacl_graph_uri)
    delete(validation_graph_uri)


