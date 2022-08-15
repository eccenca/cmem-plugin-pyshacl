from validators import url as validator_url
from rdflib import Graph, URIRef, Literal, BNode, RDF, SH, PROV, XSD, RDFS, SKOS, Namespace
from pyshacl import validate
from os import remove
from os.path import getsize
from time import time
from datetime import datetime
from uuid import uuid4
from distutils.util import strtobool
from cmem.cmempy.dp.proxy.graph import get, post_streamed
from cmem_plugin_base.dataintegration.utils import setup_cmempy_super_user_access
from cmem_plugin_base.dataintegration.description import Plugin, PluginParameter
from cmem_plugin_base.dataintegration.types import BoolParameterType, StringParameterType
from cmem_plugin_base.dataintegration.parameter.graph import GraphParameterType, get_graphs_list
from cmem_plugin_base.dataintegration.plugins import WorkflowPlugin
from cmem_plugin_base.dataintegration.entity import Entities, Entity, EntitySchema, EntityPath
from importlib.metadata import version

#using importlib, cmem_plugin_base.__version__ returns "0.1.0"
CMEM_PLUGIN_BASE_VERSION = int(version("cmem-plugin-base").split(".")[0])
if CMEM_PLUGIN_BASE_VERSION > 1:
    from cmem_plugin_base.dataintegration.context import ExecutionContext
else:
    ExecutionContext = lambda: None

SKOSXL = Namespace("http://www.w3.org/2008/05/skos-xl#")
DATA_GRAPH_TYPES = [
                    "https://vocab.eccenca.com/di/Dataset",
                    "http://rdfs.org/ns/void#Dataset",
                    "https://vocab.eccenca.com/shui/ShapeCatalog",
                    "http://www.w3.org/2002/07/owl#Ontology",
                    "https://vocab.eccenca.com/dsm/ThesaurusProject"
]


def et(start):
    return round(time() - start, 3)

def get_label(g, s):
    l = preferredLabel(g, s, labelProperties=(RDFS.label, SKOSXL.prefLabel/SKOSXL.literalForm, SKOS.prefLabel))
    if l:
        return l[0][1]

# from rdflib 6.1.1, function removed in rdflib 6.2.0
def preferredLabel(
        g,
        subject,
        lang=None,
        default=None,
        labelProperties=(SKOS.prefLabel, RDFS.label),
    ):
    if default is None:
        default = []
    # setup the language filtering
    if lang is not None:
        if lang == "":  # we only want not language-tagged literals
            def langfilter(l_):
                return l_.language is None
        else:
            def langfilter(l_):
                return l_.language == lang
    else:  # we don't care about language tags
        def langfilter(l_):
            return True
    for labelProp in labelProperties:
        labels = list(filter(langfilter, g.objects(subject, labelProp)))
        if len(labels) == 0:
            continue
        else:
            return [(labelProp, l_) for l_ in labels]
    return default


@Plugin(
    label="SHACL validation with pySHACL",
    plugin_id="shacl-pyshacl",
    description="Performs SHACL validation with pySHACL.",
    documentation="""Performs SHACL validation with pySHACL.""",
    parameters=[
        PluginParameter(
            param_type = GraphParameterType(classes = DATA_GRAPH_TYPES),
            name="data_graph_uri",
            label="Data graph URI",
            description="Data graph URI, will only list graphs of type di:Dataset, void:Dataset, shui:ShapeCatalog, owl:Ontology, dsm:ThesaurusProject"
        ),
        PluginParameter(
            param_type = GraphParameterType(classes = [
                "https://vocab.eccenca.com/shui/ShapeCatalog"
            ]),
            name="shacl_graph_uri",
            label="SHACL shapes graph URI",
            description="SHACL shapes graph URI, will only list graphs of type shui:ShapeCatalog"
        ),
        PluginParameter(
            param_type = StringParameterType(),
            name="validation_graph_uri",
            label="Validation graph URI",
            description="Validation graph URI",
            default_value=""
        ),
        PluginParameter(
            param_type = BoolParameterType(),
            name="generate_graph",
            label="Generate validation graph",
            description="Generate validation graph",
            default_value=False
        ),
        PluginParameter(
            param_type = BoolParameterType(),
            name="output_values",
            label="Output values",
            description="Output values",
            default_value=False
        ),
        PluginParameter(
            param_type = BoolParameterType(),
            name="clear_validation_graph",
            label="Clear validation graph",
            description="Clear validation graph before workflow execution.",
            default_value=True
        ),
        PluginParameter(
            param_type = BoolParameterType(),
            name="owl_imports_resolution",
            label="Resolve owl:imports",
            description="Resolve graph tree defined via owl:imports.",
            default_value=True,
            advanced=True
        ),
        PluginParameter(
            param_type = BoolParameterType(),
            name="skolemize_validation_graph",
            label="Blank node skolemization",
            description="Skolemize blank nodes in the validation graph into URIs.",
            default_value=True,
            advanced=True
        ),
        PluginParameter(
            param_type = BoolParameterType(),
            name="add_labels_to_validation_graph",
            label="Add labels",
            description="Add labels to validation graph.",
            default_value=True,
            advanced=True
        ),
        PluginParameter(
            param_type = BoolParameterType(),
            name="include_graphs_labels",
            label="Add labels to focus nodes and values",
            description='Add labels from data and SHACL shapes graph to source shapes, focus nodes and values in the validation graph. Only applied when the option "Add labels" is activated.',
            default_value=False,
            advanced=True
        ),
        PluginParameter(
            param_type = BoolParameterType(),
            name="add_shui_conforms_to_validation_graph",
            label="Add shui:conforms flag to focus node resources.",
            description="Add shui:conforms flag to focus node resources.",
            default_value=False,
            advanced=True
        ),
        PluginParameter(
            param_type = BoolParameterType(),
            name="meta_shacl",
            label="Meta-SHACL.",
            description="Validate the SHACL shapes graph against the shacl-shacl shapes graph before validating the data graph.",
            default_value=False,
            advanced=True
        )
    ]
)


class ShaclValidation(WorkflowPlugin):

    def __init__(
        self,
        data_graph_uri,
        shacl_graph_uri,
        generate_graph,
        validation_graph_uri,
        output_values,
        clear_validation_graph,
        owl_imports_resolution,
        skolemize_validation_graph,
        add_labels_to_validation_graph,
        include_graphs_labels,
        add_shui_conforms_to_validation_graph,
        meta_shacl
    ) -> None:
        self.data_graph_uri = data_graph_uri
        self.shacl_graph_uri = shacl_graph_uri
        self.validation_graph_uri = validation_graph_uri
        self.generate_graph = generate_graph
        self.output_values = output_values
        self.owl_imports_resolution = owl_imports_resolution
        self.clear_validation_graph = clear_validation_graph
        self.skolemize_validation_graph = skolemize_validation_graph
        self.add_labels_to_validation_graph = add_labels_to_validation_graph
        self.include_graphs_labels = include_graphs_labels
        self.add_shui_conforms_to_validation_graph = add_shui_conforms_to_validation_graph
        self.meta_shacl = meta_shacl
        self.bool_parameters = [p.name for p in Plugin.plugins[0].parameters if
                                isinstance(p.param_type, BoolParameterType)]
        self.graph_parameters = [p.name for p in Plugin.plugins[0].parameters if
                                 isinstance(p.param_type, GraphParameterType)]
        setup_cmempy_super_user_access()
        if CMEM_PLUGIN_BASE_VERSION < 2:
            self.execute = self.execute_1
        else:
            self.execute = self.execute_2

    def add_prov(self, validation_graph, utctime):
        self.log.info("Adding PROV information validation graph")
        validation_report_uri = validation_graph.value(predicate=RDF.type, object=SH.ValidationReport)
        validation_graph.add((
            validation_report_uri,
            PROV.wasDerivedFrom,
            URIRef(self.data_graph_uri)
        ))
        validation_graph.add((
            validation_report_uri,
            PROV.wasInformedBy,
            URIRef(self.shacl_graph_uri)
        ))
        validation_graph.add((
            validation_report_uri,
            PROV.generatedAtTime,
            Literal(utctime, datatype=XSD.dateTime)
        ))
        return validation_graph

    def add_labels(self, validation_graph, data_graph, shacl_graph, validation_result_uris):
        self.log.info("Adding labels to validation graph")
        focus_nodes = []
        validation_report_uri = validation_graph.value(predicate=RDF.type, object=SH.ValidationReport)
        conforms = validation_graph.value(subject=validation_report_uri, predicate=SH.conforms)
        label = "SHACL validation report, conforms" if conforms == "true" else "SHACL validation report, nonconforms"
        validation_graph.add((validation_report_uri, RDFS.label, Literal(label)))
        for validation_result_uri in validation_result_uris:
            message = str(validation_graph.value(subject=validation_result_uri, predicate=SH.resultMessage))
            result_path = str(validation_graph.value(subject=validation_result_uri, predicate=SH.resultPath)).split("/")[-1]
            label = f"SHACL: {result_path}: {message}"
            validation_graph.add((validation_result_uri, RDFS.label, Literal(label)))
            if self.include_graphs_labels:
                focus_node = validation_graph.value(subject=validation_result_uri, predicate=SH.focusNode)
                if self.add_shui_conforms_to_validation_graph:
                    focus_nodes.append(focus_node)
                label = get_label(data_graph, focus_node)
                if label:
                    validation_graph.add((focus_node, RDFS.label, label))
                value = validation_graph.value(subject=validation_result_uri, predicate=SH.value)
                if value:
                    if isinstance(value, (URIRef, BNode)):
                        label = get_label(data_graph, value)
                        if label:
                            validation_graph.add((value, RDFS.label, label))
                source_shape = validation_graph.value(subject=validation_result_uri, predicate=SH.sourceShape)
                label = get_label(shacl_graph, source_shape)
                if label:
                    validation_graph.add((source_shape, RDFS.label, label))
        return validation_graph, focus_nodes

    def add_shui_conforms(self, validation_graph, validation_result_uris, focus_nodes):
        self.log.info("Adding shui:conforms flags to validation graph")
        itr = focus_nodes if focus_nodes else validation_result_uris
        for i in itr:
            s = i if focus_nodes else validation_graph.value(subject=i, predicate=SH.focusNode)
            validation_graph.add((
                s,
                URIRef("https://vocab.eccenca.com/shui/conforms"),
                Literal(False, datatype=XSD.boolean)
            ))
        return validation_graph

    def post_graph(self, validation_graph):
        self.log.info("Posting SHACL validation graph...")
        temp_file = f"{uuid4()}.nt"
        validation_graph.serialize(temp_file, format="nt", encoding="utf-8")
        self.log.info(f"Created temporary file {temp_file} with size {getsize(temp_file)} bytes")
        res = post_streamed(
            self.validation_graph_uri,
            temp_file,
            replace=self.clear_validation_graph,
            content_type="application/n-triples"
        )
        remove(temp_file)
        self.log.info(f"Deleted temporary file")
        if res.status_code == 204:
            self.log.info("Successfully posted SHACL validation graph")
        else:
            self.log.info(f"Error posting SHACL validation graph: status code {res.status_code}")

    def check_object(self, g, s, p, data_graph, shacl_graph):
        if p in (SH.sourceShape, SH.conforms):
            label_g = shacl_graph
        elif p in (SH.value, SH.resultPath, SH.focusNode):
            label_g = data_graph
        l = g.value(subject=s, predicate=p)
        o = l if l else None
        v = ""
        if o:
            if isinstance(o, URIRef):
                if self.include_graphs_labels and p not in (SH.sourceConstraintComponent, SH.resultSeverity):
                    label = get_label(label_g, o)
                    v = str(label) if label else o
                else:
                    v = o
            elif isinstance(o, BNode):
                if self.include_graphs_labels:
                    label = get_label(label_g, o)
                    if label:
                        v = str(label)
                if not v:
                    # first 50 lines of turtle CBD
                    v = g.cbd(o).serialize(format="turtle")
                    cbd_lines = v.split("\n")
                    if len(cbd_lines) > 50:
                        v = "\n".join(cbd_lines[:50]) + "\n..."
            elif isinstance(o, Literal):
                if p == SH.value:
                    v = f'"{o}"^^<{o.datatype}>' if o.datatype else f'"{o}"'
                elif p == SH.resultMessage:
                    v = str(o)
        return v

    def make_entities(self, validation_graph, data_graph, shacl_graph, utctime):
        self.log.info("Creating entities")
        shp = [
            "focusNode",
            "resultPath",
            "value",
            "sourceShape",
            "sourceConstraintComponent",
            # "detail",
            "resultMessage",
            "resultSeverity"
        ]
        entities =[]
        conforms = list(validation_graph.objects(predicate=SH.conforms))[0]
        for validation_result in list(validation_graph.subjects(RDF.type, SH.ValidationResult)):
            values = [[self.check_object(validation_graph, validation_result, SH[p], data_graph, shacl_graph)] for p in shp] + [
                [conforms],
                [self.data_graph_uri],
                [self.shacl_graph_uri],
                [utctime]
            ]
            entities.append(Entity(uri=validation_result, values=values))
        paths = [EntityPath(path=SH[p]) for p in shp] + [
                    EntityPath(path=SH.conforms),
                    EntityPath(path=PROV.wasDerivedFrom),
                    EntityPath(path=PROV.wasInformedBy),
                    EntityPath(path=PROV.generatedAtTime)
                ]
        return Entities(entities=entities, schema=EntitySchema(type_uri=SH.ValidationResult, paths=paths))

    def get_graph(self, i):
        g = Graph()
        g.parse(data=get(i, owl_imports_resolution=self.owl_imports_resolution).text, format="turtle")
        return g

    def process_inputs(self, inputs):
        paths = [e.path for e in inputs[0].schema.paths]
        values = [e[0] for e in list(inputs[0].entities)[0].values]
        for p, v in zip(paths, values):
            if p not in self.graph_parameters + self.bool_parameters:
               raise ValueError(f"Invalid parameter: {p}")
            self.__dict__[p] = v
            self.log.info(f"input parameter {p}: {v}")

    def check_parameters(self):
        self.log.info("Validating parameters...")
        if not self.output_values and not self.generate_graph:
            raise ValueError("Generate validation graph or Output values parameter needs to be set to true")
        if not validator_url(self.data_graph_uri):
            raise ValueError("Data graph URI parameter is invalid")
        if not validator_url(self.shacl_graph_uri):
            raise ValueError("SHACL graph URI parameter is invalid")
        graphs_dict = {g["iri"]:g["assignedClasses"] for g in get_graphs_list()}
        if self.data_graph_uri not in graphs_dict:
            raise ValueError(f"Data graph <{self.data_graph_uri}> not found")
        if self.shacl_graph_uri not in graphs_dict:
            raise ValueError(f"SHACL graph <{self.shacl_graph_uri}> not found")
        if not any(check in graphs_dict[self.data_graph_uri] for check in DATA_GRAPH_TYPES):
            raise ValueError(f"Invalid graph type for data graph <{self.data_graph_uri}>")
        if "https://vocab.eccenca.com/shui/ShapeCatalog" not in graphs_dict[self.shacl_graph_uri]:
            raise ValueError(f"Invalid graph type for SHACL graph <{self.shacl_graph_uri}>")
        for p in self.bool_parameters:
            if not isinstance(self.__dict__[p], bool):
                try:
                    self.__dict__[p] = bool(strtobool(self.__dict__[p]))
                except:
                    raise ValueError(f"Invalid truth value for parameter {p}")
        if self.generate_graph:
            if not validator_url(self.validation_graph_uri):
                raise ValueError("Validation graph URI parameter is invalid")
            if self.validation_graph_uri in graphs_dict:
                self.log.warning(f"Graph <{self.validation_graph_uri}> already exists")
        if not self.add_labels_to_validation_graph:
            self.include_graphs_labels = False
        self.log.info("Parameters OK:")
        for p in self.graph_parameters + self.bool_parameters:
            self.log.info(f"{p}: {self.__dict__[p]}")

    def execute_1(self, inputs=()):
        self.run(inputs)

    def execute_2(self, inputs=(), context: ExecutionContext = ExecutionContext()):
        self.run(inputs)

    def run(self, inputs):
        # accepts only one set of input parameters
        if inputs:
            self.process_inputs(inputs)
        self.check_parameters()
        self.log.info(f"Loading data graph <{self.data_graph_uri}> into memory...")
        start = time()
        data_graph = self.get_graph(self.data_graph_uri)
        self.log.info(f"Finished loading data graph in {et(start)} seconds")
        self.log.info(f"Loading SHACL graph <{self.shacl_graph_uri}> into memory...")
        start = time()
        shacl_graph = self.get_graph(self.shacl_graph_uri)
        self.log.info(f"Finished loading SHACL graph in {et(start)} seconds")
        self.log.info(f"Starting SHACL validation...")
        start = time()
        conforms, validation_graph, results_text = validate(
            data_graph,
            shacl_graph=shacl_graph,
            meta_shacl=self.meta_shacl,
            inplace=True
        )
        self.log.info(f"Finished SHACL validation in {et(start)} seconds")
        utctime = str(datetime.fromtimestamp(int(time()))).replace(" ", "T") + "Z"
        if self.output_values:
            entities = self.make_entities(validation_graph, data_graph, shacl_graph, utctime)
        if self.generate_graph:
            if self.skolemize_validation_graph:
                self.log.info("Skolemizing validation graph")
                validation_graph = validation_graph.skolemize(basepath=self.validation_graph_uri)
            if self.add_labels_to_validation_graph or self.add_shui_conforms_to_validation_graph:
                validation_graph_uris = validation_graph.subjects(RDF.type, SH.ValidationResult)
                focus_nodes = None
                if self.add_labels_to_validation_graph:
                    validation_graph, focus_nodes = self.add_labels(validation_graph, data_graph, shacl_graph, validation_graph_uris)
                if self.add_shui_conforms_to_validation_graph:
                    validation_graph = self.add_shui_conforms(validation_graph, validation_graph_uris, focus_nodes)
            validation_graph = self.add_prov(validation_graph, utctime)
            self.post_graph(validation_graph)
        if self.output_values:
            self.log.info("Outputting entities")
            return entities
