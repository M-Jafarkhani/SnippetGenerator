from rdflib import Graph, URIRef, RDF, BNode, OWL
from rdflib.namespace import RDFS
from collections import deque

class SnippetGenerator:
    def __init__(self, graph, query):
        self.graph = graph
        self.query = query
        self.processed = deque()
        self.unprocessed = deque()
        self.final_graph = Graph()
    
    def bind_ns(self):
        for prefix, uri in self.graph.namespaces():
            self.final_graph.bind(prefix, uri)
    
    @staticmethod
    def extract_name_from_uri(uri):
        if not isinstance(uri, str):
            return uri
        if "#" in uri:
            return uri.split("#")[-1]
        return uri.rstrip("/").split("/")[-1]

    def add_blank_node_triples(self, bnode):
        for b_s, b_p, b_o in self.graph.triples((bnode, None, None)):
            if self.extract_name_from_uri(str(b_o)) not in self.processed:
                self.unprocessed.append(self.extract_name_from_uri(str(b_o)))
            self.final_graph.add((b_s, b_p, b_o))
            if isinstance(b_o, BNode):
                self.add_blank_node_triples(b_o)

    def get_item_content(self, class_name):
        class_uri = None
        for _, ns_uri in self.graph.namespaces():
            potential_class = URIRef(ns_uri + class_name)
            if (potential_class, RDF.type, None) in self.graph:
                class_uri = potential_class
                break
        if not class_uri:
            return f"Class '{class_name}' not found in the ontology."
        self.process_items(class_uri)
        for s, p, o in self.graph.triples((class_uri, None, None)):
            self.final_graph.add((s, p, o))
            if isinstance(o, BNode):
                self.add_blank_node_triples(o)

    def get_related_items(self, class_uri, predicates):
        related_items = set()
        for subject, predicate, obj in self.graph:
            if predicate in predicates and subject == class_uri:
                related_items.add(self.extract_name_from_uri(str(obj)))
        return list(related_items)

    def process_items(self, class_uri):
        predicates = {RDFS.subClassOf, RDFS.domain, RDFS.range, RDFS.subPropertyOf, OWL.inverseOf}
        for class_name in self.get_related_items(class_uri, predicates):
            if class_name not in self.processed:
                self.unprocessed.append(class_name)

    def run(self):
        self.bind_ns()
        self.unprocessed.append(self.query)
        while self.unprocessed:
            current_class = self.unprocessed.popleft()
            if current_class in self.processed:
                continue
            self.processed.append(current_class)
            self.get_item_content(current_class)
        rdf_content = self.final_graph.serialize(format="ttl")
        if len(rdf_content.strip()) > 0:
            with open(f"snippets/{self.query}.ttl", "w") as file:
                file.write(rdf_content)

if __name__ == "__main__":
    graph_file = "metadata4ing.ttl"
    graph = Graph()
    graph.parse(graph_file, format="ttl")
    definitions = set()
    for a, _, _ in graph.triples((None, RDF.type, None)):
        definitions.add(SnippetGenerator.extract_name_from_uri(str(a)))
    for query in definitions:
        if query:
            processor = SnippetGenerator(graph, query)
            processor.run()
