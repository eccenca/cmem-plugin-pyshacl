import validators
from rdflib import Graph, URIRef, Literal, BNode, RDF, SH, PROV, XSD, RDFS, SKOS, Namespace
from pyshacl import validate
from os import remove
from os.path import getsize
from time import time
from datetime import datetime
from uuid import uuid4
from cmem.cmempy.dp.proxy.graph import get, post_streamed
from cmem_plugin_base.dataintegration.utils import setup_cmempy_super_user_access
from cmem_plugin_base.dataintegration.description import Plugin, PluginParameter
from cmem_plugin_base.dataintegration.types import BoolParameterType, StringParameterType
from cmem_plugin_base.dataintegration.parameter.graph import GraphParameterType
from cmem_plugin_base.dataintegration.plugins import WorkflowPlugin
from cmem_plugin_base.dataintegration.entity import (
    Entities, Entity, EntitySchema, EntityPath,
)


@Plugin(
    label="SHACL validation with pySHACL",
    plugin_id="shacl-pyshacl",
    description="Performs SHACL validation with pySHACL.",
    documentation="""This plugin performs SHACL validation with pySHACL.""",
    parameters=[
        PluginParameter(
            param_type = GraphParameterType(classes = [
                "https://vocab.eccenca.com/di/Dataset",
                "http://rdfs.org/ns/void#Dataset",
                "https://vocab.eccenca.com/shui/ShapeCatalog",
                "http://www.w3.org/2002/07/owl#Ontology",
                "https://vocab.eccenca.com/dsm/ThesaurusProject"
            ]),
            name="data_graph_uri",
            label="Data graph URI",
            description="Data graph URI, will only list graphs of type di:Dataset, void:Dataset, shui:ShapeCatalog, owl:Ontology, dsm:ThesaurusProject"
        ),
        PluginParameter(
            param_type = GraphParameterType(classes = [
                "https://vocab.eccenca.com/shui/ShapeCatalog"
            ]),
            name="shacl_graph_uri",
            label="SHACL graph URI",
            description="SHACL graph URI, will only list graphs of type shui:ShapeCatalog"
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
            description="Add RDFS labels to validation graph.",
            default_value=True,
            advanced=True
        ),
        PluginParameter(
            param_type = BoolParameterType(),
            name="include_graphs_labels",
            label="Add labels from data and SHACL graphs",
            description="Include RDFS labels from data and SHACL graph when adding labels to validation graph.",
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
        )
    ]
)


class ShaclValidation(WorkflowPlugin):
    """Example Workflow Plugin: Random Values"""

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
        add_shui_conforms_to_validation_graph
    ) -> None:
        if not output_values and not generate_graph:
            raise ValueError("Generate validation graph or Output values parameter needs to be set to true.")
        if generate_graph:
            if not validators.url(validation_graph_uri):
                raise ValueError("Validation graph URI parameter is invalid.")
        self.data_graph_uri = data_graph_uri
        self.shacl_graph_uri = shacl_graph_uri
        self.validation_graph_uri = validation_graph_uri
        self.generate_graph = generate_graph
        self.output_values = output_values
        self.owl_imports_resolution = owl_imports_resolution
        self.clear_validation_graph = clear_validation_graph
        self.skolemize_validation_graph = skolemize_validation_graph
        self.add_labels_to_validation_graph = add_labels_to_validation_graph
        if add_labels_to_validation_graph:
            self.include_graphs_labels = include_graphs_labels
        else:
            self.include_graphs_labels = False
        self.add_shui_conforms_to_validation_graph = add_shui_conforms_to_validation_graph
        setup_cmempy_super_user_access()


    def add_prov(self, validation_graph, utctime):
        validation_report_uri = list(validation_graph.subjects(RDF.type, SH.ValidationReport))[0]
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

    def get_label(self, g, s):
        SKOSXL = Namespace("http://www.w3.org/2008/05/skos-xl#")
        l = g.preferredLabel(s, labelProperties=(SKOSXL.prefLabel/SKOSXL.literalForm, SKOS.prefLabel, RDFS.label))
        if l:
            return Literal(str(l[0][1]), datatype=XSD.string)

    def add_labels(self, validation_graph, data_graph, shacl_graph, validation_result_uris):
        focus_nodes = []
        validation_report_uri = list(validation_graph.subjects(RDF.type, SH.ValidationReport))[0]
        conforms = str(list(validation_graph.objects(validation_report_uri, SH.conforms))[0])
        label = "SHACL validation report, conforms" if conforms == "true" else "SHACL validation report, nonconforms"
        validation_graph.add((
            validation_report_uri,
            RDFS.label,
            Literal(label, datatype=XSD.string)
        ))
        for validation_result_uri in validation_result_uris:
            message = str(list(validation_graph.objects(validation_result_uri, SH.resultMessage))[0])
            result_path = str(list(validation_graph.objects(validation_result_uri, SH.resultPath))[0]).split("/")[-1]
            label = f"SHACL: {result_path}: {message}"
            validation_graph.add((
                validation_result_uri,
                RDFS.label,
                Literal(label, datatype=XSD.string)
            ))
            if self.include_graphs_labels:
                focus_node = list(validation_graph.objects(validation_result_uri, SH.focusNode))[0]
                if self.add_shui_conforms_to_validation_graph:
                    focus_nodes.append(focus_node)
                label = self.get_label(data_graph, focus_node)
                if label:
                    validation_graph.add((focus_node, RDFS.label, label))
                value = list(validation_graph.objects(validation_result_uri, SH.value))
                if value:
                    if isinstance(value[0], (URIRef, BNode)):
                        label = self.get_label(data_graph, value[0])
                        if label:
                            validation_graph.add((value[0], RDFS.label, label))
                source_shape =  list(validation_graph.objects(validation_result_uri, SH.sourceShape))[0]
                label = self.get_label(shacl_graph, source_shape)
                if label:
                    validation_graph.add((source_shape, RDFS.label, label))
        return validation_graph, focus_nodes

    def add_shui_conforms(self, validation_graph, validation_result_uris, focus_nodes):
        itr = focus_nodes if focus_nodes else validation_result_uris
        for i in itr:
            s = i if focus_nodes else list(validation_graph.objects(i, SH.focusNode))[0]
            validation_graph.add((
                s,
                URIRef("https://vocab.eccenca.com/shui/conforms"),
                Literal(False, datatype=XSD.boolean)
            ))
        return validation_graph

    def post_graph(self, validation_graph):
        temp_file = f"{uuid4()}.nt"
        validation_graph.serialize(temp_file, format="nt", encoding="utf-8")
        self.log.info(f"Created temporary file {temp_file} with size {getsize(temp_file)} bytes")
        post_streamed(
            self.validation_graph_uri,
            temp_file,
            replace=self.clear_validation_graph,
            content_type="application/n-triples"
        )
        remove(temp_file)
        self.log.info(f"Deleted temporary file")

    def check_object(self, g, s, p, data_graph, shacl_graph):
        if p in (SH.sourceShape, SH.conforms):
            label_g = shacl_graph
        elif p in (SH.value, SH.resultPath, SH.focusNode):
            label_g = data_graph
        l = list(g.objects(s, p))
        o = l[0] if l else None
        v = ""
        if o:
            if isinstance(o, URIRef):
                if self.include_graphs_labels and p not in (SH.sourceConstraintComponent, SH.resultSeverity):
                    label = self.get_label(label_g, o)
                    v = str(label) if label else o
                else:
                    v = o
            elif isinstance(o, BNode):
                if self.include_graphs_labels:
                    label = self.get_label(label_g, o)
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
            entities.append(
                Entity(
                    uri=validation_result,
                    values=values
                )
            )
        paths = [EntityPath(path=SH[p]) for p in shp] + \
                    [
                        EntityPath(path=SH.conforms),
                        EntityPath(path=PROV.wasDerivedFrom),
                        EntityPath(path=PROV.wasInformedBy),
                        EntityPath(path=PROV.generatedAtTime)
                    ]
        schema = EntitySchema(
            type_uri=SH.ValidationResult,
            paths=paths
        )
        return Entities(entities=entities, schema=schema)

    def get_graph(self, i):
        g = Graph()
        g.parse(data=get(i, owl_imports_resolution=self.owl_imports_resolution).text, format="turtle")
        return g

    def execute(self, inputs=()):  # -> Entities:
        self.log.info(f"Loading data graph <{self.data_graph_uri}> into memory...")
        start = time()
        data_graph = self.get_graph(self.data_graph_uri)
        self.log.info(f"Finished loading data graph in {round(time() - start, 3)} seconds")
        self.log.info(f"Loading SHACL graph <{self.shacl_graph_uri}> into memory...")
        start = time()
        shacl_graph = self.get_graph(self.shacl_graph_uri)
        self.log.info(f"Finished loading SHACL graph in {round(time() - start, 3)} seconds")
        self.log.info(f"Starting SHACL validation...")
        start = time()
        conforms, validation_graph, results_text = validate(data_graph, shacl_graph=shacl_graph, inplace=True)
        self.log.info(f"Finished SHACL validation in {round(time() - start, 3)} seconds")
        utctime = str(datetime.fromtimestamp(int(time()))).replace(" ", "T") + "Z"
        if self.output_values:
            self.log.info("Creating entities")
            entities = self.make_entities(validation_graph, data_graph, shacl_graph, utctime)
        if self.generate_graph:
            if self.skolemize_validation_graph:
                self.log.info("Skolemizing validation graph")
                validation_graph = validation_graph.skolemize(basepath=self.validation_graph_uri)
            if self.add_labels_to_validation_graph or self.add_shui_conforms_to_validation_graph:
                validation_graph_uris = validation_graph.subjects(RDF.type, SH.ValidationResult)
                focus_nodes = None
                if self.add_labels_to_validation_graph:
                    self.log.info("Adding labels to validation graph")
                    validation_graph, focus_nodes = self.add_labels(validation_graph, data_graph, shacl_graph, validation_graph_uris)
                if self.add_shui_conforms_to_validation_graph:
                    self.log.info("Adding shui:conforms flags to validation graph")
                    validation_graph = self.add_shui_conforms(validation_graph, validation_graph_uris, focus_nodes)
            self.log.info("Adding PROV information validation graph")
            validation_graph = self.add_prov(validation_graph, utctime)
            self.log.info("Posting SHACL validation graph...")
            self.post_graph(validation_graph)
        if self.output_values:
            self.log.info("Outputting entities")
            return entities
