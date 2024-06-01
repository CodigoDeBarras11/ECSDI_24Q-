from os import path, getcwd
import sys
sys.path.append(path.dirname(getcwd()))
from rdflib import Graph, Literal, XSD, Namespace, RDF
from docs.ecsdi import ECSDI

productns = ECSDI.Producto
product_graph = Graph()

products_graph = Graph()
us = None
if path.exists("product.ttl"):
    product_graph.parse("product_ori.ttl", format="turtle")
else:raise FileNotFoundError()

products_graph.bind('ECSDI', ECSDI)
product_class = ["Blender", "Computer", "Phone"]
results= {}
counters = {}
counters['max'] = 0
for p_class in product_class:
    query = """
        PREFIX pont: <http://www.products.org/ontology/>
        PREFIX pontp: <http://www.products.org/ontology/property/>
        PREFIX pontr: <http://www.products.org/ontology/resource/>

        SELECT ?product ?name ?price ?weight ?brand
        WHERE {
            ?product rdf:type pont:%s .
            ?product pontp:nombre ?name .
            ?product pontp:precio ?price .
            ?product pontp:peso ?weight .
            ?product pontp:tieneMarca ?brand_uri .
            ?brand_uri pontp:nombre ?brand .
        """ % p_class
    query += "}"
    results[p_class] = []
    result = product_graph.query(query)
    for row in result:
        product = {
            "name": str(row.name),
            "price": float(row.price),
            "weight": float(row.weight),
            "brand": str(row.brand)
        }
        results[p_class].append(product)
    counters[p_class] = len(results[p_class])
    if counters[p_class] > counters["max"]: counters["max"] = counters[p_class]

productid = 0
for i in range(counters["max"]):
    for p_class in product_class:
        if i < counters[p_class]:
            prod = productns + '/'+str(productid)
            products_graph.add((prod, RDF.type, productns))
            products_graph.add((prod, ECSDI.id, Literal(productid)))
            products_graph.add((prod, ECSDI.tipoproducto, Literal(p_class)))
            nombre = str(results[p_class][i]['name'])
            if nombre:
                products_graph.add((prod, ECSDI.nombre, Literal(nombre)))
            precio = float(results[p_class][i]['price'])
            if precio:
                products_graph.add((prod, ECSDI.precio, Literal(precio)))
            peso = float(results[p_class][i]['weight'])
            if peso:
                products_graph.add((prod, ECSDI.peso, Literal(peso)))
            tieneMarca = str(results[p_class][i]['brand'])
            if tieneMarca:
                products_graph.add((prod, ECSDI.tieneMarca, Literal(tieneMarca)))
            productid += 1
agn = Namespace("http://www.agentes.org#")
products_graph.add((agn.productid, XSD.positiveInteger, Literal(productid)))
products_graph.serialize("product.ttl", format="turtle")
print(productid)