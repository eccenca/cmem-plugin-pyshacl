"""Plugin tests."""

from cmem_plugin_pyshacl.plugin_pyshacl import ShaclValidation
from cmem.cmempy.dp.proxy.graph import post, get, delete
from tests.utils import TestExecutionContext

from uuid import uuid4
from rdflib import Graph, URIRef, RDF
import os
import pyshacl


def post_shacl_shacl(shacl_graph_uri):
    shacl_file = os.path.join(pyshacl.__path__[0], "assets", "shacl-shacl.ttl")
    g = Graph()
    g.parse(shacl_file, format="turtle")
    g.add(
        (
            URIRef(shacl_graph_uri),
            RDF.type,
            URIRef("https://vocab.eccenca.com/shui/ShapeCatalog")
        )
    )
    temp_file = f"{uuid4()}.nt"
    g.serialize(temp_file, format="nt", encoding="utf-8")
    res = post(shacl_graph_uri, temp_file, replace=True)
    os.remove(temp_file)
    if res.status_code != 204:
        raise ValueError(f"Response {res.status_code}")


def test_workflow_execution():
    """Test plugin execution"""
    shacl_graph_uri = f"https://example.org/pyshacl-plugin-test/{uuid4()}"
    data_graph_uri = "https://vocab.eccenca.com/shacl/"
    validation_graph_uri = f"https://example.org/pyshacl-plugin-test/{uuid4()}"
    generate_graph = True
    output_values = True
    clear_validation_graph = True
    owl_imports_resolution = True
    skolemize_validation_graph = True
    add_labels_to_validation_graph = True
    include_graphs_labels = True
    add_shui_conforms_to_validation_graph = True
    meta_shacl = False
    inference = "none"
    post_shacl_shacl(shacl_graph_uri)
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
        add_shui_conforms_to_validation_graph=add_shui_conforms_to_validation_graph,
        meta_shacl=meta_shacl,
        inference=inference
    )
    plugin.execute(inputs=(), context=TestExecutionContext())
    response = get(validation_graph_uri)
    if response.status_code != 200:
        raise ValueError(f"Response {response.status_code}: {response.url}")
    delete(shacl_graph_uri)
    delete(validation_graph_uri)
