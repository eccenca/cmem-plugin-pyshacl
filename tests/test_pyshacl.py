"""Plugin tests."""

import inspect
import tempfile
from collections.abc import Generator
from dataclasses import dataclass
from os import environ
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, NoReturn, cast

import pyshacl
import pytest
from cmem_client.client import Client
from cmem_client.repositories.protocols.import_item import ImportConflictPolicy
from cmem_plugin_base.testing import TestExecutionContext
from rdflib import PROV, RDF, RDFS, SH, XSD, Graph, Literal, Namespace, URIRef
from rdflib.compare import similar

from cmem_plugin_pyshacl import plugin_pyshacl
from cmem_plugin_pyshacl.plugin_pyshacl import ShaclValidation

from . import __path__

UUID4 = "b36254a836e04279aecf411d2c8e364a"
SHACL_GRAPH_URI = f"https://example.org/pyshacl-plugin-test/{UUID4}"
VALIDATION_GRAPH_URI = f"https://example.org/pyshacl-plugin-test/{UUID4}"

EX = Namespace("https://example.org/pyshacl-plugin-test/vocab#")
SHUI = Namespace("https://vocab.eccenca.com/shui/")

DATA_GRAPH_URI = f"https://example.org/pyshacl-plugin-test/data/{UUID4}"
SHAPES_GRAPH_URI = f"https://example.org/pyshacl-plugin-test/shapes/{UUID4}"
ONTOLOGY_GRAPH_URI = f"https://example.org/pyshacl-plugin-test/ontology/{UUID4}"
REPORT_GRAPH_URI = f"https://example.org/pyshacl-plugin-test/report/{UUID4}"

# ex:alice violates the datatype and the class constraint, ex:carol and the blank node the
# minimum count, the blank node the datatype constraint as well: five results in total, with
# a focus node, a value and a source shape of every RDF term type the plugin formats
EXPECTED_VIOLATIONS = 5

SHAPES_TTL = f"""
@prefix ex: <{EX}> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix shui: <{SHUI}> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<{SHAPES_GRAPH_URI}> a shui:ShapeCatalog .

ex:PersonShape a sh:NodeShape ;
    rdfs:label "Person shape" ;
    sh:targetClass ex:Person ;
    sh:property ex:NameShape, ex:AgeShape ;
    sh:property [ sh:path ex:knows ; sh:class ex:Person ] .

ex:NameShape a sh:PropertyShape ;
    rdfs:label "name of a person" ;
    sh:path ex:name ;
    sh:minCount 1 .

ex:AgeShape a sh:PropertyShape ;
    rdfs:label "age of a person" ;
    sh:path ex:age ;
    sh:datatype xsd:integer .
"""

DATA_TTL = f"""
@prefix ex: <{EX}> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix void: <http://rdfs.org/ns/void#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<{DATA_GRAPH_URI}> a void:Dataset .

ex:alice a ex:Person ;
    rdfs:label "Alice" ;
    ex:name "Alice" ;
    ex:age "not a number" ;
    ex:knows ex:bob .

ex:bob a ex:Thing ;
    rdfs:label "Bob" .

ex:carol a ex:Person .

[] a ex:Person ;
    ex:age "7"^^xsd:float .
"""

ONTOLOGY_TTL = f"""
@prefix ex: <{EX}> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

<{ONTOLOGY_GRAPH_URI}> a owl:Ontology .

ex:Person a owl:Class ;
    rdfs:label "Person" .
"""

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


def import_graph(client: Client, uri: str, turtle: str) -> None:
    """Import a graph given as turtle into cmem"""
    graph = Graph().parse(data=turtle, format="turtle")
    with NamedTemporaryFile(suffix=".nt", delete=True) as temp:
        graph.serialize(temp.name, format="nt", encoding="utf-8")
        client.graphs.import_item(
            path=Path(temp.name),
            key=uri,
            on_conflict=ImportConflictPolicy.REPLACE,
        )


def export_graph(client: Client, uri: str) -> Graph:
    """Export a graph from cmem"""
    with tempfile.NamedTemporaryFile(suffix=".ttl", delete=True) as tmp:
        path = client.graphs.export_item(key=uri, path=Path(tmp.name), replace=True)
        return Graph().parse(data=path.read_text(), format="turtle")


@pytest.fixture
def _violations_setup() -> Generator[None]:
    """Set up a data graph that does not conform to its shape catalog"""
    client = Client.from_context(TestExecutionContext())
    import_graph(client, SHAPES_GRAPH_URI, SHAPES_TTL)
    import_graph(client, DATA_GRAPH_URI, DATA_TTL)
    import_graph(client, ONTOLOGY_GRAPH_URI, ONTOLOGY_TTL)

    yield None

    for uri in (REPORT_GRAPH_URI, ONTOLOGY_GRAPH_URI, DATA_GRAPH_URI, SHAPES_GRAPH_URI):
        client.graphs.delete_item(key=uri, skip_if_missing=True)


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


@needs_cmem
def test_workflow_execution_with_violations(_violations_setup: None) -> None:  # noqa: PT019
    """Test plugin execution on a data graph that does not conform"""
    plugin = ShaclValidation(
        data_graph_uri=DATA_GRAPH_URI,
        shacl_graph_uri=SHAPES_GRAPH_URI,
        validation_graph_uri=REPORT_GRAPH_URI,
        generate_graph=True,
        output_entities=True,
        clear_validation_graph=True,
        skolemize=False,
        add_labels=True,
        include_graphs_labels=True,
        add_shui_conforms=True,
        remove_dataset_graph_type=True,
    )
    entities = plugin.execute(inputs=(), context=TestExecutionContext())

    assert entities is not None
    # one row per validation result, one column per path of the entity schema
    rows = [[value[0] for value in entity.values] for entity in entities.entities]
    assert len(rows) == EXPECTED_VIOLATIONS

    focus_nodes = {row[0] for row in rows}
    assert "Alice" in focus_nodes  # the label of ex:alice replaces its URI
    assert EX.carol in focus_nodes  # ex:carol has no label, so its URI is kept
    assert any("@prefix" in node for node in focus_nodes)  # the blank node as turtle

    values = {row[2] for row in rows}
    assert "Bob" in values  # the label of the offending object
    assert '"not a number"' in values  # a literal without a datatype
    # a literal with a datatype, whose lexical form rdflib may normalize
    assert any(value.startswith('"7') and value.endswith(f"^^<{XSD.float}>") for value in values)

    source_shapes = {row[3] for row in rows}
    assert "name of a person" in source_shapes
    assert "age of a person" in source_shapes
    assert any("@prefix" in shape for shape in source_shapes)  # the blank node property shape

    assert all(row[5] for row in rows)  # every result carries a message
    assert {row[6] for row in rows} == {SH.Violation}

    report = export_graph(Client.from_context(TestExecutionContext()), REPORT_GRAPH_URI)
    results = list(report.subjects(RDF.type, SH.ValidationResult))
    assert len(results) == EXPECTED_VIOLATIONS
    assert list(report.objects(predicate=SH.conforms)) == [Literal(False)]
    assert all(str(report.value(result, RDFS.label)).startswith("SHACL: ") for result in results)
    flagged = set(report.subjects(SHUI.conforms, Literal(False, datatype=XSD.boolean)))
    assert {EX.alice, EX.carol} <= flagged


@needs_cmem
def test_execution_with_ontology_graph_and_without_entities(
    _violations_setup: None,  # noqa: PT019
) -> None:
    """Test plugin execution with an ontology graph and without entity output"""
    plugin = ShaclValidation(
        data_graph_uri=DATA_GRAPH_URI,
        shacl_graph_uri=SHAPES_GRAPH_URI,
        ontology_graph_uri=ONTOLOGY_GRAPH_URI,
        validation_graph_uri=REPORT_GRAPH_URI,
        generate_graph=True,
        output_entities=False,
        clear_validation_graph=True,
    )
    assert plugin.execute(inputs=(), context=TestExecutionContext()) is None

    # the validation graph is posted even though no entities are returned
    report = export_graph(Client.from_context(TestExecutionContext()), REPORT_GRAPH_URI)
    assert len(list(report.subjects(RDF.type, SH.ValidationResult))) == EXPECTED_VIOLATIONS


@needs_cmem
def test_execution_with_entities_only(_violations_setup: None) -> None:  # noqa: PT019
    """Test plugin execution that outputs entities without generating a validation graph"""
    plugin = ShaclValidation(
        data_graph_uri=DATA_GRAPH_URI,
        shacl_graph_uri=SHAPES_GRAPH_URI,
        generate_graph=False,
        output_entities=True,
    )
    entities = plugin.execute(inputs=(), context=TestExecutionContext())

    assert entities is not None
    assert len(list(entities.entities)) == EXPECTED_VIOLATIONS
    client = Client.from_context(TestExecutionContext())
    assert REPORT_GRAPH_URI not in client.graphs  # nothing was posted


@dataclass
class StubGraph:
    """Stand-in for the graph model of a cmem-client graph list"""

    assigned_classes: list[str]


class StubClient:
    """Stand-in for the client, exposing only the graph list check_parameters reads"""

    def __init__(self, graphs: dict[str, StubGraph]) -> None:
        self.graphs = graphs


STUB_GRAPHS = {
    DATA_GRAPH_URI: StubGraph(["http://rdfs.org/ns/void#Dataset"]),
    SHAPES_GRAPH_URI: StubGraph(["https://vocab.eccenca.com/shui/ShapeCatalog"]),
    ONTOLOGY_GRAPH_URI: StubGraph(["http://www.w3.org/2002/07/owl#Ontology"]),
    REPORT_GRAPH_URI: StubGraph([]),
}

VALID_PARAMETERS: dict[str, Any] = {
    "data_graph_uri": DATA_GRAPH_URI,
    "shacl_graph_uri": SHAPES_GRAPH_URI,
    "validation_graph_uri": REPORT_GRAPH_URI,
    "generate_graph": True,
    "output_entities": True,
}


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"generate_graph": False, "output_entities": False}, "needs to be set to true"),
        ({"data_graph_uri": "no uri"}, "Data graph URI parameter is invalid"),
        ({"shacl_graph_uri": "no uri"}, "SHACL graph URI parameter is invalid"),
        ({"ontology_graph_uri": "no uri"}, "Ontology graph URI parameter is invalid"),
        ({"ontology_graph_uri": "https://example.org/missing"}, "Ontology graph .* not found"),
        ({"ontology_graph_uri": DATA_GRAPH_URI}, "Invalid graph type for Ontology graph"),
        ({"data_graph_uri": "https://example.org/missing"}, "Data graph .* not found"),
        ({"shacl_graph_uri": "https://example.org/missing"}, "SHACL graph .* not found"),
        ({"data_graph_uri": REPORT_GRAPH_URI}, "Invalid graph type for data graph"),
        ({"shacl_graph_uri": DATA_GRAPH_URI}, "Invalid graph type for SHACL graph"),
        ({"validation_graph_uri": "no uri"}, "Validation graph URI parameter is invalid"),
        ({"inference": "sometimes"}, "Invalid value for inference parameter"),
        ({"max_validation_depth": 0}, "Invalid value for maximum evaluation depth"),
    ],
)
def test_check_parameters_rejects_invalid_parameters(
    overrides: dict[str, Any], message: str
) -> None:
    """Test that invalid parameters are rejected before a graph is loaded"""
    plugin = ShaclValidation(**{**VALID_PARAMETERS, **overrides})
    with pytest.raises(ValueError, match=message):
        plugin.check_parameters(client=cast("Client", StubClient(STUB_GRAPHS)))


@pytest.mark.parametrize(
    "overrides",
    [
        {"validation_graph_uri": REPORT_GRAPH_URI},  # the graph exists already
        {"validation_graph_uri": "https://example.org/does-not-exist-yet"},
        {"generate_graph": False},  # no validation graph at all
    ],
)
def test_check_parameters_without_labels(overrides: dict[str, Any]) -> None:
    """Test that graph labels are switched off when no labels are added at all"""
    plugin = ShaclValidation(
        **{
            **VALID_PARAMETERS,
            "ontology_graph_uri": ONTOLOGY_GRAPH_URI,
            "add_labels": False,
            "include_graphs_labels": True,
            **overrides,
        }
    )
    plugin.check_parameters(client=cast("Client", StubClient(STUB_GRAPHS)))

    assert plugin.include_graphs_labels is False


def test_no_cmempy_backed_imports() -> None:
    """Test that the plugin module imports no cmempy-backed name

    cmempy authenticates from the process environment, which a workflow does not provide:
    in DataIntegration the token is only available via the ExecutionContext. Such a name
    can enter the module indirectly, as get_graphs_list did through
    cmem_plugin_base.dataintegration.parameter.graph, so grepping for "cmempy" is not enough.
    """
    cmempy_backed = sorted(
        f"{name} from {obj.__module__}"
        for name, obj in vars(plugin_pyshacl).items()
        if (inspect.isfunction(obj) or inspect.isclass(obj))
        and obj.__module__.startswith("cmem.cmempy")
    )
    assert not cmempy_backed, f"cmempy-backed names in the plugin module: {cmempy_backed}"


@needs_cmem
def test_execute_uses_only_the_context_client(
    _setup: None,  # noqa: PT019
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that plugin execution reaches CMEM through the context client only

    A pytest process authenticates cmempy by accident - the credentials in .env plus the
    token TestUserContext itself fetches through cmempy - so a leftover cmempy call passes
    unnoticed unless cmempy is cut off explicitly. Under DataIntegration the same call
    answers 401.
    """
    # the context has to be built before cmempy is cut off, because TestUserContext
    # fetches its token through cmempy
    context = TestExecutionContext()

    def fail(*_args: object, **_kwargs: object) -> NoReturn:
        raise AssertionError("plugin used cmempy instead of the context client")

    # _request is the funnel of every cmempy HTTP call; a rename in cmempy makes
    # monkeypatch raise AttributeError here instead of silently disarming this test
    monkeypatch.setattr("cmem.cmempy.api._request", fail)

    plugin = ShaclValidation(
        data_graph_uri="https://vocab.eccenca.com/shacl/",
        shacl_graph_uri=SHACL_GRAPH_URI,
        validation_graph_uri=VALIDATION_GRAPH_URI,
        generate_graph=True,
        output_entities=True,
        clear_validation_graph=True,
    )
    assert plugin.execute(inputs=(), context=context) is not None
