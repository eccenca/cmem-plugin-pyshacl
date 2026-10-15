"""Plugin tests."""

import inspect
import logging
import tempfile
from collections.abc import Generator
from dataclasses import dataclass
from os import environ
from pathlib import Path, PurePosixPath
from tempfile import NamedTemporaryFile
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, NoReturn, cast

import pyshacl
import pytest
from cmem_client.client import Client
from cmem_client.exceptions import FilesNotFoundError
from cmem_client.models.project import Project
from cmem_client.repositories.protocols.import_item import ImportConflictPolicy
from cmem_plugin_base.testing import TestExecutionContext
from rdflib import PROV, RDF, RDFS, SH, XSD, BNode, Graph, Literal, Namespace, URIRef
from rdflib.compare import similar

from cmem_plugin_pyshacl import plugin_pyshacl
from cmem_plugin_pyshacl.plugin_pyshacl import ShaclValidation

from . import __path__

if TYPE_CHECKING:
    from cmem_plugin_base.dataintegration.context import ExecutionContext

UUID4 = "b36254a836e04279aecf411d2c8e364a"
SHACL_GRAPH_URI = f"https://example.org/pyshacl-plugin-test/{UUID4}"
VALIDATION_GRAPH_URI = f"https://example.org/pyshacl-plugin-test/{UUID4}"

EX = Namespace("https://example.org/pyshacl-plugin-test/vocab#")
SHUI = Namespace("https://vocab.eccenca.com/shui/")

DATA_GRAPH_URI = f"https://example.org/pyshacl-plugin-test/data/{UUID4}"
SHAPES_GRAPH_URI = f"https://example.org/pyshacl-plugin-test/shapes/{UUID4}"
ONTOLOGY_GRAPH_URI = f"https://example.org/pyshacl-plugin-test/ontology/{UUID4}"
REPORT_GRAPH_URI = f"https://example.org/pyshacl-plugin-test/report/{UUID4}"
URN_DATA_GRAPH_URI = f"urn:pyshacl-plugin-test:data:{UUID4}"
PORT_DATA_GRAPH_URI = f"http://localhost:8080/pyshacl-plugin-test/data/{UUID4}"

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

# the validation graph test_workflow_execution expects, without its prov:generatedAtTime
EXPECTED_REPORT_TTL = f"""
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .

[] a sh:ValidationReport ;
    rdfs:label "SHACL validation report, conforms=true" ;
    prov:wasDerivedFrom <https://vocab.eccenca.com/shacl/> ;
    prov:wasInformedBy <{SHACL_GRAPH_URI}> ;
    sh:conforms true .
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
        test = Graph().parse(data=EXPECTED_REPORT_TTL, format="turtle")

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
    URN_DATA_GRAPH_URI: StubGraph(["http://rdfs.org/ns/void#Dataset"]),
    PORT_DATA_GRAPH_URI: StubGraph(["http://rdfs.org/ns/void#Dataset"]),
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
        # an existing graph needs no syntax check, so a malformed IRI is simply not found
        ({"data_graph_uri": "no uri"}, "Data graph <no uri> not found"),
        ({"shacl_graph_uri": "no uri"}, "SHACL graph <no uri> not found"),
        ({"ontology_graph_uri": "no uri"}, "Ontology graph <no uri> not found"),
        ({"ontology_graph_uri": "https://example.org/missing"}, "Ontology graph .* not found"),
        ({"ontology_graph_uri": DATA_GRAPH_URI}, "Invalid graph type for Ontology graph"),
        ({"data_graph_uri": "https://example.org/missing"}, "Data graph .* not found"),
        ({"shacl_graph_uri": "https://example.org/missing"}, "SHACL graph .* not found"),
        ({"data_graph_uri": REPORT_GRAPH_URI}, "Invalid graph type for data graph"),
        ({"shacl_graph_uri": DATA_GRAPH_URI}, "Invalid graph type for SHACL graph"),
        ({"validation_graph_uri": "no uri"}, "Validation graph URI .* neither a URL nor a URN"),
        ({"validation_graph_uri": "urn:example:has space"}, "neither a URL nor a URN"),
        ({"inference": "sometimes"}, "Invalid value for inference parameter"),
        ({"max_validation_depth": 0}, "Invalid value for maximum validation depth"),
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
        {"data_graph_uri": URN_DATA_GRAPH_URI},
        {"data_graph_uri": PORT_DATA_GRAPH_URI},
        {"validation_graph_uri": f"urn:pyshacl-plugin-test:report:{UUID4}"},
        {"validation_graph_uri": "urn:uuid:6e8bc430-9c3a-11d9-9669-0800200c9a66"},
    ],
)
def test_check_parameters_accepts_graph_iris(overrides: dict[str, Any]) -> None:
    """Test that existing graphs of any IRI form and new URN validation graphs are accepted"""
    plugin = ShaclValidation(**{**VALID_PARAMETERS, **overrides})
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


JS_SHAPES_GRAPH_URI = f"https://example.org/pyshacl-plugin-test/js-shapes/{UUID4}"
JS_DATA_GRAPH_URI = f"https://example.org/pyshacl-plugin-test/js-data/{UUID4}"
JS_PROJECT_ID = f"pyshacl-plugin-test-{UUID4}"
# the library as the shapes reference it, a file resource of the project
JS_LIBRARY = "js/names.js"
JS_LIBRARY_FILE = Path(__path__[0]) / "shacl_js" / "names.js"

# ex:bob violates the JavaScript constraint in shacl_js/names.js, ex:alice does not
JS_SHAPES_TTL = f"""
@prefix ex: <{EX}> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix shui: <{SHUI}> .

<{JS_SHAPES_GRAPH_URI}> a shui:ShapeCatalog .

ex:CapitalisedNameShape a sh:NodeShape ;
    sh:targetClass ex:Person ;
    sh:js [
        a sh:JSConstraint ;
        sh:jsFunctionName "hasCapitalisedName" ;
        sh:jsLibrary [ sh:jsLibraryURL "{JS_LIBRARY}" ]
    ] .
"""

JS_DATA_TTL = f"""
@prefix ex: <{EX}> .
@prefix void: <http://rdfs.org/ns/void#> .

<{JS_DATA_GRAPH_URI}> a void:Dataset .

ex:alice a ex:Person ; ex:name "Alice" .
ex:bob a ex:Person ; ex:name "bob" .
"""


@pytest.mark.parametrize("js", [False, True])
def test_js_constraints_are_evaluated(js: bool, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that SHACL-JS constraints are evaluated from project files if SHACL-JS is enabled"""
    read: list[tuple[str, str]] = []

    def read_project_file(_self: object, _client: object, project_id: str, path: object) -> bytes:
        read.append((project_id, str(path)))
        return JS_LIBRARY_FILE.read_bytes()

    monkeypatch.setattr(ShaclValidation, "read_project_file", read_project_file)
    plugin = ShaclValidation(
        data_graph_uri=JS_DATA_GRAPH_URI, shacl_graph_uri=JS_SHAPES_GRAPH_URI, js=js
    )
    shapes = Graph().parse(data=JS_SHAPES_TTL, format="turtle")
    js_libraries = plugin.read_js_libraries(cast("Client", None), JS_PROJECT_ID, shapes)
    report = plugin.validate_graphs(
        data_graph=Graph().parse(data=JS_DATA_TTL, format="turtle"),
        shacl_graph=shapes,
        ontology_graph=None,
        js_libraries=js_libraries,
    )

    results = list(report.subjects(RDF.type, SH.ValidationResult))
    if not js:
        assert results == []  # the JavaScript constraint is skipped
        assert read == []  # and its JavaScript file never read
        return
    assert read == [(JS_PROJECT_ID, JS_LIBRARY)]
    (result,) = results
    assert report.value(result, SH.focusNode) == EX.bob
    assert "does not start with a capital letter" in str(report.value(result, SH.resultMessage))


@pytest.mark.parametrize(
    "url",
    [
        "https://example.org/js/names.js",
        "http://example.org/js/names.js",
        "file:///tmp/js/names.js",
        "/js/names.js",
        "../names.js",
        "js/../../names.js",
        "",
    ],
)
def test_js_library_outside_project_files_rejected(url: str) -> None:
    """Test that a JavaScript file must be a path relative to the project file resources"""
    shapes = Graph()
    shapes.add((BNode(), SH.jsLibraryURL, Literal(url)))
    plugin = ShaclValidation(**{**VALID_PARAMETERS, "js": True})
    with pytest.raises(ValueError, match="not a path relative to the project file resources"):
        plugin.read_js_libraries(cast("Client", None), JS_PROJECT_ID, shapes)


def test_js_without_libraries_warns(caplog: pytest.LogCaptureFixture) -> None:
    """Test that enabled SHACL-JS warns if the shapes graph references no JavaScript file"""
    plugin = ShaclValidation(**{**VALID_PARAMETERS, "js": True})
    shapes = Graph().parse(data=SHAPES_TTL, format="turtle")
    with caplog.at_level(logging.WARNING):
        assert plugin.read_js_libraries(cast("Client", None), JS_PROJECT_ID, shapes) == {}
    assert "references no JavaScript files" in caplog.text


def test_missing_js_library_fails_before_data_graph(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that a missing JavaScript file fails execution before the data graph is loaded"""
    loaded: list[str] = []

    def get_graph(_self: object, client: object, uri: str) -> Graph:
        loaded.append(uri)
        return Graph().parse(data=JS_SHAPES_TTL, format="turtle")

    def read_project_file(_self: object, _client: object, project_id: str, path: object) -> bytes:
        raise ValueError(f"JavaScript file {path} not found in project {project_id}")

    monkeypatch.setattr(ShaclValidation, "get_graph", get_graph)
    monkeypatch.setattr(ShaclValidation, "read_project_file", read_project_file)
    monkeypatch.setattr(Client, "from_context", lambda **_: StubClient(STUB_GRAPHS))
    plugin = ShaclValidation(**{**VALID_PARAMETERS, "js": True})
    context = SimpleNamespace(task=SimpleNamespace(project_id=lambda: JS_PROJECT_ID))

    with pytest.raises(ValueError, match="not found"):
        plugin.execute(inputs=(), context=cast("ExecutionContext", context))
    assert loaded == [SHAPES_GRAPH_URI]


def test_missing_js_library_reported() -> None:
    """Test that a JavaScript file missing from the project files is reported with its project"""

    def read(key: str) -> NoReturn:
        raise FilesNotFoundError(f"File not found: {key}")

    client = SimpleNamespace(files=SimpleNamespace(read=read))
    plugin = ShaclValidation(**{**VALID_PARAMETERS, "js": True})
    with pytest.raises(ValueError, match=f"js/missing.js not found .* project {JS_PROJECT_ID}"):
        plugin.read_project_file(
            cast("Client", client), JS_PROJECT_ID, PurePosixPath("js/missing.js")
        )


@pytest.fixture
def _js_setup() -> Generator[None]:
    """Set up a project with a JavaScript library and graphs using it, whatever the last run left"""
    client = Client.from_context(TestExecutionContext())

    def clean_up() -> None:
        client.projects.delete_item(JS_PROJECT_ID, skip_if_missing=True)
        for uri in (JS_DATA_GRAPH_URI, JS_SHAPES_GRAPH_URI):
            client.graphs.delete_item(key=uri, skip_if_missing=True)

    clean_up()
    client.projects.create_item(Project(name=JS_PROJECT_ID))
    client.files.import_item(path=JS_LIBRARY_FILE, key=f"{JS_PROJECT_ID}:{JS_LIBRARY}")
    import_graph(client, JS_SHAPES_GRAPH_URI, JS_SHAPES_TTL)
    import_graph(client, JS_DATA_GRAPH_URI, JS_DATA_TTL)

    yield None

    clean_up()


@needs_cmem
@pytest.mark.usefixtures("_js_setup")
@pytest.mark.parametrize("js", [False, True])
def test_execution_with_js(js: bool) -> None:
    """Test that plugin execution evaluates SHACL-JS from the project files if enabled"""
    plugin = ShaclValidation(
        data_graph_uri=JS_DATA_GRAPH_URI,
        shacl_graph_uri=JS_SHAPES_GRAPH_URI,
        generate_graph=False,
        output_entities=True,
        js=js,
    )
    entities = plugin.execute(inputs=(), context=TestExecutionContext(project_id=JS_PROJECT_ID))

    assert entities is not None
    rows = [[value[0] for value in entity.values] for entity in entities.entities]
    if not js:
        assert rows == []  # the JavaScript constraint is skipped
        return
    assert len(rows) == 1
    assert rows[0][0] == EX.bob
    assert "does not start with a capital letter" in rows[0][5]


@pytest.mark.parametrize("include_graphs_labels", [False, True])
def test_complete_validation_graph_flags_every_focus_node(include_graphs_labels: bool) -> None:
    """Test that shui:conforms flags are added along with labels, with or without graph labels"""
    data = Graph().parse(data=DATA_TTL, format="turtle")
    shapes = Graph().parse(data=SHAPES_TTL, format="turtle")
    _, report, _ = pyshacl.validate(data_graph=data, shacl_graph=shapes, inplace=True)
    plugin = ShaclValidation(
        **{
            **VALID_PARAMETERS,
            "skolemize": False,
            "add_labels": True,
            "include_graphs_labels": include_graphs_labels,
            "add_shui_conforms": True,
        }
    )

    report = plugin.complete_validation_graph(report, data, shapes, "2026-10-15T00:00:00Z")

    flagged = set(report.subjects(SHUI.conforms, Literal(False, datatype=XSD.boolean)))
    # ex:alice, ex:carol and the blank node are the focus nodes of the five results
    assert len(flagged) == 3
    assert {EX.alice, EX.carol} <= flagged


# valid property paths whose blank nodes OWL-RL inference used to make SHACL-SHACL reject
BLANK_NODE_PATHS = [
    "[ sh:inversePath ex:knows ]",
    "[ sh:zeroOrMorePath ex:knows ]",
    "[ sh:alternativePath ( ex:name rdfs:label ) ]",
]


@pytest.mark.parametrize("inference", ["none", "rdfs", "owlrl", "both"])
@pytest.mark.parametrize("path", BLANK_NODE_PATHS)
def test_meta_shacl_accepts_property_paths_with_any_inference(path: str, inference: str) -> None:
    """Test that Meta-SHACL accepts valid property paths, whatever the inference"""
    shapes = Graph().parse(
        data=f"{SHAPES_TTL}\nex:PathShape a sh:NodeShape ; sh:targetClass ex:Person ;\n"
        f"    sh:property [ sh:path {path} ; sh:maxCount 5 ] .\n",
        format="turtle",
    )
    plugin = ShaclValidation(**{**VALID_PARAMETERS, "meta_shacl": True, "inference": inference})

    plugin.meta_validate_shapes(shapes)
    report = plugin.validate_graphs(
        data_graph=Graph().parse(data=DATA_TTL, format="turtle"),
        shacl_graph=shapes,
        ontology_graph=None,
        js_libraries={},
    )

    assert len(list(report.subjects(RDF.type, SH.ValidationResult))) == EXPECTED_VIOLATIONS


@pytest.mark.parametrize("meta_shacl", [False, True])
def test_meta_shacl_rejects_invalid_shapes(meta_shacl: bool) -> None:
    """Test that Meta-SHACL, and only Meta-SHACL, rejects a shapes graph SHACL-SHACL rejects"""
    shapes = Graph().parse(
        data=f"{SHAPES_TTL}\n"
        'ex:BrokenShape a sh:PropertyShape ; sh:path ex:x ; sh:minCount "one" .\n',
        format="turtle",
    )
    plugin = ShaclValidation(**{**VALID_PARAMETERS, "meta_shacl": meta_shacl})
    if not meta_shacl:
        plugin.meta_validate_shapes(shapes)
        return
    with pytest.raises(ValueError, match="does not conform to SHACL-SHACL"):
        plugin.meta_validate_shapes(shapes)


def test_check_parameters_accepts_js() -> None:
    """Test that SHACL-JS can be enabled, since its JavaScript engine is installed"""
    plugin = ShaclValidation(**{**VALID_PARAMETERS, "js": True})
    plugin.check_parameters(client=cast("Client", StubClient(STUB_GRAPHS)))


def test_check_parameters_rejects_js_without_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that enabled SHACL-JS fails instead of being skipped without its JavaScript engine"""
    monkeypatch.setattr(plugin_pyshacl, "check_extra_installed", lambda _: False)
    plugin = ShaclValidation(**{**VALID_PARAMETERS, "js": True})
    with pytest.raises(ValueError, match="pyduktape2"):
        plugin.check_parameters(client=cast("Client", StubClient(STUB_GRAPHS)))


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
