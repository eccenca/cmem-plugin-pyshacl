import validators
from rdflib import Graph, URIRef, Literal, BNode, RDF, SH, PROV, XSD
from pyshacl import validate
from os import remove
from time import time
from datetime import datetime
from uuid import uuid4
from cmem.cmempy.dp.proxy.graph import get, post
#from cmem.cmempy.rdflib.cmem_store import CMEMStore
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
    documentation="""TBD""",
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
            description="Data graph URI"
        ),
        PluginParameter(
            param_type = GraphParameterType(classes = [
                "https://vocab.eccenca.com/shui/ShapeCatalog"
            ]
            ),
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
            name="use_cmem_store",
            label="Use CMEM store",
            description="Use CMEM store",
            default_value=False
        ),
        PluginParameter(
            param_type = BoolParameterType(),
            name="owl_imports_resolution",
            label="Resolve owl:imports",
            description="Resolve graph tree defined via owl:imports.",
            default_value=True
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
        use_cmem_store,
        owl_imports_resolution
    ) -> None:
        #if not validators.url(data_graph_uri):
        #    raise ValueError("Data graph URI parameter is invalid.")
        #if not validators.url(shacl_graph_uri):
        #    raise ValueError("SHACL graph URI parameter is invalid.")
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
        self.validation_graph_uri = validation_graph_uri if generate_graph \
            else f"https://eccenca.com/cmem-plugin-pyshacl/graph/{uuid4()}/"
        self.generate_graph = generate_graph
        self.output_values = output_values
        self.owl_imports_resolution = owl_imports_resolution
        self.use_cmem_store = False  # use_cmem_store
        setup_cmempy_super_user_access()

    def post_process(self, validation_graph, utctime):
        # replace blank nodes and add prov information
        # validation_report_uri = list(validation_graph.subjects(RDF.type, SH.ValidationReport))[0]
        # validation_graph_skolemized = validation_graph.skolemize(
        #     bnode=validation_report_uri,
        #     basepath=self.validation_graph_uri
        # )
        # for v in validation_graph_skolemized.subjects(RDF.type, SH.ValidationResult):
        #     validation_graph_skolemized = validation_graph_skolemized.skolemize(
        #         bnode=v,
        #         basepath=self.validation_graph_uri
        #     )
        validation_graph_skolemized = validation_graph.skolemize(basepath=self.validation_graph_uri)
        validation_report_uri = list(validation_graph_skolemized.subjects(RDF.type, SH.ValidationReport))[0]
        validation_graph_skolemized.add((
            validation_report_uri,
            PROV.wasDerivedFrom,
            URIRef(self.data_graph_uri)
        ))
        validation_graph_skolemized.add((
            validation_report_uri,
            PROV.wasInformedBy,
            URIRef(self.shacl_graph_uri)
        ))
        validation_graph_skolemized.add((
            validation_report_uri,
            PROV.generatedAtTime,
            Literal(utctime, datatype=XSD.dateTime)
        ))
        return validation_graph_skolemized

    def post_graph(self, validation_graph):
        temp_file = f"{uuid4()}.nt"
        validation_graph.serialize(temp_file, format="nt", encoding="utf-8")
        post(self.validation_graph_uri, temp_file, replace=True)
        remove(temp_file)

    def check_object(self, g, s, p):
        l = list(g.objects(s, p))
        o = l[0] if l else None
        v = ""
        if o:
            if type(o) == URIRef:
                v = o
            elif type(o) == BNode:
                v = g.cbd(o).serialize(format="turtle")
            elif type(o) == Literal and p == SH.value:
                v = f'"{o}"^^<{o.datatype}>' if o.datatype else f'"{o}"'
        return v

    def make_entities(self, g, utctime):
        shp = [
            "focusNode",
            "resultPath",
            "value",
            "sourceShape",
            "sourceConstraintComponent",
            #"detail",
            "resultMessage",
            "resultSeverity"
        ]
        entities =[]
        for i, validation_result in enumerate(list(g.subjects(RDF.type, SH.ValidationResult))):
            values = [[self.check_object(g, validation_result, SH[p])] for p in shp]
            if i == 0:
                values += [
                    [list(g.objects(predicate=SH.conforms))[0]],
                    [self.data_graph_uri],
                    [self.shacl_graph_uri],
                    [utctime]
                ]
            else:
                values += 4 * [[""]]
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
        if False:  # self.use_cmem_store:
            g = Graph(store=CMEMStore(), identifier=i)
        else:
            g = Graph()
            g.parse(data=get(i, owl_imports_resolution=self.owl_imports_resolution).text, format="nt")
        return g

    def execute(self, inputs=()):  # -> Entities:
        self.log.info(f"Loading data graph <{self.data_graph_uri}>.")
        data_graph = self.get_graph(self.data_graph_uri)
        self.log.info(f"Loading SHACL graph <{self.shacl_graph_uri}>.")
        shacl_graph = self.get_graph(self.shacl_graph_uri)
        self.log.info("Starting SHACL validation.")
        conforms, validation_graph, results_text = validate(data_graph, shacl_graph=shacl_graph)
        utctime = str(datetime.fromtimestamp(int(time()))).replace(" ", "T") + "Z"
        self.log.info(f"Config length: {len(self.config.get())}")
        validation_graph = self.post_process(validation_graph, utctime)
        if self.generate_graph:
            self.log.info("Posting SHACL validation graph.")
            self.post_graph(validation_graph)
        if self.output_values:
            self.log.info("Creating entities.")
            return self.make_entities(validation_graph, utctime)
