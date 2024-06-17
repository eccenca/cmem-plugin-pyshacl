"""Plugin tests."""

from pathlib import Path

import pyshacl
import pytest
from cmem.cmempy.dp.proxy.graph import delete, get, post
from rdflib import RDF, Graph, URIRef

from cmem_plugin_pyshacl.plugin_pyshacl import ShaclValidation

from .utils import TestExecutionContext, needs_cmem

UUID4 = "b36254a836e04279aecf411d2c8e364a"
SHACL_GRAPH_URI = f"https://example.org/pyshacl-plugin-test/{UUID4}"
VALIDATION_GRAPH_URI = f"https://example.org/pyshacl-plugin-test/{UUID4}"


@pytest.fixture()
def _setup(request: pytest.FixtureRequest) -> None:
    """Set up"""
    shacl_file = Path(pyshacl.__path__[0]) / "assets" / "shacl-shacl.ttl"
    g = Graph()
    g.parse(shacl_file, format="turtle")
    g.add(
        (
            URIRef(SHACL_GRAPH_URI),
            RDF.type,
            URIRef("https://vocab.eccenca.com/shui/ShapeCatalog"),
        )
    )
    temp_file = f"{UUID4}.nt"
    g.serialize(temp_file, format="nt", encoding="utf-8")
    res = post(SHACL_GRAPH_URI, temp_file, replace=True)
    Path.unlink(Path(temp_file))
    if res.status_code != 204:  # noqa: PLR2004
        raise ValueError(f"Error uploading SHACL-SHACL {res.status_code}: {res.url}")

    request.addfinalizer(lambda: delete(VALIDATION_GRAPH_URI))
    request.addfinalizer(lambda: delete(SHACL_GRAPH_URI))  # noqa: PT021


@needs_cmem
def test_workflow_execution(_setup: None) -> None:  # noqa: PT019
    """Test plugin execution"""
    plugin = ShaclValidation(
        data_graph_uri="https://vocab.eccenca.com/shacl/",
        shacl_graph_uri=SHACL_GRAPH_URI,
        validation_graph_uri=VALIDATION_GRAPH_URI,
        ontology_graph_uri="",
        generate_graph=True,
        output_entities=True,
        clear_validation_graph=True,
        owl_imports=True,
        skolemize=True,
        add_labels=True,
        include_graphs_labels=True,
        add_shui_conforms=True,
        meta_shacl=False,
        inference="both",
        advanced=True,
        remove_dataset_graph_type=True,
        remove_thesaurus_graph_type=True,
        remove_shape_catalog_graph_type=True,
        max_validation_depth=15,
    )
    plugin.execute(inputs=(), context=TestExecutionContext())
    res = get(VALIDATION_GRAPH_URI)
    if res.status_code != 200:  # noqa: PLR2004
        raise ValueError(f"Response {res.status_code}: {res.url}")
