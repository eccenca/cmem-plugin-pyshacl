import validators
from rdflib import Graph, RDF, SH, URIRef, PROV, XSD, Literal, PROV, BNode
from pyshacl import validate
from os import remove
from time import time
from datetime import datetime
from uuid import uuid4
from cmem.cmempy.dp.proxy.graph import get, post
from cmem_plugin_base.dataintegration.description import Plugin, PluginParameter
from cmem_plugin_base.dataintegration.types import BoolParameterType, StringParameterType
from cmem_plugin_base.dataintegration.plugins import WorkflowPlugin
from cmem_plugin_base.dataintegration.entity import (
    Entities, Entity, EntitySchema, EntityPath,
)


@Plugin(
    label="SHACL validation with pySHACL",
    plugin_id="shacl-pyshacl",
    description="Performs SHACL validation with pySHACL.",
    documentation="""TBD""",
    parameters=[
        PluginParameter(
            param_type = StringParameterType(),
            name="data_graph_uri",
            label="Data graph URI",
            description="Data graph URI"
        ),
        PluginParameter(
            param_type = StringParameterType(),
            name="shacl_graph_uri",
            label="SHACL graph URI",
            description="SHACL graph URI"
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
            description="Generate validation graph (bool)",
            default_value=False
        ),
        PluginParameter(
            param_type = BoolParameterType(),
            name="output_values",
            label="Output values",
            description="Output values (bool)",
            default_value=False
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
        output_values
    ) -> None:
        if not validators.url(data_graph_uri):
            raise ValueError("Data graph URI parameter is invalid.")
        if not validators.url(shacl_graph_uri):
            raise ValueError("SHACL graph URI parameter is invalid.")
        if not output_values and not generate_graph:
            raise ValueError("Generate validation graph or Output values parameter needs to be set to true.")
        if generate_graph:
            if not validators.url(validation_graph_uri):
                raise ValueError("Validation graph URI parameter is invalid.")
            if not validation_graph_uri.endswith(("/", "#")):
                validation_graph_uri += "/"
        self.data_graph_uri = data_graph_uri
        self.shacl_graph_uri = shacl_graph_uri
        self.validation_graph_uri = validation_graph_uri
        self.generate_graph = generate_graph
        self.output_values = output_values

    def post_process(self, validation_graph):
        # replace blank nodes and add prov information
        validation_graph_uri = self.validation_graph_uri if self.generate_graph \
            else f"https://eccenca.com/cmem-plugin-pyshacl/graph/{uuid4()}/"
        utctime = str(datetime.fromtimestamp(int(time()))).replace(" ", "T") + "Z"
        validation_graph = validation_graph.skolemize(basepath=validation_graph_uri)
        validation_report_uri = list(validation_graph.subjects(RDF.type, SH.ValidationReport))[0]
        validation_graph.add((validation_report_uri, PROV.wasDerivedFrom, URIRef(self.data_graph_uri)))
        validation_graph.add((validation_report_uri, PROV.wasInformedBy, URIRef(self.shacl_graph_uri)))
        validation_graph.add((validation_report_uri, PROV.generatedAtTime, Literal(utctime, datatype=XSD.dateTime)))
        return validation_graph

    def post_graph(self, validation_graph):
        temp_file = f"{uuid4()}.nt"
        validation_graph.serialize(temp_file, format="nt", encoding="utf-8")
        post(self.validation_graph_uri, temp_file, replace=True)
        remove(temp_file)

    def check_object(self, g, s, p):
        l = list(g.objects(s, p))
        if l:
            o = l[0]
            if p == SH.value:
                if type(o) == Literal:
                    t = "Literal"
                    if o.datatype:
                        t += f" ({o.datatype})"
                elif type(o) == URIRef:
                    t = "IRI"
                elif type(o) == BNode:
                    t = "Blank Node"
                return [[o], [t]]
            else:
                return [[o]]
        else:
            return 2 * [[""]] if p == SH.value else [[""]]

    def make_entities(self, g):
        shp = [
            "focusNode",
            "resultPath",
            "value",
            "sourceShape",
            "sourceConstraintComponent",
            "detail",
            "resultMessage",
            "resultSeverity"
        ]
        validation_results = list(g.subjects(RDF.type, SH.ValidationResult))
        values = []
        for p in shp:
            values += self.check_object(g, validation_results[0], SH[p])
        values += [[list(g.objects(predicate=SH.conforms))[0]], [self.data_graph_uri], [self.shacl_graph_uri]]
        entities = [Entity(
            uri=validation_results[0],
            values = values
        )]
        for validation_result in validation_results[1:]: #g.subjects(RDF.type, SH.ValidationResult):
            values = []
            for p in shp:
                values += self.check_object(g, validation_result, SH[p])
            values += 3 * [[""]]
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
                        EntityPath(path=PROV.wasInformedBy)
                    ]
        paths.insert(3, EntityPath(path="https://eccenca.com/cmem-plugin-pyshacl/vocab/value_type"))
        schema = EntitySchema(
            type_uri=SH.ValidationResult,
            paths=paths
        )
        return Entities(entities=entities, schema=schema)

    def execute(self, inputs=()):  # -> Entities:
        self.log.info(f"Loading data graph <{self.data_graph_uri}>.")
        r = get(self.data_graph_uri)
        data_graph = Graph()
        data_graph.parse(data=r.text, format="nt")
        self.log.info(f"Loading SHACL graph <{self.shacl_graph_uri}>.")
        r = get(self.shacl_graph_uri)
        shacl_graph = Graph()
        shacl_graph.parse(data=r.text, format="nt")
        self.log.info("Starting SHACL validation.")
        conforms, validation_graph, results_text = validate(data_graph, shacl_graph=shacl_graph)
        validation_graph = self.post_process(validation_graph)
        self.log.info(f"Config length: {len(self.config.get())}")
        if self.generate_graph:
            self.log.info("Posting SHACL validation graph.")
            self.post_graph(validation_graph)
        if self.output_values:
            self.log.info("Creating entities.")
            return self.make_entities(validation_graph)
        # else:
        #    return Entities(entities=[], schema=EntitySchema(type_uri="", paths=[]))#EntityPath(path="")))
