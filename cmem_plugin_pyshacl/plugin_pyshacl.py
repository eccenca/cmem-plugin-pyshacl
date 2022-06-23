import validators
from rdflib import Graph, URIRef, Literal, BNode, RDF, SH, PROV, XSD
from pyshacl import validate
from os import remove # , environ
from time import time
from datetime import datetime
from uuid import uuid4
from cmem.cmempy.dp.proxy.graph import get, post
from cmem.cmempy.queries import SparqlQuery
#from cmem.cmempy.rdflib.cmem_store import CMEMStore
from cmem_plugin_base.dataintegration.utils import setup_cmempy_super_user_access
from cmem_plugin_base.dataintegration.description import Plugin, PluginParameter
from cmem_plugin_base.dataintegration.types import BoolParameterType, StringParameterType
from cmem_plugin_base.dataintegration.parameter.graph import GraphParameterType
from cmem_plugin_base.dataintegration.plugins import WorkflowPlugin
from cmem_plugin_base.dataintegration.entity import (
    Entities, Entity, EntitySchema, EntityPath,
)
# from cmem.cmempy.api import get_token
# from rdflib.plugins.stores.sparqlstore import SPARQLStore


add_label_query = """# add labels for RDFunit and shaclvalidate test results
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

# {{GRAPH}} -> http://ld.company.org/prod-shacl-validate/

# RDFunit: TestCaseResult
INSERT { GRAPH <{{GRAPH}}> { 
  ?tr rdfs:label ?descr_ .
}}
WHERE { GRAPH <{{GRAPH}}> { 
  ?tr a <http://rdfunit.aksw.org/ns/core#TestCaseResult> .
  { ?tr <http://purl.org/dc/terms/description> ?descr . }
  UNION 
  { ?tr <http://persistence.uni-leipzig.org/nlp2rdf/ontologies/rlog#message> ?descr . }
  FILTER NOT EXISTS { ?tr rdfs:label ?label .}
  BIND(CONCAT("RU: ", ?descr) AS ?descr_ )
}};

# RDFunit: PatternBasedTestCase / ManualTestCase
INSERT { GRAPH <{{GRAPH}}> { 
  ?tc rdfs:label ?descr_ .
}}
WHERE { GRAPH <{{GRAPH}}> { 
  { 
    ?tc a <http://rdfunit.aksw.org/ns/core#PatternBasedTestCase> . 
  } UNION {
    ?tc a <http://rdfunit.aksw.org/ns/core#ManualTestCase> . 
  }

  ?tc <http://purl.org/dc/terms/description> ?descr . 
  FILTER NOT EXISTS { ?tc rdfs:label ?label .}
  BIND(CONCAT("RU: ", ?descr) AS ?descr_ )
}};

# shaclvalidate
INSERT { GRAPH <{{GRAPH}}> {
    ?vr rdfs:label ?descr .
}}
WHERE { GRAPH <{{GRAPH}}> { 
  ?vr a <http://www.w3.org/ns/shacl#ValidationResult> .
  ?vr <http://www.w3.org/ns/shacl#resultPath> ?path .
  BIND(REPLACE(STR(?path), ".*[/#]([^/#])", "$1") AS ?pathLocal) .
  ?vr <http://www.w3.org/ns/shacl#resultMessage> ?msg .
  BIND(CONCAT("SH: ", ?pathLocal, ": ", ?msg) AS ?descr) .
  FILTER NOT EXISTS { ?vr rdfs:label ?label . }
}};

# shaclvalidate
INSERT { GRAPH <{{GRAPH}}> {
    ?vr rdfs:label ?descr .
}}
WHERE { GRAPH <{{GRAPH}}> { 
  ?vr a <http://www.w3.org/ns/shacl#ValidationReport> .
  ?vr <http://www.w3.org/ns/shacl#conforms> ?conf .
  BIND(CONCAT("SH: Validation Report, ", STR(?conf)) AS ?descr) .
  FILTER NOT EXISTS { ?vr rdfs:label ?label . }
}}"""

update_failure_flag_query = """# update failure flag
PREFIX owl:     <http://www.w3.org/2002/07/owl#>
PREFIX rdfs:    <http://www.w3.org/2000/01/rdf-schema#>
PREFIX org:     <http://www.w3.org/ns/org#>
PREFIX vcard:   <http://www.w3.org/2006/vcard/ns#>
PREFIX rlog:    <http://persistence.uni-leipzig.org/nlp2rdf/ontologies/rlog#>
PREFIX sh:      <http://www.w3.org/ns/shacl#>
PREFIX shui:    <https://vocab.eccenca.com/shui/>

# {{GRAPH}} -> http://ld.company.org/prod-shacl-validate/

DELETE { GRAPH <{{GRAPH}}> { ?res shui:conforms false . } }
WHERE { GRAPH <{{GRAPH}}> { ?res shui:conforms false . } };

INSERT { GRAPH <{{GRAPH}}> { ?res shui:conforms false . } }
WHERE { 
  {
    ?tc_ rlog:resource ?res .
  } UNION {
    ?tc_ sh:focusNode ?res .
  } 
}"""

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
        # PluginParameter(
        #     param_type = BoolParameterType(),
        #     name="use_cmem_store",
        #     label="Use CMEM store",
        #     description="Use CMEM store",
        #     default_value=False
        # ),
        PluginParameter(
            param_type = BoolParameterType(),
            name="clear_validation_graph",
            label="Clear validation graph",
            description="Clear the validation graph before workflow execution.",
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
            label="Skolemize validation graph",
            description="Skolemize the validation graph.",
            default_value=True,
            advanced=True
        ),
        # PluginParameter(
        #     param_type = BoolParameterType(),
        #     name="use_sparql_endpoint",
        #     label="Use SPARQL endpoint for data graph",
        #     description="Use SPARQL endpoint for the data graph (slow).",
        #     default_value=False,
        #     advanced=True
        # )
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
        # use_cmem_store,
        clear_validation_graph,
        owl_imports_resolution,
        skolemize_validation_graph,
        # use_sparql_endpoint
    ) -> None:
        if not output_values and not generate_graph:
            raise ValueError("Generate validation graph or Output values parameter needs to be set to true.")
        if generate_graph:
            if not validators.url(validation_graph_uri):
                raise ValueError("Validation graph URI parameter is invalid.")
            if not validation_graph_uri.endswith(("/", "#")):
                validation_graph_uri += "/"
        self.data_graph_uri = data_graph_uri
        self.shacl_graph_uri = shacl_graph_uri
        self.validation_graph_uri = validation_graph_uri if generate_graph \
            else f"https://eccenca.com/cmem-plugin-pyshacl/graph/{uuid4()}/"
        self.generate_graph = generate_graph
        self.output_values = output_values
        self.owl_imports_resolution = owl_imports_resolution
        self.clear_validation_graph = clear_validation_graph
        self.skolemize_validation_graph = skolemize_validation_graph
        # self.use_sparql_endpoint = use_sparql_endpoint
        # self.use_cmem_store = False  # use_cmem_store
        setup_cmempy_super_user_access()
        # if use_sparql_endpoint:
        #     self.cmem_base_uri = environ.get("CMEM_BASE_URI")
        #     self.oauth_client_secret = environ.get("OAUTH_CLIENT_SECRET")
        #     self.oauth_token_uri = f"{self.cmem_base_uri}/auth/realms/cmem/protocol/openid-connect/token"

    def post_process(self, validation_graph, utctime):
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

    def post_graph(self, validation_graph):
        temp_file = f"{uuid4()}.nt"
        validation_graph.serialize(temp_file, format="nt", encoding="utf-8")
        post(self.validation_graph_uri, temp_file, replace=self.clear_validation_graph)
        remove(temp_file)

    def check_object(self, g, s, p):
        l = list(g.objects(s, p))
        o = l[0] if l else None
        v = ""
        if o:
            if isinstance(o, URIRef):
                v = o
            elif isinstance(o, BNode):
                v = g.cbd(o).serialize(format="turtle")
            elif isinstance(o, Literal) and p == SH.value:
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
        #if self.use_cmem_store:
        #    g = Graph(store=CMEMStore(), identifier=i)
        #else:
        # if not self.use_sparql_endpoint:
        #     g = Graph()
        #     g.parse(data=get(i, owl_imports_resolution=self.owl_imports_resolution).text, format="turtle")
        #     return g
        # else:
        #     endpoint = f"{self.cmem_base_uri}/dataplatform/proxy/default/sparql"
        #     store = SPARQLStore(endpoint, headers=self.get_headers())
        #     g = Graph(store=store, identifier=URIRef(self.data_graph_uri))
        g = Graph()
        g.parse(data=get(i, owl_imports_resolution=self.owl_imports_resolution).text, format="turtle")
        return g

    # def get_headers(self):
    #     # oauth_token_uri = f"{CMEM_BASE_URI}/auth/realms/cmem/protocol/openid-connect/token"
    #     oauth_credentials = {
    #         "grant_type": "client_credentials",
    #         "client_id": "cmem-service-account",
    #         "client_secret": self.oauth_client_secret
    #     }
    #     r = get_token(self.oauth_token_uri, oauth_credentials)
    #     return {"Authorization": f"Bearer {r['access_token']}"}


    def execute(self, inputs=()):  # -> Entities:
        self.log.info(f"Loading data graph <{self.data_graph_uri}>.")
        data_graph = self.get_graph(self.data_graph_uri)
        self.log.info(f"Loading SHACL graph <{self.shacl_graph_uri}>.")
        shacl_graph = self.get_graph(self.shacl_graph_uri)
        self.log.info("Starting SHACL validation.")
        # using undocumented inplace option to skip working-copy step, see https://github.com/RDFLib/pySHACL/issues/60#issuecomment-888663172
        conforms, validation_graph, results_text = validate(data_graph, shacl_graph=shacl_graph, inplace=True)
        utctime = str(datetime.fromtimestamp(int(time()))).replace(" ", "T") + "Z"
        self.log.info(f"Config length: {len(self.config.get())}")
        validation_graph = self.post_process(validation_graph, utctime)
        if self.output_values:
            self.log.info("Creating entities.")
            entities = self.make_entities(validation_graph, utctime)
        if self.generate_graph:
            if self.skolemize_validation_graph:
                # replaces blank nodes including thoses that are values in validation results
                self.log.info("Skolemizing validation graph.")
                validation_graph = validation_graph.skolemize(basepath=self.validation_graph_uri)
            self.log.info("Posting SHACL validation graph.")
            self.post_graph(validation_graph)
            alq = SparqlQuery(add_label_query, query_type="UPDATE")
            alq.get_results(placeholder={"GRAPH": self.validation_graph_uri })
            uffq = SparqlQuery(update_failure_flag_query, query_type="UPDATE")
            uffq.get_results(placeholder={"GRAPH": self.validation_graph_uri })
        if self.output_values:
            return entities
