"""Plugin tests."""

from cmem_plugin_pyshacl.plugin_pyshacl import ShaclValidation
from cmem.cmempy.dp.proxy.graph import post, get, delete
from .utils import TestExecutionContext

from uuid import uuid4
from rdflib import Graph, URIRef, RDF
import os
import pyshacl


def post_shacl_shacl(shacl_graph_uri):
    """upload shacl-shacl graph to cmem"""
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
        raise ValueError(f"Response {res.status_code}: {res.url}")


def test_workflow_execution():
    """Test plugin execution"""
    shacl_graph_uri = f"https://example.org/pyshacl-plugin-test/{uuid4()}"
    validation_graph_uri = f"https://example.org/pyshacl-plugin-test/{uuid4()}"
    post_shacl_shacl(shacl_graph_uri)
    plugin = ShaclValidation(
        data_graph_uri="https://vocab.eccenca.com/shacl/",
        shacl_graph_uri=shacl_graph_uri,
        validation_graph_uri=validation_graph_uri,
        ontology_graph_uri="",
        generate_graph=True,
        output_values=True,
        clear_validation_graph=True,
        owl_imports=True,
        skolemize=True,
        add_labels=True,
        include_graphs_labels=True,
        add_shui_conforms=True,
        meta_shacl=False,
        inference="none",
        advanced=False
    )
    plugin.execute(inputs=(), context=TestExecutionContext())
    res = get(validation_graph_uri)
    if res.status_code != 200:
        raise ValueError(f"Response {res.status_code}: {res.url}")
    delete(shacl_graph_uri)
    delete(validation_graph_uri)
