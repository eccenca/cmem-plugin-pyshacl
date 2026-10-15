"""CMEM plugin for SHACl validation using pySHACL"""

import re
import tempfile
from collections import OrderedDict
from collections.abc import Sequence
from datetime import UTC, datetime
from http import HTTPStatus
from importlib.resources import files
from pathlib import Path, PurePosixPath
from tempfile import NamedTemporaryFile
from time import time
from typing import override
from urllib.parse import urlparse

import validators.url
from cmem_client.client import Client
from cmem_client.repositories.graphs import GraphExportConfig
from cmem_client.repositories.protocols.import_item import ImportConflictPolicy
from cmem_plugin_base.dataintegration.context import ExecutionContext
from cmem_plugin_base.dataintegration.description import Icon, Plugin, PluginParameter
from cmem_plugin_base.dataintegration.entity import Entities, Entity, EntityPath, EntitySchema
from cmem_plugin_base.dataintegration.parameter.choice import ChoiceParameterType
from cmem_plugin_base.dataintegration.parameter.graph import GraphParameterType
from cmem_plugin_base.dataintegration.plugins import WorkflowPlugin
from cmem_plugin_base.dataintegration.ports import FixedNumberOfInputs, FixedSchemaPort
from cmem_plugin_base.dataintegration.types import (
    BoolParameterType,
    IntParameterType,
    StringParameterType,
)
from pyshacl import validate
from pyshacl.entrypoints import meta_validate
from pyshacl.extras import check_extra_installed
from rdflib import PROV, RDF, RDFS, SH, SKOS, XSD, BNode, Graph, Literal, Namespace, URIRef
from rdflib.term import Node

SKOSXL = Namespace("http://www.w3.org/2008/05/skos-xl#")
DATA_GRAPH_TYPES = [
    "https://vocab.eccenca.com/di/Dataset",
    "http://rdfs.org/ns/void#Dataset",
    "https://vocab.eccenca.com/shui/ShapeCatalog",
    "http://www.w3.org/2002/07/owl#Ontology",
    "https://vocab.eccenca.com/dsm/ThesaurusProject",
]
CBD_LINES = 50
# the properties of a validation result output as entities, in the order of their paths
RESULT_PROPERTIES = [
    "focusNode",
    "resultPath",
    "value",
    "sourceShape",
    "sourceConstraintComponent",
    "resultMessage",
    "resultSeverity",
]
VALIDATION_RESULT_SCHEMA = EntitySchema(
    type_uri=SH.ValidationResult,
    paths=[EntityPath(path=SH[p]) for p in RESULT_PROPERTIES]
    + [
        EntityPath(path=SH.conforms),
        EntityPath(path=PROV.wasDerivedFrom),
        EntityPath(path=PROV.wasInformedBy),
        EntityPath(path=PROV.generatedAtTime),
    ],
)
# Any IRI of the urn scheme, such as urn:graph - the store needs a valid IRI, not
# an RFC 8141 URN - so only the characters an IRI cannot contain are excluded
URN = re.compile(r'^urn:[^\s<>"{}|\\^`]+$', re.IGNORECASE)


def is_valid_uri(uri: str) -> bool:
    """Check whether a graph IRI typed by the user is a URL or a URN"""
    return bool(validators.url(uri)) or bool(URN.match(uri))


def e_t(start: float) -> float:
    """Calculate rounded elapsed time"""
    return round(time() - start, 3)


def get_label(graph: Graph, subject: URIRef | BNode) -> Node | None:
    """Get preferred label"""
    labels = preferred_label(graph, subject)
    if labels:
        label: Node = labels[0][1]
        return label
    return None


def preferred_label(
    graph: Graph,
    subject: URIRef | BNode,
    lang: str | None = None,
    default: list | None = None,
    label_properties: tuple = (RDFS.label, SKOSXL.prefLabel / SKOSXL.literalForm, SKOS.prefLabel),
) -> list:
    """Adapted from rdflib 6.1.1, removed in rdflib 6.2.0"""
    if default is None:
        default = []
    # setup the language filtering
    if lang is not None:
        if lang == "":  # we only want not language-tagged literals

            def langfilter(lbl: Literal) -> bool:
                return lbl.language is None
        else:

            def langfilter(lbl: Literal) -> bool:
                return lbl.language == lang
    else:  # we don't care about language tags

        def langfilter(lbl: Literal) -> bool:  # noqa: ARG001
            return True

    for label_prop in label_properties:
        labels = list(filter(langfilter, graph.objects(subject, label_prop)))  # type:ignore[arg-type, var-annotated]
        if len(labels) == 0:
            continue
        return [(label_prop, lbl) for lbl in labels]
    return default


@Plugin(
    label="SHACL validation with pySHACL",
    icon=Icon(file_name="pyshacl.svg", package=__package__),
    plugin_id="shacl-pyshacl",
    description="Performs SHACL validation with pySHACL.",
    documentation=files(__package__).joinpath("pyshacl.md").read_text(encoding="utf-8"),
    parameters=[
        PluginParameter(
            param_type=GraphParameterType(classes=DATA_GRAPH_TYPES),
            name="data_graph_uri",
            label="Data graph URI",
            description="The URI of the graph to be validated. The graph URI is "
            "selected from a list of graphs of types `void:Dataset`, "
            "`shui:ShapeCatalog`, `owl:Ontology` and "
            "`dsm:ThesaurusProject`.",
        ),
        PluginParameter(
            param_type=GraphParameterType(classes=["https://vocab.eccenca.com/shui/ShapeCatalog"]),
            name="shacl_graph_uri",
            label="SHACL shapes graph URI",
            description="The URI of the graph containing the SHACL shapes to be "
            "validated against. The graph URI is selected from a list of "
            "graphs of type `shui:ShapeCatalog`.",
        ),
        PluginParameter(
            param_type=StringParameterType(),
            name="validation_graph_uri",
            label="Validation graph URI",
            description="If the `Generate validation graph` option is enabled, the validation "
            "graph is posted to the graph with this URI.",
            default_value="",
        ),
        PluginParameter(
            param_type=BoolParameterType(),
            name="generate_graph",
            label="Generate validation graph",
            description="If enabled, the validation graph is posted to the graph specified with "
            "the `Validation graph URI` option.",
            default_value=False,
        ),
        PluginParameter(
            param_type=BoolParameterType(),
            name="output_entities",
            label="Output entities",
            description="If enabled, the plugin outputs the validation results as "
            "entities and can be connected to, for instance, a CSV "
            "dataset to produce a results table.",
            default_value=False,
        ),
        PluginParameter(
            param_type=BoolParameterType(),
            name="clear_validation_graph",
            label="Clear validation graph",
            description="If enabled, the validation graph is cleared before workflow execution.",
            default_value=True,
        ),
        PluginParameter(
            param_type=BoolParameterType(),
            name="owl_imports",
            label="Resolve owl:imports",
            description="If enabled, the graph tree defined with owl:imports in the "
            "data graph is resolved.",
            default_value=True,
            advanced=True,
        ),
        PluginParameter(
            param_type=BoolParameterType(),
            name="skolemize",
            label="Blank node skolemization",
            description="If enabled, blank nodes in the validation graph are skolemized into URIs.",
            default_value=True,
            advanced=True,
        ),
        PluginParameter(
            param_type=BoolParameterType(),
            name="add_labels",
            label="Add labels",
            description="If enabled, `rdfs:label` triples are added to the validation "
            "graph for instances of `sh:ValidationReport` and "
            "`sh:ValidationResult`.",
            default_value=True,
            advanced=True,
        ),
        PluginParameter(
            param_type=BoolParameterType(),
            name="include_graphs_labels",
            label="Add labels to focus nodes and values",
            description="If enabled along with the `Add labels` option, `rdfs:label` "
            "triples are added for the focus nodes, values and SHACL "
            "shapes in the validation graph. The labels are taken from "
            "the specified data and SHACL graphs.",
            default_value=False,
            advanced=True,
        ),
        PluginParameter(
            param_type=BoolParameterType(),
            name="add_shui_conforms",
            label="Add shui:conforms flag to focus node resources",
            description="If enabled, `shui:conforms false` triples are added to the "
            "focus nodes in the validation graph.",
            default_value=False,
            advanced=True,
        ),
        PluginParameter(
            param_type=BoolParameterType(),
            name="meta_shacl",
            label="Meta-SHACL",
            description="If enabled, the SHACL shapes graph is validated against the "
            "SHACL-SHACL shapes graph before the data graph is loaded. The shapes are checked as "
            "written, without the inference configured for the data graph.",
            default_value=False,
            advanced=True,
        ),
        PluginParameter(
            param_type=GraphParameterType(classes=["http://www.w3.org/2002/07/owl#Ontology"]),
            name="ontology_graph_uri",
            label="Ontology graph URI",
            description="The URI of a graph containing extra ontological information. "
            "RDFS and OWL definitions from this are used to inoculate the "
            "data graph. The graph URI is selected from a list of graphs "
            "of type `owl:Ontology`.",
            default_value="",
            advanced=True,
        ),
        PluginParameter(
            param_type=ChoiceParameterType(
                OrderedDict({"none": "None", "rdfs": "RDFS", "owlrl": "OWLRL", "both": "Both"})
            ),
            name="inference",
            label="Inference",
            description="If enabled, OWL inferencing expansion of the data graph is "
            "performed before validation. Options are RDFS, OWLRL, Both, "
            "None.",
            default_value="none",
            advanced=True,
        ),
        PluginParameter(
            param_type=BoolParameterType(),
            name="advanced",
            label="SHACL advanced features",
            description="Enable SHACL advanced features.",
            default_value=False,
            advanced=True,
        ),
        PluginParameter(
            param_type=BoolParameterType(),
            name="js",
            label="SHACL-JS features",
            description="If enabled, SHACL-JS constraints in the SHACL shapes graph are "
            "evaluated. JavaScript targets, functions and rules are only evaluated if `SHACL "
            "advanced features` is enabled as well. The JavaScript code is read from the file "
            "resources of the project, so every `sh:jsLibraryURL` must be a path relative to "
            "them, such as `js/constraints.js`.",
            default_value=False,
            advanced=True,
        ),
        PluginParameter(
            param_type=BoolParameterType(),
            name="remove_dataset_graph_type",
            label="Remove graph type http://rdfs.org/ns/void#Dataset from data graph",
            description="Before validating, remove the triple `<data_graph_uri> a "
            "<http://rdfs.org/ns/void#Dataset>` from the in-memory data graph.",
            default_value=False,
            advanced=True,
        ),
        PluginParameter(
            param_type=BoolParameterType(),
            name="remove_thesaurus_graph_type",
            label="Remove graph type https://vocab.eccenca.com/dsm/ThesaurusProject "
            "from data graph",
            description="Before validating, remove the triple `<data_graph_uri> a "
            "<https://vocab.eccenca.com/dsm/ThesaurusProject>` from the in-memory data "
            "graph.",
            default_value=False,
            advanced=True,
        ),
        PluginParameter(
            param_type=BoolParameterType(),
            name="remove_shape_catalog_graph_type",
            label="Remove graph type https://vocab.eccenca.com/shui/ShapeCatalog from data graph",
            description="Before validating, remove the triple `<data_graph_uri> a "
            "<https://vocab.eccenca.com/shui/ShapeCatalog>` from the in-memory data "
            "graph.",
            default_value=False,
            advanced=True,
        ),
        PluginParameter(
            param_type=IntParameterType(),
            name="max_validation_depth",
            label="Maximum validation depth",
            description="The maximum number of nested shapes the validator follows, between 1 and "
            "999. If the shapes nest deeper, validation fails with `Validation path too deep`.",
            default_value=15,
            advanced=True,
        ),
    ],
)
class ShaclValidation(WorkflowPlugin):
    """Plugin class"""

    def __init__(  # noqa: PLR0913 PLR0917
        self,
        data_graph_uri: str,
        shacl_graph_uri: str,
        ontology_graph_uri: str = "",
        generate_graph: bool = False,
        validation_graph_uri: str = "",
        output_entities: bool = False,
        clear_validation_graph: bool = True,
        owl_imports: bool = True,
        skolemize: bool = True,
        add_labels: bool = True,
        include_graphs_labels: bool = False,
        add_shui_conforms: bool = False,
        meta_shacl: bool = False,
        inference: str = "none",
        advanced: bool = False,
        js: bool = False,
        remove_dataset_graph_type: bool = False,
        remove_thesaurus_graph_type: bool = False,
        remove_shape_catalog_graph_type: bool = False,
        max_validation_depth: int = 15,
    ) -> None:
        self.data_graph_uri = data_graph_uri
        self.shacl_graph_uri = shacl_graph_uri
        self.ontology_graph_uri = ontology_graph_uri
        self.validation_graph_uri = validation_graph_uri
        self.generate_graph = generate_graph
        self.output_entities = output_entities
        self.owl_imports = owl_imports
        self.clear_validation_graph = clear_validation_graph
        self.skolemize = skolemize
        self.add_labels = add_labels
        self.include_graphs_labels = include_graphs_labels
        self.add_shui_conforms = add_shui_conforms
        self.meta_shacl = meta_shacl
        self.inference = inference
        self.advanced = advanced
        self.js = js
        self.remove_dataset_graph_type = remove_dataset_graph_type
        self.remove_thesaurus_graph_type = remove_thesaurus_graph_type
        self.remove_shape_catalog_graph_type = remove_shape_catalog_graph_type
        self.max_validation_depth = max_validation_depth
        self.input_ports = FixedNumberOfInputs([])
        self.output_port = (
            FixedSchemaPort(schema=VALIDATION_RESULT_SCHEMA) if output_entities else None
        )

    def add_prov(self, validation_graph: Graph, utctime: str) -> Graph:
        """Add provenance data"""
        self.log.info("Adding PROV information validation graph")
        validation_report_uri = validation_graph.value(
            predicate=RDF.type, object=SH.ValidationReport
        )
        if validation_report_uri:
            validation_graph.add(
                (validation_report_uri, PROV.wasDerivedFrom, URIRef(self.data_graph_uri))
            )
            validation_graph.add(
                (validation_report_uri, PROV.wasInformedBy, URIRef(self.shacl_graph_uri))
            )
            validation_graph.add(
                (
                    validation_report_uri,
                    PROV.generatedAtTime,
                    Literal(utctime, datatype=XSD.dateTime),
                )
            )

        return validation_graph

    def add_labels_val(
        self,
        validation_graph: Graph,
        data_graph: Graph,
        shacl_graph: Graph,
        validation_result_uris: list,
    ) -> tuple:
        """Add labels"""
        self.log.info("Adding labels to validation graph")
        focus_nodes = []
        validation_report_uri = validation_graph.value(
            predicate=RDF.type, object=SH.ValidationReport
        )
        conforms = validation_graph.value(subject=validation_report_uri, predicate=SH.conforms)
        report_label = f"SHACL validation report, conforms={conforms!s}"
        if validation_report_uri:
            validation_graph.add((validation_report_uri, RDFS.label, Literal(report_label)))
        for validation_result_uri in validation_result_uris:
            message = str(
                validation_graph.value(subject=validation_result_uri, predicate=SH.resultMessage)
            )
            result_path = validation_graph.value(
                subject=validation_result_uri, predicate=SH.resultPath
            )
            result_path_string = f"{result_path}: " if result_path else ""
            result_label = Literal(f"SHACL: {result_path_string}{message}")
            validation_graph.add((validation_result_uri, RDFS.label, result_label))
            if self.include_graphs_labels:
                focus_node = validation_graph.value(
                    subject=validation_result_uri, predicate=SH.focusNode
                )
                if self.add_shui_conforms:
                    focus_nodes.append(focus_node)
                label = get_label(data_graph, focus_node)
                if label and focus_node:
                    validation_graph.add((focus_node, RDFS.label, label))
                value = validation_graph.value(subject=validation_result_uri, predicate=SH.value)
                if value and isinstance(value, URIRef | BNode):
                    label = get_label(data_graph, value)
                    if label:
                        validation_graph.add((value, RDFS.label, label))
                source_shape = validation_graph.value(
                    subject=validation_result_uri, predicate=SH.sourceShape
                )
                label = get_label(shacl_graph, source_shape)
                if label:
                    validation_graph.add((source_shape, RDFS.label, label))
        return validation_graph, focus_nodes

    def add_shui_conforms_val(
        self, validation_graph: Graph, validation_result_uris: list, focus_nodes: list
    ) -> Graph:
        """Add shui conforms flag"""
        self.log.info("Adding shui:conforms flags to validation graph")
        itr = focus_nodes or validation_result_uris
        for i in itr:
            subj = i if focus_nodes else validation_graph.value(subject=i, predicate=SH.focusNode)
            validation_graph.add(
                (
                    subj,
                    URIRef("https://vocab.eccenca.com/shui/conforms"),
                    Literal(False, datatype=XSD.boolean),
                )
            )
        return validation_graph

    def post_graph(self, client: Client, validation_graph: Graph) -> None:
        """Post validation graph to cmem"""
        self.log.info("Posting SHACL validation graph...")
        with NamedTemporaryFile(suffix=".nt", delete=True) as temp:
            validation_graph.serialize(temp.name, format="nt", encoding="utf-8")

            client.graphs.import_item(
                path=Path(temp.name),
                key=self.validation_graph_uri,
                on_conflict=(
                    ImportConflictPolicy.REPLACE
                    if self.clear_validation_graph
                    else ImportConflictPolicy.FAIL
                ),
            )

    def check_object(  # noqa: C901 PLR0912
        self, graph: Graph, subj: Node, pred: URIRef, data_graph: Graph, shacl_graph: Graph
    ) -> str:
        """Format RDF objects for entities output"""
        if pred in (SH.sourceShape, SH.conforms):
            label_g = shacl_graph
        elif pred in (SH.value, SH.resultPath, SH.focusNode):
            label_g = data_graph
        val = graph.value(subject=subj, predicate=pred)
        obj = val or None
        res_val = ""
        if obj:
            if isinstance(obj, URIRef):
                if self.include_graphs_labels and pred not in (
                    SH.sourceConstraintComponent,
                    SH.resultSeverity,
                ):
                    label = get_label(label_g, obj)
                    res_val = str(label) if label else obj
                else:
                    res_val = obj
            elif isinstance(obj, BNode):
                if self.include_graphs_labels:
                    label = get_label(label_g, obj)
                    if label:
                        res_val = str(label)
                if not res_val:
                    # first CBD_LINES lines of turtle CBD
                    res_val = graph.cbd(obj).serialize(format="turtle")
                    cbd_lines = res_val.split("\n")
                    if len(cbd_lines) > CBD_LINES:
                        res_val = "\n".join(cbd_lines[:CBD_LINES]) + "\n..."
            elif isinstance(obj, Literal):
                if pred == SH.value:
                    res_val = f'"{obj}"^^<{obj.datatype}>' if obj.datatype else f'"{obj}"'
                elif pred == SH.resultMessage:
                    res_val = str(obj)
        return res_val

    def make_entities(
        self, validation_graph: Graph, data_graph: Graph, shacl_graph: Graph, utctime: str
    ) -> Entities:
        """Create entities"""
        self.log.info("Creating entities")
        entities = []
        conforms = next(iter(validation_graph.objects(predicate=SH.conforms)))
        for validation_result in list(validation_graph.subjects(RDF.type, SH.ValidationResult)):
            values = [
                [
                    self.check_object(
                        validation_graph, validation_result, SH[p], data_graph, shacl_graph
                    )
                ]
                for p in RESULT_PROPERTIES
            ] + [[conforms], [self.data_graph_uri], [self.shacl_graph_uri], [utctime]]
            entities.append(Entity(uri=validation_result, values=values))
        return Entities(entities=entities, schema=VALIDATION_RESULT_SCHEMA)

    def get_graph(self, client: Client, uri: str) -> Graph:
        """Get graph from cmem"""
        graph = Graph()
        with tempfile.NamedTemporaryFile(suffix=".ttl", delete=True) as tmp:
            path = client.graphs.export_item(
                key=uri,
                path=Path(tmp.name),
                replace=True,
                configuration=GraphExportConfig(resolve_owl_imports=self.owl_imports),
            )
            data = path.read_text()
            graph.parse(data=data, format="turtle")
            return graph

    def check_parameters(self, client: Client) -> None:  # noqa: C901 PLR0912
        """Validate plugin parameters"""
        self.log.info("Validating parameters...")
        if not self.output_entities and not self.generate_graph:
            raise ValueError(
                "Generate validation graph or Output values parameter needs to be set to true"
            )
        # The data, SHACL and ontology graphs must exist, which is checked below, so
        # their IRIs need no syntax check - it could only reject a graph the store holds.
        graphs_dict = {iri: graph.assigned_classes for iri, graph in client.graphs.items()}

        if self.ontology_graph_uri:
            if self.ontology_graph_uri not in graphs_dict:
                raise ValueError(f"Ontology graph <{self.ontology_graph_uri}> not found")
            if "http://www.w3.org/2002/07/owl#Ontology" not in graphs_dict[self.ontology_graph_uri]:
                raise ValueError(
                    f"Invalid graph type for Ontology graph <{self.ontology_graph_uri}>"
                )

        if self.data_graph_uri not in graphs_dict:
            raise ValueError(f"Data graph <{self.data_graph_uri}> not found")
        if self.shacl_graph_uri not in graphs_dict:
            raise ValueError(f"SHACL graph <{self.shacl_graph_uri}> not found")
        if not any(check in graphs_dict[self.data_graph_uri] for check in DATA_GRAPH_TYPES):
            raise ValueError(f"Invalid graph type for data graph <{self.data_graph_uri}>")
        if "https://vocab.eccenca.com/shui/ShapeCatalog" not in graphs_dict[self.shacl_graph_uri]:
            raise ValueError(f"Invalid graph type for SHACL graph <{self.shacl_graph_uri}>")
        if self.generate_graph:
            if not is_valid_uri(self.validation_graph_uri):
                raise ValueError("Validation graph URI parameter is neither a URL nor a URN")
            if self.validation_graph_uri in graphs_dict:
                self.log.warning(f"Graph <{self.validation_graph_uri}> already exists")
        if not self.add_labels:
            self.include_graphs_labels = False

        if self.inference not in ("none", "rdfs", "owlrl", "both"):
            raise ValueError("Invalid value for inference parameter")

        if self.max_validation_depth not in range(1, 1000):
            raise ValueError("Invalid value for maximum validation depth")

        # Without its JavaScript engine pySHACL skips SHACL-JS with no more than a Python
        # warning, so a graph violating a JavaScript constraint would be reported as conforming
        if self.js and not check_extra_installed("js"):
            raise ValueError(
                "SHACL-JS features are enabled, but the JavaScript engine pySHACL needs for "
                "them (pyduktape2) is not installed"
            )

    def js_library_path(self, url: str) -> PurePosixPath:
        """Check that a SHACL-JS library URL is a path inside the project file resources"""
        path = PurePosixPath(url)
        if urlparse(url).scheme or path.is_absolute() or ".." in path.parts or not path.name:
            raise ValueError(
                f"JavaScript file {url!r} is not a path relative to the project file resources, "
                "such as js/constraints.js"
            )
        return path

    def read_project_file(self, client: Client, project_id: str, path: PurePosixPath) -> bytes:
        """Read a file from the file resources of a project"""
        # the files endpoint itself, since client.files first lists the file resources of every
        # project in the workspace, two plus one request per project, before reading one file
        url = client.config.url_build_api / "workspace/projects" / project_id / "files"
        response = client.http.get(url=url, params={"path": str(path)})
        if response.status_code == HTTPStatus.NOT_FOUND:
            raise ValueError(
                f"JavaScript file {path} not found in the file resources of project {project_id}"
            )
        response.raise_for_status()
        content: bytes = response.content
        return content

    def meta_validate_shapes(self, shacl_graph: Graph) -> None:
        """Validate the shapes graph against SHACL-SHACL, if Meta-SHACL is enabled"""
        if not self.meta_shacl:
            return
        self.log.info("Validating SHACL graph against SHACL-SHACL...")
        # pySHACL's own meta_shacl option applies the inference configured for the data graph
        # to the shapes graph as well, and OWL-RL inference turns the blank nodes of valid
        # property paths such as sh:inversePath into ones SHACL-SHACL rejects
        conforms, _report, text = meta_validate(shacl_graph, inference="none")
        if not conforms:
            raise ValueError(
                f"SHACL graph <{self.shacl_graph_uri}> does not conform to SHACL-SHACL.\n{text}"
            )

    def read_js_libraries(
        self, client: Client, project_id: str, shacl_graph: Graph
    ) -> dict[str, bytes]:
        """Read the SHACL-JS libraries of the shapes graph from the project files, if enabled

        Called before the data graph is loaded, so a malformed path or a missing file fails the
        task before the largest download.
        """
        if not self.js:
            return {}
        libraries: dict[str, bytes] = {}
        for url in map(str, shacl_graph.objects(None, SH.jsLibraryURL)):
            if url not in libraries:
                path = self.js_library_path(url)
                self.log.info(f"Loading JavaScript file {path} from project {project_id}")
                libraries[url] = self.read_project_file(client, project_id, path)
        if not libraries:
            self.log.warning(
                "SHACL-JS features are enabled, but the SHACL shapes graph references no "
                "JavaScript files"
            )
        return libraries

    def write_js_libraries(
        self, shacl_graph: Graph, libraries: dict[str, bytes], directory: Path
    ) -> None:
        """Point the SHACL-JS libraries of the shapes graph to local copies in the directory"""
        copies: dict[str, str] = {}
        for url, content in libraries.items():
            copy = directory.joinpath(*self.js_library_path(url).parts)
            copy.parent.mkdir(parents=True, exist_ok=True)
            copy.write_bytes(content)
            copies[url] = copy.as_uri()
        for node, value in list(shacl_graph.subject_objects(SH.jsLibraryURL)):
            shacl_graph.remove((node, SH.jsLibraryURL, value))
            shacl_graph.add((node, SH.jsLibraryURL, Literal(copies[str(value)])))

    def validate_graphs(
        self,
        data_graph: Graph,
        shacl_graph: Graph,
        ontology_graph: Graph | None,
        js_libraries: dict[str, bytes],
    ) -> Graph:
        """Validate the data graph and return the validation graph"""
        validation_graph: Graph
        with tempfile.TemporaryDirectory() as js_directory:
            if self.js:
                self.write_js_libraries(shacl_graph, js_libraries, Path(js_directory))
            self.log.info("Starting SHACL validation...")
            start = time()
            _conforms, validation_graph, _results_text = validate(
                data_graph=data_graph,
                shacl_graph=shacl_graph,
                ont_graph=ontology_graph,
                inference=self.inference,
                advanced=self.advanced,
                js=self.js,
                max_validation_depth=self.max_validation_depth,
                inplace=True,
            )
            self.log.info(f"Finished SHACL validation in {e_t(start)} seconds")
        return validation_graph

    def complete_validation_graph(
        self, validation_graph: Graph, data_graph: Graph, shacl_graph: Graph, utctime: str
    ) -> Graph:
        """Skolemize the validation graph and add labels, shui:conforms flags and provenance"""
        if self.skolemize:
            self.log.info("Skolemizing validation graph")
            validation_graph = validation_graph.skolemize(basepath=self.validation_graph_uri)
        if self.add_labels or self.add_shui_conforms:
            # a list, since adding labels and adding shui:conforms flags both iterate it
            validation_result_uris = list(validation_graph.subjects(RDF.type, SH.ValidationResult))
            focus_nodes = []
            if self.add_labels:
                validation_graph, focus_nodes = self.add_labels_val(
                    validation_graph, data_graph, shacl_graph, validation_result_uris
                )
            if self.add_shui_conforms:
                validation_graph = self.add_shui_conforms_val(
                    validation_graph, validation_result_uris, focus_nodes
                )
        return self.add_prov(validation_graph, utctime)

    def remove_graph_type(self, data_graph: Graph, iri: str) -> None:
        """Remove triple <data_graph_uri> a <iri>"""
        self.log.info(f"Removing graph type <{iri}> from data graph")
        data_graph.remove((URIRef(self.data_graph_uri), RDF.type, URIRef(iri)))

    @override
    def execute(self, inputs: Sequence, context: ExecutionContext) -> Entities | None:
        """Execute plugin"""
        client = Client.from_context(context=context)
        self.check_parameters(client=client)
        # the shapes graph first, with its Meta-SHACL check and its JavaScript files, so that
        # problems with them are reported before the data graph, usually the largest download
        self.log.info(f"Loading SHACL graph <{self.shacl_graph_uri}> into memory...")
        start = time()
        shacl_graph = self.get_graph(client=client, uri=self.shacl_graph_uri)
        self.log.info(f"Finished loading SHACL graph in {e_t(start)} seconds")
        self.meta_validate_shapes(shacl_graph)
        js_libraries = self.read_js_libraries(client, context.task.project_id(), shacl_graph)

        self.log.info(f"Loading data graph <{self.data_graph_uri}> into memory...")
        start = time()
        data_graph = self.get_graph(client=client, uri=self.data_graph_uri)
        self.log.info(f"Finished loading data graph in {e_t(start)} seconds")

        if self.remove_dataset_graph_type:
            self.remove_graph_type(data_graph, "http://rdfs.org/ns/void#Dataset")
        if self.remove_thesaurus_graph_type:
            self.remove_graph_type(data_graph, "https://vocab.eccenca.com/dsm/ThesaurusProject")
        if self.remove_shape_catalog_graph_type:
            self.remove_graph_type(data_graph, "https://vocab.eccenca.com/shui/ShapeCatalog")

        if self.ontology_graph_uri:
            self.log.info(f"Loading ontology graph <{self.ontology_graph_uri}> into memory...")
            start = time()
            ontology_graph = self.get_graph(client=client, uri=self.ontology_graph_uri)
            self.log.info(f"Finished loading ontology graph in {e_t(start)} seconds")
        else:
            ontology_graph = None

        validation_graph = self.validate_graphs(
            data_graph, shacl_graph, ontology_graph, js_libraries
        )
        utctime = str(datetime.fromtimestamp(int(time()), tz=UTC))[:-6].replace(" ", "T") + "Z"
        if self.output_entities:
            entities = self.make_entities(validation_graph, data_graph, shacl_graph, utctime)
        if self.generate_graph:
            validation_graph = self.complete_validation_graph(
                validation_graph, data_graph, shacl_graph, utctime
            )
            self.post_graph(client=client, validation_graph=validation_graph)

        if self.output_entities:
            self.log.info("Outputting entities")
            return entities
        return None
