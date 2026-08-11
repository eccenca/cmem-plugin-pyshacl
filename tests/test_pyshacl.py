"""Plugin tests."""

import tempfile
from collections.abc import Generator
from os import environ
from pathlib import Path
from tempfile import NamedTemporaryFile

import pyshacl
import pytest
from cmem_client.client import Client
from cmem_client.repositories.protocols.import_item import ImportConflictPolicy
from cmem_plugin_base.testing import TestExecutionContext
from rdflib import PROV, RDF, Graph, URIRef
from rdflib.compare import similar

from cmem_plugin_pyshacl.plugin_pyshacl import ShaclValidation

from . import __path__

UUID4 = "b36254a836e04279aecf411d2c8e364a"
SHACL_GRAPH_URI = f"https://example.org/pyshacl-plugin-test/{UUID4}"
VALIDATION_GRAPH_URI = f"https://example.org/pyshacl-plugin-test/{UUID4}"

needs_cmem = pytest.mark.skipif(
    environ.get("CMEM_BASE_URI", "") == "", reason="Needs CMEM configuration"
)


@pytest.fixture
def _setup() -> Generator[None]:
    """Set up"""
    client = Client.from_context(TestExecutionContext())
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
    with NamedTemporaryFile(suffix=".nt", delete=True) as temp:
        g.serialize(temp.name, format="nt", encoding="utf-8")

        client.graphs.import_item(
            path=Path(temp.name),
            key=SHACL_GRAPH_URI,
            on_conflict=ImportConflictPolicy.REPLACE,
        )

    yield None

    client.graphs.delete_item(key=VALIDATION_GRAPH_URI, skip_if_missing=True)
    client.graphs.delete_item(key=SHACL_GRAPH_URI, skip_if_missing=True)


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
        skolemize=False,
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

    client = Client.from_context(TestExecutionContext())
    with tempfile.NamedTemporaryFile(suffix=".ttl", delete=True) as tmp:
        path = client.graphs.export_item(
            key=VALIDATION_GRAPH_URI, path=Path(tmp.name), replace=True
        )
        data = path.read_text()
        result = Graph().parse(data=data)
        result.remove((None, PROV.generatedAtTime, None))
        test = Graph().parse(Path(__path__[0]) / "test_pyshacl.ttl", format="turtle")

    assert similar(result, test)
